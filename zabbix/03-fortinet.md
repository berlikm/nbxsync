# Fortinet

FortiGates over the **REST API**. FortiManager / FortiAnalyzer are separate products — do not merge, do not assign the FortiGate template by manufacturer onto them.

World-class here means: **page what users feel (box down, path down), never fail silent on a dead API, one incident per WAN cut** — not a second SNMP poller.

Same bar as [01-extreme-switching.md](01-extreme-switching.md). Scale: [_template.md](_template.md). Analysis: [notes/fortigate-api-and-health.md](notes/fortigate-api-and-health.md). WAN class: [05-internet-circuits.md](05-internet-circuits.md). Overlay: [04-cato.md](04-cato.md). Extreme Health notes do **not** apply to Forti.

This page is the **target contract**. FortiGates: `configure_nbxsync_network.py --apply-fortigate-http`. FortiManager / FortiAnalyzer: `--apply-fmg-faz`. Do **not** rerun zerotouch for either. Live nbxSync still links **FortiGate by SNMP** until the HTTP flag runs and HostSync processes **both members** of a cluster (each unit’s unique `primary_ip4`). The Zabbix monitoring token lives in nbxSync on **Platform FortiOS**; NetBox inventory automation keeps its different `NBX_FORTIGATE_TOKEN`. `{$FGATE.API.FQDN}` is **Platform FortiOS Jinja** on `primary_ip4` (HostSync renders per device). Generic role **Firewall** is not the Forti lever (FMG/FAZ share it — they get their own platform rules).

---

## Observability

| Rule | Here |
|---|---|
| Page **symptoms** | ICMP down (**High**). Last SD-WAN / IPsec path at a site is **Disaster** on the **site**, not this template |
| **Ticket** (Average/High) | API / HTTPS port dead while ICMP is up. Configured memory red threshold. HA member loss or VDOM checksum mismatch (**primary**). License unsuccessful (primary). In-scope SD-WAN member or health-check **down** (primary). Unsupported overlay census |
| **Graph** / next day | CPU, memory %, SD-WAN loss/latency/jitter, iface errors, license expiry, firmware available |
| One incident | API → ICMP → **site**. Two HA **members** can both High for per-chassis health. Path/license/HA-sync tickets are gated on `ha.role=1`; HA sync also depends on member count |
| Never silent | unsupported items; nodata ICMP/API; overlay endpoint errors; NetBox∩FortiOS interface baseline; SD-WAN below the exact per-device `{$FGATE.SDWAN.EXPECTED}`; HA member count ≠ `{$FGATE.HA.EXPECTED}`; HA VDOM checksum mismatch |
| Control plane | Zabbix REST token in nbxSync on **Platform FortiOS**; separate NetBox inventory automation token in `NBX_FORTIGATE_TOKEN`. FQDN is platform Jinja on `primary_ip4`. Interface LLD is an exact per-device regex from enabled+cabled NetBox interfaces observable in FortiOS CMDB; device context `{$NET.IF.CONTROL:mgmt}=0` suppresses only the unreliable reserved-management link signal while ICMP/API monitor that path |
| Collect first | Policy LLD **disabled**. util 95% silenced (101). Duplicate stock CPU/mem **High** silenced (CRIT 101); companion memory alert uses FortiOS green/red/extreme thresholds. Firmware Info off if CONTROL=0 |
| Host dashboard | **Health** (Overview / HA) + **Network interfaces** (map + traffic navigator) + **Path** (SD-WAN maps / Loss / Probe). Same chrome as EXOS |
| Severity | **Disaster** = site only (memory **extreme** is the documented exception). Warning = next day, not a dump bucket |

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
| Unplanned reboot (`uptime < 10m`) | yes | Warning | stock **Info** — `--apply-fortigate-http` retunes to Warning on the Cloud parent |
| CPU high (`{$CPU.UTIL.WARN}`=85) | yes | Warning | Warning |
| CPU critical (95) | **no** as page | — | stock **High** — `{$CPU.UTIL.CRIT}=101` on Platform FortiOS / HTTP parent |
| Memory above configured red threshold | yes | **High** | companion, sustained 5m; recovers below configured green threshold |
| Memory above configured extreme threshold | yes | **Disaster** | companion, sustained 3m; red trigger depends on this event |
| FortiOS memory thresholds | yes | — | per-device `green/red/extreme` macros refreshed from `/api/v2/cmdb/system/global`; defaults 82/88/95 |
| Disk free low | graph / Average later | — | stock Warning + **High** at 10% — High off until a log-disk product needs it |
| License unsuccessful | yes | Average | Average (`{$SERVICE.LICENSE.CONTROL}`) |
| License expires `< {$SERVICE.EXPIRY.WARN}` (7d) | yes | Warning | Warning |
| New firmware available | **no** if it never clears | Info | Info while FortiGuard lists an image — `{$FIRMWARE.UPDATES.CONTROL}=0` if noisy |
| Serial / system name changed | yes | Info | Info, manual close |
| ICMP loss / RTT | **no** | — | items on ICMP Ping; triggers **off** (CH proxy RTT is WAN) |
| HA peer / member lost | yes | Average | companion `system/ha-peer` member count |
| HA VDOM config out of sync | yes | **High** | companion `system/ha-checksums`; authoritative synchronized VDOM maps must differ. Never compare `system/ha-nonsync-checksums`: that endpoint covers intentionally member-local/non-synchronized settings |
| IPsec | inventory now; state alert after endpoint semantics are proven | — | overlay records VDOM, Phase 1/2 identity, state/type, and counters |
| Hardware temp / PSU / fan | later | — | **HTTP does not collect this** |
| **Site** last path down | yes | **Disaster** — site-level, **not** on this template | later |

