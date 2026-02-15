"""Sensor platform for ParentOS."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ParentOSConfigEntry
from .const import ATTRIBUTION, DOMAIN
from .coordinator import ParentOSCoordinator


@dataclass(frozen=True, kw_only=True)
class ParentOSSensorDescription(SensorEntityDescription):
    """Describe a ParentOS sensor."""

    value_fn: str  # dot-notation path into snapshot data
    icon_map: dict[str, str] | None = None


SENSOR_DESCRIPTIONS: tuple[ParentOSSensorDescription, ...] = (
    # --- Day State ---
    ParentOSSensorDescription(
        key="day_state",
        translation_key="day_state",
        icon="mdi:weather-sunny",
        value_fn="dayState",
        icon_map={
            "calm": "mdi:weather-sunny",
            "moderate": "mdi:weather-partly-cloudy",
            "busy": "mdi:weather-cloudy",
            "full": "mdi:weather-lightning",
        },
    ),
    ParentOSSensorDescription(
        key="attention_needed",
        translation_key="attention_needed",
        icon="mdi:alert-circle-outline",
        value_fn="attentionNeeded",
    ),
    # --- Calendar ---
    ParentOSSensorDescription(
        key="events_today",
        translation_key="events_today",
        icon="mdi:calendar-today",
        value_fn="calendar.eventsToday",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ParentOSSensorDescription(
        key="busy_minutes",
        translation_key="busy_minutes",
        icon="mdi:clock-outline",
        value_fn="calendar.busyMinutes",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ParentOSSensorDescription(
        key="conflict_count",
        translation_key="conflict_count",
        icon="mdi:calendar-alert",
        value_fn="calendar.conflictCount",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ParentOSSensorDescription(
        key="next_event",
        translation_key="next_event",
        icon="mdi:calendar-arrow-right",
        value_fn="calendar.nextEventTitle",
    ),
    ParentOSSensorDescription(
        key="next_event_minutes",
        translation_key="next_event_minutes",
        icon="mdi:timer-outline",
        value_fn="calendar.nextEventStartsInMinutes",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ParentOSSensorDescription(
        key="longest_free_slot",
        translation_key="longest_free_slot",
        icon="mdi:calendar-blank-outline",
        value_fn="calendar.longestFreeSlotMinutes",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # --- Baseline ---
    ParentOSSensorDescription(
        key="family_pace",
        translation_key="family_pace",
        icon="mdi:speedometer",
        value_fn="baseline.familyPace",
        icon_map={
            "slow": "mdi:speedometer-slow",
            "medium": "mdi:speedometer-medium",
            "fast": "mdi:speedometer",
        },
    ),
    ParentOSSensorDescription(
        key="baseline_trend",
        translation_key="baseline_trend",
        icon="mdi:trending-neutral",
        value_fn="baseline.trendDirection",
        icon_map={
            "up": "mdi:trending-up",
            "down": "mdi:trending-down",
            "stable": "mdi:trending-neutral",
        },
    ),
    # --- Health ---
    ParentOSSensorDescription(
        key="health_status",
        translation_key="health_status",
        icon="mdi:heart-pulse",
        value_fn="health.status",
    ),
    ParentOSSensorDescription(
        key="medications_tracked",
        translation_key="medications_tracked",
        icon="mdi:pill",
        value_fn="health.medicationsTracked",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # --- Finance ---
    ParentOSSensorDescription(
        key="finance_engagement",
        translation_key="finance_engagement",
        icon="mdi:cash-check",
        value_fn="finance.trackingEngagement",
    ),
    # --- Tasks ---
    ParentOSSensorDescription(
        key="tasks_overdue",
        translation_key="tasks_overdue",
        icon="mdi:clipboard-alert-outline",
        value_fn="tasks.overdueCount",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ParentOSSensorDescription(
        key="tasks_pending_today",
        translation_key="tasks_pending_today",
        icon="mdi:clipboard-list-outline",
        value_fn="tasks.pendingTodayCount",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


def _resolve(data: dict[str, Any], path: str) -> Any:
    """Resolve a dot-notation path from nested dict."""
    for key in path.split("."):
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return None
    return data


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ParentOSConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ParentOS sensor entities."""
    coordinator: ParentOSCoordinator = entry.runtime_data
    async_add_entities(
        ParentOSSensor(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS
    )


class ParentOSSensor(CoordinatorEntity[ParentOSCoordinator], SensorEntity):
    """ParentOS sensor entity."""

    entity_description: ParentOSSensorDescription
    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ParentOSCoordinator,
        description: ParentOSSensorDescription,
        entry: ParentOSConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="ParentOS",
            manufacturer="ParentOS",
            model="Family Hub",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://app.parentos.ai",
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value from snapshot data."""
        if not self.coordinator.data:
            return None
        return _resolve(self.coordinator.data, self.entity_description.value_fn)

    @property
    def icon(self) -> str:
        """Return dynamic icon based on state."""
        if self.entity_description.icon_map and self.native_value:
            return self.entity_description.icon_map.get(
                str(self.native_value), self.entity_description.icon or "mdi:help"
            )
        return self.entity_description.icon or "mdi:help"
