"""Sensor platform for the Eastron SDM72D."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactivePower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SDM72DCoordinator


@dataclass(frozen=True, kw_only=True)
class SDM72DSensorDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with the coordinator data key."""
    data_key: str


SENSOR_DESCRIPTIONS: tuple[SDM72DSensorDescription, ...] = (
    # ── Phase voltages (L-N) ──────────────────────────────────────────────────
    SDM72DSensorDescription(
        key="voltage_l1", data_key="voltage_l1",
        name="Voltage (L1)",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
    ),
    SDM72DSensorDescription(
        key="voltage_l2", data_key="voltage_l2",
        name="Voltage (L2)",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
    ),
    SDM72DSensorDescription(
        key="voltage_l3", data_key="voltage_l3",
        name="Voltage (L3)",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
    ),
    # ── Phase currents ────────────────────────────────────────────────────────
    SDM72DSensorDescription(
        key="current_l1", data_key="current_l1",
        name="Current (L1)",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
    ),
    SDM72DSensorDescription(
        key="current_l2", data_key="current_l2",
        name="Current (L2)",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
    ),
    SDM72DSensorDescription(
        key="current_l3", data_key="current_l3",
        name="Current (L3)",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
    ),
    # ── Per-phase active power ────────────────────────────────────────────────
    SDM72DSensorDescription(
        key="power_l1", data_key="power_l1",
        name="Active Power (L1)",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
    ),
    SDM72DSensorDescription(
        key="power_l2", data_key="power_l2",
        name="Active Power (L2)",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
    ),
    SDM72DSensorDescription(
        key="power_l3", data_key="power_l3",
        name="Active Power (L3)",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
    ),
    # ── Total system measurements ─────────────────────────────────────────────
    SDM72DSensorDescription(
        key="total_power", data_key="total_power",
        name="Active Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
    ),
    SDM72DSensorDescription(
        key="total_va", data_key="total_va",
        name="Apparent Power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        suggested_display_precision=1,
    ),
    SDM72DSensorDescription(
        key="total_var", data_key="total_var",
        name="Reactive Power",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
        suggested_display_precision=1,
    ),
    SDM72DSensorDescription(
        key="power_factor", data_key="power_factor",
        name="Power Factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,
        suggested_display_precision=2,
    ),
    SDM72DSensorDescription(
        key="frequency", data_key="frequency",
        name="Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        suggested_display_precision=2,
    ),
    # ── Energy counters ───────────────────────────────────────────────────────
    SDM72DSensorDescription(
        key="import_energy", data_key="import_energy",
        name="Import Energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    ),
    SDM72DSensorDescription(
        key="export_energy", data_key="export_energy",
        name="Export Energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    ),
    # ── Neutral current (0x00E0) ──────────────────────────────────────────────
    # NOTE: 0x0030 = "Sum of line currents" — NOT neutral current.
    #       Neutral current is at 0x00E0 per SDM72D-M-2 datasheet.
    SDM72DSensorDescription(
        key="neutral_current", data_key="neutral_current",
        name="Neutral Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
    ),
    # ── Average line-to-neutral voltage (0x002A) ──────────────────────────────
    SDM72DSensorDescription(
        key="avg_voltage", data_key="avg_voltage",
        name="Average Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
    ),
    # ── Total active energy import+export (0x0156) — for HA Energy Dashboard ──
    SDM72DSensorDescription(
        key="total_energy", data_key="total_energy",
        name="Total Energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    ),
    # ── Resettable import / export counters (0x0184, 0x0186) ─────────────────
    SDM72DSensorDescription(
        key="resettable_import", data_key="resettable_import",
        name="Resettable Import Energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    ),
    SDM72DSensorDescription(
        key="resettable_export", data_key="resettable_export",
        name="Resettable Export Energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    ),
    # ── Net energy balance (0x018C) ───────────────────────────────────────────
    # Can go negative (export > import), so TOTAL not TOTAL_INCREASING.
    SDM72DSensorDescription(
        key="net_energy", data_key="net_energy",
        name="Net Energy",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SDM72DCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SDM72DSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class SDM72DSensor(CoordinatorEntity[SDM72DCoordinator], SensorEntity):
    """A single SDM72D measurement sensor."""

    _attr_has_entity_name = True
    entity_description: SDM72DSensorDescription

    def __init__(
        self,
        coordinator: SDM72DCoordinator,
        entry: ConfigEntry,
        description: SDM72DSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="SDM72D",
            manufacturer="Eastron",
            model="SDM72D-M-2",
        )

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.get(self.entity_description.data_key)
        if value is None:
            return None
        # Power factor: SDM72D uses sign to indicate current direction (negative = reverse).
        # Clamp to [-1, 1] to guard against float artefacts at the limits.
        if self.entity_description.key == "power_factor":
            return max(-1.0, min(1.0, value))
        return value
