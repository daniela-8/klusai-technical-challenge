"""SQLAlchemy async database engine and session management."""

from __future__ import annotations
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core import settings

Path("./data").mkdir(parents=True, exist_ok=True)
engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 15.0},
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


async def get_db() -> AsyncSession:
    """Dependency that provides a database session."""
    async with async_session() as session:
        try:
            yield session
            try:
                await session.commit()
            except Exception:
                pass
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
