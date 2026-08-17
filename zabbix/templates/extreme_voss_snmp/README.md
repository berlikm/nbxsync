# Extreme VOSS by SNMP

Zabbix **7.0** template for Extreme VOSS / Fabric Engine devices, modeled on the official
[Extreme EXOS by SNMP](https://git.zabbix.com/projects/ZBX/repos/zabbix/browse/templates/net/extreme_snmp)
template with OIDs remapped to RAPID-CITY (`enterprises.2272`).

## Import

1. Zabbix ΓåÆ Data collection ΓåÆ Templates ΓåÆ Import
2. Select `template_net_extreme_voss_snmp.yaml`
3. Link to a host with SNMPv2c/v3 credentials

Requires Zabbix **7.0+** (export version `7.0`).

## What differs from Extreme EXOS

| Area | EXOS | VOSS |
|---|---|---|
| CPU / memory | `extremeCpuMonitor*` / `extremeMemoryMonitor*` | `rcKhiSlot*` LLD (per slot); scalar CPU for slot 1 |
| Temperature | Scalar `extremeCurrentTemperature` | `rcVossSystemTemperature*` LLD |
| Fan | Status + RPM | Status + ambient ┬░C (no RPM OID) |
| PSU / fan crit values | EXOS enums | `{$FAN_CRIT_STATUS}=3`, `{$PSU_CRIT_STATUS}=4` |
| Chassis identity | ENTITY-MIB index 1 | `rcChasSerialNumber` / `rcChasModelName` / `rcChasHardwareRevision` |
| Software rev | Extreme software MIB | `rcSysVersion` |

**Do not use** `rcSysCpuUtil` / `rcSysDram*` ΓÇö MIB marks them unsupported on VOSS.

See [OID_MAPPING.md](OID_MAPPING.md), [MIB_EXTENSIONS.md](MIB_EXTENSIONS.md), and [TEST_CHECKLIST.md](TEST_CHECKLIST.md).

## Macros (destination defaults)

| Macro | Default | Meaning |
|---|---|---|
| `{$FAN_CRIT_STATUS}` | `3` | `rcChasFanOperStatus` down |
| `{$PSU_CRIT_STATUS}` | `4` | `rcChasPowerSupplyOperStatus` down |
| `{$TEMP_CRIT_STATUS}` | `3` | `rcVossSystemTemperatureStatus` highCritial |
| `{$CPU.UTIL.CRIT}` | (from EXOS base) | Slot CPU util % |
| `{$MEMORY.UTIL.MAX}` | (from EXOS base) | Slot memory util % |
| `{$TEMP_WARN}` / `{$TEMP_CRIT}` | **95** / **100** | Chassis °C destination (not stock 55/65) |
| `{$TEMP_CRIT_LOW}` | **-273** | Silence stack/VM 0 °C false positive |
| `{$OPTIC.TEMP.CRIT}` / `{$OPTIC.TEMP.MAX}` | **70** / 150 | °C value trigger; clamp garbage |
| `{$OPTIC.RX.DBM.MIN}` / `FLOOR` | −100 / −39 | Legacy; RX alerts are DOM status only |
| `{$OPTIC.DOM.ALARM_*}` | 3 / 5 | Vendor DOM highAlarm / lowAlarm (primary) |
| `{$MLT.CONTROL}` | **1** | Agg-down on transition (`.diff()`); temporary silence = 0 |
| `{$VIST.CONTROL}` / `{$IST.CONTROL}` | **0** / **0** | Host `VIST=1` on fabric pairs; classic IST unused |
| `{$ISIS.CONTROL}` / `{$CARD.CONTROL}` | **0** / **0** | Fabric High gated until a canary |
| `{$UNSUPPORTED.MAX}` | **5** | Average ticket if unsupported items stay above this for 30m |
| `{$IF.UTIL.MAX}` | **101** | Stock bandwidth trigger off until stage 6 |
| `{$NET.IF.IFTYPE.MATCHES}` | `^(6\|161)$` | Physical + LAG only |

Role IFALIAS macros (`.*` + `^X(-|$)` for Core/Dist/Mgmt; Access `^(USW|UP)(-|$)`) are assigned on the Switch* role in NetBox, not baked into this template. Operator page: [`../../01-extreme-switching.md`](../../01-extreme-switching.md). Host dashboard **Health** (pages Overview / Hardware / Diagnostics) plus **Network interfaces** ships in this YAML — re-import updates in place (same dashboard uuid).

## Coverage

- ICMP availability + targeted SNMP traps (fan/PSU/temp/ISIS/LAG)
- Inventory: chassis model/serial/rev/PN/brand/base MAC, port/slot counts, `rcSysVersion`
- CPU/memory: instantaneous + 1m/5m averages (`rcKhiSlot*`)
- Fan / PSU (+ PSU detail) / temperature discovery
- Optics/DOM discovery (`rcPlugOptMod*`)
- LLDP remote neighbor discovery
- Fabric: V-IST / IST, SPBM enable, ISIS circuit/adjacency, SPBM nickname, MLT/SMLT
- Card/slot discovery
- IF-MIB (+ EtherLike duplex) including flap count & shutdown reason

## Port identity

CLI `name` populates SNMP **`ifAlias`** (lab canary PASS on VOSS 9.3.1.0). Prefer `ifAlias` for the shared `CLASS[-SPEED]-ID` grammar (fleet budget **20** chars). Do not rely on `rcPortName` (empty in canary).

See [port-identity.md](../../port-identity.md) and [01-extreme-switching.md](../../01-extreme-switching.md).

## Compatibility notes (Zabbix 7.0)

Export is Zabbix **7.0** (tested import on 7.0.29). Relative to the EXOS 8.0 source template, this file omits `vendor`, macro `config` UI metadata, and discovery-rule `tags` so it imports cleanly on 7.0.

## Live verification

Lab results against Virtual VOSS 9.3.1.0: see [LAB_RESULTS.md](LAB_RESULTS.md).

Notable VM gaps (template still correct for hardware): fan table absent; temperature values stay `0`; `hrSystemUptime` unsupported. Port identity: CLI `name` populates **ifAlias** (prefer over `rcPortName`).
