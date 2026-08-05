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

# Exclude — controlled notes (§2.2)
^X(-(?<xnote>STK|ISC|MLAG|SPN|OOB|OTH|[A-Z0-9]{1,12}))?$

# Monitor / temp (TMON before MON)
^(?<class>USW|US|UP|TMON|MON|UW)(-(?<speed>100M|1G|2G5|5G|10G|25G|40G|100G|400G))?(-(?<id>[A-Z0-9-]+))?$
```

---

## 2. Classes

### 3.1 Include / monitor

| CLASS | Meaning | Default speed | Absolute expect | Alerts |
|---|---|---|---|---|
| `USW` | Switch ↔ switch | 10G | Yes | link / flap / errors + speed |
| `US` | Server / storage | 10G | Yes | same |
| `UP` | Toward AP | 1G | Yes | same |
| `MON` | Other endpoint (iDRAC, client, …) | 1G | Yes | same |
| `UW` | Uplink WAN / ISP | — | Later | link / flap / errors |
| `TMON` | Temp watch | — | No | items; optional link-down **INFO** only |

**`TMON`:** keep a list of `TMON*` for ops review; reason in NetBox description.

### 3.2 Exclude — class `X`

| Display | Meaning |
|---|---|
| `X` | Excluded |
| `X-STK` | Stack / stacking |
| `X-ISC` | Inter-switch / ISC |
| `X-MLAG` | MLAG peer-link |
| `X-SPN` | SPAN / mirror |
| `X-OOB` | Out-of-band |
| `X-OTH` | Other exclude |

These are **notes on class `X`**, not separate classes. Reason may also live in NetBox description. Zabbix takes **no port alerts** on `X*`.

### 3.3 Note only — class `N`

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
2) Admin-up but uninteresting → X / X-<NOTE> or N / N-<text>
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
| Exclude stack | `X-STK` | none |
| Exclude MLAG | `X-MLAG` | none |
| Note only | `N-SPARE` | no action |

---

## TODO

- [ ] VOSS: confirm port `name` → `ifAlias` (`…31.1.1.1.18`); else `ifDescr` + per-platform OID
- [ ] EXOS: which of `display-string` / `description-string` wins for `ifAlias` at 64
- [ ] Apply labels on pilots → enable absolute-expect
- [ ] Port template: link/flap/errors, absolute expect, change vs stable-up, maintenance suppress
- [ ] Later: revisit **LAG / MLAG / MLT** monitoring (focus is physical ports for now)
