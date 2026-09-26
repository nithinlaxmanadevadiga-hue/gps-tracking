import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Device, User, AuditLog
from ..schemas import DeviceResponse, DeviceCreate
from ..auth import get_current_user, require_role, get_password_hash
from ..config import settings

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=List[DeviceResponse])
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Device).order_by(Device.registered_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("", response_model=DeviceResponse)
async def register_device(
    device_in: DeviceCreate,
    current_user: User = Depends(require_role(["admin", "operator"])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Device).where(Device.device_id == device_in.device_id)
    res = await db.execute(stmt)
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="Device ID already exists")

    raw_token = device_in.token or settings.DEFAULT_DEVICE_TOKEN
    token_hash = get_password_hash(raw_token)

    new_device = Device(
        device_id=device_in.device_id,
        name=device_in.name,
        token_hash=token_hash,
        status="ACTIVE",
        is_revoked=False,
        registered_at=time.time(),
        last_seen=0.0
    )
    db.add(new_device)

    audit = AuditLog(
        user_id=current_user.username,
        action="DEVICE_REGISTERED",
        details=f"Device {device_in.device_id} registered by {current_user.username}"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_device)
    return new_device


@router.post("/{device_id}/revoke", response_model=DeviceResponse)
async def revoke_device(
    device_id: str,
    current_user: User = Depends(require_role(["admin", "operator"])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Device).where(Device.device_id == device_id)
    res = await db.execute(stmt)
    device = res.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.is_revoked = True
    device.status = "REVOKED"

    audit = AuditLog(
        user_id=current_user.username,
        action="DEVICE_REVOKED",
        details=f"Device {device_id} revoked by {current_user.username}"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(device)
    return device


@router.post("/{device_id}/reinstate", response_model=DeviceResponse)
async def reinstate_device(
    device_id: str,
    current_user: User = Depends(require_role(["admin", "operator"])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Device).where(Device.device_id == device_id)
    res = await db.execute(stmt)
    device = res.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.is_revoked = False
    device.status = "ACTIVE"

    audit = AuditLog(
        user_id=current_user.username,
        action="DEVICE_REINSTATED",
        details=f"Device {device_id} reinstated by {current_user.username}"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(device)
    return device
