# ExtremeControl by SNMP

Zabbix **7.0** template for ExtremeControl / IA-V engines via
`ENTERASYS-NAC-APPLIANCE-MIB`.

**What pages:** [`../../07-extreme-control.md`](../../07-extreme-control.md).
Do not also link Network Generic. Do not assign EXOS / VOSS / IQ templates.

## Import

Zabbix → Templates → Import → `template_net_extremecontrol_snmp.yaml` (7.0+),
or `configure_nbxsync_network.py --apply-xiqse`. Re-import after YAML changes
— NetBox macros do not rewrite trigger status, item delays, or dashboards.

Template assignment: role **NAC**, SNMP interface. Same SNMPv3 CG as switches
(`MONITORING`, MD5/DES) — proven 2026-08-28 on all five ENACs.

Host dashboard **Health** (pages Overview / Auth) ships in this YAML.

| NetBox | Effect |
|---|---|
| Role NAC | this template (SNMP) **and** ExtremeControl Observability (ANY) |
| ICMP / Linux agent | stay on 06 — this template does not nest `icmpping` |

OIDs: [OID_MAPPING.md](OID_MAPPING.md).
