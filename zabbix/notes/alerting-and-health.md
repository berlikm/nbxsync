# Alerting and host Health — Extreme switches and APs

Operator pages: [01-extreme-switching.md](../01-extreme-switching.md), [02-extreme-access-points.md](../02-extreme-access-points.md).  
This note is the analysis those pages compress. Do not treat this file as a second policy.

## Why this exists

Cutover must be **no worse than LogicMonitor**, and **re-running zero-touch must not rebuild** hosts that already live in Zabbix. New devices must still inherit the same Template Rules, role macros, and platform templates.

## Alerting model (SRE + NMS)

A **page** (Disaster/High) must be: user or forwarding impact now, urgent, **actionable tonight**, one incident per root cause.

| Channel | Zabbix sev | Use |
|---|---|---|
| SMS/call 24/7 | Disaster, High | Device ICMP down; temp **critical** |
| Ticket, business hours | Average | PSU/fan, DOM alarm, memory, **every discovered** link down, “we are blind” (unsupported items) |
| Next day / dashboard | Warning | SNMP dead, CPU, errors, flaps, duplex, speed-expect (when linked) |
| Log | Info | Firmware / serial |

On-box classes are identity, not a second severity map: `US` = server/storage (Pure), `USW` = switch/firewall/other network box, `UP` = AP, `MON` = important with no better class. On Core/Dist/Mgmt, **only important ports are admin-up**. On Access, a grammar **display-string** is that contract. Admin-up + nothing connected (or a labelled Access port that never came up) is a ticket so dayside can check and **admin-down**. Unlabelled Access desk ports are not discovered. A Pure/`US` path down is a critical service we most likely **cannot restore at 03:00** — still Average, not High. Page the **box** (ICMP) and overtemp. If a *storage switch host* must wake pikett, that is host tag `critical`, not a special `US` trigger.

Google SRE: dashboards answer “what’s broken / why”; do not page on causes. Network practice splits **device health** (CPU, mem, temp, FRU) from **traffic**. Official Zabbix Extreme templates only ship a traffic gallery — we add a host **Health** dashboard on the platform template.

## Intended speed

The on-box label is the contract (`USW`→10G, `US`→10G, `UP`→1G, `MON`→1G, `UP-2G5-…`→2.5G). Live `ifHighSpeed` is observed state (IF-MIB million bits/s, compared in **Mbps**).

- **When a class label exists:** Warning `last(speed) <> {#IF.SPEED.EXPECTED}` while oper-up 5m. Empty `ifAlias` → no items. Next day, not a page — the link still forwards. Dayside: cable / SFP / autoneg, or the label is wrong.
- Settle on **oper-status 5m**, never `min(speed,5m)` (heartbeat 1h → unknown).
- Stock “changed to lower speed” misses `10G → bounce → 1G`. Absolute expect exists because of that hole.
- Do **not** split High by class. A Pure port at 25G labelled `US-PURE01` (expect 10G) is a **label** bug, same channel as an AP at 2.5G labelled `UP-…`.
- Utilisation (later) is **% of intended**, 1h average, **USW only** — not stock 15m vs live speed. A busy `US`/`UP` is that box’s problem.
- Discards are the “someone is dropping” signal. YAML trigger **DISABLED** until a baseline; `{$IF.DISCARDS.WARN}=1` is not gated by util `101`.
- Duplicate Speed Expect link-down is **DISABLED** — platform already Average-tickets discovered ports.
- Honeycomb stays oper-status. Operator sees the Warning title (`Speed 1000 Mbps != expected 10000 Mbps`) plus Port-page live Speed.
- **Do not wait for a census of empty ports.** No class label → LLD discovers nothing. Nesting on VOSS / Observability arms it; the day you write `US-25G-…` it starts. Dirty labels (class present, wrong token) Warning — that *is* the census. Util `{$IF.UTIL.MAX:"USW"}=101` (off). Stage 6 may set 80 after history.

`UW` has no PHY expect — commit rate is the NetBox Circuit (05). LAG aggregates (`ifType` 161) are out (`^6$`) because their speed is the sum of members.

## What was wrong vs the docs

| Issue | Was | Now (cutover) |
|---|---|---|
| Docs said `USW`/`UP` link-down **High** | Stock/VOSS one **Average** for every discovered port | Average is the live contract. Admin-up = should be live; ticket, do not page. |
| Observability listed flaps/errors as “page” | Warning (next day) | Graph/ticket, not 03:00 |
| Speed Expect `{$IF.UTIL.MAX:"USW"}=80` | Would Warning 80% of intended 10G the moment it was linked | **101** (off) |
| Speed Expect discards at 1 pps + second link-down | Would Warning besides platform Average link-down | discards and duplicate link-down **DISABLED** |
| VOSS ISIS circuit / card **High** ungated | 24/7 on unused SPBM / empty slots | `{$ISIS.CONTROL}=0`, `{$CARD.CONTROL}=0` (same pattern as V-IST) |
| Switch ICMP loss/RTT Warning | CH proxy RTT is WAN, not box health | **DISABLED** (items stay; same as APs) |
| EXOS SNMP-dead | Stock Warning | VOSS/IQ match Warning |
| “Never silent” | Census only | Average on unsupported-item count **and** on zero discovered interfaces (SNMP up 1h) |
| Host dashboards | Traffic gallery only | **Health** for chassis/diagnostics plus unified **Network interfaces** status map and graph grid |

## Zero-touch / re-apply (do not break existing hosts)

| Lever | Who | New device | Re-run on a live estate |
|---|---|---|---|
| Platform Template Rule (EXOS / VOSS / `IQ ENGINE`) | nbxSync | First HostSync links the platform template | `ensure()` updates the rule; **does not** unlink hosts; retargets only if the rule still points at Network Generic |
| Role IFALIAS / IFTYPE / Access `PORTID.*` | nbxSync MacroAssignment | Inherited on sync | Updates assignment **values**; next sync of a host pushes macros. `--apply` does **not** mass-sync; it logs who still needs HostSync |
| `{$PORTID.LLD.*}` defaults | Speed Expect **template** macros | Nested with VOSS / Observability | Not Zabbix globals. `--apply` deletes leftover globals |
| SNMP Monitoring CG on Switch* / AP | zerotouch | Inherited interface + SNMPv3 | Empty env **must not** wipe existing secrets (zerotouch already leaves them) |
| YAML import `updateExisting` + `deleteMissing: false` | network `--apply` | n/a | Updates items/triggers/dashboards on the **template**; every already-linked host inherits. Does **not** delete hosts, interfaces, or history |
| Stock EXOS patches (TEMP_*, EtherLike IFALIAS, IF LLD 15m / disable-now / delete 7d, ICMP loss disable, interface grid) + Observability companion | network `--apply` | n/a | Companion YAML owns Health + zero-interface trigger; stock keeps its graph prototype while its existing dashboard is normalized to the shared map + 3×2 grid |
| Speed Expect / OSPF | Speed Expect **nested** on VOSS / Observability; OSPF imported, not assigned | Empty ifAlias silent; OSPF stays off | `--apply` imports the nest. `--link-speed-expect` is extra role assignment — skip while nested |
| VOSS/IQ TemplateRule when YAML is not in Zabbix yet | zerotouch | skip writing the rule | **Does not** retarget an existing Extreme rule at Network Generic |

Mass `SyncHostJob` is **not** required for template dashboard / trigger-status changes. Zabbix pushes those from the template. Use per-host sync only when NetBox macros/CG/templates on **that** device changed.

### Things that look like bugs but are features

- Access unlabelled / desk ports: **no items** (IFALIAS opt-in `USW|US|UP|MON|UW|TMON`). A mistyped uplink with no CLASS is silent — fix the label.
- `HiveOS` platform without `IQ ENGINE` / `IQEngine` / `IQ-ENGINE` in the name: Template Rule never matches. Do not match bare `HiveOS`.
- After AP/switch reboot, SNMP=0 while CLI from the proxy works: RFC 3414 engine boots — `zabbix_proxy -R snmp_cache_reload`, not a template bug.

### Not this apply

Speed Expect is nested on VOSS / EXOS Observability (`--apply`). Unlabeled ports are not discovered.

## Health dashboard (host, from template)

Two host-level dashboards: **Health** for the box and **Network interfaces** for ports. Open **Monitoring → Hosts → host → Dashboards**.

### Why each widget exists

