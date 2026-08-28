# ExtremeControl / XIQ-SE

Site Engine is the NBI and log brain. ExtremeControl engines are the RADIUS boxes users hit. Same bar as [01](01-extreme-switching.md): **page what users feel, never fail silent, one incident per root cause**. OS + ICMP stay on [06](06-network-vms.md) / nbxSync. This page is **application** only.

Official Zabbix Extreme pack has **no** SE / NAC template. Collection is **HTTPS GraphQL on Site Engine** (OAuth client credentials). Do **not** put GraphQL on each engine. Do **not** install a Zabbix agent on vendor OVAs for this (BIN upgrades). Keep Linux agent if it is already there (CPU / disk).

This page is the **target contract**. YAML lives in `templates/xiqse_observability/`, `templates/extremecontrol_observability/`, and `templates/extremecontrol_snmp/`. Refresh with `configure_nbxsync_network.py --apply-xiqse`.

---

## Observability

| Rule | Here |
|---|---|
| Page **symptoms** | Engine ICMP down. RADIUS 1812 dead while the box is up (users cannot 802.1X) |
| **Ticket** (Average) | SE NBI/GUI dead while ICMP up (ops blind; RADIUS often still works). Engine disconnected from SE. **Auth events stale while RADIUS is up** (NAC worked, logs never reached SE). SE ingest jam. Engine `needsEnforce` stuck |
| **Graph** / next day | Unique MACs that authenticated in **24h** (how Extreme counts the NAC license). Pilot seats used / remaining. Heap, uptime, version, engine load vs hardware capacity. Per-engine RADIUS request/success/fail rates (SNMP) |
| One incident | RADIUS / GraphQL → ICMP → **site**. Engine tickets do not also fire SE. SE ingest jam is **one** SE ticket, not N engines |
| Never silent | GraphQL nodata; zero engines discovered; 24h census truncated (`count == maxResults`). SNMP-dead Warning on the engine if the MONITORING profile stops answering |
| Collect first | Heap / CPU thresholds off until a quiet baseline. Event-freshness gated so a quiet night is not a ticket. SNMP fail-ratio and contact-lost gated (`101` / CONTROL=0) |
| One `icmpping` | Nested only if the host does not already ping. Do not also assign Network Generic |
| Host dashboard | **Health** (SE: NBI / licenses; engine: SNMP auth rates) + **Engines** (SE LLD map) |

Disaster is campus-wide auth later, on a **service / site** host — not on this template.

---

## How Extreme counts the “RADIUS license”

This is **XIQ-NAC-S** (Access Control end-systems), not Pilot.

GTAC: unique **end-systems that authenticated in a rolling 24 hours**, global across all engines. Same MAC on two engines counts **once**. RADIUS **accounting** packets do **not** count. Unique **usernames** are not the license (laptop + phone + printer = three seats).

Per-engine **Current Capacity** `1365/3000` is **hardware load** (24h unique on that engine vs engine rating). Changing it does not change the global license.

Exceeding NAC seats is a four-stage violation (GUI pop-up → events stop for overflow MACs → catch-all profile). Stage 3 is the “RADIUS green, SE has no events” failure mode.

**Pilot** (`XIQ-PIL-S-C`) is a different pool: natively managed switches **and each Control engine** (1 Pilot each). At 0 you cannot onboard a switch or another engine. Existing RADIUS still works.

NBI has **no** entitlements field. Used seats we **count**. Purchased totals are macros from Administration → Licenses (`{$XIQ.NAC.TOTAL}`, `{$XIQ.PILOT.TOTAL}`). Refresh the macro when you buy more. Do not scrape the GUI. Do not add a Cloud XIQ tenant host.

---

## What we alert

### Site Engine (one NetBox host)

| Thing | Alert | Sev | Notes |
|---|---|---|---|
| ICMP down | yes | **High** | From 06 / nested ICMP — not a second ping |
| HTTPS 8443 / NBI unexpected | yes | Average | Ops blind; RADIUS may still work (SE upgrade) |
| GraphQL nodata | yes | Average | Token, TLS, or SE down |
| Zero Control engines discovered | yes | Average | Filter / rights / template wrong |
| Engine disconnected from SE | yes | Average | LLD on SE. Auth may still work locally |
| Auth-event pipeline stale | yes | Average | Per engine: no `lastAuthEventTime` in `{$XIQ.NAC.FRESH}` **and** RADIUS still OK. Quiet-hours gate |
| SE ingest jam (E-to-Sav / drops) | yes | Average | One SE ticket if the field exists on canary |
| Engine `needsEnforce` stuck | yes | Average | Config never pushed |
| 24h unique MACs ≥ `{$XIQ.NAC.TOTAL}` | yes | Average | License violation in progress |
| 24h unique MACs ≥ `{$XIQ.NAC.USED.WARN}`% of total | yes | Warning | Default 90%. Dayside buy more |
| 24h census truncated | yes | Average | `count == {$XIQ.NAC.ES.MAXRESULTS}` — number is a lie |
| Pilot used ≥ `{$XIQ.PILOT.TOTAL}` | yes | Warning | Cannot onboard a switch / engine |
| Pilot remaining ≤ `{$XIQ.PILOT.REMAIN.WARN}` | yes | Warning | Default 2 |
| Unplanned SE reboot (`upTime`) | yes | Warning | |
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
| Engine hardware 24h unique ≥ rating | yes | Warning | Per-engine load, not the global license |
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
| **NAC license used (24h unique MACs)** | count | The number Extreme bills / enforces |
| NAC license remaining | `{$XIQ.NAC.TOTAL}` − used | Same series, easier to read |
| NAC used % of entitlement | % | Warning at 90% |
| Unique **usernames** 24h | count | Capacity story; **not** the license |
| Pilot used / remaining | count | Device + engine seats |
| Engine count | count | Census |
| Heap used / max, physical RAM, threads | bytes / count | Collect first |
| `upTime` | s | Reboot |

