# Zabbix network monitoring

Working notes and per-domain specs for the network monitoring build.

**Rule:** one short page per domain. Copy [_template.md](_template.md). Filled example: [01-extreme-switching.md](01-extreme-switching.md).
**Rule:** one doc = one data path. Different credential or protocol → different doc (Fortinet is one vendor file with three product blocks).
**Rule:** OID walks, LLD keys, and lab canaries go in `templates/<name>/` or `notes/` — not on the operator page.

## Doc set

| # | Doc | What | Status |
|---|---|---|---|
| — | [port-identity.md](port-identity.md) | Switch port label grammar | foundation |
| 00 | [00-monitoring-plan.md](00-monitoring-plan.md) | Order and cutover bar | active |
| 01 | [01-extreme-switching.md](01-extreme-switching.md) | EXOS + VOSS | **now** |
| 02 | [02-extreme-access-points.md](02-extreme-access-points.md) | HiveOS / IQ Engine | template v1 |
| 03 | [03-fortinet.md](03-fortinet.md) | FortiGate / Manager / Analyzer | later |
| 04 | [04-cato.md](04-cato.md) | Overlay | later |
| 05 | [05-internet-circuits.md](05-internet-circuits.md) | ISP / WAN | later |
| 06 | [06-network-vms.md](06-network-vms.md) | Infra VMs | later |

## Notes

| File | Contents |
|---|---|
| [notes/verified-facts.md](notes/verified-facts.md) | Platform limits we confirmed |
| [notes/exos-stock-template-review.md](notes/exos-stock-template-review.md) | Keep / cut against stock EXOS |
| [notes/open-questions.md](notes/open-questions.md) | Still unverified |

## Templates

| Folder | Template | Status |
|---|---|---|
| `templates/extreme_voss_snmp/` | Extreme VOSS by SNMP | imported; lab on virtual Fabric Engine |
| `templates/extreme_port_speed_expect_snmp/` | Extreme Port Speed Expect by SNMP | imported, not piloted |
| `templates/extreme_routing_snmp/` | Extreme Routing by SNMP (OSPF) | imported, not piloted |
| `templates/extreme_iq_engine_snmp/` | Extreme IQ Engine by SNMP | v1 YAML; pilot snmpwalk pending |

`mibs/` holds the EXOS 32.7.3.15 and VOSS 5520 9.3.1.0 MIB dumps.

## Related (do not duplicate here)

| Concern | Doc |
|---|---|
| nbxSync GUI setup | [`../docs/netbox-zabbix/configuration.md`](../docs/netbox-zabbix/configuration.md) |
