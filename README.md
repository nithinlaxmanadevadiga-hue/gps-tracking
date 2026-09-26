# Real-Time GPS-Denied Localization & Tracking System

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![ROS 2](https://img.shields.io/badge/ROS%202-Humble%20%2F%20Iron-brightgreen.svg)](https://docs.ros.org/en/humble/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61DAFB.svg)](https://react.dev/)

A full-stack, real-time GPS-denied localization and tracking system designed for consenting persons/devices in GPS-deprived environments (underground tunnels, mining portals, dense urban canyons, collapsed structures, indoor complexes, or defense/emergency response zones).

The system integrates 3D LiDAR, 6-DOF IMU, and velocity sensors through **FAST-LIO2/LIO-SAM**, fuses measurements into a **15-error-state Continuous Extended Kalman Filter (ESEKF)** with quaternion-based attitude propagation, converts local East-North-Up (ENU) coordinates to high-precision **WGS-84 geodetic coordinates (8 decimal places)**, and transmits authenticated telemetry to a ground station and responsive live web dashboard.

---

## Architecture

```
PERSON / DEVICE (Onboard ROS 2)
  ├── 3D LiDAR (e.g., Ouster, Velodyne, Robosense)
  ├── 6-DOF IMU (accelerometer + gyroscope)
  └── Velocity / Speed Sensor
            │
            ▼
    [FAST-LIO2 / LIO-SAM]
            │
            ▼ LIO Pose (p, q, cov)
    [15-State Error-State EKF (ESEKF)] <── Velocity Constraint Update
            │
            ▼ Local ENU Position (E, N, U)
    [WGS-84 Geodetic Converter (Rigorous ECEF)]
            │
            ▼ Latitude / Longitude / Altitude
    [Telemetry Dispatcher (WebSocket / MQTT)]
            │
            ▼ (Encrypted / Token Authenticated)
GROUND STATION (FastAPI Backend + PostgreSQL / In-Memory Cache)
            │
            ▼ WebSocket Broadcast (/ws/live, /ws/devices/{id})
OPERATOR BROWSER DASHBOARD (React + TypeScript + Leaflet + Offline ENU Grid)
```

---

## Mathematical Formulation

### 1. 15-Error-State Extended Kalman Filter (ESEKF)

The state vector consists of a **16-state nominal state** and a **15-state error state**:

#### Nominal State ($16$ dimensions):
$$\mathbf{x} = \begin{bmatrix} \mathbf{p} & \mathbf{v} & \mathbf{q} & \mathbf{b}_a & \mathbf{b}_g \end{bmatrix}^T$$
where:
* $\mathbf{p} \in \mathbb{R}^3$: Position in local East-North-Up (ENU) frame (meters)
* $\mathbf{v} \in \mathbb{R}^3$: Velocity in ENU frame (m/s)
* $\mathbf{q} = [q_w, q_x, q_y, q_z]^T$: Unit quaternion representing orientation from body frame to ENU frame
* $\mathbf{b}_a \in \mathbb{R}^3$: Accelerometer bias in body frame ($\text{m/s}^2$)
* $\mathbf{b}_g \in \mathbb{R}^3$: Gyroscope bias in body frame ($\text{rad/s}$)

#### Error State ($15$ dimensions):
$$\delta \mathbf{x} = \begin{bmatrix} \delta \mathbf{p} & \delta \mathbf{v} & \delta \boldsymbol{\theta} & \delta \mathbf{b}_a & \delta \mathbf{b}_g \end{bmatrix}^T$$
where $\delta \boldsymbol{\theta}$ is the small-angle rotation error vector such that $\mathbf{R}(\mathbf{q}) \approx \mathbf{R}(\hat{\mathbf{q}})(\mathbf{I} + [\delta \boldsymbol{\theta}]_\times)$.

#### Continuous Error-State Jacobian ($F_c$):
$$\mathbf{F}_c = \begin{bmatrix}
\mathbf{0}_{3\times 3} & \mathbf{I}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} \\
\mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & -\mathbf{R}[\mathbf{a}]_\times & -\mathbf{R} & \mathbf{0}_{3\times 3} \\
\mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & -[\boldsymbol{\omega}]_\times & \mathbf{0}_{3\times 3} & -\mathbf{I}_{3\times 3} \\
\mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} \\
\mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3} & \mathbf{0}_{3\times 3}
\end{bmatrix}$$
where:
* $\mathbf{R} = \mathbf{R}(\mathbf{q})$ is the rotation matrix from body to ENU
* $\mathbf{a} = \mathbf{a}_{\text{meas}} - \mathbf{b}_a$ is the unbiased body acceleration
* $[\mathbf{a}]_\times$ is the skew-symmetric cross-product matrix of $\mathbf{a}$
* $\boldsymbol{\omega} = \boldsymbol{\omega}_{\text{meas}} - \mathbf{b}_g$ is the unbiased body angular velocity

