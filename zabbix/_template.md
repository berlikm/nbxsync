# <Domain>

One sentence: what this is, and whether platforms in this domain share the same alerts.

NetBox clicks (if any): [`../docs/netbox-zabbix/configuration.md`](../docs/netbox-zabbix/configuration.md) §…. Extra grammar (if any): link it.

Filled example: [01-extreme-switching.md](01-extreme-switching.md).

Copy this file. Keep it one short page. OID walks, LLD keys, lab canaries, and “done when” lists go in `templates/<name>/` or `notes/` — not here.

Omit **Scope**, **Ops**, or **Later** if the domain has nothing to say. Do not add staged rollout, open questions, or a requirements interview.

---

## What we alert

Each row is something ops asks. Alert, graph-only, or **no**. Neither alert nor graph → delete it.

| Thing | Alert | Sev |
|---|---|---|
| ICMP down | yes | High |
| SNMP / API dead | yes | Warning |
| | | |

Do **not** alert on:

-

---

## Scope

Which objects are in (ports, radios, tunnels, sites). How we include / exclude them.

| Role / class | In | Out |
|---|---|---|
| | | |

---

## Ops

On-box labels, vendor prerequisites, mute rules. What someone needs at 03:00 — not how LLD is implemented.

-

---

## Templates

Do not clone stock templates to specialise them. Do **not** stack Network Generic on a template that already has `icmpping`.

| Template | Where |
|---|---|
| | Platform / role / tag |

Macros that matter (on the **template**, unless the checklist says the role):

```
{$…} =
```

---

## Later

Not now. One line each. Cutover does not wait on these.

-
