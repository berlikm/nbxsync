# VOSS optic DOM canary (physical FE 9.3)

**Hosts:** `CH-STA-L26-L02-CORE01`, `CH-STA-L50-L01-CORE01` (5520 FabricEngine 9.3)  
**Dates:** 2026-08-06

## Which MIB?

| MIB | Enterprise | Optics? |
|---|---|---|
| **RC-POM-MIB** / RAPID-CITY `rcPlugOptMod*` | `2272.1.71` | **Yes** — VOSS/FE DOM |
| [EXTREME-BASE-MIB](https://github.com/librenms/librenms/blob/master/mibs/extreme/EXTREME-BASE-MIB) | `1916` (EXOS product tree) | **No** — sysObjectID / product registry only |
| LibreNMS VOSS sensors | chassis temp only | Does **not** poll `rcPlugOptModTemperature` |

Official Extreme article: OID for pluggable optics = `rcPlugOptModTable` (`2272.1.71.1`) — [000107132](https://extreme-networks.my.site.com/ExtrArticleDetail?an=000107132).

## Power — `rcPlugOptMod{Rx,Tx}Power`

### MIB (RC-POM)

Positive INTEGER in **microwatts**, 0 … 65535 µW (−40 … +18.16 dBm).

### Observed FE 9.3

| Source | Value | Notes |
|---|---|---|
| SNMP (earlier canary) | −17000 → **−17.0 dBm** | millidBm |
| SNMP | 0 → synthetic **−40 dBm** | DAC / no light |
| CLI `1/1` ACTUAL | Tx **−2.4** / Rx **−2.4** dBm | SR optic, Normal |
| CLI `1/2` ACTUAL | Tx **−2.1** / Rx **−1.9** dBm | SR optic, Normal |

### Template JS

`v<0 → v/1000`, `v==0 → -40`, `v>0 → 10*log10(v/1000)`.  
**No RX dBm value trigger** — dark/unused DDM ports sit in (−39,−25) and flood; alert via `RxPowerStatus` only.  
LLD: `SupportsDDM` `^1$`. Lost resources: disable immediately, delete after 7d.

## Temperature — `rcPlugOptModTemperature`

### MIB text (RC-POM / RAPID-CITY)

Claims SFF-8472 **1/256 °C** (MSB integer, LSB fraction) and also mentions **0.0001** accuracy.

### CLI ground truth (L50-L01-CORE01)

| Port | CLI ACTUAL Temp(C) | Implied SNMP (`×10000`) | `/256` (wrong) | `/65536` (wrong) |
|---|---|---|---|---|
| 1/1 | **29.6757** | 296757 | ≈1159 °C | ≈4.53 °C |
| 1/2 | **37.0429** | 370429 | ≈1447 °C | ≈5.65 °C |

These match the earlier Zabbix Latest-data failure modes exactly (`~1160–1960 °C` with `/256`, `~4.5–7.7 °C` with `/65536`).

### Conclusion / template JS

**FE 9.3 implements `raw / 10000` → °C** (four decimal places), not MIB SFF `/256`.

```
c = trunc(raw) / 10000
```

Prefer **`TemperatureStatus`** for paging; value trigger is secondary (`{$OPTIC.TEMP.CRIT}=70`).

## Bias

MIB: **0.1 µA** (`×0.1` → µA). CLI shows **mA** (e.g. 5.9880 mA = 5988 µA) — leave multiplier unless SNMP raw disagrees.

## Import note

MLT agg-down trigger must use `last(#1)<>last(#2)` — Zabbix 7 rejects history function `diff()`.