#### Discrete Propagation:
$$\mathbf{\Phi} = \mathbf{I}_{15\times 15} + \mathbf{F}_c \Delta t$$
$$\mathbf{P}_{k+1} = \mathbf{\Phi} \mathbf{P}_k \mathbf{\Phi}^T + \mathbf{Q}_d$$
where $\mathbf{Q}_d \approx \mathbf{G} \mathbf{Q}_c \mathbf{G}^T \Delta t$.

#### Attitude & State Error Injection:
When a measurement (LIO pose or velocity constraint) arrives, the Kalman gain $\mathbf{K}$ produces $\delta \mathbf{x}$:
$$\hat{\mathbf{p}} \leftarrow \hat{\mathbf{p}} + \delta \mathbf{p}$$
$$\hat{\mathbf{v}} \leftarrow \hat{\mathbf{v}} + \delta \mathbf{v}$$
$$\delta \mathbf{q} = \begin{bmatrix} 1 \\ \frac{1}{2} \delta \boldsymbol{\theta} \end{bmatrix}, \quad \hat{\mathbf{q}} \leftarrow \delta \mathbf{q} \otimes \hat{\mathbf{q}}, \quad \hat{\mathbf{q}} \leftarrow \frac{\hat{\mathbf{q}}}{\|\hat{\mathbf{q}}\|}$$
$$\hat{\mathbf{b}}_a \leftarrow \hat{\mathbf{b}}_a + \delta \mathbf{b}_a, \quad \hat{\mathbf{b}}_g \leftarrow \hat{\mathbf{b}}_g + \delta \mathbf{b}_g$$
$$\mathbf{P} \leftarrow (\mathbf{I} - \mathbf{K}\mathbf{H})\mathbf{P}(\mathbf{I} - \mathbf{K}\mathbf{H})^T + \mathbf{K}\mathbf{R}\mathbf{K}^T \quad \text{(Joseph form)}$$

---

### 2. WGS-84 Geodetic to Local ENU Conversion

The reference datum coordinate is defined by the operator:
$$(\phi_0, \lambda_0, h_0) \implies (E=0, N=0, U=0)$$

Conversions are implemented via **full closed-form ECEF geodesy**:
1. **Geodetic to ECEF**:
   $$N(\phi) = \frac{a}{\sqrt{1 - e^2 \sin^2 \phi}}$$
   $$X = (N(\phi) + h) \cos \phi \cos \lambda$$
   $$Y = (N(\phi) + h) \cos \phi \sin \lambda$$
   $$Z = (N(\phi)(1 - e^2) + h) \sin \phi$$
   where $a = 6378137.0\text{ m}$, $f = 1 / 298.257223563$, $e^2 = f(2 - f)$.

2. **ECEF to Local ENU**:
   $$\begin{bmatrix} E \\ N \\ U \end{bmatrix} = \begin{bmatrix} -\sin \lambda_0 & \cos \lambda_0 & 0 \\ -\sin \phi_0 \cos \lambda_0 & -\sin \phi_0 \sin \lambda_0 & \cos \phi_0 \\ \cos \phi_0 \cos \lambda_0 & \cos \phi_0 \sin \lambda_0 & \sin \phi_0 \end{bmatrix} \begin{bmatrix} X - X_0 \\ Y - Y_0 \\ Z - Z_0 \end{bmatrix}$$

3. **Local ENU to Geodetic**:
   Inverted via $\mathbf{R}_{\text{ECEF}\to\text{ENU}}^T \begin{bmatrix} E & N & U \end{bmatrix}^T + \begin{bmatrix} X_0 & Y_0 & Z_0 \end{bmatrix}^T \to (X, Y, Z)$, followed by Bowring's high-precision algorithm to extract $(\phi, \lambda, h)$ to $8$ decimal places.

---

## Coordinate Frames & Extrinsics

ROS 2 coordinate frame hierarchy:
```
map / enu (Local East-North-Up fixed at datum)
    │
base_link (Platform center of mass / body frame)
    ├── imu_link (IMU sensing center)
    └── lidar_link (3D LiDAR optical center)
```

