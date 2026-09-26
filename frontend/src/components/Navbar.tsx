import React from 'react';
import { Radio, ShieldAlert, Cpu, Settings, Smartphone, Sliders, LogOut, Navigation } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { ConnectionStatus } from '../services/websocket';
import { Device } from '../types/telemetry';

interface NavbarProps {
  connectionStatus: ConnectionStatus;
  devices: Device[];
  selectedDeviceId: string;
  onSelectDevice: (id: string) => void;
  onOpenReferenceModal: () => void;
  onOpenDeviceModal: () => void;
  onToggleSimulator: () => void;
  isSimulatorOpen: boolean;
  isSimulated: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  connectionStatus,
  devices,
  selectedDeviceId,
  onSelectDevice,
  onOpenReferenceModal,
  onOpenDeviceModal,
  onToggleSimulator,
  isSimulatorOpen,
  isSimulated,
}) => {
  const { username, role, logout } = useAuth();

  return (
    <header className="bg-panelbg border-b border-borderline px-4 py-3 sticky top-0 z-30 shadow-lg">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        {/* Title and Branding */}
        <div className="flex items-center gap-3">
          <div className="bg-blue-600/20 text-blue-400 p-2 rounded-lg border border-blue-500/30">
            <Navigation className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-white uppercase">
                GPS-Denied Localization & Tracking
              </h1>
              {isSimulated && (
                <span className="bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs px-2 py-0.5 rounded font-mono font-semibold">
                  SIMULATION
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              LiDAR-Inertial Odometry + 15-State Error-State EKF + WGS-84 Telemetry
            </p>
          </div>
        </div>

        {/* Status Indicators Pill Group */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Connection Status */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#0B0F17] border border-borderline text-xs font-mono">
            <Radio
              className={`w-3.5 h-3.5 ${
                connectionStatus === 'CONNECTED'
                  ? 'text-emerald-400 animate-pulse'
                  : connectionStatus === 'CONNECTING'
                  ? 'text-amber-400 animate-spin'
                  : 'text-rose-500'
              }`}
            />
            <span className="text-slate-400">CONN:</span>
            <span
              className={`font-semibold ${
                connectionStatus === 'CONNECTED'
                  ? 'text-emerald-400'
                  : connectionStatus === 'CONNECTING'
                  ? 'text-amber-400'
                  : 'text-rose-400'
              }`}
            >
              {connectionStatus === 'CONNECTED' ? 'ONLINE' : connectionStatus}
            </span>
          </div>

          {/* GPS Status - Mandated Section 9 & 20 */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-rose-950/40 border border-rose-800/50 text-xs font-mono">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
            <span className="text-slate-400">GPS:</span>
            <span className="font-bold text-rose-300">DENIED / NOT USED</span>
          </div>

          {/* Localization Method */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#0B0F17] border border-borderline text-xs font-mono">
            <Cpu className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-slate-400">ESTIMATOR:</span>
            <span className="font-semibold text-blue-300">FAST-LIO + ESEKF</span>
          </div>

          {/* Device Selector */}
          <div className="flex items-center bg-[#0B0F17] border border-borderline rounded text-xs">
            <span className="px-2 py-1 text-slate-400 border-r border-borderline font-mono">UNIT:</span>
            <select
              value={selectedDeviceId}
              onChange={(e) => onSelectDevice(e.target.value)}
              className="bg-transparent text-white px-2 py-1 outline-none cursor-pointer font-mono"
            >
              {devices.map((d) => (
                <option key={d.device_id} value={d.device_id} className="bg-panelbg">
                  {d.name} ({d.device_id})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Controls and User Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={onToggleSimulator}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors border ${
              isSimulatorOpen
                ? 'bg-purple-600 border-purple-500 text-white'
                : 'bg-purple-950/40 border-purple-800/50 text-purple-300 hover:bg-purple-900/40'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            Simulator
          </button>

          <button
            onClick={onOpenReferenceModal}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium transition-colors"
            title="Configure Reference Origin"
          >
            <Settings className="w-3.5 h-3.5 text-slate-400" />
            Reference
          </button>

          <button
            onClick={onOpenDeviceModal}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-medium transition-colors"
            title="Manage Authorized Units"
          >
            <Smartphone className="w-3.5 h-3.5 text-slate-400" />
            Devices
          </button>

          {/* User profile & logout */}
          <div className="flex items-center gap-2 pl-2 border-l border-borderline">
            <span className="text-xs text-slate-400 hidden xl:inline font-mono">
              {username} <span className="text-blue-400 font-semibold">({role})</span>
            </span>
            <button
              onClick={logout}
              className="p-1.5 rounded text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
