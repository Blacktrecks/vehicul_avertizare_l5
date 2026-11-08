"""TCP transport for WiFi-connected Meshtastic devices."""

from __future__ import annotations

import socket
from datetime import datetime, timezone

from .transport import Transport


class TCPTransport(Transport):
    """Minimal TCP transport for Meshtastic over WiFi."""

    def __init__(self, host: str = "127.0.0.1", port: int = 4403, *, name: str = "tcp"):
        super().__init__(name=name)
        self.host = host
        self.port = int(port)
        self._sock: socket.socket | None = None
        self._events: list[dict] = []
        self._error: str | None = None

    def open(self) -> bool:
        try:
            self._sock = socket.create_connection((self.host, self.port), timeout=2)
        except OSError as exc:
            self._error = str(exc)
            self._connected = False
            return False
        self._connected = True
        self._error = None
        self._events.append({
            "kind": "connect",
            "source": self.name,
            "ts": datetime.now(timezone.utc).isoformat(),
            "host": self.host,
            "port": self.port,
        })
        return True

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        self._sock = None
        self._connected = False

    def is_open(self) -> bool:
        return self._connected and self._sock is not None

    def info(self) -> dict:
        return {
            "id": self.name,
            "name": self.name,
            "state": "connected" if self.is_open() else "disconnected",
            "transport": "tcp",
            "host": self.host,
            "port": self.port,
            "connected": self.is_open(),
            "error": self._error,
        }

    def send_text(self, dest: str, text: str) -> int:
        if not self.is_open() or self._sock is None:
            return 0
        payload = str(text).encode("utf-8")
        sent = self._sock.send(payload)
        self._events.append({
            "kind": "tx",
            "source": self.name,
            "destination": str(dest),
            "payload": str(text),
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        return int(sent)

    def send_packet(self, dest: str, payload: bytes, portnum: int = 256) -> int:
        if not self.is_open() or self._sock is None:
            return 0
        raw = bytes(payload)
        sent = self._sock.send(raw)
        self._events.append({
            "kind": "tx",
            "source": self.name,
            "destination": str(dest),
            "payload": raw.hex(),
            "portnum": int(portnum),
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        return int(sent)

    def poll(self) -> list[dict]:
        if not self.is_open() or self._sock is None:
            return []
        try:
            data = self._sock.recv(4096)
        except socket.timeout:
            data = b""
        except OSError:
            return []
        events: list[dict] = []
        if data:
            events.append({
                "kind": "rx",
                "source": self.name,
                "payload": data.hex(),
                "ts": datetime.now(timezone.utc).isoformat(),
            })
        events.extend(self._events)
        self._events.clear()
        return events

    def get_config(self) -> dict:
        return {"transport": "tcp", "host": self.host, "port": self.port}

    def apply_config(self, diff: dict) -> dict:
        config = self.get_config()
        for key, value in diff.items():
            if isinstance(value, dict):
                config[key] = value.get("target", value.get("value", config.get(key)))
            else:
                config[key] = value
        return config
