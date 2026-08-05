# Port identity — baseline

**SoT on box:** Extreme port label → SNMP (prefer `ifAlias`)  
**SoT in NetBox:** inventory (cables, roles, `interface.speed`) → authoritative generator; description = prose  
**Scope:** Zabbix port LLD, speed expectation, excludes

---

## 1. Locked decisions

1. **Grammar:** `CLASS[-SPEED]-ID`, hyphen separators, uppercase on push.  
2. **Budget:** 64 characters (VOSS `name` + EXOS `ifAlias` default).  
3. **Generated labels always include SPEED**; ID is the real far-end name.  
4. **Classes:** `UC` `UD` `UA` `UP` `MON` `W` `TMON` | `X` (optional note). Endpoints including iDRAC use `MON`.  
5. **Class speed defaults** when token absent: `UC`/`UD`/`UA` → 10G; `UP`/`MON` → 1G.  
6. **Push:** EXOS → field that drives `ifAlias`; VOSS → `name` / `name port <list>`.  
7. **Generator overwrites** managed ports; `display_protect` skips hand-sets.  
8. **Parse:** `EMPTY` | `PARSED`. Push overwrites legacy labels; enable absolute-expect after clean diff.  
9. **Access LLD** matches include classes only; missing labels are a compliance problem, not a Zabbix safety net.  
10. **Hybrid:** admin-down spares; `X` on up-but-uninteresting; monitored clients get `MON-<ID>`.  
11. **LAG speed expect** on members only.  
12. **Port intent lives in the label** — not NetBox monitor tags.

---

## 2. Grammar

```
CLASS
CLASS-ID
CLASS-SPEED-ID
```

| Piece | Rules |
|---|---|
| **CLASS** | Atomic token from vocabulary |
| **SPEED** | Canonical tokens only (`2G5` not `2.5G`) |
| **ID** | `[A-Z0-9-]+` after normalize |
| **Case** | Generator UPPERCASE; parser case-insensitive |
| **Forbidden** | `:` space `"` `<>` `&` `?` ; first char alphanumeric |

**Platform lengths:**

| Field | Size |
|---|---|
| VOSS port `name` | 0–64 (`WORD<0-64>`) |
| VOSS MLT `name` | 0–64 |
| EXOS `display-string` | 20 |
| EXOS `description-string` | 255 |
| EXOS SNMP `ifAlias` | 64 default |

**Parser** (after uppercase normalize):

```
^X(-(?<xnote>STK|ISC|MLAG|SPN|OOB|OTH|[A-Z0-9]{1,12}))?$

^(?<class>UC|UD|UA|UP|MON|W|TMON)(-(?<speed>100M|1G|2G5|5G|10G|25G|40G|100G|400G))?(-(?<id>[A-Z0-9-]+))?$
```

`X` notes when generated: `STK` `ISC` `MLAG` `SPN` `OOB` `OTH`.

---

## 3. Classes

| CLASS | Meaning | Default speed | Absolute expect | Alerts |
|---|---|---|---|---|
| `UC` | Toward core | 10G | Yes | link / flap / errors + speed |
| `UD` | Toward dist | 10G | Yes | same |
| `UA` | Toward access | 10G | Yes | same |
| `UP` | Toward AP | 1G | Yes | same |
| `MON` | Endpoint (server, ESX, storage, iDRAC, …) | 1G | Yes | same |
| `W` | WAN / ISP | — | Later | link / flap / errors |
| `TMON` | Temp watch | — | No | items; optional link-down INFO |
| `X` / `X-<NOTE>` | Excluded | — | No | none |

**`TMON`:** compliance lists all `TMON*`; ops review cadence; reason in NetBox description.

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

Generator emits SPEED from NetBox `interface.speed`, else class default.

---

## 5. Zabbix resolution

```
1) Classify: EMPTY | PARSED
2) Class X → skip port alerts
3) Else include per role LLD (§6)
4) Discovered + {UC,UD,UA,UP,MON,W} → link-down / flap / errors
5) Discovered + {UC,UD,UA,UP,MON} → absolute expect (token or class default);
      ifHighSpeed ≠ expected ≥5m while oper-up → WARNING
6) Discovered + not TMON → change(ifHighSpeed) vs last stable oper-up ≥5m → WARNING;
      suppress in maintenance windows
7) TMON → items + optional link-down INFO
```

---

## 6. Role × LLD

| Device role | LLD |
|---|---|
| **Core / Dist / Mgmt** | Admin-up AND NOT class `X` |
| **Access** | Include classes only |
| **Subsidiary hybrid** | Same as fabric; labeling below |
| **AP** | Device health — not switch-port LLD |

Unused ports → admin-down.

**Hybrid:**

```
1) Spares / unused            → admin-down
2) Admin-up but uninteresting → X / X-<NOTE>
3) Monitor                    → MON-<ID> / UP / W / …
```

---

## 7. LAG / MLAG

| Rule | Decision |
|---|---|
| Speed expect | Members only |
| Aggregate ifIndex | Up/down / member-count |
| Peer-link | `X-MLAG` / `X` |

---

## 8. Generator

```
NetBox → generator → Extreme field that drives ifAlias
       → Zabbix polls ifAlias
```

| Input | Output |
|---|---|
| `display_protect` | Skip |
| Hybrid spare | admin-down |
| Hybrid up-but-uninteresting | `X` / `X-<NOTE>` |
| Hybrid/client monitor | `MON-<ID>` |
| Cable + speed | `UD-10G-…` / `UA-1G-…` |
| Endpoint | `MON-…` |
| WAN | `W-…` |

VOSS: `name port <portlist>` when one label applies to many ports.

---

## 9. Examples

| Scenario | Display | Expect |
|---|---|---|
| Access↔dist 10G | `UD-10G-SWD14` / `UA-10G-SWA08` | 10G |
| Access↔dist 1G | `UD-1G-SWD2` / `UA-1G-SWA2` | 1G |
| AP 1G | `UP-1G-AP3F07` | 1G |
| AP 2.5G | `UP-2G5-AP07` | 2.5G |
| ESXi 10G | `MON-10G-ESX01` | 10G |
| iDRAC | `MON-1G-IDR03` | 1G |
| WAN | `W-SC1` | link/flap/errors |
| Temp | `TMON-GUEST` | items + INFO link-down |
| Exclude stack | `X-STK` | excluded |

---

## TODO

- [ ] VOSS: confirm `name` → `ifAlias` (`…31.1.1.1.18`); else `ifDescr` + per-platform OID
- [ ] EXOS: which of `display-string` / `description-string` wins for `ifAlias` at 64
- [ ] Confirm ifAlias ingest does not write into generator-owned NetBox fields
- [ ] Generator + `display_protect` + compliance diff
- [ ] Push → clean baseline → enable absolute-expect
- [ ] Port template: link/flap/errors, absolute expect, change vs stable-up, maintenance suppress
