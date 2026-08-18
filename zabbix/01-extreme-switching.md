# Extreme switching

EXOS and VOSS share alerts and the port-label grammar; they do not share MIBs. SNMP is the data path (these platforms do not stream gNMI). World-class here means: **page what users feel, never fail silent, one incident per root cause** — not a second poller.

Labels: [port-identity.md](port-identity.md). APs: [02-extreme-access-points.md](02-extreme-access-points.md). Scale: [_template.md](_template.md). Analysis: [notes/alerting-and-health.md](notes/alerting-and-health.md).

---

## Observability

| Rule | Here |
|---|---|
| Page **symptoms** | ICMP down (**High**). Temp **critical**. Site unreachable is **Disaster** (not on this template). |
| **Ticket** (Average) | SNMP dead, PSU/fan, optic DOM **alarm**, memory, unsupported-item count, in-scope **link down** (live stock trigger) |
| **Graph** / next day | CPU, traffic, util, ICMP loss/RTT (items on, triggers **off**), flaps, errors, duplex |
| One incident | host triggers depend on SNMP → ICMP; ICMP depends on **site** (later). AP cable/PoE pages on Access `UP-` — see [02](02-extreme-access-points.md) |
| Never silent | unsupported-item **Average** trigger; zero discovered interfaces = Health honeycomb/census; proxy last-seen |
| Control plane | on-box `ifAlias` + role macros. Access collects **only** `USW`+`UP`; a mistyped uplink → no items |
| Collect first | Speed Expect / Routing **imported, not linked**. Util off (`{$IF.UTIL.MAX}=101` and Speed Expect `{$IF.UTIL.MAX:"USW"}=101`). ISIS/card High **gated off** |
| Host dashboards | **Health** for the box; **Network interfaces** for the status map, traffic grid, and (switches) one-port **Port** page. |
| Severity | **Disaster** = site only. Warning = next day, not a dump bucket |

Do **not** stack Network Generic (`icmpping` collision). Mute a port with **`X`**, not `{$IFCONTROL:"{#IFNAME}"}`.

Scale: Info → Warning → Average → High → Disaster. Disaster+High page 24/7; Average = ticket; Warning = next day; Info = log.

---

## What we alert