On **Site Engine → Engines** (LLD, one row per engine):

| Graph | Why |
|---|---|
| 24h unique MACs on **this** engine | Hardware load (`1365/3000`) |
| Age of newest `lastAuthEventTime` | Log-forwarding gap |
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
| Site Engine | GraphQL NBI + 8443 + licenses + engine LLD | SNMP walk of the OVA, Cloud XIQ |
| Role **NAC** (Control engine) | ICMP + RADIUS monitor + optional existing Linux agent + **ExtremeControl by SNMP** (`ENTERASYS-NAC-APPLIANCE-MIB`) | GraphQL to the engine, second ping, EXOS/VOSS/IQ templates |
| Switches / APs already in 01/02 | — | Do not double-ticket `up` from SE inventory |

NBI lives on **SE only**. Client: Administration → Client API Access; rights **Northbound Interface** + **Access Control NBI**. Queries only — never `enforceNacEnginesAll` or MAC add.

---

## Ops

- RADIUS Monitor Clients must exist on production engines **before** the High trigger is enabled. Until then RADIUS High stays **DISABLED**; event-freshness Average is the stand-in.
- Engine SNMP uses the switch **MONITORING** SNMPv3 profile (authPriv MD5/DES). Canary 2026-08-28: all five ENACs answered `1.3.6.1.4.1.5624.1.2.73`.
- `{$XIQ.NAC.TOTAL}` / `{$XIQ.PILOT.TOTAL}` from Administration → Licenses (Access Control quantity is the first number in `100/50`; that is NAC / GIM).
- TLS: GraphQL SCRIPT validates the SE certificate. Certificate-expiry telemetry requires a managed Agent 2 and is deliberately out of this agentless pack.
- Quiet nights: event-freshness needs a floor (for example last auth older than N hours **and** wall-clock in production hours), or a known always-on Monitor Client.

---

## Dependencies

```
RADIUS High / NBI Average  →  engine or SE ICMP High  →  site
engine disconnected Average  →  SE NBI Average  →  SE ICMP
auth-event stale Average  →  engine ICMP (and does not fire if RADIUS High already did)
```

---

## Watch the watcher

| Check | Why |
|---|---|
| GraphQL nodata | Token expired / SE upgrade / TLS |
| Zero engines LLD | Access Control NBI right missing |
| 24h census truncated | `maxResults` too small — license graph under-counts |
| Unsupported items | Schema field renamed on their SE version; or ENTERASYS-NAC-APPLIANCE-MIB view dropped on an engine |
| Proxy last-seen | already in 01 |

---

## Templates

Do not clone stock Extreme switch/AP templates.

| Template | Where |
|---|---|
| **XIQ-SE Observability** | Platform / device Site Engine. SCRIPT GraphQL from the proxy → `https://{$XIQSE.API.FQDN}:8443`. Does not nest ICMP. |
| **ExtremeControl Observability** | Role **NAC**. Portal 8444 / cert **DISABLED**. FreeRADIUS High is LLD on SE. Nested ICMP only if the host has no ping — this template does not nest it. |
| **ExtremeControl by SNMP** | Role **NAC**, SNMP interface. `ENTERASYS-NAC-APPLIANCE-MIB` (canary: five ENACs). Does not nest ICMP. OIDs: [templates/extremecontrol_snmp/OID_MAPPING.md](templates/extremecontrol_snmp/OID_MAPPING.md) |
| Linux by Zabbix agent | Keep if already linked. Do not add for this |

Macros on the **SE template** (secrets on a nbxSync CG, not in YAML):

```
{$XIQSE.API.FQDN}          = Site Engine mgmt FQDN / IP
{$XIQ.NAC.TOTAL}           = purchased Access Control end-systems
{$XIQ.NAC.USED.WARN}       = 90
{$XIQ.NAC.ES.MAXRESULTS}   = 20000
{$XIQ.NAC.FRESH}           = quiet-hours-gated max age
{$XIQ.PILOT.TOTAL}         = purchased Pilot seats
{$XIQ.PILOT.REMAIN.WARN}   = 2
```

`deleteMissing: false` on YAML. Cloud 7.0: no host-prototype `description`.

---

## Later

GIM remaining. Assessment licenses. Cloud XIQ entitlement API (Connected mode) so macros are not manual. Campus-wide auth **Disaster** on a service host. SE Event Details if GraphQL never exposes E-to-Sav.

Analysis: [notes/xiq-se-nbi.md](notes/xiq-se-nbi.md). SNMP OIDs: [templates/extremecontrol_snmp/OID_MAPPING.md](templates/extremecontrol_snmp/OID_MAPPING.md).
