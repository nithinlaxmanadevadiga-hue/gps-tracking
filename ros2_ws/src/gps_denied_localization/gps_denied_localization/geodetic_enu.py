"""
WGS-84 Geodetic and Local ENU (East-North-Up) Transformation Module.

Implements rigorous full-geodesy transformations:
  Geodetic (lat, lon, alt) <-> ECEF (X, Y, Z) <-> Local ENU (E, N, U)
as well as local meridional/prime-vertical curvature radius approximations.

Conforms to standard WGS-84 parameters:
  Semi-major axis (a) = 6378137.0 m
  Flattening (f)      = 1 / 298.257223563
  e^2                 = f * (2 - f)
"""

import math
from typing import Tuple, NamedTuple


class WGS84Constants:
    """WGS-84 reference ellipsoid parameters."""
    A: float = 6378137.0                      # Semi-major axis (meters)
    F: float = 1.0 / 298.257223563           # Flattening
    B: float = A * (1.0 - F)                  # Semi-minor axis (~6356752.314245 m)
    E2: float = F * (2.0 - F)                 # First eccentricity squared (~0.00669437999014)
    E_PRIME2: float = (A * A - B * B) / (B * B) # Second eccentricity squared


class ReferencePoint(NamedTuple):
    latitude: float   # degrees (-90 to +90)
    longitude: float  # degrees (-180 to +180)
    altitude: float   # meters above WGS-84 ellipsoid
    heading: float = 0.0 # initial heading in degrees (0 = North, 90 = East)


class GeodeticPoint(NamedTuple):
    latitude: float
    longitude: float
    altitude: float


class ENUPoint(NamedTuple):
    east: float
    north: float
    up: float


def geodetic_to_ecef(lat_deg: float, lon_deg: float, alt_m: float) -> Tuple[float, float, float]:
    """
    Convert geodetic coordinates (lat, lon, alt) to Earth-Centered, Earth-Fixed (ECEF) X, Y, Z.
    """
    phi = math.radians(lat_deg)
    lam = math.radians(lon_deg)
    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    sin_lam = math.sin(lam)
    cos_lam = math.cos(lam)

    # Prime vertical radius of curvature
    n = WGS84Constants.A / math.sqrt(1.0 - WGS84Constants.E2 * sin_phi * sin_phi)

    x = (n + alt_m) * cos_phi * cos_lam
    y = (n + alt_m) * cos_phi * sin_lam
    z = (n * (1.0 - WGS84Constants.E2) + alt_m) * sin_phi

    return x, y, z


