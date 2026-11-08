"""Driver I2C – magistrala I2C a Raspberry Pi (smbus2, /dev/i2c-1).

Fără smbus2 sau fără /dev/i2c-1 driverul folosește un MPU6050 simulat.
Argumente invalide -> ValueError; NACK / eroare de magistrală -> I2CError.
"""
import glob
import threading

from . import config

try:
    from smbus2 import SMBus
except ImportError:          # PC de dezvoltare
    SMBus = None


class I2CError(OSError):
    """Eroare de magistrală I2C (NACK, dispozitiv absent, bus închis)."""


_MAX_BLOCK = 32
_lock = threading.RLock()
_initialized = False
_simulated = True
_bus = None
_sim_devices = {}            # adresă -> dispozitiv simulat


# ------------------------------------------------------------ MPU6050 simulat
class _SimMPU6050:
    """Model minimal al registrelor MPU6050 (WHO_AM_I, putere, accelerație)."""

    _LSB_PER_G = (16384.0, 8192.0, 4096.0, 2048.0)

    def __init__(self):
        self.regs = bytearray(256)
        self.regs[0x75] = 0x68       # WHO_AM_I
        self.regs[0x6B] = 0x40       # PWR_MGMT_1: sleep la reset
        self.g = (0.0, 0.0, 1.0)     # în repaus: 1 g pe Z
        self._refresh()

    def _refresh(self):
        lsb = self._LSB_PER_G[(self.regs[0x1C] >> 3) & 0x03]
        for i, g in enumerate(self.g):
            raw = max(-32768, min(32767, int(round(g * lsb))))
            raw &= 0xFFFF
            self.regs[0x3B + 2 * i] = raw >> 8
            self.regs[0x3C + 2 * i] = raw & 0xFF

    def read(self, reg, length):
        if reg + length > 256:
            raise I2CError("citire în afara spațiului de registre")
        return bytes(self.regs[reg:reg + length])

    def write(self, reg, value):
        if reg in (0x75, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40):
            return                   # registre doar-citire
        self.regs[reg] = value
        if reg == 0x1C:
            self._refresh()

    def set_g(self, ax, ay, az):
        self.g = (float(ax), float(ay), float(az))
        self._refresh()


# ----------------------------------------------------------------- validare
def _check_addr(addr):
    if not isinstance(addr, int) or isinstance(addr, bool) or not 0 <= addr <= 0x7F:
        raise ValueError("adresă I2C invalidă: %r" % (addr,))


def _check_byte(value, what):
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 0xFF:
        raise ValueError("%s invalid: %r" % (what, value))


def _hw_available():
    return SMBus is not None and bool(glob.glob("/dev/i2c-*"))


# --------------------------------------------------------------------- API
def I2C_vInit(bus_id=None):
    """Inițializează magistrala (idempotent)."""
    global _initialized, _simulated, _bus
    with _lock:
        if _initialized:
            return
        _simulated = config.use_simulation(_hw_available())
        if _simulated:
            _sim_devices.clear()
            _sim_devices[config.MPU6050_ADDR] = _SimMPU6050()
        else:
            if SMBus is None:
                raise I2CError("smbus2 nu este instalat (pip install smbus2)")
            try:
                _bus = SMBus(config.I2C_BUS_ID if bus_id is None else bus_id)
            except OSError as exc:
                raise I2CError("nu pot deschide magistrala I2C: %s" % exc) from exc
        _initialized = True


def I2C_vDeinit():
    global _initialized, _simulated, _bus
    with _lock:
        if _bus is not None:
            _bus.close()
        _bus = None
        _sim_devices.clear()
        _initialized = False
        _simulated = True


def I2C_bIsSimulated():
    with _lock:
        return _simulated if _initialized else config.use_simulation(_hw_available())


def I2C_u8ReadReg(addr, reg):
    """Citește un registru de 8 biți."""
    return I2C_lReadBlock(addr, reg, 1)[0]


def I2C_vWriteReg(addr, reg, value):
    """Scrie un registru de 8 biți."""
    _check_addr(addr)
    _check_byte(reg, "registru")
    _check_byte(value, "valoare")
    with _lock:
        I2C_vInit()
        if _simulated:
            _sim_device(addr).write(reg, value)
            return
        try:
            _bus.write_byte_data(addr, reg, value)
        except OSError as exc:
            raise I2CError("scriere I2C eșuată (0x%02X): %s" % (addr, exc)) from exc


def I2C_lReadBlock(addr, reg, length):
    """Citește `length` (1..32) octeți începând de la `reg`."""
    _check_addr(addr)
    _check_byte(reg, "registru")
    if not isinstance(length, int) or isinstance(length, bool) or not 1 <= length <= _MAX_BLOCK:
        raise ValueError("lungime invalidă: %r" % (length,))
    with _lock:
        I2C_vInit()
        if _simulated:
            return _sim_device(addr).read(reg, length)
        try:
            return bytes(_bus.read_i2c_block_data(addr, reg, length))
        except OSError as exc:
            raise I2CError("citire I2C eșuată (0x%02X): %s" % (addr, exc)) from exc


def _sim_device(addr):
    dev = _sim_devices.get(addr)
    if dev is None:
        raise I2CError("NACK: niciun dispozitiv la adresa 0x%02X" % addr)
    return dev


def I2C_vSimSetAccelG(ax, ay, az):
    """Doar în simulare: impune accelerația (în g) raportată de MPU6050."""
    with _lock:
        I2C_vInit()
        if not _simulated:
            raise RuntimeError("I2C_vSimSetAccelG este disponibil doar în simulare")
        _sim_devices[config.MPU6050_ADDR].set_g(ax, ay, az)
