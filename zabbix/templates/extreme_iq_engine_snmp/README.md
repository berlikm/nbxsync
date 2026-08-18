# Extreme IQ Engine by SNMP

Zabbix **7.0** template for Extreme / Aerohive **HiveOS / IQ Engine** access points.

**What pages:** [`../../02-extreme-access-points.md`](../../02-extreme-access-points.md). Do not also link Network Generic.

## Import

Zabbix → Templates → Import → `template_net_extreme_iq_engine_snmp.yaml` (7.0+). Re-import after YAML changes — NetBox macros do not rewrite trigger status, item delays, or dashboards.

Template Rule: platform matches `IQ ENGINE`, `IQEngine`, or `IQ-ENGINE` (case-insensitive). `HiveOS` alone does not match.

Host dashboard **Health** (pages Overview / RF) plus **Network interfaces** ships in this YAML.

| NetBox | Effect |
|---|---|
| Role Access Point | CG SNMP Monitoring (`MONITORING` MD5/DES) |
| Platform `IQ ENGINE` | this template + `OS/Network` |

OIDs: [OID_MAPPING.md](OID_MAPPING.md).
