# nbxSync configuration

**This is the only document for basic nbxSync setup.** Follow it top to bottom in NetBox (same order as first-time apply / zerotouch). When you change something in the GUI, update **that section here**.

Day-2 (broken host, new role): `runbooks/day2.md`.  
Cutover hold: `runbooks/onboarding.md`.  
Extreme port labels / alerts: `zabbix/01-extreme-switching.md` (not nbxSync objects).

## How to follow this in the GUI

NetBox top menu **Zabbix** is the plugin. Most **assignments** are also on the object: open a Site Group, Device Role, Device, Tag, or Cluster → **Zabbix** tab (same data).

| § | Click in NetBox | What you create |
|---|---|---|
| 1 | **Zabbix → Servers → Add** | API connection to Zabbix Cloud |
| 2 | **Zabbix → Proxy Groups → Add**, **Zabbix → Proxies → Add** | Proxies |
| 3 | **Site Group → Zabbix tab → Zabbix Servers → Add** | Which proxy monitors that country |
| 4 | **Zabbix → Configuration groups → Add** | Transport profiles (Agent / SNMP) |
| 5 | Open the group → **Host Interfaces → Add** | Port, SNMPv3, Use OOB IP |
| 5b | Open the group → **Assignments → Add** (or Role / Site Group / Tag / Device → Zabbix tab) | Who gets that group |
| 6 | **Zabbix → Template Rules → Add** | Platform → OS template + `OS/…` |
| 7 | **Zabbix → Templates** → Assigned objects, or **Role → Zabbix tab** | Function templates (MSSQL, vCenter, …) |
| 8 | **Zabbix → Hostgroups → Add**, then assign on Site Group / Tag | `Sites/…`, `Roles/…`, `Priority/Critical` |
| 9 | **Zabbix → Tags**, **Organization → Tags** → Zabbix tab | environment, exclude, NetBox tag inputs |
| 10 | **Site Group → Zabbix tab → Host Inventory** | Serial, hardware, NetBox URL |
| 11 | **Zabbix → Macros → Add**, then Role / Device / VM → Zabbix tab | Thresholds and secrets |
| 12 | **Admin → Plugins → nbxSync** | Source of truth, exclude, status map |
| 13 | Device → Zabbix tab **or** Zabbix host | Check the result |

---

## How sync works (read once)

nbxSync turns a NetBox Device or VM into a Zabbix **host**. You do not edit that host in Zabbix. You hang policy on NetBox objects; a sync job pushes the result.

- **Inheritance:** Device beats Role / Tag / Manufacturer; those beat Site Group. Country **Site Group** is the default: proxy, Agent group, Sites/Roles hostgroups, environment, inventory.
- **One configuration group = transport** (how we reach the host). Hostgroups and templates **merge**; two CGs do not give two transports. Device CG beats role CG.
- Put Host Interfaces **on the configuration group**, not on every device and not on a tag. Sync fills IP from `primary_ip`, or `oob_ip` if **Use OOB IP** is Yes.
- Different SNMPv3 users need different groups (`MONITORING`, `MONITORING-LINUX`, `MONITORING-IDRAC`, `SAPUSER`).
- **Template Rules** match platform name. **Template assignments** hang a function template on a Role. Both apply. If two templates both define `icmpping`, Zabbix rejects the host.
- Zabbix tag `do_not_monitor` (from a role or from NetBox tag `onboarding`) → sync **skips** the object and deletes an existing Zabbix host.

Inventory (sites, roles, IPs) is assumed already in NetBox. Agent TLS is **No encryption**. Proxy↔Cloud mTLS is on the proxy OS / Cloud portal, not in this plugin.

---

## 1. Zabbix Server

**Click:** Zabbix → Servers → Add

The API endpoint. Without it, nothing syncs. Validate-certs is whether NetBox trusts the **API URL** certificate — not proxy mTLS.

| Field | Value |
|---|---|
| Name | Zabbix Production |
| URL | `https://sensirion.zabbix.cloud` |
| Token | API token |
| Validate certs | True |
| Sync enabled | True |
| Skip version check | False |

---

## 2. Proxies and proxy groups

**Click:** Zabbix → Proxy Groups → Add, Zabbix → Proxies → Add

TLS on the proxy object is **proxy ↔ Cloud**. PEM files are not in nbxSync; we only set `tls_accept=Certificate` so a later sync does not reset encryption to none.

Set **either** a proxy **or** a proxy group on a country — not both.

