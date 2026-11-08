"""test.py – testează toate driverele MCD (cerința 2 din L4).

Rulare (din rădăcina proiectului):
    python -m mcd.test              # doar driverele, fără Django
    python manage.py test           # prin Django (descoperă și mcd/test.py)

Testele normale forțează simularea (MCD_SIMULATE=1), deci pot rula pe orice PC
și nu pornesc buzzerul real. Pe Raspberry Pi, pentru testul cu hardware real:
    MCD_HW_TESTS=1 python -m mcd.test HardwareSmokeTest
"""
import builtins
import io
import math
import os
import unittest

from . import config, i2c, mpu6050, pcs, tim, usb


# ------------------------------------------------------------------ utilitare
class FakeClock:
    """Ceas controlabil (secunde) pentru testele TIM."""

    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t


class _DriverTestCase(unittest.TestCase):
    MODE = "1"          # valoarea lui MCD_SIMULATE în timpul testului

    @staticmethod
    def _reset_drivers():
        pcs.PCS_vDeinit()
        i2c.I2C_vDeinit()
        usb.USB_vCloseAll()
        tim.TIM_vInit()

    def setUp(self):
        old = os.environ.get(config.SIM_ENV)
        os.environ[config.SIM_ENV] = self.MODE

        def restore():
            self._reset_drivers()
            if old is None:
                os.environ.pop(config.SIM_ENV, None)
            else:
                os.environ[config.SIM_ENV] = old

        self._reset_drivers()
        self.addCleanup(restore)


# ------------------------------------------------------------------------ PCS
class PcsTests(_DriverTestCase):
    def test_init_outputs_off_and_simulated(self):
        pcs.PCS_vInit()
        self.assertTrue(pcs.PCS_bIsSimulated())
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_BUZZER), pcs.PCS_PIN_OFF)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_LED), pcs.PCS_PIN_OFF)

    def test_set_buzzer_and_led(self):
        pcs.PCS_vSetOutputGpio(config.GPIO_BUZZER, pcs.PCS_PIN_ON)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_BUZZER), 1)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_LED), 0)
        pcs.PCS_vSetOutputGpio(config.GPIO_LED, pcs.PCS_PIN_ON)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_LED), 1)
        pcs.PCS_vSetOutputGpio(config.GPIO_BUZZER, pcs.PCS_PIN_OFF)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_BUZZER), 0)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_LED), 1)

    def test_invalid_pin_is_ignored(self):
        pcs.PCS_vInit()
        pcs.PCS_vSetOutputGpio(config.GPIO_BUZZER, 1)
        for bad in (28, 255, -1, "17", None, 3.5, True):
            pcs.PCS_vSetOutputGpio(bad, 1)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_BUZZER), 1)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_LED), 0)
        self.assertEqual(pcs.PCS_u8GetGpio(28), pcs.PCS_PIN_INVALID)

    def test_invalid_value_is_ignored(self):
        pcs.PCS_vSetOutputGpio(config.GPIO_BUZZER, 1)
        for bad in (2, -1, "1", None, 1.0):
            pcs.PCS_vSetOutputGpio(config.GPIO_BUZZER, bad)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_BUZZER), 1)

    def test_pin_range_limits(self):
        pcs.PCS_vSetOutputGpio(config.PCS_PIN_MIN, 1)
        pcs.PCS_vSetOutputGpio(config.PCS_PIN_MAX, 1)
        self.assertEqual(pcs.PCS_u8GetGpio(config.PCS_PIN_MIN), 1)
        self.assertEqual(pcs.PCS_u8GetGpio(config.PCS_PIN_MAX), 1)

    def test_input_pin_read(self):
        pcs.PCS_vConfigInput(5)
        self.assertEqual(pcs.PCS_u8GetGpio(5), 0)
        pcs.PCS_vSimSetInput(5, 1)
        self.assertEqual(pcs.PCS_u8GetGpio(5), 1)

    def test_output_on_input_pin_reconfigures(self):
        pcs.PCS_vConfigInput(5)
        pcs.PCS_vSetOutputGpio(5, 1)
        self.assertEqual(pcs.PCS_u8GetGpio(5), 1)

    def test_deinit_turns_outputs_off(self):
        pcs.PCS_vSetOutputGpio(config.GPIO_BUZZER, 1)
        pcs.PCS_vSetOutputGpio(config.GPIO_LED, 1)
        pcs.PCS_vDeinit()
        pcs.PCS_vInit()
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_BUZZER), 0)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_LED), 0)


