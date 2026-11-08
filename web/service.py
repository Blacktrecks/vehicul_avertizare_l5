import json
import threading
import time


class SimulatedFleet:
    def __init__(self):
        self._vehicles = [
            {"id": "V2", "distance_m": 32, "bearing_deg": 18, "speed_kmh": 41, "heading_deg": 88, "source": "zigbee"},
            {"id": "V3", "distance_m": 68, "bearing_deg": 72, "speed_kmh": 36, "heading_deg": 96, "source": "lora"},
            {"id": "V4", "distance_m": 86, "bearing_deg": 145, "speed_kmh": 29, "heading_deg": 112, "source": "zigbee"},
        ]
        self.running = True

    def snapshot(self):
        return {
            "neighbours": [dict(item) for item in self._vehicles],
            "count": len(self._vehicles),
        }

    def inject_impact(self):
        self._vehicles[0]["distance_m"] = 18
        self._vehicles[0]["bearing_deg"] = 12


class StateService:
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._fleet = SimulatedFleet()
        self._state = {
            "v": 2,
            "ts": time.time(),
            "mode": "simulation",
            "ego": {"id": "V1", "lat": 47.15, "lon": 27.59, "speed_kmh": 42, "heading_deg": 90},
            "neighbours": [],
            "alert": {"active": False, "type": None, "source": None, "distance_m": None, "expires_in_s": None},
            "outputs": {"buzzer": 0, "led": 0},
            "accel": {"ax": 0.0, "ay": 0.0, "az": 1.0, "mag": 1.0, "threshold": 2.5},
            "links": {
                "zigbee": {"state": "ok", "last_rx_s": 0.4, "rx": 120, "tx": 120, "err": 0},
                "meshtastic": {"state": "ok", "last_rx_s": 12.0, "rx": 4, "tx": 4, "err": 0},
            },
            "devices": [
                {"id": "ZB-01", "type": "zigbee", "port": "/dev/ttyUSB0", "status": "online", "rssi_dbm": -60},
                {"id": "MS-02", "type": "meshtastic", "port": "/dev/ttyACM0", "status": "online", "rssi_dbm": -68},
                {"id": "MPU-6050", "type": "i2c", "port": "I2C-1", "status": "online", "rssi_dbm": None},
            ],
            "stats": {"pdr_pct": 96.0, "latency_ms": {"min": 210, "avg": 480, "p95": 900}, "alerts": 3, "false_alarms": 0, "rejected": 2},
            "drivers": {"gpio": "simulated", "i2c": "simulated", "usb_zigbee": "simulated", "usb_meshtastic": "simulated"},
        }

    def snapshot(self):
        with self._lock:
            fleet = self._fleet.snapshot()
            self._state["neighbours"] = [{
                "id": item["id"],
                "source": item["source"],
                "lat": 47.1500 + idx * 0.0002,
                "lon": 27.5900 + idx * 0.0003,
                "speed_kmh": item["speed_kmh"],
                "heading_deg": item["heading_deg"],
                "distance_m": item["distance_m"],
                "bearing_deg": item["bearing_deg"],
                "relevant": item["distance_m"] <= 100,
                "age_s": round(0.5 + idx * 0.3, 1),
            } for idx, item in enumerate(fleet["neighbours"]) ]
            self._state["ts"] = time.time()
            return json.loads(json.dumps(self._state))

    def set_output(self, channel, value, duration_ms=None):
        with self._lock:
            if channel not in ("buzzer", "led"):
                raise ValueError("canal invalid")
            if value not in (0, 1):
                raise ValueError("valoare invalidă")
            self._state["outputs"][channel] = int(value)
            if duration_ms is not None:
                self._state["outputs"][f"{channel}_ttl_ms"] = int(duration_ms)

    def set_outputs_off(self):
        with self._lock:
            self._state["outputs"]["buzzer"] = 0
            self._state["outputs"]["led"] = 0

    def ack_alert(self):
        with self._lock:
            self._state["alert"]["active"] = False
            self._state["alert"]["type"] = None
            self._state["alert"]["source"] = None
            self._state["alert"]["distance_m"] = None
            self._state["alert"]["expires_in_s"] = None

    def set_mode(self, mode):
        with self._lock:
            normalized = str(mode or "").strip().lower()
            if normalized in ("sim", "simulation", "virtual"):
                self._state["mode"] = "simulation"
                self._state["drivers"] = {"gpio": "simulated", "i2c": "simulated", "usb_zigbee": "simulated", "usb_meshtastic": "simulated"}
            elif normalized in ("hw", "hardware", "real"):
                self._state["mode"] = "hardware"
                self._state["drivers"] = {"gpio": "hardware", "i2c": "hardware", "usb_zigbee": "hardware", "usb_meshtastic": "hardware"}
            else:
                raise ValueError("mod invalid: alege simulation sau hardware")

    def inject_impact(self):
        self._fleet.inject_impact()
        with self._lock:
            self._state["alert"] = {
                "active": True,
                "type": "impact",
                "source": "V2",
                "distance_m": 18,
                "expires_in_s": 5,
            }

    def start(self):
        self._fleet.running = True
        self.set_mode("virtual")

    def pause(self):
        self._fleet.running = False

    def stop(self):
        self._fleet.running = False
        self.set_outputs_off()
        self.ack_alert()
