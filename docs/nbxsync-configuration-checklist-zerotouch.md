# nbxSync Configuration Checklist (Zero-Touch)

Step-by-step configuration in NetBox for the **hostgroup-first / zero-touch** model.
Execute in order. Each section is a discrete task.

**Source of truth for this document:** `scripts/configure_nbxsync_zerotouch.py` (fork PR [#23](https://github.com/berlikm/nbxsync/pull/23)), lab-verified (`--simulate` **41/41**).
**Replaces:** previous Confluence checklist (Jul 2026) that enumerated 31 role→Agent rows, Manufacturer OOB CG, Teams/*, Managed/nbxSync, and `os_family` tags.

**Automation (preferred):**

```bash
export NBX_ZABBIX_TOKEN=...
# optional: export NBX_ZABBIX_URL=http://10.0.105.144:8080
python scripts/configure_nbxsync_zerotouch.py
python scripts/configure_nbxsync_zerotouch.py --verify
# optional Zabbix dashboards (Sites / Roles / OS parents):
python scripts/create_dashboards.py
```

Manual GUI steps below match what that script creates.

---

## Model (read once)

| Axis | Mechanism | Zabbix result |
|---|---|---|
| Location | Jinja hostgroup `Sites/{{ site.group }}/{{ site }}` @ each country SiteGroup | `Sites/CH-STA/CH-STA-L26` |
| Function | Jinja hostgroup `Roles/{{ role.name }}` @ each country SiteGroup | `Roles/Switch Core` (new roles auto) |
| OS / platform | `ZabbixTemplateRule` → template **+** `OS/*` hostgroup | `OS/Linux`, `OS/Windows`, `OS/Network`, `OS/VMware` |
| Criticality | NetBox tag `critical` → hostgroup assignment | `Priority/Critical` |
| Default transport | ConfigGroup **Agent Monitoring** @ each top SiteGroup | Agent IF @ primary IP |
| SNMP transport | ConfigGroup **SNMP Monitoring** @ network + Storage roles | SNMP IF @ primary IP |
| Server BMC | ConfigGroup **Server Agent+OOB** @ Server role | Agent @ primary **+** SNMP @ `oob_ip` |
| Cohesity physical | ConfigGroup **OOB SNMP Only** @ Cohesity role | SNMP @ `oob_ip` only |
| SNMP VMs | ConfigGroup **VM by SNMP** (per VM) + NetBox tag `snmp` | SNMP IF + Linux/Windows by SNMP templates |
| App / OEM templates | `ZabbixTemplateAssignment` on Role / Manufacturer | Merges with OS rules |

**One effective ConfigGroup decides transport.** Tags never carry a transport ConfigGroup or HostInterface (anti-pattern: tag CG would beat role/site).

**Template vs hostgroup GUI:**
- Role / Manufacturer **template** assignments appear on the Role (or Template) page — not on the Hostgroup page.
- `OS/*` membership comes from `TemplateRule.zabbixhostgroup` — inspect under **Zabbix → Template Rules** (and on the Hostgroup detail “Template rules” card when that UI is present).

**Dropped vs previous checklist (do not recreate):**
- ❌ 31 DeviceRole → Agent Monitoring rows → SiteGroup Agent default
- ❌ Roles Jinja assigned per DeviceRole → once per country SiteGroup
- ❌ `Managed/nbxSync`, `Teams/*`, `Teams/Production DB`, per-device `production_db` hostgroup rows
- ❌ Manufacturer Dell → separate **OOB Management** ConfigGroup (transport)
- ❌ HostInterface / ConfigGroup on NetBox tag `snmp`
- ❌ `os_family` Zabbix tags on TemplateRules
- ❌ SiteGroup → **ICMP Ping** template (collides with `icmpping*` in SNMP templates)

---

## GUI nomenclature

Plugin menu **Zabbix**: Servers, Proxies, Proxy Groups, Templates, Macros, Tags, Hostgroups, Configuration groups, Maintenance, Template Rules.

**Add pattern:** child objects (`*Assignment`, `ZabbixHostInterface`, `ZabbixHostInventory`) are added from a parent detail page or its **Zabbix** tab (on SiteGroup, Site, Region, Cluster, ClusterType, Manufacturer, DeviceType, DeviceRole, Platform, Device, VirtualMachine, VirtualDeviceContext). Add buttons deep-link with `assigned_object_type` / `assigned_object_id` pre-filled.

**Prerequisites (NetBox data — not created by nbxsync):**
- Country SiteGroups with slugs: `ch`, `hu`, `jp`, `kr`, `nl`, `us`, `cn`
- DeviceRoles named exactly as listed below
- Platforms whose names match the TemplateRule regexes
- For BMC: `device.oob_ip` populated; without it the OOB SNMP interface is skipped
- Zabbix templates imported / present (IDs resolved **by name** at apply time)

---

## 1. ZabbixServer

Path: **Zabbix → Servers → Add**

| Field | Value |
|---|---|
| Name | Zabbix Production |
| URL | `http://10.0.105.144:8080` (or your URL; env `NBX_ZABBIX_URL`) |
| Token | (API token; env `NBX_ZABBIX_TOKEN`) |
| Validate certs | **True** (production). Lab HTTP only: False via script `--lab-http` |
| Sync enabled | True |
| Skip version check | **False** (production hygiene) |

---

## 2. ZabbixProxy + ZabbixProxyGroup

Path: **Zabbix → Proxies → Add**, **Zabbix → Proxy Groups → Add**

JP, NL, and US do not have their own proxies. JP routes through KR; NL and US route through the CH proxy group.

Script resolves `proxyid` from live Zabbix **by proxy name**.

### 2.1 ZabbixProxyGroup

| Name | Server | Description |
|---|---|---|
| CH Proxy Group | Zabbix Production | Proxy group for CH-based monitoring (NL, US route through CH) |

### 2.2 ZabbixProxy

| Name | Mode | Proxy group | Local address | Local port |
|---|---|---|---|---|
| ch-proxy-1 | Active | CH Proxy Group | 127.0.0.1 | 10051 |
| hu-proxy-1 | Active | — | — | — |
| kr-proxy-1 | Active | — | — | — |
| cn-proxy-1 | Active | — | — | — |

---

## 3. ZabbixServerAssignment (per country SiteGroup)

Path: **Site Group → Zabbix tab → Zabbix Servers → Add**

Proxy assignment is done from the Site Group in NetBox, never from the Zabbix UI. One assignment per country SiteGroup. Set a **proxy OR a proxy group** — not both.

| Assigned object | Proxy | Proxy group | Sync |
|---|---|---|---|
| SiteGroup CH | — | CH Proxy Group | ✓ |
| SiteGroup HU | hu-proxy-1 | — | ✓ |
| SiteGroup JP | kr-proxy-1 | — | ✓ |
| SiteGroup KR | kr-proxy-1 | — | ✓ |
| SiteGroup NL | — | CH Proxy Group | ✓ |
| SiteGroup US | — | CH Proxy Group | ✓ |
| SiteGroup CN | cn-proxy-1 | — | ✓ |

---

## 4. ConfigGroups (interface containers)

Path: **Zabbix → Configuration groups → Add**

A ConfigGroup is a named container. Interface parameters live on `ZabbixHostInterface` (§5). Exactly **one** effective ConfigGroup decides transport for a host.

| Name | Description |
|---|---|
| SNMP Monitoring | SNMP v3 for network + SNMP-only storage |
| Agent Monitoring | Default agent transport (assigned at **top SiteGroups**) |
| Server Agent+OOB | Server profile: Agent @ primary + SNMP @ `oob_ip` (`use_oob_ip`) |
| VM by SNMP | Per-VM SNMP **transport only** — pair with NetBox tag `snmp` for OS SNMP templates |
| OOB SNMP Only | SNMP @ `oob_ip` only — hardware without `primary_ip4` (e.g. Cohesity Dell nodes) |

**Not used:** previous “OOB Management” Manufacturer→CG pattern (broken: Manufacturer CG never merges with Role Agent CG).

---

## 5. ZabbixHostInterface (group-level defaults)

Path: **Zabbix → Configuration groups → [Group] → Host Interfaces → Add**

Design: interfaces hang on ConfigGroups. IP is left empty; sync fills `primary_ip4` or `oob_ip`.

Field notes: **Type** = AGENT / SNMP. **Interface type** = Default (1). SNMPv3 below matches the script (`SHA256` + `AES128` — not the older SHA1/AES192 checklist values).

Shared SNMPv3 fields (all SNMP interfaces in this checklist):

| Field | Value |
|---|---|
| SNMP version | 3 |
| SNMP bulk | True |
| SNMP max repetitions | 10 |
| SNMPv3 security name | MONITORING |
| SNMPv3 security level | authPriv |
| SNMPv3 auth protocol | **SHA256** |
| SNMPv3 auth passphrase | `{$SNMP_AUTHPASS}` |
| SNMPv3 priv protocol | **AES128** |
| SNMPv3 priv passphrase | `{$SNMP_PRIVPASS}` |
| SNMP push community | False |

### 5.1 SNMP Monitoring → SNMP IF

| Field | Value |
|---|---|
| Type | SNMP |
| Interface type | Default |
| Port | 161 |
| Use IP | Yes |
| Use OOB IP | False |
| + SNMPv3 fields above | |

### 5.2 Agent Monitoring → Agent IF

| Field | Value |
|---|---|
| Type | Agent |
| Interface type | Default |
| Port | 10050 |
| Use IP | Yes |
| TLS connect | No encryption |

### 5.3 Server Agent+OOB → **both** interfaces on one CG

**Agent IF** (primary): Type Agent, port 10050, Use OOB IP False — same as §5.2.

**SNMP IF** (`oob_ip`): Type SNMP, port 161, **Use OOB IP = True**, + SNMPv3 fields.

If `device.oob_ip` is empty, the SNMP interface is skipped for that device; Agent still syncs.

### 5.4 VM by SNMP → SNMP IF only

Same as §5.1 (SNMP, port 161, Use OOB IP False). **No** template on this CG — OS templates come from §6 compound rules + NetBox tag `snmp`.

### 5.5 OOB SNMP Only → SNMP IF with `use_oob_ip`

Same SNMPv3 as §5.3 SNMP side (Use OOB IP True). For roles/hardware with only `oob_ip`.

### 5.6 Do not create

- ❌ HostInterface assigned to NetBox tag `snmp` (or any tag) — script prunes these
- ❌ Separate Manufacturer-level transport interfaces

---

## 5b. ZabbixConfigurationGroupAssignment

Path: **Zabbix → Configuration groups → [Group] → Assignments → Add**  
(or Site Group / Role → Zabbix tab)

Without these, group-level interfaces are not resolved.

### Agent Monitoring → each top country SiteGroup

| ConfigGroup | Assigned object |
|---|---|
| Agent Monitoring | SiteGroup CH |
| Agent Monitoring | SiteGroup HU |
| Agent Monitoring | SiteGroup JP |
| Agent Monitoring | SiteGroup KR |
| Agent Monitoring | SiteGroup NL |
| Agent Monitoring | SiteGroup US |
| Agent Monitoring | SiteGroup CN |

This replaces the previous 31 DeviceRole→Agent rows. Roles such as Domain Controller, Fileserver, MSSQL, GitLab, vCenter, Pure Storage, VDI, … inherit Agent via their SiteGroup unless overridden below.

**Pure Storage** stays on SiteGroup Agent + HTTP template (§7) — **not** on SNMP Monitoring.

Assign Agent **only** to top-level country SiteGroups. A mid-level SiteGroup CG would win over the country default.

### SNMP Monitoring → DeviceRoles

| ConfigGroup | DeviceRole |
|---|---|
| SNMP Monitoring | Switch Core |
| SNMP Monitoring | Switch Dist |
| SNMP Monitoring | Switch Access |
| SNMP Monitoring | Switch Mgmt |
| SNMP Monitoring | Access Point |
| SNMP Monitoring | Firewall |
| SNMP Monitoring | Network Device |
| SNMP Monitoring | Virtual Appliance |
| SNMP Monitoring | Storage |

Role SNMP beats SiteGroup Agent (inheritance first-seen / more specific path).

### Server Agent+OOB → Server

| ConfigGroup | DeviceRole |
|---|---|
| Server Agent+OOB | Server |

### OOB SNMP Only → Cohesity (physical)

| ConfigGroup | DeviceRole |
|---|---|
| OOB SNMP Only | Cohesity |

### Cohesity VMs with `primary_ip4` (direct override)

Active Cohesity VMs that have `primary_ip4` get a **direct** assignment to **SNMP Monitoring** (they have no `oob_ip`; OOB SNMP Only would not work). The script does this automatically; do the same in GUI if applying by hand.

### VM by SNMP (per VM)

Assign **VM by SNMP** ConfigGroup to each VM that must use SNMP transport. Also tag the VM with NetBox tag **`snmp`** so §6 compound rules attach Linux/Windows by SNMP.

### Manufacturer

**Do not** assign any transport ConfigGroup to Manufacturer Dell. Dell iDRAC is a **template** only (§7).

---

## 6. ZabbixTemplateRules (platform regex → template + OS/*)

Path: **Zabbix → Template Rules → Add**

Also create the static OS hostgroups (value = name, empty description): `OS/Windows`, `OS/Linux`, `OS/Network`, `OS/VMware`.

Templates are nbxsync `ZabbixTemplate` rows pointing at Zabbix templates **by name** (script resolves IDs via API). Ensure these exist in Zabbix first:

| Key | Zabbix template name |
|---|---|
| windows_agent | Windows by Zabbix agent |
| linux_agent | Linux by Zabbix agent |
| linux_snmp | Linux by SNMP |
| windows_snmp | Windows by SNMP |
| extreme_exos_snmp | Extreme EXOS by SNMP |
| network_generic_snmp | Network Generic Device by SNMP |
| fortigate_snmp | FortiGate by SNMP |
| vmware_fqdn | VMware FQDN |
| storage_generic_snmp | Storage Generic Device by SNMP *(script auto-clones from Network Generic without colliding items)* |
| dell_idrac_snmp | Dell iDRAC by SNMP *(import from Zabbix share if missing)* |
| mssql_odbc | MSSQL by ODBC |
| pure_storage_http | Pure Storage FlashArray v1 by HTTP |
| gitlab_http | GitLab by HTTP |

Matching: case-insensitive `re.search` on platform name. Lower **priority** number wins when multiple rules match. Empty `require_tags` = no tag gate.

### 6.1 Platform → agent / SNMP OS templates + OS/* hostgroup

| Name | Pattern | Template | Hostgroup | require_tags | Priority | Enabled |
|---|---|---|---|---|---|---|
| Windows Server | `Windows Server` | Windows by Zabbix agent | OS/Windows | — | 50 | ✓ |
| Windows catch-all | `Windows` | Windows by Zabbix agent | OS/Windows | — | 200 | ✓ |
| Linux | `Ubuntu\|Debian\|Linux\|Red Hat\|CentOS\|Alma\|SUSE\|Arch\|Photon\|Other.*Linux` | Linux by Zabbix agent | OS/Linux | — | 100 | ✓ |
| Extreme EXOS | `EXOS` | Extreme EXOS by SNMP | OS/Network | — | 100 | ✓ |
| Extreme VOSS | `VOSS` | Network Generic Device by SNMP | OS/Network | — | 100 | ✓ |
| Extreme IQ Engine | `IQ ENGINE` | Network Generic Device by SNMP | OS/Network | — | 100 | ✓ |
| FortiOS | `FORTIOS\|FortiOS` | FortiGate by SNMP | OS/Network | — | 100 | ✓ |
| FortiAnalyzer/Manager | `FortiAnalyzer\|FortiManager` | Network Generic Device by SNMP | OS/Network | — | 50 | ✓ |
| VMware ESXi | `ESXi\|VMware ESX\|vSphere` | VMware FQDN | OS/VMware | — | 100 | ✓ |
| VMware Photon | `Photon` | Linux by Zabbix agent | OS/Linux | — | 50 | ✓ |

**No `os_family` Zabbix tags** — OS classification is the `OS/*` hostgroup. Script deletes leftover `os_family` tags.

### 6.2 SNMP OS flavor (NetBox tag `snmp`)

Pair with **VM by SNMP** CG for the interface. HostSync drops agent templates when only SNMP IF is present (and vice versa).

| Name | Pattern | Template | Hostgroup | require_tags | Priority | Enabled |
|---|---|---|---|---|---|---|
| SNMP Linux (tag) | *(same Linux pattern as above)* | Linux by SNMP | OS/Linux | `snmp` | 40 | ✓ |
| SNMP Windows (tag) | `Windows` | Windows by SNMP | OS/Windows | `snmp` | 40 | ✓ |

---

## 7. ZabbixTemplateAssignment (Role / Manufacturer → add-on templates)

Path: **Zabbix → Templates → [Template] → Assigned objects → Add**  
(or Role / Manufacturer → Zabbix tab)

These **merge** with OS templates from §6. A MSSQL VM gets Windows-by-agent (rule) + MSSQL by ODBC (role).

| Template | Assigned object | Notes |
|---|---|---|
| MSSQL by ODBC | DeviceRole MSSQL | Agent requirement |
| MSSQL by ODBC | DeviceRole MSSQL Query Server | |
| VMware FQDN | DeviceRole vCenter | ANY interface (HTTP); substitutes missing “vCenter by HTTP” |
| Pure Storage FlashArray v1 by HTTP | DeviceRole Pure Storage | ANY; Pure stays on **Agent** transport |
| GitLab by HTTP | DeviceRole GitLab | |
| Linux by SNMP | DeviceRole Virtual Appliance | Floor for VA |
| Network Generic Device by SNMP | DeviceRole Network Device | Floor |
| Storage Generic Device by SNMP | DeviceRole Storage | Avoids item collision with iDRAC |
| Storage Generic Device by SNMP | DeviceRole Cohesity | |
| Network Generic Device by SNMP | DeviceRole Switch Core | Role floor if platform missing |
| Network Generic Device by SNMP | DeviceRole Switch Dist | |
| Network Generic Device by SNMP | DeviceRole Switch Access | |
| Network Generic Device by SNMP | DeviceRole Switch Mgmt | |
| Network Generic Device by SNMP | DeviceRole Access Point | |
| FortiGate by SNMP | DeviceRole Firewall | Floor; FortiOS rule still adds when platform matches |
| Dell iDRAC by SNMP | Manufacturer Dell | Template only — not a ConfigGroup |

Import Dell iDRAC from the Zabbix templates repo if missing: `templates/server/dell_idrac_snmp/…`.

**Do not** attach templates to the **VM by SNMP** ConfigGroup (transport-only; script prunes leftover CG→template links).

**Do not** assign ICMP Ping at SiteGroup / country level — item-key collisions with SNMP templates.

---

## 8. ZabbixHostgroups

Path: **Zabbix → Hostgroups → Add**, then assignments

### 8.1 Sites (Jinja, once per country SiteGroup)

| Name | Value | Assign to |
|---|---|---|
| Sites | `Sites/{{ object.site.group.name }}/{{ object.site.name }}` | SiteGroup CH, HU, JP, KR, NL, US, CN |

Renders against Device/VM at sync (e.g. `Sites/CH-STA/CH-STA-L26`). Preview on a SiteGroup assignment may error — cosmetic.

### 8.2 Roles (Jinja, once per country SiteGroup)

| Name | Value | Assign to |
|---|---|---|
| Roles | `Roles/{{ object.role.name }}` | SiteGroup CH, HU, JP, KR, NL, US, CN |

**Not** assigned per DeviceRole. New roles materialize `Roles/<name>` automatically.

### 8.3 OS/* (via TemplateRules — no SiteGroup assignment)

Created in §6; membership is attached when a TemplateRule matches. Do not also assign OS/* to SiteGroups.

### 8.4 Priority/Critical (tag-driven)

| Name | Value | Assign to |
|---|---|---|
| Priority/Critical | `Priority/Critical` | NetBox tag `critical` |

Lifecycle: add/remove NetBox tag `critical` on the Device/VM. No per-device hostgroup rows.

### 8.5 Explicitly not created

| Previous checklist item | Status |
|---|---|
| Managed / `Managed/nbxSync` | Dropped |
| Teams/Network, Teams/Infrastructure, … | Dropped — use `Roles/*` (re-add Teams only if Zabbix RBAC needs a separate axis) |
| Teams/Production DB + `production_db` tag rows | Dropped |
| Per-device Priority/Critical assignments | Replaced by one tag assignment |

---

## 9. ZabbixTags

Path: **Zabbix → Tags → Add**, then Assigned objects → Add

Lean tags only — do not duplicate hostgroup dimensions (team, site, role, OS, priority).

### 9.0 NetBox tags (plugin / overlays)

Create in NetBox **Tags** (not Zabbix tags):

| Slug / name | Purpose |
|---|---|
| `do_not_monitor` | Exclusion via `exclude_tag` plugin setting + §9.3 |
| `critical` | → Priority/Critical hostgroup (§8.4) |
| `snmp` | → SNMP Linux/Windows TemplateRules (§6.2); **not** transport |

Optional script flag `--mutate-netbox` also tags Messpc / Sd Wan Socket devices and reassigns Forti* VMs → Virtual Appliance. Default is **no NetBox inventory mutations**.

### 9.1 Environment (Jinja @ SiteGroups)

| Tag | Value | Assign to |
|---|---|---|
| environment | *(template below)* | SiteGroup CH…CN |

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

### 9.2 Cluster (Jinja @ each Cluster)

| Tag | Value | Assign to |
|---|---|---|
| cluster | `{{ object.cluster.name }}` | each Cluster |

### 9.3 Exclusion

| Tag | Value | Assign to DeviceRole |
|---|---|---|
| do_not_monitor | *(empty)* | Messpc, Sd Wan Socket, VDI |

Plugin setting `exclude_tag: 'do_not_monitor'` must be set (§12).

### 9.4 Not created

- ❌ `os_family` Zabbix tags  
- ❌ Tags that copy hostgroup names for “dashboards”

---

## 10. ZabbixHostInventory

Path: SiteGroup → Zabbix tab → Host Inventory → Add

One identical Jinja payload on every country SiteGroup.

| Field | Value |
|---|---|
| inventory_mode | Automatic (1) |
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

Assign to SiteGroups: CH, HU, JP, KR, NL, US, CN.

Fields `os`, `os_full`, etc. are filled by Zabbix templates when inventory_mode is Automatic.

---

## 11. ZabbixMacros (role thresholds)

Path: **Zabbix → Macros → Add**  
(`ZabbixMacro` carries `assigned_object_type` / `assigned_object_id` inline — no separate assignment object.)

| Macro | Value | DeviceRole |
|---|---|---|
| `{$CPU.UTIL.CRIT}` | 90 | MSSQL |
| `{$CPU.UTIL.CRIT}` | 80 | Server |
| `{$IF.UTIL.MAX}` | 80 | Switch Core |
| `{$IF.UTIL.MAX}` | 90 | Switch Dist |
| `{$MEM.UTIL.CRIT}` | 85 | VDI |
| `{$MSSQL.DSN}` | nbxsync | MSSQL |
| `{$VMWARE.URL}` | `https://{{ object.name }}/sdk` | vCenter |

**Do not create self-referencing host macros** that shadow Zabbix globals. Define secrets only in Zabbix → Administration → General → Macros:

- `{$MSSQL.USER}`, `{$MSSQL.PASSWORD}`
- `{$VMWARE.USER}`, `{$VMWARE.PASSWORD}`
- `{$PURESTORAGE.TOKEN}`
- `{$SNMP_AUTHPASS}`, `{$SNMP_PRIVPASS}`

The zero-touch script **deletes** host macros named like those shadow macros if present.

---

## 12. Plugin settings (`configuration.py`)

Use the current string-valued `statusmapping` (not the old `0`/`1` integers). Set `exclude_tag` for §9.3.

```python
PLUGINS_CONFIG = {
    'nbxsync': {
        'sot': {
            'proxygroup': 'netbox',
            'proxy': 'netbox',
            'macro': 'netbox',
            'host': 'netbox',
            'hostmacro': 'netbox',
            'hostgroup': 'netbox',
            'hostinterface': 'netbox',
            'hosttemplate': 'netbox',
            'maintenance': 'netbox',
        },
        'statusmapping': {
            'device': {
                'active': 'enabled',
                'planned': 'disabled',
                'failed': 'deleted',
                'staged': 'disabled',
                'offline': 'deleted',
                'inventory': 'deleted',
                'decommissioning': 'deleted',
            },
            'virtualmachine': {
                'offline': 'deleted',
                'active': 'enabled',
                'planned': 'enabled_in_maintenance',
                'paused': 'enabled_no_alerting',
                'failed': 'deleted',
            },
        },
        'snmpconfig': {
            'snmp_community': '{$SNMP_COMMUNITY}',
            'snmp_authpass': '{$SNMP_AUTHPASS}',
            'snmp_privpass': '{$SNMP_PRIVPASS}',
        },
        'exclude_tag': 'do_not_monitor',
        'no_alerting_tag': 'NO_ALERTING',
        'no_alerting_tag_value': '1',
        'attach_objtag': True,
        'objtag_type': 'nb_type',
        'objtag_id': 'nb_id',
        'allow_inherited_deletion': False,
        'adopt_existing_hosts': False,
        'backgroundsync': {
            'objects': {'enabled': True, 'interval': 60},
            'templates': {'enabled': True, 'interval': 1440},
            'proxies': {'enabled': True, 'interval': 1440},
            'maintenance': {'enabled': True, 'interval': 15},
        },
    },
}
```

Keep the default `inheritance_chain` from plugin docs (device/role/platform/manufacturer first; Site/SiteGroup/Region appended). Do not put SiteGroup paths ahead of Role or they can override role SNMP floors.

---

## 13. Resolution quick reference

| Object | Effective CG | Typical templates | Interfaces | Hostgroups |
|---|---|---|---|---|
| Linux server (role Server) | Server Agent+OOB | Linux by agent (+ iDRAC if Dell + oob_ip) | Agent @ primary + SNMP @ oob_ip | Sites/…, Roles/Server, OS/Linux |
| Linux/Windows VM | Agent (SiteGroup) | OS by agent (rule) | Agent @ primary | Sites/…, Roles/…, OS/… |
| VM + tag `snmp` + VM by SNMP CG | VM by SNMP | Linux/Windows by SNMP | SNMP only | Sites/…, Roles/…, OS/… |
| Switch / AP / Firewall | SNMP Monitoring | Role floor + platform rule if match | SNMP @ primary | Sites/…, Roles/…, OS/Network |
| Storage | SNMP Monitoring | Storage Generic by SNMP | SNMP | Sites/…, Roles/Storage, … |
| Pure Storage | Agent (SiteGroup) | Pure HTTP | Agent | Sites/…, Roles/Pure Storage |
| Cohesity (physical, oob only) | OOB SNMP Only | Storage Generic (+ iDRAC if Dell) | SNMP @ oob_ip | Sites/…, Roles/Cohesity |
| Cohesity VM + primary_ip4 | SNMP Monitoring (direct) | Storage Generic | SNMP @ primary | … |
| + NetBox tag `critical` | *(unchanged)* | *(unchanged)* | *(unchanged)* | + Priority/Critical |
| New role tomorrow | Agent (SiteGroup) unless listed in §5b | OS rule if platform set | Agent | Roles/\<new\> auto |
| Bare cluster VM, `site=None` | none | — | — | unprofiled until site/scope set |

---

## 14. Verification

```bash
python scripts/configure_nbxsync_zerotouch.py --verify
```

Expect near-zero: unprofiled hosts under managed SiteGroups, SNMP-role hosts stuck on Agent IF, SNMP templates without SNMP IF, shadow host macros, Manufacturer transport CGs, `os_family` tags, Managed/Teams hostgroups leftover from the old checklist.

Lab proof: `python scripts/configure_nbxsync_zerotouch.py --simulate` → **41/41** (see `/opt/cursor/artifacts/ZEROTOUCH_CONFIGURE_SIM_REPORT.md`).

---

## 15. Zabbix-native follow-ups (out of nbxsync, still required)

Hang these off the groups/tags above:

1. Actions / escalations on `Priority/Critical`, `Roles/*`, `Sites/*`
2. User group permissions on parent `Sites/<country>` with “apply to subgroups”
3. Dashboards: `python scripts/create_dashboards.py` (filters on parent `Sites/CH`, `Roles/…`, `OS/…` — nesting expands in UI widgets)
4. Proxy-group HA (2+ proxies in CH Proxy Group) where needed
5. Maintenance windows / trigger dependencies

---

## One-line standard

**SiteGroup decides default transport and proxy; role decides transport exceptions (network, storage, server BMC, Cohesity OOB); DeviceType/Manufacturer/platform decide templates at the most specific true level; tags only add orthogonal overlays — never transport.**
