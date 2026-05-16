# Eastron SDM72D – Home Assistant Integration

HACS-kompatible Integration für den Eastron SDM72D 3-Phasen-Stromzähler via Modbus (TCP oder RTU).

## Sensoren

Die Integration erstellt ein Gerät **E72d** mit folgenden Sensoren – die Entity-IDs der bestehenden Modbus-YAML-Konfiguration bleiben erhalten:

| Entity-ID | Beschreibung | Einheit |
|---|---|---|
| `sensor.e72d_derzeitige_wirkleistung` | Gesamtwirkleistung | W |
| `sensor.e72d_derzeitige_wirkleistung_l1` | Wirkleistung L1 | W |
| `sensor.e72d_derzeitige_wirkleistung_l2` | Wirkleistung L2 | W |
| `sensor.e72d_derzeitige_wirkleistung_l3` | Wirkleistung L3 | W |
| `sensor.e72d_wirkleistung_import_tageszahler` | Import-Energie (kumulativ) | kWh |
| `sensor.e72d_wirkleistung_export_tageszahler` | Export-Energie (kumulativ) | kWh |
| `sensor.e72d_stromstarke_neutralleiter` | Neutralleiterstrom | A |
| `sensor.e72d_leistungsfaktor` | Leistungsfaktor | – |
| `sensor.e72d_spannung_l1` | Spannung L1 | V |
| `sensor.e72d_spannung_l2` | Spannung L2 | V |
| `sensor.e72d_spannung_l3` | Spannung L3 | V |
| `sensor.e72d_stromstarke_l1` | Stromstärke L1 | A |
| `sensor.e72d_stromstarke_l2` | Stromstärke L2 | A |
| `sensor.e72d_stromstarke_l3` | Stromstärke L3 | A |
| `sensor.e72d_frequenz` | Netzfrequenz | Hz |

## Installation via HACS

1. HACS → **Integrations** → ⋮ → **Custom repositories**
2. Repository-URL eintragen, Kategorie **Integration**
3. Integration installieren, Home Assistant neu starten
4. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Eastron SDM72D**

## Migration von Modbus-YAML

1. Alle `modbus:`-Einträge für den E72D aus der YAML-Konfiguration entfernen
2. Home Assistant neu starten
3. Integration über den Config-Flow einrichten

## Verbindungsparameter

**Modbus TCP:** IP-Adresse des Ethernet-Adapters, Port 502, Slave-ID des Zählers (Standard: 1)

**Modbus RTU (RS485):** Serieller Port (z.B. `/dev/ttyUSB0`), Baudrate 9600, Parität N, 1 Stoppbit, Slave-ID 1

## Modbus-Registerübersicht (SDM72D)

Alle Werte werden als IEEE 754 Float32 (2 × 16-bit-Register, Big-Endian) übertragen.

| Register | Beschreibung |
|---|---|
| 0x000C (12) | Wirkleistung L1 |
| 0x000E (14) | Wirkleistung L2 |
| 0x0010 (16) | Wirkleistung L3 |
| 0x0030 (48) | Neutralleiterstrom |
| 0x0034 (52) | Gesamtwirkleistung |
| 0x003E (62) | Leistungsfaktor |
| 0x0046 (70) | Frequenz |
| 0x0048 (72) | Import-Energie (kWh) |
| 0x004A (74) | Export-Energie (kWh) |
