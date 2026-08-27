# MSSQL named instances (Agent 2 companion)

Operator macros live in [`docs/netbox-zabbix/configuration.md`](../../docs/netbox-zabbix/configuration.md) §11.3. This note is the build spec for **SQL metrics on every named instance** without putting instance names in NetBox.

YAML is the companion in [`../templates/mssql_observability/`](../templates/mssql_observability/). Spec below is still the operator contract.

Verified against official Zabbix **7.0**:

- Template **MSSQL by Zabbix agent 2** vendor **7.0-6** (`templates/db/mssql_agent2/`)
- Agent 2 MSSQL plugin (template requires plugin **≥ 7.0.10**)
- Plugin URI instance form since **Zabbix 7.0.6**: `sqlserver://localhost/InstanceName` (no port; a port in the URI **ignores** the instance name)

---

## Decision

Keep linking stock **MSSQL by Zabbix agent 2** on roles **MSSQL** and **MSSQL Query Server** (zerotouch already does). That template has **one** `{$MSSQL.URI}` and then LLD of databases / jobs / Always On **on that one connection**.

Add a thin companion **MSSQL Observability** (same pattern as FortiGate Observability, but **linked alongside** stock rather than nested):

- Discovers **named** Windows SQL instances (`MSSQL$PITDV02`, …)
- Calls the **same plugin keys** as stock, with a URI that includes `{#MSSQL.INSTANCE}`
- Does **not** rediscover the default instance `MSSQLSERVER` (stock owns `sqlserver://localhost:1433`)
- Does **not** create extra Zabbix hosts

NetBox still has **one object per Windows box**. Secrets stay `{$MSSQL.USER}` / `{$MSSQL.PASSWORD}` on that object (or USER on the role if the login name is fleet-wide). **No** `{$MSSQL.DSN:"PITDV02"}` rows.

---

## What stock already is (do not fork)

Every collect item on **MSSQL by Zabbix agent 2** is of the form:

```
mssql.<master>.get["{$MSSQL.URI}","{$MSSQL.USER}","{$MSSQL.PASSWORD}"]
```

Masters (clone these as **item prototypes**, not the hundreds of JSONPath dependents in v1):

| Stock item | Plugin key |
|---|---|
| Version | `mssql.version[uri,user,password]` |
| Get performance counters | `mssql.perfcounter.get[…]` |
| Get job status | `mssql.job.status.get[…]` |
| Get last backup | `mssql.last.backup.get[…]` |
| Get database | `mssql.db.get[…]` |
| Get availability groups | `mssql.availability.group.get[…]` |
| Get local/non-local DB, replica, mirroring, quorum | same pattern |