| Name | Zabbix server | Description |
|---|---|---|
| Swiss proxy group | Zabbix Production | CH pair; NL and US route through CH |

| Name | Mode | Proxy group | TLS accept | Local address | Local port |
|---|---|---|---|---|---|
| ch-sta-p-zabp01 | Active | Swiss proxy group | Certificate | 10.0.104.235 | 10051 |
| ch-sta-p-zabp02 | Active | Swiss proxy group | Certificate | 10.0.105.235 | 10051 |
| hu-deb-p-zabp01 | Active | — | Certificate | — | — |
| kr-sel-p-zabp01 | Active | — | Certificate | — | — |
| cn-sha-p-zabp01 | Active | — | Certificate | — | — |

- Proxy → Cloud: active, TCP 10051, mTLS (Sensirion PKI)
- Proxy → Agent: passive, TCP 10050

`netbox-sync` sets `role=Zabbix Proxy` on `-ZABP\d+` VMs. They inherit the country proxy and poll localhost agent.

---

## 3. Server assignment (country Site Group)

**Click:** Organization → Site Groups → **CH** (etc.) → Zabbix tab → Zabbix Servers → Add

Only on **country** Site Groups, not campus mid-levels.

| Site Group | Proxy | Proxy group | Sync enabled |
|---|---|---|---|
| CH | — | Swiss proxy group | Yes |
| HU | hu-deb-p-zabp01 | — | Yes |
| JP | kr-sel-p-zabp01 | — | Yes |
| KR | kr-sel-p-zabp01 | — | Yes |
| NL | — | Swiss proxy group | Yes |
| US | — | Swiss proxy group | Yes |
| CN | cn-sha-p-zabp01 | — | Yes |

---

## 4. Configuration groups

**Click:** Zabbix → Configuration groups → Add

A group is a **transport profile**. Leave IP empty on the group.

| Name | Credential / port | Who it is for |
|---|---|---|
| Agent Monitoring | Agent :10050, TLS none | Default on every country Site Group |
| Agent Monitoring (SPACE) | Agent :10060, TLS none | Role Space Server |
| SNMP Monitoring | `MONITORING` MD5/DES | Switch*, AP, Firewall, Network Device, Virtual Appliance, Cohesity Appliance, Manufacturer Synology |
| SNMP Monitoring (by tag) | `MONITORING-LINUX` SHA1/AES128 | NetBox tag `snmp` |
| SNMP Monitoring (Huawei) | `LogicMonitor` SHA1/AES128 | Device `HU-DEB-SAN01` |
| SAP Agent+SNMP | Agent :10050 **and** `SAPUSER` | Roles SAP HANA, SAP ME |
| Dell iDRAC SNMP | `MONITORING-IDRAC` SHA384/AES256 @ oob | Role ESXi Hypervisor |
| Dell iDRAC SNMP (AES128) | `MONITORING-IDRAC` SHA384/AES128 @ oob | KR/CN ESXi devices (list in §5b) |
| Dell iDRAC SNMP (Legacy) | `MONITORING-IDRAC` SHA1/AES128 @ oob | Role Cohesity |

**Server** stays on Site Group Agent @ primary. iDRAC *template* for Dell servers is a Template Rule (§6), not an iDRAC group.

Retired (deleted by zerotouch): `Server Agent+OOB`, `ESXi OOB iDRAC`, `OOB SNMP Only`, `OOB SNMP v2c`, `Dell iDRAC HTTP`.

---

## 5. Host Interfaces (on the group)

**Click:** Zabbix → Configuration groups → *[group]* → Host Interfaces → Add

**SNMP push community = True.** Real passphrases on the interface (env `NBX_SNMP_*`), not `{$SNMP_AUTHPASS}` placeholders.

| Group | Type | Port | Use OOB IP | SNMPv3 |
|---|---|---|---|---|
| Agent Monitoring | Agent | 10050 | No | — |
| Agent Monitoring (SPACE) | Agent | 10060 | No | — |
| SNMP Monitoring | SNMP | 161 | No | MONITORING / MD5 / DES |
| SNMP Monitoring (by tag) | SNMP | 161 | No | MONITORING-LINUX / SHA1 / AES128 |
| SNMP Monitoring (Huawei) | SNMP | 161 | No | LogicMonitor / SHA1 / AES128 |
| SAP Agent+SNMP | Agent **and** SNMP | 10050 / 161 | No | SAPUSER (confirm auth/priv) |
| Dell iDRAC SNMP | SNMP | 161 | **Yes** | MONITORING-IDRAC / SHA384 / AES256 |
| Dell iDRAC SNMP (AES128) | SNMP | 161 | **Yes** | MONITORING-IDRAC / SHA384 / AES128 |
| Dell iDRAC SNMP (Legacy) | SNMP | 161 | **Yes** | MONITORING-IDRAC / SHA1 / AES128 |

