# Extreme access points — Zabbix monitoring

Status: draft    Owner:    Depends on: 01-extreme-switching.md

## 1. Scope

In:  HiveOS / IQ Engine APs
Out: switch port toward the AP (that is `UP-…` in 01), wireless client experience

## 2. Data path

| Source | Protocol | Credential | Interval |
|---|---|---|---|
| AP | SNMP? | | |
| ExtremeCloud IQ | API? | | |

**Decision needed:** SNMP direct to AP, XIQ Pilot API, or hybrid.

## 3. Signals

| # | Signal | Source | Why |
|---|---|---|---|

## 4. Discovery

Rule:
Filter:

## 5. Triggers

| Sev | Condition | Settle | Notes |
|---|---|---|---|

## 6. Template

Name:   `HiveOS Access Point` — **build**, no stock template
Base:

## 7. Open questions

- [ ] Data path: SNMP vs XIQ API vs both
- [ ] Is AP-down already covered by the switch `UP-…` port link-down? Avoid double alerting
- [ ] Radio / client-count signals in v1 or later?
- [ ] No Network Generic role floor on Access Point role — confirm

## 8. Done when

- [ ] Sample APs monitored
- [ ] AP down alerts once, not twice (AP template + switch port)

---

## Requirements interview

1. What breaks, and how do we find out today?
2. What is the data path, does it exist, who owns the credential?
3. What is one host — the AP, or the XIQ tenant?
4. For each signal: alert or graph?
5. Who gets paged, actionable at 03:00?
6. False-positive story — AP reboots, firmware pushes, PoE cycles.
