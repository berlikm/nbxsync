# Internet / Network Monitoring — Implementation Plan

**Status:** Implementation plan (reordered per stakeholder)  
**Priority order:** Device health → uplinks/ports → Cato & FortiGate → Services/SLA → ISP circuit monitoring  
**Stack:** NetBox + nbxsync + Zabbix 7 · Extreme EXOS / VOSS · HiveOS APs (XIQ Pilot) · (later) Cato · FortiGate

**Port identity (locked):** Extreme **display string only** (≤15 codes) — includes + **exclusion `X:…`**.  
See `/opt/cursor/artifacts/docs/port-identity-foundation.md`.  
NetBox = inventory + **compliance** (not a second place to edit “monitor this port”).

---

## Two separate work tracks

This plan is **monitoring capability** (what we monitor, in what order).  
**NetBox ↔ Zabbix integration** (nbxsync: populate hosts/data, template assignment automation, alerts/actions wiring, triggers packaging, configure/checklist automation) is a **separate task / backlog item** — not phases inside this list.

| Track | Owns | Examples |
|---|---|---|
| **A — Monitoring design & rollout** (this document) | What to monitor, phase order, templates content, **display-string port codes**, Cato/Forti/SLA/ISP scope | VOSS/HiveOS template *definitions*, include/exclude code lists, phase exits |
| **B — NetBox integration** (**separate task**) | How NetBox drives Zabbix day-2 | nbxsync rules/CG/inheritance, sync jobs, compliance reports, alert actions, trigger import/CI, zero-touch script/checklist wiring |

**Relationship:** Track A defines *what* each phase needs. Track B delivers *how* it is automated from NetBox. Do not mix “build HiveOS template items” and “publish display-string LLD filters to Zabbix” into one phase checkbox unless deliberately scheduled as a dependency handoff.

**Port identity (locked — Track A design):**

```
OPERATOR SOT = Extreme display string only (≤15)
  Include: U:C: U:D: U:A: U:P: W: M: MON / MON:<id>
  Exclude: X:STK X:SPN X:OOB X:INT X
  NO speed nibbles — description holds why/what

CORE/DIST/MGMT = all admin-up minus X:… (unused admin-up → disable)
ACCESS         = only include codes; APs hang off access → U:P: (1G)
                 MON: = ESX/storage/iDRAC/server (+ description)
NETBOX         = cables/circuits + compliance + description (why/what)
                 (NO day-to-day NetBox “monitor” interface tags)
                 Dist↔access: U:D:/U:A: + Zabbix baseline (1G/10G/100M)

```

Full detail: `docs/port-identity-foundation.md`.

```
Track A (this plan)          Track B (separate task)
─────────────────────        ─────────────────────────────
Phase 1 Device health   ←──  may consume: Template Rules, sync
Phase 2 Uplinks         ←──  may consume: display→LLD publish, macros, compliance
Phase 3 Cato / Forti    ←──  may consume: site fields, assignments
Phase 4 Services/SLA    ←──  may consume: hostgroups, Zabbix action tags
Phase 5 ISP circuits    ←──  may consume: Circuits, W:… display codes, sync
```

---

## 0. Principles (all phases)

1. **Health before circuits** — stable device and uplink monitoring before ISP-specific and SLA layers.  
2. NetBox is SoT for **inventory** (devices, cables, circuits) — **integration mechanics live in Track B**, not as sub-steps of every phase here.  
3. Do **not** monitor every interface the same way; scope by **device role + display string** (include / exclude codes).  
4. **One operator edit** for port intent: Extreme display string. No dual-edit with NetBox monitor tags.  
5. Underlay (Extreme/Forti) and overlay (Cato) stay separate problem classes.  
6. Same metric baseline across site classes initially; tune later.  
7. No stacking full Network Generic + specialized templates (icmpping collisions).  
8. Missing platform templates (VOSS, HiveOS AP) are **explicit Track A build tasks**.  
9. Populating NetBox data, nbxsync automation, alert/trigger pipelines = **Track B (separate)**.

---

## Current template gap

