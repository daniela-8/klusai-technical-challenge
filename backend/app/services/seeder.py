"""Database seeder — populates and syncs initial competitor sources."""

from __future__ import annotations
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger
from app.models import CompetitorSource, CompetitorCategory
from app.scrapers.mock_data import get_seed_competitors

logger = get_logger(__name__)


async def seed_competitors(db: AsyncSession) -> int:
    """Seed the database with initial competitor sources.
    - If the DB is empty: inserts all competitors.
    - If competitors already exist: updates their URLs to the latest values,
      and inserts any new ones that don't exist yet.
    """
    result = await db.execute(select(CompetitorSource))
    existing = result.scalars().all()
    existing_names = {c.name for c in existing}
    competitors_data = get_seed_competitors()
    if existing:
        updated = 0
        added = 0
        for data in competitors_data:
            if data["name"] in existing_names:
                await db.execute(
                    update(CompetitorSource)
                    .where(CompetitorSource.name == data["name"])
                    .values(
                        careers_url=data["careers_url"],
                        website_url=data["website_url"],
                    )
                )
                updated += 1
            else:
                competitor = CompetitorSource(
                    name=data["name"],
                    website_url=data["website_url"],
                    careers_url=data["careers_url"],
                    category=CompetitorCategory(data["category"]),
                )
                db.add(competitor)
                added += 1
        await db.flush()
        logger.info("competitors_synced", updated=updated, added=added)
        return added
    count = 0
    for data in competitors_data:
        competitor = CompetitorSource(
            name=data["name"],
            website_url=data["website_url"],
            careers_url=data["careers_url"],
            category=CompetitorCategory(data["category"]),
        )
        db.add(competitor)
        count += 1
    await db.flush()
    logger.info("competitors_seeded", count=count)
    return count
