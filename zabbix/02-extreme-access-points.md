# Extreme access points

HiveOS / IQ Engine APs. One Zabbix host per AP, not per XIQ tenant. Same bar as [01-extreme-switching.md](01-extreme-switching.md): **page what users feel, never fail silent, one incident per cable cut**.

The switch port toward the AP is `UP-…`. OID map: `templates/extreme_iq_engine_snmp/`.

---

## Observability

| Rule | Here |
|---|---|
| Page **symptoms** | ICMP down (**High**). SNMP dead while ping works (**Average**). Hung AP with eth still up (**High** on ICMP). |
| **Graph** causes | CPU, clients, radio noise/Tx, retries/drops, eth traffic, ICMP loss/RTT |
| One incident | Cable/PoE → switch `UP-` **High**. AP ICMP **should** depend on that port. Until NetBox/LLDP mapping exists, a PoE cut is two Highs — accept it; do not drop AP ICMP to Average (that hides a hung AP). |
| Never silent | Unsupported items; SNMP=0 while `UP-` is up; SNMP=1 and **zero** radios |
| Collect first | Radio retry alerts, client-count, ICMP loss/RTT, CPU-critical — **triggers off** in the YAML |
| Severity | Same scale as [_template.md](_template.md). **No Disaster** on this template |

Do **not** stack Network Generic (`icmpping` collision).

Scale: Info → Warning → Average → High → Disaster. Disaster+High page 24/7; Average = ticket; Warning = next day; Info = log.

---

## What we alert

| Thing | Alert | Sev |
|---|---|---|
| ICMP down | yes | **High** — device unreachable. Depends on switch `UP-` when mapping exists |
| SNMP dead (ICMP still up) | yes | **Average** — mgmt blind; Wi-Fi may still work |
| Memory high | yes | Average |
| Temperature (canary) | yes | Average — many APs stub `ahEnvirmentTemp`; **not** switch 95/100 |
| CPU high (`{$CPU.UTIL.WARN}=90`) | yes | Warning — GTAC: high CPU alone is not a fault |
| AP eth / mgt oper down | yes | Warning — plant page is switch `UP-` **High** |
| CPU critical | **no** | trigger **DISABLED** until a quiet pilot |
| ICMP loss / RTT | **no** | items on; triggers **DISABLED** (CH proxy RTT is a WAN signal) |
| Client count | **no** | graph; trigger **DISABLED** |
| Radio channel / Tx / noise | **no** | RF graphs |
| Radio retries / drops | **no** | graphs until baselined |
| Per-client association | **no** | later |
| Firmware / serial | **no** | inventory |
| Fan | **no** | wall APs are fanless (item stays 0, not unsupported) |

Do **not** alert on: XIQ tenant as a host, VAP/SSID ifaces, a laptop on a switch (Access does not collect desk ports).

---

## Scope

| Object | In | Out |
|---|---|---|
| AP chassis | Every Access Point device | XIQ tenant as a host |
| Radios | Physical wifi (`ahIfType=0`; AP305C `wifi0` / `wifi1`) | VAP / SSID virtual ifaces |
| Ethernet | Physical `eth` / `mgt` (`ifType=6`, admin-up) | wifi IF-MIB rows |
| Clients | Scalar count only | Association table |

---

## Ops

XIQ must **manage SNMP** on eth0 (and eth1 if used), then Delta update. Without that, the switch `UP-` is green and Zabbix SNMP is red.

Production poller for NL/US/CH is the **Swiss proxy group**, SNMPv3 `MONITORING` **MD5/DES**, GETBULK. A laptop `snmpget` that works does **not** prove the proxy path. ICMP Up only proves ping.

After an AP **reboot**, if CLI SNMPv3 from the CH proxy works but Zabbix stays `not available (0)`: RFC 3414 time window / engine boots. Reload the proxy SNMP cache (`zabbix_proxy -R snmp_cache_reload`) or re-sync the host. Official Zabbix note: devices that do not persist `snmpEngineBoots` need that reload. If CLI from the **proxy** times out: XIQ allow-list / UDP 161, not the IQ YAML.

Wrong OIDs look like SNMP availability **1** and items **unsupported**. Empty SNMP items + availability **0** is transport.

NetBox platform name must **contain** `IQ ENGINE` (case-insensitive). `HiveOS` alone does not match the Template Rule — the IQ template never links.

AP `{$TEMP_*}` is **this** template (70 / 85 / −273), not EXOS/VOSS 95/100.

---

## Dependencies

```
CPU / mem / temp / AP eth  →  no SNMP  →  ICMP down  →  site unreachable
AP ICMP                    →  switch UP-  (later, via NetBox/LLDP)
```

A closet PoE failure must not stay two uncorrelated Highs once mapping exists. Site WAN blip → site **Disaster**, not one High per AP.

---

## Watch the watcher

| Check | Why |
|---|---|
| Unsupported item count | OID missing on this AP class; looks like health |
| SNMP = 0, ICMP = 1, `UP-` up | XIQ manage-SNMP, credential, or CH-proxy SNMPv3 cache — not a cable |
| SNMP = 1 and **zero** radios | LLD filter or empty walk — RF is blind |
| Proxy last-seen | unknown ≠ down |

There is **no** trigger yet for “zero radios”. Treat it as a dashboard/census check until a pilot.

---

## Templates

| Template | Where | Triggers |
|---|---|---|
| Extreme IQ Engine by SNMP | Platform matching `IQ ENGINE` | as table above |

CG **SNMP Monitoring** on role Access Point. No role-level template floor.

```
{$CPU.UTIL.WARN}     = 90
{$CPU.UTIL.CRIT}     = 95          # trigger off
{$MEMORY.UTIL.MAX}   = 90
{$TEMP_WARN}         = 70          # canary, Average
{$TEMP_CRIT}         = 85          # canary, Average — not switch 100
{$TEMP_CRIT_LOW}     = -273
{$SNMP.TIMEOUT}      = 5m
{$ICMP_LOSS_WARN}    = 10          # trigger off
{$AP.CLIENT.WARN}    = 10000       # trigger off
{$AP.RADIO.IFNAME.MATCHES} = ^(wifi|Wifi|WIFI|radio|Radio)[0-9]+$
{$NET.IF.IFNAME.MATCHES}   = ^(eth|Eth|ETH|mgt|MGT)
{$NET.IF.IFTYPE.MATCHES}   = ^6$
{$IFCONTROL}         = 1
```

Radio + eth LLD: **1h**, keep-lost **0**. Re-import the YAML after this revision (severities and DISABLED flags live in the template, not in NetBox macros).

---

## Later

AP ICMP → switch `UP-` dependency via NetBox/LLDP; trigger on SNMP=1 and zero radios; per-client LLD; traps; XIQ REST; mesh; split GETBULK off APs only if HiveOS cannot take combined requests. FortiGate / VMs: same bar, different doc. Do not merge with Cato.
