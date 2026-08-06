# Port identity — Zabbix LLD & triggers

How Zabbix applies the port label grammar from `docs/port-identity-foundation.md`.  
Full monitoring design (signals, stages, capacity, OSPF): `docs/extreme-switching-zabbix.md`.

Label vocabulary and examples stay in the baseline; this doc is discovery and alerting behavior.

---

## 1. Resolution

```
1) Parse class from ifAlias (empty / unparseable / N → monitoring-neutral)
2) Class X → excluded from stock IFALIAS filter (core NOT_MATCHES)
3) Else include per role LLD macros (§2)
4) Discovered + {USW,US,UP,MON,UW} → link-down / flap / errors (platform template)
5) Discovered by speed-expect LLD + {USW,US,UP,MON} → expected speed from token or class default;
      last(speed) <> expected while oper-up ≥5m → WARNING
6) Capacity (stage 6): USW util 1h avg vs intended speed; outbound discards
7) TMON → items + optional link-down INFO only (no speed / util WARN)
```

Turn on step 5 after labels for that site follow the grammar. Capacity is stage 6.

---

## 2. Role × LLD

Stock `net.if.discovery` is **unmodified**. Scoping is host macros from nbxsync (role beats platform). **Set both IFALIAS macros on every role.**

| NetBox role | `{$NET.IF.IFALIAS.MATCHES}` | `{$NET.IF.IFALIAS.NOT_MATCHES}` | No label / `N` / legacy |
|---|---|---|---|
| **Core / Dist / Mgmt** | `.*` | `^X(-\|$)` | **monitored** |
| **Access** | `^(USW\|US\|UP\|MON\|UW\|TMON)(-\|$)` | `CHANGE_IF_NEEDED` | not monitored |
| **Hybrid** | Access values until stage 5, then Core | | flips at stage 5 |
| All | `{$NET.IF.IFTYPE.MATCHES}` = `^(6\|161)$` | | physical + LAG only |

### `X` excludes, `N` does not

| Label | Core | Access |
|---|---|---|
| class label | monitored | monitored |
| `N` / `N-<text>` | **monitored** | not monitored |
| no label / unparseable | monitored | not monitored |
| `X` / `X-<note>` | excluded | not monitored |

Unused ports → **admin-down** (not discovered). Reserve `X` for up ports that must not alert.

### Speed-expect LLD (own macros — do not reuse `{$NET.IF.*}`)

```
{$PORTID.LLD.IFALIAS.MATCHES} = ^(USW|US|UP|MON)(-|$)
{$PORTID.LLD.IFTYPE.MATCHES}  = ^6$
```

Template: `Extreme Port Speed Expect by SNMP` (`templates/zabbix/net/extreme_port_speed_expect_snmp/`).

### LLD settings

| Setting | Value |
|---|---|
| Update interval | **15m** during rollout, 1h after |
| Keep lost resources | **0** |

### Hybrid

Start in **access / opt-in** mode so unlabelled desk ports do not alert. After `X`-fill and admin-down hygiene, flip role macros to Core values (stage 5).

```
1) Spares / unused            → admin-down
2) Up but uninteresting       → X / X-<note>   (not N)
3) Monitor / temp             → USW / US / UP / MON / UW / TMON
```

---

## 3. Global destination macros (thresholds)

```
{$IF.UTIL.MAX}     = 101     # stock util% off until stage 6
{$TEMP_WARN}       = 90      # destination (NOT stock 55)
{$TEMP_CRIT}       = 100     # destination (NOT stock 65)
{$TEMP_CRIT_LOW}   = -273    # silence stack / VM 0°C false positive
```

Temporary LM silence (`TEMP_*=999`) is optional `--cutover-silence` only — not the target. Do **not** use `{$IFCONTROL:"{#IFNAME}"}` — `X` is the single mute source of truth.

---

## 4. Ops reminders

- EXOS: grammar in **`display-string`**, max **20**; leave **`description-string` empty**.
- VOSS: grammar in interface **`name`** → `ifAlias` (lab-proven).
- Relabel to `X` takes effect at the **next discovery cycle**.
- Core unlabelled admin-up: link-down only if the port **was up then went down** (`.diff()`).
