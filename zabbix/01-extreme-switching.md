# Extreme switching

EXOS and VOSS share alerts and the port-label grammar; they do not share MIBs. SNMP is the data path (these platforms do not stream gNMI). World-class here means: **page what users feel, never fail silent, one incident per root cause** — not a second poller.

Labels: [port-identity.md](port-identity.md). APs: [02-extreme-access-points.md](02-extreme-access-points.md). Scale: [_template.md](_template.md). Analysis: [notes/alerting-and-health.md](notes/alerting-and-health.md).

---

## Observability

| Rule | Here |
|---|---|
| Page **symptoms** | ICMP down (**High**). Temp **critical**. |
| **Ticket** (Average) | PSU/fan, optic DOM **alarm**, memory, unsupported-item count, **any discovered** link down |
| **Graph** / next day | SNMP dead (**Warning** — same on EXOS/VOSS/IQ), CPU, traffic, util, ICMP loss/RTT (items on, triggers **off**), flaps, errors, duplex |
| One incident | host triggers depend on SNMP → ICMP. Cable/PoE toward an AP is switch `UP-` Average plus AP ICMP High. |
| Never silent | unsupported-item **Average**; **zero discovered interfaces** Average after SNMP is up 1h; proxy last-seen |
| Control plane | on-box `ifAlias` + role macros. Access collects **only** `USW`+`UP`; a mistyped uplink → no items |
| Collect first | Speed Expect **nested** on VOSS / EXOS Observability (empty `ifAlias` = not discovered). Routing **imported, not linked**. Util off (`101`). ISIS/card High **gated off** |
| Host dashboards | **Health** for the box; **Network interfaces** for the status map, traffic grid, and (switches) one-port **Port** page. |
| Severity | **Disaster** = site only. Warning = next day, not a dump bucket |

Do **not** stack Network Generic (`icmpping` collision). Mute a labelled data port with **`X`**, not `{$IFCONTROL:"{#IFNAME}"}`. Unused chassis OOB (`VOSS` ifName `mgmt`, `EXOS` ifName `Management` / alias `MgmtPort`) is skipped in `{$NET.IF.IFNAME.NOT_MATCHES}` — it is not connected and is not a grammar port.

Scale: Info → Warning → Average → High → Disaster. Disaster+High page 24/7; Average = ticket; Warning = next day; Info = log.

---

## What we alert

**This table is the live cutover contract** (YAML + stock EXOS after `--apply`).

| Device | Alert | Sev |
|---|---|---|
| ICMP down | yes | **High** |
| SNMP dead (ICMP still up) | yes | **Warning** on VOSS, IQ, and stock EXOS — mgmt blind; forwarding / Wi-Fi may still work |
| Unplanned reboot | yes | Warning |
| Temperature **critical** (100 °C) / vendor alarm | yes | **High** |
| Temperature warning (95 °C) | yes | Warning — next day; not stock 55 |
| Temperature too low | **no** | `{$TEMP_CRIT_LOW}=-273` silences stack/VM 0 °C |
| PSU / fan failed | yes | Average — installed PSU not supplying power (down, unknown, or unpowered), not only a down transition |
| CPU high | yes | Warning — baseline first |
| Memory high | yes | Average — baseline first |
| Optic DOM **status** alarm (VOSS) | yes | Average — prefer status, not raw dBm |
| Unsupported item count | yes | Average — `{$UNSUPPORTED.MAX}` (default 5), 30m |
| Zero discovered interfaces (SNMP up 1h) | yes | Average — IFALIAS/LLD break; Access with no `USW`/`UP` is this ticket |
| Firmware / OS / serial change | yes | Info |
| System name changed | stock **Info** | disable in Zabbix if it chatters |
| ICMP loss / RTT | **no** | items on; triggers **DISABLED** (CH proxy RTT is WAN) |
| ISIS circuit / card down | collect | High **gated** (`{$ISIS.CONTROL}=0`, `{$CARD.CONTROL}=0`) until a fabric pilot |
| V-IST / IST | collect | High gated (`{$VIST.CONTROL}=0`, `{$IST.CONTROL}=0`) |
| **Site** unreachable | not on this template | Needs a site check — not EXOS/VOSS |

