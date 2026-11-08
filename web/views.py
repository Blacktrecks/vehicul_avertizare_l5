import json

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from .service import StateService

SERVICE = StateService()


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


@require_POST
@csrf_protect
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


@require_POST
@csrf_protect
def api_outputs_off(request):
    SERVICE.set_outputs_off()
    return JsonResponse({"ok": True, "state": SERVICE.snapshot()})


@require_POST
@csrf_protect
def api_alert_ack(request):
    SERVICE.ack_alert()
    return JsonResponse({"ok": True, "state": SERVICE.snapshot()})


@require_POST
@csrf_protect
def api_sim_action(request):
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
    return JsonResponse({"logs": []})


@require_POST
@csrf_protect
def api_selftest(request):
    return JsonResponse({"ok": True, "name": "selftest"})
