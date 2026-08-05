# Port identity foundation (Zabbix focus)

**Status:** Locked design direction  
**Operator SoT:** Extreme **display string only** (≤15 characters)  
**Scope:** Zabbix port discovery + speed expectations — robust, universal coding  
**NetBox (here):** cables / circuits / **compliance** / **description** (human prose only)  
**Related plan:** `docs/internet-network-monitoring-plan.md` (Track A)

---

## 1. Locked decisions

1. **Display string = operator SoT** for class, monitor/exclude, and **speed expectation**.  
2. **Class defaults for speed are real** (see §3) — not “learn anything.”  
3. When speed ≠ class default, put an **explicit speed token** in the display string (`1G`, `10G`, `100M`, …).  
4. **NetBox description** = human identity/prose (hostname, “why”) — **not** the Zabbix speed input.  
5. **No NetBox tags** for day-to-day monitor/speed intent.  
6. **Core / Dist / Mgmt:** LLD = admin-up minus `X:…`.  
7. **Access:** LLD = include codes only (`U:…`, `W:…`, `M:…`, `MON…`, `IDR…`).  
8. Structural ports (**stack / ISC / MLAG / SPAN / …**) use **`X:…`** — same coding family, excluded from uplink alerts.  
9. **iDRAC / ESX / storage / servers** use **`IDR:`** / **`MON:`** (+ speed token when ≠ default).  
10. Track B (nbxsync / LLD publish) is separate.

---

## 2. Universal display grammar (≤15)

```
<CLASS>:<ID>
<CLASS>:<SPEED>:<ID>
<XCLASS>                  (exclude — no id required)
<XCLASS>:<ID>             (exclude — optional id)
```

| Piece | Rules |
|---|---|
| **CLASS** | Fixed vocabulary below (obvious to ops) |
| **SPEED** | Optional. Only when ≠ class default. Canonical: `100M` \| `1G` \| `10G` \| `25G` \| `40G` \| `100G` |
| **ID** | Short far-end / local label (truncate; full name in NetBox description) |
| **ASCII** | No spaces. Script/compliance enforces ≤15 and valid tokens. |

**Zabbix resolution (single algorithm for every port):**

```
if display matches X:…           → do not monitor (exclude)
else if SPEED token present      → expected_mbps = token
else                             → expected_mbps = CLASS_DEFAULT[class]
alert if oper-up AND ifHighSpeed ≠ expected_mbps
```

One parser. Same rules for uplinks, AP, iDRAC, ESX, storage.

---

## 3. Class vocabulary + default speeds

### 3.1 Include / monitor classes

| CLASS | Meaning | **Default expected speed** | Typical use |
|---|---|---|---|
| `U:C` | Uplink toward **core** | **10G** | Dist/access → core |
| `U:D` | Uplink toward **dist** | **10G** | Access → dist |
| `U:A` | Uplink toward **access** | **1G** | Dist/core → access switch |
| `U:P` | Access → **AP** | **1G** | AP edge |
| `MON` | Generic monitored endpoint | **1G** | Server NIC, storage, misc |
| `IDR` | **iDRAC** / server OOB BMC | **1G** | iDRAC on mgmt/core |
| `W` | WAN / ISP | *(Phase 5 — Circuit / token)* | Internet handoff |
| `M` | Temp monitor (`M:<yymmdd>`) | **baseline learn*** | Short-lived opt-in |

\*Temp `M:` may learn baseline (no stable class). Prefer a real CLASS when possible.

### 3.2 Exclude classes (same family — robust coverage)

| CLASS | Meaning | Speed? |
|---|---|---|
| `X:STK` | Stack / stacking link | N/A — not monitored |
| `X:ISC` | ISC / inter-switch chassis link | N/A |
| `X:MLAG` | MLAG / peer-link / keepalive | N/A |
| `X:SPN` | SPAN / mirror | N/A |
| `X:OOB` | Switch own OOB/mgmt port | N/A |
| `X:INT` | Internal / do not monitor | N/A |
| `X` | Generic exclude | N/A |

Stack / ISC / MLAG are **first-class codes**, not afterthoughts. Ops set them so fabric LLD (admin-up) does not treat them as customer/uplink faults.

---

## 4. When to add a SPEED token

Add `<SPEED>:` **only if** live design ≠ class default.

