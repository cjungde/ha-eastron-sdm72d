"""Config flow for the Eastron SDM72D integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

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
    CONNECTION_RTU,
    DEFAULT_PORT,
    DEFAULT_SLAVE_ID,
    DEFAULT_BAUDRATE,
    DEFAULT_PARITY,
    DEFAULT_STOPBITS,
    DEFAULT_SCAN_INTERVAL,
)

_SCHEMA_CONNECTION_TYPE = vol.Schema(
    {vol.Required(CONF_CONNECTION_TYPE, default=CONNECTION_TCP): vol.In([CONNECTION_TCP, CONNECTION_RTU])}
)


def _schema_tcp(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("host", default=defaults.get("host", "")): str,
            vol.Required("port", default=defaults.get("port", DEFAULT_PORT)): vol.All(int, vol.Range(min=1, max=65535)),
            vol.Required(CONF_SLAVE_ID, default=defaults.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)): vol.All(int, vol.Range(min=1, max=247)),
            vol.Required(CONF_SCAN_INTERVAL, default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): vol.All(int, vol.Range(min=5, max=3600)),
        }
    )


def _schema_rtu(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_SERIAL_PORT, default=defaults.get(CONF_SERIAL_PORT, "/dev/ttyUSB0")): str,
            vol.Required(CONF_BAUDRATE, default=defaults.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)): vol.In([1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]),
            vol.Required(CONF_PARITY, default=defaults.get(CONF_PARITY, DEFAULT_PARITY)): vol.In(["N", "E", "O"]),
            vol.Required(CONF_STOPBITS, default=defaults.get(CONF_STOPBITS, DEFAULT_STOPBITS)): vol.In([1, 2]),
            vol.Required(CONF_SLAVE_ID, default=defaults.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)): vol.All(int, vol.Range(min=1, max=247)),
            vol.Required(CONF_SCAN_INTERVAL, default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): vol.All(int, vol.Range(min=5, max=3600)),
        }
    )


async def _test_connection(data: dict) -> str | None:
    """Try to connect and read one register. Returns an error key or None on success."""
    try:
        from pymodbus.client import AsyncModbusTcpClient, AsyncModbusSerialClient
        from pymodbus.exceptions import ModbusException

        if data.get(CONF_CONNECTION_TYPE, CONNECTION_TCP) == CONNECTION_TCP:
            client = AsyncModbusTcpClient(host=data["host"], port=data.get("port", DEFAULT_PORT))
        else:
            client = AsyncModbusSerialClient(
                port=data[CONF_SERIAL_PORT],
                baudrate=data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE),
                parity=data.get(CONF_PARITY, DEFAULT_PARITY),
                stopbits=data.get(CONF_STOPBITS, DEFAULT_STOPBITS),
                bytesize=8,
            )

        await client.connect()
        if not client.connected:
            return "cannot_connect"

        result = await client.read_input_registers(address=52, count=2, slave=data[CONF_SLAVE_ID])
        client.close()

        if hasattr(result, "isError") and result.isError():
            return "invalid_slave_id"
        return None

    except ModbusException:
        return "cannot_connect"
    except Exception:
        return "unknown"


class SDM72DConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the UI config flow for Eastron SDM72D."""

    VERSION = 1
    _connection_type: str = CONNECTION_TCP
    _reconfigure_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._connection_type = user_input[CONF_CONNECTION_TYPE]
            if self._connection_type == CONNECTION_TCP:
                return await self.async_step_tcp()
            return await self.async_step_rtu()

        return self.async_show_form(step_id="user", data_schema=_SCHEMA_CONNECTION_TYPE)

    async def async_step_tcp(self, user_input=None) -> FlowResult:
        errors: dict[str, str] = {}
        defaults = self._reconfigure_entry.data if self._reconfigure_entry else {}
        if user_input is not None:
            data = {CONF_CONNECTION_TYPE: CONNECTION_TCP, **user_input}
            error = await _test_connection(data)
            if error is None:
                if self._reconfigure_entry:
                    return self.async_update_reload_and_abort(
                        self._reconfigure_entry,
                        title=f"SDM72D {data['host']}",
                        data=data,
                    )
                await self.async_set_unique_id(f"{data['host']}:{data['port']}:{data[CONF_SLAVE_ID]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"SDM72D {data['host']}", data=data)
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
            error = await _test_connection(data)
            if error is None:
                if self._reconfigure_entry:
                    return self.async_update_reload_and_abort(
                        self._reconfigure_entry,
                        title=f"SDM72D {data[CONF_SERIAL_PORT]}",
                        data=data,
                    )
                await self.async_set_unique_id(f"{data[CONF_SERIAL_PORT]}:{data[CONF_SLAVE_ID]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"SDM72D {data[CONF_SERIAL_PORT]}", data=data)
            errors["base"] = error

        return self.async_show_form(
            step_id="rtu",
            data_schema=_schema_rtu(user_input or defaults),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None) -> FlowResult:
        """Allow reconfiguring an existing entry (IP, port, slave ID, connection type)."""
        self._reconfigure_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        current_type = self._reconfigure_entry.data.get(CONF_CONNECTION_TYPE, CONNECTION_TCP)

        if user_input is not None:
            self._connection_type = user_input[CONF_CONNECTION_TYPE]
            if self._connection_type == CONNECTION_TCP:
                return await self.async_step_tcp()
            return await self.async_step_rtu()

        schema = vol.Schema(
            {vol.Required(CONF_CONNECTION_TYPE, default=current_type): vol.In([CONNECTION_TCP, CONNECTION_RTU])}
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
            {vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(int, vol.Range(min=5, max=3600))}
        )
        return self.async_show_form(step_id="init", data_schema=schema)
