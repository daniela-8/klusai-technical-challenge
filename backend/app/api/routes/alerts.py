"""Alerts API — manage system notifications."""

from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import Alert
from app.models.schemas import AlertResponse

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    unread_only: bool = False,
    limit: int = Query(default=50, le=200),
) -> list:
    """List alerts, optionally filtered to unread only."""
    query = select(Alert).order_by(Alert.created_at.desc())
    if unread_only:
        query = query.where(Alert.is_read == False)
    query = query.limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/{alert_id}/read")
async def mark_read(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark a single alert as read."""
    await db.execute(update(Alert).where(Alert.id == alert_id).values(is_read=True))
    return {"status": "ok"}


@router.patch("/read-all")
async def mark_all_read(db: AsyncSession = Depends(get_db)) -> dict:
    """Mark all alerts as read."""
    await db.execute(update(Alert).values(is_read=True))
    return {"status": "ok"}
