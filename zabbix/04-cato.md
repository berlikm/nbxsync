# Cato

Overlay. Prepared later. Same observability bar as [01-extreme-switching.md](01-extreme-switching.md): a collector failure is **not** a site down; a Cato site down is **not** an Extreme `USW` down.

NetBox: Cato site ID on the Site (when we have it).

---

## What we alert

| Thing | Alert | Sev |
|---|---|---|
| Site disconnected | yes | High |
| Link down while site still up | yes | Warning — redundancy lost |
| Socket health / version | yes | — |
| Loss / latency / throughput | later | graphs first |
| Collector / API failure | **no** as site outage | own signal, or we page false site-downs |

Do **not** alert on: switch/firewall underlay (01, 03), ISP circuit inventory (05) as if they were Cato.

---

## Scope

| Object | In | Out |
|---|---|---|
| Cato site | One host per site *(confirm)* | Whole account as one host *(unless we decide that)* |
| WAN link per site | LLD under the site | Extreme `UW-` port (05) |

---

## Ops

A collector or API-key failure is not a site down. Tag / name Cato alerts so they cannot be confused with underlay.

---

## Templates

| Template | Where |
|---|---|
| Cato Networks by HTTP (build) | Site / Cato object — HTTP agent + JS |

---

## Later

Exact GraphQL field map, poll interval vs rate limits, correlation with underlay without merging problem classes.
