from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "operator"


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    created_at: float


# Device Schemas
class DeviceCreate(BaseModel):
    device_id: str
    name: str
    token: Optional[str] = None


class DeviceResponse(BaseModel):
    id: int
    device_id: str
    name: str
    status: str
    is_revoked: bool
    registered_at: float
    last_seen: float


# Reference Point Schemas
class ReferencePointBase(BaseModel):
    latitude: float = Field(..., description="WGS-84 Latitude in degrees")
    longitude: float = Field(..., description="WGS-84 Longitude in degrees")
    altitude: float = Field(..., description="Altitude in meters")
    initial_heading: float = Field(0.0, description="Initial heading degrees (0=North)")
    name: Optional[str] = "Primary Reference"


class ReferencePointCreate(ReferencePointBase):
    pass


class ReferencePointResponse(ReferencePointBase):
    id: int
    is_active: bool
    created_at: float


# Telemetry Ingestion Schemas (Section 8 Standard)
class PositionData(BaseModel):
    east: float
    north: float
    up: float
    latitude: float
    longitude: float
    altitude: float


class VelocityData(BaseModel):
    east: float
    north: float
    up: float


class OrientationData(BaseModel):
    roll: float
    pitch: float
    yaw: float


class ReferenceData(BaseModel):
    latitude: float
    longitude: float
    altitude: float


class LocalizationMetadata(BaseModel):
    source: str = "lidar_imu_ekf"
    gps_available: bool = False
    position_accuracy: float = 0.15
    status: Optional[str] = "GOOD"
    status_reason: Optional[str] = "Nominal"
    heading_deg: Optional[float] = 0.0
    speed_mps: Optional[float] = 0.0
    horizontal_distance_m: Optional[float] = 0.0
    distance_3d_m: Optional[float] = 0.0
    is_simulation: Optional[bool] = False


class TelemetryPayload(BaseModel):
    device_id: str
    timestamp: float
    reference: ReferenceData
    position: PositionData
    velocity: VelocityData
    orientation: OrientationData
    localization: LocalizationMetadata
    health: Optional[Dict[str, Any]] = None


# Current Position Response
class DevicePositionResponse(BaseModel):
    device_id: str
    timestamp: float
    reference: ReferenceData
    position: PositionData
    velocity: VelocityData
    orientation: OrientationData
    localization: LocalizationMetadata
    health: Optional[Dict[str, Any]] = None
    age_ms: float
    is_stale: bool


# History Trajectory Response
class HistoryPoint(BaseModel):
    timestamp: float
    latitude: float
    longitude: float
    altitude: float
    east: float
    north: float
    up: float
    speed: float
    heading: float
    status: str
    position_accuracy: float


class HistoryResponse(BaseModel):
    device_id: str
    count: int
    points: List[HistoryPoint]


# Simulator Controls
class SimulatorControlRequest(BaseModel):
    running: Optional[bool] = None
    paused: Optional[bool] = None
    speed: Optional[float] = None
    pattern: Optional[str] = None
    lidar_degraded: Optional[bool] = None
    comms_loss: Optional[bool] = None
