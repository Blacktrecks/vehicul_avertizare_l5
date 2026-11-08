"""Configurație MCD: mapare pini, canale și mod de simulare."""
import os

# ---------------------------------------------------------------- simulare
# MCD_SIMULATE = "auto" (implicit): hardware real dacă biblioteca și
#                dispozitivul există, altfel simulare (rulare pe PC);
#                "1": simulare forțată; "0": hardware forțat (eroare dacă lipsește).
SIM_ENV = "MCD_SIMULATE"


def simulation_mode():
    return os.environ.get(SIM_ENV, "auto").strip().lower()


def use_simulation(hw_available):
    """Decide dacă un driver rulează în simulare."""
    mode = simulation_mode()
    if mode in ("1", "true", "yes", "on"):
        return True
    if mode in ("0", "false", "no", "off"):
        return False
    return not hw_available


# -------------------------------------------------------------------- GPIO
PCS_PIN_MIN = 0
PCS_PIN_MAX = 27          # interval valid din L3 (BCM)

GPIO_I2C_SDA = 2
GPIO_I2C_SCL = 3
GPIO_BUZZER = 17          # buzzer prin tranzistor NPN
GPIO_LED = 27             # LED cu rezistență de 330 ohm
OUTPUT_PINS = (GPIO_BUZZER, GPIO_LED)

# --------------------------------------------------------------------- I2C
I2C_BUS_ID = 1            # /dev/i2c-1 pe Raspberry Pi (GPIO2/GPIO3)
MPU6050_ADDR = 0x68       # AD0 la GND

# --------------------------------------------------------------------- USB
USB_CH_ZIGBEE = 0         # XBee3 prin adaptor USB
USB_CH_MESHTASTIC = 1     # modul ESP Meshtastic

_USB_DEFAULTS = {
    USB_CH_ZIGBEE: {"name": "ZIGBEE", "port": "/dev/ttyUSB0", "baud": 9600,
                    "env": "MCD_ZIGBEE_PORT"},
    USB_CH_MESHTASTIC: {"name": "MESHTASTIC", "port": "/dev/ttyACM0",
                        "baud": 115200, "env": "MCD_MESHTASTIC_PORT"},
}


def usb_channels():
    return tuple(_USB_DEFAULTS)


def usb_config(channel):
    """Returnează {name, port, baud} pentru canal (portul poate fi suprascris din env)."""
    if channel not in _USB_DEFAULTS:
        raise ValueError("canal USB invalid: %r" % (channel,))
    cfg = dict(_USB_DEFAULTS[channel])
    cfg["port"] = os.environ.get(cfg.pop("env"), cfg["port"])
    return cfg


# ------------------------------------------------------- tabel mapare pini
# Format cerut de L4: Pin | Tip semnal | Nume semnal | Definiție
# Tipuri: DOP = ieșire digitală, DIP = intrare digitală, COM = comunicație,
#         PWR = alimentare
PIN_TABLE = [
    {"pin": "GPIO2 / SDA1 (pin 3)", "tip": "COM", "nume": "I2C_SDA",
     "definitie": "Linie date I2C către accelerometrul MPU6050"},
    {"pin": "GPIO3 / SCL1 (pin 5)", "tip": "COM", "nume": "I2C_SCL",
     "definitie": "Linie ceas I2C către accelerometrul MPU6050"},
    {"pin": "GPIO17 (pin 11)", "tip": "DOP", "nume": "BUZZER",
     "definitie": "Alertă sonoră: rezistență 1 kΩ, bază tranzistor NPN, "
                  "buzzer între 5 V și colector, diodă de protecție"},
    {"pin": "GPIO27 (pin 13)", "tip": "DOP", "nume": "LED",
     "definitie": "Alertă vizuală: LED cu rezistență de 330 Ω către GND"},
    {"pin": "USB (hub alimentat)", "tip": "COM", "nume": "ZIGBEE",
     "definitie": "XBee3 Zigbee prin adaptor USB, /dev/ttyUSB0, 9600 baud"},
    {"pin": "USB (hub alimentat)", "tip": "COM", "nume": "MESHTASTIC",
     "definitie": "Modul ESP Meshtastic (LoRa), /dev/ttyACM0, 115200 baud"},
    {"pin": "3V3 (pin 1)", "tip": "PWR", "nume": "VCC_MPU",
     "definitie": "Alimentare 3,3 V pentru MPU6050"},
    {"pin": "GND (pin 6)", "tip": "PWR", "nume": "GND",
     "definitie": "Masă comună (Pi, MPU6050, LED, tranzistor buzzer)"},
]
