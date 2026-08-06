# Extreme switching — Zabbix monitoring

Status: building    Owner:    Depends on: [port-identity.md](port-identity.md)

---

# §A EXOS

## 1. Scope

In:  EXOS device health + port monitoring driven by the `ifAlias` label
Out: VOSS (§B), OSPF routing (§C), access points (02), WAN circuits (05), LAG/MLAG (port-identity §5 TBD)

## 2. What we want to know

Plain language. Each line is a question ops actually asks. This is the requirement; everything below is just how we answer it.

### Is the switch alive and healthy?

- Is the switch reachable at all?
- Is it answering management queries, even if it still pings?
- Did it reboot when nobody planned a reboot?
- Is it overheating?
- Has a power supply or a fan failed — are we running without redundancy and don't know it?
- Is it slowly running out of CPU or memory in a way that will bite us later?
- Was the hardware swapped or the firmware changed without us being told?

### Are the links we care about up?

- Did a link that was working stop working?
- Is a link flapping — up and down repeatedly — rather than cleanly down?
- Are we told about the links we chose to care about, and left alone about the rest?

### Are the links performing as designed?

- Is a 10G link silently running at 1G? (bad optic, bad patch panel, autoneg problem)
- Is a link up but dirty — frame/CRC errors on something that otherwise looks fine?
- Is a link stuck in half duplex?
- Is an uplink sustainably full — not a brief spike, but genuinely running out of capacity?
- Is the switch actually **dropping** traffic because a link is congested?

### Can we trust the monitoring itself?

- Are we monitoring every switch we own, or did one quietly get missed?
- Did a check stop working without telling anyone?
- When a whole site drops, do we get one alert or fifty?

### What we deliberately do NOT want

- Alerts for ports we explicitly marked as uninteresting.
- An alert every time somebody unplugs a laptop.
- Utilisation alerts on access, AP or endpoint ports — a busy server port is the server's business.
- Utilisation alerts that fire on a nightly backup.
- Fifty alerts for one root cause.
- Seasonal temperature warnings from closets that have never had cooling.
- Alerts nobody can act on at 03:00.

## 3. Data path

| Source | Protocol | Credential | Interval |
|---|---|---|---|
| EXOS switch | SNMP v2c/v3 | ro-community | 1m health, 1m ports |

Poll path: decide deliberately whether Zabbix reaches the switch via the mgmt VR or in-band, and be consistent. If the mgmt path dies while the data path is fine, we get a false "device down".

### Which CLI field carries the label

Canary on EXOS-VM 32.7.2.19 — `ifAlias` resolution:

| Fields set | `ifAlias` returns |
|---|---|
| `display-string` only | display-string |
| `description-string` only | description-string |
| **both** | **description-string** (wins either order) |

**Rule: the grammar goes in `display-string`; `description-string` stays empty.** `display-string` is visible in the everyday `show ports` output, `description-string` only in `show port info detail`. If anyone sets `description-string` it silently takes over `ifAlias` and Zabbix reads the wrong thing — that is a compliance check.

The two fields cannot be combined — there is no "grammar in one, prose in the other". `description-string` always wins `ifAlias`, so human prose lives in NetBox, not on the box.

### Label budget: 20 characters

Confirmed on a live switch — EXOS **truncates silently** with a CLI warning:

```
configure ports 1:10 display-string 111111111111111111111111
Warning: port display string exceeds maximum length of 20 characters,
truncating to "11111111111111111111"!!
```

So the fleet budget is **20**, not 64. VOSS `name` allows 64, but the grammar uses the lowest common denominator.

Worst-case prefix is `USW-100M-` = 9 characters, leaving **11 for the ID**:

| Label | Len |
|---|---|
| `USW-SWD14` | 9 |
| `USW-10G-SWD14` | 13 |
| `USW-100M-ZH4-DIST01` | 19 |
| `MON-100M-IDR03` | 14 |
| `UP-2G5-AP3F07` | 13 |
| `X-MLAG-PEER` | 11 |
| `USW-10G-CH-ZRH-ZH4-DIST01` | **25 — does not fit** |

IDs must be machine-short abbreviations, not hostnames. Full identity lives in NetBox.

**The generator must enforce ≤20 and refuse**, not let the switch truncate — a truncated label produces a permanent generated-vs-live compliance diff.

**Safety property worth keeping:** because CLASS and SPEED come first in the grammar, truncation only ever damages the ID. A truncated `USW-10G-CH-ZRH-ZH4-D` still discovers correctly and still expects 10G. Monitoring semantics survive; only the label's readability degrades.

## 4. Signals

How §2 maps to data. Everything here except the last two rows comes from the stock template — see [notes/exos-stock-template-review.md](notes/exos-stock-template-review.md).

| # | Question from §2 | Signal | Source |
|---|---|---|---|
| 1 | reachable? | icmpping | simple check |
| 2 | answering management? | SNMP agent availability | Zabbix internal |
| 3 | unplanned reboot? | uptime | SNMPv2-MIB / HOST-RESOURCES-MIB |
| 4 | overheating? | temperature value + vendor alarm status | EXTREME-SYSTEM-MIB |
| 5 | PSU / fan failed? | PSU + fan status | EXTREME-SYSTEM-MIB |
| 6 | running out of resources? | CPU, memory | EXTREME-SOFTWARE-MONITOR-MIB |
| 7 | hardware/firmware changed? | serial, firmware, OS version | ENTITY-MIB |
| 8 | link down? | ifOperStatus | IF-MIB |
| 9 | running at the wrong speed? | ifHighSpeed | IF-MIB |
| 10 | dirty link? | in/out errors, discards | IF-MIB |
| 11 | **CRC specifically?** | `dot3StatsFCSErrors` | EtherLike-MIB — **not in stock template, see §9** |
| 12 | half duplex? | `dot3StatsDuplexStatus` | EtherLike-MIB |
| 13 | uplink sustainably full? | `ifHCInOctets` / `ifHCOutOctets` vs **intended** `{#IF.SPEED.EXPECTED}` | IF-MIB, 1h average — §6.4 |
| 14 | dropping traffic? | `ifOutDiscards` | IF-MIB |
| 15 | which ports do we care about? | ifAlias | IF-MIB `.1.3.6.1.2.1.31.1.1.1.18` |

