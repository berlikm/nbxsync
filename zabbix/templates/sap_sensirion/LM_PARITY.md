# SAP — what LogicMonitor actually monitored

Goal: **replicate what LM applied on each host**. Improve only where we
already have the Collection script. Do not invent Promonitor / `Z_*` /
`hdbsql`.

| Host | What LM actually applied | Zabbix (replicate / better) |
|---|---|---|
| `ch-sta-p-me05` (Windows ME) | OS + SSL + Ping + NoData. No SAP app DS | Windows by agent + ICMP + cert/port **50001**. sapcontrol + jstart are **better than LM**, not parity |
| `ch-sta-p-as02` / `ch-sta-d-as01` | Windows OS + jstart process DS | Same OS path + `proc.num[jstart.exe]` |
| `CH-STA-P-SH01` (openSUSE HANA) | Linux OS + Ping + Port + SSL + NoData + **`ABAPRuntimeErrorsCount_LMS`** | **UCD SNMP in this pack** (not Linux by agent) + cert/port **443** + **`Z_GET_ST22` count** |

ST22 “better”: LM also discovered every dump (user / program / time).
We keep the **count** (`sap.app.abap.errors`) and a threshold. That is
the same SOAP, less noise. Per-dump LLD is optional later — same
`ET_INFOTAB`, no new RFC.

The other `sap.app.*` names (IDoc, qRFC, jobs, …) stay sapcontrol CCMS
until someone exports those Collection scripts. On HANA-only and ME
Java they are 0. That is honest, not a hidden Promonitor clone.

There is **no item-level LM export** in this repo. Sources: the Aug 2026
account export in [`../../logicmonitor-assessment.md`](../../logicmonitor-assessment.md),
the operator datasource list (2026-09-05), and the SH01 walk in
[`../../notes/sap-snmp-walk.md`](../../notes/sap-snmp-walk.md).

## Application (Promonitor names, sapcontrol collection)

These were SAP-side datasources. `ABAPRuntimeErrorsCount_LMS` on SH01
exported as two scripts (2026-09-05):

1. **Do not port:** Groovy HMAC to `https://sensirion.logicmonitor.com/santaba/rest/alert/alerts`
   that counts LM alerts named “ABAP Runtime Errors”. That is LM-on-LM.
   The accessId / accessKey pasted with it are **live** — rotate them.
   They are not in this repo.
2. **Ported on Linux HANA only:** PowerShell “SAP Monitoring Interface”
   (`david.nussboeck@sensirion.com`). HTTPS SOAP `Z_GET_ST22`
   (`urn:sap-com:document:sap:rfc:functions`) to
   `https://ch-sta-p-sh01.sensirion.lokal:44301/abapruntimeerror`
   — LM `system.displayname` **is that openSUSE host**, not Windows ME.
   The script ran on an LM collector *against* SH01. Basic auth from
   **property keys** `sap.api.user` / `sap.api.pass` (`IV_TYPE=0`,
   count `ET_INFOTAB` rows with `PROGRAMNAME`). That is the only extra
   RFC. Do not invent other `Z_*` modules.

Zabbix: the **openSUSE agent on SH01** calls the same URL when
`{$SAP.API.HOST}`=`ch-sta-p-sh01.sensirion.lokal` and `{$SAP.API.USER}`
are set (`{$SAP.API.PASS}` = secret macro). Empty host keeps CCMS.
**SAP ME from Sensirion** does not carry these macros. sapcontrol
does not use this account. Do not paste passwords into git.

| LM datasource | Item key | Kind | What sapcontrol actually is |
|---|---|---|---|
| SAP / Promonitor (`C_PROMONITOR`, 11 hosts) | `sap.app.promonitor` | heartbeat | 1 when sapcontrol answers |
| Application Server Instance Status | `sap.app.instance.status` | 1=up / 0=down | `GetProcessList` (HANA hdb* / ABAP disp+work / ME jstart) |
| ABAP Runtime Errors (`ABAPRuntimeErrorsCount_LMS` on SH01) | `sap.app.abap.errors` | count | `Z_GET_ST22` when API macros are set; else CCMS. ICF may be missing on HANA-only |
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

**SAP HANA** (openSUSE) OS is **this pack’s SNMP** (`SAPUSER` UCD / IF-MIB /
HOST-RESOURCES from the SH01 probe). There is no official openSUSE template.
Stock **Linux by SNMP** is the generic Net-SNMP pack — do not link it (duplicate
OIDs). **Linux by Zabbix agent** is excluded for role SAP HANA: the appliance
may not take an agent. **SAP ME** (Windows) stays on **Windows by Zabbix
agent**. Both roles get **ICMP Ping** from CG SAP Agent+SNMP. The ME template
does not poll Linux OIDs.

