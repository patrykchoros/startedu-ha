from __future__ import annotations

from datetime import date

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import MealCancellationError, StartEduClient, StartEduError
from .const import (
    ATTR_CHILD_ID,
    ATTR_CONFIG_ENTRY_ID,
    ATTR_DATE,
    CONF_BASE_URL,
    DEFAULT_BASE_URL,
    DOMAIN,
    PLATFORMS,
    SERVICE_CANCEL_MEAL,
)
from .coordinator import StartEduDataUpdateCoordinator

CANCEL_MEAL_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_CHILD_ID): str,
        vol.Required(ATTR_DATE): str,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up StartEdu from a config entry."""
    session = async_get_clientsession(hass)
    client = StartEduClient(
        session,
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        base_url=entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
    )
    coordinator = StartEduDataUpdateCoordinator(hass, client, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    _async_register_services(hass)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a StartEdu config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            _async_remove_services(hass)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is None:
        await hass.config_entries.async_reload(entry.entry_id)
        return

    coordinator.apply_options()
    coordinator.async_update_listeners()


def _async_register_services(hass: HomeAssistant) -> None:
    services = hass.services
    if services.has_service(DOMAIN, SERVICE_CANCEL_MEAL):
        return

    async def _handle_cancel_meal(call: ServiceCall) -> None:
        await _async_handle_cancel_meal_service(hass, call)

    services.async_register(
        DOMAIN,
        SERVICE_CANCEL_MEAL,
        _handle_cancel_meal,
        schema=CANCEL_MEAL_SERVICE_SCHEMA,
    )


def _async_remove_services(hass: HomeAssistant) -> None:
    services = hass.services
    if services.has_service(DOMAIN, SERVICE_CANCEL_MEAL):
        services.async_remove(DOMAIN, SERVICE_CANCEL_MEAL)


async def _async_handle_cancel_meal_service(
    hass: HomeAssistant,
    call: ServiceCall,
) -> None:
    entry_id = str(call.data[ATTR_CONFIG_ENTRY_ID])
    child_id = str(call.data[ATTR_CHILD_ID])
    target_date = _parse_service_date(str(call.data[ATTR_DATE]))

    coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
    if coordinator is None:
        raise HomeAssistantError("StartEdu entry not found")

    try:
        await coordinator.async_cancel_meal(child_id, target_date)
    except MealCancellationError as err:
        raise HomeAssistantError(f"StartEdu cancellation failed: {err}") from err
    except StartEduError as err:
        raise HomeAssistantError("StartEdu cancellation failed") from err


def _parse_service_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as err:
        raise HomeAssistantError("Invalid StartEdu cancellation date") from err
