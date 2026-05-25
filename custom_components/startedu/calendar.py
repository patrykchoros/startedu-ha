from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import StartEduDataUpdateCoordinator
from .entity import StartEduEntity
from .models import StartEduMeal


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: StartEduDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([StartEduMealCalendar(coordinator, entry)])


class StartEduMealCalendar(StartEduEntity, CalendarEntity):
    """Calendar exposing StartEdu meals."""

    _attr_translation_key = "meals"

    def __init__(
        self,
        coordinator: StartEduDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_meals"

    @property
    def event(self) -> CalendarEvent | None:
        meal = self.coordinator.data.next_meal if self.coordinator.data else None
        if meal is None:
            return None
        return _meal_to_event(meal)

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: date | datetime,
        end_date: date | datetime,
    ) -> list[CalendarEvent]:
        if self.coordinator.data is None:
            return []

        start = _as_date(start_date)
        end = _as_date(end_date)
        return [
            _meal_to_event(meal)
            for meal in self.coordinator.data.meals
            if start <= meal.date < end
        ]


def _meal_to_event(meal: StartEduMeal) -> CalendarEvent:
    description_lines = []
    attrs = meal.as_attributes()
    for key in ("child_name", "status", "price", "can_cancel"):
        if key in attrs:
            description_lines.append(f"{key}: {attrs[key]}")
    return CalendarEvent(
        summary=meal.summary,
        start=meal.date,
        end=meal.end_date,
        description="\n".join(description_lines) or None,
    )


def _as_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value

