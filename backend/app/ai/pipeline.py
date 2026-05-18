"""AI Pipeline orchestrator — coordinates matching, scoring, and brief generation."""

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.ai.llm_client import LLMClient
from app.ai.embeddings import EmbeddingService
from app.ai.company_matcher import CompanyMatcher
from app.ai.priority_scorer import PriorityScorer
from app.ai.brief_generator import BriefGenerator
from app.ai.web_search import WebSearchService
from app.core.logging import get_logger
from app.models import (
    JobPosting,
    CompanyMatch,
    PriorityScore,
    ProspectBrief,
    Alert,
    AlertType,
)

logger = get_logger(__name__)
_PIPELINE_LOCK = asyncio.Lock()


class AIPipeline:
    """End-to-end AI processing pipeline."""

    def __init__(self) -> None:
        self.llm = LLMClient()
        self.embeddings = EmbeddingService()
        self.web_search = WebSearchService()
        self.matcher = CompanyMatcher(self.llm, self.embeddings, self.web_search)
        self.scorer = PriorityScorer(self.llm)
        self.brief_gen = BriefGenerator(self.llm)
        self.BATCH_SIZE = 5

    async def process_jobs(
        self,
        db: AsyncSession,
        job_ids: list[str] | None = None,
        max_jobs: int = 5,
    ) -> dict:
        """Process unprocessed jobs through the full AI pipeline."""
        if _PIPELINE_LOCK.locked():
            logger.warning("pipeline_already_running")
            return {
                "jobs_processed": 0,
                "matches_created": 0,
                "scores_updated": 0,
                "errors": [
                    "Pipeline already running — please wait for the current run to finish."
                ],
                "jobs_remaining": 0,
            }
        async with _PIPELINE_LOCK:
            query = select(JobPosting).options(selectinload(JobPosting.company_match))
            if job_ids:
                query = query.where(JobPosting.id.in_(job_ids))
            else:
                query = query.where(JobPosting.is_processed == False)
            result = await db.execute(query)
            all_unprocessed = result.scalars().all()
            jobs = all_unprocessed[:max_jobs]
            remaining = len(all_unprocessed) - len(jobs)
            logger.info(
                "pipeline_start",
                total_unprocessed=len(all_unprocessed),
                batch_size=len(jobs),
                remaining_after_run=remaining,
            )
            stats = {
                "jobs_processed": 0,
                "matches_created": 0,
                "scores_updated": 0,
                "errors": [],
                "jobs_remaining": remaining,
            }
            affected_companies = set()
            for job in jobs:
                try:
                    matched_company = await self._process_single_job(db, job)
                    if matched_company:
                        affected_companies.add(matched_company)
                    await db.commit()
                    stats["jobs_processed"] += 1
                    stats["matches_created"] += 1
                except Exception as e:
                    await db.rollback()
                    error_msg = f"Failed to process {job.job_title}: {e}"
                    logger.error("job_processing_failed", job_id=job.id, error=str(e))
                    stats["errors"].append(error_msg)
            try:
                score_count = await self._update_priority_scores(db, affected_companies)
                await db.commit()
                stats["scores_updated"] = score_count
            except Exception as e:
                await db.rollback()
                logger.error("scoring_failed", error=str(e))
                stats["errors"].append(f"Scoring failed: {e}")
            return stats

    async def _process_single_job(
        self, db: AsyncSession, job: JobPosting
    ) -> str | None:
        """Run company matching on a single job posting."""
        if job.company_match:
            job.is_processed = True
            return job.company_match.company_name
        days_since = None
        if job.posting_date:
            try:
                post_date = datetime.strptime(job.posting_date, "%Y-%m-%d")
                days_since = (
                    datetime.now(timezone.utc) - post_date.replace(tzinfo=timezone.utc)
                ).days
            except (ValueError, TypeError):
                pass
        match_result = await self.matcher.match_company(
            job_id=job.id,
            competitor_name=job.competitor_name,
            job_title=job.job_title,
            job_description=job.job_description,
            location=job.location,
            sector=job.sector,
            salary_range=job.salary_range,
            posting_date=job.posting_date,
        )
        company_match = CompanyMatch(
            job_id=job.id,
            company_name=match_result.get("company_name", "Unknown"),
            confidence_score=float(match_result.get("confidence_score", 0)),
            match_explanation=match_result.get("match_explanation", ""),
            signals_used=match_result.get("signals_used", []),
            enrichment_data=match_result.get("enrichment", {}),
            alternative_matches=match_result.get("alternative_matches", []),
        )
        db.add(company_match)
        enrichment = match_result.get("enrichment", {})
        if not job.sector and enrichment.get("likely_industry"):
            job.sector = enrichment["likely_industry"]
        job.is_processed = True
        confidence = float(match_result.get("confidence_score", 0))
        if confidence >= 80:
            alert = Alert(
                alert_type=AlertType.HIGH_PRIORITY,
                title=f"High-confidence match: {match_result.get('company_name', 'Unknown')}",
                message=(
                    f"Job '{job.job_title}' from {job.competitor_name} matched to "
                    f"{match_result.get('company_name', 'Unknown')} with {confidence:.0f}% confidence"
                ),
                severity="warning" if confidence >= 90 else "info",
                related_entity_id=job.id,
                related_entity_type="company_match",
            )
            db.add(alert)
        logger.info(
            "job_processed",
            job_id=job.id,
            company=match_result.get("company_name"),
            confidence=confidence,
        )
        return company_match.company_name

    async def _update_priority_scores(
        self, db: AsyncSession, affected_companies: set[str] | None = None
    ) -> int:
        """Update priority scores for matched companies."""
        query = select(CompanyMatch).options(selectinload(CompanyMatch.job))
        if affected_companies:
            query = query.where(CompanyMatch.company_name.in_(affected_companies))
        result = await db.execute(query)
        matches = result.scalars().all()
        company_jobs: dict[str, list] = {}
        company_match_data: dict[str, dict] = {}
        for match in matches:
            name = match.company_name
            if name not in company_jobs:
                company_jobs[name] = []
                company_match_data[name] = {
                    "confidence_score": match.confidence_score,
                    "match_explanation": match.match_explanation,
                    "signals_used": match.signals_used,
                    "enrichment": match.enrichment_data or {},
                }
            company_jobs[name].append(match)
        scores_updated = 0
        for company_name, matches_list in company_jobs.items():
            job_titles = [m.job.job_title for m in matches_list if m.job]
            job_descriptions = [m.job.job_description for m in matches_list if m.job]
            job_sectors = [m.job.sector for m in matches_list if m.job and m.job.sector]
            competitor_names = [m.job.competitor_name for m in matches_list if m.job]
            match_data = company_match_data[company_name]
            days_since = None
            for m in matches_list:
                if m.job and m.job.posting_date:
                    try:
                        post_date = datetime.strptime(m.job.posting_date, "%Y-%m-%d")
                        d = (
                            datetime.now(timezone.utc)
                            - post_date.replace(tzinfo=timezone.utc)
                        ).days
                        if days_since is None or d < days_since:
                            days_since = d
                    except (ValueError, TypeError):
                        pass
            score_result = await self.scorer.calculate_score(
                company_name=company_name,
                match_data=match_data,
                job_count=len(matches_list),
                job_titles=job_titles,
                days_since_posted=days_since,
                job_descriptions=job_descriptions,
                job_sectors=job_sectors,
                competitor_names=competitor_names,
            )
            existing_result = await db.execute(
                select(PriorityScore).where(PriorityScore.company_name == company_name)
            )
            existing = existing_result.scalar_one_or_none()
            if existing:
                existing.priority_score = score_result["priority_score"]
                existing.scoring_breakdown = score_result["scoring_breakdown"]
                existing.rationale = score_result["rationale"]
                existing.job_count = len(matches_list)
                existing.updated_at = datetime.now(timezone.utc)
            else:
                ps = PriorityScore(
                    company_name=company_name,
                    priority_score=score_result["priority_score"],
                    scoring_breakdown=score_result["scoring_breakdown"],
                    rationale=score_result["rationale"],
                    job_count=len(matches_list),
                )
                db.add(ps)
            scores_updated += 1
        return scores_updated

    async def generate_brief(
        self,
        db: AsyncSession,
        company_name: str,
    ) -> dict:
        """Generate a prospect brief for a specific company."""
        result = await db.execute(
            select(CompanyMatch)
            .options(selectinload(CompanyMatch.job))
            .where(CompanyMatch.company_name == company_name)
        )
        matches = result.scalars().all()
        if not matches:
            raise ValueError(f"No matches found for company: {company_name}")
        match_data = {
            "confidence_score": matches[0].confidence_score,
            "match_explanation": matches[0].match_explanation,
            "signals_used": matches[0].signals_used,
            "enrichment": matches[0].enrichment_data or {},
        }
        job_postings = [
            {
                "job_title": m.job.job_title,
                "competitor_name": m.job.competitor_name,
                "location": m.job.location,
                "sector": m.job.sector,
                "salary_range": m.job.salary_range,
                "posting_date": m.job.posting_date,
                "job_url": m.job.job_url,
                "data_source": (
                    m.job.data_source.value if m.job.data_source else "mocked"
                ),
            }
            for m in matches
            if m.job
        ]
        score_result = await db.execute(
            select(PriorityScore).where(PriorityScore.company_name == company_name)
        )
        score = score_result.scalar_one_or_none()
        score_data = {
            "priority_score": score.priority_score if score else 0,
            "scoring_breakdown": score.scoring_breakdown if score else {},
            "rationale": score.rationale if score else "",
        }
        brief_content = await self.brief_gen.generate_brief(
            company_name=company_name,
            match_data=match_data,
            score_data=score_data,
            job_postings=job_postings,
        )
        existing_result = await db.execute(
            select(ProspectBrief).where(ProspectBrief.company_name == company_name)
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            existing.brief_content = brief_content
            existing.generated_at = datetime.now(timezone.utc)
            brief_id = existing.id
        else:
            brief = ProspectBrief(
                company_name=company_name,
                brief_content=brief_content,
            )
            db.add(brief)
            await db.flush()
            brief_id = brief.id
        return {
            "id": brief_id,
            "company_name": company_name,
            "brief_content": brief_content,
        }
