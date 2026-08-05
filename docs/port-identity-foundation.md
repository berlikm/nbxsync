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
7. **Structural excludes:** prefer **derive from device state** (stack/ISC/MLAG/SPAN); display `XSTK` / `XISC` / … is **override/fallback**, not the only control.  
8. **LAGs:** explicit rule (§7) before rollout.  
9. **Access = opt-in** (include classes); **fabric/mgmt = admin-up minus excludes**.  
10. **No NetBox tags** for monitor/speed intent. Description = prose only.  
11. Track B owns generate/push, compliance diff, LLD publish.

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
^(?<class>UC|UD|UA|UP|MON|W|M|XSTK|XISC|XMLAG|XSPN|XOOB|XINT)(?:-(?<speed>100M|1G|2G5|5G|10G|25G|40G|100G|400G))?(?:-(?<id>[A-Z0-9]+))?$
```

Positional, no class-lookup heuristics, no `:` collision with `1:24`.

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
| `M` | Temp opt-in (`M-YYMMDD` or `M-YYMMDD-ID`) | — | Change-detect only; compliance ages out |

### 3.2 Exclude (override / fallback labels)

| CLASS | Meaning |
|---|---|
| `XSTK` | Stack / stacking |
| `XISC` | ISC / virtual-IST / chassis interconnect |
| `XMLAG` | MLAG peer-link / keepalive |
| `XSPN` | SPAN / mirror |
| `XOOB` | Switch own OOB |
| `XINT` | Internal / do not monitor |

Prefer **auto-derive** these from device state; set label when override needed or discovery incomplete.

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
1) Structural auto-exclude (device state)? → skip LLD / no alert
2) Display matches X*?                 → skip (label override)
3) else include per role rules (fabric admin-up / access include)
4) Always: change(ifHighSpeed)<>0 while oper-up for ≥5m → WARNING (safety net)
5) If CLASS in {UC,UD,UA,UP,MON} and label parse OK:
      expected = SPEED token OR class default
      ifHighSpeed ≠ expected for ≥5m while oper-up → WARNING
6) CLASS W: no absolute speed expect (Circuit / Phase 5)
7) CLASS M: change-detect only; no absolute expect
```

**Settle / flap guard:** speed and change triggers use **`min` / “for 5m”** (or equivalent) so negotiation blips do not storm.

**Parser location:** one version-controlled preprocess function (Track B) — not copy-pasted JS across prototypes. Optional grammar version prefix later (`V1-UD-…`) if schema evolves; v1 ships without prefix.

---

## 6. Role × LLD

| Device role | LLD |
|---|---|
| **Core / Dist / Mgmt** | Admin-up **AND NOT** (auto-structural OR `X*`) **AND NOT** (admin-up empty/unused policy — prefer admin-down unused) |
| **Access** | Display matches `^(UC\|UD\|UA\|UP\|MON\|W\|M)` |
| **AP** | Device health template — not switch-port fabric LLD |

Unused enabled ports on fabric: **disable** (hygiene) — do not rely on “monitor everything admin-up” forever.

---

## 7. LAG / LACP / MLAG bundles (mandatory before rollout)

| Rule | Decision |
|---|---|
| **What we label** | Prefer **member** ports for speed expect (each member = class default or token, usually 10G) |
| **Aggregate ifIndex** | Monitor **bundle up/down / member-count** separately — **do not** compare aggregate `ifHighSpeed` (sum) to a single-member expected |
| **Expected on member** | Per-member speed (10G default on `UD`/`UA`) |
| **Expected on aggregate** | **No** `ifHighSpeed ≠ expected` trigger on aggregate |
| **MLAG peer-link** | `XMLAG` / auto-exclude — not a fabric uplink expect |

This avoids permanent false WARN on 2×10G → `ifHighSpeed=20000` aggregates.

---

## 8. Generate from NetBox (preferred), not hand-type

```
NetBox: device role + cable far-end + interface.speed (+ LAG membership)
        → generator (dry-run / apply)
        → Extreme display string (derived cache)
        → Zabbix reads ifAlias at poll time (no NetBox dependency live)
```

| Input | Becomes |
|---|---|
| Cable to dist / access / core / AP | `UD` / `UA` / `UC` / `UP` + short far-end id |
| `interface.speed` ≠ class default | insert SPEED token |
| Endpoint = server/ESX/storage/iDRAC | `MON` (+ `10G` if needed) |
| Stack/ISC/MLAG/SPAN known | prefer auto-exclude; else push `XSTK` / … |
| No cable / guest | Manual set allowed; compliance lists orphans |

**Compliance = diff** (generated vs live ifAlias), not a second rule engine.  
Hand-typed labels are fallback; typos on access includes are softened by **change-detect safety net** on fabric and by compliance diff.

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

### Structural

| Scenario | Label (fallback) | Preferred control |
|---|---|---|
| Stack | `XSTK` | Auto from stack state |
| ISC | `XISC` | Auto from ISC/MLT/virtual-IST |
| MLAG peer | `XMLAG` | Auto from MLAG config |
| SPAN | `XSPN` | Auto from mirror config |

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
| `XSTK` | 4 |

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
| New stack member alerts as uplink | Auto structural exclude |
| `M-` forever | Compliance: `M-` older than N days = finding |
| Negotiation WARN storm | `for 5m` / min settle |
| Grammar drift across templates | One shared parser module |

---

## 12. Verify checklist

- [ ] Grammar `CLASS[-SPEED]-ID` + charset locked  
- [ ] Defaults: **UC=UD=UA=10G**, **UP=1G**, **MON=1G**; no `IDR` class  
- [ ] Symmetric 1G exception examples both ends  
- [ ] `W` = no absolute speed trigger; `M-` = aged compliance  
- [ ] Tokens include `2G5` / `5G` / `400G`  
- [ ] LAG member vs aggregate rule agreed  
- [ ] Auto structural exclude path identified per EXOS/VOSS  
- [ ] Generate-from-NetBox dry-run on canary  
- [ ] Change-detect + absolute expect both tested with 5m settle  
- [ ] ifAlias mapping confirmed EXOS + VOSS  

---

## 13. Summary

```
GRAMMAR: CLASS[-SPEED]-ID   (no colon; atomic CLASS)
CLASSES: UC UD UA UP MON W M | XSTK XISC XMLAG XSPN XOOB XINT
NO IDR — iDRAC uses MON

DEFAULTS: UC=UD=UA=10G | UP=1G | MON=1G
TOKENS: 100M 1G 2G5 5G 10G 25G 40G 100G 400G

ZABBIX:
  auto-X + X* excludes
  change(ifHighSpeed) safety net (settled)
  absolute expect where UC|UD|UA|UP|MON labeled
  W: no absolute speed; LAG: expect on members only

NETBOX → generate/push label (preferred)
DESCRIPTION = prose; no monitor tags
COMPLIANCE = diff generated vs live
```
