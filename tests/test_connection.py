"""The mapping from stored config-entry data to connection parameters."""

from __future__ import annotations

from modbus_connection import ModbusSerialParams, ModbusTcpParams

from .conftest import load_module

params_from_entry_data = load_module("connection").params_from_entry_data


def test_tcp_asks_for_no_framer() -> None:
    """Plain Modbus TCP has one framing, so the library needs no argument."""
    params = params_from_entry_data(
        {"connection_type": "tcp", "host": "192.168.1.50", "port": 502}
    )

    assert params == ModbusTcpParams(host="192.168.1.50", port=502)


def test_tcp_rtu_becomes_a_serial_link_on_a_socket() -> None:
    """A transparent serial-to-Ethernet gateway tunnels raw RTU frames."""
    params = params_from_entry_data(
        {"connection_type": "tcp_rtu", "host": "192.168.1.50", "port": 8899}
    )

    assert params == ModbusSerialParams(
        device="socket://192.168.1.50:8899", baudrate=115200, framer="rtu"
    )


def test_tcp_rtu_brackets_an_ipv6_host() -> None:
    params = params_from_entry_data({"connection_type": "tcp_rtu", "host": "fd00::10"})

    assert params.device == "socket://[fd00::10]:502"


def test_the_two_tcp_framings_do_not_compare_equal() -> None:
    """One socket cannot carry both framings, so they must not share a connection."""
    plain = params_from_entry_data({"connection_type": "tcp", "host": "192.168.1.50"})
    tunnelled = params_from_entry_data(
        {"connection_type": "tcp_rtu", "host": "192.168.1.50"}
    )

    assert plain != tunnelled


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

    assert params == ModbusTcpParams(host="192.168.1.50", port=502)
