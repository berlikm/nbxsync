# SAP — what LogicMonitor actually monitored

There is **no item-level LM export** in this repo. Sources: the Aug 2026
account export in [`../../logicmonitor-assessment.md`](../../logicmonitor-assessment.md),
the operator datasource list (2026-09-05), and the SH01 walk in
[`../../notes/sap-snmp-walk.md`](../../notes/sap-snmp-walk.md).

## Application (Promonitor / DNUS)

These were SAP-side datasources. They are **trappers** until Robert/DNUS
pushes `zabbix_sender`. `{$SAP.APP.CONTROL}=0` so empty keys do not page.

| LM datasource | Item key | Kind |
|---|---|---|
| SAP / Promonitor (`C_PROMONITOR`, 11 hosts) | `sap.app.promonitor` | heartbeat (nodata) |
| Application Server Instance Status | `sap.app.instance.status` | 1=up / 0=down |
| ABAP Runtime Errors | `sap.app.abap.errors` | count |
| IDoc Errors | `sap.app.idoc.errors` | count |
| Job Alerts | `sap.app.job.alerts` | count |
| Lock Entries | `sap.app.locks` | count |
| qRFC Monitor Inbound Queue | `sap.app.qrfc.in` | count |
| qRFC Monitor Outbound Queue | `sap.app.qrfc.out` | count |
| RFC Status | `sap.app.rfc.status` | 1=up / 0=down |
| Spool Errors | `sap.app.spool.errors` | count |
| Syslog | `sap.app.syslog.alerts` | count |
| Transactional RFC | `sap.app.trfc.errors` | count |
| Update Requests | `sap.app.update.requests` | count |

Do not invent a Promonitor API. Output format is still unknown.

## Host / OS

SAP hosts already get **Linux by Zabbix agent** (platform rule) and **ICMP
Ping** (SAP Agent+SNMP CG). This template adds the LM `SAPUSER` SNMP plane
plus the certificate/port extras that stock Linux-by-agent does not have.

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
| NoDataMonitoring | unsupported-item count + Promonitor nodata | |
| Ping | SAP Agent+SNMP CG `icmpping` | **Not** nested here |
| Port | `net.tcp.service[tcp,,{$SAP.PORT.TCP}]` SIMPLE | Default 443; `{$SAP.PORT.CONTROL}=0` |
| SSL Certificate Expiration | Zabbix agent `web.certificate.get` | See below |
| System Level IP Stats | Linux by agent | Not duplicated |
| TCP UDP stats | Linux by agent | Not duplicated |

`WinProcessStats_jstart` on ch-sta-p-as02 / ch-sta-d-as01 is the **AS Java**
stub, not this HANA / ME pack.

## SSL certificate — Zabbix agent, not Promonitor

SAP Agent+SNMP already has Agent :10050. Use the agent on the box
(`web.certificate.get`), not the proxy `tls_certificate_expiry.sh` script
(that is for agentless XIQ-SE / ExtremeControl).

1. Set host macro `{$SAP.CERT.HOST}` to the ICM / HTTPS name (and
   `{$SAP.CERT.SNI}` if different).
2. Confirm `{$SAP.CERT.PORT}` (default 443).
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
| `DataSource_script.groovy` | Groovy script from the collector | Promonitor/DNUS vehicle. Values land on the **trappers** above |
| `DataSource_batchscript.groovy` | Groovy batch (multi-instance) | Same DNUS/trapper path. Do not add `system.run` |
| `DataSource_script.others` | Other collector scripts | Same. Output format still unknown |
| `DataSource_batchscript.powershell` | PowerShell batch | Windows **collector** capability. SH01 is Linux Net-SNMP; not a SAP HANA/ME item |
| `DataSource_webpage` | Collector HTTP GET | Estate website checks are still a gap (`logicmonitor-assessment.md` §4). SAP ICM reachability is the agent cert + SIMPLE port, not a invented URL |
| `DataSource_dns` | Collector DNS lookup | Collector self-test. Not a SAP application metric. Linux/resolver stays on the OS agent if needed |

So: ping + SNMPv3 are live on the dual-plane CG. Groovy/batch scripts **are**
the missing DNUS contract (`{$SAP.APP.CONTROL}=0`). Webpage/DNS are not SAP
KPIs and are not added here.

## What we still do not have

- Promonitor / DNUS script output format
- Least-privilege SAP account beyond the name `C_PROMONITOR`
- A host list beyond “11 SAP hosts” + canary `CH-STA-P-SH01`
- SAP enterprise SNMP — probe found none
- Which TCP port LM “Port” actually used (default 443 next to the cert)

Do not treat UCD CPU/memory as HANA or ABAP health.
