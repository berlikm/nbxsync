# Port identity foundation (Zabbix focus)

**Status:** Locked design direction  
**Operator SoT:** Extreme **display string only** (≤15 characters)  
**Scope:** How Zabbix discovers and alerts on ports — not switch-config generation  
**NetBox role (here):** Inventory, cables, circuits, **compliance**, interface **description** for human notes — not a second place to edit monitor intent  
**Related plan:** `docs/internet-network-monitoring-plan.md` (Track A)

---

## 1. Locked decisions

1. **Display string = only operator control** for port class / monitor / exclude (one edit on the switch).  
2. **Do not** use NetBox interface tags for day-to-day “monitor this port” (dual-edit overhead rejected).  
3. **NetBox compliance** reports drift (“cable says AP port but display missing/wrong”).  
4. **Core / Dist / Mgmt:** monitor all **admin-up** ports, minus **exclusion display codes** (and platform excludes). Unused admin-up → disable (security housekeeping).  
5. **Access:** monitor only ports with **include** display codes (`U:…`, `W:…`, `M:…`, `MON`).  
6. **APs** attach to **access switches** — code `U:P:…`, expect **1G** in Zabbix (catch 100M fallback).  
7. **Dist ↔ access uplinks are mixed:** commonly **1G**, also **10G**, and in edge cases **100M**. Do **not** assume one fleet-wide expected speed in Zabbix.  
8. **Manual OK** when far-end device / cable missing in NetBox — set display string on the switch.  
9. Optional Python: cable → push display code (helps at scale); never requires a parallel tag.  
10. Track B (nbxsync / Zabbix LLD / compliance jobs) is a **separate** task.

---

## 2. Display string codes (≤15)

ASCII, no spaces. Script enforces length.

### Include / classify (monitor these on access; label on any role)

| Code | Meaning | Zabbix speed note |
|---|---|---|
| `U:C:<id>` | Uplink toward core | Mixed — baseline / degrade |
| `U:D:<id>` | Uplink toward dist | Mixed **1G / 10G / 100M** — baseline / degrade |
| `U:D1:<id>` | Dist uplink, intentional **1G** (ops-visible) | Optional nibble; baseline still fine |
| `U:D01:<id>` | Dist uplink, intentional **100M** (ops-visible) | Rare; id must stay short |
| `U:A:<id>` | Uplink toward access | Mixed **1G / 10G / 100M** — baseline / degrade |
| `U:A1:<id>` | Access uplink, intentional **1G** (ops-visible) | Optional nibble |
| `U:A01:<id>` | Access uplink, intentional **100M** (ops-visible) | Rare |
| `U:P:<id>` | Access switch → **AP** | Expect **1G** (almost always) |
| `W:<isp><n>` | WAN / ISP | Phase 5 / Circuit |
| `M:<yymmdd>` | Temp monitor until date | — |
| `MON` | Standing opt-in (edge) | — |

Examples: `U:C:swc01`, `U:D:swa12`, `U:P:ap3f07`, `U:A01:ps`, `W:SC1`, `M:260830`, `MON`.

Speed nibbles are optional. Prefer **NetBox description** for the human “why” (see §4.1). Do **not** use NetBox tags for speed edge cases.

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

## 4. Speed in Zabbix

Dist ↔ access (and similar fabric uplinks) run at **1G, 10G, or occasionally 100M**. Zabbix must not hardcode “expect 10G” or “expect 1G” for those classes.

| Signal | Source | Use in Zabbix |
|---|---|---|
| **Operational speed** | SNMP `ifHighSpeed` / `ifSpeed` | What the link negotiated **now** |
| **Baseline / expected** | Learned from first stable oper speed (or Extreme admin if forced) | What to **alert** on (degrade / mismatch) |
| **Human “why”** | NetBox interface **description** | Explains intentional odd speeds — not an alert input |

### Monitoring model

```
if display is U:P:     → expect ~1000 Mb/s (AP class is stable enough)
elif Extreme forced     → expected = extremePortAdminSpeed (auto-neg off)
else                    → learn baseline from first stable ifHighSpeed
                          alert if oper speed drops / changes (degrade)
```

| Class | Zabbix approach |
|---|---|
| `U:P:` | Fixed **1G** — alert on 100M fallback |
| `U:A:` / `U:D:` / `U:C:` | **Baseline / degrade** — 1G, 10G, and 100M all valid |
| Forced Extreme admin | Compare oper ↔ admin |
| Optional `U:A1:` / `U:D1:` / `U:A01:` / `U:D01:` | Ops-visible hint on box only — not required if baseline exists |

Alert: oper-up and (below baseline / ≠ forced admin / ≠ 1G on `U:P:`) → WARNING.  
Util% (later, Phase 6) is separate from speed-mismatch alerts.

### 4.1 Known intentional odd speeds (e.g. 100M) — description, not a tag

