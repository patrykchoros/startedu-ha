from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

startedu = types.ModuleType("custom_components.startedu")
startedu.__path__ = [str(ROOT / "custom_components" / "startedu")]
sys.modules.setdefault("custom_components.startedu", startedu)


def _install_homeassistant_stubs() -> None:
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    sys.modules.setdefault("homeassistant", homeassistant)

    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    sys.modules.setdefault("homeassistant.config_entries", config_entries)

    core = types.ModuleType("homeassistant.core")
    core.CALLBACK_TYPE = object
    core.HomeAssistant = object
    core.callback = lambda func: func
    sys.modules.setdefault("homeassistant.core", core)

    exceptions = types.ModuleType("homeassistant.exceptions")

    class ConfigEntryAuthFailed(Exception):
        pass

    exceptions.ConfigEntryAuthFailed = ConfigEntryAuthFailed
    sys.modules.setdefault("homeassistant.exceptions", exceptions)

    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    sys.modules.setdefault("homeassistant.helpers", helpers)

    event = types.ModuleType("homeassistant.helpers.event")

    def async_track_point_in_time(hass, action, point_in_time):
        hass.tracked_points.append(point_in_time)
        return lambda: hass.cancelled_points.append(point_in_time)

    event.async_track_point_in_time = async_track_point_in_time
    sys.modules.setdefault("homeassistant.helpers.event", event)

    update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")

    class UpdateFailed(Exception):
        pass

    class DataUpdateCoordinator:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, hass, logger, name, update_interval):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.data = None
            self.listener_updates = 0

        async def async_request_refresh(self):
            self.data = await self._async_update_data()
            return self.data

        def async_update_listeners(self):
            self.listener_updates += 1

    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator.UpdateFailed = UpdateFailed
    sys.modules.setdefault(
        "homeassistant.helpers.update_coordinator",
        update_coordinator,
    )

    util = types.ModuleType("homeassistant.util")
    util.__path__ = []
    sys.modules.setdefault("homeassistant.util", util)

    dt = types.ModuleType("homeassistant.util.dt")
    dt.now = lambda: datetime(2026, 5, 26, 8, 30, tzinfo=timezone.utc)
    sys.modules.setdefault("homeassistant.util.dt", dt)


_install_homeassistant_stubs()

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.startedu.client import CannotConnect, InvalidAuth, StartEduError
from custom_components.startedu.coordinator import (
    SYNC_ACTIVITY_WAITING,
    SYNC_RESULT_FAILED,
    SYNC_RESULT_SUCCESSFUL,
    StartEduDataUpdateCoordinator,
)
from custom_components.startedu.models import (
    MEAL_STATUS_CANCELLED,
    MEAL_STATUS_PAID,
    StartEduAccountData,
    StartEduChild,
    StartEduMeal,
)


class FakeHass:
    def __init__(self) -> None:
        self.tracked_points: list[datetime] = []
        self.cancelled_points: list[datetime] = []
        self.created_tasks = []

    def async_create_task(self, task):
        self.created_tasks.append(task)
        return task


class FakeEntry:
    entry_id = "entry-id"

    def __init__(self, options=None) -> None:
        self.options = options or {}
        self.unload_callbacks = []

    def async_on_unload(self, callback):
        self.unload_callbacks.append(callback)


