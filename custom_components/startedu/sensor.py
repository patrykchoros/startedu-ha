from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import StartEduDataUpdateCoordinator
from .entity import StartEduEntity
from .models import StartEduAccountData


@dataclass(frozen=True, slots=True)
class StartEduSensorDescription:
    key: str
    translation_key: str
    value_fn: Callable[[StartEduAccountData, StartEduDataUpdateCoordinator], Any]
    attributes_fn: Callable[[StartEduAccountData], dict[str, Any]] | None = None
    device_class: SensorDeviceClass | None = None
    native_unit_of_measurement: str | None = None
    entity_category: EntityCategory | None = None


def _next_meal_value(
    data: StartEduAccountData,
    coordinator: StartEduDataUpdateCoordinator,
) -> str | None:
    meal = data.next_meal
    return meal.summary if meal else None


def _balance_value(
    data: StartEduAccountData,
    coordinator: StartEduDataUpdateCoordinator,
) -> Decimal | None:
    return data.balance


def _refunds_value(
    data: StartEduAccountData,
    coordinator: StartEduDataUpdateCoordinator,
) -> Decimal | None:
    return data.refunds


def _last_successful_update_value(
    data: StartEduAccountData,
    coordinator: StartEduDataUpdateCoordinator,
) -> datetime:
    return data.fetched_at


def _sync_status_value(
    data: StartEduAccountData,
    coordinator: StartEduDataUpdateCoordinator,
) -> str:
    return "ok" if coordinator.last_update_success else "error"


def _next_meal_attributes(data: StartEduAccountData) -> dict[str, Any]:
    if data.next_meal is None:
        return {}
    return data.next_meal.as_attributes()


def _sync_attributes(data: StartEduAccountData) -> dict[str, Any]:
    return {
        "meal_count": len(data.meals),
        "last_successful_update": data.fetched_at.isoformat(),
    }


SENSOR_DESCRIPTIONS: tuple[StartEduSensorDescription, ...] = (
    StartEduSensorDescription(
        key="next_meal",
        translation_key="next_meal",
        value_fn=_next_meal_value,
        attributes_fn=_next_meal_attributes,
    ),
    StartEduSensorDescription(
        key="balance",
        translation_key="balance",
        value_fn=_balance_value,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="PLN",
    ),
    StartEduSensorDescription(
        key="refunds",
        translation_key="refunds",
        value_fn=_refunds_value,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="PLN",
    ),
    StartEduSensorDescription(
        key="last_successful_update",
        translation_key="last_successful_update",
        value_fn=_last_successful_update_value,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    StartEduSensorDescription(
        key="sync_status",
        translation_key="sync_status",
        value_fn=_sync_status_value,
        attributes_fn=_sync_attributes,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: StartEduDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            StartEduSensor(coordinator, entry, description)
            for description in SENSOR_DESCRIPTIONS
        ]
    )


class StartEduSensor(StartEduEntity, SensorEntity):
    """Sensor exposing a StartEdu account value."""

    def __init__(
        self,
        coordinator: StartEduDataUpdateCoordinator,
        entry: ConfigEntry,
        description: StartEduSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_key = description.translation_key
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_entity_category = description.entity_category

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data, self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.coordinator.data is None or self.entity_description.attributes_fn is None:
            return None
        attributes = self.entity_description.attributes_fn(self.coordinator.data)
        return attributes or None
