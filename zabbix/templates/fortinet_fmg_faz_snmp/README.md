# Fortinet FMG-FAZ by SNMP

Zabbix **7.0** parent for FortiManager and FortiAnalyzer. Shared MIB
`FORTINET-FORTIMANAGER-FORTIANALYZER-MIB` (`enterprises.12356.103`, build 3737).
There is no official Zabbix template ([ZBXNEXT-10433](https://support.zabbix.com/browse/ZBXNEXT-10433)).

Regenerate YAML from this directory:

```bash
python3 zabbix/templates/fortinet_fmg_faz_snmp/build_template.py
```

## Import / cutover

Do **not** import this parent onto a host by itself in production. Platform
Template Rules **FortiManager** / **FortiAnalyzer** point at the Observability
companions, which nest this parent.

```bash
python3 scripts/configure_nbxsync_network.py --check-fmg-faz
python3 scripts/configure_nbxsync_network.py --apply-fmg-faz
```

Do **not** re-run zerotouch — it still floors these platforms on
**Network Generic Device by SNMP** (`icmpping` collision). Do **not** also
link ICMP Ping, FortiGate HTTP/SNMP, or this parent beside the companion.

Requires Zabbix **7.0+**. Host interface: SNMP (icmpping is SIMPLE on the same
template).

## What this parent owns

- Own `icmpping` — ICMP High, SNMP Warning, loss/RTT collected and **DISABLED**
- Chassis: CPU / memory / disk, firmware, serial (`fnSysSerial`), uptime
- HA / RAID / hardware sensors (native empty LLD tables stay empty on VMs; optional scalar values map not-supported → zero)
- IF-MIB admin-up ethernet
- ADOM + managed-device LLD (connect-down Average; config-sync **DISABLED**, cfgit owns it)
- Host dashboards **Health** (Overview / Hardware / Cluster) and **Network interfaces**

Product boards live on the companions: FMG **Devices**, FAZ **Logs**.

Operator page: [`../../03-fortinet.md`](../../03-fortinet.md). OIDs: [OID_MAPPING.md](OID_MAPPING.md).

## Macros (destination defaults)

| Macro | Default | Meaning |
|---|---|---|
| `{$CPU.UTIL.WARN}` | `85` | CPU Warning. Not a page |
| `{$CPU.UTIL.CRIT}` | `101` | Silences CPU High |
| `{$MEMORY.UTIL.MAX}` | `90` | Memory Average % |
| `{$DISK.UTIL.WARN}` / `CRIT` | `80` / `90` | Parent disk. FAZ High is on the companion |
| `{$IF.UTIL.MAX}` | `101` | Util trigger off |
| `{$FM.DEVICE.CONTROL}` | `1` | Ticket managed-device connect-down |
| `{$FM.DEVICE.EXPECTED}` | `0` | `0` disables census |
| `{$FM.CONFIG.CONTROL}` | `0` | cfgit owns config drift |
| `{$FM.HA.CONTROL}` / `EXPECTED` | `0` / `0` | Standalone silent; pair expects `1` peer |
| `{$UNSUPPORTED.MAX}` | `5` | Average if unsupported items stay above this |
| `{$NET.IF.IFNAME.NOT_MATCHES}` | `^(vlan\|ssl\|hamgmt\|npu\|disk)` | Drop logical overlay ifaces |

## Coverage

- ICMP availability + SNMP agent availability
- Inventory: sysName / descr / fmSysVersion / fnSysSerial
- CPU (incl. exclude-nice, optional), memory used/capacity, disk used/capacity
- FAZ log rate / index rate / lag / licensed GB-day (optional on FMG)
- HA mode / cluster id / peer table
- RAID array + per-disk (optional; unavailable(0) is not an alert)
- Hardware sensors (PSU / fan / temp vendor-state)
- Logical disk table, ADOM archive/analytics %, log-forward targets
- Managed-device connect + config (config trigger disabled)
- IF-MIB oper-status / bits / errors / speed
