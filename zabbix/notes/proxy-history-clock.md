# Proxy history clock −1h (`ch-sta-p-zabp02` → Cloud)

Operator page: [07-extreme-control.md](../07-extreme-control.md).  
This is **not** NBI, Cloud XIQ credentials, JavaScript, or poller starvation. Do not treat it as a second policy.

**Symptom (live 2026-09-02):** Latest data **moves**. Every new point from zabp02 is stored with `lastclock ≈ now − 1h`. The age resets to ~1h when a newer payload arrives. `nodata(15m)` / `nodata(20m)` stay PROBLEM because they use **history `lastclock`**, not “did a value arrive”.

---

## Verdict

**zabp02 stamps or delivers all history ~1h late.** SCRIPT, SIMPLE TCP, ICMP, and SNMP on that proxy share the same offset. The XIQ JavaScript is innocent. Peer **zabp01** does not show a fixed 1h gap.

Hosts sit in **proxy group** `proxy_groupid=1`, `monitored_by=2`, **`assigned_proxyid=2`** (zabp02) — including `ch-sta-p-ensa01` and `CH-NKN-G08-L02-ACPO12`. Not a group-selection mix-up: assignment is zabp02.

---

## What is proven

| Check | Result |
|---|---|
| SCRIPT payloads | `xiqse.nbi.health` / `xiq.cloud.account`: `state=0`, `ok=1` |
| Execute now | `task.type=6` `status=3` on zabp02 |
| Proxy lastaccess vs production epoch | **1 second** — Cloud heartbeat UTC is correct |
| Host NTP | zabp02 and zabp01 `Etc/UTC`, synchronized |
| Process `TZ` | **none**. Only `CONFFILE=`. No `/etc/default/zabbix-proxy`, no drop-ins |
| Package | **7.0.27** (`e4b2990bfed`, 2026-06-02) |
| Hybrid buffer | empty at inspect; `DataSenderFrequency` default 1s |

### Split (production 2026-09-02 **10:47:38 UTC**)

All rows `assigned_proxyid=2`. Last history clocks cluster at **09:42:56–57 UTC** (~**1h 04m 42s** behind).

| Host / item | Type | Interval | Last clock UTC | Age |
|---|---|---|---|---|
| `ch-sta-p-ensa01` `net.tcp.service[tcp,{$XIQSE.API.FQDN},{$XIQSE.API.PORT}]` | SIMPLE | 1m | 09:42:56 | 1h 04m 42s |
| `CH-NKN-G08-L02-ACPO12` `icmpping` | ICMP | 1m | 09:42:56 | 1h 04m 42s |
| `CH-NKN-G08-L02-ACPO12` `net.if.status[ifOperStatus.10]` | SNMP | 1m | 09:42:56 | 1h 04m 42s |
| Several other ICMP hosts on zabp02 | ICMP | 1m | 09:42:57 | 1h 04m 41s |
| SCRIPT masters (earlier API) | SCRIPT | 2m / 5m | ~now−65–68m | same class |

**zabp01** ICMP sample at the same query: **10:37:20 UTC** (~10m behind a 1m item). Late vs interval, **not** a 1h floor.

The extra ~5m on zabp02 on top of 1h is in the same ballpark as zabp01’s lag. The **discriminant is the extra hour**, only on zabp02.

---

## What that means

`lastaccess` is Cloud’s receive time. Item `clock` is what arrives on history. Those disagree by ~1h **only for zabp02**, for **every item type**. A global Cloud clock bug would also move zabp01 and `lastaccess`. A SCRIPT bug would spare ICMP/SNMP.

Remaining: zabp02 **runtime / history path** (stamp or transport) or Cloud **handling history from this proxy**. Process TZ is ruled out. Restart is **not** required to conclude that; ops have declined it.

**Not in 7.0.28–7.0.30 release notes.** Latest 7.0 is **7.0.30**. 7.0.27 advertised no functional changes. Later patches do **not** list a proxy `lastclock` −1h fix or “proxy stopped receiving config”. Closest noise: ZBX-27698 (Clock **widget** used browser TZ — frontend only; API `lastclock` would not move) and ZBX-27495 (agent history upload delay). ZBX-27665 is remote commands on a **proxy group**, not history time.

If Cloud UI says a proxy is **outdated** (`configuration update is disabled… only data collection`), that is a **major-version** mismatch (7.0 vs 7.2/7.4), not 7.0.27 vs 7.0.30. Same-minor 7.0.x still gets config.

**zabp01 completes Execute now for the same ENSA itemids** (sqlite 2026-09-02 on `ch-sta-p-zabp01`). `task.type=6` `status=3` (`done`). `ttl=3600` is the **task expiry**, not the Latest-data 1h floor.

| taskid | clock UTC | itemid |
|---|---|---|
| 3344 / 3341 / 3340 | 10:57:28 | 523738 / 519957 / 519956 |
| 3298 | 10:57:19 | 519957 |
| 3293 / 3290 / 3289 | 10:57:07 | 523738 / 519957 / 519956 |
| 3247 / 3246 / 3245 | 10:56:23 | 519956 / 523738 / 519957 |
| 3243 / 3240 / 3239 | 10:54:53 | 523738 / 519957 / 519956 |
| 3188 / 3185 / 3184 | 08:15:04 | same three |

Cloud is delivering check-now to **both** group members. That does **not** mean zabp01 is the assigned collector (`assigned_proxyid` is still 2). Re-query `items` on zabp01 for those ids: rows present = group config sync; rows absent + tasks `done` = task fan-out without local items. Dual SCRIPT execution would hit NBI twice; it still does **not** stamp zabp02 history −1h. Compare the same `clock` values on zabp02 `task`/`task_check_now`.

September in CH is **CEST (UTC+2)**. A flat **1h** is UTC vs **CET / UTC+1**, not Zurich vs UTC — but with no `TZ=` on the process, that conversion is not on the box we can see. Take it to Cloud with 7.0.27 + the table above.

---

## Ops (no template change, no restart)

- Ack **XIQ-SE: no NBI data for 15m** and **ExtremeCloud IQ: no API data for 20m** as zabp02 clock, not SE/API down.
- Do **not** change GraphQL, widen `nodata` to 75m, or chase `Timeout=` for this.
- Do **not** stop the proxy to sqlite `proxy_history` (locks).
- Optional: one-shot `log_level_increase` on poller + data sender around Execute now, then decrease — still no restart.
- **Zabbix Cloud ticket:** zabp02 7.0.27; `lastaccess` correct; all item types `lastclock` ~now−1h; zabp01 not; no process `TZ`.

Restart later only if Cloud asks, or to test a stuck process clock. SQLite config survives.

---

## Template

`nodata(/XIQ-SE Observability/xiqse.nbi.health,15m)` stays the watcher **once zabp02 `lastclock` matches `lastaccess`**. Until then it is a false Average for every host on that proxy that uses `nodata` inside an hour.
