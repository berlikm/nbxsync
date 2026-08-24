# Fortinet

FortiGates over the **REST API**. FortiManager / FortiAnalyzer are separate products — do not merge, do not assign the FortiGate template by manufacturer onto them.

World-class here means: **page what users feel (box down, path down), never fail silent on a dead API, one incident per WAN cut** — not a second SNMP poller.

Same bar as [01-extreme-switching.md](01-extreme-switching.md). Scale: [_template.md](_template.md). Analysis: [notes/fortigate-api-and-health.md](notes/fortigate-api-and-health.md). WAN class: [05-internet-circuits.md](05-internet-circuits.md). Overlay: [04-cato.md](04-cato.md). Extreme Health notes do **not** apply to Forti.

This page is the **target contract**. Live nbxSync still links **FortiGate by SNMP** until you run `--apply-fortigate-http` (network script, **not** zerotouch) and HostSync **both members** of a cluster (each unit’s unique `primary_ip4`). Shared token lives on **Platform FortiOS**; `{$FGATE.API.FQDN}` is **Platform FortiOS Jinja** on `primary_ip4` (HostSync renders per device). Generic role **Firewall** is not the Forti lever (FMG/FAZ share it).

---

## Observability

| Rule | Here |
|---|---|
| Page **symptoms** | ICMP down (**High**). Last SD-WAN / IPsec path at a site is **Disaster** on the **site**, not this template |
| **Ticket** (Average) | API / HTTPS port dead while ICMP is up. Conserve mode. License unsuccessful (primary). In-scope SD-WAN member or health-check **down** (primary) |
| **Graph** / next day | CPU, memory %, SD-WAN loss/latency/jitter, iface errors, license expiry, firmware available |
| One incident | API → ICMP → **site**. Two HA **members** can both High (two chassis). Path/license tickets are gated on `ha.role=1`. The same WAN must not ticket on Forti **and** Extreme `UW` **and** Cato |
| Never silent | unsupported items; nodata ICMP/API; zero interfaces; SD-WAN below `{$FGATE.SDWAN.EXPECTED}`; HA member count ≠ `{$FGATE.HA.EXPECTED}` |
| Control plane | Shared REST token on **Platform FortiOS**. FQDN is platform Jinja on `primary_ip4`. Scope ifaces with LLD macros |
| Collect first | Policy LLD **disabled**. util 95% silenced (101). CPU/mem **High** silenced (CRIT 101). firmware Info off if CONTROL=0. ICMP loss/RTT stay on ICMP Ping (do not patch that template globally) |
| Host dashboard | Observability **Health** + **Path** |
| Severity | **Disaster** = site only. Warning = next day, not a dump bucket |

Data path: companion **FortiGate Observability** (nests stock **FortiGate by HTTP** + **ICMP Ping**). Do **not** also assign ICMP Ping or FortiGate by HTTP on FortiOS objects — they are nested parents, and Zabbix rejects a duplicate parent link. Do **not** also link FortiGate by SNMP or Network Generic (`icmpping` collision). After SNMP Monitoring is pruned from role Firewall, Platform FortiOS uses CG **FortiGate HTTP** (Agent @ primary, no ICMP Ping template) so Site Group **Agent Monitoring** does not win.

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
| CPU critical (95) | **no** as page | — | stock **High** — `{$CPU.UTIL.CRIT}=101` on Platform FortiOS / HTTP parent |
| Memory high (80) | yes | Average | Average |
| Memory critical (90) | **no** as page | — | stock **High** — `{$MEMORY.UTIL.CRIT}=101`. Prefer **conserve mode** (Observability) |
| Conserve mode | yes | Average | companion `fgate.observability.conserve=1` |
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
| SD-WAN member link down (WAN members only) | yes | Average — **primary/standalone only** (`fgate.ha.role=1`) | patched off `.diff()` + manual close → sustained `#3` + auto-recover |
| SD-WAN health-check down / error | yes | Average — **primary/standalone only**. Prefer this as the WAN symptom | patched the same way |
| SD-WAN health-check loss | yes | Warning | Warning at `{$SDWAN.HEALTH.IF.LOSS.WARN}`=20 |
| SD-WAN latency / jitter | **no** | dashboard **Path** | items only |
| WAN / HA / mgmt iface link down | yes | Average — **primary/standalone only** | patched the same way |
| VLAN / VPN / loopback / unused | **no** | not discovered | `{$NET.IF.IFNAME.MATCHES}`=`^(wan\|ha\|mgmt\|dmz)` |
| Interface errors | yes | Warning | patched to in **or** out errors (stock checked inbound twice) |
| Sustained util | **no** | dashboard | Warning at **95%** / 15m — `{$NET.IF.UTIL.MAX}=101` |
| Firewall policy hits / sessions | **no** | named canaries later | master `fgate.fwp.get_data` + discovery **disabled** |
| `X…` / admin-down | **no** | not discovered | — |

