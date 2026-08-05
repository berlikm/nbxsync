# Port identity foundation (Zabbix focus)

**Status:** Locked design direction (revised after architecture review)  
**Operator-visible SoT on box:** Extreme **display string** (≤15) — **derived cache**, preferably **generated from NetBox**  
**Scope:** Zabbix port LLD + speed expectation + structural excludes  
**NetBox:** inventory SoT (cables, roles, `interface.speed`) → generate/push label; **description** = human prose  
**Related plan:** `docs/internet-network-monitoring-plan.md` (Track A)

---

## 1. Locked decisions

1. **Grammar:** `CLASS[-SPEED]-ID` — single-token classes, **hyphen** separator (no `:` — avoids EXOS `slot:port` collision and context-sensitive parsing).  
2. **No special `IDR` class** — iDRAC / BMC is **`MON`** (same as server/storage endpoints).  
3. **Speed defaults are a property of the link class family, not asymmetric per direction:**  
   - `UC` / `UD` / `UA` → **10G**  
   - `UP` → **1G**  
   - `MON` → **1G**  
   Legacy 1G access↔dist carries `1G` on **both** ends.  
4. **Preferred flow:** NetBox structured data **generates** the display string and pushes it; ops do not hand-type the grammar day-to-day. Hand-edit remains emergency/manual fallback.  
5. **Zabbix safety net:** universal **`change(ifHighSpeed)`** while oper-up (with settle time) — catches degrades even if label missing/wrong.  
6. **Absolute expect** (`ifHighSpeed ≠ expected`) where a label exists: `expected = SPEED token OR class default`.  
7. **Excludes:** one class only — **`X` / `X-<note>`**. Why the port is excluded belongs in NetBox **description**.  
8. **LAGs:** explicit rule (§7) before rollout.  
9. **Access = opt-in** (include classes); **fabric/mgmt = admin-up minus excludes**.  
10. **Subsidiary hybrid (core∩access):** admin-down unused spares; label **`X` only** on ports that stay admin-up but must not alert; do **not** X-fill every port (§6.1).  
11. **Generator is authoritative** on managed ports (overwrites on-box display). **Protect** marker in NetBox skips generation for deliberate hand-sets (§8).  
12. **No NetBox tags** for monitor/speed intent. Description = prose only.  
13. Track B owns generate/push, compliance diff, LLD publish.

---

## 2. Universal grammar (≤15)

```
CLASS
CLASS-ID
CLASS-SPEED-ID
```

| Piece | Rules |
|---|---|
| **CLASS** | One atomic token from vocabulary below |
| **SPEED** | Optional. Only when ≠ class default. Canonical tokens only |
| **ID** | Machine-short (≤ ~6–8 chars after prefix). Full name in NetBox description / device name — **not** free-typed FQDN in the label |
| **Charset** | `[A-Z0-9-]` uppercased; **no colon**, no dots in tokens |

**One regex (illustrative):**

```
^(?<class>UC|UD|UA|UP|MON|W|TMON|X)(?:-(?<speed>100M|1G|2G5|5G|10G|25G|40G|100G|400G))?(?:-(?<id>[A-Z0-9]+))?$
```

**Parse note:** If CLASS is `X`, the optional tail is a free short note — **not** a SPEED token.  

**Source field:** Extreme display string maps to **`IF-MIB::ifAlias`** on EXOS and VOSS. Design depends on that mapping.

---

## 3. Class vocabulary

### 3.1 Include / monitor

| CLASS | Meaning | **Default expected** | Speed trigger? |
|---|---|---|---|
| `UC` | Uplink toward **core** | **10G** | Yes |
| `UD` | Uplink toward **dist** | **10G** | Yes |
| `UA` | Uplink toward **access** | **10G** | Yes |
| `UP` | Access → **AP** | **1G** | Yes |
| `MON` | Monitored endpoint (server, ESX, storage, **iDRAC**, misc) | **1G** | Yes |
| `W` | WAN / ISP | — | **No** absolute speed trigger (Phase 5 / Circuit bandwidth) |
| `TMON` | **Temp monitor** — metrics only, **no alerts** | — | Items yes / **triggers no**; compliance lists for audit |

**`TMON` / `TMON-<id>`** replaces dated `M-YYMMDD`. Do **not** put expiry in the switch label (stale dates on-box never get cleaned). Optional why/until belongs in NetBox **description**; compliance **inventory of all `TMON*`** is the audit lever.

### 3.2 Exclude — single class `X`

