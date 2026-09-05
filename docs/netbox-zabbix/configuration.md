## How this works (read once)

Zabbix does not browse NetBox. The **nbxSync** plugin in NetBox pushes devices and VMs. Three layers decide what the host looks like:

| Layer | Where | What it does |
|---|---|---|
| **1 — Can this object sync?** | Device / VM in NetBox | Country **Site Group** (or cluster site) selects the Zabbix server + proxy. Role **Messpc / VDI** or tag **`onboarding`** → excluded (`do_not_monitor`). `Sd Wan Socket` uses controlled per-device onboarding: the current 21 Socket hosts are released and live; a new or replacement Socket is held with `onboarding` until its primary IP and proxy path are ready. No site → not profiled. |
| **2 — How does Zabbix talk to it?** | **Zabbix → Configuration groups** | One **winning** CG supplies **Host Interfaces** (Agent / SNMP). Default is **Agent Monitoring** on every country Site Group. Role / manufacturer / device / tag assignments override that default. SNMPv3 **auth/priv protocol is an integer on the interface** — a macro cannot switch SHA vs MD5. Different crypto = a different CG. |
| **3 — Which Zabbix templates?** | **Template Rules** then role/object **Templates** | **Every matching enabled Template Rule applies** (they merge). Direct template links on a role fill gaps (MSSQL, vCenter, GitLab, …). |

**Jinja** in hostgroups, tags, inventory, and some macros is evaluated at sync (`object` = that NetBox row). Preview errors on a Site Group are cosmetic.

**`use_oob_ip`** on a CG is honoured when the interface is expanded from the CG. If a **durable** Host Interface already exists on the device with `ip=primary`, changing the CG does nothing useful — delete that Host Interface (nbxSync object) and let sync recreate it from the CG.

**TLS vs SNMP:** Proxy **TLS accept** is on the proxy object (§2). Agent **TLS connect** is on the CG (currently no encryption, §5.2 / §5.7). SNMP crypto is the CG SNMPv3 profile, not TLS.

**Plugin Settings (§12)** are set once in the plugin config (not on a Device or Role).

**Keeping this document true:** new Device Role → decide transport (§5b). Agent-class roles get ICMP automatically (§6.4). New SNMPv3 crypto → new CG, not a macro. New Zabbix template → Template Rule if role/manufacturer/platform/tag can express it (§6), else a role assignment (§7). Then sync one object and check §13.

### GUI map

Top menu **Zabbix**: Servers, Proxies, Proxy Groups, Templates, Macros, Tags, Hostgroups, Configuration groups, Maintenance, Template Rules. Most assignments and host interfaces are added from a parent’s **Zabbix** tab. Role templates → Role/Template page; `OS/Windows|Linux|Network` via Template Rules; `OS/VMware` on role ESXi Hypervisor.

---


## 1. Zabbix Server

Path: **Zabbix → Servers → Add**

| Field | Value |
|---|---|
| Name | Zabbix Production |
| URL | `https://sensirion.zabbix.cloud` |
| Token | *(API token)* |
| Validate certs | True |
| Sync enabled | True |
| Skip version check | False |

**Validate certs = True** means the NetBox host must trust the HTTPS certificate for that URL (OS trust store / corporate root).

---

## 2. Proxies and proxy groups

Path: **Zabbix → Proxies → Add**, **Zabbix → Proxy Groups → Add**

### 2.1 Proxy group

| Name | Zabbix server | Description |
|---|---|---|
| Swiss proxy group | Zabbix Production | CH proxy pair (NL and US route through CH) |

### 2.2 Proxies

| Name | Mode | Proxy group | TLS accept | Local address | Local port |
|---|---|---|---|---|---|
| ch-sta-p-zabp01 | Active | Swiss proxy group | Certificate | 10.0.104.235 | 10051 |
| ch-sta-p-zabp02 | Active | Swiss proxy group | Certificate | 10.0.105.235 | 10051 |
| hu-deb-p-zabp01 | Active | — | Certificate | — | — |
| kr-sel-p-zabp01 | Active | — | Certificate | — | — |
| cn-sha-p-zabp01 | Active | — | Certificate | — | — |

`local_address` is required by nbxSync **only when the proxy is in a group** (CH pair above). Japan devices use `kr-sel-p-zabp01` (no JP proxy).

### 2.3 Proxy self-monitoring

Proxy VMs get `role=Zabbix Proxy` via `netbox-sync` (`-ZABP\d+` pattern). Linux by agent comes from the platform Template Rule; ICMP Ping from the Agent Monitoring CG; **Remote Zabbix proxy health** from the role assignment (§7). Proxy VMs inherit the proxy assignment from their SiteGroup and poll their own localhost agent.

---

## 3. Server assignment (per country Site Group)

Path: **Site Group → Zabbix tab → Zabbix Servers → Add**

Create one assignment per country Site Group. Set a **proxy or a proxy group** — not both. Assignment always flows NetBox → Zabbix.

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

Path: **Zabbix → Configuration groups → Add**

Each group is one **transport + credential** profile. Different SNMPv3 users stay on separate groups. Which objects use which group: §5b.

| Name | Credential / port | Purpose |
|---|---|---|
| SNMP Monitoring | `MONITORING` MD5/DES | Extreme / Forti / AP / network roles |
| SNMP Monitoring (by tag) | `MONITORING-LINUX` SHA/AES | Opt-in Linux/Windows SNMP (tag `snmp`) |
| SNMP Monitoring (Huawei) | `LogicMonitor` SHA/AES | `HU-DEB-SAN01` (non-fleet SNMPv3) |
| SAP Agent+SNMP | Agent :10050 + `SAPUSER` MD5/DES | SAP HANA / SAP ME dual-plane (one CG) |
| Agent Monitoring | Agent :10050 | Default transport on country Site Groups |
| Agent Monitoring (SPACE) | Agent :10060 | Space Server role (camLine occupies 10050) |
| Dell iDRAC SNMP | `MONITORING-IDRAC` **SHA384/AES256** @ oob | ESXi Hypervisor (iDRAC9 7.x / iDRAC10) |
| Dell iDRAC SNMP (AES128) | `MONITORING-IDRAC` SHA384/AES128 @ oob | KR/CN ESXi exception hosts (iDRAC AES only) |
| Dell iDRAC SNMP (Legacy) | `MONITORING-IDRAC` SHA1/AES128 @ oob | Cohesity (C6420 fw 6.10 max) |