| Platform / class | Today | Status |
|---|---|---|
| Extreme **EXOS** | Template Rule → Extreme EXOS by SNMP | **Done** (device health baseline) |
| Extreme **VOSS** | Falls back to Network Generic | **Gap — build VOSS template** |
| **HiveOS** APs (XIQ Pilot) | No dedicated AP template | **Gap — build HiveOS/AP template** |
| Scoped **uplinks** (core / dist / access / AP) | Not systematically scoped | **Phase 2** (display codes) |
| **ISP / WAN** circuit ports | Not implemented | **Phase 5** (`W:…` + Circuits) |
| **Cato** / **FortiGate** depth | Partial / role floors only | **Phase 3** |
| **Services / SLA** | Not the focus yet | **Phase 4** |

---

## Phase overview (agreed order)

| Phase | Name | Outcome |
|---|---|---|
| **0** | Foundations | Inventory, **display-string code list**, pilots, EXOS/VOSS/AP counts |
| **1** | **Device health** | Every switch/AP has a proper platform template (EXOS, **new VOSS**, **new HiveOS AP**) |
| **2** | **Uplinks & structural ports** | Core / dist / access uplinks + uplinks to APs monitored via display codes |
| **3** | **Cato & FortiGate** | Overlay + Forti path/underlay integrations |
| **4** | **Services & SLA** | Site/service views, availability reporting |
| **5** | **ISP circuit monitoring** | Documented ISP/WAN ports (`W:…`), providers/circuits, underlay circuit alerts |
| **6** | Profiles & tuning (optional) | LTE/backup, maintenance suppress, class thresholds, util% |

```
Phase 0 Foundations
    │
    ▼
Phase 1  Device health (EXOS + build VOSS + build HiveOS AP)
    │
    ▼
Phase 2  Ports: core / dist / access uplinks + AP uplinks (display codes)
    │
    ▼
Phase 3  Cato + FortiGate
    │
    ▼
Phase 4  Services & SLA
    │
    ▼
Phase 5  ISP / circuit monitoring (W:… + NetBox Circuits)
    │
    ▼
Phase 6  Profiles / util% / maintenance (optional maturity)
```

---

## Phase 0 — Foundations

**Objective:** Know what we have and lock the **display-string** port scoping contract for Phase 2/5.

| ID | Deliverable |
|---|---|
| P0.1 | Inventory: EXOS vs VOSS switches; HiveOS/XIQ APs; Forti; Cato sites |
| P0.2 | **Lock port SoT:** Extreme display string only (≤15). Reject NetBox monitor-tags for day-to-day ops |
| P0.3 | **Code list approved:** `U:C/D/A/P`, `W:`, `M:`, `MON`/`MON:<id>`, exclusions `X:…` — **no speed nibbles** |
| P0.4 | Role matrix: core/dist/mgmt = admin-up − `X:…`; access = include codes only |
| P0.5 | Pilot lists: 1–2 EXOS, 1 VOSS, sample APs |
| P0.6 | Site class field optional (`production`/`sales`/`normal`) — same metrics for now (alert routing later = Track B) |

**Verify exit**

- [ ] Platform counts known  
- [ ] Include + **exclusion** display codes agreed (`U:` / `W:` vs `X:`; WAN = `W:` for Phase 5)  
- [ ] Role matrix locked (fabric vs access)  
- [ ] Pilots named  
- [ ] Owners for VOSS + HiveOS template builds named  

---

## Phase 1 — Device health (general)

**Objective:** Monitor **device health** for the Extreme + AP estate before worrying about ISP circuits or SLA.

### In scope

| Class | Work |
|---|---|
| **EXOS switches** | Keep / verify Extreme EXOS by SNMP (CPU, memory, general health, existing LLD as today) |
| **VOSS switches** | **Build** dedicated Extreme VOSS by SNMP template (replace Network Generic as primary). Rule *wiring* → Track B |
| **HiveOS APs** | **Build** HiveOS / Extreme AP template. Rule *wiring* → Track B |

### Work packages

