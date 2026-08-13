# Zabbix network monitoring

Working notes and per-domain specs for the network monitoring build.

**Rule:** one doc = one data path. Different credential or protocol → different doc.
**Rule:** one short page per doc. New domains start from `_template.md`.

## Doc set

| # | Doc | Sections | Depends on | Status |
|---|---|---|---|---|
| — | [port-identity.md](port-identity.md) | label grammar | — | foundation |
| 00 | [00-monitoring-plan.md](00-monitoring-plan.md) | index, order | — | active |
| 01 | [01-extreme-switching.md](01-extreme-switching.md) | EXOS + VOSS — what we alert | port-identity | **now** |
| 02 | [02-extreme-access-points.md](02-extreme-access-points.md) | HiveOS / IQ Engine | 01 | template v1 + wiring |
| 03 | [03-fortinet.md](03-fortinet.md) | FortiGate, FortiManager, FortiAnalyzer | — | later |
| 04 | [04-cato.md](04-cato.md) | overlay | — | later |
| 05 | [05-internet-circuits.md](05-internet-circuits.md) | ISP / WAN | 01, 03, 04 | later |
| 06 | [06-network-vms.md](06-network-vms.md) | infra VMs | — | later |

Skeleton to copy: [_template.md](_template.md)

## Notes

| File | Contents |
|---|---|
| [notes/verified-facts.md](notes/verified-facts.md) | Platform limits and behaviours we confirmed, with source |
| [notes/exos-stock-template-review.md](notes/exos-stock-template-review.md) | Keep / cut / modify against the stock Zabbix EXOS template |
| [notes/open-questions.md](notes/open-questions.md) | Everything still unverified |

## Templates

Pulled from `berlikm/nbxsync` branch `cursor/extreme-voss-snmp-template-e7f8` (PR #28).

| Folder | Template | Status |
|---|---|---|
| `templates/extreme_voss_snmp/` | Extreme VOSS by SNMP | imported on Zabbix 7.0.29, lab-verified on **virtual** Fabric Engine 9.3.1.0 |
| `templates/extreme_port_speed_expect_snmp/` | Extreme Port Speed Expect by SNMP | imported, not piloted |
| `templates/extreme_routing_snmp/` | Extreme Routing by SNMP (OSPF) | imported, not piloted |
| `templates/extreme_iq_engine_snmp/` | Extreme IQ Engine by SNMP | **v1 YAML** — TemplateRule wired; pilot snmpwalk pending |

`mibs/` holds the EXOS 32.7.3.15 and VOSS 5520 9.3.1.0 MIB dumps used to source OIDs.

## Reference

| Path | Contents |
|---|---|
| `reference/aerohive-mibs/` | Official XIQ Auxiliary `AH-*` MIB texts (AP template source) |
| `reference/*-zabbix.md` | Older design snapshots — prefer numbered docs above when they disagree |

## Related (do not duplicate here)

| Concern | Doc |
|---|---|
| nbxSync GUI setup (what is set in NetBox) | [`../docs/netbox-zabbix/configuration.md`](../docs/netbox-zabbix/configuration.md) |
| First-build scripts (optional) | [`../scripts/README.md`](../scripts/README.md) |
