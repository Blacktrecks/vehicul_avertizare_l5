"""IOC layer for output channel routing."""

from mcd import config
from mcd import pcs

IOC_CH_BUZZER = 0x0001
IOC_CH_LED = 0x0002

_IOC_MAP = {
    IOC_CH_BUZZER: config.GPIO_BUZZER,
    IOC_CH_LED: config.GPIO_LED,
}


def IOC_vSetOutputPort(channel, value):
    """Map MCU channel to the correct GPIO pin. Unknown or invalid values are ignored."""
    if channel not in _IOC_MAP:
        return
    if value not in (0, 1):
        return
    pcs.PCS_vSetOutputGpio(_IOC_MAP[channel], int(value))
