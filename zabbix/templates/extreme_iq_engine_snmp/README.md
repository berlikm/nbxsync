# Extreme IQ Engine by SNMP

Zabbix **7.0** template for Extreme / Aerohive **HiveOS / IQ Engine** access points.

**Status:** v1 YAML built — import via zerotouch / network configure. Pilot snmpwalk still required before enabling temp/radio alerts in production.

## Import

1. Automatic: `configure_nbxsync_zerotouch.py` (`ensure_extreme_iq_engine_template`) and `configure_nbxsync_network.py --apply`
2. Manual: Zabbix → Templates → Import → `template_net_extreme_iq_engine_snmp.yaml`

Requires Zabbix **7.0+**.

## Wiring (Track B)

| NetBox fact | Effect |
|---|---|
| Role **Access Point** | CG **SNMP Monitoring** (`MONITORING` MD5/DES) |
| Platform matches `IQ ENGINE` | TemplateRule → **Extreme IQ Engine by SNMP** + `OS/Network` |
| Role template floor | **None** (Network Generic pruned) |

## Coverage (v1)

- ICMP + SNMP availability
- AH-SYSTEM-MIB scalars (CPU/mem/temp/clients/serial/FW/…)
- Radio LLD: **primary** `ahIfType=ahPHYSICAL(0)` (MIB); secondary name `wifiN`/`radioN` (AP305C VAPs)
- Noise floor: MIB −256; FLOAT + parse for OCTET STRING agents
- Threshold macros are **ops defaults** (CPU 90/95, ICMP loss 10) — Extreme does not publish AP SNMP alert points
- Eth IF-MIB LLD (eth/mgt only): oper status + bits in/out

## Sources

| Source | Role |
|---|---|
| [XIQ Auxiliary Files](https://documentation.extremenetworks.com/XIQ/Auxiliary_Files/Auxiliary%20Files.html) | Official MIBs → `zabbix/reference/aerohive-mibs/` |
| [bgp4plus Aerohive AP](https://github.com/bgp4plus/Zabbix-Template) | OID shortlist only (`reference_bgp4plus_Aerohive_AP.xml`) |
| Spec | `zabbix/02-extreme-access-points.md` |

## Ops prerequisite

XIQ must enable SNMP Get on AP eth (`manage SNMP` + Delta update). Without that, SNMP availability stays down while the switch `UP-` port is green.

## Do not

- Also link **Network Generic** (icmpping collision).
- Page both switch `UP-…` and AP ICMP-down for the same cable cut without a dependency plan.
