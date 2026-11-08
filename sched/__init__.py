"""Scheduler utilities for 1 s / 60 s / alert watchdog tasks."""

from mcd.tim import TIM_CH_1S, TIM_CH_60S, TIM_CH_ALERT, TIM_bHasElapsed, TIM_vStart, TIM_vStop

__all__ = [
    "TIM_CH_1S",
    "TIM_CH_60S",
    "TIM_CH_ALERT",
    "TIM_bHasElapsed",
    "TIM_vStart",
    "TIM_vStop",
]


def scheduler_tick(channel):
    return TIM_bHasElapsed(channel)


def alert_expired(deadline_ms, now_ms):
    return now_ms >= deadline_ms
