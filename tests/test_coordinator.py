from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
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

from custom_components.startedu.client import CannotConnect, InvalidAuth
from custom_components.startedu.coordinator import StartEduDataUpdateCoordinator
from custom_components.startedu.models import StartEduAccountData, StartEduChild


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

    async def async_get_account_data(self):
        self.calls += 1
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
        self.assertEqual(len(hass.tracked_points), 2)
        self.assertEqual(len(entry.unload_callbacks), 1)

        result = await coordinator._async_update_data()

        self.assertIs(result, account_data)
        self.assertEqual(len(hass.tracked_points), 3)
        self.assertEqual(hass.tracked_points[-1].date(), date(2026, 6, 15))

        entry.options["scan_interval"] = "90"
        coordinator.apply_options()

        self.assertEqual(coordinator.update_interval, timedelta(minutes=90))

    async def test_startedu_connection_failure_becomes_update_failed(self) -> None:
        coordinator = StartEduDataUpdateCoordinator(
            FakeHass(),
            FakeClient(error=CannotConnect("offline")),
            FakeEntry(),
        )

        with self.assertRaises(UpdateFailed):
            await coordinator._async_update_data()

    async def test_invalid_auth_becomes_config_entry_auth_failed(self) -> None:
        coordinator = StartEduDataUpdateCoordinator(
            FakeHass(),
            FakeClient(error=InvalidAuth("bad password")),
            FakeEntry(),
        )

        with self.assertRaises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()
