"""Simple JSON registry for connected devices."""

from __future__ import annotations

import json
import re
import socket
from pathlib import Path
from typing import Any


def _is_likely_hardware_serial_port(device: str, description: str = "", hwid: str = "") -> bool:
    """Keep only real USB serial devices and ignore Linux system console ports."""
    value = (device or "").lower()
    info = f"{description or ''} {hwid or ''}".lower()
    allowed_prefixes = (
        "/dev/ttyacm",
        "/dev/ttyusb",
        "/dev/tty.usb",
        "/dev/cu.usb",
        "/dev/rfcomm",
    )
    blocked_prefixes = (
        "/dev/ttys",
        "/dev/ttys",
        "/dev/ttyama",
        "/dev/tty0",
        "/dev/tty1",
        "/dev/tty2",
        "/dev/tty3",
        "/dev/tty4",
        "/dev/tty5",
        "/dev/tty6",
    )
    if any(value.startswith(prefix) for prefix in blocked_prefixes):
        return False
    if any(value.startswith(prefix) for prefix in allowed_prefixes):
        return True
    if any(keyword in info for keyword in ("meshtastic", "heltec", "zigbee", "xbee", "wireless stick", "usb serial")):
        return True
    return False


def scan_serial_ports() -> list[dict[str, Any]]:
    """Return serial port metadata for USB devices discovered on the host."""
    try:
        import serial.tools.list_ports as list_ports
    except Exception:
        return []

    discovered: list[dict[str, Any]] = []
    for port in list_ports.comports():
        if isinstance(port, dict):
            info = port
        else:
            info = {
                "device": getattr(port, "device", ""),
                "description": getattr(port, "description", "") or "",
                "hwid": getattr(port, "hwid", "") or "",
                "vid": getattr(port, "vid", None),
                "pid": getattr(port, "pid", None),
            }

        device = str(info.get("device") or "").strip()
        if not device:
            continue

        description = str(info.get("description") or "").strip()
        hwid = str(info.get("hwid") or "").strip()
        if not _is_likely_hardware_serial_port(device, description, hwid):
            continue

        paired = (info.get("vid") or "", info.get("pid") or "")
        label = description or device
        if not label or str(label).lower() in {"n/a", "na", "unknown"}:
            label = device
        if not label and hwid:
            label = hwid

        discovered.append({
            "device": device,
            "label": label,
            "description": description,
            "hwid": hwid,
            "vid": paired[0],
            "pid": paired[1],
        })
    return discovered


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

    def _save_device(self, updated: dict[str, Any]) -> dict[str, Any]:
        devices = self._load()
        for idx, item in enumerate(devices):
            if item.get("id") == updated.get("id"):
                devices[idx] = updated
                self._save(devices)
                return updated
        devices.append(updated)
        self._save(devices)
        return updated

    def _parse_tcp_endpoint(self, device: dict[str, Any]) -> tuple[str, int]:
        raw = str(device.get("address") or "").strip()
        if not raw:
            raise ValueError("Adresa TCP lipsește")

        if ":" in raw:
            host, port_text = raw.rsplit(":", 1)
            host = host.strip()
            port = int(port_text.strip() or "4403")
        else:
            host = raw
            port = int(device.get("port") or 4403)

        if not host:
            raise ValueError("Host TCP invalid")
        return host, port

    def _serial_probe(self, device: dict[str, Any]) -> None:
        port = str(device.get("port") or device.get("address") or "").strip()
        if not port:
            raise ValueError("Port serial lipsă")
        try:
            import serial
        except Exception as exc:
            raise RuntimeError("pyserial nu este instalat") from exc
        # Open+close validates that the serial port exists and is not busy.
        handle = serial.Serial(port=port, baudrate=115200, timeout=1)
        handle.close()

    def _tcp_probe(self, device: dict[str, Any]) -> None:
        host, port = self._parse_tcp_endpoint(device)
        with socket.create_connection((host, port), timeout=2):
            return

    def _build_link(self, device: dict[str, Any]):
        transport = str(device.get("transport") or "sim").strip().lower()
        address = str(device.get("address") or device.get("port") or "").strip()
        if transport in {"sim", "simulated"}:
            return None
        if transport in {"serial", "usb", "meshtastic", "lora"} and (address.startswith("/dev/") or "tty" in address.lower()):
            from .meshtastic_link import MeshtasticLink
            return MeshtasticLink(port=address, name=str(device.get("id") or "serial"))
        if transport in {"tcp", "wifi", "meshtastic", "lora"}:
            from .meshtastic_link import MeshtasticLink
            host, port = self._parse_tcp_endpoint(device)
            return MeshtasticLink(host=host, portnum=port, name=str(device.get("id") or "tcp"))
        return None

    def probe_device(self, device: dict[str, Any]) -> dict[str, Any]:
        transport = str(device.get("transport") or "sim").strip().lower()
        if transport in {"sim", "simulated"}:
            return {"ok": True, "message": "Dispozitiv simulat: OK"}
        try:
            if transport in {"serial", "usb"}:
                self._serial_probe(device)
                return {"ok": True, "message": "Port serial accesibil"}
            if transport in {"tcp", "wifi", "meshtastic", "lora"}:
                self._tcp_probe(device)
                return {"ok": True, "message": "Conexiune TCP activă"}
            return {"ok": False, "message": f"Transport necunoscut: {transport}"}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def connect_device(self, device_id: str) -> dict[str, Any]:
        device = self.get_device(device_id)
        if device is None:
            raise KeyError("device not found")
        result = self.probe_device(device)
        device["last_action"] = "connect"
        device["last_message"] = result["message"]
        device["state"] = "connected" if result["ok"] else "error"
        self._save_device(device)
        return {"device": device, "result": result}

    def disconnect_device(self, device_id: str) -> dict[str, Any]:
        device = self.get_device(device_id)
        if device is None:
            raise KeyError("device not found")
        device["state"] = "disconnected"
        device["last_action"] = "disconnect"
        device["last_message"] = "Dispozitiv deconectat logic"
        self._save_device(device)
        return {"device": device, "result": {"ok": True, "message": device["last_message"]}}

    def send_test(self, device_id: str) -> dict[str, Any]:
        device = self.get_device(device_id)
        if device is None:
            raise KeyError("device not found")

        link = self._build_link(device)
        if link is not None:
            try:
                link.connect()
                sent = link.send_text(str(device.get("id") or "pi"), "PING")
                status_ok = sent > 0 or link.is_connected()
                message = f"Ping OK ({sent} bytes sent)" if status_ok else "Ping failed"
                result = {"ok": status_ok, "message": message}
                if link.is_connected():
                    link.disconnect()
            except Exception as exc:  # pragma: no cover - hardware/network volatility
                result = {"ok": False, "message": str(exc)}
        else:
            result = self.probe_device(device)
            if result["ok"]:
                result["message"] = "Ping OK (simulated)"

        device["last_action"] = "send-test"
        device["last_test"] = "ok" if result["ok"] else "failed"
        device["last_message"] = result["message"]
        if result["ok"]:
            device["state"] = "connected"
        self._save_device(device)
        return {"device": device, "result": result}

    def scan(self) -> list[dict[str, Any]]:
        devices = self._load()
        ports = scan_serial_ports()
        if ports:
            detected = []
            seen: set[str] = set()
            for port in ports:
                device = str(port.get("device") or "").strip()
                if not device or device in seen:
                    continue
                description = str(port.get("description") or "").strip()
                hwid = str(port.get("hwid") or "").strip()
                if not _is_likely_hardware_serial_port(device, description, hwid):
                    continue
                seen.add(device)
                lower = f"{description} {hwid}".lower()
                transport = "serial"
                role = "Zigbee / USB"
                if "heltec" in lower or "meshtastic" in lower or "xiao" in lower or "esp32" in lower:
                    role = "Vehicul Meshtastic"
                elif "xbee" in lower or "zigbee" in lower:
                    role = "Zigbee"
                label = port.get("label") or description or device
                if not label or str(label).lower() in {"n/a", "na", "unknown"}:
                    label = device
                record = {
                    "id": re.sub(r"[^a-zA-Z0-9]+", "-", device).strip("-") or f"dev-{len(detected)+1}",
                    "label": label,
                    "type": "meshtastic" if ("heltec" in lower or "meshtastic" in lower or "xiao" in lower or "esp32" in lower) else "zigbee",
                    "transport": transport,
                    "address": device,
                    "port": device,
                    "role": role,
                    "state": "connected",
                    "description": description,
                    "hwid": hwid,
                }
                detected.append(record)
            if detected:
                self._save(detected)
                return detected
        if devices:
            return devices
        default = [
            {"id": "V2", "label": "Heltec V3", "transport": "sim", "address": "sim://v3", "role": "Vehicul simulat V3", "state": "connected"},
            {"id": "V3", "label": "XIAO", "transport": "sim", "address": "sim://xiao", "role": "Vehicul simulat V2", "state": "connected"},
        ]
        self._save(default)
        return default
