# Fortinet

Three products, three short blocks. Do not merge them — different questions even when the credential is the same SNMP profile.

NetBox: CG **SNMP Monitoring** on role Firewall; Template Rule FortiOS → **FortiGate by SNMP**. Checklist: [`docs/netbox-zabbix/configuration.md`](../docs/netbox-zabbix/configuration.md) §5b / §6.1 / §7.

WAN circuits that happen to terminate on a FortiGate live in [05-internet-circuits.md](05-internet-circuits.md). Cato overlay: [04-cato.md](04-cato.md).

---

## FortiGate

### What we alert

| Thing | Alert | Sev |
|---|---|---|
| ICMP down | yes | High |
| SNMP dead | yes | Warning |
| Device health (CPU / mem / temp) | yes | — fill from stock + baseline |
| HA peer lost | yes | High |
| VPN / SD-WAN path | later | — |

Do **not** alert on: underlay switch ports (01), Cato overlay (04), ISP commit vs handoff speed (05).

### Scope

One Zabbix host per FortiGate. Do not assign the FortiGate template by manufacturer onto FortiManager / FortiAnalyzer.

### Templates

| Template | Where |
|---|---|
| FortiGate by SNMP (stock — review like EXOS) | Platform FortiOS + role Firewall |

Do **not** stack Network Generic.

### Later

SD-WAN / path health (SNMP vs API still open). Not a switch-cutover blocker.

---

## FortiManager

### What we alert

| Thing | Alert | Sev |
|---|---|---|
| Appliance down | yes | High |
| Managed device sync / offline | ? | Alert vs report — decide before enabling |
| Config drift vs cfgit | **no** | cfgit’s job unless we explicitly take it |

### Templates

| Template | Where |
|---|---|
| *(stock or thin — pick one)* | Role / platform for FortiManager only |

### Later

Whether “device stopped syncing” is a page or a daily report.

---

## FortiAnalyzer

### What we alert

| Thing | Alert | Sev |
|---|---|---|
| Appliance down | yes | High |
| Disk / log storage | yes | Warning — log loss risk |
| Device stopped sending logs | ? | Zabbix vs FAZ-native — pick one |

### Templates

| Template | Where |
|---|---|
| *(stock or thin — pick one)* | Role / platform for FortiAnalyzer only |

### Later

Log-ingestion rate as a silent-failure detector, if FAZ does not already page it.
