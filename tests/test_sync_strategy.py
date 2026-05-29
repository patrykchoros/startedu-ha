from __future__ import annotations

from datetime import date, datetime
import sys
import types
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

startedu = types.ModuleType("custom_components.startedu")
startedu.__path__ = [str(ROOT / "custom_components" / "startedu")]
sys.modules.setdefault("custom_components.startedu", startedu)

from custom_components.startedu.const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
    PLATFORMS,
)
from custom_components.startedu.sync import (
    CANCELLATION_AVAILABILITY_REFRESH_TIME,
    next_cancellation_availability_refresh,
    next_future_date,
    next_local_midnight,
    next_local_month_start,
    scan_interval_minutes,
    start_of_local_date,
)


class SyncStrategyTests(unittest.TestCase):
    def test_default_refresh_interval_is_daily(self) -> None:
        self.assertEqual(DEFAULT_SCAN_INTERVAL_MINUTES, 1440)
        self.assertEqual(scan_interval_minutes({}), 1440)

    def test_refresh_interval_is_clamped(self) -> None:
        self.assertEqual(
            scan_interval_minutes({CONF_SCAN_INTERVAL: 1}),
            MIN_SCAN_INTERVAL_MINUTES,
        )
        self.assertEqual(
            scan_interval_minutes({CONF_SCAN_INTERVAL: 9999}),
            MAX_SCAN_INTERVAL_MINUTES,
        )
        self.assertEqual(
            scan_interval_minutes({CONF_SCAN_INTERVAL: "120"}),
            120,
        )
        self.assertEqual(
            scan_interval_minutes({CONF_SCAN_INTERVAL: "not-a-number"}),
            DEFAULT_SCAN_INTERVAL_MINUTES,
        )

    def test_refresh_button_platform_is_loaded(self) -> None:
        self.assertIn("button", PLATFORMS)

    def test_day_rollover_is_local_midnight_without_network_policy(self) -> None:
        now = datetime(2026, 5, 26, 8, 30, tzinfo=ZoneInfo("Europe/Warsaw"))

        self.assertEqual(
            next_local_midnight(now),
            datetime(2026, 5, 27, 0, 0, tzinfo=ZoneInfo("Europe/Warsaw")),
        )

    def test_month_rollover_uses_next_local_month_start(self) -> None:
        now = datetime(2026, 12, 26, 8, 30, tzinfo=ZoneInfo("Europe/Warsaw"))

        self.assertEqual(
            next_local_month_start(now),
            datetime(2027, 1, 1, 0, 0, tzinfo=ZoneInfo("Europe/Warsaw")),
        )

    def test_cancellation_availability_refresh_runs_every_morning(self) -> None:
        self.assertEqual(CANCELLATION_AVAILABILITY_REFRESH_TIME.hour, 9)
        before_cutoff = datetime(
            2026,
            5,
            26,
            8,
            30,
            tzinfo=ZoneInfo("Europe/Warsaw"),
        )
        after_cutoff = datetime(
            2026,
            5,
            26,
            9,
            30,
            tzinfo=ZoneInfo("Europe/Warsaw"),
        )

        self.assertEqual(
            next_cancellation_availability_refresh(before_cutoff),
            datetime(2026, 5, 26, 9, 0, tzinfo=ZoneInfo("Europe/Warsaw")),
        )
        self.assertEqual(
            next_cancellation_availability_refresh(after_cutoff),
            datetime(2026, 5, 27, 9, 0, tzinfo=ZoneInfo("Europe/Warsaw")),
        )

    def test_next_order_opening_refresh_uses_nearest_future_date(self) -> None:
        self.assertEqual(
            next_future_date(
                (
                    date(2026, 5, 25),
                    date(2026, 6, 20),
                    date(2026, 6, 15),
                ),
                date(2026, 5, 26),
            ),
            date(2026, 6, 15),
        )
        self.assertIsNone(
            next_future_date(
                (date(2026, 5, 25), date(2026, 5, 26)),
                date(2026, 5, 26),
            )
        )

    def test_start_of_local_date_uses_current_timezone(self) -> None:
        now = datetime(2026, 5, 26, 8, 30, tzinfo=ZoneInfo("Europe/Warsaw"))

        self.assertEqual(
            start_of_local_date(date(2026, 6, 15), now),
            datetime(2026, 6, 15, 0, 0, tzinfo=ZoneInfo("Europe/Warsaw")),
        )
