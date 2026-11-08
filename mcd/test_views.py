"""Teste pentru stratul Django (necesită Django: python manage.py test)."""
import os

from django.test import SimpleTestCase
from django.urls import reverse

from . import config, i2c, pcs, tim, usb


class ViewTests(SimpleTestCase):
    def setUp(self):
        old = os.environ.get(config.SIM_ENV)
        os.environ[config.SIM_ENV] = "1"

        def restore():
            pcs.PCS_vDeinit()
            i2c.I2C_vDeinit()
            usb.USB_vCloseAll()
            tim.TIM_vInit()
            if old is None:
                os.environ.pop(config.SIM_ENV, None)
            else:
                os.environ[config.SIM_ENV] = old

        self.addCleanup(restore)

    def test_index_shows_pin_table(self):
        resp = self.client.get(reverse("mcd:index"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Sistem Hibrid de Avertizare Vehicule")
        for row in config.PIN_TABLE:
            self.assertContains(resp, row["nume"])

    def test_api_pins(self):
        resp = self.client.get(reverse("mcd:api_pins"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["pins"]), len(config.PIN_TABLE))

    def test_api_accel_at_rest(self):
        resp = self.client.get(reverse("mcd:api_accel"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["simulated"])
        self.assertAlmostEqual(data["magnitude_g"], 1.0, delta=0.01)

    def test_api_dashboard(self):
        resp = self.client.get(reverse("mcd:api_dashboard"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("own_vehicle", data)
        self.assertIn("neighbors", data)
        self.assertIn("alerts", data)
        self.assertIn("accel_trend", data)
        self.assertEqual(data["own_vehicle"]["vehicle_id"], "VH-001")
        self.assertGreaterEqual(len(data["neighbors"]), 3)
        self.assertGreaterEqual(len(data["accel_trend"]), 10)
        self.assertIn(data["alerts"]["active"], (True, False))

    def test_api_selftest(self):
        resp = self.client.get(reverse("mcd:api_selftest"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"], data["log"])
        self.assertGreater(data["tests_run"], 30)

    def test_post_not_allowed(self):
        self.assertEqual(self.client.post(reverse("mcd:api_pins")).status_code, 405)
        self.assertEqual(self.client.post(reverse("mcd:api_dashboard")).status_code, 405)