## 5. Discovery

Rule: stock `net.if.discovery` (IF-MIB) — **unmodified**. Scoping is done entirely with macro overrides.

### Where the macros live

**nbxsync assignments in NetBox.** Zabbix user macros exist at **global, template and host level only** — there is no host-group macro. nbxsync resolves assignments down its inheritance chain and writes host macros, which always win.

Host groups stay useful for dashboards, permissions and maintenance windows — just not for macros.

### Role × platform — two independent axes

A core switch can be EXOS **or** VOSS. These are orthogonal; never build a Core-EXOS / Core-VOSS template matrix.

| Axis | NetBox object | Drives | Mechanism |
|---|---|---|---|
| **Platform** (`EXOS` / `VOSS`) | Platform | the **platform** template | template inheritance is **additive** |
| **Role** (`Core` / `Dist` / `Access` / `Hybrid`) | DeviceRole | port-scoping macros **+ capability templates** (e.g. routing, §C) | macro resolution, **first path wins** |
| **Site / SiteGroup** | Site, SiteGroup | proxy, ICMP sensitivity, maintenance | appended after role/platform |

nbxsync's `inheritance_chain` resolves `['role']` at position 2 and `['platform']` at position 9, so for a same-named macro **role beats platform**. `['device']` is first, which is the escape hatch for a one-off exception.

So a VOSS core switch gets `Extreme VOSS by SNMP` from its platform and the *same* Core macros as an EXOS core switch. Nothing crosses over.

### Role model

One template set for every role. Only the macro values differ. **Set both IFALIAS macros on every role** — the stock LLD filter evaluates both, and leaving one unset lets it resolve from somewhere unintended.

| NetBox role | `{$NET.IF.IFALIAS.MATCHES}` | `{$NET.IF.IFALIAS.NOT_MATCHES}` | "No label" means |
|---|---|---|---|
| Core / Dist / Mgmt | `.*` | `^X(-\|$)` | **monitored** |
| Access | `^(USW\|US\|UP\|MON\|UW\|TMON)(-\|$)` | `CHANGE_IF_NEEDED` (never matches) | not monitored |
| Hybrid (core∩access) | Access values, → Core values at stage 5 | | changes at stage 5 |
| All roles | `{$NET.IF.IFTYPE.MATCHES}` = `^(6\|161)$` | | physical + LAG only |

### `X` excludes, `N` does not

Only **`X`** removes a port from monitoring. **`N` is monitoring-neutral** — it is a note, and behaves exactly like an unlabelled port plus human text.

| Label | Core (monitor all active) | Access (opt-in) |
|---|---|---|
| class label (`USW` `US` `UP` `MON` `UW` `TMON`) | monitored | monitored |
| `N` / `N-<text>` | **monitored** | not monitored |
| no label at all | monitored | not monitored |
| unparseable legacy label (`ISC`, `esx40_ct1_eth0`, …) | **monitored** | not monitored |
| `X` / `X-<note>` | **excluded** | not monitored |

This is why the core regex is `^X(-|$)` and not `^(X|N)(-|$)`. It also defines the behaviour of legacy labels that match nothing: they are neutral, same as `N`. Structural ports that must never alert — stack, ISC, MLAG peer-link, SPAN — need an explicit **`X`**, not a note.

`ZabbixMacroAssignment` has a `context` field, so class-scoped macros like `{$IF.UTIL.MAX:"USW"}` (§6.4) are first-class assignments rather than hand-edited host macros.

The ifType filter matters: **EXOS presents VLAN interfaces in IF-MIB**. They have no `ifAlias`, so under the core rule they would otherwise be discovered and alert on "link down" for something that isn't a port.

**EtherLike duplex is a second LLD.** Stock EXOS `net.if.duplex.discovery` historically filters only oper-up (+ duplex enum) — **not** `{$NET.IF.IFALIAS.*}`. So Access can look “correct” on traffic items and still show duplex on every up port. `configure_nbxsync_network.py` patches those IFALIAS conditions onto stock EXOS via API (VOSS YAML already ships with them).

### What happens to an unlabelled admin-up port on a core switch

This is the deliberate safety net for a forgotten label. Same applies to `N` and to unparseable legacy labels — all three are monitoring-neutral.

| Template | Discovered? | Alerts it can produce |
|---|---|---|
| Stock EXOS | **yes** | link down, errors, half duplex |
| Speed-expect (thin) | no — filter is `{$PORTID.LLD.IFALIAS.MATCHES}` | none |
| Capacity (§6.4) | no — same filter | none |

And link-down carries the stock `.diff()` guard: it only fires if the port **was up before and then went down**. An admin-up port that never had a cable in it never alerts.

Net behaviour: *"tell me if something that was working stops working, even if nobody labelled it."* Correct default for core.

### Exclusion hierarchy — admin-down beats `X`

