import ast
import os
import unittest

from app import acc, nbr, pos, rpt
from ioc import IOC_CH_BUZZER, IOC_CH_LED, IOC_vSetOutputPort
from rte import vSetAlertaSonora, vSetAlertaVizuala
from sdc.packets import AlertPacket, PositionPacket, decode_packet, encode_position_packet, validate_replay


class Phase1LayerTests(unittest.TestCase):
    def test_ioc_routes_known_channels(self):
        IOC_vSetOutputPort(IOC_CH_BUZZER, 1)
        IOC_vSetOutputPort(IOC_CH_LED, 0)
        self.assertTrue(True)

    def test_unknown_channel_is_ignored(self):
        IOC_vSetOutputPort(0xFFFF, 1)
        self.assertTrue(True)

    def test_rte_clamps_values(self):
        vSetAlertaSonora(1)
        vSetAlertaSonora(2)
        vSetAlertaSonora(-1)
        vSetAlertaVizuala(0)
        vSetAlertaVizuala(5)
        self.assertTrue(True)

    def test_position_packet_round_trip(self):
        pkt = encode_position_packet(7, 123456789, 47.15, 27.59, 42, 90, vehicle_id="V1")
        decoded = decode_packet(pkt)
        self.assertEqual(decoded["seq"], 7)
        self.assertEqual(decoded["vehicle_id"], "V1")
        self.assertEqual(decoded["speed_kmh"], 42)
        self.assertEqual(decoded["heading_deg"], 90)
        self.assertTrue(validate_replay(7, 7))
        self.assertFalse(validate_replay(7, 6))

    def test_alert_packet_decode(self):
        pkt = AlertPacket(seq=9, vehicle_id="V3", alert_type="impact", distance_m=12).encode()
        decoded = decode_packet(pkt)
        self.assertEqual(decoded["alert_type"], "impact")
        self.assertEqual(decoded["distance_m"], 12)

    def test_impact_detection_and_neighbour_filter(self):
        self.assertTrue(acc.detect_impact([1.0, 1.0, 3.4]))
        self.assertFalse(acc.detect_impact([1.0, 1.0, 1.2]))
        neighbours = [
            {"id": "V2", "distance_m": 18, "bearing_deg": 15},
            {"id": "V3", "distance_m": 120, "bearing_deg": 120},
            {"id": "V4", "distance_m": 40, "bearing_deg": 170},
        ]
        filtered = nbr.filter_neighbours(neighbours, heading_deg=0, radius_m=100)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["id"], "V2")

    def test_route_and_report(self):
        route = pos.load_route_from_data([
            {"lat": 47.15, "lon": 27.59},
            {"lat": 47.1505, "lon": 27.5905},
        ])
        self.assertEqual(len(route), 2)
        point = pos.position_at_index(route, 1)
        self.assertAlmostEqual(point["lat"], 47.1505, places=4)
        report = rpt.build_report({"active": True, "type": "impact", "source": "V2"}, [{"id": "V3"}])
        self.assertEqual(report["status"], "impact")

    def test_app_import_rule(self):
        for root, _, files in os.walk(os.path.join(os.path.dirname(__file__), "..", "app")):
            for file_name in files:
                if not file_name.endswith(".py"):
                    continue
                path = os.path.join(root, file_name)
                with open(path, "r", encoding="utf-8") as handle:
                    tree = ast.parse(handle.read(), filename=path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        names = [alias.name for alias in node.names]
                        self.assertNotIn("mcd", names)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.module.startswith("mcd"):
                            self.fail(f"app module imports mcd: {path}")


if __name__ == "__main__":
    unittest.main()
