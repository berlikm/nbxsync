# Extreme VOSS by SNMP — MIB extension recommendations

The current template is an **EXOS-parity baseline** (health + IF-MIB + inventory),
verified on Virtual Fabric Engine 9.3.1.0. It is **not** a full VOSS/Fabric ops
template yet. Below is a MIB-driven backlog (`docs/VOSS-5520.9.3.1.0_mib.txt`,
`enterprises.2272`) prioritized for nbxsync / network monitoring.

OID base unless noted: `1.3.6.1.4.1.2272.1`.

## What we already have (baseline)

- ICMP / SNMP availability
- Inventory: `rcSysVersion`, `rcChasModelName/Serial/HardwareRevision`, sys*
- CPU (slot 1 scalar) + memory LLD via `rcKhiSlot*`
- Fan / PSU / temperature LLD
- IF-MIB + EtherLike duplex; port identity via **ifAlias**
- VOSS-specific crit macros for fan/PSU/temp enums

## Must-have next (ops + NetBox)

| Feature | MIB objects | Path hint | Live VOSS-VM | Why |
|---|---|---|---|---|
| **CPU/mem averages** | `rcKhiSlotCpu5MinAve`, `Cpu1MinAve`, `Mem5MinAve` | `85.10.1.1.{3,23,9}.{slot}` | 1m CPU=0 (TCG idle?), mem 5m=69 **PASS** | Stable alerts vs instantaneous spikes |
| **Optics / DOM LLD** | `rcPlugOptMod*` Temperature/Bias/Tx/Rx + vendor/PN/SN | `71.1.1.{17,27,32,37,6,7,9}.{if}` | empty on VM (no optics) | Fiber health + NetBox optic inventory |
| **LLDP neighbors LLD** | `lldpRemSysName`, `RemPortId`, `RemChassisId`, `RemManAddr` | `1.0.8802.1.1.2.1.4…` | needs peer + slower poll | Topology / nbxsync neighbor sync |
| **PSU detail** | serial / part / output watts / oper | `4.8.2.1.{3,5,10,15}.{id}` | table **PASS** (serial empty on VM) | Richer inventory than status-only |
| **Chassis extras** | numPorts, partNumber, brandName | `4.5`, `4.66`, `4.68` | numPorts=27, PN=`DSGDPM624` **PASS** | Completes HW sync |

## Should-have (Fabric / HA)

| Feature | MIB objects | Path hint | Live VOSS-VM | Why |
|---|---|---|---|---|
| **Card/slot LLD** | `rcCardType/Serial/OperStatus/PartNumber` | `4.9.1.1.{2,3,6,8}.{slot}` | absent on fixed VM | Modular chassis inventory |
| **Total / redundant power** | `rcSysTotalPower`, `RedundantPower` | `1.116`, `1.117` | total=2200 **PASS** | Capacity planning |
| **V-IST / IST / SMLT** | session status, peer IP, MLT state | `211.*`, `17.*` | canary timed out / unused in lab | HA pair health |
| **ISIS/SPBM adjacency** | circuit oper, adj hostname, nickname | `rcIsis*` / `rcPlsb*` | not canaried | Fabric core ops |
| **Port flap / shutdown reason** | `rcPortNumStateTransition`, `rcPortShutdownReason` | `4.10.1.1.{21,114}` | needs retest | Explains link flaps |
| **Targeted SNMP traps** | fan/PSU/temp/ISIS adj/LAG | trap OIDs in MIB | — | Faster than poll-only |

## Nice-to-have

- VLAN / I-SID / VRF inventory (`rcVlan*`, `rcVrf*`) — high cardinality
- Auto-sense / Fabric Attach port state
- `rcSysBufferUtil`, NVRAM save time, license trial days left
- QSFP lane DOM (only if 40/100G optics deployed)
- Mgmt IP `rcSysIpAddr` for sync redundancy

## Skip

| Object | Reason |
|---|---|
| `rcSysCpuUtil` / `rcSysDram*` | MIB + lab: not supported / absent |
| `rcPortName` as primary label | Lab: empty while **ifAlias** works |
| Fan RPM | Not in `rcChasFan*` |
| Community template mem `.77/.78` | Mis-mapped OIDs |
| Full KHI process/pthread tables | Debug-only, huge cardinality |

## Suggested build order

1. KHI 1m/5m averages (already proven on lab)
2. Chassis partNumber / numPorts scalars
3. PSU detail LLD columns
4. Optics DOM LLD (needs real optics hardware)
5. LLDP rem LLD
6. V-IST/IST + ISIS adj (Fabric HA)
7. Trap items for fan/PSU/temp/ISIS

## Port identity (confirmed)

CLI `name USW-ID01` → `ifAlias` = `USW-ID01`. Prefer **ifAlias** for the
`CLASS[-SPEED]-ID` grammar; leave description empty.