# ------------------------------------------------------------------------ I2C
class I2cTests(_DriverTestCase):
    def test_who_am_i(self):
        self.assertTrue(i2c.I2C_bIsSimulated())
        self.assertEqual(i2c.I2C_u8ReadReg(config.MPU6050_ADDR, mpu6050.REG_WHO_AM_I), 0x68)

    def test_write_read_roundtrip(self):
        i2c.I2C_vWriteReg(config.MPU6050_ADDR, mpu6050.REG_SMPLRT_DIV, 0x42)
        self.assertEqual(i2c.I2C_u8ReadReg(config.MPU6050_ADDR, mpu6050.REG_SMPLRT_DIV), 0x42)

    def test_read_only_register_unchanged(self):
        i2c.I2C_vWriteReg(config.MPU6050_ADDR, mpu6050.REG_WHO_AM_I, 0x00)
        self.assertEqual(i2c.I2C_u8ReadReg(config.MPU6050_ADDR, mpu6050.REG_WHO_AM_I), 0x68)

    def test_block_read_length(self):
        data = i2c.I2C_lReadBlock(config.MPU6050_ADDR, mpu6050.REG_ACCEL_XOUT_H, 6)
        self.assertIsInstance(data, bytes)
        self.assertEqual(len(data), 6)

    def test_missing_device_raises_nack(self):
        with self.assertRaises(i2c.I2CError):
            i2c.I2C_u8ReadReg(0x50, 0x00)

    def test_invalid_arguments_raise_value_error(self):
        a = config.MPU6050_ADDR
        for call in (
            lambda: i2c.I2C_u8ReadReg(0x80, 0),
            lambda: i2c.I2C_u8ReadReg(True, 0),
            lambda: i2c.I2C_u8ReadReg(a, 256),
            lambda: i2c.I2C_vWriteReg(a, 0x19, -1),
            lambda: i2c.I2C_vWriteReg(a, 0x19, 256),
            lambda: i2c.I2C_lReadBlock(a, 0, 0),
            lambda: i2c.I2C_lReadBlock(a, 0, 33),
        ):
            with self.assertRaises(ValueError):
                call()

    def test_read_past_register_space_raises(self):
        with self.assertRaises(i2c.I2CError):
            i2c.I2C_lReadBlock(config.MPU6050_ADDR, 0xFE, 8)


# -------------------------------------------------------------------- MPU6050
class Mpu6050Tests(_DriverTestCase):
    def test_init_wakes_and_configures(self):
        mpu6050.MPU6050_vInit()
        a = config.MPU6050_ADDR
        self.assertEqual(i2c.I2C_u8ReadReg(a, mpu6050.REG_PWR_MGMT_1) & 0x40, 0)
        self.assertEqual(i2c.I2C_u8ReadReg(a, mpu6050.REG_ACCEL_CONFIG), 0x10)   # ±8 g
        self.assertEqual(mpu6050.MPU6050_u8ReadWhoAmI(), 0x68)

    def test_rest_reading_is_one_g_on_z(self):
        mpu6050.MPU6050_vInit()
        ax, ay, az = mpu6050.MPU6050_tReadG()
        self.assertAlmostEqual(ax, 0.0, delta=1e-3)
        self.assertAlmostEqual(ay, 0.0, delta=1e-3)
        self.assertAlmostEqual(az, 1.0, delta=1e-3)
        self.assertAlmostEqual(mpu6050.MPU6050_fReadMagnitudeG(), 1.0, delta=1e-3)

    def test_negative_values_are_signed(self):
        mpu6050.MPU6050_vInit()
        i2c.I2C_vSimSetAccelG(-2.0, 0.5, 1.0)
        raw = mpu6050.MPU6050_tReadRaw()
        self.assertEqual(raw[0], -8192)                    # -2 g la 4096 LSB/g
        g = mpu6050.MPU6050_tReadG()
        for got, want in zip(g, (-2.0, 0.5, 1.0)):
            self.assertAlmostEqual(got, want, delta=1 / 4096)

    def test_impact_magnitude(self):
        mpu6050.MPU6050_vInit()
        i2c.I2C_vSimSetAccelG(3.0, 2.0, 2.0)
        mag = mpu6050.MPU6050_fReadMagnitudeG()
        self.assertAlmostEqual(mag, math.sqrt(17), delta=0.01)
        self.assertGreater(mag, 2.5)

    def test_saturates_at_range_limit(self):
        mpu6050.MPU6050_vInit()
        i2c.I2C_vSimSetAccelG(20.0, 0.0, 0.0)
        self.assertAlmostEqual(mpu6050.MPU6050_tReadG()[0], 8.0, delta=0.01)

    def test_other_range(self):
        i2c.I2C_vSimSetAccelG(1.5, 0.0, 0.0)
        mpu6050.MPU6050_vInit(mpu6050.RANGE_2G)
        self.assertAlmostEqual(mpu6050.MPU6050_tReadG()[0], 1.5, delta=1 / 16384)

    def test_invalid_range(self):
        with self.assertRaises(ValueError):
            mpu6050.MPU6050_vInit(7)

    def test_wrong_who_am_i_rejected(self):
        i2c.I2C_vInit()
        i2c._sim_devices[config.MPU6050_ADDR].regs[0x75] = 0x70
        with self.assertRaises(i2c.I2CError):
            mpu6050.MPU6050_vInit()


