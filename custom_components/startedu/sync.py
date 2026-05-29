from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, time, timedelta
from typing import Any

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
)

CANCELLATION_AVAILABILITY_REFRESH_TIME = time(9, 0)


def scan_interval_minutes(options: Mapping[str, Any]) -> int:
    """Return the configured polling interval clamped to supported bounds."""
    raw_value = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES)
    try:
        minutes = int(raw_value)
    except (TypeError, ValueError):
        minutes = DEFAULT_SCAN_INTERVAL_MINUTES
    return min(max(minutes, MIN_SCAN_INTERVAL_MINUTES), MAX_SCAN_INTERVAL_MINUTES)


def next_local_midnight(now: datetime) -> datetime:
    """Return the next local midnight after now."""
    return datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=now.tzinfo)


def next_local_month_start(now: datetime) -> datetime:
    """Return the next local month boundary after now."""
    if now.month == 12:
        return datetime(now.year + 1, 1, 1, tzinfo=now.tzinfo)
    return datetime(now.year, now.month + 1, 1, tzinfo=now.tzinfo)


def next_local_time(now: datetime, target_time: time) -> datetime:
    """Return the next occurrence of target_time in now's local timezone."""
    candidate = datetime.combine(now.date(), target_time, tzinfo=now.tzinfo)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def next_cancellation_availability_refresh(now: datetime) -> datetime:
    """Return the next full refresh for same-day cancellation availability."""
    return next_local_time(now, CANCELLATION_AVAILABILITY_REFRESH_TIME)


def next_future_date(dates: tuple[date, ...], today: date) -> date | None:
    """Return the nearest future date from a collection of dates."""
    future_dates = sorted({candidate for candidate in dates if candidate > today})
    return future_dates[0] if future_dates else None


def start_of_local_date(target_date: date, now: datetime) -> datetime:
    """Return midnight for target_date using now's local timezone."""
    return datetime.combine(target_date, time.min, tzinfo=now.tzinfo)