SAP must be **one** group with both interfaces. Two groups on the same role would not dual-plane.

Env: `NBX_SNMP_AUTHPASS_MON` / `PRIVPASS_MON`, `_LINUX`, `_SAP`, `_IDRAC`, `_HUAWEI`. Huawei passphrases are only written when set.

iDRAC user `MONITORING-IDRAC` must also exist on each iDRAC (UI or racadm).

---

## 5b. Who gets which group

**Click:** Zabbix → Configuration groups → *[group]* → Assignments → Add  
**or** Site Group / Device Role / Tag / Device / Manufacturer → Zabbix tab

Without an assignment, the group’s interfaces are not applied.

| Configuration group | Assign to |
|---|---|
| Agent Monitoring | Site Groups CH, HU, JP, KR, NL, US, CN |
| SNMP Monitoring | Roles Switch Core / Dist / Access / Mgmt / Hybrid, Access Point, Firewall, Network Device, Virtual Appliance, Cohesity Appliance; Manufacturer **Synology** |
| SNMP Monitoring (by tag) | NetBox tag **snmp** |
| SNMP Monitoring (Huawei) | Device **HU-DEB-SAN01** |
| SAP Agent+SNMP | Roles SAP HANA, SAP ME |
| Agent Monitoring (SPACE) | Role Space Server |
| Dell iDRAC SNMP | Role ESXi Hypervisor |
| Dell iDRAC SNMP (Legacy) | Role Cohesity |
| Dell iDRAC SNMP (AES128) | Devices `cn-sha-p-esx11/12/13`, `kr-sel-p-esx11/12/13` (.sensirion.lokal) |

- Do **not** assign SNMP Monitoring on role Storage (Pure/Dell would get the wrong user) or Manufacturer Huawei.
- Do **not** assign Agent Monitoring on SAP roles.
- AES128: device group wins over role AES256. Do not leave durable per-device Host Interfaces on those hosts (propagate stamps `ip=primary`, which beats Use OOB IP). Zerotouch prunes them.
- Physical Cohesity = role Cohesity + Legacy. Cohesity VMs = role Cohesity Appliance + SNMP Monitoring.

---

## 6. Template Rules

**Click:** Zabbix → Template Rules → Add

First create hostgroups **Zabbix → Hostgroups → Add** with name = value: `OS/Windows`, `OS/Linux`, `OS/Network`, `OS/VMware`.

A rule matches **platform name** (regex), optional role / manufacturer / NetBox tags. **Every matching rule contributes.**

Extreme EXOS rule is created/retargeted by `configure_nbxsync_network.py`. VOSS / IQ Engine: zerotouch (soft-resolve until YAML import).

### Platform

| Name | Pattern | Template | Hostgroup | Tags | Pri | On |
|---|---|---|---|---|---|---|
| Windows catch-all | `Windows` | Windows by Zabbix agent | OS/Windows | — | 200 | Yes |
| Linux | `Ubuntu\|Debian\|Linux\|Red Hat\|CentOS\|Alma\|SUSE\|Arch\|Photon\|Other.*Linux` | Linux by Zabbix agent | OS/Linux | — | 100 | Yes |
| Extreme EXOS | `EXOS` | Extreme EXOS by SNMP | OS/Network | — | 100 | Yes |
| Extreme VOSS | `VOSS` | Extreme VOSS by SNMP | OS/Network | — | 100 | Yes |
| Extreme IQ Engine | `IQ ENGINE` | Extreme IQ Engine by SNMP | OS/Network | — | 100 | Yes |
| FortiOS | `FORTIOS\|FortiOS` | FortiGate by SNMP | OS/Network | — | 100 | Yes |
| FortiAnalyzer/Manager | `FortiAnalyzer\|FortiManager` | Network Generic Device by SNMP | OS/Network | — | 50 | Yes |
| VMware Photon | `Photon` | Linux by Zabbix agent | OS/Linux | — | 50 | Yes |