def ecef_to_geodetic(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """
    Convert ECEF (X, Y, Z in meters) to geodetic (lat, lon in degrees, alt in meters).
    Uses Bowring's closed-form algorithm (accurate to within 0.1 mm globally).
    """
    p = math.hypot(x, y)
    if p < 1e-9:
        # Near poles
        lat = 90.0 if z > 0 else -90.0
        lon = 0.0
        alt = abs(z) - WGS84Constants.B
        return lat, lon, alt

    theta = math.atan2(z * WGS84Constants.A, p * WGS84Constants.B)
    sin_theta = math.sin(theta)
    cos_theta = math.cos(theta)

    sin_theta3 = sin_theta * sin_theta * sin_theta
    cos_theta3 = cos_theta * cos_theta * cos_theta

    phi = math.atan2(
        z + WGS84Constants.E_PRIME2 * WGS84Constants.B * sin_theta3,
        p - WGS84Constants.E2 * WGS84Constants.A * cos_theta3,
    )
    lam = math.atan2(y, x)

    sin_phi = math.sin(phi)
    cos_phi = math.cos(phi)
    n = WGS84Constants.A / math.sqrt(1.0 - WGS84Constants.E2 * sin_phi * sin_phi)
    alt = (p / cos_phi) - n

    return math.degrees(phi), math.degrees(lam), alt


def enu_rotation_matrix(lat0_deg: float, lon0_deg: float) -> Tuple[Tuple[float, float, float], ...]:
    """
    Return the 3x3 rotation matrix R from ECEF difference vector to local ENU frame:
      [E, N, U]^T = R * [dX, dY, dZ]^T
    """
    phi0 = math.radians(lat0_deg)
    lam0 = math.radians(lon0_deg)

    sin_phi = math.sin(phi0)
    cos_phi = math.cos(phi0)
    sin_lam = math.sin(lam0)
    cos_lam = math.cos(lam0)

    # R_ECEF->ENU
    return (
        (-sin_lam, cos_lam, 0.0),
        (-sin_phi * cos_lam, -sin_phi * sin_lam, cos_phi),
        (cos_phi * cos_lam, cos_phi * sin_lam, sin_phi),
    )


def ecef_to_enu(
    x: float, y: float, z: float,
    lat0_deg: float, lon0_deg: float, alt0_m: float
) -> Tuple[float, float, float]:
    """
    Convert ECEF (X, Y, Z) to local East-North-Up (ENU) coordinates relative to reference.
    """
    x0, y0, z0 = geodetic_to_ecef(lat0_deg, lon0_deg, alt0_m)
    dx = x - x0
    dy = y - y0
    dz = z - z0

    r = enu_rotation_matrix(lat0_deg, lon0_deg)
    east = r[0][0] * dx + r[0][1] * dy + r[0][2] * dz
    north = r[1][0] * dx + r[1][1] * dy + r[1][2] * dz
    up = r[2][0] * dx + r[2][1] * dy + r[2][2] * dz

    return east, north, up


def enu_to_ecef(
    east: float, north: float, up: float,
    lat0_deg: float, lon0_deg: float, alt0_m: float
) -> Tuple[float, float, float]:
    """
    Convert local ENU coordinates to ECEF (X, Y, Z).
    Uses transpose (inverse) of ENU rotation matrix.
    """
    x0, y0, z0 = geodetic_to_ecef(lat0_deg, lon0_deg, alt0_m)
    r = enu_rotation_matrix(lat0_deg, lon0_deg)

    # dx = R^T * [E, N, U]^T
    dx = r[0][0] * east + r[1][0] * north + r[2][0] * up
    dy = r[0][1] * east + r[1][1] * north + r[2][1] * up
    dz = r[0][2] * east + r[1][2] * north + r[2][2] * up

    return x0 + dx, y0 + dy, z0 + dz


def enu_to_geodetic(
    east: float, north: float, up: float,
    lat0_deg: float, lon0_deg: float, alt0_m: float
) -> Tuple[float, float, float]:
    """
    Full rigorous conversion from local ENU to Geodetic (lat, lon, alt).
    Operates via ENU -> ECEF -> Geodetic.
    """
    x, y, z = enu_to_ecef(east, north, up, lat0_deg, lon0_deg, alt0_m)
    return ecef_to_geodetic(x, y, z)


def geodetic_to_enu(
    lat_deg: float, lon_deg: float, alt_m: float,
    lat0_deg: float, lon0_deg: float, alt0_m: float
) -> Tuple[float, float, float]:
    """
    Full rigorous conversion from Geodetic (lat, lon, alt) to local ENU.
    Operates via Geodetic -> ECEF -> ENU.
    """
    x, y, z = geodetic_to_ecef(lat_deg, lon_deg, alt_m)
    return ecef_to_enu(x, y, z, lat0_deg, lon0_deg, alt0_m)


def curvature_radii(lat_deg: float) -> Tuple[float, float]:
    """
    Calculate meridional radius of curvature (M) and prime vertical radius (N)
    at given latitude.
      M = a * (1 - e^2) / (1 - e^2 * sin^2(lat))^(3/2)
      N = a / sqrt(1 - e^2 * sin^2(lat))
    """
    phi = math.radians(lat_deg)
    sin_phi = math.sin(phi)
    denom = 1.0 - WGS84Constants.E2 * sin_phi * sin_phi
    sqrt_denom = math.sqrt(denom)

    m = WGS84Constants.A * (1.0 - WGS84Constants.E2) / (denom * sqrt_denom)
    n = WGS84Constants.A / sqrt_denom
    return m, n


def enu_to_geodetic_approx(
    east: float, north: float, up: float,
    lat0_deg: float, lon0_deg: float, alt0_m: float
) -> Tuple[float, float, float]:
    """
    Local tangential approximation using radii of curvature.
    Good for quick checks in small operations areas (< 5 km).
    """
    m, n = curvature_radii(lat0_deg)
    d_lat = north / (m + alt0_m)
    d_lon = east / ((n + alt0_m) * math.cos(math.radians(lat0_deg)))
    lat = lat0_deg + math.degrees(d_lat)
    lon = lon0_deg + math.degrees(d_lon)
    alt = alt0_m + up
    return lat, lon, alt


def compute_distances(east: float, north: float, up: float) -> Tuple[float, float]:
    """
    Calculate horizontal and 3D distance from origin (reference point).
    Returns (horizontalDistance, distance3D) in meters.
    """
    horiz = math.hypot(east, north)
    dist_3d = math.sqrt(east * east + north * north + up * up)
    return horiz, dist_3d
