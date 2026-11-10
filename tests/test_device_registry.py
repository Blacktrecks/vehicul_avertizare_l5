import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sdc.registry import DeviceRegistry
from sdc.transport_sim import SimulatedTransport
from web.service import LogStore


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

    def test_registry_scan_filters_system_serial_ports(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = DeviceRegistry(Path(temp_dir) / "devices.json")
            fake_ports = [
                {"device": "/dev/ttyS4", "description": "n/a", "vid": "0x1d50", "pid": "0x607f"},
                {"device": "/dev/ttyACM0", "description": "Heltec Wireless Stick Lite V3", "vid": "0x1d50", "pid": "0x607f"},
                {"device": "/dev/ttyUSB0", "description": "USB Serial Device", "vid": "0x0403", "pid": "0x6001"},
            ]
            with patch("sdc.registry.scan_serial_ports", return_value=fake_ports):
                detected = registry.scan()
            addresses = {item.get("address") for item in detected}
            self.assertNotIn("/dev/ttyS4", addresses)
            self.assertIn("/dev/ttyACM0", addresses)
            self.assertIn("/dev/ttyUSB0", addresses)

    def test_registry_connect_and_send_test_run_real_device_actions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = DeviceRegistry(Path(temp_dir) / "devices.json")
            registry.add_device({
                "id": "mesh-demo",
                "label": "Heltec V3",
                "transport": "sim",
                "address": "sim://mesh-demo",
                "role": "Vehicul simulat V3",
                "state": "disconnected",
            })
            with patch.object(DeviceRegistry, "probe_device", return_value={"ok": True, "message": "Meshtastic reachable"}):
                connected = registry.connect_device("mesh-demo")
                self.assertEqual(connected["device"]["state"], "connected")
                self.assertEqual(connected["result"]["message"], "Meshtastic reachable")

            with patch.object(DeviceRegistry, "probe_device", return_value={"ok": True, "message": "Test network OK"}):
                result = registry.send_test("mesh-demo")
                self.assertEqual(result["device"]["last_action"], "send-test")
                self.assertEqual(result["device"]["last_test"], "ok")
                self.assertIn("test", result["device"]["last_message"].lower())
                self.assertIn("simulat", result["device"]["last_message"].lower())

    def test_registry_disconnect_marks_device_state_and_returns_clear_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = DeviceRegistry(Path(temp_dir) / "devices.json")
            registry.add_device({
                "id": "mesh-off",
                "label": "LoRa Node",
                "transport": "sim",
                "address": "sim://mesh-off",
                "role": "Vehicul simulat",
                "state": "connected",
            })

            disconnected = registry.disconnect_device("mesh-off")
            self.assertEqual(disconnected["device"]["state"], "disconnected")
            self.assertIn("deconectat", disconnected["result"]["message"].lower())

    def test_profile_preview_and_apply(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = DeviceRegistry(Path(temp_dir) / "devices.json")
            registry.add_device({
                "id": "xiao-1",
                "label": "XIAO",
                "transport": "sim",
                "address": "sim://xiao-1",
                "region": "US_915",
                "preset": "SHORT_FAST",
                "channel_name": "LAB",
            })
            preview = registry.profile_preview("xiao-1")
            self.assertFalse(preview["compatible"])
            self.assertIn("region", preview["diff"])

            applied = registry.apply_profile("xiao-1")
            self.assertTrue(applied["result"]["ok"])
            self.assertEqual(applied["device"]["region"], "EU_868")
            self.assertEqual(applied["device"]["preset"], "LONG_FAST")
            self.assertEqual(applied["device"]["channel_name"], "VEH")

    def test_scan_preserves_disconnected_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = DeviceRegistry(Path(temp_dir) / "devices.json")
            registry.add_device({
                "id": "dev-ttyacm0",
                "label": "XIAO",
                "transport": "serial",
                "address": "/dev/ttyACM0",
                "port": "/dev/ttyACM0",
                "state": "disconnected",
            })
            fake_ports = [{"device": "/dev/ttyACM0", "description": "XIAO ESP32S3", "hwid": "USB"}]
            with patch("sdc.registry.scan_serial_ports", return_value=fake_ports):
                devices = registry.scan()
            self.assertEqual(devices[0]["state"], "disconnected")

    def test_log_store_records_and_reads_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logger = LogStore(path=Path(temp_dir) / "vehicul.log")
            logger.info("system started")
            logger.warning("link weak")
            entries = logger.read()
            self.assertTrue(any("system started" in entry.get("message", "") for entry in entries))
            self.assertTrue(any("link weak" in entry.get("message", "") for entry in entries))


if __name__ == "__main__":
    unittest.main()
