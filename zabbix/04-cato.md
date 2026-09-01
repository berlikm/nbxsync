# Cato — Zabbix monitoring

**Status:** production account collector and 21/21 NetBox-backed Socket ICMP hosts live.<br>
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
estate does not use them). `--apply-cato` immediately retires the legacy
USB-generated physical-port items and their trigger instances; it does not wait
for the normal seven-day LLD lost-resource lifetime. If Health → Census WAN
drops below 33 after apply, the new count is the Ethernet/LTE/ALT census —
update `{$CATO.WAN.EXPECTED}`.

## Data path

| Master item | API query | Interval | Retention | Purpose |
|---|---|---:|---:|---|
| `cato.account.snapshot` | `accountSnapshot` including `degradedStatus` and `interfacesLinkState` | 1m | 1d | Site, Socket, WAN, HA, CMA Degraded, and physical port state. |
| `cato.account.metrics` | `accountMetrics` with `timeFrame: "last.PT5M"`, `groupDevices: true`, `groupInterfaces: false`, `metrics(toRate: true)`, plus sibling `socketPortMetrics` LAN throughput | 5m | 1d | Overlay SLA, last-mile loss/latency, discards, WAN bandwidth, LAN bits. |

There is no third HTTP master. `socketPortMetrics` is a **root** GraphQL field (not nested under `accountMetrics`). It rides the existing 5-minute metrics POST as a sibling selection so LAN throughput does not need a third poller. Socket CPU is not on this collector.

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
| `socketPortMetrics` | 120/min general | sibling field on the metrics POST (**12/hour**) |
| Other GraphQL | 120/min account-wide | none else on this host |

That is 1 snapshot POST per minute vs a 30/min floor, and 12 metrics POSTs per
hour vs a 15/min floor. Last-mile is **not** a third poller: `timeseries(labels:
[lastMilePacketLoss, lastMileLatency], buckets: 1) { label data info
dimensions { label value } }` rides on the existing
metrics POST. LAN bits are also not a third poller: the same document selects
`socketPortMetrics` (account 964, `last.PT5M`, max `throughput_upstream` /
`throughput_downstream`, dimensions site/interface/transport). Cato rate limits
are per **query name**; one HTTP POST may increment both `accountMetrics` and
`socketPortMetrics`. `--check-cato` / `--apply-cato` GraphQL preflight is two
extra calls (one of each HTTP master), not a loop. Do not add a third HTTP
master or a 1-minute `socketPortMetrics` poller.

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
discards, `interfaceInfo.destType`, last-mile from **timeseries labels**
`lastMilePacketLoss` / `lastMileLatency` (not scalar `metrics.lastmile*`)
with `info` and `dimensions { label value }` for probe dests,
and LAN throughput from sibling `socketPortMetrics`. If the timeseries labels
are rejected, the schema-violation Warning fires.

`toRate: true` overlay byte counters are multiplied by eight for bps.
`socketPortMetrics` `throughput_*` values are the same byte/s rates: LLD keeps
`transport_type == LAN` (USB skipped; Socket sites only) and dependent items
multiply by eight so LAN RX/TX match WAN overlay units. Utilization % items
exist when `upstreamBandwidth` / `downstreamBandwidth` caps are > 0
(treated as Mbps). LAN has no circuit cap on this collector — bits only.

When replacing the older `cato.lan.port.discovery` rule, `--apply-cato`
removes only that rule's generated LAN items and graphs before the new
`cato.lan.metrics.discovery` rule runs. The changed item keys intentionally
start a new LAN history series; the cleanup prevents duplicate graph names.

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
| `cato.wan.metrics.discovery` | metrics | `{#SITE.ID}`, `{#LINK.ID}` | HA-merged overlay SLA, last-mile loss/latency, last-mile probe count/dests, discards, util %. Labels stay `site / link`. USB identities are skipped. Single-WAN sites (HU-DEB) have one row (`WAN 01`); dual-WAN sites have two. That is not an LLD miss. |
| `cato.lan.metrics.discovery` | metrics | `{#SITE.ID}`, `{#PORT.ID}` | HA-merged LAN bits from `socketPortMetrics` (`transport_type` LAN). Labels stay `site / LAN*`. USB identities are skipped. |

Every item prototype (and its triggers) is tagged `site={#SITE.NAME}` and
`connection_type={#CONN.TYPE}` so Monitoring → Latest data / Problems can
filter by site. Socket/WAN/port rows also keep `ha_role` and `serial`; serial
is identity, not a dashboard filter. Navigators group by **site**, not serial.

