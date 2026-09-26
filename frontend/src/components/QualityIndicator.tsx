import React from 'react';
import { ShieldCheck, AlertTriangle, XCircle, Info } from 'lucide-react';
import { TelemetryPayload } from '../types/telemetry';

interface QualityIndicatorProps {
  telemetry: TelemetryPayload | null;
  ageMs: number;
}

export const QualityIndicator: React.FC<QualityIndicatorProps> = ({ telemetry, ageMs }) => {
  const status = telemetry?.localization?.status ?? 'GOOD';
  const reason = telemetry?.localization?.status_reason ?? 'All estimators nominal';
  const accuracy = telemetry?.localization?.position_accuracy ?? 0.15;
  const isStale = ageMs > 3000;

  let badgeColor = 'bg-emerald-950/70 border-emerald-600 text-emerald-300';
  let Icon = ShieldCheck;
  let label = 'GOOD';

  if (status === 'DEGRADED') {
    badgeColor = 'bg-amber-950/70 border-amber-600 text-amber-300';
    Icon = AlertTriangle;
    label = 'DEGRADED';
  } else if (status === 'LOST') {
    badgeColor = 'bg-rose-950/70 border-rose-600 text-rose-300';
    Icon = XCircle;
    label = 'LOCALIZATION LOST';
  }

  return (
    <div className="bg-panelbg border border-borderline rounded-xl p-4 shadow-xl flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-borderline/80 pb-2.5">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Localization Quality Confidence
        </h3>
        <span className="text-[11px] font-mono text-slate-400">
          Uncertainty: <span className="text-white font-bold">±{accuracy.toFixed(2)} m</span>
        </span>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Quality Status Badge */}
        <div className="flex items-center gap-3">
          <div className={`px-3 py-1.5 rounded-lg border font-mono font-bold text-sm flex items-center gap-2 ${badgeColor}`}>
            <Icon className="w-4 h-4" />
            <span>{label}</span>
          </div>

          <div className="flex flex-col text-xs font-mono">
            <span className="text-slate-300 font-medium">{reason}</span>
            <span className="text-slate-500 text-[11px]">
              {telemetry ? `Last sample: ${new Date(telemetry.timestamp * 1000).toLocaleTimeString()}` : 'Awaiting data'}
            </span>
          </div>
        </div>

        {/* Stale Warning Banner if > 3s */}
        {isStale && (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded bg-rose-900/40 border border-rose-700/60 text-rose-300 text-xs font-mono animate-pulse">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>WARNING: Telemetry is stale ({Math.round(ageMs / 100) / 10}s). Not current!</span>
          </div>
        )}
      </div>
    </div>
  );
};