| Ports in scope | Alert | Live (cutover) |
|---|---|---|
| Discovered link down (Core/Dist/Mgmt admin-up; Access grammar `display-string`) | yes | **Average** — one trigger on **EXOS and VOSS**, including never-up and `lowerLayerDown`. Unlabelled Access desk = not discovered and `{$LINKDOWN.IFALIAS}` stays 0. |
| Link flapping | yes | Warning — VOSS has a counter; EXOS stock does not |
| Wrong speed vs **intended** label | **armed** | Nested; **no items** until `USW`/`US`/`UP`/`MON`. Then **Warning**, not a page |
| Half duplex | yes | Warning |
| Interface errors | yes | Warning |
| Outbound discards (`USW`) | **no** | Speed Expect discards trigger is **DISABLED** until a pps baseline |
| Sustained util vs **intended** speed | **no** | stock 15m off (`{$IF.UTIL.MAX}=101`); Speed Expect `USW` also **101** |
| `X…` ports | **no** | not discovered |

Do **not** alert on: a laptop unplugging on Access (those ports are not collected), fifty **High**s for one site down, “bandwidth high” on a backup window.

On Core/Dist/Mgmt, **admin-up is the contract**: only important ports should be up. On **Access**, a grammar **display-string** (`USW` / `US` / `UP` / `MON` / `UW` / `TMON`) is the same contract — that port should be live. Link-down is a real path loss or a labelled port that never came up; both get a **ticket**. Unlabelled Access desk/laptop ports are not discovered (a laptop unplug stays silent). Same Average for every discovered class. Do **not** page it: pikett cannot restore an array at 03:00, and cleaning unused ports is not a night job. High is ICMP (the box is gone) and overtemp. If the *storage switch itself* must wake someone, that is the host `critical` tag, not a special `US` trigger.

---

## Health dashboard (host, from the template)

After the platform template is linked, **Monitoring → Hosts → host → Dashboards → Health**.

Widget type follows the object count and the question. Honeycomb is only for **many similar things** (ports, fans, sensors). A gauge is for **one headline number with a scale** (ICMP, SNMP, CPU, Temp). Uptime is an **item** tile — a duration, not 0–100. A graph is for **trend**. Do not put a single memory pool in a honeycomb: on Access EXOS that becomes one giant hex titled Memory.

| Page | What you see in 5 seconds |
|---|---|
| **Overview** | ICMP / SNMP / CPU / **Uptime** — same four tiles on EXOS, VOSS, and IQ. Problems. Compute trend (CPU+memory on EXOS/IQ; CPU on VOSS) plus Uptime history. |
| **Hardware / RF** | Switches: fan/PSU colour. EXOS also chassis Temp gauge + trend (scalar `extremeCurrentTemperature`). VOSS also named °C and PSU watts, then per-slot memory. IQ RF: radio noise map, client census, Tx / retries grids. |

**Network interfaces → Overview** is the status map + 3×2 traffic grid. Each hex is the **port ID** (`1:1`, `1/21`, `eth0`) — not the IFALIAS paragraph — with Auto type so the ID stays readable. Colour is oper-status; hover still shows the full item. Switch maps are **72×6** (traffic at y=6, **height 14**): Zabbix floors honeycomb cells at 32px and then hides labels that do not fit, so a height-3 strip on a Core/Dist VOSS (every admin-up port except `X`) paints nameless hexes in a modest window. IQ maps are **12×3** — Zabbix has no max cell size, and ~2 AP eth in a switch-sized widget are giant hexes. Traffic is the same **height 14** 3×2 grid on all three. **Port** (VOSS YAML / EXOS `--apply` on stock **Extreme EXOS by SNMP**, not the Observability companion) is the one-port fault picker (status/speed/duplex/errors/discards, VOSS flaps) — not bits. IQ has no Port page. Zabbix 7 cannot open a hex into a graph. Ethernet is full duplex: do **not** sum RX+TX for congestion.

Util and intended-speed stay Latest data until a port has a class label. Honeycomb stays oper-status.

---

## Scope

| Role | Collect (admin-up physical/LAG) | Do not collect |
|---|---|---|
| Switch Core / Dist / Mgmt | **Every** admin-up port except `X…` | `X…`; **admin-down** is not discovered |
| Switch Access | Grammar classes: `USW` `US` `UP` `MON` `UW` `TMON` | Unlabelled desk / laptop / `N…` / `X…` |

