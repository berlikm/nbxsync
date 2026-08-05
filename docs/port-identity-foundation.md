# Port identity — baseline

**On box:** Extreme port label → SNMP (prefer `ifAlias`)  
**Scope:** Zabbix port LLD, speed expectation, excludes  
**Out of scope:** label push tooling (separate); VOSS **MLT** monitoring (skip for now)

---

## 1. Locked decisions

1. **Grammar:** `CLASS[-SPEED]-ID`, hyphen separators, labels stored **UPPERCASE**.  
2. **Budget:** 64 characters (VOSS port `name` + EXOS `ifAlias` default).  
3. **Labels include SPEED**; ID is the real far-end name.  
4. **Classes:** `UC` `UD` `UA` `UP` `MON` `W` `TMON` | `X` (optional note). Endpoints including iDRAC use `MON`.  
5. **Class speed defaults** when token absent: `UC`/`UD`/`UA` → 10G; `UP`/`MON` → 1G.  
6. **Set on box:** EXOS → field that drives `ifAlias`; VOSS → port `name` / `name port <list>`.  
7. **Zabbix** reads empty vs parsed class. Turn on “speed must equal expected” only after labels are in place.  
8. **Access LLD** matches include classes only; missing labels are fixed in inventory/ops, not by a Zabbix safety net.  
9. **Hybrid:** admin-down spares; `X` on up-but-uninteresting; monitored clients get `MON-<ID>`.  
10. **LAG:** speed expect on **members** only. MLT not monitored yet.  
11. **Port intent lives in the label** — not NetBox monitor tags.

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
^X(-(?<xnote>STK|ISC|MLAG|SPN|OOB|OTH|[A-Z0-9]{1,12}))?$

^(?<class>UC|UD|UA|UP|MON|W|TMON)(-(?<speed>100M|1G|2G5|5G|10G|25G|40G|100G|400G))?(-(?<id>[A-Z0-9-]+))?$
```

`X` notes: `STK` `ISC` `MLAG` `SPN` `OOB` `OTH`.

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

**`TMON`:** keep a list of `TMON*` ports; ops review cadence; reason in NetBox description.

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

Expected speed = SPEED token if present, else class default.

---

## 5. Zabbix resolution

```
1) Label empty → EMPTY; else parse class (and optional SPEED / ID)
2) Class X → skip port alerts
3) Else include per role LLD (§6)
4) Discovered + {UC,UD,UA,UP,MON,W} → link-down / flap / errors
5) Discovered + {UC,UD,UA,UP,MON} → expected speed = token or class default;
      ifHighSpeed ≠ expected ≥5m while oper-up → WARNING
6) Discovered + not TMON → change(ifHighSpeed) vs last stable oper-up ≥5m → WARNING;
      suppress in maintenance windows
7) TMON → items + optional link-down INFO
```

Turn on step 5 after labels for that site follow this grammar.

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

## 7. LAG / MLAG / MLT

Deferred — focus is **physical ports** first. Revisit later (see TODO).

| Rule (when revisited) | Decision so far |
|---|---|
| LAG/LACP members | Speed expect on members only |
| Aggregate ifIndex | Up/down / member-count; no absolute expect on sum |
| Peer-link | `X-MLAG` / `X` |
| VOSS MLT | Not monitored yet |

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

- [ ] VOSS: confirm port `name` → `ifAlias` (`…31.1.1.1.18`); else `ifDescr` + per-platform OID
- [ ] EXOS: which of `display-string` / `description-string` wins for `ifAlias` at 64
- [ ] Apply labels on pilots → enable absolute-expect
- [ ] Port template: link/flap/errors, absolute expect, change vs stable-up, maintenance suppress
- [ ] Later: revisit **LAG / MLAG / MLT** monitoring (focus is physical ports for now)
