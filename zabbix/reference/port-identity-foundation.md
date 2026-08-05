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
| **Forbidden** | `:` space `"` `<>` `&` `?` ; first char alphanumeric |

One fact, one encoding: if the port runs at the class default, **omit SPEED**.

**Generator rule:** refuse labels longer than 20. Do not let EXOS truncate — a truncated label produces a permanent generated-vs-live compliance diff.

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
| `UW` | Uplink WAN / ISP | — | Later (circuit bandwidth) | link / flap / errors |
| `TMON` | Temp watch | — | No | items; optional link-down **INFO** only |

**`US` vs `MON`:** ask “what speed should this be?” — 10G → `US`, 1G → `MON`. A 1G server NIC is `MON-SRV12`, not `US-1G-SRV12`.

**`TMON`:** keep a list of `TMON*` for ops review; reason in NetBox description.

### 2.2 Exclude — class `X`

| Display | Meaning |
|---|---|
| `X` / `X-<note>` | Excluded — optional free-form note |

Zabbix takes **no port alerts** on `X*`. Reason may also live in NetBox description.

Only **`X`** removes a port from monitoring. Structural ports that must never alert (stack, ISC, MLAG peer-link, SPAN) need an explicit **`X`**, not a note.

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
| 1G server NIC | `MON-SRV12` | 9 | 1G |
| WAN uplink | `UW-SC1` | 6 | link/flap/errors |
| Temp watch | `TMON-GUEST` | 10 | items + INFO link-down |
| Exclude | `X` / `X-STACK` | | none |
| Note (neutral) | `N-SPARE` | 7 | same as unlabelled |

**Exceptions (token required — not the class default):**

| Scenario | Display | Expect |
|---|---|---|
| Switch ↔ switch at 1G | `USW-1G-SWA08` | 1G |
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

**Naming TBD** — confirm later how bundle / peer-link / MLT labels fit this grammar (member ports vs aggregate, MLAG peer-link, VOSS MLT). Until then, structural links that must not alert use **`X`**.
