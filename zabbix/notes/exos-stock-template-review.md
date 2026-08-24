# Stock EXOS template review

Source: `git.zabbix.com` → `templates/net/extreme_snmp/template_net_extreme_snmp.yaml`
**Use the release/7.0 branch** — master requires Zabbix 8.0 and uses `get[OID]`/`walk[OID]` polling.

Verdict: keep almost everything. Cut two triggers, silence one, re-filter one LLD, build one small template.

## Keep

| Content | Note |
|---|---|
| ICMP ping / loss / response + triggers | only source of icmpping on the host |
| SNMP agent availability, No SNMP data collection | |
| CPU utilization + High CPU trigger | `{$CPU.UTIL.CRIT}`=90 |
| Memory Discovery + High memory utilization | `{$MEMORY.UTIL.MAX}`=90 |
| Temperature value + status, 3 triggers | stock warn 55 / crit 65 — **override**: G2+ internal sensor Normal to ~100 °C (GTAC 000088439); use warn 90 / crit 100 + overTemp status |
| PSU Discovery + critical trigger | |
| FAN Discovery + status/speed + critical trigger | |
| Hardware model / serial / firmware / HW version / OS | free inventory |
| Uptime network + hardware, Host has been restarted | |
| Device has been replaced (serial changed) | INFO, useful |
| Firmware changed, OS description changed | INFO |
| System location / contact / objectID items | items only, no triggers |
| Network interfaces discovery | re-filter, see below |
| Bits in/out, errors, discards, ifType, Speed | |
| High error rate trigger | raise `{$IF.ERRORS.WARN}` — stock 2 pkt/s is aggressive |
| Ethernet changed to lower speed | **this is our change-detect safety net, already built** |
| EtherLike-MIB Discovery + half-duplex trigger | cheap, real failure |
| Link down trigger | keep; ignore its `{$IFCONTROL:"{#IFNAME}"}` kill switch, our `X`/`N` is the SoT |

## Cut

| Content | Why |
|---|---|
| System name has changed (trigger) | noise, cfgit covers config drift |
| SNMP traps (fallback) item | we do not receive traps |

## Silence (not cut)

| Content | How |
|---|---|
| High bandwidth usage | set `{$IF.UTIL.MAX}` = `101` → threshold unreachable, no template edit. **Permanently silenced** — it is keyed on `{#IFNAME}` not port class, and its 15m window trips on nightly backups. Replaced by a class-keyed 1h-average trigger plus a discards trigger in the thin template (see 01 §6.4) |

## Re-filter

Interface LLD scoping is **macro-only**, no template edit:

| Role | Macro | Value |
|---|---|---|
| Fabric / hybrid | `{$NET.IF.IFALIAS.NOT_MATCHES}` | `^(X\|N)(-\|$)` |
| Access | `{$NET.IF.IFALIAS.MATCHES}` | `^(USW\|US\|UP\|MON\|UW\|TMON)(-\|$)` |

## Build — the only real work

Stock cannot derive an expected speed from the label.

New thin template `Extreme Port Speed Expect by SNMP`:

1. Own `net.if.discovery` LLD, filtered to `{$NET.IF.IFALIAS.MATCHES}` = `^(USW|US|MON|UP)(-|$)`.
   `UW`, `TMON`, `X`, `N` are never discovered here, so their exemptions are free.
2. JS preprocessing on the LLD parses `{#IFALIAS}` → `{#IF.CLASS}`, `{#IF.SPEED.TOKEN}`, `{#IF.ID}`, `{#IF.SPEED.EXPECTED}`.
3. Item prototype = **dependent item** on the stock master `net.if.speed[ifHighSpeed.{#SNMPINDEX}]` — no extra SNMP polling.
4. One trigger prototype:
   ```
   min(/…/<dependent>,5m) <> {#IF.SPEED.EXPECTED}
   and min(/…/net.if.status[ifOperStatus.{#SNMPINDEX}],5m)=1
   ```

Two templates on the host, stock never cloned, upgrade path intact.

## Gotchas

1. **Speed is stored in bps**, not Mbps — stock applies a custom multiplier of 1000000. `{#IF.SPEED.EXPECTED}` for 10G is `10000000000`.
2. Same item has *discard unchanged with heartbeat 1h* — values only land on change or hourly. **Do not use `min(speed,5m)`** in a trigger; the window is often empty and the trigger goes *unknown*. Use `last(speed)` with the settle on `min(ifOperStatus,5m)=1`.
3. Master branch needs Zabbix 8.0. We are on 7.
4. Stock speed-drop trigger has **no settle time** and manual close.
5. **The stock speed-drop trigger has a hole.** Its `last(speed)>0` guard correctly stops it firing when a port goes down (speed reads 0) — but that means `10G → down(0) → up at 1G` never fires. Almost every real degrade involves a link bounce, so this trigger catches far less than it appears to. That is the real justification for the absolute-expect trigger.
6. **Item key collision.** Keys must be unique per host. The new speed-expect template must not reuse `net.if.discovery` or the stock prototype keys, or linking both templates to one host fails at import. Use `net.if.speedexpect.discovery` / `net.if.speed.expect[{#SNMPINDEX}]`.
7. **CRC is on the Observability companion**, not stock. Stock EtherLike LLD still polls **only duplex**. `dot3StatsFCSErrors` / alignment / symbol live on `net.if.fcs.discovery`. Faulty-link canary still needed to prove the OID moves.
8. **VLAN interfaces are discovered.** EXOS presents VLANs in IF-MIB with no `ifAlias`, so the fabric rule (`NOT_MATCHES ^(X|N)`) picks them up. Filter with `{$NET.IF.IFTYPE.MATCHES}` = `^(6|161)$`.
9. **LAG aggregates report summed speed.** `^6$` on the speed-expect template only — physical ports get the speed expectation, aggregates keep link-down/errors from the stock template.

## LLD rule settings (not macros — set on the rule)

| Setting | Value | Why |
|---|---|---|
| Update interval | 15m during rollout, 1h after | a label change is invisible until the next discovery |
| Keep lost resources period | **0** | otherwise relabelling a port to `X` keeps alerting for 7–30 days, and ops concludes the exclude mechanism is broken |

## Template modification policy

**Do not modify or clone the stock template.** Everything above is either a macro override at host-group level or a setting on the LLD rule. That keeps the upgrade path intact and makes every silencing decision reversible in one edit.

The only new artefact is the thin `Extreme Port Speed Expect by SNMP` template, which stock cannot provide. CRC/FCS items live on **Extreme EXOS Observability** (`net.if.fcs.discovery`), not Speed Expect and not a stock YAML fork.

Keep macro overrides at **host group** level — a template re-import can clobber template-level values.
