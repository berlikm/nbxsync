# Alerting and host Health — Extreme switches and APs

Operator pages: [01-extreme-switching.md](../01-extreme-switching.md), [02-extreme-access-points.md](../02-extreme-access-points.md).  
This note is the analysis those pages compress. Do not treat this file as a second policy.

## Why this exists

Cutover must be **no worse than LogicMonitor**, and **re-running zero-touch must not rebuild** hosts that already live in Zabbix. New devices must still inherit the same Template Rules, role macros, and platform templates.

## Alerting model (SRE + NMS)

A **page** (Disaster/High) must be: user or forwarding impact now, urgent, actionable, one incident per root cause.

| Channel | Zabbix sev | Use |
|---|---|---|
| SMS/call 24/7 | Disaster, High | Site down; device ICMP down; temp **critical** |
| Ticket, business hours | Average | SNMP dead, PSU/fan, DOM alarm, memory, “we are blind” |
| Next day / dashboard | Warning | CPU, errors, flaps, duplex, speed-expect (when linked) |
| Log | Info | Firmware / serial |

Google SRE: dashboards answer “what’s broken / why”; do not page on causes. Network practice splits **device health** (CPU, mem, temp, FRU) from **traffic**. Official Zabbix Extreme templates only ship a traffic gallery — we add a host **Health** dashboard on the platform template instead of global country/role boards.

## Intended speed

The on-box label is the contract (`USW`→10G, `UP`→1G, `UP-2G5-…`→2.5G). Live `ifHighSpeed` is observed state.

- Compare `last(speed) <> {#IF.SPEED.EXPECTED}` (Mbps). Settle on **oper-status 5m**, never `min(speed,5m)` (heartbeat 1h → unknown).
- Utilisation (later) is **% of intended**, 1h average — not stock 15m vs live speed.
- Discards are the “someone is dropping” signal.
- **Do not link** Speed Expect until labels are clean. YAML util context for `USW` is **101** (off). Stage 6 may set `{$IF.UTIL.MAX:"USW"}=80` on the template.

## What was wrong vs the docs

| Issue | Was | Now (cutover) |
|---|---|---|
| Docs said `USW`/`UP` link-down **High** | Stock/VOSS one **Average** for every discovered port | Average is the live contract; class High is later |
| Observability listed flaps/errors as “page” | Warning (next day) | Graph/ticket, not 03:00 |
| Speed Expect `{$IF.UTIL.MAX:"USW"}=80` | Would page 80% of intended 10G the moment it was linked | **101** (off) |
| VOSS ISIS circuit / card **High** ungated | 24/7 on unused SPBM / empty slots | `{$ISIS.CONTROL}=0`, `{$CARD.CONTROL}=0` (same pattern as V-IST) |
| Switch ICMP loss/RTT Warning | CH proxy RTT is WAN, not box health | **DISABLED** (items stay; same as APs) |
| EXOS SNMP-dead | Stock Warning | Still stock (do not fork); VOSS/IQ are Average |
| “Never silent” | Census only | Average trigger on unsupported-item count |
| Host dashboards | Traffic gallery only | **Health** for chassis/diagnostics plus unified **Network interfaces** status map and graph grid |

## Zero-touch / re-apply (do not break existing hosts)

| Lever | Who | New device | Re-run on a live estate |
|---|---|---|---|
| Platform Template Rule (EXOS / VOSS / `IQ ENGINE`) | nbxSync | First HostSync links the platform template | `ensure()` updates the rule; **does not** unlink hosts; retargets only if the rule still points at Network Generic |
| Role IFALIAS / IFTYPE / Access `PORTID.*` | nbxSync MacroAssignment | Inherited on sync | Updates assignment **values**; next sync of a host pushes macros. `--apply` does **not** mass-sync |
| SNMP Monitoring CG on Switch* / AP | zerotouch | Inherited interface + SNMPv3 | Empty env **must not** wipe existing secrets (zerotouch already leaves them) |
| YAML import `updateExisting` + `deleteMissing: false` | network `--apply` | n/a | Updates items/triggers/dashboards on the **template**; every already-linked host inherits. Does **not** delete hosts, interfaces, or history |
| Stock EXOS patches (TEMP_*, EtherLike IFALIAS, IF LLD 15m/0, ICMP loss disable, interface grid) + Observability companion | network `--apply` | n/a | Companion YAML owns Health; stock keeps its graph prototype while its existing dashboard is normalized to the shared map + 3×2 grid |
| Speed Expect / OSPF | imported, **not** assigned | Stays off | `--apply` without `--link-speed-expect` **does not unlink** if someone linked it earlier |
| Global `create_dashboards.py` | not part of apply | — | Do not run on re-apply (hostgroup boards, not Health) |
| VOSS/IQ TemplateRule when YAML is not in Zabbix yet | zerotouch | skip writing the rule | **Does not** retarget an existing Extreme rule at Network Generic |

