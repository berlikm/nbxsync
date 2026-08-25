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
| Cato account `964` | `scripts/configure_cato_zabbix.py` | One interface-free host, `cato-account-964`, linked only to `Cato Networks by HTTP`. |
| Cato `IPSEC_V2` Azure sites | None in this rollout | Explicitly out of scope. |

The account collector discovers only Cato sites whose `info.connType` matches
`{$CATO.SITE.CONN_TYPE.MATCHES}=^SOCKET_`. It does not create Socket hosts,
link an ICMP template to a role, or poll Socket management IPs. This keeps one
`icmpping` source per NetBox device and preserves the distinction between
Socket reachability and Cato overlay state.

Live schema reconnaissance for account `964` found 13 API sites: 11
`SOCKET_*` sites with 21 nonblank Socket serials matching the 21 NetBox devices,
and two `IPSEC_V2` Azure sites excluded here. Expected Cato discoveries are 11
Socket sites, 21 physical Sockets, 33 Socket WAN tunnels, and 17 unique
Socket-site/interface SLA rows.

## Data path

| Master item | API query | Interval | Retention | Purpose |
|---|---|---:|---:|---|
| `cato.account.snapshot` | `accountSnapshot` | 1m | 1d | Site, Socket, and WAN connectivity/identity state. |
| `cato.account.metrics` | `accountMetrics` with `timeFrame: "last.PT5M"`, `groupDevices: true`, `groupInterfaces: false`, `metrics(toRate: true)` | 5m | 1d | Rate-normalized WAN bandwidth, loss, jitter, and RTT. |

Both masters are HTTP-agent `POST` requests to
`https://api.catonetworks.com/api/v1/graphql2`, with standard TLS peer and host
validation, `Content-Type: application/json`, and `x-api-key:
{$CATO.API.TOKEN}`. The host macros are:

- `{$CATO.API.URL}` = `https://api.catonetworks.com/api/v1/graphql2`
- `{$CATO.ACCOUNT.ID}` = `964`
- `{$CATO.API.TOKEN}` = Zabbix `SECRET_TEXT`, populated only from
  `NBX_CATO_API_KEY`

The API key must have read access to account `964`. A successful HTTP response
with a GraphQL `permission denied` error is a collector failure, not a valid
empty Cato estate; the collector error counters expose it.

The token is never committed, copied into NetBox, printed, or included in
verification output. The 1/minute snapshot and 1/5-minute metrics requests are
below Cato's documented account limits of 30/minute and 15/minute respectively.
A transient failure or HTTP 429 is no-data until the next scheduled Zabbix poll;
there is no inner retry loop.

The snapshot query deliberately omits `info.wanRole`. The live API returns
lowercase enum values for that optional field and reports
`extensions.schemaViolations`; WAN role is not needed for identity, state, or
alerting.

## Discovery and signals

All low-level discovery is dependent on one of the two master items and keeps
lost resources for seven days. Missing `data.accountSnapshot`, missing
`data.accountMetrics`, or missing entities discard a dependent value instead of
manufacturing zero. Discovery returns `[]` in that case, so a collector failure
cannot become a site outage.

| Discovery | Master | Stable identity | Signals |
|---|---|---|---|
| `cato.site.discovery` | snapshot | `{#SITE.ID}` | Site `connected` / `disconnected` / `Unknown`. |
| `cato.socket.discovery` | snapshot | `{#SITE.ID}`, `{#SOCKET.ID}` | Socket state, row-local site state, version; labels carry serial, HA role, platform. |
| `cato.wan.discovery` | snapshot | `{#SITE.ID}`, `{#SOCKET.ID}`, `{#LINK.ID}` | WAN state, row-local site state, tunnel uptime, POP. |
| `cato.wan.metrics.discovery` | metrics | `{#SITE.ID}`, `{#LINK.ID}` | RX/TX bps, RX/TX packet loss, RX/TX jitter, RTT. |

Connectivity value map: `0=Disconnected`, `1=Connected`, `2=Unknown`.
Site strings map `connected`/`disconnected`; Socket and WAN booleans map
`true`/`false`; all new or absent state is `Unknown`.

The seven numeric SLA prototypes use 30 days of history and 365 days of trends:

- `cato.wan.rx.bps[...]` and `cato.wan.tx.bps[...]` multiply the API's
  rate-normalized bytes by eight.
