# Swiss proxy tuning (`ch-sta-p-zabp02`)

Operator pages: [01-extreme-switching.md](../01-extreme-switching.md), [06-network-vms.md](../06-network-vms.md), [07-extreme-control.md](../07-extreme-control.md).  
Drop-in: [`../reference/zabbix_proxy.d/swiss-proxy-tuning.conf`](../reference/zabbix_proxy.d/swiss-proxy-tuning.conf).

This note is the analysis of the live `/etc/zabbix/zabbix_proxy.conf` on **`ch-sta-p-zabp02`** (active proxy → `sensirion.zabbix.cloud`). Do not treat it as a second policy. Change the box, then re-measure.

**Symptom that triggered this:** XIQ-SE / Extreme Site Engine SCRIPT items (`xiqse.nbi.health`, `xiqse.nbi.licenses`, `xiqse.nbi.pilot` — Pilot seats) last-checked about **1 hour** ago on `ch-sta-p-ensa01`. Those keys are **not** `/usr/lib/zabbix/externalscripts`. They are Zabbix **SCRIPT** (JavaScript + `HttpRequest`) and they run **on this proxy**.

---

## First: 1h on *everything* is not the poller queue

If Latest data shows **the same age on every item** — ICMP, SNMP, SCRIPT, 30-second and 15-minute alike — “1h and a couple of seconds ago” — that is a **flat 3600s clock offset**. Collection is still running; the couple of seconds is the last interval. A starved `StartPollers` pool does **not** do that: SCRIPT would lag more than ICMP, and ages would scatter.

Live on `ch-sta-p-zabp02` (2026-09-02 08:30 UTC):

```
Local time: Wed 2026-09-02 08:30:01 UTC
Time zone: Etc/UTC (UTC, +0000)
System clock synchronized: yes
NTP service: active
RTC in local TZ: no
```

That clock is healthy. `time()` on the proxy is Unix UTC. **Timezone does not change item `clock`.** Setting the proxy to `Europe/Zurich` will not move “1h ago”.

| What you see | What it is |
|---|---|
| Every item ~1h 2s | Cloud `now` minus stored `clock` is 3600s. Ingest TZ, Cloud instance TZ, or Cloud/PHP clock — not pollers |
| Swiss wall clock vs this proxy | 2 September is **CEST (UTC+2)**. 08:30 UTC = **10:30** in CH. Zurich vs UTC is **2h**, not 1h |
| 1h in September | UTC vs **CET / UTC+1** (winter offset, `CET` without DST, UK BST, or a Cloud TZ stuck on +1) |
| nodata / “no NBI data for 15m” **not** firing | items **are** checking; the 1h is display/clock |
| Graphs: newest point on the **now** edge | same — live data, shifted label |
| Graphs: newest point 1h **left** of now | same 3600s offset in history.clock |
| Only `xiqse.nbi.licenses` / `pilot` hours late, ICMP fresh | then it **is** pollers / SCRIPT timeout — skip this section |

Do **not** disable NTP or set `RTC in local TZ`. Do **not** “fix” the proxy to CET.

### Prove it in one minute

On the proxy:

```bash
date -u
date -u +%s
```

In Cloud Latest data, open any just-collected item and read **Last check** as a datetime (not only “1h ago”).

| Last check (absolute) | Meaning |
|---|---|
| Same second as `date -u` | proxy clock is in the payload; Cloud **ago** / server `now` is 1h fast, or the UI TZ is applied twice |
| Exactly 1h **behind** `date -u` | something subtracted 3600s on ingest (session TZ / CET). Cloud instance timezone and user profile timezone |
| 2h behind `date -u` | payload compared as Zurich local, or Cloud is UTC+2 vs UTC stored wrong |

Also: **User settings → Time zone** (not “System default” if that is CET). Cloud instance timezone if you have it. A host on this proxy with `system.localtime[utc]` / unixtime should match `date -u +%s` within a few seconds.

Zabbix scheduling intervals (`wd1-5h8-18`) follow the **proxy OS TZ**. UTC on this box means “h8” is 08:00 UTC = 10:00 CEST. That is independent of Latest-data ago. If you want schedules in Swiss civil time, set `Europe/Zurich` **after** the 1h ago question is closed — it will not close it.

