# Internet / Network Monitoring — Implementation Plan

**Status:** Implementation plan (reordered per stakeholder)  
**Priority order:** Device health → uplinks/ports → Cato & FortiGate → Services/SLA → ISP circuit monitoring  
**Stack:** NetBox + nbxsync + Zabbix 7 · Extreme EXOS / VOSS · HiveOS APs (XIQ Pilot) · (later) Cato · FortiGate

**Port identity (locked):** Extreme **display string only** (≤15 codes) — includes + **exclusion `X:…`**.  
See `/opt/cursor/artifacts/PORT_IDENTITY_FOUNDATION_ANALYSIS.md`.  
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
GRAMMAR: CLASS[-SPEED]-ID   (no colon; atomic CLASS)
CLASSES: UC UD UA UP MON W TMON | X (X-<note> optional; reason in description)
NO IDR class — iDRAC = MON

DEFAULTS: UC=UD=UA=10G | UP=1G | MON=1G
TOKENS: 100M 1G 2G5 5G 10G 25G 40G 100G 400G

EXAMPLES
  UD-swd14 / UA-swa08     expect 10G both (standard access↔dist)
  UD-1G-swd2 / UA-1G-swa2 expect 1G both (legacy, symmetric)
  UP-ap3f07               expect 1G
  MON-10G-esx1            ESXi 10G
  MON-idr03               iDRAC (MON, not IDR)
  TMON / TMON-guest       metrics only — no alerts; compliance lists
  X / X-<note>            exclude (reason in NetBox description)

ZABBIX: change(ifHighSpeed) safety net + absolute expect when labeled
  TMON = discover/collect only (no triggers)
LAG: speed expect on members only — not aggregate sum
HYBRID SUBSIDIARY (core∩access): admin-down spares; X only if up-but-uninteresting
GENERATOR: authoritative overwrite on managed ports
PROTECT: NetBox display_protect → skip hand-set ports
NETBOX: generate/push; description = prose; no tags
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
4. **One operator path for port labels:** prefer NetBox **generate/push** display string; no dual-edit with monitor tags.  
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
| P0.3 | **Grammar + defaults locked:** `UC/UD/UA=10G`, `UP/MON=1G`; hyphen grammar; no `IDR`; LAG + change-detect rules |
| P0.4 | Role matrix: fabric admin-up−`X`; access include-only; **hybrid = admin-down spares + X only if up-but-uninteresting** |
| P0.5 | Pilot lists: 1–2 EXOS, 1 VOSS, sample APs |
| P0.6 | Site class field optional (`production`/`sales`/`normal`) — same metrics for now (alert routing later = Track B) |

**Verify exit**

- [ ] Platform counts known  
- [ ] Include + exclusion grammar agreed (`UC/UD/UA/UP/MON/TMON` vs `X`; WAN = `W`)  
- [ ] Defaults: UC=UD=UA=10G (symmetric); UP=MON=1G  
- [ ] Role matrix: fabric / access / **hybrid (admin-down spares, not X-fill-all)**  
- [ ] Generator authoritative + **`display_protect`** agreed  
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

**Objective:** Fabric / AP / endpoint ports monitored with universal `CLASS[-SPEED]-ID` grammar; exclude via `X`; LAG rules explicit.

**SoT on box:** display string (≤15) as **derived cache** — preferably **generated from NetBox**. Zabbix reads `ifAlias`.

### Grammar

```
CLASS | CLASS-ID | CLASS-SPEED-ID
CLASS = UC|UD|UA|UP|MON|W|TMON|X
SPEED = 100M|1G|2G5|5G|10G|25G|40G|100G|400G
```

No colon. No separate `IDR` class — **iDRAC = `MON`**.

### Class defaults → Zabbix expected

| CLASS | Default | Notes |
|---|---|---|
| `UC` `UD` `UA` | **10G** | Same family — access↔dist **symmetric** (no token on standard 10G) |
| `UP` | **1G** | AP; use `2G5`/`5G` token when needed |
| `MON` | **1G** | Server / ESX / storage / **iDRAC**; `MON-10G-…` when 10G |
| `W` | — | **No** absolute speed trigger |
| `TMON` | — | **Temp monitor:** items/graphs only — **no triggers**; compliance lists `TMON*` for audit |

Legacy 1G access↔dist: `UD-1G-…` **and** `UA-1G-…` (token both ends).

### Examples

| Display | Expect |
|---|---|
| `UD-swd14` / `UA-swa08` | 10G / 10G |
| `UD-1G-swd2` / `UA-1G-swa2` | 1G / 1G |
| `UP-ap3f07` | 1G |
| `UP-2G5-ap07` | 2.5G |
| `MON-10G-esx1` | 10G |
| `MON-idr03` | 1G (iDRAC) |
| `TMON` / `TMON-guest` | — (items only, **no alerts**) |
| `X` / `X-<note>` | excluded (description = why) |

### Zabbix triggers (Phase 2)

