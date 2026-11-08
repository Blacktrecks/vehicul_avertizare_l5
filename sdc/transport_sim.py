"""Simulated device transport used for CI and local development."""

from __future__ import annotations

from datetime import datetime, timezone

from .transport import Transport


class SimulatedTransport(Transport):
    """Minimal in-memory simulator matching the transport contract."""

    def __init__(self, name: str = "sim"):
        super().__init__(name=name)
        self._events: list[dict] = []

    def open(self) -> bool:
        self._connected = True
        return True

    def close(self) -> None:
        self._connected = False

    def is_open(self) -> bool:
        return self._connected

    def info(self) -> dict:
        return {
            "id": self.name,
            "name": self.name,
            "state": "connected" if self._connected else "disconnected",
            "transport": "sim",
            "connected": self._connected,
        }

    def send_text(self, dest: str, text: str) -> int:
        payload = str(text)
        self._events.append({
            "kind": "tx",
            "source": self.name,
            "destination": str(dest),
            "payload": payload,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        return len(payload)

    def send_packet(self, dest: str, payload: bytes, portnum: int = 256) -> int:
        raw = bytes(payload)
        self._events.append({
            "kind": "tx",
            "source": self.name,
            "destination": str(dest),
            "payload": raw.hex(),
            "portnum": int(portnum),
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        return len(raw)

    def poll(self) -> list[dict]:
        events = list(self._events)
        self._events.clear()
        return events

    def get_config(self) -> dict:
        return {
            "region": "EU_868",
            "preset": "LONG_FAST",
            "channel_name": "VEH",
            "transport": "sim",
        }

    def apply_config(self, diff: dict) -> dict:
        config = self.get_config()
        for key, value in diff.items():
            if isinstance(value, dict):
                config[key] = value.get("target", value.get("value", config.get(key)))
            else:
                config[key] = value
        return config
