# Internet / Network Monitoring — Implementation Plan

**Status:** Implementation plan (reordered per stakeholder)  
**Priority order:** Device health → uplinks/ports → Cato & FortiGate → Services/SLA → ISP circuit monitoring  
**Stack:** NetBox + nbxsync + Zabbix 7 · Extreme EXOS / VOSS · HiveOS APs (XIQ Pilot) · (later) Cato · FortiGate

**Port identity:** locked baseline in `docs/port-identity-foundation.md` (64-char grammar, always-emit SPEED). Open items live in that doc’s **TODO**.

---

## Two separate work tracks

This plan is **monitoring capability** (what we monitor, in what order).  
**NetBox ↔ Zabbix integration** (nbxsync: populate hosts/data, template assignment automation, alerts/actions wiring, triggers packaging, configure/checklist automation) is a **separate task / backlog item** — not phases inside this list.

| Track | Owns | Examples |
|---|---|---|
| **A — Monitoring design & rollout** (this document) | What to monitor, phase order, templates content, **display-string port codes**, Cato/Forti/SLA/ISP scope | VOSS/HiveOS template *definitions*, include/exclude code lists, phase exits |
| **B — NetBox integration** (**separate task**) | How NetBox drives Zabbix day-2 | nbxsync rules/CG/inheritance, sync jobs, compliance reports, alert actions, trigger import/CI, zero-touch script/checklist wiring |

**Relationship:** Track A defines *what* each phase needs. Track B delivers *how* it is automated from NetBox. Do not mix “build HiveOS template items” and “publish display-string LLD filters to Zabbix” into one phase checkbox unless deliberately scheduled as a dependency handoff.

**Port identity (locked — Track A design):** see `docs/port-identity-foundation.md`.

```
BUDGET = 64 | CLASS[-SPEED]-ID | USW US MON UW | N = note only
ACCESS opt-in | HYBRID admin-down spares
LAG / MLAG / MLT = later | Label push tooling = separate
```

Full detail + TODO: `docs/port-identity-foundation.md`.

```
Track A (this plan)          Track B (separate task)
─────────────────────        ─────────────────────────────
Phase 1 Device health   ←──  may consume: Template Rules, sync
Phase 2 Uplinks         ←──  may consume: display→LLD publish, macros, compliance
Phase 3 Cato / Forti    ←──  may consume: site fields, assignments
Phase 4 Services/SLA    ←──  may consume: hostgroups, Zabbix action tags
Phase 5 ISP circuits    ←──  may consume: Circuits, UW display codes, sync
```

---

## 0. Principles (all phases)

1. **Health before circuits** — stable device and uplink monitoring before ISP-specific and SLA layers.  
2. NetBox is SoT for **inventory** (devices, cables, circuits) — **integration mechanics live in Track B**, not as sub-steps of every phase here.  
3. Do **not** monitor every interface the same way; scope by **device role + port label**.  
4. Port labels follow the baseline grammar; label push tooling is **separate**.  
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
| **ISP / WAN** circuit ports | Not implemented | **Phase 5** (`UW` + Circuits) |
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
| **5** | **ISP circuit monitoring** | Documented ISP/WAN ports (`UW`), providers/circuits, underlay circuit alerts |
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
Phase 5  ISP / circuit monitoring (UW + NetBox Circuits)
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
| P0.2 | **VOSS canary:** `name` → SNMP ifAlias (`…1.1.1.18`) or ifDescr; note per-platform OID if needed |
| P0.3 | **EXOS canary:** display-string + description-string → ifAlias winner / truncate at 64 |
| P0.4 | Lock grammar budget **64**; always-emit SPEED; `X` notes |
| P0.5 | Grammar: uppercase; no colon; split X regex |
| P0.6 | Role matrix + hybrid admin-down spares; access safety-net limit stated |
| P0.7 | Pilot lists; site class optional |

**Verify exit**

- [ ] ifAlias length canary done (EXOS + VOSS)  
- [ ] Include + `X` grammar locked  
- [ ] Access: safety net does **not** cover missing labels (stated)  
- [ ] Hybrid: admin-down spares  
- [ ] Pilots named; VOSS/HiveOS owners named  

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

**Objective:** Fabric / AP / endpoint **ports** monitored with `USW`/`US`/`MON`/`UW`; `N` = note only (no action). LAG / MLAG / MLT later.

**SoT on box:** Extreme label that Zabbix reads via SNMP (**64-char budget**). EXOS: prefer `description-string` after canary. VOSS: `name` / `name port <list>` — confirm OID.

### Grammar

```
CLASS | CLASS-ID | CLASS-SPEED-ID     (UPPERCASE; no colon)
CLASS = USW|US|MON|UW|N
SPEED = 100M|1G|2G5|5G|10G|25G|40G|100G|400G
N = note only (free text, no Zabbix action)
```

Budget **64**. Monitored labels include SPEED.  
Apply labels on box → then enable absolute-expect. Label push tooling is **separate**. LAG / MLAG / MLT → later.

### Class defaults → Zabbix expected (if token omitted)

| CLASS | Default | Phase 2 monitoring |
|---|---|---|
| `USW` | **10G** | switch↔switch — link / flap / errors + speed |
| `US` | **10G** | server / storage — same |
| `MON` | **1G** | other endpoint (iDRAC, AP, …) — same |
| `UW` | — | WAN uplink — **link / flap / errors now**; absolute speed Phase 5 |
| `N` / `N-*` | — | note only — **no action** |

### Zabbix triggers (Phase 2)

1. Link down / flap / errors-CRC (including **`UW`**).  
2. Absolute expect where `USW|US|MON` (settled ≥5m).  
3. `change(ifHighSpeed)` vs last **stable up** (≥5m); **maintenance suppress** — only on **discovered** ports.  
4. **Access:** safety net does **not** apply if label missing/typo (no LLD item) — ops/inventory catches this.  
5. `N`: no action.  
6. **Gate:** enable absolute-expect per site after labels follow the grammar.