Three SNMPv3 iDRAC CGs by firmware tier — same `MONITORING-IDRAC` user, same passphrases, different protocols. **Server** stays on Site Group Agent Monitoring @ primary (real agent). iDRAC SNMPv3 user must be configured on each iDRAC (via iDRAC UI or racadm).

---

## 5. Host interfaces (on configuration groups)

Path: **Zabbix → Configuration groups → [group] → Host Interfaces → Add**

Put the interface on the CG, not on every device: the shape (agent port, SNMPv3 credentials, OOB flag) is shared; only the IP is per device. Sync fills primary IP or out-of-band IP at runtime. Leave the IP field empty on the definition.

**Type** selects Agent or SNMP. **Interface type** = Default for the primary interface of that kind.

### SNMPv3 profiles (do not mix)

Store **real passphrases** on the Host Interface (not `{$SNMP_AUTHPASS}` placeholders). **SNMP push community = True** so sync writes secret host macros and points the Zabbix interface at them.

| Profile | CG | Security name | Auth | Priv |
|---|---|---|---|---|
| Network | SNMP Monitoring | MONITORING | MD5 | DES |
| Linux | SNMP Monitoring (by tag) | MONITORING-LINUX | SHA1* | AES128 |
| SAP | SAP Agent+SNMP | SAPUSER | MD5 | DES |
| Huawei | SNMP Monitoring (Huawei) | LogicMonitor | SHA1* | AES128 |
| Dell iDRAC | Dell iDRAC SNMP | MONITORING-IDRAC | **SHA384** | **AES256** |
| Dell iDRAC (AES128) | Dell iDRAC SNMP (AES128) | MONITORING-IDRAC | **SHA384** | **AES128** |
| Dell iDRAC (Legacy) | Dell iDRAC SNMP (Legacy) | MONITORING-IDRAC | SHA1 | AES128 |
\*SHA1 is what the SNMPv3 security-level field offers for these profiles.

The three SNMPv3 iDRAC profiles share `MONITORING-IDRAC` — see §5.4.

### 5.1 SNMP Monitoring (network)

| Field | Value |
|---|---|
| Type | SNMP |
| Use OOB IP | No |
| + Network SNMPv3 profile | |

### 5.2 Agent Monitoring

| Field | Value |
|---|---|
| Type | Agent |
| Port | 10050 |
| TLS connect | No encryption |

### 5.3 SNMP Monitoring (by tag)

Same shape as §5.1 with the **Linux** SNMPv3 profile. Transport-only — no templates on the CG. OS templates come from Template Rules (§6.2) when the host has tag `snmp`.

### 5.4 Dell iDRAC SNMPv3 (three tiers by firmware)

| Piece | Where | Why |
|---|---|---|
| SNMPv3 :161, **Use OOB IP = Yes** | CG **Dell iDRAC SNMP** (SHA384/AES256) on role **ESXi Hypervisor** | Fleet iDRAC9 7.x / iDRAC10 |
| SNMPv3 :161, **Use OOB IP = Yes** | CG **Dell iDRAC SNMP (AES128)** (SHA384/AES128) on **Device** (KR/CN list) | iDRACs that reject AES256 priv |
| SNMPv3 :161, **Use OOB IP = Yes** | CG **Dell iDRAC SNMP (Legacy)** (SHA1/AES128) on role **Cohesity** | C6420 fw 6.10 tops out at SHA1/AES128 |
| Template | TemplateRules §6.3 — Manufacturer **Dell**∧ Server/ESXi/Cohesity → Dell iDRAC by SNMP | Storage stays on HPE MSA HTTP |

**Same `MONITORING-IDRAC` user, same passphrases** — only the protocol differs. Passphrases live on each iDRAC CG Host Interface.

**AES128 exceptions:** assign the AES128 CG on the **Device** so it wins over the role AES256 CG (plugin: one CG expands HostInterfaces). Do **not** leave durable per-device HostInterfaces — CG propagate stamps `ip=primary`, which beats `use_oob_ip` at sync. If an AES128 host still has a device-level Host Interface, delete it so sync expands from the CG (`use_oob_ip`).

AES128 hosts:

`cn-sha-p-esx11.sensirion.lokal`, `cn-sha-p-esx12.sensirion.lokal`, `cn-sha-p-esx13.sensirion.lokal`, `kr-sel-p-esx11.sensirion.lokal`, `kr-sel-p-esx12.sensirion.lokal`, `kr-sel-p-esx13.sensirion.lokal`

**Server role** stays on Site Group **Agent Monitoring** @ primary (real Zabbix agent); iDRAC template via TemplateRule only.

### 5.5 SAP Agent+SNMP (two interfaces)

SAP agent templates need Agent; hardware SNMP uses `SAPUSER`. Plugin rule: **one CG wins** — two separate CGs on the same role would not dual-plane.

| Interface | Type | Port / OOB | Credential |
|---|---|---|---|
| Primary | Agent | 10050, Use OOB = No | — |
| SNMP | SNMP | 161, Use OOB = No | SAP profile (`SAPUSER`, MD5/DES) |

### 5.6 SNMP Monitoring (Huawei)

Huawei SNMPv3 profile (`LogicMonitor` SHA/AES). Passphrases live on that CG’s Host Interface.

### 5.7 Agent Monitoring (SPACE)

| Field | Value |
|---|---|
| Type | Agent |
| Port | **10060** |
| TLS connect | No encryption |

---

## 5b. Configuration group assignments

Path: **Zabbix → Configuration groups → [group] → Assignments → Add**  
(or Site Group / Device Role / Tag → Zabbix tab)

Without these assignments, the group’s interfaces are not applied during sync.

### Agent Monitoring → each country Site Group

| Configuration group | Assigned to |
|---|---|
| Agent Monitoring | Site Group CH / HU / JP / KR / NL / US / CN |

**Pure / Dell Storage** stay on this Agent default (HTTP templates). **Synology** gets SNMP via Manufacturer CG below. **Huawei** (`HU-DEB-SAN01`) uses the dedicated Huawei CG on the device — not Manufacturer SNMP.

