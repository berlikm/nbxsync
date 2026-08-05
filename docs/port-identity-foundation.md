# Port identity foundation (consistent)

**Status:** Locked design direction  
**Operator SoT:** Extreme **display string only** (≤15 characters)  
**NetBox role:** Inventory, cables, circuits, **compliance** — not a second place to edit monitoring intent  
**Related plan:** `docs/internet-network-monitoring-plan.md` (Track A)

---

## 1. Locked decisions

1. **Display string = only operator control** for port class / monitor / exclude (one edit on the switch).  
2. **Do not** use NetBox interface tags for day-to-day “monitor this port” (dual-edit overhead rejected).  
3. **NetBox compliance** reports drift (“cable says AP port but display missing/wrong”).  
4. **Core / Dist / Mgmt:** monitor all **admin-up** ports, minus **exclusion display codes** (and platform excludes). Unused admin-up → disable (security housekeeping).  
5. **Access:** monitor only ports with **include** display codes (`U:…`, `W:…`, `M:…`, `MON`).  
6. **APs** attach to **access switches** — code `U:P:…`, expect **1G**.  
7. **Access↔Dist** expect **10G** by default; **1G** = rare override (`expected_speed` CF or display nibble `U:D1:`).  
8. **Manual OK** when far-end device / cable missing in NetBox — set display string on the switch.  
9. Optional Python: cable → push display code (helps at scale); never requires a parallel tag.  
10. Track B (nbxsync / Zabbix LLD / compliance jobs) is a **separate** task.

---

## 2. Display string codes (≤15)

ASCII, no spaces. Script enforces length.

### Include / classify (monitor these on access; label on any role)

| Code | Meaning | Default speed |
|---|---|---|
| `U:C:<id>` | Uplink toward core | 10G (tune) |
| `U:D:<id>` | Uplink toward dist | **10G** |
| `U:D1:<id>` | Dist uplink, **1G exception** | **1G** |
| `U:A:<id>` | Uplink toward access | **10G** |
| `U:A1:<id>` | Access uplink, **1G exception** | **1G** |
| `U:P:<id>` | Access switch → **AP** | **1G** |
| `W:<isp><n>` | WAN / ISP | Phase 5 / Circuit |
| `M:<yymmdd>` | Temp monitor until date | — |
| `MON` | Standing opt-in (edge) | — |

Examples: `U:C:swc01`, `U:P:ap3f07`, `U:D1:swd2`, `W:SC1`, `M:260830`, `MON`.

### Exclusion codes (do **not** monitor — especially on core/dist/mgmt)

On fabric roles, LLD = admin-up **except** display matching exclude prefixes (plus hard platform excludes if needed).

| Code | Meaning |
|---|---|
| `X:STK` | Stack / ISC / MLAG member |
| `X:SPN` | SPAN / mirror |
| `X:OOB` | Out-of-band / mgmt port |
| `X:INT` | Internal / do not monitor |
| `X` | Generic exclude (minimal) |

Ops set `X:…` on the switch when a port must stay admin-up but must not alert (same single SoT as includes).

---

## 3. Role matrix

| Device role | Port LLD rule |
|---|---|
| **Core / Dist / Mgmt** | All **admin-up**, minus `X:…` display codes (and optional ifName/type excludes) |
| **Access** | Only display matching `^(U:|W:|M:|MON)` |
| **AP (HiveOS)** | Device health template (Phase 1) — not fabric port LLD |

---

## 4. Speed: default always + rare overwrite

```
expected = display_nibble_if_any   # e.g. U:D1:
        or NetBox expected_speed CF  # standing exception when object exists
        or class_default(display_prefix)
```

| Class from display | Default |
|---|---|
| `U:P:` | 1000 Mb/s |
| `U:A:` / `U:D:` (no `1` nibble) | 10000 Mb/s |
| `U:C:` | 10000 Mb/s (tune) |

Alert: oper-up and speed ≠ expected → WARNING.  
No per-port speed required for normal links.

---

## 5. NetBox = compliance, not dual SoT

| Check | Action |
|---|---|
| Cable Access↔AP, display not `U:P:…` | Report: set/fix display on switch |
| Cable Access↔Dist, display not `U:A:`/`U:D:`… | Same |
| Display `U:P:` but no cable | OK manual; or document later |
| `M:` / `MON` older than policy | Stale temp list |
| Speed ≠ default and no CF / nibble | Fix link or set exception |
| Admin-up unused on core/dist/mgmt | Disable port |

Operators fix **on the switch**. No monitor-tags to maintain.

---

## 6. Architecture

```
[Optional] NetBox cable/circuit
        → Python (dry-run/apply)
        → Extreme display string (≤15 code)

Operator manual (no cable / guest device)
        → Extreme display string only

Zabbix:
  core/dist/mgmt → admin-up AND NOT display~^X:
  access         → display~^(U:|W:|M:|MON)

NetBox compliance job → reports only
```

---

## 7. Zabbix templates (intent)

| Template | Applied to | Interface discovery |
|---|---|---|
| EXOS / VOSS health | Switches | Device metrics |
| Ports fabric | Core, Dist, Mgmt | Admin-up − `X:…` |
| Ports access | Access | Include codes only |
| WAN (Phase 5) | As needed | `W:…` |

Macros by role: `{$IF.LLD.MODE}=admin_up_excl` | `display_include`.

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| Unused admin-up noise | Treat as hygiene → disable |
| Mis-roled “mgmt” access closet | Strict device roles |
| Code typos | Canonical list; compliance |
| Stale `MON`/`M:` | Compliance age report |
| Script overwrite of codes | Only managed prefixes; dry-run |
| 15-char truncation | Enforce in script; short_name CF |
| Speed false WARN | `U:D1:` or CF exception |

---

## 9. Verify checklist

- [ ] Display ≤15 confirmed on EXOS + VOSS  
- [ ] Include codes + **exclusion `X:…`** approved  
- [ ] Core/dist/mgmt = admin-up − `X:`  
- [ ] Access = display include only (no NetBox monitor tags)  
- [ ] AP on access = `U:P:` expect 1G  
- [ ] Access↔dist default 10G; exception path agreed  
- [ ] Compliance reports listed (no dual operator edit)  
- [ ] Canary: core, dist, access, AP port, excluded stack port  

---

## 10. Summary (cross-check)

```
OPERATOR SOT = Extreme display string only (≤15)
  Include: U:C: U:D: U:D1: U:A: U:A1: U:P: W: M: MON
  Exclude: X:STK X:SPN X:OOB X:INT X
  ONE edit on switch — NO monitor tags in NetBox for ops

NETBOX = cables/circuits + compliance reports + rare expected_speed CF

SPEED = class default from display; overwrite rarely

CORE/DIST/MGMT = all admin-up minus X: codes; unused → disable
ACCESS = only include codes; AP ports U:P: (1G); manual string OK if no cable

ZABBIX = LLD from display (+ admin-up on fabric)
SCRIPT = optional cable→display push
TRACK B = automation/compliance jobs (separate task)
```
