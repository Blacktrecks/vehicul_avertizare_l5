"""Expune driverele MCD prin Django: tabelul de pini, citire accelerometru, auto-test."""
import io
import math
import time
import threading
import unittest

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from . import config, i2c, mpu6050
from . import test as driver_tests
from web.service import StateService

_selftest_lock = threading.Lock()


@ensure_csrf_cookie
@require_GET
def index(request):
    state = StateService().snapshot()
    return render(request, "web/dashboard.html", {
        "pins": config.PIN_TABLE,
        "mode": config.simulation_mode(),
        "i2c_simulated": i2c.I2C_bIsSimulated(),
        "state": state,
    })


def _page(request, title, subtitle, cards, metrics=None, table_headers=None, table_rows=None):
    return render(request, "web/section_page.html", {
        "section_title": title,
        "section_subtitle": subtitle,
        "cards": cards,
        "metrics": metrics or [],
        "table_headers": table_headers or [],
        "table_rows": table_rows or [],
    })


@ensure_csrf_cookie
@require_GET
def page_devices(request):
    return _page(
        request,
        "Dispozitive",
        "Manager dispozitive și canale de comunicație",
        [
            {"title": "Zigbee", "value": "3 noduri", "detail": "OK / 96% PDR"},
            {"title": "Meshtastic", "value": "2 noduri", "detail": "Link stabil"},
            {"title": "MPU6050", "value": "1 modul", "detail": "Simulat"},
        ],
        metrics=[
            {"label": "Scanare USB", "value": "06"},
            {"label": "Conectate", "value": "05"},
            {"label": "Lat. medie", "value": "420 ms"},
            {"label": "Profiluri", "value": "04"},
        ],
        table_headers=["Device", "Tip", "Port", "Stare", "Profil"],
        table_rows=[
            ["ZB-01", "Zigbee", "/dev/ttyUSB0", "Conectat", "Vehicul"],
            ["MS-02", "Meshtastic", "/dev/ttyACM0", "Conectat", "Rutină"],
            ["B1", "GPIO", "BUZZER", "Activ", "Default"],
            ["L1", "GPIO", "LED", "Activ", "Default"],
        ],
    )


@ensure_csrf_cookie
@require_GET
def page_simulator(request):
    return _page(
        request,
        "Simulare",
        "Laborator de scenarii și fault injection",
        [
            {"title": "Convoi", "value": "3 vehicule", "detail": "Lat. 480 ms"},
            {"title": "Impact frontal", "value": "1 scenariu", "detail": "Alertă activă"},
            {"title": "Replay", "value": "2 atacuri", "detail": "La limită"},
        ],
        metrics=[
            {"label": "Scenarii", "value": "03"},
            {"label": "Viteză medie", "value": "42 km/h"},
            {"label": "Risc", "value": "Mediu"},
            {"label": "Alertă", "value": "Normală"},
        ],
        table_headers=["Scenariu", "Tip", "Efect", "Status"],
        table_rows=[
            ["Convoi", "Traffic", "Viteză constantă", "Rulează"],
            ["Impact frontal", "Pericol", "Trigger alertă", "Test"],
            ["Spoof+replay", "Securitate", "Răspuns activ", "Monitorizat"],
        ],
    )


@ensure_csrf_cookie
@require_GET
def page_tests(request):
    return _page(
        request,
        "Teste",
        "Centrală de rulare scenarii și reportare",
        [
            {"title": "Self-test", "value": "Pass", "detail": "Driver layer OK"},
            {"title": "Comms", "value": "4/4", "detail": "Zigbee + LoRa"},
            {"title": "Rapoarte", "value": "7", "detail": "CSV / JSON / HTML"},
        ],
        metrics=[
            {"label": "Teste rulare", "value": "53"},
            {"label": "Skipped", "value": "03"},
            {"label": "Rapoarte", "value": "07"},
            {"label": "Status", "value": "OK"},
        ],
        table_headers=["Test", "Categorie", "Rezultat", "Observații"],
        table_rows=[
            ["GPIO chip", "Hardware", "OK", "Detectare stabilă"],
            ["I2C MPU6050", "Sensor", "OK", "Mag. 1.0g"],
            ["Alert logic", "Sistem", "OK", "Impact detectat"],
        ],
    )


