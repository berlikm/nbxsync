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

If the port runs at the class default, **omit SPEED**. Refuse labels over 20 — do not let EXOS truncate.

---

## Classes

| CLASS | Meaning | Default speed | Speed-expect | Alerts (live cutover) |
|---|---|---|---|---|
| `USW` | Switch ↔ switch | 10G | later (do not link yet) | **High** link (storage/server). Flap/errors Warning |
| `US` | Endpoint, expect 10G | 10G | later | **Average** link — **Core/Dist/Mgmt only** (not collected on Access) |
| `UP` | Toward AP | 1G | later | **Average** link on the switch (Access collects it). AP ICMP stays **High** |
| `MON` | Endpoint, expect 1G | 1G | later | Average link — **Core/Dist/Mgmt only** |
| `UW` | WAN / ISP | — | later (circuit bw) | Average link |
| `TMON` | Temp watch | — | no | items; optional INFO link-down |
| `X` / `X-<note>` | **Exclude** | — | — | none |
| `N` / `N-<text>` | Note — monitoring-neutral | — | — | same as unlabelled |

**`X` excludes. `N` does not.** On Core/Dist/Mgmt, `N` / empty / unparseable labels are monitored (all admin-up except `X`). On **Access**, only **`USW` (to Dist) and `UP` (to AP)** are collected — no desk, laptop, `US`, `MON`, `UW`, `TMON`, or unlabelled. A laptop unplug cannot alert: there are no items.

Live stock **link-down is Average** for every discovered port. That **is** the cutover contract. Class **High** for `USW`/`UP` is later — [01](01-extreme-switching.md).

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
| Switch ↔ switch | `USW-SWD14` | 9 | 10G |
| Hypervisor 10G | `US-ESX01` | 8 | 10G |
| AP | `UP-AP3F07` | 9 | 1G |
| iDRAC | `MON-IDR03` | 9 | 1G |
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
