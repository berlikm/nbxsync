# Zabbix network monitoring

**In scope now:** [01 Extreme switching](01-extreme-switching.md), [02 access points](02-extreme-access-points.md).  
**Prepared:** [03 Fortinet](03-fortinet.md), [06 network VMs](06-network-vms.md).  
Copy [_template.md](_template.md) for the next domain. Same observability bar everywhere.

**Rules:** one short page per domain; one data path per doc; OID/lab notes in `templates/<name>/` or `notes/`.

## Doc set

| # | Doc | What | Status |
|---|---|---|---|
| — | [port-identity.md](port-identity.md) | Switch port label grammar | foundation |
| 00 | [00-monitoring-plan.md](00-monitoring-plan.md) | Order, cutover bar, principles | active |
| 01 | [01-extreme-switching.md](01-extreme-switching.md) | EXOS + VOSS | **now** |
| 02 | [02-extreme-access-points.md](02-extreme-access-points.md) | HiveOS / IQ Engine | **now** |
| 03 | [03-fortinet.md](03-fortinet.md) | FortiGate / Manager / Analyzer | prepared |
| 04 | [04-cato.md](04-cato.md) | Overlay | later |
| 05 | [05-internet-circuits.md](05-internet-circuits.md) | ISP / WAN | later |
| 06 | [06-network-vms.md](06-network-vms.md) | Infra VMs | prepared |

## Templates

| Folder | Template | Status |
|---|---|---|
| `templates/extreme_voss_snmp/` | Extreme VOSS by SNMP | imported; lab on virtual Fabric Engine |
| `templates/extreme_port_speed_expect_snmp/` | Extreme Port Speed Expect by SNMP | imported; triggers off until labels |
| `templates/extreme_routing_snmp/` | Extreme Routing by SNMP (OSPF) | imported; triggers off |
| `templates/extreme_iq_engine_snmp/` | Extreme IQ Engine by SNMP | imported; severities per [02](02-extreme-access-points.md) |

## Related

nbxSync GUI (locked): [`../docs/netbox-zabbix/configuration.md`](../docs/netbox-zabbix/configuration.md).