Do **not** enable a VMware FQDN rule on ESXi. Legacy `VMware ESXi` stays disabled. Never Network Generic on Switch* / Access Point (`icmpping` collision).

### Tag-gated (`snmp` / `oracle`)

| Name | Pattern | Template | Hostgroup | Require tags | Pri |
|---|---|---|---|---|---|
| SNMP Linux (tag) | *(same Linux pattern)* | Linux by SNMP | OS/Linux | snmp | 40 |
| SNMP Windows (tag) | `Windows` | Windows by SNMP | OS/Windows | snmp | 40 |
| Oracle (tag) | `.*` | Oracle by Zabbix agent 2 | — | oracle | 40 |

### Manufacturer ∧ role

| Name | Pattern | Role pattern | Manufacturer | Template | Hostgroup | Pri |
|---|---|---|---|---|---|---|
| Dell iDRAC (Server) | `.*` | `^(Server\|Cohesity)$` | Dell | Dell iDRAC by SNMP | — | 80 |
| Dell iDRAC (ESXi) | `.*` | `^ESXi Hypervisor$` | Dell | Dell iDRAC by SNMP | OS/VMware | 80 |
| Pure Storage (HTTP) | `.*` | — | Pure Storage | Pure Storage FlashArray v2 by HTTP | — | 80 |
| Dell Storage (HTTP) | `.*` | `^Storage$` | Dell | HPE MSA 2060 Storage by HTTP | — | 80 |
| Huawei OceanStor (SNMP) | `.*` | `^Storage$` | Huawei | Huawei OceanStor Dorado by SNMP | — | 80 |
| Synology DiskStation (SNMP) | `.*` | `^Storage$` | Synology | Synology DiskStation SNMPv3 | — | 80 |
| Synology Storage ICMP | `.*` | `^Storage$` | Synology | ICMP Ping | — | 85 |
| Agent Host ICMP | `.*` | *(below)* | — | ICMP Ping | — | 95 |
| Zabbix Proxy ICMP | `.*` | `^Zabbix Proxy$` | — | ICMP Ping | — | 90 |
| Zabbix Proxy Health | `.*` | `^Zabbix Proxy$` | — | Remote Zabbix proxy health | — | 90 |

Legacy **HPE MSA (HTTP)** stays disabled. Huawei rule is template only (transport = Huawei CG on the device). No Huawei ICMP rule (OceanStor has `icmpping`).

**Agent Host ICMP** `role_pattern`:

`^(Server|Domain Controller|Fileserver|MSSQL|MSSQL Query Server|Tableau|GitLab|GitHub Runner|TeamCity|HLK|SCCM|PKI|NAC|Acronis Management|VDI|Session Host|Connection Broker|Azure Data Factory|FiveTran|CellMap|Production Backup|Solidworks PDM|Subversion|vCenter|SAP HANA|SAP ME|Space Server)$`

New agent-class roles must be added here.

---

## 7. Template assignments (on the Role)

**Click:** Zabbix → Templates → *[template]* → Assigned objects → Add  
**or** Devices → Device Roles → *[role]* → Zabbix tab

These **merge** with §6. Set each template’s interface requirement (Agent / SNMP / ANY) to match transport. OS / storage / iDRAC templates are §6, not this table.

Do **not** assign Network Generic on Switch* or Access Point.

| Template | Assign to | Notes |
|---|---|---|
| MSSQL by Zabbix agent 2 | MSSQL, MSSQL Query Server | |
| VMware FQDN | **vCenter only** | Not on ESXi. Secrets §11 |
| GitLab by HTTP | GitLab | |
| Linux by SNMP | Virtual Appliance | Fallback if no platform rule |
| Network Generic Device by SNMP | Network Device | Fallback only |
| Storage Generic Device by SNMP | Cohesity | Placeholder |
| FortiGate by SNMP | Firewall | Also FortiOS rule |
| Tableau Bridge by Zabbix agent `(stub)` | Tableau | Skip if template absent |
| CellMap by Zabbix agent `(stub)` | CellMap | |
| Oracle by Zabbix agent 2 `(stub)` | Database | Also tag `oracle` |
| SAP by Zabbix agent `(stub)` | SAP ME, SAP HANA | |
| Acronis by Zabbix agent `(stub)` | Acronis Management | |
| SCCM by Zabbix agent `(stub)` | SCCM | |

One-off (e.g. AS Java): assign on the **Device**. Print Spool is not role-assigned today.

