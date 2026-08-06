# VOSS optic DOM canary (physical FE 9.3)

**Host:** `CH-STA-L26-L02-CORE01` (5520-24X-FabricEngine 9.3.1.0)  
**Dates:** 2026-08-06

## Which MIB?

| MIB | Enterprise | Optics? |
|---|---|---|
| **RC-POM-MIB** / RAPID-CITY `rcPlugOptMod*` | `2272.1.71` | **Yes** — VOSS/FE DOM |
| [EXTREME-BASE-MIB](https://github.com/librenms/librenms/blob/master/mibs/extreme/EXTREME-BASE-MIB) | `1916` (EXOS product tree) | **No** — sysObjectID / product registry only |
| LibreNMS `os_discovery/voss.yaml` | chassis temp only | Does **not** poll `rcPlugOptModTemperature` |

Official Extreme article: OID for pluggable optics = `rcPlugOptModTable` (`2272.1.71.1`) — [000107132](https://extreme-networks.my.site.com/ExtrArticleDetail?an=000107132).

## Power — `rcPlugOptMod{Rx,Tx}Power`

### MIB (RC-POM)

Positive INTEGER in **microwatts**, 0 … 65535 µW (−40 … +18.16 dBm).

### Observed FE 9.3

| ifIndex | Raw SNMP | MillidBm (`v/1000`) | Notes |
|---|---|---|---|
| 192 | −17000 | **−17.0 dBm** | |
| 258 | −97000 | **−97.0 dBm** | no light |
| DAC / no light | 0 | synthetic **−40 dBm** | |

Negative millidBm matches budgets; `|raw|` as µW does not.

### Template JS

`v<0 → v/1000`, `v==0 → -40`, `v>0 → 10*log10(v/1000)`. Prefer DOM `*Status` alerts.  
LLD: `SupportsDDM` `^1$`, `lifetime: 0`.

## Temperature — `rcPlugOptModTemperature`

### MIB (RC-POM)

> expressed in units of **1/256 of a degree Celsius** … The **most significant byte** is the signed integer part … **least significant byte** is the fraction.

That is SFF-8472 fixed-point on a 16-bit word: `int16(raw) / 256`.

### Observed FE 9.3 (Latest data)

Values ~**1160–1960 °C** were shown while a `/256` multiplier was on the item — i.e. SNMP INTEGER width × `/256` ≈ 1300 °C (bogus).

| Interpretation of SNMP INTEGER | Result on canary set |
|---|---|
| Fits in 16 bits → SFF `int16/256` | ~4.5–7.7 °C (consistent) |
| Wider than 16 bits → `/65536` | ~4.5–7.7 °C (consistent) |
| Plain full-int `/256` | ~1300 °C (reject) |

Template JS: if `|raw| ≤ 0xFFFF` use SFF `/256`, else `/65536`. Prefer **`TemperatureStatus`** for paging.

**Still confirm with CLI** on the same ports (`show pluggable-optical-modules detail` or equivalent). If CLI shows ~40 °C not ~5 °C, revisit.

## Bias

MIB: **0.1 µA**. Leave `×0.1` unless CLI disagrees.

## Import note

MLT agg-down trigger must use `last(#1)<>last(#2)` — Zabbix 7 rejects history function `diff()`.
