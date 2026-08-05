# Fortinet — Zabbix monitoring

Status: draft    Owner:    Depends on: —

Three separate data paths, three sections. Do not merge.

---

# §A FortiGate

## 1. Scope
In:
Out: WAN circuit monitoring (05), Cato overlay (04)

## 2. Data path
| Source | Protocol | Credential | Interval |
|---|---|---|---|
| FortiGate | SNMP / REST API | | |

## 3. Signals
| # | Signal | Source | Why |
|---|---|---|---|

## 4. Discovery
## 5. Triggers
## 6. Template
Name: `Fortinet FortiGate by SNMP` (stock exists — review like we did for EXOS)

## 7. Open questions
- [ ] Inventory: which sites are Forti-terminated vs Extreme vs Cato-direct
- [ ] SNMP or API for path/SD-WAN health
- [ ] nbxsync assignment by role/platform — avoid manufacturer-wide accidents
- [ ] Align severity language with Extreme

## 8. Done when

---

# §B FortiManager

## 1. Scope
## 2. Data path
## 3. Signals
| # | Signal | Source | Why |
|---|---|---|---|
| | device sync status | | config drift / offline managed devices |
| | appliance health | | |

## 5. Triggers
## 6. Template
## 7. Open questions
- [ ] Is device-sync status an alert or a report?
- [ ] Overlap with cfgit config drift detection?

---

# §C FortiAnalyzer

## 1. Scope
## 2. Data path
## 3. Signals
| # | Signal | Source | Why |
|---|---|---|---|
| | disk / log storage | | log loss risk |
| | log ingestion rate | | silent device stopped logging |
| | appliance health | | |

## 5. Triggers
## 6. Template
## 7. Open questions
- [ ] Is "device stopped sending logs" a Zabbix alert or a FAZ-native one?

---

## Requirements interview (per section)

1. What breaks, and how do we find out today?
2. Data path, credential owner?
3. What is one host?
4. Alert or graph?
5. Paged, actionable at 03:00?
6. False-positive story?
