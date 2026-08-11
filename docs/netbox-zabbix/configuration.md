# Configuration

GUI / API steps to create **nbxSync** objects on top of **existing NetBox inventory**.

**Folder map:** [`README.md`](README.md) · **Mental model:** [`architecture.md`](architecture.md) · **Day-2:** [`runbooks/day2.md`](runbooks/day2.md)

**Last verified:** 2026-08-06 (lab: NetBox 4.x / Zabbix 7.0.x). Update after a production re-check.

**Assumption:** NetBox inventory (Site Groups, roles, platforms, IPs, tags) already exists. This page only configures nbxSync.

*(Italic)* = fill in for your environment. Rows marked **placeholder** are intentional stubs — assign them now, refine template content closer to production.

### GUI map

Top menu **Zabbix**: Servers, Proxies, Proxy Groups, Templates, Macros, Tags, Hostgroups, Configuration groups, Maintenance, Template Rules. Most assignments and host interfaces are added from a parent’s **Zabbix** tab. Role templates → Role/Template page; `OS/*` membership → Template Rules.

---

## Before you start

Only integration prerequisites (inventory is already in NetBox):

- [ ] Required Zabbix templates exist (including **Extreme VOSS by SNMP** / **Extreme IQ Engine by SNMP** before enabling those Template Rules in §6 — see Extreme docs)
- [ ] SNMP / VMware / Pure / MSSQL secrets available (§5, §11.4)
- [ ] Role / platform / tag names in NetBox match the strings this document uses (rename here if NetBox naming differs)

---

## Initial build

Work top to bottom. After §12, jump to §13 and §15 (verification) before declaring the estate ready.

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

**Validate certs = True** means the NetBox host must trust the HTTPS certificate for that URL (OS trust store / corporate root). That is the **API** path only — unrelated to proxy↔cloud mTLS.

Proxy TLS certificates (files on proxy hosts, uploads in the Zabbix Cloud portal) are **not** configured in nbxSync. They live in the Sensirion proxy TLS / PKI runbook.

---

## 2. Proxies and proxy groups

Path: **Zabbix → Proxies → Add**, **Zabbix → Proxy Groups → Add**

**Why:** collectors are a geography decision. Binding proxy (or proxy group) on the country Site Group means every device under that country inherits the collector without per-host proxy rows. JP has no local proxy, so it uses KR; NL and US share the CH proxy group.

Names below must match the proxy objects that already exist in Zabbix Cloud. Proxy↔cloud mTLS is already done on the proxy hosts and in the cloud portal — in NetBox only register the proxies and set **TLS accept = Certificate** on active proxies so a later NetBox→Zabbix proxy sync does not wipe encryption back to “no encryption”.

### 2.1 Proxy group

| Name | Zabbix server | Description |
|---|---|---|
| CH Proxy Group | Zabbix Production | CH Stäfa pair (NL and US route through CH) |

### 2.2 Proxies

| Name | Mode | Proxy group | TLS accept | Local address | Local port |
|---|---|---|---|---|---|
| ch-sta-p-zabp01 | Active | CH Proxy Group | Certificate | *(proxy local IP / address required by group)* | 10051 |
| ch-sta-p-zabp02 | Active | CH Proxy Group | Certificate | *(proxy local IP / address required by group)* | 10051 |
| hu-deb-p-zabp01 | Active | — | Certificate | — | — |
| kr-sel-p-zabp01 | Active | — | Certificate | — | — |
| cn-sha-p-zabp01 | Active | — | Certificate | — | — |

Proxy IDs must match Zabbix. Do **not** store CA/leaf/key PEM material in NetBox or in the onboarding scripts.

### 2.3 Proxy self-monitoring (role = Zabbix Proxy)

Proxy VMs already exist in NetBox (e.g. `ch-sta-p-zabp01`, VM id 604). The `netbox-sync` `vm_role_relation` maps `-ZABP\d+` → `Zabbix Proxy`, so these VMs get `role=Zabbix Proxy` automatically. nbxSync then assigns:

- **Linux by Zabbix agent** — platform rule (Ubuntu matches `Linux` pattern)
- **ICMP Ping** — role-scoped TemplateRule (`role_pattern = ^Zabbix Proxy$`)
- **Remote Zabbix proxy health** — role-scoped TemplateRule (stock Zabbix template: proxy-internal process utilization, buffer state, data sender, config sync, version, uptime)

**Monitoring topology:**
- Proxy → Cloud: **active** (proxy connects outbound to `sensirion.zabbix.cloud` on TCP 10051, mTLS with Sensirion PKI certificates)
- Proxy → Agent: **passive** (proxy polls agents on TCP 10050)

Proxy VMs inherit the proxy assignment from their country SiteGroup — the proxy monitors itself. This is correct: the `Remote Zabbix proxy health` items are proxy-internal metrics (type 18) collected by the proxy daemon. The `Linux by Zabbix agent` items are polled from the proxy's own local agent. No circular dependency — a proxy can poll its own localhost agent while forwarding data to the cloud.

Note: `{$ZABBIX.PROXY.ADDRESS}` / `{$ZABBIX.PROXY.PORT}` macros (3 remote-stats items) are not set by nbxSync — configure them in Zabbix Cloud if the `zabbix[stats,…]` queue items are needed. The remaining 51 proxy health items work without macros.

