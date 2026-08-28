# MSSQL named instances (Agent 2 companion)

Operator macros live in [`docs/netbox-zabbix/configuration.md`](../../docs/netbox-zabbix/configuration.md) §11.3. This note is the build spec for **SQL metrics, graphs, and database/backup inventories on every named instance** without putting instance names in NetBox.

YAML: [`templates/mssql_observability/template_mssql_observability.yaml`](../templates/mssql_observability/template_mssql_observability.yaml). Tests: `python3 scripts/test_mssql_observability.py` (WMI fixtures + YAML contract; no live Windows/SQL here). Do not return to **MSSQL by ODBC**. Do not bind stock graph prototypes on the companion (same nested-graph lesson as Forti). Do not nest stock **MSSQL by Zabbix agent 2** on this template.

Verified against official Zabbix **7.0**:

- Template **MSSQL by Zabbix agent 2** vendor **7.0-6** (`templates/db/mssql_agent2/`)
- Agent 2 MSSQL plugin (template requires plugin **≥ 7.0.10**)
- Plugin URI instance form since **Zabbix 7.0.6**: `sqlserver://<host>/InstanceName` (no port; a port in the URI **ignores** the instance name). Named-instance `<host>` is `{$MSSQL.LISTEN.HOST}` (NetBox `primary_ip4` after HostSync). Stock **parent** default-instance URI stays `sqlserver://localhost:1433`.
- Host prototypes: LLD expands `{#…}` only. `{HOST.HOST}` / `{HOST.NAME}` / `{HOST.CONN}` are **not** substituted in host names, visible names, group prototypes, tags, or prototype macro values (`src/zabbix_server/lld/lld_host.c` → `zbx_substitute_lld_macros`). Nested discovery-under-discovery on the same host is **7.4+** (ZBXNEXT-1527), not Cloud 7.0.
- Cloud **7.0** import **rejects** a `description` field on host prototypes. Leave it off the YAML. The import-contract test asserts that.

---

## Decision

Keep linking stock **MSSQL by Zabbix agent 2** on roles **MSSQL** and **MSSQL Query Server** (zerotouch already does). That template has **one** `{$MSSQL.URI}` and then first-level LLD of databases / jobs / Always On **on that one connection**.

Add companion **MSSQL Observability** (same pattern as FortiGate Observability, but **not** nested):

- Discovers **named** Windows SQL instances (`MSSQL$PITDV02`, …)
- Calls the **same plugin keys** as stock, with a URI that includes `{#MSSQL.INSTANCE}`
- Does **not** rediscover the default instance `MSSQLSERVER` (stock on the Windows host owns `sqlserver://localhost:1433`)
- On Cloud **7.0**, creates **host prototypes** so each named instance is a child host with stock Agent 2. That is the workaround until nested LLD exists (Zabbix 7.4 / 8): stock’s `mssql.database.discovery` can then run as a first-level rule on the child and produce per-database items, graphs, and honeycomb `database:` tags — the same pack operators already have on the default instance.

NetBox still has **one object per Windows box**. Secrets stay `{$MSSQL.USER}` / `{$MSSQL.PASSWORD}` on that object (or USER on the role if the login name is fleet-wide). **No** `{$MSSQL.DSN:"PITDV02"}` rows. Children are Zabbix-discovered, not NetBox devices.

This remains **template-only**. It adds no nbxsync job, model, setting, or runtime collector. HostSync still updates only the bound Windows hostid.

### Why not flatten LLD or nest stock

| Approach | Why it fails here |
|---|---|
| Nested LLD on the Windows host | Cloud 7.0 cannot attach `mssql.database.discovery` *under* each `{#MSSQL.INSTANCE}` row (ZBXNEXT-1527). |
| `last_foreach` of TEXT `db.get` catalogs | Cloud rejected it; not a valid discovery source. |
| Nest stock on the companion | Still **one** `{$MSSQL.URI}` — named instances would not get their own connection. |
| Link stock five times on the Windows host | Zabbix forbids duplicate template links. |
| External collector / trapper / ODBC | Out of scope; Agent 2 plugin is the data path. |

Host prototypes split **one URI per host**. Inherited parent macros include `{$MSSQL.USER}` / `{$MSSQL.PASSWORD}`. The prototype **must** override `{$MSSQL.URI}`; otherwise the child inherits `sqlserver://localhost:1433` and silently monitors the default instance again.

---

## What stock already is (do not fork)

Every collect item on **MSSQL by Zabbix agent 2** is of the form:

```
mssql.<master>.get["{$MSSQL.URI}","{$MSSQL.USER}","{$MSSQL.PASSWORD}"]
```

Masters on the companion are cloned as **item prototypes** on the Windows host (version, perf, jobs, plus retained `db.get` / `last.backup.get` inventories). Per-database item prototypes, graphs, and honeycomb stay **stock** — on the Windows host for the default instance, on each **child host** for named instances.

