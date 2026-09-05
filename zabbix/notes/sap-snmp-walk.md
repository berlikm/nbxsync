# SAP SNMPv3 probe — CH-STA-P-SH01

Date: 2026-09-05
Target: `CH-STA-P-SH01` / `10.0.105.112:161/udp`
Execution point: production NetBox environment.
Profile: SNMPv3 `authPriv`, security name `SAPUSER`, MD5 authentication, DES privacy. Passphrases are intentionally not recorded here.

## Result

Authenticated walks completed without SNMP errors.

| Area | OID | Result |
|---|---|---|
| System | `1.3.6.1.2.1.1` | Available; Linux Net-SNMP agent. `sysObjectID.0` is `1.3.6.1.4.1.8072.3.2.10`; `sysName.0` is `ch-sta-p-sh01`. |
| Interfaces | `1.3.6.1.2.1.2` | Available; two interfaces: `lo` and `eth0`; both administratively and operationally up. Standard byte, packet, error and discard counters are present. |
| Load | `1.3.6.1.4.1.2021.10.1.3` | Available; 1/5/15-minute load values. |
| Memory and swap | `1.3.6.1.4.1.2021.4` | Available; UCD-SNMP memory and swap counters. |
| CPU | `1.3.6.1.4.1.2021.11` | Available; UCD-SNMP CPU counters. |
| Processes | `1.3.6.1.2.1.25.4.2.1.2` | Available; standard HOST-RESOURCES process table. |

## SAP-specific discovery

| Probe | Result | Meaning |
|---|---|---|
| SAP enterprise subtree `1.3.6.1.4.1.2312` | No rows | The standard SAP enterprise subtree is not exposed. |
| Net-SNMP extend configuration `1.3.6.1.4.1.8072.1.3.2` | No rows | SNMPD has no configured `extend` scripts through which DNUS/SAP metrics could be exposed. |
| Enterprise root `1.3.6.1.4.1` | First 300 rows were only UCD-SNMP enterprise `2021`; result capped | This does not rule out every enterprise number greater than `2021`, but it found no SAP data before that branch. Do not perform an unbounded walk. |

## Monitoring decision

SNMP can supply host/infrastructure monitoring only:

- availability, uptime, interface traffic and interface errors;
- load, CPU, memory and swap;
- standard host-resource process and storage inventory.

It does not currently expose SAP operational signals: ABAP runtime/errors, HANA health, IDoc, qRFC, job alerts or SAP syslog. Those require the DNUS/SAP integration, SAP API, or explicit agent UserParameters.

## nbxsync status

The live probe proves the SAP profile is **MD5/DES**, not SHA1/AES128. The repository profile was corrected to MD5/DES and the production `SAP Agent+SNMP` SNMP interface was manually updated after the probe:

- SNMPv3 `authPriv`, `SAPUSER`, MD5/DES;
- `snmp_pushcommunity = true`;
- both passphrase fields populated; values are not recorded here.

No fleet zerotouch was run. `CH-STA-P-SH01` is still not a Zabbix Production host.

The LM-parity template **SAP template from Sensirion** is in
[`../templates/sap_sensirion/`](../templates/sap_sensirion/). Host SNMP items
match this probe (64-bit ifXTable for LM Interfaces 64 bit). Application
items are trappers for the full Promonitor list (ABAP, instance, IDoc, jobs,
locks, qRFC in/out, RFC, spool, syslog, tRFC, updates). SSL Certificate
Expiration is the Zabbix agent `web.certificate.get` (SAP hosts already have
Agent :10050). `{$SAP.APP.CONTROL}=0` and `{$SAP.CERT.CONTROL}=0` until DNUS
and the ICM name are set. Do not invent a Promonitor API.

Ungrouped LM rows `DataSource_ping` / `DataSource_snmp.v3` /
`DataSource_script.groovy` / `DataSource_batchscript.*` / `DataSource_webpage`
/ `DataSource_dns` are collector **methods** (the collector could ping, SNMP,
run Groovy, hit HTTP). They are not more SAP counters. Groovy/batch is the
DNUS vehicle for the trappers above. Do not add `system.run`.

Next:

1. `configure_nbxsync_network.py --apply-sap` — import the template, assign it
   on SAP HANA / SAP ME, and HostSync only `CH-STA-P-SH01` if that device
   exists and is not onboarding. Do not run zerotouch.
2. Verify SNMP availability from the assigned Zabbix proxy, not only from the
   NetBox execution point.
3. Leave application triggers off until the DNUS/`zabbix_sender` contract
   exists. Then set `{$SAP.APP.CONTROL}=1`.
4. Set `{$SAP.CERT.HOST}` to the ICM/HTTPS name on the canary, confirm
   Latest data, then `{$SAP.CERT.CONTROL}=1`. Port stays collect-first
   (`{$SAP.PORT.CONTROL}=0`) unless LM “Port” was actually in use.

## Handoff questions

1. Obtain the DNUS script/API contract and determine its least-privilege SAP account requirements.
2. Decide whether DNUS runs as `zabbix_sender` into the trapper keys, or as
   agent UserParameters later. Do not add UserParameters until that contract exists.
3. Do not treat the generic Linux SNMP data as HANA or ABAP health.
4. Do not walk `1.3.6.1.4.1` unbounded or poll the empty SAP enterprise tree.
