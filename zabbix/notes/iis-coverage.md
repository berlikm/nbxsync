# IIS vs stock Zabbix

Question: does [windows_exporter `iis`](https://github.com/prometheus-community/windows_exporter/blob/master/docs/collector.iis.md) need a custom template, like AD/DNS/DHCP?

**Answer: no. Use stock [IIS by Zabbix agent](https://git.zabbix.com/projects/ZBX/repos/zabbix/browse/templates/app/iis_agent?at=refs%2Fheads%2Frelease%2F7.0) (7.0).** Cloud already has it. Do not scrape the exporter. Do not write a companion. The gap is **linking the template** on the couple of IIS hosts — zerotouch does not assign it today.

These are **not** Domain Controllers. OS still comes from **Windows by Zabbix agent**. IIS sits next to it, same pattern as MSSQL / GitLab.

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

## Do not

| Source | Why not |
|---|---|
| windows_exporter on IIS boxes | Second agent; stock already uses the same Perflib objects |
| Custom “IIS Observability” YAML | Official template exists — principle 7 |
| Fork **Windows by Zabbix agent** | Link IIS beside it |
| Community “Template Microsoft IIS” XML from random blogs | Use Cloud **IIS by Zabbix agent** 7.0 |

`service.info[W3SVC]` on the IIS template is a different key from Windows LLD `service.info["W3SVC",state]`. Both can collect. If Windows Average on W3SVC is noisy next to IIS High, exclude `W3SVC`/`WAS` with `{$SERVICE.NAME.NOT_MATCHES}` **on those hosts** — do not change the OS template fleet-wide.

---

## Assignment (the actual gap)

A couple of hosts → assign **IIS by Zabbix agent** on the **Device/VM** in NetBox ([configuration.md](../../docs/netbox-zabbix/configuration.md) §7: one-offs on the object, not a new role). If a dedicated IIS role exists, put the assignment on the role instead.

Not in zerotouch today (no IIS role in step 7). Do not invent a role for two boxes.

Macros on the host if not :80/http:

```
{$IIS.PORT} =
{$IIS.SERVICE} = https
{$IIS.QUEUE.MAX.WARN} =
{$IIS.APPPOOL.NOT_MATCHES} =
```

Port check depends on W3SVC. App-pool High depends on W3SVC. Do not also page host ICMP for the same outage (Windows / ICMP already cover the box).

---

## Cutover

Not a switch/AP item. Template exists; linking is post-cutover / whenever those hosts are in the onboarding wave.
