# Template Rules

nbxSync model: `ZabbixTemplateRule`  
NetBox: **Zabbix → Template Rules**  
Zerotouch: step 6  
Extreme EXOS rule create/retarget: `configure_nbxsync_network.py`

## What this is

A rule matches the device **platform name** (regex), and optionally role, manufacturer, and required NetBox tags. Every **matching** rule contributes — priority does not suppress another rule’s different template.

Typical payload: a Zabbix template **and** an `OS/…` hostgroup.

Create the OS hostgroups first (same name and value): `OS/Windows`, `OS/Linux`, `OS/Network`, `OS/VMware`.

## Platform rules

| Name | Pattern | Template | Hostgroup | Require tags | Priority | Enabled |
|---|---|---|---|---|---|---|
| Windows catch-all | `Windows` | Windows by Zabbix agent | OS/Windows | — | 200 | Yes |
| Linux | `Ubuntu\|Debian\|Linux\|Red Hat\|CentOS\|Alma\|SUSE\|Arch\|Photon\|Other.*Linux` | Linux by Zabbix agent | OS/Linux | — | 100 | Yes |
| Extreme EXOS | `EXOS` | Extreme EXOS by SNMP | OS/Network | — | 100 | Yes |
| Extreme VOSS | `VOSS` | Extreme VOSS by SNMP | OS/Network | — | 100 | Yes |
| Extreme IQ Engine | `IQ ENGINE` | Extreme IQ Engine by SNMP | OS/Network | — | 100 | Yes |
| FortiOS | `FORTIOS\|FortiOS` | FortiGate by SNMP | OS/Network | — | 100 | Yes |
| FortiAnalyzer/Manager | `FortiAnalyzer\|FortiManager` | Network Generic Device by SNMP | OS/Network | — | 50 | Yes |
| VMware Photon | `Photon` | Linux by Zabbix agent | OS/Linux | — | 50 | Yes |

Do **not** enable a VMware FQDN platform rule on ESXi. Legacy rule `VMware ESXi` stays disabled. Hypervisor LLD is from vCenter. ESXi hardware is Dell iDRAC (below) + OS/VMware.

VOSS / IQ Engine rows are created by zerotouch (soft-resolve until YAML import). **Extreme EXOS** is owned by the network script. Never put Network Generic on Switch* or Access Point (`icmpping` collision).

## Tag-gated OS (NetBox tag `snmp` / `oracle`)

Use with CG **SNMP Monitoring (by tag)** on tag `snmp` for the interface.

| Name | Pattern | Template | Hostgroup | Require tags | Priority | Enabled |
|---|---|---|---|---|---|---|
| SNMP Linux (tag) | *(same Linux pattern)* | Linux by SNMP | OS/Linux | snmp | 40 | Yes |
| SNMP Windows (tag) | `Windows` | Windows by SNMP | OS/Windows | snmp | 40 | Yes |
| Oracle (tag) | `.*` | Oracle by Zabbix agent 2 | — | oracle | 40 | Yes |

## Manufacturer ∧ role

| Name | Pattern | Role pattern | Manufacturer | Template | Hostgroup | Priority |
|---|---|---|---|---|---|---|
| Dell iDRAC (Server) | `.*` | `^(Server\|Cohesity)$` | Dell | Dell iDRAC by SNMP | — | 80 |
| Dell iDRAC (ESXi) | `.*` | `^ESXi Hypervisor$` | Dell | Dell iDRAC by SNMP | OS/VMware | 80 |
| Pure Storage (HTTP) | `.*` | — | Pure Storage | Pure Storage FlashArray v2 by HTTP | — | 80 |
| Dell Storage (HTTP) | `.*` | `^Storage$` | Dell | HPE MSA 2060 Storage by HTTP | — | 80 |
| Huawei OceanStor (SNMP) | `.*` | `^Storage$` | Huawei | Huawei OceanStor Dorado by SNMP | — | 80 |
| Synology DiskStation (SNMP) | `.*` | `^Storage$` | Synology | Synology DiskStation SNMPv3 | — | 80 |
| Synology Storage ICMP | `.*` | `^Storage$` | Synology | ICMP Ping | — | 85 |
| Agent Host ICMP | `.*` | *(agent-class list below)* | — | ICMP Ping | — | 95 |
| Zabbix Proxy ICMP | `.*` | `^Zabbix Proxy$` | — | ICMP Ping | — | 90 |
| Zabbix Proxy Health | `.*` | `^Zabbix Proxy$` | — | Remote Zabbix proxy health | — | 90 |

Legacy **HPE MSA (HTTP)** stays disabled. MSA HTTP is Dell Storage only.

Huawei rule is template only. Transport is the Huawei CG on `HU-DEB-SAN01`. Do not add a Huawei ICMP rule (OceanStor already has `icmpping`).

**Agent Host ICMP** `role_pattern`:

`^(Server|Domain Controller|Fileserver|MSSQL|MSSQL Query Server|Tableau|GitLab|GitHub Runner|TeamCity|HLK|SCCM|PKI|NAC|Acronis Management|VDI|Session Host|Connection Broker|Azure Data Factory|FiveTran|CellMap|Production Backup|Solidworks PDM|Subversion|vCenter|SAP HANA|SAP ME|Space Server)$`

New agent-class roles must be added to this pattern.
