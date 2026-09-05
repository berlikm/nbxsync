# SAP template from Sensirion — OID and trapper map

Canary: `CH-STA-P-SH01` / `10.0.105.112`, SNMPv3 `SAPUSER` authPriv MD5/DES,
2026-09-05. See [`../../notes/sap-snmp-walk.md`](../../notes/sap-snmp-walk.md).

## Host SNMP (live)

| Item key | Object | OID |
|---|---|---|
| `system.name` | sysName | `1.3.6.1.2.1.1.5.0` |
| `system.descr` | sysDescr | `1.3.6.1.2.1.1.1.0` |
| `system.objectid[sysObjectID.0]` | sysObjectID | `1.3.6.1.2.1.1.2.0` (Linux Net-SNMP `1.3.6.1.4.1.8072.3.2.10`) |
| `system.net.uptime[sysUpTime.0]` | sysUpTime | `1.3.6.1.2.1.1.3.0` ×0.01 |
| `sap.host.load[1m\|5m\|15m]` | laLoad | `1.3.6.1.4.1.2021.10.1.3.{1,2,3}` |
| `sap.host.cpu.idle` | ssCpuIdle | `1.3.6.1.4.1.2021.11.11.0` |
| `sap.host.memory.total` / `.avail` | memTotalReal / memAvailReal | `2021.4.5.0` / `2021.4.6.0` ×1024 |
| `sap.host.swap.total` / `.avail` | memTotalSwap / memAvailSwap | `2021.4.3.0` / `2021.4.4.0` ×1024 |
| `sap.host.processes` | hrSystemProcesses | `1.3.6.1.2.1.25.1.6.0` |
| `sap.host.net.if.*` | ifTable | `1.3.6.1.2.1.2.2.1.{8,10,14,16,20}.{#SNMPINDEX}` |
| `sap.host.vfs.fs.*` | hrStorage | `1.3.6.1.2.1.25.2.3.1.{3,5,6}` |

Do not walk `1.3.6.1.4.1` unbounded. Do not poll `1.3.6.1.4.1.2312`.

## Application trappers (LM / DNUS)

| Item key | LM row | How it gets data |
|---|---|---|
| `sap.app.promonitor` | API `C_PROMONITOR` (11 hosts) | `zabbix_sender` from DNUS |
| `sap.app.abap.errors` | custom DS ABAP runtime/errors on SH01 | same |
| `sap.app.idoc.errors` | IDoc | same |
| `sap.app.qrfc.errors` | qRFC | same |
| `sap.app.job.alerts` | job alerts | same |
| `sap.app.syslog.alerts` | syslog | same |

`{$SAP.APP.CONTROL}=0` until those scripts exist.