Connectivity value map: `0=Disconnected`, `1=Connected`, `2=Unknown`.
Degraded value map: `0=OK`, `1=Degraded`. CMA Degraded is **not** a third
connectivity state — `connectivityStatus` stays connected|disconnected.

Numeric SLA prototypes keep 30 days of history and 365 days of trends. Overlay
loss for Path is `max(RX, TX)` so one honeycomb can go yellow at CMA's 2%
threshold without 51 line graphs. Overlay **loss** stays dashboard-only.
Overlay **RTT** and last-mile **latency** ticket Warning when the last three
5-minute samples are all at or above the red honeycomb (`{$CATO.RTT.WARN}` /
`{$CATO.LASTMILE.LATENCY.WARN}`, default 150 ms). Yellow at 80 ms is visual
only. Raise the host macro on a site that normally sits hot; set it to `99999`
to mute.

## Alert model

| Severity | Trigger | Meaning |
|---|---|---|
| High | `Cato site {#SITE.NAME}: Disconnected` after three zero samples | Overlay site outage. Not Disaster: the building is not dark. |
| Average | `Cato site {#SITE.NAME}: Degraded` while the site is connected | CMA yellow. Depends on site Disconnected. Reasons are a CHAR item (`WAN_DISCONNECTED`, `LAN_*`, `HA_NOT_READY_*`, …). |
| Average | Socket or WAN disconnected while the site is up | Socket- or link-specific overlay failure. |
| Average | WAN `mediaIn=0` while the site is connected | Physical WAN unplug / SFP out. Circuit class for Socket-only sites. |
| Average | WAN1 `mediaIn=1` and `hasTunnel=0` (`{$CATO.PORT.TUNNEL.MATCHES}=^WAN1$`) | Active WAN has Ethernet but no DTLS. **WAN2 standby with link and no tunnel does not page.** CMA Degraded still covers unexpected `WAN_TUNNEL_DISCONNECTED`. |
| Warning | `Cato WAN {#SITE.NAME} / {#LINK.NAME}: High overlay RTT` for three samples `>= {$CATO.RTT.WARN}` | Tunnel round-trip to the PoP. Honeycomb red, not a site outage. Depends on site Disconnected. |
| Warning | `Cato WAN {#SITE.NAME} / {#LINK.NAME}: High last-mile latency` for three samples `>= {$CATO.LASTMILE.LATENCY.WARN}` | Underlay ICMP average toward public probes. Same 150 ms red as overlay RTT. Depends on site Disconnected. |
| Warning | LAN `mediaIn=0` while the site is connected | Building LAN, not an ISP circuit. |
| Average | Site connected, `isHA`, `haStatus.readiness` not `{$CATO.HA.READINESS.OK}` | HA not ready. May coexist with site Degraded when the reason is `HA_NOT_READY_*`. |
| Warning | HA `socketVersion` not `{$CATO.HA.VERSION.OK}` | Socket software skew. |
| Average | Census below host `{$CATO.SITES.EXPECTED}` / `SOCKETS` / `WAN` / `SLA` for **30m** while the matching master is available | Silent LLD loss. `--apply-cato` writes those macros from live USB-filtered GraphQL census. Macro `0` mutes that family. |
| Average | Snapshot/metrics GraphQL errors, no snapshot for 5m, no metrics for 15m, unsupported items | Collector/API health only. |
| Warning | Snapshot or metrics schema violations | Schema drift / invalid optional-field observation. |

Site High does **not** depend on collector `nodata()`. Stale last-value during
an API outage is better than hiding a real overlay outage. Census fires only
when `cato.api.snapshot.available=1` (SLA census uses metrics availability).
`Unsupported items present` depends on both no-data triggers.