Access is **opt-in by CLASS** (the display-string). Unlabelled Access ports produce **no items**. A labelled Access port that is oper-down **does** Average-ticket, including never-up. Dist / Core / Mgmt: if it is admin-up, it is in — labelled or not (except `X`). Unused ports must be **admin-down**, not left up “with nothing connected”. The Average itself also requires `{$LINKDOWN.IFALIAS:"{#IFALIAS}"}=1`: template default is `1` (Core/Dist/Mgmt, empty alias still tickets); Switch Access sets default `0` and regex `^(USW|US|UP|MON|UW|TMON)(-|$)` = `1`.

**`X` excludes. `N` does not** (Core/Dist/Mgmt). Stack / ISC / MLAG peer-links are **`USW`** (alert). SPAN / operator-mute need **`X`**. Unused: **admin-down**.

| Role | `{$NET.IF.IFALIAS.MATCHES}` | `{$NET.IF.IFALIAS.NOT_MATCHES}` | `{$NET.IF.IFTYPE.MATCHES}` |
|---|---|---|---|
| Core / Dist / Mgmt | `.*` | `^X(-\|$)` | `^(6\|161)$` |
| Access | `^(USW\|US\|UP\|MON\|UW\|TMON)(-\|$)` | `CHANGE_IF_NEEDED` | `^(6\|161)$` |

Access also sets `{$LINKDOWN.IFALIAS}=0` and `{$LINKDOWN.IFALIAS:regex:"^(USW|US|UP|MON|UW|TMON)(-|$)"}=1`. Core/Dist/Mgmt inherit the template default `{$LINKDOWN.IFALIAS}=1`.

Access Speed Expect uses `{$PORTID.LLD.IFALIAS.MATCHES}` = `^(USW|US|UP|MON)(-|$)` (same as the template default). `UW` / `TMON` get link/error items from stock LLD, not a speed Warning.

There is no Switch Hybrid role. `^(6|161)$` drops EXOS VLAN ifaces.

NetBox: those Access macros on role Switch Access. Live role values match locked checklist §11.1.

---

## Zero-touch (nbxSync)

New switch: NetBox **platform** matches `EXOS|Switch Engine` or `VOSS|Fabric Engine`, **role** is Switch Core/Dist/Access/Mgmt, site in a country SiteGroup. First HostSync:

1. Template Rule → `Extreme EXOS Observability` (nests stock **Extreme EXOS by SNMP** and **Port Speed Expect**) or `Extreme VOSS by SNMP` (nests Speed Expect) + `OS/Network` hostgroup. Zabbix host view shows `Extreme EXOS Observability (Extreme EXOS by SNMP)` — that is the companion, not a second poller. Empty port labels do not create Speed Expect items.  
2. Role MacroAssignment → IFALIAS / IFTYPE (Access also `PORTID.*`)  
3. Configuration Group **SNMP Monitoring** → SNMPv3 interface  
4. Template **Health** dashboard is already on the template — no extra dashboard script  

Re-run `configure_nbxsync_zerotouch.py` then `configure_nbxsync_network.py --apply` on an estate that **already has** switches in Zabbix:

- Does **not** delete hosts, interfaces, history, or hostids  
- YAML `deleteMissing: false` — retired items linger; we do not wipe LLD  
- Does **not** mass-sync every device (template updates inherit in Zabbix). Speed Expect nests on VOSS / Observability, so existing switch hosts pick up the LLD on `--apply` without HostSync. Empty display-string → nothing discovered.  
- Empty SNMP secrets in env must not overwrite existing CG passphrases (zerotouch)  
- Idempotent patches: TEMP_*, EtherLike IFALIAS, EXOS IF LLD 15m / disable-lost immediately / delete after 7d, chassis OOB ifName skip (`mgmt` / `Management`), EXOS PSU LLD keep installed FRUs (status not notPresent **or** a real serial; LLD JS defaults missing `{#PSU.SERIAL}` and wipes dummy `--`; API AND/OR updates omit `formulaid` — GET still shows `A or B`) and **VOSS PSU LLD skip empty(2) even with dummy serial `--`**, **delete lost VOSS PSU rows immediately**, PSU Average `last()<>{$PSU.OK_STATUS}` (VOSS also `and last()<>{$PSU.EMPTY_STATUS}`) so two present / one connected tickets without empty-bay noise, EXOS/VOSS link-down Average without `.diff()` (admin-up + oper **not up**, including `lowerLayerDown(7)`), Access `{$LINKDOWN.IFALIAS}` grammar gate, Speed Expect `event_name` ASCII `!=` (YAML import can leave `≠` / `Γëá`; open Problems keep the create-time title), EXOS ICMP loss/RTT disable and stock **Network interfaces** 3×2 layout; Health comes from YAML/companion. Leftover Speed Expect **role** assignments are pruned (the template is nested).  
- `--apply` writes Switch Access Zabbix **host** macros for IFALIAS / PORTID / `{$LINKDOWN.IFALIAS}` (grammar regex `USW|US|UP|MON|UW|TMON`). That is not HostSync and does not rewrite Core/Dist/Mgmt. Unlabelled Access desk ports then leave LLD (disable-now) and the Average cannot fire without a proper display-string. Core/Dist/Mgmt still ticket every admin-up port except `X`. Remaining Switch* drift is logged only.
- `{$PORTID.LLD.*}` defaults live on **Extreme Port Speed Expect**. `--apply` will delete leftover Zabbix **global** PORTID macros (they bump config for every host).

