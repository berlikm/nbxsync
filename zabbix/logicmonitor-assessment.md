# LogicMonitor → Zabbix migration assessment

Status: updated (Aug 2026)
Source: LM account export (Aug 2026) + Zabbix 7.0 nbxsync stack (dev-verified)
Note: Sync counts (§6) reflect dev-environment verification. Prod has 553 objects carrying onboarding tag; prod counts will be higher once onboarding waves complete.

## 1. SNMP monitoring accounts

| LM credential | Auth/Priv | Scope | Zabbix equivalent | Status |
|---|---|---|---|---|
| `MONITORING` (global) | MD5/DES | Switches, APs, firewalls, network | `SNMP Monitoring` CG → MONITORING/MD5/DES | ✅ Covered |
| `MONITORING-LINUX` (group override) | SHA/AES | Linux servers (SNMP) | `SNMP Monitoring (Linux)` CG → MONITORING-LINUX/SHA/AES | ✅ CG built (hosts need tag `snmp`) |
| `SAPUSER` (group override) | MD5/DES | SAP systems | CG **SAP Agent+SNMP** on SAP HANA / SAP ME. Host SNMP items are **HANA/openSUSE only** (SH01 probe). ME is Windows — no UCD | ⚠️ HANA transport validated; ME Windows SNMP not walked — [probe](notes/sap-snmp-walk.md), [sapcontrol](templates/sap_sensirion/SAPCONTROL.md) |
| `MONITORING-DELL` (resource override) | SHA/AES | CN-SHA-P-STOD (Dell storage) | HPE MSA 2060 Storage by HTTP template (REST API, not SNMP); Device Type macros `{$HPE.MSA.API.HOST/USERNAME/PASSWORD}` (§11.3) | ✅ Covered |
| `LogicMonitor` (resource override) | SHA/AES | hu-deb-san01 (Huawei storage) | Huawei OceanStor Dorado by SNMP on `SNMP Monitoring (Huawei)` CG with LogicMonitor SHA/AES on CG Host Interface (§5.6b) | ✅ Covered |
| v2c community (resource override) | — | CH-STA-P-ENSA01 | `snmp_v2_if()` helper exists in zerotouch (SNMPv2 + `snmp_community`/`snmp_pushcommunity`); unused since ESXi iDRACs moved to SNMPv3. Not a model gap — just not configured. | ⚠️ Not configured (not a gap) |

## 2. Non-SNMP monitoring

| LM protocol | Scope | Zabbix equivalent | Status |
|---|---|---|---|
| **WMI** (global `CH-UPA-Monitor`) | Windows servers | `Windows by Zabbix agent` (agent, not WMI) | ✅ Covered (agent replaces WMI) |
| **WMI** (DC override `CORP-UPA-Dom_Monitor`) | Domain Controllers | Agent — DCs get Windows by agent via platform rule | ✅ Covered |
| **JDBC Oracle** (`C##logicmonitor`) | Oracle DBs | Not yet — Oracle by ODBC needed | ❌ Gap |
| **ESX/vCenter** (`LogicMonitor` SSO) | 4 vCenters (per-site SSO) | `VMware FQDN` template + per-vCenter `{$VMWARE.USERNAME}`/`{$VMWARE.PASSWORD}`/`{$VMWARE.URL}` macros (old `{$VMWARE.USER}` pruned) | ✅ Covered (per-vCenter macros via §11.4) |
| **Horizon View** (`CH-UPA-Monitor`) | VDI | Not yet — Zabbix doesn't have Horizon template | ❌ Gap (post-cutover) |

## 3. API / token monitoring

| LM API | Scope | Zabbix equivalent | Status |
|---|---|---|---|
| **Pure Storage** (per-array token) | 7 SAN arrays | `Pure Storage FlashArray v2 by HTTP` via manufacturer TemplateRule; per-array `{$PURE.FLASHARRAY.API.TOKEN}` + `{$PURE.FLASHARRAY.API.URL}` macros (old `{$PURESTORAGE.TOKEN}` pruned) | ✅ Covered (per-array macros via §11.4) |
| **SAP** (`C_PROMONITOR`) | 11 SAP hosts | Agent sapcontrol → `sap.app.promonitor` on **SAP template from Sensirion**; install Host Agent UserParameter | ⚠️ Template built; UserParameter not pushed |
| **CATO SD-WAN** (account 964) | Cato sockets | `Cato Networks by HTTP` account collector plus 21 NetBox-backed Socket ICMP hosts | ✅ Live — collector and 21/21 Socket ICMP hosts |

## 4. Website monitoring (webcheck)

| LM check | Zabbix equivalent | Status |
|---|---|---|
| JIRA, Confluence, Sensinet, Sensinet 2.0 | Zabbix web scenarios | ❌ Not built (11 checks to recreate) |
| Space Server (CH test/prod, HU test/prod) | Zabbix web scenarios | ❌ Not built |
| Libellus, Nubo Sphere, Nubo Sensor API (external) | Zabbix web scenarios | ❌ Not built |

## 5. Custom datasources (LM-specific)

