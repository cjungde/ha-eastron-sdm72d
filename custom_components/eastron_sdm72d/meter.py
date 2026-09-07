"""The top-level SDM meter object."""

from __future__ import annotations

import contextlib
import struct
from typing import TYPE_CHECKING

from modbus_connection.exceptions import ModbusProtocolError, ModbusTimeoutError

from .model import SDM72D

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

# Holding register 0x000E, KPPA (Key Parameter Programming Authorization).
# Writing the meter password unlocks key-parameter writes for the session.
_REG_KPPA = 0x000E
DEFAULT_PASSWORD = 1000.0  # factory default, stored as an IEEE 754 float

# Holding register 0xF010: writing 0x0003 clears the resettable energy counters.
_REG_RESET = 0xF010
_VAL_RESET = 0x0003


class SDM72DMeter:
    """An Eastron SDM72D-M-2 on a Modbus unit."""

    def __init__(self, unit: ModbusUnit, *, password: float = DEFAULT_PASSWORD) -> None:
        self._unit = unit
        self._password = password
        self.measurements = SDM72D(unit)

    async def async_update(self) -> None:
        """Refresh every measurement.

        The planner turns the declared ranges into as few FC04 reads as the
        meter's 30-parameter request limit allows.
        """
        await self.measurements.async_update()

    async def async_reset_energy(self) -> None:
        """Clear the resettable import, export and net energy counters.

        Two steps, both FC16: unlock key-parameter programming with the meter
        password, then send the reset command.

        0xF010 is write-only. The meter performs the reset and answers nothing,
        so the absent reply is the expected outcome, not a failure — a raised
        timeout or framing error is swallowed here. A refused unlock is not: it
        is reported, because the reset would silently do nothing.
        """
        words = list(struct.unpack(">HH", struct.pack(">f", self._password)))
        await self._unit.write_registers(_REG_KPPA, words)

        # Write-only register: the meter resets and answers nothing, so the
        # absent reply is the expected outcome rather than a failure.
        with contextlib.suppress(ModbusTimeoutError, ModbusProtocolError):
            await self._unit.write_registers(_REG_RESET, [_VAL_RESET])