When Extreme staging says so (not on the platform rule):

| Template | Assign to |
|---|---|
| Extreme Port Speed Expect by SNMP | Switch Core / Dist / Access / Mgmt / Hybrid |
| Extreme Routing by SNMP | Switch Core, Switch Dist |

---

## 8. Hostgroups

**Click:** Zabbix → Hostgroups → Add, then Site Group or Tag → Zabbix tab → Hostgroups

Value may be Jinja (renders per Device/VM). Hosts stay in the **leaf**. Parents exist so dashboards can filter on `Sites/CH`. Axes: `Sites/…`, `Roles/…`, `OS/…`, optional `Priority/Critical`. No `Teams/*`, no `Managed`.

| Name | Value | Assign to |
|---|---|---|
| Sites | `Sites/{{ object.site.group.get_ancestors(include_self=True) \| map(attribute="name") \| join("/") }}/{{ object.site.name }}` | Site Groups CH … CN |
| Roles | `Roles/{{ object.role.name }}` | Same Site Groups |
| Priority/Critical | `Priority/Critical` | NetBox tag `critical` |

Example: site under campus CH-STA → `Sites/CH/CH-STA/CH-STA-L42`. Preview error **on a Site Group** is cosmetic (no `object.site` there).

New roles appear as `Roles/<name>` automatically — do not create a per-role hostgroup assignment.

OS groups are created in §6; membership comes from Template Rules.

---

## 9. Tags

**Click:** Zabbix → Tags (Zabbix host tags)  
**and** Organization → Tags (NetBox inventory tags) → open tag → Zabbix tab

Two different things:

1. **NetBox tags** on Devices/VMs — sync **reads** them. They are not copied to Zabbix as host tags.
2. **Zabbix tags** written on the host (`environment`, `cluster`) or used as exclude (`do_not_monitor`).

A Zabbix tag on a **NetBox Tag** object applies to every Device/VM that carries that inventory tag.

| NetBox tag | Effect |
|---|---|
| `critical` | Hostgroup Priority/Critical |
| `snmp` | Group SNMP Monitoring (by tag) + Linux/Windows by SNMP rules |
| `oracle` | Oracle Template Rule |
| `onboarding` | Inherits Zabbix `do_not_monitor` — **remove this tag to start monitoring** |

Do not use leftover `snmp-sap`. SAP = roles → SAP Agent+SNMP.

### environment (Jinja on country Site Groups)

**Click:** Site Group → Zabbix tab → Tags. Name-pattern only.

```
{% set n = (object.name or "") | lower -%}
{% if "-p-" in n or n.endswith("-p") or "-p0" in n or "-p1" in n -%}Production
{%- elif "-d-" in n -%}Development
{%- elif "-q-" in n -%}QA
{%- elif "-s-" in n -%}Sandbox
{%- elif "-t-" in n -%}Test
{%- elif "vdi" in n -%}VDI
{%- else -%}Unknown
{%- endif -%}
```

Switches without `-p-` (`…-CORE01`) → `Unknown` is expected.

### cluster

| Tag | Value | Assign to |
|---|---|---|
| cluster | `{{ object.cluster.name }}` | each Cluster |

### Exclude `do_not_monitor`

Plugin `exclude_tag` = `do_not_monitor`. Sync skips and **deletes** an existing Zabbix host.

| Assign Zabbix tag to | Intent |
|---|---|
| Device Role Messpc, Sd Wan Socket, VDI | Permanent |
| NetBox Tag **onboarding** | Cutover waves |

Do **not** put it on role Server or a Site Group for waves. Waves use NetBox tag **`onboarding`** only (not a NetBox tag named `do_not_monitor`).

---

## 10. Host inventory

**Click:** Site Group → Zabbix tab → Host Inventory → Add  
Assign to CH, HU, JP, KR, NL, US, CN. Mode **Automatic**.

| Field | Value |
|---|---|
| type | `{{ object.__class__.__name__ }}` |
| serialno_a | `{{ object.serial }}` |
| hardware | `{{ object.device_type.model if object.device_type else "" }}` |
| hardware_full | `{{ object.device_type.manufacturer.name if object.device_type else "" }} {{ object.device_type.model if object.device_type else "" }}` |
| tag | `{{ object.asset_tag }}` |
| location | `{{ object.site.name }}` |
| site_rack | `{{ object.rack.name if object.rack else "" }}` |
| name | `{{ object.name }}` |
| url_a | `{% if object.device_type %}https://netbox.sensirion.lokal/dcim/devices/{{ object.id }}/{% else %}https://netbox.sensirion.lokal/virtualization/virtual-machines/{{ object.id }}/{% endif %}` |
| deployment_status | `{{ object.status }}` |

