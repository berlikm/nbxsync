# Extreme IQ Engine by SNMP — OID mapping

Enterprise: `enterprises.26928` (Aerohive / Extreme IQ Engine).  
Vendor MIBs (XIQ Auxiliary Files): `zabbix/reference/aerohive-mibs/`.  
Community shortlist reference: `reference_bgp4plus_Aerohive_AP.xml` ([bgp4plus](https://github.com/bgp4plus/Zabbix-Template), Zabbix 5.0 — do not import).

## System scalars (`AH-SYSTEM-MIB` → `ahProduct.2`)

| Item intent | Object | OID | Notes |
|---|---|---|---|
| Name | `ahSystemName` | `26928.1.2.1.0` | |
| Description | `ahSystemDescription` | `26928.1.2.2.0` | |
| CPU % | `ahCpuUtilization` | `26928.1.2.3.0` | 0..100 |
| Memory % | `ahMemUtilization` | `26928.1.2.4.0` | 0..100 |
| Serial | `ahSystemSerial` | `26928.1.2.5.0` | |
| Device mode | `ahDeviceMode` | `26928.1.2.6.0` | |
| Uptime | `ahUpTime` | `26928.1.2.7.0` | **DisplayString**, not TimeTicks |
| Hardware | `ahHwVersion` | `26928.1.2.8.0` | |
| Client count | `ahClientCount` | `26928.1.2.9.0` | 0..10000 |
| Temperature | `ahEnvirmentTemp` | `26928.1.2.10.0` | MIB spelling |
| Fan RPM | `ahEnvirmentFan` | `26928.1.2.11.0` | Often N/A on wall APs |
| Firmware | `ahFirmwareVersion` | `26928.1.2.12.0` | Missing from bgp4plus template |

## Radio / interface (`AH-INTERFACE-MIB` → `ahAPInterface.1` = `26928.1.1.1.2.1`)

| Table | Base OID | Index | Columns for v1 |
|---|---|---|---|
| `ahXIfTable` | `…2.1.1` | ifIndex | `ahIfName` (.1), type/mode for LLD filter |
| `ahRadioAttributeTable` | `…2.1.5` | ifIndex | channel (.1), txPower (.2), noiseFloor (.3) |
| `ahRadioStatsTable` | `…2.1.3` | ifIndex | retries (.7), drops (.8), errors (.9), airtime TX/RX (.22/.23) |
| `ahAssociationTable` | `…2.1.2` | ifIndex + MAC | v2 — RSSI, SSID, rates |
| `ahVIfStatsTable` | `…2.1.4` | ifIndex | v2 — per-SSID counters |

Noise floor: MIB *value = actual_dBm + 256*. Template: FLOAT + JS parse (some agents return OCTET STRING) then −256.

Radio LLD:
- **Primary (MIB):** `ahIfType=ahPHYSICAL(0)` vs `ahVIRTURAL(1)` — AH-SMI-MIB
- **Secondary (AP305C observed):** name `^(wifi|…)[0-9]+$` — drops VAP `wifi0.1` that still appear as physical in some walks
- `ahRadioAttributeTable` is per radio; VAP ifIndexes have no channel/Tx/noise rows

Thresholds (CPU/ICMP/etc.): **ops defaults** in template macros — not Extreme-published alert points (GTAC 000104240 = MIB pack only).

## Standard MIBs

| Area | MIB | Notes |
|---|---|---|
| Eth traffic / oper | IF-MIB | Filter to physical ethernet; wifi/SSID via Hive tables |
| Duplex | EtherLike-MIB | Eth only |
| ICMP / SNMP avail | Zabbix agent items | Do **not** also link Network Generic |

## Traps (later)

`AH_TRAP_MIB` under `ahAPTrap` (`26928.1.1.1.1`): failure, threshold, state change, PoE, channel/power, client info, interference.

## Canary checklist (before YAML freeze)

- [ ] `snmpget` all `ahSystem.*.0` on pilot
- [ ] `snmpwalk` `ahIfName` + radio attribute table
- [ ] Confirm wifi ifIndex set vs eth
- [ ] Confirm SNMPv3 `MONITORING` after XIQ manage-SNMP push
