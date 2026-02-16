"""Calendar platform for ParentOS."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import ParentOSConfigEntry
from .api import ParentOSApiClient
from .const import ATTRIBUTION, DOMAIN
from .coordinator import ParentOSCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ParentOSConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ParentOS calendar entity."""
    coordinator: ParentOSCoordinator = entry.runtime_data
    async_add_entities([ParentOSCalendar(coordinator, entry)])


class ParentOSCalendar(CoordinatorEntity[ParentOSCoordinator], CalendarEntity):
    """ParentOS family calendar entity."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_name = "Family Calendar"

    def __init__(
        self,
        coordinator: ParentOSCoordinator,
        entry: ParentOSConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="ParentOS",
            manufacturer="ParentOS",
            model="Family Hub",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://app.parentos.ai",
        )
        self._client: ParentOSApiClient = coordinator.client

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event from snapshot."""
        if not self.coordinator.data:
            return None

        calendar = self.coordinator.data.get("calendar", {})
        title = calendar.get("nextEventTitle")
        minutes = calendar.get("nextEventStartsInMinutes")

        if not title or minutes is None:
            return None

        now = dt_util.now()
        start = now + timedelta(minutes=minutes)
        end = start + timedelta(hours=1)

        return CalendarEvent(
            summary=title,
            start=start,
            end=end,
        )

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Fetch events from ParentOS API for a date range."""
        try:
            result = await self._client.async_get_calendar_events(
                start=start_date.isoformat(),
                end=end_date.isoformat(),
            )
        except Exception:
            return []

        events: list[CalendarEvent] = []
        for ev in result.get("events", []):
            try:
                event_start = datetime.fromisoformat(ev["start"])
                event_end = datetime.fromisoformat(ev["end"])

                events.append(
                    CalendarEvent(
                        summary=ev.get("title", ""),
                        start=event_start,
                        end=event_end,
                        location=ev.get("location"),
                    )
                )
            except (KeyError, ValueError):
                continue

        return events