Last-mile **loss** stays dashboard-only. Cato probes several public
endpoints per WAN; the loss/latency items are the **average** of the latest
point on each `lastMilePacketLoss` / `lastMileLatency` series, not the worst
probe and not one item per dest. A single-WAN site such as HU-DEB therefore
shows one Last-mile latency honeycomb cell (`WAN 01`) while dual-WAN sites
show WAN 01 and WAN 02. Probe count can also differ: HU-DEB may have one
latency series; another site may average two. That is Cato's timeseries, not
a collector hole — do not invent extra WANs or copy last-mile latency onto
overlay RTT (`metrics.rtt` is a different field and can be empty on its own).
Latest data has `Last-mile latency probes` / `Last-mile loss probes` (count)
and matching `probe dests` CHAR from timeseries `info` / `dimensions`. Path →
Last mile honeycomb still yellows at 2% loss / 80 ms latency. Last-mile
**latency** now tickets Warning at the red 150 ms honeycomb
(`{$CATO.LASTMILE.LATENCY.WARN}`). `{$CATO.LASTMILE.LOSS.WARN}` remains a
visual hint, not a trigger.

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
| **Health → Degraded** | Degraded count, site Degraded honeycomb, numeric navigator plus History, CHAR **Details** (reasons, operational status, POP) plus Latest. Navigators are **site** only. Latest is 14% left-aligned, not bold, so long `WAN_DISCONNECTED,LAN_*` strings fit | CMA yellow, not site High. CHAR is not graphed. Zabbix item-value `value_size` is **percent of widget height** — 28% clipped the reasons. |
| **Health → API** | GraphQL error and schema-violation tiles, unsupported items, Snapshot/Metrics gauges, error history | Collector failures, not overlay outages |
| **Path → Overview** | Full-width overlay **loss** honeycomb (yellow at CMA 2%), then RTT and jitter | Overlay quality scan |
| **Path → Last mile** | Last-mile loss, last-mile latency, RX/TX utilization honeycombs | Underlay toward the Socket, plus WAN fill %. One hex per SLA row: HU-DEB-style sites have `WAN 01` only. Last-mile latency tickets Warning at 150 ms; last-mile loss stays visual. WAN **bits** graphs live on Network → Ports. |
| **Path → Probe** | Navigator grouped by **site → dest_type** (loss / RTT / jitter / last-mile / probe counts / bps / util / discards) plus selected-metric history | Drill-down for one site's overlay, not a 51-graph gallery. Probe **dests** CHAR stays on host Latest data, not this graph. |
| **Network → Overview** | WAN connectivity then Socket honeycomb. WAN hex labels are `site port` (serial dropped so 33 cells stay readable) | Tunnel and Socket up/down. No USB. |
| **Network → Tunnels** | Numeric navigator (connectivity, tunnel uptime) plus History; CHAR **Details** plus Latest. Grouped **site → serial → dest_type** | Pick a Socket, then its WAN tunnels. CHAR is not graphed. |
| **Network → Ports** | WAN vs LAN **mediaIn** honeycombs side by side (`site port` labels), then EXOS-style 3×2 **WAN traffic** and **LAN traffic** | Estate scan of physical media and bits. USB ports are not discovered. |
| **Network → Port** | Navigator **site → serial → port_kind** (media / link / tunnel / internet) plus History | One Socket's WAN and LAN ports — the EXOS Port page on a multi-site collector |
| **Network → HA** | Site HA-ready honeycomb plus numeric HA ready/enabled/Socket uptime History; CHAR **Details** plus Latest. Navigators are **site** only | Pair health without dumping CHAR onto a graph |

Template **Items** (the ~50 collector keys) only have `component` / `monitoring_domain` / `scope`. Site, `connection_type`, `ha_role`, `port_kind`, `dest_type`, and `serial` are LLD tags. They show up in host Latest data / Graphs after `--apply-cato` and discovery. Navigators always start at **site** (11 sites). **Serial** is the Socket picker on Network → Tunnels and Network → Port — never the first group. `connection_type` stays on items for Latest data filters; it is not a navigator group on this SOCKET-only estate.

## Deployment and rollout

Collector refresh is **`configure_nbxsync_network.py --apply-cato`**. That flag
fail-closes on GraphQL preflight, imports the YAML, and converges the owned
account host. It does **not** run zerotouch, HostSync Socket devices, or mutate
NetBox Socket roles. `--check-cato` is the read-only preflight plus collector
shape.

Do **not** re-run `configure_nbxsync_zerotouch.py` to refresh this pack. The
one-time Socket migration is complete; use the per-Socket onboarding runbook
for a new or replacement device.

```bash
export NBX_CATO_API_KEY=...
# NetBox already has Zabbix Production; optional: NBX_CATO_ACCOUNT_ID, NBX_CATO_PROXY_GROUP
python3 scripts/configure_nbxsync_network.py --check-cato
python3 scripts/configure_nbxsync_network.py --apply-cato
```

`scripts/configure_cato_zabbix.py` remains the Zabbix-API implementation and
lab `--simulate` path. `--verify --require-sockets` enforces the 21/21 Socket
ICMP serial census.

**Production state (2026-08-25):** the account collector and all 21 Socket
ICMP hosts are live. The Socket role has no `do_not_monitor` assignment, and
no current Socket carries `onboarding` or the legacy inventory exclusion.
Refreshing this template does not mutate Socket inventory.

1. Refresh the account pack: `configure_nbxsync_network.py --apply-cato`.
2. For a new or replacement Socket, use the hold/release command in
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
