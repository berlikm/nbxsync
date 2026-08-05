# Port identity foundation (Zabbix focus)

**Status:** Locked design direction (revised — length canary + parser hardening)  
**Operator-visible SoT on box:** Extreme port label → SNMP **`ifAlias`** (derived cache from NetBox)  
**Scope:** Zabbix port LLD + speed expectation + excludes  
**NetBox:** inventory SoT (cables, roles, `interface.speed`) → **authoritative generator**; description = human prose  
**Related plan:** `docs/internet-network-monitoring-plan.md` (Track A)

---

## 0. Gate before locking length (canary)

EXOS documentation (32.7.x) distinguishes:

| Field | Documented size | Notes |
|---|---|---|
| `display-string` | historically ~**20** (not 15) | Older field |
| `description-string` | up to **255** | Separate field; guide ties extended use to **ifAlias** |
| SNMP `ifAlias` | **64** default (`config snmp ifmib ifalias size extended` for more) | What Zabbix actually reads |

**Must verify on canary EXOS + VOSS before fleet design freezes on length:**

1. Set `description-string` and/or `display-string`; read `ifAlias`.  
2. Confirm which field wins when both are set.  
3. Confirm usable length (20 vs ~64 vs more) on **your** code trains.

Until canary passes, treat **short profile (≤20)** as the safe fallback. After ~64 confirmed, use **extended profile** as primary (§2.1).

Plant labels like `MLAG_MGMT01_p51` / `Alternative_ISC` (exactly 15) look **hand-fitted to an assumed limit**, not evidence of a hard 15-char platform cap.

---

## 1. Locked decisions

1. **Grammar:** `CLASS[-SPEED]-ID` — atomic CLASS, **hyphen** only.  
2. **No `:` in labels** — EXOS `description-string` **forbids** `:`, space, `"`, `<`, `>`, `&`; first char alphanumeric. Colon grammar was **invalid**, not merely awkward. Also avoids `slot:port` collision.  
3. **No special `IDR` class** — iDRAC = **`MON`**.  
4. **Class speed defaults (fallback when token absent):** `UC`/`UD`/`UA` → **10G**; `UP`/`MON` → **1G**. Verify plant mix before treating defaults as rare (§9).  
5. **Extended profile (when ifAlias ~64+):** **always emit SPEED token**; longer far-end IDs; controlled `X-<NOTE>` vocabulary.  
6. **Short profile (fallback):** token only when ≠ default; short IDs; `X` or short `X-<NOTE>`.  
7. **Generator authoritative** on managed ports (overwrites on-box). NetBox **`display_protect`** skips hand-sets (§8).  
8. **Parse states:** `PARSED` | `EMPTY` | **`UNPARSEABLE`** — never treat legacy junk as empty (§5.1).  
9. **Access LLD is opt-in** — change-detect safety net does **not** cover unlabeled/typo’d access ports (§5, §11).  
10. **Hybrid subsidiary:** admin-down spares; `X` only on up-but-uninteresting — **not** X-fill-all (§6.1).  
11. **LAGs:** speed expect on **members** only (§7).  
12. **No NetBox tags** for monitor/speed intent.  
13. Track B: generate/push, compliance diff, shared parser, ingest-loop check (§8.1).

---

## 2. Universal grammar

```
CLASS
CLASS-ID
CLASS-SPEED-ID
```

| Piece | Rules |
|---|---|
| **CLASS** | Atomic token from vocabulary |
| **SPEED** | Canonical tokens only (`2G5` not `2.5G` — no dots) |
| **ID** | `[A-Z0-9-]+` after normalize; length per profile |
| **Case** | Generator pushes **UPPERCASE**. Parser is **case-insensitive**. Compliance compares uppercase(normalized live) vs generated |
| **Forbidden** | `:` space `"` `<>` `&` and leading non-alnum (EXOS description-string rules) |

### 2.1 Length profiles

| Profile | When | SPEED | ID | `X` notes |
|---|---|---|---|---|
| **Extended** (preferred after canary) | ifAlias usable ~**64+** | **Always emit** token | Real far-end shortnames OK | Controlled: `X-STK`, `X-ISC`, `X-MLAG`, `X-SPN`, `X-OOB`, `X-OTH` |
| **Short** (fallback) | old/limited platforms | Emit only if ≠ class default | Machine-short | `X` or short `X-<NOTE>`; full why in NetBox description |