**Edge case:** uplink that is **supposed** to run at 100M (legacy far-end, PS/special device, plant limit). Rare, but real. Same pattern for intentional 1G when peers are often 10G.

| Where | What to put | Why |
|---|---|---|
| **NetBox interface description** | e.g. `Intentional 100M uplink to PS; legacy endpoint — do not chase as fault` | Readable, searchable — **preferred for the story** |
| **Extreme display string** | e.g. `U:A:ps01` or `U:A01:ps` | Monitor class / LLD; ≤15 |
| **NetBox tag** (e.g. `speed:100m`) | **Do not** | Dual taxonomy; rejected for port intent |

**Zabbix behavior:**

1. Baseline learns **100M** → no false WARN.  
2. Alert if speed drops further (e.g. 10M) or flaps.  
3. Jump to 1G/10G after a plant change → baseline re-learn / ack, not necessarily outage.  
4. Description tells the next engineer *why* 100M is correct.

**Worked examples (Zabbix view)**

| Scenario | Display (≤15) | NetBox description | Zabbix |
|---|---|---|---|
| Dist↔access **10G** | `U:D:swa12` | *(optional)* `Uplink to swa12` | Baseline **10000** |
| Dist↔access **1G** (common) | `U:D:swa08` or `U:D1:swa08` | `1G uplink to swa08` | Baseline **1000** |
| Dist↔access **100M** (edge) | `U:A:ps01` or `U:A01:ps` | `Intentional 100M uplink to PS; legacy` | Baseline **100**; **no tag** |
| Access → AP | `U:P:ap3f07` | `AP ap-3f-07` | Expect **1G** (WARN on 100M fallback) |
| Temp edge monitor | `M:260830` | `Temp monitor until 2026-08-30` | Include via `M:` |

**Rule of thumb:** description = **why**; display = **what to monitor**; Zabbix baseline = **speed alerts**; tags = **not for this**.

---

## 5. NetBox = compliance, not dual monitor SoT

| Check | Action |
|---|---|
| Cable Access↔AP, display not `U:P:…` | Report: set/fix display on switch |
| Cable Access↔Dist, display not `U:A:`/`U:D:`… | Same |
| Display `U:P:` but no cable | OK manual; or document later |
| `M:` / `MON` older than policy | Stale temp list |
| Oper speed degraded vs Zabbix baseline | Fix cable/optic/negotiation |
| Intentional odd speed (100M, etc.) | Document in **description**; do not use a speed tag |
| Admin-up unused on core/dist/mgmt | Disable port |

Operators fix **monitor intent on the switch** (display string). No monitor-tags.

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
  speed          → U:P: expect 1G; else baseline/degrade
                   (dist↔access: 1G / 10G / 100M all valid)

NetBox compliance job → reports only (+ description for odd speeds)
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
Speed: `{$IF.SPEED.BASELINE}` (learned) or fixed 1000 for `U:P:`.

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
| Speed false WARN on mixed uplinks | Baseline / degrade — never assume one class speed |
| Intentional 100M chased as fault | NetBox **description**; baseline accepts 100M |

---

## 9. Verify checklist

- [ ] Display ≤15 confirmed on EXOS + VOSS  
- [ ] Include codes + **exclusion `X:…`** approved  
- [ ] Core/dist/mgmt = admin-up − `X:`  
- [ ] Access = display include only (no NetBox monitor tags)  
- [ ] AP on access = `U:P:` expect 1G  
- [ ] Dist↔access = **1G / 10G / 100M** via baseline/degrade (no single expected)  
- [ ] Intentional odd speed → **description**, not tag  
- [ ] Compliance reports listed (display drift)  
- [ ] Canary: 10G uplink, 1G uplink, 100M intentional, AP port, excluded stack port  

---

## 10. Summary (cross-check)

```
OPERATOR SOT = Extreme display string only (≤15)
  Include: U:C: U:D: U:D1: U:D01: U:A: U:A1: U:A01: U:P: W: M: MON
  Exclude: X:STK X:SPN X:OOB X:INT X
  ONE edit on switch — NO monitor tags in NetBox for ops

NETBOX (this doc) = cables/circuits + compliance + description (why)
  Focus = Zabbix monitoring — not switch-config generation

SPEED (Zabbix):
  Dist↔access = mixed 1G / 10G / 100M → baseline/degrade
  U:P: → expect 1G
  Forced Extreme admin → compare oper ↔ admin
  Intentional odd speed → DESCRIPTION, not a tag

CORE/DIST/MGMT = all admin-up minus X: codes; unused → disable
ACCESS = only include codes; AP ports U:P:; manual string OK if no cable

ZABBIX = LLD from display (+ admin-up on fabric) + speed baseline
SCRIPT = optional cable→display push
TRACK B = automation/compliance jobs (separate task)
```
