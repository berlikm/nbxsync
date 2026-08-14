# Extreme switching

EXOS and VOSS share alerts and the port-label grammar; they do not share MIBs. SNMP is the data path (these platforms do not stream gNMI). World-class here means: **page what users feel, never fail silent, one incident per root cause** — not a second poller.

Labels: [port-identity.md](port-identity.md). APs: [02-extreme-access-points.md](02-extreme-access-points.md). Scale: [_template.md](_template.md).

---

## Observability

| Rule | Here |
|---|---|
| Page **symptoms** | ICMP down, SNMP dead, in-scope link down, flaps, errors, optic DOM **alarm**, PSU/fan, temp **critical** |
| **Graph** causes | CPU, memory, traffic, util, inventory, ICMP loss/RTT |
| One incident | host triggers depend on SNMP → ICMP; ICMP depends on **site**. AP cable/PoE pages on Access `UP-` **High**. AP ICMP High is a duplicate until that dependency exists — do not drop it (hides a hung AP) |
| Never silent | unsupported-item count, **zero** discovered interfaces, proxy last-seen |
| Control plane | on-box `ifAlias` + role macros. Access collects **only** `USW`+`UP`; a mistyped uplink → no items |
| Collect first | Speed Expect / Routing **imported, not linked**. USW util off (`{$IF.UTIL.MAX}=101`). YAML triggers on those templates are **on** — linking them pages |
| Severity | **Disaster** = site only. Do not dump everything on Warning |

Do **not** stack Network Generic (`icmpping` collision). Mute a port with **`X`**, not `{$IFCONTROL:"{#IFNAME}"}`.

Scale: Info → Warning → Average → High → Disaster. Disaster+High page 24/7; Average = ticket; Warning = next day; Info = log.

---

## What we alert

Intended contract. Where the live YAML differs, **Templates** says so.

| Device | Alert | Sev |
|---|---|---|
| ICMP down | yes | **High** |
| SNMP dead (ICMP still up) | yes | **Average** — mgmt blind, forwarding may still work |
| Unplanned reboot | yes | Warning |
| Temperature **critical** (100 °C) / vendor alarm | yes | **High** |
| Temperature warning (95 °C) | yes | Warning — next day; not stock 55 |
| Temperature too low | **no** | `{$TEMP_CRIT_LOW}=-273` silences stack/VM 0 °C |
| PSU / fan failed | yes | Average |
| CPU high | yes | Warning — baseline first |
| Memory high | yes | Average — baseline first |
| Optic DOM **status** alarm (VOSS) | yes | Average — prefer status, not raw dBm |
| Firmware / OS / serial change | yes | Info |
| System name changed | stock **Info** | disable in Zabbix if it chatters |
| ICMP loss / RTT | stock Warning | WAN-poller noise; disable per host if CN/US false |
| **Site** unreachable | yes | **Disaster** — site-level, **not** on EXOS/VOSS |

| Ports in scope | Alert | Intended | Live YAML |
|---|---|---|---|
| `USW` / `US` / `UP` link down | yes | **High** | **Average** (one stock trigger for every discovered port) |
| `MON` link down | yes | Warning | Average — Core/Dist/Mgmt only (not collected on Access) |
| `UW` link down | yes | **High** | Average — Core/Dist/Mgmt. All circuits at a site → **Disaster** (site-level) |
| Link flapping | yes | Warning | Warning — VOSS has a counter; EXOS stock does not |
| Wrong speed vs label | later | Warning | Speed Expect YAML triggers are **on**; do **not** link until labels are clean |
| Half duplex | yes | Warning | Warning |
| Interface errors | yes | Warning | Warning |
| Outbound discards (`USW`) | later | Average | Speed Expect, not linked |
| Sustained util | **no** | dashboard | stock 15m util off (`{$IF.UTIL.MAX}=101`) |
| `X…` ports | **no** | — | not discovered |

Do **not** alert on: a laptop unplugging (Access **does not collect** desk ports), fifty **High**s for one site down, “bandwidth high” on a backup window.

Class-scoped High for `USW`/`UP` is **later** (context macros or a thin trigger). Until then, in-scope link-down is an Average ticket. Access still cannot page a desk port — those items do not exist.

---

## Scope

| Role | Collect (admin-up physical/LAG) | Do not collect |
|---|---|---|
| Switch Core / Dist / Mgmt | **Every** admin-up port except `X…` | `X…`; **admin-down** is not discovered |
| Switch Access | **Only** `USW` (to Dist) and `UP` (to AP) | Desk / laptop / `US` / `MON` / `UW` / `TMON` / unlabelled / `N…` / `X…` |

Access is two labels, full stop. Unlabelled Access ports produce **no items**. Dist / Core / Mgmt alert if an admin-up port goes down, labelled or not (except `X`). Do not leave a desk port admin-up on Dist.

**`X` excludes. `N` does not** (Core/Dist/Mgmt). Stack / ISC / MLAG peer / SPAN need **`X`**. Unused: **admin-down**.

| Role | `{$NET.IF.IFALIAS.MATCHES}` | `{$NET.IF.IFALIAS.NOT_MATCHES}` | `{$NET.IF.IFTYPE.MATCHES}` |
|---|---|---|---|
| Core / Dist / Mgmt | `.*` | `^X(-\|$)` | `^(6\|161)$` |
| Access | `^(USW\|UP)(-\|$)` | `CHANGE_IF_NEEDED` | `^(6\|161)$` |