Stock macros that stay on the role / template (do not duplicate in the companion unless overriding):

| Macro | Stock default | Companion |
|---|---|---|
| `{$MSSQL.URI}` | empty space in YAML — **set** `sqlserver://localhost:1433` on the role | unused by named-instance item prototypes; **overridden on each child** to `{#MSSQL.URI}` (`sqlserver://{$MSSQL.LISTEN.HOST}/{#MSSQL.INSTANCE}`) |
| `{$MSSQL.USER}` / `{$MSSQL.PASSWORD}` | empty | **same macros** in prototype keys; children inherit the Windows host values |
| `{$MSSQL.HOST}` / `{$MSSQL.PORT}` | `localhost` / `1433` | do not use for named instances (dynamic ports). Stock TCP Disaster on children still uses these — see canary |
| `{$MSSQL.DBNAME.NOT_MATCHES}` | `master\|tempdb\|model\|msdb` | applies to stock per-database LLD (default instance on the parent, named instance on the child) |
| `{$MSSQL.BACKUP_*.USED:"dbname"}` | mute backup-age per **database** | keep **1** on every environment; do not mute Test/Dev |

`{$MSSQL.DSN}` is **MSSQL by ODBC** only. Zerotouch already unlinked ODBC.

Stock trigger **MSSQL: Service is unavailable** is **Disaster** on `net.tcp.service[tcp,{$MSSQL.HOST},{$MSSQL.PORT}]`. That SIMPLE check runs on the **proxy**, not through Agent 2. `{$MSSQL.HOST}=localhost` is the proxy. Pointing it at the Windows IP still fails when SQL 1433 is not reachable from the proxy (normal: monitoring uses agent :10050; plugin talks to SQL on-box). Plugin items can be green while this Disaster is red. YAML cannot disable an inherited stock trigger (export/import drops host-level inherited overrides). On Cloud: disable **Service's TCP port state** / **MSSQL: Service is unavailable** on named-instance **children**, and on Windows parents if the same false Disaster is open. Availability is stock `mssql.ping` and the companion version probe. Do **not** clone that trigger onto the companion. Do **not** fork stock to delete it.

Stock per-database **performance** items are dependents of `mssql.db.perf_raw["{#DBNAME}"]` (`history: 0`), which JSONPaths `object_name=~'.*Databases'` and `instance_name=='{#DBNAME}'`, then one JSONPath per counter (`Transactions/sec`, `Active Transactions`, log-file sizes, …). **State** uses that **same** master (`counter_name=='State'`). Named-instance object names (`MSSQL$ASP:Databases`) already match `.*Databases`. If that slice contains `State` but omits the size/log/tx `counter_name` rows, those ~13 derivatives stay **unsupported** while State still works. Backups / recovery model use `last.backup.get`, not perf_raw. Instance-level `_Total` Databases counters (total data/log file size, total transactions) can still be green. That is SQL Server / perfmon payload, not a missing URI. Do **not** fork the vendor template or invent a second counter map in the companion.

Stock **Cache hit ratio** (`mssql.cache_hit_ratio`) JSONPaths `counter_name=='CacheHitRatio'` on Plan Cache `_Total`. Sibling Plan Cache items (`Cache Object Counts`, `Cache Pages`, `Cache objects in use`) use spaced names and can be green while this one is unsupported — known vendor 7.0-6 mismatch vs `Cache Hit Ratio`. **Buffer cache hit ratio** is a different object and is the useful cache metric. Do **not** fork stock to insert a space.

Latest data **empty last value** on every `component: raw` **Get …** item is **`history: 0`**, not a collection failure. Filter Latest data to hide `component: raw` before judging gaps. Count **Not supported**, not blank cells.

---

## Split of labour

Example: `CH-STA-T-MSQL01` (default only) vs `CH-STA-P-MSSQL10` (PITDV02, PCONF02, PWARE01, PJIRA01, PAPDB01).

| Signal | Who | `MSQL01` | `MSSQL10` |
|---|---|---|---|
| Service running | **Windows by Zabbix agent** `service.discovery` on the **parent** | `MSSQLSERVER`, `SQLBrowser` | those plus `MSSQL$PITDV02`, … |
| SQL metrics + DB graphs, default instance | **MSSQL by Zabbix agent 2** on the **parent** | `{$MSSQL.URI}=sqlserver://localhost:1433` | 1433 often **unused** → stock items unsupported; expected |
| Named-instance ping/version/inventory JSON | **MSSQL Observability** prototypes on the **parent** | LLD empty (OK) | one prototype row per `MSSQL$*` |
| Named-instance per-DB metrics, graphs, honeycomb | **MSSQL by Zabbix agent 2** on the **child** `{#MSSQL.PARENT}-mssql-{#MSSQL.INSTANCE}` | no children | five children |
| OS / ICMP | Windows by agent + Agent Monitoring on the **parent only** | — | do not link Windows/ICMP on children |

