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
| Proxy package | **7.0.27** (`e4b2990bfed`, compiled 2026-06-02). 7.0.27 has no advertised clock/history change |
| `/etc/default/zabbix-proxy` | **missing**. Unit `EnvironmentFile=-/etc/default/zabbix-proxy` — the `-` means optional; this is normal, not a TZ override |
| Process environ (MainPID) | **no `TZ=`**. `Environment=CONFFILE=/etc/zabbix/zabbix_proxy.conf` only. `DropInPaths=` empty |

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

**Done 2026-09-02:** `zabbix_proxy -V` → 7.0.27. `/etc/default/zabbix-proxy` does not exist. MainPID environ has **no `TZ=`**. **Do not restart** the proxy until ops agree — it is not required for the next checks.

### No restart

Process TZ is already checked (empty). Next is **SCRIPT vs the rest** (API or Latest data). Same host `ch-sta-p-ensa01`, same proxy:

| Item | If lastclock is ~now | If lastclock is now−1h |
|---|---|---|
| `xiqse.nbi.health` / `xiq.cloud.account` | already know: −1h | — |
| `net.tcp.service[tcp,{$XIQSE.API.FQDN},{$XIQSE.API.PORT}]` (SIMPLE, 1m) | SCRIPT-only stamp | whole host |
| Any switch ICMP/SNMP on zabp02 | SCRIPT-only | **whole proxy** history stamp |

Whole-proxy −1h → Cloud ticket with 7.0.27 + the epoch table (heartbeat `lastaccess` correct, history `clock` not). SCRIPT-only → still Cloud/proxy, but the poller/JS path, not SQLite sender.

Optional, still no restart: raise poller + data-sender log for **one** Execute now, then put it back.

```bash
sudo zabbix_proxy -R log_level_increase=poller
sudo zabbix_proxy -R log_level_increase=poller
sudo zabbix_proxy -R 'log_level_increase=data sender'
sudo zabbix_proxy -R 'log_level_increase=data sender'
# Execute now on 519957, wait ~30s, grep the log for wall time vs the new lastclock
sudo zabbix_proxy -R log_level_decrease=poller
sudo zabbix_proxy -R log_level_decrease=poller
sudo zabbix_proxy -R 'log_level_decrease=data sender'
sudo zabbix_proxy -R 'log_level_decrease=data sender'
```

Do **not** stop the proxy only to `sqlite3` `proxy_history` (it locks). Do **not** widen `nodata(...,15m)` to 75m.

### Restart (deferred)

A restart only tests “stuck process clock”. SQLite config stays. Skip until ops want it. If TZ in `environ` is already empty and SIMPLE/ICMP on zabp02 are also −1h, restart will not teach more than a Cloud ticket.

---

## Template

`nodata(/XIQ-SE Observability/xiqse.nbi.health,15m)` is still the right watcher **once `lastclock` is current**. While it is 1h slow, that ticket is a **false Average**. Same for Cloud XIQ `nodata` 20m. Close/ack as clock, not as SE/API down, until zabp02 history clocks match `lastaccess`.
