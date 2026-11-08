"""Serial transport for USB-connected Meshtastic or Zigbee devices."""

from __future__ import annotations

from datetime import datetime, timezone

from .transport import Transport

try:
    import serial  # type: ignore
except Exception:  # pragma: no cover - dependency is optional on desktop CI
    serial = None


class SerialTransport(Transport):
    """Minimal USB serial transport using pyserial when available."""

    def __init__(self, port: str = "/dev/ttyUSB0", *, name: str = "serial", baudrate: int = 115200, timeout: float = 0.5):
        super().__init__(name=name)
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._handle = None
        self._events: list[dict] = []
        self._error: str | None = None

    def open(self) -> bool:
        if serial is None:
            self._error = "pyserial not installed"
            self._connected = False
            return False
        try:
            self._handle = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        except Exception as exc:  # pragma: no cover - hardware-specific path
            self._error = str(exc)
            self._connected = False
            return False
        self._connected = True
        self._error = None
        self._events.append({
            "kind": "connect",
            "source": self.name,
            "ts": datetime.now(timezone.utc).isoformat(),
            "port": self.port,
        })
        return True

    def close(self) -> None:
        if self._handle is not None:
            try:
                self._handle.close()
            except Exception:
                pass
        self._handle = None
        self._connected = False

    def is_open(self) -> bool:
        return self._connected and self._handle is not None and self._handle.is_open

    def info(self) -> dict:
        return {
            "id": self.name,
            "name": self.name,
            "state": "connected" if self.is_open() else "disconnected",
            "transport": "serial",
            "port": self.port,
            "connected": self.is_open(),
            "error": self._error,
        }

    def send_text(self, dest: str, text: str) -> int:
        if not self.is_open():
            return 0
        payload = str(text).encode("utf-8")
        written = self._handle.write(payload)
        self._events.append({
            "kind": "tx",
            "source": self.name,
            "destination": str(dest),
            "payload": payload.decode("utf-8", errors="replace"),
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        return int(written)

    def send_packet(self, dest: str, payload: bytes, portnum: int = 256) -> int:
        if not self.is_open():
            return 0
        raw = bytes(payload)
        written = self._handle.write(raw)
        self._events.append({
            "kind": "tx",
            "source": self.name,
            "destination": str(dest),
            "payload": raw.hex(),
            "portnum": int(portnum),
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        return int(written)

    def poll(self) -> list[dict]:
        if not self.is_open() or self._handle is None:
            return []
        try:
            data = self._handle.read(self._handle.in_waiting or 64)
        except Exception:
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
        return {"transport": "serial", "port": self.port, "baudrate": self.baudrate, "timeout": self.timeout}

    def apply_config(self, diff: dict) -> dict:
        config = self.get_config()
        for key, value in diff.items():
            if isinstance(value, dict):
                config[key] = value.get("target", value.get("value", config.get(key)))
            else:
                config[key] = value
        return config
