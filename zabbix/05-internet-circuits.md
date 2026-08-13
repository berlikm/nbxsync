# Internet circuits

ISP / WAN circuits. A circuit alert and a fabric uplink alert must never look the same.

Depends on Extreme `UW-…` labels ([port-identity.md](port-identity.md)) and/or Forti WAN.

---

## What we alert

| Thing | Alert | Sev |
|---|---|---|
| `UW` port / Forti WAN down | yes | High — tagged as circuit, not fabric |
| Flapping | yes | Warning |
| Errors | yes | Warning |
| All circuits at a site down | yes | High — needs dual-circuit modelled |
| Util vs commit bandwidth | later | needs NetBox circuit bandwidth |
| Speed ≠ label | **no** | handoff speed rarely equals commit |

Do **not** alert on: fabric `USW` uplinks (01), Cato overlay (04).

---

## Scope

| Object | In | Out |
|---|---|---|
| Extreme WAN | `ifAlias` matching `^UW(-\|$)` | Fabric uplinks |
| Forti WAN | Forti WAN interface for that circuit | Other Forti interfaces |

---

## Ops

No absolute speed-expect on `UW`. Commit rate lives on the NetBox Circuit, not in the port label.

---

## Templates

| Template | Where |
|---|---|
| ISP WAN Ports by SNMP (thin, build) | Circuit / `UW` — dependent items on stock interface items where possible |

---

## Later

NetBox Providers + Circuits populated; multi-homing modelled vs residual risk; compliance (termination without `UW`, and the reverse).
