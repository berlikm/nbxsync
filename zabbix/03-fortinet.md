# Fortinet

Prepared — same observability bar as [01-extreme-switching.md](01-extreme-switching.md). Do not block Extreme/AP cutover. Three products, three blocks; do not merge.

WAN on a FortiGate: [05-internet-circuits.md](05-internet-circuits.md). Overlay: [04-cato.md](04-cato.md). Do not page the same outage as an Extreme `USW` and as a Forti WAN and as Cato.

---

## Observability

| Rule | Here |
|---|---|
| Page symptoms | Forti unreachable, HA peer lost, VPN/SD-WAN **path down** (when we enable it) |
| Graph causes | CPU, sessions, tunnel bytes |
| One incident | Forti down depends on ICMP → site. Do **not** also High-page every `UW` / Cato site for the same WAN cut until we have a rule |
| Never silent | Unsupported items; HA cluster with one member missing from Zabbix |
| Collect first | Stock FortiGate template like EXOS: link, baseline, then enable |

---

## FortiGate

### What we alert

| Thing | Alert | Sev |
|---|---|---|
| ICMP down | yes | High |
| SNMP dead | yes | Warning |
| Device health (CPU / mem / temp) | yes | after baseline |
| HA peer lost | yes | High |
| VPN / SD-WAN path | later | symptom — this is the Forti equivalent of OSPF/fabric |

### Scope

One host per FortiGate. Never assign the FortiGate template by manufacturer onto Manager / Analyzer.

### Dependencies

```
path / HA  →  no SNMP  →  ICMP  →  site
```

### Watch the watcher

Unsupported items; zero VPN tunnels if we expected some; proxy last-seen.

### Templates

| Template | Where |
|---|---|
| FortiGate by SNMP (stock — review like EXOS) | Platform FortiOS + role Firewall |

Do **not** stack Network Generic.

### Later

SD-WAN / path (SNMP vs API). Site synthetic still lives in 01, not here.

---

## FortiManager

### What we alert

| Thing | Alert | Sev |
|---|---|---|
| Appliance down | yes | High |
| Managed device sync / offline | ? | page vs daily report — decide before enabling |
| Config drift vs cfgit | **no** | cfgit’s job |

### Templates

Role / platform for FortiManager only.

---

## FortiAnalyzer

### What we alert

| Thing | Alert | Sev |
|---|---|---|
| Appliance down | yes | High |
| Disk / log storage | yes | Warning — log loss |
| Device stopped sending logs | ? | Zabbix vs FAZ-native — pick **one** (never silent) |

### Templates

Role / platform for FortiAnalyzer only.
