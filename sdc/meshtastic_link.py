"""Meshtastic device wrapper for serial/TCP access with a simulated fallback."""

from __future__ import annotations

from typing import Any

from .transport_serial import SerialTransport
from .transport_sim import SimulatedTransport
from .transport_tcp import TCPTransport


class MeshtasticLink:
    """Thin adapter around the transport layer used by the app."""

    def __init__(self, *, port: str | None = None, host: str | None = None, portnum: int = 4403, name: str = "meshtastic"):
        self.name = name
        self.port = port or "/dev/ttyACM0"
        self.host = host
        self.portnum = int(portnum)
        if host:
            self.transport = TCPTransport(host=host, port=self.portnum, name=name)
        elif port:
            self.transport = SerialTransport(port=port, name=name, baudrate=115200)
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
        info.setdefault("role", "meshtastic")
        info["device_type"] = "meshtastic"
        return info
