# Architecture

How nbxSync policy hangs off **existing** NetBox inventory so devices and VMs become Zabbix hosts without per-host hand configuration.

**Folder map:** [`README.md`](README.md)

**Assumption:** sites, roles, platforms, IPs, `oob_ip`, and tags are already in NetBox. This page does not describe how to populate NetBox.

| Need | Document |
|---|---|
| nbxSync GUI / API rows | [`configuration.md`](configuration.md) |
| Expected host matrix | [`configuration.md`](configuration.md) §13 |
| Day-2 procedures | [`runbooks/day2.md`](runbooks/day2.md) |
| Phased onboarding | [`runbooks/onboarding.md`](runbooks/onboarding.md) |
| Monitoring domains | [`../../zabbix/`](../../zabbix/README.md) |
| First-build scripts | [`../../scripts/README.md`](../../scripts/README.md) |

Day-to-day nbxSync changes are done in the **GUI or API**. Scripts are an optional onboarding accelerator, not the operating interface.

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

Platform (Template Rule) → OS / Extreme / Forti / storage template
                         → Dell ∧ Server|Cohesity|ESXi Hypervisor → PowerEdge HTTP + OS/VMware (ESXi)
                         → OS/… hostgroup membership

Device Role            →  transport exceptions (SNMP / SPACE / SAP)
                       →  Redfish macros `{$DELL.HTTP.API.*}` on Server / ESXi Hypervisor / Cohesity
                       →  application templates (incl. VMware FQDN on vCenter only)
                       →  Extreme port-scoping macros (values in zabbix/01)

NetBox tags            →  overlays (`critical`) + opt-ins (`snmp`, `oracle`) + exclude hold (`onboarding`)
Zabbix tag assignment  →  `do_not_monitor` on role (permanent) or on NetBox Tag `onboarding` (waves)
```

| NetBox fact | Configured as | Result in Zabbix |
|---|---|---|
| Country / site | Hostgroup on country Site Group | `Sites/<country>/…/<site>` |
| Role | Hostgroup on country Site Group | `Roles/<role name>` |
| Platform / OS | Template Rule (regex on platform name) | OS or platform template + `OS/…` |
| Default reachability | CG **Agent Monitoring** on country Site Group | Agent :10050 |
| Network gear | CG **SNMP Monitoring** on Switch*/AP/Firewall/… | SNMPv3 `MONITORING` MD5/DES |
| Linux/Windows SNMP opt-in | Tag `snmp` → CG **SNMP Monitoring (by tag)** | SNMPv3 `MONITORING-LINUX` SHA/AES |
| SAP dual-plane | Roles **SAP HANA** / **SAP ME** → CG **SAP Agent+SNMP** | Agent :10050 + SNMPv3 `SAPUSER` (one CG) |
| Dell PowerEdge iDRAC (Redfish) | CG **Dell iDRAC HTTP** (Agent) on Server / ESXi Hypervisor / Cohesity + TemplateRule Dell ∧ role | Agent :10050; Redfish macros on those **Device Roles** |
| ESXi hypervisor (Dell) | Role **ESXi Hypervisor** + Dell iDRAC HTTP | PowerEdge HTTP + OS/VMware |
| Huawei SAN | Device **`HU-DEB-SAN01`** → CG **SNMP Monitoring (Huawei)** | SNMPv3 `LogicMonitor` on CG HI |
| Agent-class ICMP | TemplateRule **Agent Host ICMP** on agent-class roles | ICMP Ping |
| Zabbix Proxy | Role **Zabbix Proxy** → ICMP + Remote Zabbix proxy health | Linux agent + proxy self-mon |
| vCenter | Role **vCenter** → template **VMware FQDN** | SDK macros; LLD covers hypervisors/VMs/cluster |
| Cohesity physical | Role **Cohesity** + Dell iDRAC HTTP | PowerEdge HTTP + Redfish macros on **role** |
| Space Server | CG **Agent Monitoring (SPACE)** on role | Agent **:10060** |
| Criticality | Tag `critical` → hostgroup | `Priority/Critical` |

Hostgroup Jinja and assignment clicks: configuration §8.  
Which CG/template/interface a given host class should end up with: configuration §13.

---

## Rules of thumb

1. **One configuration group decides transport** (how we reach the host). Hostgroups and templates can stack; transport cannot.
2. **Different SNMPv3 users need different CGs** — never reuse the network CG for Linux or SAP.
3. **Tags may select a CG** (`snmp`). SAP uses **role-based** dual-plane CG **SAP Agent+SNMP** (SAP HANA, SAP ME), not tags and not two separate CGs. Host Interfaces sit on the CG — never directly on a tag.
4. **Country Site Group is the control plane** for proxy, default Agent, Sites/Roles hostgroups, environment tag, and inventory. Assign Agent Monitoring only on **country** Site Groups, not campus mid-levels.
5. **Hierarchy paths stay after Role/Platform** in plugin inheritance so a plugin upgrade does not change who already wins for existing installs.
6. **Templates merge** — Role + Platform + Manufacturer rules all accumulate. Colliding item keys (e.g. Network Generic + Extreme both defining `icmpping`) must be avoided by assignment design, not by hoping one replaces the other.

---

## What stays outside this integration

Things with no NetBox object to hang on (website checks, account-level APIs, …) and all **monitoring-domain** work (what to poll, thresholds, notifications) are out of scope here. See configuration §§14–16 and the packs under [`../../zabbix/`](../../zabbix/README.md).

This folder owns **NetBox ↔ Zabbix integration** — assignment rules and sync lifecycle on top of existing NetBox data — not inventory hygiene and not the monitoring content that runs on those hosts.