| Priority | State | Effect |
|---|---|---|
| 1 | **admin-down** | not discovered at all — the stock filter drops `ifAdminStatus=2`. No items, no history, no cost |
| 2 | **`X` label** | excluded, but needs a config change and one discovery cycle to take effect |
| 3 | class label | monitored per class |
| 4 | `N`, unparseable, or no label | monitored on core, not monitored on access |

Unused ports should be **admin-down** as hygiene, not labelled `X`. Reserve `X` for ports that are genuinely up and carrying traffic we don't want alerts about — stack / ISC / MLAG peer-links, SPAN, test gear.

### LLD rule settings

| Setting | Value | Why |
|---|---|---|
| Update interval | **15m** during rollout, 1h after | a label change is invisible until the next discovery |
| Keep lost resources period | **0** | otherwise relabelling a port to `X` keeps alerting for 7–30 days and ops stops trusting the grammar |

### Speed expectation

A second thin template with **its own** LLD, filtered to the monitored classes and physical ports only (`^6$` excludes LAG aggregates, whose speed is the *sum* of members and would alert permanently).

**It must not reuse the stock filter macros.** A host macro has one value per name, so if the thin template shared `{$NET.IF.IFALIAS.MATCHES}` its LLD could not have a different filter from the stock one. Own namespace, assigned globally or on the template (same value everywhere — not per role):

```
{$PORTID.LLD.IFALIAS.MATCHES} = ^(USW|US|UP|MON)(-|$)
{$PORTID.LLD.IFTYPE.MATCHES}  = ^6$
```

It emits `{#IF.SPEED.EXPECTED}` from a JS preprocessing parse of `{#IFALIAS}`, plus `{#IF.CLASS}` and `{#IF.UTIL.MULT}` (= `100 / expected_bps`).

The label therefore does three jobs:

| Job | Driven by |
|---|---|
| Which ports get monitored | `USW` / `X` / `N` → LLD filter |
| What speed it should be | token or class default → `{#IF.SPEED.EXPECTED}` |
| Utilisation threshold and denominator | `{#IF.CLASS}` → `{$IF.UTIL.MAX:"USW"}`, `{#IF.SPEED.EXPECTED}` → % of designed capacity (§6.4) |

**Item keys must not collide with the stock template** — Zabbix requires unique keys per host and linking both templates would otherwise fail:

```
LLD rule:       net.if.speedexpect.discovery
dependent item: net.if.speed.expect[{#SNMPINDEX}]
master item:    net.if.speed[ifHighSpeed.{#SNMPINDEX}]   (lives in the stock template)
```

The master item is in a different template. That's fine at host level, but the speed template produces nothing if linked on its own — document the dependency.

The same template also carries dependent items for utilisation and discards (§6.4) — trigger prototypes cannot reference item prototypes belonging to another template's LLD rule, so the values have to be re-exposed as dependent items here. No extra SNMP polling.

## 6. Triggers

| Sev | Condition | Settle | Source |
|---|---|---|---|
| High | unavailable by ICMP | 3 polls (5 for remote sites) | stock |
| Warning | no SNMP data | 5m | stock |
| Warning | link down (oper down, admin up, was up before) | `.diff()` guard | stock |
| Warning | interface flapping | count of status changes in 1h | **build** |
| Warning | `last(speed) <> {#IF.SPEED.EXPECTED}` while oper up | on oper status, 5m | **build** |
| Warning | error rate above threshold | 5m | stock, threshold from baseline |
| Warning | half duplex | — | stock |
| Warning | sustained utilisation above class threshold | **1h avg** | **build**, uplinks only — §6.4 |
| Warning | outbound discards (traffic actually dropped) | 15m | **build** — §6.4 |
| High | temperature above **critical** / vendor alarm | 5m | stock |
| Average | PSU / fan critical | — | stock |
| Warning | high CPU | 5m | stock |
| Average | high memory | 5m | stock, **baseline first** |
| Info | firmware / OS / serial changed | — | stock |
| Info | TMON link down | 5m | optional |
| — | high bandwidth usage | — | **silenced** via macro |
| — | temperature warning tier | — | **silenced** via macro |
| — | temperature too low | — | **silenced** via macro |
| — | system name changed | — | disable |
| — | anything on an `X` port | — | not discovered |

### Settle-time detail that matters

Do **not** use `min(speed, 5m)`. The stock speed item has *discard unchanged with heartbeat 1h*, so a 5-minute window is frequently empty and the trigger goes **unknown** instead of firing. Use:

```
last(<speed item>) <> {#IF.SPEED.EXPECTED}
and min(net.if.status[ifOperStatus.{#SNMPINDEX}], 5m) = 1
```

`last()` is always the current value; the settle lives on the oper-status side where data is dense.

### 6.4 Capacity — utilisation and discards

Two different questions, two different treatments. Do not conflate them.

| Question | Metric | Treatment |
|---|---|---|
| Is traffic actually being dropped? | `ifOutDiscards` | **Alert** — Warning. Unambiguous user impact |
| Is this link sustainably full? | utilisation, **1h average** | **Alert** — Warning. Capacity, not an outage. Does not page |
| Which links need upgrading next quarter? | 95th percentile, weekly | **Dashboard / report**, no alert |

**Why not utilisation alone:** at 1-minute polling every datapoint is already a 60-second average, so true peaks and microbursts are invisible to SNMP. A link at 90% for 15 minutes may be a nightly backup behaving correctly; a link at 40% may be dropping user traffic to bursts. `ifOutDiscards` is the signal that means somebody is actually suffering.

**Scope:** switch↔switch (`USW`) now, WAN (`UW`) later. **Not** access, AP, server or endpoint ports — a busy server port is the server's problem.

