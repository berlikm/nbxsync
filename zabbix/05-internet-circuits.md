# Internet circuits

Prepared later. Same bar as [01](01-extreme-switching.md): a circuit page is not a fabric `USW` ticket. Tag them so Forti WAN and Extreme `UW-` can share the class later. On the switch template, `UW` is **Average** like every other discovered link.

Depends on Extreme `UW-…` labels ([port-identity.md](port-identity.md)) and/or Forti WAN / SD-WAN health-checks ([03-fortinet.md](03-fortinet.md) — API, not SNMP). Do not page the same ISP cut as Extreme `UW`, Forti path, and Cato. A Swiss central proxy only proves reachability from Switzerland.

---

## What we alert

| Thing | Alert | Sev |
|---|---|---|
| One redundant `UW` / Forti WAN / SD-WAN member down | yes | **Average** — tagged as circuit, not fabric. Forti SD-WAN health-check is the authoritative underlay symptom; Extreme `UW` is the cause signal |
| Last usable site underlay path lost | yes | **High** on the path; **Disaster** on the site (later parent) |
| Flapping | yes | Warning |
| Errors | yes | Warning |
| All circuits at a site down | yes | **Disaster** — site-level, not on the switch or Forti template |
| Util vs commit bandwidth | later | graph; Average only after Circuit bandwidth exists |
| Speed ≠ label | **no** | handoff speed rarely equals commit |

Do **not** alert on: fabric `USW` uplinks (01), Cato overlay (04).

---

## Scope

| Object | In | Out |
|---|---|---|
| Extreme WAN | `ifAlias` matching `^UW(-\|$)` | Fabric uplinks |
| Forti WAN | Forti WAN iface **or** SD-WAN health-check for that circuit (HTTP) | Other Forti interfaces / policies |

---

## Ops

No absolute speed-expect on `UW`. Commit rate lives on the NetBox Circuit, not in the port label.

---

## Templates

| Template | Where |
|---|---|
| ISP WAN Ports by SNMP (thin, build) | Extreme `UW` — dependent items on stock interface items where possible |
| FortiGate by HTTP (SD-WAN / WAN LLD) | [03](03-fortinet.md) — not this SNMP template |

---

## Later

NetBox Providers + Circuits populated; multi-homing modelled vs residual risk; compliance (termination without `UW`, and the reverse).