| Class default | Port actually is | Display shape |
|---|---|---|
| `U:D` → 10G | 10G | `U:D:<id>` |
| `U:D` → 10G | **1G** | `U:D:1G:<id>` |
| `U:D` → 10G | **100M** | `U:D:100M:<id>` |
| `U:A` → 1G | 1G | `U:A:<id>` |
| `U:A` → 1G | **10G** | `U:A:10G:<id>` |
| `U:A` → 1G | **100M** | `U:A:100M:<id>` |
| `U:P` → 1G | 1G | `U:P:<id>` |
| `U:P` → 1G | **100M** (bad/legacy) | `U:P:100M:<id>` only if **accepted**; else fix plant |
| `MON` → 1G | **10G** ESX/storage | `MON:10G:<id>` |
| `IDR` → 1G | 1G | `IDR:<id>` |
| `IDR` → 1G | **100M** | `IDR:100M:<id>` |

**Do not** invent opaque nibbles (`D1`, `01`). Speed tokens are the universal words: `1G`, `10G`, `100M`.

---

## 5. Worked examples (copy/paste set)

### Fabric uplinks

| Scenario | Display (≤15) | Zabbix expected | Description (NetBox) |
|---|---|---|---|
| Access → dist **10G** (default) | `U:D:swd14` | 10000 | `Uplink to dist swd14` |
| Access → dist **1G** (exception) | `U:D:1G:swd2` | 1000 | `Uplink to swd2 — 1G plant` |
| Dist → access **1G** (default) | `U:A:swa08` | 1000 | `Downlink to access swa08` |
| Dist → access **10G** (exception) | `U:A:10G:swa1` | 10000 | `Downlink to swa1 — 10G` |
| Dist → access **100M** (rare) | `U:A:100M:ps` | 100 | `Legacy 100M to PS closet` |
| Toward core **10G** | `U:C:swc01` | 10000 | `Uplink to core swc01` |
| Toward core **40G** | `U:C:40G:c01` | 40000 | `Uplink to core — 40G` |
| Access → AP **1G** | `U:P:ap3f07` | 1000 | `AP ap-3f-07` |

### Mgmt / core endpoints

| Scenario | Display | Zabbix expected | Description |
|---|---|---|---|
| ESXi **10G** | `MON:10G:esx1` | 10000 | `ESXi esx01 vmnic0` |
| ESXi **1G** | `MON:esx01` | 1000 | `ESXi esx01 — 1G NIC` |
| Storage **10G** | `MON:10G:nta` | 10000 | `NetApp ContA e0a` |
| Server NIC **1G** | `MON:srv12` | 1000 | `Server srv12 eth0` |
| iDRAC **1G** (default) | `IDR:r74003` | 1000 | `iDRAC dell-r740-03` |
| iDRAC **100M** | `IDR:100M:r03` | 100 | `iDRAC — 100M BMC` |

### Structural / do-not-monitor (universal excludes)

| Scenario | Display | Zabbix |
|---|---|---|
| Stack port | `X:STK` or `X:STK:1` | Excluded |
| ISC | `X:ISC` or `X:ISC:a` | Excluded |
| MLAG peer-link | `X:MLAG` or `X:MLAG:pk` | Excluded |
| SPAN/mirror | `X:SPN` | Excluded |
| Switch OOB | `X:OOB` | Excluded |
| Internal | `X:INT` | Excluded |

### Length check (must fit ≤15)

| Display | Len |
|---|---|
| `U:D:swd14` | 9 |
| `U:D:1G:swd2` | 11 |
| `U:A:10G:swa1` | 12 |
| `U:A:100M:ps` | 11 |
| `U:P:ap3f07` | 10 |
| `MON:10G:esx1` | 12 |
| `IDR:r74003` | 10 |
| `IDR:100M:r03` | 12 |
| `X:MLAG` | 6 |

If id does not fit → shorten id; full name in **description**.

---

## 6. Role × LLD matrix

| Device role | LLD rule | How codes are used |
|---|---|---|
| **Core / Dist / Mgmt** | Admin-up **AND NOT** `^X:` | Label uplinks `U:…`; endpoints `MON:`/`IDR:`; structural `X:STK`/`X:ISC`/`X:MLAG`/… |
| **Access** | Display matches `^(U:|W:|M:|MON|IDR)` | Quiet by default; set include + speed token if needed |
| **AP (HiveOS)** | Device health template | Not switch-port LLD |

---

## 7. Zabbix implementation intent

