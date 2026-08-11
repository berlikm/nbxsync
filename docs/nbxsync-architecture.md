# NetBox → nbxSync → Zabbix architecture

How monitoring policy is derived from NetBox so new devices and VMs become Zabbix hosts without per-host hand configuration.

**Audience:** anyone who needs the picture — product owners, Zabbix admins, reviewers.  
**Not this doc:** click-by-click build steps → [`nbxsync-configuration-checklist-zerotouch.md`](nbxsync-configuration-checklist-zerotouch.md).  
**Not this doc:** what Extreme/Forti/Cato templates measure → [`zabbix/`](../zabbix/README.md).

---

## Layers

| Layer | Role |
|---|---|
| **NetBox** | Inventory truth — site, role, platform, manufacturer, tags, primary IP / `oob_ip` |
| **nbxSync** | Policy bus — inheritance, configuration groups, Template Rules, hostgroups, macros |
| **Zabbix** | Telemetry engine — collects, alerts, dashboards |

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

---

## Rules of thumb

1. **One configuration group decides transport** (how we reach the host). Hostgroups and templates can stack; transport cannot.
2. **Different SNMPv3 users need different CGs** — never reuse the network CG for Linux, SAP, or iDRAC.
3. **Tags may select a CG** (`snmp`). SAP uses **role-based** CG assignment (SAP HANA, SAP ME), not tags. Host Interfaces sit on the CG — never directly on a tag.
4. **Country Site Group is the control plane** for proxy, default Agent, Sites/Roles hostgroups, environment tag, and inventory. Assign Agent Monitoring only on **country** Site Groups, not campus mid-levels.
5. **Hierarchy paths stay after Role/Platform** in plugin inheritance so a plugin upgrade does not change who already wins for existing installs.
6. **Templates merge** — Role + Platform + Manufacturer rules all accumulate. Colliding item keys (e.g. Network Generic + Extreme both defining `icmpping`) must be avoided by assignment design, not by hoping one replaces the other.

---

## What a typical host looks like

| Object | Configuration group | Typical templates | Interfaces |
|---|---|---|---|
| Linux server (role Server) | Server Agent+OOB | Linux by agent (+ Dell iDRAC if Dell + `oob_ip`) | Agent :10050 + SNMP on oob |
| Linux / Windows VM | Agent Monitoring (Site Group) | OS by agent (Template Rule) | Agent :10050 |
| SAP HANA / SAP ME | SNMP Monitoring (SAP) | Linux by agent + SAP by agent (placeholder) | SNMP `SAPUSER` |
| Host with tag `snmp` | SNMP Monitoring (Linux) | Linux/Windows by SNMP | SNMP `MONITORING-LINUX` |
| Extreme switch | SNMP Monitoring | Extreme EXOS or VOSS by SNMP | SNMP `MONITORING` |
| Access Point | SNMP Monitoring | Extreme IQ Engine by SNMP | SNMP `MONITORING` |
| Firewall | SNMP Monitoring | FortiGate by SNMP | SNMP `MONITORING` |
| Space Server | Agent Monitoring (SPACE) | OS by agent | Agent :10060 |
| Pure / Dell storage | Agent Monitoring | HTTP templates (manufacturer rules) | Agent / HTTP |
| Cohesity physical | OOB SNMP Only | Storage Generic | SNMP on oob |
| + tag `critical` | unchanged | unchanged | + hostgroup Priority/Critical |

Full expected-state matrix (including hostgroups): checklist §13.

---

## Four hostgroup axes

Zabbix navigation and alerting use hostgroups, not a second tag taxonomy:

| Axis | Example | Source |
|---|---|---|
| Location | `Sites/CH/CH-STA/CH-STA-L42` | Jinja on country Site Group (full Site Group ancestry) |
| Function | `Roles/Switch Core` | Jinja on country Site Group (`object.role.name`) |
| OS / platform family | `OS/Linux`, `OS/Network` | Template Rules |
| Criticality | `Priority/Critical` | NetBox tag `critical` |

Hosts are members of the **leaf** site group only; dashboards filter on parents (`Sites/CH`). Organisation access is global — nested Sites are for location views, not regional RBAC.

---

## What stays outside NetBox / nbxSync

Some monitoring has no inventory object to hang on (or is deliberately Zabbix-native). Examples: website checks, account-level APIs (Cato), media/actions/escalation. Those are built in Zabbix directly — see checklist §17 and `zabbix/logicmonitor-assessment.md`.

Domain packs under `zabbix/` own **what** we measure on a technology (signals, stages, thresholds). This architecture and the nbxSync checklist own **how** a NetBox object becomes a Zabbix host.

---

## Related documents

| Doc | Purpose |
|---|---|
| [`nbxsync-configuration-checklist-zerotouch.md`](nbxsync-configuration-checklist-zerotouch.md) | GUI build of nbxSync objects (source of truth for rows) |
| [`../zabbix/00-monitoring-plan.md`](../zabbix/00-monitoring-plan.md) | Cutover order and parity bar |
| [`../zabbix/01-extreme-switching.md`](../zabbix/01-extreme-switching.md) | Extreme port scope, stages, TEMP_*/optic macros |
| [`../zabbix/port-identity.md`](../zabbix/port-identity.md) | On-box port label grammar |
| [`../scripts/README.md`](../scripts/README.md) | Optional **onboarding** helpers only — day-2 is GUI/API |
