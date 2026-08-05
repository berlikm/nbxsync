# Port identity foundation (Zabbix focus)

**Status:** Grammar **locked** at 64 · always-emit SPEED · `X-STK`/`X-ISC`/`X-MLAG` restored.  
**Remaining blockers:** two SNMP canaries (OID source + EXOS field precedence) — not grammar.  
**Operator-visible SoT on box:** Extreme port label → SNMP (prefer **`ifAlias`**; VOSS OID canary open)  
**Scope:** Zabbix port LLD + speed expectation + excludes  
**NetBox:** inventory SoT (cables, roles, `interface.speed`) → **authoritative generator**; description = human prose  
**Related plan:** `docs/internet-network-monitoring-plan.md` (Track A)

---

## 0. Label length & ifAlias (EXOS + VOSS → **64 common**)

### Confirmed sizes

| Field | Size | Confirmed by |
|---|---|---|
| VOSS / Fabric Engine port `name` | **0–64** (`WORD<0-64>`) | ✅ **CLI help** (authoritative) |
| VOSS MLT `name` | 0–64 | ✅ docs |
| EXOS `display-string` | **20** | ✅ EXOS 32.7 guide |
| EXOS `description-string` | **255** | ✅ EXOS 32.7 guide |
| EXOS SNMP `ifAlias` | **64** default; `extended` → 255 | ✅ EXOS 32.7 guide |

**Common denominator = 64** (not 15). Cap the grammar at **64** → no `configure snmp ifmib ifalias size extended` needed. Plant strings of exactly 15 were legacy hand-fitting, not a vendor cap.

**Hyphen, not colon:** EXOS `description-string` forbids `:` (safe union also bans space `"` `<>` `&` `?`; first char alphanumeric). Colon grammar is **CLI-invalid**.

**VOSS generator tip:** CLI also exposes `name port <portlist>` for multi-port set from one context — prefer this when applying the same label to several ports.

**Realistic label examples at 64:** `UD-10G-CH-ZRH-ZH4-DIST01` (24) fits easily → **always-emit SPEED**, real far-end names, controlled `X-STK` / `X-ISC` / `X-MLAG`.

### Still open (SNMP canaries — do not block grammar)

Grammar revision is **already landed** (this doc). Paste canary results below when available; they only update **push field / Zabbix source OID**.

**1. Does VOSS `name` populate SNMP `ifAlias`?**  
Set a unique name, then:

```text
interface gigabitEthernet 1/20
name A123456789B123456789C123456789D123456789E123456789F123456789G123
```

```bash
snmpwalk -v2c -c <ro> CH-STA-L50-L01-CORE01 1.3.6.1.2.1.31.1.1.1.18 | grep A123
```

If empty, check `ifDescr` (`1.3.6.1.2.1.2.2.1.2`). If VOSS puts `name` in **ifDescr** instead of **ifAlias**, Zabbix needs a **per-platform source OID** (real template design change — not a grammar change).

**2. EXOS precedence:** docs contradict whether `description-string` is separate or an enhanced field. Set **both** `display-string` and `description-string` on a test port; SNMP-get `ifAlias`; record winner + truncation at 64.

Until (1) is green, do not assume VOSS LLD can read the same OID as EXOS — only that the **CLI budget is 64**.

---

## 1. Locked decisions

1. **Grammar:** `CLASS[-SPEED]-ID` — atomic CLASS, **hyphen** only.  
2. **No `:` in labels** — EXOS forbids `:` in `description-string` (safe union also bans space `"` `<>` `&` `?`; first char alphanumeric). Colon grammar is **CLI-invalid**.  
3. **Grammar budget = 64 characters** (VOSS `name` + EXOS ifAlias default). Always-emit SPEED; real far-end IDs; controlled `X-STK`/`X-ISC`/`X-MLAG`. No fictional ≤15. No EXOS `ifalias size extended` required.  
4. **No special `IDR` class** — iDRAC = **`MON`**.  
5. **Class speed defaults (when token absent — legacy/hand only):** `UC`/`UD`/`UA` → **10G**; `UP`/`MON` → **1G**. Generated labels **always** include SPEED.  
6. **Push targets:** EXOS → field that canary shows drives ifAlias (expect `description-string`); VOSS → `name` / `name port <list>` (SNMP OID canary open).  
7. **Generator authoritative** on managed ports. NetBox **`display_protect`** skips hand-sets (§8).  
8. **Parse states:** `PARSED` | `EMPTY` | **`UNPARSEABLE`**.  
9. **Access LLD is opt-in** — change-detect does **not** cover unlabeled/typo’d access ports.  
10. **Hybrid subsidiary:** admin-down spares; `X` only on up-but-uninteresting.  
11. **LAGs:** speed expect on **members** only.  
12. **No NetBox tags** for monitor/speed intent.  
13. Track B: generate/push, compliance, parser, ingest-loop check, **remaining SNMP canaries** (VOSS name→OID, EXOS field precedence).

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
| **Forbidden** | `:` space `"` `<>` `&` `?` ; first char alphanumeric (EXOS safe union) |

### 2.1 Length profile — **64 common** (locked)

| | |
|---|---|
| **Budget** | **64 characters** end-to-end |
| **SPEED** | **Always emit** on generated labels |
| **ID** | Real far-end names OK within remaining budget |
| **`X` notes** | Controlled: `X-STK`, `X-ISC`, `X-MLAG`, `X-SPN`, `X-OOB`, `X-OTH` |

Short “omit default token / tiny ID” profile is **legacy/emergency only**, not the fleet design.

