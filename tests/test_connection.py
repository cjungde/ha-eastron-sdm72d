"""The mapping from stored config-entry data to connection parameters."""

from __future__ import annotations

from modbus_connection import ModbusSerialParams, ModbusTcpParams

from .conftest import load_module

params_from_entry_data = load_module("connection").params_from_entry_data


def test_tcp_uses_socket_framing() -> None:
    params = params_from_entry_data(
        {"connection_type": "tcp", "host": "192.168.1.50", "port": 502}
    )

    assert isinstance(params, ModbusTcpParams)
    assert (params.host, params.port, params.framer) == ("192.168.1.50", 502, "socket")


def test_tcp_rtu_keeps_the_socket_but_switches_framing() -> None:
    """A transparent serial-to-Ethernet gateway tunnels raw RTU frames."""
    params = params_from_entry_data(
        {"connection_type": "tcp_rtu", "host": "192.168.1.50", "port": 8899}
    )

    assert isinstance(params, ModbusTcpParams)
    assert (params.host, params.port, params.framer) == ("192.168.1.50", 8899, "rtu")


def test_serial_carries_the_line_settings() -> None:
    params = params_from_entry_data(
        {
            "connection_type": "rtu",
            "serial_port": "/dev/ttyUSB0",
            "baudrate": 19200,
            "parity": "E",
            "stopbits": 2,
        }
    )

    assert isinstance(params, ModbusSerialParams)
    assert params.device == "/dev/ttyUSB0"
    assert (params.baudrate, params.parity, params.stopbits) == (19200, "E", 2)
    assert (params.bytesize, params.framer) == (8, "rtu")


def test_serial_falls_back_to_the_documented_defaults() -> None:
    """An entry written before a setting existed still has to open."""
    params = params_from_entry_data(
        {"connection_type": "rtu", "serial_port": "/dev/ttyUSB0"}
    )

    assert (params.baudrate, params.parity, params.stopbits) == (9600, "N", 1)


def test_a_missing_connection_type_is_treated_as_tcp() -> None:
    """The oldest entries predate the connection-type option."""
    params = params_from_entry_data({"host": "192.168.1.50"})

    assert isinstance(params, ModbusTcpParams)
    assert (params.port, params.framer) == (502, "socket")