# ------------------------------------------------------------------------ USB
class UsbTests(_DriverTestCase):
    def test_open_close(self):
        self.assertFalse(usb.USB_bIsOpen(config.USB_CH_ZIGBEE))
        usb.USB_vOpen(config.USB_CH_ZIGBEE)
        usb.USB_vOpen(config.USB_CH_ZIGBEE)                # idempotent
        self.assertTrue(usb.USB_bIsOpen(config.USB_CH_ZIGBEE))
        self.assertTrue(usb.USB_bIsSimulated(config.USB_CH_ZIGBEE))
        usb.USB_vClose(config.USB_CH_ZIGBEE)
        self.assertFalse(usb.USB_bIsOpen(config.USB_CH_ZIGBEE))

    def test_write_is_captured(self):
        usb.USB_vOpen(config.USB_CH_MESHTASTIC)
        self.assertEqual(usb.USB_u16Write(config.USB_CH_MESHTASTIC, b"\x01\x02\x03"), 3)
        self.assertEqual(usb.USB_u16Write(config.USB_CH_MESHTASTIC, bytearray(b"AB")), 2)
        self.assertEqual(usb.USB_baSimTakeTx(config.USB_CH_MESHTASTIC), b"\x01\x02\x03AB")
        self.assertEqual(usb.USB_baSimTakeTx(config.USB_CH_MESHTASTIC), b"")

    def test_read_partial_and_empty(self):
        ch = config.USB_CH_ZIGBEE
        usb.USB_vOpen(ch)
        self.assertEqual(usb.USB_baRead(ch), b"")
        usb.USB_vSimInject(ch, b"0123456789")
        self.assertEqual(usb.USB_u16Available(ch), 10)
        self.assertEqual(usb.USB_baRead(ch, 4), b"0123")
        self.assertEqual(usb.USB_baRead(ch), b"456789")
        self.assertEqual(usb.USB_u16Available(ch), 0)

    def test_flush(self):
        ch = config.USB_CH_ZIGBEE
        usb.USB_vOpen(ch)
        usb.USB_vSimInject(ch, b"xyz")
        usb.USB_vFlush(ch)
        self.assertEqual(usb.USB_u16Available(ch), 0)

    def test_channels_are_independent(self):
        usb.USB_vOpen(config.USB_CH_ZIGBEE)
        usb.USB_vOpen(config.USB_CH_MESHTASTIC)
        usb.USB_vSimInject(config.USB_CH_ZIGBEE, b"Z")
        usb.USB_u16Write(config.USB_CH_MESHTASTIC, b"M")
        self.assertEqual(usb.USB_u16Available(config.USB_CH_MESHTASTIC), 0)
        self.assertEqual(usb.USB_baSimTakeTx(config.USB_CH_ZIGBEE), b"")
        self.assertEqual(usb.USB_baSimTakeTx(config.USB_CH_MESHTASTIC), b"M")

    def test_closed_channel_raises(self):
        with self.assertRaises(usb.USBError):
            usb.USB_u16Write(config.USB_CH_ZIGBEE, b"x")
        with self.assertRaises(usb.USBError):
            usb.USB_baRead(config.USB_CH_ZIGBEE)

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            usb.USB_vOpen(99)
        usb.USB_vOpen(config.USB_CH_ZIGBEE)
        with self.assertRaises(ValueError):
            usb.USB_u16Write(config.USB_CH_ZIGBEE, "text")
        with self.assertRaises(ValueError):
            usb.USB_baRead(config.USB_CH_ZIGBEE, 0)

    def test_port_override_from_env(self):
        old = os.environ.get("MCD_ZIGBEE_PORT")
        os.environ["MCD_ZIGBEE_PORT"] = "/dev/ttyUSB7"
        try:
            self.assertEqual(config.usb_config(config.USB_CH_ZIGBEE)["port"], "/dev/ttyUSB7")
        finally:
            if old is None:
                os.environ.pop("MCD_ZIGBEE_PORT", None)
            else:
                os.environ["MCD_ZIGBEE_PORT"] = old


