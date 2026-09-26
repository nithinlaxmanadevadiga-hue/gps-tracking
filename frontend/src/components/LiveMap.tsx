import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { Layers, Crosshair, MapPin, Eye, Compass, WifiOff } from 'lucide-react';
import { HistoryPoint, ReferencePoint, TelemetryPayload } from '../types/telemetry';

interface LiveMapProps {
  currentTelemetry: TelemetryPayload | null;
  referencePoint: ReferencePoint | null;
  historyTrail: HistoryPoint[];
  isTrailPaused: boolean;
}

export const LiveMap: React.FC<LiveMapProps> = ({
  currentTelemetry,
  referencePoint,
  historyTrail,
  isTrailPaused,
}) => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const leafletMapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);
  const refMarkerRef = useRef<L.Marker | null>(null);
  const accuracyCircleRef = useRef<L.Circle | null>(null);
  const polylineRef = useRef<L.Polyline | null>(null);

  const [useOfflineGrid, setUseOfflineGrid] = useState<boolean>(false);
  const [autoFollow, setAutoFollow] = useState<boolean>(true);
  const [mapTileFailed, setMapTileFailed] = useState<boolean>(false);

  // Initialize Leaflet Map once
  useEffect(() => {
    if (!mapContainerRef.current || leafletMapRef.current) return;

    const initialLat = referencePoint?.latitude ?? 12.9716;
    const initialLon = referencePoint?.longitude ?? 77.5946;

    const map = L.map(mapContainerRef.current, {
      center: [initialLat, initialLon],
      zoom: 19,
      zoomControl: false,
      attributionControl: false,
    });

    // Dark Carto / OpenStreetMap tiles
    const tileLayer = L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png',
      {
        maxZoom: 22,
        subdomains: 'abcd',
      }
    );

    tileLayer.on('tileerror', () => {
      setMapTileFailed(true);
    });

    tileLayer.addTo(map);
    leafletMapRef.current = map;

    return () => {
      map.remove();
      leafletMapRef.current = null;
    };
  }, []);

  // Update Reference Point Marker
  useEffect(() => {
    const map = leafletMapRef.current;
    if (!map || !referencePoint) return;

    const pos: L.LatLngExpression = [referencePoint.latitude, referencePoint.longitude];

    if (!refMarkerRef.current) {
      const icon = L.divIcon({
        className: 'custom-ref-marker',
        html: `
          <div class="relative flex items-center justify-center">
            <div class="w-8 h-8 rounded-full bg-blue-500/20 border-2 border-blue-400 flex items-center justify-center shadow-lg">
              <div class="w-2.5 h-2.5 bg-blue-400 rounded-full"></div>
            </div>
            <div class="absolute -top-7 bg-slate-900/90 text-blue-300 font-mono text-[10px] font-bold px-1.5 py-0.5 rounded border border-blue-800/80 shadow whitespace-nowrap">
              ORIGIN (0,0,0)
            </div>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      refMarkerRef.current = L.marker(pos, { icon }).addTo(map);
      refMarkerRef.current.bindPopup(
        `<div class="font-mono text-xs">
          <strong class="text-blue-400">Reference Origin Datum</strong><br/>
          Lat: ${referencePoint.latitude.toFixed(8)}<br/>
          Lon: ${referencePoint.longitude.toFixed(8)}<br/>
          Alt: ${referencePoint.altitude.toFixed(2)} m<br/>
          ENU: (0.00, 0.00, 0.00)
        </div>`
      );
    } else {
      refMarkerRef.current.setLatLng(pos);
    }
  }, [referencePoint]);

  // Update Real-Time Device Marker, Heading Indicator & Accuracy Circle
  useEffect(() => {
    const map = leafletMapRef.current;
    if (!map || !currentTelemetry) return;

    const lat = currentTelemetry.position.latitude;
    const lon = currentTelemetry.position.longitude;
    const heading = currentTelemetry.localization.heading_deg ?? 0.0;
    const accuracy = currentTelemetry.localization.position_accuracy ?? 0.15;
    const status = currentTelemetry.localization.status ?? 'GOOD';

    const latLng: L.LatLngExpression = [lat, lon];

    // Status colors
    const colorHex = status === 'GOOD' ? '#10B981' : status === 'DEGRADED' ? '#F59E0B' : '#EF4444';
    const bgGlowClass =
      status === 'GOOD'
        ? 'bg-emerald-500/20 border-emerald-400'
        : status === 'DEGRADED'
        ? 'bg-amber-500/20 border-amber-400'
        : 'bg-rose-500/20 border-rose-400';

    // Rotating heading indicator icon
    const iconHtml = `
      <div class="relative flex items-center justify-center" style="width: 44px; height: 44px;">
        <div class="absolute w-10 h-10 rounded-full ${bgGlowClass} border-2 marker-pulse-ring"></div>
        <div class="w-8 h-8 rounded-full bg-slate-900 border-2 border-white shadow-xl flex items-center justify-center relative">
          <!-- Heading direction arrow -->
          <div style="transform: rotate(${heading}deg); transition: transform 0.1s linear;" class="flex items-center justify-center">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="${colorHex}">
              <path d="M12 2L4.5 20.29l.71.71L12 18l6.79 3 .71-.71z" />
            </svg>
          </div>
        </div>
      </div>
    `;

    const icon = L.divIcon({
      className: 'device-heading-marker',
      html: iconHtml,
      iconSize: [44, 44],
      iconAnchor: [22, 22],
    });

    if (!markerRef.current) {
      markerRef.current = L.marker(latLng, { icon, zIndexOffset: 1000 }).addTo(map);
    } else {
      markerRef.current.setLatLng(latLng);
      markerRef.current.setIcon(icon);
    }

    // Dynamic Accuracy Circle
    if (!accuracyCircleRef.current) {
      accuracyCircleRef.current = L.circle(latLng, {
        radius: Math.max(0.2, accuracy),
        color: colorHex,
        fillColor: colorHex,
        fillOpacity: 0.15,
        weight: 1,
        dashArray: '3, 3',
      }).addTo(map);
    } else {
      accuracyCircleRef.current.setLatLng(latLng);
      accuracyCircleRef.current.setRadius(Math.max(0.2, accuracy));
      accuracyCircleRef.current.setStyle({
        color: colorHex,
        fillColor: colorHex,
      });
    }

    // Follow marker if enabled
    if (autoFollow) {
      map.panTo(latLng, { animate: true, duration: 0.2 });
    }
  }, [currentTelemetry, autoFollow]);

  // Update Polyline History Trail
  useEffect(() => {
    const map = leafletMapRef.current;
    if (!map) return;

    if (historyTrail.length < 2) {
      if (polylineRef.current) {
        polylineRef.current.setLatLngs([]);
      }
      return;
    }

    const latLngs: L.LatLngExpression[] = historyTrail.map((p) => [p.latitude, p.longitude]);

    if (!polylineRef.current) {
      polylineRef.current = L.polyline(latLngs, {
        color: '#3B82F6',
        weight: 3.5,
        opacity: 0.85,
        smoothFactor: 1,
      }).addTo(map);
    } else {
      polylineRef.current.setLatLngs(latLngs);
    }
  }, [historyTrail]);

  // Offline Cartesian ENU Canvas Renderer
  useEffect(() => {
    if (!useOfflineGrid || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = (canvas.width = canvas.parentElement?.clientWidth || 800);
    const height = (canvas.height = canvas.parentElement?.clientHeight || 600);

    // Clear background
    ctx.fillStyle = '#0B0F17';
    ctx.fillRect(0, 0, width, height);

    const centerX = width / 2;
    const centerY = height / 2;
    const scale = 8.0; // pixels per meter

    // Draw Grid Lines (every 5m and 10m)
    ctx.lineWidth = 1;
    ctx.strokeStyle = '#1F2937';
    const gridStep = 5 * scale;

    for (let x = centerX % gridStep; x < width; x += gridStep) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = centerY % gridStep; y < height; y += gridStep) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Axes
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, centerY);
    ctx.lineTo(width, centerY); // East Axis
    ctx.moveTo(centerX, 0);
    ctx.lineTo(centerX, height); // North Axis
    ctx.stroke();

    // Axis Labels
    ctx.fillStyle = '#6B7280';
    ctx.font = '10px monospace';
    ctx.fillText('+E (East) ->', width - 75, centerY - 8);
    ctx.fillText('+N (North) ^', centerX + 8, 18);
    ctx.fillText('Datum (0,0)', centerX + 6, centerY + 14);

    // Draw Origin Marker
    ctx.fillStyle = '#3B82F6';
    ctx.beginPath();
    ctx.arc(centerX, centerY, 5, 0, 2 * Math.PI);
    ctx.fill();

    // Draw History Trail
    if (historyTrail.length > 1) {
      ctx.strokeStyle = '#60A5FA';
      ctx.lineWidth = 2;
      ctx.beginPath();
      historyTrail.forEach((pt, idx) => {
        const px = centerX + pt.east * scale;
        const py = centerY - pt.north * scale;
        if (idx === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.stroke();
    }

    // Draw Current Device Position
    if (currentTelemetry) {
      const east = currentTelemetry.position.east;
      const north = currentTelemetry.position.north;
      const headingRad = (currentTelemetry.localization.heading_deg ?? 0) * (Math.PI / 180);

      const devX = centerX + east * scale;
      const devY = centerY - north * scale;

      // Accuracy circle
      const acc = currentTelemetry.localization.position_accuracy ?? 0.15;
      ctx.fillStyle = 'rgba(16, 185, 129, 0.15)';
      ctx.strokeStyle = '#10B981';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(devX, devY, Math.max(3, acc * scale), 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();

      // Heading arrow
      const arrowLen = 18;
      const tipX = devX + arrowLen * Math.sin(headingRad);
      const tipY = devY - arrowLen * Math.cos(headingRad);

      ctx.strokeStyle = '#F59E0B';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(devX, devY);
      ctx.lineTo(tipX, tipY);
      ctx.stroke();

      // Center point
      ctx.fillStyle = '#FFFFFF';
      ctx.beginPath();
      ctx.arc(devX, devY, 4, 0, 2 * Math.PI);
      ctx.fill();
    }
  }, [useOfflineGrid, currentTelemetry, historyTrail]);

  const handleCenterOnDevice = () => {
    if (leafletMapRef.current && currentTelemetry) {
      leafletMapRef.current.setView(
        [currentTelemetry.position.latitude, currentTelemetry.position.longitude],
        20,
        { animate: true }
      );
      setAutoFollow(true);
    }
  };

  const handleCenterOnOrigin = () => {
    if (leafletMapRef.current && referencePoint) {
      leafletMapRef.current.setView(
        [referencePoint.latitude, referencePoint.longitude],
        19,
        { animate: true }
      );
      setAutoFollow(false);
    }
  };

  return (
    <div className="relative w-full h-[520px] rounded-xl overflow-hidden border border-borderline shadow-2xl bg-[#0B0F17]">
      {/* Map Tile Error / Offline Notification Banner */}
      {mapTileFailed && !useOfflineGrid && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 bg-amber-950/80 border border-amber-700/80 text-amber-200 text-xs px-3 py-1.5 rounded-lg flex items-center gap-2 shadow-lg backdrop-blur">
          <WifiOff className="w-4 h-4 text-amber-400" />
          <span>No internet tiles available. Switched to offline local tracking.</span>
          <button
            onClick={() => setUseOfflineGrid(true)}
            className="underline font-bold text-amber-300 ml-1 hover:text-white"
          >
            Open Local ENU Grid
          </button>
        </div>
      )}

      {/* Mode 1: Leaflet Interactive Map View */}
      <div
        ref={mapContainerRef}
        className={`w-full h-full ${useOfflineGrid ? 'hidden' : 'block'}`}
      />

      {/* Mode 2: Offline Cartesian ENU Canvas View (Section 19) */}
      <div className={`w-full h-full ${useOfflineGrid ? 'block' : 'hidden'} relative`}>
        <canvas ref={canvasRef} className="w-full h-full block" />
        <div className="absolute bottom-3 left-3 bg-panelbg/90 border border-borderline px-3 py-1.5 rounded font-mono text-[11px] text-slate-300 shadow backdrop-blur">
          Local ENU Grid Mode (Offline) | Grid Step: 5m
        </div>
      </div>

      {/* Floating Map Controls Overlay */}
      <div className="absolute top-3 right-3 z-10 flex flex-col gap-2">
        {/* Toggle Mode: Map vs Local ENU Grid */}
        <button
          onClick={() => setUseOfflineGrid(!useOfflineGrid)}
          className={`p-2 rounded-lg border text-xs font-medium shadow-lg backdrop-blur flex items-center gap-1.5 transition-colors ${
            useOfflineGrid
              ? 'bg-blue-600 border-blue-500 text-white'
              : 'bg-panelbg/90 border-borderline text-slate-300 hover:bg-slate-800'
          }`}
          title="Toggle Local ENU Cartesian Grid Mode"
        >
          <Layers className="w-4 h-4" />
          <span className="hidden sm:inline font-mono">{useOfflineGrid ? 'MAP TILES' : 'ENU GRID'}</span>
        </button>

        {/* Center on Device */}
        <button
          onClick={handleCenterOnDevice}
          className={`p-2 rounded-lg border text-xs shadow-lg backdrop-blur flex items-center gap-1.5 transition-colors ${
            autoFollow
              ? 'bg-emerald-600/90 border-emerald-500 text-white'
              : 'bg-panelbg/90 border-borderline text-slate-300 hover:bg-slate-800'
          }`}
          title="Center and Follow Device"
        >
          <Crosshair className="w-4 h-4" />
          <span className="hidden sm:inline font-mono">FOLLOW</span>
        </button>

        {/* Center on Reference Origin */}
        <button
          onClick={handleCenterOnOrigin}
          className="p-2 rounded-lg bg-panelbg/90 border border-borderline text-slate-300 hover:bg-slate-800 text-xs shadow-lg backdrop-blur flex items-center gap-1.5 transition-colors"
          title="Center on Reference Point"
        >
          <MapPin className="w-4 h-4 text-blue-400" />
          <span className="hidden sm:inline font-mono">ORIGIN</span>
        </button>
      </div>

      {/* Map Legend Overlay */}
      <div className="absolute bottom-3 right-3 z-10 bg-panelbg/90 border border-borderline rounded-lg p-2.5 shadow-xl backdrop-blur font-mono text-[11px] text-slate-300 flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-blue-500 border border-blue-300"></div>
          <span>Reference Origin (E=0, N=0)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-emerald-500 border border-white"></div>
          <span>Current Device (Estimated)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-6 h-0.5 bg-blue-500"></div>
          <span>Trajectory Trail ({historyTrail.length} pts)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full border border-dashed border-emerald-400 bg-emerald-500/20"></div>
          <span>± Accuracy 1-σ Envelope</span>
        </div>
      </div>
    </div>
  );
};
