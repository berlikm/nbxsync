# MSSQL Observability (estate companion)

Sits **next to** stock **MSSQL by Zabbix agent 2** (not nested). Stock keeps the default instance (`{$MSSQL.URI}=sqlserver://localhost:1433`). This companion LLD `MSSQL$*` named instances and calls the same Agent 2 plugin with `sqlserver://localhost/{#MSSQL.INSTANCE}`.

Import `template_mssql_observability.yaml` into Zabbix 7.0 (Templates/Databases). Zerotouch then **soft-assigns** it on roles MSSQL / MSSQL Query Server; apply does **not** fail if Cloud has not imported it yet, and it does **not** HostSync the fleet.

Do not add `service.discovery` (Windows by agent already owns that key). Do not add graph prototypes that point at stock. Do not put instance names in NetBox.

Tests (no live SQL): `python3 scripts/test_mssql_observability.py`. Canary still needs a real box (`CH-STA-T-MSQL01` + `CH-STA-P-MSSQL10`) — see [`../../notes/mssql-agent2-instances.md`](../../notes/mssql-agent2-instances.md).