#### Denominator: intended speed, not `ifHighSpeed`

Utilisation is measured against `{#IF.SPEED.EXPECTED}` — the speed the label says the link *should* be — not against the live `ifHighSpeed`.

| | Actual (`ifHighSpeed`) | **Intended (`{#IF.SPEED.EXPECTED}`)** |
|---|---|---|
| Meaning | "is the pipe full right now" | "% of designed capacity" |
| When the link degrades | denominator moves — graph history silently changes meaning | stable, the dip is visible |
| When speed reads 0 | stock's `last(speed)>0` guard makes utilisation alerting **silently stop** | no guard needed, never zero |
| Cost | — | already parsed for the speed-expect trigger |

The obvious objection — a 10G link stuck at 1G and saturated reads only 10% of intended — is covered twice by other signals: **speed-expect** fires on the wrong speed (the root cause) and **discards** fire on the dropped traffic (the impact). Utilisation was never the right detector for that case.

A mislabelled port therefore fails **loudly**, not silently: a 1G link wrongly labelled `USW` (default 10G) under-reports utilisation, but speed-expect is already alerting on it.

**`UW` is the exception.** For WAN ports neither the actual nor the intended *physical* speed is the right denominator — a 1G handoff on a 200 Mbps circuit is full at 20% of the port. The denominator has to come from the NetBox Circuit's contracted bandwidth, which is why `UW` has no speed expectation and is deferred to 05.

#### Thresholds

Keyed by **class** using a context macro. `{$IF.UTIL.MAX:"{#IF.CLASS}"}` resolves to e.g. `{$IF.UTIL.MAX:"USW"}` at discovery and falls back to the global default for any class not named — so utilisation alerting is **opt-in per class**:

```
{$IF.UTIL.MAX}         = 101      # global default = off, nothing alerts
{$IF.UTIL.MAX:"USW"}   = 80       # switch <-> switch
{$IF.UTIL.MAX:"UW"}    = 70       # WAN, phase 05, denominator from Circuit
{$IF.DISCARDS.WARN}    = 1        # pps, tune from baseline
```

Triggers (in the thin template, on dependent items):

```
Warning:  avg(in_bps, 1h)  > ({$IF.UTIL.MAX:"{#IF.CLASS}"}/100) * {#IF.SPEED.EXPECTED}
       or avg(out_bps, 1h) > ({$IF.UTIL.MAX:"{#IF.CLASS}"}/100) * {#IF.SPEED.EXPECTED}

Warning:  min(out_discards, 15m) > {$IF.DISCARDS.WARN}
```

No `last(speed)>0` guard — the denominator is a constant from the label.

**Dependency:** utilisation → depends on → speed-expect. The wrong-speed alert is the root cause; "link is full" is a consequence.

For dashboards and percentile reporting, emit `{#IF.UTIL.MULT}` = `100 / expected_bps` from the same LLD parse, then a util-% item is just a dependent item on the bps master with that value as a custom multiplier. No calculated items, no division by zero.

The **stock** utilisation trigger stays silenced (`{$IF.UTIL.MAX}` = 101 globally) — it is keyed on `{#IFNAME}` not class, uses the live speed as denominator, and its 15m window trips on backups.

Enable in **stage 6**, after the label set is stable and there is enough history to pick real thresholds. Consider restricting to business hours on links with known nightly backup windows.

### Dependencies — the single biggest noise reduction

```
speed-expect      → depends on → link down
utilisation       → depends on → speed-expect      (wrong speed is the root cause)
link down         → depends on → no SNMP data
no SNMP data      → depends on → unavailable by ICMP
CPU / mem / temp  → depends on → unavailable by ICMP    (stock does not do all of these)
all host triggers → depends on → site core unreachable
```

Without this, one WAN blip produces one alert per device per site. A Zabbix **proxy per site** is the cleanest version of the last line.

### Known false-positive sources

| Source | Behaviour | Handling |
|---|---|---|
| Stack non-master nodes | report temperature **0** | silence the "too low" trigger |
| Closets without cooling | 45–55 °C in summer | silence the warning tier, keep critical + vendor alarm |
| `sysUpTime` 32-bit counter | wraps at ~497 days → false "restarted" | accept, or prefer `hrSystemUptime` where supported |
| Stack master failover | ENTITY-MIB serial can change → "device replaced" | Info + manual close |
| Chassis with one PSU fitted | empty slot may report a failed status | **verify on pilot before enabling** |
| Remote sites over WAN | 3 consecutive ICMP misses is easy to hit | use `#5` for remote host groups |
| LAG aggregate speed | reports the sum of members | excluded by the ifType filter |
| EXOS VLAN interfaces | discovered as "ports" | excluded by the ifType filter |
| Poller saturation | timeouts look identical to a sick device | size pollers before rollout |

### Known false-negative sources

Blindness is worse than noise. These produce silence, not alerts.

| Source | Detection |
|---|---|
| Item goes "not supported" — polling silently stops | monitor unsupported item count. **Mandatory** |
| Access port label typo → LLD never discovers it → no items at all | NetBox compliance diff is the *only* detector |
| LLD filter regex wrong → discovers nothing | alert if a switch has **zero** discovered interfaces |
| Host matched by no template rule | alert on hosts with no items |
| Proxy down → hosts go *unknown*, not *down* | monitor proxy last-seen |
| Stock "changed to lower speed" trigger | its `last()>0` guard means a degrade **via a link bounce is missed** — 10G → down(0) → up at 1G never fires. This is why the absolute-expect trigger exists |
| Stock utilisation trigger's `last(speed)>0` guard | when `ifHighSpeed` reads 0, utilisation alerting silently stops. Avoided by using `{#IF.SPEED.EXPECTED}` as the denominator (§6.4) |

