# LogicMonitor → Zabbix migration assessment

Status: draft  
Source: LM account export (Aug 2026) + Zabbix 7.0 nbxsync stack

## 1. SNMP monitoring accounts

| LM credential | Auth/Priv | Scope | Zabbix equivalent | Status |
|---|---|---|---|---|
| `MONITORING` (global) | MD5/DES | Switches, APs, firewalls, network | `SNMP Monitoring` CG → MONITORING/MD5/DES | ✅ Covered |
| `MONITORING-LINUX` (group override) | SHA/AES | Linux servers (SNMP) | `SNMP Monitoring (Linux)` CG → MONITORING-LINUX/SHA/AES | ✅ CG built (hosts need tag `snmp`) |
| `SAPUSER` (group override) | SHA/AES | SAP systems | CG **SAP Agent+SNMP** → Agent + SAPUSER/SHA/AES on roles SAP HANA / SAP ME | ✅ CG built (role-based; no `snmp-sap` tag) |
| `MONITORING-DELL` (resource override) | SHA/AES | CN-SHA-P-STOD (Dell storage) | Not yet — Dell storage needs HTTP template | ❌ Gap |
| `LogicMonitor` (resource override) | SHA/AES | hu-deb-san01 (Huawei storage) | Not yet — Huawei needs template | ❌ Gap |
| v2c community (resource override) | — | CH-STA-P-ENSA01 | v2c not in CG model | ❌ Gap (single device) |

## 2. Non-SNMP monitoring

| LM protocol | Scope | Zabbix equivalent | Status |
|---|---|---|---|
| **WMI** (global `CH-UPA-Monitor`) | Windows servers | `Windows by Zabbix agent` (agent, not WMI) | ✅ Covered (agent replaces WMI) |
| **WMI** (DC override `CORP-UPA-Dom_Monitor`) | Domain Controllers | Agent — DCs get Windows by agent via platform rule | ✅ Covered |
| **JDBC Oracle** (`C##logicmonitor`) | Oracle DBs | Not yet — Oracle by ODBC needed | ❌ Gap |
| **ESX/vCenter** (`LogicMonitor` SSO) | 4 vCenters (per-site SSO) | `VMware FQDN` template + per-vCenter `{$VMWARE.USER}`/`{$VMWARE.PASSWORD}` macros | ✅ Covered (host-level macros needed per vCenter) |
| **Horizon View** (`CH-UPA-Monitor`) | VDI | Not yet — Zabbix doesn't have Horizon template | ❌ Gap (post-cutover) |

## 3. API / token monitoring

| LM API | Scope | Zabbix equivalent | Status |
|---|---|---|---|
| **Pure Storage** (per-array token) | 7 SAN arrays | `Pure Storage FlashArray v1 by HTTP` via manufacturer TemplateRule | ✅ Covered (need per-array `{$PURESTORAGE.TOKEN}` macros) |
| **SAP** (`C_PROMONITOR`) | 11 SAP hosts | Not yet — SAP scripts from DNUS, integrated by Robert | ❌ Gap (post-cutover) |
| **CATO SD-WAN** (account 964) | Cato sockets | Not yet — Cato by HTTP template needed | ❌ Gap (post-cutover) |

## 4. Website monitoring (webcheck)

| LM check | Zabbix equivalent | Status |
|---|---|---|
| JIRA, Confluence, Sensinet, Sensinet 2.0 | Zabbix web scenarios | ❌ Not built (11 checks to recreate) |
| Space Server (CH test/prod, HU test/prod) | Zabbix web scenarios | ❌ Not built |
| Libellus, Nubo Sphere, Nubo Sensor API (external) | Zabbix web scenarios | ❌ Not built |

## 5. Custom datasources (LM-specific)

| LM custom datasource | Scope | Zabbix equivalent | Status |
|---|---|---|---|
| SAP ABAP runtime/errors, IDoc, qRFC, job alerts, syslog | ch-sta-p-sh01 | DNUS scripts → Robert integrates | ❌ Post-cutover |
| WinProcessStats_jstart (AS Java) | ch-sta-p-as02, ch-sta-d-as01 | Agent process monitoring | ❌ Not built |
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
| VMware/vCenter | 4 vCenters + ESXi | ✅ 24 ESXi synced | Per-vCenter macros needed | `{$VMWARE.USER}`/`{$VMWARE.PASSWORD}` per host |
| MSSQL | ~30 | ✅ 2 synced (Agent 2) | 0 | `MSSQL by Zabbix agent 2` on MSSQL role |
| Pure Storage | 7 arrays | ✅ 7 synced | Per-array token macros needed | `{$PURESTORAGE.TOKEN}` per host |
| Dell/Huawei storage | 2 devices | ❌ | 2 | Need HTTP/SNMP templates |
| SAP | 11 hosts | ❌ | 11 | DNUS scripts, post-cutover |
| CATO SD-WAN | (API) | ❌ | 1 | Cato by HTTP, post-cutover |
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
