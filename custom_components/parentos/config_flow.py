"""Config flow for ParentOS integration."""
from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import ParentOSApiClient, ParentOSAuthError, ParentOSConnectionError
from .const import CONF_API_TOKEN, CONF_API_URL, DEFAULT_API_URL, DOMAIN, LOGGER


class ParentOSConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ParentOS."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step — user enters API URL and token."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_url = user_input[CONF_API_URL].rstrip("/")
            api_token = user_input[CONF_API_TOKEN]

            try:
                client = ParentOSApiClient(
                    api_url=api_url,
                    api_token=api_token,
                    session=async_create_clientsession(self.hass),
                )
                ping_result = await client.async_ping()
            except ParentOSAuthError:
                errors["base"] = "invalid_auth"
            except ParentOSConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"
            else:
                family_id = ping_result.get("familyId", "unknown")

                await self.async_set_unique_id(f"parentos_{family_id}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"ParentOS ({family_id})",
                    data={
                        CONF_API_URL: api_url,
                        CONF_API_TOKEN: api_token,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_URL, default=DEFAULT_API_URL): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.URL)
                    ),
                    vol.Required(CONF_API_TOKEN): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth when token expires."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauth confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            reauth_entry = self._get_reauth_entry()
            api_url = reauth_entry.data[CONF_API_URL]
            api_token = user_input[CONF_API_TOKEN]

            try:
                client = ParentOSApiClient(
                    api_url=api_url,
                    api_token=api_token,
                    session=async_create_clientsession(self.hass),
                )
                await client.async_ping()
            except ParentOSAuthError:
                errors["base"] = "invalid_auth"
            except ParentOSConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                LOGGER.exception("Unexpected error during reauth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_API_TOKEN: api_token},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_TOKEN): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )
