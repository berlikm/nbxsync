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
| Host dashboards | Traffic gallery only | Template dashboard **Health** (host-level) |

## Zero-touch / re-apply (do not break existing hosts)

| Lever | Who | New device | Re-run on a live estate |
|---|---|---|---|
| Platform Template Rule (EXOS / VOSS / `IQ ENGINE`) | nbxSync | First HostSync links the platform template | `ensure()` updates the rule; **does not** unlink hosts; retargets only if the rule still points at Network Generic |
| Role IFALIAS / IFTYPE / Access `PORTID.*` | nbxSync MacroAssignment | Inherited on sync | Updates assignment **values**; next sync of a host pushes macros. `--apply` does **not** mass-sync |
| SNMP Monitoring CG on Switch* / AP | zerotouch | Inherited interface + SNMPv3 | Empty env **must not** wipe existing secrets (zerotouch already leaves them) |
| YAML import `updateExisting` + `deleteMissing: false` | network `--apply` | n/a | Updates items/triggers/dashboards on the **template**; every already-linked host inherits. Does **not** delete hosts, interfaces, or history |
| Stock EXOS patches (TEMP_*, EtherLike IFALIAS, IF LLD 15m/0, ICMP loss disable, Health dashboard) | network `--apply` | n/a | Idempotent API merge; re-assert after an official EXOS re-import |
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

One dashboard named **Health** on the platform template. Open **Monitoring → Hosts → host → Dashboards**. No hostgroup widgets, no Host Navigator.

| Page | Question | Widgets (Zabbix 7 template-safe) |
|---|---|---|
| Health | Is this box OK? | Item tiles: ICMP, SNMP, CPU (and AP: clients/temp). Graph: CPU. Graph prototype: memory (VOSS) or clients (AP). |
| Path / RF | Errors and status, not a traffic farm | IF traffic prototype (2×3). AP: radio RF + retries. |

Stock EXOS keeps upstream **Network interfaces**; `--apply` upserts **Health** via API so we do not fork stock YAML. VOSS/IQ ship Health in YAML (same uuid on VOSS so re-import **renames** the old traffic-only board in place).
