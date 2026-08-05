# Port identity foundation (Zabbix focus)

**Status:** Locked design direction  
**Operator SoT:** Extreme **display string only** (≤15 characters)  
**Scope:** How Zabbix discovers and alerts on ports — not switch-config generation  
**NetBox role (here):** Inventory, cables, circuits, **compliance**, interface **description** for human notes — not a second place to edit monitor intent  
**Related plan:** `docs/internet-network-monitoring-plan.md` (Track A)

---

## 1. Locked decisions

1. **Display string = only operator control** for port class / monitor / exclude (one edit on the switch).  
2. **Do not** use NetBox interface tags for day-to-day “monitor this port.”  
3. **NetBox description** = human-readable **what / why** (ESX hostname, iDRAC, intentional plant notes). Not a Zabbix input.  
4. **Speed is not encoded in the display string** and does **not** need a special “exception” code. For `U:D:` / `U:A:` / `U:C:` / `MON:`, Zabbix **baseline** is the expected speed (see §4).  
5. **Core / Dist / Mgmt:** monitor all **admin-up** ports, minus **exclusion** codes (`X:…`). Unused admin-up → disable.  
6. **Access:** monitor only **include** codes (`U:…`, `W:…`, `M:…`, `MON` / `MON:…`).  
7. **APs** hang off **access** — `U:P:…`, Zabbix expects **1G** (catch 100M fallback).  
8. **Dist ↔ access** speeds are mixed (**1G / 10G / 100M**). `U:D:` / `U:A:` identify the **role**, not the speed.  
9. **Servers / ESX / storage / iDRAC** on **mgmt or core**: admin-up LLD covers them; label with **`MON:`** + **description**.  
10. Manual OK when no cable in NetBox — set display on the switch.  
11. Track B (nbxsync / LLD / compliance) is a **separate** task.

---

## 2. Display string codes (≤15)

ASCII, no spaces. Keep codes **obvious**. Put the story in NetBox **description**.

### Include / classify

| Code | Meaning (obvious) | Zabbix speed |
|---|---|---|
| `U:C:<id>` | Uplink toward **core** | Baseline / degrade |
| `U:D:<id>` | Uplink toward **dist** | Baseline / degrade (1G / 10G / 100M) |
| `U:A:<id>` | Uplink toward **access** | Baseline / degrade (1G / 10G / 100M) |
| `U:P:<id>` | Access → **AP** | Expect **1G** |
| `W:<isp><n>` | **WAN / ISP** | Phase 5 |
| `M:<yymmdd>` | **Temp** monitor until date | Baseline if needed |
| `MON` or `MON:<id>` | **Monitor** — non-fabric endpoint (ESX, storage, iDRAC, server NIC, …) | Baseline / degrade |

Examples: `U:C:swc01`, `U:D:swa12`, `U:A:swd03`, `U:P:ap3f07`, `W:SC1`, `M:260830`, `MON`, `MON:esx01`, `MON:idr3`.

### Exclusion codes (core / dist / mgmt)

| Code | Meaning |
|---|---|
| `X:STK` | Stack / ISC / MLAG member |
| `X:SPN` | SPAN / mirror |
| `X:OOB` | Out-of-band / mgmt port (switch’s own OOB) |
| `X:INT` | Internal / do not monitor |
| `X` | Generic exclude |

---

## 3. Role matrix

| Device role | Port LLD rule | Display use |
|---|---|---|
| **Core / Dist / Mgmt** | All **admin-up**, minus `X:…` | `U:…` / `W:…` label uplinks; **`MON:`** label servers/ESX/storage/iDRAC; `X:…` to skip |
| **Access** | Only `^(U:|W:|M:|MON)` | Must set include code or port stays quiet |
| **AP (HiveOS)** | Device health (Phase 1) | Not fabric port LLD |

On **mgmt/core**, admin-up already monitors the link. **`MON:` + description** is how humans (and reports) know *what* it is — not a second SoT.

---

## 4. Speed in Zabbix — no speed “exceptions” in the code

### Why there is nothing to encode

Older drafts assumed “`U:D:` means expect 10G” and then needed overrides (`U:D1:`, `01`, …) for 1G/100M. **That model is rejected.**

Dist ↔ access (and `MON:`) links are **legitimately mixed**. So Zabbix does **not** assume a class speed. It learns each port’s **baseline** from live `ifHighSpeed`.

| Situation | What you do | What Zabbix does |
|---|---|---|
| `U:D:swa12` runs at **10G** | Display `U:D:swa12` | Baseline = 10000; alert if it drops |
| `U:D:swa08` runs at **1G** | Same code shape `U:D:swa08` — **not** an exception code | Baseline = 1000; alert if it drops |
| `U:A:ps01` runs at **100M** | Same code shape `U:A:ps01` — **not** an exception code | Baseline = 100; alert if it drops |
| AP `U:P:ap3f07` | Display `U:P:…` | **Fixed** expect 1G (class is uniform enough) |
| Must **not** monitor a port | Display `X:STK` / `X:SPN` / … | Excluded from LLD — **this** is the real exception |

So: **1G and 100M are normal baselines for `U:D:` / `U:A:` / `MON:`, not special cases.**  
There is no speed-exception field to invent in the display string.

### Real exceptions (monitoring include/exclude only)

| Need | Mechanism |
|---|---|
| Do **not** alert on this admin-up port | **`X:…`** exclusion code |
| Do monitor on access (opt-in) | **`U:` / `W:` / `M:` / `MON:`** include code |
| Human note (“why is this 1G?”) | NetBox **description** (ops only — Zabbix ignores it for triggers) |