1. Link down / flap / **errors-CRC** (narrow speed-only win is not enough).  
2. **`change(ifHighSpeed)`** while oper-up for ≥5m — **universal safety net** (not on `TMON`).  
3. Absolute `ifHighSpeed ≠ expected` for ≥5m where `UC|UD|UA|UP|MON` labeled.  
4. **`TMON`:** LLD items/graphs only — **no triggers / no problems**.  
5. **LAG:** absolute speed expect on **members only**; never compare aggregate sum to member expected.

### Excludes

Label **`X` / `X-<note>`**; reason in NetBox **description**.

### Subsidiary hybrid (core∩access)

Same LLD as fabric (`admin-up AND NOT X`). **Do not X-fill every port** (config bloat / cfgit churn).

- **Spares / unused** → **admin-down** (preferred).  
- **Admin-up but must not alert** → `X` / `X-<note>` + description.  
- **Monitor** → non-X (`empty` / `MON` / `TMON` / `UP` / `UC|UD|UA` / `W`).

### Generator authority

- Generator **overwrites** on-box display on **managed** interfaces.  
- NetBox **`display_protect`** → skip that interface (deliberate hand-set).  
- Compliance diffs managed ports; lists protect-set separately.

### Work packages

| ID | Work | Detail |
|---|---|---|
| P2.1 | Lock grammar + defaults + LAG rule | As above |
| P2.2 | Generator design (Track B handoff) | Authoritative push; **`display_protect`** skip; dry-run/apply |
| P2.3 | LLD contract | One shared parser; ifAlias; macros |
| P2.4 | Port template | Down/flap/errors + change + absolute expect (settled) |
| P2.5 | Exclude via `X` | Only admin-up uninteresting ports — not every spare |
| P2.6 | Access include / fabric admin-up | Unused → **admin-down** hygiene |
| P2.7 | `MON` endpoints incl. iDRAC | No IDR class |
| P2.8 | Compliance = **diff** + **`TMON*` inventory** + protect list | Managed vs live; list `display_protect` |
| P2.9 | AP dual view | `UP-…` + HiveOS |
| P2.10 | Canaries | 10G symmetric, 1G symmetric, MON/iDRAC, LAG members, `X` |
| P2.11 | Hybrid subsidiary profile | admin-down spares; `X` only if up-but-uninteresting |
| P2.12 | Canary hybrid switch | Client ports alert; spares admin-down; uplink/WAN/AP OK |

### Scoping options (locked)

| Option | Role |
|---|---|
| `CLASS[-SPEED]-ID` on ifAlias | On-box cache for Zabbix |
| NetBox generate/push | **Preferred SoT path** |
| Hand-type grammar day-to-day | Emergency only |
| Monitor tags | **Reject** |
| Learn-baseline as primary absolute expect | **Reject** |
| Change-detect safety net | **Required** |
| Colon grammar / `IDR` class | **Reject** |

### Exit criteria

- [ ] Symmetric 10G `UD`/`UA` without tokens on both ends  
- [ ] Symmetric 1G exception tokens both ends  
- [ ] `MON-idr…` works (no IDR class)  
- [ ] LAG members clean; aggregate no false speed WARN  
- [ ] `X` / `X-<note>` excludes work; description holds reason  
- [ ] Change-detect catches unlabeled degrade  
- [ ] Generator dry-run + compliance diff on canary  
- [ ] Hybrid subsidiary: admin-down spares; `X` only if up-but-uninteresting  
- [ ] Generator overwrite + `display_protect` skip verified  
- [ ] `TMON` collects metrics with **zero** triggers; compliance lists all `TMON*`  

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
| Compliance | Cable/display diff; **list all `TMON*`** for audit; Circuit without `W` |
| nbxsync automation | Template Rules; generate/push display; shared LLD parser; speed macros |
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
| 2 | Fabric / AP / MON | `UC/UD/UA/UP/MON/TMON` + optional SPEED; exclude `X` |
| 5 | Internet circuits | `W` (+ Circuit object); no absolute speed trigger |

**Design (Track A):** display-string codes + which template / LLD mode watches them.  
**Automation (Track B):** NetBox generate/push display; shared parser; compliance **diff**.  
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
  CLASS[-SPEED]-ID (no colon); no IDR (iDRAC=MON); TMON=metrics no alerts
  Defaults: UC=UD=UA=10G | UP=1G | MON=1G
  Tokens: 100M 1G 2G5 5G 10G 25G 40G 100G 400G
  Zabbix: change(ifHighSpeed) + absolute expect; LAG=members only
  Compliance lists all TMON* for audit (no dates on switch)
  NetBox generate/push preferred; description=prose; no monitor-tags

TRACK A ORDER:
0 Foundations (grammar + defaults + LAG + generate path)
1 Device health (EXOS + BUILD VOSS + BUILD HiveOS AP templates)
2 Ports — admin-up−X; access includes; hybrid=admin-down spares;
   generator authoritative + display_protect; MON incl iDRAC; TMON no alerts
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
