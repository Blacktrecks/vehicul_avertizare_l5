"""Report builder for the APP layer."""


def build_report(alert, neighbours):
    if alert is None:
        return {"status": "clear", "neighbour_count": len(neighbours or [])}
    alert_type = str(alert.get("type", "alert"))
    return {
        "status": alert_type,
        "source": alert.get("source", "unknown"),
        "neighbour_count": len(neighbours or []),
        "active": bool(alert.get("active", False)),
    }
