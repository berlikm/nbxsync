# Fortinet FMG-FAZ by SNMP — OID mapping

MIB: `zabbix/mibs/FORTINET-FORTIMANAGER-FORTIANALYZER-MIB-build3737.mib`
(`enterprises.12356.103` = `fnFortiManagerMib`). Serial is
**FORTINET-CORE-MIB** `fnSysSerial` (`enterprises.12356.100.1.1.1.0`), not this
MIB.

There is no official Zabbix template to remap against ([ZBXNEXT-10433](https://support.zabbix.com/browse/ZBXNEXT-10433)).
Optional objects (RAID, sensors, log rate, HA on standalone/VMs) use
`CHECK_NOT_SUPPORTED` → `0` or `[]` so appliances stay quiet.

Base: `FM = 1.3.6.1.4.1.12356.103`.

## Scalars

| Item key | Object | OID | Notes |
|---|---|---|---|
| `system.name` | `sysName` | `1.3.6.1.2.1.1.5.0` | SNMPv2-MIB |
| `system.descr` | `sysDescr` | `1.3.6.1.2.1.1.1.0` | |
| `system.net.uptime[sysUpTime.0]` | `sysUpTime` | `get[1.3.6.1.2.1.1.3.0]` | ×0.01; Overview 4th tile |
| `fm.sys.uptime` | `fmSysUpTime` | `FM.2.1.8.0` | Counter64 hundredths; reboot authority |
| `fm.sys.version` | `fmSysVersion` | `FM.2.1.7.0` | |
| `system.hw.serialnumber` | `fnSysSerial` | `1.3.6.1.4.1.12356.100.1.1.1.0` | CORE-MIB |
| `fm.sys.cpu.util` | `fmSysCpuUsage` | `FM.2.1.1.0` | 0..100 |
| `fm.sys.cpu.util.excl.nice` | `fmSysCpuUsageExcludedNice` | `FM.2.1.6.0` | optional |
| `fm.sys.mem.used` | `fmSysMemUsed` | `FM.2.1.2.0` | KB → B |
| `fm.sys.mem.capacity` | `fmSysMemCapacity` | `FM.2.1.3.0` | KB, physical+swap |
| `fm.sys.disk.used` | `fmSysDiskUsage` | `FM.2.1.4.0` | MB → B |
| `fm.sys.disk.capacity` | `fmSysDiskCapacity` | `FM.2.1.5.0` | MB |
| `fm.sys.log.rate.hr` | `fmSysLogRateHr` | `FM.2.1.10.0` | FmHundredths; ×0.01 |
| `fm.sys.log.index.rate` | `fmSysLogIndexingRate` | `FM.2.1.11.0` | FmHundredths |
| `fm.sys.log.lag` | `fmSysLogLagTime` | `FM.2.1.12.0` | seconds; FAZ product signal |
| `fm.sys.lic.gbday.today` | `fmSysLicGbDayToday` | `FM.2.1.13.0` | FmHundredths GiB |
| `fm.sys.lic.gbday.yesterday` | `fmSysLicGbDayYesterday` | `FM.2.1.14.0` | |
| `fm.sys.lic.gbday.weekavg` | `fmSysLicGbDayWeekAvg` | `FM.2.1.15.0` | |
| `fm.device.number` | `fmDeviceNumber` | `FM.6.1.1.0` | FMG = managed FortiGates; FAZ = log devices |
| `fm.vdom.number` | `fmVdomNumber` | `FM.6.1.2.0` | optional |
| `fm.adom.enabled` | `fmAdomEnabled` | `FM.5.1.1.0` | FnBoolState |
| `fm.adom.number` | `fmAdomNumber` | `FM.5.1.2.0` | |
| `fm.adom.max` | `fmAdomMax` | `FM.5.1.3.0` | optional |
| `fm.ha.mode` | `fmHaMode` | `FM.9.1.1.0` | 0=standalone 1=master 2=slave |
| `fm.ha.cluster.id` | `fmHaClusterId` | `FM.9.1.2.0` | |
| `fm.ha.peer.number` | `fmHaPeerNumber` | `FM.9.1.3.0` | standalone = 0 |
| `fm.raid.level` | `fmRaidLevel` | `FM.7.1.1.0` | 0=unavailable (VMs) |
| `fm.raid.state` | `fmRaidState` | `FM.7.1.2.0` | 0 silent; 2 degraded; 3 failed; 6 rebuilding |
| `fm.raid.size` | `fmRaidSize` | `FM.7.1.3.0` | GB |
| `fm.raid.disk.number` | `fmRaidDiskNumber` | `FM.7.1.4.0` | |

## Discovery

| Rule key | Table | Walk | Filter |
|---|---|---|---|
| `net.if.discovery` | IF-MIB | ifName / ifType / ifAdminStatus / ifOperStatus / ifAlias | ethernet + admin-up; drop vlan/ssl/hamgmt/npu/disk |
| `fm.sensor.discovery` | `fmSensorTable` | `FM.8.2.1.{2,4,5}` | empty → `[]` on VMs |
| `fm.raid.disk.discovery` | `fmRaidDiskTable` | `FM.7.2.1.{2,3}` | unused/spare/unavailable not alerted |
| `fm.ha.peer.discovery` | `fmHaPeerTable` | `FM.9.2.1.{2,3,5,6}` | peer-down gated `{$FM.HA.CONTROL}` |
| `fm.disk.discovery` | `fmSysDiskTable` | `FM.2.1.17.1.{2,3,4}` | per-volume usage/capacity/IO |
| `fm.adom.discovery` | `fmAdomTable` | `FM.5.2.1.{2,3,5}` | archive/analytics used % is FmTenths (×0.1) |
| `fm.device.discovery` | `fmDeviceTable` | `FM.6.2.1.{2,3,4,5,12,14}` | drop unregistered(0); connect 1=up 2=down |
| `fm.logfwd.discovery` | `fmSysLogForwardTable` | `FM.2.1.19.1.{2,3}` | empty when unused |

### Device / HA / RAID / sensor enums

| Object | Values used in triggers |
|---|---|
| `fmDeviceEntConnectState` | unknown(0) silent; up(1); down(2) Average |
| `fmDeviceEntConfigState` | in-sync(1); out-of-sync(2) trigger **DISABLED** |
| `fmDeviceEntMode` | unregistered(0) dropped; fmg(1) faz(2) fmg-faz(3) |
| `fmHaPeerEntState` | down(0) / negotiating(1) / synchronizing(2) / up(3) |
| `fmRaidState` | unavailable(0) silent; ok(1); degraded(2); failed(3); init(4); verify(5); rebuild(6) |
| `fmRaidDiskEntState` | unavailable(0)/unused(2)/spare(5) silent; failed(1) Average; ok(3); rebuilding(4) |
| `fmSensorEntState` | ok(0); failed(1)+input-lost(5) Average; out-of-range(2) Warning; critical(3)+not-recoverable(4) **High** on temp; not-present(6) silent |
| `fmSensorEntType` | Power(0) Fan(1) Temp(2) Voltage(3) — LLD `{#SENSOR_KIND}` |

## Test matrix

Every SNMP OID must pass `snmpget`/`snmpwalk` against a live FMG and FAZ
before the item is considered verified. VMs commonly omit RAID and sensors —
those walks must return not-supported (template maps that) not a red trigger.