| VM name | NetBox ID | Site | IP | Role | Templates (via nbxSync) |
|---|---|---|---|---|---|
| ch-sta-p-zabp01 | 604 | CH-ZRH-ZH4 | 10.0.104.235 | Zabbix Proxy | Linux by Zabbix agent, ICMP Ping, Remote Zabbix proxy health |
| ch-sta-p-zabp02 | 610 | CH-ZRH-ZH5 | 10.0.105.235 | Zabbix Proxy | Linux by Zabbix agent, ICMP Ping, Remote Zabbix proxy health |
| hu-deb-p-zabp01 | 608 | HU-DEB-NAG-DC | 10.40.100.235 | Zabbix Proxy | Linux by Zabbix agent, ICMP Ping, Remote Zabbix proxy health |
| kr-sel-p-zabp01 | 609 | KR-SEL-HAN | 10.30.100.235 | Zabbix Proxy | Linux by Zabbix agent, ICMP Ping, Remote Zabbix proxy health |
| cn-sha-p-zabp01 | 607 | CN-SHA-JIU | 10.31.100.235 | Zabbix Proxy | Linux by Zabbix agent, ICMP Ping, Remote Zabbix proxy health |

---

## 3. Server assignment (per country Site Group)

Path: **Site Group → Zabbix tab → Zabbix Servers → Add**

Create one assignment per country Site Group. Set a **proxy or a proxy group** — not both. Assignment always flows NetBox → Zabbix.

| Site Group | Proxy | Proxy group | Sync enabled |
|---|---|---|---|
| CH | — | CH Proxy Group | Yes |
| HU | hu-deb-p-zabp01 | — | Yes |
| JP | kr-sel-p-zabp01 | — | Yes |
| KR | kr-sel-p-zabp01 | — | Yes |
| NL | — | CH Proxy Group | Yes |
| US | — | CH Proxy Group | Yes |
| CN | cn-sha-p-zabp01 | — | Yes |

---

## 4. Configuration groups

Path: **Zabbix → Configuration groups → Add**

Each group is one **transport + credential** profile. Why these groups exist and which NetBox facts select them: [`architecture.md`](architecture.md). Different SNMPv3 users stay on separate groups.

| Name | Credential / port | Purpose |
|---|---|---|
| SNMP Monitoring | `MONITORING` MD5/DES | Extreme / Forti / AP / network roles |
| SNMP Monitoring (Linux) | `MONITORING-LINUX` SHA/AES | Opt-in Linux/Windows SNMP (tag `snmp`) |
| SNMP Monitoring (SAP) | `SAPUSER` (confirm auth/priv) | SAP HANA and SAP ME roles |
| Agent Monitoring | Agent :10050 | Default transport on country Site Groups |
| Agent Monitoring (SPACE) | Agent :10060 | Space Server role (camLine occupies 10050) |
| Server Agent+OOB | Agent :10050 + `MONITORING-DELL` SHA/AES @ oob | Dell iDRAC dual-plane servers |
| ESXi OOB iDRAC | `MONITORING-DELL` SHA/AES @ oob | ESXi hypervisors (BMC only; no agent) |
| OOB SNMP Only | `MONITORING` MD5/DES @ oob | Cohesity physical (no primary IP) |

---

## 5. Host interfaces (on configuration groups)

Path: **Zabbix → Configuration groups → [group] → Host Interfaces → Add**

**Why on the group, not on every device:** the interface *shape* (agent port, SNMPv3 credentials, OOB flag) is shared; only the IP is per device. Sync fills primary IP or out-of-band IP at runtime. Leave the IP field empty on the definition.

**Type** selects Agent or SNMP. **Interface type** = Default for the primary interface of that kind.

### SNMPv3 profiles (do not mix)

Store **real passphrases** on the Host Interface (not `{$SNMP_AUTHPASS}` placeholders). **SNMP push community = True** so sync writes secret host macros and points the Zabbix interface at them.

| Profile | CG | Security name | Auth | Priv |
|---|---|---|---|---|
| Network | SNMP Monitoring, OOB SNMP Only | MONITORING | MD5 | DES |
| Linux | SNMP Monitoring (Linux) | MONITORING-LINUX | SHA1* | AES128 |
| Dell iDRAC | Server Agent+OOB (SNMP side), ESXi OOB iDRAC | MONITORING-DELL | SHA1* | AES128 |
| SAP | SNMP Monitoring (SAP) | SAPUSER | *(confirm)* | *(confirm)* |

\*Source notes say "SHA"; Zabbix offers SHA1 and SHA256 — use **SHA1** until confirmed.

Common SNMP fields for all SNMP profiles: version **3**, bulk **True**, max repetitions **10**, security level **authPriv**, push community **True**, port **161**.

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

### 5.3 Server Agent+OOB (two interfaces)

**Why both on one group:** OS + BMC is one atomic server profile.

| Interface | Type | Port / OOB | Credential |
|---|---|---|---|
| Primary | Agent | 10050, Use OOB = No | — |
| BMC | SNMP | 161, Use OOB = **Yes** | Dell profile (MONITORING-DELL SHA/AES) |

If `oob_ip` is empty, the SNMP interface is skipped; the agent still syncs.

> Non-Dell BMC (iLO/XCC) is not covered by `MONITORING-DELL`. Add a separate CG later if needed.

### 5.4 SNMP Monitoring (Linux)

Same shape as §5.1 with the **Linux** SNMPv3 profile. Transport-only — no templates on the CG. OS templates come from Template Rules (§6.2) when the host has tag `snmp`.

### 5.5 OOB SNMP Only

Network SNMPv3 profile, Use OOB IP = **Yes**. Cohesity physical nodes.

### 5.5b ESXi OOB iDRAC

Dell SNMPv3 profile (`MONITORING-DELL`), Use OOB IP = **Yes**. **No Agent interface.**

**Why a separate group:** ESXi hosts are not dual-plane servers. Hardware health is iDRAC on `oob_ip`; hypervisor/VM/cluster metrics come from **vCenter** (VMware FQDN + LLD). Do not put VMware FQDN on ESXi platforms.

### 5.6 SNMP Monitoring (SAP)

