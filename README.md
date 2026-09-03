# Eastron SDM72D – Home Assistant Integration

HACS-kompatible Integration für den Eastron SDM72D 3-Phasen-Stromzähler via Modbus (TCP oder RTU).

## Sensoren

Die Integration legt ein Gerät **SDM72D** (Eastron, SDM72D-M-2) mit 22 Sensoren und einem Button an.

| Entity-ID | Messgröße | Einheit | State Class |
|---|---|---|---|
| `sensor.sdm72d_voltage_l1` | Spannung L1 | V | measurement |
| `sensor.sdm72d_voltage_l2` | Spannung L2 | V | measurement |
| `sensor.sdm72d_voltage_l3` | Spannung L3 | V | measurement |
| `sensor.sdm72d_average_voltage` | Spannung, Mittel L-N | V | measurement |
| `sensor.sdm72d_current_l1` | Stromstärke L1 | A | measurement |
| `sensor.sdm72d_current_l2` | Stromstärke L2 | A | measurement |
| `sensor.sdm72d_current_l3` | Stromstärke L3 | A | measurement |
| `sensor.sdm72d_neutral_current` | Neutralleiterstrom | A | measurement |
| `sensor.sdm72d_active_power_l1` | Wirkleistung L1 | W | measurement |
| `sensor.sdm72d_active_power_l2` | Wirkleistung L2 | W | measurement |
| `sensor.sdm72d_active_power_l3` | Wirkleistung L3 | W | measurement |
| `sensor.sdm72d_active_power` | Wirkleistung gesamt | W | measurement |
| `sensor.sdm72d_apparent_power` | Scheinleistung | VA | measurement |
| `sensor.sdm72d_reactive_power` | Blindleistung | var | measurement |
| `sensor.sdm72d_power_factor` | Leistungsfaktor | – | measurement |
| `sensor.sdm72d_frequency` | Netzfrequenz | Hz | measurement |
| `sensor.sdm72d_import_energy` | Import-Energie | kWh | total_increasing |
| `sensor.sdm72d_export_energy` | Export-Energie | kWh | total_increasing |
| `sensor.sdm72d_total_energy` | Gesamtenergie (Import + Export) | kWh | total_increasing |
| `sensor.sdm72d_resettable_import_energy` | Import, rücksetzbar | kWh | total_increasing |
| `sensor.sdm72d_resettable_export_energy` | Export, rücksetzbar | kWh | total_increasing |
| `sensor.sdm72d_net_energy` | Netto-Energie (Import − Export) | kWh | total |
| `button.sdm72d_reset_energy_counters` | Rücksetzbare Zähler löschen | – | – |

`net_energy` trägt bewusst `total` statt `total_increasing`: der Wert kann fallen, sobald mehr exportiert als importiert wird.

## Voraussetzungen

* **Home Assistant 2026.9 oder neuer.** Die Integration bezieht ihre Modbus-Verbindung über `async_get_unit` der `modbus`-Integration und teilt sie sich dadurch mit anderen Integrationen am selben Bus. Diese API gibt es erst ab 2026.9.
* Ab Version 2.0.0 wird die Geräte-Bibliothek [`eastron-sdm-modbus`](https://github.com/cjungde/eastron-sdm-modbus) benötigt; Home Assistant installiert sie beim Einrichten selbst.

## Installation via HACS

1. HACS → **Integrations** → ⋮ → **Custom repositories**
2. Repository-URL eintragen, Kategorie **Integration**
3. Integration installieren, Home Assistant neu starten
4. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Eastron SDM72D**

## Migration von Modbus-YAML

1. Alle `modbus:`-Einträge für den Zähler aus der YAML-Konfiguration entfernen
2. Home Assistant neu starten
3. Integration über den Config-Flow einrichten

**Die Entity-IDs ändern sich dabei.** Die Integration vergibt eigene IDs nach dem
Schema `sensor.sdm72d_*`; die alten YAML-Namen (`sensor.e72d_*`) bleiben nicht
erhalten. Die vollständige Gegenüberstellung steht in
[`tools/entity_id_migration.md`](tools/entity_id_migration.md), und
[`tools/migrate_influxdb.py`](tools/migrate_influxdb.py) schreibt vorhandene
InfluxDB-Reihen auf die neuen Namen um.

Beim Umstieg von Version 1.x auf 2.0.0 ist dagegen **nichts zu migrieren**: die
Entity-IDs, ihre Historie und ihre Langzeitstatistik bleiben unverändert.

## Verbindungsparameter

**Modbus TCP:** IP-Adresse des Ethernet-Adapters, Port 502, Slave-ID des Zählers (Standard: 1)

**Modbus RTU (RS485):** Serieller Port (z.B. `/dev/ttyUSB0`), Baudrate 9600, Parität N, 1 Stoppbit, Slave-ID 1

## Modbus-Registerübersicht (SDM72D-M-2)

Alle Werte sind IEEE 754 Float32 über zwei Register, Big-Endian, gelesen als
Input-Register (FC04). Die Adressen sind Protokolladressen. Der Zähler
beantwortet höchstens 30 Parameter je Anfrage.

| Register | Messgröße |
|---|---|
| 0x0000 (0) | Spannung L1 |
| 0x0002 (2) | Spannung L2 |
| 0x0004 (4) | Spannung L3 |
| 0x0006 (6) | Stromstärke L1 |
| 0x0008 (8) | Stromstärke L2 |
| 0x000A (10) | Stromstärke L3 |
| 0x000C (12) | Wirkleistung L1 |
| 0x000E (14) | Wirkleistung L2 |
| 0x0010 (16) | Wirkleistung L3 |
| 0x002A (42) | Spannung, Mittel L-N |
| 0x0034 (52) | Gesamtwirkleistung |
| 0x0038 (56) | Scheinleistung |
| 0x003C (60) | Blindleistung |
| 0x003E (62) | Leistungsfaktor |
| 0x0046 (70) | Frequenz |
| 0x0048 (72) | Import-Energie |
| 0x004A (74) | Export-Energie |
| 0x00E0 (224) | Neutralleiterstrom |
| 0x0156 (342) | Gesamtenergie |
| 0x0184 (388) | Import, rücksetzbar |
| 0x0186 (390) | Export, rücksetzbar |
| 0x018C (396) | Netto-Energie |

Der Neutralleiterstrom steht auf **0x00E0**, nicht auf 0x0030 — dort liegt die
Summe der Leiterströme, die bei unsymmetrischer Last davon abweicht.

Die rücksetzbaren Zähler löscht der Button über zwei Holding-Register: die
Freigabe (KPPA) auf 0x000E mit dem Zählerpasswort, danach 0x0003 auf 0xF010.
Letzteres ist schreibgeschützt ohne Antwort — der Zähler führt den Reset aus und
quittiert nicht.
