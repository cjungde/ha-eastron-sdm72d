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
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
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


# Entity names are designed so that slugify("E72d " + name) reproduces
# the original entity_ids from the Modbus YAML configuration:
#   e72d_derzeitige_wirkleistung, e72d_wirkleistung_import_tageszahler, etc.
SENSOR_DESCRIPTIONS: tuple[SDM72DSensorDescription, ...] = (
    SDM72DSensorDescription(
        key="voltage_l1",
        data_key="voltage_l1",
        name="Spannung (L1)",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
    ),
    SDM72DSensorDescription(
        key="voltage_l2",
        data_key="voltage_l2",
        name="Spannung (L2)",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
    ),
    SDM72DSensorDescription(
        key="voltage_l3",
        data_key="voltage_l3",
        name="Spannung (L3)",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
    ),
    SDM72DSensorDescription(
        key="current_l1",
        data_key="current_l1",
        name="Stromstärke (L1)",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
    ),
    SDM72DSensorDescription(
        key="current_l2",
        data_key="current_l2",
        name="Stromstärke (L2)",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
    ),
    SDM72DSensorDescription(
        key="current_l3",
        data_key="current_l3",
        name="Stromstärke (L3)",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
    ),
    # --- Existing entities (entity_id preserved via name slug) ---
    # slugify("E72d Derzeitige Wirkleistung (L1)") = e72d_derzeitige_wirkleistung_l1
    SDM72DSensorDescription(
        key="power_l1",
        data_key="power_l1",
        name="Derzeitige Wirkleistung (L1)",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
    ),
    SDM72DSensorDescription(
        key="power_l2",
        data_key="power_l2",
        name="Derzeitige Wirkleistung (L2)",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
    ),
    SDM72DSensorDescription(
        key="power_l3",
        data_key="power_l3",
        name="Derzeitige Wirkleistung (L3)",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
    ),
    # slugify("E72d Stromstärke Neutralleiter") = e72d_stromstarke_neutralleiter
    SDM72DSensorDescription(
        key="neutral_current",
        data_key="neutral_current",
        name="Stromstärke Neutralleiter",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        suggested_display_precision=2,
    ),
    # slugify("E72d Derzeitige Wirkleistung") = e72d_derzeitige_wirkleistung
    SDM72DSensorDescription(
        key="total_power",
        data_key="total_power",
        name="Derzeitige Wirkleistung",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
    ),
    # slugify("E72d Leistungsfaktor") = e72d_leistungsfaktor
    SDM72DSensorDescription(
        key="power_factor",
        data_key="power_factor",
        name="Leistungsfaktor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=None,
        suggested_display_precision=2,
    ),
    SDM72DSensorDescription(
        key="frequency",
        data_key="frequency",
        name="Frequenz",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        suggested_display_precision=2,
    ),
    # slugify("E72d Wirkleistung Import (Tageszähler)") = e72d_wirkleistung_import_tageszahler
    SDM72DSensorDescription(
        key="import_energy",
        data_key="import_energy",
        name="Wirkleistung Import (Tageszähler)",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    ),
    # slugify("E72d Wirkleistung Export (Tageszähler)") = e72d_wirkleistung_export_tageszahler
    SDM72DSensorDescription(
        key="export_energy",
        data_key="export_energy",
        name="Wirkleistung Export (Tageszähler)",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
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
            name="E72d",
            manufacturer="Eastron",
            model="SDM72D",
        )

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.data_key)
