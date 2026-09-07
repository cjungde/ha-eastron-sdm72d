"""Register model for the Eastron SDM72D-M-2.

Every published measurement is a 32-bit IEEE 754 float held in two consecutive
input registers (function code 04), addressed as documented in the SDM72D-M-2
Modbus protocol sheet. Addresses below are the protocol addresses, i.e. what
goes on the wire, not the 3xxxx display convention.
"""

from __future__ import annotations

from modbus_connection.model import Component, float32


class SDM72D(Component):
    """The measurement block of an SDM72D-M-2."""

    # All measurements live in the input-register space (FC04).
    register_space = "input"

    # The meter answers a maximum of 30 parameters (60 registers) per request.
    max_span = 60

    # The address map is sparse. Declaring the readable ranges keeps the planner
    # from bridging a gap into addresses the meter does not answer, which it
    # rejects with an illegal-data-address exception rather than padding.
    register_ranges = (
        (0x0000, 0x0011),  # per-phase voltage, current, active power
        (0x002A, 0x002B),  # average line-to-neutral voltage
        (0x0034, 0x004B),  # totals, power factor, frequency, import/export
        (0x00E0, 0x00E1),  # neutral current
        (0x0156, 0x0157),  # total active energy (import + export)
        (0x0184, 0x018D),  # resettable import / export / net
    )

    # -- per phase -----------------------------------------------------------
    voltage_l1 = float32(0x0000, unit="V")
    voltage_l2 = float32(0x0002, unit="V")
    voltage_l3 = float32(0x0004, unit="V")

    current_l1 = float32(0x0006, unit="A")
    current_l2 = float32(0x0008, unit="A")
    current_l3 = float32(0x000A, unit="A")

    power_l1 = float32(0x000C, unit="W")
    power_l2 = float32(0x000E, unit="W")
    power_l3 = float32(0x0010, unit="W")

    # -- system totals -------------------------------------------------------
    avg_voltage = float32(0x002A, unit="V")
    total_power = float32(0x0034, unit="W")
    total_va = float32(0x0038, unit="VA")
    total_var = float32(0x003C, unit="var")
    power_factor = float32(0x003E)
    frequency = float32(0x0046, unit="Hz")

    # Neutral current. NOT 0x0030 — that address holds the sum of line currents,
    # which differs from the neutral current on an unbalanced three-phase load.
    neutral_current = float32(0x00E0, unit="A")

    # -- energy counters -----------------------------------------------------
    import_energy = float32(0x0048, unit="kWh")
    export_energy = float32(0x004A, unit="kWh")
    total_energy = float32(0x0156, unit="kWh")

    # Cleared by SDM72DMeter.async_reset_energy(); the three above are not.
    resettable_import = float32(0x0184, unit="kWh")
    resettable_export = float32(0x0186, unit="kWh")
    net_energy = float32(0x018C, unit="kWh")