### SNMP Monitoring → network Device Roles

| Configuration group | Assigned to |
|---|---|
| SNMP Monitoring | Switch Core / Dist / Access / Mgmt |
| SNMP Monitoring | Access Point |
| SNMP Monitoring | Firewall |
| SNMP Monitoring | Network Device |
| SNMP Monitoring | Virtual Appliance |

**Do not** assign role Storage here (Pure/Dell HTTP would inherit SNMP). Synology uses Manufacturer assignment below.

### Manufacturer → SNMP (storage exceptions)

| Configuration group | Assigned to |
|---|---|
| SNMP Monitoring | Manufacturer **Synology** |

Manufacturer CG wins over Site Group Agent. Pure Storage and Dell Storage stay Agent/HTTP. **Do not** assign fleet SNMP Monitoring on Manufacturer Huawei — that would use wrong `MONITORING` creds.

### Server / Cohesity / SPACE / SAP roles

| Configuration group | Assigned to |
|---|---|
| Dell iDRAC SNMP (SHA384/AES256) | ESXi Hypervisor |
| Dell iDRAC SNMP (AES128) | KR/CN exception hosts (per-device) |
| Dell iDRAC SNMP (Legacy) (SHA1/AES128) | Cohesity |
| Agent Monitoring (SPACE) | Space Server |
| SAP Agent+SNMP | SAP HANA |
| SAP Agent+SNMP | SAP ME |

**Server** stays on Site Group Agent Monitoring.

### Huawei device → SNMP Monitoring (Huawei)

| Configuration group | Assigned to |
|---|---|
| SNMP Monitoring (Huawei) | Device **`HU-DEB-SAN01`** |

Overrides Site Group Agent. Credentials are on the CG Host Interface (§5.6).

### Tag opt-ins

| Configuration group | Assigned to | Operator action |
|---|---|---|
| SNMP Monitoring (by tag) | NetBox tag **`snmp`** | Tag the Device/VM — no per-host CG row |

### Cohesity Appliance role → SNMP Monitoring

Cohesity VMs (role=Cohesity Appliance) inherit **SNMP Monitoring**. Physical Cohesity nodes (role=Cohesity) get **Dell iDRAC SNMP (Legacy)** (SNMPv3 SHA1/AES128 @ oob_ip) + TemplateRule Dell ∧ Cohesity.

---

## 6. Template Rules

Path: **Zabbix → Template Rules → Add**

**How matching works:** every **enabled** rule that matches is applied (they merge). `priority` is only evaluation order — it does **not** suppress another rule’s different template. Platform regex is `re.search` (substring, case-insensitive). Empty role / tags / manufacturer = any.

Use Template Rules for things that follow **platform** or **vendor**. Do not use them as a role allowlist (that does not scale). ICMP and proxy health are **not** Template Rules — see §6.4 and §7.

First create these hostgroups (**Zabbix → Hostgroups → Add**). Name and value are the same; leave description empty:

- `OS/Windows` — attached by the Windows / SNMP Windows rules
- `OS/Linux` — attached by the Linux / SNMP Linux rules
- `OS/Network` — attached by Extreme / Forti platform rules
- `OS/VMware` — assigned on Device Role **ESXi Hypervisor** (not a Template Rule)

### 6.1 Platform → OS / network OS

| Name | Pattern | Role pattern | Template | Hostgroup | Enabled |
|---|---|---|---|---|---|
| Windows catch-all | `Windows` | — | Windows by Zabbix agent | OS/Windows | Yes |
| Linux | `Linux\|Ubuntu\|Debian\|CentOS\|Alma\|SUSE\|Arch` | `^(?!vCenter$|SAP HANA$).*` | Linux by Zabbix agent | OS/Linux | Yes |
| Extreme EXOS | `EXOS` | — | Extreme EXOS by SNMP | OS/Network | Yes |
| Extreme VOSS | `VOSS` | — | Extreme VOSS by SNMP | OS/Network | Yes |
| Extreme IQ Engine | `IQ ENGINE` | — | Extreme IQ Engine by SNMP | OS/Network | Yes |
| FortiOS | `FORTIOS\|FortiOS` | — | FortiGate by SNMP | OS/Network | Yes |
| FortiAnalyzer/Manager | `FortiAnalyzer\|FortiManager` | — | Network Generic Device by SNMP | OS/Network | Yes |

**vCenter / SAP HANA exclusion:** vCenter VMs use platform `VMware Photon OS/Linux 4.0`, which matches the Linux pattern (`Linux`). Role **SAP HANA** is openSUSE and would also match. Rules merge, so without a role filter they would get **Linux by Zabbix agent** on top of the intended pack. `role_pattern` `^(?!vCenter$|SAP HANA$).*` means any role except those two:

- role **Server** / … + Linux-like platform → Linux by agent
- role **vCenter** + Photon OS/Linux → Linux rule does **not** apply → VMware FQDN + ICMP Ping from the Agent CG only
- role **SAP HANA** + SUSE/Linux → Linux rule does **not** apply → **Linux by SNMP** (role assignment, `SAPUSER` via CG SAP Agent+SNMP) + **SAP template from Sensirion** (ST22 only). No Linux by agent. OS/Linux hostgroup is assigned on the role. `--apply-sap` writes this exclusion and disables ping on Linux by SNMP so ICMP stays on the CG.

### 6.2 Tag overlays

Use together with the matching configuration group for transport.

| Name | Pattern | Template | Hostgroup | Require tags |
|---|---|---|---|---|
| SNMP Linux (tag) | *(same Linux pattern as §6.1)*; role `^(?!SAP HANA$).*` | Linux by SNMP | OS/Linux | `snmp` |
| SNMP Windows (tag) | `Windows` | Windows by SNMP | OS/Windows | `snmp` |
| Oracle (tag) | `.*` | Oracle by Zabbix agent 2 | — | `oracle` |

Tag `snmp` also selects CG **SNMP Monitoring (by tag)** (§5b). The agent OS rule still matches on non-SAP Linux; HostSync **drops** the agent template because the host has only an SNMP interface. Role **SAP HANA** is excluded from both the Linux agent rule and this SNMP Linux tag rule (wrong CG). HANA OS is **Linux by SNMP** assigned on the role, riding CG **SAP Agent+SNMP**.