SAP SNMPv3 profile (`SAPUSER` — confirm auth/priv before production). Transport-only; application templates are separate (§7).

### 5.7 Agent Monitoring (SPACE)

| Field | Value |
|---|---|
| Type | Agent |
| Port | **10060** |
| TLS connect | No encryption |

### One-off overrides

| Case | How |
|---|---|
| `HU-DEB-SAN01` (Huawei, SNMPv3 user `LogicMonitor` SHA/AES) | Per-device `ZabbixHostInterface` — TemplateRule (§6.3) links the template; credential differs from fleet CGs so transport stays on the device. |

---

## 5b. Configuration group assignments

Path: **Zabbix → Configuration groups → [group] → Assignments → Add**  
(or Site Group / Device Role / Tag → Zabbix tab)

Without these assignments, the group’s interfaces are not applied during sync.

### Agent Monitoring → each country Site Group

| Configuration group | Assigned to |
|---|---|
| Agent Monitoring | Site Group CH / HU / JP / KR / NL / US / CN |

**Pure / Dell Storage** stay on this Agent default (HTTP templates). **Synology / Huawei** get SNMP via Manufacturer CG (§5b) — not the Storage role.

### SNMP Monitoring → network Device Roles

| Configuration group | Assigned to |
|---|---|
| SNMP Monitoring | Switch Core / Dist / Access / Mgmt / **Hybrid** |
| SNMP Monitoring | Access Point |
| SNMP Monitoring | Firewall |
| SNMP Monitoring | Network Device |
| SNMP Monitoring | Virtual Appliance |

**Do not** assign role Storage here (Pure/HPE would inherit SNMP). Synology / Huawei use Manufacturer assignment below.

### Manufacturer → SNMP (storage exceptions)

| Configuration group | Assigned to |
|---|---|
| SNMP Monitoring | Manufacturer **Synology** |
| SNMP Monitoring | Manufacturer **Huawei** |

Manufacturer CG wins over Site Group Agent. Pure Storage and HPE stay Agent/HTTP. If a Huawei box uses non-fleet SNMPv3 (`LogicMonitor`), keep the per-device HostInterface override (§5 one-off).

### Server / Cohesity / SPACE roles

| Configuration group | Assigned to |
|---|---|
| Server Agent+OOB | Server |
| OOB SNMP Only | Cohesity |
| Agent Monitoring (SPACE) | Space Server |
| SNMP Monitoring (SAP) | SAP HANA |
| SNMP Monitoring (SAP) | SAP ME |

### ESXi platforms → OOB iDRAC (role = ESXi Hypervisor)

| Configuration group | Assigned to |
|---|---|
| ESXi OOB iDRAC | Platform name matching `ESXi\|VMware ESX` AND role **ESXi Hypervisor** |

ESXi devices are migrated from role `Server` to `ESXi Hypervisor` by the zerotouch script (`--mutate-netbox`). This prevents inheriting `Server Agent+OOB` (which adds an unwanted Agent interface on primary IP — ESXi hosts have no Zabbix agent). The ESXi OOB iDRAC CG provides SNMP-only on oob_ip with `MONITORING-DELL` SHA/AES credentials. Dell iDRAC template comes from TemplateRule `Dell iDRAC (ESXi)` in §6.3.

**NetBox role migration:** the script creates DeviceRole `ESXi Hypervisor` (slug `esxi-hypervisor`) and migrates all Devices with platform matching `ESXi|VMware ESX` from role `Server` to the new role. Run with `--mutate-netbox` once during initial build.

### Zero-touch tag opt-ins

| Configuration group | Assigned to | Operator action |
|---|---|---|
| SNMP Monitoring (Linux) | NetBox tag **`snmp`** | Tag the Device/VM — no per-host CG row |

### Cohesity VMs with a primary IP

