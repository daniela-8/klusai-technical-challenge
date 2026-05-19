"""Job postings API — list, search, upload, and manage job postings."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models import JobPosting, CompetitorSource, DataSource
from app.models.schemas import JobPostingCreate, JobPostingResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=List[JobPostingResponse])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    competitor: Optional[str] = None,
    sector: Optional[str] = None,
    location: Optional[str] = None,
    search: Optional[str] = None,
    processed_only: bool = False,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
) -> list:
    """List job postings with optional filtering."""
    query = (
        select(JobPosting)
        .options(selectinload(JobPosting.company_match))
        .order_by(JobPosting.detected_at.desc())
    )
    if competitor:
        query = query.where(JobPosting.competitor_name == competitor)
    if sector:
        query = query.where(JobPosting.sector.ilike(f"%{sector}%"))
    if location:
        query = query.where(JobPosting.location.ilike(f"%{location}%"))
    if search:
        query = query.where(
            or_(
                JobPosting.job_title.ilike(f"%{search}%"),
                JobPosting.job_description.ilike(f"%{search}%"),
            )
        )
    if processed_only:
        query = query.where(JobPosting.is_processed == True)
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/count")
async def get_job_count(db: AsyncSession = Depends(get_db)) -> dict:
    """Get total job count."""
    result = await db.execute(select(func.count(JobPosting.id)))
    return {"count": result.scalar() or 0}


@router.get("/{job_id}", response_model=JobPostingResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobPostingResponse:
    """Get a single job posting by ID."""
    result = await db.execute(
        select(JobPosting)
        .options(selectinload(JobPosting.company_match))
        .where(JobPosting.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("", response_model=JobPostingResponse, status_code=201)
async def upload_job(
    data: JobPostingCreate,
    db: AsyncSession = Depends(get_db),
) -> JobPostingResponse:
    """Upload or paste a job description for analysis."""
    result = await db.execute(
        select(CompetitorSource).where(CompetitorSource.name == data.competitor_name)
    )
    competitor = result.scalar_one_or_none()
    if not competitor:
        competitor = CompetitorSource(
            name=data.competitor_name,
            website_url="https://manual-upload.local",
            careers_url="https://manual-upload.local",
            category="large",
        )
        db.add(competitor)
        await db.flush()
    job = JobPosting(
        competitor_id=competitor.id,
        competitor_name=data.competitor_name,
        job_title=data.job_title,
        job_description=data.job_description,
        location=data.location,
        sector=data.sector,
        salary_range=data.salary_range,
        job_url=data.job_url,
        posting_date=data.posting_date,
        data_source=DataSource.UPLOADED,
    )
    db.add(job)
    await db.flush()
    result2 = await db.execute(
        select(JobPosting)
        .options(selectinload(JobPosting.company_match))
        .where(JobPosting.id == job.id)
    )
    return result2.scalar_one()


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a job posting."""
    result = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await db.delete(job)
    return Response(status_code=204)
