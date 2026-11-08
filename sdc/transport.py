"""Abstract transport contract for Meshtastic/Zigbee device access."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Transport(ABC):
    """Common API for serial, TCP and simulated transports."""

    def __init__(self, name: str = "device"):
        self.name = name
        self._connected = False

    @abstractmethod
    def open(self) -> bool:
        """Open the device link."""

    @abstractmethod
    def close(self) -> None:
        """Close the device link."""

    @abstractmethod
    def is_open(self) -> bool:
        """Return True while the transport is active."""

    @abstractmethod
    def info(self) -> dict:
        """Return a metadata summary for the transport."""

    @abstractmethod
    def send_text(self, dest: str, text: str) -> int:
        """Send text data to a destination and return bytes/characters sent."""

    @abstractmethod
    def send_packet(self, dest: str, payload: bytes, portnum: int = 256) -> int:
        """Send a binary packet."""

    @abstractmethod
    def poll(self) -> list[dict]:
        """Return queued RX events."""

    @abstractmethod
    def get_config(self) -> dict:
        """Return current device configuration."""

    @abstractmethod
    def apply_config(self, diff: dict) -> dict:
        """Apply a configuration difference and return the resulting config."""
