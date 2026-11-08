"""USB Zigbee transport for XBee-like adapters."""

from __future__ import annotations

from .transport_serial import SerialTransport


class ZigbeeTransport(SerialTransport):
    """Transport wrapper tuned for Zigbee/XBee serial links."""

    def __init__(self, port: str = "/dev/ttyUSB0", *, name: str = "zigbee", baudrate: int = 9600, timeout: float = 0.5):
        super().__init__(port=port, name=name, baudrate=baudrate, timeout=timeout)

    def info(self) -> dict:
        payload = super().info()
        payload["transport"] = "zigbee"
        payload["radio"] = "zigbee"
        return payload

    def get_config(self) -> dict:
        config = super().get_config()
        config["transport"] = "zigbee"
        config["radio"] = "zigbee"
        return config
