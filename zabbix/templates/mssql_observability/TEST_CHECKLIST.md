# MSSQL Observability — test checklist

Import `template_mssql_observability.yaml` on Zabbix **7.0**. Link it **next to**
stock **MSSQL by Zabbix agent 2**. Agent 2 + MSSQL plugin ≥ **7.0.10**.

v1 covers **named instances**. Per-database LLD on those instances is v2 — not
in this YAML.

## Before the canary

1. Plugin version on the agent matches 7.0.10+.
2. SQL Server Browser running, **or** a static TCP port per instance (URI-with-name uses Browser).
3. Monitoring login created **on every named instance** (`VIEW SERVER STATE` /
   `VIEW ANY DEFINITION` / msdb job grants). Same password as `{$MSSQL.PASSWORD}`.
4. Do **not** set `Plugins.MSSQL.Sessions` on the agent.
5. Stock `{$MSSQL.URI}` stays `sqlserver://localhost:1433`. Do not point it at a named instance.

## Canary hosts

Use **one default-only** (`CH-STA-T-MSQL01`) and **one named** (`CH-STA-P-MSSQL10`).

| Check | `MSQL01` | `MSSQL10` |
|---|---|---|
| Stock `mssql.version` with role URI | value | 1433 may be unused / unsupported — expected |
| Companion LLD | **empty** | one row per `MSSQL$*` (`sqlserver://localhost/PITDV02`, …) |
| Census (`MIN=0`) | quiet | quiet unless you set MIN on the Device |
| Stock backup-age PROBLEM | **off** (`USED=0`, Test) | **on** (`USED=1`, Production) after HostSync |
| Buffer cache / page life PROBLEM | **off** (`HYGIENE.CONTROL=0`) | **on** (`=1`) |
| Each `mssql.ping` / `mssql.version` | n/a | has a value |
| Login missing on **one** instance | n/a | one Average, not five, not a Windows service down |
| Stop `MSSQL$PITDV02` | n/a | Windows service item fires; companion ping/version go quiet (nodata depends on ping) |
| HostSync | does **not** create hosts named PITDV02 | same |
| Re-import companion | LLD rows stable (`{#MSSQL.INSTANCE}`) | same |

Health honeycomb should show one cell per named instance (green=ping 1).

## Do not

- Nest stock MSSQL on this template
- Add `service.discovery` (collides with Windows by agent)
- Use `sqlserver://localhost:1433/PITDV02` (port wins; instance ignored)
- Clone stock TCP 1433 Disaster onto named instances
- Expect per-DB backup/state on named instances (v2)
