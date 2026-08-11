# Monitoring plan

Status: active

## Migration constraint

**Hard deadline: LogicMonitor → Zabbix cutover.** That reframes everything below.

The bar for cutover is **"no worse than LogicMonitor"**, not "everything in the design docs". Anything LogicMonitor does not watch today cannot be a regression, so it cannot be a blocker.

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
| **OSPF adjacency (§C)** | LogicMonitor almost certainly is not watching it — deferring is not a regression |
| Speed expectation | new capability, not parity. Needs labels first |
| Capacity: discards + utilisation | new capability. Needs 4+ weeks of history to threshold honestly |
| CRC / `dot3StatsFCSErrors` | new capability, and unconfirmed |
| Full port-label rollout | parity only needs *link down*, which works on unlabelled ports under the core role |
| Access-switch opt-in scoping | can start permissive and tighten after cutover |
| APs, Fortinet, Cato, circuits, VMs (02–06) | separate domains, separate timelines |

**Rule for the migration window:** if a request is not in the "cutover minimum" table, it goes on the post-cutover list. Scope creep is the main risk to the date, not technical difficulty.

## Order

```
port-identity (foundation)
    │
    ▼
01  Extreme switching — EXOS then VOSS        ← now, cutover critical
    │
    ▼
02  Extreme access points (HiveOS / XIQ)
    │
    ▼
03  Fortinet (FortiGate, FortiManager, FortiAnalyzer)
    │
    ▼
04  Cato
    │
    ▼
05  Internet circuits (UW + NetBox Circuits)
    │
    ▼
06  Network VMs

post-cutover:  OSPF (01 §C) · speed expectation · capacity · CRC
```

Rationale: device health before ports, ports before overlay, overlay before circuits, circuits before SLA composition.

## Status

| # | Domain | Template exists | Spec written | Piloted | Live |
|---|---|---|---|---|---|
| 01a | EXOS | stock (7.0 branch) | yes | no | no |
| 01b | VOSS | **built** — `templates/extreme_voss_snmp/` | yes | lab only (virtual) | no |
| 01–ports | Port Speed Expect | **built** — `templates/extreme_port_speed_expect_snmp/` | yes | no | no |
| 01c | OSPF routing (core/dist, both platforms) | **built** — `templates/extreme_routing_snmp/` | yes | no | no |
| 02 | HiveOS / IQ Engine AP | **built** — `templates/extreme_iq_engine_snmp/` | analysis (`02`) | no | no |
| 03 | FortiGate | ? | scaffold | no | no |
| 03 | FortiManager | ? | scaffold | no | no |
| 03 | FortiAnalyzer | ? | scaffold | no | no |
| 04 | Cato | none (HTTP agent) | scaffold | no | no |
| 05 | Circuits | n/a | scaffold | no | no |
| 06 | Network VMs | stock OS templates | scaffold | no | no |

## Principles

1. Health before ports, ports before circuits.
2. Scope by device role + port label, never "monitor everything".
3. One source of icmpping per host — no stacking Network Generic under a platform template.
4. Underlay (Extreme / Fortinet) and overlay (Cato) stay separate problem classes.
5. Prefer macro overrides over cloning stock templates — keeps the upgrade path.
6. Signals with no trigger and no dashboard get deleted.

## Lab proof (optional onboarding scripts)

Architecture: `docs/nbxsync-architecture.md`.  
nbxSync GUI rows: `docs/nbxsync-configuration-checklist-zerotouch.md`.  
Day-2 is GUI/API; scripts only accelerate a first build (`scripts/README.md`).

```bash
# 1) Fleet (CGs, TemplateRules, hostgroups, …)
PYTHONPATH=/workspace/.deps/netbox/netbox:/workspace \
  /workspace/.deps/venv/bin/python scripts/configure_nbxsync_zerotouch.py --simulate

# 2) Extreme half (IFALIAS, VOSS import, EXOS LLD/TEMP patches)
PYTHONPATH=/workspace/.deps/netbox/netbox:/workspace \
  /workspace/.deps/venv/bin/python scripts/configure_nbxsync_network.py --simulate

# Zabbix-only smoke (no NetBox graph)
python3 scripts/run_network_zabbix_sim.py --with-speed-expect
```

Reports: `/opt/cursor/artifacts/ZEROTOUCH_*` and `NETWORK_NBXSYNC_SIM_REPORT.md`.

## Out of scope until listed

| Item | Until |
|---|---|
| Interface utilization % | 06 / later, needs NetBox commit bandwidth |
| Services / SLA composition | after 01–05 |
| LAG / MLAG / MLT port labelling | port-identity §5 TBD |
| LTE / backup tolerance profiles | later |
