# Cato — Zabbix monitoring

**Status:** production account collector live; Socket ICMP rollout held at 0/21.<br>
**Owner:** Network monitoring
**Depends on:** NetBox Socket inventory, nbxSync Agent Monitoring inheritance, and the Cato API token.

Cato is an overlay monitoring domain. Keep it separate from Extreme/Fortinet
underlay health and ISP-circuit inventory: one event can affect all three, but
they are distinct evidence and must not be collapsed into one alert.

## Scope and host model

| Object | Zabbix ownership | Monitoring path |
|---|---|---|
| 21 active NetBox `Sd Wan Socket` devices | nbxSync | One ordinary Zabbix host per Socket, with its NetBox primary IPv4 and inherited stock `ICMP Ping` only. |
| Cato account `964` (override with `NBX_CATO_ACCOUNT_ID`) | `configure_nbxsync_network.py --apply-cato` | One interface-free host, `cato-account-964`, linked only to `Cato Networks by HTTP`. |
| Cato `IPSEC_V2` Azure sites | None in this rollout | Explicitly out of scope. |

The account collector discovers only Cato sites whose `info.connType` matches
`{$CATO.SITE.CONN_TYPE.MATCHES}=^SOCKET_`. It does not create Socket hosts,
link an ICMP template to a role, or poll Socket management IPs. This keeps one
`icmpping` source per NetBox device and preserves the distinction between
Socket reachability and Cato overlay state.

Do **not** attach this HTTP template to NetBox Socket devices. Account-scoped
`accountMetrics` with `groupDevices: true` is mandatory for a multi-site
account; per-Socket HTTP would blow Cato's 15/minute metrics budget.

Live schema reconnaissance for account `964` found 13 API sites: 11
`SOCKET_*` sites with 21 nonblank Socket serials matching the 21 NetBox devices,
and two `IPSEC_V2` Azure sites excluded here. Expected Cato discoveries are 11
Socket sites, 21 physical Sockets, 33 Socket WAN tunnels, and 17 unique
Socket-site/interface SLA rows. Snapshot WAN is per-Socket; SLA rows are
HA-merged (`groupDevices: true`). 33 vs 17 is expected, not a discovery bug.
USB modem ports/tunnels are excluded from WAN, port, and SLA discovery (this
estate does not use them). If Health → Census WAN drops below 33 after apply,
the new count is the Ethernet/LTE/ALT census — update `{$CATO.WAN.EXPECTED}`.

## Data path

| Master item | API query | Interval | Retention | Purpose |
|---|---|---:|---:|---|
| `cato.account.snapshot` | `accountSnapshot` including `degradedStatus` and `interfacesLinkState` | 1m | 1d | Site, Socket, WAN, HA, CMA Degraded, and physical port state. |
| `cato.account.metrics` | `accountMetrics` with `timeFrame: "last.PT5M"`, `groupDevices: true`, `groupInterfaces: false`, `metrics(toRate: true)` | 5m | 1d | Overlay SLA, last-mile loss/latency, discards, bandwidth. |

There is no third HTTP master. `socketPortMetrics` (Socket CPU) is a different
shape and a later pass: CMA treats CPU >90% as a cause of overlay loss, not a
Health tile on this collector.

Both masters are HTTP-agent `POST` requests to
`https://api.catonetworks.com/api/v1/graphql2`, with standard TLS peer and host
validation, `Content-Type: application/json`, and `x-api-key:
{$CATO.API.TOKEN}`. Host macros:

- `{$CATO.API.URL}` = `https://api.catonetworks.com/api/v1/graphql2`
- `{$CATO.ACCOUNT.ID}` = `964` (from `NBX_CATO_ACCOUNT_ID`)
- `{$CATO.API.TOKEN}` = Zabbix `SECRET_TEXT`, populated only from
  `NBX_CATO_API_KEY`

The API key must have read access to the account. A successful HTTP response
with a GraphQL `permission denied` error is a collector failure, not a valid
empty estate. `--apply-cato` fail-closes on that before import.

The token is never committed, copied into NetBox, printed, or included in
verification output.

Cato rate limits are **per query name, per account**. Every API key that hits
account `964` shares the same counter. Two different queries do not share a
bucket; two users calling the same query do. Documented floors (not hard
ceilings):

| Query | Cato floor | This collector |
|---|---|---|
| `accountSnapshot` | 1/sec (30/min) | **1/min** HTTP master |
| `accountMetrics` | 15/min | **1/5 min** HTTP master |
| Other GraphQL | 120/min account-wide | none on this host |

