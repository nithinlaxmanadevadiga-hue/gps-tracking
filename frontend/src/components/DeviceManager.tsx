import React, { useState } from 'react';
import { X, Smartphone, ShieldCheck, ShieldAlert, Plus, Ban, RotateCcw } from 'lucide-react';
import { Device } from '../types/telemetry';
import { api } from '../services/api';

interface DeviceManagerProps {
  isOpen: boolean;
  onClose: () => void;
  devices: Device[];
  onRefreshDevices: () => Promise<void>;
}

export const DeviceManager: React.FC<DeviceManagerProps> = ({
  isOpen,
  onClose,
  devices,
  onRefreshDevices,
}) => {
  const [newDeviceId, setNewDeviceId] = useState('');
  const [newDeviceName, setNewDeviceName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDeviceId || !newDeviceName) return;
    setLoading(true);
    setError(null);
    try {
      await api.registerDevice(newDeviceId, newDeviceName);
      setNewDeviceId('');
      setNewDeviceName('');
      await onRefreshDevices();
    } catch (err: any) {
      setError(err.message || 'Failed to register unit');
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (id: string) => {
    setLoading(true);
    try {
      await api.revokeDevice(id);
      await onRefreshDevices();
    } catch (err: any) {
      setError(err.message || 'Failed to revoke unit');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-panelbg border border-borderline rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-5 py-4 border-b border-borderline flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-600/20 text-emerald-400 border border-emerald-500/30">
              <Smartphone className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white uppercase tracking-tight">
                Authorized Tracking Devices
              </h2>
              <p className="text-xs text-slate-400">
                Authorized Units & Access Revocation (Section 13)
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
        <div className="p-5 flex flex-col gap-5 overflow-y-auto">
          {error && (
            <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-300 font-mono text-xs">
              {error}
            </div>
          )}

          {/* Register New Unit Form */}
          <form onSubmit={handleRegister} className="bg-[#0B0F17] border border-borderline rounded-xl p-4 flex flex-col gap-3 font-mono text-xs">
            <span className="text-slate-300 font-bold uppercase tracking-wider font-sans">
              Register Consenting Unit
            </span>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                placeholder="Unit ID (e.g. unit_002)"
                value={newDeviceId}
                onChange={(e) => setNewDeviceId(e.target.value)}
                className="bg-panelbg border border-borderline rounded px-3 py-2 text-white outline-none focus:border-blue-500"
                required
              />
              <input
                type="text"
                placeholder="Unit Display Name"
                value={newDeviceName}
                onChange={(e) => setNewDeviceName(e.target.value)}
                className="bg-panelbg border border-borderline rounded px-3 py-2 text-white outline-none focus:border-blue-500"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center justify-center gap-1.5 py-2 rounded bg-blue-600 hover:bg-blue-500 text-white font-sans font-bold transition-colors disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              <span>Register Unit</span>
            </button>
          </form>

          {/* Device List */}
          <div className="flex flex-col gap-2 font-mono text-xs">
            <span className="text-slate-400 font-semibold font-sans uppercase text-[11px]">
              Active & Revoked Devices ({devices.length})
            </span>
            <div className="flex flex-col gap-2">
              {devices.map((d) => (
                <div
                  key={d.device_id}
                  className="bg-[#0B0F17] border border-borderline/80 rounded-lg p-3 flex items-center justify-between"
                >
                  <div className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white text-sm">{d.name}</span>
                      <span className="text-slate-400">[{d.device_id}]</span>
                      {d.is_revoked ? (
                        <span className="px-2 py-0.5 rounded bg-rose-950/70 border border-rose-800 text-rose-300 text-[10px] font-bold">
                          REVOKED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-emerald-950/70 border border-emerald-800 text-emerald-300 text-[10px] font-bold">
                          ACTIVE
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-slate-500">
                      Last seen:{' '}
                      {d.last_seen > 0 ? new Date(d.last_seen * 1000).toLocaleString() : 'Never'}
                    </span>
                  </div>

                  <div>
                    {!d.is_revoked ? (
                      <button
                        onClick={() => handleRevoke(d.device_id)}
                        disabled={loading}
                        className="flex items-center gap-1 px-3 py-1.5 rounded bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 text-xs font-sans font-medium transition-colors"
                        title="Immediately revoke authorization"
                      >
                        <Ban className="w-3.5 h-3.5" />
                        <span>Revoke</span>
                      </button>
                    ) : (
                      <span className="text-xs text-rose-400 font-sans">Blocked</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
