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

NAC Manager **Current Capacity** `1365/3000` is 24h unique **on that engine** vs **hardware** rating. Unrelated to `{$XIQ.NAC.TOTAL}`. `NacAppliance.capacity` is that rating; `licensed` is a boolean; `licenseData` is an undocumented blob — dump on canary.

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

Do **not** LLD each MAC as a host or item.

Prefer a native engine “24h unique” field if `schema.idl` has one (GUI already shows it). Then JS paging is a fallback.

Pilot used:

```
network { devices { deviceData { xiqLicenseState xiqLicenseCount } } }
```

`DeviceXIQLicenseState` includes `XIQ_PILOT`, `XIQ_NAVIGATOR`, `XIQ_UNMANAGED`, `NOT_LICENSED`, `XIQ_PENDING`, Platform ONE `XIQ_ADVANCED*` / `XIQ_STANDARD*`, … Remaining = purchased macro − used. Connected-mode cloud pool is shared; do not add an XIQ tenant host on this template.

---

## Engine / freshness

Published Engine type page is 404. Query `accessControl { engines }` and take whatever fields exist. Known on `NacAppliance`: `ipAddress`, `name`, `version`, `licensed`, `licenseData`, `capacity`, `freeRadiusEnabled`, `needsEnforce`, `applianceProperties`.

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

8443 + certificate item on the same host. Heap triggers **DISABLED** until baseline.

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

On one SE, query-only, after `--apply-xiqse` + HostSync of that host:

1. Token + `serverInfo` + 8443 + cert.
2. `engines` / `NacAppliance` field dump (`licenseData`, connected/last-contact names).
3. One page of `endSystems`: time units, typical `count`, whether 24h filter can be approximated.
4. `xiqLicenseState` histogram (Pilot / Navigator / Platform ONE / pending).
5. Confirm RADIUS Monitor Clients exist before enabling High.

If `licenseData` already contains 24h used / entitlement, prefer that over paging MACs.

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

