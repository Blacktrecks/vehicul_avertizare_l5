"""Simple JSON registry for connected devices."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class DeviceRegistry:
    """Manage and persist a small list of configured devices."""

    def __init__(self, path: str | Path | None = None):
        if path is None:
            project_root = Path(__file__).resolve().parent.parent
            self.path = project_root / "data" / "devices.json"
        else:
            self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save([])

    def _load(self) -> list[dict[str, Any]]:
        try:
            content = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        if not content.strip():
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []

    def _save(self, devices: list[dict[str, Any]]) -> None:
        self.path.write_text(json.dumps(devices, indent=2), encoding="utf-8")

    def list_devices(self) -> list[dict[str, Any]]:
        return self._load()

    def get_device(self, device_id: str) -> dict[str, Any] | None:
        for device in self._load():
            if device.get("id") == device_id:
                return device
        return None

    def add_device(self, device: dict[str, Any]) -> dict[str, Any]:
        devices = self._load()
        record = dict(device)
        record.setdefault("id", f"d{len(devices) + 1}")
        record.setdefault("transport", "sim")
        record.setdefault("role", "Vehicul simulat")
        record.setdefault("state", "connected")
        devices.append(record)
        self._save(devices)
        return record

    def remove_device(self, device_id: str) -> bool:
        devices = self._load()
        filtered = [d for d in devices if d.get("id") != device_id]
        if len(filtered) == len(devices):
            return False
        self._save(filtered)
        return True

    def scan(self) -> list[dict[str, Any]]:
        devices = self._load()
        if devices:
            return devices
        default = [
            {"id": "V2", "label": "Heltec V3", "transport": "sim", "address": "sim://v3", "role": "Vehicul simulat V3", "state": "connected"},
            {"id": "V3", "label": "XIAO", "transport": "sim", "address": "sim://xiao", "role": "Vehicul simulat V2", "state": "connected"},
        ]
        self._save(default)
        return default