---

## 11. Macros

**Click:** Zabbix → Macros → Add (definition on the Zabbix Server)  
then Device Role / Device / VM → Zabbix tab → Macros

This is **not** SNMPv3 passphrases (those are on the group Host Interface, §5) and **not** TLS.

### Thresholds (role)

| Macro | Value | Role |
|---|---|---|
| `{$CPU.UTIL.CRIT}` | 90 | MSSQL |
| `{$CPU.UTIL.CRIT}` | 80 | Server |
| `{$MEM.UTIL.CRIT}` | 85 | VDI |
| `{$MSSQL.DSN}` | nbxsync | MSSQL |
| `{$VMWARE.URL}` | `https://{{ object.name }}/sdk` | vCenter |

### Switch* IFALIAS

On Switch Core / Dist / Mgmt / Access / Hybrid:

`{$NET.IF.IFALIAS.MATCHES}`, `{$NET.IF.IFALIAS.NOT_MATCHES}`, `{$NET.IF.IFTYPE.MATCHES}`

Regex **strings** live with Extreme switching (`zabbix/01`). Copy from the closest peer if you add a Switch* role. Applied by `configure_nbxsync_network.py`.

### Secrets

| Macro | Type | Where | Source |
|---|---|---|---|
| `{$PURE.FLASHARRAY.API.TOKEN}` | Secret | each Pure Device | `NBX_PURE_TOKEN_<HOSTNAME>` |
| `{$PURE.FLASHARRAY.API.URL}` | Text | each Pure Device | `https://<primary_ip>/` |
| `{$HPE.MSA.API.HOST}` | Text | Dell Storage Device | `NBX_MSA_API_HOST_<HOSTNAME>` |
| `{$HPE.MSA.API.USERNAME}` | Text | Dell Storage Device | `NBX_MSA_API_USER_<HOSTNAME>` |
| `{$HPE.MSA.API.PASSWORD}` | Secret | Dell Storage Device | `NBX_MSA_API_PASS_<HOSTNAME>` |
| `{$VMWARE.USERNAME}` | Secret | each vCenter VM | `NBX_VMWARE_USER_<HOSTNAME>` |
| `{$VMWARE.PASSWORD}` | Secret | each vCenter VM | `NBX_VMWARE_PASS_<HOSTNAME>` |
| `{$MSSQL.USER}` | Secret | Role MSSQL | `NBX_MSSQL_USER` |
| `{$MSSQL.PASSWORD}` | Secret | Role MSSQL | `NBX_MSSQL_PASS` |

Pure arrays: `hu-deb-san11`, `kr-sel-san11`, `cn-sha-san11`, `ch-zrh-zh4-san01/02`, `ch-zrh-zh5-san01/02`.  
MSA: `CN-SHA-P-STOD01`.  
vCenter SSO: `ch-sta-p-vcsa02/10` → `VCENTER-SSO.SENSIRION\LogicMonitor`; `hu-deb-p-vcsa01` → `HU.VSPHERE.LOCAL\…`; `kr-sel-p-vcsa01` → `KR.VSPHERE.LOCAL\…`; `cn-sha-p-vcsa01` → `cn.vsphere.lokal\…`.

Zerotouch prunes `{$PURESTORAGE.TOKEN}` and `{$VMWARE.USER}`.

---

## 12. Plugin settings

**Click:** Admin → Plugins → nbxSync  
(Not in the Zabbix menu. Set once; zerotouch does not write this.)

| Setting | Value |
|---|---|
| Source of truth (host, hostgroup, interface, template, tag, macro, proxy, maintenance) | NetBox |
| Exclude tag | `do_not_monitor` |
| Soft-state tag / value | `NO_ALERTING` / `1` |
| Attach object identity tags | Yes (`nb_type` / `nb_id`) |
| Allow inherited deletion | No |
| Adopt existing Zabbix hosts | No |
| Device status → Zabbix | active → enabled; planned/staged → disabled; failed/offline/inventory/decommissioning → deleted |
| VM status → Zabbix | active → enabled; planned → enabled in maintenance; paused → enabled + soft-state; failed/offline → deleted |
| SNMP community / auth / priv macro names | `{$SNMP_COMMUNITY}`, `{$SNMP_AUTHPASS}`, `{$SNMP_PRIVPASS}` |

