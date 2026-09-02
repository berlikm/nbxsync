# Proxy history clock −1h (`ch-sta-p-zabp02` → Cloud)

Operator page: [07-extreme-control.md](../07-extreme-control.md).  
This is **not** NBI, Cloud XIQ credentials, or poller starvation. Do not treat it as a second policy.

**Symptom (live 2026-09-02):** `ch-sta-p-ensa01` SCRIPT masters keep producing new `ok=1` JSON. Latest data **moves**. Every new point is stored with `lastclock ≈ now − 1h`. The “age” resets to ~1h when a newer payload arrives. That keeps these Average tickets open:

| Trigger | Expression | Why it stays PROBLEM |
|---|---|---|
| XIQ-SE: no NBI data for 15m | `nodata(...,15m)` on `xiqse.nbi.health` | `nodata` uses **history `lastclock`**, not “did a value arrive” |
| ExtremeCloud IQ: no API data for 20m | `nodata(...,20m)` on `xiq.cloud.account` | same |

JavaScript cannot set Zabbix history time. Changing the SCRIPT is the wrong first fix.

---

## What is proven

| Check | Result |
|---|---|
| Item state | `xiqse.nbi.health` (519957, 2m) and `xiq.cloud.account` (523738, 5m): `state=0`, `error=""`, payloads `{"ok":1,"error":""}` |
| Host | `ch-sta-p-ensa01` `hostid=14450`, `monitored_by=1`, **`proxyid=2` = zabp02**, not a group, not maintenance |
| zabp01 cache | those itemids **absent** — not a second collector |
| Execute now | `task.type=6` `status=3` (done) on zabp02 |
| Proxy lastaccess vs production epoch | **1 second** (`1788337928` vs `1788337929`) — Cloud and the proxy heartbeat agree on UTC |
| Host NTP | zabp02 and zabp01 `Etc/UTC`, synchronized |
| Hybrid buffer at inspect | `Items:0 values:0` — not a 1h sender backlog |
| `DataSenderFrequency` | comment-default 1s; no `zabbix_proxy.d` override |

API comparison (production epoch `1788343044` = 2026-09-02 **09:57:24 UTC**):

| Item | `lastclock` | UTC | Behind |
|---|---|---|---|
| `xiqse.nbi.health` | 1788339117 | 08:51:57 | **65m 27s** |
| `xiq.cloud.account` | 1788338939 | 08:48:59 | **68m 25s** |

So: Cloud **stores** the values with a stale `clock`. Heartbeat `lastaccess` is **not** stale. OS `timedatectl` is **not** stale. Collection is **not** stopped.

---

## What that means

`lastaccess` is stamped when Cloud hears the proxy. Item `clock` is the field the **proxy puts on history**. Those two disagree by ~1h. A global “Cloud clock is wrong” would move **both**. A dead poller would stop new values. A 1h `DataSenderFrequency` is not configured.

Remaining causes, in order:

1. **`zabbix_proxy` on zabp02** stamps SCRIPT (or all) history with an internal/TZ offset while `time()` for the heartbeat is correct. Check the **process** environment, not only `timedatectl`.
2. History rewrite on the Cloud side for this proxy. Possible after (1) is clean — take `zabbix_proxy -V` to support.

September in CH is **CEST (UTC+2)**. A flat **1h** is UTC vs **CET / UTC+1**, not Zurich vs UTC.

---

## Do this on zabp02 (no template change)

```bash
zabbix_proxy -V
rpm -q zabbix-proxy-sqlite3 2>/dev/null || dpkg-query -W zabbix-proxy-sqlite3

sudo cat /etc/default/zabbix-proxy
# systemd unit EnvironmentFile=-/etc/default/zabbix-proxy — TZ= here would not show in timedatectl

tr '\0' '\n' < /proc/$(pidof zabbix_proxy | awk '{print $1}')/environ | grep -E '^TZ=|^TZDIR='

date -u
date -u +%s
```

If `TZ=` is `CET`, `MET`, or anything other than empty / `UTC` / `Etc/UTC`, that is the first thing to clear, then restart.

A **controlled `systemctl restart zabbix-proxy`** is the local test that the process held a stale clock. Short gap; SQLite config stays. Then compare one Execute-now `lastclock` to `date -u +%s` (must be seconds, not ~3600).

If after restart + `TZ` clean the API `lastclock` is still `now-3600`, escalate to **Zabbix Cloud** with the epoch table above. Do not raise SCRIPT timeouts or rewrite GraphQL for this.

Do **not** stop the proxy only to `sqlite3` `proxy_history` (it locks). Do **not** widen `nodata(...,15m)` to 75m — that papers over the clock and delays a real NBI death by an hour.

---

## Template

`nodata(/XIQ-SE Observability/xiqse.nbi.health,15m)` is still the right watcher **once `lastclock` is current**. While it is 1h slow, that ticket is a **false Average**. Same for Cloud XIQ `nodata` 20m. Close/ack as clock, not as SE/API down, until zabp02 history clocks match `lastaccess`.
