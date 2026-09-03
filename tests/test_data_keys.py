"""The contract the entity unique_ids are built from.

Each sensor's unique_id is ``f"{entry.entry_id}_{description.key}"``, so a
renamed key silently orphans an entity: it loses its history, its statistics,
and every dashboard, utility meter and automation that names it. These tests
read both files with ``ast`` — no import, no Home Assistant — and pin the keys
in place, including against the measurement names the device library exposes.
"""

from __future__ import annotations

import ast
from pathlib import Path

INTEGRATION_DIR = (
    Path(__file__).resolve().parent.parent / "custom_components" / "eastron_sdm72d"
)

# The 22 keys as they were published. Frozen deliberately: this list is the
# reason the rewrite onto a device library did not have to migrate any data.
PUBLISHED_KEYS = frozenset(
    {
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
    }
)


def _module(name: str) -> ast.Module:
    return ast.parse((INTEGRATION_DIR / f"{name}.py").read_text())


def _sensor_keys() -> list[str]:
    """Every ``key=`` passed to a sensor description, in declaration order."""
    keys: list[str] = []
    for node in ast.walk(_module("sensor")):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg == "key" and isinstance(keyword.value, ast.Constant):
                keys.append(keyword.value.value)
    return keys


def _data_keys() -> list[str]:
    """The DATA_KEYS tuple the coordinator fills from the device library."""
    for node in ast.walk(_module("coordinator")):
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "DATA_KEYS"
        ):
            return [element.value for element in node.value.elts]
    raise AssertionError("DATA_KEYS not found in coordinator.py")


def test_sensor_keys_are_unchanged() -> None:
    assert set(_sensor_keys()) == PUBLISHED_KEYS


def test_no_sensor_key_appears_twice() -> None:
    """Two descriptions sharing a key would collide on one unique_id."""
    keys = _sensor_keys()
    assert len(keys) == len(set(keys))


def test_the_coordinator_publishes_exactly_those_keys() -> None:
    """A key a sensor reads but the coordinator never fills is a dead entity."""
    assert set(_data_keys()) == PUBLISHED_KEYS


def test_data_keys_has_no_duplicates() -> None:
    keys = _data_keys()
    assert len(keys) == len(set(keys))