Per-host sync only when **that** device’s NetBox role/platform/macros changed.

---

## Ops

Production poller for NL/US/CH is the **Swiss proxy group**, SNMPv3 `MONITORING` **MD5/DES**, GETBULK. A laptop `snmpget` does not prove that path. ICMP Up only proves ping.

After a **reboot**, if CLI SNMPv3 from the proxy works but Zabbix stays SNMP=0: RFC 3414 engine boots. Reload `zabbix_proxy -R snmp_cache_reload` or re-sync the host. If CLI from the proxy times out: UDP 161 / allow-list, not the template.

Platform names must match Template Rules (case-insensitive `re.search`): **`EXOS|Switch Engine`**, **`VOSS|Fabric Engine`**. Extreme renamed Universal hardware in 31.6 / 8.6; a platform named only `Switch Engine` used to miss the EXOS rule.

Grammar: EXOS `display-string` (max 20), leave `description-string` empty. VOSS interface `name` → `ifAlias`. Do not use `rcPortName`.

---

## Dependencies

```
util / speed-expect  →  link down  →  no SNMP  →  ICMP down
CPU / mem / temp     →  ICMP down
```

A site WAN blip is one ICMP High per switch. That is accepted.

---

## Watch the watcher

| Check | Why | Live |
|---|---|---|
| Unsupported item count | SNMP walk died; looks like health | Average trigger `{$UNSUPPORTED.MAX}` |
| Switch with **zero** discovered interfaces | IFALIAS regex or LLD broken | Average after SNMP up 1h (`{$NET.IF.DISCOVERY.MIN}=1`). Count item stays **0 (supported)** while empty so it recovers when LLD creates a port — not nodata / Not supported. ICMP down is not this ticket. |
| SNMP = 0, ICMP = 1 | credentials / proxy cache / UDP 161 — not a forwarding outage | SNMP Warning |
| Proxy last-seen | hosts go *unknown*, not *down* | Zabbix internal / later |

---

## EXOS

| Template | Where |
|---|---|
| Extreme EXOS Observability | Platform EXOS Template Rule; nests stock **Extreme EXOS by SNMP** + **Port Speed Expect**; owns **Health** |
| Extreme EXOS by SNMP (stock) | Parent of the companion; owns the native **Network interfaces** graph prototype/dashboard |

We do **not** fork or add dashboards to the stock template. `--apply` idempotently sets `{$TEMP_WARN}=95`, `{$TEMP_CRIT}=100`, `{$TEMP_CRIT_LOW}=-273`, aligns EtherLike/interface LLD (15m, disable-lost immediately, delete after 7d), skips EXOS PSU padding (`notPresent` with no real serial — padding slots often omit the serial OID, so LLD JS defaults `{#PSU.SERIAL}` to empty and wipes dummy `--` before the filter), tickets installed PSUs that are not `presentOK` (`presentNotOK`, `presentPowerOff`, or serialled `notPresent`), keeps discovered link-down **Average** (drops leftover USW High), disables ICMP loss/RTT noise and changes only the existing **Network interfaces** dashboard layout to the shared map + 3×2 grid plus a **Port** page. Stock EXOS `net.if.discovery` is classic SNMP OID LLD, not `walk[`/`get[`, so the rule `timeout` field must stay empty (proxy/global SNMP timeout). The companion carries calculated mirrors for Health (ICMP/CPU/memory/uptime, including slot-1 memory), the zero-interface Average trigger, and owns **Health** (Overview / Hardware). Overview 4th tile is Uptime, same as VOSS/IQ — not Temp. Chassis temp lives on Hardware as a gauge next to Fans/PSU. Memory is on Overview with CPU, not a Hardware honeycomb — Zabbix svggraph item patterns on the companion throw `Array to string conversion` in `CSvgGraphHelper::getMetricsPattern`.

