"""Ingestion API — kick off + monitor Theme Q2 ingestion jobs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.ingestion import (
    DocumentChunk,
    IngestionSource,
    IngestionSourceType,
    IngestionStatus,
)
from app.models.job import Job, JobStatus
from app.models.organization import OrganizationMembership, OrganizationRole
from app.models.user import User


router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestFileRequest(BaseModel):
    organization_id: UUID
    asset_id: UUID
    name: str | None = Field(default=None, max_length=255)


class IngestGitRequest(BaseModel):
    organization_id: UUID
    repo_url: str = Field(min_length=8, max_length=2048)
    name: str | None = Field(default=None, max_length=255)


class IngestUrlRequest(BaseModel):
    organization_id: UUID
    url: str = Field(min_length=8, max_length=2048)
    name: str | None = Field(default=None, max_length=255)


class IngestResponse(BaseModel):
    source_id: UUID
    job_id: UUID
    status: IngestionStatus

    class Config:
        from_attributes = True


class IngestStatusResponse(BaseModel):
    id: UUID
    organization_id: UUID
    source_type: IngestionSourceType
    source_reference: str
    name: str | None
    status: IngestionStatus
    document_chunks_created: int
    error_message: str | None
    metadata_json: dict | None
    job_id: UUID | None

    class Config:
        from_attributes = True


async def _require_member(
    session: AsyncSession,
    user: User,
    organization_id: UUID,
    roles: tuple[OrganizationRole, ...],
) -> None:
    if user.is_superuser:
        return
    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == organization_id,
        )
    )
    m = result.scalar_one_or_none()
    if m is None or m.role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role admin / manager / creatives / seo_specialist required.",
        )


_INGEST_ROLES = (
    OrganizationRole.admin,
    OrganizationRole.manager,
    OrganizationRole.creatives,
    OrganizationRole.seo_specialist,
)


@router.post("/files", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_file(
    body: IngestFileRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """Trigger ingestion of an already-uploaded Asset.

    Creates an IngestionSource + a Job row, then dispatches the
    Celery task. Lazy-imports Celery so the API request path doesn't
    pay the import cost.
    """
    await _require_member(session, user, body.organization_id, _INGEST_ROLES)

    # Create Job tracker
    job = Job(
        organization_id=body.organization_id,
        initiated_by_user_id=user.id,
        kind="app.worker.tasks.ingest_asset",
        status=JobStatus.queued,
    )
    session.add(job)
    await session.flush()

    # Create the IngestionSource
    src = IngestionSource(
        organization_id=body.organization_id,
        initiated_by_user_id=user.id,
        source_type=IngestionSourceType.file,
        source_reference=str(body.asset_id),
        name=body.name,
        status=IngestionStatus.queued,
        job_id=job.id,
    )
    session.add(src)
    await session.flush()
    await session.commit()
    await session.refresh(src)
    await session.refresh(job)

    # Dispatch the task. We import here to avoid pulling Celery into
    # the request hot path unless needed.
    from app.worker.tasks.ingestion import ingest_asset as _task
    try:
        _task.delay(str(job.id), str(src.id))
    except Exception as exc:
        # Broker down or worker missing — mark both rows failed
        src.status = IngestionStatus.failed
        src.error_message = f"Failed to dispatch: {exc}"
        job.status = JobStatus.failed
        job.error_message = str(exc)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to dispatch ingestion task: {exc}",
        )

    return IngestResponse(source_id=src.id, job_id=job.id, status=src.status)


@router.post("/urls", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_url(
    body: IngestUrlRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """Trigger URL ingestion. Creates an IngestionSource + Job row + dispatches
    the Celery task. The worker fetches, extracts HTML/text, chunks, embeds.
    """
    await _require_member(session, user, body.organization_id, _INGEST_ROLES)

    url = body.url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with http:// or https://",
        )

    job = Job(
        organization_id=body.organization_id,
        initiated_by_user_id=user.id,
        kind="app.worker.tasks.ingest_url",
        status=JobStatus.queued,
    )
    session.add(job)
    await session.flush()

    src = IngestionSource(
        organization_id=body.organization_id,
        initiated_by_user_id=user.id,
        source_type=IngestionSourceType.url,
        source_reference=url,
        name=body.name,
        status=IngestionStatus.queued,
        job_id=job.id,
    )
    session.add(src)
    await session.flush()
    await session.commit()
    await session.refresh(src)
    await session.refresh(job)

    from app.worker.tasks.ingestion import ingest_url as _task
    try:
        _task.delay(str(job.id), str(src.id))
    except Exception as exc:
        src.status = IngestionStatus.failed
        src.error_message = f"Failed to dispatch: {exc}"
        job.status = JobStatus.failed
        job.error_message = str(exc)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to dispatch URL ingestion task: {exc}",
        )

    return IngestResponse(source_id=src.id, job_id=job.id, status=src.status)


@router.post("/git", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_git(
    body: IngestGitRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """Trigger git-repo ingestion (SP3-8).

    Shallow-clones the repo, collects README + docs, then chunks/embeds
    the concatenated text through the standard pipeline. Public repos
    work out of the box; private repos need credentials baked into the
    URL (handed off to git clone as-is) and a follow-up will key them
    off Connection rows instead.
    """
    await _require_member(session, user, body.organization_id, _INGEST_ROLES)

    repo_url = body.repo_url.strip()
    if not (
        repo_url.startswith("http://")
        or repo_url.startswith("https://")
        or repo_url.startswith("git@")
        or repo_url.startswith("ssh://")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repo URL must be http(s), git@, or ssh://",
        )

    job = Job(
        organization_id=body.organization_id,
        initiated_by_user_id=user.id,
        kind="app.worker.tasks.ingest_git",
        status=JobStatus.queued,
    )
    session.add(job)
    await session.flush()

    src = IngestionSource(
        organization_id=body.organization_id,
        initiated_by_user_id=user.id,
        source_type=IngestionSourceType.git,
        source_reference=repo_url,
        name=body.name,
        status=IngestionStatus.queued,
        job_id=job.id,
    )
    session.add(src)
    await session.flush()
    await session.commit()
    await session.refresh(src)
    await session.refresh(job)

    from app.worker.tasks.ingestion import ingest_git as _task
    try:
        _task.delay(str(job.id), str(src.id))
    except Exception as exc:
        src.status = IngestionStatus.failed
        src.error_message = f"Failed to dispatch: {exc}"
        job.status = JobStatus.failed
        job.error_message = str(exc)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to dispatch git ingestion task: {exc}",
        )

    return IngestResponse(source_id=src.id, job_id=job.id, status=src.status)


@router.get("/{source_id}", response_model=IngestStatusResponse)
async def get_ingestion_status(
    source_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> IngestionSource:
    src = await session.get(IngestionSource, source_id)
    if src is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    # Access: superuser, the initiator, or an Org member.
    if not user.is_superuser and src.initiated_by_user_id != user.id:
        result = await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == src.organization_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access.")

    return src


@router.get("", response_model=list[IngestStatusResponse])
async def list_ingestions(
    organization_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
    limit: int = 50,
) -> list[IngestionSource]:
    await _require_member(session, user, organization_id, tuple(OrganizationRole))
    result = await session.execute(
        select(IngestionSource)
        .where(IngestionSource.organization_id == organization_id)
        .order_by(IngestionSource.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


class ChunkRead(BaseModel):
    id: UUID
    source_id: UUID
    position: int
    text: str
    estimated_tokens: int | None
    metadata_json: dict | None

    class Config:
        from_attributes = True


@router.get("/{source_id}/chunks", response_model=list[ChunkRead])
async def list_chunks(
    source_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
    limit: int = 200,
) -> list[DocumentChunk]:
    src = await session.get(IngestionSource, source_id)
    if src is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    if not user.is_superuser:
        result = await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == src.organization_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access.")

    result = await session.execute(
        select(DocumentChunk)
        .where(DocumentChunk.source_id == source_id)
        .order_by(DocumentChunk.position)
        .limit(limit)
    )
    return list(result.scalars().all())
