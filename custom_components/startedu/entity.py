from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import StartEduDataUpdateCoordinator
from .models import StartEduChild


class StartEduEntity(CoordinatorEntity[StartEduDataUpdateCoordinator]):
    """Base entity for StartEdu integration entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: StartEduDataUpdateCoordinator,
        entry: ConfigEntry,
        child: StartEduChild | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._child = child

    @property
    def device_info(self) -> DeviceInfo:
        if self._child is not None:
            return DeviceInfo(
                identifiers={(DOMAIN, self._entry.entry_id, self._child.child_id)},
                manufacturer="StartEdu",
                name=self._child.name,
            )
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            manufacturer="StartEdu",
            name="StartEdu",
        )