Tag `oracle` does **not** change transport. Pattern `.*` + require tag `oracle` → **Oracle by Zabbix agent 2** on that Device/VM, merged with whatever OS template the platform rule already attached. Windows with Oracle: tag the host `oracle` (keeps Windows by agent). Space Server with Oracle: same — tag the Device/VM; it stays on **Agent Monitoring (SPACE)** (:10060). The Oracle template needs an **Agent** interface (SPACE has one). SNMP-only hosts drop it. Dedicated DB servers also get Oracle from role **Database** (§7) — the tag is the overlay for any other role.

### 6.3 Manufacturer ∧ role (vendor products)

Manufacturer Dell alone would put iDRAC on Dell storage — always AND with role.

| Name | Pattern | Role pattern | Manufacturer | Template |
|---|---|---|---|---|
| Dell iDRAC | `.*` | `^(Server\|Cohesity\|ESXi Hypervisor)$` | Dell | Dell iDRAC by SNMP |
| Pure Storage (HTTP) | `.*` | — | Pure Storage | Pure Storage FlashArray v2 by HTTP |
| Dell Storage (HTTP) | `.*` | `^Storage$` | Dell | HPE MSA 2060 Storage by HTTP |
| Huawei OceanStor (SNMP) | `.*` | `^Storage$` | Huawei | Huawei OceanStor Dorado by SNMP |
| Synology DiskStation (SNMP) | `.*` | `^Storage$` | Synology | Synology DiskStation SNMPv3 |
| Synology Storage ICMP | `.*` | `^Storage$` | Synology | ICMP Ping |

**Dell Storage:** rule name **Dell Storage (HTTP)** — MSA HTTP template on Dell Storage (not manufacturer HPE).

**Huawei OceanStor:** transport is device CG **SNMP Monitoring (Huawei)** on `HU-DEB-SAN01`. No Huawei ICMP rule (OceanStor already has `icmpping`).

**Synology ICMP:** the DiskStation template has no `icmpping`. Fleet SNMP Monitoring must **not** get ICMP Ping (switches would collide). This one manufacturer rule is the exception.

### 6.4 ICMP Ping (not a Template Rule)

Agent OS templates do not include `icmpping`. Extreme / Forti / Huawei SNMP templates do — attaching the ICMP Ping **template** there creates duplicate keys and Zabbix rejects the host.

ICMP Ping is therefore assigned on the **configuration group** that already means “this plane has no icmpping”:

| Configuration group | Who gets ICMP |
|---|---|
| Agent Monitoring | Everyone on the Site Group Agent default (new roles included) |
| Agent Monitoring (SPACE) | Space Server |
| SAP Agent+SNMP | SAP HANA / SAP ME |
| SNMP Monitoring (by tag) | Hosts tagged `snmp` (Linux/Windows by SNMP have no icmpping) |

Do **not** put ICMP Ping on fleet **SNMP Monitoring**, on iDRAC CGs, or on **Site Groups / Device Roles / Tags**. A Site Group assignment is inherited by every switch and collides with Extreme / Forti / Huawei `icmpping` (Zabbix rejects the host). Only the four CGs in the table above.

A new Agent-class Device Role needs **no ICMP edit**. A new Switch* role uses SNMP Monitoring and must **not** get this template.

---

## 7. Template assignments (Role)

Path: **Zabbix → Templates → [template] → Assigned objects → Add**  
(or Device Role → Zabbix tab)

Assignments **merge** with Template Rules from §6. Do **not** assign Network Generic on Switch* or Access Point (those already get Extreme/Forti from §6). Manufacturer-scoped storage / iDRAC rules are in §6.3.

Set each template’s interface requirement (Agent / SNMP / ANY) to match the transport the host will have.

| Template | Assigned to | Notes |
|---|---|---|
| MSSQL by Zabbix agent 2 | Device Role MSSQL | |
| MSSQL by Zabbix agent 2 | Device Role MSSQL Query Server | |
| MSSQL Observability | Device Role MSSQL, MSSQL Query Server | Companion named-instance LLD, inventories, and 7.0 host prototypes (stock Agent 2 on each child). Zerotouch assigns **only after** YAML import; no nbxsync change |
| VMware FQDN | Device Role vCenter | **Only** on vCenter — not on ESXi platforms. Secrets via §11.3 |
| GitLab by HTTP | Device Role GitLab | |
| Linux by SNMP | Device Role Virtual Appliance | Baseline if no platform rule matches |
| Linux by SNMP | Device Role SAP HANA | HANA OS (CPU cores, disk IO, FS, RAM, NICs). `--apply-sap` disables its `icmpping` so ping stays on CG SAP Agent+SNMP. Do not use the snmp-tag rule (wrong CG). |
| Network Generic Device by SNMP | Device Role Network Device | Fallback only |
| FortiGate by SNMP | Device Role Firewall | Also via FortiOS platform rule |
| Tableau Bridge by Zabbix agent `(stub)` | Device Role Tableau | Assign if the template exists on the Zabbix server |
| CellMap by Zabbix agent `(stub)` | Device Role CellMap | Assign if the template exists |
| Oracle by Zabbix agent 2 | Device Role Database | Also tag rule §6.2 |
| SAP template from Sensirion | Device Role SAP HANA (openSUSE) | Import with `--apply-sap`. **ST22 / sapcontrol only**. OS is Linux by SNMP on this role. Do not assign Linux by agent. `Z_GET_ST22` URL macros go on device **CH-STA-P-SH01** only (not this role). sapcontrol UserParameter + `web.certificate.get` stay optional until an agent exists. Interface req AGENT. |
| SAP ME from Sensirion | Device Role SAP ME (Windows) | Same `--apply-sap`. No UCD SNMP. PowerShell sapcontrol + `proc.num[jstart.exe]` + cert/port default **50001** (LM `ssl.ports` on ch-sta-p-me05). Interface req AGENT. OS stays on Windows by agent. |
| Acronis Cyber Protect Cloud by HTTP | Device Role Acronis Management | Assign if the template exists |
| SCCM by Zabbix agent `(stub)` | Device Role SCCM | Assign if the template exists |
| Remote Zabbix proxy health | Device Role Zabbix Proxy | ICMP comes from the Agent Monitoring CG (§6.4) |

