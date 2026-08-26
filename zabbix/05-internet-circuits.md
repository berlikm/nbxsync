# Internet circuits

Prepared later. Same bar as [01](01-extreme-switching.md): a circuit page is not a fabric `USW` ticket. Tag them so Forti WAN and Extreme `UW-` can share the class later. On the switch template, `UW` is **Average** like every other discovered link.

Depends on Extreme `UW-…` labels ([port-identity.md](port-identity.md)) and/or Forti WAN / SD-WAN health-checks ([03-fortinet.md](03-fortinet.md) — API, not SNMP). Some sites have **only a Cato Socket** — no Forti SD-WAN probe. For those, Cato last-mile and WAN snapshot are the underlay signals; they are not Forti Path and must not double-page a Forti site. A Swiss central proxy only proves reachability from Switzerland.

---

## FortiGate HTTP is the probe we have

SD-WAN health-checks (loss / latency / jitter / probe status) are the underlay probe **where a FortiGate exists**. They run for **internet failover** on at least two VDOMs: **`root` (production)** and **`Untrust` (guest)**. Do not build a second ICMP/SLA poller for the same Forti circuit.

Until this page has its own circuit host, operators use the FortiGate host boards from [03](03-fortinet.md):

| Board | What to use for ISP work |
|---|---|
| **Path → Overview** | Member link vs health-check colour, VDOM-prefixed (`root/wan1`, `Untrust/Google/wan1`) |
| **Path → Loss** | Packet loss honeycomb (0 green / 5 yellow / 20 red = stock Warning). Production vs guest are different cells |
| **Path → Probe** | Navigator grouped by **vdom** — latency / jitter / loss / status / byte rate |
| **Network interfaces → Port** | Physical WAN bits through the per-interface navigator — not the stock 1-column Statistics slide |

A later circuit template should **reuse these items** (dependent items / a thin overlay), not poll FortiOS twice. Tag so Extreme `UW` and Forti path share a class without double-paging.

---

## Cato-only sites (no Forti SD-WAN)

Forti Path is the probe **where a FortiGate exists**. It does not cover Socket-only sites. The account collector in [04](04-cato.md) already sees those Sockets; it does not need a third HTTP master to start answering “is this circuit up / sick”.

The collector is `cato-account-964` in Zabbix, not on the Socket. Unplugging a WAN or putting a site **Degraded** does **not** stop snapshot/metrics: other sites and remaining tunnels still answer GraphQL.

### What CMA “Degraded” actually is

GraphQL `connectivityStatus` is only `connected` | `disconnected`. CMA’s yellow **Degraded** is a **separate** object, `degradedStatus { isDegraded, degradedDetails { reason, args } }`. Today’s site honeycomb and the site High trigger use connectivity only, so a site with one WAN unplugged still looks **Connected** / green while CMA shows Degraded.

| `degradedDetails.reason` | Meaning | Circuit class? |
|---|---|---|
| `WAN_DISCONNECTED` | A WAN / ALT WAN port is down (includes physically unplugged). Args: `deviceName`, `portID`, `portName`. | **Yes** — this is the Cato-only analog of a Forti member down |
| `WAN_TUNNEL_DISCONNECTED` | Port has link but no DTLS tunnel to a PoP | **Yes** — ISP or path to PoP, not a LAN cable |
| `ALT_WAN_DISCONNECTED` | Alternate WAN down | Yes if that site uses alt-WAN as a circuit |
| `LAN_DISCONNECTED` / `LAN_LAG_*` | LAN / LAG / VRRP port down | **No** — building LAN, not an ISP circuit |
| `HA_NOT_READY_*` | Peer down, keepalive fail, Socket version skew | **No** — HA, already Average on [04](04-cato.md) |
| `IPSEC_*` / `CROSS_CONNECT_CIRCUIT_DISCONNECTED` | IPsec / Cloud Interconnect | Out of Socket scope |

### Physical unplug vs tunnel down

`devices.interfaces[].connected` is **tunnel to the PoP**, not Ethernet link. Physical state is `devices.interfacesLinkState[]` (all Socket ports, including LAN):

| Field | What it tells you |
|---|---|
| `mediaIn` | Cable / SFP present (the unplug bit) |
| `up` | Port link up |
| `hasAddress` | WAN has an IP |
| `hasInternet` | Port can reach the internet |
| `hasTunnel` | DTLS to Cato is up |
| `id` | `WAN1` / `LAN1` / `LTE` / … |
| `duplex`, `linkSpeed` | Ethernet settings |

Same snapshot also has, per WAN tunnel: `physicalPort`, `destType` (`CATO` / `LAN` / `ALTERNATIVE` / …), `tunnelRemoteIP`, `tunnelRemoteIPInfo.provider` (ISP name from geo-IP), `tunnelConnectionReason` (CMA events include *“Reconnected after WAN port was physically disconnected”*).

`info.wanRole` stays omitted: the live API returns lowercase enums and `schemaViolations`. Dest type + physical port are enough to tell WAN from LAN.

### Last-mile vs overlay (already on the collector)

Cato documents two different losses:

