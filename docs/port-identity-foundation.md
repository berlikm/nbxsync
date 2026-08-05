# Port identity — baseline

**SoT on box:** Extreme port label → SNMP (prefer `ifAlias`)  
**SoT in NetBox:** inventory (cables, roles, `interface.speed`) → authoritative generator; description = prose  
**Scope:** Zabbix port LLD, speed expectation, excludes

---

## 1. Locked decisions

1. **Grammar:** `CLASS[-SPEED]-ID` — hyphen only (no `:`).  
2. **Budget:** **64** characters (VOSS `name` `WORD<0-64>` + EXOS `ifAlias` default). No fictional ≤15. No EXOS `ifalias size extended`.  
3. **Always emit SPEED** on generated labels; real far-end IDs; controlled `X-STK` / `X-ISC` / `X-MLAG` / `X-SPN` / `X-OOB` / `X-OTH`.  
4. **Case:** generator pushes **UPPERCASE**; parser case-insensitive.  
5. **No `IDR` class** — iDRAC = `MON`.  
6. **Class defaults** (token omitted — hand/legacy only): `UC`/`UD`/`UA` → 10G; `UP`/`MON` → 1G.  
7. **Push:** EXOS → field that drives `ifAlias` (expect `description-string`); VOSS → `name` / `name port <list>`.  
8. **Generator authoritative** on managed ports; `display_protect` skips hand-sets.  
9. **Parse:** `EMPTY` | `PARSED`. Legacy labels overwritten — no quarantine state.  
10. **Baseline first:** push → clean generated-vs-live diff → then absolute-expect.  
11. **Access LLD opt-in** — no safety net for missing/typo labels (compliance catches them).  
12. **Hybrid:** admin-down spares; `X` only if up-but-uninteresting; monitored clients get `MON-<ID>` (not empty). No X-fill-all.  
13. **LAGs:** speed expect on **members** only.  
14. **No NetBox tags** for monitor/speed intent.

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
| **Forbidden** | `:` space `"` `<>` `&` `?` ; first char alphanumeric (EXOS safe union) |

**Length (confirmed):**

| Field | Size |
|---|---|
| VOSS port `name` | 0–64 (`WORD<0-64>`, CLI) |
| VOSS MLT `name` | 0–64 |
| EXOS `display-string` | 20 |
| EXOS `description-string` | 255 |
| EXOS SNMP `ifAlias` | 64 default / 255 extended |

**Parser** (after uppercase normalize):

```
# Exclude — note is never a speed token
^X(-(?<xnote>STK|ISC|MLAG|SPN|OOB|OTH|[A-Z0-9]{1,12}))?$

# Include
^(?<class>UC|UD|UA|UP|MON|W|TMON)(-(?<speed>100M|1G|2G5|5G|10G|25G|40G|100G|400G))?(-(?<id>[A-Z0-9-]+))?$
```

---

## 3. Classes

| CLASS | Meaning | Default speed | Absolute expect | Phase 2 |
|---|---|---|---|---|
| `UC` | Toward core | 10G | Yes | link / flap / errors + speed |
| `UD` | Toward dist | 10G | Yes | same |
| `UA` | Toward access | 10G | Yes | same |
| `UP` | Toward AP | 1G | Yes | same |
| `MON` | Endpoint (server, ESX, storage, iDRAC, …) | 1G | Yes | same |
| `W` | WAN / ISP | — | No (bandwidth later) | link / flap / errors |
| `TMON` | Temp watch | — | No | items; optional link-down **INFO** only |
| `X` / `X-<NOTE>` | Excluded | — | No | skip port alerts |

**`TMON`:** compliance lists all `TMON*`; review cadence in ops; why/until lives in NetBox description.

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

Generator always emits SPEED from NetBox `interface.speed` (or class default if unset).

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

**Hygiene:** unused ports → admin-down.

**Hybrid (no X-fill-all):**

```
1) Spares / unused            → admin-down
2) Admin-up but uninteresting → X / X-<NOTE>
3) Monitor                    → MON-<ID> (never empty) / UP / W / …
```

---

## 7. LAG / MLAG

| Rule | Decision |
|---|---|
| Speed expect | **Members only** |
| Aggregate ifIndex | Up/down / member-count — no absolute expect on sum |
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
| Hybrid up-but-uninteresting | `X` / `X-STK` / … |
| Hybrid/client monitor | `MON-<ID>` |
| Cable + speed | `UD-10G-…` / `UA-1G-…` |
| iDRAC / ESX / storage | `MON-…` |
| WAN | `W-…` |

VOSS: prefer `name port <portlist>` when applying one label to many ports.

**Ingest:** do not let ifAlias collection write into generator-owned NetBox fields (loop hazard).

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

- [ ] **VOSS SNMP:** does `name` populate `ifAlias` (`1.3.6.1.2.1.31.1.1.1.18`)? If not, check `ifDescr` (`…2.2.1.2`) and use per-platform OID in Zabbix.
- [ ] **EXOS SNMP:** set both `display-string` and `description-string`; record which wins for `ifAlias` and truncation at 64.
- [ ] Confirm ingest does not clobber generator inputs.
- [ ] Implement generator + `display_protect` + compliance diff.
- [ ] Push labels → clean baseline → enable absolute-expect.
- [ ] Port template: link/flap/errors, absolute expect, change vs stable-up, maintenance suppress.
