import React, { useEffect, useState } from 'react';
import { Play, Pause, RotateCcw, AlertOctagon, WifiOff, Zap, Sliders, CheckCircle2 } from 'lucide-react';
import { api } from '../services/api';
import { SimulatorState } from '../types/telemetry';

interface SimulatorControlPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SimulatorControlPanel: React.FC<SimulatorControlPanelProps> = ({ isOpen, onClose }) => {
  const [simState, setSimState] = useState<SimulatorState | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchStatus = async () => {
    try {
      const state = await api.getSimulatorStatus();
      setSimState(state);
    } catch (_) {}
  };

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
      const interval = setInterval(fetchStatus, 1500);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleControl = async (updates: Partial<{
    running: boolean;
    paused: boolean;
    speed: number;
    pattern: string;
    lidar_degraded: boolean;
    comms_loss: boolean;
  }>) => {
    setLoading(true);
    try {
      const res = await api.controlSimulator(updates);
      setSimState(res.state);
    } catch (e) {
      console.error('Failed to control simulator:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await api.resetSimulator();
      await fetchStatus();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-panelbg border border-purple-800/60 rounded-xl p-4 shadow-2xl flex flex-col gap-4 font-mono text-xs">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-borderline pb-3">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-purple-400" />
          <h2 className="text-sm font-bold text-white uppercase tracking-tight">
            Simulator Engine Controls (Hardware-Free Testing)
          </h2>
          <span className="bg-purple-950/80 border border-purple-700 text-purple-300 text-[10px] px-2 py-0.5 rounded font-bold">
            DEV MODE
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-800/80"
        >
          Hide Panel
        </button>
      </div>

      {/* Main Controls Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {/* Playback State */}
        <div className="bg-[#0B0F17] border border-borderline/80 rounded-lg p-3 flex flex-col gap-2">
          <span className="text-slate-400 text-[11px] font-semibold">ENGINE RUNTIME</span>
          <div className="flex items-center gap-2">
            {!simState?.is_running ? (
              <button
                onClick={() => handleControl({ running: true })}
                disabled={loading}
                className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold transition-colors"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>START SIM</span>
              </button>
            ) : (
              <button
                onClick={() => handleControl({ running: false })}
                disabled={loading}
                className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold transition-colors"
              >
                <span>STOP SIM</span>
              </button>
            )}

            <button
              onClick={() => handleControl({ paused: !simState?.is_paused })}
              disabled={!simState?.is_running || loading}
              className={`p-2 rounded-lg border text-white transition-colors ${
                simState?.is_paused
                  ? 'bg-amber-600 border-amber-500'
                  : 'bg-slate-800 hover:bg-slate-700 border-slate-700'
              }`}
              title="Pause / Resume"
            >
              {simState?.is_paused ? <Play className="w-4 h-4 fill-current" /> : <Pause className="w-4 h-4" />}
            </button>

            <button
              onClick={handleReset}
              disabled={loading}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition-colors"
              title="Reset Filter & Position"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
          <span className="text-[10px] text-slate-500">
            Status: {simState?.is_running ? (simState?.is_paused ? 'PAUSED' : 'STREAMING 50Hz') : 'STOPPED'}
          </span>
        </div>

        {/* Trajectory Pattern Selection */}
        <div className="bg-[#0B0F17] border border-borderline/80 rounded-lg p-3 flex flex-col gap-2">
          <span className="text-slate-400 text-[11px] font-semibold">SYNTHETIC TRAJECTORY</span>
          <select
            value={simState?.pattern ?? 'figure8'}
            onChange={(e) => handleControl({ pattern: e.target.value })}
            className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-white outline-none cursor-pointer"
          >
            <option value="figure8">Figure-8 Patrol (Lissajous)</option>
            <option value="warehouse">Warehouse Perimeter (Rect)</option>
            <option value="zigzag">Search & Rescue (Lawnmower)</option>
            <option value="tunnel">Subterranean Tunnel (Descent)</option>
          </select>
          <span className="text-[10px] text-slate-500">
            Pattern: {simState?.pattern?.toUpperCase()}
          </span>
        </div>

        {/* Speed Multiplier */}
        <div className="bg-[#0B0F17] border border-borderline/80 rounded-lg p-3 flex flex-col gap-2">
          <span className="text-slate-400 text-[11px] font-semibold">MOTION SPEED</span>
          <div className="grid grid-cols-4 gap-1">
            {[0.5, 1.0, 2.0, 5.0].map((s) => (
              <button
                key={s}
                onClick={() => handleControl({ speed: s })}
                className={`py-1.5 rounded text-xs font-bold border transition-colors ${
                  simState?.speed_multiplier === s
                    ? 'bg-blue-600 border-blue-500 text-white'
                    : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
          <span className="text-[10px] text-slate-500">
            Current: {simState?.speed_multiplier ?? 1.0}x realtime
          </span>
        </div>

        {/* Fault Injection Toggles */}
        <div className="bg-[#0B0F17] border border-borderline/80 rounded-lg p-3 flex flex-col gap-2">
          <span className="text-slate-400 text-[11px] font-semibold">FAULT INJECTION</span>
          <div className="flex flex-col gap-1.5">
            <button
              onClick={() => handleControl({ lidar_degraded: !simState?.fault_lidar_degraded })}
              className={`flex items-center justify-between px-2.5 py-1 rounded border text-[11px] transition-colors ${
                simState?.fault_lidar_degraded
                  ? 'bg-amber-950/80 border-amber-600 text-amber-300 font-bold'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800'
              }`}
            >
              <span>Degrade LiDAR</span>
              {simState?.fault_lidar_degraded ? <AlertOctagon className="w-3.5 h-3.5 text-amber-400" /> : <span className="text-[10px]">OFF</span>}
            </button>

            <button
              onClick={() => handleControl({ comms_loss: !simState?.fault_comms_loss })}
              className={`flex items-center justify-between px-2.5 py-1 rounded border text-[11px] transition-colors ${
                simState?.fault_comms_loss
                  ? 'bg-rose-950/80 border-rose-600 text-rose-300 font-bold'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800'
              }`}
            >
              <span>Drop Comms</span>
              {simState?.fault_comms_loss ? <WifiOff className="w-3.5 h-3.5 text-rose-400" /> : <span className="text-[10px]">OFF</span>}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
