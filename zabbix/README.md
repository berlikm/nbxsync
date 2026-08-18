# Zabbix network monitoring

**In scope now:** [01 Extreme switching](01-extreme-switching.md), [02 access points](02-extreme-access-points.md).  
**Prepared:** [03 Fortinet](03-fortinet.md) (FortiGate **API** spec written; not live), [06 network VMs](06-network-vms.md).  
Copy [_template.md](_template.md) for the next domain. Same observability bar everywhere.

**Rules:** one short page per domain; one data path per doc; OID/lab notes in `templates/<name>/` or `notes/`. Extreme alerting + host **Health**: [notes/alerting-and-health.md](notes/alerting-and-health.md). FortiGate API + Health: [notes/fortigate-api-and-health.md](notes/fortigate-api-and-health.md).

## Doc set

| # | Doc | What | Status |
|---|---|---|---|
| — | [port-identity.md](port-identity.md) | Switch port label grammar | foundation |
| 00 | [00-monitoring-plan.md](00-monitoring-plan.md) | Order, cutover bar, principles | active |
| 01 | [01-extreme-switching.md](01-extreme-switching.md) | EXOS + VOSS | **now** |
| 02 | [02-extreme-access-points.md](02-extreme-access-points.md) | HiveOS / IQ Engine | **now** |
| 03 | [03-fortinet.md](03-fortinet.md) | FortiGate by HTTP (API) + FMG/FAZ | spec written; not live |
| 04 | [04-cato.md](04-cato.md) | Overlay | later |
| 05 | [05-internet-circuits.md](05-internet-circuits.md) | ISP / WAN | later |
| 06 | [06-network-vms.md](06-network-vms.md) | Infra VMs | prepared |

## Templates

| Folder | Template | Status |
|---|---|---|
| `templates/extreme_voss_snmp/` | Extreme VOSS by SNMP | imported; **Health** dashboard; SNMP-dead **Warning**; link-down **Average**; ISIS/card High gated; ICMP loss **off** — [01](01-extreme-switching.md) |
| `templates/extreme_port_speed_expect_snmp/` | Extreme Port Speed Expect by SNMP | imported; YAML triggers **on** — do not link; `{$IF.UTIL.MAX:"USW"}=101` |
| `templates/extreme_routing_snmp/` | Extreme Routing by SNMP (OSPF) | imported; not linked (YAML High if linked) |
| `templates/extreme_iq_engine_snmp/` | Extreme IQ Engine by SNMP | imported; **Health** dashboard; severities per [02](02-extreme-access-points.md) |

## Related

nbxSync GUI (locked): [`../docs/netbox-zabbix/configuration.md`](../docs/netbox-zabbix/configuration.md).
