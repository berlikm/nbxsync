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

OS collection is stock **Linux by SNMP** on role SAP HANA (not custom
UCD/IF/FS items in the SAP YAML). The SAP pack is ST22 / sapcontrol
only. Ping stays on CG SAP Agent+SNMP (`icmpping` on Linux by SNMP is
disabled). IP / TCP-UDP stay omitted until an agent exists.

SNMP can supply host/infrastructure monitoring only:

- availability, uptime, interface traffic and interface errors;
- load, CPU, memory and swap;
- standard host-resource process and storage inventory.

It does not currently expose SAP operational signals: ABAP runtime/errors, HANA health, IDoc, qRFC, job alerts or SAP syslog. Those come from local sapcontrol (SAP Host Agent / sapstartsrv) via the Zabbix agent UserParameter — not from this SNMP tree.

## nbxsync status

The live probe proves the SAP profile is **MD5/DES**, not SHA1/AES128. The repository profile was corrected to MD5/DES and the production `SAP Agent+SNMP` SNMP interface was manually updated after the probe:

- SNMPv3 `authPriv`, `SAPUSER`, MD5/DES;
- `snmp_pushcommunity = true`;
- both passphrase fields populated; values are not recorded here.

No fleet zerotouch was run. `CH-STA-P-SH01` is still not a Zabbix Production host.

The HANA (openSUSE) template **SAP template from Sensirion** is in
[`../templates/sap_sensirion/`](../templates/sap_sensirion/). Host SNMP is
stock **Linux by SNMP** (this probe). The SAP YAML is ST22 only. SAP ME is
Windows — **SAP ME from Sensirion** has no UCD items. Application items keep
the Promonitor names and collect via local sapcontrol — see
[`../templates/sap_sensirion/SAPCONTROL.md`](../templates/sap_sensirion/SAPCONTROL.md).
SSL Certificate Expiration is the Zabbix agent `web.certificate.get` (SAP
hosts already have Agent :10050). `{$SAP.APP.CONTROL}=0` and
`{$SAP.CERT.CONTROL}=0` until the UserParameter is installed and the ICM
name is set. Do not invent a Promonitor API.

Ungrouped LM rows `DataSource_ping` / `DataSource_snmp.v3` /
`DataSource_script.groovy` / `DataSource_batchscript.*` / `DataSource_webpage`
/ `DataSource_dns` are collector **methods** (the collector could ping, SNMP,
run Groovy, hit HTTP). They are not more SAP counters. Groovy/batch is
retired; sapcontrol replaces it. Do not add agent remote commands.

Next:

1. Install the Host Agent UserParameter on the canary (script +
   `zabbix/userparameters/sap_sensirion.conf`). `--apply-sap` cannot push it.
2. `configure_nbxsync_network.py --apply-sap` — import the template, assign it
   on SAP HANA / SAP ME, and HostSync only `CH-STA-P-SH01` if that device
   exists and is not onboarding. Do not run zerotouch.
3. Verify SNMP availability from the assigned Zabbix proxy, not only from the
   NetBox execution point.
4. Confirm Latest data `sap.app.promonitor`=1, then set `{$SAP.APP.CONTROL}=1`.
5. Set `{$SAP.CERT.HOST}` to the ICM/HTTPS name on the canary, confirm
   Latest data, then `{$SAP.CERT.CONTROL}=1`. Port stays collect-first
   (`{$SAP.PORT.CONTROL}=0`) unless LM “Port” was actually in use.

## Handoff questions

1. Instance number / SID on SH01 if `saphostctrl ListInstances` is ambiguous.
2. Whether any non-HANA SAP ME host needs `{$SAP.SID}` so ListInstances does
   not mix stacks.
3. Do not treat the generic Linux SNMP data as HANA or ABAP health.
4. Do not walk `1.3.6.1.4.1` unbounded or poll the empty SAP enterprise tree.
   ST22/IDoc/qRFC as RFC tables still need a real SAP account — out of scope.
