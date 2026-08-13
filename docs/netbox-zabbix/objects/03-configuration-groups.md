# Configuration groups

nbxSync models: `ZabbixConfigurationGroup`, `ZabbixHostInterface`, `ZabbixConfigurationGroupAssignment`  
NetBox: **Zabbix → Configuration groups** → open a group → **Host Interfaces** and **Assignments**  
(or Site Group / Device Role / Tag / Device → Zabbix tab)  
Zerotouch: steps 4, 5, 5b

## What this is

A configuration group (CG) is a **transport profile**: Agent and/or SNMP interface, port, SNMPv3 user. You define the interface **once on the group**. Sync copies the shape onto each member and fills IP from `primary_ip` (or `oob_ip` when Use OOB IP is Yes). Leave IP empty on the group definition.

**One CG wins per host.** Assignments can exist on Site Group, Role, Tag, Manufacturer, and Device; the plugin uses one CG to expand Host Interfaces (device beats inherited). Hostgroups and templates still stack.

Host Interfaces must sit on the **CG**, never on a Tag. Tags may *select* a CG (`snmp`).

Different SNMPv3 users = different CGs.

## Groups we have

| Name | Credential / port | Who it is for |
|---|---|---|
| Agent Monitoring | Agent :10050, TLS none | Default on every country Site Group |
| Agent Monitoring (SPACE) | Agent :10060, TLS none | Role Space Server (camLine uses 10050) |
| SNMP Monitoring | `MONITORING` MD5/DES | Switch*, AP, Firewall, Network Device, Virtual Appliance, Cohesity Appliance, Manufacturer Synology |
| SNMP Monitoring (by tag) | `MONITORING-LINUX` SHA1/AES128 | NetBox tag `snmp` |
| SNMP Monitoring (Huawei) | `LogicMonitor` SHA1/AES128 | Device `HU-DEB-SAN01` only |
| SAP Agent+SNMP | Agent :10050 **and** `SAPUSER` | Roles SAP HANA, SAP ME (one CG, two interfaces) |
| Dell iDRAC SNMP | `MONITORING-IDRAC` SHA384/AES256 @ oob | Role ESXi Hypervisor |
| Dell iDRAC SNMP (AES128) | `MONITORING-IDRAC` SHA384/AES128 @ oob | KR/CN exception Devices (list below) |
| Dell iDRAC SNMP (Legacy) | `MONITORING-IDRAC` SHA1/AES128 @ oob | Role Cohesity |

Retired (deleted by zerotouch): `Server Agent+OOB`, `ESXi OOB iDRAC`, `OOB SNMP Only`, `OOB SNMP v2c`, `Dell iDRAC HTTP`.

**Server** role stays on Site Group Agent Monitoring @ primary (real agent). iDRAC template for Dell servers comes from a Template Rule, not from an iDRAC CG.

## Host Interfaces (on the group)

**SNMP push community = True.** Passphrases are real values on the interface (env `NBX_SNMP_*`), not `{$SNMP_AUTHPASS}` placeholders. Sync writes secret host macros.

| CG | Type | Port | Use OOB IP | SNMPv3 |
|---|---|---|---|---|
| Agent Monitoring | Agent | 10050 | No | — |
| Agent Monitoring (SPACE) | Agent | 10060 | No | — |
| SNMP Monitoring | SNMP | 161 | No | MONITORING / MD5 / DES |
| SNMP Monitoring (by tag) | SNMP | 161 | No | MONITORING-LINUX / SHA1 / AES128 |
| SNMP Monitoring (Huawei) | SNMP | 161 | No | LogicMonitor / SHA1 / AES128 |
| SAP Agent+SNMP | Agent + SNMP | 10050 / 161 | No | SAPUSER (confirm auth/priv) |
| Dell iDRAC SNMP | SNMP | 161 | **Yes** | MONITORING-IDRAC / SHA384 / AES256 |
| Dell iDRAC SNMP (AES128) | SNMP | 161 | **Yes** | MONITORING-IDRAC / SHA384 / AES128 |
| Dell iDRAC SNMP (Legacy) | SNMP | 161 | **Yes** | MONITORING-IDRAC / SHA1 / AES128 |

SAP must be **one** CG with both interfaces. Two CGs on the same role would not dual-plane.

Env: `NBX_SNMP_AUTHPASS_MON` / `PRIVPASS_MON`, `_LINUX`, `_SAP`, `_IDRAC`, `_HUAWEI`. Huawei passphrases are only written when set (re-run does not blank them).

iDRAC user `MONITORING-IDRAC` must also exist on each iDRAC (UI or racadm).

## Assignments

### Agent Monitoring → country Site Groups

CH, HU, JP, KR, NL, US, CN.

Pure Storage and Dell Storage stay on this default (HTTP templates). Do not assign Agent Monitoring on SAP roles (they use SAP Agent+SNMP instead).

### SNMP Monitoring → roles and Synology

| Assigned to |
|---|
| Switch Core / Dist / Access / Mgmt / Hybrid |
| Access Point |
| Firewall |
| Network Device |
| Virtual Appliance |
| Cohesity Appliance (VMs) |
| Manufacturer **Synology** |

Do **not** assign this on role Storage (Pure/Dell would get the wrong SNMP user). Do **not** assign it on Manufacturer Huawei.

### Other CGs

| CG | Assigned to |
|---|---|
| Agent Monitoring (SPACE) | Role Space Server |
| SAP Agent+SNMP | Roles SAP HANA, SAP ME |
| SNMP Monitoring (by tag) | NetBox tag **snmp** (operator tags the Device/VM) |
| SNMP Monitoring (Huawei) | Device **HU-DEB-SAN01** |
| Dell iDRAC SNMP | Role ESXi Hypervisor |
| Dell iDRAC SNMP (Legacy) | Role Cohesity |
| Dell iDRAC SNMP (AES128) | Devices: `cn-sha-p-esx11/12/13`, `kr-sel-p-esx11/12/13` (.sensirion.lokal) |

AES128: device CG wins over role AES256. Do **not** leave durable per-device HostInterfaces on those hosts — CG propagate stamps `ip=primary`, which beats Use OOB IP at sync. Zerotouch prunes those device HIs.

Physical Cohesity = role Cohesity + Legacy iDRAC CG. Cohesity VMs = role Cohesity Appliance + SNMP Monitoring.
