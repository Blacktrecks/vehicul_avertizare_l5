"""Meshtastic device wrapper for serial/TCP access with a simulated fallback."""

from __future__ import annotations

from typing import Any

try:
    from meshtastic.serial_interface import SerialInterface  # type: ignore
    from meshtastic.tcp_interface import TCPInterface  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    SerialInterface = None
    TCPInterface = None

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
        self._iface = None
        self._backend = "transport"
        if host:
            self.transport = TCPTransport(host=host, port=self.portnum, name=name)
        elif port:
            self.transport = SerialTransport(port=port, name=name, baudrate=115200)
        else:
            self.transport = SimulatedTransport(name=name)

    def connect(self) -> bool:
        if self.host and TCPInterface is not None:
            try:
                self._iface = TCPInterface(hostname=self.host)
                self._backend = "meshtastic"
                return True
            except Exception:
                self._iface = None
        if self.port and SerialInterface is not None:
            try:
                self._iface = SerialInterface(devPath=self.port)
                self._backend = "meshtastic"
                return True
            except Exception:
                self._iface = None
        self._backend = "transport"
        return bool(self.transport.open())

    def disconnect(self) -> None:
        if self._iface is not None:
            try:
                self._iface.close()
            except Exception:
                pass
            self._iface = None
        self.transport.close()

    def is_connected(self) -> bool:
        if self._iface is not None:
            return True
        return bool(self.transport.is_open())

    def send_text(self, dest: str, text: str) -> int:
        if self._iface is not None:
            payload = str(text)
            destination = str(dest or "^all")
            try:
                self._iface.sendText(text=payload, destinationId=destination, wantAck=False)
            except TypeError:
                self._iface.sendText(payload, destinationId=destination)
            return len(payload.encode("utf-8", errors="replace"))
        return int(self.transport.send_text(dest, text))

    def send_packet(self, dest: str, payload: bytes, portnum: int = 256) -> int:
        if self._iface is not None:
            raw = bytes(payload)
            destination = str(dest or "^all")
            try:
                self._iface.sendData(raw, destinationId=destination, portNum=int(portnum), wantAck=False)
            except TypeError:
                self._iface.sendData(raw, destinationId=destination)
            return len(raw)
        return int(self.transport.send_packet(dest, payload, portnum=portnum))

    def poll(self) -> list[dict[str, Any]]:
        return list(self.transport.poll())

    def info(self) -> dict[str, Any]:
        info = self.transport.info()
        info.setdefault("role", "meshtastic")
        info["device_type"] = "meshtastic"
        info["backend"] = self._backend
        info["meshtastic_lib"] = SerialInterface is not None
        return info
