from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .client import CannotConnect, InvalidAuth, StartEduClient, StartEduError
from .const import (
    DOMAIN,
)
from .models import StartEduAccountData
from .sync import (
    next_future_date,
    next_local_midnight,
    next_local_month_start,
    scan_interval_minutes,
    start_of_local_date,
)

_LOGGER = logging.getLogger(__name__)


class StartEduDataUpdateCoordinator(DataUpdateCoordinator[StartEduAccountData]):
    """Coordinates StartEdu polling for all entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: StartEduClient,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=scan_interval_minutes(entry.options)),
        )
        self.client = client
        self.entry = entry
        self._day_rollover_unsub: CALLBACK_TYPE | None = None
        self._month_rollover_unsub: CALLBACK_TYPE | None = None
        self._next_order_opening_unsub: CALLBACK_TYPE | None = None
        self._schedule_day_rollover()
        self._schedule_month_rollover()
        entry.async_on_unload(self.cancel_scheduled_refreshes)

    def apply_options(self) -> None:
        """Apply local option changes without fetching StartEdu."""
        self.update_interval = timedelta(
            minutes=scan_interval_minutes(self.entry.options)
        )

    @callback
    def cancel_scheduled_refreshes(self) -> None:
        """Cancel scheduled local updates and refresh triggers."""
        for unsubscribe in (
            self._day_rollover_unsub,
            self._month_rollover_unsub,
            self._next_order_opening_unsub,
        ):
            if unsubscribe is not None:
                unsubscribe()
        self._day_rollover_unsub = None
        self._month_rollover_unsub = None
        self._next_order_opening_unsub = None

    @callback
    def _schedule_day_rollover(self) -> None:
        if self._day_rollover_unsub is not None:
            self._day_rollover_unsub()
        self._day_rollover_unsub = async_track_point_in_time(
            self.hass,
            self._handle_day_rollover,
            next_local_midnight(dt_util.now()),
        )

    @callback
    def _handle_day_rollover(self, *_: object) -> None:
        self.async_update_listeners()
        self._schedule_day_rollover()

    @callback
    def _schedule_month_rollover(self) -> None:
        if self._month_rollover_unsub is not None:
            self._month_rollover_unsub()
        self._month_rollover_unsub = async_track_point_in_time(
            self.hass,
            self._handle_full_refresh_schedule,
            next_local_month_start(dt_util.now()),
        )

    @callback
    def _schedule_next_order_opening_refresh(self, data: StartEduAccountData) -> None:
        if self._next_order_opening_unsub is not None:
            self._next_order_opening_unsub()
            self._next_order_opening_unsub = None

        now = dt_util.now()
        opening_date = next_future_date(
            tuple(
                child.next_order_opening_date
                for child in data.child_accounts
                if child.next_order_opening_date is not None
            ),
            now.date(),
        )
        if opening_date is None:
            return

        self._next_order_opening_unsub = async_track_point_in_time(
            self.hass,
            self._handle_full_refresh_schedule,
            start_of_local_date(opening_date, now),
        )

    @callback
    def _handle_full_refresh_schedule(self, *_: object) -> None:
        self._schedule_month_rollover()
        self.hass.async_create_task(self.async_request_refresh())

    async def _async_update_data(self) -> StartEduAccountData:
        try:
            async with asyncio.timeout(30):
                data = await self.client.async_get_account_data()
                self._schedule_next_order_opening_refresh(data)
                return data
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed from err
        except CannotConnect as err:
            raise UpdateFailed(str(err)) from err
        except StartEduError as err:
            raise UpdateFailed(str(err)) from err
