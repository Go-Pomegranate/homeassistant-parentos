"""DataUpdateCoordinator for ParentOS."""
from __future__ import annotations

import asyncio
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
        """Fetch snapshot, shopping lists, meals, and family members."""
        try:
            snapshot, shopping_lists, meals, members = await asyncio.gather(
                self.client.async_get_snapshot(),
                self._safe_fetch("shopping_lists", self.client.async_get_shopping_lists, "lists"),
                self._safe_fetch("meals_today", self.client.async_get_meals_today, "meals"),
                self._safe_fetch("family_members", self.client.async_get_family_members, "members"),
            )
            snapshot["shopping_lists"] = shopping_lists
            snapshot["meals_today"] = meals
            snapshot["family_members"] = members
            return snapshot
        except ParentOSAuthError as err:
            raise ConfigEntryAuthFailed(
                "Developer token is invalid or expired"
            ) from err
        except ParentOSApiError as err:
            raise UpdateFailed(f"Error fetching ParentOS data: {err}") from err

    async def _safe_fetch(
        self, name: str, fn: Any, key: str
    ) -> list[dict[str, Any]]:
        """Fetch optional data, gracefully returning empty on failures."""
        try:
            result = await fn()
            return result.get(key, [])
        except ParentOSAuthError:
            LOGGER.debug("Token lacks scope for %s, skipping", name)
            return []
        except Exception:
            LOGGER.debug("Failed to fetch %s", name)
            return []