Stock EXOS trigger severities stay upstream except those patches. SNMP-dead is **Warning** on EXOS, VOSS, and IQ.

---

## VOSS

| Template | Where |
|---|---|
| Extreme VOSS by SNMP | Platform VOSS; nests **Port Speed Expect** |

Same `{$TEMP_*}` on **this template**. Re-import after this revision. PSU LLD keeps a row when status is not `empty(2)`. Firmware often fills serial with `--` on every bay (canary CH-STA-L26-L02-MGMT03 — one PSU installed, PSU 2 `empty(2)` / `--`); that dummy is not a FRU. Fitted-unplugged is `unknown(1)` or `down(4)`, not empty. Lost padding is **deleted** immediately (`lifetime: 0`). Average is `last()<>{$PSU.OK_STATUS} and last()<>{$PSU.EMPTY_STATUS}` so leftover empty rows recover before LLD delete. `--apply` queues check-now so padding leaves Health without HostSync. Fleet macros (template / globals, not Switch* role):

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

Poll weight (same idea as APs, more SNMP budget on a chassis): inventory **1h**; IF counters **3m**; oper-status default **1m**; chassis temp **1m**; optic DOM **5m** (Average tickets, not 03:00). Duplex LLD **15m**, same as `net.if.discovery`. Lost **interface** LLD resources: **disable immediately**, **delete after 7d** (not delete-now). A discovery rule that goes **not supported** (SNMP timeout) does not process lost resources — a full outage is a graph gap, history stays. Immediate delete is how a truncated GETBULK or a wrong IFALIAS filter wipes interface history. **VOSS PSU** LLD is the exception: **delete lost immediately** (`lifetime: 0`) — Health honeycomb keeps lastvalue on a disabled item, so a 7d lifetime leaves `empty(2)` hexes visible. Uptime **1m** (reboot Warning still sees `< 10m`). Do not 1-minute every optic on a Core.

---

## Both platforms

| Template | Where | Triggers |
|---|---|---|
| Extreme Port Speed Expect by SNMP | Nested on VOSS + EXOS Observability | Mismatch Warning **on**. Duplicate link-down and discards **DISABLED**. Util `{$IF.UTIL.MAX:"USW"}=101` (off) |
| Extreme Routing by SNMP (OSPF) | Switch Core / Dist | YAML **on** (OSPF High). **Not linked** |

Speed Expect uses its **own** LLD macros (not `{$NET.IF.*}`). Defaults live on **that template** (not Zabbix globals). Core/Dist/Mgmt:

```
{$PORTID.LLD.IFALIAS.MATCHES} = ^(USW|US|UP|MON)(-|$)
{$PORTID.LLD.IFTYPE.MATCHES}  = ^6$
```

On **Access**, the same PORTID MATCHES value is assigned on the role so HostSync overwrites a leftover `USW|UP`-only host macro.

### How intended speed works

The on-box label **is** the contract. Live `ifHighSpeed` (IF-MIB, million bits/s → we store **Mbps**) is observed state.

| Label | Expected (Mbps) | Why |
|---|---|---|
| `USW-C02_1` | 10000 | class default `USW` = 10G |
| `US-SAN02_CT0_10` | 10000 | class default `US` = 10G — **wrong** if the array is 25G/100G; write `US-25G-SAN02_CT0_10` |
| `UP-L02-AP07` | 1000 | class default `UP` = 1G — **wrong** if the AP is 2.5G; write `UP-2G5-L02-AP07` |
| `UP-2G5-L02-AP07` | 2500 | token overrides the class default |
| `USW-1G-GFL-A01_23` | 1000 | Dist↔Access copper that is really 1G |
| `MON-ESX40_ILO10_1` | 1000 | class default `MON` = 1G |
| `UW-SC1` | — | **not in this LLD**. PHY speed ≠ circuit commit (05) |
| unlabelled Dist port | — | **not in this LLD**. Platform still Average-tickets link-down. No intended speed without a class |

