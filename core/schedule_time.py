"""Rough 교시(period) -> wall-clock time mapping, used only for the home
dashboard's "다음 수업" card. The rest of the app works entirely in period
numbers, so this is a display-only approximation (1교시 = 09:00, each
period treated as a flat 60-minute block)."""
from __future__ import annotations

from datetime import time

PERIOD_START_HOUR = 9
PERIOD_LENGTH_MINUTES = 60

DAY_TO_WEEKDAY = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}


def period_start_time(period: int) -> time:
    total_minutes = (period - 1) * PERIOD_LENGTH_MINUTES
    hour = (PERIOD_START_HOUR + total_minutes // 60) % 24
    minute = total_minutes % 60
    return time(hour=hour, minute=minute)