| ID | Work | Detail |
|---|---|---|
| P1.1 | Verify EXOS health coverage on pilots | Gaps list (temp, PSU, fan, etc. if needed later) |
| P1.2 | Build **Extreme VOSS by SNMP** Zabbix template | Vendor/community base; SNMP requirements |
| P1.3 | Define Template Rule intent: platform `VOSS` → VOSS template + `OS/Network` | **Wiring into nbxsync/checklist = Track B** |
| P1.4 | Build **HiveOS AP** Zabbix template | Availability, uplink basic, radio/client as agreed for v1 |
| P1.5 | Define Template Rule intent for AP platforms (e.g. `IQ ENGINE` / HiveOS) | Access Point: no Network Generic role floor; **automation = Track B** |
| P1.6 | Decide AP v1 data path | SNMP to AP vs ExtremeCloud IQ Pilot API (or hybrid) |
| P1.7 | Pilot: apply templates on VOSS switch + sample APs | Manual or existing sync OK for prove-out |
| P1.8 | Document required NetBox fields/platforms for health | Handoff note to Track B |

### Explicitly not Phase 1

- ISP/WAN circuit alerts  
- Cato / FortiGate deep integration  
- Services / SLA trees  
- util% capacity alerts  
- Full uplink scoping (Phase 2)  
- **NetBox data population / nbxsync / alert-action / trigger pipelines** (Track B — separate task)

### Exit criteria

- [ ] EXOS health OK on pilots  
- [ ] VOSS template exists and works on pilot (rule *intent* documented)  
- [ ] HiveOS/AP template exists and works on pilot  
- [ ] Handoff to Track B documented (platforms, template names, rule patterns)  
- [ ] No new icmpping collisions introduced  

---

## Phase 2 — Uplinks & structural ports

**Objective:** Monitor **important ports** — core / distribution / access uplinks and **uplinks to access points** — not every access edge port, not ISP circuits yet.

**SoT:** Extreme **display string** codes (see foundation doc). One edit on the switch.

### Port classes (Phase 2) — display codes

| Display code | Meaning | Zabbix speed |
|---|---|---|
| `U:C:<id>` | Uplink toward core | Baseline / degrade |
| `U:D:<id>` | Uplink toward dist | Baseline — **1G / 10G / 100M all normal** (no override code) |
| `U:A:<id>` | Uplink toward access | Baseline — **1G / 10G / 100M all normal** |
| `U:P:<id>` | Access → AP | Expect **1G** |
| `MON` / `MON:<id>` | Non-fabric endpoint (ESX, storage, iDRAC, server, …) | Baseline |
| `M:<yymmdd>` | Temp monitor until date | Baseline if needed |

Display = **role / include class only**. Speed is not in the code.  
ISP/WAN (`W:…`) → **Phase 5**.

### Exclusion codes (core / dist / mgmt)

On fabric roles, LLD = **all admin-up** except display matching:

| Code | Meaning |
|---|---|
| `X:STK` | Stack / ISC / MLAG member |
| `X:SPN` | SPAN / mirror |
| `X:OOB` | Out-of-band / mgmt port |
| `X:INT` | Internal / do not monitor |
| `X` | Generic exclude |

Unused admin-up on core/dist/mgmt → **disable** (security hygiene), not “monitor everything forever.”

**AP topology (locked):** Access points connect to **access switches**, not core/dist. Monitor:

1. **Switch side** — display `U:P:…` — link state + **speed** (expect 1G).  
2. **AP side** — Phase 1 HiveOS device health (separate from switch port speed).

### Speed monitoring (Phase 2 — in scope)

**No speed-exception codes.** We do **not** assume `U:D:` = 10G and then override for 1G/100M. Those speeds are **normal** for that class; Zabbix **baseline** is the expected value per port.

| Link class | Zabbix approach | Alert if |
|---|---|---|
| Access → AP (`U:P:`) | Fixed expect **1G** | Oper up but not 1G → WARNING |
| Dist ↔ access / fabric (`U:D:` / `U:A:` / `U:C:`) | **Baseline / degrade** | Oper drops vs baseline |
| `MON:` (ESX / storage / iDRAC / server) | **Baseline / degrade** | Oper drops vs baseline |
| Forced Extreme admin | Expected = admin | Oper ≠ admin |

