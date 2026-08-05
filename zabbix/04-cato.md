# Cato — Zabbix monitoring

Status: draft    Owner:    Depends on: —

Overlay. Keep strictly separate from Extreme/Fortinet underlay — do not merge problem classes or dashboards will double-count a single outage.

## 1. Scope

In:  Cato sites, sockets, links as seen by the Cato API
Out: underlay switch/firewall health (01, 03), ISP circuit inventory (05)

## 2. Data path

| Source | Protocol | Credential | Interval |
|---|---|---|---|
| Cato API | HTTP agent (GraphQL) | API key | |

## 3. Signals

| # | Signal | Source | Why |
|---|---|---|---|
| | site connected / disconnected | `accountSnapshot` | site down |
| | link state per WAN interface | `accountSnapshot` | last-mile failure |
| | socket version / health | | |
| | throughput / loss / latency per link | `accountMetrics` | degradation |

## 4. Discovery

Rule:   LLD over sites, then links per site
Filter:

## 5. Triggers

| Sev | Condition | Settle | Notes |
|---|---|---|---|
| | site disconnected | | |
| | link down while site up | | redundancy loss |
| | **collector failure ≠ site outage** | | must not alert as an outage |

## 6. Template

Name:   `Cato Networks by HTTP` — build
Base:   HTTP agent + JS preprocessing

## 7. Open questions

- [ ] API version + exact field map
- [ ] Rate limits / poll interval
- [ ] What is one host — Cato account, or one host per site?
- [ ] Cato site ID stored on the NetBox Site (Track B)
- [ ] Correlation with Extreme underlay without double-counting

## 8. Done when

- [ ] Pilot sites visible
- [ ] Collector health distinguishable from site outage
- [ ] Cato alert and underlay alert for the same event are visibly related, not duplicated
