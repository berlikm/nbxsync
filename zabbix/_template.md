# <Domain>

One sentence: what this is, and whether platforms in this domain share the same alerts.

Filled example (now): [01-extreme-switching.md](01-extreme-switching.md), [02-extreme-access-points.md](02-extreme-access-points.md).  
Prepared the same way: [03-fortinet.md](03-fortinet.md), [06-network-vms.md](06-network-vms.md).

Copy this file. Keep it one short page. OID walks and lab notes go in `templates/<name>/` or `notes/`.

Omit a section if the domain has nothing to say. Do not add staged rollout, open questions, or a requirements interview.

---

## Observability

Every domain uses the same bar. Only the signals change.

| Rule | Meaning |
|---|---|
| Page **symptoms** | Something a human must act on at 03:00. User impact, or the box is unreachable. |
| **Graph** causes | CPU, util, inventory, “busy but fine”. Warning that never pages trains people to ignore Warnings — don’t. |
| One incident | Trigger dependencies up the stack (item → SNMP → ICMP → **site**). Do not merge underlay with overlay (Cato) or with a different vendor (Forti vs Extreme). |
| Never silent | Unsupported items, zero discovered objects, proxy last-seen. Blindness is worse than noise. |
| Collect first | Link the template; leave noisy triggers off until a pilot is quiet. |
| One `icmpping` | Never stack Network Generic on a template that already pings. |
| Use the **full severity scale** | Zabbix: Info → Warning → Average → High → **Disaster**. Disaster is **site/service only**, never on a device template (Zabbix’s own rule). Warning is “next business day”, not the default dump. |

### Severity (every domain)

| Sev | Page? | Meaning | Examples |
|---|---|---|---|
| **Disaster** | 24/7 | Site or business service is down. Not a single box. | Site unreachable, both WAN circuits down, site→DC synthetic dead |
| **High** | 24/7 if it affects production | Device or **key path** gone | Host ICMP down, Core/Dist `USW` down, Access `USW`/`UP` down, temp **critical** |
| **Average** | Ticket / business hours | Partial failure; will become an outage | PSU/fan, optic DOM alarm, SNMP dead (forwarding may still work), memory |
| **Warning** | Next business day | Could escalate; do not SMS | Errors, flaps, half duplex, CPU, endpoint `US`/`MON` down, speed-expect |
| **Info** | No | Notice | Firmware / serial change |

Actions: Disaster+High → SMS/call. Average → ticket. Warning → queue/dashboard. Info → log. If everything is Warning, the scale is unused.

Site / role hostgroups already exist from nbxSync — reuse them for correlation. Do not invent a second inventory.

---

## What we alert

Each row is something ops asks. Alert, graph-only, or **no**. Neither → delete it.

| Thing | Alert | Sev |
|---|---|---|
| ICMP / reachability down | yes | High |
| Management path dead | yes | Average |
| Site / all paths down | yes | **Disaster** — not on the device template |
| | | |

Do **not** alert on:

-

---

## Scope

Which objects are in. How we include / exclude them.

| Role / class | In | Out |
|---|---|---|
| | | |

---

## Ops

On-box labels, vendor prerequisites, mute rules. 03:00, not LLD internals.

-

---

## Dependencies

What suppresses duplicates when one root cause hits many hosts.

```
… → no SNMP / no agent → ICMP down → site unreachable
```

---

## Watch the watcher

| Check | Why |
|---|---|
| Unsupported items | Collection stopped |
| Zero discovered objects | Filter / credential / template wrong |
| Proxy last-seen | Unknown ≠ down |

---

## Templates

Do not clone stock templates to specialise them.

| Template | Where |
|---|---|
| | Platform / role / tag |

Macros on the **template**, unless the nbxSync checklist already assigns them on the role:

```
{$…} =
```

---

## Later

Not now. One line each. Cutover does not wait. Leave hooks so FortiGate / VMs / Cato can attach without rewriting this domain.

-