Do **not** put `{#MSSQL.INSTANCE}` in a NetBox macro. HostSync runs before Zabbix has discovered PITDV02.

---

## Host groups

Estate groups stay **Sites × Roles × OS × Priority** (§8 in the operator doc). Discovered children are **not** NetBox objects, so they cannot join `Sites/…`, `Roles/MSSQL`, or `OS/Windows` via HostSync.

Zabbix 7.0: **group prototypes that match a manually created group are not linked**. `Roles/MSSQL` and `Roles/MSSQL Query Server` are HostSync groups — never name them as group prototypes or `group_links` (the link is silently skipped).

Children join **one** YAML group:

| Group | Kind | Purpose |
|---|---|---|
| `MSSQL instances` | YAML `host_groups` + host-prototype `group_links` (UUID `6f2c8a91d4b047e3b8c15a7e9d04f3c2`) | Fleet of discovered instance hosts. Grant this group to the same user groups that can see `Roles/MSSQL` and `Roles/MSSQL Query Server`. |

Do **not** add group prototypes. The canary used three and they do not belong in production:

| Dropped prototype | Why it is wrong |
|---|---|
| `{#MSSQL.PARENT}` | New **root** group named like a hostname (`CH-STA-T-MSQL25` next to `Sites` / `Roles` / `OS`). N groups for N boxes. Parent Windows host is already in `Roles/MSSQL` |
| `{#MSSQL.PARENT}/{#MSSQL.INSTANCE}` | One group per named instance, usually **one host**. Databases are stock LLD **items** on that host, not extra hosts. The child visible name is already `{#MSSQL.PARENT} / {#MSSQL.INSTANCE}` |
| `Roles/MSSQL/{#MSSQL.PARENT}` | N more groups. Puts **MSSQL Query Server** children under `Roles/MSSQL`. Parent is already in the correct role group |

Find a box’s instances with host tags `parent_host` / `sql_instance` (or search `…-mssql-…`). Do not recreate the Sites/Roles tree under LLD.

Scale: N Windows boxes with named instances, M named instances total.

| Design | Groups created |
|---|---|
| Three prototypes + fleet (old) | `1 + 2N + M` (MSSQL10 with five instances → 8 groups; ~30 boxes × 2 instances → ~121) |
| Fleet only (production) | **1** (`MSSQL instances`) |

`{#MSSQL.PARENT}` still names the **child host** (`{#MSSQL.PARENT}-mssql-{#MSSQL.INSTANCE}`). It comes from `{$MSSQL.PARENT.HOST}` when that user macro is set (user macros **do** expand in JS preprocessing), otherwise from WMI `Win32_Service.SystemName`. Built-in `{HOST.HOST}` cannot be used there.

When Cloud has nested LLD, drop the host prototype. Named-instance databases then live on the **parent**, which is already in `Roles/MSSQL` / `Roles/MSSQL Query Server`. Delete leftover empty groups (`CH-STA-T-MSQL25`, `CH-STA-T-MSQL25/ASP`, `Roles/MSSQL/CH-STA-T-MSQL25`, …) after the prototype no longer creates them.

Re-import uses `deleteMissing: false`, so Cloud **keeps** the three group prototypes until you delete them on the host prototype (Data collection → Templates → MSSQL Observability → Discovery → Host prototypes). Then check-now LLD on the parent; then delete the empty leftover groups. Do not HostSync-delete `MSSQL instances`.

---

## Companion LLD (v1)

### Why not `service.discovery` again

Windows by agent already owns `service.discovery`. A second template with the same key **collides**. Use a **distinct** master key.

### Master item

Type: Zabbix agent (passive — proxy polls the Windows IP). Active-agent-only boxes would not feed child hosts; this estate’s companion items are agent-passive.

Key (unique; **no `$` in the key**):

```
wmi.getall[root\cimv2,"SELECT Name,DisplayName,State,StartMode,SystemName FROM Win32_Service WHERE Name LIKE 'MSSQL%'"]
```

`LIKE 'MSSQL$%'` would put `$` in a Zabbix item key. `LIKE 'MSSQL%'` is the documented `wmi.getall` shape; JS then keeps only `/^MSSQL\$/` and drops `MSSQLSERVER` plus `MSSQLFDLauncher` / `MSSQLFDLauncher$…`. `SQLSERVERAGENT` / `SQLAgent$…` / `SQLBrowser` never match `MSSQL%`. Default-only hosts (`MSQL01`) correctly yield `[]`.