Always-emit (extended) makes class defaults **display documentation only** for generation — changing a default later does not require rewriting every label. Hand-typed fallback still uses defaults when token omitted.

### 2.2 Parser (two branches — no speed on `X`)

```
# Exclude — note is NEVER a speed token
^X(-(?<xnote>STK|ISC|MLAG|SPN|OOB|OTH|[A-Z0-9]{1,12}))?$

# Include
^(?<class>UC|UD|UA|UP|MON|W|TMON)(-(?<speed>100M|1G|2G5|5G|10G|25G|40G|100G|400G))?(-(?<id>[A-Z0-9-]+))?$
```

(All matching after uppercase normalize.)

**`X` notes:** controlled vocabulary when **generated**. Diff rule: generated `X` / `X-STK` / … must match exactly; do not treat arbitrary hand `X-spare` as equal to generated `X` unless protect-set. Prefer generator-owned notes only.

**Source field:** Zabbix reads **`IF-MIB::ifAlias`**. Push path must target the Extreme field that actually populates ifAlias on that OS version (`description-string` vs `display-string` — canary).

---

## 3. Class vocabulary

### 3.1 Include / monitor

| CLASS | Meaning | Default if token omitted | Absolute speed trigger? | Now (Phase 2) |
|---|---|---|---|---|
| `UC` | Toward **core** | 10G | Yes | link / flap / errors + speed |
| `UD` | Toward **dist** | 10G | Yes | same |
| `UA` | Toward **access** | 10G | Yes | same |
| `UP` | Toward **AP** | 1G | Yes | same |
| `MON` | Endpoint (server, ESX, storage, **iDRAC**, client drop) | 1G | Yes | same |
| `W` | WAN / ISP | — | **No** (Phase 5 bandwidth) | **Yes:** link-down, flap, errors — not a monitoring hole |
| `TMON` | Temp watch | — | No | items yes; triggers: **link-down INFO only** optional; no WARN/CRITICAL (§3.3) |

### 3.2 Exclude — class `X`

| Display | Meaning |
|---|---|
| `X` | Excluded |
| `X-STK` / `X-ISC` / `X-MLAG` / `X-SPN` / `X-OOB` / `X-OTH` | Excluded + controlled note (extended / generated) |

These are **notes on class `X`**, not separate classes. NetBox description may still carry prose detail.

### 3.3 `TMON` — temp monitor (not a black hole)

| | |
|---|---|
| **Display** | `TMON` or `TMON-<ID>` |
| **Items** | Yes (graphs/history) |
| **Triggers** | Prefer **link-down at INFO** (visible, non-paging). No speed WARN / no change-detect PROBLEM. |
| **Audit** | Compliance lists **all `TMON*`** — owner + **review cadence** (e.g. weekly ops review) |
| **Cleanup** | Clear label or promote to `MON`/`UP`/… |
| **Why/until** | NetBox description — not dated on-box strings |

---

## 4. Speed tokens

| Token | Mbps |
|---|---|
| `100M` | 100 |
| `1G` | 1000 |
| `2G5` | 2500 |
| `5G` | 5000 |
| `10G` | 10000 |
| `25G` | 25000 |
| `40G` | 40000 |
| `100G` | 100000 |
| `400G` | 400000 |

**Extended profile:** always `CLASS-SPEED-ID` (e.g. `UD-10G-SWD14`, `UA-1G-SWA08`).  
**Short profile:** omit SPEED when it matches class default.

`UA=10G` / `UD=10G` symmetry stands; if plant majority is still 1G access uplinks, always-emit from `interface.speed` carries the truth — count NetBox speeds before stressing about hand-typed defaults.

---

## 5. Zabbix resolution