**This table is the live cutover contract** (YAML + stock EXOS after `--apply`). Class-scoped High and Speed Expect stay in [Later](#later).

| Device | Alert | Sev |
|---|---|---|
| ICMP down | yes | **High** |
| SNMP dead (ICMP still up) | yes | **Average** on VOSS. Stock EXOS stays **Warning** (do not fork) |
| Unplanned reboot | yes | Warning |
| Temperature **critical** (100 °C) / vendor alarm | yes | **High** |
| Temperature warning (95 °C) | yes | Warning — next day; not stock 55 |
| Temperature too low | **no** | `{$TEMP_CRIT_LOW}=-273` silences stack/VM 0 °C |
| PSU / fan failed | yes | Average |
| CPU high | yes | Warning — baseline first |
| Memory high | yes | Average — baseline first |
| Optic DOM **status** alarm (VOSS) | yes | Average — prefer status, not raw dBm |
| Unsupported item count | yes | Average — `{$UNSUPPORTED.MAX}` (default 5), 30m |
| Firmware / OS / serial change | yes | Info |
| System name changed | stock **Info** | disable in Zabbix if it chatters |
| ICMP loss / RTT | **no** | items on; triggers **DISABLED** (CH proxy RTT is WAN) |
| ISIS circuit / card down | collect | High **gated** (`{$ISIS.CONTROL}=0`, `{$CARD.CONTROL}=0`) until a fabric pilot |
| V-IST / IST | collect | High gated (`{$VIST.CONTROL}=0`, `{$IST.CONTROL}=0`) |
| **Site** unreachable | yes | **Disaster** — site-level, **not** on EXOS/VOSS (later) |

| Ports in scope | Alert | Live (cutover) | Later |
|---|---|---|---|
| `USW` / `US` / `UP` link down | yes | **Average** (one stock trigger for every discovered port) | class-scoped **High** for `USW`/`UP` |
| `MON` link down | yes | Average — Core/Dist/Mgmt only | Warning |
| `UW` link down | yes | Average — Core/Dist/Mgmt | **High**; all circuits at a site → **Disaster** |
| Link flapping | yes | Warning — VOSS has a counter; EXOS stock does not | — |
| Wrong speed vs **intended** label | later | Speed Expect YAML triggers **on** — **do not link** | Warning |
| Half duplex | yes | Warning | — |
| Interface errors | yes | Warning | — |
| Outbound discards (`USW`) | later | Speed Expect, not linked; util context **101** | Average (user impact) |
| Sustained util vs **intended** speed | **no** | stock 15m off (`{$IF.UTIL.MAX}=101`); Speed Expect `USW` also **101** | Warning, 1h avg, stage 6 |
| `X…` ports | **no** | not discovered | — |

Do **not** alert on: a laptop unplugging (Access **does not collect** desk ports), fifty **High**s for one site down, “bandwidth high” on a backup window.

Until class-scoped High exists, a Core `USW` down is a **ticket**. ICMP High still catches a dead box. Access still cannot page a desk port — those items do not exist.

---

## Health dashboard (host, from the template)

Not a country/role board. After the platform template is linked, **Monitoring → Hosts → host → Dashboards → Health**.

Widget type follows the object count and the question. Honeycomb is only for **many similar things** (ports, fans, sensors). A gauge is for **one headline number with a scale** (ICMP, SNMP, CPU, Temp). Uptime is an **item** tile — a duration, not 0–100. A graph is for **trend**. Do not put a single memory pool in a honeycomb: on Access EXOS that becomes one giant hex titled Memory.

| Page | What you see in 5 seconds |
|---|---|
| **Overview** | ICMP / SNMP / CPU / **Uptime** — same four tiles on EXOS, VOSS, and IQ. Problems. Compute trend (CPU+memory on EXOS/IQ; CPU on VOSS) plus Uptime history. |
| **Hardware / RF** | Switches: fan/PSU colour. EXOS also chassis Temp gauge + trend (scalar `extremeCurrentTemperature`). VOSS also named °C and PSU watts, then per-slot memory. IQ RF: radio noise map, client census, Tx / retries grids. |

**Network interfaces → Overview** is the status map + 3×2 traffic grid. Each hex is the **port ID** (`1:1`, `1/21`, `eth0`) — not the IFALIAS paragraph — with Auto type so the ID stays readable. Colour is oper-status; hover still shows the full item. Switch maps are **72×6** (traffic at y=6, **height 14**): Zabbix floors honeycomb cells at 32px and then hides labels that do not fit, so a height-3 strip on a Core/Dist VOSS (every admin-up port except `X`) paints nameless hexes in a modest window. IQ maps are **12×3** — Zabbix has no max cell size, and ~2 AP eth in a switch-sized widget are giant hexes. Traffic is the same **height 14** 3×2 grid on all three. **Port** (VOSS YAML / EXOS `--apply` on stock **Extreme EXOS by SNMP**, not the Observability companion) is the one-port fault picker (status/speed/duplex/errors/discards, VOSS flaps) — not bits. IQ has no Port page. Zabbix 7 cannot open a hex into a graph. Ethernet is full duplex: do **not** sum RX+TX for congestion.

Util and intended-speed comparison stay graphs until Speed Expect is linked.

---

## Scope

| Role | Collect (admin-up physical/LAG) | Do not collect |
|---|---|---|
| Switch Core / Dist / Mgmt | **Every** admin-up port except `X…` | `X…`; **admin-down** is not discovered |
| Switch Access | **Only** `USW` (to Dist) and `UP` (to AP) | Desk / laptop / `US` / `MON` / `UW` / `TMON` / unlabelled / `N…` / `X…` |

Access is two labels, full stop. Unlabelled Access ports produce **no items**. Dist / Core / Mgmt alert if an admin-up port goes down, labelled or not (except `X`). Do not leave a desk port admin-up on Dist.

**`X` excludes. `N` does not** (Core/Dist/Mgmt). Stack / ISC / MLAG peer / SPAN need **`X`**. Unused: **admin-down**.

| Role | `{$NET.IF.IFALIAS.MATCHES}` | `{$NET.IF.IFALIAS.NOT_MATCHES}` | `{$NET.IF.IFTYPE.MATCHES}` |
|---|---|---|---|
| Core / Dist / Mgmt | `.*` | `^X(-\|$)` | `^(6\|161)$` |
| Access | `^(USW\|UP)(-\|$)` | `CHANGE_IF_NEEDED` | `^(6\|161)$` |

Access must also override Speed Expect or `US`/`MON` leak in: `{$PORTID.LLD.IFALIAS.MATCHES}` = `^(USW|UP)(-|$)`.

There is no Switch Hybrid role. `^(6|161)$` drops EXOS VLAN ifaces.

NetBox: those Access macros on role Switch Access. Locked checklist §11.1 still has the wider `USW|US|UP|MON|UW|TMON` pattern — **the live role value is the tighter regex.**

---

## Zero-touch (nbxSync)

New switch: NetBox **platform** contains `EXOS` or `VOSS`, **role** is Switch Core/Dist/Access/Mgmt, site in a country SiteGroup. First HostSync:

1. Template Rule → `Extreme EXOS Observability` (nests stock **Extreme EXOS by SNMP**) or `Extreme VOSS by SNMP` + `OS/Network` hostgroup. Zabbix host view shows `Extreme EXOS Observability (Extreme EXOS by SNMP)` — that is the companion, not a second poller.  
2. Role MacroAssignment → IFALIAS / IFTYPE (Access also `PORTID.*`)  
3. Configuration Group **SNMP Monitoring** → SNMPv3 interface  
4. Template **Health** dashboard is already on the template — no extra dashboard script  

Re-run `configure_nbxsync_zerotouch.py` then `configure_nbxsync_network.py --apply` on an estate that **already has** switches in Zabbix:

- Does **not** delete hosts, interfaces, history, or hostids  
- YAML `deleteMissing: false` — retired items linger; we do not wipe LLD  
- Does **not** mass-sync every device (template updates inherit in Zabbix)  
- Does **not** unlink Speed Expect if it was linked earlier (no `--link-speed-expect` ≠ unlink)  
- Does **not** run `create_dashboards.py`  
- Empty SNMP secrets in env must not overwrite existing CG passphrases (zerotouch)  
- Idempotent patches: TEMP_*, EtherLike IFALIAS, EXOS IF LLD 15m/keep-lost 0, EXOS PSU LLD skip `notPresent`, EXOS ICMP loss/RTT disable and stock **Network interfaces** 3×2 layout; Health comes from YAML/companion

Per-host sync only when **that** device’s NetBox role/platform/macros changed.

---

## Ops

Production poller for NL/US/CH is the **Swiss proxy group**, SNMPv3 `MONITORING` **MD5/DES**, GETBULK. A laptop `snmpget` does not prove that path. ICMP Up only proves ping.

After a **reboot**, if CLI SNMPv3 from the proxy works but Zabbix stays SNMP=0: RFC 3414 engine boots. Reload `zabbix_proxy -R snmp_cache_reload` or re-sync the host. If CLI from the proxy times out: UDP 161 / allow-list, not the template.

Platform names must match Template Rules: **EXOS**, **VOSS** (case-insensitive substring).

Grammar: EXOS `display-string` (max 20), leave `description-string` empty. VOSS interface `name` → `ifAlias`. Do not use `rcPortName`.

---

## Dependencies

```
util / speed-expect  →  link down  →  no SNMP  →  ICMP down  →  site unreachable
CPU / mem / temp     →  ICMP down
AP ICMP              →  Access UP-   (later — see 02)
```

A site WAN blip must not be one High per switch. Those Highs **depend on** a site **Disaster** (proxy / core / synthetic) — **later**. Until then, expect N ICMP Highs for a WAN cut.

---

## Watch the watcher

| Check | Why | Live |
|---|---|---|
| Unsupported item count | SNMP walk died; looks like health | Average trigger `{$UNSUPPORTED.MAX}` |
| Switch with **zero** discovered interfaces | IFALIAS regex or LLD broken | Health / census (no trigger yet) |
| SNMP = 0, ICMP = 1 | credentials / proxy cache / UDP 161 — not a forwarding outage | SNMP Average |
| Proxy last-seen | hosts go *unknown*, not *down* | Zabbix internal / later |

---

## EXOS

| Template | Where |
|---|---|
| Extreme EXOS Observability | Platform EXOS Template Rule; links the stock template and owns **Health** |
| Extreme EXOS by SNMP (stock) | Parent of the companion; owns the native **Network interfaces** graph prototype/dashboard |

We do **not** fork or add dashboards to the stock template. `--apply` idempotently sets `{$TEMP_WARN}=95`, `{$TEMP_CRIT}=100`, `{$TEMP_CRIT_LOW}=-273`, aligns EtherLike/interface LLD, skips EXOS PSU `notPresent` stack-MIB padding, disables ICMP loss/RTT noise and changes only the existing **Network interfaces** dashboard layout to the shared map + 3×2 grid plus a **Port** page. The companion carries calculated mirrors for Health (ICMP/CPU/memory/uptime, including slot-1 memory) and owns **Health** (Overview / Hardware). Overview 4th tile is Uptime, same as VOSS/IQ — not Temp. Chassis temp lives on Hardware as a gauge next to Fans/PSU. Memory is on Overview with CPU, not a Hardware honeycomb — Zabbix svggraph item patterns on the companion throw `Array to string conversion` in `CSvgGraphHelper::getMetricsPattern`.

Stock EXOS trigger severities stay upstream except those patches. SNMP-dead on stock is typically Warning until we match VOSS (Average) without a fork.

---

## VOSS

| Template | Where |
|---|---|
| Extreme VOSS by SNMP | Platform VOSS |

Same `{$TEMP_*}` on **this template**. Re-import after this revision. Fleet macros (template / globals, not Switch* role):

```
{$OPTIC.TEMP.CRIT}     = 70
{$OPTIC.TEMP.MAX}      = 150
{$OPTIC.RX.DBM.MIN}    = -100
{$OPTIC.DOM.ALARM_HIGH}= 3
{$OPTIC.DOM.ALARM_LOW} = 5
{$MLT.CONTROL}         = 1
{$VIST.CONTROL}        = 0
{$IST.CONTROL}         = 0
{$ISIS.CONTROL}        = 0
{$CARD.CONTROL}        = 0
{$UNSUPPORTED.MAX}     = 5
{$SNMP.TIMEOUT}        = 5m
{$IF.UTIL.MAX}         = 101
```

V-IST: host `{$VIST.CONTROL}=1` only on fabric pairs. Classic IST stays 0. Fabric High (ISIS/card) stays collected; set the CONTROL macro to `1` on a canary **after** a quiet pilot — not on `--apply`. Traps: collect; do not page duplicates of polled items until seen on hardware.

Poll weight (same idea as APs, more SNMP budget on a chassis): inventory **1h**; IF counters **3m**; oper-status default **1m**; chassis temp **1m**; optic DOM **5m** (Average tickets, not 03:00). Duplex LLD **15m** / keep-lost **0**, same as `net.if.discovery`. Uptime **1m** (reboot Warning still sees `< 10m`). Do not 1-minute every optic on a Core.

---

## Both platforms

| Template | Where | Triggers |
|---|---|---|
| Extreme Port Speed Expect by SNMP | Switch Core / Dist / Access / Mgmt | YAML **on**. **Do not assign** on Switch roles until labels are clean. `{$IF.UTIL.MAX:"USW"}=101` (off) |
| Extreme Routing by SNMP (OSPF) | Switch Core / Dist | YAML **on** (OSPF High). **Not linked** |

Speed Expect uses its **own** LLD macros (not `{$NET.IF.*}`). Default (Core/Dist/Mgmt):

```
{$PORTID.LLD.IFALIAS.MATCHES} = ^(USW|US|UP|MON)(-|$)
{$PORTID.LLD.IFTYPE.MATCHES}  = ^6$
```

On **Access**, override MATCHES to `^(USW|UP)(-|$)`.

Intended speed = token or class default (`USW` 10G, `UP` 1G). Live `ifHighSpeed` is compared in **Mbps**. Util (when enabled) is `% of intended`, 1h — not live speed.

---

## Later

Class-scoped link-down High (`USW`/`UP`); OSPF count; USW util + discards after history; `{$ISIS.CONTROL}=1` / `{$CARD.CONTROL}=1` on fabric canaries; sFlow on a few Core `USW`; one synthetic ping per site as the **Disaster** SLI; NetBox vs live `ifAlias`; AP ICMP → `UP-`; syslog on the proxy; `walk[]` when we retune poll load; EXOS SNMP-dead → Average without forking stock.

FortiGate (API) and network VMs reuse this bar ([03](03-fortinet.md), [06](06-network-vms.md)). Do not merge with Cato ([04](04-cato.md)).