The rest of this note is still true: `Timeout=30` is a bad poller default. It is **not** why every last-check is 1h 2s.

---

## What those “scripts” actually are

| Item | Interval | Item timeout | Work |
|---|---|---|---|
| `xiqse.nbi.health` | **2m** | `{$XIQSE.DATA.TIMEOUT}` = 30s | OAuth + `serverInfo` + engines |
| `xiqse.nbi.licenses` | **15m** | `{$XIQSE.LICENSE.TIMEOUT}` = 60s | Page `endSystems` (canary **4055** rows, 500/page) |
| `xiqse.nbi.pilot` | **15m** | 60s | Count `network.devices` `xiqLicenseState` (canary **563** devices, **320** Pilot) |

A 15-minute item that is **really** not checking for an hour missed four cycles (queue / timeout). If *every* item on the proxy shows the same 1h 2s, that is the clock section above — not this paragraph.

Cloud 7.0 SCRIPT items are executed by **synchronous pollers** (`StartPollers`). One check occupies **one** poller for the whole runtime (OAuth + every GraphQL page). They do **not** use `StartHTTPAgentPollers` or `StartSNMPPollers`.

Same poller pool also runs:

- **legacy SNMP** (plain OID, including stock EXOS `net.if.discovery` — not `walk[` / `get[`)
- simple checks, internal checks, SSH / Telnet, external checks
- FortiGate **SCRIPT** items (stock HTTP + Observability), when those templates are linked

Async pollers (`StartSNMPPollers`, `StartHTTPAgentPollers`, `StartAgentPollers`) only take `walk[`/`get[`, HTTP agent, and passive agent. Cato HTTP is async. Extreme SNMP that is still classic OID is **not**.

---

## Verdict

Two separate facts:

1. **Latest data “1h ago” on the whole proxy** (ICMP and SCRIPT the same age) is a **3600s clock/TZ offset**. The box is UTC + NTP. Do not chase GraphQL or `StartPollers` for that.
2. The conf is still a **partial** 7.0 tune: hybrid buffer, extra pingers, VMware, Cloud TLS, but **`Timeout=30`** with classic SNMP + SCRIPT on the same 30 sync pollers. That *will* starve SCRIPT items when the delayed queue is real (scattered ages, poller busy ~100%). It does not produce a uniform 1h 2s.

Confirm clock first (absolute Last check vs `date -u`). Confirm queue second. Then NBI.

---

## What is wrong (this conf)

Non-defaults and important defaults only. Lines left at comment-default are called out when they matter.

### 1. `Timeout=30` — this is the main bug

Range is 1–30; default is **3**. 30 is the ceiling.

This timeout is for **legacy SNMP**, agent, simple checks, IPC, talking to Cloud — **not** for SCRIPT item JS (item-level 30s/60s) and **not** for `walk[`/`get[` (frontend / proxy Timeouts tab).

Raising it does **not** make the NAC census more reliable. It makes every slow or dead classic-SNMP target hold a sync poller for up to **30 seconds**. Thirty pollers × 30s ≈ **one check per second** when the estate has timeouts (WAN, SNMPv3, unused iDRACs, closets). SCRIPT items sit in the delayed queue — ages **scatter**, they do not all freeze at 1h 2s. SNMP timeouts also look like a sick switch ([reference/extreme-switching-zabbix.md](../reference/extreme-switching-zabbix.md) — poller saturation).

**Set 4–5s** on this proxy (WAN, not a LAN-only collector). Do **not** keep 30. Slow walks belong on `walk[` item timeouts / Administration → Timeouts, not here.

Also check **Zabbix Cloud → Proxies → this proxy → Timeouts**. Frontend proxy timeouts override globals for types that use them. SCRIPT item timeout still wins when the YAML field is present — if a census is `Not supported: RangeError: execution timeout`, the item finished starting but not finishing (queue delay plus SE slowness can still blow 60s).

### 2. `StartPollers=30` with `StartSNMPPollers` and `StartPollersUnreachable` left at 1

