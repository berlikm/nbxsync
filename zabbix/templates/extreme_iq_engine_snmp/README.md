# Extreme IQ Engine by SNMP

Zabbix **7.0** template for Extreme / Aerohive **HiveOS / IQ Engine** access points.

Operator page (source of truth for what pages): [`../../02-extreme-access-points.md`](../../02-extreme-access-points.md).

## Import

Zabbix → Templates → Import → `template_net_extreme_iq_engine_snmp.yaml`. Requires Zabbix **7.0+**.  
Re-import after severity / DISABLED changes — NetBox macros do not rewrite trigger status.

NetBox Template Rule: platform matches `IQ ENGINE` (case-insensitive substring). `HiveOS` alone does not match.

## Wiring

| NetBox fact | Effect |
|---|---|
| Role **Access Point** | CG **SNMP Monitoring** (`MONITORING` MD5/DES, GETBULK) |
| Platform matches `IQ ENGINE` | TemplateRule → **Extreme IQ Engine by SNMP** + `OS/Network` |
| Role template floor | **None** (Network Generic pruned) |

## What pages (live YAML)

| Trigger | Sev | State |
|---|---|---|
| ICMP down | High | on |
| No SNMP data collection | Average | on (depends on ICMP) |
| Memory high | Average | on (depends on ICMP + SNMP) |
| Temperature warn / crit | Average | on — canary 70/85, not switch 95/100 |
| CPU warn (90%) | Warning | on |
| AP eth link down | Warning | on — plant page is switch `UP-` High |
| CPU critical, ICMP loss/RTT, client count | — | **DISABLED** |

Radio items have **no** triggers (graphs only).

## Coverage

- ICMP + SNMP availability
- AH-SYSTEM-MIB scalars (CPU/mem/temp/clients/serial/FW/…)
- Radio LLD: **primary** `ahIfType=ahPHYSICAL(0)`; secondary name `wifiN`/`radioN`
- Noise floor: MIB −256; FLOAT + parse for OCTET STRING agents
- Graphs: host CPU + clients; radio RF + retries/drops; eth traffic
- Eth IF-MIB LLD (`eth`/`mgt` only)

## Ops

XIQ **manage SNMP** on AP eth, then Delta update.

NL/US/CH APs are polled by the **Swiss proxy group**. `snmpget` from a laptop is not the production path.

After AP reboot: if proxy CLI SNMPv3 works but Zabbix availability stays 0, reload proxy SNMP cache (`zabbix_proxy -R snmp_cache_reload`) — Zabbix/RFC 3414 engine-boots window, not a wrong OID.

## Do not

- Also link **Network Generic** (icmpping collision).
- High-page AP temperature (stub OID) or dump SNMP-dead on Warning.
- Treat a working dev `snmpget` as proof the CH proxy can poll UDP/161.