Do **not** alert on: every policy, every VLAN, FortiGuard “firmware exists”, CPU as High, the same ISP cut as Extreme `UW` **and** Cato, FMG/FAZ as if they were FortiGates. Path tickets on the secondary HA member are gated; ICMP/API/CPU health stays on both.

---

## Health dashboard (host, from the template)

After **FortiGate Observability** is linked, **Monitoring → Hosts → host → Dashboards → Health** (and **Path**).

| Page | What you see in 5 seconds |
|---|---|
| **Health** | ICMP / API / CPU / memory gauges |
| **Path** | HA role, conserve, in-scope interface count, SD-WAN member count. Stock LLD WAN graphs stay on the HTTP parent |

Stock HTTP has **no** host Health board. Observability ships **Health** and **Path**. Traffic graphs from interface/SD-WAN LLD remain on the stock parent until a later board wires them in.

---

## Scope

| Object | In | Out |
|---|---|---|
| FortiGate | **One Zabbix host per physical unit** (NetBox Device). Poll that unit’s **HA management IP** | A floating **WAN/data-plane VIP** as the API target. A single VIP host that hides the backup |
| HA pair | **Both** members, always — one Zabbix host each, unique OOB / ha-mgmt. Health (ICMP/API/CPU/mem) on **each** | A VIP host, “primary only”, or skipping HostSync of the backup. Path/SD-WAN/license **tickets** doubling is later noise, not a reason to omit the second box |
| Interfaces | WAN, SD-WAN members, HA, mgmt — admin-up | VLAN, VPN, loopback, unused, `ssl.root`, every `npu`/`fortilink` unless it **is** the WAN |
| SD-WAN | Members + health-checks that are real underlay paths | Health-checks with “all members” if LLD is empty ([ZBX-26072](https://support.zabbix.com/browse/ZBX-26072)) — census, don’t assume WAN is fine |
| Licenses | Production FortiGuard SKUs | `no_support` / `no_license` (stock NOT_MATCHES already) |
| Firewall policies | Collect **none** until a named canary list exists | Discover-all |
| FortiAP / WTP | **no** | Extreme APs are [02](02-extreme-access-points.md) |
| FortiManager / FortiAnalyzer | own blocks below | FortiGate HTTP template |

Mute an in-scope iface with context `{$NET.IF.CONTROL:"wan1"}=0` (or SD-WAN CONTROL), not a second CMDB. Prefer **excluding from LLD** over CONTROL=0 on a hundred names.

Starter LLD (tighten on the first canary — **do not** MATCH `port`; on a 40F/100F `port1` is often LAN). `--apply-fortigate-http` (or `--apply-firewall-macros` / Extreme `--apply` for the **platform** macros only) puts these on **Platform FortiOS**:

```
{$NET.IF.IFNAME.MATCHES}     = ^(wan|ha|mgmt|dmz)
{$NET.IF.IFNAME.NOT_MATCHES} = ^(ssl\.|npu|fortilink|loopback|vlan)
{$FWP.FWNAME.MATCHES}        = ^$
{$NET.IF.UTIL.MAX}           = 101
```

If aliases follow the port-identity grammar, prefer `{$NET.IF.IFALIAS.MATCHES}` the same way Access uses `USW|US|UP|MON|UW|TMON`. Aggregated WAN (`agg` / `x1`) is a host override, not the fleet regex.

---

## HA

**Both members, unique OOB, not a VIP.** Fortinet reserved HA management (`ha-mgmt` or in-band `management-ip`) exists so API/ICMP can reach **each** unit on its own address. Config on those IPs is **not** synced. NetBox already has two devices with two IPs; nbxSync already creates two Zabbix hosts — HostSync them the same way.

That is the **simple** path. Do **not** invent a cluster VIP host, skip the backup, or give the two members different templates. `--apply-fortigate-http` writes `{$FGATE.API.FQDN}` as **Platform FortiOS Jinja** (`{{ object.primary_ip4.address.ip }}` — this estate’s OOB / ha-mgmt; NetBox `oob_ip` is BMC-only) and one shared token on **Platform FortiOS**. A leftover **Device**-level FQDN (literal IP) is pruned so inheritance wins. HostSync of member A and member B is two jobs with the same inheritance; only the rendered FQDN differs. ICMP uses the same `primary_ip4`.

VIP-only polling hides a dead chassis: the floating address fails over, ICMP/API stay green, and stock HTTP has **no** HA member/sync LLD to tell you the peer is gone. That is a silent split-brain / silent RMA. “Primary only” has the same hole until failover.

| Poll this | As `{$FGATE.API.FQDN}` / ICMP |
|---|---|
| Each unit’s **ha-mgmt** / dedicated **OOB** IP | **yes** — default. HostSync **both** |
| Shared GUI name that resolves to the **primary only** | only if the backup has no unique mgmt IP (inventory/reachability gap) |
| WAN / SD-WAN / data-plane VIP | **never** — that is a path, not the API |

Health alerts (ICMP **High**, API Average, CPU/mem) stay on **both** members. A backup chassis down is still a dead box, not “redundancy Warning”.

Path/SD-WAN/license **tickets** are gated on `fgate.ha.role=1` (primary/standalone) after apply patches. Secondary chassis still has ICMP/API/CPU health. Do **not** skip HostSync of the backup.

REST API admin usually **syncs**; one token often works on both mgmt IPs. Trusted hosts do **not** — allow the Swiss proxy on **each** unit. Verify the secondary 200s; a 401 there is trusted-hosts / ha-mgmt, not “leave this host unsynced”.

VIP-only is a **fallback** when the secondary is unreachable (no ha-mgmt). Call that out as a watcher gap, not the design.

OOB / ha-mgmt is how you poll **both HA members at once**. It is **not** a reason to link **FortiGate by HTTP and FortiGate by SNMP** on the same host. Stock item keys do not collide, but SNMP re-adds `icmpping` (collision with ICMP Ping), and you get two WAN link-down families plus two CPU Highs for the same box. Keep HTTP + ICMP Ping. HA peer/sync and sensors stay a later thin item, not a second platform template.

**Cutover order** is not “monitor only one box”. After `--apply-fortigate-http`, HostSync **both members of the first cluster**, prove API/ICMP/LLD, then HostSync the remaining clusters (still both members). Do not mass-HostSync the whole firewall fleet in one click — that is SNMP→HTTP risk, not HA topology.

---

## Zero-touch (nbxSync)

**Do not re-run `configure_nbxsync_zerotouch.py` for this cutover.** Zerotouch still floors FortiOS on **FortiGate by SNMP** and puts Firewall on **SNMP Monitoring**. A later zerotouch re-apply would undo HTTP.

**Live today** (until `--apply-fortigate-http`):

1. Template Rule **FortiOS** `FORTIOS|FortiOS` → **FortiGate by SNMP** + `OS/Network`
2. Role **Firewall** floor → FortiGate by SNMP
3. Role Firewall → **SNMP Monitoring** CG (`MONITORING` MD5/DES)
4. ICMP Ping is **not** on fleet SNMP Monitoring (Forti SNMP already has `icmpping`)
5. FMG/FAZ rule → Network Generic
6. `--apply-firewall-macros` writes HTTP fleet macros on **Platform FortiOS** (not role Firewall), including `{$FGATE.API.FQDN}` Jinja on `primary_ip4`. Shared token belongs on that platform.

Locked GUI checklist still lists FortiGate by SNMP — that file is not updated here. Empty env must **not** wipe `{$FGATE.API.TOKEN}`.

**Operator path** (no zerotouch, no Extreme YAML, no mass-HostSync):

```bash
export NBX_ZABBIX_TOKEN=...
export NBX_FGATE_TOKEN=...          # shared REST key → Platform FortiOS
python3 scripts/configure_nbxsync_network.py --apply-fortigate-http
```

The flag **fails closed** (preflight). It looks up Cloud **FortiGate by HTTP** vendor **Zabbix, 7.0-2**, surgically patches ZBX-27082 / WAN `.diff()` / policy LLD / CPU-mem CRIT 101, imports companion **FortiGate Observability**, and retargets **FortiOS only**. It never imports bundled 7.0-3 over Cloud.

That flag:

| Lever | What it writes |
|---|---|
| Platform FortiOS | **FortiGate Observability** (nests Cloud HTTP + ICMP Ping) + `OS/Network`. ANY. Winning CG **FortiGate HTTP** (Agent :10050, no ICMP Ping template) |
| Role Firewall | **prune** FortiGate HTTP/SNMP and ICMP Ping leftovers. **Prune** SNMP Monitoring (FortiOS is HTTP) |
| SNMP Monitoring | **moved** onto FortiManager / FortiAnalyzer **platforms**. Not on FortiGates |
| ICMP | Nested on Observability — **not** on role Firewall. Leftover ICMP/HTTP/SNMP on FortiOS devices, platforms, and device types is **pruned**. Agent-plane CGs keep ICMP Ping (servers). FortiOS winning CG is **FortiGate HTTP**. |
| Fleet HTTP defaults | **Platform FortiOS** — https/20443, WAN/HA/mgmt LLD, CPU/mem CRIT 101, empty policy LLD |
| Secrets | Shared `{$FGATE.API.TOKEN}` on **Platform FortiOS** (`NBX_FGATE_TOKEN`). `{$FGATE.API.FQDN}` = platform Jinja `{{ object.primary_ip4.address.ip }}` |

`--apply-firewall-macros` is the lighter sibling (FortiOS platform macros only). Extreme `--apply` still does **not** retarget FortiOS.

Then HostSync **both members of the first cluster** (each unique OOB). Inheritance does not hit live Zabbix hosts until that sync. After that cluster is green, HostSync the remaining Firewalls the same way — still both members, not a VIP. Do not mass-HostSync the fleet in one click.

**Target** after the flag + HostSync of both members:

| Lever | Target |
|---|---|
| Platform FortiOS | **FortiGate Observability** + `OS/Network`. Interface requirement **ANY**, not SNMP |
| Role Firewall | no FortiGate template floor and no SNMP Monitoring CG |
| Secrets | Shared `{$FGATE.API.TOKEN}` on **Platform FortiOS**. `{$FGATE.API.FQDN}` = platform Jinja `{{ object.primary_ip4.address.ip }}` (OOB / ha-mgmt; not a WAN VIP). HostSync renders per device. |
| Fleet HTTP defaults | **Platform FortiOS** — https/20443, WAN/HA/mgmt LLD, `{$FWP.FWNAME.MATCHES}`=`^$`, util 101, CPU/mem CRIT 101. Not Switch* or Firewall role |
| ICMP | nested on Observability. Winning CG **FortiGate HTTP** (Platform FortiOS) beats Site Group Agent Monitoring so ICMP Ping is not assigned twice. Do not strip ICMP from agent CGs. |
| SNMP Monitoring | **FortiManager / FortiAnalyzer platforms only**. FortiOS does **not** fall through to Site Group Agent Monitoring. |
| Health | already on the HTTP template after upsert — no dashboard script |

Before the flag:

1. FortiGate by HTTP is already in Zabbix Cloud as **Zabbix, 7.0-2** — keep it. `--apply-fortigate-http` looks it up and never imports 7.0-3 over it.
2. On-box: read-only admin profile (Zabbix: enable **all Read**) → REST API Admin → token **once** (usually syncs). Trusted hosts = **Swiss proxy on each member’s ha-mgmt / OOB**, not a laptop.

Do **not** HostSync a Forti that still has FortiGate by SNMP **and** Observability (`icmpping` key collision). `--apply-fortigate-http` prunes leftover SNMP from FortiOS devices/platforms/device types and from role Firewall, and assigns CG **FortiGate HTTP** on Platform FortiOS so Agent Monitoring (ICMP Ping) does not win. Nested ICMP Ping + Observability is the failure mode this CG avoids. Device-level SNMP is still a fail-closed preflight abort.

Then HostSync **both members of the first cluster** (each unique OOB). Inheritance does not hit live Zabbix hosts until that sync. After that cluster is green, HostSync the remaining Firewalls the same way — still both members, not a VIP. Do not mass-HostSync the fleet in one click.

---

## Ops

Production poller for NL/US/CH is the **Swiss proxy group**. HTTP items run **from that proxy** to Forti HTTPS. A laptop `curl` that works does **not** prove the path. ICMP Up only proves ping.

| Macro | Default | We set |
|---|---|---|
| `{$FGATE.SCHEME}` | `http` | **https** |
| `{$FGATE.API.PORT}` | `80` | **20443** (ha-mgmt GUI; 443 is SSL-VPN) |
| `{$FGATE.API.FQDN}` | empty | **Platform FortiOS** Jinja `{{ object.primary_ip4.address.ip }}` (OOB / ha-mgmt). Not the WAN VIP. A leftover Device-level literal IP is pruned so this inherits. |
| `{$FGATE.API.TOKEN}` | empty | **one** secret on **Platform FortiOS** (`NBX_FGATE_TOKEN`). Same key for the FortiOS fleet. Not role Firewall. Per-cluster / Vault is later |
| `{$FGATE.DATA.TIMEOUT}` | `15s` | keep unless slow VDOMs |
| `{$FGATE.HTTP.PROXY}` | empty | leave empty — the Zabbix proxy **is** the poller, not an HTTP forward proxy unless required |

FortiOS **7.4.5+** requires `Authorization: Bearer`. Do **not** enable `rest-api-key-url-query` to paper over an old template.

TLS: verify the GUI cert from the proxy. Wrong name / private CA looks like API Average, not ICMP High.

VDOM: the REST admin must see the VDOM(s) you monitor. HTTP exposes **current VDOM** only — not VDOM LLD.

HA: poll **each member’s unique OOB / ha-mgmt IP**. HostSync both. After failover, health items follow that chassis. Path/license tickets are gated on `fgate.ha.role=1`. If API 401s on the secondary: trusted-hosts / ha-mgmt, not the template. See [HA](#ha).

After a **reboot**: HTTPS/API comes up after forwarding. ICMP High then API Average is expected. Token is not SNMPv3 engine-boots — do not `snmp_cache_reload` for HTTP.

Platform name must match **FortiOS** (`FORTIOS|FortiOS`). `FortiGate` hardware without that platform string never hits the rule.

Link-down / SD-WAN-down triggers are patched to **sustained state** (`max/min(...,#3)`) and **no manual close**. Do not ACK-to-mute a dead path; use `{$SDWAN.*.CONTROL}=0` or maintenance.

---

## Dependencies

```
SD-WAN / WAN iface  →  API dead  →  ICMP down  →  site unreachable
CPU / mem / license →  ICMP down
```

A site WAN blip must not be Forti Average **plus** Extreme `UW` Average **plus** Cato site High for the same circuit. Unified with [05](05-internet-circuits.md):

- One redundant circuit / SD-WAN member lost: **Average** (Forti health-check is the underlay symptom; Extreme `UW` is the cause signal).
- Last usable site underlay path lost: **High** on the path, **Disaster** on the site (later parent).
- Cato site state: overlay symptom, not a second underlay ticket.

Tag events with `site`, `circuit_id`, `path`, `device/member`, `cluster`, `layer` when those exist. A Swiss proxy only proves reachability from Switzerland — it cannot alone distinguish a dead firewall from an upstream mgmt-path failure.

---

## Watch the watcher

| Check | Why | Live |
|---|---|---|
| Unsupported item count | JS/HTTP died; looks like health | Observability `zabbix[host,,items_unsupported]` Average after 10m |
| No ICMP data 10m | host *unknown* / proxy not collecting | Observability nodata on `fgate.observability.icmp` Average |
| No API data 10m | API item silent | Observability nodata on `fgate.observability.api` Average |
| API = 0, ICMP = 1 | token, trusted-host, TLS, FortiOS Bearer, wrong FQDN/port | Average Unexpected API |
| ICMP = 0 | box or path to mgmt | ICMP High |
| HTTPS port down, API items stale | GUI port / scheme still `80`/`http`, or poller still on `443` instead of `20443` | Average port unavailable |
| Zero interfaces | IFNAME regex or `netif` API fail | `fgate.observability.netif.count` < `{$NET.IF.DISCOVERY.MIN}` |
| SD-WAN site, too few members | [ZBX-26072](https://support.zabbix.com/browse/ZBX-26072) or not SD-WAN | `fgate.observability.sdwan.count` < `{$FGATE.SDWAN.EXPECTED}` (default 0) |
| Duplicate Authorization 401 | 7.0-2/7.0-3 reuse `HttpRequest` in `getHttpData` ([ZBX-27082](https://support.zabbix.com/browse/ZBX-27082), fix in **7.0.30rc1**) | `--apply-fortigate-http` patches scripts in place; aborts if still vulnerable |
| HA pair, wrong member count | backup never polled, or checksums API | `fgate.observability.ha.member.count` ≠ `{$FGATE.HA.EXPECTED}` (set 2 on pairs) |
| Secondary API 401, ICMP up | trusted-hosts on **that** unit’s ha-mgmt; token not valid there | Average Unexpected API |
| Proxy last-seen | hosts go *unknown*, not *down* | nodata ICMP/API above. `zabbix[proxy,<name>,lastaccess]` needs a per-proxy name — Cloud console / later |

---

## Templates

Do **not** clone stock FortiGate by HTTP.

| Template | Where | Notes |
|---|---|---|
| FortiGate Observability | Platform FortiOS — **target** | Nests Cloud HTTP + ICMP Ping. Health + Path, census, conserve, ha.member.count |
| FortiGate by HTTP (stock) | nested parent | Cloud is **Zabbix, 7.0-2**. Reuse; never import 7.0-3. Apply patches ZBX-27082 / WAN state / policy off / CRIT 101 / ha.role |
| ICMP Ping | nested on Observability | HTTP has no `icmpping`. Not on role Firewall. FortiOS winning CG **FortiGate HTTP** has no ICMP Ping template. Do not strip ICMP from agent CGs. |
| FortiGate by SNMP (stock) | Platform FortiOS — **live until `--apply-fortigate-http`** | Do not dual-link with HTTP. Pruned from role Firewall |
| Network Generic Device by SNMP | **not** on FortiGate | FMG/FAZ only (SNMP Monitoring on those **platforms**) |

Template-level macros (not globals, not Switch roles, **not role Firewall**). **`--apply-fortigate-http` writes these as ZabbixMacroAssignment on Platform FortiOS** (same as `--apply-firewall-macros` / Extreme `--apply`). Shared TOKEN is also on that platform. FQDN is the same platform Jinja. None of these flags mass-HostSync Fortis.

```
{$FGATE.SCHEME}                 = https
{$FGATE.API.PORT}               = 20443
{$NET.IF.IFNAME.MATCHES}        = ^(wan|ha|mgmt|dmz)
{$NET.IF.IFNAME.NOT_MATCHES}    = ^(ssl\.|npu|fortilink|loopback|vlan)
{$SDWAN.HEALTH.IFNAME.MATCHES}  = ^(wan|ha|mgmt|dmz)
{$SDWAN.MEMBER.NAME.MATCHES}    = ^(wan|ha|mgmt|dmz)
{$FWP.FWNAME.MATCHES}           = ^$
{$NET.IF.UTIL.MAX}              = 101
{$FIRMWARE.UPDATES.CONTROL}     = 0
{$DISK.FREE.CRIT}               = 0
{$CPU.UTIL.CRIT}                = 101
{$MEMORY.UTIL.CRIT}             = 101
{$FGATE.PATH.CONTROL}           = 1
{$NET.IF.DISCOVERY.MIN}         = 1
{$FGATE.SDWAN.EXPECTED}         = 0
{$FGATE.HA.EXPECTED}            = 1
{$FGATE.API.FQDN}               = {{ object.primary_ip4.address.ip }}
```

`{$FGATE.API.FQDN}` is **Platform FortiOS Jinja**, not a Device row. HostSync renders `object` as that FortiGate, so HA members get different IPs from one assignment. Shared `{$FGATE.API.TOKEN}` is on **Platform FortiOS**. Empty env must not wipe the platform token. Set `{$FGATE.HA.EXPECTED}=2` on HA pair hosts after the canary.

CPU/mem **High** are silenced with CRIT 101 on FortiOS / HTTP / Observability — **never** on role Firewall (zerotouch already uses `{$CPU.UTIL.CRIT}` on Server/MSSQL). Conserve mode is the memory page. ICMP Ping loss/RTT stays on the nested ICMP template (do not patch ICMP Ping globally).

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

## Canary acceptance (required before fleet HostSync)

Use **one standalone** and **one HA pair**. Do not mass-HostSync until this list is green.

1. Both member serials match their NetBox devices.
2. API 200 through the assigned production (Swiss) proxy, not a laptop curl.
3. Revoke the token → one clear API-blindness Average (ICMP still up).
4. Stop HTTPS, ICMP remains up → API/port Average, not silent.
5. Disable a WAN → one Average that stays open until recovery (no `.diff()` / manual-close hole).
6. HA failover → no duplicate WAN incidents (`ha.role` gate).
7. Break HA sync / hide a member → `{$FGATE.HA.EXPECTED}=2` census Average.
8. An “all members” SD-WAN health-check does not look like a healthy WAN ([ZBX-26072](https://support.zabbix.com/browse/ZBX-26072)).
9. Zero-discovery and unsupported-item Averages fire, then clear.
10. Proxy failure / maintenance / notification delivery.
11. Record API response time, proxy queue, and total API request rate.
12. Shadow LogicMonitor/SNMP for 2–4 weeks with an explicit parity matrix.

---

## Later

Per-cluster REST tokens and Zabbix Vault secrets (fleet-wide token blast radius). Certificate verification + unique DNS/SANs per ha-mgmt. Logical HA cluster host if `ha.role` gating is not enough. Thin IPsec / session-table / sensor items (HTTP or a **minimal** SNMPv3 `authPriv` SHA/AES companion — never another `icmpping`, CPU family, or interface LLD). Named policy canaries. Site Disaster parent. FMG device-sync. FAZ log ingest vs native.

Do not block Extreme/AP cutover on this page.