Extrinsic configuration ([`calibration.yaml`](ros2_ws/src/gps_denied_localization/config/calibration.yaml)):
```yaml
extrinsic_calibration:
  lidar_to_imu:
    translation: { x: 0.05, y: 0.0, z: 0.12 }
    rotation: { roll: 0.0, pitch: 0.0, yaw: 0.0 }
```

---

## Telemetry Schema (Section 8 Compliant)

```json
{
  "device_id": "unit_001",
  "timestamp": 1727000000.123,
  "reference": {
    "latitude": 12.97160000,
    "longitude": 77.59460000,
    "altitude": 900.0
  },
  "position": {
    "east": 15.24,
    "north": 8.31,
    "up": 2.47,
    "latitude": 12.97167500,
    "longitude": 77.59474000,
    "altitude": 902.47
  },
  "velocity": {
    "east": 1.23,
    "north": 0.72,
    "up": 0.08
  },
  "orientation": {
    "roll": 0.0100,
    "pitch": 0.0300,
    "yaw": 1.4200
  },
  "localization": {
    "source": "lidar_imu_ekf",
    "gps_available": false,
    "position_accuracy": 0.15,
    "status": "GOOD",
    "status_reason": "Nominal",
    "heading_deg": 81.3,
    "speed_mps": 1.42,
    "horizontal_distance_m": 17.36,
    "distance_3d_m": 17.53,
    "is_simulation": false
  },
  "health": {
    "overall_quality": "GOOD",
    "subsystems": {
      "lidar": "ONLINE",
      "imu": "ONLINE",
      "velocity": "ONLINE",
      "lio": "TRACKING",
      "ekf": "RUNNING",
      "telemetry": "CONNECTED",
      "gps": "NOT USED"
    },
    "frequencies_hz": {
      "imu_hz": 50.0,
      "lidar_hz": 10.0,
      "lio_hz": 10.0,
      "ekf_hz": 50.0,
      "telemetry_hz": 10.0
    },
    "last_update_age_ms": 20.4
  }
}
```

---

## Security Architecture

1. **User Authentication & RBAC**:
   * Passwords hashed with `bcrypt`.
   * Secure JSON Web Tokens (`HS256`, 24-hour expiration).
   * Roles: `admin` (device registry/revocation, audit logs), `operator` (datum configuration, tracking, trail export), `viewer` (read-only live telemetry).
2. **Device Authorization & Revocation**:
   * Each tracking unit requires an authorized `device_id` and token hash.
   * Operators can instantly **revoke a device** via `POST /api/devices/{device_id}/revoke`, blocking incoming telemetry and notifying the console.
   * Anonymous or unregistered telemetry streams are rejected with HTTP 401/403.
3. **WebSocket Protection**:
   * All WebSocket streaming connections require a validated JWT token (`?token=...`).

---

## Quick Start (Development & Simulation Mode)

You can run the entire full-stack application and test all trajectories without physical hardware:

### 1. Start the Backend Ground Station
```bash
# In terminal 1:
cd backend
python run.py
```
Backend will start on `http://localhost:8000`. Database tables and default accounts are automatically created.

### 2. Start the Frontend Dashboard
```bash
# In terminal 2:
cd frontend
npm run dev
```
Open `http://localhost:3000` in your browser.

### 3. Log In to Ground Station
* **Username**: `operator` (or `admin`)
* **Password**: `operator123` (or `admin123`)

### 4. Interactive Simulation Panel
* Click the **Simulator** button in the top navigation bar.
* Click **START SIM** to stream synthetic 50Hz IMU, 10Hz LiDAR, and Velocity data.
* Switch trajectories:
  * **Figure-8 Patrol**: Smooth continuous Lissajous curves.
  * **Warehouse Perimeter**: Rectangular 90° cornering.
  * **Search & Rescue Zig-Zag**: Lawnmower area sweep.
  * **Subterranean Tunnel**: Slope descent with elevation decline.
* Adjust playback speed (0.5x, 1x, 2x, 5x).
* Test fault injections:
  * **Degrade LiDAR**: Simulates feature starvation, high residual, and covariance expansion (status changes to `DEGRADED`).
  * **Drop Comms**: Simulates radio link failure (stale telemetry warning activates).

---

## Connecting Real Hardware (ROS 2)

When running on an onboard computer (Jetson AGX, Intel NUC) with physical sensors:

1. **Verify Sensor Drivers**:
   * LiDAR publishing `/lidar/points` (`sensor_msgs/msg/PointCloud2`).
   * IMU publishing `/imu/data` (`sensor_msgs/msg/Imu`).
   * Speed sensor publishing `/velocity` (`geometry_msgs/msg/TwistStamped`).
   * FAST-LIO2 or LIO-SAM publishing `/lio/pose` (`nav_msgs/msg/Odometry`).

2. **Configure Calibration**:
   Update `ros2_ws/src/gps_denied_localization/config/calibration.yaml` with the measured translation and rotation offsets between the LiDAR optical center and IMU origin.

3. **Build & Launch ROS 2 Node**:
```bash
cd ros2_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

ros2 launch gps_denied_localization localization.launch.py
```

The node will broadcast local transforms `map -> base_link -> imu_link, lidar_link` and securely dispatch real-time telemetry to the ground station.

---

## Running with Docker Compose

Deploy the complete stack (PostgreSQL + Mosquitto MQTT + FastAPI + React/Nginx + ROS 2):

```bash
docker-compose up --build -d
```
* **Web Dashboard**: `http://localhost:3000`
* **Ground Station API**: `http://localhost:8000`
* **API Documentation**: `http://localhost:8000/docs`
* **MQTT Broker**: `localhost:1883`
* **PostgreSQL**: `localhost:5432`

---

## Running Automated Tests

Run the test suite covering ESEKF filter math, WGS-84 coordinate roundtrips, authentication, and telemetry flow:

```bash
python -m pytest backend/tests -v
```
Output:
```
backend/tests/test_auth_api.py::test_auth_and_protected_routes PASSED
backend/tests/test_esekf.py::test_skew_matrix PASSED
backend/tests/test_esekf.py::test_quat_euler_conversions PASSED
backend/tests/test_esekf.py::test_esekf_imu_prediction_stationary PASSED
backend/tests/test_esekf.py::test_esekf_lio_measurement_update PASSED
backend/tests/test_esekf.py::test_esekf_velocity_constraint PASSED
backend/tests/test_esekf.py::test_esekf_jump_rejection_and_degradation PASSED
backend/tests/test_geodetic.py::test_geodetic_ecef_roundtrip PASSED
backend/tests/test_geodetic.py::test_enu_origin_identity PASSED
backend/tests/test_geodetic.py::test_enu_displacement_and_distances PASSED
backend/tests/test_geodetic.py::test_approx_vs_rigorous_comparison PASSED
backend/tests/test_telemetry.py::test_telemetry_flow PASSED
======================== 12 passed in 3.9s ========================
```

---

## API Endpoints Reference

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Authenticate and obtain JWT token | None |
| `GET` | `/api/auth/me` | Current user profile | Bearer JWT |
| `GET` | `/api/devices` | List registered tracking units | Bearer JWT |
| `POST` | `/api/devices` | Register new tracking device | Admin/Operator |
| `POST` | `/api/devices/{id}/revoke` | Revoke device authorization | Admin/Operator |
| `GET` | `/api/devices/{id}/position` | Get current estimated position | Bearer JWT |
| `GET` | `/api/devices/{id}/history` | Query trajectory history | Bearer JWT |
| `POST` | `/api/devices/{id}/clear-trail` | Clear trajectory trail buffer | Bearer JWT |
| `GET` | `/api/reference` | Get active reference origin datum | Bearer JWT |
| `POST` | `/api/reference` | Set new reference coordinates | Admin/Operator |
| `POST` | `/api/telemetry` | Ingest sensor telemetry stream | Device Token |
| `GET` | `/api/events/localization` | Query localization fault events | Bearer JWT |
| `POST` | `/api/simulator/control` | Control simulation engine | Bearer JWT |
| `WS` | `/ws/live` | Real-time global telemetry stream | JWT Token |
| `WS` | `/ws/devices/{id}` | Real-time device-specific stream | JWT Token |
| `WS` | `/ws/telemetry/ingest` | High-frequency telemetry ingestion | Device Token |
| `GET` | `/health` | Ground station health check | None |

---

## Offline Local Operation

In disconnected remote field scenarios without Internet or satellite imagery:
* The dashboard features an **Offline Local ENU Grid mode** rendered directly on HTML5 Canvas.
* Tracks displacement relative to the datum $(E=0, N=0, U=0)$ with 5-meter grid graduations, directional indicator, and accuracy circles.
* Operates 100% on a local ad-hoc Wi-Fi network, Ethernet cable, or tactical radio link.
