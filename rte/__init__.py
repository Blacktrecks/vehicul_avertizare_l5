"""RTE layer – public API used by APP."""

from ioc import IOC_vSetOutputPort


def _normalize(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    value = float(value)
    if not 0.0 <= value <= 1.0:
        return None
    return int(round(value))


def vSetAlertaSonora(value):
    normalized = _normalize(value)
    if normalized is None:
        return
    IOC_vSetOutputPort(0x0001, normalized)


def vSetAlertaVizuala(value):
    normalized = _normalize(value)
    if normalized is None:
        return
    IOC_vSetOutputPort(0x0002, normalized)
