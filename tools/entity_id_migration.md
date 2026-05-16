# Entity ID Migration: YAML Modbus → HACS Integration

| Messgröße | Alte Entity-ID (YAML) | Neue Entity-ID (HACS) |
|---|---|---|
| **Spannung** | | |
| Spannung L1 | `sensor.e72d_spannung_l1` | `sensor.sdm72d_voltage_l1` |
| Spannung L2 | `sensor.e72d_spannung_l2` | `sensor.sdm72d_voltage_l2` |
| Spannung L3 | `sensor.e72d_spannung_l3` | `sensor.sdm72d_voltage_l3` |
| Ø Spannung *(neu)* | — | `sensor.sdm72d_average_voltage` |
| **Stromstärke** | | |
| Stromstärke L1 | `sensor.e72d_stromstarke_l1` | `sensor.sdm72d_current_l1` |
| Stromstärke L2 | `sensor.e72d_stromstarke_l2` | `sensor.sdm72d_current_l2` |
| Stromstärke L3 | `sensor.e72d_stromstarke_l3` | `sensor.sdm72d_current_l3` |
| Neutralleiter | `sensor.e72d_stromstarke_neutralleiter` | `sensor.sdm72d_neutral_current` |
| **Leistung** | | |
| Wirkleistung L1 | `sensor.e72d_derzeitige_wirkleistung_l1` | `sensor.sdm72d_active_power_l1` |
| Wirkleistung L2 | `sensor.e72d_derzeitige_wirkleistung_l2` | `sensor.sdm72d_active_power_l2` |
| Wirkleistung L3 | `sensor.e72d_derzeitige_wirkleistung_l3` | `sensor.sdm72d_active_power_l3` |
| Wirkleistung Gesamt | `sensor.e72d_derzeitige_wirkleistung` | `sensor.sdm72d_active_power` |
| Scheinleistung | `sensor.e72d_scheinleistung_gesamt` | `sensor.sdm72d_apparent_power` |
| Blindleistung | `sensor.e72d_blindleistung_gesamt` | `sensor.sdm72d_reactive_power` |
| Leistungsfaktor | `sensor.e72d_leistungsfaktor` | `sensor.sdm72d_power_factor` |
| Frequenz | `sensor.e72d_frequenz` | `sensor.sdm72d_frequency` |
| **Energie** | | |
| Import (Tageszähler) | `sensor.e72d_wirkleistung_import_tageszahler` | `sensor.sdm72d_import_energy` |
| Export (Tageszähler) | `sensor.e72d_wirkleistung_export_tageszahler` | `sensor.sdm72d_export_energy` |
| Gesamtenergie *(neu)* | — | `sensor.sdm72d_total_energy` |
| Import rücksetzbar *(neu)* | — | `sensor.sdm72d_resettable_import_energy` |
| Export rücksetzbar *(neu)* | — | `sensor.sdm72d_resettable_export_energy` |
| Nettoenergie *(neu)* | — | `sensor.sdm72d_net_energy` |

> Die 5 mit *(neu)* markierten Sensoren existieren nur in der HACS-Integration — keine History, kein Migrationsaufwand.
