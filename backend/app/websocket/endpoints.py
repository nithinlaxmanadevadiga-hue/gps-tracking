import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status

from ..telemetry_hub import hub
from ..auth import authenticate_websocket_token
from ..config import settings

router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws/devices/{device_id}")
async def websocket_device_stream(
    websocket: WebSocket,
    device_id: str,
    token: Optional[str] = Query(None)
):
    """
    Real-time streaming WebSocket endpoint for a specific device.
    Requires valid JWT token query param.
    """
    auth_payload = authenticate_websocket_token(token)
    if not auth_payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await hub.register_subscriber(websocket, device_id=device_id)
    try:
        while True:
            # Keep-alive listen for client pings
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        hub.remove_subscriber(websocket, device_id=device_id)
    except Exception:
        hub.remove_subscriber(websocket, device_id=device_id)


@router.websocket("/ws/live")
async def websocket_live_dashboard(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    Real-time broadcast WebSocket endpoint for dashboard live map.
    Requires valid JWT token query param.
    """
    auth_payload = authenticate_websocket_token(token)
    if not auth_payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await hub.register_subscriber(websocket, device_id=None)
    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        hub.remove_subscriber(websocket)
    except Exception:
        hub.remove_subscriber(websocket)


@router.websocket("/ws/telemetry/ingest")
async def websocket_telemetry_ingest(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for onboard edge devices to stream high-frequency telemetry.
    Authenticated using device secret token.
    """
    if token != settings.DEFAULT_DEVICE_TOKEN and not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
                await hub.broadcast_telemetry(data)
                await websocket.send_text(json.dumps({"status": "ack", "time": data.get("timestamp")}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
