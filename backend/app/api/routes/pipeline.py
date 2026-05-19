"""Pipeline API — trigger scraping and AI processing."""

from typing import Optional
import httpx
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core import settings
from app.core.database import get_db, async_session
from app.ai.pipeline import AIPipeline
from app.scrapers.manager import ScrapingManager
from app.scrapers.html_parsers import (
    detect_competitor_from_url,
    get_parser_for_competitor,
)
from app.models import (
    CompetitorSource,
    JobPosting,
    DataSource,
    Alert,
    AlertType,
    CompanyMatch,
    PriorityScore,
    ProspectBrief,
)
from app.models.schemas import (
    ScrapeRequest,
    ScrapeStatusResponse,
    ScrapeUrlRequest,
    ScrapeUrlResponse,
    ProcessRequest,
    ProcessStatusResponse,
    GenerateBriefRequest,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/pipeline", tags=["Pipeline"])
_pipeline_state: dict = {
    "is_running": False,
    "started_at": None,
    "last_result": None,
}


@router.post("/reset")
async def reset_all_data(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Clear all scraped data for a clean start.
    Deletes ALL job postings, company matches, priority scores, briefs,
    and alerts. Competitors are preserved (re-seeded on startup anyway).
    Use this instead of deleting klusai.db manually.
    """
    try:
        await db.execute(delete(PriorityScore))
        await db.execute(delete(CompanyMatch))
        await db.execute(delete(ProspectBrief))
        await db.execute(delete(Alert))
        await db.execute(delete(JobPosting))
        await db.execute(update(CompetitorSource).values(last_scraped_at=None))
        await db.commit()
        logger.info("data_reset_complete")
        return {
            "status": "ok",
            "message": "All job postings, matches, scores, briefs and alerts deleted. Competitors preserved.",
        }
    except Exception as e:
        await db.rollback()
        logger.error("data_reset_failed", error=str(e))
        return {"status": "error", "message": str(e)}


@router.post("/scrape", response_model=ScrapeStatusResponse)
async def trigger_scrape(
    request: Optional[ScrapeRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> ScrapeStatusResponse:
    """Trigger scraping for all or specific competitors."""
    try:
        manager = ScrapingManager(db)
        competitor_ids = request.competitor_ids if request else None
        results = await manager.scrape_all(competitor_ids=competitor_ids)
        total_jobs = sum(len(r.jobs) for r in results)
        errors = [r.error for r in results if r.error]
        return ScrapeStatusResponse(
            status="completed",
            competitors_scraped=len(results),
            jobs_collected=total_jobs,
            errors=errors,
        )
    except Exception as e:
        return ScrapeStatusResponse(
            status="error",
            competitors_scraped=0,
            jobs_collected=0,
            errors=[str(e)],
        )


@router.post("/scrape-url", response_model=ScrapeUrlResponse)
async def scrape_single_url(
    request: ScrapeUrlRequest,
    db: AsyncSession = Depends(get_db),
) -> ScrapeUrlResponse:
    """Scrape a single job URL — auto-detects competitor and extracts all fields.
    This is the demo-critical endpoint: paste a URL → get structured data instantly.
    Supported competitors: CPA Partners, Michael Page, Robert Half, Robert Walters.
    """
    url = request.url.strip()
    competitor_name = detect_competitor_from_url(url)
    if not competitor_name:
        return ScrapeUrlResponse(
            status="error",
            error=(
                f"Unrecognized domain. Supported competitors: "
                f"CPA Partners (cpa-partner.com), Michael Page (michaelpage.fr), "
                f"Robert Half (roberthalf.com), Robert Walters (robertwalters.fr)"
            ),
        )
    parser_cls = get_parser_for_competitor(competitor_name)
    if not parser_cls:
        return ScrapeUrlResponse(
            status="error",
            competitor_detected=competitor_name,
            error=f"No parser available for {competitor_name}",
        )
    try:
        async with httpx.AsyncClient(
            timeout=settings.scrape_timeout,
            headers={"User-Agent": settings.scrape_user_agent},
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text
    except httpx.HTTPStatusError as exc:
        return ScrapeUrlResponse(
            status="error",
            competitor_detected=competitor_name,
            error=f"HTTP {exc.response.status_code} fetching {url}",
        )
    except httpx.TimeoutException:
        return ScrapeUrlResponse(
            status="error",
            competitor_detected=competitor_name,
            error=f"Timeout after {settings.scrape_timeout}s fetching {url}",
        )
    except Exception as exc:
        return ScrapeUrlResponse(
            status="error",
            competitor_detected=competitor_name,
            error=f"Failed to fetch URL: {exc}",
        )
    try:
        scraped_job = parser_cls.parse(html, url)
    except Exception as exc:
        logger.error(
            "scrape_url_parse_error", competitor=competitor_name, error=str(exc)
        )
        return ScrapeUrlResponse(
            status="error",
            competitor_detected=competitor_name,
            error=f"Parse error: {exc}",
        )
    job_id = None
    try:
        result = await db.execute(
            select(CompetitorSource).where(CompetitorSource.name == competitor_name)
        )
        competitor = result.scalar_one_or_none()
        if not competitor:
            competitor = CompetitorSource(
                name=competitor_name,
                website_url=url,
                careers_url=url,
                category="large",
            )
            db.add(competitor)
            await db.flush()
        existing_result = await db.execute(
            select(JobPosting).where(JobPosting.job_url == scraped_job.job_url)
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            job_id = existing.id
            logger.info("scrape_url_duplicate", job_id=job_id, url=url)
        else:
            job = JobPosting(
                competitor_id=competitor.id,
                competitor_name=scraped_job.competitor_name,
                job_title=scraped_job.job_title,
                job_description=scraped_job.job_description,
                location=scraped_job.location,
                sector=scraped_job.sector,
                salary_range=scraped_job.salary_range,
                job_url=scraped_job.job_url,
                posting_date=scraped_job.posting_date,
                data_source=DataSource.SCRAPED,
            )
            db.add(job)
            alert = Alert(
                alert_type=AlertType.NEW_JOB,
                title=f"New job scraped: {scraped_job.job_title}",
                message=(
                    f"{scraped_job.competitor_name} — '{scraped_job.job_title}' "
                    f"in {scraped_job.location or 'unknown location'}"
                ),
                severity="info",
                related_entity_type="job_posting",
            )
            db.add(alert)
            await db.flush()
            job_id = job.id
    except Exception as exc:
        logger.error("scrape_url_persist_error", error=str(exc))
    return ScrapeUrlResponse(
        status="success",
        competitor_detected=competitor_name,
        job_id=job_id,
        job={
            "job_title": scraped_job.job_title,
            "job_description": scraped_job.job_description[:500]
            + ("..." if len(scraped_job.job_description) > 500 else ""),
            "location": scraped_job.location,
            "sector": scraped_job.sector,
            "salary_range": scraped_job.salary_range,
            "job_url": scraped_job.job_url,
            "posting_date": scraped_job.posting_date,
            "competitor_name": scraped_job.competitor_name,
            "data_source": scraped_job.data_source,
        },
    )


async def _run_pipeline_in_background(
    job_ids: Optional[list],
    max_jobs: int,
) -> None:
    """Run the AI pipeline in the background using its own DB session."""
    from datetime import datetime, timezone as tz

    _pipeline_state["is_running"] = True
    _pipeline_state["started_at"] = datetime.now(tz.utc).isoformat()
    _pipeline_state["last_result"] = None
    pipeline = AIPipeline()
    async with async_session() as db:
        try:
            stats = await pipeline.process_jobs(db, job_ids=job_ids, max_jobs=max_jobs)
            _pipeline_state["last_result"] = stats
            logger.info(
                "background_pipeline_completed",
                jobs_processed=stats["jobs_processed"],
                matches_created=stats["matches_created"],
                scores_updated=stats["scores_updated"],
                errors=stats.get("errors", []),
                remaining=stats.get("jobs_remaining", 0),
            )
        except Exception as e:
            import traceback

            _pipeline_state["last_result"] = {
                "jobs_processed": 0,
                "matches_created": 0,
                "scores_updated": 0,
                "errors": [str(e)],
            }
            logger.error(
                "background_pipeline_failed",
                error=str(e),
                traceback=traceback.format_exc(),
            )
        finally:
            _pipeline_state["is_running"] = False


@router.get("/status")
async def get_pipeline_status() -> dict:
    """Poll this endpoint to know when background processing finishes."""
    return {
        "is_running": _pipeline_state["is_running"],
        "started_at": _pipeline_state["started_at"],
        "last_result": _pipeline_state["last_result"],
    }


@router.get("/match-count")
async def get_match_count(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return current count of matched jobs (for detecting new matches via polling)."""
    from sqlalchemy import func

    result = await db.execute(select(func.count(CompanyMatch.id)))
    count = result.scalar() or 0
    return {"match_count": count}


@router.post("/process", response_model=ProcessStatusResponse)
async def trigger_processing(
    request: Optional[ProcessRequest] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> ProcessStatusResponse:
    """Process jobs through the AI pipeline (matching + scoring).
    Returns immediately and runs the pipeline in the background.
    """
    job_ids = request.job_ids if request else None
    max_jobs = (request.max_jobs if request and request.max_jobs else None) or 5
    background_tasks.add_task(_run_pipeline_in_background, job_ids, max_jobs)
    return ProcessStatusResponse(
        status="accepted",
        jobs_processed=0,
        matches_created=0,
        scores_updated=0,
        errors=[],
        jobs_remaining=0,
        message="Pipeline processing in background. Refresh the dashboard to see results.",
    )


@router.post("/brief")
async def generate_brief(
    request: GenerateBriefRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a prospect brief for a specific company."""
    pipeline = AIPipeline()
    brief = await pipeline.generate_brief(db, company_name=request.company_name)
    return brief


@router.post("/full-pipeline")
async def run_full_pipeline(
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run the complete pipeline: scrape → process → score."""
    try:
        manager = ScrapingManager(db)
        scrape_results = await manager.scrape_all()
        total_scraped = sum(len(r.jobs) for r in scrape_results)
        background_tasks.add_task(_run_pipeline_in_background, None, 5)
        return {
            "status": "accepted",
            "scraping": {
                "competitors_scraped": len(scrape_results),
                "jobs_collected": total_scraped,
                "errors": [r.error for r in scrape_results if r.error],
            },
            "processing": {
                "status": "running_in_background",
                "message": "Refresh dashboard for results.",
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "scraping": {
                "competitors_scraped": 0,
                "jobs_collected": 0,
                "errors": [str(e)],
            },
            "processing": {
                "jobs_processed": 0,
                "matches_created": 0,
                "scores_updated": 0,
                "errors": [str(e)],
            },
        }
