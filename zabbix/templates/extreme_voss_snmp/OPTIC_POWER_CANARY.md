# VOSS optic power unit canary (physical FE 9.3)

**Host:** `CH-STA-L26-L02-CORE01` (5520-24X-FabricEngine 9.3.1.0)  
**Date:** 2026-08-06  
**OID:** `rcPlugOptModRxPower` / `rcPlugOptModTxPower` (`1.3.6.1.4.1.2272.1.71.1.1.{37,32}`)

## What the MIB says

Positive INTEGER in **microwatts**, range 0 … 65535 µW (−40 … +18.16 dBm).

## What the box returns

| ifIndex | Raw SNMP (Zabbix lastvalue) | If µW (MIB) | If millidBm (`v/1000`) |
|---|---|---|---|
| 192 | −17000 | invalid (negative) | **−17.0 dBm** ≈ 20 µW |
| 193 | −1000 | invalid | **−1.0 dBm** ≈ 794 µW |
| 194 | −29000 | invalid | **−29.0 dBm** ≈ 1.3 µW |
| 210 | −31000 | invalid | **−31.0 dBm** ≈ 0.8 µW |
| 258 | −97000 | invalid | **−97.0 dBm** (no light) |
| 195 / 198 | 0 | DAC / no optical power | synthetic −40 dBm in template |

Taking `|raw|` as µW yields +12 … +19 dBm RX — physically wrong for these SR/LR links.  
MillidBm matches normal optical budgets.

## Template decision

1. **JS preprocess** TX/RX → **dBm**: `v<0 → v/1000`, `v>0 → 10*log10(v/1000)`, `v==0 → -40`.
2. **Prefer vendor DOM status** OIDs for alerts (`rcPlugOptMod{Rx,Tx}PowerStatus`, `TemperatureStatus`) — thresholds are optic-native.
3. **LLD filter** `SupportsDDM=true(1)` — drop DAC/copper without DDM.
4. Secondary RX dBm floor macro stays cutover-safe (`{$OPTIC.RX.DBM.MIN}=-100`).

## Temperature

`rcPlugOptModTemperature` is **1/256 °C** (MIB + SFF-style). Multiplier `0.00390625` is correct. First-light mass alerts were from absolute CRIT without status gating / cutover silence — not from a wrong scale.