### Notes (`N`)

Label **`N` / `N-<text>`** — free description; Zabbix does nothing.

### Subsidiary hybrid (core∩access)

Same LLD as fabric (`admin-up AND NOT N`). Spares admin-down; `N` when up but uninteresting.

- Spares → **admin-down**.  
- Up-but-uninteresting → `N` / `N-<text>`  
- Monitor → **`USW` / `US` / `MON` / `UW`**

### Work packages

| ID | Work | Detail |
|---|---|---|
| P2.0 | SNMP canaries | VOSS name→OID; EXOS field→ifAlias precedence |
| P2.1 | Shared parser | UPPERCASE; USW/US/MON/UW/N; 64-char validate |
| P2.2 | Port template | link/flap/errors; speed; change vs stable-up; maint suppress |
| P2.3 | Access LLD | Include classes only; no safety net without label |
| P2.4 | Hybrid profile | admin-down spares; N for uninteresting |
| P2.5 | `UW` Phase 2 | link/flap/errors now |
| P2.6 | Rollout gate | labels in place → then absolute-expect |
| P2.7 | Pilot canaries | labels, hybrid, access typo via ops check |

### Scoping options (locked)

| Option | Role |
|---|---|
| `CLASS[-SPEED]-ID` on ifAlias | What Zabbix reads |
| Label push tooling | Separate |
| Monitor tags | Not used |
| Change-detect on discovered ports | Yes |
| LAG / MLAG / MLT | Later |

### Exit criteria

- [ ] Switch↔switch `USW` labels both ends  
- [ ] Server/storage `US` + iDRAC/AP `MON`  
- [ ] `UW` link/flap/errors  
- [ ] `N` / `N-<text>` → no Zabbix action  
- [ ] Hybrid: admin-down spares; `N` if up-but-uninteresting  

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
| P5.2 | Set `UW` label on Extreme (or Forti) WAN ports; link interface to Circuit in NetBox |
| P5.3 | Thin **ISP/WAN Ports** template (or extend uplink template with circuit macros) — LLD on `UW` |
| P5.4 | Alerts: circuit down / flap; redundancy-loss logic when dual-circuit known |
| P5.5 | Dashboards: site internet underlay (distinct from uplink-fabric views) |
| P5.6 | Correlate with Cato (Phase 3) without merging problem classes |
| P5.7 | Compliance: Circuit termination present but label not `UW` (or reverse) |

### Not required at start of Phase 5

- util% from ifHighSpeed (optional later in Phase 6)  
- LTE/backup special profiles (Phase 6)  
- Treating XIQ APs as ISP edge (never)

### Exit criteria

- [ ] Pilot Prod circuits: port (`UW`) ↔ ISP ↔ site visible in NetBox and Zabbix  
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
| Compliance | Cable/label diff; Circuit without `UW` |
| nbxsync automation | Template Rules; shared LLD parser; speed macros |
| Alerts & actions | Zabbix actions, media, **Zabbix** tags for routing (site class) — not NetBox port monitor-tags |
| Triggers / templates ops | Import, versioning, promote lab→prod; collision checks |
| Zero-touch | Checklist + configure script updates when Track A templates are ready |
| Sync / verify | Host sync, census, regression after template changes |

**Rule of thumb:** If the work is “make NetBox drive Zabbix,” it is Track B. If the work is “what should we monitor next on Extreme/Cato/Forti,” it is Track A (this plan).

---

## Cross-cutting lists

### Do now (Track A → Phases 0–2)

1. Foundations + **port label code list** (`USW` `US` `MON` `UW` | `N`; `UW` depth in Phase 5)  
2. **Device health templates:** EXOS verify + **build VOSS** + **build HiveOS AP**  
3. **Ports:** switch / server / MON / WAN scoped and monitored via labels  

### Do later (Track A → Phases 3–6)

4. Cato + FortiGate  
5. Services & SLA  
6. ISP/circuit monitoring (`UW` + Circuits)  
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
| ISP inventory + `UW` WAN alerts | Phase 5 |
| util% / LTE / maintenance / ICMP severity | Phase 6 |

---

## Port scoping (Phases 2 and 5)

| Phase | What we scope | Display codes |
|---|---|---|
| 2 | Fabric / AP / endpoints | `USW` `US` `MON` + optional SPEED; `UW`; `N` = note only |
| 5 | Internet circuits | `UW` (+ Circuit object); no absolute speed trigger |

**Design (Track A):** port label codes + which template / LLD mode watches them.  
**Automation (Track B):** shared parser; compliance; label tooling separate.  
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
  Budget 64; CLASS[-SPEED]-ID; USW(10G) US(10G) MON(1G) UW | N=note
  Access opt-in; Hybrid admin-down spares
  UW: link/flap/errors now; N: no action
  Label push tooling = separate; LAG/MLAG/MLT = later

TRACK A ORDER:
0 Foundations (port grammar)
1 Device health (EXOS + BUILD VOSS + BUILD HiveOS AP templates)
2 Ports — admin-up−N; access includes; hybrid; USW/US/MON/UW
3 Cato + FortiGate
4 Services & SLA
5 ISP circuit monitoring (UW + Circuits)
6 Optional profiles / util% / maintenance

NOW (A) = 0, 1, 2
LATER (A) = 3, 4, 5, 6
ALWAYS SEPARATE (B) = NetBox data + automation + alerts/triggers

GAPS TO BUILD IN PHASE 1 (A):
- Extreme VOSS by SNMP template
- HiveOS Access Point template
(nbxsync/checklist automation of those rules = Track B)
```
