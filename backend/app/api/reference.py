import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import ReferencePoint, User, AuditLog
from ..schemas import ReferencePointCreate, ReferencePointResponse
from ..auth import get_current_user, require_role

router = APIRouter(prefix="/reference", tags=["Reference Point"])


@router.get("", response_model=ReferencePointResponse)
async def get_active_reference(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ReferencePoint).where(ReferencePoint.is_active == True).order_by(ReferencePoint.created_at.desc())
    res = await db.execute(stmt)
    ref = res.scalars().first()

    if not ref:
        # Default fallback reference: Bengaluru test coords
        ref = ReferencePoint(
            latitude=12.97160000,
            longitude=77.59460000,
            altitude=900.0,
            initial_heading=0.0,
            name="Default Reference Point",
            is_active=True,
            created_at=time.time()
        )
        db.add(ref)
        await db.commit()
        await db.refresh(ref)

    return ref


@router.post("", response_model=ReferencePointResponse)
async def configure_reference_point(
    ref_in: ReferencePointCreate,
    current_user: User = Depends(require_role(["admin", "operator"])),
    db: AsyncSession = Depends(get_db)
):
    # Deactivate existing active points
    stmt = select(ReferencePoint).where(ReferencePoint.is_active == True)
    res = await db.execute(stmt)
    active_points = res.scalars().all()
    for p in active_points:
        p.is_active = False

    new_ref = ReferencePoint(
        latitude=ref_in.latitude,
        longitude=ref_in.longitude,
        altitude=ref_in.altitude,
        initial_heading=ref_in.initial_heading,
        name=ref_in.name or "Configured Reference",
        is_active=True,
        created_at=time.time()
    )
    db.add(new_ref)

    audit = AuditLog(
        user_id=current_user.username,
        action="UPDATE_REFERENCE_POINT",
        details=f"Lat: {ref_in.latitude}, Lon: {ref_in.longitude}, Alt: {ref_in.altitude}, Heading: {ref_in.initial_heading}"
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_ref)

    return new_ref
