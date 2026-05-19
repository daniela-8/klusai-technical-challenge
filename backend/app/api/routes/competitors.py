"""Competitor sources API — CRUD for competitor management."""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import CompetitorSource, CompetitorCategory, JobPosting
from app.models.schemas import CompetitorCreate, CompetitorResponse

router = APIRouter(prefix="/competitors", tags=["Competitors"])


@router.get("", response_model=list[CompetitorResponse])
async def list_competitors(db: AsyncSession = Depends(get_db)) -> list:
    """List all competitor sources with job counts."""
    result = await db.execute(select(CompetitorSource).order_by(CompetitorSource.name))
    competitors = result.scalars().all()
    response = []
    for comp in competitors:
        count_result = await db.execute(
            select(func.count(JobPosting.id)).where(JobPosting.competitor_id == comp.id)
        )
        job_count = count_result.scalar() or 0
        resp = CompetitorResponse(
            id=comp.id,
            name=comp.name,
            website_url=comp.website_url,
            careers_url=comp.careers_url,
            category=comp.category,
            is_active=comp.is_active,
            last_scraped_at=comp.last_scraped_at,
            created_at=comp.created_at,
            job_count=job_count,
        )
        response.append(resp)
    return response


@router.post("", response_model=CompetitorResponse, status_code=201)
async def create_competitor(
    data: CompetitorCreate,
    db: AsyncSession = Depends(get_db),
) -> CompetitorResponse:
    """Add a new competitor source."""
    existing = await db.execute(
        select(CompetitorSource).where(CompetitorSource.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail=f"Competitor '{data.name}' already exists"
        )
    competitor = CompetitorSource(
        name=data.name,
        website_url=data.website_url,
        careers_url=data.careers_url,
        category=CompetitorCategory(data.category.value),
    )
    db.add(competitor)
    await db.flush()
    return CompetitorResponse(
        id=competitor.id,
        name=competitor.name,
        website_url=competitor.website_url,
        careers_url=competitor.careers_url,
        category=competitor.category,
        is_active=competitor.is_active,
        last_scraped_at=competitor.last_scraped_at,
        created_at=competitor.created_at,
        job_count=0,
    )


@router.delete("/{competitor_id}")
async def delete_competitor(
    competitor_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a competitor source."""
    result = await db.execute(
        select(CompetitorSource).where(CompetitorSource.id == competitor_id)
    )
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    await db.delete(competitor)
    return Response(status_code=204)


@router.patch("/{competitor_id}/toggle", response_model=CompetitorResponse)
async def toggle_competitor(
    competitor_id: str,
    db: AsyncSession = Depends(get_db),
) -> CompetitorResponse:
    """Toggle a competitor's active status."""
    result = await db.execute(
        select(CompetitorSource).where(CompetitorSource.id == competitor_id)
    )
    competitor = result.scalar_one_or_none()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    competitor.is_active = not competitor.is_active
    await db.flush()
    count_result = await db.execute(
        select(func.count(JobPosting.id)).where(
            JobPosting.competitor_id == competitor.id
        )
    )
    job_count = count_result.scalar() or 0
    return CompetitorResponse(
        id=competitor.id,
        name=competitor.name,
        website_url=competitor.website_url,
        careers_url=competitor.careers_url,
        category=competitor.category,
        is_active=competitor.is_active,
        last_scraped_at=competitor.last_scraped_at,
        created_at=competitor.created_at,
        job_count=job_count,
    )
