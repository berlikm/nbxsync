# MSSQL Observability (estate companion)

Zabbix **7.0** companion for named SQL Server instances. Link **next to** stock
**MSSQL by Zabbix agent 2** — do not nest stock (that would still be one
`{$MSSQL.URI}`).

Stock keeps the default instance (`sqlserver://localhost:1433`). This template
LLD-discovers `MSSQL$%` Windows services via WMI and calls the Agent 2 plugin
with `sqlserver://localhost/{#MSSQL.INSTANCE}` (no port; plugin ≥ 7.0.6,
template requires plugin ≥ 7.0.10).

Regenerate YAML from this directory:

```bash
python3 zabbix/templates/mssql_observability/build_template.py
```

## Import

**Manual (one host, for a first test):** Configuration → Templates → Import
`template_mssql_observability.yaml` (`deleteMissing` off). Link **MSSQL
Observability** on the Windows host **alongside** stock Agent 2. Do not unlink
stock. Do not also link ICMP Ping.

**Estate:**

```bash
python3 scripts/configure_nbxsync_network.py --check-mssql
python3 scripts/configure_nbxsync_network.py --apply-mssql
```

That fail-closes if stock **MSSQL by Zabbix agent 2** is missing in Zabbix,
imports this YAML, and assigns it on roles **MSSQL** / **MSSQL Query Server**.
No HostSync, no zerotouch. Then HostSync the canary hosts.

Do **not** re-run zerotouch for this companion.

## What v1 owns

- WMI master `Win32_Service WHERE Name LIKE 'MSSQL$%'` (not `service.discovery`)
- LLD `{#MSSQL.SERVICE}` / `{#MSSQL.INSTANCE}` / `{#MSSQL.URI}` / `{#MSSQL.DISPLAY}`
- Per named instance: `mssql.ping`, `mssql.version`, sparse perfcounters
  (buffer cache, page life, batch req/s, lock timeouts), job/backup/db masters,
  database **count**
- Census `mssql.observability.instance.count` (MIN=0 so default-only hosts stay quiet)
- Host dashboard **Health** (count + ping honeycomb)

v2 (not in this YAML): flattened `{#MSSQL.INSTANCE}+{#DBNAME}` LLD. Zabbix
cannot nest discovery-under-discovery on the same host.

## Alerting

No Disaster. Ping-down and version nodata are **Average** (one ticket: nodata
depends on ping). Buffer cache / page life are **Warning** only.

## Spec / canary

[`../../notes/mssql-agent2-instances.md`](../../notes/mssql-agent2-instances.md) ·
[`TEST_CHECKLIST.md`](TEST_CHECKLIST.md)