`SystemName` is the Windows computer name. It is **not** always the Zabbix technical name (`CH-STA-P-MSSQL10`). Optional role/device macro `{$MSSQL.PARENT.HOST}` (Jinja `{{ object.name }}`) overrides it so child names and hostname groups match NetBox.

If WMI is locked down on some boxes, fallback is a loadable/userparameter that reads:

`HKLM\SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL`

Same JSON shape after preprocessing, including a parent name. Do not enable `system.run`.

### Preprocessing → LLD JSON

JavaScript (`lld_named_instances.js`, discard unchanged heartbeat `1h`). Same script is embedded in the YAML (tests compare them) and run under Node against WMI fixtures.

For each WMI row `Name` = `MSSQL$PITDV02`:

| LLD macro | Value |
|---|---|
| `{#MSSQL.SERVICE}` | `MSSQL$PITDV02` |
| `{#MSSQL.INSTANCE}` | `PITDV02` (strip `MSSQL$`) |
| `{#MSSQL.URI}` | `sqlserver://{$MSSQL.LISTEN.HOST}/PITDV02` (falls back to `localhost` if the macro is empty, unresolved, or contains `:` / `/`) |
| `{#MSSQL.LISTEN}` | resolved listen host (NetBox primary IPv4 after HostSync, else `localhost`) |
| `{#MSSQL.DISPLAY}` | WMI `DisplayName` (hover; e.g. `SQL Server (PITDV02)`) |
| `{#MSSQL.PARENT}` | `{$MSSQL.PARENT.HOST}` if set, else sanitized `SystemName` |

URI rules (plugin 7.0.6+):

- Named: `sqlserver://{$MSSQL.LISTEN.HOST}/{#MSSQL.INSTANCE}` — **no port**
- Never `sqlserver://localhost:1433/PITDV02` (port wins, instance ignored)
- Never put a port in `sqlserver://10.0.100.10/PCONF02` either (same rule)
- Do **not** put per-instance VIP:1433 URIs in NetBox. SQL Browser on the Windows host plus the instance name is the discovery path.

`{$MSSQL.LISTEN.HOST}` is required when SQL has `ListenOnAllIPs=0` and loopback (`IPLocalhost`) off: those instances listen on the Windows IP (and often a dedicated VIP:1433), **not** on `127.0.0.1`. Agent 2 `sqlserver://localhost/<instance>` then fails with `no instance matching '…' returned from host 'localhost'`. Pointing Browser at the Windows `primary_ip4` (`sqlserver://10.0.100.10/PCONF02`) hits the IPHost port. Instances that already listen on `0.0.0.0` (e.g. PAPPDB01) keep working. Override the host macro to `localhost` only on a box whose SQL is loopback-only. Do **not** enable `ListenOnAllIPs` on the four dedicated-IP instances (they share 1433 on different VIPs).

Live on `CH-STA-P-MSQL10` (do not change SQL):

| Instance | ListenOnAllIPs | Loopback | Where it actually listens |
|---|---|---|---|
| **PAPPDB01** (MSSQL17) | **1** | yes (`0.0.0.0:50807`) | Agent 2 already ESTABLISHED to `127.0.0.1:50807` |
| **PCONF02** | 0 | IPLocalhost **Enabled=0** | `10.0.100.10:55664`, VIP `10.0.100.23:1433` |
| **PWARE01** | 0 | off | `10.0.100.10:55665`, VIP `10.0.100.32:1433` |
| **PJIRA01** | 0 | off | `10.0.100.10:55666`, VIP `10.0.100.36:1433` |
| **PITDB02** | 0 | off | `10.0.100.10:55662`, VIP `10.0.100.20:1433` (also `.19:1433`) |

SQL Browser is up on `0.0.0.0:1434`. `HideInstance=0`. IPAll dynamic ports are **not** listening. Same four named instances fail the same way on MSQL11.

A named-instance row with no resolvable parent **throws** (item unsupported), not a fake empty census.

### LLD filters (macros on the companion)

| Macro | Default | Purpose |
|---|---|---|
| `{$MSSQL.INSTANCE.MATCHES}` | `.*` | allowlist if a box grows a junk instance |
| `{$MSSQL.INSTANCE.NOT_MATCHES}` | `CHANGE_IF_NEEDED` | e.g. `SQLEXPRESS` |
| `{$MSSQL.INSTANCE.DISCOVERY.MIN}` | `0` | census; **0** is valid (`MSQL01`). Set per Device only if you want “we expect five” |
| `{$MSSQL.PARENT.HOST}` | empty | optional Zabbix technical name; empty → WMI `SystemName` |
| `{$MSSQL.LISTEN.HOST}` | `localhost` | named-instance plugin host (no port). HostSync Jinja `{{ object.primary_ip4.address.ip }}` on the role. Override to `localhost` if SQL is loopback-only |

Filter on `{#MSSQL.INSTANCE}`. Do not filter in NetBox.

