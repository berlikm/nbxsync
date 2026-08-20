# Extreme VOSS by SNMP ΓÇö live verification checklist

Target: Virtual VOSS / Fabric Engine (e.g. 9.3.1.0) with SNMP enabled.
Community (lab): document the community string used; default lab often `public`.

Mark each row: **PASS** / **FAIL** / **N/A** with the observed value or error.

## Prerequisites

- [ ] SNMP agent responds: `snmpget -v2c -c <community> <host> sysDescr.0`
- [ ] Template imported into Zabbix 7.0 without errors
- [ ] Host linked to **Extreme VOSS by SNMP** with correct interface/community

## Scalar / system items

| Item key | OID | snmpget result | Zabbix | Notes |
|---|---|---|---|---|
| `system.descr[sysDescr.0]` | `1.3.6.1.2.1.1.1.0` | | | |
| `system.name` | `1.3.6.1.2.1.1.5.0` | | | |
| `system.contact` | `1.3.6.1.2.1.1.4.0` | | | |
| `system.location` | `1.3.6.1.2.1.1.6.0` | | | |
| `system.hw.uptime[hrSystemUptime.0]` | `1.3.6.1.2.1.25.1.1.0` | | | |
| `system.net.uptime[sysUpTime.0]` | `1.3.6.1.2.1.1.3.0` | | | |
| `system.sw.os[rcSysVersion.0]` | `1.3.6.1.4.1.2272.1.1.7.0` | | | |
| `system.hw.model` | `1.3.6.1.4.1.2272.1.4.67.0` | | | |
| `system.hw.serialnumber` | `1.3.6.1.4.1.2272.1.4.2.0` | | | |
| `system.hw.version` | `1.3.6.1.4.1.2272.1.4.3.0` | | | |
| `system.hw.firmware` | `1.3.6.1.2.1.47.1.1.1.1.9.1` | | | May be empty on VOSS-VM |
| `system.cpu.util[rcKhiSlotCpuCurrentUtil.1]` | `1.3.6.1.4.1.2272.1.85.10.1.1.2.1` | | | Must NOT use rcSysCpuUtil |

## Negative checks (must fail / noSuchObject)

| Object | OID | Expected |
|---|---|---|
| `rcSysCpuUtil` | `1.3.6.1.4.1.2272.1.1.50.0` (confirm MIB) | not supported / noSuchObject |
| `rcSysDram*` | under `rcSystem` | not supported |

## LLD: Slot memory / CPU (`memory.discovery`)

Walk: `1.3.6.1.4.1.2272.1.85.10.1.1.2`

| Prototype key | OID pattern | Observed | Zabbix LLD |
|---|---|---|---|
| `vm.memory.available[rcKhiSlotMemFree.{#SNMPINDEX}]` | `...1.1.7.{slot}` | | units KBΓåÆB ├ù1024 |
| `vm.memory.used[rcKhiSlotMemUsed.{#SNMPINDEX}]` | `...1.1.6.{slot}` | | |
| `vm.memory.util[rcKhiSlotMemUtil.{#SNMPINDEX}]` | `...1.1.8.{slot}` | | |
| `system.cpu.util[rcKhiSlotCpuCurrentUtil.{#SNMPINDEX}]` | `...1.1.2.{slot}` | | |

## LLD: Fans (`fan.discovery`)

Walk: `1.3.6.1.4.1.2272.1.4.7.1.1.1`

| Prototype key | OID | Observed | Notes |
|---|---|---|---|
| `sensor.fan.status[rcChasFanOperStatus.{i}]` | `...7.1.1.2.{i}` | | crit = 3 |
| `sensor.fan.temp[rcChasFanAmbientTemperature.{i}]` | `...7.1.1.3.{i}` | | ┬░C; no RPM |

## LLD: PSU (`psu.discovery` / `psu.detail.discovery`)

Walk id + status. Filter `{#PSU.STATUS}` **NOT_MATCHES** `^2$` (`empty`). Keep `unknown(1)` / `up(3)` / `down(4)`.

Walk status: `1.3.6.1.4.1.2272.1.4.8.1.1.1` + `...8.1.1.2`
Walk detail: `1.3.6.1.4.1.2272.1.4.8.2.1.1` + `...8.2.1.15`

| Prototype key | OID | Observed | Notes |
|---|---|---|---|
| `sensor.psu.status[rcChasPowerSupplyOperStatus.{i}]` | `...8.1.1.2.{i}` | | crit = 4; empty(2) **not discovered** |
| `sensor.psu.watts[rcChasPowerSupplyDetailOutputWatts.{i}]` | `...8.2.1.10.{i}` | | Health Power honeycomb |

## LLD: Temperature (`temp.discovery`)

Walk description + value + status under `rcVossSystemTemperatureTable`

| Prototype key | OID | Observed |
|---|---|---|
| `sensor.temp.value[rcVossSystemTemperatureTemperature.{i}]` | `2272.1.101.1.1.2.1.3.{i}` | name = `{#SENSOR_DESCR}` (not index) |
| `sensor.temp.status[rcVossSystemTemperatureStatus.{i}]` | `2272.1.101.1.1.2.1.6.{i}` | 1/2/3 — **not** the Health honeycomb |

## LLD: Interfaces

| Check | Result |
|---|---|
| `net.if.discovery` returns ports | |
| ifAlias populated when CLI `name` set | canary |
| Traffic counters (`ifHCIn/OutOctets`) increment | |
| EtherLike duplex discovery | |

## Triggers (smoke)

| Trigger | How verified |
|---|---|
| Unavailable by ICMP | stop ping / wrong IP |
| No SNMP data collection | bad community |
| High CPU (slot) | threshold temp-lowered or load |
| Fan critical | only if lab can force status |
| PSU critical | only if lab can force status |
| Temp warning/critical | threshold macros |
| Interface link down | shut port |
| Host has been restarted | after reboot (uptime &lt; 10m) |

## Port-identity canary (optional)

| Step | Result |
|---|---|
| Set port `name` to `USW-ID01` | |
| `ifAlias` shows `USW-ID01` | |
| `rcPortName` shows same / truncated | SIZE Γëñ 42 |
| Leave description empty | ifAlias not overridden |

## Sign-off

| Field | Value |
|---|---|
| VOSS version | |
| Platform / image | |
| Zabbix version | |
| Date | |
| Verified by | |


## Lab sign-off (2026-08-05)

| Field | Value |
|---|---|
| VOSS version | 9.3.1.0 (FEGNS3.9.3.1.0) |
| Platform / image | Virtual 5520-24T-FabricEngine |
| Zabbix version | 7.0.29 |
| Template import | PASS |
| SNMP scalar core | PASS (except hrSystemUptime / fans on VM) |
| LLD memory/PSU/temp/IF | PASS |
| LLD fan | N/A on VOSS-VM (OID tree absent) |
| Port ifAlias canary | PASS (`name` ΓåÆ ifAlias) |
| Notes | QEMU needs `-cpu Haswell` (or richer) for FIPS; `qemu64` crashes |
