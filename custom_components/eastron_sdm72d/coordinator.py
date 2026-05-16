"""DataUpdateCoordinator for the Eastron SDM72D."""
from __future__ import annotations

import asyncio
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
# Block 2: 0x0034–0x004B — total power, VA, VAr, PF, frequency, import/export energy
# Block 3: 0x00E0–0x00E1 — neutral current
#
# NOTE: 0x0030 is "Sum of line currents" (NOT neutral current).
#       Neutral current is at 0x00E0 per the SDM72D-M-2 datasheet.

_BLOCK1_START = 0x0000   # 9 parameters (18 registers): per-phase V, I, P
_BLOCK1_COUNT = 18

_BLOCK2_START = 0x0034   # 12 parameters (24 registers): total P/VA/VAr, PF, freq, energy
_BLOCK2_COUNT = 24

_BLOCK3_START = 0x00E0   # 1 parameter (2 registers): neutral current
_BLOCK3_COUNT = 2

_BLOCK4_START = 0x002A   # 1 parameter (2 registers): average line-to-neutral voltage
_BLOCK4_COUNT = 2

# Block 5 covers: total active energy (0x0156), resettable import (0x0184),
# resettable export (0x0186), and net kWh (0x018C).
# Reading as two sub-blocks is more efficient than one large sparse read.
_BLOCK5_START = 0x0156   # 1 parameter (2 registers): total active energy (import+export)
_BLOCK5_COUNT = 2

_BLOCK6_START = 0x0184   # 3 parameters (10 registers): resettable import, export, net kWh
_BLOCK6_COUNT = 10       # 0x0184–0x018D  (offsets: import=0, export=2, net=8)

# (block_start, absolute_register_address) for each data key
_R: dict[str, tuple[int, int]] = {
    "voltage_l1":           (_BLOCK1_START, 0x0000),
    "voltage_l2":           (_BLOCK1_START, 0x0002),
    "voltage_l3":           (_BLOCK1_START, 0x0004),
    "current_l1":           (_BLOCK1_START, 0x0006),
    "current_l2":           (_BLOCK1_START, 0x0008),
    "current_l3":           (_BLOCK1_START, 0x000A),
    "power_l1":             (_BLOCK1_START, 0x000C),
    "power_l2":             (_BLOCK1_START, 0x000E),
    "power_l3":             (_BLOCK1_START, 0x0010),
    "avg_voltage":          (_BLOCK4_START, 0x002A),
    "total_power":          (_BLOCK2_START, 0x0034),
    "total_va":             (_BLOCK2_START, 0x0038),
    "total_var":            (_BLOCK2_START, 0x003C),
    "power_factor":         (_BLOCK2_START, 0x003E),
    "frequency":            (_BLOCK2_START, 0x0046),
    "import_energy":        (_BLOCK2_START, 0x0048),
    "export_energy":        (_BLOCK2_START, 0x004A),
    "neutral_current":      (_BLOCK3_START, 0x00E0),
    "total_energy":         (_BLOCK5_START, 0x0156),
    "resettable_import":    (_BLOCK6_START, 0x0184),
    "resettable_export":    (_BLOCK6_START, 0x0186),
    "net_energy":           (_BLOCK6_START, 0x018C),
}

# Seconds before a connect or read attempt is abandoned
_MODBUS_TIMEOUT = 10


def _f32(registers: list[int], block_start: int, address: int) -> float:
    """Decode a 32-bit IEEE 754 float from two consecutive input registers.

    Raises UpdateFailed if the register block is shorter than expected so the
    caller gets a clean error instead of an IndexError.
    """
    offset = address - block_start
    if offset < 0 or offset + 1 >= len(registers):
        raise UpdateFailed(
            f"Register block starting at 0x{block_start:04X} is too short "
            f"(need offset {offset + 1}, got {len(registers)} registers)"
        )
    raw = struct.pack(">HH", registers[offset], registers[offset + 1])
    return round(struct.unpack(">f", raw)[0], 4)


