"""Model resolver service (S4-M11).

Single entry point for "what model should I use for
(org, user, capability)?" called by every agent + service.

Resolution priority chain (top wins):

1. `UserModelPreference` for `(user_id, org_id, capability)` — user's
   explicit selection.
2. `OrgModelAssignment` for `(org_id, capability)` — org-level default.
3. First healthy `ModelEntry` with the capability in the org-scoped
   pool, then in the global (org_id NULL) pool, lexicographic by model_id
   for determinism.
4. Env-var fallback (existing `settings.anthropic_api_key`, etc.) — the
   legacy code-path still works while everything migrates.
5. Deterministic stub (dev / CI / no key configured).

The resolver does not call the model — it just returns a `ResolvedModel`
that callers feed into their own provider client. This keeps the
provider-call surface (httpx + SDK calls) where it belongs in
`asset_gen.py`, `embeddings.py`, `anthropic_client.py`, etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.model_assignment import OrgModelAssignment, UserModelPreference
from app.models.model_registry import (
    Capability,
    HealthStatus,
    ModelEntry,
    ModelProvider,
    ProviderType,
)
from app.services.secret_box import try_unseal


@dataclass
class ResolvedModel:
    """The decision: which model, on which provider, at which level."""

    model_entry_id: UUID | None
    provider_id: UUID | None
    provider_type: ProviderType | None
    model_id: str | None
    capability: str
    resolved_by: str  # "user" | "org" | "auto" | "env" | "stub"
    base_url: str | None = None
    api_key: str | None = None  # decrypted at resolve time; do not log


async def _by_id(db: AsyncSession, entry_id: UUID) -> tuple[ModelEntry, ModelProvider] | None:
    e = await db.get(ModelEntry, entry_id)
    if e is None or not e.is_active:
        return None
    p = await db.get(ModelProvider, e.provider_id)
    if p is None or not p.is_active:
        return None
    return e, p


def _to_resolved(
    e: ModelEntry, p: ModelProvider, capability: str, by: str
) -> ResolvedModel:
    return ResolvedModel(
        model_entry_id=e.id,
        provider_id=p.id,
        provider_type=p.provider_type,
        model_id=e.model_id,
        capability=capability,
        resolved_by=by,
        base_url=p.base_url,
        api_key=try_unseal(p.encrypted_api_key) if p.encrypted_api_key else None,
    )


async def _user_pref(
    db: AsyncSession, user_id: UUID, org_id: UUID, capability: str
) -> ResolvedModel | None:
    pref = (
        await db.execute(
            select(UserModelPreference).where(
                UserModelPreference.user_id == user_id,
                UserModelPreference.organization_id == org_id,
                UserModelPreference.capability == capability,
            )
        )
    ).scalar_one_or_none()
    if pref is None:
        return None
    pair = await _by_id(db, pref.model_entry_id)
    if pair is None:
        return None
    e, p = pair
    return _to_resolved(e, p, capability, "user")


async def _org_assign(
    db: AsyncSession, org_id: UUID, capability: str
) -> ResolvedModel | None:
    a = (
        await db.execute(
            select(OrgModelAssignment).where(
                OrgModelAssignment.organization_id == org_id,
                OrgModelAssignment.capability == capability,
            )
        )
    ).scalar_one_or_none()
    if a is None:
        return None
    pair = await _by_id(db, a.model_entry_id)
    if pair is None:
        return None
    e, p = pair
    return _to_resolved(e, p, capability, "org")


async def _pool(
    db: AsyncSession, org_id: UUID | None, capability: str
) -> ResolvedModel | None:
    """First healthy entry with the capability, org-scoped pool first, then global."""
    candidates_stmts = [
        select(ModelEntry, ModelProvider)
        .join(ModelProvider, ModelEntry.provider_id == ModelProvider.id)
        .where(
            ModelProvider.is_active.is_(True),
            ModelEntry.is_active.is_(True),
            ModelEntry.status == HealthStatus.healthy,
        ),
    ]
    # Two passes: org-scoped, then global.
    for scope_filter in [
        lambda s: s.where(ModelProvider.organization_id == org_id) if org_id else None,
        lambda s: s.where(ModelProvider.organization_id.is_(None)),
    ]:
        for base in candidates_stmts:
            stmt = scope_filter(base) if callable(scope_filter) else base
            if stmt is None:
                continue
            rows = (await db.execute(stmt.order_by(ModelEntry.model_id))).all()
            for entry, provider in rows:
                if capability in (entry.capabilities or []):
                    return _to_resolved(entry, provider, capability, "auto")
    return None


def _env_fallback(capability: str) -> ResolvedModel | None:
    """Fall back to legacy env-var keys for the headline capabilities."""
    if capability == Capability.text.value:
        key = settings.anthropic_api_key
        if key:
            return ResolvedModel(
                model_entry_id=None,
                provider_id=None,
                provider_type=ProviderType.anthropic,
                model_id="claude-sonnet-4-6",
                capability=capability,
                resolved_by="env",
                api_key=key,
            )
    if capability == Capability.embedding.value:
        key = getattr(settings, "openai_api_key", None)
        if key:
            return ResolvedModel(
                model_entry_id=None,
                provider_id=None,
                provider_type=ProviderType.openai,
                model_id="text-embedding-3-large",
                capability=capability,
                resolved_by="env",
                api_key=key,
            )
    return None


def _stub(capability: str) -> ResolvedModel:
    """No key configured anywhere — return the deterministic stub marker."""
    return ResolvedModel(
        model_entry_id=None,
        provider_id=None,
        provider_type=None,
        model_id=None,
        capability=capability,
        resolved_by="stub",
    )


async def resolve(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    org_id: UUID | None,
    capability: Capability | str,
) -> ResolvedModel:
    """Top-level resolver. Returns a ResolvedModel; never raises."""
    cap = capability.value if isinstance(capability, Capability) else capability

    if user_id and org_id:
        r = await _user_pref(db, user_id, org_id, cap)
        if r is not None:
            return r
    if org_id:
        r = await _org_assign(db, org_id, cap)
        if r is not None:
            return r
    r = await _pool(db, org_id, cap)
    if r is not None:
        return r
    r = _env_fallback(cap)
    if r is not None:
        return r
    return _stub(cap)
