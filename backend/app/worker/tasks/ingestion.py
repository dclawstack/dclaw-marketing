"""Q2 ingestion Celery task — pull bytes, extract text, chunk, store."""

from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.ingestion import (
    DocumentChunk,
    IngestionSource,
    IngestionSourceType,
    IngestionStatus,
)
from app.models.job import JobStatus
from app.services.embeddings import embed_texts_sync
from app.services.ingestion import chunk_text, estimate_tokens, extract_text
from app.services.storage import sync_s3_client
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession, update_job


@celery_app.task(name="app.worker.tasks.ingest_asset", bind=True)
def ingest_asset(self, job_id: str, source_id: str) -> dict:
    """Ingest a file Asset → DocumentChunks.

    Lifecycle stages reflected in the IngestionSource.status field:
    queued → fetching → parsing → chunking → ready (or failed).
    """
    jid = UUID(job_id)
    sid = UUID(source_id)

    update_job(jid, status=JobStatus.running, celery_task_id=self.request.id, progress_label="fetching")

    try:
        with SyncSession() as session:
            return _do_ingest(session, jid, sid)
    except Exception as exc:
        update_job(jid, status=JobStatus.failed, error_message=str(exc))
        with SyncSession() as session:
            src = session.get(IngestionSource, sid)
            if src is not None:
                src.status = IngestionStatus.failed
                src.error_message = str(exc)
                session.commit()
        raise


def _do_ingest(session: Session, job_id: UUID, source_id: UUID) -> dict:
    source = session.get(IngestionSource, source_id)
    if source is None:
        raise ValueError(f"IngestionSource {source_id} not found.")

    # ------ fetch ------
    source.status = IngestionStatus.fetching
    session.commit()
    update_job(job_id, progress=0.1, progress_label="fetching from storage")

    asset_id = UUID(source.source_reference)
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise ValueError(f"Asset {asset_id} not found.")

    s3 = sync_s3_client()
    obj = s3.get_object(Bucket=asset.bucket, Key=asset.storage_key)
    content: bytes = obj["Body"].read()

    # ------ parse ------
    source.status = IngestionStatus.parsing
    session.commit()
    update_job(job_id, progress=0.4, progress_label=f"parsing {asset.mime_type}")
    text = extract_text(content, asset.mime_type)

    # ------ chunk ------
    source.status = IngestionStatus.chunking
    session.commit()
    update_job(job_id, progress=0.6, progress_label="chunking")
    chunks = chunk_text(text)

    # ------ embed (Q3) ------
    source.status = IngestionStatus.embedding
    session.commit()
    update_job(job_id, progress=0.8, progress_label=f"embedding {len(chunks)} chunks")
    vectors, model_name = ([], "")
    if chunks:
        vectors, model_name = embed_texts_sync(chunks)

    for i, chunk in enumerate(chunks):
        session.add(
            DocumentChunk(
                organization_id=source.organization_id,
                source_id=source.id,
                position=i,
                text=chunk,
                estimated_tokens=estimate_tokens(chunk),
                embedding=vectors[i] if i < len(vectors) else None,
                embedding_model=model_name if vectors else None,
            )
        )
    source.document_chunks_created = len(chunks)
    source.metadata_json = {
        "original_byte_size": len(content),
        "text_byte_size": len(text),
        "chunk_count": len(chunks),
        "mime_type": asset.mime_type,
        "embedding_model": model_name,
    }
    source.status = IngestionStatus.ready
    source.updated_at = datetime.now(timezone.utc)
    session.commit()

    result = {
        "source_id": str(source.id),
        "chunks": len(chunks),
        "bytes": len(content),
    }
    update_job(
        job_id,
        status=JobStatus.succeeded,
        progress=1.0,
        progress_label=f"ready ({len(chunks)} chunks)",
        result_json=result,
    )
    return result


# ---------- dispatcher (freshness + live_pollers refer to this) -------------


@celery_app.task(name="app.worker.tasks.process_ingestion_source", bind=True)
def process_ingestion_source(self, source_id: str) -> dict:
    """Look up an IngestionSource and dispatch to the right per-type task.

    Used by the freshness sweep (#179) and the live URL/git pollers
    (#185) which only know the source id, not the source type.
    """
    sid = UUID(source_id)
    with SyncSession() as session:
        src = session.get(IngestionSource, sid)
        if src is None:
            return {"source_id": source_id, "dispatched": False, "reason": "not_found"}

        from app.models.job import Job

        job = Job(
            organization_id=src.organization_id,
            kind="app.worker.tasks.process_ingestion_source",
            status=JobStatus.queued,
        )
        session.add(job)
        session.flush()
        src.job_id = job.id
        src.status = IngestionStatus.queued
        session.commit()
        job_id = str(job.id)
        stype = src.source_type

    if stype == IngestionSourceType.file:
        ingest_asset.delay(job_id, source_id)
        return {"source_id": source_id, "dispatched": "file"}
    if stype == IngestionSourceType.url:
        ingest_url.delay(job_id, source_id)
        return {"source_id": source_id, "dispatched": "url"}
    return {"source_id": source_id, "dispatched": False, "reason": f"unsupported:{stype}"}


