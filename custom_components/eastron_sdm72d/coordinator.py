"""DataUpdateCoordinator for the Eastron SDM72D."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components.modbus import async_get_unit
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection.exceptions import ModbusError

from .connection import params_from_entry_data
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .meter import SDM72DMeter

_LOGGER = logging.getLogger(__name__)

# The meter reports full float precision; the sensors have always published
# four decimals. Kept here rather than in the device library, where rounding a
# measurement to taste would be the wrong layer, and kept at four so the states
# recorded before this rewrite and after it are the same strings.
_PRECISION = 4

# The measurements published as sensors, in the order the register map lists
# them. Every name is an attribute of the library's measurement component; the
# strings double as the coordinator data keys the sensor descriptions look up,
# so they must not be renamed — the entity unique_ids are built from them.
DATA_KEYS: tuple[str, ...] = (
    "voltage_l1",
    "voltage_l2",
    "voltage_l3",
    "current_l1",
    "current_l2",
    "current_l3",
    "power_l1",
    "power_l2",
    "power_l3",
    "avg_voltage",
    "total_power",
    "total_va",
    "total_var",
    "power_factor",
    "frequency",
    "import_energy",
    "export_energy",
    "neutral_current",
    "total_energy",
    "resettable_import",
    "resettable_export",
    "net_energy",
)


class SDM72DCoordinator(DataUpdateCoordinator[dict[str, float]]):
    """Polls the SDM72D at a fixed interval and distributes data to sensors."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Take a unit on a shared connection and wrap it in a meter.

        Asking for the unit performs no I/O, so a meter that is powered down or
        behind a dead gateway does not stop the entry setting up. The first read
        opens the link and a dropped link reopens on the next request, which is
        why nothing here reconnects or reloads the entry by hand.
        """
        self._entry = entry
        unit = async_get_unit(
            hass,
            entry,
            params_from_entry_data(dict(entry.data)),
            int(entry.data[CONF_SLAVE_ID]),
        )
        self.meter = SDM72DMeter(unit)

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

    async def _async_update_data(self) -> dict[str, float]:
        """Read every measurement in as few requests as the meter allows."""
        try:
            await self.meter.async_update()
        except ModbusError as exc:
            raise UpdateFailed(f"Modbus communication error: {exc}") from exc

        measurements = self.meter.measurements
        return {key: round(getattr(measurements, key), _PRECISION) for key in DATA_KEYS}
