# Port identity — baseline

Shared on-box label grammar for Extreme switch ports (prefer SNMP `ifAlias`): class, optional speed, far-end ID.

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
| **SPEED** | Only when **not** the class default (`2G5` not `2.5G`) — not used on `X` / `N` |
| **ID** | Far-end / free text after normalize |
| **Case** | Store UPPERCASE; match case-insensitive |
| **Length** | Max **64** characters |
| **Forbidden** | `:` space `"` `<>` `&` `?` ; first char alphanumeric |

One fact, one encoding: if the port runs at the class default, **omit SPEED**.

---

## 2. Classes

### 2.1 Include / monitor

Classes are chosen by **expected default speed** (and role), not by inventing device-type subclasses.

| CLASS | Rule | Default speed | Absolute expect | Alerts |
|---|---|---|---|---|
| `USW` | Switch ↔ switch — expect 10G | 10G | Yes | link / flap / errors + speed |
| `US` | Endpoint expect **10G** (hypervisor, storage, 10G server NIC, …) | 10G | Yes | same |
| `UP` | Toward AP — expect 1G | 1G | Yes | same |
| `MON` | Endpoint expect **1G** (BMC/iDRAC, client, 1G server NIC, …) | 1G | Yes | same |
| `UW` | Uplink WAN / ISP | — | Later | link / flap / errors |
| `TMON` | Temp watch | — | No | items; optional link-down **INFO** only |

**`US` vs `MON`:** ask “what speed should this be?” — 10G → `US`, 1G → `MON`. A 1G server NIC is `MON-SRV12`, not `US-1G-SRV12`.

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
Emit a token **only** for non-default speeds.

---

## 4. Examples

**Normal (default speed — no token):**

| Scenario | Display | Expect |
|---|---|---|
| Switch ↔ switch | `USW-SWD14` | 10G |
| Hypervisor / 10G NIC | `US-ESX01` | 10G |
| Storage 10G | `US-SAN01` | 10G |
| AP | `UP-AP3F07` | 1G |
| iDRAC / BMC | `MON-IDR03` | 1G |
| 1G server NIC | `MON-SRV12` | 1G |
| WAN uplink | `UW-SC1` | link/flap/errors |
| Temp watch | `TMON-GUEST` | items + INFO link-down |
| Exclude | `X` / `X-STACK` | none |
| Note only | `N-SPARE` | no action |

**Exceptions (token required — not the class default):**

| Scenario | Display | Expect |
|---|---|---|
| Switch ↔ switch at 1G | `USW-1G-SWA08` | 1G |
| AP at 2.5G | `UP-2G5-AP07` | 2.5G |
| 10G port that would otherwise be `MON` | `MON-10G-…` | 10G |

---

## 5. LAG / MLAG / MLT

**Naming TBD** — confirm later how bundle / peer-link / MLT labels fit this grammar (member ports vs aggregate, MLAG peer-link, VOSS MLT).
