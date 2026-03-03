"""Todo platform for ParentOS shopping lists."""
from __future__ import annotations

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ParentOSConfigEntry
from .const import ATTRIBUTION, DOMAIN
from .coordinator import ParentOSCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ParentOSConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ParentOS todo entities from shopping lists."""
    coordinator: ParentOSCoordinator = entry.runtime_data
    shopping_lists = coordinator.data.get("shopping_lists", [])

    async_add_entities(
        ParentOSShoppingList(coordinator, entry, sl)
        for sl in shopping_lists
    )


class ParentOSShoppingList(
    CoordinatorEntity[ParentOSCoordinator], TodoListEntity
):
    """ParentOS shopping list as a HA todo entity."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(
        self,
        coordinator: ParentOSCoordinator,
        entry: ParentOSConfigEntry,
        shopping_list: dict,
    ) -> None:
        super().__init__(coordinator)
        self._list_id: int = shopping_list["id"]
        self._attr_name = shopping_list["name"]
        self._attr_unique_id = f"{entry.entry_id}_shopping_{self._list_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="ParentOS",
            manufacturer="ParentOS",
            model="Family Hub",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://app.parentos.ai",
        )
        self._items: list[TodoItem] = []

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Return cached todo items."""
        return self._items

    async def async_added_to_hass(self) -> None:
        """Fetch items when entity is added."""
        await super().async_added_to_hass()
        await self._async_refresh_items()

    def _handle_coordinator_update(self) -> None:
        """Schedule item refresh when coordinator updates."""
        self.hass.async_create_task(self._async_refresh_items())
        super()._handle_coordinator_update()

    async def _async_refresh_items(self) -> None:
        """Fetch items from ParentOS API."""
        try:
            result = await self.coordinator.client.async_get_shopping_items(
                self._list_id
            )
            self._items = [
                TodoItem(
                    uid=item["uid"],
                    summary=item["summary"],
                    status=(
                        TodoItemStatus.COMPLETED
                        if item["status"] == "completed"
                        else TodoItemStatus.NEEDS_ACTION
                    ),
                    description=item.get("description"),
                )
                for item in result.get("items", [])
            ]
        except Exception:
            self._items = []
        self.async_write_ha_state()

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create a new shopping list item."""
        try:
            await self.coordinator.client.async_create_shopping_item(
                list_id=self._list_id,
                summary=item.summary or "",
                description=item.description,
            )
        except Exception as err:
            raise HomeAssistantError(f"Failed to create item: {err}") from err
        await self._async_refresh_items()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an existing shopping list item."""
        if not item.uid:
            return
        data: dict = {}
        if item.summary is not None:
            data["summary"] = item.summary
        if item.status is not None:
            data["status"] = (
                "completed"
                if item.status == TodoItemStatus.COMPLETED
                else "needs_action"
            )
        if item.description is not None:
            data["description"] = item.description
        try:
            await self.coordinator.client.async_update_shopping_item(
                int(item.uid), **data
            )
        except Exception as err:
            raise HomeAssistantError(f"Failed to update item: {err}") from err
        await self._async_refresh_items()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete shopping list items."""
        try:
            await self.coordinator.client.async_delete_shopping_items(uids)
        except Exception as err:
            raise HomeAssistantError(f"Failed to delete items: {err}") from err
        await self._async_refresh_items()