class FakeClient:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls = 0
        self.cancel_calls = []

    async def async_get_account_data(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result

    async def async_cancel_meal(self, child_id, target_date):
        self.cancel_calls.append((child_id, target_date))
        if self.error is not None:
            raise self.error
        return self.result


class CoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_schedules_opening_date_and_applies_options(self) -> None:
        account_data = StartEduAccountData(
            fetched_at=datetime(2026, 5, 26, tzinfo=timezone.utc),
            children=(
                StartEduChild(
                    child_id="child-1",
                    name="Child 1",
                    next_order_opening_date=date(2026, 6, 15),
                ),
            ),
        )
        hass = FakeHass()
        entry = FakeEntry({"scan_interval": "120"})
        coordinator = StartEduDataUpdateCoordinator(
            hass,
            FakeClient(account_data),
            entry,
        )

        self.assertEqual(coordinator.update_interval, timedelta(minutes=120))
        self.assertEqual(len(hass.tracked_points), 3)
        self.assertIn(
            datetime(2026, 5, 26, 9, 0, tzinfo=timezone.utc),
            hass.tracked_points,
        )
        self.assertEqual(len(entry.unload_callbacks), 1)

        result = await coordinator._async_update_data()

        self.assertIs(result, account_data)
        self.assertEqual(coordinator.sync_activity, SYNC_ACTIVITY_WAITING)
        self.assertEqual(coordinator.last_sync_status, SYNC_RESULT_SUCCESSFUL)
        self.assertEqual(
            coordinator.last_sync_time,
            datetime(2026, 5, 26, 8, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(coordinator.listener_updates, 2)
        self.assertEqual(len(hass.tracked_points), 4)
        self.assertEqual(hass.tracked_points[-1].date(), date(2026, 6, 15))

        entry.options["scan_interval"] = "90"
        coordinator.apply_options()

        self.assertEqual(coordinator.update_interval, timedelta(minutes=90))

    async def test_scheduled_full_refresh_reschedules_morning_refresh(self) -> None:
        account_data = StartEduAccountData(
            fetched_at=datetime(2026, 5, 26, tzinfo=timezone.utc),
            children=(),
        )
        hass = FakeHass()
        coordinator = StartEduDataUpdateCoordinator(
            hass,
            FakeClient(account_data),
            FakeEntry(),
        )

        coordinator._handle_full_refresh_schedule()
        result = await hass.created_tasks[0]

        self.assertIs(result, account_data)
        self.assertEqual(coordinator.last_sync_status, SYNC_RESULT_SUCCESSFUL)
        self.assertIn(
            datetime(2026, 5, 26, 9, 0, tzinfo=timezone.utc),
            hass.cancelled_points,
        )
        self.assertIn(
            datetime(2026, 5, 26, 9, 0, tzinfo=timezone.utc),
            hass.tracked_points,
        )

    async def test_startedu_connection_failure_becomes_update_failed(self) -> None:
        coordinator = StartEduDataUpdateCoordinator(
            FakeHass(),
            FakeClient(error=CannotConnect("offline")),
            FakeEntry(),
        )

        with self.assertRaises(UpdateFailed):
            await coordinator._async_update_data()
        self.assertEqual(coordinator.sync_activity, SYNC_ACTIVITY_WAITING)
        self.assertEqual(coordinator.last_sync_status, SYNC_RESULT_FAILED)

    async def test_startedu_downtime_becomes_update_failed(self) -> None:
        coordinator = StartEduDataUpdateCoordinator(
            FakeHass(),
            FakeClient(error=StartEduError("maintenance")),
            FakeEntry(),
        )

        with self.assertRaises(UpdateFailed):
            await coordinator._async_update_data()
        self.assertEqual(coordinator.sync_activity, SYNC_ACTIVITY_WAITING)
        self.assertEqual(coordinator.last_sync_status, SYNC_RESULT_FAILED)

    async def test_startedu_timeout_becomes_update_failed(self) -> None:
        coordinator = StartEduDataUpdateCoordinator(
            FakeHass(),
            FakeClient(error=TimeoutError("slow")),
            FakeEntry(),
        )

        with self.assertRaises(UpdateFailed):
            await coordinator._async_update_data()
        self.assertEqual(coordinator.sync_activity, SYNC_ACTIVITY_WAITING)
        self.assertEqual(coordinator.last_sync_status, SYNC_RESULT_FAILED)

    async def test_invalid_auth_becomes_config_entry_auth_failed(self) -> None:
        coordinator = StartEduDataUpdateCoordinator(
            FakeHass(),
            FakeClient(error=InvalidAuth("bad password")),
            FakeEntry(),
        )

        with self.assertRaises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()
        self.assertEqual(coordinator.sync_activity, SYNC_ACTIVITY_WAITING)
        self.assertEqual(coordinator.last_sync_status, SYNC_RESULT_FAILED)

    async def test_empty_schedule_is_valid_account_data(self) -> None:
        account_data = StartEduAccountData(
            fetched_at=datetime(2026, 5, 26, 7, 0, tzinfo=timezone.utc),
            children=(),
            meals=(),
            balance=Decimal("0.00"),
        )
        coordinator = StartEduDataUpdateCoordinator(
            FakeHass(),
            FakeClient(account_data),
            FakeEntry(),
        )

        result = await coordinator._async_update_data()

        self.assertEqual(result.child_accounts, ())
        self.assertIsNone(result.next_meal)

    async def test_cancelled_meals_and_missing_balance_are_preserved(self) -> None:
        cancelled_meal = StartEduMeal(
            meal_id="MEAL-27-LUNCH",
            date=date(2026, 5, 27),
            name="Obiad",
            menu="Naleśniki.",
            meal_type="lunch",
            child_id="CHILD-ID-1",
            child_name="Child 1",
            status=MEAL_STATUS_CANCELLED,
            can_cancel=False,
        )
        active_meal = StartEduMeal(
            meal_id="MEAL-28-LUNCH",
            date=date(2026, 5, 28),
            name="Obiad",
            menu="Zupa.",
            meal_type="lunch",
            child_id="CHILD-ID-1",
            child_name="Child 1",
            status=MEAL_STATUS_PAID,
            can_cancel=True,
        )
        account_data = StartEduAccountData(
            fetched_at=datetime(2026, 5, 26, 7, 0, tzinfo=timezone.utc),
            children=(
                StartEduChild(
                    child_id="CHILD-ID-1",
                    name="Child 1",
                    meals=(cancelled_meal, active_meal),
                    refund_available=None,
                    unpaid_amount=None,
                ),
            ),
            balance=None,
        )
        coordinator = StartEduDataUpdateCoordinator(
            FakeHass(),
            FakeClient(account_data),
            FakeEntry(),
        )

        result = await coordinator._async_update_data()

        self.assertIsNone(result.balance)
        self.assertEqual(
            result.child_accounts[0].meals[0].status,
            MEAL_STATUS_CANCELLED,
        )
        self.assertIs(result.next_meal, active_meal)

    async def test_cancel_meal_updates_coordinator_data_after_success(self) -> None:
        account_data = StartEduAccountData(
            fetched_at=datetime(2026, 5, 26, tzinfo=timezone.utc),
            children=(StartEduChild(child_id="CHILD-ID-1", name="Child 1"),),
        )
        client = FakeClient(account_data)
        coordinator = StartEduDataUpdateCoordinator(FakeHass(), client, FakeEntry())

        result = await coordinator.async_cancel_meal(
            "CHILD-ID-1",
            date(2026, 5, 26),
        )

        self.assertIs(result, account_data)
        self.assertIs(coordinator.data, account_data)
        self.assertEqual(client.cancel_calls, [("CHILD-ID-1", date(2026, 5, 26))])
        self.assertEqual(coordinator.listener_updates, 1)