| CLASS | Meaning |
|---|---|
| `X` or `X-<note>` | Port is **excluded** from port monitoring alerts |

That is the full exclude vocabulary. Optional `<note>` is free-form within the 15-char limit if useful on-box; the explanation stays in NetBox **description**.

| Display | Description |
|---|---|
| `X` | *(why this port is excluded)* |
| `X-<note>` | *(why this port is excluded)* |

### 3.3 `TMON` — temp monitor without alerts

| | |
|---|---|
| **Display** | `TMON` or `TMON-<id>` (e.g. `TMON-guest`, `TMON-rack3`) |
| **Zabbix** | LLD **includes** the port → items/graphs/history **yes** |
| **Triggers** | **None** — no link-down problem, no speed WARN, no change-detect alert |
| **Audit** | Compliance report: **every interface with `TMON*`** (site, device, ifName, description, last seen) |
| **Cleanup** | Human reviews the list → remove label, or promote to `MON`/`UP`/… if permanent |
| **Description** | Optional why/until in **NetBox** — not encoded in the 15-char string |

Do **not** use dated `M-YYMMDD` on the switch. Dates rot in place; an auditable `TMON` inventory does not.

---

## 4. Speed tokens (universal)

| Token | Mbps |
|---|---|
| `100M` | 100 |
| `1G` | 1000 |
| `2G5` | 2500 (NBASE-T / Wi-Fi AP edge — no dot in token) |
| `5G` | 5000 |
| `10G` | 10000 |
| `25G` | 25000 |
| `40G` | 40000 |
| `100G` | 100000 |
| `400G` | 400000 |

**When to add SPEED:** only if ≠ class default.  
Because `UD`/`UA`/`UC` all default **10G**, a standard 10G access↔dist link needs **no token on either end**. A legacy **1G** link gets `1G` on **both** ends → symmetric compliance.

---

## 5. Zabbix resolution (robust)

```
1) Display class X?                         → skip (excluded)
2) Else include per role rules (fabric admin-up / access include)
3) Always: change(ifHighSpeed)<>0 while oper-up for ≥5m → WARNING (safety net)
   (not for TMON)
4) If CLASS in {UC,UD,UA,UP,MON} and label parse OK:
      expected = SPEED token OR class default
      ifHighSpeed ≠ expected for ≥5m while oper-up → WARNING
5) CLASS W: no absolute speed expect (Circuit / Phase 5)
6) CLASS TMON: discover + collect items only — no triggers / no problems
   Compliance lists every TMON for audit
```

**Settle / flap guard:** speed and change triggers use **`min` / “for 5m”** (or equivalent) so negotiation blips do not storm.

**Parser location:** one version-controlled preprocess function (Track B) — not copy-pasted JS across prototypes. Optional grammar version prefix later (`V1-UD-…`) if schema evolves; v1 ships without prefix.

---

## 6. Role × LLD

| Device role | LLD |
|---|---|
| **Core / Dist / Mgmt** | Admin-up **AND NOT** display class `X` (prefer admin-down unused) |
| **Access** | Display matches `^(UC\|UD\|UA\|UP\|MON\|W\|TMON)` |
| **Subsidiary hybrid (core∩access)** | Same LLD as fabric: admin-up **AND NOT** `X` — **labeling policy inverted** (§6.1) |
| **AP** | Device health template — not switch-port fabric LLD |

Unused enabled ports on fabric: **disable** (hygiene) — do not rely on “monitor everything admin-up” forever.

### 6.1 Subsidiary sites — core that also acts as access

At many subsidiaries one switch is **both core and access** (clients hang off the same box). Fabric “monitor all admin-up” would drown in client-edge noise.

**Locked policy — do not X-fill every port**

Pushing `X` onto every interface is an interface-level config line per port → config bloat, save/sync churn, and noisy cfgit diffs on every apply. **Rejected as the default.**

**Cheaper equivalent (same LLD outcome):**

```
1) Unused / spare ports     → admin-down (preferred hygiene; same as fabric §6)
2) Admin-up but uninteresting → label X / X-<note> + description
3) Ports to monitor         → leave non-X (empty, MON, TMON, UP, UC|UD|UA, W, …)
```

LLD stays: admin-up **AND NOT** class `X`. Admin-down ports never enter LLD. Only the smaller set of up-but-silent ports needs an `X` label.

