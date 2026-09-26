import math
import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ros2_ws", "src", "gps_denied_localization")))
from gps_denied_localization.geodetic_enu import (
    geodetic_to_ecef,
    ecef_to_geodetic,
    ecef_to_enu,
    enu_to_ecef,
    enu_to_geodetic,
    geodetic_to_enu,
    compute_distances,
    curvature_radii,
    enu_to_geodetic_approx
)


def test_geodetic_ecef_roundtrip():
    # Test Bengaluru coordinates
    lat0, lon0, alt0 = 12.97160000, 77.59460000, 900.0

    x, y, z = geodetic_to_ecef(lat0, lon0, alt0)
    lat_res, lon_res, alt_res = ecef_to_geodetic(x, y, z)

    assert abs(lat_res - lat0) < 1e-8
    assert abs(lon_res - lon0) < 1e-8
    assert abs(alt_res - alt0) < 1e-4


def test_enu_origin_identity():
    # Reference point transformed to ENU must be (0, 0, 0)
    lat0, lon0, alt0 = 12.97160000, 77.59460000, 900.0
    east, north, up = geodetic_to_enu(lat0, lon0, alt0, lat0, lon0, alt0)

    assert abs(east) < 1e-5
    assert abs(north) < 1e-5
    assert abs(up) < 1e-5


def test_enu_displacement_and_distances():
    lat0, lon0, alt0 = 12.97160000, 77.59460000, 900.0
    east_in, north_in, up_in = 15.24, 8.31, 2.47

    # ENU -> Geodetic -> ENU roundtrip
    lat, lon, alt = enu_to_geodetic(east_in, north_in, up_in, lat0, lon0, alt0)
    e_out, n_out, u_out = geodetic_to_enu(lat, lon, alt, lat0, lon0, alt0)

    assert abs(e_out - east_in) < 1e-4
    assert abs(n_out - north_in) < 1e-4
    assert abs(u_out - up_in) < 1e-4

    # Distance test
    horiz, dist3d = compute_distances(east_in, north_in, up_in)
    expected_horiz = math.hypot(15.24, 8.31)
    expected_3d = math.sqrt(15.24**2 + 8.31**2 + 2.47**2)

    assert abs(horiz - expected_horiz) < 1e-4
    assert abs(dist3d - expected_3d) < 1e-4


def test_approx_vs_rigorous_comparison():
    lat0, lon0, alt0 = 12.97160000, 77.59460000, 900.0
    east, north, up = 50.0, 30.0, 5.0

    lat_rigorous, lon_rigorous, alt_rigorous = enu_to_geodetic(east, north, up, lat0, lon0, alt0)
    lat_approx, lon_approx, alt_approx = enu_to_geodetic_approx(east, north, up, lat0, lon0, alt0)

    # Within 50 meters, difference between rigorous and curvature approximation is sub-millimeter (< 1e-6 degrees)
    assert abs(lat_rigorous - lat_approx) < 1e-6
    assert abs(lon_rigorous - lon_approx) < 1e-6
