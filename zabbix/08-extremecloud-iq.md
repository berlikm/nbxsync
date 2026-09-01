# ExtremeCloud IQ (Pilot / VIQ)

The **cloud tenant** (VIQ) for CUID `sApsGq3wp`: entitlements, VIQ backup, tenant health. Same bar as [07](07-extreme-control.md) / [04](04-cato.md). Not a switch, not Site Engine NBI, not IQ Engine SNMP.

One Site Engine, one CUID → **same Zabbix host as `ch-sta-p-ensa01`**. A second template, not a second host, so Licenses live in one Latest data / one Health board. Do **not** fold `api.extremecloudiq.com` into the NBI SCRIPT. Do **not** invent a Cato-style `xiq-cloud-*` host unless a second Site Engine appears.

This page is the **target contract**. YAML is not built. Refresh later with `configure_nbxsync_network.py --apply-xiq-cloud` (import companion, link on the Site Engine, no HostSync of switches). Analysis: [notes/xiq-cloud.md](notes/xiq-cloud.md).

---

## Observability

| Rule | Here |
|---|---|
| Page **symptoms** | Nothing 03:00. Cloud down does not take RADIUS or switch SNMP with it |
| **Ticket** (Average) | Cloud API / token dead (ops blind to onboarding and Portal seats). VIQ **expired** or VHM not `ACTIVE`. Last CONFIG backup older than `{$XIQ.CLOUD.BACKUP.MAX}` |
| **Graph** / next day | Portal purchased / activated / available / expire (Pilot, NAC, Navigator, CoPilot). Cloud managed vs connected census. Token TTL |
| One incident | Cloud API tickets do not also fire SE NBI. Cloud “disconnected” census does not also fire 01/02 ICMP. Pilot remaining is Cloud `available`, never `581 − 320` |
| Never silent | API nodata; zero license rows while `licenses:r` should see the Portal pools; backup grid empty |
| Collect first | Unmanaged / cloud-disconnected counts. Copilot. HIQ. Per-SKU exhaust until `license_type` is canaried |
| One `icmpping` | None. SaaS. Do not ping `extremecloudiq.com` |
| Host dashboard | Same SE **Health**: NAC used from 07; Pilot **have / consume / available** from Cloud (APs included). SE 320 is not the Pilot used tile |

Disaster is still campus auth / site — not this template.

---

## What we alert

| Thing | Alert | Sev | Notes |
|---|---|---|---|
| Cloud API unexpected / nodata | yes | Average | Bearer token or `api.extremecloudiq.com`. Onboarding and Portal seats go dark. RADIUS still works |
| API token expires `< {$XIQ.CLOUD.TOKEN.WARN}` | yes | Warning | `GET /auth/apitoken/info`. Dayside rotate |
| VIQ `expired=true` | yes | Average | Connected-mode devices go unmanaged. Not a switch ICMP |
| VHM `current_status` ≠ `ACTIVE_STATUS` | yes | Average | Tenant suspended |
| Last CONFIG backup age ≥ `{$XIQ.CLOUD.BACKUP.MAX}` | yes | Average | VIQ is the cloud config brain. Default 8d. `GET /backup/history/grid` |
| Pilot / Navigator **Cloud** available = 0 | yes | Warning | Cannot onboard. From VIQ `licenses[].available`, not `{$XIQ.PILOT.TOTAL}` |
| SKU expire `< {$XIQ.CLOUD.EXPIRY.WARN}` | yes | Warning | Portal 99d / 152d class of problem |
| NAC Cloud available = 0 | **no** until `/nac-entitlements/stats` is canaried | Warning | May not be on `GET /account/viq` |
| Cloud disconnected / unmanaged census | **no** until baseline | — | Items only. 01/02 already page the box |
| Per-device Cloud LLD | **no** | — | 01/02 own the device |
| Cloud IQ alert inbox | **no** | — | Do not alert on their alerts |
| `POST /account/viq/:backup` / reset / unmanage | **no** | — | Mutations |

Do **not** alert on: floor plans, clients, CoPilot anomalies, HIQ org tree, the same Pilot exhaust as 07 remaining, `581 − 320`.

