"""Button platform for Eastron SDM72D — reset resettable energy counters."""

from __future__ import annotations

import logging
import struct

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pymodbus.exceptions import ModbusException, ModbusIOException

from .const import CONF_SLAVE_ID, DOMAIN
from .coordinator import _SLAVE_KWARG, SDM72DCoordinator

_LOGGER = logging.getLogger(__name__)

# Holding register 0x000E: KPPA (Key Parameter Programming Authorization).
# Writing the meter password here unlocks key-parameter writes for this session.
_REG_KPPA = 0x000E
_DEFAULT_PASSWORD = 1000.0  # factory default; stored as IEEE-754 float (2 registers)

# Holding register 0xF010: write 0x0003 to reset all resettable energy counters.
_REG_RESET = 0xF010
_VAL_RESET = 0x0003


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
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_reset_energy"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="SDM72D",
            manufacturer="Eastron",
            model="SDM72D-M-2",
        )

    async def async_press(self) -> None:
        async with self._coordinator._modbus_lock:
            try:
                client = await self._coordinator._get_client()
                slave = self._entry.data[CONF_SLAVE_ID]
                slave_kwargs = {_SLAVE_KWARG: slave} if _SLAVE_KWARG else {}

                # Step 1: unlock KPPA with factory password (float 1000.0 → 2 registers)
                raw = struct.pack(">f", _DEFAULT_PASSWORD)
                words = list(struct.unpack(">HH", raw))
                result = await client.write_registers(_REG_KPPA, words, **slave_kwargs)
                if hasattr(result, "isError") and result.isError():
                    _LOGGER.error("SDM72D KPPA unlock failed: %s", result)
                    return

                # Step 2: send reset command via FC16 (write multiple registers).
                # 0xF010 is write-only — the device executes the reset without
                # sending a Modbus response, so a ModbusIOException here is expected.
                try:
                    result = await client.write_registers(
                        _REG_RESET, [_VAL_RESET], **slave_kwargs
                    )
                    if hasattr(result, "isError") and result.isError():
                        _LOGGER.warning(
                            "SDM72D reset returned Modbus error: %s", result
                        )
                except ModbusIOException:
                    pass  # write-only register sends no response — reset was executed

                _LOGGER.info("SDM72D resettable energy counters reset")

            except ModbusException as exc:
                _LOGGER.error("SDM72D Modbus error during reset: %s", exc)
                return

        await self._coordinator.async_request_refresh()
