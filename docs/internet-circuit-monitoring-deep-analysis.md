# Internet Circuit Monitoring — Deep Analysis & Recommendations

**Status:** Historical analysis of BASELINE DRAFT (Requirements + feasibility)  
**Stack context:** NetBox + nbxsync + Zabbix 7 + Extreme SNMP + Cato GraphQL (planned)  
**Purpose:** Stress-test the draft across scenarios; recommend a target design. Suitable for independent review / second-LLM verification.

> **Superseded as primary plan.** Prefer `docs/port-identity-foundation.md` and  
> `docs/internet-network-monitoring-plan.md` for phase order and port SoT.  
> Operator SoT = Extreme **display string only** (includes + exclusion `X:…`);  
> NetBox = inventory + compliance — **not** day-to-day NetBox interface monitor-tags.  
> This file keeps the scenario matrix / Cato / site-class analysis; §4 was aligned to display-string SoT.

---

## 1. What the draft gets right

1. **Split underlay vs SD-WAN** — ISP on Extreme and Cato overlay are different failure domains; alerting must distinguish them.
2. **Site classes (Production / Sales / Normal)** — depth matches criticality; avoids identical monitoring everywhere.
3. **Alerting + analysis** — history/trends/95th percentile are first-class, not afterthoughts.
4. **Feasibility honesty** — Extreme = native SNMP; Cato = custom HTTP agent (build + own it).
5. **Severity model** — “redundancy lost” (WARNING) ≠ “site offline” (HIGH) at Production.
6. **Open items parked** — thresholds, OIDs, API fields correctly deferred to technical design.

These should stay as non-negotiables in any revision.

---

## 2. Gaps and risks in the current draft

| Gap | Why it matters | Risk if ignored |
|---|---|---|
| No **circuit object / inventory model** | Metrics hang off “site” or “switch” without a circuit identity | Can’t map port ↔ ISP ↔ bandwidth ↔ class; wrong capacity % |
| No **port scoping** | Extreme LLD typically monitors many interfaces | Access-port flaps/noise; missed WAN ports if named oddly |
| **Bandwidth % of link speed** assumes correct `ifHighSpeed` / NetBox speed | Wrong speed → false 80%/90% alerts | Chronic WARNING or silent under-alert |
| Cato + Extreme **double-count** bandwidth | Both report throughput for related paths | Confusing graphs; capacity decisions from wrong series |
| No **backup/LTE tolerance** profile | Same loss/latency thresholds on primary fiber and LTE | Backup always “degraded” |
| No **maintenance / planned failover** handling | Failover event → WARNING always | Noise during change windows |
| ICMP listed as optional but not placed in severity model | Unclear when ping contradicts Cato/SNMP | Conflicting alerts |
| “Zabbix Services” mentioned lightly | Site-level status needs explicit composition rules | Dashboard red without actionable child |
| nbxsync inheritance not referenced | Today OS/templates merge by role/platform | Easy to bolt circuit monitoring on wrong template layer |
| No **auth/rate-limit/failure mode** for Cato poller | API outage ≠ site outage | Mass false HIGH if poller dies |
| Sales vs Normal almost same metrics | Differentiation unclear beyond hours | Two classes without two behaviors |
| No **multi-homing / asymmetric** cases | Active/active, unequal bandwidth, third circuit | Thresholds and “all circuits down” logic break |

---

## 3. Scenario matrix (every important case)

### 3.1 Topology scenarios

| ID | Scenario | Underlay source | Overlay source | What “healthy” means | Recommended monitoring |
|---|---|---|---|---|---|
| T1 | Prod DC: dual ISP on Extreme → Cato | Extreme WAN ports | Cato site/links | Both ISP up + Cato up + loss/lat OK | FULL separated |
| T2 | Prod: one ISP on Extreme, one ISP direct to Cato | Mixed | Cato | Both underlays up in *their* domains + Cato | FULL; don’t force Extreme items on Cato-only link |
| T3 | Prod: dual ISP both direct to Cato (no Extreme WAN) | — | Cato only | Cato links + HA | Cato-centric FULL (no fake Extreme section) |
| T4 | Sales: dual Socket links | — | Cato | Both links / HA OK | STANDARD |
| T5 | Sales: single Socket link | — | Cato | Link up | STANDARD without redundancy WARNING |
| T6 | Normal: single link, no HA | — | Cato | Connected | BASIC availability |
| T7 | LTE/backup secondary | Extreme and/or Cato | Cato | Primary OK; backup may be lossy | Separate threshold profile for backup |
| T8 | Circuit on switch but site class Sales | Extreme optional | Cato primary | Prefer Cato; Extreme only if documented | Don’t auto-FULL from “has Extreme” |
| T9 | Extreme switch monitored, but WAN is downstream firewall | Wrong device | Cato | Don’t treat access/uplink as ISP | Inventory must point to correct termination |
| T10 | Third-party / dark fiber / P2P not via Cato | Extreme or other CPE | — | Link + capacity only | Underlay-only profile |