That is 1 snapshot POST per minute vs a 30/min floor, and 12 metrics POSTs per
hour vs a 15/min floor. Last-mile is **not** a third poller: `timeseries(labels:
[lastMilePacketLoss, lastMileLatency], buckets: 1)` rides on the existing
metrics POST. `--check-cato` / `--apply-cato` GraphQL preflight is two extra
calls (one of each query), not a loop. Do not add `socketPortMetrics` or a
third HTTP master; that is a later pass and would compete with the metrics
bucket if CMA or another tool already uses `accountMetrics`.

Zabbix HTTP agent does not retry 429s. Stay on these intervals. If
`Cato API: Metrics GraphQL errors` or snapshot/metrics `nodata` fires together
with CMA API 429s, slow down — never add polls.

The snapshot query deliberately omits `info.wanRole`. The live API returns
lowercase enum values for that optional field and reports
`extensions.schemaViolations`. Snapshot does collect `operationalStatus`,
`lastConnected`, `connectedSince`, `popName`, `hostCount`,
`degradedStatus { isDegraded, degradedDetails { reason } }`,
`haStatus { readiness, wanConnectivity, keepalive, socketVersion }`,
per-Socket `haRole` / `deviceUptime`, WAN `physicalPort`,
`tunnelRemoteIP`, `tunnelRemoteIPInfo.provider`, `tunnelConnectionReason`,
and `interfacesLinkState { id, mediaIn, up, hasAddress, hasInternet,
hasTunnel, duplex, linkSpeed }`. Metrics collect overlay loss/RTT/jitter,
discards, `interfaceInfo.destType`, and last-mile from **timeseries labels**
`lastMilePacketLoss` / `lastMileLatency` (not scalar `metrics.lastmile*`). If
the timeseries labels are rejected, the schema-violation Warning fires.

`toRate: true` byte counters are multiplied by eight for bps. Utilization %
items exist when `upstreamBandwidth` / `downstreamBandwidth` caps are > 0
(treated as Mbps).

## Discovery and signals

All low-level discovery is dependent on one of the two master items and keeps
lost resources for seven days. Missing `data.accountSnapshot`, missing
`data.accountMetrics`, or missing entities discard a dependent value instead of
manufacturing zero. Discovery returns `[]` in that case, so a collector failure
cannot become a site outage.

| Discovery | Master | Stable identity | Signals |
|---|---|---|---|
| `cato.site.discovery` | snapshot | `{#SITE.ID}` | Connectivity, CMA Degraded, operational status, POP, host count, HA enabled/readiness/socket version. |
| `cato.socket.discovery` | snapshot | `{#SITE.ID}`, `{#SOCKET.ID}` | Socket state, row-local site state, version, uptime. Labels are `site / serial`. `{#HA.ROLE}` is CMA `MASTER` / `BACKUP` / `NONE` from `device.haRole` (with `isPrimary` fallback). |
| `cato.wan.discovery` | snapshot | `{#SITE.ID}`, `{#SOCKET.ID}`, `{#LINK.ID}` | Per-Socket WAN state, tunnel uptime, POP, dest type, physical port, ISP provider, tunnel remote IP. Labels are `site / serial / link`. USB identities are skipped. |
| `cato.port.discovery` | snapshot | `{#SITE.ID}`, `{#SOCKET.ID}`, `{#PORT.ID}` | Physical `mediaIn` / link / tunnel / internet from `interfacesLinkState`. `{#PORT.KIND}` is `wan` / `lan` / `other`. USB ports are skipped (unused on this estate). LTE/ALT stay WAN. |
| `cato.wan.metrics.discovery` | metrics | `{#SITE.ID}`, `{#LINK.ID}` | HA-merged overlay SLA, last-mile loss/latency, discards, util %. Labels stay `site / link`. USB identities are skipped. |

Every item prototype (and its triggers) is tagged `site={#SITE.NAME}` and
`connection_type={#CONN.TYPE}` so Monitoring → Latest data / Problems can
filter by site. Socket/WAN/port rows also keep `ha_role` and `serial`; serial
is identity, not a dashboard filter. Navigators group by **site**, not serial.

Connectivity value map: `0=Disconnected`, `1=Connected`, `2=Unknown`.
Degraded value map: `0=OK`, `1=Degraded`. CMA Degraded is **not** a third
connectivity state — `connectivityStatus` stays connected|disconnected.

Numeric SLA prototypes keep 30 days of history and 365 days of trends. Overlay
loss for Path is `max(RX, TX)` so one honeycomb can go yellow at CMA's 2%
threshold without 51 line graphs.

## Alert model