def _build_client(data: dict) -> Any:
    """Instantiate the appropriate pymodbus async client from config entry data."""
    from pymodbus.client import AsyncModbusTcpClient, AsyncModbusSerialClient

    if data.get(CONF_CONNECTION_TYPE, CONNECTION_TCP) == CONNECTION_TCP:
        return AsyncModbusTcpClient(
            host=data["host"],
            port=data.get("port", 502),
            timeout=_MODBUS_TIMEOUT,
        )

    # RTU — explicitly request the RTU framer; pymodbus 3.x defaults to RTU for
    # serial clients but being explicit avoids any version-specific surprises.
    try:
        from pymodbus.framer import FramerType
        framer = FramerType.RTU
    except ImportError:
        framer = "rtu"  # pymodbus < 3.4 string fallback

    return AsyncModbusSerialClient(
        port=data[CONF_SERIAL_PORT],
        framer=framer,
        baudrate=data.get(CONF_BAUDRATE, 9600),
        parity=data.get(CONF_PARITY, "N"),
        stopbits=data.get(CONF_STOPBITS, 1),
        bytesize=8,
        timeout=_MODBUS_TIMEOUT,
    )


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
        """Return a connected Modbus client, closing any stale connection first."""
        if self._client is not None:
            if self._client.connected:
                return self._client
            # Stale client — close it cleanly before creating a new one so that
            # serial ports and TCP sockets are released immediately.
            self._client.close()
            self._client = None

        client = _build_client(self._entry.data)
        try:
            await asyncio.wait_for(client.connect(), timeout=_MODBUS_TIMEOUT)
        except asyncio.TimeoutError as exc:
            client.close()
            raise UpdateFailed("Connection to SDM72D timed out") from exc

        if not client.connected:
            client.close()
            raise UpdateFailed("Could not connect to SDM72D")

        self._client = client
        return self._client

    async def _async_update_data(self) -> dict[str, float]:
        from pymodbus.exceptions import ModbusException

        slave = self._entry.data[CONF_SLAVE_ID]
        try:
            client = await self._get_client()

            # Targeted reads — all within the 30-parameter-per-request limit.
            # asyncio.wait_for enforces a hard deadline per read in case the device
            # stalls mid-response (e.g. RS485 bus contention).
            async def read(address: int, count: int) -> list[int]:
                result = await asyncio.wait_for(
                    client.read_input_registers(address=address, count=count, slave=slave),
                    timeout=_MODBUS_TIMEOUT,
                )
                if hasattr(result, "isError") and result.isError():
                    raise UpdateFailed(f"Modbus error at 0x{address:04X}: {result}")
                return result.registers

            b1 = await read(_BLOCK1_START, _BLOCK1_COUNT)
            b2 = await read(_BLOCK2_START, _BLOCK2_COUNT)
            b3 = await read(_BLOCK3_START, _BLOCK3_COUNT)
            b4 = await read(_BLOCK4_START, _BLOCK4_COUNT)
            b5 = await read(_BLOCK5_START, _BLOCK5_COUNT)
            b6 = await read(_BLOCK6_START, _BLOCK6_COUNT)

            block_map = {
                _BLOCK1_START: b1,
                _BLOCK2_START: b2,
                _BLOCK3_START: b3,
                _BLOCK4_START: b4,
                _BLOCK5_START: b5,
                _BLOCK6_START: b6,
            }

            return {
                key: _f32(block_map[block_start], block_start, address)
                for key, (block_start, address) in _R.items()
            }

        except asyncio.TimeoutError as exc:
            self._client = None
            raise UpdateFailed("Modbus read timed out") from exc
        except ModbusException as exc:
            self._client = None
            raise UpdateFailed(f"Modbus communication error: {exc}") from exc
        except UpdateFailed:
            raise
        except Exception as exc:
            self._client = None
            raise UpdateFailed(f"Unexpected error polling SDM72D: {exc}") from exc

    async def async_close(self) -> None:
        """Close the Modbus connection on integration unload."""
        if self._client is not None:
            self._client.close()
            self._client = None