Keep one deliberately mislabelled canary port whose alert should always be present. If it ever clears on its own, the pipeline is broken.

## 7. Staged rollout

Each stage runs for a week. Only promote if the previous stage is quiet. Target: **fewer than 5 actionable alerts per day**.

| Stage | Enable | Gate to next |
|---|---|---|
| **0** | Nothing. Link templates, collect data. **Hybrid switches in access/opt-in mode** | 1 week clean collection; ifIndex stability verified across a pilot reboot |
| **1** | ICMP unavailable, no SNMP data, proxy + self-monitoring, unsupported-item count | < 5 alerts/day |
| **2** | Link down, flapping, PSU, fan, temperature **critical** | PSU-empty-slot and stack-temperature behaviour verified; < 5 alerts/day |
| **3** | CPU, memory, errors — thresholds from **2 weeks of baseline**, not stock defaults | baseline data exists |
| **4** | Speed expectation, per host group | that site's label diff is clean |
| **5** | Flip hybrids from opt-in to fabric mode, per site | that site's `X`-fill and admin-down hygiene verified |
| **6** | Capacity: outbound discards, then sustained utilisation on `USW` (§6.4) | 4+ weeks of traffic history to pick real thresholds |

**Why hybrids start in opt-in mode:** on a subsidiary core∩access switch the fabric rule means *unlabelled = monitored*. Before the `X`-fill is done that is every desk port, and every laptop unplug is an alert. Opt-in is safe-by-default during the risky window; one macro flips it afterwards.

## 8. Template policy

**We do not modify the stock template.** Everything in §5–§7 is macro assignments in NetBox via nbxsync, which survives template upgrades.

One template set for every role — never a per-role copy of the template. Two copies drift.

| | Assigned on | |
|---|---|---|
| Stock | Platform `EXOS` | `Extreme EXOS by SNMP` — **release/7.0 branch** (master requires Zabbix 8.0) |
| Stock | Platform `VOSS` | `Extreme VOSS by SNMP` — build, see §B |
| Build | Both platforms | `Extreme Port Speed Expect by SNMP` — thin, own keys, own macro namespace, dependent items |
| Build | **Core / Dist roles** | `Extreme Routing by SNMP` — OSPF, platform-neutral, see §C |
| Maybe build | Both platforms | CRC error items if `dot3StatsFCSErrors` turns out to be needed (§9) |

### Macro assignments — destination standard

**Global** (or on the Zabbix server object) — production end-state. Applied by `configure_nbxsync_network.py` by default. Temporary LM silence is `--cutover-silence` only (see checklist §11.2).

```
{$IF.UTIL.MAX}                = 101          # stock util% off until stage 6 context macros
{$TEMP_WARN}                  = 90           # EXOS G2+ / VOSS — NOT stock 55
{$TEMP_CRIT}                  = 100          # NOT stock 65 (GTAC 000088439: Normal often to 100)
# extremeCurrentTemperature is an *internal* sensor, not ambient.
# Prefer vendor overTemp *status* as the hard alarm.
{$TEMP_CRIT_LOW}              = -273         # silence stack-returns-0 false positive
{$OPTIC.TEMP.CRIT}            = 70           # optic °C value trigger; prefer DOM *Status
{$OPTIC.TEMP.MAX}             = 150          # drop garbage DOM readings
{$OPTIC.RX.DBM.MIN}           = -100         # RX dBm value trigger removed; DOM status only
{$OPTIC.RX.DBM.FLOOR}         = -39          # legacy (synthetic -40); unused for alerts
{$OPTIC.DOM.ALARM_HIGH}       = 3            # primary optic alerts
{$OPTIC.DOM.ALARM_LOW}        = 5
{$MLT.CONTROL}                = 1            # .diff() keeps unused/disabled MLTs quiet
{$VIST.CONTROL}               = 0            # host =1 on VOSS fabric pairs
{$IST.CONTROL}                = 0            # classic IST unused on FE
{$SNMP.TIMEOUT}               = 5m
{$PORTID.LLD.IFALIAS.MATCHES} = ^(USW|US|UP|MON)(-|$)
{$PORTID.LLD.IFTYPE.MATCHES}  = ^6$
```

Stock **Extreme EXOS by SNMP** also defines template-level `{$TEMP_WARN}=55` / `{$TEMP_CRIT}=65`, which **override** globals. `configure_nbxsync_network.py` patches those (and VOSS) to the destination values above — globals alone are not enough.

**Device role** — port scoping. Set **both** IFALIAS macros on every role:

```
Core / Dist / Mgmt:
  {$NET.IF.IFALIAS.MATCHES}     = .*
  {$NET.IF.IFALIAS.NOT_MATCHES} = ^X(-|$)
  {$NET.IF.IFTYPE.MATCHES}      = ^(6|161)$

Access (and Hybrid until stage 5):
  {$NET.IF.IFALIAS.MATCHES}     = ^(USW|US|UP|MON|UW|TMON)(-|$)
  {$NET.IF.IFALIAS.NOT_MATCHES} = CHANGE_IF_NEEDED
  {$NET.IF.IFTYPE.MATCHES}      = ^(6|161)$
```

Only `X` appears in the core exclusion. `N` is a note, not an exclude — see §5.

**Site / SiteGroup** — geography, appended after role/platform so it cannot clobber them:

```
Remote sites: ICMP sensitivity, proxy binding
```

**Stage 6** (capacity, §6.4) — uses the `context` field on the macro assignment:

```
{$IF.UTIL.MAX:"USW"}          = 80           # opt-in per class; global stays 101 = off
{$IF.DISCARDS.WARN}           = 1            # pps, from baseline
```

Silencing by macro rather than disabling triggers keeps the template untouched and is reversible in one edit.

### Operational notes for ops

- The label goes in **`display-string`**, max **20 characters** — EXOS truncates silently past that. Leave `description-string` empty; if it is set it wins `ifAlias` and Zabbix reads the wrong value.
- IDs are machine-short abbreviations, not hostnames. The full far-end name lives in NetBox.
- **`X` excludes. `N` does not.** `N` is a note — a port labelled `N-SPARE` is still monitored on a core switch. To silence a port, use `X` or admin-down.
- Unused ports: **admin-down**, not `X`. Admin-down ports are not discovered at all.
- Labelling a port `X` takes effect at the **next discovery cycle**, not immediately.
- On core/dist, an unlabelled admin-up port still gets link-down and error alerts — deliberately. It will not alert unless it was up and then went down.
- The stock link-down trigger uses `.diff()` and manual close — after a manual close it will **not** re-fire on the next poll.
- `{$IFCONTROL:"{#IFNAME}"}` is a second, ifName-keyed mute switch built into the stock template. **Do not use it** — `X` is the single source of truth. Leaving two mute mechanisms creates a shadow config.
- Firmware upgrades need a maintenance window **with data collection** — otherwise we create data gaps as well as noise.
- Remove a device from Zabbix *before* powering it off for decommission.

## 9. Open questions

- [x] ~~EXOS: does `display-string` or `description-string` win for `ifAlias`?~~ **Answered** — canary on EXOS-VM 32.7.2.19: `description-string` wins when both are set; either alone is used. Decision: grammar in `display-string`, `description-string` left empty. Write-up: `/opt/cursor/artifacts/EXOS_IFALIAS_CANARY.txt`
- [x] ~~`display-string` max length~~ **Answered — 20 characters, silently truncated.** Confirmed on CH-NKN-G08-L02-CORE01. Fleet label budget is **20, not 64**. Documented in [port-identity.md](port-identity.md); generator must enforce ≤20 rather than let the switch truncate
- [ ] Confirm `:` is rejected by `display-string` on our EXOS versions; also test `,` and `;`
- [ ] Compliance check: any port where `description-string` is non-empty (it would hijack `ifAlias`)
- [ ] **Do CRC errors actually show up?** `ifInErrors` is an aggregate and may not move for FCS errors. The proper counter is `dot3StatsFCSErrors`, which the stock EtherLike LLD does **not** poll. Test with a known-bad patch lead before assuming §2 "dirty link" is covered
- [ ] `{$IF.ERRORS.WARN}` sane value — stock 2 pkt/s is a guess, set from baseline
- [ ] `{$IF.DISCARDS.WARN}` and `{$IF.UTIL.MAX:"USW"}` — set from 4+ weeks of history, not guessed
- [ ] Do our uplinks have predictable nightly backup windows that need time-of-day handling?
- [ ] Memory baseline — if the fleet normally sits above 90% the stock trigger fires permanently
- [ ] PSU status reported by an **empty** slot in a 2-PSU chassis
- [ ] ifIndex stability across reboot and across adding a stack member
- [ ] Legacy unparseable labels (`ISC`, `MLAG_MGMT01_p51`, `esx40_ct1_eth0`) — migration list. None match `^(X|N)`, so today they are monitored as ordinary fabric ports, on our busiest devices

## 10. Done when

- [ ] Pilot EXOS switch: health items green, only labelled ports discovered
- [ ] No alerts on `X` ports, and relabelling to `X` visibly stops alerts within one discovery cycle
- [ ] A port labelled `N-<text>` is **still monitored** on a core switch and **not** monitored on an access switch
- [ ] No VLAN interfaces or LAG aggregates in the port list
- [ ] Speed mismatch fires on a deliberately downgraded canary port
- [ ] Trigger dependency chain verified: a simulated site outage produces one alert, not fifty
- [ ] Unsupported-item and zero-interface checks in place
- [ ] No duplicate icmpping (Network Generic not stacked)
- [ ] A week at stage 2 with fewer than 5 actionable alerts/day
- [ ] Capacity: discard alerting live on `USW`, utilisation thresholds set from real history not guesses

---

# §B VOSS

Inherits **all** of §A: the plain-language requirements (§A.2), discovery scoping (§A.5), noise controls and dependencies (§A.6), staged rollout (§A.7) and operational notes (§A.8). Only the items below differ.

## 1. Scope

In:  VOSS device health + port monitoring, same label grammar as §A
Out: same as §A

## 2. Data path

| Source | Protocol | Credential | Interval |
|---|---|---|---|
| VSP switch | SNMP v2c/v3 | ro-community | 1m |

## 3. Signals

Same questions as §A.2. Interface half is identical (IF-MIB). Device-health half uses RAPID-CITY — **confirmed on a live lab** (Virtual Fabric Engine 9.3.1.0, see [templates/extreme_voss_snmp/LAB_RESULTS.md](templates/extreme_voss_snmp/LAB_RESULTS.md)).