Active Cohesity VMs with `primary_ip4` need a **direct** assignment to **SNMP Monitoring** (network profile) — they have no `oob_ip`. Track via [day-2 runbook §7](runbooks/day2.md#7-recurring-manual-checks) until a cleaner signal exists.

### Manufacturer

Do **not** assign Dell iDRAC on Manufacturer Dell. Use Template Rules §6.3 (Dell ∧ Server, and Dell ∧ ESXi platform). OOB SNMP credentials come from **Server Agent+OOB** or **ESXi OOB iDRAC** (`MONITORING-DELL`).

---

## 6. Template Rules (platform → template + OS hostgroup)

Path: **Zabbix → Template Rules → Add**

**Why Template Rules:** OS and network OS family follow the platform name, which changes far less often than the device list. A regex rule attaches both the right stock template and the `OS/…` hostgroup in one place.

First create these hostgroups (**Zabbix → Hostgroups → Add**). Name and value are the same; leave description empty:

- `OS/Windows`
- `OS/Linux`
- `OS/Network`
- `OS/VMware`

Ensure these Zabbix templates exist (create the nbxsync Template objects pointing at them under **Zabbix → Templates** if needed):

| Template name in Zabbix | Notes |
|---|---|
| Windows by Zabbix agent | |
| Linux by Zabbix agent | |
| Linux by SNMP | |
| Windows by SNMP | |
| Extreme EXOS by SNMP | Stock (Zabbix 7.0) |
| Extreme VOSS by SNMP | Import from `zabbix/templates/extreme_voss_snmp/` |
| Extreme Port Speed Expect by SNMP | Import when ready (Extreme stages) |
| Extreme Routing by SNMP | Import when ready (Extreme stages) |
| Extreme IQ Engine by SNMP | Import from `zabbix/templates/extreme_iq_engine_snmp/` |
| Network Generic Device by SNMP | Fallback only — not Switch* / AP |
| FortiGate by SNMP | |
| VMware FQDN | |
| Storage Generic Device by SNMP | Cohesity — use a suitable SNMP storage/generic template for now; refine later |
| Dell iDRAC by SNMP | |
| MSSQL by Zabbix agent 2 | |
| Pure Storage FlashArray v2 by HTTP | Production (v1 alias accepted by script) |
| HPE MSA 2060 Storage by HTTP | Used for Dell Storage arrays in this estate |
| Huawei OceanStor Dorado by SNMP | |
| Synology DiskStation SNMPv3 | |
| GitLab by HTTP | |
| Oracle by Zabbix agent 2 | Placeholder for now |
| Tableau / CellMap / SAP / Acronis / SCCM / Print Spool by agent | Placeholders for now — assign the role; fill template content closer to production |

Create the matching nbxSync **Template** objects (name → Zabbix template) under **Zabbix → Templates** before the rules below. Placeholder names can point at a stub template until the real content exists.

**How matching works (short):** pattern is a case-insensitive regex (`search` on the platform name). Every matching rule can add its template/hostgroup; priority only orders evaluation. Leave require-tags / role / manufacturer empty unless the table sets them (AND; missing data fails closed).

### 6.1 Platform rules

| Name | Pattern | Template | Hostgroup | Require tags | Priority | Enabled |
|---|---|---|---|---|---|---|
| Windows Server | `Windows Server` | Windows by Zabbix agent | OS/Windows | — | 50 | Yes |
| Windows catch-all | `Windows` | Windows by Zabbix agent | OS/Windows | — | 200 | Yes |
| Linux | `Ubuntu\|Debian\|Linux\|Red Hat\|CentOS\|Alma\|SUSE\|Arch\|Photon\|Other.*Linux` | Linux by Zabbix agent | OS/Linux | — | 100 | Yes |
| Extreme EXOS | `EXOS` | Extreme EXOS by SNMP | OS/Network | — | 100 | Yes |
| Extreme VOSS | `VOSS` | Extreme VOSS by SNMP | OS/Network | — | 100 | Yes |
| Extreme IQ Engine | `IQ ENGINE` | **Extreme IQ Engine by SNMP** (`zabbix/templates/extreme_iq_engine_snmp/`) | OS/Network | — | 100 | Yes |
| FortiOS | `FORTIOS\|FortiOS` | FortiGate by SNMP | OS/Network | — | 100 | Yes |
| FortiAnalyzer/Manager | `FortiAnalyzer\|FortiManager` | Network Generic Device by SNMP | OS/Network | — | 50 | Yes |
| VMware Photon | `Photon` | Linux by Zabbix agent | OS/Linux | — | 50 | Yes |

**VMware:** do **not** attach VMware FQDN via an ESXi platform rule (legacy rule `VMware ESXi` stays disabled). Hypervisor/VM/cluster discovery is vCenter LLD (§7). ESXi hardware = §5.5b + §6.3 Dell iDRAC (ESXi).

**Extreme:** platform rules above attach EXOS / VOSS / IQ Engine — never Network Generic on Switch* (`icmpping` collision). Macro values, stages, LLD patches → [`zabbix/01-extreme-switching.md`](../../zabbix/01-extreme-switching.md); labels → [`port-identity.md`](../../zabbix/port-identity.md); nbxSync macro assignment clicks → §11.1.

### 6.2 SNMP OS rules (NetBox tag `snmp`)

Use together with configuration group **SNMP Monitoring (Linux)** (assigned on NetBox tag `snmp`) for the interface.

**Why a tag gate:** only selected hosts should switch from agent OS templates to SNMP OS templates. The tag is an explicit operator choice; the configuration group supplies the SNMP interface (Device or VM).

| Name | Pattern | Template | Hostgroup | Require tags | Priority | Enabled |
|---|---|---|---|---|---|---|
| SNMP Linux (tag) | *(same Linux pattern as above)* | Linux by SNMP | OS/Linux | snmp | 40 | Yes |
| SNMP Windows (tag) | `Windows` | Windows by SNMP | OS/Windows | snmp | 40 | Yes |
| Oracle (tag) | `.*` | Oracle by Zabbix agent 2 | — | oracle | 40 | Yes |

### 6.3 Manufacturer ∧ role rules

Scoped here so Manufacturer Dell does not put iDRAC on every Dell device. Server BMC transport stays **Server Agent+OOB** (`oob_ip`); ESXi BMC transport stays **ESXi OOB iDRAC**. Map matches production Zabbix hosts (STOD* / snas* / san* / ESXi).

| Name | Pattern | Role pattern | Manufacturer | Template | Hostgroup | Require tags | Priority | Enabled |
| Dell iDRAC (Server) | `.*` | `^Server$` | Dell | Dell iDRAC by SNMP | — | — | 80 | Yes |
| Dell iDRAC (ESXi) | `ESXi\|VMware ESX` | — | Dell | Dell iDRAC by SNMP | OS/VMware | — | 80 | Yes |
| Pure Storage (HTTP) | `.*` | — | Pure Storage | Pure Storage FlashArray v2 by HTTP | — | — | 80 | Yes |
| Dell Storage (HTTP) | `.*` | `^Storage$` | Dell | HPE MSA 2060 Storage by HTTP | — | — | 80 | Yes |
| Huawei OceanStor (SNMP) | `.*` | `^Storage$` | Huawei | Huawei OceanStor Dorado by SNMP | — | — | 80 | Yes |
| Synology DiskStation (SNMP) | `.*` | `^Storage$` | Synology | Synology DiskStation SNMPv3 | — | — | 80 | Yes |
| Synology Storage ICMP | `.*` | `^Storage$` | Synology | ICMP Ping | — | — | 85 | Yes |
| Zabbix Proxy ICMP | `.*` | `^Zabbix Proxy$` | — | ICMP Ping | — | — | 90 | Yes |
| Zabbix Proxy Health | `.*` | `^Zabbix Proxy$` | — | Remote Zabbix proxy health | — | — | 90 | Yes |

---

## 7. Template assignments (Role)

Path: **Zabbix → Templates → [template] → Assigned objects → Add**  
(or Device Role → Zabbix tab)

Assignments **merge** with Template Rules from §6. Do **not** assign Network Generic on Switch* or Access Point (those already get Extreme/Forti from §6). Manufacturer-scoped storage / iDRAC rules are in §6.3 — not repeated below.

Set each template’s interface requirement (Agent / SNMP / ANY) to match the transport the host will have.

| Template | Assigned to | Notes |
|---|---|---|
| MSSQL by Zabbix agent 2 | Device Role MSSQL | |
| MSSQL by Zabbix agent 2 | Device Role MSSQL Query Server | |
| VMware FQDN | Device Role vCenter | **Only** on vCenter — not on ESXi platforms. Secrets via §11.4 |
| GitLab by HTTP | Device Role GitLab | |
| Linux by SNMP | Device Role Virtual Appliance | Baseline if no platform rule matches |
| Network Generic Device by SNMP | Device Role Network Device | Fallback only |
| Storage Generic Device by SNMP | Device Role Cohesity | Placeholder/generic for now |
| FortiGate by SNMP | Device Role Firewall | Also via FortiOS platform rule |
| Tableau Bridge by Zabbix agent | Device Role Tableau | Placeholder |
| CellMap by Zabbix agent | Device Role CellMap | Placeholder |
| SAP by Zabbix agent | Device Role SAP ME, SAP HANA | Placeholder |
| Acronis by Zabbix agent | Device Role Acronis Management | Placeholder |
| SCCM by Zabbix agent | Device Role SCCM | Placeholder |
| Print Spool by Zabbix agent | Device Role Print Server | Placeholder |

Pure / Dell / Huawei / Synology storage and Dell iDRAC: §6.3 (and tag `oracle` → §6.2).  
One-off templates on a single host (e.g. AS Java): assign on the Device, not the role.

### 7.1 Extreme capability templates

Assign on the **role** when Extreme staging says so ([`zabbix/01-extreme-switching.md`](../../zabbix/01-extreme-switching.md) §7) — not on the platform Template Rule.

| Template | Assigned to |
|---|---|
| Extreme Port Speed Expect by SNMP | Switch Core / Dist / Access / Mgmt / Hybrid |
| Extreme Routing by SNMP | Switch Core, Switch Dist |

---

## 8. Hostgroups

Path: **Zabbix → Hostgroups → Add**, then assignments on each hostgroup or from the Site Group / tag Zabbix tab.

Axes (Sites / Roles / OS / Priority): [`architecture.md`](architecture.md). Below are the Jinja values and assignment clicks only.

### 8.1 Sites

| Name | Value | Assign to |
|---|---|---|
| Sites | `Sites/{{ object.site.group.get_ancestors(include_self=True) \| map(attribute="name") \| join("/") }}/{{ object.site.name }}` | Site Groups CH, HU, JP, KR, NL, US, CN |

This is the configured Sites value. `get_ancestors(include_self=True)` walks the Site Group tree so the Zabbix path always includes the country:

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

Created in §6. Membership is applied by Template Rules when the platform matches.

### 8.4 Priority / Critical

**Why a tag → hostgroup:** criticality is an orthogonal overlay. Devices already tagged `critical` in NetBox sync into Zabbix hostgroup `Priority/Critical` — no per-device hostgroup rows.

| Name | Value | Assign to |
|---|---|---|
| Priority/Critical | `Priority/Critical` | NetBox tag `critical` |

---

## 9. Tags

Two tag systems:

1. **NetBox tags** — already on devices/VMs/roles in inventory. Sync reads them as inputs.
2. **Zabbix tags** — written on the Zabbix host during sync from Jinja (§9.1, §9.2).

### 9.0 NetBox tags (inputs — assumed present where needed)

| NetBox tag | Effect during sync | Typical scope |
|---|---|---|
| `critical` | Hostgroup `Priority/Critical` (§8.4) | Device/VM |
| `snmp` | Transport → **SNMP Monitoring (Linux)** + Linux/Windows by SNMP templates | Device/VM |
| `oracle` | Links **Oracle by Zabbix agent 2** (merges with OS template) | Device/VM |

**Exclusion** uses a separate nbxSync **Zabbix** tag assignment named `do_not_monitor` (not a NetBox inventory tag) — §9.3. Phased cutover: [`runbooks/onboarding.md`](runbooks/onboarding.md).

NetBox tags are **not** copied into Zabbix as tags; they drive interfaces, templates, and hostgroups. Zabbix tags are separate (§9.1–§9.2).

### 9.1 Zabbix host tags — Environment (Jinja on Site Groups)

nbxSync owns the tag definition and Site Group assignment. At sync, Jinja renders a per-host value (e.g. `Production`) onto the Zabbix host.

**Why Jinja from the hostname:** environment is already encoded in naming; no second taxonomy.

| Tag | Value | Assign to |
|---|---|---|
| environment | *(template below)* | Site Groups CH … CN |

```
{% set n = object.name | lower -%}
{%- if "-p-" in n or n.endswith("-p") or "-p0" in n or "-p1" in n -%}Production
{%- elif "-d-" in n -%}Development
{%- elif "-q-" in n -%}QA
{%- elif "-s-" in n -%}Sandbox
{%- elif "-t-" in n -%}Test
{%- elif "vdi" in n -%}VDI
{%- else -%}Unknown
{%- endif -%}
```

Renders against the device or VM at sync. Preview on a Site Group may show an error — cosmetic.

**Failure mode:** names that do not match the `-p-` / `-d-` / … conventions resolve to **`Unknown`**. That is silent. **Extreme switches** (`CH-STA-…-CORE01`, `…-MGMT01`, `…-ACCE01`, …) normally have no `-p-` token — `environment=Unknown` on them is expected, not a sync bug. Extend the Jinja later if needed (e.g. treat `Switch*` roles as Production) rather than renaming the fleet.

### 9.2 Zabbix host tags — Cluster (auto-generated, Jinja on Clusters)

| Tag | Value | Assign to |
|---|---|---|
| cluster | `{{ object.cluster.name }}` | each Cluster |

### 9.3 Exclusion — `do_not_monitor`

Plugin `exclude_tag` = `do_not_monitor` (§12). Assign the nbxSync **Zabbix** tag (Zabbix tab → Tags), not a NetBox inventory tag.

| Tag | Value | Assign to |
|---|---|---|
| do_not_monitor | *(empty)* | **Role** — Messpc, Sd Wan Socket, VDI (permanent) |
| do_not_monitor | *(empty)* | **Device / VM** — onboarding waves (temporary) |

Sync **skips** excluded objects (no host/interfaces/templates). An existing Zabbix host from a prior sync is **deleted**. Untag + re-sync recreates the host.

**Phased cutover** (exclude agent fleet, enable one-by-one): [`runbooks/onboarding.md`](runbooks/onboarding.md). Use **object-level** assignments for waves — role-level inheritance cannot open a single host.

## 10. Host inventory

Path: Site Group → Zabbix tab → Host Inventory → Add

**Why on every country Site Group:** same Jinja mapping everywhere; values come from the existing NetBox object. Same control plane as Sites, Roles, proxy, and Agent default.

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
| url_a | `https://netbox.sensirion.lokal/dcim/devices/{{ object.id }}/` |
| deployment_status | `{{ object.status }}` |

Assign to Site Groups: CH, HU, JP, KR, NL, US, CN.

Fields such as `os` and `os_full` are filled by Zabbix templates when inventory mode is Automatic.

---

## 11. Macros

Path: **Zabbix → Macros → Add** (definition on Zabbix Server, then Macro Assignment on the role / or assign from the Role Zabbix tab)

**Why on the role:** class-wide thresholds and (for switches) Extreme port filters. Application secrets (VMware, Pure Storage, MSSQL) are role-level secret macros — see §11.4. Extreme *values* → `zabbix/01-extreme-switching.md`.

### 11.1 Extreme switch macros (nbxSync rows; values in Extreme docs)

**Path:** Zabbix → Macros → Add, then Macro Assignment on each Switch* Device Role (or Role → Zabbix tab).

Stock Extreme LLD evaluates **both** IFALIAS macros — set both on every Switch* role, plus `{$NET.IF.IFTYPE.MATCHES}`.

| What to create in nbxSync | Where values and meaning live |
|---|---|
| Role macros `{$NET.IF.IFALIAS.MATCHES}`, `{$NET.IF.IFALIAS.NOT_MATCHES}`, `{$NET.IF.IFTYPE.MATCHES}` on Switch Core / Dist / Mgmt / Access / Hybrid | [`zabbix/01-extreme-switching.md`](../../zabbix/01-extreme-switching.md) §5 Role model and §8 Macro assignments |
| Fleet / template destination macros (`{$TEMP_WARN}`, optics, MLT, Speed Expect `{$PORTID.LLD.*}`, …) | Same doc §8 (including temporary cutover-silence overlay) |
| On-box port label grammar | [`zabbix/port-identity.md`](../../zabbix/port-identity.md) |
| Hybrid flip Access→Core, stages 4–6 | Extreme doc §7 Staged rollout |

Do **not** duplicate those tables here — the Extreme doc is authoritative for values. This checklist only requires that the nbxSync macro assignments exist. Fleet TEMP_*/optic/MLT globals and cutover-silence overlays are also in Extreme §8 (not repeated here).

### 11.3 Application / threshold macros (role)

| Macro | Value | Device Role |
|---|---|---|
| `{$CPU.UTIL.CRIT}` | 90 | MSSQL |
| `{$CPU.UTIL.CRIT}` | 80 | Server |
| `{$MEM.UTIL.CRIT}` | 85 | VDI |
| `{$MSSQL.DSN}` | nbxsync | MSSQL |
| `{$VMWARE.URL}` | `https://{{ object.name }}/sdk` | vCenter |


### 11.4 Application secrets (per-device / per-site)

Each macro is defined as a server-level **ZabbixMacro** (on ZabbixServer) with a **ZabbixMacroAssignment** on the target object (Device, VM, or DeviceRole). The assignment carries the secret value and is resolved during sync via the inheritance chain.

#### Pure Storage API tokens (per-device)

Each Pure array has its own API token. The macro assignment is on each **Device** (not the manufacturer).

| Macro | Target | Type | Env var |
|---|---|---|---|
| `{$PURESTORAGE.TOKEN}` | Device (per array) | Secret | `NBX_PURE_TOKEN_<HOSTNAME>` |

| Array | Env var |
|---|---|
| `hu-deb-san11` | `NBX_PURE_TOKEN_HU_DEB_SAN11` |
| `kr-sel-san11` | `NBX_PURE_TOKEN_KR_SEL_SAN11` |
| `cn-sha-san11` | `NBX_PURE_TOKEN_CN_SHA_SAN11` |
| `ch-zrh-zh4-san01` | `NBX_PURE_TOKEN_CH_ZRH_ZH4_SAN01` |
| `ch-zrh-zh4-san02` | `NBX_PURE_TOKEN_CH_ZRH_ZH4_SAN02` |
| `ch-zrh-zh5-san01` | `NBX_PURE_TOKEN_CH_ZRH_ZH5_SAN01` |
| `ch-zrh-zh5-san02` | `NBX_PURE_TOKEN_CH_ZRH_ZH5_SAN02` |

Token format: UUID (generated on each array via `purearray connect --api-token`).

#### VMware vCenter SSO credentials (per-VM)

SSO domains differ per site. The macro assignment is on each **VM** (not the role).

| Macro | Target | Type | Env var |
|---|---|---|---|
| `{$VMWARE.USER}` | VM (per vCenter) | Secret | `NBX_VMWARE_USER_<HOSTNAME>` |
| `{$VMWARE.PASSWORD}` | VM (per vCenter) | Secret | `NBX_VMWARE_PASS_<HOSTNAME>` |

| vCenter | SSO domain | Env var prefix |
|---|---|---|
| `ch-sta-p-vcsa02` | `VCENTER-SSO.SENSIRION` | `NBX_VMWARE_USER/PASS_CH_STA_P_VCSA02` |
| `ch-sta-p-vcsa10` | `VCENTER-SSO.SENSIRION` | `NBX_VMWARE_USER/PASS_CH_STA_P_VCSA10` |
| `hu-deb-p-vcsa01` | `HU.VSPHERE.LOCAL` | `NBX_VMWARE_USER/PASS_HU_DEB_P_VCSA01` |
| `kr-sel-p-vcsa01` | `KR.VSPHERE.LOCAL` | `NBX_VMWARE_USER/PASS_KR_SEL_P_VCSA01` |
| `cn-sha-p-vcsa01` | `cn.vsphere.lokal` | `NBX_VMWARE_USER/PASS_CN_SHA_P_VCSA01` |

Username format: `<SSO_DOMAIN>\LogicMonitor` (e.g. `VCENTER-SSO.SENSIRION\LogicMonitor`).

#### MSSQL credentials (role-level, shared)

Single service account across all MSSQL hosts. Assignment is on **DeviceRole = MSSQL**.

| Macro | Target | Type | Env var |
|---|---|---|---|
| `{$MSSQL.USER}` | DeviceRole: MSSQL | Secret | `NBX_MSSQL_USER` |
| `{$MSSQL.PASSWORD}` | DeviceRole: MSSQL | Secret | `NBX_MSSQL_PASS` |

#### Huawei SAN01 (per-device SNMPv3 interface)

`HU-DEB-SAN01` uses a non-fleet SNMPv3 credential (`LogicMonitor` user, SHA/AES). This is a **per-device ZabbixHostInterface** (created in §5), not a macro. The passphrases are set directly on the interface object with `snmp_pushcommunity=True`.

If a macro is not set, the template will show "no data" until the credential is provided.

SNMPv3 auth/priv passphrases are **not** global or role macros: they live on the SNMP Host Interface (§5) and are pushed as secret **host** macros when SNMP push community is True.

---

## 12. Plugin settings

Ask the NetBox administrator to set the following under the nbxsync plugin configuration (adjust intervals if your environment differs).

| Setting | Intended value |
|---|---|
| Source of truth for host, hostgroup, interface, template, tag, macro, proxy, maintenance | NetBox |
| Exclude tag | `do_not_monitor` |
| Soft-state tag / value | `NO_ALERTING` / `1` (plugin host tag on paused VMs — monitoring packs interpret it) |
| Attach object identity tags | Yes (`nb_type` / `nb_id`) |
| Allow inherited deletion | No |
| Adopt existing Zabbix hosts | No |
| Device status → Zabbix | active → enabled; planned/staged → disabled; failed/offline/inventory/decommissioning → deleted |
| VM status → Zabbix | active → enabled; planned → enabled in maintenance; paused → enabled + soft-state tag; failed/offline → deleted |
| SNMP community / auth / priv macro names | `{$SNMP_COMMUNITY}`, `{$SNMP_AUTHPASS}`, `{$SNMP_PRIVPASS}` |

Keep Site / Site Group inheritance **after** role and platform in the inheritance order (architecture rule 5) so country defaults do not override role SNMP or Server Agent+OOB.

---

## 13. What a typical host should look like

Authoritative expected-state matrix (architecture links here; do not copy this table elsewhere).

| Object | Configuration group | Typical templates | Interfaces | Hostgroups |
|---|---|---|---|---|
| Linux server (role Server) | Server Agent+OOB | Linux by agent (+ Dell iDRAC if Dell and oob IP set) | Agent :10050 + SNMP `MONITORING-DELL` on oob | Sites/CH/…, Roles/Server, OS/Linux |
| Linux or Windows VM | Agent Monitoring (from Site Group) | OS by agent (Template Rule) | Agent :10050 | Sites/CH/…, Roles/…, OS/… |
| SAP HANA | SNMP Monitoring (SAP) | Linux by agent + SAP by Zabbix agent | SNMP `SAPUSER` | Sites/…, Roles/SAP HANA, OS/Linux |
| Host with tag `snmp` only | SNMP Monitoring (Linux) via tag | Linux or Windows by SNMP | SNMP `MONITORING-LINUX` | Sites/CH/…, Roles/…, OS/… |
| EXOS Switch Core/Dist/Mgmt | SNMP Monitoring | Extreme EXOS by SNMP (+ role IFALIAS macros) | SNMP `MONITORING` MD5/DES | Sites/CH/…, Roles/Switch …, OS/Network |
| VOSS Switch Core/Access/Hybrid | SNMP Monitoring | Extreme VOSS by SNMP (**not** Network Generic) + role IFALIAS | SNMP `MONITORING` MD5/DES | Sites/CH/…, Roles/Switch …, OS/Network |
| Storage (Huawei) | SNMP Monitoring (Manufacturer) | Huawei OceanStor Dorado by SNMP (template already has `icmpping`); LogicMonitor creds → per-device IF | SNMP | Sites/…, Roles/Storage |
| Firewall | SNMP Monitoring | Platform/role template (FortiGate, …) | SNMP `MONITORING` MD5/DES | Sites/CH/…, Roles/…, OS/Network |
| Space Server | Agent Monitoring (SPACE) | OS by agent | Agent **:10060** | Sites/CH/…, Roles/Space Server, OS/… |
| Storage (Pure) | Agent Monitoring | Pure Storage FlashArray v2 by HTTP | Agent / HTTP | Sites/…, Roles/Storage |
| Storage (Synology) | SNMP Monitoring (Manufacturer) | Synology DiskStation SNMPv3 + ICMP Ping | SNMP `MONITORING` | Sites/…, Roles/Storage |
| Storage (Huawei) | SNMP Monitoring (Manufacturer) | Huawei OceanStor Dorado by SNMP (+ ICMP); LogicMonitor creds → per-device IF | SNMP | Sites/…, Roles/Storage |
| Storage (Dell) | Agent Monitoring | HPE MSA 2060 Storage by HTTP | Agent / HTTP | Sites/CH/…, Roles/Storage |
| Pure Storage | Agent Monitoring | Pure Storage by HTTP | Agent / HTTP | Sites/CH/…, Roles/Pure Storage |
| Cohesity physical (oob only) | OOB SNMP Only | Storage Generic | SNMP `MONITORING` on oob | Sites/CH/…, Roles/Cohesity |
| Cohesity VM with primary IP | SNMP Monitoring (direct) | Storage Generic | SNMP `MONITORING` on primary | … |
| ESXi hypervisor (Dell) | ESXi OOB iDRAC (platform) | Dell iDRAC by SNMP | SNMP `MONITORING-DELL` on oob only | Sites/…, Roles/…, OS/VMware |
| vCenter | Agent Monitoring (Site Group) unless overridden | VMware FQDN (+ OS template if platform matches) | Agent / HTTP(SDK) | Sites/…, Roles/vCenter |
| Any of the above + tag `critical` | unchanged | unchanged | unchanged | + Priority/Critical |
| Brand-new role tomorrow | Agent Monitoring (from Site Group) unless listed in §5b | OS Template Rule if platform set | Agent | Roles/\<new name\> appears automatically |
| VM on a cluster with no site | none | — | — | Not profiled until the VM or cluster has a site |

---

## 14. Out of scope for this document

This document stops at **NetBox → nbxSync → Zabbix host wiring** (interfaces, templates, hostgroups, macros, sync).

What to poll, thresholds, and notifications live under [`zabbix/`](../../zabbix/README.md).  
Day-2 operator procedures: [`runbooks/day2.md`](runbooks/day2.md).

---

## 15. Verification

After the initial build, and after major changes, confirm coverage against §13.

**What “good” looks like (spot-check in GUI / Zabbix):**

| Check | Expect |
|---|---|
| Sample Linux server | Server Agent+OOB; agent + oob SNMP; OS/Linux; Roles/Server; leaf under `Sites/CH/…` |
| Sample EXOS switch | SNMP Monitoring; **Extreme EXOS by SNMP**; role IFALIAS macros (§11.1 / Extreme doc); no Network Generic; single `icmpping`; OS/Network |
| Sample VOSS switch | SNMP Monitoring; **Extreme VOSS by SNMP** (imported YAML); same role IFALIAS as EXOS peer role; no Network Generic; single `icmpping` |
| Sample Switch Hybrid (pre–stage 5) | Same platform template as peer EXOS/VOSS; IFALIAS macros still Access-like (`USW\|…` opt-in), not Core `.*` |
| Sample Windows VM | Agent; Windows by agent; OS/Windows; leaf under `Sites/CH/…` |
| Sample ESXi (Dell) | ESXi OOB iDRAC; Dell iDRAC on oob; OS/VMware; **no** VMware FQDN template |
| Sample vCenter | VMware FQDN + SDK macros; hypervisors appear via LLD, not as separate NetBox→VMware-template hosts |
| Nested Sites path | Host is leaf under `Sites/CH/…`; parent groups exist without duplicating membership |
| Host with `critical` | Also in hostgroup Priority/Critical |
| Role not listed in §5b SNMP/OOB | Still has Agent via Site Group |
| VM without site | No useful profile until site/scope is set |

**Unprofiled / wrong template symptoms:** host missing in Zabbix, empty template list, or only partial stack vs §13. Use the [day-2 runbook §6](runbooks/day2.md#6-host-not-monitored--wrong-templates) ladder.

**Optional onboarding census:** see [`scripts/README.md`](../../scripts/README.md) (`--verify`). Map gaps to that runbook.

---

## 16. Not driven by this integration

| Area | Where it lives |
|---|---|
| Objects with no NetBox device/VM (web scenarios, account-level APIs, …) | Configured in Zabbix / monitoring packs — [`zabbix/`](../../zabbix/README.md) |
| Monitoring content (signals, thresholds, notifications) | [`zabbix/`](../../zabbix/README.md) (§14) |
| NetBox inventory population / LM migration | Outside this checklist (data assumed present) |
| SAP application content / DNUS scripts | Placeholder assignment in §7; content owned outside this integration |
| Configuration backup | cfgit — not Zabbix / not nbxSync |

---

## Appendix A — Optional onboarding scripts

First-build helpers only — not day-2. Commands, env vars, flags, and run order: [`scripts/README.md`](../../scripts/README.md).  
This checklist remains authoritative for the objects those scripts create.

