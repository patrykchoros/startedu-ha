from __future__ import annotations

import asyncio
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import CannotConnect, InvalidAuth, StartEduClient, StartEduError
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
)
from .models import StartEduAccountData


class StartEduDataUpdateCoordinator(DataUpdateCoordinator[StartEduAccountData]):
    """Coordinates StartEdu polling for all entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: StartEduClient,
        entry: ConfigEntry,
    ) -> None:
        minutes = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES))
        minutes = min(max(minutes, MIN_SCAN_INTERVAL_MINUTES), MAX_SCAN_INTERVAL_MINUTES)
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=DOMAIN,
            update_interval=timedelta(minutes=minutes),
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> StartEduAccountData:
        try:
            async with asyncio.timeout(30):
                return await self.client.async_get_account_data()
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed from err
        except CannotConnect as err:
            raise UpdateFailed(str(err)) from err
        except StartEduError as err:
            raise UpdateFailed(str(err)) from err

