"""Base scraper class — defines the interface for all competitor scrapers."""

from __future__ import annotations
import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
import httpx
from app.core import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ScrapedJob:
    """A single job posting extracted from a competitor website."""

    competitor_name: str
    job_title: str
    job_description: str
    location: str | None = None
    sector: str | None = None
    salary_range: str | None = None
    job_url: str | None = None
    posting_date: str | None = None
    raw_html: str | None = None
    data_source: str = "scraped"


@dataclass
class ScrapeResult:
    """Result of a scraping operation."""

    competitor_name: str
    jobs: list[ScrapedJob] = field(default_factory=list)
    success: bool = True
    error: str | None = None
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseScraper(abc.ABC):
    """Abstract base class for all competitor scrapers.
    Each competitor gets its own scraper subclass that knows
    how to navigate that specific site's HTML structure.
    """

    def __init__(self, competitor_name: str, careers_url: str) -> None:
        self.competitor_name = competitor_name
        self.careers_url = careers_url
        self.client = httpx.AsyncClient(
            timeout=settings.scrape_timeout,
            headers={"User-Agent": settings.scrape_user_agent},
            follow_redirects=True,
        )

    async def scrape(self) -> ScrapeResult:
        """Execute the scraping pipeline with error handling."""
        try:
            logger.info(
                "scraping_started",
                competitor=self.competitor_name,
                url=self.careers_url,
            )
            jobs = await self._extract_jobs()
            logger.info(
                "scraping_completed",
                competitor=self.competitor_name,
                job_count=len(jobs),
            )
            return ScrapeResult(
                competitor_name=self.competitor_name,
                jobs=jobs,
                success=True,
            )
        except httpx.HTTPStatusError as exc:
            error_msg = f"HTTP {exc.response.status_code} from {self.careers_url}"
            logger.warning(
                "scraping_http_error", competitor=self.competitor_name, error=error_msg
            )
            return ScrapeResult(
                competitor_name=self.competitor_name,
                success=False,
                error=error_msg,
            )
        except httpx.TimeoutException:
            error_msg = f"Timeout after {settings.scrape_timeout}s"
            logger.warning("scraping_timeout", competitor=self.competitor_name)
            return ScrapeResult(
                competitor_name=self.competitor_name,
                success=False,
                error=error_msg,
            )
        except Exception as exc:
            error_msg = f"Unexpected error: {exc}"
            logger.error(
                "scraping_error", competitor=self.competitor_name, error=str(exc)
            )
            return ScrapeResult(
                competitor_name=self.competitor_name,
                success=False,
                error=error_msg,
            )
        finally:
            await self.client.aclose()

    @abc.abstractmethod
    async def _extract_jobs(self) -> list[ScrapedJob]:
        """Subclasses implement this to extract jobs from the competitor site."""
        ...

    async def _fetch_page(self, url: str) -> str:
        """Fetch a page and return its HTML content."""
        response = await self.client.get(url)
        response.raise_for_status()
        return response.text

    def _resolve_url(self, href: str | None) -> str | None:
        """Convert a relative URL to an absolute URL using the careers_url base."""
        if not href:
            return None
        if href.startswith(("http://", "https://")):
            return href
        from urllib.parse import urlparse, urljoin

        base = (
            f"{urlparse(self.careers_url).scheme}://{urlparse(self.careers_url).netloc}"
        )
        return urljoin(base, href)
