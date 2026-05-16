#!/usr/bin/env python3
"""
Migrate Eastron SDM72D entity IDs in InfluxDB 2.x
from old German YAML-Modbus names to new English HACS-integration names.

Usage:
    pip install influxdb-client
    python3 migrate_influxdb.py              # dry-run (no writes)
    python3 migrate_influxdb.py --run        # actually write migrated data
    python3 migrate_influxdb.py --run --delete-old  # also delete old entity data

Configuration:
    Set the four constants below, or use environment variables:
        INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET

How to find your values in the InfluxDB UI (http://<ha-ip>:8086):
    Token:  Data → API Tokens → copy your admin token
    Org:    Settings → About → Organisation name
    Bucket: "home_assistant" (confirmed from HA addon data path)
"""

import argparse
import os
import sys
from datetime import datetime

# ── Configuration ─────────────────────────────────────────────────────────────

INFLUXDB_URL    = os.getenv("INFLUXDB_URL",    "http://<HA-IP>:8086")
INFLUXDB_TOKEN  = os.getenv("INFLUXDB_TOKEN",  "YOUR_TOKEN_HERE")
INFLUXDB_ORG    = os.getenv("INFLUXDB_ORG",    "homeassistant")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "home_assistant")

# Start of migration range — all data from this date onwards will be migrated.
# Use "1970-01-01T00:00:00Z" to migrate everything.
RANGE_START = "1970-01-01T00:00:00Z"

# ── Entity ID mapping: old (German YAML) → new (English HACS) ─────────────────

ENTITY_MAPPING = {
    # Voltages
    "e72d_spannung_l1":                     "sdm72d_voltage_l1",
    "e72d_spannung_l2":                     "sdm72d_voltage_l2",
    "e72d_spannung_l3":                     "sdm72d_voltage_l3",
    # Currents
    "e72d_stromstarke_l1":                  "sdm72d_current_l1",
    "e72d_stromstarke_l2":                  "sdm72d_current_l2",
    "e72d_stromstarke_l3":                  "sdm72d_current_l3",
    # Per-phase active power
    "e72d_derzeitige_wirkleistung_l1":      "sdm72d_active_power_l1",
    "e72d_derzeitige_wirkleistung_l2":      "sdm72d_active_power_l2",
    "e72d_derzeitige_wirkleistung_l3":      "sdm72d_active_power_l3",
    # Total power / VA / VAr
    "e72d_derzeitige_wirkleistung":         "sdm72d_active_power",
    "e72d_scheinleistung_gesamt":           "sdm72d_apparent_power",
    "e72d_blindleistung_gesamt":            "sdm72d_reactive_power",
    # Power factor / frequency
    "e72d_leistungsfaktor":                 "sdm72d_power_factor",
    "e72d_frequenz":                        "sdm72d_frequency",
    # Energy counters
    "e72d_wirkleistung_import_tageszahler": "sdm72d_import_energy",
    "e72d_wirkleistung_export_tageszahler": "sdm72d_export_energy",
    # Neutral current
    "e72d_stromstarke_neutralleiter":       "sdm72d_neutral_current",
    # Note: avg_voltage / total_energy / resettable_* / net_energy
    # are new sensors with no prior history — no migration needed.
}

# ── Flux query templates ───────────────────────────────────────────────────────

_FLUX_COUNT = """
from(bucket: "{bucket}")
  |> range(start: {start})
  |> filter(fn: (r) => r["entity_id"] == "{old_id}")
  |> count()
  |> sum(column: "_value")
"""

_FLUX_MIGRATE = """
from(bucket: "{bucket}")
  |> range(start: {start})
  |> filter(fn: (r) => r["entity_id"] == "{old_id}")
  |> map(fn: (r) => ({{r with entity_id: "{new_id}"}}) )
  |> to(bucket: "{bucket}", org: "{org}")
"""

_FLUX_DELETE = """
import "influxdata/influxdb"
influxdb.cardinality(
  bucket: "{bucket}",
  predicate: (r) => r["entity_id"] == "{old_id}",
  start: {start},
)
"""

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run",        action="store_true", help="Write migrated data (default: dry-run only)")
    parser.add_argument("--delete-old", action="store_true", help="Delete old entity data after migration (requires --run)")
    args = parser.parse_args()

    if args.delete_old and not args.run:
        print("ERROR: --delete-old requires --run")
        sys.exit(1)

    if "YOUR_TOKEN_HERE" in INFLUXDB_TOKEN or "<HA-IP>" in INFLUXDB_URL:
        print("ERROR: Set INFLUXDB_URL and INFLUXDB_TOKEN before running.")
        print("       See configuration section at the top of this script.")
        sys.exit(1)

    try:
        from influxdb_client import InfluxDBClient
        from influxdb_client.client.delete_api import DeleteApi
    except ImportError:
        print("ERROR: influxdb-client not installed. Run: pip install influxdb-client")
        sys.exit(1)

    mode = "DRY-RUN" if not args.run else "LIVE"
    print(f"\n{'='*60}")
    print(f"  SDM72D InfluxDB Migration  [{mode}]")
    print(f"  URL:    {INFLUXDB_URL}")
    print(f"  Org:    {INFLUXDB_ORG}")
    print(f"  Bucket: {INFLUXDB_BUCKET}")
    print(f"  From:   {RANGE_START}")
    print(f"{'='*60}\n")

    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    query_api = client.query_api()

    total_migrated = 0
    skipped = 0

    for old_id, new_id in ENTITY_MAPPING.items():
        # Count existing data points for old entity
        count_query = _FLUX_COUNT.format(
            bucket=INFLUXDB_BUCKET, start=RANGE_START, old_id=old_id
        )
        try:
            tables = query_api.query(count_query)
            count = sum(r.get_value() for table in tables for r in table.records)
        except Exception as e:
            count = 0

        if count == 0:
            print(f"  SKIP  {old_id}  (no data found)")
            skipped += 1
            continue

        print(f"  {'WRITE' if args.run else 'WOULD'}  {old_id}")
        print(f"         → {new_id}  ({count:,} data points)")

        if args.run:
            migrate_query = _FLUX_MIGRATE.format(
                bucket=INFLUXDB_BUCKET,
                start=RANGE_START,
                old_id=old_id,
                new_id=new_id,
                org=INFLUXDB_ORG,
            )
            try:
                query_api.query(migrate_query)
                total_migrated += count
            except Exception as e:
                print(f"  ERROR migrating {old_id}: {e}")
                continue

            if args.delete_old:
                delete_api = client.delete_api()
                try:
                    delete_api.delete(
                        start="1970-01-01T00:00:00Z",
                        stop=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        predicate=f'entity_id="{old_id}"',
                        bucket=INFLUXDB_BUCKET,
                        org=INFLUXDB_ORG,
                    )
                    print(f"         ✓ old data deleted")
                except Exception as e:
                    print(f"  ERROR deleting old data for {old_id}: {e}")
        else:
            total_migrated += count

    print(f"\n{'='*60}")
    if args.run:
        print(f"  Done. {total_migrated:,} data points migrated, {skipped} entities skipped.")
        if not args.delete_old:
            print(f"  Old entity data still exists. Re-run with --delete-old to remove it.")
    else:
        print(f"  Dry-run complete. {total_migrated:,} data points would be migrated.")
        print(f"  Run with --run to apply, or --run --delete-old to apply and clean up.")
    print(f"{'='*60}\n")

    client.close()


if __name__ == "__main__":
    main()
