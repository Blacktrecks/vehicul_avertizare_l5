import io
import json
import unittest

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from mcd import test as driver_tests
from sdc.registry import DeviceRegistry
from .service import StateService

SERVICE = StateService()
REGISTRY = DeviceRegistry()


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
            device = REGISTRY.get_device(device_id)
            device["last_action"] = "apply-profile"
            device["last_message"] = "Profile loaded: EU_868 / LONG_FAST / VEH"
            device["state"] = "connected"
            REGISTRY._save_device(device)
            SERVICE.logger.info(f"Applied profile to device {device_id}", device=device_id)
            return JsonResponse({"ok": True, "device": device})
    except KeyError:
        return JsonResponse({"error": "device not found"}, status=404)
    except Exception as exc:  # pragma: no cover - defensive
        return JsonResponse({"error": str(exc)}, status=500)
    return JsonResponse({"error": "unknown action"}, status=400)


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
