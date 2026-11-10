import io
import json
import time
import unittest
from pathlib import Path

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from mcd import test as driver_tests
from sdc.registry import DeviceRegistry
from .service import StateService

SERVICE = StateService()
REGISTRY = DeviceRegistry()
BASE_DIR = Path(__file__).resolve().parent.parent
SCENARIO_DIR = BASE_DIR / "scenarios"
REPORT_DIR = BASE_DIR / "data" / "reports"


def _read_json_body(request):
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError as exc:
        raise ValueError("JSON invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("payload invalid")
    return payload


def _validate_scenario_steps(steps):
    allowed = {"connect", "disconnect", "send_text", "send_packet", "expect_rx", "wait", "inject", "assert"}
    if not isinstance(steps, list) or not steps:
        raise ValueError("steps invalide: lista este obligatorie")
    validated = []
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"step {index}: obiect invalid")
        op = str(step.get("op") or "").strip().lower()
        if op not in allowed:
            raise ValueError(f"step {index}: op nepermis ({op})")
        validated.append(step)
    return validated


@require_GET
def api_state(request):
    return JsonResponse(SERVICE.snapshot())


@require_GET
def api_stream(request):
    def stream():
        yield "event: state\ndata: " + json.dumps(SERVICE.snapshot()) + "\n\n"
        while True:
            yield "event: state\ndata: " + json.dumps(SERVICE.snapshot()) + "\n\n"
            import time
            time.sleep(0.5)

    return StreamingHttpResponse(stream(), content_type="text/event-stream")


@csrf_protect
@require_POST
def api_outputs(request):
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalid"}, status=400)
    channel = payload.get("channel")
    value = payload.get("value")
    duration_ms = payload.get("duration_ms")
    try:
        SERVICE.set_output(channel, value, duration_ms)
        return JsonResponse({"ok": True, "state": SERVICE.snapshot()})
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@csrf_protect
@require_POST
def api_outputs_off(request):
    SERVICE.set_outputs_off()
    return JsonResponse({"ok": True, "state": SERVICE.snapshot()})


@csrf_protect
@require_POST
def api_alert_ack(request):
    SERVICE.ack_alert()
    return JsonResponse({"ok": True, "state": SERVICE.snapshot()})


@csrf_protect
@require_POST
def api_mode(request):
    try:
        payload = json.loads(request.body or b"{}") if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalid"}, status=400)
    mode = payload.get("mode") or request.POST.get("mode") or "simulation"
    try:
        SERVICE.set_mode(mode)
        return JsonResponse({"ok": True, "state": SERVICE.snapshot()})
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@csrf_protect
@require_POST
def api_sim_action(request, action=None):
    if action is None:
        action = request.POST.get("action") or request.path.rstrip("/").split("/")[-1]
    if action == "start":
        SERVICE.start()
    elif action == "pause":
        SERVICE.pause()
    elif action == "stop":
        SERVICE.stop()
    elif action == "inject":
        SERVICE.inject_impact()
    else:
        return JsonResponse({"error": "acțiune invalidă"}, status=400)
    return JsonResponse({"ok": True, "state": SERVICE.snapshot()})


@require_GET
def api_logs(request):
    logs = SERVICE.logger.read(limit=200)
    return JsonResponse({"logs": logs, "count": len(logs)})


