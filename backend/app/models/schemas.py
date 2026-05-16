"""Pydantic schemas for API request/response validation."""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class DataSourceEnum(str, Enum):
    SCRAPED = "scraped"
    MOCKED = "mocked"
    UPLOADED = "uploaded"


class CompetitorCategoryEnum(str, Enum):
    LARGE = "large"
    SALES_TECH = "sales_tech"
    FINANCE = "finance"


class AlertTypeEnum(str, Enum):
    NEW_JOB = "new_job"
    HIGH_PRIORITY = "high_priority"
    REPOSTED_JOB = "reposted_job"
    NEW_COMPETITOR = "new_competitor"
    CONFIDENCE_CHANGE = "confidence_change"


class CompetitorCreate(BaseModel):
    name: str
    website_url: str
    careers_url: str
    category: CompetitorCategoryEnum
    scrape_config: Optional[dict] = None


class CompetitorResponse(BaseModel):
    id: str
    name: str
    website_url: str
    careers_url: str
    category: CompetitorCategoryEnum
    is_active: bool
    last_scraped_at: Optional[datetime] = None
    created_at: datetime
    job_count: int = 0
    model_config = {"from_attributes": True}


class JobPostingCreate(BaseModel):
    """For uploading / pasting a job description."""

    job_title: str
    job_description: str
    competitor_name: str = "Manual Upload"
    location: Optional[str] = None
    sector: Optional[str] = None
    salary_range: Optional[str] = None
    job_url: Optional[str] = None
    posting_date: Optional[str] = None


class CompanyMatchResponse(BaseModel):
    id: str
    company_name: str
    confidence_score: float
    match_explanation: str
    signals_used: list
    enrichment_data: Optional[dict] = None
    alternative_matches: Optional[list] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class JobPostingResponse(BaseModel):
    id: str
    competitor_id: str
    competitor_name: str
    job_title: str
    job_description: str
    location: Optional[str] = None
    sector: Optional[str] = None
    salary_range: Optional[str] = None
    job_url: Optional[str] = None
    posting_date: Optional[str] = None
    detected_at: datetime
    data_source: DataSourceEnum
    is_processed: bool
    company_match: Optional[CompanyMatchResponse] = None
    model_config = {"from_attributes": True}


class PriorityScoreResponse(BaseModel):
    id: str
    company_name: str
    priority_score: float
    scoring_breakdown: dict
    rationale: str
    job_count: int
    created_at: datetime
    updated_at: datetime
    jobs: List[JobPostingResponse] = []
    model_config = {"from_attributes": True}


class ProspectBriefResponse(BaseModel):
    id: str
    company_name: str
    brief_content: dict
    generated_at: datetime
    model_config = {"from_attributes": True}


class GenerateBriefRequest(BaseModel):
    company_name: str


class AlertResponse(BaseModel):
    id: str
    alert_type: AlertTypeEnum
    title: str
    message: str
    severity: str
    related_entity_id: Optional[str] = None
    related_entity_type: Optional[str] = None
    is_read: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_jobs: int
    total_companies_matched: int
    high_priority_targets: int
    active_competitors: int
    avg_confidence: float
    recent_alerts: int
    jobs_by_source: Dict[str, int]
    jobs_by_competitor: Dict[str, int]
    confidence_distribution: Dict[str, int]
    top_sectors: list


class ScrapeRequest(BaseModel):
    competitor_ids: Optional[List[str]] = None


class ScrapeStatusResponse(BaseModel):
    status: str
    competitors_scraped: int
    jobs_collected: int
    errors: List[str]


class ProcessRequest(BaseModel):
    job_ids: Optional[List[str]] = None
    max_jobs: Optional[int] = None


class ProcessStatusResponse(BaseModel):
    status: str
    jobs_processed: int
    matches_created: int
    scores_updated: int
    errors: List[str]
    jobs_remaining: int = 0
    message: Optional[str] = None


class ScrapeUrlRequest(BaseModel):
    """Request to scrape a single job URL."""

    url: str = Field(..., description="Full URL of the job posting to scrape")


class ScrapeUrlResponse(BaseModel):
    """Response from scraping a single URL."""

    status: str
    competitor_detected: Optional[str] = None
    job: Optional[Dict] = None
    job_id: Optional[str] = None
    error: Optional[str] = None
