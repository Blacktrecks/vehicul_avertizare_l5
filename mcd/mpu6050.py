"""Acces la accelerometrul MPU6050 peste driverul I2C (CF5: detecția impactului).

Stratul acesta doar citește senzorul; pragul de impact/frânare bruscă
aparține aplicației (modulul ACC din L3).
"""
import math
import struct

from . import config, i2c

REG_SMPLRT_DIV = 0x19
REG_CONFIG = 0x1A
REG_ACCEL_CONFIG = 0x1C
REG_ACCEL_XOUT_H = 0x3B
REG_PWR_MGMT_1 = 0x6B
REG_WHO_AM_I = 0x75

WHO_AM_I_VALUE = 0x68

RANGE_2G, RANGE_4G, RANGE_8G, RANGE_16G = 0, 1, 2, 3
_LSB_PER_G = {RANGE_2G: 16384.0, RANGE_4G: 8192.0, RANGE_8G: 4096.0, RANGE_16G: 2048.0}

_range = RANGE_8G


def MPU6050_vInit(range_sel=RANGE_8G):
    """Trezește senzorul, setează domeniul (implicit ±8 g) și filtrul (44 Hz, 100 Hz)."""
    global _range
    if range_sel not in _LSB_PER_G:
        raise ValueError("domeniu invalid: %r" % (range_sel,))
    addr = config.MPU6050_ADDR
    i2c.I2C_vInit()
    who = i2c.I2C_u8ReadReg(addr, REG_WHO_AM_I)
    if who != WHO_AM_I_VALUE:
        raise i2c.I2CError("WHO_AM_I neașteptat: 0x%02X (așteptat 0x%02X)"
                           % (who, WHO_AM_I_VALUE))
    i2c.I2C_vWriteReg(addr, REG_PWR_MGMT_1, 0x01)       # ieșire din sleep, ceas PLL
    i2c.I2C_vWriteReg(addr, REG_CONFIG, 0x03)           # DLPF 44 Hz
    i2c.I2C_vWriteReg(addr, REG_SMPLRT_DIV, 0x09)       # 1 kHz / (1+9) = 100 Hz
    i2c.I2C_vWriteReg(addr, REG_ACCEL_CONFIG, range_sel << 3)
    _range = range_sel


def MPU6050_u8ReadWhoAmI():
    return i2c.I2C_u8ReadReg(config.MPU6050_ADDR, REG_WHO_AM_I)


def MPU6050_tReadRaw():
    """(ax, ay, az) ca întregi cu semn pe 16 biți."""
    data = i2c.I2C_lReadBlock(config.MPU6050_ADDR, REG_ACCEL_XOUT_H, 6)
    return struct.unpack(">hhh", data)


def MPU6050_tReadG():
    """(ax, ay, az) în g, conform domeniului configurat."""
    lsb = _LSB_PER_G[_range]
    return tuple(v / lsb for v in MPU6050_tReadRaw())


def MPU6050_fReadMagnitudeG():
    """Modulul accelerației în g (≈1 g în repaus)."""
    ax, ay, az = MPU6050_tReadG()
    return math.sqrt(ax * ax + ay * ay + az * az)
