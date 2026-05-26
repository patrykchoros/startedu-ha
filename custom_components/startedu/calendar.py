from __future__ import annotations

from datetime import date, datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import StartEduDataUpdateCoordinator
from .entity import StartEduEntity
from .entity_model import (
    calendar_meals,
    meal_event_description,
    meal_event_summary,
    meal_time_window,
)
from .models import StartEduChild, StartEduMeal


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: StartEduDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    children = coordinator.data.child_accounts if coordinator.data else ()
    async_add_entities(
        [StartEduMealCalendar(coordinator, entry, child) for child in children]
    )


class StartEduMealCalendar(StartEduEntity, CalendarEntity):
    """Calendar exposing StartEdu meals."""

    _attr_translation_key = "meals"

    def __init__(
        self,
        coordinator: StartEduDataUpdateCoordinator,
        entry: ConfigEntry,
        child: StartEduChild,
    ) -> None:
        super().__init__(coordinator, entry, child)
        self._child = child
        self._attr_unique_id = f"{entry.entry_id}_{child.child_id}_meals"

    @property
    def event(self) -> CalendarEvent | None:
        meal = self._child.next_meal
        if meal is None:
            return None
        return _meal_to_event(
            meal,
            self.coordinator.entry.options,
            _hass_language(getattr(self, "hass", None)),
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: date | datetime,
        end_date: date | datetime,
    ) -> list[CalendarEvent]:
        if self.coordinator.data is None:
            return []

        start = _as_datetime(start_date)
        end = _as_datetime(end_date)
        language = _hass_language(hass)
        return [
            _meal_to_event(meal, self.coordinator.entry.options, language)
            for meal in calendar_meals(self._child)
            if start <= meal_time_window(meal, self.coordinator.entry.options).start < end
        ]


def _meal_to_event(
    meal: StartEduMeal,
    options: dict[str, object],
    language: str | None = None,
) -> CalendarEvent:
    window = meal_time_window(meal, options)
    return CalendarEvent(
        summary=meal_event_summary(meal, language),
        start=window.start,
        end=window.end,
        description=meal_event_description(meal),
    )


def _as_datetime(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, datetime.min.time())


def _hass_language(hass: HomeAssistant | None) -> str | None:
    config = getattr(hass, "config", None)
    language = getattr(config, "language", None)
    return str(language) if language else None