# ------------------------------------------------------------------------ TIM
class TimTests(_DriverTestCase):
    def setUp(self):
        super().setUp()
        self.clk = FakeClock(0.0)
        tim.TIM_vSetClock(self.clk)

    def test_periodic_fires_once_per_period(self):
        tim.TIM_vStart(tim.TIM_CH_1S, 1000)
        self.clk.t = 0.999
        self.assertFalse(tim.TIM_bHasElapsed(tim.TIM_CH_1S))
        self.clk.t = 1.0
        self.assertTrue(tim.TIM_bHasElapsed(tim.TIM_CH_1S))
        self.assertFalse(tim.TIM_bHasElapsed(tim.TIM_CH_1S))
        self.clk.t = 1.999
        self.assertFalse(tim.TIM_bHasElapsed(tim.TIM_CH_1S))
        self.clk.t = 2.0
        self.assertTrue(tim.TIM_bHasElapsed(tim.TIM_CH_1S))

    def test_missed_periods_resync_without_burst(self):
        tim.TIM_vStart(tim.TIM_CH_1S, 1000)
        self.clk.t = 5.5
        self.assertTrue(tim.TIM_bHasElapsed(tim.TIM_CH_1S))
        self.assertFalse(tim.TIM_bHasElapsed(tim.TIM_CH_1S))
        self.clk.t = 5.9
        self.assertFalse(tim.TIM_bHasElapsed(tim.TIM_CH_1S))
        self.clk.t = 6.0
        self.assertTrue(tim.TIM_bHasElapsed(tim.TIM_CH_1S))

    def test_channels_are_independent(self):
        tim.TIM_vStart(tim.TIM_CH_1S, 1000)
        tim.TIM_vStart(tim.TIM_CH_60S, 60000)
        self.clk.t = 1.0
        self.assertTrue(tim.TIM_bHasElapsed(tim.TIM_CH_1S))
        self.assertFalse(tim.TIM_bHasElapsed(tim.TIM_CH_60S))
        self.clk.t = 60.0
        self.assertTrue(tim.TIM_bHasElapsed(tim.TIM_CH_60S))

    def test_oneshot(self):
        tim.TIM_vStart(tim.TIM_CH_ALERT, 5000, tim.TIM_MODE_ONESHOT)
        self.assertTrue(tim.TIM_bIsRunning(tim.TIM_CH_ALERT))
        self.clk.t = 4.9
        self.assertFalse(tim.TIM_bHasElapsed(tim.TIM_CH_ALERT))
        self.clk.t = 5.0
        self.assertTrue(tim.TIM_bHasElapsed(tim.TIM_CH_ALERT))
        self.assertFalse(tim.TIM_bIsRunning(tim.TIM_CH_ALERT))
        self.clk.t = 50.0
        self.assertFalse(tim.TIM_bHasElapsed(tim.TIM_CH_ALERT))

    def test_stop(self):
        tim.TIM_vStart(tim.TIM_CH_1S, 1000)
        tim.TIM_vStop(tim.TIM_CH_1S)
        self.clk.t = 10.0
        self.assertFalse(tim.TIM_bIsRunning(tim.TIM_CH_1S))
        self.assertFalse(tim.TIM_bHasElapsed(tim.TIM_CH_1S))

    def test_invalid_arguments(self):
        for call in (
            lambda: tim.TIM_vStart(3, 1000),
            lambda: tim.TIM_vStart(-1, 1000),
            lambda: tim.TIM_vStart(tim.TIM_CH_1S, 0),
            lambda: tim.TIM_vStart(tim.TIM_CH_1S, 1000, mode=7),
            lambda: tim.TIM_bHasElapsed("a"),
            lambda: tim.TIM_vDelayMs(-5),
        ):
            with self.assertRaises(ValueError):
                call()

    def test_get_ms_and_32bit_wrap(self):
        self.clk.t = 12.5
        self.assertEqual(tim.TIM_u32GetMs(), 12500)
        self.clk.t = 4294967.5                              # 4294967500 ms > 2^32
        self.assertEqual(tim.TIM_u32GetMs(), 4294967500 - 2 ** 32)

    def test_real_clock_is_monotonic(self):
        tim.TIM_vInit()
        a = tim.TIM_u32GetMs()
        tim.TIM_vDelayMs(5)
        self.assertGreaterEqual(tim.TIM_u32GetMs() - a, 4)