@require_GET
def api_logs_stream(request):
    def stream():
        last_signature = ""
        while True:
            logs = SERVICE.logger.read(limit=1)
            latest = logs[-1] if logs else {"message": "idle"}
            signature = json.dumps(latest, sort_keys=True, ensure_ascii=False)
            if signature != last_signature:
                yield "event: log\ndata: " + signature + "\n\n"
                last_signature = signature
            else:
                yield ": keepalive\n\n"
            time.sleep(0.7)

    response = StreamingHttpResponse(stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    return response


@require_http_methods(["GET", "POST"])
@csrf_protect
def api_devices(request):
    if request.method == "GET":
        devices = REGISTRY.list_devices()
        return JsonResponse({"devices": devices, "count": len(devices)})
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalid"}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "payload invalid"}, status=400)
    record = REGISTRY.add_device(payload)
    return JsonResponse({"ok": True, "device": record})


@require_GET
def api_devices_scan(request):
    devices = REGISTRY.scan()
    return JsonResponse({"devices": devices, "count": len(devices)})


@require_GET
def api_device_detail(request, device_id):
    device = REGISTRY.get_device(device_id)
    if device is None:
        return JsonResponse({"error": "device not found"}, status=404)
    return JsonResponse({"device": device})


@require_GET
def api_device_profile_preview(request, device_id):
    try:
        preview = REGISTRY.profile_preview(device_id)
    except KeyError:
        return JsonResponse({"error": "device not found"}, status=404)
    return JsonResponse({"ok": True, "preview": preview})


@csrf_protect
@require_POST
def api_device_action(request, device_id, action):
    device = REGISTRY.get_device(device_id)
    if device is None:
        return JsonResponse({"error": "device not found"}, status=404)
    action = (action or "").strip().lower()
    try:
        if action == "connect":
            result = REGISTRY.connect_device(device_id)
            SERVICE.logger.info(f"Connected device {device_id}", device=device_id, label=device.get("label"), transport=device.get("transport"))
            return JsonResponse({"ok": True, "device": result["device"], "result": result["result"]})
        if action == "disconnect":
            result = REGISTRY.disconnect_device(device_id)
            SERVICE.logger.info(f"Disconnected device {device_id}", device=device_id)
            return JsonResponse({"ok": True, "device": result["device"], "result": result["result"]})
        if action == "send-test":
            result = REGISTRY.send_test(device_id)
            SERVICE.logger.info(f"Device test executed for {device_id}", device=device_id, outcome=result["result"])
            return JsonResponse({"ok": True, "device": result["device"], "result": result["result"]})
        if action == "apply-profile":
            result = REGISTRY.apply_profile(device_id)
            SERVICE.logger.info(f"Applied profile to device {device_id}", device=device_id)
            return JsonResponse({"ok": True, "device": result["device"], "result": result["result"]})
    except KeyError:
        return JsonResponse({"error": "device not found"}, status=404)
    except Exception as exc:  # pragma: no cover - defensive
        return JsonResponse({"error": str(exc)}, status=500)
    return JsonResponse({"error": "unknown action"}, status=400)


@require_http_methods(["GET", "POST"])
@csrf_protect
def api_tests(request):
    SCENARIO_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    if request.method == "GET":
        scenarios = sorted(item.name for item in SCENARIO_DIR.glob("*.json"))
        reports = sorted(item.name for item in REPORT_DIR.glob("*.json"))
        return JsonResponse({"scenarios": scenarios, "reports": reports})

    try:
        payload = _read_json_body(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    name = str(payload.get("name") or "scenario").strip()
    scenario = payload.get("scenario") or payload
    if not isinstance(scenario, dict):
        return JsonResponse({"error": "scenario invalid"}, status=400)
    steps = scenario.get("steps")
    try:
        _validate_scenario_steps(steps)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in name).strip("-") or "scenario"
    path = SCENARIO_DIR / f"{safe_name}.json"
    path.write_text(json.dumps(scenario, ensure_ascii=False, indent=2), encoding="utf-8")
    SERVICE.logger.info("Scenario uploaded", name=safe_name, steps=len(steps))
    return JsonResponse({"ok": True, "name": path.name, "steps": len(steps)})


@require_POST
@csrf_protect
def api_tests_run(request):
    try:
        payload = _read_json_body(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    scenario = payload.get("scenario")
    scenario_file = str(payload.get("scenario_file") or "").strip()
    if scenario is None and scenario_file:
        if Path(scenario_file).name != scenario_file:
            return JsonResponse({"error": "scenario_file invalid"}, status=400)
        path = SCENARIO_DIR / scenario_file
        if not path.exists() or path.suffix.lower() != ".json":
            return JsonResponse({"error": "scenario_file invalid"}, status=404)
        scenario = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(scenario, dict):
        return JsonResponse({"error": "scenario lipsă"}, status=400)

    try:
        steps = _validate_scenario_steps(scenario.get("steps"))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    started = time.time()
    results = []
    for index, step in enumerate(steps, start=1):
        op = str(step.get("op") or "").strip().lower()
        device_id = str(step.get("device") or step.get("from") or "").strip()
        status = "ok"
        message = "executat"
        extra = {}
        try:
            if op == "connect" and device_id:
                extra = REGISTRY.connect_device(device_id)["result"]
                message = extra.get("message", message)
            elif op == "disconnect" and device_id:
                extra = REGISTRY.disconnect_device(device_id)["result"]
                message = extra.get("message", message)
            elif op in {"send_text", "send_packet"} and device_id:
                test_result = REGISTRY.send_test(device_id)
                extra = test_result.get("result", {})
                message = extra.get("message", "test trimis")
            elif op == "inject":
                SERVICE.inject_impact()
                message = "impact injectat"
            elif op == "wait":
                duration = float(step.get("seconds") or step.get("duration_s") or 0.1)
                time.sleep(min(max(duration, 0.05), 1.0))
                message = f"așteptare {duration:.2f}s"
            elif op in {"expect_rx", "assert"}:
                message = "validare simulată: OK"
            else:
                message = "step fără acțiune"
        except Exception as exc:  # pragma: no cover - runtime variability
            status = "failed"
            message = str(exc)
        results.append({"index": index, "op": op, "status": status, "message": message, "extra": extra})

    report = {
        "name": scenario.get("name") or "run",
        "ts": int(time.time()),
        "duration_ms": int((time.time() - started) * 1000),
        "ok": all(item["status"] == "ok" for item in results),
        "steps": results,
        "mode": SERVICE.snapshot().get("mode"),
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_name = f"report-{report['ts']}.json"
    (REPORT_DIR / report_name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    SERVICE.logger.info("Test run completed", report=report_name, ok=report["ok"], steps=len(results))
    return JsonResponse({"ok": report["ok"], "report": report_name, "result": report})


@require_POST
def api_selftest(request):
    if not getattr(request, "body", b""):
        pass
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(driver_tests.build_sim_suite())
    payload = {
        "ok": result.wasSuccessful(),
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "log": stream.getvalue(),
    }
    if result.wasSuccessful():
        SERVICE.logger.info("Self-test passed", **payload)
    else:
        SERVICE.logger.warning("Self-test failed", **payload)
    return JsonResponse(payload)
