"""Prospect briefs API."""

from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import ProspectBrief
from app.models.schemas import ProspectBriefResponse

router = APIRouter(prefix="/briefs", tags=["Briefs"])


@router.get("", response_model=list[ProspectBriefResponse])
async def list_briefs(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=200),
) -> list:
    """List all generated prospect briefs."""
    result = await db.execute(
        select(ProspectBrief).order_by(ProspectBrief.generated_at.desc()).limit(limit)
    )
    return result.scalars().all()


@router.get("/{company_name}")
async def get_brief(
    company_name: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the prospect brief for a specific company."""
    result = await db.execute(
        select(ProspectBrief).where(ProspectBrief.company_name == company_name)
    )
    brief = result.scalar_one_or_none()
    if not brief:
        return {
            "error": "No brief found. Generate one first via POST /api/pipeline/brief"
        }
    return {
        "id": brief.id,
        "company_name": brief.company_name,
        "brief_content": brief.brief_content,
        "generated_at": brief.generated_at.isoformat() if brief.generated_at else None,
    }
