# SAP — what LogicMonitor actually monitored

There is **no item-level LM export** in this repo. The only sources are
[`../../logicmonitor-assessment.md`](../../logicmonitor-assessment.md)
(from the Aug 2026 LM account export) and the placeholder commit that
counted SAP ME hosts. The 2026-09-05 walk of `CH-STA-P-SH01` is in
[`../../notes/sap-snmp-walk.md`](../../notes/sap-snmp-walk.md).

## LM planes

| LM thing | Where | What it watched | This template |
|---|---|---|---|
| Credential `SAPUSER` (group override, MD5/DES) | SAP systems, roles SAP HANA / SAP ME | Host SNMP (Linux Net-SNMP) | **Live** — MIB-II, IF-MIB, UCD 2021, HOST-RESOURCES |
| API account `C_PROMONITOR` | **11 SAP hosts** | Promonitor RFC/API session | Trapper `sap.app.promonitor` — empty until DNUS/`zabbix_sender` |
| Custom datasource | **ch-sta-p-sh01 only** | ABAP runtime/errors, IDoc, qRFC, job alerts, syslog | Trappers `sap.app.abap.errors`, `sap.app.idoc.errors`, `sap.app.qrfc.errors`, `sap.app.job.alerts`, `sap.app.syslog.alerts` |
| `WinProcessStats_jstart` | ch-sta-p-as02, ch-sta-d-as01 | AS Java `jstart` process | **Not here** — AS Java agent stub |
| Placeholder “SAP ME (10)” | Role SAP ME | Hosts discoverable in Zabbix, items later | Same YAML on SAP ME **and** SAP HANA |

## What we do not have

- Promonitor / DNUS script output format
- Least-privilege SAP account beyond the name `C_PROMONITOR`
- A host list beyond “11 SAP hosts” + canary `CH-STA-P-SH01`
- SAP enterprise SNMP (`1.3.6.1.4.1.2312`) — probe found none
- Net-SNMP `extend` — probe found none

Do not treat UCD CPU/memory as HANA or ABAP health. Application triggers
stay off until `{$SAP.APP.CONTROL}=1` after Robert/DNUS pushes the trappers.
