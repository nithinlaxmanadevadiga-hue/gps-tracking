import React from 'react';
import { Activity, Radio, Cpu, Eye, Zap, ShieldOff, Gauge } from 'lucide-react';
import { HealthSummary, TelemetryPayload } from '../types/telemetry';

interface SystemHealthPanelProps {
  telemetry: TelemetryPayload | null;
  ageMs: number;
}

export const SystemHealthPanel: React.FC<SystemHealthPanelProps> = ({ telemetry, ageMs }) => {
  const health: HealthSummary | undefined = telemetry?.health;

  // Fallbacks if telemetry stream has not attached yet
  const subsystems = health?.subsystems ?? {
    lidar: 'ONLINE',
    imu: 'ONLINE',
    velocity: 'ONLINE',
    lio: 'TRACKING',
    ekf: 'RUNNING',
    telemetry: ageMs < 3000 ? 'CONNECTED' : 'DISCONNECTED',
    gps: 'NOT USED',
  };

  const freqs = health?.frequencies_hz ?? {
    imu_hz: 50.0,
    lidar_hz: 10.0,
    lio_hz: 10.0,
    ekf_hz: 50.0,
    telemetry_hz: 10.0,
  };

  const getSubsystemBadge = (val: string) => {
    switch (val) {
      case 'ONLINE':
      case 'TRACKING':
      case 'RUNNING':
      case 'CONNECTED':
        return 'bg-emerald-950/60 border-emerald-800 text-emerald-400';
      case 'DEGRADED':
      case 'WARNING':
        return 'bg-amber-950/60 border-amber-800 text-amber-400 animate-pulse';
      case 'OFFLINE':
      case 'LOST':
      case 'FAILED':
      case 'DISCONNECTED':
        return 'bg-rose-950/60 border-rose-800 text-rose-400 font-bold';
      default:
        return 'bg-slate-800 border-slate-700 text-slate-300';
    }
  };

  return (
    <div className="bg-panelbg border border-borderline rounded-xl p-4 shadow-xl flex flex-col gap-4">
      {/* Title */}
      <div className="flex items-center justify-between border-b border-borderline/80 pb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-bold text-white uppercase tracking-tight">
            Subsystem Health & Telemetry Metrics
          </h2>
        </div>
        <div className="text-xs font-mono text-slate-400">
          Telemetry Hz: <span className="font-bold text-white">{freqs.telemetry_hz.toFixed(1)}</span>
        </div>
      </div>

      {/* Sensor & Pipeline Subsystems */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 font-mono text-xs">
        {/* LiDAR */}
        <div className="bg-[#0B0F17] border border-borderline/70 rounded-lg p-2.5 flex flex-col items-center justify-center gap-1.5 text-center">
          <span className="text-slate-400 text-[11px]">LiDAR</span>
          <span className={`px-2 py-0.5 rounded border text-[11px] ${getSubsystemBadge(subsystems.lidar)}`}>
            {subsystems.lidar}
          </span>
          <span className="text-[10px] text-slate-500">{freqs.lidar_hz.toFixed(1)} Hz</span>
        </div>

        {/* IMU */}
        <div className="bg-[#0B0F17] border border-borderline/70 rounded-lg p-2.5 flex flex-col items-center justify-center gap-1.5 text-center">
          <span className="text-slate-400 text-[11px]">IMU</span>
          <span className={`px-2 py-0.5 rounded border text-[11px] ${getSubsystemBadge(subsystems.imu)}`}>
            {subsystems.imu}
          </span>
          <span className="text-[10px] text-slate-500">{freqs.imu_hz.toFixed(1)} Hz</span>
        </div>

        {/* Velocity */}
        <div className="bg-[#0B0F17] border border-borderline/70 rounded-lg p-2.5 flex flex-col items-center justify-center gap-1.5 text-center">
          <span className="text-slate-400 text-[11px]">Velocity</span>
          <span className={`px-2 py-0.5 rounded border text-[11px] ${getSubsystemBadge(subsystems.velocity)}`}>
            {subsystems.velocity}
          </span>
          <span className="text-[10px] text-slate-500">10.0 Hz</span>
        </div>

        {/* LIO (FAST-LIO2 / LIO-SAM) */}
        <div className="bg-[#0B0F17] border border-borderline/70 rounded-lg p-2.5 flex flex-col items-center justify-center gap-1.5 text-center">
          <span className="text-slate-400 text-[11px]">LIO</span>
          <span className={`px-2 py-0.5 rounded border text-[11px] ${getSubsystemBadge(subsystems.lio)}`}>
            {subsystems.lio}
          </span>
          <span className="text-[10px] text-slate-500">{freqs.lio_hz.toFixed(1)} Hz</span>
        </div>

        {/* ESEKF */}
        <div className="bg-[#0B0F17] border border-borderline/70 rounded-lg p-2.5 flex flex-col items-center justify-center gap-1.5 text-center">
          <span className="text-slate-400 text-[11px]">ESEKF</span>
          <span className={`px-2 py-0.5 rounded border text-[11px] ${getSubsystemBadge(subsystems.ekf)}`}>
            {subsystems.ekf}
          </span>
          <span className="text-[10px] text-slate-500">{freqs.ekf_hz.toFixed(1)} Hz</span>
        </div>

        {/* Telemetry Transport */}
        <div className="bg-[#0B0F17] border border-borderline/70 rounded-lg p-2.5 flex flex-col items-center justify-center gap-1.5 text-center">
          <span className="text-slate-400 text-[11px]">Telemetry</span>
          <span className={`px-2 py-0.5 rounded border text-[11px] ${getSubsystemBadge(subsystems.telemetry)}`}>
            {subsystems.telemetry}
          </span>
          <span className="text-[10px] text-slate-500">{ageMs} ms</span>
        </div>

        {/* GPS Sensor Status (Explicitly NOT USED) */}
        <div className="bg-rose-950/30 border border-rose-900/40 rounded-lg p-2.5 flex flex-col items-center justify-center gap-1.5 text-center col-span-2 sm:col-span-1">
          <span className="text-rose-300 text-[11px] flex items-center gap-1">
            <ShieldOff className="w-3 h-3 text-rose-400" />
            GPS
          </span>
          <span className="px-2 py-0.5 rounded border border-rose-800/80 bg-rose-950/70 text-rose-300 text-[11px] font-bold">
            NOT USED
          </span>
          <span className="text-[10px] text-rose-400/80">DENIED</span>
        </div>
      </div>
    </div>
  );
};
