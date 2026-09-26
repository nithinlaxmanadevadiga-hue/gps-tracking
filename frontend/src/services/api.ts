import { Device, HistoryPoint, ReferencePoint, SimulatorState, TelemetryPayload } from '../types/telemetry';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
}

export const api = {
  // Authentication
  async login(username: string, password: string): Promise<{ access_token: string; role: string; username: string }> {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Login failed');
    }
    return res.json();
  },

  async getMe() {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Not authenticated');
    return res.json();
  },

  // Devices
  async getDevices(): Promise<Device[]> {
    const res = await fetch(`${API_BASE}/devices`, {
      headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Failed to fetch devices');
    return res.json();
  },

  async registerDevice(deviceId: string, name: string, token?: string): Promise<Device> {
    const res = await fetch(`${API_BASE}/devices`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ device_id: deviceId, name, token })
    });
    if (!res.ok) throw new Error('Failed to register device');
    return res.json();
  },

  async revokeDevice(deviceId: string): Promise<Device> {
    const res = await fetch(`${API_BASE}/devices/${deviceId}/revoke`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Failed to revoke device');
    return res.json();
  },

  // Reference Point
  async getReference(): Promise<ReferencePoint> {
    const res = await fetch(`${API_BASE}/reference`, {
      headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Failed to fetch reference point');
    return res.json();
  },

  async setReference(ref: { latitude: number; longitude: number; altitude: number; initial_heading: number; name?: string }): Promise<ReferencePoint> {
    const res = await fetch(`${API_BASE}/reference`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(ref)
    });
    if (!res.ok) throw new Error('Failed to update reference point');
    return res.json();
  },

  // Telemetry Position & History
  async getDevicePosition(deviceId: string): Promise<TelemetryPayload> {
    const res = await fetch(`${API_BASE}/devices/${deviceId}/position`, {
      headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Failed to fetch position');
    return res.json();
  },

  async getDeviceHistory(deviceId: string, limit: number = 500): Promise<{ device_id: string; count: number; points: HistoryPoint[] }> {
    const res = await fetch(`${API_BASE}/devices/${deviceId}/history?limit=${limit}`, {
      headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Failed to fetch history');
    return res.json();
  },

  async clearDeviceTrail(deviceId: string): Promise<void> {
    await fetch(`${API_BASE}/devices/${deviceId}/clear-trail`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
  },

  // Simulator
  async getSimulatorStatus(): Promise<SimulatorState> {
    const res = await fetch(`${API_BASE}/simulator/status`, {
      headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error('Failed to fetch simulator status');
    return res.json();
  },

  async controlSimulator(controls: {
    running?: boolean;
    paused?: boolean;
    speed?: number;
    pattern?: string;
    lidar_degraded?: boolean;
    comms_loss?: boolean;
  }): Promise<{ status: string; state: SimulatorState }> {
    const res = await fetch(`${API_BASE}/simulator/control`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(controls)
    });
    if (!res.ok) throw new Error('Failed to control simulator');
    return res.json();
  },

  async resetSimulator(): Promise<void> {
    await fetch(`${API_BASE}/simulator/reset`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
  }
};
