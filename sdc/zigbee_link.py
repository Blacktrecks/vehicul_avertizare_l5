"""Zigbee link wrapper around the serial transport layer."""

from __future__ import annotations

from typing import Any

from .transport_sim import SimulatedTransport
from .transport_zigbee import ZigbeeTransport


class ZigbeeLink:
    """Simple wrapper exposing a Zigbee transport for the app."""

    def __init__(self, *, port: str | None = None, name: str = "zigbee"):
        self.name = name
        self.port = port or "/dev/ttyUSB0"
        if port:
            self.transport = ZigbeeTransport(port=port, name=name, baudrate=9600)
        else:
            self.transport = SimulatedTransport(name=name)

    def connect(self) -> bool:
        return bool(self.transport.open())

    def disconnect(self) -> None:
        self.transport.close()

    def is_connected(self) -> bool:
        return bool(self.transport.is_open())

    def send_text(self, dest: str, text: str) -> int:
        return int(self.transport.send_text(dest, text))

    def send_packet(self, dest: str, payload: bytes, portnum: int = 256) -> int:
        return int(self.transport.send_packet(dest, payload, portnum=portnum))

    def poll(self) -> list[dict[str, Any]]:
        return list(self.transport.poll())

    def info(self) -> dict[str, Any]:
        info = self.transport.info()
        info.setdefault("role", "zigbee")
        info["device_type"] = "zigbee"
        return info
