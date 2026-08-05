# Extreme VOSS by SNMP

Zabbix **7.0** template for Extreme VOSS / Fabric Engine devices, modeled on the official
[Extreme EXOS by SNMP](https://git.zabbix.com/projects/ZBX/repos/zabbix/browse/templates/net/extreme_snmp)
template with OIDs remapped to RAPID-CITY (`enterprises.2272`).

## Import

1. Zabbix → Data collection → Templates → Import
2. Select `template_net_extreme_voss_snmp.yaml`
3. Link to a host with SNMPv2c/v3 credentials

Requires Zabbix **7.0+** (export version `7.0`).

## What differs from Extreme EXOS

| Area | EXOS | VOSS |
|---|---|---|
| CPU / memory | `extremeCpuMonitor*` / `extremeMemoryMonitor*` | `rcKhiSlot*` LLD (per slot); scalar CPU for slot 1 |
| Temperature | Scalar `extremeCurrentTemperature` | `rcVossSystemTemperature*` LLD |
| Fan | Status + RPM | Status + ambient °C (no RPM OID) |
| PSU / fan crit values | EXOS enums | `{$FAN_CRIT_STATUS}=3`, `{$PSU_CRIT_STATUS}=4` |
| Chassis identity | ENTITY-MIB index 1 | `rcChasSerialNumber` / `rcChasModelName` / `rcChasHardwareRevision` |
| Software rev | Extreme software MIB | `rcSysVersion` |

**Do not use** `rcSysCpuUtil` / `rcSysDram*` — MIB marks them unsupported on VOSS.

See [OID_MAPPING.md](OID_MAPPING.md), [MIB_EXTENSIONS.md](MIB_EXTENSIONS.md), and [TEST_CHECKLIST.md](TEST_CHECKLIST.md).

## Macros (VOSS-specific defaults)

| Macro | Default | Meaning |
|---|---|---|
| `{$FAN_CRIT_STATUS}` | `3` | `rcChasFanOperStatus` down |
| `{$PSU_CRIT_STATUS}` | `4` | `rcChasPowerSupplyOperStatus` down |
| `{$TEMP_CRIT_STATUS}` | `3` | `rcVossSystemTemperatureStatus` highCritial |
| `{$CPU.UTIL.CRIT}` | (from EXOS base) | Slot CPU util % |
| `{$MEMORY.UTIL.MAX}` | (from EXOS base) | Slot memory util % |
| `{$TEMP_CRIT}` / `{$TEMP_WARN}` | 65 / **999** | Critical kept; warning tier silenced (design §A.8) |
| `{$TEMP_CRIT_LOW}` | **-273** | Silence stack/VM 0°C false positive |
| `{$IF.UTIL.MAX}` | **101** | Stock bandwidth trigger off; capacity → Port Speed Expect |
| `{$NET.IF.IFTYPE.MATCHES}` | `^(6\|161)$` | Physical + LAG only |

Role IFALIAS macros (`.*` + `^X(-|$)` for core, opt-in for access) are assigned via **nbxsync**, not baked into this template. Interface LLD defaults to **15m** / keep-lost **0** during rollout.

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

See `docs/port-identity-foundation.md` and `docs/extreme-switching-zabbix.md` §B.

## Compatibility notes (Zabbix 7.0)

Export is Zabbix **7.0** (tested import on 7.0.29). Relative to the EXOS 8.0 source template, this file omits `vendor`, macro `config` UI metadata, and discovery-rule `tags` so it imports cleanly on 7.0.

## Live verification

Lab results against Virtual VOSS 9.3.1.0: see [LAB_RESULTS.md](LAB_RESULTS.md).

Notable VM gaps (template still correct for hardware): fan table absent; temperature values stay `0`; `hrSystemUptime` unsupported. Port identity: CLI `name` populates **ifAlias** (prefer over `rcPortName`).