| LM datasource | Where it lives | Notes |
|---|---|---|
| CPU Cores | omitted on HANA until an agent exists | Do not invent `hrDeviceProcessor` |
| CPU Overview | `sap.host.cpu.util` (UCD `ssCpuIdle`) | Host CPU, not ST06 |
| Disks | omitted on HANA (disk IO needs an agent) | This pack does filesystems (space), not disk IO |
| Filesystems | `sap.host.vfs.fs.*` (hrStorageFixedDisk) | |
| Host Status | `zabbix[host,snmp,available]` | SNMP plane only. `{$UNSUPPORTED.CONTROL}=0` so missing agent items do not ticket |
| Interfaces (64 bit) | `sap.host.net.if.in/out[ifHC*]` | ifXTable 64-bit counters |
| Memory Usage | `sap.host.memory.*` / `sap.host.swap.*` | UCD; not HANA allocation |
| Network Interfaces | same IF-MIB LLD + oper-status / errors | Drops `lo` |
| NoDataMonitoring | unsupported-item count (gated) + sapcontrol heartbeat | LM vehicle was collector `!tlist` (see Groovy below). Not SAP SM37 |
| Ping | SAP Agent+SNMP CG `icmpping` | **Not** nested here |
| Port | `net.tcp.service[tcp,,{$SAP.PORT.TCP}]` SIMPLE | HANA default 443; ME default **50001** (LM `ssl.ports` on `ch-sta-p-me05`). `{$SAP.PORT.CONTROL}=0` |
| SSL Certificate Expiration | Zabbix agent `web.certificate.get` | Optional. Needs an agent. `{$SAP.CERT.CONTROL}=0` |
| System Level IP Stats | omitted on HANA until an agent exists | Not duplicated |
| TCP UDP stats | omitted on HANA until an agent exists | Not duplicated |

`WinProcessStats_jstart` on ch-sta-p-as02 / ch-sta-d-as01 **is SAP ME**
(Windows AS Java). It lives on **SAP ME from Sensirion** as
`proc.num[jstart.exe]`. Do not put it on openSUSE HANA.
`ch-sta-p-me05` does **not** have that datasource in LM.

LM Manage Resource `ch-sta-p-me05.sensirion.lokal` (2026-09-05) is the
**host card**, not the Groovy. Facts taken from it:

| Field | Value | What we do with it |
|---|---|---|
| Collector Group | CH (Auto Balanced Group - windows) | Confirms Windows ME |
| Preferred Collector | `CH-STA-P-LMCO02` | Windows LM collector. Zabbix replacement is the host agent, not that collector |
| `system.categories` | `SAP,PCoIP` | SAP role only. PCoIP is Horizon/Teradici — not a SAP KPI |
| `ssl.ports` | `50001,50014,51014` | ME `{$SAP.CERT.PORT}` / `{$SAP.PORT.TCP}` default **50001** (AS Java HTTPS). 50014 / 51014 are sapstartsrv HTTPS (instances 00 and 10) — override per host; do not ticket instance 10 on every ME box |
| Properties | no `C_PROMONITOR` | That user is not on this host. Do not hunt a SAP Collection script on me05 |

### me05 Alerting tree (2026-09-05) — no SAP application datasources

This is the whole applied pack. There is nothing named Promonitor, ABAP,
IDoc, Instance Status, or `WinProcessStats_jstart`.

| LM datasource | Zabbix | Notes |
|---|---|---|
| CPU / CPU Cores | Windows by agent | Do not duplicate on the ME pack |
| Disks | Windows by agent | |
| Memory and Processes / Memory Stats | Windows by agent | |
| Interfaces | Windows by agent | No UCD / IF-MIB on ME |
| TCP stats / UDP stats | Windows by agent | |
| Host Status | Agent availability | |
| Ping | SAP Agent+SNMP CG `icmpping` | Not nested |
| SSL Certificate Expiration | `web.certificate.get` | `ssl.ports` 50001 / 50014 / 51014 |
| NoDataMonitoring | unsupported items + sapcontrol heartbeat | The `!tlist` Groovy |
| Time Offset | Windows by agent `system.localtime` | Listed twice in the UI |
| DotNet | — | Not a SAP KPI. Do not add here |
| File Server | — | Not a SAP KPI. Do not add here |
| Terminal Services | — | Matches `PCoIP` / RDP. Not a SAP KPI |
| Microsoft_Defender_for_Endpoint_2019 | — | Estate Defender gap, not this pack |

ssl.ports still prove sapstartsrv is on the box (instances 00 and 10).
sapcontrol + `proc.num[jstart.exe]` on the ME template are **additive**
for me05, not LM parity. If a Windows ME Collection script still exists,
it is on **as02 / as01**, not SH01 (Linux HANA) and not this tree.

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