**Real exceptions** = monitor include/exclude only: `X:…` to skip; include codes on access to opt in.  
**Description** = human notes (optional plant-speed note; required clarity for `MON:`) — not a Zabbix speed override.

**Not required in Phase 2:** util% capacity alerts.

### Work packages

| ID | Work | Detail |
|---|---|---|
| P2.1 | Classify ports from cables | Access↔dist, access→AP, etc. |
| P2.2 | Short display codes ≤15 | `U:D:swa12`, `MON:esx01`, `MON:idr3`, `X:STK` — **no speed nibbles** |
| P2.3 | Discovery contract for Track B | Display regex / ifIndexes; LLD modes `admin_up_excl` vs `display_include` |
| P2.4 | Uplink / fabric port template | State, flap, errors, **speed baseline / degrade** (+ `U:P:` = 1G) |
| P2.5 | Discovery by role | Fabric: admin-up − `X:…`; access: include codes only |
| P2.6 | Manual no-cable path | Set ≤15 display on switch; done |
| P2.7 | NetBox **compliance** reports | Cable implies code missing; `MON:` without description; stale `M:` |
| P2.8 | AP dual view | Switch `U:P:` (expect 1G) + HiveOS health |
| P2.9 | `MON:` for ESX / storage / iDRAC / servers | On mgmt/core + description; baseline speed |
| P2.10 | Runbook | Display = class; description = why/what |

### Scoping options (locked)

| Option | Role |
|---|---|
| Extreme **display string** include / exclude codes | **Operator SoT (locked)** |
| NetBox interface **monitor tags** for day-to-day | **Reject** (dual-edit) |
| NetBox cables / Circuits + **compliance** reports | Drift detection only |
| NetBox interface **description** | Human why/what (intentional 1G/100M; ESX; iDRAC; storage) |
| Optional Python cable → push display | Scale aid; not a second control plane |
| Fixed port numbers | Reject |
| Monitor all interfaces as “uplinks” | Reject |

### Exit criteria

- [ ] Core/dist: admin-up − `X:…` alerts on down/flap on pilots  
- [ ] Access: only include-coded ports in alert stream (edge quiet by default)  
- [ ] VOSS + EXOS both work with same **display-string** pattern  
- [ ] AP wired path visible (AP health + switch `U:P:`)  
- [ ] Exclusion codes validated (e.g. stack port does not alert)  
- [ ] Speed canaries: 10G `U:D:`, 1G `U:D:` + description, 100M + description  
- [ ] `MON:` canaries: ESX, storage, iDRAC on mgmt/core (+ description)  

---

## Phase 3 — Cato & FortiGate (later)

**Objective:** Add overlay (Cato) and FortiGate path/underlay where they matter.

### Cato

| ID | Work |
|---|---|
| P3.C1 | API version + field map (`accountSnapshot` / `accountMetrics`) |
| P3.C2 | HTTP-agent template + LLD (sites/links) |
| P3.C3 | Collector health ≠ site outage |
| P3.C4 | Dashboards vs Extreme underlay (avoid double-count confusion) |
| P3.C5 | Cato site ID on NetBox Site |

### FortiGate

| ID | Work |
|---|---|
| P3.F1 | Inventory: Forti-terminated vs Extreme vs Cato-direct |
| P3.F2 | Forti WAN/path monitoring (SNMP/API as applicable) |
| P3.F3 | nbxsync assignment (role/platform rules; no manufacturer-wide accidents) |
| P3.F4 | Align severity language with Extreme |

**Depends on:** Phase 1 (stable device health) recommended; Phase 2 nice-to-have for correlation.

---

## Phase 4 — Services & SLA (later)

**Objective:** Compose device/uplink/(later circuit) signals into **site/service** status and availability reporting.

| ID | Work |
|---|---|
| P4.1 | Define service tree (e.g. Site Network → core/dist/access → key uplinks) |
| P4.2 | Zabbix Services (or equivalent) mapping from NetBox sites |
| P4.3 | Availability / SLA reporting for agreed site classes |
| P4.4 | Alert routing by service state (degraded vs outage) |
| P4.5 | Dashboards for service owners (not only device owners) |

**Depends on:** Phases 1–2 solid; Phase 3 if overlay is part of “site up.”

