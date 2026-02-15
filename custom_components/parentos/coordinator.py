"""DataUpdateCoordinator for ParentOS."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ParentOSApiClient, ParentOSAuthError, ParentOSApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER


class ParentOSCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch ParentOS snapshot data."""

    def __init__(self, hass: HomeAssistant, client: ParentOSApiClient) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch snapshot from ParentOS API."""
        try:
            return await self.client.async_get_snapshot()
        except ParentOSAuthError as err:
            raise ConfigEntryAuthFailed(
                "Developer token is invalid or expired"
            ) from err
        except ParentOSApiError as err:
            raise UpdateFailed(f"Error fetching ParentOS data: {err}") from err
