# Extreme switching

EXOS and VOSS share alerts and the port-label grammar; they do not share MIBs. SNMP is the data path (these platforms do not stream gNMI). World-class here means: **page what users feel, never fail silent, one incident per root cause** — not a second poller.

Labels: [port-identity.md](port-identity.md). Same page shape: [_template.md](_template.md).

---

## Observability

| Rule | Here |
|---|---|
| Page **symptoms** | ICMP down, SNMP dead, link down, flaps, errors, discards, optic DOM **alarm**, PSU/fan, temp **critical** |
| **Graph** causes | CPU, memory, traffic, util, inventory change |
| One incident | host triggers depend on SNMP → ICMP; ICMP depends on **site** (proxy / core). AP cable/PoE pages on Access `UP-` **High**. AP ICMP High is a duplicate until that dependency exists — do not drop it (hides a hung AP) |
| Never silent | unsupported-item count, **zero** discovered interfaces, proxy last-seen |
| Control plane | on-box `ifAlias` + role macros. Access collects **only** `USW`+`UP`; a mistyped uplink → no items |
| Collect first | Speed Expect / Routing / USW util **linked or imported, triggers off** until labels and history exist |
| Severity | **Disaster** = site only. Device templates use High / Average / Warning / Info — do not dump everything on Warning |

Do **not** stack Network Generic (`icmpping` collision). Mute a port with **`X`**, not `{$IFCONTROL:"{#IFNAME}"}`.

Scale (Zabbix): Info → Warning → Average → High → Disaster. Disaster+High page 24/7; Average = ticket; Warning = next day; Info = log. Full table: [_template.md](_template.md).

---

## What we alert

| Device | Alert | Sev |
|---|---|---|
| ICMP down | yes | **High** |
| SNMP dead (ICMP still up) | yes | **Average** — mgmt blind, forwarding may still work |
| Unplanned reboot | yes | Warning |
| Temperature **critical** / vendor alarm | yes | **High** |
| PSU / fan failed | yes | Average |
| CPU high | yes | Warning — baseline first |
| Memory high | yes | Average — baseline first |
| Optic DOM **status** alarm (VOSS) | yes | Average — prefer status, not raw dBm |
| Firmware / OS / serial change | yes | Info |
| System name changed | **no** | disabled |
| Temperature warning / too low | **no** | closets + stack 0 °C |
| **Site** unreachable (all switches / last path) | yes | **Disaster** — site-level trigger, **not** on EXOS/VOSS templates |

| Ports in scope | Alert | Sev |
|---|---|---|
| `USW` / `US` / `UP` link down | yes | **High** — on **Access**, only `USW` and `UP` exist as items |
| `MON` link down | yes | Warning — iDRAC / OOB. **Core/Dist/Mgmt only** (not collected on Access) |
| `UW` link down | yes | **High** — Core/Dist/Mgmt (or 05). All circuits at a site → **Disaster** |
| Link flapping | yes | Warning — VOSS has a counter; EXOS stock does not |
| Wrong speed vs label | later | Warning — Speed Expect triggers off until labels are clean |
| Half duplex | yes | Warning |
| Interface errors | yes | Warning |
| Outbound discards (`USW`) | later | Average — after history (user impact) |
| Sustained util | **no** | dashboard. Stock 15m util off (`{$IF.UTIL.MAX}=101`) |
| Traffic graphs | **no** | dashboards |
| `X…` ports | **no** | not discovered |

Do **not** alert on: a laptop unplugging (Access **does not collect** desk ports at all), fifty **High**s for one site down (they depend on the site **Disaster**), “bandwidth high” on a backup window.

---

## Scope

| Role | Collect (admin-up physical/LAG) | Do not collect |
|---|---|---|
| Switch Core / Dist / Mgmt | **Every** admin-up port except `X…` | `X…`; **admin-down** is not discovered |
| Switch Access | **Only** `USW` (to Dist) and `UP` (to AP) | Desk / laptop / `US` / `MON` / `UW` / `TMON` / unlabelled / `N…` / `X…` |

Access is not “opt-in a long class list”. It is **two labels**, full stop. Unlabelled Access ports produce **no items** — a laptop unplug cannot alert because there is nothing to alert on.

Dist / Core / Mgmt will alert if an admin-up port goes down, labelled or not (except `X`). Do not leave a desk port admin-up on Dist.

