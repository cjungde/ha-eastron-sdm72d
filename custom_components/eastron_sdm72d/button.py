"""Button platform for Eastron SDM72D — reset resettable energy counters."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from modbus_connection.exceptions import ModbusError

from .const import DOMAIN
from .coordinator import SDM72DCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SDM72DCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SDM72DResetButton(coordinator, entry)])


class SDM72DResetButton(ButtonEntity):
    """Resets the SDM72D resettable import/export/net energy counters."""

    _attr_has_entity_name = True
    _attr_name = "Reset Energy Counters"
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator: SDM72DCoordinator, entry: ConfigEntry) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_reset_energy"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="SDM72D",
            manufacturer="Eastron",
            model="SDM72D-M-2",
        )

    async def async_press(self) -> None:
        """Unlock key-parameter programming, then clear the counters.

        The two-step sequence and the meter's silence on the write-only reset
        register are the device library's business; a refused unlock surfaces
        here, because the counters would then still be standing.
        """
        try:
            await self._coordinator.meter.async_reset_energy()
        except ModbusError as exc:
            _LOGGER.error("SDM72D reset failed: %s", exc)
            return

        _LOGGER.info("SDM72D resettable energy counters reset")
        await self._coordinator.async_request_refresh()
