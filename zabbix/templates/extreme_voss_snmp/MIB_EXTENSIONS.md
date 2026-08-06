# Extreme VOSS by SNMP ΓÇö MIB extensions

Must-have and should-have items from the VOSS MIB backlog are **implemented**
in `template_net_extreme_voss_snmp.yaml` (Zabbix 7.0).

OID base: `1.3.6.1.4.1.2272.1` unless noted.

## Implemented ΓÇö must-have

| Feature | Keys / LLD | OID hint | Lab VOSS-VM |
|---|---|---|---|
| CPU/mem averages | `system.cpu.util.avg1/avg5`, `vm.memory.util.avg5` (+ LLD mem 5m) | `85.10.1.1.{23,3,9}` | PASS (5m CPU=70, mem=69; 1m CPU=0) |
| Optics / DOM LLD | `optic.discovery` — DDM-only; temp/TX/RX (dBm)+status/bias | `71.1.1.*` | empty on VM; **physical canary** see `OPTIC_POWER_CANARY.md` |
| LLDP neighbors | `lldp.discovery` ΓÇö sysname/port/chassis/desc | `1.0.8802.1.1.2.1.4.1.1.*` | needs peers |
| PSU detail | `psu.detail.discovery` ΓÇö status/SN/PN/watts | `4.8.2.1.*` | PASS (ids 1ΓÇô2) |
| Chassis extras | slots/ports/PN/brand/base MAC | `4.{4,5,66,68}`, `100.1.5` | PASS (27 ports, PN DSGDPM624, brand Extreme Networks.) |
| Total / redundant power | `sensor.power.total/redundant` | `1.{116,117}` | PASS (2200 / 1100 W) |

## Implemented ΓÇö should-have

| Feature | Keys / LLD | OID hint | Lab VOSS-VM |
|---|---|---|---|
| Card/slot LLD | `card.discovery` | `4.9.1.1.*` | empty (fixed VM) |
| V-IST | status/peer/VLAN (+ optional trigger via `{$VIST.CONTROL}`) | `211.{1,2,3}` | status=down(2) unused |
| IST | status/peer (+ `{$IST.CONTROL}`) | `17.{4,5}` | status OID absent on VM |
| SPBM enable | `fabric.plsb.enable` | `78.1.2` | enable(1) |
| ISIS circuits | `isis.circuit.discovery` | `63.2.1.*` | empty / absent |
| ISIS adjacency | `isis.adj.discovery` | `63.10.1.*` | empty |
| SPBM nickname | `spbm.node.discovery` | `63.4.1.*` | empty until SPBM peers |
| MLT/SMLT | `mlt.discovery` | `17.10.1.*` | empty |
| Port flap / shutdown | IF LLD prototypes | `4.10.1.1.{21,114}` | PASS on ifIndex 192 |
| SNMP traps | fan/PSU/overheat/CPU/ISIS adj/LAG | `snmptrap["rcnΓÇª"]` | needs trap config |

## Control macros (destination)

| Macro | Default | Meaning |
|---|---|---|
| `{$VIST.CONTROL}` | `0` | Set host `1` on VOSS fabric pairs (V-IST HA) |
| `{$IST.CONTROL}` | `0` | Classic IST unused on FE — keep off |
| `{$OPTIC.TEMP.CRIT}` | `70` | Optic °C **value** trigger (prefer DOM status) |
| `{$OPTIC.TEMP.MAX}` | `150` | Ignore garbage DOM above this |
| `{$OPTIC.RX.DBM.MIN}` | `-25` | Secondary RX dBm floor; prefer DOM status |
| `{$OPTIC.RX.DBM.FLOOR}` | `-39` | Ignore synthetic −40 (zero reading) |
| `{$OPTIC.DOM.ALARM_HIGH}` / `LOW` | `3` / `5` | Vendor DOM highAlarm / lowAlarm |
| `{$MLT.CONTROL}` | `1` | Gate MLT agg-down; trigger also requires `.diff()` |
| `{$TEMP_WARN}` / `{$TEMP_CRIT}` | `90` / `100` | Chassis °C destination |
| `{$IF.FLAP.WARN}` | `0` | Flap change threshold (context) |

Temporary LM silence (`TEMP`/`OPTIC` = 999, `MLT.CONTROL` = 0) is an optional script overlay (`--cutover-silence`), not the template default.

### Optic power units (verified)

MIB documents µW. Physical FE 9.3 returns **negative millidBm**. Template JS normalizes to **dBm**; alerts prefer `rcPlugOptMod*Status`. Details: `OPTIC_POWER_CANARY.md`.

## Still nice-to-have (not in template)

VLAN/I-SID/VRF inventory, Auto-sense/FA, buffer/NVRAM, license trial, QSFP lane DOM.

## Generator

`extend_template.py` regenerates these blocks from a clean baseline if needed.