| Process | This conf | Default | Who uses it |
|---|---|---|---|
| poller | **30** | 5 | SCRIPT, legacy SNMP, simple/internal/SSH |
| snmp poller | **1** (unset) | 1 | `walk[` / `get[` only |
| unreachable poller | **1** (unset) | 1 | hosts already marked unreachable |
| http agent poller | **1** (unset) | 1 | Forti HTTP, Cato, other HTTP agent |
| agent poller | **1** (unset) | 1 | **passive** agent (active agents do not) |
| preprocessor | **16** (unset, 7.0.6+ default) | 16 | dependent JSON (XIQ-SE has a lot) |

Bumping only `StartPollers` while `Timeout=30` just creates 30 processes that sleep on the network. Unreachable hosts keep burning regular pollers until `UnreachablePeriod` (45s), then **one** unreachable poller retries them at `Timeout=30`.

`StartPingers=10` is already a real tune (ICMP for the Swiss group). Leave it.

### 3. SQLite + 16M hybrid buffer

```
DBName=/var/lib/zabbix/zabbix_proxy.db
ProxyBufferMode=hybrid
ProxyMemoryBufferSize=16M
```

Hybrid is the right **mode**. 16M is not a size for this role. When the memory buffer fills, 7.0 hybrid **flushes to SQLite** and stays on disk until Cloud has uploaded everything. SQLite serializes writers. Housekeeping (default hourly) locks the same file.

Zabbix’s own proxy guidance: SQLite is for small proxies (ballpark NVPS under 1000). This host is the production poller for Extreme SNMP, VMware (`StartVMwareCollectors=5`, `VMwareCacheSize=512M`), XIQ-SE SCRIPT, and Forti HTTP. Measure `zabbix[requiredperformance]` / `zabbix[proxy_buffer,*]` before migrating the DB. First fix timeout + poller split + buffer size. If the buffer sits in **disk** mode or NVPS stays high after that, move the proxy DB to PostgreSQL (or MySQL) — do not grow SQLite.

`ProxyOfflineBuffer` default **1 hour**: if the Cloud session dies, local history older than 1h is dropped. That is upload retention, not a uniform “1h 2s ago” on live Latest data. Still raise it to **24**.

### 4. VMware on the same box as the network proxy

`StartVMwareCollectors=5` and **512M** VMware cache are a second estate. They do not share the SCRIPT poller queue, but they share CPU, RAM, and SQLite. If vSphere can live on another proxy later, do that. Do not drop these values blindly if VMware items are in production.

### 5. Housekeeping / logs / identity

| Setting | This conf | Problem |
|---|---|---|
| `LogFileSize=0` | on | log never rotates |
| `Hostname=` | commented | Cloud name must match `system.hostname` **exactly** (case). Set it explicitly. |
| `StartSNMPTrapper=0` | default | `SNMPTrapperFile` is set; traps are not collected. LM Netsight traps were never in scope for this symptom. |
| `Include=/etc/zabbix/zabbix_proxy.d/*.conf` | on | **cat the drop-ins**. A second file can override everything below. |

TLS (`TLSConnect=cert` + chain/cert/key) is correct for Zabbix Cloud. `CacheSize=256M` is a reasonable starting cache; confirm `zabbix[rcache,pfree]` stays comfortable. `LogSlowQueries=3000` is fine for catching SQLite stalls.

`StartHTTPPollers=1`, `StartODBCPollers=1`, `StartBrowserPollers=1` start unused workers if you have no web scenarios / ODBC / browser items. Optional: set them to **0** after you confirm.

---

## What is already fine

- Active proxy to `sensirion.zabbix.cloud` with cert TLS.
- `ProxyBufferMode=hybrid` (right 7.0 mode).
- `StartPingers=10` for a large ICMP set.
- `StatsAllowedIP=127.0.0.1` (local `zabbix_get` / `nc` stats).
- `FpingLocation` / `Fping6Location` under `/usr/bin`.
- Item-level SCRIPT timeouts on XIQ-SE (30s health, 60s census) — keep them. Do not lower them to “match” `Timeout=`.

---

## Change on the box (order)

