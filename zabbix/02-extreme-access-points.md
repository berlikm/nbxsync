# Extreme access points

HiveOS / IQ Engine APs. One Zabbix host per AP, not per XIQ tenant. Same bar as [01-extreme-switching.md](01-extreme-switching.md): **page what users feel, never fail silent, one incident per cable cut**.

The switch port toward the AP is `UP-…` (Access collects **only** `USW`+`UP` — [01](01-extreme-switching.md)). OID map: `templates/extreme_iq_engine_snmp/`. Analysis: [notes/alerting-and-health.md](notes/alerting-and-health.md).

---

## Observability

| Rule | Here |
|---|---|
| Page **symptoms** | ICMP down (**High**). Hung AP with eth still up (**High** on ICMP). |
| **Ticket** (Average) | SNMP dead while ping works. Memory. Temp canary. Unsupported-item count. |
| **Graph** causes | CPU, clients, radio noise/Tx, retries/drops, eth traffic, ICMP loss/RTT (triggers **off**) |
| One incident | Cable/PoE → switch `UP-` **Average** live (class High later). AP ICMP **should** depend on that port. Until NetBox/LLDP mapping exists, a PoE cut is two events — accept it; do not drop AP ICMP to Average (that hides a hung AP). |
| Never silent | Unsupported items (Average trigger); SNMP=0 while `UP-` is up; SNMP=1 and **zero** radios = Health census |
| Collect first | Radio retry alerts, client-count, ICMP loss/RTT, CPU-critical — **triggers off** in the YAML |
| Host dashboard | Template dashboard **Health** (host-level). RF is page 2 |
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
| AP eth / mgt oper down | yes | Warning — plant page is switch `UP-` (Average live; High later) |
| Unsupported item count | yes | Average — `{$UNSUPPORTED.MAX}` (default 5), 30m |
| CPU critical | **no** | trigger **DISABLED** until a quiet pilot |
| ICMP loss / RTT | **no** | items on; triggers **DISABLED** (CH proxy RTT is a WAN signal) |
| Client count | **no** | graph; trigger **DISABLED** |
| Radio channel / Tx / noise | **no** | RF graphs on **Health** page 2 |
| Radio retries / drops | **no** | graphs until baselined |
| Zero radios (SNMP=1) | **no** | Health census until a pilot |
| Per-client association | **no** | later |
| Firmware / serial | **no** | inventory |
| Fan | **no** | wall APs are fanless (item stays 0, not unsupported) |

Do **not** alert on: XIQ tenant as a host, VAP/SSID ifaces, a laptop on a switch (Access does not collect desk ports).

---

## Health dashboard (host, from the template)

**Monitoring → Hosts → AP → Dashboards → Health.** Linked automatically with `Extreme IQ Engine by SNMP`.

| Page | 5-second read |
|---|---|
| **Overview** | ICMP / SNMP / CPU / clients. Problems. CPU+mem and client history. Same 4-tile + strip + two panes as switches. |
| **RF** | Radio noise honeycomb. Noise/Tx and retries/drops as a 2-column grid (wifi0 \| wifi1). Empty radios = census. |

**Network interfaces → Overview** is the same map + 3×2 grid as switches (same IFNAME labels and oper-status colours), scoped to AP eth (`ifType=6`). The map is **12×3**, not 72×6: Zabbix honeycomb has no max cell size, and an AP has ~2 eth, so a switch-sized widget paints two giant hexes. Traffic stays full width underneath. RF does not live there. There is no Health Diagnostics page and no Port page — AP eth has only status + RX/TX.

---

## Scope

| Object | In | Out |
|---|---|---|
| AP chassis | Every Access Point device | XIQ tenant as a host |
| Radios | Physical wifi (`ahIfType=0`; AP305C `wifi0` / `wifi1`) | VAP / SSID virtual ifaces |
| Ethernet | Physical `eth` / `mgt` (`ifType=6`, admin-up) | wifi IF-MIB rows |
| Clients | Scalar count only | Association table |

---

## Zero-touch (nbxSync)

New AP: NetBox **platform name contains `IQ ENGINE`** (case-insensitive), role **Access Point**, SNMP Monitoring CG on that role.

First HostSync links this template + `OS/Network`. **`HiveOS` alone does not match** — the IQ template never links.

Re-run zerotouch + `configure_nbxsync_network.py --apply` on APs **already in Zabbix**: same contract as [01](01-extreme-switching.md) — no host delete, no mass sync, YAML `deleteMissing: false`, Health dashboard updates in place on the template.

---

## Ops

XIQ must **manage SNMP** on eth0 (and eth1 if used), then Delta update. Without that, the switch `UP-` is green and Zabbix SNMP is red.

Production poller for NL/US/CH is the **Swiss proxy group**, SNMPv3 `MONITORING` **MD5/DES**, GETBULK. A laptop `snmpget` that works does **not** prove the proxy path. ICMP Up only proves ping.

After an AP **reboot**, if CLI SNMPv3 from the CH proxy works but Zabbix stays `not available (0)`: RFC 3414 time window / engine boots. Reload the proxy SNMP cache (`zabbix_proxy -R snmp_cache_reload`) or re-sync the host. Official Zabbix note: devices that do not persist `snmpEngineBoots` need that reload. If CLI from the **proxy** times out: XIQ allow-list / UDP 161, not the IQ YAML.

Wrong OIDs look like SNMP availability **1** and items **unsupported**. Empty SNMP items + availability **0** is transport.

AP `{$TEMP_*}` is **this** template (70 / 85 / −273), not EXOS/VOSS 95/100. Many APs stub `ahEnvirmentTemp` at 0 — Health Overview does **not** show a temp gauge (green 0 °C would lie). Temperature still tickets Average and appears on the problems strip.

---

## Dependencies

```
CPU / mem / temp / AP eth  →  no SNMP  →  ICMP down  →  site unreachable
AP ICMP                    →  switch UP-  (later, via NetBox/LLDP)
```

A closet PoE failure must not stay two uncorrelated Highs once mapping exists. Site WAN blip → site **Disaster**, not one High per AP (later).

---

## Watch the watcher

| Check | Why | Live |
|---|---|---|
| Unsupported items | OID missing on this AP class; looks like health | Average `{$UNSUPPORTED.MAX}` |
| SNMP = 0, ICMP = 1, `UP-` up | XIQ manage-SNMP, credential, or CH-proxy SNMPv3 cache — not a cable | SNMP Average |
| SNMP = 1 and **zero** radios | LLD filter or empty walk — RF is blind | Health / RF page census |
| Proxy last-seen | unknown ≠ down | later |

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
{$UNSUPPORTED.MAX}   = 5
{$AP.RADIO.IFNAME.MATCHES} = ^(wifi|Wifi|WIFI|radio|Radio)[0-9]+$
{$NET.IF.IFNAME.MATCHES}   = ^(eth|Eth|ETH|mgt|MGT)
{$NET.IF.IFTYPE.MATCHES}   = ^6$
{$IFCONTROL}         = 1
```

Radio + eth LLD: **1h**, keep-lost **0**. Inventory (name/serial/fw/hw) **1h**. Health (CPU/mem/temp/clients) **1m**. Radio items **5m**. Re-import the YAML after this revision (poll delays, DISABLED flags, and **Health** live in the template).

---

## Later

AP ICMP → switch `UP-` dependency via NetBox/LLDP; trigger on SNMP=1 and zero radios; per-client LLD; traps; XIQ REST; mesh; split GETBULK off APs only if HiveOS cannot take combined requests. FortiGate (API) / VMs: same bar, different doc ([03](03-fortinet.md)). Do not merge with Cato.