LLD JS parses `CLASS[-SPEED]-ID` into `{#IF.CLASS}` + `{#IF.SPEED.EXPECTED}`. Only **physical ethernet** (`ifType=6`). LAG/MLT aggregates report **summed** speed and would sit in problem forever — they stay on the platform template for link-down/errors, not here.

**Operator view:** nothing, until a port has a class label. Then, within **15m** LLD:

- **Problems:** Warning, next day — `Port identity: Interface 23(USW-GFL-A01_23): Speed 1000 Mbps != expected 10000 Mbps (class USW)`. Titles are ASCII `!=` (`≠` showed as `Γëá` in tickets). `--apply` force-patches live prototypes; already-open Problems keep the title from create until they recover.
- **Network interfaces → Overview** honeycomb stays **oper-status**. Do not paint hexes by Mbps (10G vs 1G vs 2.5G is not a colour scale).
- **Network interfaces → Port** already shows live **Speed** (platform item, bps after ×1e6) + duplex. That is the “what is it now” pane. The Warning is “what should it be”.
- **Latest data** grows `Speed (speed-expect)` in Mbps (`units: !Mbps` — without `!`, Zabbix prints `10 KMbps` for a 10 Mbps link). Util-%-of-intended helpers are later; they are **% of the label**, 1h average — not stock 15m vs live speed.
- Stock/VOSS **“Ethernet has changed to lower speed”** stays as a change-detect safety net until this LLD is proven. It has a hole: `10G → down → up at 1G` often never fires (speed reads 0 while down). Absolute expect exists because of that hole. After a quiet pilot, disable the stock change-detect so one mismatch is not two Warnings.

**Severity (SRE):** wrong speed still forwards. Dayside checks cable / SFP / autoneg **or** fixes the label. Do **not** High it (pikett cannot make autoneg 10G at 03:00). Do **not** Average it (that queue is link-down / unused-port cleanup). Warning = next day. If the 1G pipe is actually dropping users, **discards** (later) is the impact signal. If the box is gone, **ICMP**.

**Empty display-string is the safe case.** LLD filter is `^(USW|US|UP|MON)(-|$)`. No class → no Speed Expect items → no Warnings. Building production without labels does **not** need a census first. Arm it now (`--apply` nests the template). The 15m discovery starts the day you write `USW-…` / `US-25G-…` / `UP-2G5-…`.

**Dirty labels are the noisy case** — class present, token wrong (`US-SAN02_CT0_10` on a 25G array, `UP-L02-AP07` on a 2.5G AP). That Warning *is* the census: fix the token. Changing a class default later (`USW` 10G → 25G) silently re-values every tokenless label; freeze defaults.

Do **not** pass `--link-speed-expect` while nested: HostSync would try to link the same template directly and Zabbix rejects that. Util stays off (`101`) until 4+ weeks of history, then maybe `{$IF.UTIL.MAX:"USW"}=80` — **USW only**, not `US`/`UP`/`MON`. Discards stay DISABLED. Extra SNMP GETs exist today (platform-neutral YAML cannot declare cross-template dependent masters); swap to dependents later — compare in Mbps, never `min(speed,5m)` (heartbeat 1h → unknown).

---

## Not this apply

`--apply` is the Extreme switching + AP contract. Do not add extra flags.

**Speed Expect** is nested on VOSS and EXOS Observability. `--apply` is enough — unlabeled ports stay silent; a class label starts the LLD within 15m. Do **not** pass `--link-speed-expect` (that is a second, direct role assignment; Zabbix rejects the same template linked twice). Util is off (`101`). Duplicate link-down and discards are **DISABLED**. Routing stays imported-not-linked.

OSPF stays imported-not-linked. Fabric High stays gated (`{$ISIS.CONTROL}=0`, `{$CARD.CONTROL}=0`) until a canary.

FortiGate (API) and network VMs reuse this bar ([03](03-fortinet.md), [06](06-network-vms.md)). Do not merge with Cato ([04](04-cato.md)).
