import React, { useState } from 'react';
import { X, Save, MapPin, Compass, ArrowRight } from 'lucide-react';
import { ReferencePoint } from '../types/telemetry';

interface ReferenceConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentReference: ReferencePoint | null;
  onSaveReference: (ref: {
    latitude: number;
    longitude: number;
    altitude: number;
    initial_heading: number;
    name?: string;
  }) => Promise<void>;
}

export const ReferenceConfigModal: React.FC<ReferenceConfigModalProps> = ({
  isOpen,
  onClose,
  currentReference,
  onSaveReference,
}) => {
  const [lat, setLat] = useState<string>(currentReference?.latitude.toFixed(8) ?? '12.97160000');
  const [lon, setLon] = useState<string>(currentReference?.longitude.toFixed(8) ?? '77.59460000');
  const [alt, setAlt] = useState<string>(currentReference?.altitude.toFixed(2) ?? '900.00');
  const [heading, setHeading] = useState<string>(currentReference?.initial_heading.toFixed(1) ?? '0.0');
  const [name, setName] = useState<string>(currentReference?.name ?? 'Ground Station Datum');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await onSaveReference({
        latitude: parseFloat(lat),
        longitude: parseFloat(lon),
        altitude: parseFloat(alt),
        initial_heading: parseFloat(heading),
        name,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to update reference point');
    } finally {
      setLoading(false);
    }
  };

  const applyPreset = (presetName: string, pLat: number, pLon: number, pAlt: number, pHead: number) => {
    setName(presetName);
    setLat(pLat.toFixed(8));
    setLon(pLon.toFixed(8));
    setAlt(pAlt.toFixed(2));
    setHeading(pHead.toFixed(1));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-panelbg border border-borderline rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-5 py-4 border-b border-borderline flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30">
              <MapPin className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white uppercase tracking-tight">
                Reference Point Configuration
              </h2>
              <p className="text-xs text-slate-400">
                Defines local tangent plane datum (E=0, N=0, U=0)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-5 flex flex-col gap-4 font-mono text-xs">
          {error && (
            <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300">
              {error}
            </div>
          )}

          {/* Quick Presets */}
          <div>
            <span className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold block mb-2 font-sans">
              Operational Presets
            </span>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => applyPreset('Field Ops Base (Bengaluru)', 12.9716, 77.5946, 900.0, 0.0)}
                className="p-2 text-left rounded bg-[#0B0F17] hover:bg-slate-800/80 border border-borderline text-[11px] text-slate-300 transition-colors"
              >
                <div className="font-bold text-blue-400">Bengaluru Base</div>
                <div className="text-[10px] text-slate-500">12.9716, 77.5946</div>
              </button>
              <button
                type="button"
                onClick={() => applyPreset('Underground Mine Portal', 39.7392, -104.9903, 1609.0, 90.0)}
                className="p-2 text-left rounded bg-[#0B0F17] hover:bg-slate-800/80 border border-borderline text-[11px] text-slate-300 transition-colors"
              >
                <div className="font-bold text-blue-400">Mine Shaft Portal</div>
                <div className="text-[10px] text-slate-500">39.7392, -104.9903</div>
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-slate-400 font-sans text-xs font-semibold">Datum Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="bg-[#0B0F17] border border-borderline rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500 font-sans"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-slate-400 font-sans text-xs font-semibold">Latitude (WGS-84)</label>
              <input
                type="number"
                step="0.00000001"
                value={lat}
                onChange={(e) => setLat(e.target.value)}
                className="bg-[#0B0F17] border border-borderline rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500"
                required
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-slate-400 font-sans text-xs font-semibold">Longitude (WGS-84)</label>
              <input
                type="number"
                step="0.00000001"
                value={lon}
                onChange={(e) => setLon(e.target.value)}
                className="bg-[#0B0F17] border border-borderline rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-slate-400 font-sans text-xs font-semibold">Altitude (meters)</label>
              <input
                type="number"
                step="0.01"
                value={alt}
                onChange={(e) => setAlt(e.target.value)}
                className="bg-[#0B0F17] border border-borderline rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500"
                required
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-slate-400 font-sans text-xs font-semibold">Initial Heading (° North)</label>
              <input
                type="number"
                step="0.1"
                value={heading}
                onChange={(e) => setHeading(e.target.value)}
                className="bg-[#0B0F17] border border-borderline rounded-lg px-3 py-2 text-white outline-none focus:border-blue-500"
                required
              />
            </div>
          </div>

          <div className="p-3 rounded-lg bg-blue-950/30 border border-blue-900/50 text-[11px] text-blue-300">
            <strong>Coordinate Invariant:</strong> The reference coordinate maps directly to East=0, North=0, Up=0. All subsequent LiDAR/IMU relative motion vectors are evaluated in this local tangent coordinate system.
          </div>

          {/* Footer Buttons */}
          <div className="flex items-center justify-end gap-2 pt-2 border-t border-borderline">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-sans text-xs font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-sans text-xs font-bold transition-colors disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>{loading ? 'Applying...' : 'Apply Reference'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