Pure / Dell / Huawei / Synology storage and Dell iDRAC: §6.3 (and tag `oracle` → §6.2).  
One-off templates on a single host (e.g. AS Java): assign on the Device, not the role.

### 7.1 Extreme capability templates

Assigned on the **role**, not on the platform Template Rule. Enablement order: *[Extreme switching — Confluence TBD]*.

| Template | Assigned to |
|---|---|
| Extreme Port Speed Expect by SNMP | Switch Core / Dist / Access / Mgmt |
| Extreme Routing by SNMP | Switch Core, Switch Dist |

---

## 8. Hostgroups

Path: **Zabbix → Hostgroups → Add**, then assignments on each hostgroup or from the Site Group / tag Zabbix tab.

### 8.1 Sites

| Name | Value | Assign to |
|---|---|---|
| Sites | `Sites/{{ object.site.group.get_ancestors(include_self=True) \| map(attribute="name") \| join("/") }}/{{ object.site.name }}` | Site Groups CH, HU, JP, KR, NL, US, CN |

`get_ancestors(include_self=True)` walks the Site Group tree so the Zabbix path always includes the country:

| NetBox layout | Rendered hostgroup | Parents created |
|---|---|---|
| Site under campus CH-STA (parent CH) | `Sites/CH/CH-STA/CH-STA-L42` | `Sites`, `Sites/CH`, `Sites/CH-STA` |
| Site directly under country CH | `Sites/CH/<site>` | `Sites`, `Sites/CH` |

Hosts stay members of the **leaf** only. Parent groups such as `Sites/CH` exist for nested membership; do not also put hosts in a flat country group. A preview error when viewing the assignment on a Site Group is cosmetic and does not affect sync.

### 8.2 Roles

| Name | Value | Assign to |
|---|---|---|
| Roles | `Roles/{{ object.role.name }}` | Site Groups CH, HU, JP, KR, NL, US, CN |

Assigned on each country Site Group so every device under that country inherits the Roles template; the role *name* still comes from the device.

### 8.3 OS hostgroups

Created in §6. Membership: platform Template Rules for OS/Windows, OS/Linux, OS/Network. **OS/VMware** is assigned on Device Role **ESXi Hypervisor**.

### 8.4 Priority / Critical

**NetBox tag** `critical` on the Device/VM. The hostgroup assignment sits on that tag (not on each device). Sync puts those hosts in Zabbix hostgroup `Priority/Critical`.

| Name | Value | Assign to |
|---|---|---|
| Priority/Critical | `Priority/Critical` | NetBox tag `critical` |

---

## 9. Tags

Two tag systems:

1. **NetBox tags** — already on devices/VMs/roles in inventory. Sync reads them as inputs.
2. **Zabbix tags** — written on the Zabbix host during sync from Jinja (§9.1, §9.2).

### 9.0 NetBox tags (inputs)

Create NetBox tags `critical`, `snmp`, and `onboarding` if they are missing. `oracle` is operator-created when needed.

| NetBox tag | Effect during sync | Typical scope |
|---|---|---|
| `critical` | Hostgroup `Priority/Critical` (§8.4) | Device/VM |
| `snmp` | Transport → **SNMP Monitoring (by tag)** + Linux/Windows by SNMP templates | Device/VM |
| `oracle` | **Oracle by Zabbix agent 2** on that Device/VM (merges with OS template; any role, including Space Server / Windows) | Device/VM |
| `onboarding` | Sync hold — inherits Zabbix exclude via Tag assignment (§9.3). **Remove this NetBox tag to start monitoring.** | Device/VM |

Permanent never-monitor: Zabbix tag `do_not_monitor` on the Device Role.

NetBox tags are **not** copied into Zabbix as host tags; they drive interfaces, templates, hostgroups, and (for `onboarding`) exclusion. Zabbix tags are separate (§9.1–§9.2).

### 9.1 Zabbix host tags — Environment (Jinja on Site Groups)

nbxSync owns the tag definition and Site Group assignment. At sync, Jinja renders a per-host value (e.g. `Production`) onto the Zabbix host.

Environment is encoded in the hostname; no second taxonomy.

| Tag | Value | Assign to |
|---|---|---|
| environment | *(template below)* | Site Groups CH … CN |

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

**Failure mode:** names that do not match the `-p-` / `-d-` / … conventions resolve to **`Unknown`**. That is silent. **Extreme switches** (`CH-STA-…-CORE01`, `…-MGMT01`, `…-ACCE01`, …) normally have no `-p-` token — `environment=Unknown` on them is expected, not a sync bug.

### 9.2 Zabbix host tags — Cluster (auto-generated, Jinja on Clusters)

| Tag | Value | Assign to |
|---|---|---|
| cluster | `{{ object.cluster.name }}` | each Cluster |

### 9.3 Exclusion — `do_not_monitor` (permanent and controlled holds)

Plugin `exclude_tag` = `do_not_monitor` (§12) — one setting. Same nbxSync **Zabbix** tag; two places you assign it:

| Zabbix tag | Value | Assign to | Operator day-2 |
|---|---|---|---|
| do_not_monitor | *(empty)* | **Device Role** — Messpc, VDI | Permanent — leave on the role. |
| do_not_monitor | *(empty)* | **NetBox Tag `onboarding`** (Organization → Tags → **onboarding** → Zabbix tab → Tags) | Temporary wave or controlled release hold. |

**Current production state (2026-08-25):** all 21 `Sd Wan Socket` devices are
released and their ICMP hosts are live. None carries `onboarding` or the legacy
inventory `do_not_monitor` tag, and the role-level `do_not_monitor` assignment
is absent.

For a new or replacement Socket, add NetBox inventory tag `onboarding` before
its first nbxSync run. It remains excluded until its primary IP and proxy path
are ready; removing `onboarding` from that one Socket starts monitoring it.
The role supplies `component=cato` and `monitoring_domain=cato_socket` host
tags, while inherited Agent Monitoring supplies the one stock `ICMP Ping`
template.

nbxSync resolves assignments on a NetBox Tag onto every Device/VM that carries
that tag. The generic onboarding sweep must not tag or untag controlled-release
Socket devices; use the idempotent hold/release command in
[`runbooks/onboarding.md`](runbooks/onboarding.md) for a new or replacement
Socket.