| # | Signal | Source | Status |
|---|---|---|---|
| 1 | reachability | icmpping | reuse |
| 2 | CPU | `rcKhiSlotCpuCurrentUtil.<slot>` | ✅ confirmed |
| 3 | memory | `rcKhiSlot*` used / free / util | ✅ confirmed |
| 4 | temperature | temp LLD, 7 sensors | ✅ confirmed — **reads 0 °C on the VM** |
| 5 | PSU | `OperStatus` 3 = up, PS1/PS2 | ✅ confirmed |
| 6 | fan | `rcChasFan*` | **absent on virtual** — verify on hardware |
| 7 | model / serial / HW rev | `rcChasModelName` / Serial / HwRev | ✅ confirmed |
| 8 | version | `rcSysVersion.0` | ✅ confirmed |
| 9–15 | interfaces | IF-MIB | ✅ ports `1/1..` → ifIndex 192+ |

**Do not use** — confirmed absent (`No Such Object`):

| OID | Use instead |
|---|---|
| `rcSysCpuUtil` (`…2272.1.1.20.0`) | `rcKhiSlotCpuCurrentUtil` |
| `rcSysDramSize` / `Used` / `Free` (46/47/48.0) | `rcKhiSlot*` memory |
| `hrSystemUptime.0` | `sysUpTime.0` only — see §7 |
| `rcPortName` | `ifAlias` — `rcPortName` returns empty even when `name` is set |

## 4. Discovery

Same role-based macro model as §A.5 — identical macro values, only the platform template differs. A VOSS core switch and an EXOS core switch get the same Core role macros. Same LLD settings (15m interval, keep-lost-resources 0).

**Canary closed — VOSS uses `ifAlias`, same as EXOS:**

```
interface gigabitEthernet 1/1
 name USW-ID01
→ ifAlias.192   = "USW-ID01"    PASS
→ rcPortName.192 = ""           empty — do not rely on it
```

So the `{$NET.IF.IFALIAS.*}` macro approach works unchanged on VOSS. `name` allows 64 characters, but the fleet grammar stays at **20** — EXOS is the constraint.

## 5. Triggers

Same set, severities and dependency chain as §A.6, with two platform deltas:

| Delta | Why |
|---|---|
| "Host restarted" uses `sysUpTime.0` only | `hrSystemUptime.0` returns *No Such Object* on VOSS. The 32-bit wrap at ~497 days therefore has **no fallback mitigation** here — accept the false restart, or suppress it |
| Low-temperature trigger must ignore `0 °C` | VOSS-VM sensors report 0. Same shape as the EXOS stack finding — guard with `>0` |

## 6. Template

Name:   `Extreme VOSS by SNMP` — **built**, see [templates/extreme_voss_snmp/](templates/extreme_voss_snmp/)
Status: imported on Zabbix 7.0.29, lab host linked, 42 items / 14 LLD rules
Note:   TemplateRule **Extreme VOSS → Extreme VOSS by SNMP** (not Network Generic). Checklist §6.1 / `configure_nbxsync_zerotouch.py` + network script.

**Post-import fix worth remembering:** an LLD CPU prototype collided with the scalar slot-1 CPU key on `memory.discovery`. That is the same class of key-collision problem called out in §A.5 — it is real, and it bites within one import.

## 7. Open questions

- [x] ~~Does VOSS `name` populate `ifAlias` or `ifDescr`?~~ **Answered — `ifAlias`.** `name USW-ID01` → `ifAlias.192 = "USW-ID01"`. `rcPortName` stays empty; do not use it.
- [x] ~~VOSS device-health OIDs~~ **Answered** — see §3. `rcKhiSlot*` for CPU/memory, not `rcSysCpuUtil` / `rcSysDram*`.
- [ ] **Hardware canary still required.** The lab is a *virtual* Fabric Engine, so these were absent or unrepresentative: fan table (`rcChasFan*`), optics, LLDP peers, cards, ISIS/MLT tables, IST scalar, and temperature (reads 0 °C). Re-run on a physical 5520 before trusting fan/temp/PSU triggers.
- [ ] `hrSystemUptime` absent — decide whether to accept the 497-day `sysUpTime` wrap or suppress the restart trigger on VOSS.

## 8. Done when

- [ ] Pilot **hardware** VSP: health + labelled ports discovered
- [ ] Fan and temperature confirmed on physical hardware, not the VM
- [ ] Network Generic removed, no icmpping collision
- [ ] Same trigger set and severities as EXOS

---

# §C Routing — OSPF

> **Status: nice-to-have. Not a migration blocker.**
> The LogicMonitor cutover does not depend on this. The template exists and is imported, but it stays **disabled** until the platform work in §A/§B is quiet and the two canaries below are answered. Do not let it consume migration time.

Applies to **both platforms**. OSPF-MIB is standard (`1.3.6.1.2.1.14`), so one template covers EXOS and VOSS. Linked on the **Core / Dist device roles**, not on platform.

## 1. Scope