| Severity | Trigger | Meaning |
|---|---|---|
| High | `Cato site {#SITE.NAME}: Disconnected` after three zero samples | Overlay site outage. Not Disaster: the building is not dark. |
| Average | `Cato site {#SITE.NAME}: Degraded` while the site is connected | CMA yellow. Depends on site Disconnected. Reasons are a CHAR item (`WAN_DISCONNECTED`, `LAN_*`, `HA_NOT_READY_*`, …). |
| Average | Socket or WAN disconnected while the site is up | Socket- or link-specific overlay failure. |
| Average | WAN `mediaIn=0` while the site is connected | Physical WAN unplug / SFP out. Circuit class for Socket-only sites. |
| Average | WAN `mediaIn=1` and `hasTunnel=0` | Port has Ethernet but no DTLS to a PoP. |
| Warning | LAN `mediaIn=0` while the site is connected | Building LAN, not an ISP circuit. |
| Average | Site connected, `isHA`, `haStatus.readiness` not `{$CATO.HA.READINESS.OK}` | HA not ready. May coexist with site Degraded when the reason is `HA_NOT_READY_*`. |
| Warning | HA `socketVersion` not `{$CATO.HA.VERSION.OK}` | Socket software skew. |
| Warning | Overlay loss > `{$CATO.LOSS.WARN}` (default **2**, CMA yellow) | Path quality. Not a circuit ticket. |
| Warning | Overlay RTT > `{$CATO.RTT.WARN}` (default **101**, off until baselined) | Path delay. |
| Average | Census below `{$CATO.SITES.EXPECTED}` / `SOCKETS` / `WAN` / `SLA` while the matching master is available | Silent LLD loss. Macro `0` mutes that family. Defaults are 11 / 21 / 33 / 17. |
| Average | Snapshot/metrics GraphQL errors, no snapshot for 5m, no metrics for 15m, unsupported items | Collector/API health only. |
| Warning | Snapshot or metrics schema violations | Schema drift / invalid optional-field observation. |

Site High does **not** depend on collector `nodata()`. Stale last-value during
an API outage is better than hiding a real overlay outage. Census fires only
when `cato.api.snapshot.available=1` (SLA census uses metrics availability).
`Unsupported items present` depends on both no-data triggers.

Last-mile loss/latency are dashboard-only. Cato probes several public
endpoints per WAN; the item is the **average** of the latest point on each
`lastMilePacketLoss` / `lastMileLatency` series, not the worst probe. Path →
Last mile honeycomb still yellows at 2% so you can see a sick underlay.
`{$CATO.LASTMILE.LOSS.WARN}` is that visual hint, not a trigger.

Identity CHAR (ISP provider, POP, dest type, physical port, remote IP,
connection reason, operational status, HA readiness, degraded reasons) is
optional: missing geo-IP/provider returns empty string instead of throwing, so
it does not inflate `zabbix[host,,items_unsupported]`. Network → Tunnels,
Network → HA, and Health → Degraded keep CHAR on a **Details** navigator plus
a Latest text widget. History graphs only numeric series (connectivity,
uptime, Degraded, host count). Selecting `Cato WAN …: ISP provider` no longer
feeds svggraph.

Foreach rollups (worst overlay loss/RTT/jitter, worst last-mile, worst util)
have `__seed` items so they stay supported before LLD and when every real
prototype discards (no timeseries, no bandwidth cap). Do not treat seed `0`
as a real 0% last-mile.

Direct ICMP failure on a NetBox Socket, Cato site/Socket/WAN state, and API
collector failure remain separate problem classes.

## Dashboards

Same chrome as Forti/EXOS: four header tiles, problems strip, interpolated
honeycombs with identity labels, svggraph history. Graph prototypes stay on
this template (same-template refs are valid) but are not dumped onto Health.

