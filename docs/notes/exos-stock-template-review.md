# Extreme EXOS by SNMP — stock template review notes

Reference for `docs/extreme-switching-zabbix.md` §A.4.

We use the official **Extreme EXOS by SNMP** template from the Zabbix **release/7.0** branch (master requires Zabbix 8.0). **We do not modify the stock template** — scoping and silencing are macro assignments via nbxsync.

## Covered by stock (signals §A.4)

| Signal | Mechanism |
|---|---|
| ICMP / SNMP availability | simple check + internal |
| Uptime / restart | SNMPv2-MIB / HOST-RESOURCES-MIB |
| Temperature, PSU, fan | EXTREME-SYSTEM-MIB |
| CPU / memory | EXTREME-SOFTWARE-MONITOR-MIB |
| Serial / firmware / OS | ENTITY-MIB |
| Link status, speed, errors, discards, octets | IF-MIB LLD `net.if.discovery` |
| Half duplex | EtherLike-MIB LLD |
| Utilisation trigger | present — **silence** with `{$IF.UTIL.MAX}=101` (wrong denominator / window for our use) |

## Gaps vs design (build elsewhere)

| Gap | Where |
|---|---|
| Absolute speed expectation vs label | `Extreme Port Speed Expect by SNMP` |
| Sustained util vs `{#IF.SPEED.EXPECTED}`, outbound discard alert | same thin template (§6.4) |
| Flapping as count of status changes in 1h | build (VOSS already has `rcPortNumStateTransition`; EXOS needs equivalent or ifOperStatus change count) |
| `dot3StatsFCSErrors` (CRC) | open — EtherLike LLD does not poll FCS |
| OSPF adjacency count | `Extreme Routing by SNMP` (§C) |

## LLD filter macros used by stock

`{$NET.IF.IFALIAS.MATCHES}` / `NOT_MATCHES`, `{$NET.IF.IFTYPE.MATCHES}`, admin/oper status, ifName, ifDescr — see design §A.5 / §A.8 for role values.

## Known stock trigger pitfalls

- Speed “changed to lower” uses `last()>0` — misses 10G→down→1G bounce (hence absolute expect).
- Utilisation uses live `ifHighSpeed` and 15m window — silenced globally; replaced by class-scoped 1h avg in stage 6.
- Speed item discard-unchanged heartbeat 1h — do not use `min(speed, 5m)` in triggers.
