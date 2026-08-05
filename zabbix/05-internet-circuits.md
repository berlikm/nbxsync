# Internet circuits — Zabbix monitoring

Status: draft    Owner:    Depends on: 01, 03, 04

ISP / WAN circuits. Distinct from fabric uplinks — a circuit alert and an uplink alert must never look the same.

## 1. Scope

In:  documented ISP terminations, labelled `UW-…` on Extreme, or the equivalent Forti WAN interface
Out: fabric uplinks (01), Cato overlay view (04), utilization % (later)

## 2. Data path

| Source | Protocol | Credential | Interval |
|---|---|---|---|
| Extreme WAN port | SNMP | ro-community | 1m |
| FortiGate WAN | SNMP / API | | |

## 3. Signals

| # | Signal | Source | Why |
|---|---|---|---|
| | ifOperStatus on `UW` port | IF-MIB | circuit down |
| | flap count | | unstable last mile |
| | errors | IF-MIB | dirty handoff |
| | (later) utilization vs commit bandwidth | NetBox circuit field | capacity |

**No absolute speed trigger on `UW`** — handoff speed rarely equals commit rate.

## 4. Discovery

Rule:   LLD on `ifAlias` matching `^UW(-|$)`
Filter: `{$NET.IF.IFALIAS.MATCHES}` = `^UW(-|$)` on a thin circuits template

## 5. Triggers

| Sev | Condition | Settle | Notes |
|---|---|---|---|
| High | `UW` port down | 2m | separate severity/tag from fabric uplinks |
| Warning | flapping | 15m | |
| High | **all** circuits at a site down | | redundancy-loss logic, needs dual-circuit modelled |

## 6. Template

Name:   `ISP WAN Ports by SNMP` — thin, build
Base:   dependent items on the stock interface items where possible

## 7. Open questions

- [ ] NetBox Providers + Circuits + terminations populated? (Track B)
- [ ] Multi-homing modelled, or documented as residual risk?
- [ ] Compliance: circuit termination exists but port not labelled `UW`, and the reverse
- [ ] Correlation with Cato without merging problem classes

## 8. Done when

- [ ] Pilot circuits: port ↔ ISP ↔ site visible in NetBox and Zabbix
- [ ] ISP alerts visually and by tag separate from fabric uplink alerts