| Question | Where | Widget | Why this type |
|---|---|---|---|
| Can we reach the box? | Overview | ICMP + SNMP gauges | One binary number. Same chrome as CPU. |
| Is compute saturating? | Overview | CPU gauge; **CPU / memory** graph (EXOS, IQ) | Brendan Gregg USE: CPU and memory are the same class. IQ already did this. A honeycomb of one EXOS Access slot is a giant hex named Memory — wrong. |
| How long has SNMP been up? | Overview | **Uptime** item tile + graph | Same 4th tile on EXOS, VOSS, and IQ. Duration, not a 0–100 gauge. Reboot still tickets Warning from the template trigger. |
| Overtemp on this switch? | Hardware | EXOS Temp gauge + trend; VOSS named °C honeycomb | Off Overview so the four tiles stay identical. Overtemp High still pages; the problems strip shows it. HiveOS often stubs 0 °C — APs keep temp off the board. |
| How many clients on this AP? | RF | Clients item + graph | Census, not a page. Association table stays out. |
| What is broken right now? | Overview | Problems strip | Tickets, not decoration. |
| Did a fan/PSU die? | Hardware | Colour honeycomb, identity only | N similar FRUs. Empty map on Access = LLD found nothing (census). |
| Where is heat / draw? | Hardware (VOSS chassis) | Temp °C + Power W honeycombs | Values, named sensors. Not SNMP indexes 1–5. |
| Per-slot memory on a chassis | Hardware (VOSS) | Graph prototype on **this** template | Same-template graph refs import cleanly. |
| Are radios noisy? | RF (IQ) | Noise honeycomb + 2-col graphs | Two radios, gallery is enough. |
| Which port is down? | Network interfaces | Honeycomb of **IFNAME** (`1:1`, `1/21`, `eth0`) | Colour without an ID is a Christmas tree. Auto type + short ID; alias is hover. Switches: height 6 so cells stay above Zabbix's 32px floor. IQ: **12×3** — Zabbix has no max cell size; two eth in 72×6 are giant hexes. Custom 20% truncated IDs on dense maps. |
| How much traffic? | Network interfaces | 3×2 native graphs, **height 14** | Demand. Errors/discards on the VOSS/EXOS secondary axis. Same size on VOSS YAML, IQ YAML, and stock EXOS `--apply`. |
| Why is *this* port sick? | Network interfaces → Port | Navigator of faults, not bits | Does not repeat Overview traffic. |

There is no Health **Diagnostics** page. That was a second interface browser.

Do **not** bind an svggraph **item pattern** on the EXOS companion (`ds.dataset_type=1` / `#*: Memory utilization`). Host view hits `CSvgGraphHelper::getMetricsPattern` and PHP `Array to string conversion`. Bind a calculated item on the companion (`last(//vm.memory.util[1])`) like CPU.

All platforms expose **Network interfaces → Overview** with the same map + 3×2 grid. Switches add **Port**. IQ has no Port page. YAML import does not delete leftover Diagnostics pages (`deleteMissing: false`); `--apply` drops them. Do not use RX+TX as a congestion total on full-duplex Ethernet.

Overview tiles are short labels. Gauges show a bold value and colour arc only. The 4th tile is an **item** widget (Uptime) on every platform — same chrome as VOSS already had. FRU honeycombs keep **Custom 20%** (two fans must not explode) at height 3. Interface honeycombs use **Auto** on the short port ID (not bold). Switch maps are **72×6** so a dense VOSS stays above the 32px floor. IQ maps are **12×3**: same widget, ~2 eth, no max cell size — a switch-sized box would be two giant hexes. VOSS Temp binds `Temperature sensor *` (°C, `{#SENSOR_DESCR}`). Power is `PSU *: Output watts`. `rcSysTotalPower` is capacity, not load.

- Honeycomb thresholds are `>=`. VOSS fan `notpresent(4)` paints like `down(3)` (red). VOSS PSU LLD **skips `empty(2)`** chassis bays — SNMP keeps a row for every PSU slot, CLI `show sys power power-supply` lists fitted units only. Failed/unknown units stay (`down(4)` / `unknown(1)`); crit is still `{$PSU_CRIT_STATUS}=4`. EXOS PSU LLD **skips `notPresent(1)`** — a stack MIB row for every possible member is padding, not a FRU. Failed/off units stay (`presentNotOK` / `presentPowerOff`). `--apply` queues check-now LLD tasks for hosts retaining stale EXOS `notPresent(1)` or VOSS `empty(2)` rows; it does not host-sync or write NetBox.

AP Overview omits a temperature gauge: HiveOS often stubs `ahEnvirmentTemp` at 0 °C.
