# Macros

nbxSync models: `ZabbixMacro`, `ZabbixMacroAssignment`  
NetBox: **Zabbix → Macros** (definition on the Zabbix Server), then assignment on Role / Device / VM → Zabbix tab  
Zerotouch: step 11  
Switch* IFALIAS values: `configure_nbxsync_network.py` + Extreme switching doc

## What this is

`ZabbixMacro` is the definition (name, type) on the **Zabbix Server**. `ZabbixMacroAssignment` puts a value on a NetBox object. Inheritance resolves it onto the host. Direct device assignment beats role.

This is **not** SNMPv3 passphrases. Those live on the configuration-group Host Interface and are pushed as secret host macros when SNMP push community is True.

This is **not** agent/proxy TLS. Encryption is a host/proxy field, not a user macro.

## Thresholds and DSN (role)

| Macro | Value | Device Role |
|---|---|---|
| `{$CPU.UTIL.CRIT}` | 90 | MSSQL |
| `{$CPU.UTIL.CRIT}` | 80 | Server |
| `{$MEM.UTIL.CRIT}` | 85 | VDI |
| `{$MSSQL.DSN}` | nbxsync | MSSQL |
| `{$VMWARE.URL}` | `https://{{ object.name }}/sdk` | vCenter |

## Extreme Switch* (assignments here, regexes in Extreme switching)

Every Switch Core / Dist / Mgmt / Access / Hybrid role has:

- `{$NET.IF.IFALIAS.MATCHES}`
- `{$NET.IF.IFALIAS.NOT_MATCHES}`
- `{$NET.IF.IFTYPE.MATCHES}`

The regex **strings** change with port-label grammar — keep them in `zabbix/01-extreme-switching.md`. If you add a Switch* role, copy those three assignments from the closest peer.

Fleet TEMP_* / optic globals and cutover-silence overlays are also Extreme-owned (network script).

## Secrets

Each secret is a server-level `ZabbixMacro` plus an assignment on Device, VM, or Role.

### Pure Storage (per Device)

| Macro | Type | Source |
|---|---|---|
| `{$PURE.FLASHARRAY.API.TOKEN}` | Secret | `NBX_PURE_TOKEN_<HOSTNAME>` |
| `{$PURE.FLASHARRAY.API.URL}` | Text | `https://<primary_ip>/` |

Arrays: `hu-deb-san11`, `kr-sel-san11`, `cn-sha-san11`, `ch-zrh-zh4-san01/02`, `ch-zrh-zh5-san01/02`. Legacy name `{$PURESTORAGE.TOKEN}` is pruned.

### HPE MSA on Dell Storage (per Device)

| Macro | Type | Env |
|---|---|---|
| `{$HPE.MSA.API.HOST}` | Text | `NBX_MSA_API_HOST_<HOSTNAME>` (host only; template adds https/:443) |
| `{$HPE.MSA.API.USERNAME}` | Text | `NBX_MSA_API_USER_<HOSTNAME>` |
| `{$HPE.MSA.API.PASSWORD}` | Secret | `NBX_MSA_API_PASS_<HOSTNAME>` |

Known array: `CN-SHA-P-STOD01`.

### VMware (per vCenter VM)

| Macro | Type | Env |
|---|---|---|
| `{$VMWARE.USERNAME}` | Secret | `NBX_VMWARE_USER_<HOSTNAME>` |
| `{$VMWARE.PASSWORD}` | Secret | `NBX_VMWARE_PASS_<HOSTNAME>` |

| vCenter | SSO domain |
|---|---|
| ch-sta-p-vcsa02 / vcsa10 | `VCENTER-SSO.SENSIRION\LogicMonitor` |
| hu-deb-p-vcsa01 | `HU.VSPHERE.LOCAL\LogicMonitor` |
| kr-sel-p-vcsa01 | `KR.VSPHERE.LOCAL\LogicMonitor` |
| cn-sha-p-vcsa01 | `cn.vsphere.lokal\LogicMonitor` |

Legacy `{$VMWARE.USER}` is pruned.

### MSSQL (role, shared)

| Macro | Type | Env |
|---|---|---|
| `{$MSSQL.USER}` | Secret | `NBX_MSSQL_USER` |
| `{$MSSQL.PASSWORD}` | Secret | `NBX_MSSQL_PASS` |

On Device Role **MSSQL**.
