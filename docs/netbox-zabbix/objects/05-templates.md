# Templates

nbxSync models: `ZabbixTemplate`, `ZabbixTemplateAssignment`  
NetBox: **Zabbix → Templates** → Assigned objects, or **Device Role → Zabbix tab**  
Zerotouch: step 7

## What this is

`ZabbixTemplate` is a pointer to a template that already exists in Zabbix (matched by name). `interface_requirements` (Agent / SNMP / ANY) must match the host’s transport or the template is **not** linked (silent).

`ZabbixTemplateAssignment` hangs the template on a NetBox object. Assignments **merge** with Template Rules. Visible on the Role (or Template) page — **not** on a Hostgroup page.

Do not assign Network Generic on Switch* or Access Point (platform rules already attach Extreme/Forti; both define `icmpping`).

Storage / iDRAC / OS templates are Template Rules, not role rows below.

## Role assignments

| Template | Assigned to | Notes |
|---|---|---|
| MSSQL by Zabbix agent 2 | MSSQL, MSSQL Query Server | |
| VMware FQDN | **vCenter only** | Not on ESXi. Secrets on each VM (macros article) |
| GitLab by HTTP | GitLab | |
| Linux by SNMP | Virtual Appliance | Baseline if no platform rule matches |
| Network Generic Device by SNMP | Network Device | Fallback only |
| Storage Generic Device by SNMP | Cohesity | Placeholder |
| FortiGate by SNMP | Firewall | Also FortiOS platform rule |
| Tableau Bridge by Zabbix agent `(stub)` | Tableau | Skipped if template absent |
| CellMap by Zabbix agent `(stub)` | CellMap | Soft-resolve |
| Oracle by Zabbix agent 2 `(stub)` | Database | Also tag `oracle` rule |
| SAP by Zabbix agent `(stub)` | SAP ME, SAP HANA | Soft-resolve |
| Acronis by Zabbix agent `(stub)` | Acronis Management | Soft-resolve |
| SCCM by Zabbix agent `(stub)` | SCCM | Soft-resolve |

One-off (e.g. AS Java): assign on the **Device**, not the role. Print Spool is not role-assigned today.

## Extreme extras (on the role, when staging says so)

Not on the platform Template Rule.

| Template | Assigned to |
|---|---|
| Extreme Port Speed Expect by SNMP | Switch Core / Dist / Access / Mgmt / Hybrid |
| Extreme Routing by SNMP | Switch Core, Switch Dist |

Port-label regexes and stage gates live with Extreme switching, not here.
