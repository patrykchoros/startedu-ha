from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .client import MealCancellationError, StartEduError
from .const import DOMAIN
from .coordinator import StartEduDataUpdateCoordinator
from .entity import StartEduEntity
from .entity_model import can_cancel
from .models import StartEduChild


@dataclass(frozen=True, kw_only=True)
class StartEduCancelMealButtonDescription(ButtonEntityDescription):
    offset_days: int


CANCEL_MEAL_BUTTON_DESCRIPTIONS: tuple[StartEduCancelMealButtonDescription, ...] = (
    StartEduCancelMealButtonDescription(
        key="cancel_today_meals",
        translation_key="cancel_today_meals",
        offset_days=0,
    ),
    StartEduCancelMealButtonDescription(
        key="cancel_tomorrow_meals",
        translation_key="cancel_tomorrow_meals",
        offset_days=1,
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
            StartEduRefreshButton(coordinator, entry),
            *[
                StartEduCancelMealButton(coordinator, entry, child, description)
                for child in children
                for description in CANCEL_MEAL_BUTTON_DESCRIPTIONS
            ],
        ]
    )


class StartEduRefreshButton(StartEduEntity, ButtonEntity):
    """Button that refreshes all StartEdu data for the config entry."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "refresh_startedu_data"

    def __init__(
        self,
        coordinator: StartEduDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_refresh_startedu_data"

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()


class StartEduCancelMealButton(StartEduEntity, ButtonEntity):
    """Button that cancels one child's whole-day StartEdu meals."""

    def __init__(
        self,
        coordinator: StartEduDataUpdateCoordinator,
        entry: ConfigEntry,
        child: StartEduChild,
        description: StartEduCancelMealButtonDescription,
    ) -> None:
        super().__init__(coordinator, entry, child)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{child.child_id}_{description.key}"
        self._attr_translation_key = description.translation_key

    @property
    def available(self) -> bool:
        child = self._current_data_child()
        return (
            bool(getattr(super(), "available", True))
            and self.coordinator.data is not None
            and child is not None
            and can_cancel(child, self._target_date())
        )

    async def async_press(self) -> None:
        child = self._current_data_child()
        target_date = self._target_date()
        if self.coordinator.data is None or child is None:
            raise HomeAssistantError("StartEdu child not found")
        if not can_cancel(child, target_date):
            raise HomeAssistantError("StartEdu meal cannot be cancelled")

        try:
            await self.coordinator.async_cancel_meal(child.child_id, target_date)
        except MealCancellationError as err:
            raise HomeAssistantError(f"StartEdu cancellation failed: {err}") from err
        except StartEduError as err:
            raise HomeAssistantError("StartEdu cancellation failed") from err

    def _target_date(self) -> date:
        return dt_util.now().date() + timedelta(
            days=self.entity_description.offset_days
        )

    def _current_data_child(self) -> StartEduChild | None:
        if self.coordinator.data is None or self._child is None:
            return None
        return next(
            (
                child
                for child in self.coordinator.data.child_accounts
                if child.child_id == self._child.child_id
            ),
            None,
        )
