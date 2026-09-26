#!/usr/bin/env python3
"""CLI runner for standalone GPS-denied simulator."""
import time
import argparse
from synthetic_sensor_stream import SimulatorEngine

def main():
    parser = argparse.ArgumentParser(description="GPS-Denied Localization Simulator CLI")
    parser.add_argument("--pattern", type=str, default="figure8", choices=["figure8", "warehouse", "zigzag", "tunnel"])
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--url", type=str, default="http://localhost:8000/api/telemetry")
    parser.add_argument("--device", type=str, default="unit_001")
    args = parser.parse_args()

    print(f"Starting GPS-Denied Simulator [{args.pattern}] at {args.speed}x speed for {args.device}...")
    sim = SimulatorEngine(device_id=args.device, backend_url=args.url)
    sim.set_controls(running=True, speed=args.speed, pattern=args.pattern)

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopping simulator...")
        sim.stop()

if __name__ == "__main__":
    main()
