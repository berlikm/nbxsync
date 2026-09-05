# SAP — what LogicMonitor actually monitored

There is **no item-level LM export** in this repo. Sources: the Aug 2026
account export in [`../../logicmonitor-assessment.md`](../../logicmonitor-assessment.md),
the operator datasource list (2026-09-05), and the SH01 walk in
[`../../notes/sap-snmp-walk.md`](../../notes/sap-snmp-walk.md).

## Application (Promonitor names, sapcontrol collection)

These were SAP-side datasources. DNUS / `C_PROMONITOR` is gone. The same
names are now dependents of one Zabbix-agent sapcontrol snapshot (SAP Host
Agent / sapstartsrv — already on every HANA and ME host). See
[`SAPCONTROL.md`](SAPCONTROL.md). `{$SAP.APP.CONTROL}=0` until that
UserParameter is installed and Latest data is quiet.

| LM datasource | Item key | Kind | What sapcontrol actually is |
|---|---|---|---|
| SAP / Promonitor (`C_PROMONITOR`, 11 hosts) | `sap.app.promonitor` | heartbeat | 1 when sapcontrol answers |
| Application Server Instance Status | `sap.app.instance.status` | 1=up / 0=down | `GetProcessList` (HANA hdb* / ABAP disp+work / ME jstart) |
| ABAP Runtime Errors | `sap.app.abap.errors` | count | CCMS `GetAlerts` (Shortdumps), not ST22 RFC. 0 on HANA-only |
| IDoc Errors | `sap.app.idoc.errors` | count | CCMS, not EDIDS |
| Job Alerts | `sap.app.job.alerts` | count | CCMS, not SM37 |
| Lock Entries | `sap.app.locks` | count | CCMS / enqueue, not SM12 |
| qRFC Monitor Inbound Queue | `sap.app.qrfc.in` | count | CCMS, not SMQ2 |
| qRFC Monitor Outbound Queue | `sap.app.qrfc.out` | count | CCMS, not SMQ1 |
| RFC Status | `sap.app.rfc.status` | 1=up / 0=down | `gwrd` process. HANA/Java: 1 when the instance is up. Not SM59 |
| Spool Errors | `sap.app.spool.errors` | count | CCMS, not SP01 |
| Syslog | `sap.app.syslog.alerts` | count | CCMS, not SM21 |
| Transactional RFC | `sap.app.trfc.errors` | count | CCMS, not SM58 |
| Update Requests | `sap.app.update.requests` | count | CCMS, not SM13 |

Do not invent a Promonitor API. Do not add `hdbsql` until there is a HANA
SQL contract. Host RAM/CPU is not HANA allocation.

## Host / OS

**SAP HANA** (openSUSE) already gets **Linux by Zabbix agent**. **SAP ME**
(Windows) already gets **Windows by Zabbix agent**. Both get **ICMP Ping**
from CG SAP Agent+SNMP. Only the HANA template adds the LM `SAPUSER` UCD
SNMP plane (SH01 probe). The ME template does not poll Linux OIDs.

| LM datasource | Where it lives | Notes |
|---|---|---|
| CPU Cores | Linux by agent `system.cpu.num` | Do not duplicate that key here |
| CPU Overview | `sap.host.cpu.util` (UCD `ssCpuIdle`) + Linux by agent | Host CPU, not ST06 |
| Disks | Linux by agent disk IO | This pack does filesystems (space), not disk IO |
| Filesystems | `sap.host.vfs.fs.*` (hrStorageFixedDisk) | |
| Host Status | `zabbix[host,snmp,available]` + Linux agent availability | |
| Interfaces (64 bit) | `sap.host.net.if.in/out[ifHC*]` | ifXTable 64-bit counters |
| Memory Usage | `sap.host.memory.*` / `sap.host.swap.*` | UCD; not HANA allocation |
| Network Interfaces | same IF-MIB LLD + oper-status / errors | Drops `lo` |
| NoDataMonitoring | unsupported-item count + sapcontrol heartbeat | |
| Ping | SAP Agent+SNMP CG `icmpping` | **Not** nested here |
| Port | `net.tcp.service[tcp,,{$SAP.PORT.TCP}]` SIMPLE | HANA default 443; ME default **50001** (LM `ssl.ports` on `ch-sta-p-me05`). `{$SAP.PORT.CONTROL}=0` |
| SSL Certificate Expiration | Zabbix agent `web.certificate.get` | See below |
| System Level IP Stats | Linux by agent | Not duplicated |
| TCP UDP stats | Linux by agent | Not duplicated |