### 3.2 Failure scenarios

| ID | Failure | Expected signal | Common false positive |
|---|---|---|---|
| F1 | One ISP port down, other up (Prod) | WARNING redundancy lost; site still 🟡 | HIGH outage |
| F2 | Both ISP ports down, Cato still “connected” briefly | Underlay HIGH + watch Cato | Trusting only Cato |
| F3 | Both ISP up, Cato disconnected | Overlay HIGH; underlay green | Blaming ISP |
| F4 | Failover active link A→B | WARNING info (Prod); suppress if maintenance | Ticket storm |
| F5 | High loss on backup only | WARNING only if backup in use / or softer threshold | Primary looks fine, backup always red |
| F6 | Utilization >80% on 1G port with wrong ifHighSpeed (reports 100M) | Fake capacity alert | — |
| F7 | Port flap during EXOS upgrade | Flap WARNING | No maintenance window |
| F8 | Cato API 401/429/timeout | **Integration** PROBLEM (not site outage) | All sites HIGH |
| F9 | Zabbix proxy loss to switch | SNMP unavailable; don’t invent ISP down without corroboration | — |
| F10 | ICMP to public IP fails; Cato OK (ICMP blocked) | Ignore or low-weight | False outage |
| F11 | Partial site: one building circuit down | Site service may stay green if poorly modeled | Missed blast radius |
| F12 | Asymmetric: 1G + 100M; 80% on 100M | Per-circuit capacity, not site average | — |

### 3.3 Operational scenarios

| ID | Event | Recommendation |
|---|---|---|
| O1 | New Prod site onboarding | NetBox: class + circuits; Extreme: set `W:…` display; bandwidth before Zabbix alerts enable |
| O2 | Circuit RMA / ISP change | Update NetBox Circuit + interface link; set/confirm display `W:…`; LLD/macro follows |
| O3 | Class change Sales→Prod | Unlock Extreme underlay + stricter thresholds + 24/7 |
| O4 | Planned failover test | Maintenance tag / suppress failover WARNING |
| O5 | Capacity planning monthly | 95th pct from Extreme *or* Cato per design—pick primary series per site type |
| O6 | Security blocks SNMP from proxy | Proxy placement / ACL checklist in runbook |

---

## 4. Architecture recommendation (target state)

### 4.1 Principles

1. **NetBox is SoT for Circuits / Providers / cables** (inventory). **Port monitor intent** on Extreme = **display string** (`W:…` for WAN). Zabbix renders and alerts; NetBox compliance reports drift.
2. **Never monitor “all switch ports” as internet circuits.** Fabric uses admin-up − `X:…`; access uses include codes; WAN uses `W:…`.
3. **Underlay and overlay alerts are separate problems** with separate severities and dashboards.
4. **Site class selects a monitoring profile**, not ad-hoc per ticket.
5. **Poller health ≠ site health** (Cato API / proxy / SNMP agent).
6. **Reuse nbxsync patterns**: Site Group / role for transport & OS; WAN scope from **display `W:…` + Circuit link** — don’t overload Device Role “Switch” with circuit logic. Do **not** use NetBox interface monitor-tags as a second operator SoT.

### 4.2 Suggested object model (NetBox)

Minimal viable:

- **Site** → custom field: `monitor_class` = `production` | `sales` | `normal`
- **Circuit** (NetBox Circuit) or equivalent: provider, CID, commit bandwidth, role (`primary`/`backup`), delivery (`extreme_wan` | `cato_direct` | `other`)
- **Interface** (on Extreme): linked to Circuit; operator sets display `W:…` on the switch (compliance checks the match)
- Optional: Cato site ID custom field on Site for API correlation

Zabbix host remains the switch (SNMP) and/or a logical “Site Internet” host / host group for Cato items—see 4.4.

### 4.3 Extreme / underlay

**Do:**