Sync **skips** excluded objects (no host/interfaces/templates). An existing
Zabbix host from a prior sync is **deleted**.

Refresh the separate account collector with
`configure_nbxsync_network.py --apply-cato` — it does not mutate Socket roles
or hosts. The one-time `--enable-cato --mutate-netbox` migration is complete;
do **not** rerun it for a normal collector refresh.

Do **not** put Zabbix `do_not_monitor` on role Server (or a Site Group) for
waves — you cannot open a single child while the parent excludes.

## 10. Host inventory

Path: Site Group → Zabbix tab → Host Inventory → Add

Same Jinja mapping on every country Site Group; values come from the NetBox object.

| Field | Value |
|---|---|
| Inventory mode | Automatic |
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

Assign to Site Groups: CH, HU, JP, KR, NL, US, CN.

Fields such as `os` and `os_full` are filled by Zabbix templates when inventory mode is Automatic.

---

## 11. Macros

Path: **Zabbix → Macros → Add** (definition on Zabbix Server, then Macro Assignment on the role / or assign from the Role Zabbix tab)

Class-wide thresholds and Extreme port filters sit on the role. Application secrets (VMware, Pure Storage, MSSQL): §11.3.

### 11.1 Extreme switch macros (role)

**Path:** Zabbix → Macros → Add, then Macro Assignment on each Switch* Device Role (or Role → Zabbix tab).

Set all three on every Switch Core / Dist / Mgmt / Access role. Core / Dist / Mgmt: all physical/LAG except `X…`. Access: labelled opt-in only (`USW` `US` `UP` `MON` `UW` `TMON`). `{$NET.IF.IFTYPE.MATCHES}` `^(6|161)$` is physical + LAG (drops EXOS VLAN ifaces).

| Macro | Value | Device Role |
|---|---|---|
| `{$NET.IF.IFALIAS.MATCHES}` | `.*` | Switch Core / Dist / Mgmt |
| `{$NET.IF.IFALIAS.NOT_MATCHES}` | `^X(-\|$)` | Switch Core / Dist / Mgmt |
| `{$NET.IF.IFTYPE.MATCHES}` | `^(6\|161)$` | Switch Core / Dist / Mgmt |
| `{$NET.IF.IFALIAS.MATCHES}` | `^(USW\|US\|UP\|MON\|UW\|TMON)(-\|$)` | Switch Access |
| `{$NET.IF.IFALIAS.NOT_MATCHES}` | `CHANGE_IF_NEEDED` | Switch Access |
| `{$NET.IF.IFTYPE.MATCHES}` | `^(6\|161)$` | Switch Access |

Port-label grammar and staged enablement: *[Extreme switching — Confluence TBD]*. Chassis temperature (`{$TEMP_WARN}` / `{$TEMP_CRIT}` / `{$TEMP_CRIT_LOW}`) is on the Extreme templates, not an nbxSync role macro.

### 11.2 Application / threshold macros (role)

| Macro | Value | Device Role |
|---|---|---|
| `{$CPU.UTIL.CRIT}` | 90 | MSSQL |
| `{$MSSQL.URI}` | `sqlserver://localhost:1433` | MSSQL, MSSQL Query Server |
| `{$MSSQL.LISTEN.HOST}` | `{{ object.primary_ip4.address.ip }}` | MSSQL, MSSQL Query Server |
| `{$CPU.UTIL.CRIT}` | 80 | Server |
| `{$MEM.UTIL.CRIT}` | 85 | VDI |
| `{$VMWARE.URL}` | `https://{{ object.primary_ip4.address.ip }}/sdk` | vCenter |


### 11.3 Application secrets (per-device / per-type / per-site)

Each macro is defined as a server-level **ZabbixMacro** (on ZabbixServer) with a **ZabbixMacroAssignment** on the target object (Device, Device Type, VM, or DeviceRole). The assignment carries the secret value and is resolved during sync via the inheritance chain. HostSync renders Jinja with `object` = the host, so a Device Type assignment can still use `object.primary_ip4`.

#### Pure Storage API token + URL (per-device)

Each Pure array has its own API token and base URL. Macro assignments are on each **Device** (not the manufacturer).

| Macro | Target | Type | Value |
|---|---|---|---|
| `{$PURE.FLASHARRAY.API.TOKEN}` | Device (per array) | Secret | API token from the array |
| `{$PURE.FLASHARRAY.API.URL}` | Device (per array) | Text | `https://<primary_ip>/` (from device IP) |

Arrays with their own token: `hu-deb-san11`, `kr-sel-san11`, `cn-sha-san11`, `ch-zrh-zh4-san01`, `ch-zrh-zh4-san02`, `ch-zrh-zh5-san01`, `ch-zrh-zh5-san02`.

#### Dell iDRAC SNMPv3 credentials (shared on CG)

Same `MONITORING-IDRAC` user, same passphrases on all three CGs — only the protocol differs. CG list and assignments: §5.4.

Passphrases live on each iDRAC CG Host Interface. The iDRAC SNMPv3 user must be configured on each iDRAC (via iDRAC UI or racadm).

#### HPE MSA API credentials (Device Type)

Dell Storage arrays (HPE MSA 2060) use the HPE MSA HTTP template — REST API, not SNMP. Macro assignments are on the **Device Type** (the MSA 2060 type), not each Device, manufacturer Dell, or Agent Monitoring. HostSync evaluates `object` as that array, so HOST is the device’s primary IPv4. Do **not** wrap HOST in `https://` — scheme/port stay on the template macros. A leftover **Device**-level assignment wins over Device Type; delete it if one remains.

Each array needs **primary IPv4** set (controller mgmt / VIP, not iSCSI/FC). An IP change in NetBox reaches Zabbix on HostSync of that host.

| Macro | Target | Type | Value |
|---|---|---|---|
| `{$HPE.MSA.API.HOST}` | Device Type | Text | `{{ object.primary_ip4.address.ip }}` |
| `{$HPE.MSA.API.USERNAME}` | Device Type | Text | Shared API user |
| `{$HPE.MSA.API.PASSWORD}` | Device Type | Secret | Shared API password |

Arrays of that Device Type include `CN-SHA-P-STOD01`.

#### VMware vCenter SSO credentials (per-VM)