`WinProcessStats_jstart` on ch-sta-p-as02 / ch-sta-d-as01 / ch-sta-p-me05
**is SAP ME** (Windows AS Java). It lives on **SAP ME from Sensirion** as
`proc.num[jstart.exe]`. Do not put it on openSUSE HANA.

LM Manage Resource `ch-sta-p-me05.sensirion.lokal` (2026-09-05) is the
**host card**, not the Groovy. Facts taken from it:

| Field | Value | What we do with it |
|---|---|---|
| Collector Group | CH (Auto Balanced Group - windows) | Confirms Windows ME |
| Preferred Collector | `CH-STA-P-LMCO02` | Windows LM collector. Zabbix replacement is the host agent, not that collector |
| `system.categories` | `SAP,PCoIP` | SAP role only. PCoIP is Horizon/Teradici — not a SAP KPI |
| `ssl.ports` | `50001,50014,51014` | ME `{$SAP.CERT.PORT}` / `{$SAP.PORT.TCP}` default **50001** (AS Java HTTPS). 50014 / 51014 are sapstartsrv HTTPS (instances 00 and 10) — override per host; do not ticket instance 10 on every ME box |
| Properties | no `C_PROMONITOR` | That user is not on the host card. Open a live datasource → Collection for the script |

## SSL certificate — Zabbix agent, not Promonitor

SAP Agent+SNMP already has Agent :10050. Use the agent on the box
(`web.certificate.get`), not the proxy `tls_certificate_expiry.sh` script
(that is for agentless XIQ-SE / ExtremeControl).

1. Set host macro `{$SAP.CERT.HOST}` to the ICM / HTTPS name (and
   `{$SAP.CERT.SNI}` if different). ME example:
   `ch-sta-p-me05.sensirion.lokal`.
2. Confirm `{$SAP.CERT.PORT}` (HANA default 443; ME default **50001**).
3. Set `{$SAP.CERT.CONTROL}=1` when Latest data shows a real `not_after`.

Empty `{$SAP.CERT.HOST}` is caught with `CHECK_NOT_SUPPORTED` so it does not
trip “too many unsupported items”.

## LM collector methods (Ungrouped `DataSource_*`)

These are **how the LogicMonitor collector collected**, not extra SAP
counters. They show up Ungrouped with `true` because the collector could run
that method. Do not clone Groovy/PowerShell into Zabbix.

| LM collector DataSource | What it was | Zabbix |
|---|---|---|
| `DataSource_ping` | Collector ICMP | ICMP Ping on CG **SAP Agent+SNMP**. Not nested in this template |
| `DataSource_snmp.v3` | Collector SNMPv3 | `SAPUSER` MD5/DES on that CG + host SNMP items here |
| `DataSource_script.groovy` | Groovy script from the collector | Was the Promonitor/DNUS vehicle. Replaced by local sapcontrol |
| `DataSource_batchscript.groovy` | Groovy batch (multi-instance) | Same. `{$SAP.INSTANCE}` / ListInstances. Do not add agent remote commands |
| `DataSource_script.others` | Other collector scripts | Same sapcontrol path |
| `DataSource_batchscript.powershell` | PowerShell batch | Windows **SAP ME** vehicle. Replaced by `sap_sensirion.ps1` on the ME host. Not for openSUSE HANA |
| `DataSource_webpage` | Collector HTTP GET | Estate website checks are still a gap (`logicmonitor-assessment.md` §4). SAP ICM reachability is the agent cert + SIMPLE port, not a invented URL |
| `DataSource_dns` | Collector DNS lookup | Collector self-test. Not a SAP application metric. Linux/resolver stays on the OS agent if needed |

So: ping + SNMPv3 are live on the dual-plane CG. Groovy/batch is retired;
sapcontrol on the existing agent is the application path. Webpage/DNS are
not SAP KPIs and are not added here.

## What we still do not have

- A least-privilege SAP RFC / HANA SQL account (the name `C_PROMONITOR` is
  not a contract)
- A host list beyond “11 SAP hosts” + HANA canary `CH-STA-P-SH01` + ME
  `ch-sta-p-as02` / `ch-sta-d-as01` / `ch-sta-p-me05`
- SAP enterprise SNMP — probe found none
- The live LM Collection script (the me05 Manage Resource page is the
  host card; `C_PROMONITOR` is not a property there)
- ST22 / IDoc / qRFC / SM13 as RFC tables — CCMS only, 0 on HANA-only
  and typically on ME Java

Do not treat UCD CPU/memory as HANA or ABAP health.