```
1) Classify label: EMPTY | PARSED | UNPARSEABLE
2) UNPARSEABLE → do not treat as EMPTY; exclude from “customer uplink” assumes;
                 compliance inventory + migrate (§5.1)
3) PARSED class X → skip port alerts
4) Else include per role LLD rules (§6)
5) If discovered AND class in {UC,UD,UA,UP,MON,W}:
      link-down / flap / errors (W included)
6) If discovered AND class in {UC,UD,UA,UP,MON}:
      absolute expect = SPEED token OR class default
      ifHighSpeed ≠ expected for ≥5m while oper-up → WARNING
7) If discovered AND not TMON:
      change(ifHighSpeed) vs last *stable up* value for ≥5m → WARNING
      suppress in maintenance windows (§5.2)
8) TMON: items + optional link-down INFO only
```

**Access safety net limit:** change-detect and absolute-expect only run on **discovered** items. Access LLD is opt-in regex — **typo / missing label ⇒ no items ⇒ no safety net**. Mitigation = NetBox compliance diff (+ generator). Say this plainly: safety net covers **fabric + hybrid discovered ports**, not silent access opt-in failures.

### 5.1 `UNPARSEABLE` (legacy plant)

Existing labels (`ISC`, `ALTERNATIVE_ISC`, `ESX40_CT1_ETH0`, `GFL-ACPO01`, `MLAG_MGMT01_P51`, …) often **do not parse**.

| State | Fabric / hybrid meaning | Access meaning |
|---|---|---|
| `EMPTY` | Monitored (admin-up) | **Not** monitored |
| `PARSED` include | Per class | Per class |
| `PARSED` `X` | Excluded | Excluded |
| **`UNPARSEABLE`** | **Not** “empty” — do **not** auto-monitor as normal uplink; quarantine via compliance until migrated | Same — not an include |

Run a **migration inventory** of live ifAlias values → PARSED / EMPTY / UNPARSEABLE counts before enabling absolute-expect triggers.

### 5.2 Maintenance / settle

- Compare speed change against last **stable oper-up** sample, not a single previous poll during negotiation.  
- **Maintenance windows** suppress change-detect and absolute-expect WARNs (SFP swap, reload, LAG member work).  
- Rollout gate: do **not** enable absolute-expect for a site until generated-vs-live diff is clean (first push otherwise = WARN storm).

---

## 6. Role × LLD

| Device role | LLD |
|---|---|
| **Core / Dist / Mgmt** | Admin-up AND NOT (class `X` OR UNPARSEABLE-as-exclude policy) |
| **Access** | Display matches include classes only |
| **Subsidiary hybrid** | Same as fabric LLD; labeling per §6.1 |
| **AP** | Device health — not switch-port fabric LLD |

**Hygiene (not LLD logic):** unused ports → **admin-down** (fabric and hybrid).

**Empty on hybrid:** generator **must not** leave monitored hybrid client ports empty — push `MON-<ID>` (or `TMON-<ID>`). Then **empty = unmanaged/unknown** is uniform and compliance-visible. (Fabric may still allow empty = monitored during migration; prefer generating includes there too.)

### 6.1 Subsidiary hybrid — no X-fill-all

Pushing `X` on every port = per-port config lines, save/sync churn, noisy cfgit diffs. **Rejected.**

```
1) Spares / unused              → admin-down
2) Admin-up but uninteresting   → X / X-<NOTE>
3) Monitor                      → non-X (prefer MON-<ID>, never empty)
```

Same LLD outcome (`admin-up AND NOT X`), fraction of the config.

---

## 7. LAG / LACP / MLAG bundles

| Rule | Decision |
|---|---|
| Speed expect | **Members only** (per-member speed) |
| Aggregate ifIndex | Up/down / member-count — **no** `ifHighSpeed ≠ expected` on aggregate sum |
| Peer-link | `X-MLAG` / `X` — not a fabric uplink expect |

---

## 8. Generate from NetBox (authoritative)

```
NetBox → generator (dry-run/apply) → Extreme field that drives ifAlias
       → Zabbix polls ifAlias
```

**Authority:** managed interfaces → generator **overwrites** on-box label. CLI edits on managed ports are not kept.

**Protect:** NetBox `display_protect=true` → generator **skips** that interface. Compliance lists protect-set separately.

| Input | Output |
|---|---|
| `display_protect` | Skip |
| Hybrid spare | admin-down |
| Hybrid up-but-uninteresting | `X` / `X-STK` / … |
| Hybrid/client monitor | `MON-<ID>` (not empty) |
| Cable + speed | `UD-10G-…` / `UA-1G-…` (extended: always token) |
| iDRAC / ESX / storage | `MON-…` |
| WAN | `W-…` |

