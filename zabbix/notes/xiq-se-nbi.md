# XIQ-SE / ExtremeControl NBI — analysis

Operator page: [07-extreme-control.md](../07-extreme-control.md).  
This note is the research that page compresses. **Do not** treat it as a second policy. YAML: [`templates/xiqse_observability/`](../templates/xiqse_observability/), [`templates/extremecontrol_observability/`](../templates/extremecontrol_observability/), and [`templates/extremecontrol_snmp/`](../templates/extremecontrol_snmp/).

---

## Decision

Monitor **Site Engine** with companion **XIQ-SE Observability** (HTTPS GraphQL, OAuth). Monitor each **Control engine** as a NetBox role **NAC** host for ICMP + RADIUS + **ExtremeControl by SNMP** (`ENTERASYS-NAC-APPLIANCE-MIB`). License / connected / needsEnforce stay **on SE**, not a GraphQL scrape of each OVA.

Do **not**: install agent on vendor OVAs for this; GraphQL to NAC IPs; SNMP EXOS/VOSS/IQ templates on these appliances; Cloud XIQ tenant as a host; `system.run`; mutations; `net.udp.service` as a RADIUS check; second `icmpping`.

---

## Auth (query only)

Contract: ExtremeScripting `XMC_NBI.py` — use as the call pattern, do not import.

1. `POST https://<se>:8443/oauth/token/access-token?grant_type=client_credentials`
2. `POST https://<se>:8443/nbi/graphql` with `Authorization: Bearer`
3. Client: Administration → Client API Access
4. Rights: Northbound Interface + Access Control NBI
5. Verify TLS. Vendor samples use `verify=False` — do not copy.

Live schema for **their** version: Diagnostics → Server Utilities → **NBI Schema (JSON)** or `https://<se>:8443/nbi/graphql/schema.idl`. Published HTML Engine pages 404; dump Engine fields from that file.

---

## License counting (GTAC)

| Pool | SKU | Counted how | API today |
|---|---|---|---|
| Access Control (the RADIUS / NAC license) | `XIQ-NAC-S` | Unique **MACs** that **authenticated** in a **rolling 24h**, global across engines | **Not** a pool field. Count `EndSystemDTO` with `lastAuthEventTime` in window |
| Guest / IoT | second number in Licenses Quantity `100/50` | GIM end-systems | later |
| Pilot | `XIQ-PIL-S-C` | `network.devices` with `xiqLicenseState == XIQ_PILOT` (switches + Control engines in inventory) | Count + remaining vs `{$XIQ.PILOT.TOTAL}` |
| Navigator | Navigator SKU | `xiqLicenseState == XIQ_NAVIGATOR` | Count + remaining vs `{$XIQ.NAV.TOTAL}` |
| Platform ONE / Advanced / Standard | various | `XIQ_ADVANCED*` / `XIQ_STANDARD*` | graph `xiqse.lic.platformone`; tickets later |