1. **Read** `/etc/zabbix/zabbix_proxy.d/*.conf` so you do not fight an override.
2. Drop [`swiss-proxy-tuning.conf`](../reference/zabbix_proxy.d/swiss-proxy-tuning.conf) into that directory (or merge). **Do not** copy TLS paths or `Server=` from the snippet — those stay in the main file.
3. Set `Hostname=` to the Cloud proxy name if it is not already identical to `hostname`.
4. `systemctl restart zabbix-proxy` (buffer/poller counts are not runtime-reload).
5. Cloud UI: proxy **Timeouts** tab — SCRIPT / HTTP agent high enough for 60s census; SNMP walk timeouts for EXOS LLD stay on the **frontend**, not `Timeout=` in the file. Stock EXOS discovery `timeout` field stays **empty** ([notes/exos-if-lld-empty.md](exos-if-lld-empty.md)).
6. Re-measure. `xiqse.nbi.health` should move every ~2m; licenses / pilot every ~15m. Then look at Extreme SNMP queue — it should improve once classic SNMP is not stuck at 30s.

Restart in a change window. Hybrid flushes the 16M buffer to SQLite on stop; that is safe, just slow if the DB is already unhappy.

---

## Prove it (on `ch-sta-p-zabp02`)

Clock first, if every Latest-data age is the same ~1h:

```bash
date -u
date -u +%s
timedatectl
```

Then queue / process busy. Internal items need the proxy health template (or `zabbix_get` against a local agent). Stats on port 10051 also work because `StatsAllowedIP` includes localhost.

```bash
# delayed queue — the 1h SCRIPT symptom in one number
echo queue | nc -q1 127.0.0.1 10051

# 7.0 runtime (names vary slightly by package)
zabbix_proxy -R diaginfo=queue

# process busy: poller ~100% + snmp poller ~100% = this note
# (keys work if a local agent / proxy-health host exists)
zabbix_get -s 127.0.0.1 -k 'zabbix[process,poller,avg,busy]'
zabbix_get -s 127.0.0.1 -k 'zabbix[process,snmp poller,avg,busy]'
zabbix_get -s 127.0.0.1 -k 'zabbix[process,unreachable poller,avg,busy]'
zabbix_get -s 127.0.0.1 -k 'zabbix[process,http agent poller,avg,busy]'
zabbix_get -s 127.0.0.1 -k 'zabbix[process,vmware collector,avg,busy]'
zabbix_get -s 127.0.0.1 -k 'zabbix[queue]'
zabbix_get -s 127.0.0.1 -k 'zabbix[requiredperformance]'
zabbix_get -s 127.0.0.1 -k 'zabbix[proxy_buffer,buffer,pused]'
zabbix_get -s 127.0.0.1 -k 'zabbix[proxy_buffer,state,current]'
zabbix_get -s 127.0.0.1 -k 'zabbix[rcache,pfree]'

grep -E 'queue|slow query|script|hybrid|buffer' /var/log/zabbix/zabbix_proxy.log | tail -n 50
ps -o pid,pcpu,pmem,comm -C zabbix_proxy
```

| Reading | Meaning |
|---|---|
| every item the same ~1h 2s | clock/TZ offset — see the first section |
| `zabbix[queue]` (or delayed more than 10m) large | items not scheduled on time — SCRIPT last-check hours late **and ages differ** |
| poller busy ~100% | `Timeout=30` and/or too much classic SNMP + SCRIPT on sync pollers |
| snmp poller busy ~100% | raise `StartSNMPPollers` (walk/get only) |
| `proxy_buffer state` = disk / pused high | 16M too small or Cloud upload slow — raise buffer; if it sticks, SQLite is the next limit |
| SCRIPT item **Not supported** `RangeError: execution timeout` | census started but hit 30s/60s — NBI slow **or** started after waiting in queue |
| health 2m fresh, licenses 1h stale only | licenses SCRIPT is the long one; still a poller-queue / 60s-timeout problem, not “Pilot template off” |

Do not debug ENSA GraphQL until **queue is quiet**. A laptop curl to `:8443` does not prove the proxy had a free poller.

---

## After this is quiet

- Keep XIQ-SE SCRIPT timeouts at 30s / 60s. Do not turn the census into an external script.
- If `endSystems` paging still burns 60s after the queue is gone, that is an NBI size problem ([notes/xiq-se-nbi.md](xiq-se-nbi.md)) — `endSystemsForEngines` / lower page size — not another `Timeout=` bump.
- Split VMware off this proxy if collectors stay busy.
- PostgreSQL for the proxy DB only after NVPS / disk-mode buffer is still bad with 256M hybrid.