Keep **Site / Site Group after Role / Platform** in inheritance so country Agent does not override role SNMP or iDRAC.

---

## 13. What a host should look like

After sync, check the Device **Zabbix** tab or the Zabbix host. If a row is wrong, fix the matching section above.

| Object | Configuration group | Templates | Interfaces | Hostgroups |
|---|---|---|---|---|
| Linux server (role Server) | Agent Monitoring (Site Group) | Linux by agent + ICMP (+ Dell iDRAC by SNMP if Dell) | Agent :10050 @ primary | Sites/…, Roles/Server, OS/Linux |
| Linux or Windows VM | Agent Monitoring | OS by agent + ICMP if role in Agent Host ICMP | Agent :10050 | Sites/…, Roles/…, OS/… |
| SAP HANA / SAP ME | SAP Agent+SNMP | Linux + SAP `(stub)` + ICMP | Agent :10050 + SNMP SAPUSER | Sites/…, Roles/SAP …, OS/Linux |
| Tag `snmp` | SNMP Monitoring (by tag) | Linux or Windows by SNMP | SNMP MONITORING-LINUX | Sites/…, Roles/…, OS/… |
| EXOS Switch | SNMP Monitoring | Extreme EXOS by SNMP + IFALIAS | SNMP MONITORING MD5/DES | Sites/…, Roles/Switch …, OS/Network |
| VOSS Switch | SNMP Monitoring | Extreme VOSS (**not** Network Generic) | SNMP MONITORING MD5/DES | Sites/…, Roles/Switch …, OS/Network |
| Access Point | SNMP Monitoring | Extreme IQ Engine (**not** Network Generic) | SNMP MONITORING MD5/DES | Sites/…, Roles/Access Point, OS/Network |
| Firewall | SNMP Monitoring | FortiGate by SNMP | SNMP MONITORING MD5/DES | Sites/…, Roles/…, OS/Network |
| Space Server | Agent Monitoring (SPACE) | OS by agent + ICMP | Agent :10060 | Sites/…, Roles/Space Server |
| Storage (Pure) | Agent Monitoring | FlashArray HTTP + API macros | Agent / HTTP | Sites/…, Roles/Storage |
| Storage (Synology) | SNMP Monitoring (Manufacturer) | Synology DiskStation SNMPv3 + ICMP | SNMP MONITORING | Sites/…, Roles/Storage |
| HU-DEB-SAN01 | SNMP Monitoring (Huawei) on Device | Huawei OceanStor | SNMP LogicMonitor | Sites/…, Roles/Storage |
| Storage (Dell) | Agent Monitoring | HPE MSA HTTP + API macros | Agent / HTTP | Sites/…, Roles/Storage |
| Cohesity physical | Dell iDRAC SNMP (Legacy) | Dell iDRAC by SNMP | SHA1/AES128 @ oob | Sites/…, Roles/Cohesity |
| ESXi Hypervisor | Dell iDRAC SNMP | Dell iDRAC by SNMP | SHA384/AES256 @ oob | Sites/…, Roles/ESXi Hypervisor, OS/VMware |
| ESXi KR/CN exceptions | Dell iDRAC SNMP (AES128) on Device | Dell iDRAC by SNMP | SHA384/AES128 @ oob | same |
| vCenter | Agent Monitoring | VMware FQDN + ICMP | Agent / HTTP(SDK) | Sites/…, Roles/vCenter |
| Zabbix Proxy | Agent Monitoring | Linux + ICMP + Remote proxy health | Agent :10050 | Sites/…, Roles/Zabbix Proxy, OS/Linux |
| + tag `critical` | unchanged | unchanged | unchanged | + Priority/Critical |
| New role tomorrow | Agent Monitoring unless §5b lists it | OS rule if platform set | Agent | Roles/\<name\> automatic |
| No site | — | — | — | Not profiled |
| Tag `onboarding` or excluded role | — | — | — | No Zabbix host |

---

## First-build scripts (optional)

Day-to-day: GUI. Scripts only for first apply:

1. `python scripts/configure_nbxsync_zerotouch.py` — this document §§1–11
2. `python scripts/configure_nbxsync_network.py --apply` — Extreme YAML, Switch* IFALIAS, TEMP_*

Details: `scripts/README.md`.