### Discovery

- Fabric template: filter admin-up, drop `X:*`.  
- Access template: include regex on CLASS.  
- LLD macros from display parse:
  - `{#IF.CLASS}` = `U:D` / `MON` / `IDR` / `X:STK` / …  
  - `{#IF.SPEED.TOKEN}` = `10G` / empty  
  - `{#IF.SPEED.EXPECTED}` = Mbps number (token or class default)  
  - `{#IF.ID}` = trailing id  

### Triggers

- Link down / flap / errors (existing).  
- **Speed mismatch:** `ifHighSpeed <> {#IF.SPEED.EXPECTED}` while oper-up → WARNING.  
- Same trigger prototype for `U:D`, `U:A`, `U:P`, `MON`, `IDR` — only the expected value changes.

### Why not “learn baseline” as primary

Class defaults are known engineering standards here (`U:D`=10G, `U:A`=1G, `U:P`=1G). Learning would accept a silent 10G→1G degrade on `U:D` as “new normal.” **Token + default** catches that. Learning remains optional only for `M:` temp ports.

---

## 8. NetBox role (narrow)

| NetBox field | Role |
|---|---|
| Cable / Circuit | Inventory + compliance (“should have `U:P:` / `U:D:`”) |
| Interface **description** | Human prose — hostname, plant note |
| Tags | **Not** for monitor/speed |
| Interface.speed | **Out of scope here** (config tooling — not Zabbix) |

Compliance examples: cable Access↔Dist but display missing/`U:A` on wrong side; `MON:`/`IDR:` without description; admin-up without `X:` on known stack port.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| 15-char overflow | Short ids; enforce in script; description holds long names |
| Typo `1G` vs `1g` | Canonical uppercase tokens only |
| Forgot speed token on exception | Compliance + false WARN on mismatch → ops add token |
| Stack/MLAG alerting as uplinks | Mandatory `X:STK` / `X:ISC` / `X:MLAG` |
| iDRAC mixed with server NIC | Prefer `IDR:` vs `MON:` |
| Assuming learn-baseline for `U:D` | Rejected — use defaults + tokens |

---

## 10. Verify checklist

- [ ] Grammar: `CLASS:ID` / `CLASS:SPEED:ID` / `X:…` approved  
- [ ] Defaults locked: **`U:D`=10G**, **`U:A`=1G**, **`U:P`=1G**, **`U:C`=10G**, **`MON`/`IDR`=1G**  
- [ ] Speed tokens: `100M|1G|10G|25G|40G|100G` only  
- [ ] Excludes: `X:STK` `X:ISC` `X:MLAG` `X:SPN` `X:OOB` `X:INT`  
- [ ] Examples validated ≤15 on EXOS + VOSS  
- [ ] Zabbix parse → `{#IF.SPEED.EXPECTED}` works for uplink + IDR + MON  
- [ ] Canaries: default `U:D`, exception `U:D:1G:…`, default `U:A`, exception `U:A:10G:…`, `U:P`, `MON:10G:…`, `IDR:…`, `X:STK`, `X:MLAG`  

---

## 11. Summary (cross-check)

```
UNIVERSAL DISPLAY (≤15)
  CLASS:ID
  CLASS:SPEED:ID          ← only when ≠ class default
  X:STK | X:ISC | X:MLAG | X:SPN | X:OOB | X:INT

CLASS DEFAULTS (Zabbix expected)
  U:C  → 10G
  U:D  → 10G      (access → dist)
  U:A  → 1G       (toward access switch)
  U:P  → 1G       (toward AP)
  MON  → 1G       (override e.g. MON:10G:esx1)
  IDR  → 1G       (override e.g. IDR:100M:r03)

SPEED TOKENS (universal words)
  100M | 1G | 10G | 25G | 40G | 100G

ZABBIX
  expected = SPEED token OR class default
  alert if oper ifHighSpeed ≠ expected
  X:* → exclude from LLD

NETBOX DESCRIPTION = human prose only (not speed SoT)
NO MONITOR TAGS

EXAMPLES
  U:D:swd14        expect 10G
  U:D:1G:swd2      expect 1G
  U:A:swa08        expect 1G
  U:A:10G:swa1     expect 10G
  U:P:ap3f07       expect 1G
  MON:10G:esx1     expect 10G
  IDR:r74003       expect 1G
  X:STK / X:ISC / X:MLAG
```
