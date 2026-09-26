import React from 'react';
import { Play, Pause, Trash2, Download, FileText, History } from 'lucide-react';
import { HistoryPoint } from '../types/telemetry';

interface TrajectoryControlsProps {
  isPaused: boolean;
  onTogglePause: () => void;
  onClearTrail: () => void;
  historyTrail: HistoryPoint[];
  pointLimit: number;
  onChangePointLimit: (limit: number) => void;
}

export const TrajectoryControls: React.FC<TrajectoryControlsProps> = ({
  isPaused,
  onTogglePause,
  onClearTrail,
  historyTrail,
  pointLimit,
  onChangePointLimit,
}) => {
  // Export as GeoJSON LineString
  const exportGeoJSON = () => {
    const geojson = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: {
            name: 'GPS-Denied Localization Trail',
            exported_at: new Date().toISOString(),
            total_points: historyTrail.length,
          },
          geometry: {
            type: 'LineString',
            coordinates: historyTrail.map((p) => [p.longitude, p.latitude, p.altitude]),
          },
        },
      ],
    };

    const blob = new Blob([JSON.stringify(geojson, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trajectory_${Date.now()}.geojson`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Export as CSV
  const exportCSV = () => {
    const headers = ['timestamp', 'latitude', 'longitude', 'altitude', 'east', 'north', 'up', 'speed', 'heading', 'accuracy', 'status'];
    const rows = historyTrail.map((p) => [
      p.timestamp,
      p.latitude.toFixed(8),
      p.longitude.toFixed(8),
      p.altitude.toFixed(3),
      p.east.toFixed(3),
      p.north.toFixed(3),
      p.up.toFixed(3),
      p.speed.toFixed(2),
      p.heading.toFixed(1),
      p.position_accuracy.toFixed(3),
      p.status,
    ]);

    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trajectory_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-panelbg border border-borderline rounded-xl p-3 shadow-lg flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
      {/* Left: Trail Status & Point Count */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-slate-300">
          <History className="w-4 h-4 text-blue-400" />
          <span>TRAIL POINTS:</span>
          <span className="font-bold text-white bg-[#0B0F17] px-2 py-0.5 rounded border border-borderline">
            {historyTrail.length}
          </span>
        </div>

        {/* Limit selector */}
        <div className="flex items-center gap-1.5 text-slate-400">
          <span>MAX:</span>
          <select
            value={pointLimit}
            onChange={(e) => onChangePointLimit(Number(e.target.value))}
            className="bg-[#0B0F17] border border-borderline rounded px-2 py-0.5 text-white outline-none cursor-pointer"
          >
            <option value="100">100</option>
            <option value="250">250</option>
            <option value="500">500</option>
            <option value="1000">1000</option>
          </select>
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {/* Pause / Resume */}
        <button
          onClick={onTogglePause}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded font-medium transition-colors border ${
            isPaused
              ? 'bg-amber-600/90 border-amber-500 text-white'
              : 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-200'
          }`}
          title={isPaused ? 'Resume Trail Logging' : 'Pause Trail Logging'}
        >
          {isPaused ? <Play className="w-3.5 h-3.5 fill-current" /> : <Pause className="w-3.5 h-3.5" />}
          <span>{isPaused ? 'RESUME' : 'PAUSE'}</span>
        </button>

        {/* Clear */}
        <button
          onClick={onClearTrail}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-rose-900/60 border border-slate-700 hover:border-rose-700 text-slate-300 hover:text-rose-200 transition-colors"
          title="Clear Trajectory Trail"
        >
          <Trash2 className="w-3.5 h-3.5 text-rose-400" />
          <span>CLEAR</span>
        </button>

        {/* Export GeoJSON */}
        <button
          onClick={exportGeoJSON}
          disabled={historyTrail.length === 0}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 disabled:opacity-40 transition-colors"
          title="Export GeoJSON LineString"
        >
          <Download className="w-3.5 h-3.5 text-blue-400" />
          <span>GEOJSON</span>
        </button>

        {/* Export CSV */}
        <button
          onClick={exportCSV}
          disabled={historyTrail.length === 0}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 disabled:opacity-40 transition-colors"
          title="Export Raw CSV Table"
        >
          <FileText className="w-3.5 h-3.5 text-emerald-400" />
          <span>CSV</span>
        </button>
      </div>
    </div>
  );
};
