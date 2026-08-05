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

## 4. Examples

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