Access must also override Speed Expect or `US`/`MON` leak in: `{$PORTID.LLD.IFALIAS.MATCHES}` = `^(USW|UP)(-|$)`.

There is no Switch Hybrid role. `^(6|161)$` drops EXOS VLAN ifaces.

NetBox: those Access macros on role Switch Access. Locked checklist §11.1 still has the wider `USW|US|UP|MON|UW|TMON` pattern — **the live role value is the tighter regex.**

---

## Ops

Production poller for NL/US/CH is the **Swiss proxy group**, SNMPv3 `MONITORING` **MD5/DES**, GETBULK. A laptop `snmpget` does not prove that path. ICMP Up only proves ping.

After a **reboot**, if CLI SNMPv3 from the proxy works but Zabbix stays SNMP=0: RFC 3414 engine boots. Reload `zabbix_proxy -R snmp_cache_reload` or re-sync the host. If CLI from the proxy times out: UDP 161 / allow-list, not the template.

Platform names must match Template Rules: **EXOS**, **VOSS** (case-insensitive substring).

Grammar: EXOS `display-string` (max 20), leave `description-string` empty. VOSS interface `name` → `ifAlias`. Do not use `rcPortName`.

---

## Dependencies

```
util / speed-expect  →  link down  →  no SNMP  →  ICMP down  →  site unreachable
CPU / mem / temp     →  ICMP down
AP ICMP              →  Access UP-   (later — see 02)
```

A site WAN blip must not be one High per switch. Those Highs **depend on** a site **Disaster** (proxy / core / synthetic).

---

## Watch the watcher

| Check | Why |
|---|---|
| Unsupported item count | SNMP walk died; looks like health |
| Switch with **zero** discovered interfaces | IFALIAS regex or LLD broken |
| SNMP = 0, ICMP = 1 | credentials / proxy cache / UDP 161 — not a forwarding outage |
| Proxy last-seen | hosts go *unknown*, not *down* |

---

## EXOS

| Template | Where |
|---|---|
| Extreme EXOS by SNMP (stock) | Platform EXOS |

We do **not** fork the stock template. Apply: `{$TEMP_WARN}=95`, `{$TEMP_CRIT}=100`, `{$TEMP_CRIT_LOW}=-273` on **this template** (not globals). Patch EtherLike duplex LLD to the same IFALIAS filters as `net.if.discovery`. Interface LLD: **15m**, keep-lost **0**.

Stock EXOS trigger severities stay upstream except those patches. SNMP-dead on stock is typically Warning until we match VOSS (Average).

---

## VOSS

| Template | Where |
|---|---|
| Extreme VOSS by SNMP | Platform VOSS |

Same `{$TEMP_*}` on **this template**. Re-import after this revision (SNMP-dead is **Average**). Fleet macros (template / globals, not Switch* role):

```
{$OPTIC.TEMP.CRIT}     = 70
{$OPTIC.TEMP.MAX}      = 150
{$OPTIC.RX.DBM.MIN}    = -100
{$OPTIC.DOM.ALARM_HIGH}= 3
{$OPTIC.DOM.ALARM_LOW} = 5
{$MLT.CONTROL}         = 1
{$VIST.CONTROL}        = 0
{$IST.CONTROL}         = 0
{$SNMP.TIMEOUT}        = 5m
{$IF.UTIL.MAX}         = 101
```

V-IST: host `{$VIST.CONTROL}=1` only on fabric pairs. Classic IST stays 0. Traps are in the template — collect; do not page duplicates of polled items until seen on hardware.

Poll weight (same idea as APs, more SNMP budget on a chassis): inventory **1h**; IF counters **3m**; oper-status default **1m**; chassis temp **1m**; optic DOM **5m** (Average tickets, not 03:00). Duplex LLD **15m** / keep-lost **0**, same as `net.if.discovery`. Uptime **1m** (reboot Warning still sees `< 10m`). Do not 1-minute every optic on a Core.

Fabric (ISIS / V-IST / card down) YAML includes **High** triggers. VIST/IST are gated by the macros above. ISIS/card High is live — retune **later** (more important than OSPF for this estate).

---

## Both platforms

| Template | Where | Triggers |
|---|---|---|
| Extreme Port Speed Expect by SNMP | Switch Core / Dist / Access / Mgmt | YAML **on**. **Do not assign** on Switch roles until labels are clean |
| Extreme Routing by SNMP (OSPF) | Switch Core / Dist | YAML **on** (OSPF High). **Not linked** |

Speed Expect uses its **own** LLD macros (not `{$NET.IF.*}`). Default (Core/Dist/Mgmt):

```
{$PORTID.LLD.IFALIAS.MATCHES} = ^(USW|US|UP|MON)(-|$)
{$PORTID.LLD.IFTYPE.MATCHES}  = ^6$
```

On **Access**, override MATCHES to `^(USW|UP)(-|$)`.

`{$IF.UTIL.MAX:"USW"}=80` is **not** current. Keep global 101 until there is history.

---

## Later

Class-scoped link-down High (`USW`/`UP`); OSPF count; USW util + discards; VOSS fabric adjacency retune; sFlow on a few Core `USW`; one synthetic ping per site as the **Disaster** SLI; NetBox vs live `ifAlias`; AP ICMP → `UP-`; syslog on the proxy; `walk[]` when we retune poll load.

FortiGate (API) and network VMs reuse this bar ([03](03-fortinet.md), [06](06-network-vms.md)). Do not merge with Cato ([04](04-cato.md)).
