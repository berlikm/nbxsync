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

## Data path

| Master item | API query | Interval | Retention | Purpose |
|---|---|---:|---:|---|
| `cato.account.snapshot` | `accountSnapshot` | 1m | 1d | Site, Socket, WAN, and HA state. |
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
verification output. The 1/minute snapshot and 1/5-minute metrics requests are
below Cato's documented account limits of 30/minute and 15/minute respectively.

The snapshot query deliberately omits `info.wanRole`. The live API returns
lowercase enum values for that optional field and reports
`extensions.schemaViolations`. Snapshot does collect `operationalStatus`,
`lastConnected`, `connectedSince`, and `haStatus { readiness, wanConnectivity,
keepalive, socketVersion }`. Metrics collect overlay loss/RTT/jitter plus
`lastmilePacketLoss`, `lastmileLatency`, `packetsDiscardedDownstream`, and
`packetsDiscardedUpstream`. If those last-mile/discard fields are rejected,
the schema-violation Warning fires — field names may differ from the public
docs (camelCase `lastmilePacketLoss` / `lastmileLatency`).

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
| `cato.site.discovery` | snapshot | `{#SITE.ID}` | Connectivity, operational status, HA enabled/readiness/socket version. |
| `cato.socket.discovery` | snapshot | `{#SITE.ID}`, `{#SOCKET.ID}` | Socket state, row-local site state, version. Labels are `site / serial`. `{#HA.ROLE}` is `primary` / `secondary` / `standalone` from `socketInfo.isPrimary`. |
| `cato.wan.discovery` | snapshot | `{#SITE.ID}`, `{#SOCKET.ID}`, `{#LINK.ID}` | Per-Socket WAN state, tunnel uptime, POP. Labels are `site / serial / link`. |
| `cato.wan.metrics.discovery` | metrics | `{#SITE.ID}`, `{#LINK.ID}` | HA-merged overlay SLA, last-mile loss/latency, discards, util %. Labels stay `site / link`. |

Connectivity value map: `0=Disconnected`, `1=Connected`, `2=Unknown`.

Numeric SLA prototypes keep 30 days of history and 365 days of trends. Overlay
loss for Path is `max(RX, TX)` so one honeycomb can go yellow at CMA's 2%
threshold without 51 line graphs.

## Alert model

| Severity | Trigger | Meaning |
|---|---|---|
| High | `Cato site {#SITE.NAME}: Disconnected` after three zero samples | Overlay site outage. Not Disaster: the building is not dark. |
| Average | Socket or WAN disconnected while the site is up | Socket- or link-specific overlay failure. |
| Average | Site connected, `isHA`, `haStatus.readiness` not `{$CATO.HA.READINESS.OK}` | HA not ready. |
| Warning | HA `socketVersion` not `{$CATO.HA.VERSION.OK}` | Socket software skew. |
| Warning | Overlay loss > `{$CATO.LOSS.WARN}` (default **2**, CMA yellow) | Path quality. |
| Warning | Last-mile loss > `{$CATO.LASTMILE.LOSS.WARN}` (default **2**) | ISP last mile, separate from overlay. |
| Warning | Overlay RTT > `{$CATO.RTT.WARN}` (default **101**, off until baselined) | Path delay. |
| Average | Census below `{$CATO.SITES.EXPECTED}` / `SOCKETS` / `WAN` / `SLA` while the matching master is available | Silent LLD loss. Macro `0` mutes that family. Defaults are 11 / 21 / 33 / 17. |
| Average | Snapshot/metrics GraphQL errors, no snapshot for 5m, no metrics for 15m, unsupported items | Collector/API health only. |
| Warning | Snapshot or metrics schema violations | Schema drift / invalid optional-field observation. |

Site High does **not** depend on collector `nodata()`. Stale last-value during
an API outage is better than hiding a real overlay outage. Census fires only
when `cato.api.snapshot.available=1` (SLA census uses metrics availability).
`Unsupported items present` depends on both no-data triggers.

Direct ICMP failure on a NetBox Socket, Cato site/Socket/WAN state, and API
collector failure remain separate problem classes.

## Dashboards

Same chrome as Forti/EXOS: four header tiles, problems strip, interpolated
honeycombs with identity labels, svggraph history. Graph prototypes stay on
this template (same-template refs are valid) but are not dumped onto Health.

| Dashboard | Pages | What it is |
|---|---|---|
| **Health → Overview** | Snapshot / Metrics gauges, **Sites up** / **Sockets up**, problems, full-width **site** honeycomb (names, not serials), census and worst-overlay-loss history | The collector box plus the estate map |
| **Health → Census** | Discovered vs up counts (sites / Sockets / WAN / SLA), HA not-ready count, worst overlay loss / RTT / last-mile loss / RX util gauges, discovery and connected history | 11 / 21 / 33 / 17 expected; 33 vs 17 is `groupDevices: true` |
| **Health → API** | GraphQL error and schema-violation tiles, unsupported items, Snapshot/Metrics gauges, error history | Collector failures, not overlay outages |
| **Path → Overview** | Full-width overlay **loss** honeycomb (yellow at CMA 2%), then RTT and jitter | Overlay quality scan |
| **Path → Last mile** | Last-mile loss, last-mile latency, RX/TX utilization honeycombs | Underlay toward the Socket, plus WAN fill |
| **Path → Probe** | Navigator (loss / RTT / jitter / last-mile / bps / util / discards) plus selected-metric history | Drill-down, not a 51-graph gallery |
| **Network → Overview** | Full-width WAN connectivity (`site / serial / link`) then Socket honeycomb (`site / serial`) | Tunnel and Socket up/down |
| **Network → Tunnels** | Navigator for connectivity, tunnel uptime, PoP | Per-Socket WAN drill-down |
| **Network → HA** | Site HA-ready honeycomb (standalone counts as ready) plus readiness / socket-version / operational-status navigator | Pair health without dumping CHAR items onto Overview |

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

## API references

- Cato API endpoint and GraphQL guidance:
  <https://api.catonetworks.com/api/v1/graphql2>
- Cato API rate limiting:
  <https://knowledge.catonetworks.com/docs/en/understanding-cato-api-rate-limiting>
- `accountMetrics` field reference:
  <https://knowledge.catonetworks.com/docs/cato-api-accountmetrics.md>
