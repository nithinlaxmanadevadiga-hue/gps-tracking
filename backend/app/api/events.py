from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..database import get_db
from ..models import AuditLog, LocalizationEvent, User
from ..auth import get_current_user, require_role

router = APIRouter(prefix="/events", tags=["Events & Audit Logs"])


class EventResponse(BaseModel):
    id: int
    device_id: str
    event_type: str
    severity: str
    description: str
    timestamp: float


class AuditResponse(BaseModel):
    id: int
    user_id: str
    action: str
    details: Optional[str]
    timestamp: float


@router.get("/localization", response_model=List[EventResponse])
async def get_localization_events(
    device_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(LocalizationEvent)
    if device_id:
        query = query.where(LocalizationEvent.device_id == device_id)
    query = query.order_by(LocalizationEvent.timestamp.desc()).limit(limit)

    res = await db.execute(query)
    return res.scalars().all()


@router.get("/audit", response_model=List[AuditResponse])
async def get_audit_logs(
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()
