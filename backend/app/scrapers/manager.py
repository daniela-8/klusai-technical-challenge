"""Scraping manager — orchestrates scraping across all 4 target competitors.
Strategy: listing page → extract job URLs → fetch detail pages → parse with BS4.
If live scraping fails for a competitor, falls back to mock data (data_source="mocked").
Competitors: CPA Partners, Michael Page, Robert Half, Robert Walters.
Robert Walters always uses mock fallback (their WAF returns HTTP 403).
"""

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import settings
from app.core.logging import get_logger
from app.models import CompetitorSource, JobPosting, DataSource, Alert, AlertType
from app.scrapers.base import ScrapeResult
from app.scrapers.competitors import SCRAPER_REGISTRY
from app.scrapers.mock_data import get_mock_jobs

logger = get_logger(__name__)


class ScrapingManager:
    """Orchestrates scraping across all competitor sources."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._db_lock = asyncio.Lock()

    async def scrape_all(
        self, competitor_ids: list[str] | None = None
    ) -> list[ScrapeResult]:
        """Scrape all active competitors (or specific ones by ID)."""
        query = select(CompetitorSource).where(CompetitorSource.is_active == True)
        if competitor_ids:
            query = query.where(CompetitorSource.id.in_(competitor_ids))
        result = await self.db.execute(query)
        competitors = result.scalars().all()
        if not competitors:
            logger.warning("no_competitors_found")
            return []
        results: list[ScrapeResult] = []
        for comp in competitors:
            try:
                httpx_result = await self._scrape_with_httpx(comp)
                if httpx_result and httpx_result.success and httpx_result.jobs:
                    logger.info(
                        "scraper_success",
                        competitor=comp.name,
                        jobs=len(httpx_result.jobs),
                    )
                    await self._persist_jobs(comp, httpx_result)
                    results.append(httpx_result)
                    continue
            except Exception as e:
                logger.warning("scraper_failed", competitor=comp.name, error=str(e))
            if settings.use_mock_fallback:
                logger.info(
                    "using_mock_data",
                    competitor=comp.name,
                    reason="BS4 scraper returned no jobs — using curated mock data",
                )
                mock_jobs = get_mock_jobs().get(comp.name, [])
                mock_result = ScrapeResult(
                    competitor_name=comp.name,
                    jobs=mock_jobs,
                    success=True,
                )
                await self._persist_jobs(comp, mock_result)
                results.append(mock_result)
            else:
                results.append(
                    ScrapeResult(
                        competitor_name=comp.name,
                        success=False,
                        error="Scraper failed and mock fallback disabled",
                    )
                )
        return results

    async def _scrape_with_httpx(
        self, competitor: CompetitorSource
    ) -> ScrapeResult | None:
        """Try the httpx-based scraper for a single competitor."""
        scraper_cls = SCRAPER_REGISTRY.get(competitor.name)
        if not scraper_cls:
            return None
        scraper = scraper_cls(competitor.name, competitor.careers_url)
        return await scraper.scrape()

    async def _persist_jobs(
        self, competitor: CompetitorSource, scrape_result: ScrapeResult
    ) -> int:
        """Persist scraped jobs — upserts on duplicate URL or title+competitor.
        New jobs are INSERTed. Existing jobs are UPDATEd with fresh scraped data
        (salary, description, location, posting date may have changed).
        """
        jobs_added = 0
        jobs_updated = 0
        async with self._db_lock:
            for scraped_job in scrape_result.jobs:
                existing = None
                if scraped_job.job_url:
                    existing_result = await self.db.execute(
                        select(JobPosting).where(
                            JobPosting.job_url == scraped_job.job_url
                        )
                    )
                    existing = existing_result.scalar_one_or_none()
                if not existing:
                    existing_result = await self.db.execute(
                        select(JobPosting).where(
                            JobPosting.job_title == scraped_job.job_title,
                            JobPosting.competitor_id == competitor.id,
                        )
                    )
                    existing = existing_result.scalar_one_or_none()
                if existing:
                    existing.job_description = scraped_job.job_description
                    existing.salary_range = (
                        scraped_job.salary_range or existing.salary_range
                    )
                    existing.location = scraped_job.location or existing.location
                    existing.posting_date = (
                        scraped_job.posting_date or existing.posting_date
                    )
                    if scraped_job.job_url and not existing.job_url:
                        existing.job_url = scraped_job.job_url
                    jobs_updated += 1
                    continue
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
                    data_source=DataSource(scraped_job.data_source),
                    raw_html=scraped_job.raw_html,
                )
                self.db.add(job)
                jobs_added += 1
                alert = Alert(
                    alert_type=AlertType.NEW_JOB,
                    title=f"New job posting detected: {scraped_job.job_title}",
                    message=f"{scraped_job.competitor_name} posted '{scraped_job.job_title}' in {scraped_job.location or 'unknown location'}",
                    severity="info",
                    related_entity_type="job_posting",
                )
                self.db.add(alert)
            competitor.last_scraped_at = datetime.now(timezone.utc)
            await self.db.flush()
        logger.info(
            "competitor_scraped",
            competitor=competitor.name,
            jobs_added=jobs_added,
            jobs_updated=jobs_updated,
            total_scraped=len(scrape_result.jobs),
        )
        return jobs_added