SSO domains differ per site. The macro assignment is on each **VM** (not the role).

| Macro | Target | Type |
|---|---|---|
| `{$VMWARE.USERNAME}` | VM (per vCenter) | Secret |
| `{$VMWARE.PASSWORD}` | VM (per vCenter) | Secret |

| vCenter | SSO domain |
|---|---|
| `ch-sta-p-vcsa02` | `VCENTER-SSO.SENSIRION` |
| `ch-sta-p-vcsa10` | `VCENTER-SSO.SENSIRION` |
| `hu-deb-p-vcsa01` | `HU.VSPHERE.LOCAL` |
| `kr-sel-p-vcsa01` | `KR.VSPHERE.LOCAL` |
| `cn-sha-p-vcsa01` | `cn.vsphere.lokal` |

Username format: `<SSO_DOMAIN>\LogicMonitor` (e.g. `VCENTER-SSO.SENSIRION\LogicMonitor`).

#### MSSQL (Agent 2; URI + per-host login)

Stock **MSSQL by Zabbix agent 2** uses `{$MSSQL.URI}` / `{$MSSQL.USER}` / `{$MSSQL.PASSWORD}`, not ODBC DSN. Set the **parent** URI once on the role (`sqlserver://localhost:1433` for a default instance). Named instances do **not** use that URI: companion LLD builds `{#MSSQL.URI}=sqlserver://{$MSSQL.LISTEN.HOST}/{#MSSQL.INSTANCE}` (no port). Set `{$MSSQL.LISTEN.HOST}` on the same roles to Jinja `{{ object.primary_ip4.address.ip }}` so dedicated-IP instances (`ListenOnAllIPs=0`, loopback off) still resolve via SQL Browser on the Windows host. Do **not** put instance names or VIP:1433 URIs in NetBox. Loopback-only **box**: Device `{$MSSQL.LISTEN.HOST}=localhost` then HostSync. VIP-only **one instance**: set `{$MSSQL.URI}` on that Zabbix child (`sqlserver://<vip>/<Instance>`, no port) — LLD can reset it; details in the notes. Put the password (and user if the login name is not fleet-wide) on the **Device or VM**. Do **not** create `{$MSSQL.DSN:"PITDV02"}` context rows — Agent 2 does not read DSN, and named instances are LLD ([notes/mssql-agent2-instances.md](../../zabbix/notes/mssql-agent2-instances.md)). Import companion **MSSQL Observability** for `MSSQL$*` instances. On Cloud 7.0 the companion creates child hosts (`{#MSSQL.PARENT}-mssql-{#MSSQL.INSTANCE}`) with stock Agent 2 so per-database graphs work; children join **only** host group `MSSQL instances` (grant that group to the same user groups as `Roles/MSSQL` / `Roles/MSSQL Query Server`). Do **not** create hostname or `Roles/MSSQL/{parent}` group prototypes. Optional `{$MSSQL.PARENT.HOST}` = `{{ object.name }}` on the role when WMI `SystemName` differs from the Zabbix host (child **host names**, not groups). Parent inventories stay in Latest data. HostSync the canary Windows host after YAML import so Jinja renders `LISTEN.HOST` — do not HostSync the fleet from the template import, and do not sync hosts named like `PITDV02`. Stock **MSSQL: Service is unavailable** (TCP 1433 from the proxy) is a false Disaster when plugin items have data; disable **Service's TCP port state** on that parent or child. YAML cannot mute inherited stock triggers. After importing Observability with the version-item heartbeat removed, parent `MSSQL [<instance>]: no version data for 15m` should recover on a stable version. On a named-instance child, Latest data blank **Get …** rows are stock `history: 0` masters — hide `component: raw` and count **Not supported**.

| Macro | Target | Type | Value |
|---|---|---|---|
| `{$MSSQL.URI}` | DeviceRole: MSSQL **and** MSSQL Query Server | Text | `sqlserver://localhost:1433` (default instance on the parent) |
| `{$MSSQL.LISTEN.HOST}` | DeviceRole: MSSQL **and** MSSQL Query Server | Text | `{{ object.primary_ip4.address.ip }}` — named-instance plugin host (no port). **Whole-box** exception: Device assignment `localhost` (loopback-only) or one IPv4, then HostSync that Windows host. **One instance VIP-only** (does not listen on `primary_ip4`): do **not** put the VIP in NetBox — set `{$MSSQL.URI}=sqlserver://<vip>/<Instance>` (no port) on that Zabbix **child**. Details: [notes/mssql-agent2-instances.md](../../zabbix/notes/mssql-agent2-instances.md) (Override when loopback-only or VIP-only) |
| `{$MSSQL.USER}` | DeviceRole: MSSQL **or** Device if the name differs | Secret | SQL login |
| `{$MSSQL.PASSWORD}` | Device (per MSSQL host) | Secret | that host’s password |
| `{$MSSQL.INSTANCE.DISCOVERY.MIN}` | Device, optional | Text | e.g. `5` on a named-instance box; template default `0` |
| `{$MSSQL.PARENT.HOST}` | DeviceRole: MSSQL **and** MSSQL Query Server, optional | Text | `{{ object.name }}` — child host names match the Zabbix host when WMI `SystemName` differs |

Leftover role `{$MSSQL.DSN}` is ODBC-era; ignore for Agent 2. Companion filters `{$MSSQL.INSTANCE.MATCHES}` / `NOT_MATCHES` stay on the **template**, not in NetBox.

#### Huawei SAN01 (CG Host Interface — not a macro)

`HU-DEB-SAN01` uses non-fleet SNMPv3 (`LogicMonitor` SHA/AES). Credentials live on the **SNMP Monitoring (Huawei)** configuration-group Host Interface (§5.6), with the CG assigned on the **Device** (§5b). Do **not** put a per-device Host Interface or fleet SNMP Monitoring on that device.

If passphrases are unset, the OceanStor template will show "no data" until they are set on the CG Host Interface.

SNMPv3 auth/priv passphrases for other profiles are **not** global or role macros: they live on the SNMP Host Interface (§5) and are pushed as secret **host** macros when SNMP push community is True.

---

## 12. Plugin settings

Ask the NetBox administrator to set the following under the nbxsync plugin configuration (adjust intervals if your environment differs).

