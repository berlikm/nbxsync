# IIS vs stock Zabbix

Question: does [windows_exporter `iis`](https://github.com/prometheus-community/windows_exporter/blob/master/docs/collector.iis.md) need a custom template, like AD/DNS/DHCP?

**Answer: stock [IIS by Zabbix agent](https://git.zabbix.com/projects/ZBX/repos/zabbix/browse/templates/app/iis_agent?at=refs%2Fheads%2Frelease%2F7.0) for W3SVC / WAS / port / app pools. HTTPS certificates are a thin companion — [IIS Observability](../templates/iis_observability/).** Cloud already has stock IIS. Do not scrape the exporter. Do not clone stock IIS. The remaining gap is **linking both** on the couple of IIS hosts — zerotouch does not assign them today (no IIS role).

These are **not** Domain Controllers. OS still comes from **Windows by Zabbix agent**. Stock IIS + this companion sit next to it, same pattern as MSSQL / GitLab.

---

## What the exporter is

`collector.iis` is **off by default**. Perflib: `Web Service` (per **site**), `APP_POOL_WAS`, worker-process caches, HTTP.sys queue. No alerting examples. Site/app include/exclude regexes.

Zabbix agent already reads those objects as `perf_counter_en["\Web Service(…)\…"]` and `perf_counter_en["\APP_POOL_WAS({#APPPOOL})\…"]`. Stock does that.

---

## What stock 7.0 already covers

Template **IIS by Zabbix agent** (`templates/app/iis_agent`). Needs Windows feature **IIS Management Scripts and Tools** (`root\webAdministration` WMI for app-pool LLD).

| Symptom / cause | Stock | Exporter |
|---|---|---|
| W3SVC / WAS not running | **High** `service.info[W3SVC]` / `[WAS]` | not a first-class alert (would be `service` collector) |
| HTTP(S) port down | **Average** `net.tcp.service[{$IIS.SERVICE},,{$IIS.PORT}]` | no |
| App pool not Running | **High** LLD `APP_POOL_WAS` state ≠ 3 | `windows_iis_current_application_pool_state` |
| App pool request queue | Warning if `{$IIS.QUEUE.MAX.WARN}` is set | `windows_iis_http_requests_current_queue_size` (server-wide) |
| Bytes / connections / method rates / 404 / 423 | `_Total` Web Service | same counters, **per `site`** |
| App pool recycles / uptime | Info | recycles + worker failures |
| Per-site LLD | **no** — `_Total` only | `site` label |
| Per-worker cache / WebSocket / errors by status | **no** | lots of `app`,`pid` series |

Stock is the **better** ops template: it pages W3SVC/WAS/port/pool-down. The exporter dumps site/worker series with no alerts.

Skip exporter extras unless a ticket names a **site** (not `_Total`) or worker-process crashes. Then a thin LLD on `\Web Service` instances — still do not clone the official template.

`$IIS.QUEUE.MAX.WARN` defaults **empty** — the queue trigger does not fire until you set it.

---

## Certificate expiry — companion, not a FQDN list

Stock **IIS by Zabbix agent** does not inspect TLS. `{$IIS.SERVICE}` / `{$IIS.PORT}` default **http/80** — a TCP ping, not a handshake. No `web.certificate.get`, no binding LLD, no days-to-expiry. [windows_exporter `iis`](https://github.com/prometheus-community/windows_exporter/blob/master/docs/collector.iis.md) has no cert metrics either.

Stock **Website certificate by Zabbix agent 2** is one `{$CERT.WEBSITE.HOSTNAME}` per host on **7.0**. We do **not** have that FQDN list, and one name per box cannot cover several SNI bindings.

**IIS Observability** (`templates/iis_observability/`) sits **next to** stock IIS. It does not nest it. An HTTPS `<binding>` in `applicationHost.config` is treated as “certificate applied on the binding.” HTTP-only boxes discover nothing and stay at binding count 0.

| Thing | Companion |
|---|---|
| Who has a cert | LLD `https` bindings from `{$IIS.CONFIG.PATH}` (default `C:\Windows\System32\inetsrv\config\applicationHost.config`) |
| Handshake | Agent 2 `web.certificate.get["{#IIS.SNI}","{#IIS.PORT}","{#IIS.CONNECT}"]` |
| Connect | Binding IP, or `127.0.0.1` when the IP is `*` — **no public DNS** |
| SNI | Host header. Empty host = default SSL binding; `{#IIS.SNI}` is the connect address |
| Expires soon | Warning — `(not_after - now())/86400 < {$IIS.CERT.EXPIRY.WARN}` default **30** (matches [06](../06-network-vms.md)) |
| Invalid / wrong name | **High** only when `{#IIS.HAS_HOST}=1` (empty host header skips hostname-mismatch) |

Needs **Zabbix agent 2** (WebCertificate plugin). Classic agent cannot. Agent 2 still serves Windows + IIS `perf_counter_en` — swap those boxes to Agent 2 rather than a second agent.

Do not also link **Website certificate** on the same IIS sites (duplicate handshakes, and 7.0 still needs a handwritten hostname). Use that stock template only for a **known** non-IIS name. Do not WMI-scrape the Windows cert store — the handshake is the symptom.

Tests (no live IIS): `python3 scripts/test_iis_observability.py`.

---

## Do not

| Source | Why not |
|---|---|
| windows_exporter on IIS boxes | Second agent; stock already uses the same Perflib objects |
| Clone **IIS by Zabbix agent** | Companion is cert-only; stock already pages W3SVC/WAS/pools |
| Link **Website certificate by Zabbix agent 2** for IIS sites | Needs a FQDN list; 7.0 is one hostname per host |
| Fork **Windows by Zabbix agent** | Link IIS beside it |
| Community “Template Microsoft IIS” XML from random blogs | Use Cloud **IIS by Zabbix agent** 7.0 |

`service.info[W3SVC]` on the IIS template is a different key from Windows LLD `service.info["W3SVC",state]`. Both can collect. If Windows Average on W3SVC is noisy next to IIS High, exclude `W3SVC`/`WAS` with `{$SERVICE.NAME.NOT_MATCHES}` **on those hosts** — do not change the OS template fleet-wide.

---

## Assignment (the actual gap)

A couple of hosts → assign **IIS by Zabbix agent** **and** **IIS Observability** on the **Device/VM** in NetBox ([configuration.md](../../docs/netbox-zabbix/configuration.md) §7: one-offs on the object, not a new role). If a dedicated IIS role exists, put both on the role instead.

Not in zerotouch today (no IIS role in step 7). Do not invent a role for two boxes. Import the companion YAML before linking it.

Macros on the host if not :80/http:

```
{$IIS.PORT} =
{$IIS.SERVICE} = https
{$IIS.QUEUE.MAX.WARN} =
{$IIS.APPPOOL.NOT_MATCHES} =
```

Port check depends on W3SVC. App-pool High depends on W3SVC. Do not also page host ICMP for the same outage (Windows / ICMP already cover the box). Cert expiry is the companion (Agent 2), not stock IIS.

---

## Cutover

Not a switch/AP item. Companion YAML is built; import + Device link is post-cutover / whenever those hosts are in the onboarding wave. Canary still needs a live IIS box (Agent 2 handshake).
