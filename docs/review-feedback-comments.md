# Response to configuration review

Thank you for the feedback. Current decisions:

---

## Tenancy

Not now. NetBox tenancy is not defined for our processes, and Zabbix does not need it — location, function, OS, and criticality are already hostgroups.

---

## Continents / regional permissions

Not needed. Access is global (flat org). Country Site Groups already give nested `Sites/CH/…` for location dashboards and filters. No Regions or continent Site Groups.

---

## Site Groups

Keep as the control plane (proxy, server assignment, default Agent CG, Sites/Roles hostgroups, environment tag, inventory).

Sites hostgroup value uses full Site Group ancestry so country parents exist (`Sites/CH/CH-STA/…`). Hosts stay in the leaf; boards filter on the parent.

---

## Templates (Manufacturer vs Device type)

Templates **merge** by ID — Device type **adds**, it never replaces Manufacturer *(lab-verified)*. Put each template at the level that is generally true; Device only for true one-offs.

| Level | Use for |
|---|---|
| Device Role | Application / class baseline (MSSQL, switch floors, …) |
| Manufacturer | Vendor-wide templates that are safe for the whole vendor class |
| Device type | Model / OEM extras |
| Template Rule | Platform OS, and compound cases (e.g. Dell ∧ Server → iDRAC) |

**Dell iDRAC:** not on Manufacturer Dell (too wide — storage and other SNMP Dell hosts also got it). Configured as Template Rule: pattern `.*`, role `^Server$`, Manufacturer Dell → Dell iDRAC by SNMP. Transport stays Server Agent+OOB (`oob_ip`).

Interface requirements still drop a template when the host lacks Agent/SNMP/etc.; they do not separate two SNMP templates that both qualify.

---

## Zabbix server

Production: cert validation on, skip version check off, sync on.

---

## Proxies

Unchanged: CH proxy group; JP via KR; NL/US via CH group.

---

## Template Rules

Keep for platform → OS template + `OS/…`. Also used for SNMP-by-tag OS templates and Dell iDRAC (above). Multi-group membership is already the model.

---

## Tags

Keep lean — do not mirror hostgroup names as tags.

In use: NetBox `critical`, `snmp`, `do_not_monitor`; Zabbix `environment`, `cluster`. Add a tag only if a specific action/widget cannot use hostgroup filters.

---

## SNMP Linux / Windows CGs

No separate SNMP Linux/Windows configuration groups. One transport CG **SNMP by tag** + Template Rules gated by NetBox tag `snmp` (Device or VM).

---

## Hostgroups / dashboards / permissions

Axes: `Sites/…`, `Roles/…`, `OS/…`, optional `Priority/Critical`. Dashboards and permissions on **parents** cover nested children; hosts stay in the leaf. Zabbix permissions stay global — nested Sites are for location views, not regional RBAC.

---

## Summary

| Topic | Decision |
|---|---|
| Tenant | Not now |
| Continents / regional ACL | Not needed — access global |
| Site Groups | Country control plane; nested Sites for location |
| Templates | Merge only; Device type adds |
| iDRAC | Template Rule Dell ∧ Server (not Manufacturer-wide) |
| Certs / version check | On / off for production |
| Proxies | Keep current plan |
| Tags | Lean |
| SNMP override | SNMP by tag + tag `snmp` |
| Nested groups | Parent filter; hosts in leaf |
