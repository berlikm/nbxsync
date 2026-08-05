# Port identity foundation (consistent)

**Status:** Locked design direction  
**Operator SoT:** Extreme **display string only** (≤15 characters)  
**NetBox role:** Inventory, cables, circuits, **compliance**, and **`Interface.speed` for Jinja config** — not monitoring expected speed / not a second place to edit monitor intent  
**Related plan:** `docs/internet-network-monitoring-plan.md` (Track A)

---

## 1. Locked decisions

1. **Display string = only operator control** for port class / monitor / exclude (one edit on the switch).  
2. **Do not** use NetBox interface tags for day-to-day “monitor this port” (dual-edit overhead rejected).  
3. **NetBox compliance** reports drift (“cable says AP port but display missing/wrong”).  
4. **Core / Dist / Mgmt:** monitor all **admin-up** ports, minus **exclusion display codes** (and platform excludes). Unused admin-up → disable (security housekeeping).  
5. **Access:** monitor only ports with **include** display codes (`U:…`, `W:…`, `M:…`, `MON`).  
6. **APs** attach to **access switches** — code `U:P:…`, expect **1G**.  
7. **Access↔Dist speeds are mixed** — do **not** assume fleet-wide 10G as monitoring expected.  
8. **NetBox `Interface.speed`** = **static configured speed for Jinja config generation** (render/push port speed).  
   It is **not** a monitoring “intended speed” field and must not be overloaded as Zabbix expected.  
9. **Manual OK** when far-end device / cable missing in NetBox — set display string on the switch.  
10. Optional Python: cable → push display code (helps at scale); never requires a parallel tag.  
11. Track B (nbxsync / Zabbix LLD / compliance jobs) is a **separate** task.

---

## 2. Display string codes (≤15)

ASCII, no spaces. Script enforces length.

### Include / classify (monitor these on access; label on any role)

| Code | Meaning | Speed note |
|---|---|---|
| `U:C:<id>` | Uplink toward core | Mixed — see §4 |
| `U:D:<id>` | Uplink toward dist | Mixed — see §4 |
| `U:D1:<id>` | Dist uplink, **intentional 1G** (ops-visible) | Prefer baseline; nibble optional |
| `U:A:<id>` | Uplink toward access | Mixed — see §4 |
| `U:A1:<id>` | Access uplink, **intentional 1G** (ops-visible) | Prefer baseline; nibble optional |
| `U:P:<id>` | Access switch → **AP** | **1G** (almost always) |
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

## 4. Speed — three different concepts (do not mix)

| Concept | Where it lives | Purpose |
|---|---|---|
| **Static / configured speed** | NetBox `Interface.speed` (+ Extreme admin when forced) | **Jinja config generation** — render the port speed into switch config |
| **Operational speed** | SNMP `ifHighSpeed` / `ifSpeed` | What the link negotiated **now** |
| **Monitoring expected** | Zabbix baseline / rare display nibble | What to **alert** on (degrade / mismatch) |

**Locked:** NetBox `Interface.speed` is **config data for templates**, not “intended monitoring speed.”  
Do not invent a parallel NetBox `expected_speed` just for Zabbix if that duplicates or fights Jinja.

### Monitoring model (Phase 2)

```
if display is U:P:     → expect ~1000 Mb/s (AP class is stable enough)
elif Extreme forced     → expected = extremePortAdminSpeed (auto-neg off)
else                    → learn baseline from first stable ifHighSpeed
                          alert if oper speed drops / changes (degrade)
optional: U:D1: / U:A1: → ops-visible “intentional 1G” hint (not required if baseline exists)
```

| Class | Monitoring approach |
|---|---|
| `U:P:` | Fixed **1G** (catch 100M fallback) |
| `U:A:` / `U:D:` / `U:C:` | **Baseline / degrade** — fleet uplink speeds are mixed |
| Forced admin speed | Compare oper ↔ Extreme admin |
| NetBox `Interface.speed` | Config/Jinja only — optional **compliance**: rendered config vs live Extreme admin |

Alert: oper-up and (below baseline / ≠ forced admin / ≠ 1G on `U:P:`) → WARNING.  
Util% (later) needs Circuit/commit bandwidth — not “whatever ifHighSpeed is today” alone.

---

## 5. NetBox = compliance + config SoT, not dual monitor SoT

| Check | Action |
|---|---|
| Cable Access↔AP, display not `U:P:…` | Report: set/fix display on switch |
| Cable Access↔Dist, display not `U:A:`/`U:D:`… | Same |
| Display `U:P:` but no cable | OK manual; or document later |
| `M:` / `MON` older than policy | Stale temp list |
| NetBox `Interface.speed` vs Extreme admin (forced ports) | Config drift for Jinja path |
| Oper speed degraded vs Zabbix baseline | Fix cable/optic/negotiation |
| Admin-up unused on core/dist/mgmt | Disable port |

Operators fix **monitor intent on the switch** (display string).  
Operators/automation fix **configured speed in NetBox** for Jinja. No monitor-tags.

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
| Speed false WARN | Baseline / re-learn after intentional upgrade; don’t use class 10G |
| NetBox speed ≠ monitor expected | Keep Jinja speed separate from Zabbix baseline |

---

## 9. Verify checklist

- [ ] Display ≤15 confirmed on EXOS + VOSS  
- [ ] Include codes + **exclusion `X:…`** approved  
- [ ] Core/dist/mgmt = admin-up − `X:`  
- [ ] Access = display include only (no NetBox monitor tags)  
- [ ] AP on access = `U:P:` expect 1G  
- [ ] Access↔dist = **baseline/degrade** (no fleet-wide 10G assumed)  
- [ ] NetBox `Interface.speed` = Jinja config only (not Zabbix expected)  
- [ ] Compliance reports listed (display drift; optional config-speed drift)  
- [ ] Canary: core, dist, access, AP port, excluded stack port, speed degrade  

---

## 10. Summary (cross-check)

```
OPERATOR SOT = Extreme display string only (≤15)
  Include: U:C: U:D: U:D1: U:A: U:A1: U:P: W: M: MON
  Exclude: X:STK X:SPN X:OOB X:INT X
  ONE edit on switch — NO monitor tags in NetBox for ops

NETBOX = cables/circuits + compliance + Interface.speed for JINJA CONFIG
         (static configured speed — NOT monitoring “intended” speed)

SPEED MONITORING:
  U:P:     → expect 1G
  U:A/D/C: → baseline/degrade (mixed uplink speeds)
  Forced:  → Extreme admin speed
  Do not use NetBox Interface.speed as Zabbix expected

CORE/DIST/MGMT = all admin-up minus X: codes; unused → disable
ACCESS = only include codes; AP ports U:P:; manual string OK if no cable

ZABBIX = LLD from display (+ admin-up on fabric)
SCRIPT = optional cable→display push
TRACK B = automation/compliance jobs (separate task)
```