| Dashboard | Pages | What it is |
|---|---|---|
| **Health → Overview** | Snapshot / Metrics gauges, **Sites up** / **Sockets up**, problems (tags, site first), full-width **site** honeycomb (names, not serials), census and worst-overlay-loss history | The collector box plus the estate map |
| **Health → Census** | Discovered vs up counts (sites / Sockets / WAN / SLA), **Degraded** count, worst overlay loss / RTT / last-mile loss / RX util gauges, discovery and connected history | 11 / 21 / 33 / 17 expected; 33 vs 17 is `groupDevices: true`. USB is excluded from WAN/port/SLA LLD — if census WAN drops after apply, set `{$CATO.WAN.EXPECTED}` (and SLA if needed) to the new Health → Census count. |
| **Health → Degraded** | Degraded count, site Degraded honeycomb, numeric navigator (Degraded / connectivity / hosts / HA ready) plus History, CHAR **Details** (reasons, operational status, POP) plus Latest | CMA yellow, not site High. CHAR is not graphed. |
| **Health → API** | GraphQL error and schema-violation tiles, unsupported items, Snapshot/Metrics gauges, error history | Collector failures, not overlay outages |
| **Path → Overview** | Full-width overlay **loss** honeycomb (yellow at CMA 2%), then RTT and jitter | Overlay quality scan |
| **Path → Last mile** | Last-mile loss, last-mile latency, RX/TX utilization honeycombs | Underlay toward the Socket, plus WAN fill. No last-mile trigger. |
| **Path → Probe** | Navigator grouped by **site → connection_type → dest_type** (loss / RTT / jitter / last-mile / bps / util / discards) plus selected-metric history | Drill-down / tag filter, not a 51-graph gallery |
| **Network → Overview** | Full-width WAN connectivity (`site / serial / link`) then Socket honeycomb (`site / serial`) | Tunnel and Socket up/down. No USB. |
| **Network → Tunnels** | Numeric navigator (connectivity, tunnel uptime) plus History; CHAR **Details** (PoP, dest type, physical port, ISP provider, remote IP, reason) plus Latest. Grouped by **site → connection_type → ha_role → dest_type** | Per-Socket WAN drill-down. CHAR is not graphed. |
| **Network → Ports** | WAN vs LAN **mediaIn** honeycombs, navigator grouped by **site → port_kind → ha_role → connection_type** | Physical unplug vs tunnel-down. USB ports are not discovered. |
| **Network → HA** | Site HA-ready honeycomb plus numeric HA ready/enabled/Socket uptime History; CHAR **Details** (readiness, socket version, operational status) plus Latest | Pair health without dumping CHAR onto a graph |

Template **Items** (the ~50 collector keys) only have `component` / `monitoring_domain` / `scope`. Site, `connection_type`, `ha_role`, `port_kind`, and `dest_type` are LLD tags. They show up in host Latest data / Graphs after `--apply-cato` and discovery, and as nested groups on the navigators above. Serial is identity, not a filter.

## Deployment and rollout

Collector refresh is **`configure_nbxsync_network.py --apply-cato`**. That flag
fail-closes on GraphQL preflight, imports the YAML, and converges the owned
account host. It does **not** run zerotouch, HostSync Socket devices, or mutate
NetBox Socket roles. `--check-cato` is the read-only preflight plus collector
shape.

Do **not** re-run `configure_nbxsync_zerotouch.py` to refresh this pack. Zerotouch
`--enable-cato --mutate-netbox` is a future Socket-inventory migration only.

```bash
export NBX_CATO_API_KEY=...
# NetBox already has Zabbix Production; optional: NBX_CATO_ACCOUNT_ID, NBX_CATO_PROXY_GROUP
python3 scripts/configure_nbxsync_network.py --check-cato
python3 scripts/configure_nbxsync_network.py --apply-cato
```

`scripts/configure_cato_zabbix.py` remains the Zabbix-API implementation and
lab `--simulate` path. `--verify` is collector-only during the 0/21 hold;
`--verify --require-sockets` fails on missing Socket ICMP serials after the
approved migration.

**Production state (2026-08-25):** collector live; all 21 Sockets retain the
existing role-level `do_not_monitor` exclusion. Do not run the zerotouch
Socket migration merely to refresh this template.

1. Refresh the account pack: `configure_nbxsync_network.py --apply-cato`.
2. **Future approved migration only:** migrate Socket inventory to the gapless
   `onboarding` hold with
   `configure_nbxsync_zerotouch.py --enable-cato --mutate-netbox`.
3. Release individual Socket hosts only after their primary IP and proxy route
   are ready. The exact hold/release command is in
   `docs/netbox-zabbix/runbooks/onboarding.md`.

## Circuit / last-mile vs overlay

Socket-only sites have no Forti SD-WAN health-check. Last-mile loss/latency on this collector is the underlay probe (ICMP outside the tunnel). Overlay loss stays overlay. CMA **Degraded** is `degradedStatus`, not `connectivityStatus` — an unplugged WAN does not disconnect the site or the account collector. Physical unplug is `interfacesLinkState.mediaIn`, not `interfaces.connected` (that is tunnel-to-PoP). Circuit class, degraded reasons, and last-mile vs overlay: [05](05-internet-circuits.md).

## API references

- Cato API endpoint and GraphQL guidance:
  <https://api.catonetworks.com/api/v1/graphql2>
- Cato API rate limiting:
  <https://knowledge.catonetworks.com/docs/en/understanding-cato-api-rate-limiting>
- `accountMetrics` field reference:
  <https://knowledge.catonetworks.com/docs/cato-api-accountmetrics.md>
- Site connectivity statuses (CMA Degraded vs API `degradedStatus`):
  <https://knowledge.catonetworks.com/docs/connectivity-statuses-for-cato-sites>
- `accountSnapshot` interface fields (`physicalPort`, `tunnelRemoteIPInfo`, `interfacesLinkState`):
  <https://knowledge.catonetworks.com/docs/cato-api-accountsnapshot-sites-devices-interfaces>
