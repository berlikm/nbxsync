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
3. **NetBox description** = human-readable **why / what** (speed exceptions, ESX, storage, iDRAC, etc.). Codes stay short and obvious.  
4. **No cryptic speed nibbles** in the display string (`U:D1:`, `U:A01:`, …). People will not remember them. Speed → Zabbix **baseline**; intentional odd speed → **description**.  
5. **Core / Dist / Mgmt:** monitor all **admin-up** ports, minus **exclusion** codes. Unused admin-up → disable.  
6. **Access:** monitor only **include** codes (`U:…`, `W:…`, `M:…`, `MON` / `MON:…`).  
7. **APs** hang off **access** — `U:P:…`, Zabbix expects **1G** (catch 100M fallback).  
8. **Dist ↔ access** speeds are mixed (**1G / 10G / 100M**). `U:D:` / `U:A:` identify the **role**, not the speed.  
9. **Servers / ESX / storage / iDRAC** (and similar) on **mgmt or core**: still covered by admin-up LLD; set display **`MON:`** + a clear **description** so ops know what the port is.  
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

**Do not encode speed in the code.** No `U:D1:`, no `01` for 100M.

Examples (display only): `U:C:swc01`, `U:D:swa12`, `U:A:swd03`, `U:P:ap3f07`, `W:SC1`, `M:260830`, `MON`, `MON:esx01`, `MON:idr3`.

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

## 4. Speed in Zabbix

| Link | How Zabbix treats speed |
|---|---|
| `U:D:` / `U:A:` / `U:C:` / `MON:` | Learn **baseline** from stable `ifHighSpeed`. 10G stays 10G; 1G stays 1G; 100M stays 100M. Alert on **degrade/change**. |
| `U:P:` | Fixed expect **1G** (AP class). |
| Forced Extreme admin | Expected = admin speed when auto-neg off. |

**Intentional 1G or 100M uplink:** keep display as plain `U:D:<id>` / `U:A:<id>`. Write the why in **description**. Baseline learns the real speed — no special code.

### 4.1 Description = human meaning (not tags, not cryptic codes)

| Field | Holds |
|---|---|
| **Display string** | Short class: `U:D:…`, `MON:…`, `X:STK`, … |
| **NetBox description** | Full story ops can read |
| **NetBox tag** | **Do not** use for port monitor/speed intent |

**Description examples**

| Display | Description |
|---|---|
| `U:D:swa12` | `Uplink to access swa12 — 10G` *(optional; baseline already has 10G)* |
| `U:D:swa08` | `Uplink to access swa08 — intentional 1G (SFP/plant)` |
| `U:A:ps01` | `Uplink toward access/PS — intentional 100M legacy; do not chase` |
| `MON:esx01` | `ESXi esx01 — vmnic / uplink to host` |
| `MON:netapp` | `NetApp ContA e0a — storage` |
| `MON:idr3` | `iDRAC dell-r740-03 — server OOB` |
| `MON:srv12` | `Server srv12 NIC — production` |
| `U:P:ap3f07` | `AP ap-3f-07` |
| `M:260830` | `Temp monitor until 2026-08-30 — guest rack` |

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
| Intentional odd speed | **Description** only — no speed code, no tag |
| Unused admin-up on core/dist/mgmt | Disable |

---

## 6. Architecture

```
Operator / optional cable script
        → Extreme display string (≤15, obvious codes)

NetBox description
        → human why/what (1G intentional, ESX, iDRAC, …)

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
| Cryptic codes nobody understands | Keep `U:` / `MON:` / `X:` only; story in description |
| Speed false WARN on mixed uplinks | Baseline — never assume one class speed |
| ESX/iDRAC noise on mgmt | Admin-up is intentional; use `X:` only when must exclude |
| `MON:` without description | Compliance: require description on `MON:` |
| 15-char limit | Short ids (`MON:esx01`); full name in description |
| Unused admin-up | Disable as hygiene |

---

## 9. Verify checklist

- [ ] Codes are only obvious classes (`U:C/D/A/P`, `W:`, `M:`, `MON`, `X:`) — **no speed nibbles**  
- [ ] Dist↔access: `U:D:`/`U:A:` + baseline; intentional 1G/100M in **description**  
- [ ] Mgmt/core: ESX / storage / iDRAC use **`MON:` + description**  
- [ ] Access include-only; AP = `U:P:` expect 1G  
- [ ] Exclusions `X:…` validated  
- [ ] Canaries: 10G `U:D:`, 1G `U:D:` + description, 100M + description, `MON:esx…`, `MON:idr…`, `U:P:`, `X:STK`  

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