- Keep **Extreme EXOS by SNMP** (or Network Generic) for **switch health** (CPU, general IF LLD if desired).
- Add a **thin “ISP Underlay / WAN Port” layer**:
  - LLD filtered by display matching `^W:` (and/or macro derived from that)
  - Items: `ifOperStatus`, HC octets, errors, discards, flap detection
  - Triggers use **circuit commit speed** from macro `{$IF.BANDWIDTH}` (from NetBox), not blind trust in `ifHighSpeed` alone
- Scope: **only interfaces with `W:…` display** (linked to Circuit when inventory exists)

**Don’t:**

- Floor Network Generic + EXOS together on same host (icmpping collision—already learned).
- Alert Production capacity on access VLAN ports.

### 4.4 Cato / overlay

**Do:**

- One **custom Zabbix template**: HTTP agent → GraphQL (`accountSnapshot` + `accountMetrics`).
- LLD by **site** (and per-link discovery).
- Dependent items for loss/latency/jitter/bytes.
- Separate triggers: site disconnected, tunnel down, failover, SLO breach.
- **Internal items**: last successful poll, HTTP status → trigger “Cato collector degraded” on a **meta host**, not on every site.

**Host placement options (pick one in tech design):**

| Option | Pros | Cons |
|---|---|---|
| A. Items on a per-site “logical host” | Clean site view | Extra hosts to sync/manage |
| B. Items on Cato “account” host + LLD | Fewer hosts | Permissions/dashboards harder |
| C. Attach to primary switch host | Fewer objects | Mixes underlay device with overlay SaaS |

**Recommendation:** **A** for Production (clear service tree); **B** acceptable for Sales/Normal if cost matters.

### 4.5 ICMP

- Optional **cross-check only** for Production.
- Never sole outage criteria if ICMP is filtered.
- Weight: inform or low severity unless both ICMP and Cato/SNMP agree.

### 4.6 Zabbix Services / site status

Compose explicitly:

```
Site Internet (Production)
├── Underlay ISP-A (Extreme port)
├── Underlay ISP-B (Extreme port)
└── Cato SD-WAN (site + links)
```

Rules:

- 🔴 if (all underlays down) OR (Cato disconnected) — tune with dependency
- 🟡 if exactly one underlay down OR Cato degraded metrics
- Collector failure → soft state / separate service, not 🔴 site

### 4.7 Alert routing

| Class | Hours | Page on |
|---|---|---|
| Production | 24/7 | Redundancy loss, sustained loss/lat, outage |
| Sales | Business + optional on-call for outage | Outage, strong degradation |
| Normal | Business | Outage / persistent degradation |

Use NetBox `monitor_class` → Zabbix tag → action conditions (fits lean-tag philosophy: tag carries **routing**, not a copy of hostgroups).

---

## 5. Threshold strategy (better than one global table)

Keep draft numbers as **defaults**, then overlay profiles:

| Profile | Loss WARN/HIGH | Latency WARN | Notes |
|---|---|---|---|
| Fiber primary | 2% / 5%, 5 min | 150 ms | Draft OK |
| Fiber backup (standby) | Higher or alert only when active | Higher | Avoid permanent WARN |
| LTE / cellular | 5% / 10%+, longer window | Higher | Always softer |
| Utilization | 80% / 15m WARN; 90% / 5m WARN | — | Based on **commit** bandwidth |

**Flap:** ≥3 in 5 min WARN — OK; suppress in maintenance.

**Discords:** prefer rate vs counter growth; ignore one-shot blips.

---

## 6. What to improve in the written baseline (doc edits)

1. Add **port/circuit scoping** as a hard requirement — **display-string codes** (see foundation), not NetBox monitor-tags.
2. Add **scenario table**: T1–T7 at least (mixed terminations, Cato-only Prod, LTE).
3. Add **collector failure** as distinct from site outage.
4. State **primary analysis series** per class (Extreme vs Cato bytes)—avoid dual graphs without legend.
5. Clarify Sales vs Normal **behavioral** difference (HA required? failover WARN? metrics ◐).
6. Require **NetBox circuit inventory fields** before “FULL” profile enables.
7. Mention **maintenance / suppress** for failover tests.
8. Point Extreme section at **display-filtered WAN ports (`W:…`)**, not “the switch.”
9. Align with existing nbxsync lessons: no duplicate ICMP templates; interface requirements; Site Group proxies.
10. Split roadmap: **Phase A Extreme WAN**, **Phase B Cato API**, **Phase C Services/SLA**—don’t block A on B.

---

## 7. Phased delivery (best path)

### Phase A — Underlay (fast value, native tooling)

