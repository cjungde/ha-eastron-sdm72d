#!/usr/bin/env python3
"""Build a shadow copy of the integration that can run beside the installed one.

The point is to compare two versions against the same physical meter at the
same time. The shadow declares its own domain, so Home Assistant treats it as
an unrelated integration: its own config entry, its own device, its own
entities. Nothing that the production entry feeds -- the COP chain, the
utility_meter counters, the SCOP sensors -- can see it.

Why only these five substitutions are needed:

* ``unique_id`` is built from the config entry id, and a second entry gets a
  fresh one. There is no unique_id collision to avoid and no ``_2`` suffix to
  fear, so nothing about the entity descriptions has to change.
* ``DeviceInfo.identifiers`` carries the domain, so the device separates itself
  once the domain differs.
* Entity ids, though, come from the device name, because the entities set
  ``_attr_has_entity_name``. Renaming the device is what turns
  ``sensor.sdm72d_active_power`` into ``sensor.sdm72d_test_active_power``.
* Everything else in the component reaches the domain through ``const.DOMAIN``
  or a relative import, translations included.

The scan interval is slackened deliberately. Two integrations and the shadow
all talk to the same gateway; if a single RS485 line sits behind it, overlapping
requests can interleave into framing errors that hit the production entry too.
Sampling every five minutes is plenty for a comparison and cuts the collision
rate by an order of magnitude.

Usage:

    python3 tools/make_shadow.py <target-dir>

where <target-dir> is the Home Assistant ``custom_components`` directory, e.g.

    python3 tools/make_shadow.py /config/custom_components

Re-running replaces the shadow, so regenerate it after every code change rather
than maintaining two copies that drift apart.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

SOURCE_DOMAIN = "eastron_sdm72d"
SHADOW_DOMAIN = "eastron_sdm72d_test"

# (relative path, exact text to find, replacement). Every one of these must
# match exactly once; a miss means the component moved on and this script is
# stale, which is worth failing over rather than shipping a half-renamed copy.
SUBSTITUTIONS: tuple[tuple[str, str, str], ...] = (
    (
        "manifest.json",
        f'"domain": "{SOURCE_DOMAIN}"',
        f'"domain": "{SHADOW_DOMAIN}"',
    ),
    (
        "manifest.json",
        '"name": "Eastron SDM72D"',
        '"name": "Eastron SDM72D (Test)"',
    ),
    (
        "const.py",
        f'DOMAIN = "{SOURCE_DOMAIN}"',
        f'DOMAIN = "{SHADOW_DOMAIN}"',
    ),
    (
        "const.py",
        "DEFAULT_SCAN_INTERVAL = 30",
        "DEFAULT_SCAN_INTERVAL = 300",
    ),
    (
        "sensor.py",
        'name="SDM72D",',
        'name="SDM72D Test",',
    ),
    (
        "button.py",
        'name="SDM72D",',
        'name="SDM72D Test",',
    ),
)

IGNORE = shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc")


def build(source: Path, target_parent: Path) -> Path:
    """Copy the component and rewrite it into the shadow domain."""
    target = target_parent / SHADOW_DOMAIN
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=IGNORE)

    for filename, old, new in SUBSTITUTIONS:
        path = target / filename
        text = path.read_text()
        count = text.count(old)
        if count != 1:
            shutil.rmtree(target)
            raise SystemExit(
                f"{filename}: expected exactly one occurrence of {old!r}, "
                f"found {count}. The component changed; update SUBSTITUTIONS."
            )
        path.write_text(text.replace(old, new))

    # A leftover reference means a substitution was forgotten, not that the
    # copy is merely cosmetic: two components claiming one domain break both.
    stale = [
        p.relative_to(target)
        for p in target.rglob("*")
        if p.is_file()
        and p.suffix in {".py", ".json"}
        and SOURCE_DOMAIN in p.read_text()
        and SHADOW_DOMAIN not in p.read_text()
    ]
    if stale:
        shutil.rmtree(target)
        raise SystemExit(f"stale references to {SOURCE_DOMAIN} in: {stale}")

    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        type=Path,
        help="Home Assistant custom_components directory",
    )
    args = parser.parse_args()

    source = Path(__file__).resolve().parent.parent / "custom_components" / SOURCE_DOMAIN
    if not source.is_dir():
        raise SystemExit(f"component not found at {source}")
    if not args.target.is_dir():
        raise SystemExit(f"not a directory: {args.target}")

    target = build(source, args.target)
    print(f"shadow written to {target}")
    print("Restart Home Assistant, then add the integration 'Eastron SDM72D (Test)'.")
    print("Entities appear as sensor.sdm72d_test_*, polled every 300 s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