LLD rules on stock are **dependent** on those masters (`mssql.database.discovery` → `{#DBNAME}`, job discovery → `{#JOBNAME}`, …). Zabbix **cannot** attach a new discovery rule per discovered instance on the same host (discovery prototypes exist for **host** prototypes only). So v1 of the companion does **instance-level** masters only. Per-database LLD on named instances is v2 (flatten). See [Later](#later-v2-flattened-database-lld).

Stock macros that stay on the role / template (do not duplicate in the companion unless overriding):

| Macro | Stock default | Companion |
|---|---|---|
| `{$MSSQL.URI}` | empty space in YAML — **set** `sqlserver://localhost:1433` on the role | unused by named-instance prototypes |
| `{$MSSQL.USER}` / `{$MSSQL.PASSWORD}` | empty | **same macros** in prototype keys |
| `{$MSSQL.HOST}` / `{$MSSQL.PORT}` | `localhost` / `1433` | do not use for named instances (dynamic ports) |
| `{$MSSQL.DBNAME.NOT_MATCHES}` | `master\|tempdb\|model\|msdb` | v2 only |
| `{$MSSQL.BACKUP_*.USED:"dbname"}` | mute backup-age per **database** | official context use; **not** DSN |
| `{$MSSQL.BACKUP_*.USED}` (no context) | **role Jinja**: `1` on `-p-` Production, `0` on Dev/Test | stock backup-age stays off on non-prod; v2 named-instance backup should reuse this |
| `{$MSSQL.HYGIENE.CONTROL}` | companion default `1`; **role Jinja** same as USED | buffer-cache / page-life Warnings on Production only |

`{$MSSQL.DSN}` is **MSSQL by ODBC** only (DSN lives in **proxy** `odbc.ini`). Zerotouch already unlinked ODBC. Role `{$MSSQL.DSN}=nbxsync` is dead for Agent 2.

Stock trigger **MSSQL: Service is unavailable** is **Disaster** on `net.tcp.service[tcp,{$MSSQL.HOST},{$MSSQL.PORT}]`. That simple check runs on the **proxy**, so `HOST=localhost` is the proxy, not SQL. Named instances often are **not** on 1433. Estate rule: Disaster is site-only. Mute or drop to High **after** Windows `MSSQLSERVER` / `MSSQL$*` service items. Out of scope for this companion, but do not copy that trigger onto named-instance prototypes.

---

## Split of labour (one Windows host)

Example: `CH-STA-T-MSQL01` (default only) vs `CH-STA-P-MSSQL10` (Protocols for PITDV02, PCONF02, PWARE01, PJIRA01, PAPDB01).

| Signal | Who | `MSQL01` | `MSSQL10` |
|---|---|---|---|
| Service running | **Windows by Zabbix agent** `service.discovery` | `MSSQLSERVER`, `SQLBrowser` | those plus `MSSQL$PITDV02`, … |
| SQL metrics, default instance | **MSSQL by Zabbix agent 2** | `{$MSSQL.URI}=sqlserver://localhost:1433` | 1433 often **unused** → stock items unsupported; that is expected |
| SQL metrics, named instances | **MSSQL Observability** | LLD empty (OK) | one prototype row per `MSSQL$*` |

Do **not** put `{#MSSQL.INSTANCE}` in a NetBox macro. HostSync runs before Zabbix has discovered PITDV02.

---

## Companion LLD (v1)

### Why not `service.discovery` again

Windows by agent already owns `service.discovery`. A second template with the same key **collides**. Use a **distinct** master key.

### Master item

Type: Zabbix agent (active if that is how Windows is polled).

Key (unique):

```
wmi.getall[root\cimv2,"SELECT Name,DisplayName,State,StartMode FROM Win32_Service WHERE Name LIKE 'MSSQL$%'"]
```

`MSSQLSERVER` is **intentionally omitted** (no `$`). `SQLSERVERAGENT` / `SQLAgent$…` / `SQLBrowser` do not match `MSSQL$%`.

If WMI is locked down on some boxes, fallback is a loadable/userparameter that reads:

`HKLM\SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL`

Same JSON shape after preprocessing. Do not enable `system.run`.

### Preprocessing → LLD JSON

JavaScript (discard unchanged heartbeat `1h`):

For each WMI row `Name` = `MSSQL$PITDV02`:

| LLD macro | Value |
|---|---|
| `{#MSSQL.SERVICE}` | `MSSQL$PITDV02` |
| `{#MSSQL.INSTANCE}` | `PITDV02` (strip `MSSQL$`) |
| `{#MSSQL.URI}` | `sqlserver://localhost/PITDV02` |
| `{#MSSQL.DISPLAY}` | WMI `DisplayName` (hover; e.g. `SQL Server (PITDV02)`) |

URI rules (plugin 7.0.6+):

- Named: `sqlserver://localhost/{#MSSQL.INSTANCE}` — **no port**
- Never `sqlserver://localhost:1433/PITDV02` (port wins, instance ignored)
- Never `sqlserver://<primary_ip>/…` for Agent 2 on-box (that is a different host)

### LLD filters (macros on the companion)

| Macro | Default | Purpose |
|---|---|---|
| `{$MSSQL.INSTANCE.MATCHES}` | `.*` | allowlist if a box grows a junk instance |
| `{$MSSQL.INSTANCE.NOT_MATCHES}` | `CHANGE_IF_NEEDED` | e.g. `SQLEXPRESS` |
| `{$MSSQL.INSTANCE.DISCOVERY.MIN}` | `0` | census; **0** is valid (`MSQL01`). Set per Device only if you want “we expect five” |

Filter on `{#MSSQL.INSTANCE}`. Do not filter in NetBox.

---

## Item prototypes (v1)

All use **plugin keys** so the loadable MSSQL plugin does the query. User/password are **host** macros (same for every instance on that box).

Keys **include the URI string**, so they cannot collide with stock `…["{$MSSQL.URI}",…]` unless someone sets `{$MSSQL.URI}` to `sqlserver://localhost/PITDV02` **and** that instance is also discovered. Do not do that. Stock URI stays `sqlserver://localhost:1433`.

Minimum set (each: agent, then a few JSONPath dependents if the master is JSON):

1. `mssql.version["{#MSSQL.URI}","{$MSSQL.USER}","{$MSSQL.PASSWORD}"]`  
   - Item name: `MSSQL [{#MSSQL.INSTANCE}]: Version`  
   - Tags: `sql_instance={#MSSQL.INSTANCE}`
2. `mssql.perfcounter.get["{#MSSQL.URI}","{$MSSQL.USER}","{$MSSQL.PASSWORD}"]`  
   - History `0`, dependent rates as needed (start with batch requests / page life / buffer cache — not the full stock pack)
3. `mssql.job.status.get["{#MSSQL.URI}",…]`
4. `mssql.last.backup.get["{#MSSQL.URI}",…]`
5. `mssql.db.get["{#MSSQL.URI}",…]`  
   - History `0`. Dependent: **database count** via JSONPath length (no DB LLD). System DBs still in the JSON; count is “what SQL returned”, not the stock MATCHES filter.

Triggers (on the companion, **not** Disaster):

| Event | Sev | Notes |
|---|---|---|
| `mssql.version` unsupported / nodata 15m | Average | login missing **on that instance**, plugin, Browser/port |
| Version item empty while Windows `MSSQL$…` is running | Average | service up, TDS down |
| Named instance count `< {$MSSQL.INSTANCE.DISCOVERY.MIN}` when MIN>0 | Average | census, same idea as Forti SD-WAN expected |

Do **not** clone stock “TCP 1433 Disaster” onto each instance.

Dependent JSONPath metrics: copy **sparingly** from stock (buffer cache, batch req/s, lock timeouts). Full stock clone as prototypes is unmaintainable across 7.0-6 → 7.0-7.

---

## Census / never silent

Calculated item on the companion (not LLD):

```
mssql.observability.instance.count
```

Formula: count of items matching `mssql.version["sqlserver://localhost/*` **or** a dependent count from the WMI master JSON length after JS.

Trigger when `{$MSSQL.INSTANCE.DISCOVERY.MIN}>0` and `last()<min`. Default MIN=0 so `MSQL01` stays quiet.

Windows already alerts if `MSSQL$PITDV02` is stopped. Companion alerts if the service is up but SQL login/URI fails.

---

## Prerequisites (Windows box, not NetBox)

1. **Zabbix agent 2** with MSSQL **loadable plugin ≥ 7.0.10** (template 7.0-6 text).
2. Server/proxy **7.0.6+** for instance-in-URI.
3. **SQL Server Browser** running, **or** a static TCP port per instance (URI-with-name uses Browser; URI-with-port cannot name the instance).
4. Monitoring login **created on every named instance** (logins are not Windows-wide):

```sql
CREATE LOGIN zabbix WITH PASSWORD = '...';
GRANT VIEW SERVER STATE TO zabbix;          -- 2017/2019; 2022: VIEW SERVER PERFORMANCE STATE
GRANT VIEW ANY DEFINITION TO zabbix;
USE msdb;
CREATE USER zabbix FOR LOGIN zabbix;
GRANT SELECT ON msdb.dbo.sysjobs TO zabbix;
GRANT SELECT ON msdb.dbo.sysjobactivity TO zabbix;
GRANT SELECT ON msdb.dbo.sysjobservers TO zabbix;
GRANT EXECUTE ON msdb.dbo.agent_datetime TO zabbix;
```

Same password as `{$MSSQL.PASSWORD}` on that NetBox object. Repeat on PITDV02, PCONF02, …

5. Do **not** configure `Plugins.MSSQL.Sessions.*` on the agent. That is per-host file config; the URI argument on the item is the zerotouch path.

---

## NetBox / nbxSync (still zerotouch)

| Object | Assignment |
|---|---|
| Role **MSSQL** / **MSSQL Query Server** | stock **MSSQL by Zabbix agent 2** (already) + companion **MSSQL Observability** (`--apply-mssql`) |
| Role | `{$MSSQL.URI}` = `sqlserver://localhost:1433` |
| Role | `{$MSSQL.USER}` only if the login **name** is global |
| **Device / VM** | `{$MSSQL.PASSWORD}` (and USER if not global) — like vCenter, not like a shared Forti token |
| Device | optional `{$MSSQL.INSTANCE.DISCOVERY.MIN}` = `5` on `MSSQL10` if you want census |
| Device | **no** instance names, **no** DSN contexts |

HostSync that one host. Companion LLD fills PITDV02. If NetBox is SOT for host macros, do not leave DSN contexts only in Zabbix.

Query Server: same companion. If it is a true replica, stock AG items on the default URI may still apply; named-instance AG is v2.

---

## What not to do

| Idea | Why not |
|---|---|
| `{$MSSQL.DSN:"PITDV02"}` in NetBox | Agent 2 has no DSN; not in stock 7.0-6 |
| Host prototypes per instance | Unmanaged hosts; same hole as VMware VM LLD (disabled here) |
| Link stock template five times | Zabbix forbids duplicate template link |
| Companion `service.discovery` | Key collision with Windows by agent |
| `{#INSTANCE}` in a NetBox Jinja macro | HostSync cannot see LLD |
| `Plugins.MSSQL.Sessions` in `mssql.conf` | Hand-edited agents |
| Fork stock YAML to add instance LLD | Update pain; companion only |
| URI `sqlserver://localhost:1433/PITDV02` | Port wins; instance ignored |
| Disaster on one named instance down | Site/service only; Windows service is Average/High per estate OS bar |
| Nest ICMP Ping on the companion | Windows hosts already have Agent Monitoring / ICMP |

---

## Canary (before fleet)

Use **one default-only** (`CH-STA-T-MSQL01`) and **one named** (`CH-STA-P-MSSQL10`).

1. Plugin version on the agent matches 7.0.10+.
2. `MSQL01`: stock `mssql.version` works with role URI; companion LLD **empty**; no census alarm (MIN=0).
3. `MSSQL10`: Windows shows five `MSSQL$*` services; companion LLD = five URIs `sqlserver://localhost/PITDV02` …; each `mssql.version` has a value.
4. Login missing on **one** instance → one Average, not five, not a Windows service down.
5. Stop `MSSQL$PITDV02` → Windows service item fires; companion version goes nodata (depend or accept both; do not double-page — later: version depends on service, if we can reference Windows items without a hard key contract).
6. Stock 1433 items on `MSSQL10` may be unsupported — record it; do not “fix” with a fake DSN.
7. HostSync **does not** create hosts named PITDV02.
8. Second apply / re-import companion: LLD rows stable (same `{#MSSQL.INSTANCE}`).

---

## Later (v2: flattened database LLD)

Zabbix cannot nest `mssql.database.discovery` under each instance on the same host.

v2 master (single item, JS on the server/proxy **or** an agent script item with a unique key): for each `{#MSSQL.URI}` from v1, call `mssql.db.get`, merge:

```
{#MSSQL.INSTANCE} + {#MSSQL.URI} + {#DBNAME}
```

Then item prototypes for backup age / state using JSONPath filters, with `{$MSSQL.DBNAME.NOT_MATCHES}` applied in LLD filters. Keys must stay unique: include instance **and** dbname.

Until v2, per-DB backup mutes (`{$MSSQL.BACKUP_FULL.USED:"dbname"}`) apply only to **stock** (default instance).

Reporting Service QUEUE (LogicMonitor leftover) is still a **custom query**, not instance LLD.

---

## Implementation (v1 YAML shipped)

New folder: `zabbix/templates/mssql_observability/` (YAML + README). Template name **MSSQL Observability**.

- Group: Templates/Databases  
- Do **not** nest stock MSSQL (nesting would still be one URI). **Link alongside** stock on the role (two templates, different keys).  
- One LLD rule, filters, five prototype masters above, census item, valuemap none required.  
- Dashboard optional and later: honeycomb of instance version/unsupported is enough; do not bind stock graph prototypes (same nested-graph lesson as Forti).  
- Import from `configure_nbxsync_network.py --apply-mssql` (or the UI). **do not** HostSync the fleet from a template import alone. **Do not** add this to zerotouch.

Assign on Device Role **MSSQL** and **MSSQL Query Server** the same way as stock (zerotouch `ZabbixTemplateAssignment`).
