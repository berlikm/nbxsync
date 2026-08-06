# Extreme IQ Engine by SNMP

Zabbix **7.0** template for Extreme / Aerohive **HiveOS / IQ Engine** access points (ExtremeCloud IQ).

**Status:** design + OID analysis — YAML not built yet. Spec: `zabbix/02-extreme-access-points.md`.

## Sources

| Source | Role |
|---|---|
| [XIQ Auxiliary Files](https://documentation.extremenetworks.com/XIQ/Auxiliary_Files/Auxiliary%20Files.html) | Official `AH-*` MIBs → `zabbix/reference/aerohive-mibs/` |
| [bgp4plus/Zabbix-Template](https://github.com/bgp4plus/Zabbix-Template) `Aerohive_AP.xml` | Community shortlist (Zabbix 5.0) — reference only |
| Track B zerotouch | Role Access Point → SNMP CG; TemplateRule `IQ ENGINE` (today Network Generic → retarget here) |

## Do not

- Import `reference_bgp4plus_Aerohive_AP.xml` into production Zabbix 7.
- Link **Network Generic** on Access Point / IQ Engine (icmpping policy).
- Page both switch `UP-…` link-down and AP host-down for the same cable cut without a dependency plan.

## Next build steps

1. Pilot `snmpwalk` against a production-like AP (OIDs in `OID_MAPPING.md`).
2. Author `template_net_extreme_iq_engine_snmp.yaml` (Zabbix 7.0 export).
3. Point TemplateRule **Extreme IQ Engine** at this template.
4. Staged triggers per `02` §9.
