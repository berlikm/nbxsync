# Fortinet

FortiGates over the **REST API**. FortiManager / FortiAnalyzer are separate products — do not merge, do not assign the FortiGate template by manufacturer onto them.

World-class here means: **page what users feel (box down, path down), never fail silent on a dead API, one incident per WAN cut** — not a second SNMP poller.

Same bar as [01-extreme-switching.md](01-extreme-switching.md). Scale: [_template.md](_template.md). Analysis: [notes/fortigate-api-and-health.md](notes/fortigate-api-and-health.md). WAN class: [05-internet-circuits.md](05-internet-circuits.md). Overlay: [04-cato.md](04-cato.md). Extreme Health notes do **not** apply to Forti.

This page is the **target contract**. Live nbxSync still links **FortiGate by SNMP**. Do not retarget production until tokens exist — [Zero-touch](#zero-touch-nbxsync).

---

## Observability

| Rule | Here |
|---|---|
| Page **symptoms** | ICMP down (**High**). Last SD-WAN / IPsec path at a site is **Disaster** on the **site**, not this template |
| **Ticket** (Average) | API / HTTPS port dead while ICMP is up. Memory high. License unsuccessful. In-scope SD-WAN member or health-check **down** |
| **Graph** / next day | CPU, SD-WAN loss/latency/jitter, iface errors, license expiry, firmware available |
| One incident | API → ICMP → **site**. Two HA **members** can both High (two chassis). The same WAN must not ticket on both members **and** Extreme `UW` **and** Cato |
| Never silent | unsupported items; API `*.data_errors`; SD-WAN site with **zero** members/health-checks; **zero** interfaces; HA pair with only one member in Zabbix |
| Control plane | REST token + FQDN macros on the **device** (Pure pattern). Scope ifaces with LLD macros, not a second inventory |
| Collect first | Policy LLD, util 95%, CPU/mem/disk **High**, firmware Info, ICMP loss/RTT |
| Host dashboard | Template dashboard **Health**. Traffic is page **Path** (WAN/SD-WAN, not 40 policies) |
| Severity | **Disaster** = site only. Warning = next day, not a dump bucket |

Data path: stock **FortiGate by HTTP** + **ICMP Ping**. Do **not** also link FortiGate by SNMP or Network Generic (`icmpping` collision once ICMP Ping is on the host).

Scale: Info → Warning → Average → High → Disaster. Disaster+High page 24/7; Average = ticket; Warning = next day; Info = log.

---

## What we alert

**This table is the intended cutover contract** after HTTP is linked. Stock HTTP defaults that would page 03:00 are called out; we do **not** fork the template.

| Device | Alert | Sev | Live stock HTTP |
|---|---|---|---|
| ICMP down | yes | **High** — per **member**, not a VIP. Cluster may still forward | **missing** on HTTP — add **ICMP Ping**. SNMP Forti (today) already Highs this |
| HTTPS API port down (`net.tcp.service`) | yes | Average | Average — depends under Unexpected API |
| Unexpected response from API (`fgate.api.status`) | yes | Average | Average — mgmt blind; forwarding may still work |
| Per-endpoint API item errors | yes | Warning | Warning — depends on Unexpected API |
| Unplanned reboot (`uptime < 10m`) | yes | Warning | stock **Info** — retune later, do not fork now |
| CPU high (`{$CPU.UTIL.WARN}`=85) | yes | Warning | Warning |
| CPU critical (95) | **no** as page | — | stock **High** — disable / raise; CPU is next-day like Extreme |
| Memory high (80) | yes | Average | Average |
| Memory critical (90) | **no** as page | — | stock **High** — disable / raise |
| Disk free low | graph / Average later | — | stock Warning + **High** at 10% — High off until a log-disk product needs it |
| License unsuccessful | yes | Average | Average (`{$SERVICE.LICENSE.CONTROL}`) |
| License expires `< {$SERVICE.EXPIRY.WARN}` (7d) | yes | Warning | Warning |
| New firmware available | **no** if it never clears | Info | Info while FortiGuard lists an image — `{$FIRMWARE.UPDATES.CONTROL}=0` if noisy |
| Serial / system name changed | yes | Info | Info, manual close |
| ICMP loss / RTT | **no** | — | items on ICMP Ping; triggers **off** (CH proxy RTT is WAN) |
| HA peer / sync lost | later | Average | **HTTP does not collect this** (SNMP does) |
| IPsec / SSL-VPN | later | — | **HTTP does not collect this** |
| Hardware temp / PSU / fan | later | — | **HTTP does not collect this** |
| **Site** last path down | yes | **Disaster** — site-level, **not** on this template | later |

| Paths / ifaces in scope | Alert | Intended | Stock HTTP |
|---|---|---|---|
| SD-WAN member link down (WAN members only) | yes | Average — **primary only** until HA role exists | Average, **`.diff()` + manual close** — ACK will **not** re-fire until another up→down |
| SD-WAN health-check down / error | yes | Average — **primary only** | Average, same `.diff()` trap. **Prefer this** as the WAN symptom |
| SD-WAN health-check loss | yes | Warning | Warning at `{$SDWAN.HEALTH.IF.LOSS.WARN}`=20 |
| SD-WAN latency / jitter | **no** | dashboard **Path** | items only |
| WAN / HA / mgmt iface link down | yes | Average | Average on **every** discovered iface if CONTROL=1 |
| VLAN / VPN / loopback / unused | **no** | not discovered | default LLD `.*` |
| Interface errors | yes | Warning | Warning (in_errors; outbound coverage is a stock bug) |
| Sustained util | **no** | dashboard | Warning at **95%** / 15m — set `{$NET.IF.UTIL.MAX}=101` |
| Firewall policy hits / sessions | **no** | named canaries later | **no triggers**, but default LLD is every policy × ~8 items |
| `X…` / admin-down | **no** | not discovered | — |

Do **not** alert on: every policy, every VLAN, FortiGuard “firmware exists”, CPU as High, the same ISP cut as Extreme `UW` **and** Cato, **the same WAN down on both HA members**, FMG/FAZ as if they were FortiGates.

---

## Health dashboard (host, from the template)

After **FortiGate by HTTP** is linked, **Monitoring → Hosts → host → Dashboards → Health**.

| Page | What you see in 5 seconds |
|---|---|
| **Health** | ICMP / API / CPU tiles. CPU + memory graphs |
| **Path** | In-scope WAN / SD-WAN traffic + health-check loss/latency (2 columns) — not a policy wall |

Stock HTTP has **no** host Health board. Upsert on this template via API (same pattern as EXOS `--apply`).

---

## Scope

| Object | In | Out |
|---|---|---|
| FortiGate | **One Zabbix host per physical unit** (NetBox Device). Poll that unit’s **HA management IP** | A floating **WAN/data-plane VIP** as the API target. A single VIP host that hides the backup |
| HA pair | Both members. Health (ICMP/API/CPU/mem) on **each** | Path/SD-WAN/license **tickets** on both members for the same cut |
| Interfaces | WAN, SD-WAN members, HA, mgmt — admin-up | VLAN, VPN, loopback, unused, `ssl.root`, every `npu`/`fortilink` unless it **is** the WAN |
| SD-WAN | Members + health-checks that are real underlay paths | Health-checks with “all members” if LLD is empty ([ZBX-26072](https://support.zabbix.com/browse/ZBX-26072)) — census, don’t assume WAN is fine |
| Licenses | Production FortiGuard SKUs | `no_support` / `no_license` (stock NOT_MATCHES already) |
| Firewall policies | Collect **none** until a named canary list exists | Discover-all |
| FortiAP / WTP | **no** | Extreme APs are [02](02-extreme-access-points.md) |
| FortiManager / FortiAnalyzer | own blocks below | FortiGate HTTP template |

Mute an in-scope iface with context `{$NET.IF.CONTROL:"wan1"}=0` (or SD-WAN CONTROL), not a second CMDB. Prefer **excluding from LLD** over CONTROL=0 on a hundred names.

Starter LLD (tighten on the first canary — **do not** MATCH `port`; on a 40F/100F `port1` is often LAN). `--apply` puts these on Device Role **Firewall**:

```
{$NET.IF.IFNAME.MATCHES}     = ^(wan|ha|mgmt|dmz)
{$NET.IF.IFNAME.NOT_MATCHES} = ^(ssl\.|npu|fortilink|loopback|vlan)
{$FWP.FWNAME.MATCHES}        = ^$
{$NET.IF.UTIL.MAX}           = 101
```

If aliases follow the port-identity grammar, prefer `{$NET.IF.IFALIAS.MATCHES}` the same way Access uses `USW|US|UP|MON|UW|TMON`. Aggregated WAN (`agg` / `x1`) is a host override, not the fleet regex.

---

## HA

**Per member, not a VIP.** Fortinet reserved HA management (`ha-mgmt` or in-band `management-ip`) exists so SNMP/API can reach **each** unit on its own address. Config on those IPs is **not** synced. NetBox already has two devices; nbxSync will create two Zabbix hosts — do not fight that.

VIP-only polling hides a dead chassis: the floating address fails over, ICMP/API stay green, and stock HTTP has **no** HA member/sync LLD to tell you the peer is gone. That is a silent split-brain / silent RMA.

| Poll this | As `{$FGATE.API.FQDN}` / ICMP |
|---|---|
| Each unit’s **ha-mgmt** / dedicated mgmt IP | **yes** — default |
| Shared GUI name that resolves to the **primary only** | only if the backup has no unique mgmt IP (inventory/reachability gap) |
| WAN / SD-WAN / data-plane VIP | **never** — that is a path, not the API |

Health alerts (ICMP **High**, API Average, CPU/mem) stay on **both** members. A backup chassis down is still a dead box, not “redundancy Warning”. Path/SD-WAN/license **tickets** must not double: until a thin `ha.role` item exists, empty path LLD on the current secondary (`{$NET.IF.IFNAME.MATCHES}` / `{$SDWAN.*.NAME.MATCHES}` = `^$`, `{$SERVICE.LICENSE.CONTROL}=0`). After failover, flip those macros or accept a quiet path until the new primary is marked — do not leave path triggers on both.

REST API admin usually **syncs**; one token often works on both mgmt IPs. Trusted hosts do **not** — allow the Swiss proxy on **each** unit. Verify on a canary; do not assume the secondary 200s.

VIP-only is a **fallback** when the secondary is unreachable (no ha-mgmt). Call that out as a watcher gap, not the design.

---

## Zero-touch (nbxSync)

**Live today** (do not change in this docs pass):

1. Template Rule **FortiOS** `FORTIOS|FortiOS` → **FortiGate by SNMP** + `OS/Network`
2. Role **Firewall** floor → FortiGate by SNMP
3. Role Firewall → **SNMP Monitoring** CG (`MONITORING` MD5/DES)
4. ICMP Ping is **not** on fleet SNMP Monitoring (Forti SNMP already has `icmpping`)
5. FMG/FAZ rule → Network Generic

Locked GUI checklist still lists FortiGate by SNMP — that file is not updated here. Re-running zerotouch **will retarget** every FortiOS host if that Template Rule’s template changes. Empty env must **not** wipe `{$FGATE.API.TOKEN}` (same Pure rule).

**Target** (after tokens + trusted-hosts exist):

| Lever | Target |
|---|---|
| Platform FortiOS | **FortiGate by HTTP** + `OS/Network`. Interface requirement **ANY**, not SNMP |
| Role Firewall | HTTP template floor **or** platform rule only — not both SNMP and HTTP |
| Secrets | Per-device `{$FGATE.API.TOKEN}` + `{$FGATE.API.FQDN}` = **that unit’s HA mgmt IP** (not a WAN VIP) |
| Fleet HTTP defaults | Device Role **Firewall** — https/443, WAN/HA/mgmt LLD, `{$FWP.FWNAME.MATCHES}`=`^$`, util 101. Not Switch* roles |
| ICMP | **ICMP Ping** on a CG/path SNMP Fortis **never** inherit during the mixed window |
| SNMP Monitoring | **off** the HTTP Forti (HTTP does not use UDP 161) |
| Health | already on the HTTP template after upsert — no dashboard script |

Cutover sequence:

1. Import **latest 7.0** FortiGate by HTTP (Bearer header, [ZBX-27082](https://support.zabbix.com/browse/ZBX-27082) request-per-call). Lab is 7.0.29 — still re-import; do not assume the image template is current.
2. On-box: read-only admin profile (Zabbix: enable **all Read**) → REST API Admin → token **once** (usually syncs). Trusted hosts = **Swiss proxy on each member’s ha-mgmt**, not a laptop.
3. Host macros: FQDN, token, and if not set on the template **https** / **443**.
4. Canaries: link HTTP + ICMP Ping **without** unlinking the fleet SNMP rule.
5. Only then retarget FortiOS / prune the SNMP floor.

Do **not** put ICMP Ping on role Firewall while any Forti still has FortiGate by SNMP (`icmpping` key collision).

---

## Ops

Production poller for NL/US/CH is the **Swiss proxy group**. HTTP items run **from that proxy** to Forti HTTPS. A laptop `curl` that works does **not** prove the path. ICMP Up only proves ping.

| Macro | Default | We set |
|---|---|---|
| `{$FGATE.SCHEME}` | `http` | **https** |
| `{$FGATE.API.PORT}` | `80` | **443** |
| `{$FGATE.API.FQDN}` | empty | **that unit’s** HA mgmt IP / GUI FQDN — not the WAN VIP |
| `{$FGATE.API.TOKEN}` | empty | secret; often one synced token, **per-device** assignment (Pure pattern) |
| `{$FGATE.DATA.TIMEOUT}` | `15s` | keep unless slow VDOMs |
| `{$FGATE.HTTP.PROXY}` | empty | leave empty — the Zabbix proxy **is** the poller, not an HTTP forward proxy unless required |

FortiOS **7.4.5+** requires `Authorization: Bearer`. Do **not** enable `rest-api-key-url-query` to paper over an old template.

TLS: verify the GUI cert from the proxy. Wrong name / private CA looks like API Average, not ICMP High.

VDOM: the REST admin must see the VDOM(s) you monitor. HTTP exposes **current VDOM** only — not VDOM LLD.

HA: poll **each member’s mgmt IP**. After failover, health items follow that chassis; path tickets stay on whoever still has path LLD enabled. If API 401s on the secondary: trusted-hosts / ha-mgmt, not the template. See [HA](#ha).

After a **reboot**: HTTPS/API comes up after forwarding. ICMP High then API Average is expected. Token is not SNMPv3 engine-boots — do not `snmp_cache_reload` for HTTP.

Platform name must match **FortiOS** (`FORTIOS|FortiOS`). `FortiGate` hardware without that platform string never hits the rule.

Link-down / SD-WAN-down triggers use **`.diff()`** and **manual close**. If ops ACKs a still-down WAN, it stays silent until the next up→down. Prefer health-check status; do not ACK-to-mute a dead path.

---

## Dependencies

```
SD-WAN / WAN iface  →  API dead  →  ICMP down  →  site unreachable
CPU / mem / license →  ICMP down
```

A site WAN blip must not be Forti Average **plus** Extreme `UW` Average **plus** Cato site High for the same circuit. Tag Forti path events as **firewall/path**, not fabric `USW`. Site **Disaster** parent is later — until then expect per-device ICMP Highs.

---

## Watch the watcher

| Check | Why | Live |
|---|---|---|
| Unsupported item count | JS/HTTP died; looks like health | later Average `{$UNSUPPORTED.MAX}` (HTTP has no such trigger today) |
| API = 0, ICMP = 1 | token, trusted-host, TLS, FortiOS Bearer, wrong FQDN/port | Average Unexpected API |
| ICMP = 0 | box or path to mgmt | ICMP High |
| HTTPS port down, API items stale | GUI port / scheme still `80`/`http` | Average port unavailable |
| Zero interfaces | IFNAME regex or `netif` API fail | Health census |
| SD-WAN site, zero members | [ZBX-26072](https://support.zabbix.com/browse/ZBX-26072) “all members” health-check, or not SD-WAN | Health / Path census |
| Duplicate Authorization 401 | old HTTP template ([ZBX-27082](https://support.zabbix.com/browse/ZBX-27082)) | re-import latest 7.0 |
| HA pair, only one host in Zabbix | backup never polled — VIP-only or missing NetBox device | census; add the member |
| Secondary API 401, ICMP up | trusted-hosts on **that** unit’s ha-mgmt; token not valid there | Average Unexpected API |
| Proxy last-seen | hosts go *unknown*, not *down* | later |

---

## Templates

Do **not** clone stock FortiGate by HTTP.

| Template | Where | Notes |
|---|---|---|
| FortiGate by HTTP (stock, latest 7.0) | Platform FortiOS — **target** | Bearer 7.0-2+; import newer than the 401 bugs |
| ICMP Ping | CG that SNMP Fortis do not inherit | HTTP has no `icmpping` |
| FortiGate by SNMP (stock) | Platform FortiOS — **live today** | Fallback / HA-VPN gap only. Do not dual-link with HTTP |
| Network Generic Device by SNMP | **not** on FortiGate | FMG/FAZ only |

Template-level macros (not globals, not Switch roles). **`--apply` writes these as ZabbixMacroAssignment on Device Role Firewall** — same lever as Switch Access IFALIAS. Inheritance lands on HostSync of that firewall. `--apply` does **not** mass-HostSync Fortis (live SNMP still uses `{$NET.IF.IFNAME.MATCHES}`).

```
{$FGATE.SCHEME}                 = https
{$FGATE.API.PORT}               = 443
{$NET.IF.IFNAME.MATCHES}        = ^(wan|ha|mgmt|dmz)
{$NET.IF.IFNAME.NOT_MATCHES}    = ^(ssl\.|npu|fortilink|loopback|vlan)
{$FWP.FWNAME.MATCHES}           = ^$
{$NET.IF.UTIL.MAX}              = 101
{$FIRMWARE.UPDATES.CONTROL}     = 0
{$DISK.FREE.CRIT}               = 0
```

Per **device** (not the role): `{$FGATE.API.TOKEN}`, `{$FGATE.API.FQDN}` = that unit’s HA mgmt IP. Empty env must not wipe tokens.

CPU/mem **High** stay a later HTTP-template trigger-status patch (do not put `{$CPU.UTIL.CRIT}` on Firewall — zerotouch already uses that name on Server/MSSQL). ICMP Ping loss/RTT and firmware Info if CONTROL=0 is not enough. Same apply-patch style as EXOS ICMP disable.

---

## FortiManager

No official Zabbix template ([ZBXNEXT-10433](https://support.zabbix.com/browse/ZBXNEXT-10433)).

| Thing | Alert | Sev |
|---|---|---|
| ICMP down | yes | **High** |
| SNMP dead (if we keep Generic) | yes | Average |
| Managed device sync / offline | later | page vs daily report — decide before enabling |
| Config drift vs cfgit | **no** | cfgit’s job |

Live: platform FortiAnalyzer/Manager → **Network Generic** + `OS/Network`. Do **not** link FortiGate by HTTP.

---

## FortiAnalyzer

Same: no official template. Log disk **is** the product — disk High may be justified here later, unlike FortiGate.

| Thing | Alert | Sev |
|---|---|---|
| ICMP down | yes | **High** |
| Disk / log storage | later | Warning — log loss |
| Device stopped sending logs | later | pick **one** of Zabbix vs FAZ-native (never silent, never both) |

---

## Later

Thin HTTP items for **HA role / peer / sync** (so path tickets follow the primary after failover without flipping macros) and IPsec/SSL-VPN. Global session table. Sensors. VDOM LLD. Named policy canaries. Class-scoped WAN High. Site Disaster parent. Unsupported-item Average trigger. Health upsert. FortiOS Template Rule retarget **after** tokens. FMG device-sync. FAZ log ingest vs native.

Do not block Extreme/AP cutover on this page.
