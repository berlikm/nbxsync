# SAP HANA (openSUSE) + SAP ME (Windows) — OID, agent, and sapcontrol map

Canary: `CH-STA-P-SH01` / `10.0.105.112`, SNMPv3 `SAPUSER` authPriv MD5/DES,
2026-09-05. See [`../../notes/sap-snmp-walk.md`](../../notes/sap-snmp-walk.md).

Host SNMP is the **openSUSE HANA OS plane** (LM `SAPUSER`, not a host
agent). There is no official openSUSE template. Role SAP HANA links
stock **Linux by SNMP** for those OIDs. This YAML has **no** UCD / IF /
FS items (duplicate keys). Windows ME uses
[`template_sap_me_sensirion.yaml`](template_sap_me_sensirion.yaml) (agent
sapcontrol + `proc.num[jstart.exe]`, no UCD).

## Host SNMP (stock Linux by SNMP, HANA / openSUSE)

SH01 probe (2026-09-05) proved Linux Net-SNMP
`1.3.6.1.4.1.8072.3.2.10`. The official template already covers:

| LM title | Official Linux by SNMP |
|---|---|
| CPU / load / RAM / swap | UCD + HOST-RESOURCES |
| CPU Cores | `system.cpu.num[snmp]` / `hrProcessorTable` |
| Disks (IO) | UCD-DISKIO `vfs.dev.walk` |
| Filesystems | `vfs.fs.*` |
| Interfaces (64 bit) | IF-MIB / ifXTable |
| Ping | **Disabled** — ICMP stays on CG SAP Agent+SNMP |
| System Level IP Stats / TCP UDP stats | **Omitted** — no official SNMP overlay; add an agent later |

Do not walk `1.3.6.1.4.1` unbounded. Do not poll the SAP enterprise tree.
Do not invent IP-MIB / TCP-MIB / UDP-MIB items.

## Agent / SIMPLE (LM SSL + Port)

| Item key | LM row | How |
|---|---|---|
| `web.certificate.get[{$SAP.CERT.HOST},{$SAP.CERT.PORT},{$SAP.CERT.SNI}]` | SSL Certificate Expiration | Zabbix agent on the SAP host |
| `sap.host.cert.not_after` | same | JSONPath `$.x509.not_after` |
| `sap.host.cert.days` | same | calculated days remaining |
| `net.tcp.service[tcp,,{$SAP.PORT.TCP}]` | Port | SIMPLE from the assigned proxy |

`{$SAP.CERT.CONTROL}=0` and `{$SAP.PORT.CONTROL}=0` until the hostname / port
are confirmed. Empty cert host is `CHECK_NOT_SUPPORTED` → `{}`.

HANA TLS/TCP default is **443**. ME default is **50001** (LM `ssl.ports`
on `ch-sta-p-me05.sensirion.lokal`: 50001 / 50014 / 51014).

## Application (LM names, sapcontrol)

Master: `sap.sensirion[json,{$SAP.INSTANCE},{$SAP.SID},{$SAP.CONTROL.HOST}]`
(Zabbix agent UserParameter → `zabbix/externalscripts/sap_sensirion.py`).
See [`SAPCONTROL.md`](SAPCONTROL.md).

| Item key | LM row | JSONPath | How it gets data |
|---|---|---|---|
| `sap.app.promonitor` | SAP / API `C_PROMONITOR` (11 hosts) | `$.promonitor` | sapcontrol answers |
| `sap.app.instance.status` | Application Server Instance Status | `$.instance_status` | `GetProcessList` |
| `sap.app.abap.errors` | ABAP Runtime Errors (`ABAPRuntimeErrorsCount_LMS`) | `$.abap_errors` | `Z_GET_ST22` when API macros are set on **CH-STA-P-SH01**; else `GetAlerts` CCMS |
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