- NetBox: class + Circuits + bandwidth; Extreme display `W:…` on WAN ports
- Zabbix: WAN LLD on `^W:` + triggers (link, util, errors, flaps)
- Compliance: Circuit present but display not `W:…` (or reverse)
- Dashboards: per-site WAN ports
- No Cato dependency

### Phase B — Cato overlay

- HTTP agent template + LLD sites/links
- Meta host for API health
- Correlate on dashboards with Phase A

### Phase C — Service tree & reporting

- Zabbix Services composition
- SLA for Production
- 95th percentile capacity report

### Phase D — Tuning

- Per-circuit profiles (LTE/backup)
- Action schedules by class
- Threshold review after 30–60 days of history

---

## 8. Anti-patterns to reject

1. Monitor all Extreme interfaces as “internet.”
2. Single alert “site network down” mixing ISP + Cato + switch reboot.
3. Capacity % without trusted bandwidth SoT.
4. Cato API failure → page every site.
5. Identical thresholds on LTE backup and primary fiber.
6. Building continent hostgroups only for this use case (unrelated; keep location nesting as today).
7. Per-device template assignment as mass pattern (conflicts with your zero-touch model).
8. Waiting for perfect Cato field list before starting Extreme WAN scoping.

---

## 9. Fit with current nbxsync / zero-touch work

| Existing capability | Use for circuits? |
|---|---|
| Site Group → proxy/server | Yes — poll from right place |
| Template Rules (platform EXOS) | Switch OS/health template |
| Manufacturer ∧ role rules | Not for WAN ports |
| Interface / OOB patterns | Conceptual cousin to “special ports” |
| Lean Zabbix tags (`critical`, `snmp`) | Add `monitor_class` for **alert routing** sparingly — not NetBox port monitor-tags |
| Hostgroups Sites/Roles/OS | Dashboards by site; **don’t** encode ISP in Roles |

**New work is mostly:** Circuit inventory + Extreme `W:…` display + Zabbix LLD filters + Cato template—not a redesign of zero-touch.

---

## 10. Decision summary (for cross-LLM / human verification)

Copy block below for independent review.

```
CLAIM: The draft’s split (Extreme underlay vs Cato overlay), site classes, and
alerting+analysis dual goal are correct and should be kept.

MUST ADD:
1) Scope Extreme monitoring via display codes (WAN = W:…); fabric uses
   admin-up minus X:… excludes; access uses include codes — not all ports.
2) Circuit inventory: site class, termination type, bandwidth, primary/backup.
3) Treat Cato API/proxy failure as collector fault, not mass site outage.
4) Separate threshold profiles for primary fiber vs backup/LTE.
5) Phase delivery: Extreme WAN first, Cato second, Services/SLA third.
   (Authoritative phase order: see docs/internet-network-monitoring-plan.md)

MUST NOT:
1) Use full interface LLD as “internet circuit monitoring.”
2) Collapse underlay+overlay into one undifferentiated alert.
3) Trust ifHighSpeed alone for utilization without NetBox commit speed.
4) Block Phase A on unfinished Cato API field discovery.
5) Use NetBox interface monitor-tags as a second day-to-day SoT.

BEST TARGET ARCHITECTURE:
- Operator SoT: Extreme display string (W:… for WAN; X:… excludes on fabric).
- NetBox: monitor_class + Circuit + compliance + bandwidth CF.
- Zabbix: EXOS health template + filtered WAN underlay template;
  custom Cato HTTP/LLD template; optional ICMP cross-check;
  Services tree composing underlay+overlay; lean Zabbix tags for alert routing.
- Align with existing nbxsync inheritance; don’t assign circuit templates
  manufacturer-wide or per-random-device.

SUCCESS METRICS:
- Prod redundancy loss visible without paging as full outage.
- No access-port flap noise in ISP alert stream.
- Capacity graphs use correct denominator (commit bandwidth).
- Cato outage vs ISP outage distinguishable on dashboard.
- New site: classify + document circuits in NetBox + set W:… on switch
  → monitoring follows.
```

---

## 11. Recommended “best” configuration (one paragraph)

Classify every site in NetBox; document each internet circuit and the Extreme interface that terminates it; set display `W:…` on that port (operator SoT); monitor only those ports via SNMP with bandwidth from inventory; use NetBox for compliance drift, not a second monitor edit; monitor Cato separately via a maintained GraphQL HTTP-agent template with its own collector health; compose site status in Zabbix Services so Production warns on lost redundancy and goes critical only on true site internet failure; tune backup/LTE softer; roll out underlay before overlay so the program delivers value without waiting on API reverse-engineering.
