# FortiGate over API — analysis

Operator page: [03-fortinet.md](../03-fortinet.md).  
This note is the research that page compresses. Do **not** treat it as a second policy, and do **not** copy Extreme switch/AP trigger patches onto Forti HTTP.

Sources: official Zabbix 7.0 `templates/net/fortinet/` (`FortiGate by HTTP`, `FortiGate by SNMP`), [integrations/fortinet](https://www.zabbix.com/integrations/fortinet), ZBX-25448, ZBX-27082, ZBX-26072, ZBXNEXT-10433, FortiOS 7.4.5+ REST token behaviour.

---

## Decision

Monitor FortiGates with companion **FortiGate Observability** (nests stock **FortiGate by HTTP** + **ICMP Ping**). Do **not** also assign ICMP Ping or FortiGate by HTTP on FortiOS objects (nested parents). Winning CG is **FortiGate HTTP** on Platform FortiOS so Site Group Agent Monitoring does not add ICMP Ping again. Do **not** also link **FortiGate by SNMP** or **Network Generic**. Do **not** put Forti templates or the REST token on generic role **Firewall** (FMG/FAZ share it).

Live nbxSync today still points FortiOS at **FortiGate by SNMP**. Retarget with `configure_nbxsync_network.py --apply-fortigate-http` — **do not re-run zerotouch**. The flag fails closed, looks up Cloud **Zabbix, 7.0-2**, patches ZBX-27082 in place, and never imports bundled 7.0-3. HostSync **both members** of a cluster (`primary_ip4`).

---

## What Zabbix actually ships

Official Fortinet templates (Zabbix 7.0+): **FortiGate by HTTP**, **FortiGate by SNMP**.  
No official FortiManager or FortiAnalyzer template ([ZBXNEXT-10433](https://support.zabbix.com/browse/ZBXNEXT-10433) Won’t Do). FMG/FAZ stay **Network Generic Device by SNMP** + ICMP.

HTTP collection is HTTP agent + **JS Script** items on the **proxy/server**. No external scripts. No Agent/SNMP interface required for metrics. The poller is the Swiss proxy talking **HTTPS to the FortiGate GUI/API**, not a laptop curl.

Tested upstream on FortiGate **v7.6.4**. Production FortiOS must be treated as unknown until a canary: **7.4.5+ rejects tokens in the URL** unless `rest-api-key-url-query` is enabled (do not enable that). Template **7.0-2+** sends `Authorization: Bearer`. Import the **latest 7.0** HTTP template onto lab **7.0.29**.

| Bug | What | Why it matters here |
|---|---|---|
| [ZBX-25448](https://support.zabbix.com/browse/ZBX-25448) | Token moved from URL query to Bearer header | Old HTTP templates 401 on FortiOS 7.4.5+ |
| [ZBX-27082](https://support.zabbix.com/browse/ZBX-27082) | Reused `HttpRequest` sends **duplicate** Authorization → 401 | Fixed by recreating the request per call; **7.0.30rc1** (not 7.0.29rc1). Cloud 7.0-2 still has the bug — `--apply-fortigate-http` patches scripts in place and aborts if they stay vulnerable |
| [ZBX-26072](https://support.zabbix.com/browse/ZBX-26072) | SD-WAN **member** LLD fails when a health-check is “all members” | Health-check LLD can still work; member graphs go empty. Census, not a silent “WAN is fine” |
| [ZBX-26408](https://support.zabbix.com/browse/ZBX-26408) | Interface API omits VLANs unless `include_vlan=true` | Apply adds `include_vlan=true&vdom=*` on the monitor iface call so other-VDOM VLANs can appear during open canary LLD |

---

## HTTP vs SNMP (keep this matrix)

| Signal | HTTP (chosen) | SNMP (live today / fallback) |
|---|---|---|
| ICMP | **none** — link **ICMP Ping** | `icmpping` High on 3 misses |
| Management plane | `net.tcp.service` on `{$FGATE.SCHEME/FQDN/PORT}` + `fgate.api.status` | SNMP agent availability |
| CPU / memory / disk | yes | CPU/mem; disk weaker |
| Interfaces (status, bits, errors, speed) | yes | yes (IF-MIB + Fortinet) |
| SD-WAN members + health-checks (loss/latency/jitter) | **yes — this is why API wins** | health-check OIDs exist; HTTP is the first-class path |
| FortiGuard licenses / expiry | **yes** | weak / absent |
| Firmware available | yes | inventory change only |
| Firewall **policy** LLD (sessions/hits/bytes) | yes — item bomb if unfiltered | no |
| HA mode / members / sync | **no** | **yes** (`fgHa*`) |
| IPsec tunnel LLD / SSL-VPN user count | **no** | **yes** |
| Global session table `fgSysSesCount` | **no** (only per-policy / per-SD-WAN-member) | **yes** |
| Hardware sensors (temp / PSU / fan) | **no** | **yes** |
| IPS / AV event rates | **no** | yes (often HA-member scoped) |
| VDOM LLD | all VDOMs the token can read after apply `?vdom=*`; `fgate.device.vdom` is still the login VDOM | **yes** |
| FortiAP / WTP | **no** | yes — do not use; APs are [02](../02-extreme-access-points.md) |
| SNMP traps | n/a | in template; collect ≠ page |

Do **not** dual-link HTTP + SNMP to “fill the gaps”. Duplicate CPU/iface LLD, two link-down families, and SNMP re-adds `icmpping` on top of ICMP Ping. HA / IPsec / sensors are **later** thin HTTP items (`/api/v2/monitor/system/ha/peer` and VPN monitor endpoints) or a conscious SNMP-only exception — not a second platform template on the same host.

---

## What an observability engineer should watch

A FortiGate is not a switch. Users feel **paths** (SD-WAN / IPsec / last circuit at a site), not every VLAN or every firewall policy hit.

| Layer | Page / ticket | Graph | Leave alone |
|---|---|---|---|
| Box reachable | ICMP **High** | loss/RTT (triggers off) | — |
| API reachable | API/port dead while ICMP up = **Average** (blind) | per-endpoint `*.data_errors` | — |
| Device health | memory Average; CPU Warning | disk, session counts later | CPU/mem/disk **High** stock |
| Path | SD-WAN member/health **down** after WAN filters = Average; **last path at site = Disaster on the site**, not this template | loss / latency / jitter | every physical iface |
| License | unsuccessful = Average | expiry Warning (7d) | `no_support` / `no_license` rows (already NOT_MATCHES) |
| Policy | — | named canaries only | discover-all policies |
| HA / IPsec | later (peer/sync); ICMP High per member now | later | do not pretend HTTP has HA LLD; do not hide members behind a VIP |
| Firmware | Info or off | inventory | Info forever if FortiGuard always offers an image |

One incident: **API → ICMP → site**. Do not also ticket Extreme `UW`, Forti WAN iface, and Cato for the same ISP cut ([05](../05-internet-circuits.md), [04](../04-cato.md)). Forti WAN ≠ fabric `USW`.

---

## Stock HTTP landmines (defaults that will page)

Do **not** fork the stock template. Macro / trigger-status patches on apply, same idea as EXOS ICMP-disable.

| Default | What happens if left stock | What we do |
|---|---|---|
| `{$FGATE.SCHEME}`=`http`, `{$FGATE.API.PORT}`=`80` | Port-unavailable Average immediately (GUI is HTTPS/20443 on ha-mgmt) | Template-level **https** / **20443**. Per-host FQDN + token |
| `{$NET.IF.UTIL.MAX}`=`95` | 15m util Warning on any discovered iface | **101** (same as Extreme) |
| `{$NET.IF.CONTROL}`=`1` on **all** discovered ifaces | Link-down Average on every VLAN/VPN/loopback that flaps | Scope LLD to enabled+cabled NetBox links. Keep reserved `mgmt` discovered but apply device context `{$NET.IF.CONTROL:mgmt}=0`: FortiOS reports false physical-down there, while ICMP/API own availability |
| CPU CRIT 95 = **High**, mem CRIT 90 = **High**, disk free 10% = **High** | 03:00 pages for busy/log disk | Duplicate stock CPU/memory High is silenced at 101. Companion memory pressure uses configured green/red/extreme thresholds; disk High remains off |
| `{$FIRMWARE.UPDATES.CONTROL}`=`1` | Info as long as FortiGuard lists an image | `0` if it never clears |
| `{$SERVICE.LICENSE.CONTROL}`=`1`, expiry 7d | Average on unsuccessful; Warning at 7d | Keep for production FortiGuard SKUs. Platform context `{$SERVICE.LICENSE.CONTROL:forticloud}=0` silences unused FortiCloud `Unknown (30)` while retaining the metric |
| Policy LLD `{$FWP.FWNAME.MATCHES}`=`.*` | No policy **triggers**, but ~8 items × every policy | MATCHES=`^$` **and** disable `fgate.fwp.get_data` + discovery (MATCHES alone still polls) |
| Link-down uses `.diff()` + **manual close** | ACK a down WAN and it **will not re-fire** until another up→down | Patch to sustained `#3` + auto-recover + `ha.role` gate |
| No `vdom=*` on iface/SD-WAN scripts | Only the REST login VDOM is discovered; FortiOS 7.6 SD-WAN monitor results may be arrays | Version-pinned compatibility patch normalizes array/object envelopes and all VDOMs |
| Secondary 404/424 aborts a multi-request collector | Healthy member/CMDB data is discarded | Fetch wrapper classifies inactive-secondary 404/424 as absent endpoint and preserves successful data |
| Broad interface LLD | VLAN/VPN/loopback/unused interfaces generate noise | Exact Device regex from enabled+cabled NetBox interfaces observable in FortiOS CMDB; reserved `mgmt` remains discovered with its link trigger context-disabled; safe template default `^$` |
| `{$NET.IF.IFNAME.NOT_MATCHES}`=`.*` | MATCHES `.*` **and** NOT_MATCHES `.*` excludes every iface | Keep `CHANGE_IF_NEEDED`; never set NOT_MATCHES to `.*` |
| Stock high-error trigger | README expression checks **in_errors twice** (no out_errors) | patched to in **or** out |

SNMP-only landmines we **leave behind** by not using SNMP as the long-term path: ICMP loss/RTT Warning from the CH proxy (WAN RTT), HA member CPU High, FortiAP WTP noise. If SNMP stays on a host during the mixed cutover, those still apply.

FortiGate `port1` is **not** a WAN class. Apply intersects each device’s enabled+cabled NetBox interfaces with names exposed by FortiOS CMDB, then writes `{$NET.IF.IFNAME.MATCHES}` and the matching `{$NET.IF.DISCOVERY.MIN}`. Unobservable model-specific ports are logged instead of becoming permanent false alarms. It also writes `{$NET.IF.CONTROL:mgmt}=0`: `mgmt` telemetry stays visible, but the unreliable FortiOS physical-link field cannot page; ICMP/API monitor management availability. SD-WAN member/health LLD remains independently scoped with `.*`; apply sets `{$FGATE.SDWAN.EXPECTED}` to the exact configured member count, including zero.

---

## HA

**Default: one Zabbix host per physical FortiGate.** Poll that unit’s **reserved HA management IP** (`ha-mgmt` / in-band `management-ip`), not a floating WAN VIP.

Fortinet documents reserved HA management specifically so SNMP and other NMS tools can monitor **each cluster unit** on its own address. Those IPs are **not** config-synced. NetBox already models two devices; zero-touch will create two hosts.

### Why VIP-only is the wrong default

Stock **FortiGate by HTTP has no HA member/sync LLD**. If Zabbix only talks to a floating address:

- Primary dies, VIP/GUI fails over, ICMP + API stay green.
- The dead chassis never pages.
- Split-brain / checksum mismatch is invisible.

That is fail-silent on the exact failure HA exists to survive.

A WAN/SD-WAN **data-plane VIP is never** `{$FGATE.API.FQDN}` — HTTPS GUI is not that address, and it is a **path** signal ([05](../05-internet-circuits.md)), not a poller target.

### Why not “only primary” either

Polling only the current primary (shared DNS that always follows master) has the same blind spot as a VIP: the backup is unmonitored until it becomes master. Use it only when the secondary has **no** unique mgmt IP.

### Duplicate path tickets (not a HostSync problem)

Config **is** synced. HTTP LLD of SD-WAN / wan1 / policies on **both** members can double every WAN-down Average. That is the only good argument for a single logical host — and it is solved later by **gating path triggers**, not by skipping HostSync of the backup or inventing a VIP host.

HostSync of both members is the same job twice: shared Zabbix monitoring token from nbxSync Platform FortiOS + templates, unique rendered `{$FGATE.API.FQDN}` from each `primary_ip4`. The NetBox inventory automation token is separate. Do not give the members different templates, and do not flip macros on failover as part of cutover.

| Signal | Both physical members | Alert ownership |
|---|---|---|
| ICMP, API, CPU, memory | collect on both | chassis health remains per member |
| SD-WAN / WAN iface tickets | collect on both | gate on authoritative `fgate.ha.role=1` from `system/ha-peer` |
| Licenses / firmware Info | collect on both | primary-only gate avoids duplicates |
| HA membership and VDOM checksums | compare from both | member count Average on each chassis; VDOM checksum mismatch High on the primary only |

Role collection matches the local system serial to `/api/v2/monitor/system/ha-peer`. Unknown transport/auth/role is unsupported, never primary. `/api/v2/monitor/system/ha-checksums` supplies the authoritative synchronized VDOM checksum signal; `/api/v2/monitor/system/ha-nonsync-checksums` contains intentionally member-local/non-synchronized configuration and must not drive an HA sync alarm. The mismatch metric remains on both hosts for visibility, but only `ha.role=1` creates the incident.

### Token / trusted hosts

REST API **admin** usually syncs; one token often works when you hit each member’s mgmt IP. **Trusted hosts** are per ha-mgmt instance — allow the Swiss proxy on **both**. Canary the secondary; 401 there is not “the template is wrong”.

### Fallback

VIP- or primary-DNS-only when the backup is unreachable. Record it as a watcher gap (HA pair with one Zabbix host).

---

## Health dashboard

Stock HTTP has no host **Health** board. Companion **FortiGate Observability** ships **Health**, **Network interfaces**, and **Path**, same chrome as EXOS/VOSS/IQ — not a second vendor gallery. Hex labels are **VDOM-prefixed** after apply (`root/wan1`, `Untrust/Google/wan1`) so production and guest internet-failover SD-WAN do not share a nameless pile of `wan1`s.

| Page | 5-second read |
|---|---|
| **Health → Overview** | ICMP / API / CPU gauges + **Uptime** item tile. Problems. CPU+memory trend, Uptime history |
| **Health → HA** | Memory (the Forti analog of EXOS Temp — conserve-mode kills sessions) + HA role / members / VDOM mismatches as **item** tiles |
| **Network interfaces → Overview** | 72×6 link-status map |
| **Network interfaces → Port** | Navigator of link / speed / errors / **bits** with history |
| **Path → Overview** | Two 36×6 maps (SD-WAN members + health-checks) |
| **Path → Loss** | Packet-loss honeycomb (0 / 5 / 20). HTTP probe seed for [05](../05-internet-circuits.md) |
| **Path → Probe** | Navigator grouped by **vdom** — loss / latency / jitter / status / **byte rate** |

### Why each widget exists

| Question | Where | Widget | Why this type |
|---|---|---|---|
| Can we reach the box? | Overview | ICMP gauge | Binary, same chrome as EXOS |
| Can we see inside it? | Overview | API gauge | Control plane — SNMP's job on EXOS |
| Is compute saturating? | Overview | CPU gauge; **CPU / memory** graph | Memory belongs on the trend, not a 4th gauge (EXOS rule). Conserve-mode still pages from the trigger |
| How long has the OS been up? | Overview | **Uptime** item tile + graph | Same 4th tile as EXOS/VOSS/IQ. Duration, not 0–100 |
| What is broken right now? | Overview | Problems strip | Tickets, not decoration |
| Is this chassis in conserve-mode? | HA | Memory gauge (82/88/95) + trend | FortiOS green/red/extreme. Display colours are the estate defaults; triggers use per-device macros |
| Who is primary? | HA | HA role **item** | 0/1 identity with valuemap — not a gauge with fake max=1 |
| Is the peer still there? | HA | Member count item | Census, not a 0–10 gauge |
| Are we split-brain on config? | HA | VDOM mismatch count item | 0 green, ≥1 red. Ticket is primary-only |
| Which WAN/HA port is down? | Network interfaces | Honeycomb of **VDOM/IFNAME** (`root/wan1`) | Colour without an ID is a Christmas tree. Forti link 0=up 1=down (inverted vs IF-MIB). **72×6** like a switch |
| How much traffic on *this* WAN? | Network interfaces → Port / Path → Probe | Navigator + selected-metric history | It selects inherited HTTP items by name; template dashboards cannot refer to graph prototypes owned by a nested parent |
| Which SD-WAN member / probe is down? | Path | Two 36×6 maps | Member link (`root/wan1`) vs health-check (`root/Google/wan1`). Empty = none discovered, not “WAN is fine” |
| What is loss on production vs guest internet? | Path → Loss | Metric honeycomb | Only HTTP probe we have (latency/jitter and byte rate live on Probe). `Untrust` vs `root` must not share a cell label |
| Why is *this* probe sick? | Path → Probe | Navigator grouped by **vdom** | Does not repeat Overview maps |

Do **not** put HA role, interface count, or SD-WAN count on a gauge with a hardcoded max. A site with 3 members looked 30% empty; a site with 12 looked broken. Item tiles and honeycombs scale.

Path Overview is scan-only (two maps + traffic). Problems live on Health. Do not duplicate Path as a page *inside* Health. Do not put physical interfaces back on Path — they live on **Network interfaces**.

---

## How we alert

Same SRE bar as Extreme: page symptoms, ticket partials, graph causes, never fail silent.

```
SD-WAN / WAN iface  →  API dead  →  ICMP down  →  site unreachable
CPU / mem / license →  ICMP down
```

| Channel | Zabbix sev | Forti |
|---|---|---|
| SMS/call 24/7 | Disaster, High | ICMP down per **member**. Memory **extreme** (Disaster — exception; FortiOS is refusing new sessions). HA VDOM checksum **High** on primary. Memory **red** High |
| Ticket, business hours | Average | API/port blind. Path down (primary only, sustained `#3`). HA member count. Unsupported items. Interface / SD-WAN census. License unsuccessful |
| Next day | Warning | CPU 85%. SD-WAN loss. Interface errors. Per-endpoint API errors. License 7d. Reboot (`uptime < 10m`, apply retunes stock Info) |
| Log | Info | Firmware (off if `CONTROL=0`). Serial / sysname |

**One incident per chassis outage:** companion watchers depend on no-API → no-ICMP. **One incident per WAN cut:** path triggers gated on `ha.role=1`. Secondary still has ICMP/API/CPU so a dead backup is not silent.

**What must not page:** util 95%, stock CPU/mem High, every policy, VLAN/VPN LLD, firmware-available Info, ICMP loss/RTT from the Swiss proxy, reserved `mgmt` physical-down, both HA members for the same SD-WAN member.

Actions/media are **not** in this template. Cutover still needs the estate action that maps High/Disaster → pikett and Average → ticket. LogicMonitor parity failed open there.

---

## Remaining gaps (after dashboards)

| Gap | Why it is not silent-fail | Do later |
|---|---|---|
| Path Average does not depend on stock ICMP High | Dead mgmt path can still open WAN tickets on the current primary | Parent after ICMP triggerid is stable. Template-level parent needs a duplicate `icmpping` link — skip |
| Memory **Disaster** vs “Disaster = site only” | Extreme *is* user impact (new sessions die). HA peer may still forward | Keep until site parent exists; then drop this to High |
| No PSU/fan/temp | HTTP does not collect it | Thin SNMPv3 or HTTP sensor item — never a second `icmpping` |
| IPsec state | Inventory census only | After endpoint semantics + expected-tunnel macros |
| Site last-path Disaster | Contracted; not built | 05 + site host |
| Proxy last-seen | Hosts go *unknown* | Cloud console / later |

---

## Zero-touch / cutover (do not break live SNMP Fortis)

Live today (`configure_nbxsync_zerotouch.py` + locked GUI checklist) until the network-script flag:

- Template Rule **FortiOS** `FORTIOS|FortiOS` → **FortiGate by SNMP** + `OS/Network`
- Role **Firewall** floor → same SNMP template
- Role Firewall → **SNMP Monitoring** CG (`MONITORING` MD5/DES)
- ICMP Ping is **not** on fleet SNMP Monitoring (Forti SNMP already has `icmpping`)
- FMG/FAZ → Network Generic (do **not** assign FortiGate HTTP by manufacturer)

**Do not re-run zerotouch for the HTTP cutover.** Zerotouch would put FortiOS back on SNMP.

Operator path: `python3 scripts/configure_nbxsync_network.py --apply-fortigate-http`

- Look up **FortiGate by HTTP** already in Zabbix Cloud (**Zabbix, 7.0-2**). Never import bundled 7.0-3. Fail closed if missing/wrong vendor
- Before any write, require HTTP 200 JSON from every FortiOS `primary_ip4` using NetBox inventory automation’s `NBX_FORTIGATE_TOKEN`; separately require the nbxSync Platform FortiOS monitoring token to exist. The NetBox-origin check does not prove the Zabbix proxy path
- Patch the version-pinned parent with a fresh `HttpRequest` per request plus tested multi-VDOM interface/SD-WAN normalization; patch WAN state, policy master off, unsupported absolute-capacity items, stock CPU/mem CRIT 101, and reboot Info→Warning. Import **FortiGate Observability** with navigators for inherited interface and SD-WAN traffic items; a companion dashboard cannot reference graph prototypes owned by the nested HTTP parent
- FortiOS → Observability (`HostInterfaceRequirement` **ANY**). Not role Firewall
- Preserve the existing NetBox `{$FGATE.API.TOKEN}` on Platform FortiOS. `NBX_FORTIGATE_TOKEN` remains the separate automation credential
- Keep `{$FGATE.API.FQDN}` as Platform FortiOS Jinja. Prune Device-level literals
- Write an exact per-device interface LLD regex/count from enabled+cabled NetBox interfaces observable in FortiOS, set the exact configured SD-WAN member count, context-disable only reserved `mgmt` link alerts (ICMP/API own availability), and refresh device green/red/extreme memory threshold macros
- Prune Forti/ICMP templates and SNMP Monitoring from generic role Firewall/FortiOS objects; assign SNMP only to FortiManager/FortiAnalyzer platforms
- Assign CG **FortiGate HTTP** on Platform FortiOS (Agent @ primary, no duplicate ICMP parent)
- Overlay auth/transport/JSON failures become unsupported; optional 404/424 endpoints do not abort successful census data. HA role failures never return primary
- Do **not** dual-link HTTP+SNMP. No Extreme YAML, no mass-HostSync. HostSync both members of the first cluster, then the rest

Changing the FortiOS Template Rule on a live estate **will** retarget on next HostSync of that firewall.

Locked [`docs/netbox-zabbix/configuration.md`](../../docs/netbox-zabbix/configuration.md) still lists FortiGate by SNMP. That file stays locked; this note is the drift record.

---

## FortiManager / FortiAnalyzer

No official template. Keep ICMP High + (FAZ) disk/log later. Device-sync vs cfgit: cfgit owns config drift. Do not assign FortiGate HTTP onto FMG/FAZ (wrong API, wrong objects).
