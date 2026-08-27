# MSSQL named instances (Agent 2 companion)

Operator macros live in [`docs/netbox-zabbix/configuration.md`](../../docs/netbox-zabbix/configuration.md) §11.3. This note is the build spec for **SQL metrics and database/backup inventories on every named instance** without putting instance names in NetBox.

YAML: [`templates/mssql_observability/template_mssql_observability.yaml`](../templates/mssql_observability/template_mssql_observability.yaml). Tests: `python3 scripts/test_mssql_observability.py` (WMI fixtures + YAML contract; no live Windows/SQL here). Do not invent host prototypes. Do not return to **MSSQL by ODBC**. Do not bind stock graph prototypes (same nested-graph lesson as Forti).

Verified against official Zabbix **7.0**:

- Template **MSSQL by Zabbix agent 2** vendor **7.0-6** (`templates/db/mssql_agent2/`)
- Agent 2 MSSQL plugin (template requires plugin **≥ 7.0.10**)
- Plugin URI instance form since **Zabbix 7.0.6**: `sqlserver://localhost/InstanceName` (no port; a port in the URI **ignores** the instance name)

---

## Decision

Keep linking stock **MSSQL by Zabbix agent 2** on roles **MSSQL** and **MSSQL Query Server** (zerotouch already does). That template has **one** `{$MSSQL.URI}` and then LLD of databases / jobs / Always On **on that one connection**.

Add a thin companion **MSSQL Observability** (same pattern as FortiGate Observability, but **not** nested):

- Discovers **named** Windows SQL instances (`MSSQL$PITDV02`, …)
- Calls the **same plugin keys** as stock, with a URI that includes `{#MSSQL.INSTANCE}`
- Does **not** rediscover the default instance `MSSQLSERVER` (stock owns `sqlserver://localhost:1433`)
- Does **not** create extra Zabbix hosts

NetBox still has **one object per Windows box**. Secrets stay `{$MSSQL.USER}` / `{$MSSQL.PASSWORD}` on that object (or USER on the role if the login name is fleet-wide). **No** `{$MSSQL.DSN:"PITDV02"}` rows.

This remains **template-only**. It adds no nbxsync job, model, setting, or
runtime collector. One Windows host remains one NetBox object and one Zabbix
host.

---

## What stock already is (do not fork)

Every collect item on **MSSQL by Zabbix agent 2** is of the form:

```
mssql.<master>.get["{$MSSQL.URI}","{$MSSQL.USER}","{$MSSQL.PASSWORD}"]
```

Masters are cloned as **item prototypes**, not as another stock template.
The companion retains named-instance `mssql.db.get` and
`mssql.last.backup.get` JSON long enough to render durable, normalized
database and backup inventories in Latest data.

Stock's `mssql.database.discovery` is dependent on one connection and creates
per-database item prototypes for that connection. Zabbix cannot attach a
second discovery rule *under each discovered named instance* on the same host.
The companion therefore has one inventory item per named instance instead of
pretending nested LLD exists. Every returned database is visible in that
inventory; per-database trigger prototypes remain stock/default-instance-only.

Stock macros that stay on the role / template (do not duplicate in the companion unless overriding):

| Macro | Stock default | Companion |
|---|---|---|
| `{$MSSQL.URI}` | empty space in YAML — **set** `sqlserver://localhost:1433` on the role | unused by named-instance prototypes |
| `{$MSSQL.USER}` / `{$MSSQL.PASSWORD}` | empty | **same macros** in prototype keys |
| `{$MSSQL.HOST}` / `{$MSSQL.PORT}` | `localhost` / `1433` | do not use for named instances (dynamic ports) |
| `{$MSSQL.DBNAME.NOT_MATCHES}` | `master\|tempdb\|model\|msdb` | applies to stock per-database LLD on the default instance; companion inventories show all returned databases |
| `{$MSSQL.BACKUP_*.USED:"dbname"}` | mute backup-age per **database** | stock/default-instance triggers only; companion presents named-instance backup ages without per-DB threshold triggers |

`{$MSSQL.DSN}` is **MSSQL by ODBC** only (DSN lives in **proxy** `odbc.ini`). Zerotouch already unlinked ODBC. Role `{$MSSQL.DSN}=nbxsync` is dead for Agent 2.

