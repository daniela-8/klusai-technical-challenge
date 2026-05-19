"""FastAPI application entry point."""

from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core import settings
from app.core.database import init_db, async_session
from app.core.logging import setup_logging, get_logger
from app.services.seeder import seed_competitors
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.competitors import router as competitors_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.companies import router as companies_router
from app.api.routes.pipeline import router as pipeline_router
from app.api.routes.alerts import router as alerts_router
from app.api.routes.briefs import router as briefs_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    setup_logging()
    logger.info("starting_application", openai_available=settings.has_openai_key)
    await init_db()
    async with async_session() as db:
        try:
            await seed_competitors(db)
            await db.commit()
        except Exception as e:
            logger.error("seeding_failed", error=str(e))
            await db.rollback()
    logger.info("application_ready")
    yield
    logger.info("shutting_down")


app = FastAPI(
    title="KlusAI — Competitor Intelligence PoC",
    description=(
        "AI-powered competitor intelligence tool for recruitment agencies. "
        "Scrapes competitor job postings, identifies hiring companies using LLM analysis, "
        "scores priorities, and generates prospect briefs for targeted outreach."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(dashboard_router, prefix="/api")
app.include_router(competitors_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(companies_router, prefix="/api")
app.include_router(pipeline_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(briefs_router, prefix="/api")


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "openai_configured": settings.has_openai_key,
    }
