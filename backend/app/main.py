import os
import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.future import select

from .config import settings
from .database import engine, Base, AsyncSessionLocal
from .models import User, Device, ReferencePoint
from .auth import get_password_hash
from .mqtt_service import mqtt_service

from .api.auth import router as auth_router
from .api.devices import router as devices_router
from .api.reference import router as reference_router
from .api.telemetry import router as telemetry_router
from .api.events import router as events_router
from .api.simulator import router as simulator_router
from .websocket.endpoints import router as ws_router


async def seed_initial_data():
    """Initializes tables and seeds default authorized users, devices, and reference point."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 1. Seed Admin User
        admin_res = await session.execute(select(User).where(User.username == "admin"))
        if not admin_res.scalars().first():
            admin = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                is_active=True,
                created_at=time.time()
            )
            session.add(admin)

        # 2. Seed Operator User
        op_res = await session.execute(select(User).where(User.username == "operator"))
        if not op_res.scalars().first():
            operator = User(
                username="operator",
                hashed_password=get_password_hash("operator123"),
                role="operator",
                is_active=True,
                created_at=time.time()
            )
            session.add(operator)

        # 3. Seed Default Device "unit_001"
        dev_res = await session.execute(select(Device).where(Device.device_id == "unit_001"))
        if not dev_res.scalars().first():
            device = Device(
                device_id="unit_001",
                name="Field Unit 01 (Consenting Tracker)",
                token_hash=get_password_hash(settings.DEFAULT_DEVICE_TOKEN),
                status="ACTIVE",
                is_revoked=False,
                registered_at=time.time(),
                last_seen=0.0
            )
            session.add(device)

        # 4. Seed Initial Reference Point
        ref_res = await session.execute(select(ReferencePoint).where(ReferencePoint.is_active == True))
        if not ref_res.scalars().first():
            ref = ReferencePoint(
                latitude=12.97160000,
                longitude=77.59460000,
                altitude=900.0,
                initial_heading=0.0,
                name="Ground Station Datum (E=0, N=0, U=0)",
                is_active=True,
                created_at=time.time()
            )
            session.add(ref)

        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await seed_initial_data()
    loop = asyncio.get_running_loop()
    from .api.simulator import set_main_loop
    set_main_loop(loop)
    mqtt_service.start(loop)
    yield
    # Shutdown
    mqtt_service.stop()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Real-Time GPS-Denied Localization & Tracking Ground Station API",
    lifespan=lifespan
)

# CORS Middleware configuration
cors_raw = settings.CORS_ORIGINS
if cors_raw == "*" or "*" in cors_raw.split(","):
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    origins_list = [o.strip() for o in cors_raw.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Include Routers
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(devices_router, prefix=settings.API_PREFIX)
app.include_router(reference_router, prefix=settings.API_PREFIX)
app.include_router(telemetry_router, prefix=settings.API_PREFIX)
app.include_router(events_router, prefix=settings.API_PREFIX)
app.include_router(simulator_router, prefix=settings.API_PREFIX)
app.include_router(ws_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "gps-denied-ground-station",
        "version": settings.VERSION,
        "gps_status": "DENIED / NOT USED",
        "timestamp": time.time()
    }


# Optional: Serve production frontend static assets if dist exists
_curr_dir = os.path.dirname(os.path.abspath(__file__))
_dist_candidates = [
    os.path.abspath(os.path.join(_curr_dir, "..", "..", "frontend", "dist")),
    os.path.abspath(os.path.join(_curr_dir, "..", "frontend", "dist")),
    "/app/frontend/dist",
    "/app/dist"
]

_frontend_dist = None
for _cand in _dist_candidates:
    if os.path.exists(_cand) and os.path.isfile(os.path.join(_cand, "index.html")):
        _frontend_dist = _cand
        break

if _frontend_dist:
    import os
    from fastapi.staticfiles import StaticFiles
    from starlette.responses import FileResponse
    from fastapi.exceptions import HTTPException

    _assets_dir = os.path.join(_frontend_dist, "assets")
    if os.path.exists(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api") or full_path.startswith("ws") or full_path in ["health", "docs", "openapi.json", "redoc"]:
            raise HTTPException(status_code=404, detail="Not found")
        target_file = os.path.join(_frontend_dist, full_path)
        if full_path and os.path.exists(target_file) and os.path.isfile(target_file):
            return FileResponse(target_file)
        index_file = os.path.join(_frontend_dist, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Page not found")