Stock trigger **MSSQL: Service is unavailable** is **Disaster** on `net.tcp.service[tcp,{$MSSQL.HOST},{$MSSQL.PORT}]`. That simple check runs on the **proxy**, so `HOST=localhost` is the proxy, not SQL. Named instances often are **not** on 1433. Estate rule: Disaster is site-only. Mute or drop to High **after** Windows `MSSQLSERVER` / `MSSQL$*` service items. Out of scope for this companion, but do not copy that trigger onto named-instance prototypes.

---

## Split of labour (one Windows host)

Example: `CH-STA-T-MSQL01` (default only) vs `CH-STA-P-MSSQL10` (Protocols for PITDV02, PCONF02, PWARE01, PJIRA01, PAPDB01).

| Signal | Who | `MSQL01` | `MSSQL10` |
|---|---|---|---|
| Service running | **Windows by Zabbix agent** `service.discovery` | `MSSQLSERVER`, `SQLBrowser` | those plus `MSSQL$PITDV02`, … |
| SQL metrics, default instance | **MSSQL by Zabbix agent 2** | `{$MSSQL.URI}=sqlserver://localhost:1433` | 1433 often **unused** → stock items unsupported; that is expected until v1 companion is live |
| SQL metrics, named instances | **MSSQL Observability** | LLD empty (OK) | one prototype row per `MSSQL$*` |

Do **not** put `{#MSSQL.INSTANCE}` in a NetBox macro. HostSync runs before Zabbix has discovered PITDV02.

---

## Companion LLD (v1)

### Why not `service.discovery` again

Windows by agent already owns `service.discovery`. A second template with the same key **collides**. Use a **distinct** master key.

### Master item

Type: Zabbix agent (active if that is how Windows is polled).

Key (unique; **no `$` in the key**):

```
wmi.getall[root\cimv2,"SELECT Name,DisplayName,State,StartMode FROM Win32_Service WHERE Name LIKE 'MSSQL%'"]
```

`LIKE 'MSSQL$%'` would put `$` in a Zabbix item key and still need a regex-safe filter (`$` is end-of-line in LLD regex). `LIKE 'MSSQL%'` is the documented `wmi.getall` shape; JS then keeps only `/^MSSQL\$/` and drops `MSSQLSERVER` plus `MSSQLFDLauncher` / `MSSQLFDLauncher$…`. `SQLSERVERAGENT` / `SQLAgent$…` / `SQLBrowser` never match `MSSQL%`. Default-only hosts (`MSQL01`) correctly yield `[]`.

If WMI is locked down on some boxes, fallback is a loadable/userparameter that reads:

`HKLM\SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL`

Same JSON shape after preprocessing. Do not enable `system.run`.

### Preprocessing → LLD JSON

JavaScript (`lld_named_instances.js`, discard unchanged heartbeat `1h`). Same script is embedded in the YAML (tests compare them) and run under Node against WMI fixtures:

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

## Item prototypes and instance inventory

All SQL collection uses **plugin keys** so the loadable MSSQL plugin executes
the query. User/password remain host macros (the same values for every
instance on that Windows box).

Keys include the URI string, so they cannot collide with stock
`…["{$MSSQL.URI}",…]` unless someone sets `{$MSSQL.URI}` to a named URI and
also discovers it. Do not do that. Stock URI stays
`sqlserver://localhost:1433`.

The companion creates these items for every discovered named instance:

1. `mssql.version[uri,user,password]` — a 5-minute version probe and one
   Average `nodata(15m)` trigger.
2. `mssql.perfcounter.get[…]` and `mssql.job.status.get[…]` — raw plugin
   masters; per-counter/job LLD is deliberately not forked from stock.
3. `mssql.db.get[…]` — raw JSON retained 7d, plus:
   - `mssql.observability.db.count["instance"]` (90d);
   - `mssql.observability.db.inventory["instance"]` (30d): every database
     name and normalized recovery model.
4. `mssql.last.backup.get[…]` — raw JSON retained 7d, plus
   `mssql.observability.backup.inventory["instance"]` (7d): every database's
   available full (`D`), differential (`I`), and log (`L`) backup age.

