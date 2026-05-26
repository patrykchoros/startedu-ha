from __future__ import annotations

from types import SimpleNamespace
import unittest

from ha_stubs import install_homeassistant_stubs

install_homeassistant_stubs()

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.startedu.client import CannotConnect, InvalidAuth
from custom_components.startedu.config_flow import StartEduConfigFlow
from custom_components.startedu.const import CONF_BASE_URL, DEFAULT_BASE_URL


class FakeConfigEntry:
    entry_id = "entry-id"

    def __init__(self) -> None:
        self.data = {
            CONF_USERNAME: "family@example.test",
            CONF_PASSWORD: "old-password",
            CONF_BASE_URL: DEFAULT_BASE_URL,
        }


class FakeConfigEntries:
    def __init__(self, entry: FakeConfigEntry) -> None:
        self.entry = entry
        self.reloaded: list[str] = []
        self.updated_data: dict[str, object] | None = None

    def async_get_entry(self, entry_id: str) -> FakeConfigEntry:
        self.requested_entry_id = entry_id
        return self.entry

    def async_update_entry(
        self,
        entry: FakeConfigEntry,
        *,
        data: dict[str, object],
    ) -> None:
        self.updated_data = data
        entry.data = data

    async def async_reload(self, entry_id: str) -> None:
        self.reloaded.append(entry_id)


class ConfigFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_user_step_success_creates_entry(self) -> None:
        flow = StartEduConfigFlow()
        validated: list[dict[str, object]] = []

        async def validate(data: dict[str, object]) -> None:
            validated.append(dict(data))

        flow._async_validate_credentials = validate

        result = await flow.async_step_user(
            {
                CONF_USERNAME: " Family@Example.Test ",
                CONF_PASSWORD: "secret",
                CONF_BASE_URL: DEFAULT_BASE_URL,
            }
        )

        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "StartEdu")
        self.assertEqual(result["data"][CONF_USERNAME], "Family@Example.Test")
        self.assertEqual(flow.unique_id, "family@example.test")
        self.assertEqual(validated[0][CONF_USERNAME], "Family@Example.Test")

    async def test_user_step_invalid_credentials_shows_error(self) -> None:
        flow = StartEduConfigFlow()

        async def validate(data: dict[str, object]) -> None:
            raise InvalidAuth("bad credentials")

        flow._async_validate_credentials = validate

        result = await flow.async_step_user(
            {
                CONF_USERNAME: "family@example.test",
                CONF_PASSWORD: "wrong",
                CONF_BASE_URL: DEFAULT_BASE_URL,
            }
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"], {"base": "invalid_auth"})

    async def test_user_step_connection_failure_shows_error(self) -> None:
        flow = StartEduConfigFlow()

        async def validate(data: dict[str, object]) -> None:
            raise CannotConnect("offline")

        flow._async_validate_credentials = validate

        result = await flow.async_step_user(
            {
                CONF_USERNAME: "family@example.test",
                CONF_PASSWORD: "secret",
                CONF_BASE_URL: DEFAULT_BASE_URL,
            }
        )

        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"], {"base": "cannot_connect"})

    async def test_reauth_updates_password_and_reloads_entry(self) -> None:
        entry = FakeConfigEntry()
        config_entries = FakeConfigEntries(entry)
        flow = StartEduConfigFlow()
        flow.hass = SimpleNamespace(config_entries=config_entries)
        flow.context = {"entry_id": entry.entry_id}

        async def validate(data: dict[str, object]) -> None:
            self.assertEqual(data[CONF_PASSWORD], "new-password")

        flow._async_validate_credentials = validate

        start_result = await flow.async_step_reauth({})
        finish_result = await flow.async_step_reauth_confirm(
            {CONF_PASSWORD: "new-password"}
        )

        self.assertEqual(start_result["type"], "form")
        self.assertEqual(start_result["step_id"], "reauth_confirm")
        self.assertEqual(
            finish_result,
            {"type": "abort", "reason": "reauth_successful"},
        )
        self.assertEqual(entry.data[CONF_PASSWORD], "new-password")
        self.assertEqual(config_entries.reloaded, [entry.entry_id])
