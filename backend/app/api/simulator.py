from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
import sys
import os

from ..schemas import SimulatorControlRequest
from ..models import User
from ..auth import get_current_user

# Add simulator folder to sys.path
_curr = os.path.dirname(os.path.abspath(__file__))
for candidate in [
    os.path.abspath(os.path.join(_curr, "..", "..", "..", "simulator")),
    os.path.abspath(os.path.join(_curr, "..", "..", "simulator")),
    os.path.abspath(os.path.join(_curr, "..", "simulator")),
    "/app/simulator",
    "simulator"
]:
    if os.path.exists(candidate) and candidate not in sys.path:
        sys.path.insert(0, candidate)

from synthetic_sensor_stream import SimulatorEngine


router = APIRouter(prefix="/simulator", tags=["Simulator"])

from ..config import settings
from ..telemetry_hub import hub
import asyncio

_main_loop = None

def set_main_loop(loop):
    global _main_loop
    _main_loop = loop

def _dispatch_to_hub(payload):
    global _main_loop
    try:
        loop = _main_loop
        if loop is None or loop.is_closed():
            try:
                loop = asyncio.get_event_loop()
            except Exception:
                loop = None
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(hub.broadcast_telemetry(payload), loop)
    except Exception:
        pass

# Global simulator engine instance attached to backend
sim_engine = SimulatorEngine(
    device_id="unit_001",
    ref_lat=12.97160000,
    ref_lon=77.59460000,
    ref_alt=900.0,
    ref_heading=0.0,
    auth_token=settings.DEFAULT_DEVICE_TOKEN,
    on_telemetry=_dispatch_to_hub
)


@router.get("/status")
async def get_simulator_status(current_user: User = Depends(get_current_user)):
    return sim_engine.get_state()


@router.post("/control")
async def control_simulator(
    req: SimulatorControlRequest,
    current_user: User = Depends(get_current_user)
):
    state = sim_engine.set_controls(
        running=req.running,
        paused=req.paused,
        speed=req.speed,
        pattern=req.pattern,
        lidar_degraded=req.lidar_degraded,
        comms_loss=req.comms_loss
    )
    return {
        "status": "success",
        "state": state
    }


@router.post("/reset")
async def reset_simulator(current_user: User = Depends(get_current_user)):
    sim_engine.reset()
    return {"status": "reset", "state": sim_engine.get_state()}
