"""Health endpoints — /health/ + /health/dependencies (§6.12).

The basic ``/health/`` returns 200 OK so docker-compose + Kubernetes
liveness probes pass.

``/health/dependencies`` probes every external thing the app touches
and returns a flat dict — the operator's monitoring system polls
this every minute and pages when anything flips to False.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import engine


router = APIRouter()


@router.get("/")
async def health_check() -> dict:
    return {"status": "ok"}


async def _check_db() -> tuple[bool, str | None]:
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await session.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        return False, str(exc)[:200]


async def _check_redis() -> tuple[bool, str | None]:
    try:
        import redis.asyncio as redis_mod

        r = redis_mod.from_url(settings.redis_url)
        await r.ping()
        await r.close()
        return True, None
    except Exception as exc:
        return False, str(exc)[:200]


async def _check_minio() -> tuple[bool, str | None]:
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            res = await c.get(
                settings.s3_endpoint.rstrip("/") + "/minio/health/ready"
            )
        return (
            res.status_code == 200,
            None if res.status_code == 200 else f"status={res.status_code}",
        )
    except Exception as exc:
        return False, str(exc)[:200]


async def _check_anthropic() -> tuple[bool, str | None]:
    """Don't hit Anthropic on health-probes (cost). Just confirm a
    key is configured."""
    return bool(settings.anthropic_api_key), (
        None if settings.anthropic_api_key else "anthropic_api_key unset"
    )


async def _check_resend() -> tuple[bool, str | None]:
    return bool(settings.resend_api_key), (
        None if settings.resend_api_key else "resend_api_key unset"
    )


@router.get("/dependencies")
async def health_dependencies() -> dict:
    """Probe every external dependency in parallel."""
    results = await asyncio.gather(
        _check_db(),
        _check_redis(),
        _check_minio(),
        _check_anthropic(),
        _check_resend(),
        return_exceptions=False,
    )
    names = ["postgres", "redis", "minio", "anthropic", "resend"]
    out: dict[str, Any] = {"all_ok": True, "checks": {}}
    for name, (ok, detail) in zip(names, results):
        out["checks"][name] = {"ok": ok, "detail": detail}
        if not ok:
            out["all_ok"] = False
    return out


__all__ = ["router"]
