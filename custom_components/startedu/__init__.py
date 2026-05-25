from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import StartEduClient
from .const import CONF_BASE_URL, DEFAULT_BASE_URL, DOMAIN, PLATFORMS
from .coordinator import StartEduDataUpdateCoordinator


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
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a StartEdu config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