---

## Item prototypes and instance inventory (on the Windows host)

All SQL collection uses **plugin keys** so the loadable MSSQL plugin executes
the query. User/password remain host macros (the same values for every
instance on that Windows box).

Keys include the URI string, so they cannot collide with stock
`…["{$MSSQL.URI}",…]` unless someone sets `{$MSSQL.URI}` to a named URI and
also discovers it. Do not do that. Stock URI on the parent stays
`sqlserver://localhost:1433`.

The companion creates these items for every discovered named instance **on the parent** (additive with stock on the child):

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

Open the **child** host for per-database graphs. Parent inventories remain the searchable JSON census.

---

## Host prototype

| Field | Value |
|---|---|
| Technical name | `{#MSSQL.PARENT}-mssql-{#MSSQL.INSTANCE}` (unique vs NetBox device names; contains `{#…}`) |
| Visible name | `{#MSSQL.PARENT} / {#MSSQL.INSTANCE}` |
| Templates | **MSSQL by Zabbix agent 2** only (no Windows, no ICMP) |
| Interfaces | inherit parent (`custom_interfaces: NO`) — passive poll of the Windows IP; plugin URI is `{$MSSQL.LISTEN.HOST}` (primary IPv4 after HostSync) |
| Inventory | DISABLED |
| Macro | `{$MSSQL.URI}={#MSSQL.URI}` (`sqlserver://{$MSSQL.LISTEN.HOST}/{#MSSQL.INSTANCE}`; `{HOST.CONN}` is not expanded on prototypes) |
| Tags | `component=mssql-instance`, `sql_instance={#MSSQL.INSTANCE}`, `parent_host={#MSSQL.PARENT}` |
| Host groups | **`MSSQL instances` only** (`group_links`). No group prototypes |

LLD lifetime 7d `DELETE_AFTER`; `enabled_lifetime` disable immediately. Lost instances disable the child at once and delete it after a week.

HostSync looks up the bound Windows host by NetBox name. It does not sweep-delete extra Zabbix hosts. Collision only if a child technical name equals a NetBox device name — the `-mssql-` infix is the guard (same hole VMware VM LLD had, which is why that LLD is disabled; named SQL instances are **not** NetBox devices).

---

## Census / never silent

Calculated item on the companion (not LLD):

```
mssql.observability.instance.count
```

Dependent count from the WMI master JSON length after JS.

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
| Role | `{$MSSQL.URI}` = `sqlserver://localhost:1433` (default instance on the **parent**) |
| Role | `{$MSSQL.LISTEN.HOST}` = `{{ object.primary_ip4.address.ip }}` (named-instance URI host; zerotouch step 11) |
| Role | `{$MSSQL.USER}` only if the login **name** is global |
| Role (optional) | `{$MSSQL.PARENT.HOST}` = `{{ object.name }}` so child host names match the Zabbix host when WMI `SystemName` differs |
| **Device / VM** | `{$MSSQL.PASSWORD}` (and USER if not global) — like vCenter, not like a shared Forti token |
| Device | optional `{$MSSQL.INSTANCE.DISCOVERY.MIN}` = `5` on `MSSQL10` if you want census |
| Device | **no** instance names, **no** DSN contexts, **no** VIP:1433 URIs |

Import the companion YAML in Zabbix (GUI). Then HostSync the **canary Windows host** so Jinja renders `{$MSSQL.LISTEN.HOST}` (and optional `{$MSSQL.PARENT.HOST}`). LLD creates children. Template import alone must **not** HostSync the fleet.

---

## What not to do

| Idea | Why not |
|---|---|
| `{$MSSQL.DSN:"PITDV02"}` in NetBox | Agent 2 has no DSN; not in stock 7.0-6 |
| `{HOST.HOST}` / `{HOST.CONN}` in host/group prototype fields | Server LLD does not expand built-in host macros there; children would collide as `{HOST.HOST}-mssql-PITDV02`. Listen host is `{$MSSQL.LISTEN.HOST}` (user macros **do** expand in JS) |
| `description` on the host prototype | Cloud 7.0 import rejects the field; keep it off the YAML |
| Fork stock to “fix” named-instance DB perf counters | Stock already matches `.*Databases`. Missing `Transactions/sec` etc. means those counters are absent from `mssql.perfcounter.get` for that DB. Enable/repair SQL perf counters on the instance; do not vendor-fork |
| Put children in HostSync group `Roles/MSSQL` via `group_links` | Prototype groups that match manually created groups are not linked |
| Hostname / `{parent}/{instance}` / `Roles/MSSQL/{parent}` group prototypes | Explodes the group tree (1+2N+M groups). Query Server children would sit under `Roles/MSSQL`. Tags `parent_host` / `sql_instance` already identify the box. Children join only `MSSQL instances` |
| Link stock template five times on the parent | Zabbix forbids duplicate template link |
| Companion `service.discovery` | Key collision with Windows by agent |
| `{#INSTANCE}` in a NetBox Jinja macro | HostSync cannot see LLD |
| `Plugins.MSSQL.Sessions` in `mssql.conf` | Hand-edited agents |
| Fork stock YAML to add instance LLD | Update pain; companion only |
| URI `sqlserver://localhost:1433/PITDV02` | Port wins; instance ignored |
| URI `sqlserver://<vip>:1433` per instance in NetBox | Children are LLD, not NetBox objects. Browser + Windows `primary_ip4` is the path. Do not enable `ListenOnAllIPs` on dedicated-VIP instances that share 1433 |
| Disaster on one named instance down | Site/service only; Windows service is Average/High per estate OS bar |
| Nest ICMP Ping or Windows by agent on the child | Duplicate OS/ICMP; parent already has them |
| HostSync the fleet from this template import | Children are LLD; sync the canary Windows host only |

