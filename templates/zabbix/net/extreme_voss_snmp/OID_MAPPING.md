# Extreme VOSS by SNMP — OID mapping vs Extreme EXOS by SNMP

Source EXOS template: [templates/net/extreme_snmp](https://git.zabbix.com/projects/ZBX/repos/zabbix/browse/templates/net/extreme_snmp) (Zabbix 8.0).  
VOSS MIBs: RapidCity `enterprises.2272` (`docs/VOSS-5520.9.3.1.0_mib.txt`).

**Important:** `rcSysCpuUtil` / `rcSysDram*` are **not supported on VOSS** (MIB DESCRIPTION). Use `rcKhiSlot*` instead.

| EXOS (official) | EXOS OID | VOSS object | VOSS OID | Notes |
|---|---|---|---|---|
| CPU util (scalar) | `1916.1.32.1.2.0` | `rcKhiSlotCpuCurrentUtil` | `2272.1.85.10.1.1.2.{slot}` | LLD by slot; INTEGER 1..100 |
| Memory free/total LLD | `1916.1.32.2.2.1.{2,3}` | `rcKhiSlotMemFree` / `MemUsed` | `2272.1.85.10.1.1.{7,6}.{slot}` | KB; util also at `.8` |
| Temperature value | `1916.1.1.1.8.0` | `rcVossSystemTemperatureTemperature` | `2272.1.101.1.1.2.1.3.{idx}` | °C; LLD sensors |
| Temperature status | `1916.1.1.1.7.0` | `rcVossSystemTemperatureStatus` | `2272.1.101.1.1.2.1.6.{idx}` | 1=normal 2=highWarning 3=highCritial |
| Fan status LLD | `1916.1.1.1.27.1.2` | `rcChasFanOperStatus` | `2272.1.4.7.1.1.2.{id}` | 1=unk 2=up 3=down 4=notpresent; **crit=3** |
| Fan speed | `1916.1.1.1.27.1.?` | — | — | No RPM in rcChasFan; ambient °C at `.3` instead |
| PSU status LLD | `1916.1.1.1.9.1.2` | `rcChasPowerSupplyOperStatus` | `2272.1.4.8.1.1.2.{id}` | 1=unk 2=empty 3=up 4=down; **crit=4** |
| OS / software rev | `1916.1.1.1.13.0` | `rcSysVersion` | `2272.1.1.7.0` | |
| HW model | ENTITY `47.1.1.1.1.2.1` | `rcChasModelName` | `2272.1.4.67.0` | Prefer chassis MIB |
| HW serial | ENTITY `47.1.1.1.1.11.1` | `rcChasSerialNumber` | `2272.1.4.2.0` | |
| HW revision | ENTITY `47.1.1.1.1.9.1` | `rcChasHardwareRevision` | `2272.1.4.3.0` | |
| IF-MIB / EtherLike / ICMP / SNMPv2 | same | same | same | Unchanged |
| Port label (canary) | ifAlias | ifAlias (+ `rcPortName` SIZE 42) | `31.1.1.1.18` / `2272.1.4.10.1.1.35` | Prefer ifAlias for Zabbix |

## Macro defaults (VOSS-specific)

| Macro | Value | Reason |
|---|---|---|
| `{$FAN_CRIT_STATUS}` | `3` | `down(3)` |
| `{$PSU_CRIT_STATUS}` | `4` | `down(4)` |
| `{$TEMP_CRIT_STATUS}` | `3` | `highCritial(3)` (MIB spelling) |

## Test matrix

Every SNMP OID in the template must pass `snmpget`/`snmpwalk` against a live VOSS agent before the item is considered verified. See `TEST_CHECKLIST.md`.


## Live lab (VOSS-VM 9.3.1.0)

Verified 2026-08-05 against Virtual Fabric Engine (`FEGNS3.9.3.1.0`) under QEMU TCG (`-cpu Haswell`).

| Check | Result |
|---|---|
| `rcKhiSlotCpuCurrentUtil.1` | PASS (values ~40–80%) |
| `rcKhiSlotMemUsed/Free/Util.1` | PASS (KB; util %) |
| `rcSysCpuUtil` / `rcSysDram*` | **absent** (`No Such Object`) |
| `rcChasPowerSupplyOperStatus` | PASS (PS1/PS2 = up(3)) |
| `rcChasFan*` | **absent on VOSS-VM** (keep LLD for hardware) |
| `rcVossSystemTemperature*` | PASS LLD; values `0` °C on VM; status `normal(1)` |
| `hrSystemUptime` | **absent**; use `sysUpTime` fallback |
| `ifAlias` after CLI `name USW-ID01` | PASS (`ifAlias.192=USW-ID01`) |
| `rcPortName` same port | empty — prefer **ifAlias** |
| Port ifIndex | `1/1` → `192`, `1/2` → `193`, … |

See `LAB_RESULTS.md` and `/opt/cursor/artifacts/VOSS_OID_VERIFY.txt`.