---

## Licenses in one place

One host, **split by pool**. Do not subtract across columns.

| Pool | Have | Consume | Why SE 320 is not Pilot used |
|---|---|---|---|
| **NAC** | Cloud / CG total (Portal **3000**) | **SE** 24h unique MACs | NAC seats are authentications, not Cloud devices |
| **Pilot** | Cloud `devices` (Portal **581**) | **Cloud** `activated` (Portal **578**) | IQ Engine **APs** consume Pilot in Cloud. SE `network.devices` `XIQ_PILOT` **320** is switches + Control engines in Site Engine only |
| **Navigator** | Cloud | Cloud `activated` | Same as Pilot: SE inventory is a subset |

Remaining is Cloud `available` (Pilot **3**). Never `581 − 320`. 07 `xiqse.pilot.used` stays as “SE-managed Pilot devices” (graph), not the billable consume tile once this companion is live.

---

## Scope

| Object | In | Out |
|---|---|---|
| Site Engine host `ch-sta-p-ensa01` | Companion **ExtremeCloud IQ by HTTP** next to **XIQ-SE Observability** | Cloud REST inside `collect_health.js` |
| CUID / VIQ | `GET /account/viq`, `/account/vhm/status`, `/backup/history/grid`, `/auth/apitoken/info`, `/devices/stats` | `GET /devices` page-all, `/locations/*`, `/users` |
| Switches / APs | Census counts only | Hosts, SNMP, ICMP, Cloud “disconnected” as a page |
| Control engines | — | 07 |

Auth: long-lived `POST /auth/apitoken` (permission `licenses:r` + account/backup/device read). Secret on nbxSync CG, assigned to the Site Engine platform — not a Zabbix host macro typed on `ch-sta-p-ensa01`, not SE OAuth.

---

## Ops

- Connected mode: every Site Engine shares this pool. A second SE later still uses **this** companion (link it there too) — do not clone the CUID.
- Air-gap SE would not use this template.
- TLS verify on. Do not `POST` backup from Zabbix.
- Canary before YAML: one token, dump `GET /account/viq` `license_type` values and whether NAC 3000 is in `licenses[]` or only Platform ONE `/nac-entitlements/stats`.

---

## Dependencies

```
SKU exhaust / backup stale / VHM  →  Cloud API Average
Cloud API Average  does not depend on  SE NBI / 8443
SE NBI Average  does not depend on  Cloud API
Cloud disconnected census  does not ticket  (01/02 ICMP owns the box)
```

---

## Watch the watcher

| Check | Why |
|---|---|
| Cloud API nodata | Token, proxy egress, Extreme outage |
| Zero license rows | Token missing `licenses:r`, or Portal unlink |
| Backup grid empty | Backups never run — ticket is the stale-age trigger once a first backup exists; until then collect |
| Proxy last-seen | already in 01 |

---

## Templates

Do not clone stock. There is no official ExtremeCloud IQ Zabbix template.

| Template | Where |
|---|---|
| **ExtremeCloud IQ by HTTP** | Linked on the **Site Engine** host. SCRIPT HTTPS to `{$XIQ.CLOUD.API.URL}` default `https://api.extremecloudiq.com`. Does not nest ICMP. Does not nest XIQ-SE Observability |

```
{$XIQ.CLOUD.API.URL}       = https://api.extremecloudiq.com
{$XIQ.CLOUD.API.TOKEN}     = SECRET_TEXT (CG, not YAML)
{$XIQ.CLOUD.BACKUP.MAX}    = 691200   (8d elapsed)
{$XIQ.CLOUD.TOKEN.WARN}    = 14d
{$XIQ.CLOUD.EXPIRY.WARN}   = 30d
```

---

## Later

NAC entitlements API if `viq` omits `XIQ-NAC-S`. Copilot. HIQ. Auto-fill 07 `{$XIQ.*.TOTAL}` from Cloud `devices` (only after canary proves SKU map). Second SE. Platform ONE `cloudapi.extremecloudiq.com/subscription/v1`.
