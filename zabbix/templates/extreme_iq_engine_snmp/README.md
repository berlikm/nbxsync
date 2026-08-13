# Extreme IQ Engine by SNMP

Zabbix **7.0** template for Extreme / Aerohive **HiveOS / IQ Engine** access points.

**What pages:** [`../../02-extreme-access-points.md`](../../02-extreme-access-points.md). Do not also link Network Generic.

## Import

Zabbix → Templates → Import → `template_net_extreme_iq_engine_snmp.yaml` (7.0+). Re-import after YAML changes — NetBox macros do not rewrite trigger status or item delays.

Template Rule: platform name contains `IQ ENGINE` (case-insensitive). `HiveOS` alone does not match.

| NetBox | Effect |
|---|---|
| Role Access Point | CG SNMP Monitoring (`MONITORING` MD5/DES) |
| Platform `IQ ENGINE` | this template + `OS/Network` |

OIDs: [OID_MAPPING.md](OID_MAPPING.md).