# ---------- URL ingestion (Theme Q2 follow-up) ------------------------------


_URL_USER_AGENT = "DClawMarketing-Bot/1.0 (+https://dclaw.io)"
_URL_MAX_BYTES = 5 * 1024 * 1024  # 5 MiB hard cap
_URL_TIMEOUT_SECONDS = 30.0


@celery_app.task(name="app.worker.tasks.ingest_url", bind=True)
def ingest_url(self, job_id: str, source_id: str) -> dict:
    """Ingest a URL IngestionSource → DocumentChunks.

    Fetches via httpx (5 MiB cap, 30s timeout), runs the HTML/text
    extractor based on Content-Type, then reuses the existing
    chunk + embed + persist path.
    """
    jid = UUID(job_id)
    sid = UUID(source_id)

    update_job(
        jid,
        status=JobStatus.running,
        celery_task_id=self.request.id,
        progress_label="fetching url",
    )

    try:
        with SyncSession() as session:
            return _do_url_ingest(session, jid, sid)
    except Exception as exc:
        update_job(jid, status=JobStatus.failed, error_message=str(exc))
        with SyncSession() as session:
            src = session.get(IngestionSource, sid)
            if src is not None:
                src.status = IngestionStatus.failed
                src.error_message = str(exc)
                session.commit()
        raise


def _fetch_url(url: str) -> tuple[bytes, str, int]:
    """Returns (body_bytes, content_type, status_code).

    Raises on non-2xx or on payload > _URL_MAX_BYTES.
    """
    with httpx.Client(
        timeout=_URL_TIMEOUT_SECONDS,
        follow_redirects=True,
        headers={"User-Agent": _URL_USER_AGENT, "Accept": "text/html,*/*"},
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
        body = resp.content
        if len(body) > _URL_MAX_BYTES:
            raise ValueError(
                f"URL payload {len(body)} bytes exceeds {_URL_MAX_BYTES} cap."
            )
        ct = (resp.headers.get("content-type") or "text/html").lower()
        return body, ct, resp.status_code


def _do_url_ingest(session: Session, job_id: UUID, source_id: UUID) -> dict:
    source = session.get(IngestionSource, source_id)
    if source is None:
        raise ValueError(f"IngestionSource {source_id} not found.")
    if source.source_type != IngestionSourceType.url:
        raise ValueError(
            f"IngestionSource {source_id} is not a url source; got {source.source_type}."
        )

    url = source.source_reference

    # ------ fetch ------
    source.status = IngestionStatus.fetching
    session.commit()
    update_job(job_id, progress=0.1, progress_label=f"fetching {url}")

    body, content_type, status_code = _fetch_url(url)

    # ------ parse ------
    source.status = IngestionStatus.parsing
    session.commit()
    update_job(job_id, progress=0.4, progress_label=f"parsing {content_type}")
    text = extract_text(body, content_type)

    # ------ chunk ------
    source.status = IngestionStatus.chunking
    session.commit()
    update_job(job_id, progress=0.6, progress_label="chunking")
    chunks = chunk_text(text)

    # ------ embed ------
    source.status = IngestionStatus.embedding
    session.commit()
    update_job(job_id, progress=0.8, progress_label=f"embedding {len(chunks)} chunks")
    vectors, model_name = ([], "")
    if chunks:
        vectors, model_name = embed_texts_sync(chunks)

    # Replace any prior chunks for idempotency on re-fetch (freshness task).
    session.query(DocumentChunk).filter(
        DocumentChunk.source_id == source.id
    ).delete()
    session.flush()

    for i, chunk in enumerate(chunks):
        session.add(
            DocumentChunk(
                organization_id=source.organization_id,
                source_id=source.id,
                position=i,
                text=chunk,
                estimated_tokens=estimate_tokens(chunk),
                embedding=vectors[i] if i < len(vectors) else None,
                embedding_model=model_name if vectors else None,
            )
        )

    source.document_chunks_created = len(chunks)
    source.metadata_json = {
        "url": url,
        "http_status": status_code,
        "content_type": content_type,
        "original_byte_size": len(body),
        "text_byte_size": len(text),
        "chunk_count": len(chunks),
        "embedding_model": model_name,
    }
    source.status = IngestionStatus.ready
    source.updated_at = datetime.now(timezone.utc)
    session.commit()

    result = {
        "source_id": str(source.id),
        "url": url,
        "chunks": len(chunks),
        "bytes": len(body),
    }
    update_job(
        job_id,
        status=JobStatus.succeeded,
        progress=1.0,
        progress_label=f"ready ({len(chunks)} chunks)",
        result_json=result,
    )
    return result