In:  OSPF adjacency health on core/dist switches
Out: firewall-side routing (03), Cato overlay (04), WAN circuits (05), route-policy correctness (cfgit's job)

OSPF is load-bearing — it routes traffic to the firewalls and the datacenter — so when this *is* enabled it is an outage-class signal. But LogicMonitor is presumably not watching it today either, so deferring it does not make the migration a regression.

## 2. What we want to know

- Did we silently lose a routing path to the firewalls or the datacenter?
- Is a neighbour *supposed* to be there but isn't — and would we ever notice?
- Is a link physically up but not carrying routes? (MTU mismatch, area/auth/timer mismatch after a config change, wedged process)
- Are we running on the last remaining adjacency without knowing it?
- Did someone disable OSPF on an interface or globally by mistake?

### What we deliberately do NOT want

- A second alert for every cable pull that link-down already reported.
- Alerts on normal DR/BDR election transitions.
- Per-neighbour alerts that vanish when the neighbour vanishes.

## 3. Data path

Same SNMP session as §A/§B. One `walk[]` master item, everything else dependent — no extra polling.

| Source | Protocol | Interval |
|---|---|---|
| Core / dist switch | SNMP, OSPF-MIB `1.3.6.1.2.1.14` | 1m |

## 4. Signals

| # | Question from §2 | Signal | OID |
|---|---|---|---|
| 1 | how many adjacencies are healthy? | `ospfNbrState` | `1.3.6.1.2.1.14.10.1.6` |
| 2 | which neighbour, for diagnosis | `ospfNbrIpAddr`, `ospfNbrRtrId` | `…14.10.1.1`, `…14.10.1.3` |
| 3 | is OSPF enabled at all? | `ospfAdminStat` | `1.3.6.1.2.1.14.1.2` |
| 4 | is OSPF enabled on the interface? | `ospfIfState` | `1.3.6.1.2.1.14.7.1.12` |

`ospfNbrState` values: `1` down, `2` attempt, `3` init, `4` twoWay, `5` exchangeStart, `6` exchange, `7` loading, **`8` full**.

## 5. Discovery — count for alerting, LLD for diagnosis

**Per-neighbour LLD cannot detect a missing neighbour.** If a neighbour goes away and stays away, it stops being discovered, its item is removed, and the trigger clears. The permanent failure looks like health. Same trap as opt-in access ports, but worse — here the missing thing *is* the fault.

So:

| Purpose | Type | Alerts? |
|---|---|---|
| Count of adjacencies in `full` | **scalar** dependent item | **yes** — this is the alert |
| Per-neighbour state / IP / router ID | LLD from the same master walk | **no** — diagnosis only |

```
master item:  walk[1.3.6.1.2.1.14.10.1.6,1.3.6.1.2.1.14.10.1.1,1.3.6.1.2.1.14.10.1.3]
dependent:    ospf.nbr.full.count     JS preprocessing, counts state = 8
LLD:          ospf.nbr.discovery      from the same master, items only
```

`{$OSPF.NBR.MIN}` is **per device** — an MLAG pair and a single core have different expected counts. Assign it from NetBox topology via nbxsync, or baseline it once and review.

## 6. Triggers

| Sev | Condition | Settle | Meaning |
|---|---|---|---|
| **High** | `min(ospf.nbr.full.count, 5m) = 0` | 5m | L3 isolated — no path to firewalls or DC |
| Warning | `min(ospf.nbr.full.count, 5m) < {$OSPF.NBR.MIN}` | 5m | redundancy lost, still routing |
| **High** | `last(ospfAdminStat) <> 1` | 5m | OSPF disabled globally |
| — | per-neighbour state | — | no triggers, diagnosis only |

### Dependency

```
ospf adjacency → depends on → no SNMP data → unavailable by ICMP
```

**Deliberately not dependent on link-down.** A count-based trigger cannot depend on a specific port's link-down prototype, and the pair is diagnostic:

| What fires | Diagnosis |
|---|---|
| link-down **and** OSPF | physical — cable, optic, far-end down |
| OSPF **without** link-down | **protocol or config** — MTU, area, auth, timers, wedged process |

The second row is the whole reason this section exists. Nothing else in the design catches it.

### Known false positives

| Source | Handling |
|---|---|
| DR/BDR election transitions | 5m settle absorbs them |
| **Broadcast segments with >2 routers** | non-DR/BDR pairs correctly sit in **twoWay**, not full. Counting only `full` would under-count permanently. Core links are usually p2p or /30 with two routers — **verify before setting `{$OSPF.NBR.MIN}`**, or count `full + twoWay` |
| Planned reboots / upgrades | maintenance window |

## 7. Complementary check — measure the impact, not just the protocol

Adjacency count is the *cause*. The *impact* is "can this site still reach the DC". Cheapest version: a synthetic `icmpping` from the site's Zabbix proxy to a known DC-side target. That tests the actual forwarding path rather than the routing protocol, and catches failures OSPF is healthy through.

Site-level, not per-switch. Belongs with the proxy-per-site work.

## 8. Template

Name:      `Extreme Routing by SNMP` — **build**
Assigned:  **Core / Dist device roles** (not platform — OSPF-MIB is standard)
Macros:    `{$OSPF.NBR.MIN}` per device

This is a legitimate second use of role: **platform → platform template, role → capability templates + macros.** Template inheritance is additive, so a VOSS core gets `Extreme VOSS by SNMP` (platform) plus `Extreme Routing by SNMP` (role).

## 9. Rollout

**Post-migration.** Enable only after §A/§B are live and quiet, and after the two canaries in §10 are answered. Items may be collected earlier (harmless, builds baseline) — **triggers stay disabled**.

## 10. Open questions

- [ ] **Does `ospfNbrTable` populate on our EXOS and VOSS versions?** Standard-MIB support varies, and an unsupported item fails silently. Canary before anything else
- [ ] Are core adjacencies p2p, or broadcast segments with >2 routers? Decides whether to count `full` or `full + twoWay`
- [ ] `{$OSPF.NBR.MIN}` per device — from NetBox topology, or baselined?
- [ ] Is losing *one* adjacency actually user-impacting at each site, or is it always redundant? Decides Warning vs High
- [ ] DC-side synthetic target for the impact check (§7)

## 11. Done when

- [ ] `ospfNbrTable` confirmed populated on both platforms
- [ ] Adjacency count alerts on a deliberately shut OSPF interface, and **clears** when restored
- [ ] A simulated MTU mismatch produces an OSPF alert with **no** link-down alert
- [ ] A cable pull produces both, and they are recognisably one incident
- [ ] Per-neighbour items exist for diagnosis and produce no alerts
