import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sdc.registry import DeviceRegistry
from sdc.transport_sim import SimulatedTransport


class DeviceRegistryTests(unittest.TestCase):
    def test_simulated_transport_round_trip(self):
        transport = SimulatedTransport(name="V2")
        self.assertTrue(transport.open())
        self.assertEqual(transport.send_text("CTR", "hello"), 5)
        events = transport.poll()
        self.assertTrue(events)
        self.assertIn("hello", events[0]["payload"])
        self.assertEqual(transport.info()["state"], "connected")

    def test_registry_add_and_persist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = DeviceRegistry(Path(temp_dir) / "devices.json")
            registry.add_device({
                "id": "d1",
                "label": "Heltec V3",
                "transport": "sim",
                "address": "sim://v3",
                "role": "Vehicul simulat V3",
            })
            stored = registry.list_devices()
            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0]["label"], "Heltec V3")
            self.assertTrue((Path(temp_dir) / "devices.json").exists())

    def test_profile_diff_detects_mismatch(self):
        from sdc.profile import ProjectProfile

        profile = ProjectProfile(region="EU_868", preset="LONG_FAST", channel_name="VEH")
        target = {"region": "US_915", "preset": "LONG_FAST", "channel_name": "VEH"}
        diff = profile.diff(target)
        self.assertIn("region", diff)
        self.assertEqual(diff["region"]["current"], "EU_868")
        self.assertEqual(diff["region"]["target"], "US_915")

    def test_registry_scan_detects_serial_devices(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = DeviceRegistry(Path(temp_dir) / "devices.json")
            fake_ports = [
                {"device": "/dev/ttyACM0", "description": "Heltec Wireless Stick Lite V3", "vid": "0x1d50", "pid": "0x607f"},
                {"device": "/dev/ttyUSB0", "description": "USB Serial Device", "vid": "0x0403", "pid": "0x6001"},
            ]
            with patch("sdc.registry.scan_serial_ports", return_value=fake_ports):
                detected = registry.scan()
            self.assertTrue(any(item.get("address") == "/dev/ttyACM0" for item in detected))
            self.assertTrue(any(item.get("transport") == "serial" for item in detected))
            self.assertTrue(any(item.get("label") and "Heltec" in item.get("label") for item in detected))


if __name__ == "__main__":
    unittest.main()
