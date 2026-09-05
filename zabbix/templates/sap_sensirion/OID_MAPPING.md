# SAP template from Sensirion — OID, agent, and sapcontrol map

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
| `sap.host.net.if.in/out` | ifXTable 64-bit | `1.3.6.1.2.1.31.1.1.1.{6,10}.{#SNMPINDEX}` |
| `sap.host.net.if.*.errors` | ifTable | `1.3.6.1.2.1.2.2.1.{14,20}.{#SNMPINDEX}` |
| `sap.host.vfs.fs.*` | hrStorage | `1.3.6.1.2.1.25.2.3.1.{3,5,6}` |

Do not walk `1.3.6.1.4.1` unbounded. Do not poll the SAP enterprise tree.

## Agent / SIMPLE (LM SSL + Port)

| Item key | LM row | How |
|---|---|---|
| `web.certificate.get[{$SAP.CERT.HOST},{$SAP.CERT.PORT},{$SAP.CERT.SNI}]` | SSL Certificate Expiration | Zabbix agent on the SAP host |
| `sap.host.cert.not_after` | same | JSONPath `$.x509.not_after` |
| `sap.host.cert.days` | same | calculated days remaining |
| `net.tcp.service[tcp,,{$SAP.PORT.TCP}]` | Port | SIMPLE from the assigned proxy |

`{$SAP.CERT.CONTROL}=0` and `{$SAP.PORT.CONTROL}=0` until the hostname / port
are confirmed. Empty cert host is `CHECK_NOT_SUPPORTED` → `{}`.

## Application (LM names, sapcontrol)

Master: `sap.sensirion[json,{$SAP.INSTANCE},{$SAP.SID},{$SAP.CONTROL.HOST}]`
(Zabbix agent UserParameter → `zabbix/externalscripts/sap_sensirion.py`).
See [`SAPCONTROL.md`](SAPCONTROL.md).

| Item key | LM row | JSONPath | How it gets data |
|---|---|---|---|
| `sap.app.promonitor` | SAP / API `C_PROMONITOR` (11 hosts) | `$.promonitor` | sapcontrol answers |
| `sap.app.instance.status` | Application Server Instance Status | `$.instance_status` | `GetProcessList` |
| `sap.app.abap.errors` | ABAP Runtime Errors | `$.abap_errors` | `GetAlerts` CCMS |
| `sap.app.idoc.errors` | IDoc Errors | `$.idoc_errors` | `GetAlerts` CCMS |
| `sap.app.job.alerts` | Job Alerts | `$.job_alerts` | `GetAlerts` CCMS |
| `sap.app.locks` | Lock Entries | `$.locks` | `GetAlerts` CCMS |
| `sap.app.qrfc.in` | qRFC Monitor Inbound Queue | `$.qrfc_in` | `GetAlerts` CCMS |
| `sap.app.qrfc.out` | qRFC Monitor Outbound Queue | `$.qrfc_out` | `GetAlerts` CCMS |
| `sap.app.rfc.status` | RFC Status | `$.rfc_status` | `gwrd`, or instance-up on HANA/Java |
| `sap.app.spool.errors` | Spool Errors | `$.spool_errors` | `GetAlerts` CCMS |
| `sap.app.syslog.alerts` | Syslog | `$.syslog_alerts` | `GetAlerts` CCMS |
| `sap.app.trfc.errors` | Transactional RFC | `$.trfc_errors` | `GetAlerts` CCMS |
| `sap.app.update.requests` | Update Requests | `$.update_requests` | `GetAlerts` CCMS |

`{$SAP.APP.CONTROL}=0` until the Host Agent UserParameter is installed.