### Speed rules

| Link | Zabbix |
|---|---|
| `U:D:` / `U:A:` / `U:C:` / `MON:` | Baseline / degrade from stable oper speed |
| `U:P:` | Fixed expect **1G** |
| Forced Extreme admin (auto-neg off) | Expected = admin speed |

### 4.1 Description = human notes (optional for speed, required clarity for `MON:`)

Description does **not** drive Zabbix speed triggers. It stops humans chasing known plant limits or misreading ESX/iDRAC ports.

| Display | Description (examples) |
|---|---|
| `U:D:swa12` | `Uplink to swa12` *(speed optional — baseline has it)* |
| `U:D:swa08` | `Uplink to swa08 — plant is 1G` *(note for humans)* |
| `U:A:ps01` | `Toward PS — 100M legacy plant` *(note for humans)* |
| `MON:esx01` | `ESXi esx01 — vmnic` |
| `MON:netapp` | `NetApp ContA e0a` |
| `MON:idr3` | `iDRAC dell-r740-03` |
| `U:P:ap3f07` | `AP ap-3f-07` |

No NetBox tags for speed or monitor intent.

### 4.2 Servers / ESX / storage / iDRAC on mgmt or core

These are **not** fabric uplinks (`U:…`). Pattern:

1. Port is **admin-up** on mgmt/core → Zabbix already includes it (minus `X:`).  
2. Set display **`MON:`** or **`MON:<short>`** (≤15 total) so the class is obvious on the switch and in LLD labels.  
3. Put identity in **description** (hostname, role, NIC).  
4. Speed = **baseline** (often 1G or 10G to ESX/storage; iDRAC often 1G/100M).  
5. If a port must stay up but must **not** alert → `X:…`, not `MON:`.

**Access switch** edge to a server (rare vs mgmt): same `MON:` / `MON:<id>` — required for LLD include.

---

## 5. NetBox = compliance, not dual monitor SoT

| Check | Action |
|---|---|
| Cable Access↔AP, display not `U:P:…` | Report: set/fix display |
| Cable Access↔Dist, display not `U:A:`/`U:D:…` | Same |
| Mgmt/core port to ESX/storage/iDRAC without `MON:` | Soft report: set `MON:` + description (clarity) |
| `M:` / `MON` stale / empty description on `MON:` | Stale / incomplete list |
| Oper speed degraded vs baseline | Fix plant / optic / negotiation |
| Human note for unusual plant speed | Optional description — Zabbix does not need a speed code |
| Unused admin-up on core/dist/mgmt | Disable |

---

## 6. Architecture

```
Operator / optional cable script
        → Extreme display string (≤15, obvious codes)

NetBox description
        → human what/why (ESX, iDRAC, optional plant-speed note)

Zabbix LLD:
  core/dist/mgmt → admin-up AND NOT display~^X:
  access         → display~^(U:|W:|M:|MON)

Zabbix speed:
  U:P:  → expect 1G
  else  → baseline/degrade
           (U:D:/U:A: = 1G|10G|100M all valid)

Compliance → missing/wrong display; MON without description
```

---

## 7. Zabbix templates (intent)

| Template | Applied to | Interface discovery |
|---|---|---|
| EXOS / VOSS health | Switches | Device metrics |
| Ports fabric | Core, Dist, Mgmt | Admin-up − `X:…` |
| Ports access | Access | Include codes only |
| WAN (Phase 5) | As needed | `W:…` |

Speed macros: `{$IF.SPEED.BASELINE}` (learned); fixed 1000 for `U:P:`.

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| Cryptic codes nobody understands | Keep `U:` / `MON:` / `X:` only; details in description |
| Assuming “U:D: = 10G” then needing overrides | Rejected — use baseline; 1G/100M are normal |
| ESX/iDRAC noise on mgmt | Admin-up is intentional; use `X:` only when must exclude |
| `MON:` without description | Compliance: require description on `MON:` |
| 15-char limit | Short ids (`MON:esx01`); full name in description |
| Unused admin-up | Disable as hygiene |

---

## 9. Verify checklist

- [ ] Codes are only obvious classes (`U:C/D/A/P`, `W:`, `M:`, `MON`, `X:`)  
- [ ] Speed model understood: **baseline** for `U:`/`MON:` — no speed-exception codes  
- [ ] Real exceptions = **`X:…`** (don’t monitor) or access include codes  
- [ ] Mgmt/core: ESX / storage / iDRAC use **`MON:` + description**  
- [ ] Access include-only; AP = `U:P:` expect 1G  
- [ ] Canaries: 10G `U:D:`, 1G `U:D:`, 100M `U:A:`, `MON:esx…`, `MON:idr…`, `U:P:`, `X:STK`  

---

## 10. Summary (cross-check)

```
DISPLAY = short obvious class only (≤15)
  U:C: U:D: U:A: U:P: W: M: MON / MON:<id>
  X:STK X:SPN X:OOB X:INT X
  NO speed nibbles (no D1 / A01)

DESCRIPTION = human why/what
  intentional 1G or 100M uplink
  ESXi / storage / iDRAC / server identity
  NO NetBox tags for this

ZABBIX SPEED
  U:D: / U:A: / U:C: / MON: → baseline (1G|10G|100M OK)
  U:P: → expect 1G

MGMT/CORE = admin-up − X: ; label endpoints MON:+description
ACCESS    = include codes only
AP        = U:P: on access switch

TRACK B = LLD/compliance automation (separate)
```
