# NetBox → nbxSync → Zabbix architecture

How monitoring policy is derived from NetBox so new devices and VMs become Zabbix hosts without per-host hand configuration.

| Need | Document |
|---|---|
| Click-by-click nbxSync build (GUI / API) | [`nbxsync-configuration-checklist-zerotouch.md`](nbxsync-configuration-checklist-zerotouch.md) |
| Expected host matrix, day-2, scope gaps | Checklist §§13, 15, 17 |
| Extreme ports, stages, TEMP_*/optics | [`../zabbix/01-extreme-switching.md`](../zabbix/01-extreme-switching.md) |
| On-box port labels | [`../zabbix/port-identity.md`](../zabbix/port-identity.md) |
| Cutover order / other domains | [`../zabbix/00-monitoring-plan.md`](../zabbix/00-monitoring-plan.md), [`../zabbix/README.md`](../zabbix/README.md) |
| First-build helper scripts only | [`../scripts/README.md`](../scripts/README.md) |

Day-to-day changes are done in the **GUI or API**. Scripts are an optional onboarding accelerator, not the operating interface.

---

## Layers

| Layer | Role |
|---|---|
| **NetBox** | Inventory truth — site, role, platform, manufacturer, tags, primary IP / `oob_ip` |
| **nbxSync** | Policy bus — inheritance, configuration groups, Template Rules, hostgroups, macros |
| **Zabbix** | Receives hosts, interfaces, templates, hostgroups, macros from sync |

Operators encode policy once on NetBox objects. Sync pushes the effective result to Zabbix.

---

## Control plane (where policy hangs)

```
Country Site Group     →  proxy + default Agent :10050
                       →  Sites/… and Roles/… hostgroup templates
                       →  environment tag + host inventory mapping

Device Role            →  transport exceptions (SNMP / OOB / SPACE / SAP)
                       →  application templates
                       →  Extreme port-scoping macros (values in zabbix/01)

Platform (Template Rule) → OS / Extreme / Forti / storage template
                         → OS/… hostgroup membership

NetBox tags            →  overlays (critical, do_not_monitor)
                       →  snmp / oracle opt-ins
```

| NetBox fact | Configured as | Result in Zabbix |
|---|---|---|
| Country / site | Hostgroup on country Site Group | `Sites/<country>/…/<site>` |
| Role | Hostgroup on country Site Group | `Roles/<role name>` |
| Platform / OS | Template Rule (regex on platform name) | OS or platform template + `OS/…` |
| Default reachability | CG **Agent Monitoring** on country Site Group | Agent :10050 |
| Network gear | CG **SNMP Monitoring** on Switch*/AP/Firewall/… | SNMPv3 `MONITORING` MD5/DES |
| Linux/Windows SNMP opt-in | Tag `snmp` → CG **SNMP Monitoring (Linux)** | SNMPv3 `MONITORING-LINUX` SHA/AES |
| SAP SNMP | Roles **SAP HANA** / **SAP ME** → CG **SNMP Monitoring (SAP)** | SNMPv3 `SAPUSER` |
| Dell server BMC | CG **Server Agent+OOB** on role Server | Agent :10050 + `MONITORING-DELL` on `oob_ip` |
| Cohesity physical | CG **OOB SNMP Only** on role Cohesity | `MONITORING` on `oob_ip` only |
| Space Server | CG **Agent Monitoring (SPACE)** on role | Agent **:10060** |
| Criticality | Tag `critical` → hostgroup | `Priority/Critical` |

Hostgroup Jinja and assignment clicks: checklist §8.  
Which CG/template/interface a given host class should end up with: checklist §13.

---

## Rules of thumb

1. **One configuration group decides transport** (how we reach the host). Hostgroups and templates can stack; transport cannot.
2. **Different SNMPv3 users need different CGs** — never reuse the network CG for Linux, SAP, or iDRAC.
3. **Tags may select a CG** (`snmp`). SAP uses **role-based** CG assignment (SAP HANA, SAP ME), not tags. Host Interfaces sit on the CG — never directly on a tag.
4. **Country Site Group is the control plane** for proxy, default Agent, Sites/Roles hostgroups, environment tag, and inventory. Assign Agent Monitoring only on **country** Site Groups, not campus mid-levels.
5. **Hierarchy paths stay after Role/Platform** in plugin inheritance so a plugin upgrade does not change who already wins for existing installs.
6. **Templates merge** — Role + Platform + Manufacturer rules all accumulate. Colliding item keys (e.g. Network Generic + Extreme both defining `icmpping`) must be avoided by assignment design, not by hoping one replaces the other.

---

## What stays outside this integration

Things with no NetBox object to hang on (website checks, account-level APIs, …) and all **monitoring-domain** work (what to poll, thresholds, notifications) are out of scope here. See checklist §14 and the packs under [`../zabbix/`](../zabbix/README.md).

This page and the nbxSync checklist own **NetBox ↔ Zabbix integration** — host inventory, assignment rules, sync lifecycle — not the monitoring content that runs on those hosts.