The Extreme **XIQ-SE licensing calculation** OneView workflow ([ExtremeScripting `oneview_workflows`](https://github.com/extremenetworks/ExtremeScripting/tree/master/XMC_XIQ-SE/oneview_workflows), `XIQ-SE_Licensing_calculation-v116.xwf`, [KB 000098925](https://extreme-networks.my.site.com/ExtrArticleDetail?an=000098925)) is the official **one-shot** XMC → XIQ-SE buy-list. It reads `appdata/license` and JDBC to the SE database, and needs NMS-ADV / 27001 (or EVAL). Do **not** import or schedule that `.xwf` from Zabbix. Do **not** JDBC. Live monitoring is the same three pools from GraphQL.

Accounting packets do **not** consume NAC seats. Unique **usernames** are a useful graph and are **not** the license.

NAC Manager **Current Capacity** `1365/3000` is 24h unique **on that engine** vs **hardware** rating. Unrelated to `{$XIQ.NAC.TOTAL}`. `NacAppliance.capacity` is on the schema but **25.5.12.6 NBI returns 0** for every engine — the GUI column is a different number. The hardware-cap trigger requires `last(capacity)>0`. `licensed` is a boolean; each engine reports license class `XIQ-NAC-S`. `licenseData` is an undocumented blob — not used.

Published GraphQL through 26.08: `Administration` has `serverInfo` only (version, upTime, heap, RAM, threads). No `entitlements`. Old XMC community: “no way to query licenses via the API” still holds for the **purchased** pool.

Over-license: four stages, ≥120 days 1→4, 40 days per step. Stage 3: overflow MACs authenticate but **events are not populated**. Stage 4: catch-all profile (`tag.log`: `System is oversubscribed, using catch-all profile`).

---

## 24h unique MAC (how we will collect)

GraphQL does **not** filter `endSystems` by time (community + schema: `maxResults` / `firstResult` only). Wrapper:

```
accessControl {
  endSystems(maxResults: $n, firstResult: 0) {
    count
    currentBatchPosition
    success
    errorMessage
    endSystems { macAddress lastAuthEventTime username nacApplianceIP }
  }
}
```

`WsEndSystemListResult.count` is the **batch** size, not the 24h total.

Zabbix HTTP item + JS:

1. Request `macAddress`, `lastAuthEventTime`, `username`, `nacApplianceIP` only.
2. Count unique MAC where `lastAuthEventTime` is within 24h (epoch ms — confirm on canary).
3. Count unique `username` the same way (graph only).
4. Bucket by `nacApplianceIP` for per-engine LLD (hardware load).
5. If `count == maxResults`, fire truncated census — do not pretend remaining is correct.

Interval: 15m is enough for a license graph. Payload risk: `{$XIQ.NAC.ES.MAXRESULTS}` starts at 20000; raise only if truncated. Prefer `endSystemsForEngines` per LLD engine if a single global pull is too large — then unique-union MACs for the global license (same MAC on two engines = 1).

These are Zabbix **SCRIPT** items on the Swiss proxy (not `externalscripts`). They share **synchronous pollers** with legacy SNMP. If Latest data on `ch-sta-p-ensa01` is ~1h stale while NBI curl works, the proxy queue is the fault — [swiss-proxy-tuning.md](swiss-proxy-tuning.md).

Do **not** LLD each MAC as a host or item.

Prefer a native engine “24h unique” field if `schema.idl` has one (GUI already shows it). Then JS paging is a fallback.

Pilot used:

```
network { devices { deviceData { xiqLicenseState xiqLicenseCount } } }
```

`DeviceXIQLicenseState` includes `XIQ_PILOT`, `XIQ_NAVIGATOR`, `XIQ_UNMANAGED`, `NOT_LICENSED`, `XIQ_PENDING`, Platform ONE `XIQ_ADVANCED*` / `XIQ_STANDARD*`, … Purchased totals (`{$XIQ.PILOT.TOTAL}`, `{$XIQ.NAV.TOTAL}`, `{$XIQ.NAC.TOTAL}`) live on nbxSync CG **XIQ-SE licenses**, assigned to Site Engine platforms. Remaining is computed in the census SCRIPT (`if purchased <= 0: 0 else purchased − used`) and exported as a DEPENDENT item. Calculated remaining was rejected or left unguarded on Cloud 7.0 (live `−2175` on 2026-08-29). `0` remaining means the CG is still 0, not that the pool is empty. `--apply-xiqse` never overwrites the CG; it mirrors CG → platform (HostSync does not expand CG macros at resolve time). After editing the CG, re-apply then HostSync the SE. Do not set Zabbix host macros on `ch-sta-p-ensa01`.

---

## Engine / freshness

Published Engine type page is 404. Query `accessControl { engines }` and take whatever fields exist. Known on `NacAppliance` (25.5.12.6): `ipAddress`, `name`, `version`, `licensed`, `licenseData`, `capacity`, `freeRadiusEnabled`, `needsEnforce`, `applianceProperties`. **`connected` is not on the type.** The engine SCRIPT tries `connected`, then `isConnected`, then a query without either, and prefers a later clean response over a GraphQL error. The item stays `2` (unknown). The disconnected trigger is `last()=0`, so unknown does not page.

Event pipeline (user-reported: RADIUS green, SE has no logs). This **is** the NAC → SE log-forward check. It is **not** syslog to a SIEM.

- Per engine, max `lastAuthEventTime` (and/or `lastSeenTime`) of that engine’s end-systems.
- Average when older than `{$XIQ.NAC.FRESH}` elapsed seconds (`{$XIQ.NAC.FRESH.CONTROL}`). No `time()` / `dayofweek()` window — engines are in different time zones; Zabbix `time()` is the server clock.
- Per-engine override: host macro `{$XIQ.NAC.FRESH:"10.0.104.43"}`.
- Trigger name: **not forwarding auth logs**. Age `-1` (no events in the census) stays silent so a quiet engine is not a ticket.
- A Monitor Client that authenticates on a schedule is the cleanest heartbeat.

`EndSystemDTO.lastAuthEventTime` is the auth-event clock; `lastSeenTime` is presence. Prefer auth-event for “did the log ship?”

---

## RADIUS High

Zabbix cannot speak RADIUS. `net.udp.service[udp,,1812]` is a false green.

Prerequisite: ExtremeControl **RADIUS Monitor Clients** on each production engine. Then:

1. Canary: does NBI expose monitor last-success / fail?
2. If yes: High on fail, depends on ICMP.
3. If no: leave RADIUS High **DISABLED**; log-forward Average is the stand-in until we have a real monitor field.

TCP 8444 is admin, not 1812.

---

## SE health skeleton (enough for v1)

```
administration {
  serverInfo {
    version upTime startTime
    heapMemoryUsed heapMemoryMax
    freePhysicalMemory totalPhysicalMemory
    threadCount
  }
}
```

8443 is a SIMPLE TCP item. No `web.certificate.get` — YAML cannot carry it without an agent on the OVA. TLS verify stays on the GraphQL SCRIPT. Heap / RAM / threads are items only (collect first). 2026-08-29: heap 3.88 / 7.64 GB, free RAM 357 MB / 16.76 GB, 1040 threads — no trigger.

---

## Explicitly out of v1

| Item | Why |
|---|---|
| Mutations (`enforceNacEnginesAll`, add MAC) | Blast radius |
| `network { devices { up } }` | 01/02 already own switches |
| Host prototype per end-system | Scale |
| SNMP on SE/NAC OVAs | Wrong MIBs; BIN upgrades |
| Cloud XIQ license API | Separate host later |
| GIM / assessment | Same 24h idea, after NAC MAC graph is quiet |
| Campus auth Disaster | Service host, not device template |

---

## Canary (live SE)

### 2026-08-29 — production `ch-sta-p-ensa01` (query only)

NBI OAuth client-credentials succeeded with TLS verify on. Version **25.5.12.6**, started 2026-03-29 09:00:52 CEST, uptime ~153 days (`upTime` is **ms**: 13,221,883,291). Heap 3.88 / 7.64 GB. Free RAM 357 MB / 16.76 GB. Threads 1040.

Five engines, same version, licensed, `needsEnforce=no`, FreeRADIUS enabled, license class `XIQ-NAC-S`:

| Engine | IP |
|---|---|
| CH-STA-P-ENAC01 | 10.0.104.43 |
| CH-STA-P-ENAC02 | 10.0.105.36 |
| KR-SEL-P-ENAC01 | 10.30.100.15 |
| CN-SHA-P-ENAC01 | 10.31.100.15 |
| HU-DEB-P-ENAC01 | 10.40.100.15 |

`connected` is **not** on `NacAppliance`. `capacity` is **0** for all five through NBI (GUI Current Capacity is a different number). `administration.eventStats` does not exist. `NacAppliance.radiusMonitorClients` does not exist.

`accessControl.endSystems`: count **4055**, success=true, not truncated. Sample auth: EAP-PEAP / EAP-TLS, states ACCEPT / REJECT. Zabbix `xiqse.nac.used24h` = **2150** (rolling 24h unique MACs — not the 4055 inventory).

Devices: **563** total — **320** `XIQ_PILOT`, **243** `XIQ_PENDING`, **0** Navigator.

Purchased Access Control / Pilot / Navigator quantities are **not** on the OAuth NBI client. Do not invent them.

Zabbix on `ch-sta-p-ensa01` (all queried items supported, inherited totals still 0):

| Item | Value |
|---|---|
| `xiqse.nbi.available` | 1 |
| `xiqse.nac.fetched` | 4055 |
| `xiqse.nac.ok` | 1 |
| `xiqse.nac.truncated` | 0 |
| `xiqse.nac.used24h` | 2150 |
| `xiqse.pilot.used` | 320 |
| `xiqse.pilot.ok` | 1 |
| `xiqse.nav.used` | 0 |
| `xiqse.nac.remaining` | **−2175** |

That remaining value is the live **unguarded calculated** formula `{$XIQ.NAC.TOTAL}-last(//xiqse.nac.used24h)` with TOTAL=0. Repo later used a multiply-guard; Cloud 7.0 did not apply it to calculated `params`. Remaining is now computed in the SCRIPT and must stay **0** until the CG totals are set.

### 2026-08-29 — Latest data after SCRIPT remaining import

Template re-import is live on `ch-sta-p-ensa01`. Snapshot JSON includes `nacRemaining` / `nacUsedPct` / `pilotRemaining` / `navRemaining`. Remaining items are **0**, used % is **0 %**, unsupported items **0**. Not −2175.

| Item | Value |
|---|---|
| `xiqse.nac.used24h` | **1815** (Saturday; was 2150 earlier) |
| `xiqse.nac.users24h` | 992 |
| `xiqse.nac.fetched` | 4055, not truncated |
| `xiqse.pilot.used` | 320 |
| `xiqse.lic.pending` | 243 |
| `xiqse.nav.used` | 0 |
| remaining / used % | **0** / **0 %** (totals still unset) |

Per-engine 24h unique MACs sum to the global seat count (no cross-engine overlap this window):

| Engine | 24h MACs | last auth age |
|---|---|---|
| CH-STA-P-ENAC01 | 1460 | was **−33s** (SE clock ahead of proxy; clamp to 0) |
| HU-DEB-P-ENAC01 | 227 | 11m |
| CN-SHA-P-ENAC01 | 105 | 20m |
| KR-SEL-P-ENAC01 | 21 | 41m |
| CH-STA-P-ENAC02 | 2 | 6h 27m (quiet pair; under 24h FRESH) |

`connected=2` and `capacity=0` on all five. FreeRADIUS yes, licensed yes, `needsEnforce=no`. Heap ~60 %, free RAM ~372 MB (collect-first). Age `-1` still means “no event in census”; a slightly-future `lastAuthEventTime` is now age **0**, not a negative.

### Still open on canary

1. Native 24h-unique / entitlement field in `schema.idl` or `licenseData` — not present; keep paging MACs.
2. RADIUS Monitor Clients field on `NacAppliance` — still absent; RADIUS High stays DISABLED.
3. Purchased seat integers from Administration → Licenses — fill CG **XIQ-SE licenses** by hand.

---

## Engine SNMP (live)

IA-V `sysObjectID` (`1.3.6.1.4.1.1916.2.252` in `EXTREME-BASE-MIB`) is identity only.

Status is `ENTERASYS-NAC-APPLIANCE-MIB` (`1.3.6.1.4.1.5624.1.2.73`). Canary
2026-08-28 from NetBox Dev with the switch **MONITORING** SNMPv3 profile: all
five ENACs returned 16 Counter64 scalars `.1.1.0` … `.1.16.0`.
`contact.lost` and `connected.agents` were 0 everywhere. Assessment requests
were 0. Challenges dominate successes (EAP).

That MIB does **not** expose `XIQ-NAC-S`, Pilot, `connected`, `needsEnforce`,
or FreeRADIUS. Those stay GraphQL.

OIDs: [`templates/extremecontrol_snmp/OID_MAPPING.md`](../templates/extremecontrol_snmp/OID_MAPPING.md).
Fixture: [`templates/extremecontrol_snmp/fixtures/canary_enac.json`](../templates/extremecontrol_snmp/fixtures/canary_enac.json).

