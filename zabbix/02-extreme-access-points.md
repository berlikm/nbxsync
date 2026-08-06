# Extreme access points — Zabbix monitoring

Status: template v1 + wiring    Owner:    Depends on: 01-extreme-switching.md (switch `UP-…` port only)

## 1. Scope

| In | Out |
|---|---|
| HiveOS / IQ Engine APs (ExtremeCloud IQ managed) | Switch port toward the AP (`UP-…` in 01) |
| Direct SNMPv3 to the AP | Wireless client experience / UX SLAs |
| Chassis health, radio health, aggregate client count | Full per-client inventory as v1 alerts |
| Optional traps later | Mesh/MRP deep dive (v2+) |
| XIQ API | Deferred — not required if SNMP works on eth |

**Host model:** one Zabbix host per AP (NetBox Device), not one host per XIQ tenant.

## 2. Data path — decision

| Source | Protocol | Credential | Role |
|---|---|---|---|
| AP (eth0/eth1) | **SNMPv3** | `MONITORING` MD5/DES (same as Switch*) | **Primary — destination** |
| ExtremeCloud IQ | REST (Pilot) | TBD | Optional later for cloud-only signals |
| Switch `UP-…` | already in 01 | — | Link toward AP; do not double-page AP-down |

**Decision: SNMP direct.** Track B assigns CG **SNMP Monitoring** on role Access Point. Platform TemplateRule `IQ ENGINE` → **`Extreme IQ Engine by SNMP`** (Network Generic removed).

### Ops prerequisite (XIQ)

SNMP answers only if enabled on the AP wired interface. Extreme/Auvik guidance:

1. XIQ → SNMP server (v3 Get) pointing at the Zabbix poller / proxy.
2. AP template / port type: **Traffic Filter → manage SNMP** on eth0 (and eth1 if used).
3. Often also Supplemental CLI: `interface eth0 manage SNMP` (+ eth1), then Delta update.

Without that, Network Generic / any HiveOS template will show SNMP unavailable even when the AP is up on the switch port.

