from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import CannotConnect, InvalidAuth, StartEduClient
from .const import (
    CONF_AFTERNOON_SNACK_TIME,
    CONF_BREAKFAST_TIME,
    CONF_LUNCH_TIME,
    CONF_OTHER_MEAL_TIME,
    CONF_SCAN_INTERVAL,
    DEFAULT_AFTERNOON_SNACK_TIME,
    DEFAULT_BASE_URL,
    DEFAULT_BREAKFAST_TIME,
    DEFAULT_LUNCH_TIME,
    DEFAULT_OTHER_MEAL_TIME,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MAX_SCAN_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL_MINUTES,
)

TIME_VALUE = vol.All(str, vol.Match(r"^([01]\d|2[0-3]):[0-5]\d$"))


def _user_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")): str,
            vol.Required(CONF_PASSWORD): str,
        }
    )


class StartEduConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for StartEdu."""

    VERSION = 1

    def __init__(self) -> None:
        self._reauth_entry: config_entries.ConfigEntry | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return StartEduOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            user_input[CONF_USERNAME] = username
            try:
                await self._async_validate_credentials(user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - Home Assistant displays unknown error.
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(username.casefold())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="StartEdu", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> config_entries.FlowResult:
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.FlowResult:
        if self._reauth_entry is None:
            return self.async_abort(reason="reauth_failed")

        errors: dict[str, str] = {}
        data = dict(self._reauth_entry.data)

        if user_input is not None:
            data[CONF_PASSWORD] = user_input[CONF_PASSWORD]
            try:
                await self._async_validate_credentials(data)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data=data,
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    async def _async_validate_credentials(self, data: dict[str, Any]) -> None:
        session = async_get_clientsession(self.hass)
        client = StartEduClient(
            session,
            data[CONF_USERNAME],
            data[CONF_PASSWORD],
            base_url=DEFAULT_BASE_URL,
        )
        await client.async_login()


class StartEduOptionsFlow(config_entries.OptionsFlow):
    """Handle StartEdu options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            DEFAULT_SCAN_INTERVAL_MINUTES,
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=current_interval,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_SCAN_INTERVAL_MINUTES,
                            max=MAX_SCAN_INTERVAL_MINUTES,
                        ),
                    ),
                    vol.Required(
                        CONF_BREAKFAST_TIME,
                        default=self._config_entry.options.get(
                            CONF_BREAKFAST_TIME,
                            DEFAULT_BREAKFAST_TIME,
                        ),
                    ): TIME_VALUE,
                    vol.Required(
                        CONF_LUNCH_TIME,
                        default=self._config_entry.options.get(
                            CONF_LUNCH_TIME,
                            DEFAULT_LUNCH_TIME,
                        ),
                    ): TIME_VALUE,
                    vol.Required(
                        CONF_AFTERNOON_SNACK_TIME,
                        default=self._config_entry.options.get(
                            CONF_AFTERNOON_SNACK_TIME,
                            DEFAULT_AFTERNOON_SNACK_TIME,
                        ),
                    ): TIME_VALUE,
                    vol.Required(
                        CONF_OTHER_MEAL_TIME,
                        default=self._config_entry.options.get(
                            CONF_OTHER_MEAL_TIME,
                            DEFAULT_OTHER_MEAL_TIME,
                        ),
                    ): TIME_VALUE,
                }
            ),
        )
