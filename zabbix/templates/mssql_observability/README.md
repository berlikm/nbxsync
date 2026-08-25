# MSSQL Observability (estate companion)

YAML is **not shipped yet**. Spec: [`../../notes/mssql-agent2-instances.md`](../../notes/mssql-agent2-instances.md).

Will sit **next to** stock **MSSQL by Zabbix agent 2** (not nested). Stock keeps the default instance (`{$MSSQL.URI}=sqlserver://localhost:1433`). This companion LLD `MSSQL$*` named instances and calls the same Agent 2 plugin with `sqlserver://localhost/{#MSSQL.INSTANCE}`.

Do not add `service.discovery` (Windows by agent already owns that key). Do not add graph prototypes that point at stock. Do not put instance names in NetBox.
