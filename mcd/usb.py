"""Driver USB (port serial) – XBee3 Zigbee și modul ESP Meshtastic (pyserial).

Acces prin polling, fără blocare. Fără pyserial sau fără portul /dev/tty*
canalul rulează în simulare (buffer TX/RX în memorie).
Argumente invalide -> ValueError; port închis / eroare -> USBError.
"""
import os
import threading

from . import config

try:
    import serial
except ImportError:          # PC de dezvoltare
    serial = None


class USBError(OSError):
    """Eroare de port USB (port absent, închis, eroare de I/O)."""


_lock = threading.RLock()
_channels = {}               # canal -> {"sim", "ser", "rx", "tx"}


def _cfg(channel):
    return config.usb_config(channel)      # ValueError pentru canal invalid


def _get_open(channel):
    ch = _channels.get(channel)
    if ch is None:
        _cfg(channel)
        raise USBError("canalul USB %r nu este deschis" % (channel,))
    return ch


def USB_vOpen(channel):
    """Deschide canalul (idempotent)."""
    cfg = _cfg(channel)
    with _lock:
        if channel in _channels:
            return
        hw = serial is not None and os.path.exists(cfg["port"])
        if config.use_simulation(hw):
            _channels[channel] = {"sim": True, "ser": None,
                                  "rx": bytearray(), "tx": bytearray()}
            return
        if serial is None:
            raise USBError("pyserial nu este instalat (pip install pyserial)")
        try:
            ser = serial.Serial(cfg["port"], cfg["baud"], timeout=0, write_timeout=1.0)
        except (OSError, serial.SerialException) as exc:
            raise USBError("nu pot deschide %s: %s" % (cfg["port"], exc)) from exc
        _channels[channel] = {"sim": False, "ser": ser, "rx": None, "tx": None}


def USB_vClose(channel):
    _cfg(channel)
    with _lock:
        ch = _channels.pop(channel, None)
        if ch and ch["ser"] is not None:
            ch["ser"].close()


def USB_vCloseAll():
    with _lock:
        for channel in list(_channels):
            USB_vClose(channel)


def USB_bIsOpen(channel):
    _cfg(channel)
    with _lock:
        return channel in _channels


def USB_bIsSimulated(channel):
    with _lock:
        return _get_open(channel)["sim"]


def USB_u16Write(channel, data):
    """Trimite octeți; returnează numărul de octeți scriși."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise ValueError("data trebuie să fie bytes")
    with _lock:
        ch = _get_open(channel)
        if ch["sim"]:
            ch["tx"].extend(data)
            return len(data)
        try:
            return int(ch["ser"].write(bytes(data)))
        except (OSError, serial.SerialException) as exc:
            raise USBError("scriere USB eșuată: %s" % exc) from exc


def USB_u16Available(channel):
    """Numărul de octeți primiți și neciți."""
    with _lock:
        ch = _get_open(channel)
        return len(ch["rx"]) if ch["sim"] else int(ch["ser"].in_waiting)


def USB_baRead(channel, max_len=256):
    """Citește fără blocare până la `max_len` octeți (b"" dacă nu e nimic)."""
    if not isinstance(max_len, int) or isinstance(max_len, bool) or max_len < 1:
        raise ValueError("max_len invalid: %r" % (max_len,))
    with _lock:
        ch = _get_open(channel)
        if ch["sim"]:
            out = bytes(ch["rx"][:max_len])
            del ch["rx"][:max_len]
            return out
        try:
            n = min(int(ch["ser"].in_waiting), max_len)
            return bytes(ch["ser"].read(n)) if n else b""
        except (OSError, serial.SerialException) as exc:
            raise USBError("citire USB eșuată: %s" % exc) from exc


def USB_vFlush(channel):
    """Șterge datele primite și neciți."""
    with _lock:
        ch = _get_open(channel)
        if ch["sim"]:
            ch["rx"].clear()
        else:
            ch["ser"].reset_input_buffer()


# --------------------------------------------------------- ajutoare simulare
def USB_vSimInject(channel, data):
    """Doar în simulare: pune octeți în bufferul de recepție."""
    with _lock:
        ch = _get_open(channel)
        if not ch["sim"]:
            raise RuntimeError("USB_vSimInject este disponibil doar în simulare")
        ch["rx"].extend(data)


def USB_baSimTakeTx(channel):
    """Doar în simulare: returnează și golește ce s-a trimis."""
    with _lock:
        ch = _get_open(channel)
        if not ch["sim"]:
            raise RuntimeError("USB_baSimTakeTx este disponibil doar în simulare")
        out = bytes(ch["tx"])
        ch["tx"].clear()
        return out
