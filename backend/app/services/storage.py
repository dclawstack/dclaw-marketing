"""Object storage abstraction — S3-compatible (MinIO / R2 / AWS S3 / DO Spaces).

Used by:
- Direct uploads: clients PUT to a presigned URL; we never see the bytes.
- Server-side reads: agents download generated content from S3.
- Public reads: presigned GET URLs for `<img src>` / `<video>` tags.

Async via aiobotocore. Sync helper provided for use inside Celery
tasks (which are sync-native).
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, BinaryIO
from uuid import uuid4

import aiobotocore.session
import boto3

from app.core.config import settings


# -----------------------------------------------------------------
# Async client (FastAPI request path)
# -----------------------------------------------------------------

@asynccontextmanager
async def _async_client() -> AsyncIterator:
    """Yield an aiobotocore S3 client configured from settings."""
    session = aiobotocore.session.get_session()
    async with session.create_client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        use_ssl=settings.s3_use_ssl,
    ) as client:
        yield client


async def ensure_bucket(bucket: str | None = None) -> None:
    """Create the bucket if it doesn't already exist. Safe to call on
    every app start — MinIO + S3 both return a specific error code that
    we ignore.
    """
    name = bucket or settings.s3_bucket
    async with _async_client() as s3:
        try:
            await s3.head_bucket(Bucket=name)
        except Exception:
            try:
                await s3.create_bucket(Bucket=name)
            except Exception:
                pass  # raced with another worker — harmless


def make_storage_key(
    organization_id: str | None,
    kind: str,
    extension: str,
) -> str:
    """Deterministic storage-key shape:

        orgs/<org_id_or_global>/<kind>/<uuid>.<ext>

    Org-scoped → org isolation in object names too (defense in depth).
    """
    ext = extension.lstrip(".").lower() if extension else "bin"
    org_part = str(organization_id) if organization_id else "_global"
    return f"orgs/{org_part}/{kind}/{uuid4().hex}.{ext}"


async def presigned_put_url(
    storage_key: str,
    content_type: str = "application/octet-stream",
    *,
    bucket: str | None = None,
    expires_in: int = 600,
) -> str:
    """Returns a presigned URL the client uploads to via HTTP PUT.

    The client is responsible for sending the bytes; the server never
    sees them. After upload the client calls our /assets/{id}/confirm
    endpoint to flip Asset.status from `uploading` → `ready`.
    """
    name = bucket or settings.s3_bucket
    async with _async_client() as s3:
        return await s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": name, "Key": storage_key, "ContentType": content_type},
            ExpiresIn=expires_in,
        )


async def presigned_get_url(
    storage_key: str,
    *,
    bucket: str | None = None,
    expires_in: int = 3600,
) -> str:
    """Returns a presigned URL the client downloads from via HTTP GET."""
    name = bucket or settings.s3_bucket
    async with _async_client() as s3:
        return await s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": name, "Key": storage_key},
            ExpiresIn=expires_in,
        )


async def put_object(
    storage_key: str,
    body: bytes | BinaryIO,
    *,
    content_type: str = "application/octet-stream",
    bucket: str | None = None,
) -> None:
    """Server-side upload — used when agents generate content themselves
    rather than receiving an external upload.
    """
    name = bucket or settings.s3_bucket
    async with _async_client() as s3:
        await s3.put_object(
            Bucket=name, Key=storage_key, Body=body, ContentType=content_type
        )


async def get_object_bytes(
    storage_key: str, *, bucket: str | None = None
) -> bytes:
    """Server-side download — used when agents need to read content
    they previously stored.
    """
    name = bucket or settings.s3_bucket
    async with _async_client() as s3:
        response = await s3.get_object(Bucket=name, Key=storage_key)
        async with response["Body"] as stream:
            return await stream.read()


async def head_object(
    storage_key: str, *, bucket: str | None = None
) -> dict | None:
    """Returns object metadata (size, etag, content-type) or None if
    the object doesn't exist. Used to confirm an upload completed.
    """
    name = bucket or settings.s3_bucket
    async with _async_client() as s3:
        try:
            response = await s3.head_object(Bucket=name, Key=storage_key)
            return {
                "size": response.get("ContentLength"),
                "etag": response.get("ETag", "").strip('"'),
                "content_type": response.get("ContentType"),
            }
        except Exception:
            return None


async def delete_object(
    storage_key: str, *, bucket: str | None = None
) -> None:
    """Idempotent delete — succeeds whether or not the object exists."""
    name = bucket or settings.s3_bucket
    async with _async_client() as s3:
        await s3.delete_object(Bucket=name, Key=storage_key)


# -----------------------------------------------------------------
# Sync helpers for Celery tasks
# -----------------------------------------------------------------


def sync_s3_client():
    """Sync boto3 client for use inside Celery tasks."""
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        use_ssl=settings.s3_use_ssl,
    )


__all__ = [
    "ensure_bucket",
    "make_storage_key",
    "presigned_put_url",
    "presigned_get_url",
    "put_object",
    "get_object_bytes",
    "head_object",
    "delete_object",
    "sync_s3_client",
]