---

## Canary (before fleet)

Planned boxes: **one default-only** (`CH-STA-T-MSQL01`) and **one named** (`CH-STA-P-MSSQL10`). First live proof used **`CH-STA-T-MSQL25`** (named instance `ASP`).

**Live (Cloud, after YAML import + forced WMI on the parent):**

| Object | Id / result |
|---|---|
| Template **MSSQL Observability** | 14024 |
| Host group **MSSQL instances** | 265 |
| Parent `ch-sta-t-msql25` | 14007 |
| Child `CH-STA-T-MSQL25-mssql-ASP` | 14080; visible `CH-STA-T-MSQL25 / ASP` |
| Child templates | stock **MSSQL by Zabbix agent 2** only |
| Child URI | `sqlserver://localhost/ASP` (inherited user/password; inherited parent agent interface) |
| Tags | `sql_instance=ASP`, `parent_host=CH-STA-T-MSQL25` |
| Child DB LLD | `database=ServerInformationDb` materialized (23 discovered items). **State** `ONLINE (0)` and **full/diff/log backup** items supported, with values. `{$MSSQL.DBNAME.NOT_MATCHES}` hides master/tempdb/model/msdb — one user DB on ASP is expected |
| Parent default instance | **HADB** still supported, state `0`. **SensirionAuthDB** per-DB **Percent log used** fires on the parent — default-instance Databases counters work on this box |
| Child Latest data | **176** items: **162 Normal**, **14 Not supported**. SQL version `17.0.1125.2` (2025 Developer). Jobs: nine Agent jobs, all status/schedule items valued |
| Child empty cells | **32** `component: raw` Get-masters (`history: 0`) look blank while Normal. Hide `component: raw` |
| Child Not supported (14) | **Cache hit ratio** + **13** ServerInformationDb perf derivatives (list below). State on the same `perf_raw` is green |

**Child Latest data accounting (`CH-STA-T-MSQL25 / ASP`, stock Agent 2):**

| What you see | Count | Verdict |
|---|---:|---|
| Total items | 176 | Stock template + one DB LLD row + nine jobs |
| Normal | 162 | Includes 32 raw masters that store nothing |
| Not supported | 14 | Real gaps (below) |
| `component: raw` | 32 | `history: 0` by design. Dependents have values (jobs, SQL Statistics, Buffer Manager, backups, State) |
| Jobs (`mssql-job`) | 9 × 7 | Enabled, last/next run, duration, status, message — complete. Only **Get job status** is raw |
| AG / replica / quorum / mirroring / local DB / non-local DB | masters only | No discovered AG/mirroring items. ASP is not in an AG (or LLD empty). Expected, not a URI miss |
| **Service's TCP port state** | Down (0) | **False** SIMPLE from the proxy. Disable that item/trigger. Plugin Version and Uptime are green |
| Instance-level perf (batch requests, PLE, memory, locks, latches, SQL compilations, worktables, …) | valued ~24s | Agent 2 + `sqlserver://localhost/ASP` is collecting |
| Instance Databases `_Total` | Total data file size 282.52 GB, total log 5.05 GB, total tx/sec | `Get DB counters` payload is healthy at `_Total` |
| ServerInformationDb State / recovery / backups | valued | `perf_raw` slice exists (State); backup master exists |
| ServerInformationDb size/log/tx (13) | empty + Not supported | Those `counter_name` rows are missing from `instance_name=='ServerInformationDb'` even though State is present. Same stock JSONPaths work for SensirionAuthDB on the **default** instance. SQL/perfmon on ASP, not companion |
| Cache hit ratio | empty + Not supported | Vendor JSONPath `CacheHitRatio` vs Plan Cache `Cache Hit Ratio`. Buffer cache hit ratio **100%** is the item to use |