## LM Groovy seen 2026-09-05 — collector `!tlist`, not SAP

Two operator pastes from the same LogicModule pair. Neither is Promonitor,
RFC, sapcontrol, or SM37.

**Active Discovery** — expands `auto.taskTypesList` (comma-separated,
written by a PropertySource) as `name##name`. The AD script imports
`com.santaba.agent.debugger.TlistTask` and does not call it (the comment
says `TlistTask` does not work in AD).

**Collection** — LM collector debugger, not the SAP host:

```
!tlist h=<system.hostname> summary=true
!tlist h=<system.hostname> status=NaN summary=true
```

via `new TlistTask(...)`. Parsed lines are
`sourceType sourceCollector count`. Instance key is
`sourceType_sourceCollector`. Metrics: `taskCount`, `taskNoData`.
Types missing from `!tlist` but still in `auto.taskTypesList` are
forced to 0 so they do not inflate NaN / NoData.

`com.santaba.agent` is LogicMonitor (Santaba). `!tlist` lists **collector
poll tasks** for that resource (groovy / snmp / webpage / …), and how
many returned NaN. It is NoDataMonitoring / “all tasks”, not ABAP
jobs.

Do not clone `TlistTask` / `!tlist` onto the Zabbix proxy. There is no
LM collector in the Zabbix path. The equivalent is already
`zabbix[host,,items_unsupported]` + `sap.app.promonitor` nodata.

Do not open another datasource on **me05** looking for Promonitor — it
is not in that tree.

### Where to open the SAP Collection script

Do not mix OS. **SH01 is Linux SAP HANA. SAP ME is Windows.** A script
from SH01 is the wrong collector and the wrong pack for me05 / as02.

**Windows SAP ME** (this hunt — same collector family as me05,
`CH-STA-P-LMCO02`):

1. Leave `ch-sta-p-me05` (Windows + SSL + NoData only).
2. Open **ch-sta-p-as02** or **ch-sta-d-as01** (jstart DS in the Aug
   2026 export).
3. Skip any other Windows SAP box whose Alerting tree looks like me05.

**Linux SAP HANA** (SH01 Alerting tree, 2026-09-05):

The only SAP application row is **`ABAPRuntimeErrorsCount_LMS`**.
Everything else is Linux OS + Ping + Port + SSL + NoData
(`CPU Cores`, `CPU Overview`, `Disks`, `Filesystems`, `Host Status`,
`Interfaces (64 bit)`, `Memory Usage`, `Monitored Processes`,
`Network Interfaces`, `NoDataMonitoring`, `Ping`, `Port`,
`SSL Certificate Expiration`, `System Level IP Stats`, `TCP UDP stats`).

Open **`ABAPRuntimeErrorsCount_LMS` → Manage → Collection** is done.
The PowerShell SOAP is ported. The Groovy LM-alert counter is not.
Do not apply `Z_GET_ST22` to Windows ME unless that host has
`:44301/abapruntimeerror`.

On the Windows ME host, from the **Alerting / datasource tree** (not
Manage Resource properties):

1. Open a row whose **name** is Promonitor, Application Server Instance
   Status, ABAP, IDoc, qRFC, Job Alerts, or similar.
2. Manage / Open DataSource → **Collection** (the poll script).
   Active Discovery is a different tab — that is how we got `!tlist`.
3. If the tree has no such row, **Settings → LogicModules →
   DataSources** (and PropertySources). Search SAP / ABAP / Promonitor /
   IDoc. Try **My Modules** and **Exchange**. If that menu is missing,
   the LM user cannot see modules — someone with Manage must export.

You have the right script when it talks to SAP (RFC / JCo / sapcontrol /
a Promonitor URL / ST22 / IDoc). You have the wrong one when you see
`TlistTask`, `!tlist`, `auto.taskTypesList`, `taskCount`, or
`taskNoData`.

Safe to send: DataSource name, Collection method, AppliesTo, script with
secrets stripped (keep URLs, RFC names, sapcontrol, ports), last collect
time, property **keys** only. Do not paste passwords.

## What we still do not have

- Other SAP RFC contracts (IDoc / qRFC / SM13 / SM37 / …). Only
  `Z_GET_ST22` was exported. Do not invent sibling `Z_*` modules
- A host list beyond “11 SAP hosts” + HANA canary `CH-STA-P-SH01` + ME
  `ch-sta-p-as02` / `ch-sta-d-as01` / `ch-sta-p-me05`
- SAP enterprise SNMP — probe found none
- Whether SH01 actually serves `:44301/abapruntimeerror` (HANA-only
  boxes often do not; then ST22 stays unused and CCMS stays 0)
- me05 has no SAP application DS (`!tlist` is NoDataMonitoring)

Do not treat UCD CPU/memory as HANA or ABAP health.
