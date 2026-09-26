import time
import json
import asyncio
from typing import Dict, Any, List, Set, Optional
from fastapi import WebSocket


class TelemetryHub:
    """
    Central real-time telemetry dispatch and cache.
    Provides sub-millisecond in-memory cache and WebSocket fan-out.
    """

    def __init__(self):
        # Latest telemetry payload by device_id
        self._latest_positions: Dict[str, Dict[str, Any]] = {}

        # Recent history cache in memory for rapid replay (last 500 points per device)
        self._recent_history: Dict[str, List[Dict[str, Any]]] = {}

        # Active WebSockets: device_id -> set of WebSockets
        self._device_subscribers: Dict[str, Set[WebSocket]] = {}

        # Global subscribers (dashboard live stream)
        self._global_subscribers: Set[WebSocket] = set()

        # Ingestion WebSockets (from edge devices streaming up)
        self._ingestion_clients: Set[WebSocket] = set()

    async def register_subscriber(self, websocket: WebSocket, device_id: Optional[str] = None):
        await websocket.accept()
        if device_id:
            if device_id not in self._device_subscribers:
                self._device_subscribers[device_id] = set()
            self._device_subscribers[device_id].add(websocket)

            # Send immediate cached position if available
            if device_id in self._latest_positions:
                cached = self.get_latest_position(device_id)
                if cached:
                    await websocket.send_text(json.dumps(cached))
        else:
            self._global_subscribers.add(websocket)
            # Send all known latest device positions
            for d_id in self._latest_positions:
                cached = self.get_latest_position(d_id)
                if cached:
                    await websocket.send_text(json.dumps(cached))

    def remove_subscriber(self, websocket: WebSocket, device_id: Optional[str] = None):
        if device_id and device_id in self._device_subscribers:
            self._device_subscribers[device_id].discard(websocket)
            if not self._device_subscribers[device_id]:
                del self._device_subscribers[device_id]
        self._global_subscribers.discard(websocket)

    async def broadcast_telemetry(self, payload: Dict[str, Any]):
        device_id = payload.get("device_id")
        if not device_id:
            return

        now = time.time()
        payload["server_received_at"] = now
        self._latest_positions[device_id] = payload

        # Update in-memory ring buffer
        if device_id not in self._recent_history:
            self._recent_history[device_id] = []
        self._recent_history[device_id].append(payload)
        if len(self._recent_history[device_id]) > 1000:
            self._recent_history[device_id].pop(0)

        data_str = json.dumps(payload)

        # Broadcast to device-specific subscribers
        dead_device_ws = set()
        for ws in self._device_subscribers.get(device_id, set()):
            try:
                await ws.send_text(data_str)
            except Exception:
                dead_device_ws.add(ws)
        for ws in dead_device_ws:
            self.remove_subscriber(ws, device_id)

        # Broadcast to global subscribers
        dead_global_ws = set()
        for ws in self._global_subscribers:
            try:
                await ws.send_text(data_str)
            except Exception:
                dead_global_ws.add(ws)
        for ws in dead_global_ws:
            self.remove_subscriber(ws)

    def get_latest_position(self, device_id: str) -> Optional[Dict[str, Any]]:
        if device_id not in self._latest_positions:
            return None
        cached = self._latest_positions[device_id].copy()
        now = time.time()
        msg_time = cached.get("timestamp", now)
        cached["age_ms"] = round((now - msg_time) * 1000.0, 1)
        cached["is_stale"] = (now - msg_time) > 3.0
        return cached

    def get_recent_history(self, device_id: str, limit: int = 500) -> List[Dict[str, Any]]:
        history = self._recent_history.get(device_id, [])
        return history[-limit:]

    def clear_device_history(self, device_id: str):
        if device_id in self._recent_history:
            self._recent_history[device_id] = []


# Singleton instance
hub = TelemetryHub()