- `cato.wan.loss.rx.pct[...]`, `cato.wan.loss.tx.pct[...]`,
  `cato.wan.jitter.rx.ms[...]`, `cato.wan.jitter.tx.ms[...]`, and
  `cato.wan.rtt.ms[...]` retain the API values.

No loss, jitter, or RTT threshold trigger ships in this rollout. Production
baselines do not yet define actionable values; the `Health` dashboard exposes
the values instead.

## Alert model

| Severity | Trigger | Meaning |
|---|---|---|
| Disaster | `Cato site {#SITE.NAME}: Disconnected` after three zero samples | Overlay site outage. |
| Average | `Cato Socket {#SERIAL}: Disconnected while site is up` | Socket-specific state failure; row-local site state must be connected. |
| Average | `Cato WAN {#SITE.NAME} / {#LINK.NAME}: Disconnected while site is up` | Last-mile/WAN-link loss; row-local site state must be connected. |
| Average | Snapshot GraphQL errors, metrics GraphQL errors, no snapshot data for 5m, no metrics data for 15m, unsupported items | Collector/API health only. |
| Warning | Snapshot or metrics schema violations | Schema drift / invalid optional-field observation. |

All Cato triggers have `component=cato`, `monitoring_domain=cato_overlay`, and
`scope=site`, `socket`, `wan`, or `collector`. `Unsupported items present`
depends on both no-data triggers, avoiding duplicate collector incidents.
State triggers never use `nodata()`.

Direct ICMP failure on a NetBox Socket, Cato site/Socket/WAN state, and API
collector failure are intentionally separate problem classes. Operators may
correlate them during triage, but should not suppress one based on another.

## Dashboard

Template dashboard **Health** has:

- **Overview:** Problems; honeycombs for site, Socket, and WAN connectivity;
  snapshot/metrics GraphQL error counts, schema-violation counts, and
  unsupported-item count.
- **WAN SLA:** graph prototypes `Bandwidth`, `Packet loss`, and `Latency and
  jitter` for every discovered SLA row.

No event, audit, webhook, XOps, or `socketPortMetrics` collection is part of
this pack.

## Deployment and rollout
Run this sequence in the development NetBox/Zabbix environment first. The
Socket migration mutates NetBox inventory tags and nbxSync configuration; repeat
it against production only after development validation and change approval.

**Production state (2026-08-25):** only step 1 is deployed. All 21 Sockets
retain the existing role-level `do_not_monitor` exclusion; none carries a Cato
component tag or has an ICMP host. Do not run step 2 merely to refresh this
state: it mutates GUI-managed NetBox and nbxSync configuration.

Production verification observed 11 in-scope Socket sites, 21 Socket serials,
33 WAN-state rows, and 17 SLA rows. Both HTTP masters were fresh, all
GraphQL/schema/unsupported counters were zero, and the account host had no
active problem.

1. Apply the account pack first: `scripts/configure_cato_zabbix.py --apply`.
   It imports idempotently, owns only a host tagged `managed_by=cato-pack`, and
   refuses to adopt an existing unowned `cato-account-964`.
2. **Future approved migration only:** migrate Socket inventory to the gapless
   `onboarding` hold with
   `configure_nbxsync_zerotouch.py --enable-cato --mutate-netbox`. The legacy
   role-level exclusion is removed only after every current Socket has the
   per-device `onboarding` exclusion.
3. Release individual Socket hosts only after their primary IP and proxy route
   are ready. The exact hold/release command is in
   `docs/netbox-zabbix/runbooks/onboarding.md`.
4. Start with the three pilots documented in the rollout plan, then verify the
   final fresh ICMP count as `N/21` before declaring the integration live.

During the current account-collector-only rollout, retain the existing Socket
role hold. After a future approved migration, a new Socket becomes an
operator-owned NetBox step: tag `onboarding` before its first nbxSync run and
remove it only when ready. `nbx-ingestor-v2` is unchanged.

## API references

- Cato API endpoint and GraphQL guidance:
  <https://api.catonetworks.com/api/v1/graphql2>
- Cato API rate limiting:
  <https://knowledge.catonetworks.com/docs/en/understanding-cato-api-rate-limiting>
- `accountMetrics` field reference:
  <https://knowledge.catonetworks.com/docs/cato-api-accountmetrics.md>