| Paths / ifaces in scope | Alert | Intended | Stock HTTP |
|---|---|---|---|
| SD-WAN member link down (WAN members only) | yes | Average — **primary/standalone only** (`fgate.ha.role=1`) | patched off `.diff()` + manual close → sustained `#3` + auto-recover |
| SD-WAN health-check down / error | yes | Average — **primary/standalone only**. Prefer this as the WAN symptom. Factory `Default_FortiGuard` is LLD-excluded | patched the same way |
| SD-WAN health-check loss | yes | Warning — same exclude for `Default_FortiGuard` | Warning at `{$SDWAN.HEALTH.IF.LOSS.WARN}`=20 |
| SD-WAN latency / jitter | **no** | dashboard **Path → Loss / Probe** | items only; reuse later on [05](05-internet-circuits.md) |
| WAN / HA physical iface link down | yes | Average — **primary/standalone only** | patched the same way |
| Reserved `mgmt` | discovered, but link-down trigger off | none | FortiOS reports false physical-down on the live HA management path; device context `{$NET.IF.CONTROL:mgmt}=0`; ICMP/API own availability |
| Interface errors | yes | Warning | patched to in **or** out errors (stock checked inbound twice) |
| Sustained util | **no** | dashboard | Warning at **95%** / 15m — `{$NET.IF.UTIL.MAX}=101` |
| Firewall policy hits / sessions | **no** | named canaries later | master `fgate.fwp.get_data` + discovery **disabled** |
| `X…` / admin-down | **no** | not discovered | — |

Do **not** alert on: every policy, every VLAN, FortiGuard “firmware exists”, CPU as High, the same ISP cut as Extreme `UW` **and** Cato, FMG/FAZ as if they were FortiGates. Path tickets on the secondary HA member are gated; ICMP/API/CPU health stays on both.

Latest data and Problems expose a `vdom` tag subfilter for every discovered interface and SD-WAN item/trigger. Values are the actual FortiOS VDOM names (for example `root`, `Untrust`, `Lumiphase`, and `Zoning`), not interface-name inference.

---

## How it pages

Template triggers are the contract. **Actions / media are estate-wide** (not this YAML): Disaster+High SMS/call 24/7, Average ticket, Warning next day, Info log. A trigger with nobody listening is not monitoring.

| What the operator sees | What actually fired | Do this |
|---|---|---|
| Member unreachable | Nested **ICMP Ping** **High** (3 misses). Per chassis, not the VIP | Is the **peer** still forwarding? Secondary High is still a dead box — RMA / console / OOB. Not a WAN ticket |
| GUI/API blind, ping lives | Stock **Unexpected response from API** Average, and/or **port unavailable** Average. Companion **no API data 10m** if the item went silent | Token, trusted-hosts on **that** ha-mgmt, TLS name, scheme/port still `https`/`20443` |
| One underlay member / health-check dead | Stock SD-WAN or WAN iface **Average**, sustained `#3`, **primary/standalone only** (`fgate.ha.role=1`) | Circuit / SFP / ISP. Mute with `{$SDWAN.*.CONTROL}=0` or maintenance — never ACK a `.diff()` hole (already patched) |
| Factory `Default_FortiGuard` SLA flap | Would be stock SD-WAN **Link down** / **High packets loss** on `{#NAME}=Default_FortiGuard` (often overlay `v0665-trin*` / `v0666-trin*` in `root` and `Untrust`) | **Not a WAN ticket.** Companion `{$SDWAN.HEALTH.NAME.NOT_MATCHES}` drops that SLA from LLD. Optional on the box: disable the factory SLA or replace it with a real underlay probe. Do not mute overlay members themselves |
| Last usable site path | **Not this template.** Later: High on the path, **Disaster** on the site | Do not also ticket Extreme `UW` and Cato for the same ISP cut |
| HA peer missing | Companion **HA member count unexpected** Average (`system/ha-peer` ≠ `{$FGATE.HA.EXPECTED}`) | Backup down, never HostSynced, or standalone still at estate default 2 |
| Cluster config drift | Companion **HA VDOM configuration is out of sync** **High**, primary only, 15m | Authoritative `system/ha-checksums` only — not `ha-nonsync-checksums` |
| Conserve-mode | Companion memory **High** (red) / **Disaster** (extreme), recover below **green**. Stock CPU/mem **High** is silenced (`CRIT` 101) | Fail over; extreme is FortiOS dropping new sessions. Disaster here is a known exception to “site only” |
| We went blind | Companion **unsupported items** / **fewer interfaces** / **fewer SD-WAN members** Average | IFNAME regex, ZBX-26072, script item, proxy. Not a WAN outage |
| CPU 85% | Stock **Warning** (`{$CPU.UTIL.WARN}`) | Next day. Do not page |
| License unsuccessful / 7d expiry | Average / Warning, primary-gated after apply | FortiGuard SKU — FortiCloud `Unknown` is context-muted |
| Reboot | Stock **Warning** after apply (`uptime < 10m`; Cloud parent ships Info) | Next day, same as EXOS unplanned reboot. Do not page |

Dependencies (companion, applied after import): watchers and memory/HA tickets hang off **no API data**, which hangs off **no ICMP data**. A dead box is one ICMP High, not a census fan-out. Path tickets do **not** yet depend on stock ICMP High — a mgmt-path failure can still open WAN Averages on the current primary; that is a later parent, not a reason to skip the backup host.

---

## Health dashboard (host, from the template)

After **FortiGate Observability** is linked, **Monitoring → Hosts → host → Dashboards**. Three boards, same chrome as EXOS: **Health** for the box, **Network interfaces** for ports, **Path** for SD-WAN / ISP probes.

Widget type follows the EXOS rule: gauge = one headline number with a scale; item tile = identity or duration; honeycomb = many similar status cells; graph = trend. Honeycomb is **not** for HA role or a single memory pool. Hex labels are **VDOM/name** so production `root` and guest `Untrust` (and any other VDOM) do not look like one pile of `wan1`s.

| Page | What you see in 5 seconds |
|---|---|
| **Health → Overview** | ICMP / API / CPU / **Uptime** — same four-tile chrome as EXOS (API stands in for SNMP). Problems strip. CPU+memory trend plus Uptime history |
| **Health → HA** | Memory gauge (FortiOS 82/88/95 colours) + trend. HA role (Primary/Secondary), member count, VDOM mismatch count |
| **Network interfaces → Overview** | 72×6 link-status map (`root/wan1`). No more sliding the stock **FortiGate: Statistics** gallery to find the WAN |
| **Network interfaces → Port** | One-iface picker (link / speed / in+out errors / **bits**) with history |
| **Path → Overview** | Two 36×6 maps: **SD-WAN members** (`root/wan1`) and **health-checks** (`root/Google/wan1`). Colour is Forti link/probe state (0=up) |
| **Path → Loss** | Metric honeycomb of SD-WAN packet loss (green / 5 yellow / 20 red). This is the HTTP probe seed for [05](05-internet-circuits.md) |
| **Path → Probe** | Navigator grouped by **vdom** (loss / latency / jitter / status / **byte rate**) with history |

