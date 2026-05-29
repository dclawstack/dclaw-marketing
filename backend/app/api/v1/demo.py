"""Demo seed/reset router for the public landing page.

Gated on `settings.enable_demo_mode` (env ENABLE_DEMO_MODE). When off,
GET /demo/status returns {enabled: false} (HTTP 200) so the landing can
quietly hide the section; seed/reset return 403.

----------------------------------------------------------------------
TO REMOVE THE DEMO FEATURE, delete these three things:
  1. app/api/v1/demo.py          (this file)
  2. app/services/demo.py        (the seed/reset logic)
  3. The demo router registration in app/api/main.py
----------------------------------------------------------------------
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.services.demo import gather_status, reset_demo, seed_demo

router = APIRouter(prefix="/demo", tags=["demo"])


def _require_enabled() -> None:
    if not settings.enable_demo_mode:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Demo mode is disabled (set ENABLE_DEMO_MODE=true)",
        )


@router.get("/status")
async def demo_status(db: AsyncSession = Depends(get_db)) -> dict:
    """Probe — returns enabled:false (200) when the flag is off so the
    landing page can hide the section quietly instead of erroring."""
    return asdict(await gather_status(db, enabled=settings.enable_demo_mode))


@router.post("/seed")
async def demo_seed(db: AsyncSession = Depends(get_db)) -> dict:
    _require_enabled()
    return asdict(await seed_demo(db))


@router.delete("/reset")
async def demo_reset(db: AsyncSession = Depends(get_db)) -> dict:
    _require_enabled()
    return asdict(await reset_demo(db))
