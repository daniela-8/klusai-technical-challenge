"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db, engine, Base


@pytest.fixture(autouse=True)
async def setup_db():
    """Set up and tear down the database for each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Health endpoint returns 200."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "openai_configured" in data


@pytest.mark.asyncio
async def test_list_competitors(client: AsyncClient):
    """List competitors returns seeded data."""
    response = await client.get("/api/competitors")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_create_competitor(client: AsyncClient):
    """Create a new competitor."""
    response = await client.post(
        "/api/competitors",
        json={
            "name": "Test Competitor",
            "website_url": "https://test.com",
            "careers_url": "https://test.com/careers",
            "category": "large",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Competitor"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_duplicate_competitor(client: AsyncClient):
    """Creating a duplicate competitor returns 409."""
    payload = {
        "name": "Unique Corp",
        "website_url": "https://unique.com",
        "careers_url": "https://unique.com/jobs",
        "category": "finance",
    }
    await client.post("/api/competitors", json=payload)
    response = await client.post("/api/competitors", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_upload_job(client: AsyncClient):
    """Upload a job description."""
    response = await client.post(
        "/api/jobs",
        json={
            "job_title": "Test Engineer",
            "job_description": "This is a test job at a SaaS company.",
            "location": "Paris",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["job_title"] == "Test Engineer"
    assert data["data_source"] == "uploaded"


@pytest.mark.asyncio
async def test_list_jobs_with_search(client: AsyncClient):
    """Search jobs by keyword."""
    await client.post(
        "/api/jobs",
        json={
            "job_title": "Python Developer",
            "job_description": "Looking for an experienced Python developer for a FinTech company.",
        },
    )
    response = await client.get("/api/jobs?search=Python")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any("Python" in j["job_title"] for j in data)


@pytest.mark.asyncio
async def test_dashboard(client: AsyncClient):
    """Dashboard returns aggregated stats."""
    response = await client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "total_jobs" in data
    assert "total_companies_matched" in data
    assert "high_priority_targets" in data


@pytest.mark.asyncio
async def test_alerts_list(client: AsyncClient):
    """List alerts."""
    response = await client.get("/api/alerts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_briefs_list(client: AsyncClient):
    """List briefs."""
    response = await client.get("/api/briefs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_pipeline_scrape(client: AsyncClient):
    """Trigger scraping pipeline."""
    response = await client.post("/api/pipeline/scrape")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "jobs_collected" in data


@pytest.mark.asyncio
async def test_pipeline_process(client: AsyncClient):
    """Trigger processing pipeline."""
    await client.post("/api/pipeline/scrape")
    response = await client.post("/api/pipeline/process")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "jobs_processed" in data
