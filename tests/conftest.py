"""Load individual integration modules without importing Home Assistant.

``custom_components.eastron_sdm72d.__init__`` imports Home Assistant, which is
not a test dependency here. The helper below binds selected modules into a
synthetic package so their relative imports resolve, letting the Home
Assistant-free parts of the integration be tested on their own.

``model`` and ``meter`` are exactly that: they describe the meter's registers
and talk to it through ``modbus-connection``, and know nothing about Home
Assistant. They used to be a separate distribution, tested in its own
repository; the fixtures at the bottom of this file are that suite's, moved
across with the code they cover.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import struct
import sys
import types

from modbus_connection.mock import MockModbusUnit
from modbus_connection.pytest_plugin import (
    mock_modbus_connection as mock_modbus_connection,
)
from modbus_connection.pytest_plugin import (
    mock_modbus_unit as mock_modbus_unit,
)
import pytest

INTEGRATION_DIR = (
    Path(__file__).resolve().parent.parent / "custom_components" / "eastron_sdm72d"
)
_PACKAGE = "sdm72d_under_test"


def load_module(name: str) -> types.ModuleType:
    """Import one integration module by name, with its siblings available."""
    if _PACKAGE not in sys.modules:
        package = types.ModuleType(_PACKAGE)
        package.__path__ = [str(INTEGRATION_DIR)]
        sys.modules[_PACKAGE] = package

    qualified = f"{_PACKAGE}.{name}"
    if qualified in sys.modules:
        return sys.modules[qualified]

    spec = importlib.util.spec_from_file_location(
        qualified, INTEGRATION_DIR / f"{name}.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    spec.loader.exec_module(module)
    return module


_meter = load_module("meter")
SDM72DMeter = _meter.SDM72DMeter
DEFAULT_PASSWORD = _meter.DEFAULT_PASSWORD
SDM72D = load_module("model").SDM72D


# -- The meter under test, on modbus-connection's in-memory mock backend ------
#
# The mock backend and its fixtures ship with ``modbus-connection`` and are
# imported explicitly so the suite does not rely on pytest entry-point
# autoloading. No socket, no serial port, no meter — just an address-keyed
# register store.


def f32(value: float) -> list[int]:
    """Encode a float the way the meter lays it out: two big-endian words."""
    return list(struct.unpack(">HH", struct.pack(">f", value)))


def words(mapping: dict[int, float]) -> dict[int, int]:
    """Expand ``{address: float}`` into the register words the meter would hold."""
    out: dict[int, int] = {}
    for address, value in mapping.items():
        hi, lo = f32(value)
        out[address] = hi
        out[address + 1] = lo
    return out


# A synthetic snapshot: a light, deliberately unbalanced load on a meter that
# has been running for a while. The numbers are made up — the suite only cares
# that what goes into the registers comes back out of the fields.
MEASUREMENTS: dict[int, float] = {
    0x0000: 230.1,  # voltage_l1
    0x0002: 229.4,  # voltage_l2
    0x0004: 231.2,  # voltage_l3
    0x0006: 1.5,  # current_l1
    0x0008: 0.0,  # current_l2 — an idle phase
    0x000A: 0.25,  # current_l3
    0x000C: 300.0,  # power_l1
    0x000E: 0.0,  # power_l2
    0x0010: 50.0,  # power_l3
    0x002A: 230.2,  # avg_voltage
    0x0030: 1.75,  # sum of line currents — a trap, see test_neutral_current
    0x0034: 350.0,  # total_power
    0x0038: 400.0,  # total_va
    0x003C: -190.0,  # total_var — a capacitive load
    0x003E: 0.875,  # power_factor
    0x0046: 50.02,  # frequency
    0x0048: 12345.678,  # import_energy
    0x004A: 0.0,  # export_energy — a meter that never exports
    0x00E0: 1.25,  # neutral_current, distinct from the line-current sum
    0x0156: 12345.678,  # total_energy
    0x0184: 250.5,  # resettable_import
    0x0186: 0.0,  # resettable_export
    0x018C: 12345.678,  # net_energy
}


@pytest.fixture
def loaded_unit(mock_modbus_unit: MockModbusUnit) -> MockModbusUnit:
    """A unit whose input registers hold the snapshot above."""
    mock_modbus_unit.load_raw({"input": words(MEASUREMENTS)})
    return mock_modbus_unit


@pytest.fixture
def meter(loaded_unit: MockModbusUnit) -> SDM72DMeter:
    """An SDM72D meter on the loaded unit."""
    return SDM72DMeter(loaded_unit)
