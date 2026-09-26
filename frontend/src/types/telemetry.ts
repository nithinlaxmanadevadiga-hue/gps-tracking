export interface ReferencePoint {
  id?: number;
  latitude: number;
  longitude: number;
  altitude: number;
  initial_heading: number;
  name?: string;
  is_active?: boolean;
}

export interface PositionData {
  east: number;
  north: number;
  up: number;
  latitude: number;
  longitude: number;
  altitude: number;
}

export interface VelocityData {
  east: number;
  north: number;
  up: number;
}

export interface OrientationData {
  roll: number;
  pitch: number;
  yaw: number;
}

export interface LocalizationMetadata {
  source: string;
  gps_available: boolean;
  position_accuracy: number;
  status: "GOOD" | "DEGRADED" | "LOST" | string;
  status_reason?: string;
  heading_deg?: number;
  speed_mps?: number;
  horizontal_distance_m?: number;
  distance_3d_m?: number;
  is_simulation?: boolean;
}

export interface HealthSummary {
  overall_quality: "GOOD" | "DEGRADED" | "LOST" | string;
  overall_reason: string;
  subsystems: {
    lidar: "ONLINE" | "DEGRADED" | "OFFLINE";
    imu: "ONLINE" | "DEGRADED" | "OFFLINE";
    velocity: "ONLINE" | "DEGRADED" | "OFFLINE";
    lio: "TRACKING" | "DEGRADED" | "LOST";
    ekf: "RUNNING" | "WARNING" | "FAILED";
    telemetry: "CONNECTED" | "DISCONNECTED";
    gps: string;
  };
  frequencies_hz: {
    imu_hz: number;
    lidar_hz: number;
    lio_hz: number;
    ekf_hz: number;
    telemetry_hz: number;
  };
  last_update_age_ms: number;
}

export interface TelemetryPayload {
  device_id: string;
  timestamp: number;
  reference: ReferencePoint;
  position: PositionData;
  velocity: VelocityData;
  orientation: OrientationData;
  localization: LocalizationMetadata;
  health?: HealthSummary;
  age_ms?: number;
  is_stale?: boolean;
}

export interface Device {
  id: number;
  device_id: string;
  name: string;
  status: "ACTIVE" | "INACTIVE" | "REVOKED";
  is_revoked: boolean;
  registered_at: number;
  last_seen: number;
}

export interface HistoryPoint {
  timestamp: number;
  latitude: number;
  longitude: number;
  altitude: number;
  east: number;
  north: number;
  up: number;
  speed: number;
  heading: number;
  status: string;
  position_accuracy: number;
}

export interface SimulatorState {
  is_running: boolean;
  is_paused: boolean;
  speed_multiplier: number;
  pattern: string;
  fault_lidar_degraded: boolean;
  fault_comms_loss: boolean;
  gps_unavailable: boolean;
  reference: {
    latitude: number;
    longitude: number;
    altitude: number;
    heading: number;
  };
}
