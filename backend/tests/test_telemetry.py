import time
import pytest
from httpx import AsyncClient, ASGITransport
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app, seed_initial_data


@pytest.mark.asyncio
async def test_telemetry_flow():
    await seed_initial_data()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Login to get viewer/operator JWT
        login_res = await ac.post("/api/auth/login", json={"username": "operator", "password": "operator123"})
        jwt_token = login_res.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {jwt_token}"}

        # 1. Telemetry ingest without token must fail
        telemetry_payload = {
            "device_id": "unit_001",
            "timestamp": time.time(),
            "reference": {
                "latitude": 12.97160000,
                "longitude": 77.59460000,
                "altitude": 900.0
            },
            "position": {
                "east": 15.24,
                "north": 8.31,
                "up": 2.47,
                "latitude": 12.971675,
                "longitude": 77.594740,
                "altitude": 902.47
            },
            "velocity": {
                "east": 1.23,
                "north": 0.72,
                "up": 0.08
            },
            "orientation": {
                "roll": 0.01,
                "pitch": 0.03,
                "yaw": 1.42
            },
            "localization": {
                "source": "lidar_imu_ekf",
                "gps_available": False,
                "position_accuracy": 0.15,
                "status": "GOOD",
                "heading_deg": 81.3,
                "speed_mps": 1.42,
                "horizontal_distance_m": 17.36,
                "distance_3d_m": 17.53
            }
        }

        res_bad_ingest = await ac.post("/api/telemetry", json=telemetry_payload)
        assert res_bad_ingest.status_code == 401

        # 2. Ingest with valid device token
        device_headers = {"Authorization": "Bearer dev-device-token-secret"}
        res_ingest = await ac.post("/api/telemetry", json=telemetry_payload, headers=device_headers)
        assert res_ingest.status_code == 201

        # 3. Retrieve latest device position via REST
        res_pos = await ac.get("/api/devices/unit_001/position", headers=user_headers)
        assert res_pos.status_code == 200
        pos_data = res_pos.json()
        assert abs(pos_data["position"]["east"] - 15.24) < 1e-3
        assert pos_data["localization"]["gps_available"] is False

        # 4. Retrieve device history trail
        res_hist = await ac.get("/api/devices/unit_001/history", headers=user_headers)
        assert res_hist.status_code == 200
        hist_data = res_hist.json()
        assert hist_data["count"] >= 1
        assert abs(hist_data["points"][-1]["east"] - 15.24) < 1e-3
