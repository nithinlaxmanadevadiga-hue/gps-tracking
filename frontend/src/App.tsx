import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { CoordinateHud } from './components/CoordinateHud';
import { LiveMap } from './components/LiveMap';
import { TrajectoryControls } from './components/TrajectoryControls';
import { SystemHealthPanel } from './components/SystemHealthPanel';
import { QualityIndicator } from './components/QualityIndicator';
import { SimulatorControlPanel } from './components/SimulatorControlPanel';
import { ReferenceConfigModal } from './components/ReferenceConfigModal';
import { DeviceManager } from './components/DeviceManager';
import { ConnectionStatus, TelemetryWebSocket } from './services/websocket';
import { Device, HistoryPoint, ReferencePoint, TelemetryPayload } from './types/telemetry';
import { api } from './services/api';
import { Lock, LogIn, Compass, ShieldAlert } from 'lucide-react';

export const App: React.FC = () => {
  const { isAuthenticated, login, token } = useAuth();

  // Login form state
  const [loginUser, setLoginUser] = useState('operator');
  const [loginPass, setLoginPass] = useState('operator123');
  const [loginError, setLoginError] = useState<string | null>(null);

  // App state
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('unit_001');
  const [referencePoint, setReferencePoint] = useState<ReferencePoint | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryPayload | null>(null);
  const [historyTrail, setHistoryTrail] = useState<HistoryPoint[]>([]);
  const [pointLimit, setPointLimit] = useState<number>(500);
  const [isTrailPaused, setIsTrailPaused] = useState<boolean>(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('DISCONNECTED');
  const [ageMs, setAgeMs] = useState<number>(0);

  // Modals state
  const [isRefModalOpen, setIsRefModalOpen] = useState<boolean>(false);
  const [isDeviceModalOpen, setIsDeviceModalOpen] = useState<boolean>(false);
  const [isSimulatorOpen, setIsSimulatorOpen] = useState<boolean>(true); // open by default in dev

  const wsClientRef = useRef<TelemetryWebSocket | null>(null);
  const lastPacketTimeRef = useRef<number>(Date.now());

  // Handle Login
  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);
    try {
      await login(loginUser, loginPass);
    } catch (err: any) {
      setLoginError(err.message || 'Login failed');
    }
  };

  // Fetch initial devices & reference
  const loadInitialData = async () => {
    try {
      const devs = await api.getDevices();
      setDevices(devs);
      if (devs.length > 0 && !devs.some((d) => d.device_id === selectedDeviceId)) {
        setSelectedDeviceId(devs[0].device_id);
      }

      const ref = await api.getReference();
      setReferencePoint(ref);

      // Load initial history
      const hist = await api.getDeviceHistory(selectedDeviceId, pointLimit);
      setHistoryTrail(hist.points);
    } catch (e) {
      console.error('Failed to load initial ground station data:', e);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      loadInitialData();
    }
  }, [isAuthenticated, selectedDeviceId]);

  // Telemetry freshness ticker (updates every 100ms)
  useEffect(() => {
    const timer = setInterval(() => {
      if (telemetry) {
        setAgeMs(Math.round(Date.now() - telemetry.timestamp * 1000));
      }
    }, 100);
    return () => clearInterval(timer);
  }, [telemetry]);

  // Establish WebSocket connection when authenticated & device selected
  useEffect(() => {
    if (!isAuthenticated || !selectedDeviceId || !token) return;

    if (wsClientRef.current) {
      wsClientRef.current.disconnect();
    }

    const ws = new TelemetryWebSocket(selectedDeviceId, token);
    wsClientRef.current = ws;

    ws.connect(
      (payload) => {
        setTelemetry(payload);
        lastPacketTimeRef.current = Date.now();

        // Append to history trail if not paused
        if (!isTrailPaused) {
          const newPoint: HistoryPoint = {
            timestamp: payload.timestamp,
            latitude: payload.position.latitude,
            longitude: payload.position.longitude,
            altitude: payload.position.altitude,
            east: payload.position.east,
            north: payload.position.north,
            up: payload.position.up,
            speed: payload.localization.speed_mps ?? 0.0,
            heading: payload.localization.heading_deg ?? 0.0,
            status: payload.localization.status,
            position_accuracy: payload.localization.position_accuracy,
          };

          setHistoryTrail((prev) => {
            const next = [...prev, newPoint];
            return next.length > pointLimit ? next.slice(-pointLimit) : next;
          });
        }
      },
      (status) => {
        setConnectionStatus(status);
      }
    );

    return () => {
      ws.disconnect();
    };
  }, [isAuthenticated, selectedDeviceId, token, isTrailPaused, pointLimit]);

  // Trail management
  const handleClearTrail = async () => {
    setHistoryTrail([]);
    try {
      await api.clearDeviceTrail(selectedDeviceId);
    } catch (_) {}
  };

  const handleSaveReference = async (ref: {
    latitude: number;
    longitude: number;
    altitude: number;
    initial_heading: number;
    name?: string;
  }) => {
    const updated = await api.setReference(ref);
    setReferencePoint(updated);
    // Reload history relative to new datum
    const hist = await api.getDeviceHistory(selectedDeviceId, pointLimit);
    setHistoryTrail(hist.points);
  };

  // Render Login Modal if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-[#0B0F17] flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-panelbg border border-borderline rounded-2xl p-6 shadow-2xl flex flex-col gap-5">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-600/20 text-blue-400 rounded-xl border border-blue-500/30">
              <Compass className="w-7 h-7 animate-pulse" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white uppercase tracking-tight">
                Ground Station Console
              </h1>
              <p className="text-xs text-slate-400">
                GPS-Denied Real-Time Tracking & Telemetry
              </p>
            </div>
          </div>

          <div className="bg-rose-950/30 border border-rose-900/40 rounded-lg p-3 text-xs text-rose-300 flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
            <span>
              <strong>Authorized Access Only:</strong> Consenting tracking system. Anonymous access is strictly prohibited.
            </span>
          </div>

          {loginError && (
            <div className="bg-rose-950/60 border border-rose-800 text-rose-300 rounded-lg p-3 text-xs font-mono">
              {loginError}
            </div>
          )}

          <form onSubmit={handleLoginSubmit} className="flex flex-col gap-3 font-mono text-xs">
            <div className="flex flex-col gap-1">
              <label className="text-slate-400 font-sans text-xs font-semibold">Operator Username</label>
              <input
                type="text"
                value={loginUser}
                onChange={(e) => setLoginUser(e.target.value)}
                className="bg-[#0B0F17] border border-borderline rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500"
                required
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-slate-400 font-sans text-xs font-semibold">Password</label>
              <input
                type="password"
                value={loginPass}
                onChange={(e) => setLoginPass(e.target.value)}
                className="bg-[#0B0F17] border border-borderline rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500"
                required
              />
            </div>

            <div className="p-2.5 rounded bg-[#0B0F17] border border-borderline text-[11px] text-slate-400">
              Default operator: <span className="text-white font-bold">operator</span> /{' '}
              <span className="text-white font-bold">operator123</span>
              <br />
              Default admin: <span className="text-white font-bold">admin</span> /{' '}
              <span className="text-white font-bold">admin123</span>
            </div>

            <button
              type="submit"
              className="mt-2 flex items-center justify-center gap-2 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-sans text-sm font-bold transition-colors"
            >
              <LogIn className="w-4 h-4" />
              <span>Authenticate & Enter Console</span>
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B0F17] text-slate-100 flex flex-col">
      {/* Top Navigation */}
      <Navbar
        connectionStatus={connectionStatus}
        devices={devices}
        selectedDeviceId={selectedDeviceId}
        onSelectDevice={setSelectedDeviceId}
        onOpenReferenceModal={() => setIsRefModalOpen(true)}
        onOpenDeviceModal={() => setIsDeviceModalOpen(true)}
        onToggleSimulator={() => setIsSimulatorOpen(!isSimulatorOpen)}
        isSimulatorOpen={isSimulatorOpen}
        isSimulated={telemetry?.localization?.is_simulation ?? true}
      />

      {/* Main Container */}
      <main className="flex-1 p-4 md:p-6 max-w-7xl mx-auto w-full flex flex-col gap-4">
        {/* Simulator Control Panel (Collapsible) */}
        {isSimulatorOpen && (
          <SimulatorControlPanel
            isOpen={isSimulatorOpen}
            onClose={() => setIsSimulatorOpen(false)}
          />
        )}

        {/* Live Coordinate HUD & Datums */}
        <CoordinateHud telemetry={telemetry} ageMs={ageMs} />

        {/* Live Map & Trajectory Trail Controls */}
        <div className="flex flex-col gap-3">
          <LiveMap
            currentTelemetry={telemetry}
            referencePoint={referencePoint}
            historyTrail={historyTrail}
            isTrailPaused={isTrailPaused}
          />

          <TrajectoryControls
            isPaused={isTrailPaused}
            onTogglePause={() => setIsTrailPaused(!isTrailPaused)}
            onClearTrail={handleClearTrail}
            historyTrail={historyTrail}
            pointLimit={pointLimit}
            onChangePointLimit={setPointLimit}
          />
        </div>

        {/* Subsystem Health & Localization Confidence */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <SystemHealthPanel telemetry={telemetry} ageMs={ageMs} />
          </div>
          <div>
            <QualityIndicator telemetry={telemetry} ageMs={ageMs} />
          </div>
        </div>
      </main>

      {/* Modals */}
      <ReferenceConfigModal
        isOpen={isRefModalOpen}
        onClose={() => setIsRefModalOpen(false)}
        currentReference={referencePoint}
        onSaveReference={handleSaveReference}
      />

      <DeviceManager
        isOpen={isDeviceModalOpen}
        onClose={() => setIsDeviceModalOpen(false)}
        devices={devices}
        onRefreshDevices={loadInitialData}
      />
    </div>
  );
};
export default App;