@ensure_csrf_cookie
@require_GET
def page_stats(request):
    return _page(
        request,
        "Statistici",
        "Indicatori de performanță și trenduri",
        [
            {"title": "PDR", "value": "96%", "detail": "Last 24h"},
            {"title": "Lat. avg", "value": "480 ms", "detail": "P95 900 ms"},
            {"title": "Alerte", "value": "3", "detail": "Ultimele 8h"},
        ],
        metrics=[
            {"label": "Vehicule", "value": "07"},
            {"label": "Conexiuni", "value": "12"},
            {"label": "False alarms", "value": "00"},
            {"label": "SNR", "value": "18 dB"},
        ],
        table_headers=["Metrică", "Valoare", "Trend"],
        table_rows=[
            ["PDR Zigbee", "96%", "↑ 2%"],
            ["PDR Meshtastic", "94%", "→"],
            ["Lat. alertă", "0.42 s", "↓ 0.1 s"],
        ],
    )


@ensure_csrf_cookie
@require_GET
def page_logs(request):
    return _page(
        request,
        "Loguri",
        "Flux de evenimente și extragere de date",
        [
            {"title": "Sursă", "value": "sim", "detail": "În directoarea logs/"},
            {"title": "Ultimul eveniment", "value": "2.1s", "detail": "RX Zigbee"},
            {"title": "Rotație", "value": "5x2MB", "detail": "Auto-rotate"},
        ],
        metrics=[
            {"label": "Level", "value": "INFO"},
            {"label": "Stream", "value": "Live"},
            {"label": "Filtre", "value": "04"},
            {"label": "Export", "value": "CSV"},
        ],
        table_headers=["Timp", "Sursă", "Nivel", "Mesaj"],
        table_rows=[
            ["17:33:01", "zigbee", "INFO", "Link activ"],
            ["17:33:04", "sim", "WARN", "Impact în față"],
            ["17:33:12", "mcd", "INFO", "Self-test complet"],
        ],
    )


@ensure_csrf_cookie
@require_GET
def page_diagnostics(request):
    return _page(
        request,
        "Diagnoză",
        "Stare hardware, pin table și verificări active",
        [
            {"title": "GPIO", "value": "Detectat", "detail": "Chip selectat"},
            {"title": "I2C", "value": "OK", "detail": "MPU6050 online"},
            {"title": "LED/Buzzer", "value": "Testabil", "detail": "Auto-off"},
        ],
        metrics=[
            {"label": "Pini", "value": "08"},
            {"label": "Buzzer", "value": "0/1"},
            {"label": "LED", "value": "0/1"},
            {"label": "Accel", "value": "1.00g"},
        ],
        table_headers=["Nume", "Valoare", "Status"],
        table_rows=[
            ["I2C_SDA", "GPIO2", "OK"],
            ["I2C_SCL", "GPIO3", "OK"],
            ["BUZZER", "GPIO17", "Activ"],
            ["LED", "GPIO27", "Activ"],
        ],
    )


@ensure_csrf_cookie
@require_GET
def page_operator(request):
    return _page(
        request,
        "Centru operator",
        "Vizualizare vehicule, alert list și control central",
        [
            {"title": "Vehicule", "value": "07", "detail": "2 periculoase"},
            {"title": "Harta", "value": "Online", "detail": "SVG fallback"},
            {"title": "Alertă", "value": "1", "detail": "Neconfirmată"},
        ],
        metrics=[
            {"label": "Noduri LoRa", "value": "04"},
            {"label": "Rapoarte", "value": "12"},
            {"label": "Alerte", "value": "01"},
            {"label": "Operator", "value": "Live"},
        ],
        table_headers=["Vehicul", "Coordonate", "Viteză", "Status"],
        table_rows=[
            ["V1", "47.15 / 27.59", "42 km/h", "Normal"],
            ["V2", "47.15 / 27.59", "41 km/h", "Atenție"],
            ["V3", "47.15 / 27.59", "36 km/h", "Risc"],
        ],
    )


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