Mass `SyncHostJob` is **not** required for template dashboard / trigger-status changes. Zabbix pushes those from the template. Use per-host sync only when NetBox macros/CG/templates on **that** device changed.

### Things that look like bugs but are features

- Access unlabelled / desk ports: **no items** (IFALIAS `USW|UP` only). A mistyped uplink is silent — fix the label, do not widen the regex.
- `HiveOS` platform without `IQ ENGINE` in the name: Template Rule never matches.
- After AP/switch reboot, SNMP=0 while CLI from the proxy works: RFC 3414 engine boots — `zabbix_proxy -R snmp_cache_reload`, not a template bug.

### Still later (do not invent in this pass)

- Site **Disaster** parent (WAN blip → one incident). Without it, ICMP High is per device.
- AP ICMP depends on Access `UP-` (needs NetBox/LLDP map).
- Class-scoped link-down High.
- OSPF, CRC/`dot3StatsFCSErrors`, util/discards enable.

## Health dashboard (host, from template)

Two host-level dashboards: **Health** for chassis/diagnostics and **Network interfaces** for the status map and combined discovered graphs. Open **Monitoring → Hosts → host → Dashboards**. No hostgroup widgets, no Host Navigator.

| Page | Question | Widgets (Zabbix 7 template-safe) |
|---|---|---|
| Overview | Is this box reachable and healthy? | ICMP + SNMP + CPU + platform 4th tile (EXOS temp / VOSS uptime / AP clients). Problems full width. Two history panes. |
| Hardware / RF | Are FRUs or radios unhealthy? | Honeycombs. Switches: memory graph under the map. IQ: noise/Tx **and** retries/drops in a 2-column radio grid. |
| Diagnostics | What is the exact state of one object? | Switches: interface-tagged navigator (EXOS has no flap counter in stock). APs: **radio**-tagged navigator only — eth lives on **Network interfaces**. |

All platforms expose **Network interfaces → Overview** with the same compact status map and 3×2 graph grid. The map is scan-only (red/green). Zabbix 7 cannot open that port’s Network traffic graph from a hex; use **Health → Diagnostics** for bits/errors/discards of one interface. VOSS/IQ ship it in YAML; `--apply` applies the layout to the existing stock EXOS dashboard. VOSS/EXOS graphs combine RX/TX with errors/discards on a secondary axis; IQ Engine shows RX/TX only. `create_dashboards.py` is not involved. Do not use RX+TX as a congestion total on full-duplex Ethernet.

Overview tiles are short labels (ICMP, SNMP, CPU, Temp/Uptime/Clients). Gauges show a bold value and colour arc only. Honeycombs are compact heatmaps: identity on the cell, colour for health (no “up” on every hex). Diagnostics is navigator + graph; there is no giant last-value tile. Graph legends are off when the widget title is enough.

Honeycomb thresholds are `>=`. VOSS fan `notpresent(4)` therefore paints like `down(3)` (red). Empty PSU `empty(2)` stays grey (green starts at 3). EXOS PSU `notPresent(1)` stays grey (green starts at 2). Do not “fix” that with inverted colours; filter LLD later if empty fans noise the map.

AP Overview omits a temperature gauge: HiveOS often stubs `ahEnvirmentTemp` at 0 °C. A green gauge would look healthy. The Average temp ticket still lands on the problems strip. Memory is on the CPU+mem history pane, not a fifth Overview tile.