**Note:** Earlier draft mentioned Services lightly — this phase is where it belongs, after network integration health/uplinks exist.

---

## Phase 5 — ISP circuit monitoring (later)

**Objective:** Monitor **internet circuits** — documented ISP ports / terminations — after health, uplinks, and (ideally) overlay/Forti context exist.

| ID | Work |
|---|---|
| P5.1 | NetBox **Providers + Circuits** + terminations (ISP inventory task) |
| P5.2 | Set display `W:…` on Extreme (or Forti) WAN ports; link interface to Circuit in NetBox |
| P5.3 | Thin **ISP/WAN Ports** template (or extend uplink template with circuit macros) — LLD on `W:…` |
| P5.4 | Alerts: circuit down / flap; redundancy-loss logic when dual-circuit known |
| P5.5 | Dashboards: site internet underlay (distinct from uplink-fabric views) |
| P5.6 | Correlate with Cato (Phase 3) without merging problem classes |
| P5.7 | Compliance: Circuit termination present but display not `W:…` (or reverse) |

### Not required at start of Phase 5

- util% from ifHighSpeed (optional later in Phase 6)  
- LTE/backup special profiles (Phase 6)  
- Treating XIQ APs as ISP edge (never)

### Exit criteria

- [ ] Pilot Prod circuits: port (`W:…`) ↔ ISP ↔ site visible in NetBox and Zabbix  
- [ ] ISP alerts separate from fabric uplink alerts  
- [ ] Multi-homing documented as residual risk if not fully modeled  

---

## Phase 6 — Profiles & analysis maturity (optional)

| ID | Work | Comment |
|---|---|---|
| P6.1 | Backup / LTE tolerance profiles | How we monitor non-primary internet lines |
| P6.2 | ISP maintenance / planned failover suppressions | Future ops nicety |
| P6.3 | Utilization % from NetBox commit bandwidth | Not blind ifHighSpeed |
| P6.4 | ICMP in severity model | Only if impact understood |
| P6.5 | Tune thresholds by site class | After shared baseline history |
| P6.6 | XIQ API depth beyond Phase 1 AP template | Enrichment only |

---

## Track B — NetBox integration (separate task — not phases above)

Track as its **own backlog item / project**, linked to but not inside Phases 1–5.

| Theme | Examples |
|---|---|
| Data population | Sites, roles, platforms, cables, Circuits/Providers when Phase 5 needs them |
| Display / LLD publish | Read Extreme (or push) display codes → Zabbix LLD filters / macros |
| Compliance | “Cable says AP but display missing”; stale `M:`/`MON`; Circuit without `W:…` |
| nbxsync automation | Template Rules, CG assignments, inheritance; Zabbix speed baseline / LLD macros |
| Alerts & actions | Zabbix actions, media, **Zabbix** tags for routing (site class) — not NetBox port monitor-tags |
| Triggers / templates ops | Import, versioning, promote lab→prod; collision checks |
| Zero-touch | Checklist + configure script updates when Track A templates are ready |
| Sync / verify | Host sync, census, regression after template changes |

**Rule of thumb:** If the work is “make NetBox drive Zabbix,” it is Track B. If the work is “what should we monitor next on Extreme/Cato/Forti,” it is Track A (this plan).

---

## Cross-cutting lists

### Do now (Track A → Phases 0–2)

1. Foundations + **display-string code list** (includes + `X:…` exclusions; `W:` reserved for Phase 5)  
2. **Device health templates:** EXOS verify + **build VOSS** + **build HiveOS AP**  
3. **Uplinks:** core / dist / access / AP ports scoped and monitored via display codes  

### Do later (Track A → Phases 3–6)

4. Cato + FortiGate  
5. Services & SLA  
6. ISP/circuit monitoring (`W:…` + Circuits)  
7. Profiles / util% / maintenance / ICMP  

### Separate (Track B — always its own task)

- Populate NetBox data  
- nbxsync / sync automation + display→LLD + compliance  
- Alerts, actions, trigger packaging  
- Checklist/script wiring when A delivers templates  

### Risks

