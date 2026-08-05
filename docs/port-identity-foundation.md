# Port identity — baseline

**On box:** Extreme port label → SNMP (prefer `ifAlias`)  
**Scope:** Zabbix port LLD, speed expectation, notes  
**Out of scope for now:** label push tooling (separate); LAG / MLAG / MLT monitoring (revisit later)

---

## 1. Locked decisions

1. **Grammar:** `CLASS[-SPEED]-ID`, hyphen separators, labels stored **UPPERCASE**.  
2. **Budget:** 64 characters (VOSS port `name` + EXOS `ifAlias` default).  
3. **Monitored labels include SPEED** where a default applies; ID is the real far-end name.  
4. **Classes:** `USW` `US` `MON` `UW` `TMON` | `X` (exclude) | `N` (note only).  
5. **Defaults:** `USW`/`US` → 10G; `MON` → 1G.  
6. **Set on box:** EXOS → field that drives `ifAlias`; VOSS → port `name` / `name port <list>`.  
7. **Zabbix** reads empty vs parsed class. Turn on “speed must equal expected” only after labels are in place.  
8. **Access LLD** matches include classes only; missing labels are fixed in inventory/ops, not by a Zabbix safety net.  
9. **Hybrid:** admin-down spares; `X` / `N` on up-but-uninteresting; monitored clients get `US` / `MON` / ….  
10. **Port intent lives in the label** — not NetBox monitor tags.  
11. **LAG / MLAG / MLT** — revisit later; focus is physical ports.

---

## 2. Grammar

```
CLASS
CLASS-ID
CLASS-SPEED-ID
```

| Piece | Rules |
|---|---|
| **CLASS** | `USW` `US` `MON` `UW` `TMON` `X` `N` |
| **SPEED** | Canonical tokens only (`2G5` not `2.5G`) — not used on `X` / `N` |
| **ID** | Far-end / free text after normalize |
| **Case** | Store UPPERCASE; match case-insensitive |
| **Forbidden** | `:` space `"` `<>` `&` `?` ; first char alphanumeric |

**Platform lengths (ports only):**

| Field | Size |
|---|---|
| VOSS port `name` | 0–64 (`WORD<0-64>`) |
| EXOS `display-string` | 20 |
| EXOS `description-string` | 255 |
| EXOS SNMP `ifAlias` | 64 default |

**Parser** (after uppercase normalize):

```
# Note only — free text, no Zabbix action
^N(-(?<note>[A-Z0-9-]+))?$

# Exclude
^X(-(?<xnote>[A-Z0-9-]+))?$

# Monitor / temp (TMON before MON)
^(?<class>USW|US|TMON|MON|UW)(-(?<speed>100M|1G|2G5|5G|10G|25G|40G|100G|400G))?(-(?<id>[A-Z0-9-]+))?$
```

---

## 3. Classes

| CLASS | Meaning | Default speed | Absolute expect | Alerts |
|---|---|---|---|---|
| `USW` | Switch ↔ switch | 10G | Yes | link / flap / errors + speed |
| `US` | Server / storage | 10G | Yes | same |
| `MON` | Other monitored endpoint (iDRAC, AP, client, …) | 1G | Yes | same |
| `UW` | Uplink WAN / ISP | — | Later | link / flap / errors |
| `TMON` | Temp watch | — | No | items; optional link-down **INFO** only |
| `X` / `X-<text>` | Excluded | — | No | **none** |
| `N` / `N-<text>` | Note only — free description | — | No | **none** |

`X` = deliberately excluded from port monitoring.  
`N` = free-form note, Zabbix takes **no action**.  
`TMON` = temporary watch — collect metrics; optional INFO link-down; keep a list of `TMON*` for ops review; reason in NetBox description.

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

Expected speed = SPEED token if present, else class default (`USW`/`US` → 10G, `MON` → 1G).

---

## 5. Zabbix resolution

```
1) Label empty → EMPTY; else parse class
2) Class X or N → no port alerts
3) Else include per role LLD (§6)
4) Discovered + {USW,US,MON,UW} → link-down / flap / errors
5) Discovered + {USW,US,MON} → expected speed = token or class default;
      ifHighSpeed ≠ expected ≥5m while oper-up → WARNING
6) Discovered + {USW,US,MON,UW} → change(ifHighSpeed) vs last stable oper-up ≥5m → WARNING;
      suppress in maintenance windows
7) TMON → items + optional link-down INFO only (no speed / change WARN)
```

Turn on step 5 after labels for that site follow this grammar.

---

## 6. Role × LLD

| Device role | LLD |
|---|---|
| **Core / Dist / Mgmt** | Admin-up AND NOT class `X` AND NOT class `N` |
| **Access** | Include classes only (`USW` `US` `MON` `UW` `TMON`) |
| **Subsidiary hybrid** | Same as fabric; labeling below |
| **AP** | Device health — not switch-port LLD |

Unused ports → admin-down.

**Hybrid:**

```
1) Spares / unused            → admin-down
2) Admin-up but uninteresting → X / X-<text> or N / N-<text>
3) Monitor / temp             → USW / US / MON / UW / TMON / …
```

---

## 7. LAG / MLAG / MLT

Deferred — physical ports first. Notes for later are in the TODO.

---

## 8. On-box fields

| Platform | Write label to |
|---|---|
| EXOS | Field that drives `ifAlias` (see TODO) |
| VOSS | Port `name` (or `name port <list>` for several ports) |

Zabbix polls SNMP (`ifAlias` preferred).

---

## 9. Examples

| Scenario | Display | Expect |
|---|---|---|
| Switch ↔ switch 10G | `USW-10G-SWD14` | 10G |
| Switch ↔ switch 1G | `USW-1G-SWA08` | 1G |
| Server / ESXi 10G | `US-10G-ESX01` | 10G |
| Storage 10G | `US-10G-SAN01` | 10G |
| iDRAC | `MON-1G-IDR03` | 1G |
| AP 1G | `MON-1G-AP3F07` | 1G |
| AP 2.5G | `MON-2G5-AP07` | 2.5G |
| WAN uplink | `UW-SC1` | link/flap/errors |
| Temp watch | `TMON-GUEST` | items + INFO link-down |
| Exclude | `X` / `X-STK` | none |
| Note only | `N-STACK` / `N-SPARE` | no action |

---

## TODO

- [ ] VOSS: confirm port `name` → `ifAlias` (`…31.1.1.1.18`); else `ifDescr` + per-platform OID
- [ ] EXOS: which of `display-string` / `description-string` wins for `ifAlias` at 64
- [ ] Apply labels on pilots → enable absolute-expect
- [ ] Port template: link/flap/errors, absolute expect, change vs stable-up, maintenance suppress
- [ ] Later: revisit **LAG / MLAG / MLT** monitoring (focus is physical ports for now)
