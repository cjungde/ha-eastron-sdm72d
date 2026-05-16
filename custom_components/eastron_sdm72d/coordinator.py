"""DataUpdateCoordinator for the Eastron SDM72D."""
from __future__ import annotations

import logging
import struct
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_CONNECTION_TYPE,
    CONF_SLAVE_ID,
    CONF_SERIAL_PORT,
    CONF_BAUDRATE,
    CONF_PARITY,
    CONF_STOPBITS,
    CONF_SCAN_INTERVAL,
    CONNECTION_TCP,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# SDM72D input register map (all values are 32-bit IEEE 754 floats, 2 registers each)
_REG_VOLTAGE_L1 = 0       # V
_REG_VOLTAGE_L2 = 2       # V
_REG_VOLTAGE_L3 = 4       # V
_REG_CURRENT_L1 = 6       # A
_REG_CURRENT_L2 = 8       # A
_REG_CURRENT_L3 = 10      # A
_REG_POWER_L1 = 12        # W
_REG_POWER_L2 = 14        # W
_REG_POWER_L3 = 16        # W
_REG_NEUTRAL_CURRENT = 48  # A
_REG_TOTAL_POWER = 52      # W
_REG_POWER_FACTOR = 62     # dimensionless
_REG_FREQUENCY = 70        # Hz
_REG_IMPORT_ENERGY = 72    # kWh
_REG_EXPORT_ENERGY = 74    # kWh

# Read two contiguous blocks to cover all needed registers
_BLOCK1_START = 0   # registers 0-17: voltages, currents, per-phase power
_BLOCK1_COUNT = 18
_BLOCK2_START = 48  # registers 48-75: neutral I, total P, PF, freq, energy
_BLOCK2_COUNT = 28


def _to_float(registers: list[int], address: int, block_start: int) -> float:
    """Decode two 16-bit input registers as a big-endian IEEE 754 float32."""
    offset = address - block_start
    raw = struct.pack(">HH", registers[offset], registers[offset + 1])
    return round(struct.unpack(">f", raw)[0], 4)


class SDM72DCoordinator(DataUpdateCoordinator[dict[str, float]]):
    """Polls the SDM72D at a fixed interval and distributes data to sensors."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._entry = entry
        self._client: Any = None
        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _get_client(self) -> Any:
        """Return a connected Modbus client, (re-)connecting if necessary."""
        from pymodbus.client import AsyncModbusTcpClient, AsyncModbusSerialClient

        if self._client is not None and self._client.connected:
            return self._client

        data = self._entry.data
        if data.get(CONF_CONNECTION_TYPE, CONNECTION_TCP) == CONNECTION_TCP:
            self._client = AsyncModbusTcpClient(
                host=data["host"],
                port=data.get("port", 502),
            )
        else:
            self._client = AsyncModbusSerialClient(
                port=data[CONF_SERIAL_PORT],
                baudrate=data.get(CONF_BAUDRATE, 9600),
                parity=data.get(CONF_PARITY, "N"),
                stopbits=data.get(CONF_STOPBITS, 1),
                bytesize=8,
            )

        await self._client.connect()
        if not self._client.connected:
            self._client = None
            raise UpdateFailed("Could not connect to SDM72D")
        return self._client

    async def _async_update_data(self) -> dict[str, float]:
        from pymodbus.exceptions import ModbusException

        slave = self._entry.data[CONF_SLAVE_ID]
        try:
            client = await self._get_client()

            r1 = await client.read_input_registers(
                address=_BLOCK1_START, count=_BLOCK1_COUNT, slave=slave
            )
            r2 = await client.read_input_registers(
                address=_BLOCK2_START, count=_BLOCK2_COUNT, slave=slave
            )

            if hasattr(r1, "isError") and r1.isError():
                raise UpdateFailed(f"Modbus error block 1: {r1}")
            if hasattr(r2, "isError") and r2.isError():
                raise UpdateFailed(f"Modbus error block 2: {r2}")

            b1, b2 = r1.registers, r2.registers

            return {
                "voltage_l1":        _to_float(b1, _REG_VOLTAGE_L1,       _BLOCK1_START),
                "voltage_l2":        _to_float(b1, _REG_VOLTAGE_L2,       _BLOCK1_START),
                "voltage_l3":        _to_float(b1, _REG_VOLTAGE_L3,       _BLOCK1_START),
                "current_l1":        _to_float(b1, _REG_CURRENT_L1,       _BLOCK1_START),
                "current_l2":        _to_float(b1, _REG_CURRENT_L2,       _BLOCK1_START),
                "current_l3":        _to_float(b1, _REG_CURRENT_L3,       _BLOCK1_START),
                "power_l1":          _to_float(b1, _REG_POWER_L1,         _BLOCK1_START),
                "power_l2":          _to_float(b1, _REG_POWER_L2,         _BLOCK1_START),
                "power_l3":          _to_float(b1, _REG_POWER_L3,         _BLOCK1_START),
                "neutral_current":   _to_float(b2, _REG_NEUTRAL_CURRENT,  _BLOCK2_START),
                "total_power":       _to_float(b2, _REG_TOTAL_POWER,      _BLOCK2_START),
                "power_factor":      _to_float(b2, _REG_POWER_FACTOR,     _BLOCK2_START),
                "frequency":         _to_float(b2, _REG_FREQUENCY,        _BLOCK2_START),
                "import_energy":     _to_float(b2, _REG_IMPORT_ENERGY,    _BLOCK2_START),
                "export_energy":     _to_float(b2, _REG_EXPORT_ENERGY,    _BLOCK2_START),
            }

        except ModbusException as exc:
            self._client = None  # force reconnect on next poll
            raise UpdateFailed(f"Modbus communication error: {exc}") from exc

    async def async_close(self) -> None:
        """Close the Modbus connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
