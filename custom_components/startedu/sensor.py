from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import StartEduDataUpdateCoordinator
from .entity import StartEduEntity
from .entity_model import (
    day_menu_attributes,
    day_menu_state,
    day_status,
)
from .i18n import status_label
from .models import StartEduChild


@dataclass(frozen=True, kw_only=True)
class StartEduSensorDescription(SensorEntityDescription):
    value_fn: Callable[[StartEduChild, StartEduDataUpdateCoordinator], Any]
    attributes_fn: (
        Callable[[StartEduChild, StartEduDataUpdateCoordinator], dict[str, Any]]
        | None
    ) = None


@dataclass(frozen=True, kw_only=True)
class StartEduAccountSensorDescription(SensorEntityDescription):
    value_fn: Callable[[StartEduDataUpdateCoordinator], Any]


def _target_date(coordinator: StartEduDataUpdateCoordinator, offset_days: int) -> date:
    return dt_util.now().date() + timedelta(days=offset_days)


def _today_menu_value(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> str | None:
    return day_menu_state(
        child,
        _target_date(coordinator, 0),
        _hass_language(coordinator),
    )


def _tomorrow_menu_value(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> str | None:
    return day_menu_state(
        child,
        _target_date(coordinator, 1),
        _hass_language(coordinator),
    )


def _today_status_value(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> str | None:
    return status_label(
        day_status(child, _target_date(coordinator, 0)),
        _hass_language(coordinator),
    )


def _tomorrow_status_value(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> str | None:
    return status_label(
        day_status(child, _target_date(coordinator, 1)),
        _hass_language(coordinator),
    )


def _last_successful_update_value(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> datetime:
    return coordinator.data.fetched_at


def _current_month_order_status_value(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> str | None:
    return status_label(
        child.current_month_order_status,
        _hass_language(coordinator),
    )


def _next_month_order_status_value(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> str | None:
    return status_label(
        child.next_month_order_status,
        _hass_language(coordinator),
    )


def _refund_available_value(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> Decimal | None:
    return child.refund_available


def _unpaid_amount_value(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> Decimal | None:
    return child.unpaid_amount


def _next_order_opening_date_value(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> date | None:
    return child.next_order_opening_date


def _sync_status_value(coordinator: StartEduDataUpdateCoordinator) -> str | None:
    return status_label(coordinator.sync_activity, _hass_language(coordinator))


def _last_sync_status_value(coordinator: StartEduDataUpdateCoordinator) -> str | None:
    return status_label(coordinator.last_sync_status, _hass_language(coordinator))


def _last_sync_time_value(coordinator: StartEduDataUpdateCoordinator) -> datetime | None:
    return coordinator.last_sync_time


def _today_menu_attributes(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> dict[str, Any]:
    return day_menu_attributes(
        child,
        _target_date(coordinator, 0),
        _hass_language(coordinator),
    )


def _tomorrow_menu_attributes(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> dict[str, Any]:
    return day_menu_attributes(
        child,
        _target_date(coordinator, 1),
        _hass_language(coordinator),
    )


def _hass_language(coordinator: StartEduDataUpdateCoordinator) -> str | None:
    hass = getattr(coordinator, "hass", None)
    config = getattr(hass, "config", None)
    language = getattr(config, "language", None)
    return str(language) if language else None


SENSOR_DESCRIPTIONS: tuple[StartEduSensorDescription, ...] = (
    StartEduSensorDescription(
        key="today_menu",
        translation_key="today_menu",
        value_fn=_today_menu_value,
        attributes_fn=_today_menu_attributes,
    ),
    StartEduSensorDescription(
        key="tomorrow_menu",
        translation_key="tomorrow_menu",
        value_fn=_tomorrow_menu_value,
        attributes_fn=_tomorrow_menu_attributes,
    ),
    StartEduSensorDescription(
        key="today_meal_status",
        translation_key="today_meal_status",
        value_fn=_today_status_value,
    ),
    StartEduSensorDescription(
        key="tomorrow_meal_status",
        translation_key="tomorrow_meal_status",
        value_fn=_tomorrow_status_value,
    ),
    StartEduSensorDescription(
        key="last_successful_update",
        translation_key="last_successful_update",
        value_fn=_last_successful_update_value,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    StartEduSensorDescription(
        key="current_month_order_status",
        translation_key="current_month_order_status",
        value_fn=_current_month_order_status_value,
    ),
    StartEduSensorDescription(
        key="next_month_order_status",
        translation_key="next_month_order_status",
        value_fn=_next_month_order_status_value,
    ),
    StartEduSensorDescription(
        key="refund_available",
        translation_key="refund_available",
        value_fn=_refund_available_value,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="PLN",
    ),
    StartEduSensorDescription(
        key="unpaid_amount",
        translation_key="unpaid_amount",
        value_fn=_unpaid_amount_value,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="PLN",
    ),
    StartEduSensorDescription(
        key="next_order_opening_date",
        translation_key="next_order_opening_date",
        value_fn=_next_order_opening_date_value,
        device_class=SensorDeviceClass.DATE,
    ),
)


ACCOUNT_SENSOR_DESCRIPTIONS: tuple[StartEduAccountSensorDescription, ...] = (
    StartEduAccountSensorDescription(
        key="sync_status",
        translation_key="sync_status",
        value_fn=_sync_status_value,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    StartEduAccountSensorDescription(
        key="last_sync_status",
        translation_key="last_sync_status",
        value_fn=_last_sync_status_value,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    StartEduAccountSensorDescription(
        key="last_sync_time",
        translation_key="last_sync_time",
        value_fn=_last_sync_time_value,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: StartEduDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    children = coordinator.data.child_accounts if coordinator.data else ()
    account_entities = [
        StartEduAccountSensor(coordinator, entry, description)
        for description in ACCOUNT_SENSOR_DESCRIPTIONS
    ]
    child_entities = [
        StartEduSensor(coordinator, entry, child, description)
        for child in children
        for description in SENSOR_DESCRIPTIONS
    ]
    async_add_entities([*account_entities, *child_entities])


class StartEduAccountSensor(StartEduEntity, SensorEntity):
    """Sensor exposing StartEdu synchronization state for the main device."""

    def __init__(
        self,
        coordinator: StartEduDataUpdateCoordinator,
        entry: ConfigEntry,
        description: StartEduAccountSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_key = description.translation_key
        self._attr_device_class = description.device_class
        self._attr_entity_category = description.entity_category

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator)


class StartEduSensor(StartEduEntity, SensorEntity):
    """Sensor exposing a StartEdu account value."""

    def __init__(
        self,
        coordinator: StartEduDataUpdateCoordinator,
        entry: ConfigEntry,
        child: StartEduChild,
        description: StartEduSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry, child)
        self._child = child
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{child.child_id}_{description.key}"
        self._attr_translation_key = description.translation_key
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_entity_category = description.entity_category

    @property
    def native_value(self) -> Any:
        child = self.current_child
        if self.coordinator.data is None or child is None:
            return None
        return self.entity_description.value_fn(child, self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        child = self.current_child
        if (
            self.coordinator.data is None
            or self.entity_description.attributes_fn is None
            or child is None
        ):
            return None
        attributes = self.entity_description.attributes_fn(
            child,
            self.coordinator,
        )
        return attributes or None