| Port kind on hybrid switch | Action | Display | Monitored? |
|---|---|---|---|
| Spare / unused | **admin-down** | n/a (or clear) | No |
| Admin-up, do not alert | keep up | `X` / `X-<note>` | No |
| Client access (care about) | admin-up | empty or `MON` / `TMON` | Yes (`TMON` = metrics, no alerts) |
| AP | admin-up | `UP-…` | Yes |
| Uplink / fabric | admin-up | `UC`/`UD`/`UA`-… | Yes |
| WAN | admin-up | `W-…` | Yes |
| Server / iDRAC / storage | admin-up | `MON-…` | Yes |

**NetBox:** device role e.g. `Core-Access` / `Subsidiary Core` selects this profile: generate includes + `X` only where admin-up exclude is required; drive admin-down for spares via the same automation where possible.

**Why not pure access opt-in alone:** hybrid boxes often need “monitor these client ports” without an include code on every drop — non-X under fabric LLD is enough; use `MON`/`TMON` when you need identity or metrics-only.

---

## 7. LAG / LACP / MLAG bundles (mandatory before rollout)

| Rule | Decision |
|---|---|
| **What we label** | Prefer **member** ports for speed expect (each member = class default or token, usually 10G) |
| **Aggregate ifIndex** | Monitor **bundle up/down / member-count** separately — **do not** compare aggregate `ifHighSpeed` (sum) to a single-member expected |
| **Expected on member** | Per-member speed (10G default on `UD`/`UA`) |
| **Expected on aggregate** | **No** `ifHighSpeed ≠ expected` trigger on aggregate |
| **MLAG / bundle peer links you must not treat as uplinks** | Label `X` (description) and/or follow LAG rules (§7) — not a fabric uplink expect |

This avoids permanent false WARN on 2×10G → `ifHighSpeed=20000` aggregates.

---

## 8. Generate from NetBox (authoritative)

```
NetBox: device role + cable far-end + interface.speed (+ LAG + protect flag)
        → generator (dry-run / apply)
        → Extreme display string (derived cache)
        → Zabbix reads ifAlias at poll time (no NetBox dependency live)
```

**Authority:** On **managed** interfaces the generator **is authoritative**. Apply **overwrites** the on-box display string (ifAlias) to match the generated value. Manual CLI edits on managed ports are not preserved — fix the intent in NetBox (or protect the port), then re-apply.

### Protect marker (hand-set ports)

| Mechanism | Behavior |
|---|---|
| NetBox interface flag / CF e.g. `display_protect` = true | Generator **skips** that interface (no push, no overwrite) |
| Compliance | Lists protected ports separately (live vs desired N/A); drift is ops-owned |
| On-box | No magic display prefix required — protect lives in **NetBox**, not in the 15-char string |

Use protect only for deliberate exceptions (lab, break-glass, pending NetBox model). Default is unmanaged → managed by generator.

| Input | Becomes |
|---|---|
| `display_protect` | **Skip** — leave on-box display untouched |
| Device role = hybrid / subsidiary | Includes + **`X` only** on admin-up excludes; **admin-down** spares (not X-fill-all) |
| Cable to dist / access / core / AP | `UD` / `UA` / `UC` / `UP` + short far-end id |
| Client access port flagged monitor | non-X (empty or `MON` / `TMON`) |
| `interface.speed` ≠ class default | insert SPEED token |
| Endpoint = server/ESX/storage/iDRAC | `MON` (+ `10G` if needed) |
| Admin-up, must not alert | `X` / `X-<note>` + description |
| Spare / unused | **admin-down** (preferred) |

**Compliance = diff** (generated vs live ifAlias) on managed ports; protected ports reported as protect-set, not as generator failures.

**ID policy:** controlled short names (NetBox abbrev / asset slug), not full hostnames. Example budget: `MON-10G-` = 8 chars → **7 left** for id.

---

## 9. Worked examples

### Fabric (symmetric defaults)

| Scenario | Access side | Dist/core side | Expect |
|---|---|---|---|
| Standard **10G** access↔dist | `UD-swd14` | `UA-swa08` | 10G both |
| Legacy **1G** access↔dist | `UD-1G-swd2` | `UA-1G-swa2` | 1G both |
| Toward core **10G** | `UC-swc01` | (peer as designed) | 10G |
| Toward core **40G** | `UC-40G-c01` | … | 40G |
| Access → AP **1G** | `UP-ap3f07` | — | 1G |
| AP **2.5G** | `UP-2G5-ap07` | — | 2500 |

### Endpoints (no IDR class)

