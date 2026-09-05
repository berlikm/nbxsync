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
| Host dashboard | One **Health** board. **Licenses** is the only seat worksheet (used + remaining for NAC / Pilot / Navigator). Overview **NAC used** is the same global unique-MAC item — not a second count. Engine 24h unique stays Latest data (hardware load; do not add it up). |

Disaster is campus-wide auth later, on a **service / site** host — not on this template.

---

## Health dashboard (host, from the template)

After the platform template is linked, **Monitoring → Hosts → Site Engine → Dashboards → Health**. Same chrome as ExtremeControl SNMP and the switch Health boards: four headline tiles, a problems strip, then the one graph or map that answers the page.

| Page | What you see in 5 seconds |
|---|---|
| **Overview** | NBI, engine count, **NAC used** (global unique MACs — same item as Licenses), uptime. Problems. Last-auth-age honeycomb (red at 24h). No remaining tiles and no NAC graph here. |
| **Engines** | FreeRADIUS and `needsEnforce` only. No 24h unique map: per-engine MACs are hardware load (`1365/3000`) and **do not add up** to the NAC seat. No **Connected** map (unknown on 25.5.12.6). |
| **Licenses** | One worksheet. Row 1 = used (NAC / Pilot / Navigator / NAC %). Row 2 = remaining. Remaining is **0 until** CG `{$XIQ.*.TOTAL}` is set — that is not “out of seats”. 7d graphs of used only. |

There is no second **Engines** dashboard. `--apply-xiqse` drops the leftover host board (`deleteMissing: false` would otherwise keep it). Heap / RAM / threads stay items (collect first). Do not put Pilot / Navigator used on Overview. Do not put remaining on Overview.

---

## How Extreme counts licenses

