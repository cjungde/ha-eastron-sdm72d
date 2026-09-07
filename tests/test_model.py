"""Decoding and read planning for the SDM72D measurement block."""

from __future__ import annotations

from modbus_connection.mock import MockModbusUnit
import pytest

from .conftest import MEASUREMENTS, SDM72D, SDM72DMeter


async def test_every_field_decodes(meter: SDM72DMeter) -> None:
    """All 22 published measurements come back as the floats that were stored."""
    await meter.async_update()
    m = meter.measurements

    assert m.voltage_l1 == pytest.approx(230.1)
    assert m.voltage_l2 == pytest.approx(229.4)
    assert m.voltage_l3 == pytest.approx(231.2)
    assert m.current_l1 == pytest.approx(1.5)
    assert m.current_l2 == pytest.approx(0.0)
    assert m.current_l3 == pytest.approx(0.25)
    assert m.power_l1 == pytest.approx(300.0)
    assert m.power_l2 == pytest.approx(0.0)
    assert m.power_l3 == pytest.approx(50.0)
    assert m.avg_voltage == pytest.approx(230.2)
    assert m.total_power == pytest.approx(350.0)
    assert m.total_va == pytest.approx(400.0)
    assert m.total_var == pytest.approx(-190.0)
    assert m.power_factor == pytest.approx(0.875)
    assert m.frequency == pytest.approx(50.02)
    assert m.import_energy == pytest.approx(12345.678)
    assert m.export_energy == pytest.approx(0.0)
    assert m.neutral_current == pytest.approx(1.25)
    assert m.total_energy == pytest.approx(12345.678)
    assert m.resettable_import == pytest.approx(250.5)
    assert m.resettable_export == pytest.approx(0.0)
    assert m.net_energy == pytest.approx(12345.678)


async def test_declared_field_count() -> None:
    """The model publishes exactly the 22 measurements the integration exposes."""
    assert len(SDM72D.declared_fields) == 22


async def test_neutral_current_is_not_the_line_current_sum(
    meter: SDM72DMeter,
) -> None:
    """0x00E0 is the neutral current; 0x0030 is the sum of line currents.

    The two differ on an unbalanced load, and the datasheet address is easy to
    confuse. The snapshot holds a distinct value at 0x0030 so that reading the
    wrong register fails loudly here instead of quietly shipping a wrong sensor.
    """
    await meter.async_update()

    assert MEASUREMENTS[0x0030] != MEASUREMENTS[0x00E0]
    assert meter.measurements.neutral_current == pytest.approx(MEASUREMENTS[0x00E0])


async def test_reads_stay_inside_the_declared_ranges(
    meter: SDM72DMeter, loaded_unit: MockModbusUnit
) -> None:
    """The planner never asks for an address the meter does not answer."""
    await meter.async_update()

    readable = SDM72D.register_ranges
    for event in loaded_unit.read_events:
        first = event.address
        last = event.address + event.count - 1
        assert any(low <= first and last <= high for low, high in readable), (
            f"read {first:#06x}-{last:#06x} falls outside the declared ranges"
        )


async def test_reads_respect_the_request_limit(
    meter: SDM72DMeter, loaded_unit: MockModbusUnit
) -> None:
    """No block exceeds the meter's 30-parameter (60-register) request limit."""
    await meter.async_update()

    assert loaded_unit.read_events
    assert all(event.count <= 60 for event in loaded_unit.read_events)


async def test_the_planned_blocks_match_the_hand_tuned_reads(
    meter: SDM72DMeter, loaded_unit: MockModbusUnit
) -> None:
    """The planner reproduces the six blocks the register map was read with before.

    Pinned so a later change to the ranges or to the planning limits shows up as
    a diff in the read plan rather than as extra traffic on a shared bus.
    """
    await meter.async_update()

    assert [(e.address, e.count) for e in loaded_unit.read_events] == [
        (0x0000, 18),  # per-phase V, I, P
        (0x002A, 2),  # average voltage
        (0x0034, 24),  # totals, PF, frequency, import/export
        (0x00E0, 2),  # neutral current
        (0x0156, 2),  # total active energy
        (0x0184, 10),  # resettable import/export, net
    ]
