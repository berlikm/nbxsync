# ExtremeControl by SNMP — OID mapping

MIB: [`../../mibs/enterasys-nac-appliance-mib.txt`](../../mibs/enterasys-nac-appliance-mib.txt)
(`ENTERASYS-NAC-APPLIANCE-MIB`, `etsysModules 73`).

**Canary 2026-08-28** from NetBox Dev (`ch-sta-d-ssot01`), SNMPv3 authPriv user
`MONITORING` (MD5/DES), OID `1.3.6.1.4.1.5624.1.2.73`. All five production
ENACs returned 16 Counter64 scalars `.1.1.0` … `.1.16.0`.

This is **not** IA-V `sysObjectID` (`1.3.6.1.4.1.1916.2.252` in
`EXTREME-BASE-MIB`). That only classifies the box. Status is this Enterasys
tree.

Do **not** assign EXOS / VOSS / IQ switch templates on these OVAs.

## Scalars

Base `NAC = 1.3.6.1.4.1.5624.1.2.73.1`.

| Item key | Object | OID | Canary |
|---|---|---|---|
| `system.name` | `sysName` | `1.3.6.1.2.1.1.5.0` | MIB-II |
| `system.descr` | `sysDescr` | `1.3.6.1.2.1.1.1.0` | MIB-II |
| `system.objectid[sysObjectID.0]` | `sysObjectID` | `1.3.6.1.2.1.1.2.0` | IA-V = `1916.2.252` if Extreme set it; net-snmp Linux is OK |
| `system.net.uptime[sysUpTime.0]` | `sysUpTime` | `get[1.3.6.1.2.1.1.3.0]` | ×0.01 |
| `nac.appl.auth.requests` | `etsysNacApplAuthenticationRequests` | `NAC.1.0` | raw Counter64 |
| `nac.appl.auth.successes` | `etsysNacApplAuthenticationSuccesses` | `NAC.2.0` | |
| `nac.appl.auth.failures` | `etsysNacApplAuthenticationFailures` | `NAC.3.0` | |
| `nac.appl.auth.challenges` | `etsysNacApplRadiusChallenges` | `NAC.4.0` | EAP — not a failure |
| `nac.appl.auth.invalid` | `etsysNacApplAuthenticationInvalidRequests` | `NAC.5.0` | |
| `nac.appl.auth.duplicate` | `etsysNacApplAuthenticationDuplicateRequests` | `NAC.6.0` | |
| `nac.appl.auth.malformed` | `etsysNacApplAuthenticationMalformedRequests` | `NAC.7.0` | |
| `nac.appl.auth.bad` | `etsysNacApplAuthenticationBadRequests` | `NAC.8.0` | |
| `nac.appl.auth.dropped` | `etsysNacApplAuthenticationDroppedPackets` | `NAC.9.0` | |
| `nac.appl.auth.unknown` | `etsysNacApplAuthenticationUnknownTypes` | `NAC.10.0` | |
| `nac.appl.assessment` | `etsysNacApplAssessmentRequests` | `NAC.11.0` | 0 on all five ENACs |
| `nac.appl.captive.portal` | `etsysNacApplCaptivePortalRequests` | `NAC.12.0` | |
| `nac.appl.contact.lost` | `etsysNacApplContactLostSwitches` | `NAC.13.0` | **0** on all five; stored as last() |
| `nac.appl.ip.res.failures` | `etsysNacApplIPResolutionFailures` | `NAC.14.0` | lifetime counter — graph rate |
| `nac.appl.ip.res.timeouts` | `etsysNacApplIPResolutionTimeouts` | `NAC.15.0` | |
| `nac.appl.connected.agents` | `etsysNacApplConnectedAgents` | `NAC.16.0` | **0** on all five |

Rate items `nac.appl.*.rate` are dependents with `CHANGE_PER_SECOND`.
`nac.appl.auth.fail.pct` is failures / (successes + failures). Challenges are
excluded. Both rates 0 (quiet engine, live CH-STA-P-ENAC02) must be **0 %**,
not Not supported: Cloud 7.0 still evaluates `fail/sum` inside `(sum>0)*…`.
The denominator adds 1 when the sum is 0. STA decided-fail was ~30% on the
canary — threshold stays 101.

## What this MIB is not

| Need | Where |
|---|---|
| 24h unique MAC (`XIQ-NAC-S`) | XIQ-SE Observability GraphQL |
| Pilot seats | same |
| Engine `connected` / `needsEnforce` / `freeRadiusEnabled` | SE engine LLD |
| RADIUS 1812 dead | vendor RADIUS Monitor Clients — **not** `net.udp.service` |
| Switch 802.1X / MAC auth | 01 EXOS/VOSS — `enterasys-8021x-*` / `EXTREME-MAC-AUTH-MIB` |

Fixture: [`fixtures/canary_enac.json`](fixtures/canary_enac.json).
