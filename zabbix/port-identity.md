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
| **Forbidden** | `:` `.` space `"` `<>` `&` `?` ; first char alphanumeric |

If the port runs at the class default, **omit SPEED**. If it does not (Pure 25G, AP 2.5G, Dist↔Access 1G), **the token is the contract** — Speed Expect will Warning the live `ifHighSpeed` against that number. Refuse labels over 20 — do not let EXOS truncate.

---

## Classes

| CLASS | Meaning | Default speed | Speed-expect | Alerts (live cutover) |
|---|---|---|---|---|
| `USW` | Switch / firewall | 10G | Warning when linked (`USW-1G-…` if not 10G) | **Average** link. Flap/errors Warning |
| `US` | Server / storage | 10G | Warning when linked (`US-25G-…` / `US-100G-…` if the array is not 10G) | **Average** link — **Core/Dist/Mgmt only** (not collected on Access) |
| `UP` | Access point | 1G | Warning when linked (`UP-2G5-…` if the AP is not 1G) | **Average** link on the switch (Access collects it). AP ICMP stays **High** |
| `MON` | Important to monitor, no better default class | 1G | Warning when linked | **Average** link — **Core/Dist/Mgmt only** |
| `UW` | WAN / ISP | — | **no** (circuit commit, not PHY) | Average link |
| `TMON` | Temp watch | — | no | items; optional INFO link-down |
| `X` / `X-<note>` | **Exclude** | — | — | none |
| `N` / `N-<text>` | Note — monitoring-neutral | — | — | same as unlabelled |

**`X` excludes. `N` does not.** On Core/Dist/Mgmt, **admin-up means it should be live** — including `N`, empty, or odd labels. Unused: **admin-down** (or `X`). On **Access**, grammar **display-string** classes `USW` `US` `UP` `MON` `UW` `TMON` are collected — a labelled port that is down tickets Average (including never-up). No desk, laptop, `N…`, `X…`, or unlabelled.

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

Same two tables as [reference/port-identity-foundation.md](reference/port-identity-foundation.md) §4.

**Normal (default speed — no token):**

| Scenario | Display | Len | Expect |
|---|---|---|---|
| Switch ↔ switch | `USW-C02_1` | 9 | 10G |
| Hypervisor / 10G NIC | `US-ESX40_NIC0` | 13 | 10G |
| Storage 10G | `US-SAN01_CT0_10` | 15 | 10G |
| AP | `UP-L02-AP07` | 11 | 1G |
| iDRAC / BMC | `MON-ESX40_ILO10_1` | 17 | 1G |
| WAN uplink | `UW-SC1` | 6 | link/flap/errors |
| Temp watch | `TMON-GUEST` | 10 | items + INFO link-down |
| Exclude | `X` / `X-SPAN` | | none |
| Note only | `N-SPARE` | 7 | same as unlabelled |

**Exceptions (token required — not the class default):**

| Scenario | Display | Len | Expect |
|---|---|---|---|
| Switch ↔ switch at 1G | `USW-1G-GFL-A01_23` | 17 | 1G |
| 1G server NIC | `US-1G-ESX40_NIC4` | 16 | 1G |
| AP at 2.5G | `UP-2G5-L02-AP07` | 15 | 2.5G |
| 10G port that would otherwise be `MON` | `MON-10G-…` | | 10G |

Too long (refuse): `USW-10G-CH-ZRH-ZH4-DIST01` (**25**). A 1G server NIC is `US-1G-…`, not `MON`. Stack is `USW`, not `X-STACK`.

---

## On-box field

| Platform | Field | Rule |
|---|---|---|
| **EXOS** | `display-string` | Grammar here. Leave **`description-string` empty** (it wins `ifAlias` if both are set) |
| **VOSS** | interface `name` | Lands in **`ifAlias`**. Do not use `rcPortName` |

---

## LAG / MLAG / MLT

Bundle naming TBD. Peer-link / ISC / stack members are **`USW`**. SPAN and other never-alert ports stay **`X`**.
