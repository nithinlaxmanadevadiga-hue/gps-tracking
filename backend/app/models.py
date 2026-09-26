import time
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, Index, DateTime
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(32), default="operator", nullable=False) # admin, operator, viewer
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(Float, default=time.time, nullable=False)


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False)
    token_hash = Column(String(256), nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False) # ACTIVE, INACTIVE, REVOKED
    is_revoked = Column(Boolean, default=False, nullable=False)
    registered_at = Column(Float, default=time.time, nullable=False)
    last_seen = Column(Float, default=0.0, nullable=False)


class ReferencePoint(Base):
    __tablename__ = "reference_points"

    id = Column(Integer, primary_key=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=False)
    initial_heading = Column(Float, default=0.0, nullable=False)
    name = Column(String(128), default="Default Reference", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(Float, default=time.time, nullable=False)


class TelemetryRecord(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), nullable=False, index=True)
    timestamp = Column(Float, nullable=False, index=True)

    # Geodetic coordinates
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=False)

    # Local ENU coordinates
    east = Column(Float, nullable=False)
    north = Column(Float, nullable=False)
    up = Column(Float, nullable=False)

    # Velocities (m/s)
    velocity_east = Column(Float, nullable=False)
    velocity_north = Column(Float, nullable=False)
    velocity_up = Column(Float, nullable=False)

    # Attitude & Quality
    heading = Column(Float, default=0.0, nullable=False)
    position_accuracy = Column(Float, default=0.0, nullable=False)
    localization_status = Column(String(32), default="GOOD", nullable=False)

    # Full JSON payload
    raw_json = Column(Text, nullable=True)

    __table_args__ = (
        Index("idx_device_timestamp", "device_id", "timestamp"),
    )


class LocalizationEvent(Base):
    __tablename__ = "localization_events"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), index=True, nullable=False)
    event_type = Column(String(64), nullable=False) # DEGRADATION, JUMP_REJECTED, TIMEOUT, LOST
    severity = Column(String(32), nullable=False)   # INFO, WARNING, CRITICAL
    description = Column(String(512), nullable=False)
    timestamp = Column(Float, default=time.time, nullable=False, index=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    action = Column(String(128), nullable=False)
    details = Column(String(512), nullable=True)
    ip_address = Column(String(64), nullable=True)
    timestamp = Column(Float, default=time.time, nullable=False, index=True)
