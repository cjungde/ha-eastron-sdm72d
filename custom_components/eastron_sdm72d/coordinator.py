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

# SDM72D-M-2 input register map — all values are 32-bit IEEE 754 floats (2 registers each).
# Function code 04. Max 30 parameters (60 registers) per request.
#
# Block 1: 0x0000–0x0011 — per-phase voltage, current, active power
# Block 2: 0x0034–0x004B — total power, power factor, frequency, import/export energy
# Block 3: 0x00E0–0x00E1 — neutral current
#
# NOTE: 0x0030 is "Sum of line currents" (NOT neutral current).
#       Neutral current is at 0x00E0 per the SDM72D-M-2 datasheet.

_BLOCK1_START = 0x0000   # 9 parameters (18 registers)
_BLOCK1_COUNT = 18

_BLOCK2_START = 0x0034   # 12 parameters (24 registers): total P, VA, VAr, PF, freq, energy
_BLOCK2_COUNT = 24

_BLOCK3_START = 0x00E0   # 1 parameter (2 registers): neutral current
_BLOCK3_COUNT = 2

# Register offsets within each block (absolute address - block_start)
_R = {
    "voltage_l1":       (_BLOCK1_START, 0x0000),
    "voltage_l2":       (_BLOCK1_START, 0x0002),
    "voltage_l3":       (_BLOCK1_START, 0x0004),
    "current_l1":       (_BLOCK1_START, 0x0006),
    "current_l2":       (_BLOCK1_START, 0x0008),
    "current_l3":       (_BLOCK1_START, 0x000A),
    "power_l1":         (_BLOCK1_START, 0x000C),
    "power_l2":         (_BLOCK1_START, 0x000E),
    "power_l3":         (_BLOCK1_START, 0x0010),
    "total_power":      (_BLOCK2_START, 0x0034),
    "total_va":         (_BLOCK2_START, 0x0038),
    "total_var":        (_BLOCK2_START, 0x003C),
    "power_factor":     (_BLOCK2_START, 0x003E),
    "frequency":        (_BLOCK2_START, 0x0046),
    "import_energy":    (_BLOCK2_START, 0x0048),
    "export_energy":    (_BLOCK2_START, 0x004A),
    "neutral_current":  (_BLOCK3_START, 0x00E0),
}


def _f32(registers: list[int], block_start: int, address: int) -> float:
    """Decode a 32-bit IEEE 754 float from two consecutive input registers."""
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
        """Return a connected Modbus client, reconnecting if necessary."""
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

            # Three targeted reads — all within the 30-parameter-per-request limit
            r1 = await client.read_input_registers(address=_BLOCK1_START, count=_BLOCK1_COUNT, slave=slave)
            r2 = await client.read_input_registers(address=_BLOCK2_START, count=_BLOCK2_COUNT, slave=slave)
            r3 = await client.read_input_registers(address=_BLOCK3_START, count=_BLOCK3_COUNT, slave=slave)

            for label, r in (("block1", r1), ("block2", r2), ("block3", r3)):
                if hasattr(r, "isError") and r.isError():
                    raise UpdateFailed(f"Modbus error {label}: {r}")

            b1, b2, b3 = r1.registers, r2.registers, r3.registers

            def f(key: str) -> float:
                block_start, address = _R[key]
                regs = {_BLOCK1_START: b1, _BLOCK2_START: b2, _BLOCK3_START: b3}[block_start]
                return _f32(regs, block_start, address)

            return {key: f(key) for key in _R}

        except ModbusException as exc:
            self._client = None  # force reconnect on next poll
            raise UpdateFailed(f"Modbus communication error: {exc}") from exc

    async def async_close(self) -> None:
        """Close the Modbus connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
