import pytest
from httpx import AsyncClient, ASGITransport
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.main import app, seed_initial_data


@pytest.mark.asyncio
async def test_auth_and_protected_routes():
    await seed_initial_data()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Test unauthenticated rejection
        res_unauth = await ac.get("/api/devices")
        assert res_unauth.status_code == 401

        # 2. Test successful admin login
        res_login = await ac.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert res_login.status_code == 200
        token_data = res_login.json()
        assert "access_token" in token_data
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Test access to devices with valid token
        res_devices = await ac.get("/api/devices", headers=headers)
        assert res_devices.status_code == 200
        devices = res_devices.json()
        assert any(d["device_id"] == "unit_001" for d in devices)

        # 4. Test reference point access
        res_ref = await ac.get("/api/reference", headers=headers)
        assert res_ref.status_code == 200
        ref_data = res_ref.json()
        assert abs(ref_data["latitude"] - 12.9716) < 1e-4

        # 5. Test health check (public)
        res_health = await ac.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["gps_status"] == "DENIED / NOT USED"
