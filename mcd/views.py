"""Expune driverele MCD prin Django: tabelul de pini, citire accelerometru, auto-test."""
import io
import math
import time
import threading
import unittest

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from . import config, i2c, mpu6050
from . import test as driver_tests

_selftest_lock = threading.Lock()


@require_GET
def index(request):
    return render(request, "mcd/index.html", {
        "pins": config.PIN_TABLE,
        "mode": config.simulation_mode(),
        "i2c_simulated": i2c.I2C_bIsSimulated(),
    })


@require_GET
def api_pins(request):
    return JsonResponse({"pins": config.PIN_TABLE})


@require_GET
def api_accel(request):
    """Citește MPU6050 (real sau simulat) și returnează accelerația în g."""
    try:
        mpu6050.MPU6050_vInit()
        ax, ay, az = mpu6050.MPU6050_tReadG()
        magnitude = mpu6050.MPU6050_fReadMagnitudeG()
    except (OSError, RuntimeError) as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    return JsonResponse({
        "ax_g": round(ax, 4), "ay_g": round(ay, 4), "az_g": round(az, 4),
        "magnitude_g": round(magnitude, 4),
        "simulated": i2c.I2C_bIsSimulated(),
    })


def _risk_level(distance_m, rel_speed_kmh):
    if distance_m <= 35 and rel_speed_kmh >= 30:
        return "high"
    if distance_m <= 80 and rel_speed_kmh >= 15:
        return "medium"
    return "low"


def _build_dummy_dashboard_data(now_s):
    """Date de demo pentru interfață: vecini, alerte și trend accelerație."""
    phase = now_s / 10.0
    own_speed = 56.0 + 7.0 * math.sin(phase)

    neighbors = []
    neighbor_seeds = [
        ("VH-021", "Zigbee", 22, 30, -4.0, -3.5),
        ("VH-305", "Zigbee", 41, 120, +2.0, +1.0),
        ("VH-117", "Meshtastic", 95, 280, -8.0, +3.2),
        ("VH-442", "Meshtastic", 155, 340, +12.0, -1.7),
    ]
    for idx, seed in enumerate(neighbor_seeds):
        vid, source, base_dist, bearing, rel_speed, drift = seed
        dynamic_dist = max(8.0, base_dist + 9.0 * math.sin(phase + idx * 0.8))
        dynamic_rel = rel_speed + 4.0 * math.cos(phase + idx * 0.6)
        neighbors.append({
            "vehicle_id": vid,
            "source": source,
            "distance_m": round(dynamic_dist, 1),
            "bearing_deg": int((bearing + int(now_s) * (idx + 1)) % 360),
            "speed_kmh": round(max(0.0, own_speed + dynamic_rel), 1),
            "rel_speed_kmh": round(dynamic_rel, 1),
            "drift_mps": round(drift, 1),
            "risk": _risk_level(dynamic_dist, abs(dynamic_rel)),
        })

    accel_samples = []
    for i in range(14):
        t = now_s - (13 - i)
        spike = 0.0
        if i in (5, 11):
            spike = 0.7 + 0.3 * math.sin(phase + i)
        mag = 1.0 + 0.08 * math.sin(t / 3.0) + spike
        accel_samples.append({"t": int(t), "magnitude_g": round(mag, 3)})

    high_risk = sum(1 for n in neighbors if n["risk"] == "high")
    medium_risk = sum(1 for n in neighbors if n["risk"] == "medium")
    return {
        "timestamp": int(now_s),
        "mode": config.simulation_mode(),
        "simulated": i2c.I2C_bIsSimulated(),
        "own_vehicle": {
            "vehicle_id": "VH-001",
            "speed_kmh": round(own_speed, 1),
            "heading_deg": int((25 + int(now_s * 2)) % 360),
            "gps": {"lat": 45.7558, "lon": 21.2285},
            "impact_threshold_g": 2.5,
        },
        "neighbors": neighbors,
        "alerts": {
            "high": high_risk,
            "medium": medium_risk,
            "active": bool(high_risk or medium_risk),
        },
        "accel_trend": accel_samples,
    }


@require_GET
def api_dashboard(request):
    return JsonResponse(_build_dummy_dashboard_data(time.time()))


@require_GET
def api_selftest(request):
    """Rulează testele driverelor în simulare (nu atinge hardware-ul)."""
    if not _selftest_lock.acquire(blocking=False):
        return JsonResponse({"error": "auto-testul rulează deja"}, status=409)
    try:
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            driver_tests.build_sim_suite())
    finally:
        _selftest_lock.release()
    return JsonResponse({
        "ok": result.wasSuccessful(),
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "log": stream.getvalue(),
    })