**`X` excludes. `N` does not** (Core/Dist/Mgmt). Stack / ISC / MLAG peer / SPAN need **`X`**. Unused: **admin-down**.

| Role | `{$NET.IF.IFALIAS.MATCHES}` | `{$NET.IF.IFALIAS.NOT_MATCHES}` | `{$NET.IF.IFTYPE.MATCHES}` |
|---|---|---|---|
| Core / Dist / Mgmt | `.*` | `^X(-\|$)` | `^(6\|161)$` |
| Access | `^(USW\|UP)(-\|$)` | `CHANGE_IF_NEEDED` | `^(6\|161)$` |

Access must also override Speed Expect’s filter or `US`/`MON` on an Access box would still be discovered:

`{$PORTID.LLD.IFALIAS.MATCHES}` on Access = `^(USW|UP)(-|$)`

There is no Switch Hybrid role. `^(6|161)$` drops EXOS VLAN ifaces.

NetBox: put those Access macros on role Switch Access. The locked checklist §11.1 still has the wider `USW|US|UP|MON|UW|TMON` pattern — **the live role value is this tighter regex.**

---

## Dependencies

```
util / speed-expect  →  link down  →  no SNMP  →  ICMP down  →  site unreachable
CPU / mem / temp     →  ICMP down
```

A site WAN blip must not be one High per switch. Those Highs **depend on** a site **Disaster** (proxy / core / synthetic).

---

## Watch the watcher

| Check | Why |
|---|---|
| Unsupported item count | SNMP walk died; looks like health |
| Switch with **zero** discovered interfaces | IFALIAS regex or LLD broken |
| Proxy last-seen | hosts go *unknown*, not *down* |

---

## EXOS

Grammar in **`display-string`**, max **20** characters. Leave **`description-string` empty** (it wins `ifAlias`).

| Template | Where |
|---|---|
| Extreme EXOS by SNMP | Platform EXOS |

On **this template**:

```
{$TEMP_WARN}     = 95
{$TEMP_CRIT}     = 100
{$TEMP_CRIT_LOW} = -273
```

Stock duplex LLD does **not** honour IFALIAS — it must use the same MATCHES / NOT_MATCHES as `net.if.discovery` or Access alerts on unlabelled ports. Interface LLD: **15m**, keep-lost **0** (relabel to `X` must stop the same day, not in a week).

---

## VOSS

Grammar in interface **`name`** → `ifAlias`. Do not use `rcPortName`. Same 20-character budget.

| Template | Where |
|---|---|
| Extreme VOSS by SNMP | Platform VOSS |

Same `{$TEMP_*}` on **this template**. Also (template / fleet macros, not the Switch* role):

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

V-IST: set host `{$VIST.CONTROL}=1` only on fabric pairs. Classic IST stays 0. Traps (fan/PSU/overheat/ISIS/LAG) are in the template — collect; do not page duplicates of the polled items until we have seen them on hardware.

Fabric (ISIS / V-IST) is the VOSS equivalent of OSPF — **later**, more important than OSPF for this estate.

---

## Both platforms

| Template | Where | Triggers |
|---|---|---|
| Extreme Port Speed Expect by SNMP | Switch Core / Dist / Access / Mgmt | **off** until labels are clean |
| Extreme Routing by SNMP (OSPF) | Switch Core / Dist | **off** |

Speed Expect uses its **own** LLD macros (not `{$NET.IF.*}`). Default (Core/Dist/Mgmt):

```
{$PORTID.LLD.IFALIAS.MATCHES} = ^(USW|US|UP|MON)(-|$)
{$PORTID.LLD.IFTYPE.MATCHES}  = ^6$
```

On **Access**, override MATCHES to `^(USW|UP)(-|$)` so desk `US`/`MON` labels cannot leak into Speed Expect.

`{$IF.UTIL.MAX:"USW"}=80` is **not** current. Keep global 101 until there is history. Discards after that.

---

## Later

OSPF count; USW util + discards; VOSS fabric adjacency; sFlow on a few Core `USW`; one synthetic ping per site (proxy → DC) as the **Disaster** SLI; NetBox vs live `ifAlias` compliance; syslog on the proxy; `walk[]` dependent items when we retune poll load.

FortiGate and network VMs reuse this bar ([03](03-fortinet.md), [06](06-network-vms.md)) — different data path, same rules. Do not merge problem classes with Cato ([04](04-cato.md)).