# ---------------------------------------------- lanț complet: impact -> alertă
class AlertChainTests(_DriverTestCase):
    """Accelerometru -> buzzer + LED -> oprire la expirarea alertei (TIM)."""

    def test_impact_triggers_alert_and_expires(self):
        clk = FakeClock(0.0)
        tim.TIM_vSetClock(clk)
        mpu6050.MPU6050_vInit()
        self.assertLess(mpu6050.MPU6050_fReadMagnitudeG(), 2.5)      # repaus: fără alertă

        i2c.I2C_vSimSetAccelG(3.0, 2.0, 2.0)                          # impact simulat
        if mpu6050.MPU6050_fReadMagnitudeG() > 2.5:
            pcs.PCS_vSetOutputGpio(config.GPIO_BUZZER, pcs.PCS_PIN_ON)
            pcs.PCS_vSetOutputGpio(config.GPIO_LED, pcs.PCS_PIN_ON)
            tim.TIM_vStart(tim.TIM_CH_ALERT, 5000, tim.TIM_MODE_ONESHOT)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_BUZZER), 1)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_LED), 1)

        clk.t = 5.0
        if tim.TIM_bHasElapsed(tim.TIM_CH_ALERT):
            pcs.PCS_vSetOutputGpio(config.GPIO_BUZZER, pcs.PCS_PIN_OFF)
            pcs.PCS_vSetOutputGpio(config.GPIO_LED, pcs.PCS_PIN_OFF)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_BUZZER), 0)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_LED), 0)


