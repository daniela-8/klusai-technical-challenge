"""SQLAlchemy ORM models for the Competitor Intelligence PoC."""

from __future__ import annotations
import enum
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DataSource(str, enum.Enum):
    SCRAPED = "scraped"
    MOCKED = "mocked"
    UPLOADED = "uploaded"


class CompetitorCategory(str, enum.Enum):
    LARGE = "large"
    SALES_TECH = "sales_tech"
    FINANCE = "finance"


class AlertType(str, enum.Enum):
    NEW_JOB = "new_job"
    HIGH_PRIORITY = "high_priority"
    REPOSTED_JOB = "reposted_job"
    NEW_COMPETITOR = "new_competitor"
    CONFIDENCE_CHANGE = "confidence_change"


class CompetitorSource(Base):
    """A recruitment competitor whose jobs we track."""

    __tablename__ = "competitor_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    website_url: Mapped[str] = mapped_column(String(500), nullable=False)
    careers_url: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[CompetitorCategory] = mapped_column(
        Enum(CompetitorCategory), nullable=False
    )
    scrape_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    jobs: Mapped[List["JobPosting"]] = relationship(
        back_populates="competitor", cascade="all, delete-orphan"
    )


class JobPosting(Base):
    """A job posting collected from a competitor source."""

    __tablename__ = "job_postings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    competitor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("competitor_sources.id"), nullable=False
    )
    competitor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(500), nullable=False)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    salary_range: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    posting_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    data_source: Mapped[DataSource] = mapped_column(Enum(DataSource), nullable=False)
    raw_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    competitor: Mapped["CompetitorSource"] = relationship(back_populates="jobs")
    company_match: Mapped[Optional["CompanyMatch"]] = relationship(
        back_populates="job", uselist=False, cascade="all, delete-orphan"
    )


class CompanyMatch(Base):
    """AI-inferred company match for a job posting."""

    __tablename__ = "company_matches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("job_postings.id"), nullable=False, unique=True
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    match_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    signals_used: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    enrichment_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    alternative_matches: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    job: Mapped["JobPosting"] = relationship(back_populates="company_match")


class PriorityScore(Base):
    """Priority score for a matched company — determines outreach order."""

    __tablename__ = "priority_scores"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    scoring_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    job_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class ProspectBrief(Base):
    """AI-generated one-page prospect brief for cold outreach."""

    __tablename__ = "prospect_briefs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    brief_content: Mapped[dict] = mapped_column(JSON, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Alert(Base):
    """System alerts for notable events."""

    __tablename__ = "alerts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="info")
    related_entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    related_entity_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
