"""Sensor platform for ParentOS."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ParentOSConfigEntry
from .const import ATTRIBUTION, DOMAIN, LOGGER
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

    entities: list[SensorEntity] = [
        ParentOSSensor(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS
    ]

    # Meal plan sensor (from coordinator.data["meals_today"])
    entities.append(ParentOSMealPlanSensor(coordinator, entry))

    # Family member sensors (one per member, with dynamic discovery)
    initial_members = coordinator.data.get("family_members", [])
    known_member_ids: set[int] = {m["id"] for m in initial_members}
    for member in initial_members:
        entities.append(ParentOSFamilyMemberSensor(coordinator, entry, member))

    async_add_entities(entities)

    # Dynamic family member discovery — auto-create/remove on coordinator updates
    @callback
    def _async_check_members() -> None:
        current_members = coordinator.data.get("family_members", [])
        if not current_members:
            return  # safety guard against empty API response

        current_ids = {m["id"] for m in current_members}

        # New members
        new_ids = current_ids - known_member_ids
        if new_ids:
            new_members = [m for m in current_members if m["id"] in new_ids]
            known_member_ids.update(new_ids)
            async_add_entities(
                ParentOSFamilyMemberSensor(coordinator, entry, m)
                for m in new_members
            )
            LOGGER.debug("Created %d new family member sensors", len(new_ids))

        # Removed members
        removed_ids = known_member_ids - current_ids
        if removed_ids and current_ids:
            ent_reg = er.async_get(hass)
            for member_id in removed_ids:
                unique_id = f"{entry.entry_id}_member_{member_id}"
                entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
                if entity_id:
                    ent_reg.async_remove(entity_id)
            known_member_ids.difference_update(removed_ids)
            LOGGER.debug("Removed %d family member sensors", len(removed_ids))

    entry.async_on_unload(coordinator.async_add_listener(_async_check_members))


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


class ParentOSMealPlanSensor(CoordinatorEntity[ParentOSCoordinator], SensorEntity):
    """Sensor showing today's meal plan."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_name = "Meal Plan Today"
    _attr_icon = "mdi:silverware-fork-knife"

    def __init__(
        self,
        coordinator: ParentOSCoordinator,
        entry: ParentOSConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_meal_plan_today"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="ParentOS",
            manufacturer="ParentOS",
            model="Family Hub",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://app.parentos.ai",
        )

    @property
    def _meals(self) -> list[dict[str, Any]]:
        if not self.coordinator.data:
            return []
        return self.coordinator.data.get("meals_today", [])

    @property
    def native_value(self) -> int:
        """Return number of meals planned today."""
        return len(self._meals)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return meal details as attributes."""
        meals = self._meals
        attrs: dict[str, Any] = {"meals_count": len(meals)}

        for meal_type in ("breakfast", "lunch", "dinner", "snack"):
            typed = [m for m in meals if m.get("type") == meal_type]
            if typed:
                attrs[meal_type] = ", ".join(m.get("name", "") for m in typed)
            else:
                attrs[meal_type] = None

        # Next upcoming meal
        now_hour = datetime.now().hour
        order = {"breakfast": 8, "lunch": 12, "dinner": 18, "snack": 15}
        upcoming = [
            m for m in meals
            if order.get(m.get("type", ""), 24) >= now_hour
        ]
        attrs["next_meal"] = upcoming[0].get("name") if upcoming else None

        return attrs


class ParentOSFamilyMemberSensor(CoordinatorEntity[ParentOSCoordinator], SensorEntity):
    """Sensor for a single family member's status."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ParentOSCoordinator,
        entry: ParentOSConfigEntry,
        member: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._member_id: int = member["id"]
        member_name = member.get("name", f"Member {self._member_id}")
        self._attr_name = member_name
        self._attr_unique_id = f"{entry.entry_id}_member_{self._member_id}"
        self._attr_icon = (
            "mdi:account-child" if member.get("role") == "child"
            else "mdi:account"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="ParentOS",
            manufacturer="ParentOS",
            model="Family Hub",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://app.parentos.ai",
        )

    @property
    def _member_data(self) -> dict[str, Any] | None:
        if not self.coordinator.data:
            return None
        for m in self.coordinator.data.get("family_members", []):
            if m.get("id") == self._member_id:
                return m
        return None

    @property
    def native_value(self) -> str | None:
        """Return member status (healthy, sick, etc.)."""
        member = self._member_data
        return member.get("status", "unknown") if member else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return member details as attributes."""
        member = self._member_data
        if not member:
            return {}
        return {
            "role": member.get("role"),
            "age": member.get("age"),
            "picture": member.get("picture"),
        }

    @property
    def entity_picture(self) -> str | None:
        """Return member avatar."""
        member = self._member_data
        if member:
            return member.get("picture")
        return None
