# Port identity — baseline

Shared on-box label grammar for Extreme switch ports (prefer SNMP `ifAlias`): class, optional speed, far-end ID.

Monitoring design that consumes this grammar: `docs/extreme-switching-zabbix.md`.

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
| **ID** | Far-end / free text after normalize — **machine-short abbreviation**, not a hostname |
| **Case** | Store UPPERCASE; match case-insensitive |
| **Length** | Max **20** characters (EXOS `display-string` hard limit; VOSS allows 64 — use LCD **20**) |
| **Forbidden** | `:` `.` space `"` `<>` `&` `?` ; first char alphanumeric |

One fact, one encoding: if the port runs at the class default, **omit SPEED**.

**Generator rule:** refuse labels longer than 20. Do not let EXOS truncate — a truncated label produces a permanent generated-vs-live compliance diff.

---

## 2. Classes

### 2.1 Include / monitor

Classes are chosen by **far-end identity** (NetBox role / what the cable hits).
Speed only decides whether a SPEED token is emitted after CLASS is known.

| CLASS | Rule | Default speed | Absolute expect | Alerts |
|---|---|---|---|---|
| `USW` | Switch or firewall | 10G | Yes | link / flap / errors + speed |
| `US` | Server / storage / Cohesity **data** NIC | 10G | Yes | same |
| `UP` | Toward AP | 1G | Yes | same |
| `MON` | BMC/iDRAC, **and anything else** (printer, camera, client, generic “Network Device”) | 1G | Yes | same |
| `UW` | Uplink WAN / ISP | — | Later (circuit bandwidth) | link / flap / errors |
| `TMON` | Temp watch | — | No | items; optional link-down **INFO** only |

**`US` vs `MON`:** ask “what is this?” — server/storage data NIC → `US` (a 1G
server is `US-1G-SRV12`, not `MON-SRV12`). Everything that is not a named class
is `MON`, **including 10G cameras / printers** (`MON-10G-…`). Speed is the
token, not the class.

ID role codes are always two letters **for fabric** so 40G still fits: `CORE→CO` `DIST→DI`
`ACCE→AC` `MGMT→MG`. Ports have no extra `P` (`_25` not `_P25`). Endpoints keep
the hostname (`SAN`, `SNAS`, `ESX`). `USW-40G-L01-MG01_120` is 20.

**`TMON`:** keep a list of `TMON*` for ops review; reason in NetBox description.

### 2.2 Exclude — class `X`

| Display | Meaning |
|---|---|
| `X` / `X-<note>` | Excluded — optional free-form note |

Zabbix takes **no port alerts** on `X*`. Reason may also live in NetBox description.

Only **`X`** removes a port from monitoring. Use it for SPAN / operator-mute / up-but-uninteresting. **Stack, ISC, and MLAG peer-links are switch↔switch fabric** — label them **`USW`** and alert like any other uplink (split-stack / dual-active is a real outage). Do not auto-`X` from a NetBox description of `ISC`. Unused ports stay **admin-down**.

### 2.3 Note — class `N` (monitoring-neutral)

| Display | Meaning |
|---|---|
| `N` / `N-<text>` | Free-form note on the box |

**`N` does not exclude.** It behaves like an unlabelled port plus human text:

| Role | `N` / unlabelled / unparseable legacy |
|---|---|
| Core / Dist / Mgmt | **monitored** (link-down, errors, …) |
| Access | not monitored (opt-in classes only) |

To silence a port: use **`X`** or **admin-down**. Unused ports should be admin-down as hygiene; reserve `X` for ports that stay up but must not alert.

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

| Scenario | Display | Len | Expect |
|---|---|---|---|
| Switch ↔ switch | `USW-SWD14` | 9 | 10G |
| Hypervisor / 10G NIC | `US-ESX01` | 8 | 10G |
| Storage 10G | `US-SAN01` | 8 | 10G |
| AP | `UP-AP3F07` | 9 | 1G |
| iDRAC / BMC | `MON-IDR03` | 9 | 1G |
| Printer / camera / anything else | `MON-PRN01` | 9 | 1G |
| WAN uplink | `UW-SC1` | 6 | link/flap/errors |
| Temp watch | `TMON-GUEST` | 10 | items + INFO link-down |
| Exclude | `X` / `X-SPAN` | | none |
| Note (neutral) | `N-SPARE` | 7 | same as unlabelled |

**Exceptions (token required — not the class default):**

| Scenario | Display | Expect |
|---|---|---|
| Switch ↔ switch at 1G | `USW-1G-SWA08` | 1G |
| 1G server NIC | `US-1G-SRV12` | 1G |
| AP at 2.5G | `UP-2G5-AP07` | 2.5G |
| 10G port that would otherwise be `MON` | `MON-10G-…` | 10G |

**Does not fit (25 > 20):** `USW-10G-CH-ZRH-ZH4-DIST01` — shorten the ID; full name stays in NetBox.

---

## 5. On-box field → SNMP `ifAlias`

### EXOS

**Prefer `display-string`** for the grammar label (what ops see in CLI port summaries).

Lab canary on **EXOS-VM 32.7.2.19** (IF-MIB):

| On-box fields set | `ifAlias` value |
|---|---|
| `display-string` only | display-string |
| `description-string` only | description-string |
| both | **description-string** (wins regardless of order) |

**Rule:** put `CLASS[-SPEED]-ID` in **`display-string`**. Leave **`description-string` empty**. Max **20** characters — EXOS truncates silently past that.

Port `ifName` is `1:N`; data ports use ifIndex `1000+N` (e.g. port 1 → `1001`).

### VOSS

Lab canary on **Virtual Fabric Engine 9.3.1.0**:

| CLI | SNMP |
|---|---|
| `interface gigabitEthernet 1/1` → `name USW-ID01` | **`ifAlias.192 = USW-ID01`** |
| | `rcPortName.192` empty — do not rely on it |

`name` allows 0–64 characters; fleet grammar still uses **20**. Prefer `ifAlias` for the shared grammar.

---

## 6. LAG / MLAG / MLT

**Bundle naming TBD** — confirm later how LAG / MLT *aggregates* fit this grammar (member ports vs bundle). **Peer-link / ISC / stack members are `USW`**, same as any switch↔switch cable. SPAN and other never-alert ports stay **`X`**.
