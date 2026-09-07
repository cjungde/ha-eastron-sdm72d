"""The two-step reset of the resettable energy counters."""

from __future__ import annotations

import struct

from modbus_connection.exceptions import ModbusTimeoutError
from modbus_connection.mock import MockModbusUnit, WriteEvent

from .conftest import DEFAULT_PASSWORD, SDM72DMeter

_REG_KPPA = 0x000E
_REG_RESET = 0xF010


async def test_reset_unlocks_then_commands(
    meter: SDM72DMeter, loaded_unit: MockModbusUnit
) -> None:
    """Password to KPPA first, reset command second, both as holding writes."""
    seen: list[WriteEvent] = []
    loaded_unit.on_write(seen.append)

    await meter.async_reset_energy()

    assert [(e.register_type, e.address) for e in seen] == [
        ("holding", _REG_KPPA),
        ("holding", _REG_RESET),
    ]

    unlock = struct.unpack(">f", struct.pack(">HH", *seen[0].values))[0]
    assert unlock == DEFAULT_PASSWORD
    assert seen[1].values == [0x0003]


async def test_missing_reply_to_the_reset_is_not_an_error(
    meter: SDM72DMeter, loaded_unit: MockModbusUnit
) -> None:
    """0xF010 is write-only: the meter resets and answers nothing.

    A timeout on that write is the documented behaviour, so it must not
    propagate — the counters were cleared.
    """
    loaded_unit.fail_write(_REG_RESET, ModbusTimeoutError("no response"))

    await meter.async_reset_energy()  # must not raise


async def test_a_refused_unlock_is_reported(
    meter: SDM72DMeter, loaded_unit: MockModbusUnit
) -> None:
    """A failed KPPA write is a real failure: the reset would do nothing."""
    loaded_unit.fail_write(_REG_KPPA, ModbusTimeoutError("no response"))

    try:
        await meter.async_reset_energy()
    except ModbusTimeoutError:
        return
    raise AssertionError("a refused unlock must not be swallowed")


async def test_a_custom_password_is_used(loaded_unit: MockModbusUnit) -> None:
    """A meter whose password was changed from the factory default."""
    seen: list[WriteEvent] = []
    loaded_unit.on_write(seen.append)

    await SDM72DMeter(loaded_unit, password=4242.0).async_reset_energy()

    unlock = struct.unpack(">f", struct.pack(">HH", *seen[0].values))[0]
    assert unlock == 4242.0