### 8.1 Ingest loop hazard

If `nbx-ingestor` / XIQ-SE (or similar) writes **ifAlias → NetBox `interface.description` or `label`**, enabling push creates a cycle: NetBox → ifAlias → NetBox.

**Before push:** confirm ingest does **not** clobber generator inputs. Decide one mapping: e.g. live ifAlias → NetBox `label` for **observation only**, or stop ingest of ifAlias into fields the generator owns. Align with any existing `display-string → Interface.label` collection so efforts do not collide.

---

## 9. Worked examples (extended profile, UPPERCASE)

| Scenario | Display | Expect |
|---|---|---|
| Access↔dist 10G | `UD-10G-SWD14` / `UA-10G-SWA08` | 10G |
| Access↔dist 1G | `UD-1G-SWD2` / `UA-1G-SWA2` | 1G |
| AP 1G | `UP-1G-AP3F07` | 1G |
| AP 2.5G | `UP-2G5-AP07` | 2.5G |
| ESXi 10G | `MON-10G-ESX01` | 10G |
| iDRAC | `MON-1G-IDR03` | 1G |
| WAN | `W-SC1` | link/flap/errors only |
| Temp | `TMON-GUEST` | items + INFO link-down |
| Exclude stack | `X-STK` | excluded |
| Legacy junk | `ALTERNATIVE_ISC` | **UNPARSEABLE** → migrate |

Short-profile equivalents omit default tokens and shorten IDs (`UD-SWD14`, `X`, …).

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| Designing for fake 15-char cap | Canary ifAlias length; extended profile |
| Access typo = silent | Compliance diff; state safety net does **not** cover access opt-in |
| Legacy label monitored as uplink | `UNPARSEABLE` ≠ empty |
| Empty ambiguous by role | Hybrid: never empty for monitored — use `MON-<ID>` |
| X-fill config bloat | admin-down spares |
| Manual edit lost | Expected; `display_protect` |
| ifAlias ingest loop | Confirm before push (§8.1) |
| TMON black hole | INFO link-down + review cadence |
| `W` looks unmonitored | Phase 2: link/flap/errors now |
| Change-detect during changes | Stable-up baseline + maintenance suppress |
| First-push WARN storm | Gate absolute-expect on clean diff |

---

## 11. Verify checklist

- [ ] Canary: `description-string` / `display-string` → ifAlias on EXOS + VOSS  
- [ ] Choose extended (~64) vs short profile  
- [ ] Uppercase push; case-insensitive parse; split `X` regex  
- [ ] `UNPARSEABLE` inventory + migration plan  
- [ ] Access: document safety-net does **not** cover missing labels  
- [ ] Hybrid: admin-down spares; `MON-<ID>` not empty; no X-fill-all  
- [ ] Generator authoritative + `display_protect`  
- [ ] Ingest loop check (ifAlias ↛ generator inputs)  
- [ ] `W` = link/flap/errors; `TMON` review cadence + INFO link-down  
- [ ] LAG members-only; maintenance suppress; rollout gate on clean diff  

---

## 12. Summary

```
CANARY FIRST: ifAlias usable length (20 vs ~64+) on EXOS+VOSS
  Extended: always SPEED token, longer IDs, X-STK/X-ISC/X-MLAG notes
  Short fallback: omit default tokens, short IDs

GRAMMAR: CLASS[-SPEED]-ID  UPPERCASE  no colon (EXOS-forbidden)
CLASSES: UC UD UA UP MON W TMON | X (+ controlled X-NOTE)
NO IDR — use MON

PARSE: EMPTY | PARSED | UNPARSEABLE (legacy ≠ empty)
ACCESS: opt-in LLD — change-detect does NOT cover missing labels
HYBRID: admin-down spares; X only if up-but-uninteresting; MON-ID not empty
W NOW: link/flap/errors (speed later Phase 5)
TMON: items + INFO link-down; compliance list + review cadence

GENERATOR authoritative overwrite | display_protect skip
CHECK ingest loop before push
LAG: expect on members only
GATE absolute-expect until diff clean
```
