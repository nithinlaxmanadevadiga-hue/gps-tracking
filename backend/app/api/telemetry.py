import json
import time
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import TelemetryRecord, Device, LocalizationEvent, User
from ..schemas import TelemetryPayload, DevicePositionResponse, HistoryResponse, HistoryPoint
from ..telemetry_hub import hub
from ..auth import get_current_user, verify_device_credentials

router = APIRouter(tags=["Telemetry"])


@router.post("/telemetry", status_code=status.HTTP_201_CREATED)
async def ingest_telemetry(
    payload: TelemetryPayload,
    authorization: Optional[str] = Header(None),
    x_device_token: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Secure Telemetry Ingestion endpoint for onboard localization units.
    Requires device authentication token.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    elif x_device_token:
        token = x_device_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing device authentication token"
        )

    # Verify device authorization and non-revocation
    device = await verify_device_credentials(payload.device_id, token, db)

    now = time.time()
    device.last_seen = now

    # Store telemetry record in DB
    record = TelemetryRecord(
        device_id=payload.device_id,
        timestamp=payload.timestamp,
        latitude=payload.position.latitude,
        longitude=payload.position.longitude,
        altitude=payload.position.altitude,
        east=payload.position.east,
        north=payload.position.north,
        up=payload.position.up,
        velocity_east=payload.velocity.east,
        velocity_north=payload.velocity.north,
        velocity_up=payload.velocity.up,
        heading=payload.localization.heading_deg or 0.0,
        position_accuracy=payload.localization.position_accuracy,
        localization_status=payload.localization.status or "GOOD",
        raw_json=json.dumps(payload.model_dump())
    )
    db.add(record)

    # Detect and record localization failure events
    if payload.localization.status in ["DEGRADED", "LOST"]:
        event = LocalizationEvent(
            device_id=payload.device_id,
            event_type=payload.localization.status,
            severity="WARNING" if payload.localization.status == "DEGRADED" else "CRITICAL",
            description=payload.localization.status_reason or f"Quality transitioned to {payload.localization.status}",
            timestamp=payload.timestamp
        )
        db.add(event)

    await db.commit()

    # Instant broadcast to all WebSocket connected browser clients
    await hub.broadcast_telemetry(payload.model_dump())

    return {"status": "accepted", "device_id": payload.device_id}


@router.get("/devices/{device_id}/position", response_model=DevicePositionResponse)
async def get_device_position(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Try in-memory cache first for real-time speed
    cached = hub.get_latest_position(device_id)
    if cached:
        return cached

    # Query last known record from database
    stmt = (
        select(TelemetryRecord)
        .where(TelemetryRecord.device_id == device_id)
        .order_by(TelemetryRecord.timestamp.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    record = res.scalars().first()

    if not record or not record.raw_json:
        raise HTTPException(status_code=404, detail="No position telemetry available for device")

    data = json.loads(record.raw_json)
    now = time.time()
    data["age_ms"] = round((now - record.timestamp) * 1000.0, 1)
    data["is_stale"] = (now - record.timestamp) > 3.0
    return data


@router.get("/devices/{device_id}/history", response_model=HistoryResponse)
async def get_device_history(
    device_id: str,
    limit: int = Query(500, ge=1, le=5000),
    since: Optional[float] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(TelemetryRecord).where(TelemetryRecord.device_id == device_id)
    if since:
        query = query.where(TelemetryRecord.timestamp >= since)
    query = query.order_by(TelemetryRecord.timestamp.asc()).limit(limit)

    res = await db.execute(query)
    records = res.scalars().all()

    points = [
        HistoryPoint(
            timestamp=r.timestamp,
            latitude=r.latitude,
            longitude=r.longitude,
            altitude=r.altitude,
            east=r.east,
            north=r.north,
            up=r.up,
            speed=round((r.velocity_east**2 + r.velocity_north**2 + r.velocity_up**2)**0.5, 2),
            heading=r.heading,
            status=r.localization_status,
            position_accuracy=r.position_accuracy
        )
        for r in records
    ]

    return HistoryResponse(
        device_id=device_id,
        count=len(points),
        points=points
    )


@router.post("/devices/{device_id}/clear-trail")
async def clear_device_trail(
    device_id: str,
    current_user: User = Depends(get_current_user)
):
    hub.clear_device_history(device_id)
    return {"status": "cleared", "device_id": device_id}
