"""ParentOS API client."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class ParentOSApiError(Exception):
    """Base exception for ParentOS API."""


class ParentOSAuthError(ParentOSApiError):
    """Authentication error."""


class ParentOSConnectionError(ParentOSApiError):
    """Connection error."""


class ParentOSApiClient:
    """API client for ParentOS /api/ha/v1 endpoints."""

    def __init__(
        self,
        api_url: str,
        api_token: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._api_token = api_token
        self._session = session

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_token}"}

    @property
    def _base_url(self) -> str:
        return f"{self._api_url}/api/ha/v1"

    async def async_ping(self) -> dict[str, Any]:
        """Validate token and get family info."""
        return await self._request("GET", "/ping")

    async def async_get_snapshot(self) -> dict[str, Any]:
        """Get aggregated family state snapshot."""
        return await self._request("GET", "/snapshot")

    async def async_get_calendar_events(
        self, start: str, end: str
    ) -> dict[str, Any]:
        """Get calendar events for a date range (ISO 8601)."""
        return await self._request(
            "GET", "/calendar/events", params={"start": start, "end": end}
        )

    # ── Shopping list endpoints ──────────────────────────────────────────

    async def async_get_shopping_lists(self) -> dict[str, Any]:
        """Get all active shopping lists with item counts."""
        return await self._request("GET", "/shopping/lists")

    async def async_get_shopping_items(self, list_id: int) -> dict[str, Any]:
        """Get items for a shopping list."""
        return await self._request("GET", f"/shopping/lists/{list_id}/items")

    async def async_create_shopping_item(
        self, list_id: int, summary: str, description: str | None = None
    ) -> dict[str, Any]:
        """Create a shopping list item."""
        data: dict[str, Any] = {"summary": summary}
        if description:
            data["description"] = description
        return await self._request(
            "POST", f"/shopping/lists/{list_id}/items", json_data=data
        )

    async def async_update_shopping_item(
        self, item_id: int, **kwargs: Any
    ) -> dict[str, Any]:
        """Update a shopping list item (summary, status, description)."""
        return await self._request(
            "PUT", f"/shopping/items/{item_id}", json_data=kwargs
        )

    async def async_delete_shopping_items(self, uids: list[str]) -> dict[str, Any]:
        """Delete shopping list items by UIDs."""
        return await self._request(
            "DELETE", "/shopping/items", json_data={"uids": uids}
        )

    # ── HTTP transport ───────────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an API request with error handling."""
        try:
            async with asyncio.timeout(10):
                response = await self._session.request(
                    method,
                    f"{self._base_url}{path}",
                    headers=self._headers,
                    params=params,
                    json=json_data,
                )
        except asyncio.TimeoutError as err:
            raise ParentOSConnectionError("Request timed out") from err
        except aiohttp.ClientError:
            raise ParentOSConnectionError("Connection failed") from None

        if response.status == 401:
            raise ParentOSAuthError("Invalid or expired developer token")
        if response.status == 403:
            raise ParentOSAuthError("Token missing required scopes")
        if response.status >= 400:
            _LOGGER.debug("API %s %s returned %s", method, path, response.status)
            raise ParentOSApiError(f"API error (HTTP {response.status})")

        return await response.json()
