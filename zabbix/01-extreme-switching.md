# Extreme switching

EXOS and VOSS are the same from ops: one set of alerts, one label grammar, different platform templates.

Labels: [port-identity.md](port-identity.md). NetBox IFALIAS clicks: [`docs/netbox-zabbix/configuration.md`](../docs/netbox-zabbix/configuration.md) §11.1.

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

## Which ports

| Role | Monitored | Quiet |
|---|---|---|
| Switch Core / Dist / Mgmt | All admin-up physical/LAG **except** `X…` | `X…`; admin-down is not discovered |
| Switch Access | Only `USW` `US` `UP` `MON` `UW` `TMON` | Unlabelled, `N…`, `X…` |

**`X` excludes. `N` does not.** On Core, `N` / empty / leftover labels still get link-down if the port was up and then went down. Structural links (stack, ISC, MLAG peer, SPAN) need **`X`**, not a note. Unused ports: **admin-down**, not `X`.

---

## Labels (on the box)

Grammar goes in EXOS **`display-string`** / VOSS interface **`name`**. Max **20** characters (EXOS truncates). Leave EXOS **`description-string` empty** — if set, it wins `ifAlias` and Zabbix reads the wrong value. IDs are short abbreviations; full names live in NetBox.

Classes, speed tokens, examples: [port-identity.md](port-identity.md).

---

## Templates

Do not clone stock templates. Do **not** stack Network Generic on Switch* (`icmpping` collision).

| Template | Where |
|---|---|
| Extreme EXOS by SNMP | Platform EXOS |
| Extreme VOSS by SNMP | Platform VOSS |
| Extreme Port Speed Expect by SNMP | Switch Core / Dist / Access / Mgmt |
| Extreme Routing by SNMP (OSPF) | Switch Core / Dist — **imported, triggers off** |

Chassis temperature macros live on the **EXOS/VOSS templates**, not global and not on the role:

```
{$TEMP_WARN}     = 95
{$TEMP_CRIT}     = 100
{$TEMP_CRIT_LOW} = -273
```

Mute a port with **`X`**. Do not use `{$IFCONTROL:"{#IFNAME}"}`.

---

## OSPF

Nice-to-have, not cutover. Template is linked on Core/Dist; leave triggers disabled until EXOS/VOSS are quiet.
