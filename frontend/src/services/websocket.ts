import { TelemetryPayload } from '../types/telemetry';

export type ConnectionStatus = 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED';

export class TelemetryWebSocket {
  private ws: WebSocket | null = null;
  private reconnectTimer: any = null;
  private isExplicitlyClosed = false;
  private onMessageCallback: ((payload: TelemetryPayload) => void) | null = null;
  private onStatusChangeCallback: ((status: ConnectionStatus) => void) | null = null;

  constructor(
    private deviceId: string | null = null,
    private token: string | null = null
  ) {}

  public connect(
    onMessage: (payload: TelemetryPayload) => void,
    onStatusChange?: (status: ConnectionStatus) => void
  ) {
    this.isExplicitlyClosed = false;
    this.onMessageCallback = onMessage;
    if (onStatusChange) this.onStatusChangeCallback = onStatusChange;

    this._setupWebSocket();
  }

  private _setupWebSocket() {
    if (this.ws) {
      try { this.ws.close(); } catch (_) {}
    }

    if (this.onStatusChangeCallback) {
      this.onStatusChangeCallback('CONNECTING');
    }

    let endpoint = this.deviceId ? `/ws/devices/${this.deviceId}` : '/ws/live';
    const token = this.token || localStorage.getItem('access_token') || '';

    let fullUrl: string;
    const configuredWsBase = import.meta.env.VITE_WS_BASE_URL;
    if (configuredWsBase) {
      const cleanBase = configuredWsBase.replace(/\/$/, '');
      fullUrl = `${cleanBase}${endpoint}?token=${encodeURIComponent(token)}`;
    } else {
      const loc = window.location;
      const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = loc.host; // Uses vite proxy in dev or nginx in prod
      fullUrl = `${protocol}//${host}${endpoint}?token=${encodeURIComponent(token)}`;
    }

    try {
      this.ws = new WebSocket(fullUrl);

      this.ws.onopen = () => {
        if (this.onStatusChangeCallback) {
          this.onStatusChangeCallback('CONNECTED');
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const data: TelemetryPayload = JSON.parse(event.data);
          if (this.onMessageCallback) {
            this.onMessageCallback(data);
          }
        } catch (e) {
          console.warn('Failed to parse WebSocket telemetry JSON:', e);
        }
      };

      this.ws.onclose = () => {
        if (this.onStatusChangeCallback) {
          this.onStatusChangeCallback('DISCONNECTED');
        }
        if (!this.isExplicitlyClosed) {
          this._scheduleReconnect();
        }
      };

      this.ws.onerror = () => {
        if (this.onStatusChangeCallback) {
          this.onStatusChangeCallback('DISCONNECTED');
        }
      };
    } catch (e) {
      console.error('WebSocket connection error:', e);
      this._scheduleReconnect();
    }
  }

  private _scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      if (!this.isExplicitlyClosed) {
        this._setupWebSocket();
      }
    }, 2000);
  }

  public disconnect() {
    this.isExplicitlyClosed = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      try { this.ws.close(); } catch (_) {}
      this.ws = null;
    }
    if (this.onStatusChangeCallback) {
      this.onStatusChangeCallback('DISCONNECTED');
    }
  }
}
