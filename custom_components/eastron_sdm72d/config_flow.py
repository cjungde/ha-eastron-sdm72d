"""Config flow for the Eastron SDM72D integration."""

from __future__ import annotations

import asyncio
import logging

from homeassistant import config_entries
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
from modbus_connection.exceptions import IllegalDataAddressError, ModbusError
import voluptuous as vol

from .connection import params_from_entry_data
from .const import (
    CONF_BAUDRATE,
    CONF_CONNECTION_TYPE,
    CONF_PARITY,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL_PORT,
    CONF_SLAVE_ID,
    CONF_STOPBITS,
    CONNECTION_RTU,
    CONNECTION_TCP,
    CONNECTION_TCP_RTU,
    DEFAULT_BAUDRATE,
    DEFAULT_PARITY,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DEFAULT_STOPBITS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

_SLAVE_ID_SELECTOR = NumberSelector(
    NumberSelectorConfig(min=1, max=247, step=1, mode=NumberSelectorMode.BOX)
)

_SCHEMA_CONNECTION_TYPE = vol.Schema(
    {
        vol.Required(CONF_CONNECTION_TYPE, default=CONNECTION_TCP): vol.In(
            [CONNECTION_TCP, CONNECTION_TCP_RTU, CONNECTION_RTU]
        )
    }
)


def _schema_tcp(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("host", default=defaults.get("host", "")): str,
            vol.Required("port", default=defaults.get("port", DEFAULT_PORT)): vol.All(
                int, vol.Range(min=1, max=65535)
            ),
            vol.Required(
                CONF_SLAVE_ID, default=defaults.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)
            ): _SLAVE_ID_SELECTOR,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(int, vol.Range(min=5, max=3600)),
        }
    )


def _schema_rtu(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_SERIAL_PORT, default=defaults.get(CONF_SERIAL_PORT, "/dev/ttyUSB0")
            ): str,
            vol.Required(
                CONF_BAUDRATE, default=defaults.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)
            ): vol.In([1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]),
            vol.Required(
                CONF_PARITY, default=defaults.get(CONF_PARITY, DEFAULT_PARITY)
            ): vol.In(["N", "E", "O"]),
            vol.Required(
                CONF_STOPBITS, default=defaults.get(CONF_STOPBITS, DEFAULT_STOPBITS)
            ): vol.In([1, 2]),
            vol.Required(
                CONF_SLAVE_ID, default=defaults.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)
            ): _SLAVE_ID_SELECTOR,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(int, vol.Range(min=5, max=3600)),
        }
    )


_TEST_TIMEOUT = 10  # seconds


async def _test_connection(hass: HomeAssistant, data: dict) -> str | None:
    """Read one register from the meter. Returns an error key, or None on success.

    Holds a unit only for the duration of the check. The flow has no config
    entry yet to tie a lasting hold to, so it borrows one: an existing shared
    connection to the same device is reused and stays up, and a connection
    opened for this check alone is closed again on the way out. Either way the
    probe serializes with whatever else is already talking on that bus.
    """
    params = params_from_entry_data(data)
    unit_id = int(data[CONF_SLAVE_ID])

    try:
        async with (
            asyncio.timeout(_TEST_TIMEOUT),
            async_get_temporary_unit(hass, params, unit_id) as unit,
        ):
            await unit.read_input_registers(0x0034, 2)
    except IllegalDataAddressError:
        # Something answered on the link, just not at this unit id.
        return "invalid_slave_id"
    except (ModbusError, TimeoutError):
        return "cannot_connect"
    except HomeAssistantError:
        # The device is already held over different link settings; one
        # connection cannot honour two baud rates at once.
        return "cannot_connect"
    except Exception:
        _LOGGER.exception("Unexpected error testing the SDM72D connection")
        return "unknown"

    return None


class SDM72DConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the UI config flow for Eastron SDM72D."""

    VERSION = 1
    _connection_type: str = CONNECTION_TCP
    _reconfigure_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._connection_type = user_input[CONF_CONNECTION_TYPE]
            if self._connection_type in (CONNECTION_TCP, CONNECTION_TCP_RTU):
                return await self.async_step_tcp()
            return await self.async_step_rtu()

        return self.async_show_form(step_id="user", data_schema=_SCHEMA_CONNECTION_TYPE)

    async def async_step_tcp(self, user_input=None) -> FlowResult:
        errors: dict[str, str] = {}
        defaults = self._reconfigure_entry.data if self._reconfigure_entry else {}
        if user_input is not None:
            data = {CONF_CONNECTION_TYPE: self._connection_type, **user_input}
            error = await _test_connection(self.hass, data)
            if error is None:
                if self._reconfigure_entry:
                    return self.async_update_reload_and_abort(
                        self._reconfigure_entry,
                        title=f"SDM72D {data['host']}",
                        data=data,
                    )
                await self.async_set_unique_id(
                    f"{data['host']}:{data['port']}:{data[CONF_SLAVE_ID]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"SDM72D {data['host']}", data=data
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="tcp",
            data_schema=_schema_tcp(user_input or defaults),
            errors=errors,
        )

    async def async_step_rtu(self, user_input=None) -> FlowResult:
        errors: dict[str, str] = {}
        defaults = self._reconfigure_entry.data if self._reconfigure_entry else {}
        if user_input is not None:
            data = {CONF_CONNECTION_TYPE: CONNECTION_RTU, **user_input}
            error = await _test_connection(self.hass, data)
            if error is None:
                if self._reconfigure_entry:
                    return self.async_update_reload_and_abort(
                        self._reconfigure_entry,
                        title=f"SDM72D {data[CONF_SERIAL_PORT]}",
                        data=data,
                    )
                await self.async_set_unique_id(
                    f"{data[CONF_SERIAL_PORT]}:{data[CONF_SLAVE_ID]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"SDM72D {data[CONF_SERIAL_PORT]}", data=data
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="rtu",
            data_schema=_schema_rtu(user_input or defaults),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None) -> FlowResult:
        """Allow reconfiguring an existing entry (IP, port, slave ID, connection type)."""
        self._reconfigure_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        current_type = self._reconfigure_entry.data.get(
            CONF_CONNECTION_TYPE, CONNECTION_TCP
        )

        if user_input is not None:
            self._connection_type = user_input[CONF_CONNECTION_TYPE]
            if self._connection_type in (CONNECTION_TCP, CONNECTION_TCP_RTU):
                return await self.async_step_tcp()
            return await self.async_step_rtu()

        schema = vol.Schema(
            {
                vol.Required(CONF_CONNECTION_TYPE, default=current_type): vol.In(
                    [CONNECTION_TCP, CONNECTION_TCP_RTU, CONNECTION_RTU]
                )
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SDM72DOptionsFlow(config_entry)


class SDM72DOptionsFlow(config_entries.OptionsFlow):
    """Allow changing the scan interval without re-entering connection details."""

    def __init__(self, entry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._entry.options.get(
            CONF_SCAN_INTERVAL,
            self._entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                    int, vol.Range(min=5, max=3600)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
