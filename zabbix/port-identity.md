# Port identity

Status: foundation · Owner: · Depends on: —

Shared on-box label grammar for Extreme switch ports (SNMP `ifAlias`).  
Consumed by [01-extreme-switching.md](01-extreme-switching.md).

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
| **ID** | Machine-short abbreviation, not a hostname — full name lives in NetBox |
| **Case** | Store UPPERCASE; match case-insensitive |
| **Length** | Max **20** (EXOS `display-string` hard limit; VOSS allows 64 — use LCD **20**) |
| **Forbidden** | `:` space `"` `<>` `&` `?` ; first char alphanumeric |

One fact, one encoding: if the port runs at the class default, **omit SPEED**.

**Generator must refuse >20** — do not let EXOS truncate (permanent compliance diff).

---

## 2. Classes

| CLASS | Rule | Default speed | Absolute expect | Alerts |
|---|---|---|---|---|
| `USW` | Switch ↔ switch | 10G | Yes | link / flap / errors + speed |
| `US` | Endpoint expect **10G** | 10G | Yes | same |
| `UP` | Toward AP | 1G | Yes | same |
| `MON` | Endpoint expect **1G** | 1G | Yes | same |
| `UW` | WAN / ISP | — | Later (circuit bw) | link / flap / errors |
| `TMON` | Temp watch | — | No | items; optional INFO link-down |
| `X` / `X-<note>` | **Exclude** | — | — | none |
| `N` / `N-<text>` | Note — **monitoring-neutral** | — | — | same as unlabelled |

**`X` excludes. `N` does not.** On core/dist, `N` / empty / unparseable legacy labels are monitored. On access, only include-classes are. Structural ports that must never alert need **`X`**, not a note.

Unused ports → **admin-down** (not discovered). Reserve `X` for ports that stay up.

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

Expected = token if present, else class default. Emit a token **only** for non-default speeds.

---

## 4. Examples

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

## 5. On-box → `ifAlias`

| Platform | Field | Rule |
|---|---|---|
| **EXOS** | `display-string` | Grammar here; leave **`description-string` empty** (`description` wins `ifAlias` if both set) |
| **VOSS** | interface `name` | Lands in **`ifAlias`** (lab-proven). Do not use `rcPortName` |

Evidence: [notes/verified-facts.md](notes/verified-facts.md).

---

## 6. Zabbix LLD (summary)

Stock `net.if.discovery` unmodified — scope via host macros from nbxsync:

| Role | `{$NET.IF.IFALIAS.MATCHES}` | `{$NET.IF.IFALIAS.NOT_MATCHES}` | No label / `N` |
|---|---|---|---|
| Core / Dist / Mgmt | `.*` | `^X(-\|$)` | monitored |
| Access (Hybrid until stage 5) | `^(USW\|US\|UP\|MON\|UW\|TMON)(-\|$)` | `CHANGE_IF_NEEDED` | not monitored |
| All | `{$NET.IF.IFTYPE.MATCHES}` = `^(6\|161)$` | | physical + LAG |

Speed-expect thin template uses **own** macros (`{$PORTID.LLD.*}`), not `{$NET.IF.*}`.  
LLD: 15m during rollout, keep-lost **0**.  
Do **not** use `{$IFCONTROL:"{#IFNAME}"}` — `X` is the only mute.

Full triggers / capacity / rollout: [01-extreme-switching.md](01-extreme-switching.md).

---

## 7. LAG / MLAG / MLT

**Naming TBD.** Until then, structural links that must not alert use **`X`**.
