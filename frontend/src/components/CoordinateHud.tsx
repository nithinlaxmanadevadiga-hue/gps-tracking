import React from 'react';
import { Compass, Gauge, Clock, Target, AlertTriangle, ArrowUpRight, Crosshair } from 'lucide-react';
import { TelemetryPayload } from '../types/telemetry';

interface CoordinateHudProps {
  telemetry: TelemetryPayload | null;
  ageMs: number;
}

export const CoordinateHud: React.FC<CoordinateHudProps> = ({ telemetry, ageMs }) => {
  if (!telemetry) {
    return (
      <div className="bg-panelbg border border-borderline rounded-xl p-4 shadow-lg text-center text-slate-400 font-mono text-sm">
        Waiting for initial localization telemetry stream...
      </div>
    );
  }

  const { position, velocity, localization, reference } = telemetry;
  const isStale = ageMs > 2500;
  const isCriticalStale = ageMs > 5000;

  const horizDist = localization.horizontal_distance_m ?? Math.hypot(position.east, position.north);
  const dist3D = localization.distance_3d_m ?? Math.sqrt(position.east ** 2 + position.north ** 2 + position.up ** 2);
  const speed = localization.speed_mps ?? Math.sqrt(velocity.east ** 2 + velocity.north ** 2 + velocity.up ** 2);
  const heading = localization.heading_deg ?? 0.0;
  const accuracy = localization.position_accuracy ?? 0.15;

  return (
    <div className="bg-panelbg border border-borderline rounded-xl p-4 shadow-xl flex flex-col gap-4">
      {/* Header and Telemetry Freshness */}
      <div className="flex items-center justify-between border-b border-borderline/80 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Position Source</span>
            <span className="text-xs font-mono font-bold text-blue-400 bg-blue-950/50 border border-blue-800/40 px-2 py-0.5 rounded">
              LiDAR-Inertial Odometry + ESEKF
            </span>
          </div>
          <h2 className="text-sm font-bold text-white uppercase tracking-tight mt-0.5">
            Estimated Position (GPS-Denied)
          </h2>
        </div>

        {/* Telemetry Age Pill */}
        <div className="flex items-center gap-2 font-mono">
          <div
            className={`flex items-center gap-1.5 px-3 py-1 rounded text-xs border ${
              isCriticalStale
                ? 'bg-rose-950/60 border-rose-800 text-rose-300 animate-pulse'
                : isStale
                ? 'bg-amber-950/50 border-amber-800 text-amber-300'
                : 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>
              {isCriticalStale ? 'STALE TELEMETRY' : 'LAST UPDATE'}:{' '}
              <span className="font-bold">{ageMs < 1000 ? `${ageMs} ms ago` : `${(ageMs / 1000).toFixed(1)} s ago`}</span>
            </span>
          </div>
        </div>
      </div>

      {/* Main Coordinates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* 1. WGS-84 Geodetic Position */}
        <div className="bg-[#0B0F17] border border-borderline/70 rounded-lg p-3 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-mono">
            <span className="flex items-center gap-1">
              <Crosshair className="w-3.5 h-3.5 text-blue-400" />
              GEODETIC (WGS-84)
            </span>
            <span className="text-[10px] text-blue-400/80 font-bold">8 DECIMALS</span>
          </div>
          <div className="space-y-1 font-mono text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400 text-xs">LAT:</span>
              <span className="text-emerald-400 font-bold">{position.latitude.toFixed(8)}°</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 text-xs">LON:</span>
              <span className="text-emerald-400 font-bold">{position.longitude.toFixed(8)}°</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 text-xs">ALT:</span>
              <span className="text-white font-semibold">{position.altitude.toFixed(2)} m</span>
            </div>
          </div>
        </div>

        {/* 2. Local ENU Coordinate Offset */}
        <div className="bg-[#0B0F17] border border-borderline/70 rounded-lg p-3 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-mono">
            <span className="flex items-center gap-1">
              <ArrowUpRight className="w-3.5 h-3.5 text-cyan-400" />
              LOCAL ENU FRAME
            </span>
            <span className="text-[10px] text-slate-500">REL TO DATUM</span>
          </div>
          <div className="space-y-1 font-mono text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400 text-xs">EAST:</span>
              <span className="text-cyan-300 font-semibold">{position.east.toFixed(2)} m</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 text-xs">NORTH:</span>
              <span className="text-cyan-300 font-semibold">{position.north.toFixed(2)} m</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 text-xs">UP:</span>
              <span className="text-cyan-300 font-semibold">{position.up.toFixed(2)} m</span>
            </div>
          </div>
        </div>

        {/* 3. Dynamics: Speed & Heading */}
        <div className="bg-[#0B0F17] border border-borderline/70 rounded-lg p-3 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-mono">
            <span className="flex items-center gap-1">
              <Gauge className="w-3.5 h-3.5 text-amber-400" />
              MOTION DYNAMICS
            </span>
            <span className="text-[10px] text-amber-400/80">INERTIAL</span>
          </div>
          <div className="space-y-1 font-mono text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400 text-xs">SPEED:</span>
              <span className="text-white font-bold">{speed.toFixed(2)} m/s</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 text-xs">HEADING:</span>
              <span className="text-amber-300 font-semibold flex items-center gap-1">
                <Compass className="w-3.5 h-3.5 text-amber-400" />
                {heading.toFixed(1)}°
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 text-xs">ACCURACY:</span>
              <span className="text-emerald-400 font-semibold">± {accuracy.toFixed(2)} m</span>
            </div>
          </div>
        </div>

        {/* 4. Distance from Reference Datum */}
        <div className="bg-[#0B0F17] border border-borderline/70 rounded-lg p-3 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-mono">
            <span className="flex items-center gap-1">
              <Target className="w-3.5 h-3.5 text-purple-400" />
              DATUM DISPLACEMENT
            </span>
            <span className="text-[10px] text-purple-400/80">ORIGIN</span>
          </div>
          <div className="space-y-1 font-mono text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400 text-xs">HORIZONTAL:</span>
              <span className="text-purple-300 font-bold">{horizDist.toFixed(2)} m</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 text-xs">3D DISTANCE:</span>
              <span className="text-purple-300 font-semibold">{dist3D.toFixed(2)} m</span>
            </div>
            <div className="flex justify-between text-[11px] text-slate-500 pt-0.5">
              <span>DATUM:</span>
              <span className="truncate max-w-[130px]" title={`${reference.latitude.toFixed(6)}, ${reference.longitude.toFixed(6)}`}>
                {reference.latitude.toFixed(6)}, {reference.longitude.toFixed(6)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