| Setting | Intended value |
|---|---|
| Source of truth for host, hostgroup, interface, template, tag, macro, proxy, maintenance | NetBox |
| Exclude tag | `do_not_monitor` (Zabbix tag — on permanent roles **and** on NetBox Tag `onboarding`) |
| Soft-state tag / value | `NO_ALERTING` / `1` (plugin host tag on paused VMs — monitoring packs interpret it) |
| Attach object identity tags | Yes (`nb_type` / `nb_id`) |
| Allow inherited deletion | No |
| Adopt existing Zabbix hosts | No |
| Device status → Zabbix | active → enabled; planned/staged → disabled; failed/offline/inventory/decommissioning → deleted |
| VM status → Zabbix | active → enabled; planned → enabled in maintenance; paused → enabled + soft-state tag; failed/offline → deleted |
| SNMP community / auth / priv macro names | `{$SNMP_COMMUNITY}`, `{$SNMP_AUTHPASS}`, `{$SNMP_PRIVPASS}` |

Keep Site / Site Group inheritance **after** role and platform in the inheritance order so country defaults do not override role SNMP or Dell iDRAC SNMP.

---

## 13. What a typical host should look like

| Object | Configuration group | Typical templates | Interfaces | Hostgroups |
|---|---|---|---|---|
| Linux server (role Server) | Agent Monitoring (Site Group) | Linux by agent + ICMP Ping (+ Dell iDRAC by SNMP if Dell w/ oob_ip) | Agent :10050 @ primary | Sites/CH/…, Roles/Server, OS/Linux |
| Linux or Windows VM | Agent Monitoring (from Site Group) | OS by agent (Template Rule) + ICMP Ping | Agent :10050 | Sites/CH/…, Roles/…, OS/… |
| SAP HANA (openSUSE) | **SAP Agent+SNMP** | **Linux by SNMP** (ping disabled) + **SAP template from Sensirion** (ST22) + ICMP Ping on the CG. **No** Linux by agent. `Z_GET_ST22` macros on **CH-STA-P-SH01** only | SNMP `SAPUSER` MD5/DES + Agent :10050 (unused until an agent is installed) | Sites/…, Roles/SAP HANA, OS/Linux |
| SAP ME (Windows) | **SAP Agent+SNMP** | Windows by agent + **SAP ME from Sensirion** + ICMP Ping | Agent :10050 + SNMP IF unused until walked | Sites/…, Roles/SAP ME, OS/Windows |
| Host with tag `snmp` only | SNMP Monitoring (by tag) via tag | Linux or Windows by SNMP + ICMP Ping | SNMP `MONITORING-LINUX` | Sites/CH/…, Roles/…, OS/… |
| EXOS Switch Core/Dist/Mgmt | SNMP Monitoring | Extreme EXOS by SNMP (+ role IFALIAS macros) | SNMP `MONITORING` MD5/DES | Sites/CH/…, Roles/Switch …, OS/Network |
| VOSS Switch Core/Access | SNMP Monitoring | Extreme VOSS by SNMP (**not** Network Generic) + role IFALIAS | SNMP `MONITORING` MD5/DES | Sites/CH/…, Roles/Switch …, OS/Network |
| Access Point | SNMP Monitoring | Extreme IQ Engine / platform template (**not** Network Generic) | SNMP `MONITORING` MD5/DES | Sites/CH/…, Roles/Access Point, OS/Network |
| Firewall | SNMP Monitoring | Platform/role template (FortiGate, …) | SNMP `MONITORING` MD5/DES | Sites/CH/…, Roles/…, OS/Network |
| Space Server | Agent Monitoring (SPACE) | OS by agent + ICMP Ping | Agent **:10060** | Sites/CH/…, Roles/Space Server, OS/… |
| Storage (Pure) | Agent Monitoring | Pure Storage FlashArray v2 by HTTP + ICMP Ping; macros `{$PURE.FLASHARRAY.API.TOKEN}` + `{$PURE.FLASHARRAY.API.URL}` | Agent / HTTP | Sites/…, Roles/Storage |
| Storage (Synology) | SNMP Monitoring → Manufacturer Synology | Synology DiskStation SNMPv3 + ICMP Ping | SNMP `MONITORING` | Sites/…, Roles/Storage |
| Storage (Huawei) `HU-DEB-SAN01` | **SNMP Monitoring (Huawei)** on Device | Huawei OceanStor Dorado by SNMP (has `icmpping`; no extra ICMP rule); LogicMonitor on **CG HI** | SNMP `LogicMonitor` | Sites/…, Roles/Storage |
| Storage (Dell) | Agent Monitoring | HPE MSA 2060 Storage by HTTP + ICMP Ping (rule **Dell Storage (HTTP)**); Device Type macros `{$HPE.MSA.API.HOST}` / `{$HPE.MSA.API.USERNAME}` / `{$HPE.MSA.API.PASSWORD}` (§11.3) | Agent / HTTP | Sites/CH/…, Roles/Storage |
| Cohesity physical (oob only) | Dell iDRAC SNMP (Legacy) (SHA1/AES128) | Dell iDRAC by SNMP | SNMP **v3 MONITORING-IDRAC** on oob | Sites/CH/…, Roles/Cohesity |
| ESXi hypervisor (Dell) | Dell iDRAC SNMP (SHA384/AES256) | Dell iDRAC by SNMP | SNMP **v3 MONITORING-IDRAC SHA384/AES256** on oob | Sites/…, Roles/ESXi Hypervisor, OS/VMware |
| vCenter | Agent Monitoring (Site Group) unless overridden | VMware FQDN + ICMP Ping (**no** Linux by agent — Linux rule excludes role vCenter); macros `{$VMWARE.USERNAME}` / `{$VMWARE.PASSWORD}` | Agent / HTTP(SDK) | Sites/…, Roles/vCenter |
| Zabbix Proxy | Agent Monitoring (Site Group) | Linux by agent + ICMP Ping + Remote Zabbix proxy health | Agent :10050 | Sites/…, Roles/Zabbix Proxy, OS/Linux |
| Any of the above + tag `critical` | unchanged | unchanged | unchanged | + Priority/Critical |
| VM on a cluster with no site | none | — | — | Not profiled until the VM or cluster has a site |

