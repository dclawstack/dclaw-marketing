from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.lead import Lead, LeadStatus
from app.schemas.lead import LeadCreate, LeadUpdate, LeadRead
from app.repositories.lead_repo import LeadRepository

router = APIRouter()


@router.post("/", response_model=LeadRead, status_code=201)
async def create_lead(data: LeadCreate, db: AsyncSession = Depends(get_db)):
    repo = LeadRepository(db)
    existing = await repo.get_by_email(data.email)
    if existing:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Lead with this email already exists")
    lead = Lead(**data.model_dump())
    return await repo.create(lead)


@router.get("/", response_model=dict)
async def list_leads(
    search: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    status: Optional[LeadStatus] = Query(None),
    campaign_id: Optional[UUID] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = LeadRepository(db)
    items, total = await repo.list_filtered(
        search=search, source=source, status=status, campaign_id=campaign_id, limit=limit, offset=offset
    )
    return {"items": [LeadRead.model_validate(item) for item in items], "total": total}


@router.get("/{lead_id}", response_model=LeadRead)
async def get_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = LeadRepository(db)
    lead = await repo.get_by_id(lead_id)
    if not lead:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/{lead_id}", response_model=LeadRead)
async def update_lead(lead_id: UUID, data: LeadUpdate, db: AsyncSession = Depends(get_db)):
    repo = LeadRepository(db)
    lead = await repo.get_by_id(lead_id)
    if not lead:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Lead not found")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lead, key, value)
    await repo.db.commit()
    await repo.db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = LeadRepository(db)
    lead = await repo.get_by_id(lead_id)
    if not lead:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Lead not found")
    await repo.delete(lead)
    return None


# ---------- E2 Lead enrichment fan-out (SP3-12) ---------------------------


@router.post("/{lead_id}/enrich")
async def post_enrich_lead(lead_id: UUID, db: AsyncSession = Depends(get_db)):
    """Run the Apollo / Clearbit / PDL chain against this Lead's email
    and merge the result into ``Lead.enrichment_json``.

    Provider-or-stub: returns deterministic stubs when no API key is set.
    """
    from app.services.enrichment import enrich_lead_email

    repo = LeadRepository(db)
    lead = await repo.get_by_id(lead_id)
    if not lead:
        from fastapi import HTTPException as _HE
        raise _HE(status_code=404, detail="Lead not found")
    if not lead.email:
        from fastapi import HTTPException as _HE
        raise _HE(status_code=400, detail="Lead has no email to enrich.")

    result = await enrich_lead_email(lead.email)
    existing = lead.enrichment_json or {}
    # Merge first-wins so human edits stay sticky.
    for k, v in result["merged"].items():
        if k not in existing or existing[k] in (None, "", [], {}):
            existing[k] = v
    existing.setdefault("audit", []).extend(result["audit"])
    lead.enrichment_json = existing
    await db.commit()
    await db.refresh(lead)
    return {"lead_id": str(lead.id), "enrichment_json": lead.enrichment_json}
