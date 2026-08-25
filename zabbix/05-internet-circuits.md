# Internet circuits

Prepared later. Same bar as [01](01-extreme-switching.md): a circuit page is not a fabric `USW` ticket. Tag them so Forti WAN and Extreme `UW-` can share the class later. On the switch template, `UW` is **Average** like every other discovered link.

Depends on Extreme `UW-…` labels ([port-identity.md](port-identity.md)) and/or Forti WAN / SD-WAN health-checks ([03-fortinet.md](03-fortinet.md) — API, not SNMP). Do not page the same ISP cut as Extreme `UW`, Forti path, and Cato. A Swiss central proxy only proves reachability from Switzerland.

---

## FortiGate HTTP is the probe we have

SD-WAN health-checks (loss / latency / jitter / probe status) are the only underlay probe this estate collects today. They run for **internet failover** on at least two VDOMs: **`root` (production)** and **`Untrust` (guest)**. Do not build a second ICMP/SLA poller for the same circuit.

Until this page has its own circuit host, operators use the FortiGate host boards from [03](03-fortinet.md):

| Board | What to use for ISP work |
|---|---|
| **Path → Overview** | Member link vs health-check colour, VDOM-prefixed (`root/wan1`, `Untrust/Google/wan1`) |
| **Path → Loss** | Packet loss honeycomb (0 green / 5 yellow / 20 red = stock Warning). Production vs guest are different cells |
| **Path → Probe** | Navigator grouped by **vdom** — latency / jitter / loss / status / byte rate |
| **Network interfaces → Port** | Physical WAN bits through the per-interface navigator — not the stock 1-column Statistics slide |

A later circuit template should **reuse these items** (dependent items / a thin overlay), not poll FortiOS twice. Tag so Extreme `UW` and Forti path share a class without double-paging.

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
| Forti WAN | Forti WAN iface **or** SD-WAN health-check for that circuit (HTTP). Split `root` vs `Untrust` — they are different internet paths | Other Forti interfaces / policies |

---

## Ops

No absolute speed-expect on `UW`. Commit rate lives on the NetBox Circuit, not in the port label.

---

## Templates

| Template | Where |
|---|---|
| ISP WAN Ports by SNMP (thin, build) | Extreme `UW` — dependent items on stock interface items where possible |
| FortiGate by HTTP (SD-WAN / WAN LLD) | [03](03-fortinet.md) **Path** Loss/Probe — not this SNMP template |

---

## Later

NetBox Providers + Circuits populated; multi-homing modelled vs residual risk; compliance (termination without `UW`, and the reverse).