Three subscription pools. Same three the Extreme **XIQ-SE licensing calculation** workflow reports for an XMC → XIQ-SE move ([KB 000098925](https://extreme-networks.my.site.com/ExtrArticleDetail?an=000098925), `.xwf` v116). That workflow is a **one-shot** report: it reads `appdata/license` and the SE database, and needs NMS-ADV / 27001. We do **not** run it from Zabbix. We graph the same pools continuously from NBI.

| Pool | SKU | Counted how | Live item |
|---|---|---|---|
| Access Control | `XIQ-NAC-S` | Deduplicated union of end-system MACs authenticated in a rolling 24h and `XIQ_PENDING` network-device base MACs. Same identity in both sets = one seat. Usernames and accounting do not count. | `xiqse.nac.used` |
| Pilot | `XIQ-PIL-S-C` | Authoritative purchased / activated / available / expiry values from the already-linked stock **ExtremeCloud IQ by HTTP** template; NBI device-class count is informational | `xiqse.pilot.cloud.*`, `xiqse.pilot.devices` |
| Navigator | Navigator SKU | NBI `xiqLicenseState == XIQ_NAVIGATOR`; informational because no purchased-total API field exists | `xiqse.nav.devices` |

Per-engine **Current Capacity** `1365/3000` is **hardware load** (24h unique on that engine vs engine rating). Changing it does not change the global NAC license.

Exceeding NAC seats is a four-stage violation (GUI pop-up → events stop for overflow MACs → catch-all profile). Stage 3 is the “RADIUS green, SE has no events” failure mode.

At 0 Pilot you cannot onboard a switch or another engine. At 0 Navigator you cannot onboard another Navigator-tier device. Existing RADIUS still works.

NBI has **no** entitlements field. NAC used seats are counted; `{$XIQ.NAC.TOTAL}` remains at the template default `0` because the purchased total is unavailable. `0` means remaining shows 0 (not “out of seats”) and NAC cap tickets stay silent. Pilot purchased values come from the linked stock Cloud template. Do not scrape the GUI, add a separate Cloud tenant host, or query the SE database.

Platform ONE / Advanced / Standard is not purchased and is not collected. Pending onboarding remains `xiqse.lic.pending` (graph).

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
| NAC not forwarding auth logs to SE | yes | Average | Per engine: newest `lastAuthEventTime` older than `{$XIQ.NAC.FRESH}` (default 24h elapsed). Naive NBI stamps are `{$XIQSE.TZ}` (Europe/Zurich), not UTC. Override a quiet engine with `{$XIQ.NAC.FRESH:"<engine-ip>"}`. `{$XIQ.NAC.FRESH.CONTROL}` still gates the ticket. Age `-1` = no event in the census (silent). Age `0` = just now, or SE clock slightly ahead of the proxy. Not syslog to a SIEM |
| SE ingest jam (E-to-Sav / drops) | **no** until the field exists | Average | One SE ticket if GraphQL exposes it on canary |
| Engine `needsEnforce` stuck | yes | Average | Config never pushed |
| NAC license identities ≥ `{$XIQ.NAC.TOTAL}` | yes | Average | Authenticated end systems plus pending-device identities reach entitlement |
| NAC license identities ≥ `{$XIQ.NAC.USED.WARN}`% of total | yes | Warning | Default 90%. Dayside buy more |
| 24h census truncated | yes | Average | `count == {$XIQ.NAC.ES.MAXRESULTS}` — number is a lie |
| Pilot used ≥ `{$XIQ.PILOT.TOTAL}` | yes | Warning | Cannot onboard a switch / engine. `TOTAL=0` silences |
| Pilot remaining ≤ `{$XIQ.PILOT.REMAIN.WARN}` | yes | Warning | Default 2 |
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

Do **not** alert on: Cloud XIQ tenant, every end-system MAC as a host, GraphQL mutations, accounting-only storms, Guest/IoT (GIM) until the same 24h pattern is proven.

---

## What we graph (no ticket unless the table says so)

On **Site Engine → Health**:

| Graph | Unit | Why |
|---|---|---|
| **NAC license identities** | count | The deduplicated authenticated-MAC plus pending-device-MAC count Extreme bills / enforces |
| NAC license remaining | SCRIPT: 0 while `{$XIQ.NAC.TOTAL}` is 0, else purchased − used | **Item only** (Health tiles show used). The template default is **0**, so remaining is 0 rather than “out of seats” or −2175. NBI has no entitlement field |
| NAC used % of entitlement | % | Warning at 90% |
| Authenticated MACs / unique usernames 24h | count | Authentication capacity story; not the complete license count |
| Pilot used / remaining | count | Device + engine seats (`XIQ_PILOT`) |
| Navigator used / remaining | count | `XIQ_NAVIGATOR` |
| Pending / Platform ONE | count | Graph; no ticket yet |
| Engine count | count | Census |
| Heap used / max, physical RAM, threads | bytes / count | Collect first |
| `upTime` | s | Reboot |

On **Site Engine → Health → Engines** (LLD honeycomb, one hex per engine):

| Map | Why |
|---|---|
| FreeRADIUS / `needsEnforce` | Colour. Connected is omitted (unknown on 25.5.12.6) |
| Age of newest `lastAuthEventTime` | On **Overview** — NAC → SE log-forward gap |

Per-engine 24h unique MACs stay Latest data / graph prototypes. That number is hardware load. Summing the hexes double-counts a MAC that authenticated on two engines and will **not** match **NAC used**.

Do **not** LLD every laptop. Sample and count on SE.

On each **Control engine → Health** (SNMP):

| Graph | Why |
|---|---|
| Auth requests / successes / failures per second | Engine is doing RADIUS. Failures going up is **not** RADIUS-dead |
| Decided-auth failure % | Failures / (success + fail). Idle pair (ENAC02) is **0 %**, not unsupported |
| RADIUS challenges per second | EAP; large vs successes on the 2026-08-28 canary |
| Dropped / invalid / duplicate | Error rates |
| Contact-lost switches | Engine → switch SNMP (the other direction). 0 on all five ENACs |
| Captive portal / assessment / connected agents | Assessment was 0 fleet-wide |

---

## Scope

| Role / class | In | Out |
|---|---|---|
| Site Engine | GraphQL NBI + 8443 + licenses + engine LLD | SNMP walk of the OVA, Cloud XIQ |
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
- Production canary 2026-08-29 (`ch-sta-p-ensa01`, 25.5.12.6): NBI up, 4055 end-systems / 2150 authenticated 24h MACs / 243 pending-device MACs / 320 Pilot / 0 Navigator. `connected` and RADIUS monitor fields absent. NBI `capacity` is 0. Details: [notes/xiq-se-nbi.md](notes/xiq-se-nbi.md).

---

## Purchased seat totals

`ch-sta-p-ensa01` is linked to **XIQ-SE Observability** with no host-level macro overrides. Template defaults are `{$XIQ.NAC.TOTAL}=0`, `{$XIQ.PILOT.TOTAL}=0`, `{$XIQ.NAV.TOTAL}=0`.

Remaining is computed **inside the census SCRIPT** (NAC from `{$XIQ.NAC.TOTAL}`, Pilot / Navigator from their macros) and stored as a DEPENDENT item. It is not a calculated item. Cloud 7.0 kept the unguarded live formula `TOTAL-used` — that produced **−2175** on 2026-08-29 (`TOTAL=0`, auth-only count=2150). SCRIPT-side remaining stays **0** while TOTAL is 0.

While a purchased total is 0, remaining is forced to **0**. That is “unknown entitlement”, not “out of seats” and not a negative. Cap tickets stay silent until the total is set.

After this template change: `--apply-xiqse` (re-import) then HostSync `ch-sta-p-ensa01`. If remaining stays negative, the leftover CALCULATED item was not replaced — delete that item or unlink/relink the template.

NBI has no entitlements field. The three purchased-total macros remain at their template defaults of `0`; they are not configured through an nbxSync configuration group or Zabbix host macros. Remaining therefore stays 0 and capacity tickets remain silent.

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
| GraphQL nodata | Token expired / SE upgrade / TLS. **Exception:** zabp02 `lastclock` ~1h behind on SCRIPT **and** ICMP/SNMP/SIMPLE — not NBI ([notes/proxy-history-clock.md](notes/proxy-history-clock.md)) |
| Zero engines LLD | Access Control NBI right missing |
| 24h unique MACs ≪ GUI entitlement used | Timezone-less `lastAuthEventTime` parsed as UTC (fixed: `{$XIQSE.TZ}`). 2026-09-04: ~2052 stored vs ~2841 CEST vs GUI 2915 |
| NAC census failed | NBI up but `endSystems` SCRIPT failed or timed out — Overview used tiles stay empty |
| Device license census failed | NBI up but `xiqLicenseState` query failed — Pilot/Navigator remaining unknown |
| Remaining negative | Leftover CALCULATED remaining item after import (2026-08-29 live: −2175). Re-import or unlink/relink |
| Unsupported items | Schema field renamed on their SE version; or ENTERASYS-NAC-APPLIANCE-MIB view dropped on an engine |
| `nac.appl.auth.fail.pct` division by zero | Quiet engine, both rates 0. Cloud 7.0 does not short-circuit `(sum>0)*(fail/sum)` — re-import ExtremeControl by SNMP after the denom `+(sum=0)` guard |
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
{$XIQ.NAC.TOTAL}           = template default 0; no entitlement source is configured
{$XIQ.NAC.USED.WARN}       = 90
{$XIQ.NAC.ES.MAXRESULTS}   = 20000
{$XIQ.NAC.FRESH}           = 86400 elapsed seconds (any TZ)
{$XIQ.NAC.FRESH.CONTROL}   = 1
{$XIQ.PILOT.TOTAL}         = template default 0; no entitlement source is configured
{$XIQ.PILOT.REMAIN.WARN}   = 2
{$XIQ.NAV.TOTAL}           = template default 0; no entitlement source is configured
{$XIQ.NAV.REMAIN.WARN}     = 2
```

`deleteMissing: false` on YAML. Cloud 7.0: no host-prototype `description`.

---

## Later

GIM remaining. Assessment licenses. Platform ONE tickets. Cloud XIQ entitlement API (Connected mode) so macros are not manual. Campus-wide auth **Disaster** on a service host. SE Event Details if GraphQL never exposes E-to-Sav.

Analysis: [notes/xiq-se-nbi.md](notes/xiq-se-nbi.md). History `lastclock` −1h while payloads refresh: [notes/proxy-history-clock.md](notes/proxy-history-clock.md). SNMP OIDs: [templates/extremecontrol_snmp/OID_MAPPING.md](templates/extremecontrol_snmp/OID_MAPPING.md).
