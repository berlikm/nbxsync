# Zabbix network monitoring

**In scope now:** [01 Extreme switching](01-extreme-switching.md), [02 access points](02-extreme-access-points.md).  
**Prepared:** [03 Fortinet](03-fortinet.md) (FortiGate **API** spec written; FMG/FAZ SNMP YAML built, not live), [06 network VMs](06-network-vms.md).  
**Live collector:** [04 Cato](04-cato.md) account monitoring and all 21 NetBox-backed Socket ICMP hosts.
Copy [_template.md](_template.md) for the next domain. Same observability bar everywhere.

**Rules:** one short page per domain; one data path per doc; OID/lab notes in `templates/<name>/` or `notes/`. Extreme alerting + host **Health**: [notes/alerting-and-health.md](notes/alerting-and-health.md). FortiGate API + Health: [notes/fortigate-api-and-health.md](notes/fortigate-api-and-health.md). MSSQL named instances (Agent 2 companion): [notes/mssql-agent2-instances.md](notes/mssql-agent2-instances.md).

## Doc set

| # | Doc | What | Status |
|---|---|---|---|
| — | [port-identity.md](port-identity.md) | Switch port label grammar | foundation |
| 00 | [00-monitoring-plan.md](00-monitoring-plan.md) | Order, cutover bar, principles | active |
| 01 | [01-extreme-switching.md](01-extreme-switching.md) | EXOS + VOSS | **now** |
| 02 | [02-extreme-access-points.md](02-extreme-access-points.md) | HiveOS / IQ Engine | **now** |
| 03 | [03-fortinet.md](03-fortinet.md) | FortiGate by HTTP (API) + FMG/FAZ SNMP | FortiGate spec written, not live; FMG/FAZ YAML built, not live |
| 04 | [04-cato.md](04-cato.md) | Cato account HTTP collector + Socket ICMP | live; 21/21 Socket hosts |
| 05 | [05-internet-circuits.md](05-internet-circuits.md) | ISP / WAN | later |
| 06 | [06-network-vms.md](06-network-vms.md) | Infra VMs | prepared |

## Templates

| Folder | Template | Status |
|---|---|---|
| `templates/extreme_voss_snmp/` | Extreme VOSS by SNMP | imported; **Health** dashboard; SNMP-dead **Warning**; link-down **Average**; ISIS/card High gated; ICMP loss **off** — [01](01-extreme-switching.md) |
| `templates/extreme_port_speed_expect_snmp/` | Extreme Port Speed Expect by SNMP | nested on VOSS + EXOS Observability; mismatch Warning on; empty `ifAlias` silent; discards **off**; `{$IF.UTIL.MAX:"USW"}=101` |
| `templates/extreme_routing_snmp/` | Extreme Routing by SNMP (OSPF) | imported; not linked (YAML High if linked) |
| `templates/extreme_iq_engine_snmp/` | Extreme IQ Engine by SNMP | imported; **Health** dashboard; severities per [02](02-extreme-access-points.md) |
| `templates/fortinet_fortigate_observability/` | FortiGate Observability | companion; nests Cloud **FortiGate by HTTP** 7.0-2 + ICMP Ping; **Health** + **Network interfaces** + **Path** (Loss/Probe) — [03](03-fortinet.md) |
| `templates/fortinet_fmg_faz_snmp/` | Fortinet FMG-FAZ by SNMP | **built**; Health + Network interfaces; own `icmpping`; no official stock template (ZBXNEXT-10433) — [03](03-fortinet.md) |
| `templates/fortinet_fortimanager_observability/` | FortiManager Observability | companion; nests FMG-FAZ SNMP; **Devices** board; FGFM connect-down; config drift collect-only — [03](03-fortinet.md) |
| `templates/fortinet_fortianalyzer_observability/` | FortiAnalyzer Observability | companion; nests FMG-FAZ SNMP; **Logs** board; log lag Average; log-disk High at 95% — [03](03-fortinet.md) |
| `templates/mssql_observability/` | MSSQL Observability | companion YAML + named-instance LLD/database-inventory fixtures; **soft** zerotouch assign; import before canary — [notes/mssql-agent2-instances.md](notes/mssql-agent2-instances.md) |
| `templates/cato_http/` | Cato Networks by HTTP | imported; account collector with **Health** (Census/API) + **Path** (Last mile/Probe) + **Network** (Tunnels/HA/Port); 21/21 Socket ICMP hosts live — [04](04-cato.md) |

## Related

nbxSync GUI (locked): [`../docs/netbox-zabbix/configuration.md`](../docs/netbox-zabbix/configuration.md).