| LM custom datasource | Scope | Zabbix equivalent | Status |
|---|---|---|---|
| SAP ABAP / instance / IDoc / jobs / locks / qRFC in+out / RFC / spool / syslog / tRFC / updates | Promonitor / `C_PROMONITOR` (11 hosts; SH01 custom DS) | sapcontrol dependents on **SAP template from Sensirion** (Host Agent). `{$SAP.APP.CONTROL}=0` until the UserParameter is installed | ⚠️ Template built; install UserParameter on the host |
| SSL Certificate Expiration + Port | SAP hosts | Agent `web.certificate.get` + SIMPLE TCP; HANA 443 / ME **50001** from me05 `ssl.ports`; `{$SAP.CERT.CONTROL}` / `{$SAP.PORT.CONTROL}=0` until the ICM name is set | ⚠️ Built; host macros pending |
| Ungrouped `DataSource_*` (ping, snmp.v3, groovy/batch, powershell, webpage, dns) | LM **collector methods**, not SAP KPIs | Ping + SNMPv3 = SAP CG. Groovy/batch retired; local sapcontrol replaces it. Do not import Groovy/PowerShell. Webpage/DNS are collector self-tests / estate webchecks (§4) | ⚠️ Documented — [LM parity](templates/sap_sensirion/LM_PARITY.md) |
| WinProcessStats_jstart (AS Java) | ch-sta-p-as02, ch-sta-d-as01, ch-sta-p-me05 | **SAP ME** Windows `proc.num[jstart.exe]` on **SAP ME from Sensirion** | ⚠️ Template built; install PowerShell UserParameter |
| tableauBridgeWorker_service | 15 Tableau servers | Agent service check | ❌ Not built |
| WinProcessStats_cellmap | ch-sta-p-cmap03 | Agent process monitoring | ❌ Not built |
| Reporting Service QUEUE | MSSQL servers | MSSQL by Zabbix agent 2 | ⚠️ Template linked, queue item not built |
| Azure Application Insights | (disabled in LM) | — | N/A |

## 6. SNMP traps (event sources)

| LM trap event | Scope | Zabbix equivalent | Status |
|---|---|---|---|
| SNMP Receive - Netsight | CH-STA-P-ENSA01 | Zabbix SNMP trapper | ❌ Not configured |
| SNMP Receive - Huawei E9000 | CH-ZRH-ZH4/ZH5 (hosts not in system) | — | N/A (hosts gone) |
| Windows Firewall Drops | (disabled) | — | N/A |

## 7. ConfigSources

All 38 ConfigSources in LM are standard Exchange content. Zabbix doesn't have a direct equivalent — configuration monitoring is handled by cfgit (NetBox) or Zabbix agent items.

## Coverage summary

| Domain | LM items | Zabbix covered | Gap | Notes |
|---|---|---|---|---|
| Switch/AP/Firewall SNMP | ~568 devices | ✅ 568 synced | 0 | Templates: EXOS, VOSS, IQ Engine, FortiGate |
| Windows servers (agent/WMI) | ~100+ | ✅ 37+ synced | 0 | Windows by Zabbix agent replaces WMI |
| Linux servers (agent) | ~50+ | ✅ 9+ synced | 0 | Linux by Zabbix agent |
| VMware/vCenter | 4 vCenters + ESXi | ✅ 24 ESXi synced | 0 | `{$VMWARE.USERNAME}`/`{$VMWARE.PASSWORD}`/`{$VMWARE.URL}` per vCenter (§11.4) |
| MSSQL | ~30 | ✅ 2 synced (Agent 2) | 0 | `MSSQL by Zabbix agent 2` on MSSQL role |
| Pure Storage | 7 arrays | ✅ 7 synced | 0 | `Pure Storage FlashArray v2 by HTTP`; `{$PURE.FLASHARRAY.API.TOKEN}` + `{$PURE.FLASHARRAY.API.URL}` per array (§11.4) |
| Dell/Huawei storage | 2 devices | ✅ 2 synced | 0 | HPE MSA HTTP (Dell); Huawei OceanStor SNMP (Huawei CG) |
| SAP | 11 hosts | ⚠️ templates built; 0 synced | 11 application values | HANA openSUSE vs ME Windows (two YAMLs). UserParameter per OS, then HostSync SH01 — [sapcontrol](templates/sap_sensirion/SAPCONTROL.md) |
| CATO SD-WAN | (API) | ✅ collector live | 21/21 Socket ICMP | Cato by HTTP plus stock ICMP Ping on NetBox-backed Socket hosts |
| Website checks | 11 | ❌ | 11 | Zabbix web scenarios |
| Custom process/service checks | ~5 datasources | ❌ | 5 | Agent-based, post-cutover |
| Oracle JDBC | (unknown count) | ❌ | ? | Oracle by ODBC |
| Horizon/VDI | (global) | ❌ | 1 | Not in Zabbix |
| SNMP traps | 3 sources | ❌ | 1 active | Zabbix SNMP trapper needed |

## Cutover minimum (from 00-monitoring-plan.md)

| # | Capability | Status |
|---|---|---|
| 1 | Every switch is a Zabbix host with the right platform template | ✅ 568 network devices synced |
| 2 | Device reachable/not reachable (ICMP + SNMP availability) | ✅ icmpping + zabbix[host,snmp,available] |
| 3 | Device health: CPU, memory, temperature, PSU, fan | ✅ EXOS/VOSS/IQ Engine templates |
| 4 | Link down on ports we care about | ✅ IFALIAS macros on switch roles |
| 5 | Interface errors | ✅ IF-MIB in templates |
| 6 | Alerts reach a human (media, actions, escalation) | ❌ Not yet configured (Zabbix actions/mediatype needed) |
| 7 | Monitor-the-monitoring (unsupported items, proxy last-seen) | ❌ Not yet configured |

**Cutover blocker:** items 6 and 7 are not yet configured. Everything else (1-5) is verified working.
