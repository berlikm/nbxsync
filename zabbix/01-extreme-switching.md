# Extreme switching

EXOS and VOSS are the same from ops: one set of alerts, one label grammar, different platform templates.

Labels: [port-identity.md](port-identity.md).

---

## What we alert

| Device | Alert | Sev |
|---|---|---|
| ICMP down | yes | High |
| SNMP dead (ICMP still up) | yes | Warning |
| Unplanned reboot | yes | Warning |
| Temperature **critical** / vendor alarm | yes | High |
| PSU / fan failed | yes | Average |
| CPU high | yes | Warning |
| Memory high | yes | Average — baseline first |
| Firmware / OS / serial change | yes | Info |
| System name changed | **no** | disabled |

Temperature **warning** and “too low” are silenced (closets + stack nodes at 0 °C).

| Ports in scope | Alert | Sev |
|---|---|---|
| Link down (was up → down) | yes | Warning |
| Link flapping | yes | Warning |
| Wrong speed vs label | yes | Warning — physical ports only |
| Half duplex | yes | Warning |
| Interface errors | yes | Warning |
| Outbound discards (`USW`) | yes | Warning |
| Sustained util 1h avg (`USW`) | yes | Warning — does **not** page |
| Traffic graphs | **no** | dashboards only |
| `X…` ports | **no** | not discovered |
| Access / AP / endpoint util | **no** | |

Do **not** alert on: laptop unplug (Access is opt-in), util on access/AP/server ports, stock 15m bandwidth-usage, fifty hosts for one site down (dependencies + proxy per site).

---

## Scope

| Role | In | Out |
|---|---|---|
| Switch Core / Dist / Mgmt | All admin-up physical/LAG **except** `X…` | `X…`; admin-down is not discovered |
| Switch Access | Only `USW` `US` `UP` `MON` `UW` `TMON` | Unlabelled, `N…`, `X…` |

**`X` excludes. `N` does not.** On Core, `N` / empty / leftover labels still get link-down if the port was up and then went down. Structural links (stack, ISC, MLAG peer, SPAN) need **`X`**, not a note. Unused ports: **admin-down**, not `X`.

Port-filter macros on those Switch* roles (nbxSync):

| Role | `{$NET.IF.IFALIAS.MATCHES}` | `{$NET.IF.IFALIAS.NOT_MATCHES}` | `{$NET.IF.IFTYPE.MATCHES}` |
|---|---|---|---|
| Core / Dist / Mgmt | `.*` | `^X(-\|$)` | `^(6\|161)$` |
| Access | `^(USW\|US\|UP\|MON\|UW\|TMON)(-\|$)` | `CHANGE_IF_NEEDED` | `^(6\|161)$` |

`^(6|161)$` is physical + LAG (drops EXOS VLAN ifaces). Mute a port with **`X`**. Do not use `{$IFCONTROL:"{#IFNAME}"}`.

---

## EXOS

Grammar in **`display-string`**. Max **20** characters (EXOS truncates). Leave **`description-string` empty** — if set, it wins `ifAlias` and Zabbix reads the wrong value.

| Template | Where |
|---|---|
| Extreme EXOS by SNMP | Platform EXOS |

On **this template** (not global, not the role):

```
{$TEMP_WARN}     = 95
{$TEMP_CRIT}     = 100
{$TEMP_CRIT_LOW} = -273
```

Do **not** stack Network Generic (`icmpping` collision).

---

## VOSS

Grammar in interface **`name`** (lands in `ifAlias`). Do not use `rcPortName`. Same 20-character budget as EXOS.

| Template | Where |
|---|---|
| Extreme VOSS by SNMP | Platform VOSS |

Same chassis TEMP macros on **this template**:

```
{$TEMP_WARN}     = 95
{$TEMP_CRIT}     = 100
{$TEMP_CRIT_LOW} = -273
```

Do **not** stack Network Generic.

---

## Both platforms

IDs are short abbreviations; full names live in NetBox. Classes, speed tokens, examples: [port-identity.md](port-identity.md).

| Template | Where |
|---|---|
| Extreme Port Speed Expect by SNMP | Switch Core / Dist / Access / Mgmt |
| Extreme Routing by SNMP (OSPF) | Switch Core / Dist — **imported, triggers off** |

On **Port Speed Expect** (not the stock EXOS/VOSS LLD macros):

```
{$PORTID.LLD.IFALIAS.MATCHES} = ^(USW|US|UP|MON)(-|$)
{$PORTID.LLD.IFTYPE.MATCHES}  = ^6$
{$IF.UTIL.MAX}                = 101
{$IF.UTIL.MAX:"USW"}          = 80
{$IF.DISCARDS.WARN}           = 1
```

`{$IF.UTIL.MAX}=101` keeps stock util off until `USW` has enough history.

---

## Later

OSPF adjacency — template linked on Core/Dist; triggers stay off until EXOS/VOSS are quiet. Not a cutover item.
