from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import StartEduDataUpdateCoordinator
from .entity import StartEduEntity
from .entity_model import can_cancel, has_food
from .models import StartEduChild


@dataclass(frozen=True, kw_only=True)
class StartEduBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[StartEduChild, StartEduDataUpdateCoordinator], bool | None]


def _target_date(coordinator: StartEduDataUpdateCoordinator, offset_days: int) -> date:
    return dt_util.now().date() + timedelta(days=offset_days)


def _has_food_today(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> bool:
    return has_food(child, _target_date(coordinator, 0))


def _has_food_tomorrow(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> bool:
    return has_food(child, _target_date(coordinator, 1))


def _can_cancel_today(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> bool:
    return can_cancel(child, _target_date(coordinator, 0))


def _can_cancel_tomorrow(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> bool:
    return can_cancel(child, _target_date(coordinator, 1))


def _next_month_ordering_available(
    child: StartEduChild,
    coordinator: StartEduDataUpdateCoordinator,
) -> bool | None:
    return child.next_month_ordering_available


BINARY_SENSOR_DESCRIPTIONS: tuple[StartEduBinarySensorDescription, ...] = (
    StartEduBinarySensorDescription(
        key="has_food_today",
        translation_key="has_food_today",
        value_fn=_has_food_today,
    ),
    StartEduBinarySensorDescription(
        key="has_food_tomorrow",
        translation_key="has_food_tomorrow",
        value_fn=_has_food_tomorrow,
    ),
    StartEduBinarySensorDescription(
        key="can_cancel_today_meal",
        translation_key="can_cancel_today_meal",
        value_fn=_can_cancel_today,
    ),
    StartEduBinarySensorDescription(
        key="can_cancel_tomorrow_meal",
        translation_key="can_cancel_tomorrow_meal",
        value_fn=_can_cancel_tomorrow,
    ),
    StartEduBinarySensorDescription(
        key="next_month_ordering_available",
        translation_key="next_month_ordering_available",
        value_fn=_next_month_ordering_available,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: StartEduDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    children = coordinator.data.child_accounts if coordinator.data else ()
    async_add_entities(
        [
            StartEduBinarySensor(coordinator, entry, child, description)
            for child in children
            for description in BINARY_SENSOR_DESCRIPTIONS
        ]
    )


class StartEduBinarySensor(StartEduEntity, BinarySensorEntity):
    """Binary sensor exposing StartEdu day/order booleans."""

    def __init__(
        self,
        coordinator: StartEduDataUpdateCoordinator,
        entry: ConfigEntry,
        child: StartEduChild,
        description: StartEduBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, entry, child)
        self._child = child
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{child.child_id}_{description.key}"
        self._attr_translation_key = description.translation_key

    @property
    def is_on(self) -> bool | None:
        child = self.current_child
        if self.coordinator.data is None or child is None:
            return None
        return self.entity_description.value_fn(child, self.coordinator)
