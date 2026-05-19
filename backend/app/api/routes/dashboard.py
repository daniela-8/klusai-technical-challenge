"""Dashboard API — aggregated stats and KPIs."""

from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import (
    JobPosting,
    CompanyMatch,
    PriorityScore,
    CompetitorSource,
    Alert,
)
from app.models.schemas import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardStats)
async def get_dashboard(db: AsyncSession = Depends(get_db)) -> DashboardStats:
    """Return aggregated dashboard statistics."""
    total_jobs_result = await db.execute(select(func.count(JobPosting.id)))
    total_jobs = total_jobs_result.scalar() or 0
    matched_result = await db.execute(
        select(func.count(func.distinct(CompanyMatch.company_name)))
    )
    total_matched = matched_result.scalar() or 0
    high_prio_result = await db.execute(
        select(func.count(PriorityScore.id)).where(PriorityScore.priority_score > 70)
    )
    high_priority = high_prio_result.scalar() or 0
    active_result = await db.execute(
        select(func.count(CompetitorSource.id)).where(
            CompetitorSource.is_active == True
        )
    )
    active_competitors = active_result.scalar() or 0
    avg_conf_result = await db.execute(select(func.avg(CompanyMatch.confidence_score)))
    avg_confidence = round(avg_conf_result.scalar() or 0, 1)
    alerts_result = await db.execute(
        select(func.count(Alert.id)).where(Alert.is_read == False)
    )
    recent_alerts = alerts_result.scalar() or 0
    source_result = await db.execute(
        select(JobPosting.data_source, func.count(JobPosting.id)).group_by(
            JobPosting.data_source
        )
    )
    jobs_by_source = {
        str(row[0].value if hasattr(row[0], "value") else row[0]): row[1]
        for row in source_result.all()
    }
    comp_result = await db.execute(
        select(JobPosting.competitor_name, func.count(JobPosting.id)).group_by(
            JobPosting.competitor_name
        )
    )
    jobs_by_competitor = {row[0]: row[1] for row in comp_result.all()}
    conf_dist: dict[str, int] = {"0-25": 0, "25-50": 0, "50-75": 0, "75-100": 0}
    conf_result = await db.execute(select(CompanyMatch.confidence_score))
    for (score,) in conf_result.all():
        if score < 25:
            conf_dist["0-25"] += 1
        elif score < 50:
            conf_dist["25-50"] += 1
        elif score < 75:
            conf_dist["50-75"] += 1
        else:
            conf_dist["75-100"] += 1
    sector_result = await db.execute(
        select(JobPosting.sector, func.count(JobPosting.id))
        .where(JobPosting.sector.isnot(None))
        .group_by(JobPosting.sector)
        .order_by(func.count(JobPosting.id).desc())
        .limit(8)
    )
    top_sectors = [{"name": row[0], "count": row[1]} for row in sector_result.all()]
    return DashboardStats(
        total_jobs=total_jobs,
        total_companies_matched=total_matched,
        high_priority_targets=high_priority,
        active_competitors=active_competitors,
        avg_confidence=avg_confidence,
        recent_alerts=recent_alerts,
        jobs_by_source=jobs_by_source,
        jobs_by_competitor=jobs_by_competitor,
        confidence_distribution=conf_dist,
        top_sectors=top_sectors,
    )
