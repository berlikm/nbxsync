# ExtremeControl / XIQ-SE

Site Engine is the NBI and log brain. ExtremeControl engines are the RADIUS boxes users hit. Same bar as [01](01-extreme-switching.md): **page what users feel, never fail silent, one incident per root cause**. OS + ICMP stay on [06](06-network-vms.md) / nbxSync. This page is **application** only.

Official Zabbix Extreme pack has **no** SE / NAC template. Collection is **HTTPS GraphQL on Site Engine** (OAuth client credentials). Do **not** put GraphQL on each engine. Do **not** install a Zabbix agent on vendor OVAs for this (BIN upgrades). Keep Linux agent if it is already there (CPU / disk).

This page is the **target contract**. YAML lives in `templates/xiqse_observability/`, `templates/extremecontrol_observability/`, and `templates/extremecontrol_snmp/`. Refresh with `configure_nbxsync_network.py --apply-xiqse`.

---

## Observability

| Rule | Here |
|---|---|
| Page **symptoms** | Engine ICMP down. RADIUS 1812 dead while the box is up (users cannot 802.1X) |
| **Ticket** (Average) | SE NBI/GUI dead while ICMP up (ops blind; RADIUS often still works). Engine disconnected from SE. **NAC not forwarding auth logs to SE** (`lastAuthEventTime` stale while RADIUS is up). SE ingest jam. Engine `needsEnforce` stuck |
| **Graph** / next day | Unique MACs that authenticated in **24h** (XIQ-NAC-S). Pilot + Navigator seats used / remaining (live equivalent of Extreme's XIQ-SE licensing-calculation workflow). Heap, uptime, version, engine load vs hardware capacity. Per-engine RADIUS request/success/fail rates (SNMP) |
| One incident | RADIUS / GraphQL → ICMP → **site**. Engine tickets do not also fire SE. SE ingest jam is **one** SE ticket, not N engines |
| Never silent | GraphQL nodata; zero engines discovered; 24h census truncated (`count == maxResults`). SNMP-dead Warning on the engine if the MONITORING profile stops answering |
| Collect first | Heap / CPU thresholds off until a quiet baseline. Log-forward is elapsed `{$XIQ.NAC.FRESH}` (no wall clock — engines are in CH / CN / HU / KR). SNMP fail-ratio and contact-lost gated (`101` / CONTROL=0) |
| One `icmpping` | Nested only if the host does not already ping. Do not also assign Network Generic |
| Host dashboard | **Health** Overview + Licenses: NAC **SE used**. Pilot **Cloud consumed** once 08 is linked (`--apply-xiq-cloud`); until then the 320 tile is SE inventory only |

Disaster is campus-wide auth later, on a **service / site** host — not on this template.

---

## How Extreme counts licenses

Three subscription pools. Same three the Extreme **XIQ-SE licensing calculation** workflow reports for an XMC → XIQ-SE move ([KB 000098925](https://extreme-networks.my.site.com/ExtrArticleDetail?an=000098925), `.xwf` v116). That workflow is a **one-shot** report: it reads `appdata/license` and the SE database, and needs NMS-ADV / 27001. We do **not** run it from Zabbix. We graph the same pools continuously from NBI.

| Pool | SKU | Have (purchased) | Consume (used) |
|---|---|---|---|
| Access Control | `XIQ-NAC-S` | Cloud / CG `{$XIQ.NAC.TOTAL}` (Portal 3000). NBI has no entitlements field | **SE**: unique MACs that authenticated in a rolling 24h (`xiqse.nac.used24h`). Accounting does not count. Usernames are not the license |
| Pilot | `XIQ-PIL-S-C` | **Cloud** `devices` / Portal 581 | **Cloud** `activated` / Portal 578. Includes IQ Engine **APs**. `xiqse.pilot.used` **320** is only SE `network.devices` with `XIQ_PILOT` (switches + Control engines in SE inventory) — not APs, not the billable used |
| Navigator | Navigator SKU | **Cloud** | **Cloud** `activated`. SE `xiqse.nav.used` is SE inventory only |

Per-engine **Current Capacity** `1365/3000` is **hardware load** (24h unique on that engine vs engine rating). Changing it does not change the global NAC license.

Exceeding NAC seats is a four-stage violation (GUI pop-up → events stop for overflow MACs → catch-all profile). Stage 3 is the “RADIUS green, SE has no events” failure mode.

At 0 Pilot you cannot onboard a switch or another engine. At 0 Navigator you cannot onboard another Navigator-tier device. Existing RADIUS still works.

NBI has **no** entitlements field. NAC used we **count** on SE. Pilot **consumed** is Cloud (APs are not in SE `network.devices` — that is why 320 ≠ 578). Purchased totals on CG **XIQ-SE licenses** stay the stand-in until [08](08-extremecloud-iq.md) is live. `--apply-xiqse` creates those assignments at 0 if missing and **never overwrites the CG**; it mirrors the CG onto the Site Engine platform so HostSync can push them (HostSync inherits platform macros; it does not expand CG macros at resolve time). Refresh the CG when you buy more, re-apply, then HostSync. Do not scrape the GUI. Do not JDBC the SE database. Do not put the Cloud REST client inside the NBI SCRIPT. Do not set these as Zabbix host macros on `ch-sta-p-ensa01`. `{$…TOTAL}=0` means remaining shows 0 (not “out of seats”) and cap tickets stay silent. Never `581 − 320`.

Platform ONE / Advanced / Standard states are counted on `xiqse.lic.platformone` (graph). Tickets stay off until that SKU is in use. Pending onboard is `xiqse.lic.pending` (graph).

---

## What we alert

### Site Engine (one NetBox host)

| Thing | Alert | Sev | Notes |
|---|---|---|---|
| ICMP down | yes | **High** | From 06 / nested ICMP — not a second ping |
| HTTPS 8443 / NBI unexpected | yes | Average | Ops blind; RADIUS may still work (SE upgrade) |
| GraphQL nodata | yes | Average | Token, TLS, or SE down |
| Zero Control engines discovered | yes | Average | Filter / rights / template wrong |
| Engine disconnected from SE | yes | Average | LLD on SE. Auth may still work locally. `connected` is **not** on 25.5.12.6 `NacAppliance` — item stays `2` (silent) |
| NAC not forwarding auth logs to SE | yes | Average | Per engine: newest `lastAuthEventTime` older than `{$XIQ.NAC.FRESH}` (default 24h elapsed, **any time zone**). Override a quiet engine with `{$XIQ.NAC.FRESH:"<engine-ip>"}`. `{$XIQ.NAC.FRESH.CONTROL}` still gates the ticket. Age `-1` = no event in the census (silent). Age `0` = just now, or SE clock slightly ahead of the proxy. Not syslog to a SIEM |
| SE ingest jam (E-to-Sav / drops) | **no** until the field exists | Average | One SE ticket if GraphQL exposes it on canary |
| Engine `needsEnforce` stuck | yes | Average | Config never pushed |
| 24h unique MACs ≥ `{$XIQ.NAC.TOTAL}` | yes | Average | License violation in progress |
| 24h unique MACs ≥ `{$XIQ.NAC.USED.WARN}`% of total | yes | Warning | Default 90%. Dayside buy more |
| 24h census truncated | yes | Average | `count == {$XIQ.NAC.ES.MAXRESULTS}` — number is a lie |
| Pilot used ≥ `{$XIQ.PILOT.TOTAL}` | **no** as the billable consume (under-counts APs) | Warning | `xiqse.pilot.used` is SE inventory only. Ticket Cloud available=0 on [08](08-extremecloud-iq.md). Keep this trigger silent (`TOTAL=0`) until 08 |
| Pilot remaining ≤ `{$XIQ.PILOT.REMAIN.WARN}` | **no** until 08 | Warning | Same: remaining vs SE 320 is a lie. Cloud `available` is the 3 seats |
| Navigator used ≥ `{$XIQ.NAV.TOTAL}` | yes | Warning | Cannot onboard a Navigator-tier device. `TOTAL=0` silences |
| Navigator remaining ≤ `{$XIQ.NAV.REMAIN.WARN}` | yes | Warning | Default 2 |
| Unplanned SE reboot (`upTime`) | yes | Warning | |
| Cert on 8443 | **no** | — | No agent on the OVA for this pack; YAML cannot carry `web.certificate.get`. TLS verify stays on the GraphQL SCRIPT |
| Heap / RAM / threads | **no** until baseline | — | Items + Health graphs |
| Version change | yes | Info | |
| `network { devices { up } }` | **no** | — | Switches already have SNMP/ICMP |

### Control engine (each NetBox role **NAC**)

| Thing | Alert | Sev | Notes |
|---|---|---|---|
| ICMP down | yes | **High** | Users fail 802.1X at this site’s engines |
| RADIUS 1812 dead, ICMP up | yes | **High** | Requires vendor **RADIUS Monitor Clients**. Zabbix `net.udp.service` is **not** RADIUS — do not use it |
| `freeRadiusEnabled` false | yes | **High** | If NBI returns it on the engine object |
| TCP 8444 | **no** as High | Warning later | Admin UI, not auth |
| Engine hardware 24h unique ≥ rating | yes | Warning | Per-engine load, not the global license. 25.5.12.6 NBI `capacity` is **0** on every engine — trigger requires `last(capacity)>0` |
| Linux CPU / disk (existing agent) | yes | Warning | Do not add an agent for this |
| SNMP agent dead, ICMP up | yes | Warning | `ExtremeControl by SNMP`. Same MONITORING profile as switches. RADIUS may still work |
| Engine lost SNMP to switches (`contact.lost` > 0) | **no** until opted in | Warning | Canary 2026-08-28 was **0** on all five ENACs. `{$NAC.SNMP.CONTACTLOST.CONTROL}` |
| Auth fail ratio / drop rate | **no** until baseline | Warning | `{$NAC.SNMP.FAIL.WARN}=101`. Challenges are EAP, not failures |

Do **not** alert on: Cloud IQ from **this** template (companion is [08](08-extremecloud-iq.md)), every end-system MAC as a host, GraphQL mutations, accounting-only storms, Guest/IoT (GIM) until the same 24h pattern is proven.

---

## What we graph (no ticket unless the table says so)

On **Site Engine → Health**:

| Graph | Unit | Why |
|---|---|---|
| **NAC license used (24h unique MACs)** | count | The number Extreme bills / enforces |
| NAC license remaining | SCRIPT: 0 while `{$XIQ.NAC.TOTAL}` is 0, else purchased − used | **Item only** (Health tiles show used). **0 until you set the CG.** That is not “out of seats” and not −2175. NBI cannot read Administration → Licenses |
| NAC used % of entitlement | % | Warning at 90% |
| Unique **usernames** 24h | count | Capacity story; **not** the license |
| Pilot SE inventory (`xiqse.pilot.used`) | count | Switches + engines in SE only. **Not** APs. Billable consume is 08 Cloud `activated` |
| Pilot remaining | — | Do not graph SE remaining as if it were Portal 3 |
| Navigator used / remaining | count | `XIQ_NAVIGATOR` |
| Pending / Platform ONE | count | Graph; no ticket yet |
| Engine count | count | Census |
| Heap used / max, physical RAM, threads | bytes / count | Collect first |
| `upTime` | s | Reboot |

On **Site Engine → Engines** (LLD, one row per engine):

| Graph | Why |
|---|---|
| 24h unique MACs on **this** engine | Hardware load (`1365/3000`) |
| Age of newest `lastAuthEventTime` | NAC → SE log-forward gap |
| Connected / licensed / `needsEnforce` | Honeycomb |

Do **not** LLD every laptop. Sample and count on SE.

On each **Control engine → Health** (SNMP):

| Graph | Why |
|---|---|
| Auth requests / successes / failures per second | Engine is doing RADIUS. Failures going up is **not** RADIUS-dead |
| RADIUS challenges per second | EAP; large vs successes on the 2026-08-28 canary |
| Dropped / invalid / duplicate | Error rates |
| Contact-lost switches | Engine → switch SNMP (the other direction). 0 on all five ENACs |
| Captive portal / assessment / connected agents | Assessment was 0 fleet-wide |

---

## Scope

| Role / class | In | Out |
|---|---|---|
| Site Engine | GraphQL NBI + 8443 + SE used seats + engine LLD | SNMP walk of the OVA, Cloud REST inside NBI JS (Cloud companion is [08](08-extremecloud-iq.md) on this host) |
| Role **NAC** (Control engine) | ICMP + RADIUS monitor + optional existing Linux agent + **ExtremeControl by SNMP** (`ENTERASYS-NAC-APPLIANCE-MIB`) | GraphQL to the engine, second ping, EXOS/VOSS/IQ templates |
| Switches / APs already in 01/02 | — | Do not double-ticket `up` from SE inventory |

NBI lives on **SE only**. Client: Administration → Client API Access; rights **Northbound Interface** + **Access Control NBI**. Queries only — never `enforceNacEnginesAll` or MAC add.

---

## Ops

- RADIUS Monitor Clients must exist on production engines **before** the High trigger is enabled. Until then RADIUS High stays **DISABLED**; log-forward Average is the stand-in.
- Engine SNMP uses the switch **MONITORING** SNMPv3 profile (authPriv MD5/DES). Canary 2026-08-28: all five ENACs answered `1.3.6.1.4.1.5624.1.2.73`.
- Purchased seat totals: see **Purchased seat totals** below. Do not put `{$XIQ.*.TOTAL}` as Zabbix host macros on `ch-sta-p-ensa01`.
- TLS: verify the SE cert. Do not copy vendor samples that set `verify=False`.
- Quiet engines: raise `{$XIQ.NAC.FRESH}` (elapsed seconds) or set `{$XIQ.NAC.FRESH:"<engine-ip>"}` on the SE host. There is **no** 07:00–19:00 clock — Site Engine `time()` is one TZ and the fleet is not.
- Extreme's `.xwf` license calculator stays a one-shot migration report. Do not schedule it from Zabbix. Do not point the template at `appdata/license`.
- Production canary 2026-08-29 (`ch-sta-p-ensa01`, 25.5.12.6): NBI up, 4055 end-systems / 2150 24h MACs / 320 Pilot / 0 Navigator. `connected` and RADIUS monitor fields absent. NBI `capacity` is 0. Details: [notes/xiq-se-nbi.md](notes/xiq-se-nbi.md).

---

## Purchased seat totals

`ch-sta-p-ensa01` is linked to **XIQ-SE Observability** with no host-level macro overrides. Template defaults are `{$XIQ.NAC.TOTAL}=0`, `{$XIQ.PILOT.TOTAL}=0`, `{$XIQ.NAV.TOTAL}=0`.

Remaining is computed **inside the census SCRIPT** (NAC from `{$XIQ.NAC.TOTAL}`, Pilot / Navigator from their macros) and stored as a DEPENDENT item. It is not a calculated item. Cloud 7.0 kept the unguarded live formula `{$XIQ.NAC.TOTAL}-last(//xiqse.nac.used24h)` — that produced **−2175** on 2026-08-29 (`TOTAL=0`, `used24h=2150`). SCRIPT-side remaining stays **0** while TOTAL is 0.

While a purchased total is 0, remaining is forced to **0**. That is “unknown entitlement”, not “out of seats” and not a negative. Cap tickets stay silent until the total is set.

After this template change: `--apply-xiqse` (re-import) then HostSync `ch-sta-p-ensa01`. If remaining stays negative, the leftover CALCULATED item was not replaced — delete that item or unlink/relink the template.

NBI has no entitlements field. Set the three counts on nbxSync CG **XIQ-SE licenses**, not as Zabbix host macros.

1. `configure_nbxsync_network.py --apply-xiqse` creates the CG (totals 0 if missing), assigns it to Site Engine platforms, and mirrors CG → platform. It never overwrites CG values. It does not HostSync.
2. NetBox → Plugins → nbxSync → Configuration Groups → **XIQ-SE licenses** → Zabbix Macros. Copy integers from Administration → Licenses on the SE:
   - `{$XIQ.NAC.TOTAL}` = Access Control quantity (the **first** number in `100/50` = NAC / GIM). GIM is not this graph.
   - `{$XIQ.PILOT.TOTAL}` = Pilot quantity
   - `{$XIQ.NAV.TOTAL}` = Navigator quantity
3. Re-run `--apply-xiqse` so the platform copies match the CG. HostSync inherits platform macros; it does not expand CG macros at resolve time.
4. HostSync `ch-sta-p-ensa01`.

If numbers were already typed as Zabbix host macros, copy them onto the CG **before** HostSync, or HostSync will replace them with the platform copy (0 until the CG is set).

---

## Dependencies

```
RADIUS High / NBI Average  →  engine or SE ICMP High  →  site
engine disconnected Average  →  SE NBI Average  →  SE ICMP
auth-log-forward Average  →  engine ICMP (and does not fire if RADIUS High already did)
```

---

## Watch the watcher

| Check | Why |
|---|---|
| GraphQL nodata | Token expired / SE upgrade / TLS / 8443. `xiqse.nbi.health` silent ≥15m unsports **every** health dependent — engine Connected / FreeRADIUS / capacity / Licensed / needsEnforce / Version go empty. That is the 42-unsupported ticket, not 42 schema bugs |
| Zero engines LLD | Access Control NBI right missing |
| 24h census truncated | `maxResults` too small — license graph under-counts |
| NAC census failed | NBI up but `endSystems` SCRIPT failed or timed out — Overview used tiles stay empty |
| Device license census failed | NBI up but `xiqLicenseState` query failed — Pilot/Navigator remaining unknown |
| Remaining negative | Leftover CALCULATED remaining item after import (2026-08-29 live: −2175). Re-import or unlink/relink |
| Engine last auth age empty while 24h MACs exist | Age **0** (SE clock ahead). Cloud 7.0 JS preprocessing treats numeric `0` as empty — stringify in extract JS |
| Unsupported items | First check NBI nodata. Then schema rename / SNMP view |
| Proxy last-seen | already in 01 |

---

## Templates

Do not clone stock Extreme switch/AP templates.

| Template | Where |
|---|---|
| **XIQ-SE Observability** | Platform / device Site Engine. SCRIPT GraphQL from the proxy → `https://{$XIQSE.API.FQDN}:8443`. Does not nest ICMP. |
| **ExtremeControl Observability** | Role **NAC**. Portal 8444 **DISABLED**. FreeRADIUS High is LLD on SE. Nested ICMP only if the host has no ping — this template does not nest it. |
| **ExtremeControl by SNMP** | Role **NAC**, SNMP interface. `ENTERASYS-NAC-APPLIANCE-MIB` (canary: five ENACs). Does not nest ICMP. OIDs: [templates/extremecontrol_snmp/OID_MAPPING.md](templates/extremecontrol_snmp/OID_MAPPING.md) |
| Linux by Zabbix agent | Keep if already linked. Do not add for this |

Macros on the **SE template** (secrets on a nbxSync CG, not in YAML):

```
{$XIQSE.API.FQDN}          = Site Engine mgmt FQDN / IP
{$XIQ.NAC.TOTAL}           = purchased Access Control (CG XIQ-SE licenses; 0 until set)
{$XIQ.NAC.USED.WARN}       = 90
{$XIQ.NAC.ES.MAXRESULTS}   = 20000
{$XIQ.NAC.FRESH}           = 86400 elapsed seconds (any TZ)
{$XIQ.NAC.FRESH.CONTROL}   = 1
{$XIQ.PILOT.TOTAL}         = purchased Pilot seats (same CG; 0 until set)
{$XIQ.PILOT.REMAIN.WARN}   = 2
{$XIQ.NAV.TOTAL}           = purchased Navigator seats (same CG; 0 until set)
{$XIQ.NAV.REMAIN.WARN}     = 2
```

`deleteMissing: false` on YAML. Cloud 7.0: no host-prototype `description`.

---

## Later

GIM remaining. Assessment licenses. Platform ONE tickets. Auto-fill CG totals from 08 after SKU canary. Campus-wide auth **Disaster** on a service host. SE Event Details if GraphQL never exposes E-to-Sav.

Analysis: [notes/xiq-se-nbi.md](notes/xiq-se-nbi.md). Cloud VIQ: [08-extremecloud-iq.md](08-extremecloud-iq.md). SNMP OIDs: [templates/extremecontrol_snmp/OID_MAPPING.md](templates/extremecontrol_snmp/OID_MAPPING.md).
