import asyncio
from sqlalchemy import select, update
from app.core.database import async_session
from app.models import CompetitorSource
from app.scrapers.mock_data import get_seed_competitors
async def main():
    async with async_session() as db:
        seed_data = get_seed_competitors()
        for data in seed_data:
            stmt = update(CompetitorSource).where(
                CompetitorSource.name == data["name"]
            ).values(careers_url=data["careers_url"])
            await db.execute(stmt)
        await db.commit()
        print("Updated competitor URLs in the database.")
if __name__ == "__main__":
    asyncio.run(main())