Official MIB pack: [XIQ Auxiliary Files](https://documentation.extremenetworks.com/XIQ/Auxiliary_Files/Auxiliary%20Files.html)  
Local copies: `zabbix/reference/aerohive-mibs/`.

## 3. Enterprise OID tree

Root: `enterprises.26928` (`aerohive`) — from `AH-SMI-MIB` (copyright Extreme 2022; includes Wi‑Fi 6 models through AP4000).

```
.1.3.6.1.4.1.26928
├── 1 ahProduct
│   ├── 1 ahAP
│   │   └── 1 ahAPCommon
│   │       ├── 1 ahAPTrap        → AH_TRAP_MIB
│   │       ├── 2 ahAPInterface   → AH-INTERFACE-MIB  (.1.1.1.2)
│   │       ├── 3 ahAPMRP         → AH-MRP-MIB
│   │       └── 4 ahAPIDP
│   ├── 2 ahSystem                → AH-SYSTEM-MIB     (.1.2)
│   └── 2..38                     → per-model sysObjectID leaves (AP250…AP4000…)
```

Scalar system objects are under **`ahProduct.2`**, not under `ahAPCommon`. Numeric form used by every known NMS:

| Object | OID | Type | Use |
|---|---|---|---|
| `ahSystemName` | `.1.3.6.1.4.1.26928.1.2.1.0` | DisplayString | Inventory |
| `ahSystemDescription` | `.1.3.6.1.4.1.26928.1.2.2.0` | DisplayString | Inventory |
| `ahCpuUtilization` | `.1.3.6.1.4.1.26928.1.2.3.0` | 0..100 | Alert + graph |
| `ahMemUtilization` | `.1.3.6.1.4.1.26928.1.2.4.0` | 0..100 | Alert + graph |
| `ahSystemSerial` | `.1.3.6.1.4.1.26928.1.2.5.0` | DisplayString | Inventory |
| `ahDeviceMode` | `.1.3.6.1.4.1.26928.1.2.6.0` | DisplayString | Inventory |
| `ahUpTime` | `.1.3.6.1.4.1.26928.1.2.7.0` | DisplayString | **Not** TimeTicks — string; prefer IF-MIB/`hrSystemUptime` or SNMP agent uptime if available |
| `ahHwVersion` | `.1.3.6.1.4.1.26928.1.2.8.0` | DisplayString | Inventory |
| `ahClientCount` | `.1.3.6.1.4.1.26928.1.2.9.0` | 0..10000 | Graph; soft warn later |
| `ahEnvirmentTemp` | `.1.3.6.1.4.1.26928.1.2.10.0` | 0..100 | Alert (MIB spelling) |
| `ahEnvirmentFan` | `.1.3.6.1.4.1.26928.1.2.11.0` | RPM | Graph; many wall APs = 0 / unsupported |
| `ahFirmwareVersion` | `.1.3.6.1.4.1.26928.1.2.12.0` | DisplayString | Inventory (**missing from community template**) |

### Interface / radio (`AH-INTERFACE-MIB` under `.1.3.6.1.4.1.26928.1.1.1.2.1`)

| Table | Index | Key columns |
|---|---|---|
| `ahXIfTable` (1) | ifIndex | `ahIfName`, `ahSSIDName`, `ahIfType` (phys/virt), `ahIfMode` (access/backhaul/…) |
| `ahAssociationTable` (2) | ifIndex + client MAC | Per-client RSSI, SSID, VLAN, rates, airtime — **inventory/graph, not v1 paging** |
| `ahRadioStatsTable` (3) | ifIndex | TX/RX frames, retries, drops, errors, RTS failures, airtime |
| `ahVIfStatsTable` (4) | ifIndex | Per-SSID/VIF frame counters |
| `ahRadioAttributeTable` (5) | ifIndex | **Channel, TxPower, NoiseFloor** |

**Noise floor:** MIB says value is *actual + 256* (range documented 0..256). Template must convert: `noise_dbm = value - 256` (verify on pilot).

### Traps (`AH_TRAP_MIB`)

Useful later (not v1 blockers): `ahFailureTrap`, `ahStateChangeEvent`, `ahPoEEvent`, `ahChannelPowerChangeEvent`, `ahClientInfoEvent`, `ahInterferenceMapAlertEvent`. Need trap receiver + filter — out of cutover path.

### MRP (`AH-MRP-MIB`)

Mesh neighbor table. Skip unless the estate runs mesh backhaul.

## 4. Community template review ([bgp4plus/Zabbix-Template](https://github.com/bgp4plus/Zabbix-Template))

Local copy: `zabbix/templates/extreme_iq_engine_snmp/reference_bgp4plus_Aerohive_AP.xml`.

| | Community `Aerohive AP` | Our destination |
|---|---|---|
| Zabbix export | **5.0 XML** (2021) | **7.0 YAML** |
| Proven on | AP245X / AP250 HiveOS 10.0–10.3 | Must re-canary on current IQ Engine (AP3xx/4xxx in SMI) |
| Linked modules | EtherLike + Generic SNMPv2 + Interfaces | ICMP + SNMP avail + IF-MIB eth only; **no** Network Generic (icmpping collision policy) |
| System scalars | 10 items under `ahSystem` | Same + **`ahFirmwareVersion`**, optional fan |
| Radio LLD | `ahIfName` discovery → channel + TxPower only | + **noise floor**, + radio stats (retries/drops/airtime) |
| Clients | Scalar `ahClientCount` only | Scalar in v1; association LLD = v2 (graph, no page) |
| Triggers | CPU warn, temp warn (old `{avg(#3)}` syntax) | Macro-gated destination thresholds; staged enable |
| Traps | none | optional later |

**Verdict:** good OID shortlist and proof that `ahSystem` + radio attribute LLD work on real hardware — **do not import as-is**. Rebuild for Zabbix 7 / our naming / destination macros / no Generic module.

## 5. Signals (destination)

| # | Signal | Source | v1 | Alert / graph |
|---|---|---|---|---|
| 1 | Host ICMP / SNMP availability | ICMP + `zabbix[host,snmp,available]` | yes | Alert |
| 2 | CPU % | `ahCpuUtilization` | yes | Alert (macro) |
| 3 | Memory % | `ahMemUtilization` | yes | Alert (macro) |
| 4 | Temperature °C | `ahEnvirmentTemp` | yes | Alert (macro; canary first — many APs may stub) |
| 5 | Client count | `ahClientCount` | yes | Graph; soft warn optional |
| 6 | Serial / model / FW / HW | system scalars | yes | Inventory |
| 7 | Eth link / traffic | IF-MIB (filter phys eth) | yes | Link-down alert; util graph |
| 8 | Radio channel / Tx power / noise | `ahRadioAttributeTable` LLD | yes | Graph; channel change = info later |
| 9 | Radio retries / drops / airtime | `ahRadioStatsTable` LLD | yes | Graph; alert only after baseline |
| 10 | Per-client association | `ahAssociationTable` | **v2** | Graph / inventory |
| 11 | VIF/SSID stats | `ahVIfStatsTable` | **v2** | Graph |
| 12 | HiveOS traps | trap MIB | later | Event |
| 13 | Mesh MRP | MRP MIB | later | — |

## 6. Discovery

| Rule | Walk | Filter | Prototypes |
|---|---|---|---|
| `radio.discovery` | `ahIfName` (`.…2.1.1.1.1`) | physical radio ifaces (`ahIfType=0` / name `wifi*`) — confirm on pilot | channel, txPower, noiseFloor, key radio stats |
| `net.if.discovery` | IF-MIB | eth only (`ifType` ethernet); exclude wifi/SSID virt | oper status, traffic, errors |
| `client.discovery` | association table | v2 | RSSI, SSID, rates |

## 7. Triggers (destination macros)

| Sev | Condition | Macros | Notes |
|---|---|---|---|
| High | ICMP unavailable × N | remote sites `#5` | Same estate policy as switches |
| High | SNMP unavailable | `{$SNMP.TIMEOUT}` | |
| Average | CPU ≥ warn for settle | `{$CPU.UTIL.WARN}` / `CRIT` | Start ~85/95; baseline |
| Average | Mem ≥ warn | `{$MEMORY.UTIL.MAX}` | |
| Average | Temp ≥ warn | `{$TEMP_WARN}` / `{$TEMP_CRIT}` | Canary — may need silence if OID stub |
| Warning | Eth oper down (phys) | IFCONTROL-style / ifOper | Coordinate with switch `UP-` (see §8) |
| Info/off | Client count ≥ N | `{$AP.CLIENT.WARN}` | Optional; default high |

Cutover silence overlay is **not** the default (same rule as Extreme switching).

## 8. Double-alert policy (AP vs switch `UP-`)

| Failure | Switch `UP-…` | AP host | Destination paging |
|---|---|---|---|
| PoE / cable / switch port | link-down | ICMP+SNMP down | **Page on switch port** (cabled plant); AP host may depend or lower severity |
| AP OS hung, eth still up | up | SNMP/ICMP fail | **Page on AP host** |
| Radio soft failure, eth up | up | radio/noise/client anomalies | AP template only |

Prefer Zabbix trigger dependency: AP unavailable **depends on** matching switch port not down — when we have reliable NetBox/LLDP mapping. Until then: different severities, not two High pages for the same cable cut.

## 9. Template

| | |
|---|---|
| Name | **`Extreme IQ Engine by SNMP`** |
| Path | `zabbix/templates/extreme_iq_engine_snmp/template_net_extreme_iq_engine_snmp.yaml` |
| Base | Custom Zabbix **7.0** YAML (v1 built) |
| Reference | bgp4plus XML (OID shortlist only); official MIBs in `zabbix/reference/aerohive-mibs/` |
| NetBox | TemplateRule `Extreme IQ Engine` / regex `IQ ENGINE` → this template + `OS/Network` |
| Import | `ensure_extreme_iq_engine_template` (zerotouch) + network `--apply` |
| Role floor | **None** on Access Point (already pruned) |
| CG | SNMP Monitoring (`MONITORING` MD5/DES) |

### Staged enablement

| Stage | Enable |
|---|---|
| 0 | Import template; collect inventory + scalars + radio LLD; no pages |
| 1 | ICMP + SNMP availability |
| 2 | CPU / mem / temp (after canary) |
| 3 | Eth link-down |
| 4 | Radio graphs; retry/drop baselines |
| 5 | Soft client-count warn (optional) |
| later | Association LLD, traps, XIQ API |

## 10. Open questions

- [x] Data path: SNMP direct (TemplateRule + YAML wired)
- [ ] Confirm SNMP Get works on a pilot AP with production `MONITORING` after XIQ “manage SNMP”
- [ ] `ahUpTime` string format — parse or ignore in favour of standard uptime
- [ ] `ahEnvirmentTemp` / fan populated on AP305C / AP4000 / AP5010-class hardware?
- [ ] Noise-floor offset (`value - 256`) verified live
- [ ] Radio ifIndex naming (`wifi0` / `wifi1` / …) for LLD filters
- [ ] Trigger dependency wiring to switch `UP-` (NetBox cable / LLDP)
- [ ] SNMPv3 auth/priv on IQ Engine vs MD5/DES used for switches — same profile?

## 11. Done when

- [x] Template YAML v1 + TemplateRule wired (not Network Generic)
- [ ] Pilot AP: system scalars + radio LLD + eth IF-MIB green
- [ ] AP-down alerts once for cable cuts (switch `UP-`), once for AP OS/SNMP failure
- [ ] Destination macros confirmed on live hardware (temp/noise)

---

## Requirements interview (remaining)

1. What breaks today in LM / XIQ that Zabbix must catch at 03:00?
2. Is SNMP already enabled estate-wide on AP eth, or only on a lab policy?
3. Per-client visibility needed in Zabbix, or XIQ remains the client tool?
4. Mesh backhaul anywhere?