The 13 unsupported per-DB items (all dependents of `mssql.db.perf_raw["ServerInformationDb"]`):

Active transactions; Data file size; Log bytes flushed per second; Log file size; Log file used size; Log flushes per second; Log flush waits per second; Log flush wait time; Log growths; Log shrinks; Log truncations; Percent log used; Transactions per second.

Do **not** fork stock. To see the payload once: on the **child**, set history 1h on **MSSQL DB 'ServerInformationDb': Get performance counters**, check-now, read `counter_name` values, then set history back to 0. If you need those graphs, repair SQL per-db counters for `MSSQL$ASP` (not a second map in Observability).

**Problems opened after the child appeared (do not “fix” the wrong layer):**

| Problem | Host | Verdict |
|---|---|---|
| **MSSQL: Service is unavailable** Disaster | Child *and* parent (parent since 2026-08-26) | **False.** Stock SIMPLE `net.tcp.service[tcp,localhost,1433]` from the **proxy**. Plugin/HADB/ASP data still flow via Agent 2. Disable **Service's TCP port state** on the child (and on the parent if that Disaster is still open). YAML cannot disable inherited stock triggers. |
| **MSSQL [ASP]: no version data for 15m** Average | Parent | **Companion false nodata.** Version prototype used `DISCARD_UNCHANGED_HEARTBEAT` **1d** with `nodata(15m)`. A stable version looked silent. Removed the discard; re-import Observability. |
| Ad hoc compilations > 10% / scans vs searches / recompiles > 10% Warning | Parent **and** child | **Two instances, same stock OLTP hygiene — and proof instance-level Agent 2 on ASP is collecting.** Parent = default instance (`localhost:1433`). Child = ASP. Instance-level SQL Statistics, not per-DB. Test workload; not a prototype duplicate of one item. Do not fork stock to raise `{$MSSQL.PERCENT_COMPILATIONS.MAX}` unless operators want that estate-wide. |
| Work tables from cache < 90% High | Parent **and** child | Same split: stock `{$MSSQL.WORKTABLES_FROM_CACHE_RATIO.MIN.CRIT}=90`. High is a page in the Extreme bar; here it is vendor MSSQL on Test. Leave stock; do not mute Test backups to “fix” this. |
| Full backup older than 10d HADB / SensirionAuthDB High | Parent | **Real default-instance backup age.** `{$MSSQL.BACKUP_FULL.USED}` stays **1**. |
| SensirionAuthDB log usage > 80% Warning | Parent | **Real** stock per-DB log counter on the default instance. |
| Windows InventorySvc Disaster / TempDB T: > 80% High | Parent | **OS template**, not MSSQL Observability. |

Import path: GUI/YAML into Cloud (`deleteMissing: false`), then HostSync / check-now of the **Windows** host only. After the version-item change, re-import Observability so the parent ASP version prototype drops the 1d discard.

Remaining checklist:

1. Plugin version on the agent matches 7.0.10+.
2. `MSQL01`: stock `mssql.version` works with role URI; companion LLD **empty**; no census alarm (MIN=0); **no** child hosts.
3. `MSSQL10` / `MSQL11`: Windows shows five `MSSQL$*` services; HostSync renders `{$MSSQL.LISTEN.HOST}` = `10.0.100.10`; companion LLD = five URIs `sqlserver://10.0.100.10/PCONF02` … (no port); PAPPDB01 (ListenOnAllIPs=1) and the four dedicated-IP instances all return plugin version. `sqlserver://localhost/<instance>` stays **wrong** for PCONF02 / PITDB02 / PJIRA01 / PWARE01 (loopback off).
4. Five children `…-mssql-PITDV02` … with stock Agent 2. Host group: **MSSQL instances** only. Parent stays in NetBox `Roles/MSSQL`. No hostname / `{parent}/{instance}` / `Roles/MSSQL/{parent}` groups.
5. Open a **child** → Latest data → stock database LLD (graphs / honeycomb / `database:` tags). Hide `component: raw` (history 0). Count **Not supported**, not blank Get-items. Do not look for those graphs on the Observability filter of the Windows host.
6. Login missing on **one** instance → one Average on that child/parent version item, not five, not a Windows service down.
7. Stop `MSSQL$PITDV02` → Windows service item fires; companion version goes nodata.
8. Stock 1433 items on `MSSQL10` parent may be unsupported — record it; do not “fix” with a fake DSN.
9. Stock TCP Disaster on parent or child: **false** when plugin items have data. Disable **Service's TCP port state** on that host. Leave `mssql.ping` as availability. Do not retarget `{$MSSQL.HOST}` hoping the proxy can reach 1433.
10. HostSync **does not** create hosts named `PITDV02` or `ASP`. It **may** create `CH-STA-T-MSQL25-mssql-ASP` only via LLD, not NetBox. Re-sync of the Windows host must not delete children.
11. Second apply / re-import companion: LLD rows and children stable (same `{#MSSQL.INSTANCE}` / `{#MSSQL.PARENT}`). Host prototype still has **no** `description` and **no** group prototypes. `deleteMissing: false` will **not** drop the three canary group prototypes — delete them on the template host prototype, check-now the parent, then delete leftover empty groups `CH-STA-T-MSQL25`, `CH-STA-T-MSQL25/ASP`, `Roles/MSSQL/CH-STA-T-MSQL25`. Child stays in `MSSQL instances`.
12. After Cloud nested LLD exists: remove the host prototype; keep named-instance item prototypes on the parent.

