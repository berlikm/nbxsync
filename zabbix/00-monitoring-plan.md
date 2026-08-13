# Monitoring plan

Status: active

## Migration constraint

**Hard deadline: LogicMonitor → Zabbix cutover.** That reframes everything below.

**In scope now:** Extreme switches (01) and access points (02).  
**Prepared, not blocking cutover:** FortiGate (03), network VMs (06). Same page shape and observability bar.  
**Later still:** Cato (04), circuits (05).

The bar for switch/AP cutover is **"no worse than LogicMonitor"**, not "everything in the design docs". Anything LM does not watch today cannot be a regression.

### Cutover minimum — must be live

| # | Capability | Why it blocks |
|---|---|---|
| 1 | Every switch is a Zabbix host with the right platform template | a device nobody monitors is the only unrecoverable regression |
| 2 | Device reachable / not reachable (ICMP + SNMP availability) | the single most-used signal in any NMS |
| 3 | Device health: CPU, memory, temperature, PSU, fan | LogicMonitor parity |
| 4 | Link down on ports we care about | LogicMonitor parity |
| 5 | Interface errors | LogicMonitor parity |
| 6 | Alerts actually reach a human (media, actions, escalation) | monitoring nobody receives is not monitoring |
| 7 | Monitoring-the-monitoring: unsupported items, zero-interface hosts, proxy last-seen | catches a silent migration gap |

### Explicitly NOT blocking cutover

| Capability | Why it can wait |
|---|---|
| **OSPF adjacency** | LogicMonitor almost certainly is not watching it — deferring is not a regression |
| Speed expectation | new capability, not parity. Needs labels first |
| Capacity: discards + utilisation | new capability. Needs 4+ weeks of history to threshold honestly |
| CRC / `dot3StatsFCSErrors` | new capability, and unconfirmed |
| Full port-label rollout | parity only needs *link down*, which works on unlabelled ports under the core role |
| Access-switch opt-in scoping | can start permissive and tighten after cutover |
| Fortinet, Cato, circuits, VMs (03–06) | prepared page + same bar; do not block switch/AP cutover |

**Rule for the migration window:** if a request is not in the "cutover minimum" table, it goes on the post-cutover list. Scope creep is the main risk to the date, not technical difficulty.

## Order

```
port-identity (foundation)
    │
    ▼
01  Extreme switching                         ← now
    │
    ▼
02  Extreme access points                     ← now
    │
    ▼
03  Fortinet                                  ← prepared
    │
    ▼
04  Cato
    │
    ▼
05  Internet circuits
    │
    ▼
06  Network VMs                               ← prepared

post-cutover:  OSPF · VOSS fabric · speed-expect triggers · USW discards/util · label compliance · site synthetic
```

Rationale: device health before ports, ports before overlay, overlay before circuits, circuits before SLA composition.

## Status

| # | Domain | Template exists | Spec written | Piloted | Live |
|---|---|---|---|---|---|
| 01a | EXOS | stock (7.0 branch) | yes | no | no |
| 01b | VOSS | **built** — `templates/extreme_voss_snmp/` | yes | lab only (virtual) | no |
| 01–ports | Port Speed Expect | **built** — `templates/extreme_port_speed_expect_snmp/` | yes | no | no |
| 01c | OSPF routing (core/dist, both platforms) | **built** — `templates/extreme_routing_snmp/` | yes | no | no |
| 02 | HiveOS / IQ Engine AP | **built** — `templates/extreme_iq_engine_snmp/` | yes | no | no |
| 03 | FortiGate | ? | scaffold | no | no |
| 03 | FortiManager | ? | scaffold | no | no |
| 03 | FortiAnalyzer | ? | scaffold | no | no |
| 04 | Cato | none (HTTP agent) | scaffold | no | no |
| 05 | Circuits | n/a | scaffold | no | no |
| 06 | Network VMs | stock OS templates | scaffold | no | no |

## Principles

1. Page **symptoms**, graph **causes**. A Warning that never pages should not be a Warning.
2. Scope by role + label (or equivalent). Never monitor every IF-MIB / radio / tunnel row.
3. One `icmpping` per host — no Network Generic under a platform template.
4. One incident per root cause (dependencies up to **site**). Underlay ≠ overlay ≠ firewall.
5. Never fail silent: unsupported items, zero discovered objects, proxy last-seen.
6. Collect first; enable noisy triggers after a quiet pilot.
7. Macro overrides, not cloned stock templates.
8. Signal with no trigger and no dashboard → delete it.
9. Next domain copies [_template.md](_template.md) — FortiGate and VMs are already stubbed that way.
10. Use the full Zabbix scale. **Disaster** is site/service only (never on a switch/AP template). Do not park everything on Warning.

## Lab proof

NetBox ↔ Zabbix integration: [`../docs/netbox-zabbix/configuration.md`](../docs/netbox-zabbix/configuration.md).

## Out of scope until listed

| Item | Until |
|---|---|
| Interface utilization % | 06 / later, needs NetBox commit bandwidth |
| Services / SLA composition | after 01–05 |
| LAG / MLAG / MLT port labelling | port-identity §5 TBD |
| LTE / backup tolerance profiles | later |
