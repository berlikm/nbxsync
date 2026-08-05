# Port identity — baseline

What Zabbix uses to scope Extreme switch ports: an on-box label (prefer SNMP `ifAlias`) with a shared grammar for class, optional speed, and far-end ID. Covers LLD include/exclude, speed expectation, and notes. Label push tooling and LAG/MLAG/MLT are out of scope here.

---

## 1. Grammar

```
CLASS
CLASS-ID
CLASS-SPEED-ID
```

| Piece | Rules |
|---|---|
| **CLASS** | `USW` `US` `UP` `MON` `UW` `TMON` `X` `N` |
| **SPEED** | Canonical tokens only (`2G5` not `2.5G`) — not used on `X` / `N` |
| **ID** | Far-end / free text after normalize |
| **Case** | Store UPPERCASE; match case-insensitive |
| **Length** | Max **64** characters |
| **Forbidden** | `:` space `"` `<>` `&` `?` ; first char alphanumeric |

---

## 2. Classes

### 2.1 Include / monitor

| CLASS | Meaning | Default speed | Absolute expect | Alerts |
|---|---|---|---|---|
| `USW` | Switch ↔ switch | 10G | Yes | link / flap / errors + speed |
| `US` | Server / storage | 10G | Yes | same |
| `UP` | Toward AP | 1G | Yes | same |
| `MON` | Other endpoint (iDRAC, client, …) | 1G | Yes | same |
| `UW` | Uplink WAN / ISP | — | Later | link / flap / errors |
| `TMON` | Temp watch | — | No | items; optional link-down **INFO** only |

**`TMON`:** keep a list of `TMON*` for ops review; reason in NetBox description.

### 2.2 Exclude — class `X`

| Display | Meaning |
|---|---|
| `X` / `X-<note>` | Excluded — optional free-form note |

Zabbix takes **no port alerts** on `X*`. Reason may also live in NetBox description.

### 2.3 Note only — class `N`

| Display | Meaning |
|---|---|
| `N` / `N-<text>` | Free-form note — no Zabbix action |

`N` is for freedom in on-box descriptions that are not excludes and not monitored classes.

---

## 3. Speed tokens

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

Expected speed = SPEED token if present, else class default (`USW`/`US` → 10G, `UP`/`MON` → 1G).

---

## 4. Zabbix resolution

```
1) Label empty → EMPTY; else parse class
2) Class X or N → no port alerts
3) Else include per role LLD (§5)
4) Discovered + {USW,US,UP,MON,UW} → link-down / flap / errors
5) Discovered + {USW,US,UP,MON} → expected speed = token or class default;
      ifHighSpeed ≠ expected ≥5m while oper-up → WARNING
6) Discovered + {USW,US,UP,MON,UW} → change(ifHighSpeed) vs last stable oper-up ≥5m → WARNING;
      suppress in maintenance windows
7) TMON → items + optional link-down INFO only (no speed / change WARN)
```

Turn on step 5 after labels for that site follow this grammar.

---

## 5. Role × LLD

| Device role | LLD |
|---|---|
| **Core / Dist / Mgmt** | Admin-up AND NOT class `X` AND NOT class `N` |
| **Access** | Include classes only (`USW` `US` `UP` `MON` `UW` `TMON`) |
| **Subsidiary hybrid** | Same as fabric; labeling below |
| **AP** | Device health — not switch-port LLD |

Unused ports → admin-down.

**Hybrid:**

```
1) Spares / unused            → admin-down
2) Admin-up but uninteresting → X / X-<note> or N / N-<text>
3) Monitor / temp             → USW / US / UP / MON / UW / TMON / …
```

---

## 6. LAG / MLAG / MLT

Deferred — physical ports first. Notes for later are in the TODO.

---

## 7. On-box fields

| Platform | Write label to |
|---|---|
| EXOS | Field that drives `ifAlias` (see TODO) |
| VOSS | Port `name` (or `name port <list>` for several ports) |

Zabbix polls SNMP (`ifAlias` preferred).

---

## 8. Examples

| Scenario | Display | Expect |
|---|---|---|
| Switch ↔ switch 10G | `USW-10G-SWD14` | 10G |
| Switch ↔ switch 1G | `USW-1G-SWA08` | 1G |
| Server / ESXi 10G | `US-10G-ESX01` | 10G |
| Storage 10G | `US-10G-SAN01` | 10G |
| AP 1G | `UP-1G-AP3F07` | 1G |
| AP 2.5G | `UP-2G5-AP07` | 2.5G |
| iDRAC | `MON-1G-IDR03` | 1G |
| WAN uplink | `UW-SC1` | link/flap/errors |
| Temp watch | `TMON-GUEST` | items + INFO link-down |
| Exclude | `X` / `X-STACK` | none |
| Note only | `N-SPARE` | no action |

---

## TODO

- [ ] VOSS: confirm port `name` → `ifAlias` (`…31.1.1.1.18`); else `ifDescr` + per-platform OID
- [ ] EXOS: which of `display-string` / `description-string` wins for `ifAlias` at 64
- [ ] Apply labels on pilots → enable absolute-expect
- [ ] Port template: link/flap/errors, absolute expect, change vs stable-up, maintenance suppress
- [ ] Later: revisit **LAG / MLAG / MLT** monitoring (focus is physical ports for now)