| Scenario | Display | Expect |
|---|---|---|
| ESXi 10G | `MON-10G-esx1` | 10G |
| Server 1G | `MON-srv12` | 1G |
| **iDRAC 1G** | `MON-idr03` | 1G |
| iDRAC 100M | `MON-100M-idr3` | 100M |
| Storage 10G | `MON-10G-nta` | 10G |

### Subsidiary hybrid (core∩access)

| Scenario | Action / display | Monitored? |
|---|---|---|
| Client PC drop (care) | empty or `MON` / `TMON` | Yes |
| Spare / unused | **admin-down** | No |
| Up but uninteresting | `X` / `X-<note>` | No |
| AP / WAN on same switch | `UP-…` / `W-…` | Yes |

### Length

| Display | Len |
|---|---|
| `UD-swd14` | 8 |
| `UD-1G-swd2` | 10 |
| `UA-1G-swa2` | 10 |
| `UP-ap3f07` | 9 |
| `UP-2G5-ap07` | 11 |
| `MON-10G-esx1` | 12 |
| `MON-idr03` | 9 |
| `X` / `X-<note>` | ≤15 |

---

## 10. Errors / duplex (scope note)

Speed mismatch is **necessary but narrow**. Phase 2 templates still include **errors / CRC / discards** (and flap). “Up at 10G with CRCs” remains an errors trigger — not solved by speed alone.

---

## 11. Risks → mitigations

| Risk | Mitigation |
|---|---|
| `UD`/`UA` asymmetric tokens | Fixed — both default 10G |
| Colon / slot:port collision | Hyphen grammar, atomic CLASS |
| Hand-type typos drop access monitoring | Generate from NetBox; compliance diff; change-detect safety net |
| 15-char hostname overflow | Machine-short IDs only |
| Aggregate LAG false WARN | Members vs aggregate rule (§7) |
| X-fill every subsidiary port | **Reject** — admin-down spares; `X` only if admin-up but uninteresting |
| Manual edit lost on apply | Expected on managed ports; set **`display_protect`** to skip |
| Protected port forgotten | Compliance lists protect-set |
| `TMON` forever / forgotten | Compliance **list all TMON*** regularly; clear or promote to `MON`/`UP`/… |
| Negotiation WARN storm | `for 5m` / min settle |
| Grammar drift across templates | One shared parser module |

---

## 12. Verify checklist

- [ ] Grammar `CLASS[-SPEED]-ID` + charset locked  
- [ ] Defaults: **UC=UD=UA=10G**, **UP=1G**, **MON=1G**; no `IDR` class  
- [ ] Symmetric 1G exception examples both ends  
- [ ] `W` = no absolute speed trigger; **`TMON` = monitor only, no alerts**; compliance lists `TMON*`  
- [ ] Tokens include `2G5` / `5G` / `400G`  
- [ ] LAG member vs aggregate rule agreed  
- [ ] Exclude class is only `X` / `X-<note>`; reason in description  
- [ ] Generate-from-NetBox dry-run on canary  
- [ ] Change-detect + absolute expect both tested with 5m settle  
- [ ] Hybrid subsidiary: admin-down spares; `X` only on up-but-uninteresting  
- [ ] Generator authoritative on managed ports; **`display_protect`** skips hand-sets  
- [ ] ifAlias mapping confirmed EXOS + VOSS  

---

## 13. Summary

```
GRAMMAR: CLASS[-SPEED]-ID   (no colon; atomic CLASS)
CLASSES: UC UD UA UP MON W TMON | X (optional X-<note>)
NO IDR — iDRAC uses MON
EXCLUDE: X only — reason in description

DEFAULTS: UC=UD=UA=10G | UP=1G | MON=1G
TOKENS: 100M 1G 2G5 5G 10G 25G 40G 100G 400G

ZABBIX:
  class X excludes
  change(ifHighSpeed) safety net (settled)
  absolute expect where UC|UD|UA|UP|MON labeled
  TMON: items only — no triggers; compliance lists TMON* for audit
  W: no absolute speed; LAG: expect on members only

HYBRID SUBSIDIARY (core∩access)
  spares → admin-down (not X-fill-all)
  up-but-uninteresting → X / X-<note>
  monitor → non-X (empty|MON|TMON|UP|UC|UD|UA|W)
  LLD = admin-up AND NOT X

GENERATOR = authoritative overwrite on managed ports
PROTECT = NetBox display_protect → skip interface
DESCRIPTION = prose (incl. why a port is X); no monitor tags
COMPLIANCE = diff generated vs live (managed); list protect-set
```
