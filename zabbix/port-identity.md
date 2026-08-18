# Port identity

On-box label grammar for Extreme switch ports (SNMP `ifAlias`).  
What we alert: [01-extreme-switching.md](01-extreme-switching.md).

---

## Grammar

```
CLASS
CLASS-ID
CLASS-SPEED-ID
```

| Piece | Rules |
|---|---|
| **CLASS** | `USW` `US` `UP` `MON` `UW` `TMON` `X` `N` |
| **SPEED** | Only when **not** the class default (`2G5` not `2.5G`). Not used on `X` / `N` |
| **ID** | Short abbreviation, not a hostname — full name lives in NetBox |
| **Case** | Store UPPERCASE; match case-insensitive |
| **Length** | Max **20** (EXOS `display-string` hard limit; VOSS allows 64 — use **20**) |
| **Forbidden** | `:` space `"` `<>` `&` `?` ; first char alphanumeric |

If the port runs at the class default, **omit SPEED**. If it does not (Pure 25G, AP 2.5G, Dist↔Access 1G), **the token is the contract** — Speed Expect will Warning the live `ifHighSpeed` against that number. Refuse labels over 20 — do not let EXOS truncate.

---

## Classes

| CLASS | Meaning | Default speed | Speed-expect | Alerts (live cutover) |
|---|---|---|---|---|
| `USW` | Switch / firewall / other network box | 10G | Warning when linked (`USW-1G-…` if not 10G) | **Average** link. Flap/errors Warning |
| `US` | Server / storage | 10G | Warning when linked (`US-25G-…` / `US-100G-…` if the array is not 10G) | **Average** link — **Core/Dist/Mgmt only** (not collected on Access) |
| `UP` | Access point | 1G | Warning when linked (`UP-2G5-…` if the AP is not 1G) | **Average** link on the switch (Access collects it). AP ICMP stays **High** |
| `MON` | Important to monitor, no better default class | 1G | Warning when linked | **Average** link — **Core/Dist/Mgmt only** |
| `UW` | WAN / ISP | — | **no** (circuit commit, not PHY) | Average link |
| `TMON` | Temp watch | — | no | items; optional INFO link-down |
| `X` / `X-<note>` | **Exclude** | — | — | none |
| `N` / `N-<text>` | Note — monitoring-neutral | — | — | same as unlabelled |

**`X` excludes. `N` does not.** On Core/Dist/Mgmt, **admin-up means it should be live** — including `N`, empty, or odd labels. Unused: **admin-down** (or `X`). On **Access**, only **`USW` (to Dist) and `UP` (to AP)** are collected — no desk, laptop, `US`, `MON`, `UW`, `TMON`, or unlabelled.

Every discovered **link-down is Average** (ticket). Same for Pure/`US` and an empty admin-up port you forgot to shut. Do not also split High by class.

---

## Speed tokens

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

Expected = token if present, else class default.

---

## Examples

| Scenario | Display | Len | Expect |
|---|---|---|---|
| Switch / firewall | `USW-SWD14` | 9 | 10G |
| Hypervisor / storage 10G | `US-ESX01` | 8 | 10G |
| Pure / array | `US-PURE01` | 10 | 10G |
| AP | `UP-AP3F07` | 9 | 1G |
| iDRAC (MON: important, no better class) | `MON-IDR03` | 9 | 1G |
| Pure 25G | `US-25G-P01` | 10 | 25G |
| AP at 2.5G | `UP-2G5-AP07` | 12 | 2.5G |
| Exclude | `X-STACK` | 7 | none |
| Note | `N-SPARE` | 7 | = unlabelled |
| Too long | `USW-10G-CH-ZRH-ZH4-DIST01` | **25** | refuse |

---

## On-box field

| Platform | Field | Rule |
|---|---|---|
| **EXOS** | `display-string` | Grammar here. Leave **`description-string` empty** (it wins `ifAlias` if both are set) |
| **VOSS** | interface `name` | Lands in **`ifAlias`**. Do not use `rcPortName` |

---

## LAG / MLAG / MLT

Naming TBD. Until then, structural links that must not alert use **`X`**.