**Open:** VOSS SNMP source OID for the name; EXOS display vs description → ifAlias precedence.

### 2.2 Parser (two branches — no speed on `X`)

```
# Exclude — note is NEVER a speed token
^X(-(?<xnote>STK|ISC|MLAG|SPN|OOB|OTH|[A-Z0-9]{1,12}))?$

# Include
^(?<class>UC|UD|UA|UP|MON|W|TMON)(-(?<speed>100M|1G|2G5|5G|10G|25G|40G|100G|400G))?(-(?<id>[A-Z0-9-]+))?$
```

(All matching after uppercase normalize.)

**`X` notes:** controlled vocabulary when **generated**. Diff rule: generated `X` / `X-STK` / … must match exactly; do not treat arbitrary hand `X-spare` as equal to generated `X` unless protect-set. Prefer generator-owned notes only.

**Source field:** Zabbix reads port identity from SNMP — **prefer `ifAlias`** (`IF-MIB::ifAlias`).  
- **EXOS:** push `description-string` (or whichever canary shows wins) so ifAlias carries the label.  
- **VOSS:** push `name` / `name port <list>`; **confirm** OID (`ifAlias` vs `ifDescr`) before templating.

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

**Extended profile:** always `CLASS-SPEED-ID` (e.g. `UD-10G-CH-ZRH-ZH4-DIST01`, `UA-1G-SWA08`).  
Token omission is hand/legacy only — generator always emits SPEED from NetBox `interface.speed` (or class default if speed unset).

---

## 5. Zabbix resolution

```
1) Classify label: EMPTY | PARSED | UNPARSEABLE
2) UNPARSEABLE ≠ EMPTY — exclude from fabric “unlabeled uplink” path;
                 list in compliance until migrated (do not invent class from junk)
3) PARSED class X → skip port alerts
4) Else include per role LLD rules (§6)
5) If discovered AND class in {UC,UD,UA,UP,MON,W}:
      link-down / flap / errors (W included)
6) If discovered AND class in {UC,UD,UA,UP,MON}:
      absolute expect = SPEED token OR class default
      ifHighSpeed ≠ expected for ≥5m while oper-up → WARNING
7) If discovered AND not TMON:
      change(ifHighSpeed) vs last *stable up* value for ≥5m → WARNING
      suppress in maintenance windows
8) TMON: items + optional link-down INFO only
```

**Why `UNPARSEABLE` exists (one rule):** live plant labels (`ISC`, `ALTERNATIVE_ISC`, `ESX40_CT1_ETH0`, …) are non-empty but not our grammar. Treating them as `EMPTY` would auto-monitor them as fabric uplinks. Parser reports three buckets for migration inventory; LLD does not invent include/exclude from junk.

**Access safety net limit:** change-detect and absolute-expect only run on **discovered** items. Access LLD is opt-in regex — **typo / missing label ⇒ no items ⇒ no safety net**. Mitigation = NetBox compliance diff (+ generator).

**Settle / maintenance:** compare speed change against last **stable oper-up** sample (not a mid-negotiation poll). Maintenance windows suppress change-detect and absolute-expect WARNs. Gate absolute-expect per site until generated-vs-live diff is clean.
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

**Grammar (done):**
- [x] Grammar budget **64** locked (VOSS CLI `WORD<0-64>` + EXOS ifAlias default)
- [x] Always-emit SPEED; real far-end IDs; `X-STK`/`X-ISC`/`X-MLAG` restored
- [x] Reject fictional ≤15; no EXOS `ifalias size extended` required
- [x] Uppercase push; case-insensitive parse; split `X` regex
- [x] Hyphen only (colon forbidden)

**SNMP canaries (open — paste results):**
- [ ] EXOS: both fields set → ifAlias winner + truncate at 64
- [ ] VOSS: `name` visible in **ifAlias** (or document ifDescr fallback OID)

**Track B / ops:**
- [ ] `UNPARSEABLE` inventory + migration plan
- [ ] Access: safety net does **not** cover missing labels
- [ ] Hybrid: admin-down spares; `MON-<ID>` not empty; no X-fill-all
- [ ] Generator authoritative + `display_protect`
- [ ] Ingest loop check (ifAlias ↛ generator inputs)
- [ ] `W` = link/flap/errors; `TMON` review cadence + INFO link-down
- [ ] LAG members-only; maintenance suppress; rollout gate on clean diff

---

## 12. Summary

```
BUDGET = 64 (VOSS name WORD<0-64> + EXOS ifAlias default)
  Always emit SPEED | real far-end IDs | X-STK/X-ISC/X-MLAG
  No vendor 15-char limit | colon forbidden → hyphen
  No EXOS ifalias size extended required

OPEN CANARIES:
  1) VOSS name → ifAlias or ifDescr? (per-platform OID if ifDescr)
  2) EXOS display-string vs description-string → ifAlias precedence

GRAMMAR: CLASS[-SPEED]-ID  UPPERCASE  no colon
CLASSES: UC UD UA UP MON W TMON | X (+ controlled X-NOTE)
NO IDR — use MON

PARSE: EMPTY | PARSED | UNPARSEABLE
ACCESS: opt-in — change-detect does NOT cover missing labels
HYBRID: admin-down spares; X only if up-but-uninteresting; MON-ID not empty
W NOW: link/flap/errors | TMON: INFO link-down + audit cadence

GENERATOR authoritative | display_protect skip | check ingest loop
LAG: members only | GATE absolute-expect until diff clean
```