Stock HTTP has **no** host Health board (`FortiGate: General` / `Statistics` stay as vendor galleries). Observability owns the three host boards. Do **not** bind svggraph item patterns on this companion (same PHP `Array to string` hole as EXOS). Zabbix template dashboards may reference only objects owned by that exact template: the HTTP-parent graph prototypes cannot appear on the companion. The navigators select the inherited traffic items by name instead, so the YAML is importable and the selected metric has a history graph. The cutover still completes the stock **General → Disk usage** SVG interval as `now-1d` through `now`; Cloud 7.0-2 otherwise omits `time_period.to` and Zabbix rejects the widget.

---

## Scope

| Object | In | Out |
|---|---|---|
| FortiGate | **One Zabbix host per physical unit** (NetBox Device). Poll that unit’s **HA management IP** | A floating **WAN/data-plane VIP** as the API target. A single VIP host that hides the backup |
| HA pair | **Both** members, always — one Zabbix host each, unique OOB / ha-mgmt. Health (ICMP/API/CPU/mem) on **each** | A VIP host, “primary only”, or skipping HostSync of the backup. Path/SD-WAN/license **tickets** doubling is later noise, not a reason to omit the second box |
| Interfaces | WAN, SD-WAN members, HA, mgmt — admin-up. Reserved `mgmt` remains discovered, but its unreliable physical-link alert is context-disabled and ICMP/API monitor availability | VLAN, VPN, loopback, unused, `ssl.root`, every `npu`/`fortilink` unless it **is** the WAN |
| SD-WAN | Members + health-checks that are real underlay paths. This estate uses SD-WAN for **internet failover** on at least **`root` (production)** and **`Untrust` (guest)** — maps and Probe are VDOM-split so those do not mix | Factory SLA **`Default_FortiGuard`** (FortiGuard via overlay members, not internet-failover). Health-checks with “all members” if LLD is empty ([ZBX-26072](https://support.zabbix.com/browse/ZBX-26072)) — census, don’t assume WAN is fine |
| Licenses | Production FortiGuard SKUs | `no_support` / `no_license` (stock NOT_MATCHES already) |
| Firewall policies | Collect **none** until a named canary list exists | Discover-all |
| FortiAP / WTP | **no** | Extreme APs are [02](02-extreme-access-points.md) |
| FortiManager / FortiAnalyzer | own blocks below | FortiGate HTTP template |

Mute an in-scope iface with context `{$NET.IF.CONTROL:"wan1"}=0` only as a short operational exception. Desired discovery state is NetBox constrained by actual telemetry: `--apply-fortigate-http` intersects **enabled+cabled** NetBox interfaces with FortiOS CMDB names, then writes the device-level exact-match `{$NET.IF.IFNAME.MATCHES}` regex and matching `{$NET.IF.DISCOVERY.MIN}` count. Names FortiOS cannot expose (for example dedicated HA ports on some models) are logged and excluded from the runtime baseline rather than generating permanent false census alarms. It also writes `{$NET.IF.CONTROL:mgmt}=0`: reserved `mgmt` stays discovered, but its false FortiOS physical-down signal cannot page; ICMP/API monitor that management path. HostSync renders those assignments. The safe template default is `^$` / count `0`.

```
{$NET.IF.IFNAME.MATCHES}        = ^(?:ha|port1|port2|...)$  # per Device from NetBox
{$NET.IF.IFNAME.NOT_MATCHES}    = CHANGE_IF_NEEDED
{$NET.IF.DISCOVERY.MIN}         = <same NetBox count>
{$SDWAN.MEMBER.NAME.MATCHES}    = .*
{$SDWAN.HEALTH.IFNAME.MATCHES}  = .*
{$SDWAN.HEALTH.NAME.NOT_MATCHES}= ^Default_FortiGuard$
{$FGATE.SDWAN.EXPECTED}         = 0|6|...  # exact configured member count per Device
{$FGATE.HA.EXPECTED}            = 2
{$FWP.FWNAME.MATCHES}           = ^$
{$NET.IF.UTIL.MAX}              = 101
```

`NOT_MATCHES=.*` is invalid here because Zabbix evaluates MATCHES **and** NOT_MATCHES. Aggregated WAN (`agg` / `x1`) is monitored only when NetBox marks the relevant physical member links enabled+cabled; logical overlay state remains the SD-WAN collector’s job.

Factory **`Default_FortiGuard`** is a FortiOS Performance SLA that probes FortiGuard through whatever members are attached — on `CH-ZRH-ZH4-FWGW01` those are overlay `v0665-trin*` / `v0666-trin*`, so FortiGuard reachability looks like WAN down / high loss in both `root` and `Untrust`. Companion `{$SDWAN.HEALTH.NAME.NOT_MATCHES}` drops that health-check name from LLD (link-down **and** packet-loss). `{$SDWAN.HEALTH.IF.CONTROL:"Default_FortiGuard"}=0` would mute link-down only; loss keys off member `{#IFNAME}`. Do not denylist the overlay members — a real internet SLA can still use them. A host that uses a health-check literally named `Default_FortiGuard` as its underlay probe overrides the macro to `CHANGE_IF_NEEDED`. On the FortiGate, disable the factory SLA if unused, or add a probe to a public resolver on the underlay WAN; Zabbix still excludes the factory name so leftover checks do not page. Re-import **FortiGate Observability**, then **Check now** on `fgate.sdwan_health.discovery` (lost `Default_FortiGuard` rows can keep firing until LLD lifetime or they are deleted).

---

## HA

**Both members, unique OOB, not a VIP.** Fortinet reserved HA management (`ha-mgmt` or in-band `management-ip`) exists so API/ICMP can reach **each** unit on its own address. Config on those IPs is **not** synced. NetBox already has two devices with two IPs; nbxSync already creates two Zabbix hosts — HostSync them the same way.

That is the **simple** path. Do **not** invent a cluster VIP host, skip the backup, or give the two members different templates. `--apply-fortigate-http` writes `{$FGATE.API.FQDN}` as **Platform FortiOS Jinja** (`{{ object.primary_ip4.address.ip }}` — this estate’s OOB / ha-mgmt; NetBox `oob_ip` is BMC-only) and preserves the Zabbix monitoring token on **Platform FortiOS**. The separate NetBox inventory automation token is never copied into that macro. A leftover **Device**-level FQDN (literal IP) is pruned so inheritance wins. HostSync of member A and member B is two jobs with the same inheritance; only the rendered FQDN differs. ICMP uses the same `primary_ip4`.

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
5. FMG/FAZ rule → Network Generic (until `--apply-fmg-faz`)
6. `--apply-firewall-macros` writes HTTP fleet macros on **Platform FortiOS** (not role Firewall), including `{$FGATE.API.FQDN}` Jinja on `primary_ip4`. The Zabbix monitoring token belongs in nbxSync on that platform; `NBX_FORTIGATE_TOKEN` remains inventory automation only.

Locked GUI checklist still lists FortiGate by SNMP — that file is not updated here. The script never copies `NBX_FORTIGATE_TOKEN` into `{$FGATE.API.TOKEN}`.

**Operator path** (no zerotouch, no Extreme YAML, no mass-HostSync):

```bash
# NBX_FORTIGATE_TOKEN is the existing NetBox inventory automation credential.
python3 scripts/configure_nbxsync_network.py --check-fortigate-http  # read-only
python3 scripts/configure_nbxsync_network.py --apply-fortigate-http
```

The flag **fails closed** before any write. From the NetBox process, it calls `/api/v2/monitor/system/status` for every active FortiOS `primary_ip4` with the inventory automation `NBX_FORTIGATE_TOKEN` and requires HTTP 200 with JSON. It separately requires a non-empty effective nbxSync `{$FGATE.API.TOKEN}` for Zabbix monitoring. The tokens are intentionally different: the NetBox-origin probe does **not** validate the monitoring credential or Zabbix proxy trusted-host path. It then looks up Cloud **FortiGate by HTTP** vendor **Zabbix, 7.0-2**, surgically patches ZBX-27082 / WAN state / policy LLD / CPU-memory CRIT 101, imports companion **FortiGate Observability**, and retargets **FortiOS only**. It never imports bundled 7.0-3 over Cloud.

That flag:

| Lever | What it writes |
|---|---|
| Platform FortiOS | **FortiGate Observability** (nests Cloud HTTP + ICMP Ping) + `OS/Network`. ANY. Winning CG **FortiGate HTTP** (Agent :10050, no ICMP Ping template) |
| Role Firewall | **prune** FortiGate HTTP/SNMP and ICMP Ping leftovers. **Prune** SNMP Monitoring (FortiOS is HTTP) |
| SNMP Monitoring | **moved** onto FortiManager / FortiAnalyzer **platforms**. Not on FortiGates |
| ICMP | Nested on Observability — **not** on role Firewall. Leftover ICMP/HTTP/SNMP on FortiOS devices, platforms, and device types is **pruned**. Agent-plane CGs keep ICMP Ping (servers). FortiOS winning CG is **FortiGate HTTP**. |
| Fleet HTTP defaults | **Platform FortiOS** — https/20443, WAN/HA/mgmt LLD (`mgmt` link trigger context-disabled; availability via ICMP/API), CPU/mem CRIT 101, empty policy LLD |
| Secrets | Existing NetBox `{$FGATE.API.TOKEN}` assignment on **Platform FortiOS** is the Zabbix monitoring credential and is preserved. `NBX_FORTIGATE_TOKEN` is the separate NetBox inventory automation credential and is never copied into nbxSync. `{$FGATE.API.FQDN}` = platform Jinja `{{ object.primary_ip4.address.ip }}` |

`--apply-firewall-macros` is the lighter sibling (FortiOS platform macros only). Extreme `--apply` still does **not** retarget FortiOS.

Then HostSync **both members of the first cluster** (each unique OOB). Inheritance does not hit live Zabbix hosts until that sync. After that cluster is green, HostSync the remaining Firewalls the same way — still both members, not a VIP. Do not mass-HostSync the fleet in one click.

**Target** after the flag + HostSync of both members:

| Lever | Target |
|---|---|
| Platform FortiOS | **FortiGate Observability** + `OS/Network`. Interface requirement **ANY**, not SNMP |
| Role Firewall | no FortiGate template floor and no SNMP Monitoring CG |
| Secrets | Zabbix monitoring `{$FGATE.API.TOKEN}` in nbxSync on **Platform FortiOS**; separate inventory automation token in `NBX_FORTIGATE_TOKEN`. `{$FGATE.API.FQDN}` = platform Jinja `{{ object.primary_ip4.address.ip }}` (OOB / ha-mgmt; not a WAN VIP). HostSync renders per device. |
| Fleet HTTP defaults | **Platform FortiOS** — https/20443, WAN/HA/mgmt LLD (`{$NET.IF.CONTROL:mgmt}=0`, availability via ICMP/API), `{$FWP.FWNAME.MATCHES}`=`^$`, util 101, CPU/mem CRIT 101. Not Switch* or Firewall role |
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
| `{$FGATE.API.TOKEN}` | empty | Existing **Platform FortiOS** nbxSync assignment is authoritative for Zabbix monitoring. Never populate it from `NBX_FORTIGATE_TOKEN`, which belongs only to NetBox inventory automation. Not role Firewall |
| `{$FGATE.DATA.TIMEOUT}` | `15s` | keep unless slow VDOMs |
| `{$FGATE.HTTP.PROXY}` | empty | leave empty — the Zabbix proxy **is** the poller, not an HTTP forward proxy unless required |

FortiOS **7.4.5+** requires `Authorization: Bearer`. Do **not** enable `rest-api-key-url-query` to paper over an old template.

TLS: verify the GUI cert from the proxy. Wrong name / private CA looks like API Average, not ICMP High.

VDOM: the Cloud 7.0-2 parent stays version-pinned but receives two bounded compatibility fixes: a fresh `HttpRequest` per call ([ZBX-27082](https://support.zabbix.com/browse/ZBX-27082)) and tested multi-VDOM normalization for interface/SD-WAN responses. The fetcher short-circuits inactive-secondary 404/424 responses instead of walking every VDOM or aborting successful endpoints. The independent companion `fgate.observability.inventory` census keeps 1h history and records all-VDOM SD-WAN and IPsec identity/state/counters. Authentication, transport, and malformed-response failures make it unsupported; optional 404/424 endpoints do not.

Stock HTTP still has no IPsec trigger family. Treat overlay IPsec fields as inventory until the canary proves state semantics and expected-tunnel controls. HostSync is not required for the script-item patches. Never put the token in the URL query and never set `{$NET.IF.IFNAME.NOT_MATCHES}=.*`.

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
| Overlay census unsupported | authentication, transport, or malformed JSON on an enabled endpoint | covered by Observability unsupported-item count Average; 404/424 is ignored |
| No ICMP data 10m | host *unknown* / proxy not collecting | Observability nodata on `fgate.observability.icmp` Average |
| No API data 10m | API item silent | Observability nodata on `fgate.observability.api` Average |
| API = 0, ICMP = 1 | token, trusted-host, TLS, FortiOS Bearer, wrong FQDN/port | Average Unexpected API |
| ICMP = 0 | box or path to mgmt | ICMP High |
| HTTPS port down, API items stale | GUI port / scheme still `80`/`http`, or poller still on `443` instead of `20443` | Average port unavailable |
| Zero interfaces | IFNAME regex or `netif` API fail | `fgate.observability.netif.count` < `{$NET.IF.DISCOVERY.MIN}` |
| SD-WAN site, too few members | [ZBX-26072](https://support.zabbix.com/browse/ZBX-26072) or LLD/API regression | `fgate.observability.sdwan.count` < exact configured per-device `{$FGATE.SDWAN.EXPECTED}`; zero on devices without SD-WAN |
| Duplicate Authorization 401 | 7.0-2/7.0-3 reuse `HttpRequest` in `getHttpData` ([ZBX-27082](https://support.zabbix.com/browse/ZBX-27082), fix in **7.0.30rc1**) | `--apply-fortigate-http` patches scripts in place; aborts if still vulnerable |
| HA pair, wrong member count | backup never polled or peer missing | `fgate.observability.ha.member.count` from `system/ha-peer` ≠ `{$FGATE.HA.EXPECTED}` |
| HA VDOM checksum mismatch | configuration sync drift | `fgate.observability.ha.vdom_mismatches` High after 15m on the **primary only**; depends on API and member-count health |
| HA role collection error | auth/transport/unknown role must not masquerade as primary | `fgate.ha.role` becomes unsupported; only explicit 404/424 means standalone |
| Secondary API 401, ICMP up | trusted-hosts on **that** unit’s ha-mgmt; token not valid there | Average Unexpected API |
| Proxy last-seen | hosts go *unknown*, not *down* | nodata ICMP/API above. `zabbix[proxy,<name>,lastaccess]` needs a per-proxy name — Cloud console / later |

---

## Templates

Do **not** clone stock FortiGate by HTTP.

| Template | Where | Notes |
|---|---|---|
| FortiGate Observability | Platform FortiOS — **target** | Nests Cloud HTTP + ICMP Ping. Health + Path, detailed census, configured memory pressure, authoritative HA member/sync signals |
| FortiGate by HTTP (stock) | nested parent | Cloud is **Zabbix, 7.0-2**. Never import 7.0-3. Apply adds version-pinned ZBX-27082 + multi-VDOM compatibility and patches WAN state / policy off / unsupported capacity items / CRIT 101 / `ha.role` |
| ICMP Ping | nested on Observability | HTTP has no `icmpping`. Not on role Firewall. FortiOS winning CG **FortiGate HTTP** has no ICMP Ping template. Do not strip ICMP from agent CGs. |
| FortiGate by SNMP (stock) | Platform FortiOS — **live until `--apply-fortigate-http`** | Do not dual-link with HTTP. Pruned from role Firewall |
| Network Generic Device by SNMP | **not** on FortiGate | Leftover on FMG/FAZ until `--apply-fmg-faz` (then Observability companions nest **Fortinet FMG-FAZ by SNMP**) |

Template-level macros (not globals, not Switch roles, **not role Firewall**). **`--apply-fortigate-http` writes these as ZabbixMacroAssignment on Platform FortiOS** (same as `--apply-firewall-macros` / Extreme `--apply`). The existing Zabbix monitoring TOKEN is preserved on that platform; the NetBox automation token is separate. FQDN is the same platform Jinja. None of these flags mass-HostSync Fortis.

```
{$FGATE.SCHEME}                 = https
{$FGATE.API.PORT}               = 20443
{$NET.IF.IFNAME.MATCHES}        = ^$       # safe platform default; exact Device regex from NetBox
{$NET.IF.IFNAME.NOT_MATCHES}    = CHANGE_IF_NEEDED
{$SDWAN.HEALTH.IFNAME.MATCHES}  = .*
{$SDWAN.HEALTH.NAME.NOT_MATCHES}= ^Default_FortiGuard$
{$SDWAN.MEMBER.NAME.MATCHES}    = .*
{$FWP.FWNAME.MATCHES}           = ^$
{$NET.IF.UTIL.MAX}              = 101
{$FIRMWARE.UPDATES.CONTROL}     = 0
{$DISK.FREE.CRIT}               = 0
{$CPU.UTIL.CRIT}                = 101
{$MEMORY.UTIL.CRIT}             = 101
{$FGATE.MEMORY.GREEN}           = 82       # per Device when API provides it
{$FGATE.MEMORY.RED}             = 88
{$FGATE.MEMORY.EXTREME}         = 95
{$FGATE.PATH.CONTROL}           = 1
{$NET.IF.DISCOVERY.MIN}         = 0        # per Device = NetBox∩FortiOS observable count
{$FGATE.SDWAN.EXPECTED}         = 0        # per Device = exact configured member count
{$FGATE.HA.EXPECTED}            = 2
{$FGATE.API.FQDN}               = {{ object.primary_ip4.address.ip }}
```
`{$FGATE.API.FQDN}` is **Platform FortiOS Jinja**, not a Device row. HostSync renders `object` as that FortiGate, so HA members get different IPs. The monitoring token remains the existing Platform assignment; `NBX_FORTIGATE_TOKEN` is only for NetBox automation. Apply creates per-device interface-scope and memory-threshold overrides; HostSync is still explicit.

Duplicate stock CPU/memory **High** triggers are silenced with CRIT 101. Companion memory pressure uses the device’s configured green/red/extreme thresholds and recovers below green. ICMP loss/RTT remains on nested ICMP Ping.

---

## FortiManager / FortiAnalyzer

No official Zabbix template ([ZBXNEXT-10433](https://support.zabbix.com/browse/ZBXNEXT-10433) Won’t Do). Shared MIB `FORTINET-FORTIMANAGER-FORTIANALYZER-MIB` (`enterprises.12356.103`, build 3737). Do **not** assign FortiGate HTTP/SNMP or Network Generic onto these platforms (`icmpping` collision; wrong objects). Role Firewall is not the lever.

Three templates (VOSS/IQ parent + EXOS-style companions):

| Template | Role |
|---|---|
| **Fortinet FMG-FAZ by SNMP** | Owns `icmpping` (do **not** also nest ICMP Ping or Network Generic). Chassis, HA, RAID, sensors, IF-MIB, ADOM/device LLD. Host dashboards **Health** (Overview / Hardware / Cluster) + **Network interfaces** |
| **FortiManager Observability** | Nests the parent. **Devices** board. FGFM connect-down is the product ticket. Config out-of-sync stays collect-only (`{$FM.CONFIG.CONTROL}=0` — cfgit owns drift) |
| **FortiAnalyzer Observability** | Nests the parent. **Logs** board. Log lag Average, log-disk **High** at 95% (log loss is the product). Device connect-down on the parent is the Zabbix choice for “device stopped sending logs” |

Parent name has **no** `/` (Zabbix trigger paths are `/template/key`).

### Observability

| Rule | Here |
|---|---|
| Page **symptoms** | ICMP down (**High**). FAZ log disk **High** at 95% (documented exception — the product is about to drop data). Site Disaster is still not this template |
| **Ticket** (Average) | Managed-device connect-down (`{$FM.DEVICE.CONTROL}=1`). RAID failed/degraded. Memory 90%. Disk 90%. HA peer-count if `{$FM.HA.EXPECTED}>0`. FAZ log lag 300s. FAZ licensed GB/day if cap is set. Watchers (unsupported items, nodata ICMP, zero interfaces, device census) |
| **Graph** / next day | CPU 85, disk 80, RAID rebuild/init/verify, sensor out-of-range, iface errors, reboot, SNMP dead |
| One incident | Watchers and chassis tickets hang off ICMP High then SNMP Warning. A dead box is one ICMP High, not a census fan-out |
| Never silent | unsupported items; nodata ICMP 10m; zero interfaces after SNMP up 1h; device census if `{$FM.DEVICE.EXPECTED}>0` |
| Collect first | Config out-of-sync **DISABLED**. ICMP loss/RTT **DISABLED** (Swiss proxy RTT is WAN). CPU High silenced (`{$CPU.UTIL.CRIT}=101`). RAID unavailable(0) silent (VMs). Util 101 |
| Host dashboard | Parent **Health** + **Network interfaces**. FMG **Devices**. FAZ **Logs**. Same chrome as EXOS |
| Severity | **Disaster** = site only. FAZ log-disk High is the documented product exception (same class as FortiOS memory extreme). Warning = next day |

Scale: Info → Warning → Average → High → Disaster. Disaster+High page 24/7; Average = ticket; Warning = next day; Info = log.

### What we alert

| Device | Alert | Sev | Notes |
|---|---|---|---|
| ICMP down | yes | **High** | Per chassis, not a cluster VIP. Own `icmpping` on the parent |
| SNMP dead | yes | Warning | Mgmt blind; FMG/FAZ may still manage or ingest. Same as EXOS/VOSS/IQ |
| ICMP loss / RTT | **no** | — | Items stay for Health; triggers **DISABLED** |
| Unplanned reboot | yes | Warning | `fmSysUpTime < 10m`. Next day. Do not page |
| CPU 85% | yes | Warning | `{$CPU.UTIL.WARN}`. Not a page |
| CPU critical (95) | **no** | — | `{$CPU.UTIL.CRIT}=101` silences High |
| Memory 90% | yes | Average | 5m |
| Disk 80 / 90% | yes | Warning / Average | Parent. FAZ still has High at 95% on the companion |
| FAZ log disk 95% | yes | **High** | FortiAnalyzer Observability. 03:00 page — ingest will stop |
| FAZ log lag 60s / 300s | yes | Warning / Average | Receive-to-index delay. This is the FAZ product failure mode |
| FAZ GB/day license | **no** until cap is known | Average when `{$FAZ.LIC.GBDAY.MAX}>0` | Default 0 disables |
| RAID unavailable(0) | **no** | — | Normal on VMs |
| RAID degraded / failed | yes | Average | Ticket, not a 03:00 page |
| RAID init / verify / rebuild | yes | Warning | Background. Next day unless it stalls |
| Temp vendor-state critical | yes | **High** | `out-of-range-critical` / `not-recoverable`. Same as switch chassis overtemp |
| PSU / fan failed | yes | Average | `failed` / `input-lost`. `not-present` silent |
| HA peer down | **no** until armed | Average when `{$FM.HA.CONTROL}=1` | Standalone default 0 |
| HA peer count | **no** until expected is set | Average when `{$FM.HA.EXPECTED}>0` | Pair typically expects 1 |
| Managed device offline | yes | Average | FGFM down on FMG; log device stopped sending on FAZ. Mute FAZ-native duplicates |
| Config out-of-sync | **no** | — | Trigger **DISABLED**. cfgit owns drift |
| Link down (admin-up ethernet) | yes | Average | Trigger uses `{$IFCONTROL:"{#IFNAME}"}`. FAZ Observability mutes **port2/3/4** (unused NICs on `S-FortiAnalyzer02`). FMG `CH-STA-P-FWMG01` port1 **and** port2 stay armed. A FAZ that uses port2 sets host `{$IFCONTROL:"port2"}=1`. Prefer admin-down unused ports. |
| Interface errors | yes | Warning | In **or** out |
| Sustained util | **no** | dashboard | `{$IF.UTIL.MAX}=101` |
| Serial / name / firmware changed | yes | Info | Manual close |

Do **not** alert on: config drift (cfgit), every ADOM as a page, RAID unavailable on VMs, CPU as High, FortiGate objects, FAZ-native device-down **and** Zabbix connect-down together.

### How it pages

| What the operator sees | What actually fired | Do this |
|---|---|---|
| Box unreachable | Parent ICMP **High** (3 misses) | Console / OOB / RMA. Not a FortiGate WAN ticket |
| SNMP blind, ping lives | Parent **No SNMP data** Warning | Community/user, ACL, proxy. Product may still run |
| FortiGate disappeared from FMG | Parent **Managed device … is offline** Average | FGFM tunnel, routing, device down. Mute with `{$FM.DEVICE.CONTROL}=0` or name NOT_MATCHES |
| Log device went quiet on FAZ | Same connect-down Average | Device stopped sending logs. Do **not** also ticket FAZ-native |
| FAZ about to drop logs | Companion **Log disk is critically full** **High** | Free space / archive policy. This is the 03:00 page |
| FAZ search lagging | Companion log lag Warning → Average | Disk/CPU/ingest path |
| RAID unhappy | Parent RAID Average / rebuild Warning | Ticket. unavailable(0) is a VM, not a disk |
| Chassis overtemp | Sensor **High** | Same as switch overtemp |
| We went blind | Unsupported items / zero interfaces / device census Average | MIB/firmware, IFNAME filter, `{$FM.DEVICE.EXPECTED}` |
| CPU 85% | Warning | Next day. Do not page |
| Config drift | **Nothing here** | cfgit. Do not enable `{$FM.CONFIG.CONTROL}` |

### Health / Devices / Logs dashboards

After the Observability companion is linked: **Monitoring → Hosts → host → Dashboards**.

| Board | Pages | What you see in 5 seconds |
|---|---|---|
| **Health** (parent) | Overview / Hardware / Cluster | ICMP / SNMP / CPU / **Uptime** (same four-tile chrome as EXOS). Fans/PSU/Temp honeycombs. HA mode, RAID, device count |
| **Network interfaces** (parent) | Overview / Port | Admin-up ethernet map + traffic navigator |
| **Devices** (FMG companion) | Overview | Managed-device count + **ADOM** enabled/disabled + FGFM connect honeycomb. Config honeycomb is inventory — cfgit owns tickets. Headline tiles clone parent items (Cloud 7.0 dashboard bind). MIB ADOM *number* stays Latest data (includes factory slots) |
| **Logs** (FAZ companion) | Overview | Disk gauge, log lag, log rate, GB/day, ADOM archive % (real ADOMs), log-device connect. Headline tiles clone parent items because Cloud 7.0 dashboards can only bind objects owned by this template — Latest data shows both names; that is not extra SNMP |

Widget type follows the EXOS rule: gauge = one headline number; item tile = identity or duration; honeycomb = many similar status cells; graph = trend.

### Production Latest data

**`CH-STA-P-FWMG01`** (FortiManager VM, firmware `v7.6.6-build3654`, serial `FMG-VM0A12000925`). Same factory-ADOM dump as FAZ.

| Signal | Last value | Verdict |
|---|---|---|
| ADOM enabled | disabled (1) | **Real.** This manager is not in ADOM mode. All six FortiGates live in `root`. |
| ADOM number / LLD ADOMs | 19 | MIB slot count: 15 empty factory Forti* product ADOMs + `root` / `others` / `Syslog` / `Unmanaged_Devices`. Parent `{$FM.ADOM.NAME.NOT_MATCHES}` drops the Forti* rows from LLD. The Devices **ADOM** tile is enabled/disabled, not this 19. |
| ADOM root FortiGate count 15 vs managed devices 6 | 15 vs 6 | `fmAdomDevNumber` tracks VDOMs (`VDOM number` is 15), not chassis. Census on `{$FM.DEVICE.EXPECTED}` after a quiet count of **6**. Do not alert on the ADOM FGT figure. |
| Factory ADOMs (FortiMail, FortiWeb, …) | 0 FGT / 0 % / 0 logs/s | Empty product slots. Exclude. Keep `root` / `others` / `Syslog` / `Unmanaged_Devices`. |
| Archive / analytics / ADOM log rate / license GB/day | 0 | FAZ objects on a manager. Expected. Do not alert. |
| Six devices (CH-STA-FWZone, CH-ZRH-FWCL01, CN-SHA-JIU-L03-FWGW01, HU-DEB-FWGW02, KR-SEL-HAN-L14-FWCL01, NL-ENS-FWGW01) | in-sync, connect up | FGFM healthy. **Devices → Connect** honeycomb is the product page. Config honeycomb is inventory (cfgit). |
| port1 and port2 | both up, both with traffic | **Do not** admin-down or `{$IFCONTROL:"port2"}=0`. Opposite of FAZ unused NICs. |
| CPU 0 % / memory 39.6 % / disk 54.8 % | under WARN | No ticket. |
| RAID unavailable / HA standalone / 0 peers | VM | Silent (`unavailable(0)` is not an alert). |
| ICMP / SNMP / unsupported item count | Up / Up / 0 | Collection is clean. |
| Log receive / index / lag | 0 | Same FAZ MIB on FMG. Expected. |

**Devices board (this dump):** Devices **6**, ADOM **disabled**, HA peers **0**, Connect six teal cells, Config six in-sync. Health Overview ICMP/SNMP up, CPU 0 %, uptime ~154 d. Cluster RAID unavailable is a VM. Network map is two live 10 Gbps ports.

**`S-FortiAnalyzer02`** (same factory ADOM list). After the parent exclude, Logs **ADOM archive %** keeps `root` (archive **94.3 %** is a **real** Average — do not mute) plus `others` / `Syslog` / `Unmanaged_Devices`. Serial Warning with a stable `fnSysSerial` was false (`DISCARD_UNCHANGED_HEARTBEAT` 6h vs `nodata(2h)` — discard removed). Unused admin-up NICs **port2/3/4** are muted on FortiAnalyzer Observability (`{$IFCONTROL:"portN"}=0`). The parent trigger now reads that context (plain `{$IFCONTROL}` did not). Re-import **Fortinet FMG-FAZ by SNMP** then **FortiAnalyzer Observability**; the three link-down Averages recover. Archive quota critical stays until retention/archive policy frees space.

After Cloud import: ADOM LLD **check-now** on both hosts. Leftover companion item `fmg.observability.adom.count` (`ADOMs`) may remain until deleted in the GUI (`deleteMissing: false`).

### Zero-touch / cutover

**Do not re-run `configure_nbxsync_zerotouch.py` for this pack.** Zerotouch still floors FMG/FAZ on **Network Generic Device by SNMP** (`FortiAnalyzer/Manager`). Both that rule and the new Observability rules enabled would dual-link `icmpping`.

**Live today** (until `--apply-fmg-faz`): platform FortiAnalyzer/Manager → Network Generic + `OS/Network`. SNMP Monitoring already belongs on those **platforms** (FortiGate HTTP apply moved it off role Firewall).

**Operator path** (no zerotouch, no Extreme YAML, no HostSync, no FortiOS retarget):

```bash
python3 scripts/configure_nbxsync_network.py --check-fmg-faz
python3 scripts/configure_nbxsync_network.py --apply-fmg-faz
```

That flag fail-closes if YAML is missing, no FMG/FAZ platform exists, or **SNMP Monitoring** is absent. It then:

| Lever | What it writes |
|---|---|
| Import | **Fortinet FMG-FAZ by SNMP**, then **FortiManager Observability**, then **FortiAnalyzer Observability** |
| Template Rule **FortiManager** | Observability companion + `OS/Network`. SNMP. Pattern `FortiManager` |
| Template Rule **FortiAnalyzer** | Observability companion + `OS/Network`. SNMP. Pattern `FortiAnalyzer` |
| Legacy **FortiAnalyzer/Manager** | **disabled** (Network Generic must not stay enabled) |
| SNMP Monitoring | kept / assigned on FortiManager and FortiAnalyzer **platforms** |
| Colliding templates | pruned from FMG/FAZ devices/platforms/device types: Network Generic, ICMP Ping, FortiGate HTTP/Observability/SNMP, and a direct parent link (companion nests it) |
| Platform macros | FGFM connect on, config-sync off, HA control off, FAZ log-disk High=95 |

Then HostSync the FMG/FAZ hosts (not the FortiGate fleet). Inheritance does not hit live Zabbix until that sync. If someone re-runs zerotouch, it will re-enable Network Generic — run `--apply-fmg-faz` again.

### Macros (template defaults; apply writes platform overrides)

```
{$CPU.UTIL.WARN}            = 85
{$CPU.UTIL.CRIT}            = 101
{$MEMORY.UTIL.MAX}          = 90
{$DISK.UTIL.WARN}           = 80
{$DISK.UTIL.CRIT}           = 90
{$DISK.UTIL.HIGH}           = 95      # FAZ Observability only
{$IF.UTIL.MAX}              = 101
{$IFCONTROL}                = 1       # per-port mute {$IFCONTROL:"{#IFNAME}"}
{$IFCONTROL:"port2"}        = 0       # FAZ Observability only (unused NIC)
{$IFCONTROL:"port3"}        = 0       # FAZ Observability only
{$IFCONTROL:"port4"}        = 0       # FAZ Observability only
{$FM.DEVICE.CONTROL}        = 1
{$FM.DEVICE.EXPECTED}       = 0       # set after a quiet census
{$FM.CONFIG.CONTROL}        = 0       # cfgit
{$FM.HA.CONTROL}            = 0
{$FM.HA.EXPECTED}           = 0       # pair = 1
{$FAZ.LOG.LAG.WARN}         = 60
{$FAZ.LOG.LAG.CRIT}         = 300
{$FAZ.LIC.GBDAY.MAX}        = 0
{$FM.ADOM.NAME.NOT_MATCHES} = ^Forti(Analyzer|Authenticator|Cache|Carrier|Client|DDoS|Deceptor|Firewall(Carrier)?|Mail|Manager|NAC|Proxy|Sandbox|Web)$
                              # Shared parent — factory empty product ADOMs on FMG and FAZ.
{$NET.IF.IFNAME.NOT_MATCHES}= ^(vlan|ssl|hamgmt|npu|disk)
```

OID map: [`templates/fortinet_fmg_faz_snmp/OID_MAPPING.md`](templates/fortinet_fmg_faz_snmp/OID_MAPPING.md).

---


## Canary acceptance (required before fleet HostSync)

Use **one standalone** and **one HA pair**. Do not mass-HostSync until this list is green.

1. The network-script preflight returns HTTP 200 JSON for every FortiOS management IP **before any write**.
2. Both member serials match their NetBox devices.
3. API 200 through the assigned production (Swiss) proxy, not only the NetBox preflight.
4. Revoke the token → one clear API-blindness Average (ICMP still up); `fgate.ha.role` must not return `1`.
5. Stop HTTPS, ICMP remains up → API/port Average, not silent.
6. Break one overlay endpoint while the base API remains healthy → `fgate.observability.inventory` becomes unsupported and the watcher raises Average.
7. Disable a WAN → one Average that stays open until recovery (no `.diff()` / manual-close hole).
8. HA failover → no duplicate WAN incidents (`ha.role` gate).
9. Break HA sync / hide a member → VDOM checksum High or `{$FGATE.HA.EXPECTED}=2` member-count Average, never a false primary role.
10. An “all members” SD-WAN health-check does not look like a healthy WAN ([ZBX-26072](https://support.zabbix.com/browse/ZBX-26072)).
11. Zero-discovery and unsupported-item Averages fire, then clear.
12. Proxy failure / maintenance / notification delivery.
13. Record API response time, proxy queue, and total API request rate.
14. Shadow LogicMonitor/SNMP for 2–4 weeks with an explicit parity matrix.

---

## Later

Per-cluster REST tokens and Zabbix Vault secrets (fleet-wide token blast radius). Certificate verification + unique DNS/SANs per ha-mgmt. Logical HA cluster host if `ha.role` gating is not enough. Thin IPsec / session-table / sensor items (HTTP or a **minimal** SNMPv3 `authPriv` SHA/AES companion — never another `icmpping`, CPU family, or interface LLD). Named policy canaries. Site Disaster parent. Path Average → stock ICMP High parent (cannot be a template-level parent without a duplicate `icmpping` link). Memory extreme Disaster → High once the site parent exists. Circuit strategy / ISP commit graphs on [05](05-internet-circuits.md) reusing Path Loss/Probe. FMG `{$FM.DEVICE.EXPECTED}` after a quiet census. FAZ `{$FAZ.LIC.GBDAY.MAX}` once the licensed cap is known.

Do not block Extreme/AP cutover on this page.
