import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "GPS-Denied Real-Time Localization System"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-jwt-signing-key-for-gps-denied-localization-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours

    # Database: Supports SQLite (aiosqlite) or PostgreSQL (asyncpg)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./gps_tracking.db"
    )

    # Telemetry
    DEFAULT_DEVICE_TOKEN: str = os.getenv("DEFAULT_DEVICE_TOKEN", "dev-device-token-secret")
    DATA_RETENTION_DAYS: int = 30
    STALE_TELEMETRY_THRESHOLD_SEC: float = 3.0

    # CORS
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    # MQTT Bridge
    MQTT_ENABLE: bool = os.getenv("MQTT_ENABLE", "false").lower() == "true"
    MQTT_BROKER: str = os.getenv("MQTT_BROKER", "localhost")
    MQTT_PORT: int = int(os.getenv("MQTT_PORT", "1883"))
    MQTT_TOPIC: str = os.getenv("MQTT_TOPIC", "telemetry/#")

    model_config = SettingsConfigDict(case_sensitive=True)


settings = Settings()
