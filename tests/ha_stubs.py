from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sys
import types
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def install_homeassistant_stubs(
    now: datetime | None = None,
) -> None:
    """Install the small Home Assistant surface used by unit tests."""
    _install_custom_component_packages()
    _install_voluptuous_stub()

    current_time = now or datetime(2026, 5, 26, 8, 30, tzinfo=timezone.utc)

    homeassistant = _module("homeassistant")
    homeassistant.__path__ = []

    config_entries = _module("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    config_entries.ConfigFlow = _ConfigFlow
    config_entries.FlowResult = dict
    config_entries.OptionsFlow = _OptionsFlow

    const = _module("homeassistant.const")
    const.CONF_PASSWORD = "password"
    const.CONF_USERNAME = "username"

    core = _module("homeassistant.core")
    core.CALLBACK_TYPE = object
    core.HomeAssistant = object
    core.ServiceCall = ServiceCall
    core.callback = lambda func: func

    exceptions = _module("homeassistant.exceptions")
    exceptions.ConfigEntryAuthFailed = ConfigEntryAuthFailed
    exceptions.HomeAssistantError = HomeAssistantError

    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []

    aiohttp_client = _module("homeassistant.helpers.aiohttp_client")
    aiohttp_client.async_get_clientsession = lambda hass: object()

    device_registry = _module("homeassistant.helpers.device_registry")
    device_registry.DeviceInfo = DeviceInfo

    entity = _module("homeassistant.helpers.entity")
    entity.EntityCategory = EntityCategory

    entity_platform = _module("homeassistant.helpers.entity_platform")
    entity_platform.AddEntitiesCallback = object

    event = _module("homeassistant.helpers.event")
    event.async_track_point_in_time = async_track_point_in_time

    update_coordinator = _module("homeassistant.helpers.update_coordinator")
    update_coordinator.CoordinatorEntity = CoordinatorEntity
    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator.UpdateFailed = UpdateFailed

    util = _module("homeassistant.util")
    util.__path__ = []

    dt = _module("homeassistant.util.dt")
    dt.DEFAULT_TIME_ZONE = timezone.utc
    dt.now = lambda: current_time

    components = _module("homeassistant.components")
    components.__path__ = []

    calendar = _module("homeassistant.components.calendar")
    calendar.CalendarEntity = CalendarEntity
    calendar.CalendarEvent = CalendarEvent

    sensor = _module("homeassistant.components.sensor")
    sensor.SensorDeviceClass = SensorDeviceClass
    sensor.SensorEntity = SensorEntity
    sensor.SensorEntityDescription = SensorEntityDescription

    binary_sensor = _module("homeassistant.components.binary_sensor")
    binary_sensor.BinarySensorEntity = BinarySensorEntity
    binary_sensor.BinarySensorEntityDescription = BinarySensorEntityDescription

    button = _module("homeassistant.components.button")
    button.ButtonEntity = ButtonEntity
    button.ButtonEntityDescription = ButtonEntityDescription


def _install_custom_component_packages() -> None:
    custom_components = _module("custom_components")
    custom_components.__path__ = [str(ROOT / "custom_components")]

    startedu = _module("custom_components.startedu")
    startedu.__path__ = [str(ROOT / "custom_components" / "startedu")]


def _install_voluptuous_stub() -> None:
    if "voluptuous" in sys.modules:
        return

    voluptuous = types.ModuleType("voluptuous")
    voluptuous.All = lambda *validators: validators[-1] if validators else None
    voluptuous.Coerce = lambda target_type: target_type
    voluptuous.Match = lambda pattern: str
    voluptuous.Optional = lambda key, default=None: key
    voluptuous.Range = lambda min=None, max=None: int
    voluptuous.Required = lambda key, default=None: key
    voluptuous.Schema = _Schema
    sys.modules["voluptuous"] = voluptuous


def _module(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        sys.modules[name] = module
    return module


class _Schema:
    def __init__(self, schema: Any) -> None:
        self.schema = schema

    def __call__(self, value: Any) -> Any:
        return value


class _ConfigFlow:
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__()

    def __init__(self) -> None:
        self.context: dict[str, Any] = {}
        self.hass = None
        self.unique_id: str | None = None

    async def async_set_unique_id(self, unique_id: str) -> None:
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self) -> None:
        return None

    def async_abort(self, *, reason: str) -> dict[str, Any]:
        return {"type": "abort", "reason": reason}

    def async_create_entry(self, *, title: str, data: dict[str, Any]) -> dict[str, Any]:
        return {"type": "create_entry", "title": title, "data": data}

    def async_show_form(
        self,
        *,
        step_id: str,
        data_schema: Any,
        errors: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return {
            "type": "form",
            "step_id": step_id,
            "data_schema": data_schema,
            "errors": errors or {},
        }


class _OptionsFlow:
    def async_create_entry(self, *, title: str, data: dict[str, Any]) -> dict[str, Any]:
        return {"type": "create_entry", "title": title, "data": data}

    def async_show_form(
        self,
        *,
        step_id: str,
        data_schema: Any,
    ) -> dict[str, Any]:
        return {"type": "form", "step_id": step_id, "data_schema": data_schema}


class ConfigEntryAuthFailed(Exception):
    pass


class HomeAssistantError(Exception):
    pass


class UpdateFailed(Exception):
    pass


class DataUpdateCoordinator:
    def __class_getitem__(cls, item: Any):
        return cls

    def __init__(
        self,
        hass: Any,
        logger: Any,
        name: str,
        update_interval: Any,
    ) -> None:
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None
        self.listener_updates = 0

    async def async_request_refresh(self):
        self.data = await self._async_update_data()
        return self.data

    def async_update_listeners(self) -> None:
        self.listener_updates += 1


class CoordinatorEntity:
    def __class_getitem__(cls, item: Any):
        return cls

    def __init__(self, coordinator: Any) -> None:
        self.coordinator = coordinator


class DeviceInfo(dict):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(kwargs)


class EntityCategory:
    DIAGNOSTIC = "diagnostic"


class CalendarEntity:
    pass


class CalendarEvent:
    def __init__(
        self,
        *,
        summary: str,
        start: Any,
        end: Any,
        description: str | None = None,
    ) -> None:
        for value in (start, end):
            if (
                isinstance(value, datetime)
                and (value.tzinfo is None or value.utcoffset() is None)
            ):
                raise HomeAssistantError(
                    "Failed to validate CalendarEvent: "
                    "Expected all values to have a timezone"
                )
        self.summary = summary
        self.start = start
        self.end = end
        self.description = description


class SensorDeviceClass:
    DATE = "date"
    MONETARY = "monetary"
    TIMESTAMP = "timestamp"


@dataclass(frozen=True, kw_only=True)
class SensorEntityDescription:
    key: str
    translation_key: str | None = None
    device_class: str | None = None
    native_unit_of_measurement: str | None = None
    suggested_unit_of_measurement: str | None = None
    entity_category: str | None = None
    entity_registry_enabled_default: bool = True
    translation_placeholders: dict[str, str] | None = None


class SensorEntity:
    pass


@dataclass(frozen=True, kw_only=True)
class BinarySensorEntityDescription:
    key: str
    translation_key: str | None = None
    device_class: str | None = None
    entity_category: str | None = None
    entity_registry_enabled_default: bool = True
    translation_placeholders: dict[str, str] | None = None


class BinarySensorEntity:
    pass


class ButtonEntity:
    pass


@dataclass(frozen=True, kw_only=True)
class ButtonEntityDescription:
    key: str
    translation_key: str | None = None
    device_class: str | None = None
    entity_category: str | None = None
    entity_registry_enabled_default: bool = True
    translation_placeholders: dict[str, str] | None = None


class ServiceCall:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data


def async_track_point_in_time(hass: Any, action: Any, point_in_time: datetime):
    hass.tracked_points.append(point_in_time)
    return lambda: hass.cancelled_points.append(point_in_time)
