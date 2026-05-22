"""Database migration — ensure all job_postings have a valid data_source value.
This script sets any NULL data_source rows to 'mocked' as a safety net.
The current codebase already sets data_source correctly, but older DB rows
might have NULL values from before the field was added.
Usage:
    cd backend && python migrate_data_source.py
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
async def main():
    from sqlalchemy import text
    from app.core.database import engine
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM job_postings WHERE data_source IS NULL")
        )
        null_count = result.scalar()
        print(f"Found {null_count} rows with NULL data_source")
        if null_count > 0:
            await conn.execute(
                text("UPDATE job_postings SET data_source = 'mocked' WHERE data_source IS NULL")
            )
            print(f"Updated {null_count} rows to data_source='mocked'")
        else:
            print("All rows already have a valid data_source ✓")
        result = await conn.execute(
            text("SELECT data_source, COUNT(*) as cnt FROM job_postings GROUP BY data_source")
        )
        rows = result.fetchall()
        print("\nData source distribution:")
        for row in rows:
            print(f"  {row[0]}: {row[1]} jobs")
    print("\nMigration complete ✓")
if __name__ == "__main__":
    asyncio.run(main())