| Signal | Where | What it is | Forti analog |
|---|---|---|---|
| Overlay `lost*Pcnt` / `rtt` / jitter | Inside the DTLS tunnel to the PoP | Overlay quality. [04](04-cato.md) Path Overview. **Not** a circuit ticket | — |
| Last-mile `lastMilePacketLoss` / `lastMileLatency` | ICMP from the Socket to well-known sites **outside** the tunnel, per WAN | ISP last mile. [04](04-cato.md) Path Last mile. Circuit quality | SD-WAN health-check loss / latency |
| `remoteIP` / `remoteIPInfo.provider` | Metrics interface | ISP-assigned WAN IP and provider string | Forti WAN address, not the probe |

Public schema puts last-mile on **timeseries labels** `lastMilePacketLoss` /
`lastMileLatency`, not on the scalar `metrics { }` object. The collector reads
those labels from the existing `accountMetrics` master (`buckets: 1`) and
averages the latest point across probe endpoints. Do not invent a third HTTP
master. Last-mile is dashboard-only: Path → Last mile honeycomb, no trigger.

`socketPortMetrics` (physical/LAN/WAN/LTE throughput, cellular RSRP) is a
**different query** and a later pass: CMA treats Socket CPU / port fill as a
*cause* of overlay loss, and a third HTTP POST is out of scope while we stay
inside the `accountMetrics` 15/minute floor.

### Will monitoring still work?

| Failure | Collector | What you should see |
|---|---|---|
| One WAN unplugged, another WAN still tunneled | Snapshot keeps working | Site `connected` + `isDegraded`; that port `mediaIn=false`; that WAN `connected=false`; reason `WAN_DISCONNECTED`; Health → Degraded yellow; Network → Ports WAN media red |
| WAN has Ethernet but ISP/path to PoP is dead | Snapshot keeps working | `mediaIn=true`, `hasTunnel=false`, reason `WAN_TUNNEL_DISCONNECTED`; last-mile sick or missing |
| All Socket WANs down | Site High already; account collector still polls other sites | Site `disconnected`. Last-mile for that site goes empty, not a fake 0% |
| LAN unplugged | Snapshot keeps working | Degraded with `LAN_*`; LAN media Warning — do not raise a circuit Average |
| CMA Degraded disabled in System Settings | Snapshot still has the object | Treat `isDegraded` as optional (`0` when absent); physical `mediaIn` / WAN `connected` remain the source of truth |

Do **not** page Cato overlay loss as an ISP cut at Forti sites. At Socket-only sites, last-mile + `WAN_DISCONNECTED` / `WAN_TUNNEL_DISCONNECTED` + `mediaIn` are the circuit class.

---

## What we alert

| Thing | Alert | Sev |
|---|---|---|
| One redundant `UW` / Forti WAN / SD-WAN member down | yes | **Average** — tagged as circuit, not fabric. Forti SD-WAN health-check is the authoritative underlay symptom; Extreme `UW` is the cause signal |
| Cato-only: one WAN unplugged or tunnel down while the site stays connected | yes | **Average** circuit — site Degraded + WAN `mediaIn=false` / `hasTunnel=false`. Not site High. Not LAN. |
| Last usable site underlay path lost | yes | **High** on the path; **Disaster** on the site (later parent) |
| Flapping | yes | Warning |
| Errors | yes | Warning |
| All circuits at a site down | yes | **Disaster** — site-level, not on the switch or Forti template |
| Util vs commit bandwidth | later | graph; Average only after Circuit bandwidth exists |
| Speed ≠ label | **no** | handoff speed rarely equals commit |

Do **not** alert on: fabric `USW` uplinks (01), Cato **overlay** loss/RTT (04), Cato last-mile (04, dashboard only), Cato LAN/LAG/HA degraded reasons.

---

## Scope

| Object | In | Out |
|---|---|---|
| Extreme WAN | `ifAlias` matching `^UW(-\|$)` | Fabric uplinks |
| Forti WAN | Forti WAN iface **or** SD-WAN health-check for that circuit (HTTP). Split `root` vs `Untrust` — they are different internet paths | Other Forti interfaces / policies |
| Cato-only Socket WAN | Last-mile + WAN snapshot / degraded `WAN_*` / `interfacesLinkState` on [04](04-cato.md). Sites with a FortiGate keep Forti as the probe | Overlay SLA, LAN ports, HA, IPsec Azure sites |

---

## Ops

No absolute speed-expect on `UW`. Commit rate lives on the NetBox Circuit, not in the port label.

---

## Templates

| Template | Where |
|---|---|
| ISP WAN Ports by SNMP (thin, build) | Extreme `UW` — dependent items on stock interface items where possible |
| FortiGate by HTTP (SD-WAN / WAN LLD) | [03](03-fortinet.md) **Path** Loss/Probe — not this SNMP template |
| Cato Networks by HTTP | Socket-only sites: last-mile, `degradedStatus`, and `interfacesLinkState` on the **existing** snapshot master. No `socketPortMetrics`. Filter Latest data by the `site` tag. |

---

## Later

NetBox Providers + Circuits populated; multi-homing modelled vs residual risk; compliance (termination without `UW`, and the reverse).

Cato collector (still two HTTP masters, still `--apply-cato`): last-mile is
timeseries on the metrics master (average of probe endpoints, no alert); USB
ports/tunnels are not discovered; ISP provider and other CHAR identity live on
Network → Tunnels **Details** / Latest, not History. Do not add
`socketPortMetrics` until the metrics budget is measured.