| Risk | When |
|---|---|
| Mixing Track A and Track B in one ticket → unclear ownership | Always |
| VOSS/AP template slips | Phase 1 |
| Wrong / missing display codes (or unused admin-up noise) | Phase 2 |
| Fabric uplinks mixed with ISP alerts | Phase 2 vs 5 |
| Services before health/uplinks stable | Phase 4 too early |
| Multi-homing | Phase 5 |
| Cato + Extreme double-count | Phase 3 |
| XIQ as ISP SoT | Never |
| Reintroducing NetBox monitor-tags as dual SoT | Never |

### Out of scope until listed phase (Track A)

| Item | Until |
|---|---|
| Dedicated VOSS/HiveOS templates | Phase 1 |
| Fabric / access port scoping via display codes | Phase 2 |
| Cato / Forti deep work | Phase 3 |
| Services / SLA | Phase 4 |
| ISP inventory + `W:…` WAN alerts | Phase 5 |
| util% / LTE / maintenance / ICMP severity | Phase 6 |

---

## Port scoping (Phases 2 and 5)

| Phase | What we scope | Display codes |
|---|---|---|
| 2 | Fabric / AP / MON endpoints | `U:C:`, `U:D:`, `U:A:`, `U:P:`, `MON`/`MON:<id>` (+ `M:`); fabric excludes `X:…` |
| 5 | Internet circuits | `W:…` (+ Circuit object in NetBox) |

**Design (Track A):** display-string codes + which template / LLD mode watches them.  
**Automation (Track B):** publish LLD from display; compliance reports; optional cable→display script.  
**Reject:** NetBox day-to-day monitor-tags; “monitor everything.”

---

## Verify before build

### Phase 1 (device health — Track A)

- [ ] Owner: VOSS template content  
- [ ] Owner: HiveOS AP template content  
- [ ] AP path: SNMP and/or XIQ API  
- [ ] Rule patterns documented for Track B handoff  
- [ ] Pilots: EXOS / VOSS / APs  

### Phase 2 (uplinks — Track A)

- [ ] Include + **exclusion** display codes locked  
- [ ] Role matrix locked (admin-up−`X:` vs include-only)  
- [ ] Discovery contract documented for Track B  
- [ ] Port template item list (down/flap/speed; no util% required)  

### Track B (separate)

- [ ] Own ticket/epic exists (data, nbxsync, LLD/compliance, alerts/triggers)  
- [ ] Not blocked on inventing Phase 3–5 scope  

### Later backlog (Track A)

- [ ] Phase 3 Cato + FortiGate  
- [ ] Phase 4 Services/SLA  
- [ ] Phase 5 ISP circuits  

---

## One-page summary (cross-check)

```
TWO TRACKS:
A) This plan — monitoring phases (what/when)
B) SEPARATE TASK — NetBox integration (populate data, nbxsync,
   display→LLD, compliance, alerts/actions, triggers, zero-touch)

PORT SOT (locked):
  Extreme display string ≤15 only
  Include: U:C: U:D: U:A: U:P: W: M: MON / MON:<id>
  Exclude: X:STK X:SPN X:OOB X:INT X
  NetBox = compliance + description (why/what) — NO monitor-tags
  NO speed nibbles — baseline for U:/MON:; U:P: expect 1G
  Focus = Zabbix (not switch-config generation)

TRACK A ORDER:
0 Foundations (code list + role matrix)
1 Device health (EXOS + BUILD VOSS + BUILD HiveOS AP templates)
2 Ports — core/dist/mgmt admin-up−X: (+ MON: labels for ESX/storage/iDRAC);
   access includes; U:P: (1G); U:D:/U:A: baseline 1G|10G|100M
3 Cato + FortiGate
4 Services & SLA
5 ISP circuit monitoring (W:… + Circuits)
6 Optional profiles / util% / maintenance

NOW (A) = 0, 1, 2
LATER (A) = 3, 4, 5, 6
ALWAYS SEPARATE (B) = NetBox data + automation + alerts/triggers

GAPS TO BUILD IN PHASE 1 (A):
- Extreme VOSS by SNMP template
- HiveOS Access Point template
(nbxsync/checklist automation of those rules = Track B)
```