The two inventory items are text JSON intentionally: they are searchable and
auditable in **Monitoring → Latest data**, tagged
`sql_instance=<instance>`, and require no per-instance host or NetBox row.
They do not fabricate missing ages as zero and do not add threshold triggers
without named-instance baseline policy.

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
| Role **MSSQL** / **MSSQL Query Server** | stock **MSSQL by Zabbix agent 2** (already) + companion **MSSQL Observability** (soft: only after YAML import) |
| Role | `{$MSSQL.URI}` = `sqlserver://localhost:1433` |
| Role | `{$MSSQL.USER}` only if the login **name** is global |
| **Device / VM** | `{$MSSQL.PASSWORD}` (and USER if not global) — like vCenter, not like a shared Forti token |
| Device | optional `{$MSSQL.INSTANCE.DISCOVERY.MIN}` = `5` on `MSSQL10` if you want census |
| Device | **no** instance names, **no** DSN contexts |

HostSync that one host after the companion template is imported. LLD fills
PITDV02 and its instance-level database/backup inventories. No nbxsync code
or scheduled NetBox collector is needed. If NetBox is SOT for host macros, do
not leave DSN contexts only in Zabbix.

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

## Template-only database inventory boundary

The v1 LLD discovers named instances, but Zabbix has no nested database LLD
for item prototypes on the same host. This rollout explicitly keeps nbxsync
unchanged rather than adding a server-side flattener or creating unmanaged host
prototypes.

Use these Latest data items for a named instance:

| Item key | Retention | Contents |
|---|---:|---|
| `mssql.observability.db.inventory["<instance>"]` | 30d | every `db.get` database name and recovery model |
| `mssql.observability.backup.inventory["<instance>"]` | 7d | every valid full/diff/log age from `last.backup.get` |
| `mssql.observability.db.count["<instance>"]` | 90d | count returned by `db.get`, including system databases |

This exposes every database from every dynamically discovered named instance
without hard-coding names. It intentionally does **not** synthesize
per-database item keys, per-database backup triggers, or
`{$MSSQL.BACKUP_*:"instance/db"}` policy until there is an operator-approved
data path that does not alter nbxsync or create unmanaged hosts.

Reporting Service QUEUE (LogicMonitor leftover) remains a **custom query**,
not instance LLD.
---

## What the tests cover vs canary

**Covered in-repo** (`scripts/test_mssql_observability.py`):

- Default-only WMI fixture (`MSSQLSERVER` + Browser + Agent + FDLauncher) → LLD `[]`
- `MSSQL10` fixture → five URIs `sqlserver://localhost/PITDV02` … `PAPDB01`, no port
- JS drops `MSSQLFDLauncher$…`, `SQLAgent$…`, telemetry, writer
- Single WMI object (not array) still becomes one LLD row
- Invalid JSON throws (item unsupported) instead of a fake empty census
- Database fixture → all five names and normalized recovery models; backup
  fixture → all valid `D`/`I`/`L` ages without zero-filled missing data
- YAML: Zabbix 7.0, official `Templates/Databases` UUID, no nest of stock,
  no `service.discovery`, no `graphprototype`, no `net.tcp.service`, no
  Disaster; raw database/backup history and inventory retention are explicit
- Zerotouch: optional template, no YAML import, URI on both MSSQL roles

**Still canary-only** (no Windows/SQL in this environment): plugin
`mssql.version` against a real named instance, WMI on Agent 2, login created
inside each instance, SQL Browser / dynamic port, and every database shown in
the two inventory items.

## Implementation

Folder: `zabbix/templates/mssql_observability/` (YAML, named-instance LLD,
database/backup inventory JS, and fixtures). Template name **MSSQL
Observability**.

- Do **not** nest stock MSSQL. Link alongside stock on the role: two templates,
  different keys.
- One WMI master, dependent instance LLD + census, five plugin prototype
  masters, database count, durable database inventory, and backup inventory.
- No dashboard and no stock graph prototypes.
- No nbxsync source or configuration change is required for these inventories.
- Import the YAML in Zabbix (GUI or later `--apply-mssql`), then HostSync the
  canary; do not HostSync the fleet from a template import alone.