---

## Parent inventories vs child graphs

Parent Latest data (companion):

| Item key | Retention | Contents |
|---|---:|---|
| `mssql.observability.db.inventory["<instance>"]` | 30d | every `db.get` database name and recovery model |
| `mssql.observability.backup.inventory["<instance>"]` | 7d | every valid full/diff/log age from `last.backup.get` |
| `mssql.observability.db.count["<instance>"]` | 90d | count returned by `db.get`, including system databases |

Child Latest data (stock Agent 2): per-database items, graph prototypes, honeycomb. That is the operator path that matches the default instance.

Reporting Service QUEUE (LogicMonitor leftover) remains a **custom query**, not instance LLD.

---

## What the tests cover vs canary

**Covered in-repo** (`scripts/test_mssql_observability.py`):

- Default-only WMI fixture (`MSSQLSERVER` + Browser + Agent + FDLauncher) → LLD `[]`
- `MSSQL10` fixture → five URIs `sqlserver://localhost/PITDV02` … `PAPDB01` when `{$MSSQL.LISTEN.HOST}` is unresolved (Node does not expand macros); with listen host `10.0.100.10` → `sqlserver://10.0.100.10/PCONF02` …, no port, `{#MSSQL.LISTEN}` set, `{#MSSQL.PARENT}=CH-STA-P-MSSQL10`
- JS drops `MSSQLFDLauncher$…`, `SQLAgent$…`, telemetry, writer
- Single WMI object (not array) still becomes one LLD row
- Invalid JSON throws (item unsupported) instead of a fake empty census
- Missing parent on a named-instance row throws; `{$MSSQL.PARENT.HOST}` wins over `SystemName`; illegal characters sanitized
- Database fixture → all five names and normalized recovery models; backup
  fixture → all valid `D`/`I`/`L` ages without zero-filled missing data
- YAML: Zabbix 7.0, official `Templates/Databases` UUID, no nest of stock on
  the companion, host prototype links stock, **no host-prototype `description`**
  (Cloud import rejects it), **no group prototypes**, children `group_links`
  only `MSSQL instances`, `{#MSSQL.PARENT}` in host/visible names and tags
  (not `{HOST.HOST}`), no `service.discovery`, no
  `graphprototype`, no `net.tcp.service`, no Disaster, no `last_foreach`,
  host-prototype `{$MSSQL.URI}={#MSSQL.URI}`, companion `{$MSSQL.LISTEN.HOST}`
- Zerotouch: optional template, no YAML import, parent URI on both MSSQL
  roles, `{$MSSQL.LISTEN.HOST}` Jinja `{{ object.primary_ip4.address.ip }}`
  on both MSSQL roles

**Still canary-only** (no Windows/SQL in this environment): plugin
`mssql.version` against a real named instance, WMI `SystemName` vs NetBox
name, child host creation, stock database LLD/graphs on the child, TCP
Disaster behaviour, HostSync of the parent leaving children alone.
`CH-STA-T-MSQL25` / `ASP` already proved child creation, URI override,
inherited credentials/interface, stock DB **state** + **backup**, jobs,
and instance-level Agent 2 perf. Named-instance **per-DB size/log/tx**
and stock **Cache hit ratio** remain SQL/vendor JSONPath gaps (14 Not
supported). Filter out `component: raw` when reading Latest data.

## Implementation

Folder: `zabbix/templates/mssql_observability/` (YAML, named-instance LLD,
database/backup inventory JS, and fixtures). Template name **MSSQL
Observability**.

- Do **not** nest stock MSSQL on the companion. Link alongside stock on the
  role. Link stock on **host prototypes** (children) — that is not nesting
  on the companion.
- One WMI master, dependent instance LLD + census, plugin prototypes,
  inventories, and one host prototype.
- No dashboard and no stock graph prototypes on the companion.
- Zerotouch step 11 writes `{$MSSQL.LISTEN.HOST}` Jinja on both MSSQL
  roles (same HostSync path as `{$VMWARE.URL}`). Import the YAML in
  Zabbix, then HostSync the canary Windows parent so the listen host
  renders; do not HostSync the fleet from a template import alone.