class PcsChipSelectionTests(unittest.TestCase):
    def test_detect_gpiochip_from_env_override(self):
        old = os.environ.get("MCD_GPIOCHIP")
        os.environ["MCD_GPIOCHIP"] = "gpiochip3"
        try:
            self.assertEqual(pcs._resolve_gpiochip(), 3)
        finally:
            if old is None:
                os.environ.pop("MCD_GPIOCHIP", None)
            else:
                os.environ["MCD_GPIOCHIP"] = old

    def test_detect_gpiochip_pi4_layout(self):
        old = os.environ.get("MCD_GPIOCHIP")
        os.environ.pop("MCD_GPIOCHIP", None)
        original_glob = pcs.glob.glob
        original_exists = os.path.exists
        original_open = builtins.open
        original_lgpio = pcs.lgpio
        try:
            pcs.glob.glob = lambda pattern: ["/dev/gpiochip0", "/dev/gpiochip1"]
            os.path.exists = lambda path: path == "/sys/class/gpio/gpiochip1/label"

            def fake_open(path, mode="r", *args, **kwargs):
                if path == "/sys/class/gpio/gpiochip1/label":
                    return io.StringIO("pinctrl-bcm2711")
                raise FileNotFoundError(path)

            pcs.lgpio = type("FakeLgpio", (), {"gpio_get_chip_info": lambda self, chip: {"label": "pinctrl-bcm2711" if chip == 1 else "pinctrl-bcm2835"}, "gpiochip_open": lambda self, chip: chip, "gpiochip_close": lambda self, chip: None})()
            builtins.open = fake_open
            self.assertEqual(pcs._resolve_gpiochip(), 1)
        finally:
            pcs.glob.glob = original_glob
            os.path.exists = original_exists
            builtins.open = original_open
            pcs.lgpio = original_lgpio
            if old is None:
                os.environ.pop("MCD_GPIOCHIP", None)
            else:
                os.environ["MCD_GPIOCHIP"] = old

    def test_detect_gpiochip_pi5_layout_old_numbering(self):
        old = os.environ.get("MCD_GPIOCHIP")
        os.environ.pop("MCD_GPIOCHIP", None)
        original_glob = pcs.glob.glob
        original_exists = os.path.exists
        original_open = builtins.open
        original_lgpio = pcs.lgpio
        try:
            pcs.glob.glob = lambda pattern: ["/dev/gpiochip4", "/dev/gpiochip0"]
            os.path.exists = lambda path: path == "/sys/class/gpio/gpiochip4/label"

            def fake_open(path, mode="r", *args, **kwargs):
                if path == "/sys/class/gpio/gpiochip4/label":
                    return io.StringIO("pinctrl-rp1")
                raise FileNotFoundError(path)

            pcs.lgpio = type("FakeLgpio", (), {"gpio_get_chip_info": lambda self, chip: {"label": "pinctrl-rp1" if chip == 4 else "pinctrl-bcm2835"}, "gpiochip_open": lambda self, chip: chip, "gpiochip_close": lambda self, chip: None})()
            builtins.open = fake_open
            self.assertEqual(pcs._resolve_gpiochip(), 4)
        finally:
            pcs.glob.glob = original_glob
            os.path.exists = original_exists
            builtins.open = original_open
            pcs.lgpio = original_lgpio
            if old is None:
                os.environ.pop("MCD_GPIOCHIP", None)
            else:
                os.environ["MCD_GPIOCHIP"] = old

    def test_detect_gpiochip_by_label_when_available(self):
        old = os.environ.get("MCD_GPIOCHIP")
        os.environ.pop("MCD_GPIOCHIP", None)
        try:
            original_glob = pcs.glob.glob
            original_exists = os.path.exists
            original_open = builtins.open
            original_lgpio = pcs.lgpio
            try:
                pcs.glob.glob = lambda pattern: ["/dev/gpiochip4", "/dev/gpiochip0"]
                os.path.exists = lambda path: path == "/sys/class/gpio/gpiochip4/label"

                def fake_open(path, mode="r", *args, **kwargs):
                    if path == "/sys/class/gpio/gpiochip4/label":
                        return io.StringIO("pinctrl-rp1")
                    raise FileNotFoundError(path)

                pcs.lgpio = type("FakeLgpio", (), {"gpio_get_chip_info": lambda self, chip: {"label": "pinctrl-rp1" if chip == 4 else "pinctrl-bcm2835"}, "gpiochip_open": lambda self, chip: chip, "gpiochip_close": lambda self, chip: None})()
                builtins.open = fake_open
                self.assertEqual(pcs._resolve_gpiochip(), 4)
            finally:
                pcs.glob.glob = original_glob
                os.path.exists = original_exists
                builtins.open = original_open
                pcs.lgpio = original_lgpio
        finally:
            if old is None:
                os.environ.pop("MCD_GPIOCHIP", None)
            else:
                os.environ["MCD_GPIOCHIP"] = old


# -------------------------------------------------- hardware real (Raspberry Pi)
@unittest.skipUnless(os.environ.get("MCD_HW_TESTS") == "1",
                     "test hardware: setează MCD_HW_TESTS=1 pe Raspberry Pi")
class HardwareSmokeTest(_DriverTestCase):
    MODE = "0"

    def test_buzzer_and_led_pulse(self):
        for pin in (config.GPIO_LED, config.GPIO_BUZZER):
            pcs.PCS_vSetOutputGpio(pin, 1)
            tim.TIM_vDelayMs(150)
            pcs.PCS_vSetOutputGpio(pin, 0)
        self.assertFalse(pcs.PCS_bIsSimulated())

    def test_mpu6050_present(self):
        mpu6050.MPU6050_vInit()
        self.assertFalse(i2c.I2C_bIsSimulated())
        self.assertAlmostEqual(mpu6050.MPU6050_fReadMagnitudeG(), 1.0, delta=0.3)

    def test_usb_ports(self):
        found = 0
        for ch in config.usb_channels():
            if not os.path.exists(config.usb_config(ch)["port"]):
                continue
            usb.USB_vOpen(ch)
            self.assertFalse(usb.USB_bIsSimulated(ch))
            found += 1
        if not found:
            self.skipTest("niciun port USB conectat")


# ------------------------------------------------------------------- rulare
SIM_TEST_CLASSES = (PcsTests, I2cTests, Mpu6050Tests, UsbTests, TimTests, AlertChainTests)


def build_sim_suite():
    """Suita fără hardware (folosită și de pagina web de auto-test)."""
    loader = unittest.TestLoader()
    return unittest.TestSuite(loader.loadTestsFromTestCase(c) for c in SIM_TEST_CLASSES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
