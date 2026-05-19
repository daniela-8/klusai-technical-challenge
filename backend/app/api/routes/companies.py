"""Company matches and priority scores API."""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models import CompanyMatch, PriorityScore, JobPosting
from app.models.schemas import PriorityScoreResponse, JobPostingResponse

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.get("/matches")
async def list_matches(
    db: AsyncSession = Depends(get_db),
    min_confidence: float = 0,
    limit: int = Query(default=100, le=500),
) -> list:
    """List all company matches with their associated jobs."""
    result = await db.execute(
        select(CompanyMatch)
        .options(selectinload(CompanyMatch.job))
        .where(CompanyMatch.confidence_score >= min_confidence)
        .order_by(CompanyMatch.confidence_score.desc())
        .limit(limit)
    )
    matches = result.scalars().all()
    return [
        {
            "id": m.id,
            "company_name": m.company_name,
            "confidence_score": m.confidence_score,
            "match_explanation": m.match_explanation,
            "signals_used": m.signals_used,
            "enrichment_data": m.enrichment_data,
            "alternative_matches": m.alternative_matches,
            "additional_data_needed": (
                (m.enrichment_data or {}).get("additional_data_needed")
                if m.enrichment_data
                else None
            ),
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "job": (
                {
                    "id": m.job.id,
                    "job_title": m.job.job_title,
                    "competitor_name": m.job.competitor_name,
                    "location": m.job.location,
                    "sector": m.job.sector,
                    "salary_range": m.job.salary_range,
                    "posting_date": m.job.posting_date,
                    "data_source": (
                        m.job.data_source.value if m.job.data_source else None
                    ),
                    "job_url": m.job.job_url,
                }
                if m.job
                else None
            ),
        }
        for m in matches
    ]


@router.get("/priorities")
async def list_priorities(
    db: AsyncSession = Depends(get_db),
    min_score: float = 0,
    limit: int = Query(default=50, le=200),
) -> list:
    """List companies ranked by priority score.
    Only includes companies whose best match confidence is >= 75%.
    Low-confidence companies are excluded from the priority board.
    """
    result = await db.execute(
        select(PriorityScore)
        .where(PriorityScore.priority_score >= min_score)
        .order_by(PriorityScore.priority_score.desc())
        .limit(limit)
    )
    scores = result.scalars().all()
    priorities = []
    for s in scores:
        conf_result = await db.execute(
            select(func.max(CompanyMatch.confidence_score)).where(
                CompanyMatch.company_name == s.company_name
            )
        )
        max_confidence = conf_result.scalar() or 0
        if max_confidence < 50:
            continue
        jobs_result = await db.execute(
            select(JobPosting)
            .join(CompanyMatch, CompanyMatch.job_id == JobPosting.id)
            .where(CompanyMatch.company_name == s.company_name)
        )
        jobs = jobs_result.scalars().all()
        priorities.append(
            {
                "id": s.id,
                "company_name": s.company_name,
                "priority_score": s.priority_score,
                "scoring_breakdown": s.scoring_breakdown,
                "rationale": s.rationale,
                "job_count": s.job_count,
                "confidence_score": max_confidence,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                "jobs": [
                    {
                        "id": j.id,
                        "job_title": j.job_title,
                        "competitor_name": j.competitor_name,
                        "location": j.location,
                        "sector": j.sector,
                        "salary_range": j.salary_range,
                        "data_source": j.data_source.value if j.data_source else None,
                    }
                    for j in jobs
                ],
            }
        )
    return priorities


@router.get("/priorities/{company_name}")
async def get_priority_detail(
    company_name: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get detailed priority information for a specific company."""
    result = await db.execute(
        select(PriorityScore).where(PriorityScore.company_name == company_name)
    )
    score = result.scalar_one_or_none()
    if not score:
        raise HTTPException(
            status_code=404, detail=f"No priority score for '{company_name}'"
        )
    matches_result = await db.execute(
        select(CompanyMatch)
        .options(selectinload(CompanyMatch.job))
        .where(CompanyMatch.company_name == company_name)
    )
    matches = matches_result.scalars().all()
    return {
        "id": score.id,
        "company_name": score.company_name,
        "priority_score": score.priority_score,
        "scoring_breakdown": score.scoring_breakdown,
        "rationale": score.rationale,
        "job_count": score.job_count,
        "matches": [
            {
                "confidence_score": m.confidence_score,
                "match_explanation": m.match_explanation,
                "signals_used": m.signals_used,
                "enrichment_data": m.enrichment_data,
                "job": (
                    {
                        "id": m.job.id,
                        "job_title": m.job.job_title,
                        "competitor_name": m.job.competitor_name,
                        "location": m.job.location,
                        "sector": m.job.sector,
                        "salary_range": m.job.salary_range,
                    }
                    if m.job
                    else None
                ),
            }
            for m in matches
        ],
    }
