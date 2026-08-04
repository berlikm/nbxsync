# nbxSync Configuration Checklist

Step-by-step configuration in NetBox. Execute in order for the initial build. Day-2 procedures are in §15; verification in §16.

This checklist is for **GUI operators**. Fill in production URLs, tokens, and secrets when you apply it in the target environment.

**Last verified:** 2026-08-04 against NetBox 4.x / Zabbix 7.0.x (lab). Update this stamp when you re-validate against production.

**Canonical copy:** keep one authoritative home (this repo file or Confluence). If both exist, the other must be a pointer only — do not maintain two full copies by hand.

---

## Design (why it is built this way)

Monitoring membership and transport should follow **facts already in NetBox** (site, role, platform, manufacturer, a few tags). Operators encode business knowledge once; new devices onboard without new hand-maintained rows.

| Fact in NetBox | Encoded as | Effect in Zabbix |
|---|---|---|
| Country / site | Hostgroup template on each country Site Group | Nested full path `Sites/<country>/…/<site>` (Site Group ancestry) |
| Function (role) | Hostgroup template on each country Site Group | `Roles/<role name>` |
| Platform / OS | Template Rule (regex on platform name) | OS template + `OS/Linux`, `OS/Windows`, `OS/Network`, or `OS/VMware` |
| Criticality | NetBox tag `critical` | Hostgroup `Priority/Critical` |
| Default transport | Configuration group **Agent Monitoring** on each country Site Group | Zabbix agent on the primary IP |
| Network / SNMP-only storage | Configuration group **SNMP Monitoring** on those roles | SNMP on the primary IP |
| Server with BMC | Configuration group **Server Agent+OOB** on role Server | Agent on primary IP **and** SNMP on the out-of-band IP |
| Cohesity physical (OOB only) | Configuration group **OOB SNMP Only** on role Cohesity | SNMP on the out-of-band IP only |
| VM or server monitored by SNMP (override) | Configuration group **SNMP by tag** on that object + NetBox tag `snmp` | SNMP interface + Linux/Windows by SNMP templates |
| Application / OEM extras | Template assignment on Role or Manufacturer | Extra templates merged with the OS template |

### Why hostgroups hang on Site Groups (including Roles)

Zabbix hostgroups are the primary axis for dashboards, permissions, and alert routing. Two orthogonal trees cover almost every view:

- **Location** — `Sites/…` with the full Site Group chain (country → campus → site), e.g. `Sites/CH/CH-STA/CH-STA-L42`
- **Function** — `Roles/…` (what the host is)

Both templates are assigned on the **country Site Group**, not on every Device Role or every Site:

1. **One row per country** — a new Device Role tomorrow still gets `Roles/<name>` automatically; you do not open the checklist again.
2. **Same inheritance path as proxy and default transport** — country Site Group is already the control plane for “everything under this country.”
3. **Jinja renders against the device/VM at sync** — `{{ object.role.name }}` and `{{ object.site… }}` resolve on the real host, so a Site Group assignment is enough.

`OS/…` is a third tree for OS-centric views. It is attached by **Template Rules** (platform match), because OS is a property of the platform, not of the country.

### Why transport uses configuration groups (not tags)

Exactly **one** configuration group decides how the host is reached (agent vs SNMP vs OOB). Hostgroups and templates can stack freely; transport cannot. Tags are for overlays only (`critical`, `snmp` OS flavor, `do_not_monitor`). Putting transport on a tag would silently override role and site defaults.

Role-level SNMP / Server Agent+OOB **overrides** the country Site Group’s Agent default. Assign Agent Monitoring on **country** Site Groups only — not on campus mid-levels (those would win over the country default).

### Where to look in the GUI

- Role or Manufacturer **templates** appear on the Role (or Template) page.
- `OS/*` membership comes from Template Rules — inspect under **Zabbix → Template Rules**. A hostgroup detail page may also list those rules when that card is available.

---

## GUI nomenclature

The plugin registers one top-level menu labelled **Zabbix** with: Servers, Proxies, Proxy Groups, Templates, Macros, Tags, Hostgroups, Configuration groups, Maintenance, Template Rules.

**Add pattern:** most child objects (assignments, host interfaces, host inventory) are added from a parent object’s detail page or its **Zabbix** tab. The tab’s Add buttons open the form with the parent already selected.

The Zabbix tab appears on: Site Group, Site, Region, Cluster, Cluster Type, Manufacturer, Device Type, Device Role, Platform, Device, Virtual Machine, Virtual Device Context.

**NetBox data you need before starting** (created in NetBox itself, not in the Zabbix menu):

- Country Site Groups with slugs: `ch`, `hu`, `jp`, `kr`, `nl`, `us`, `cn`
- Device Roles named exactly as listed in this checklist
- Platforms whose names match the Template Rule patterns
- For BMC monitoring: each server’s **out-of-band IP** (`oob_ip`) filled in; without it the OOB SNMP interface is skipped
- Required Zabbix templates already present in Zabbix (import any that are missing before assigning them here)

---

## 1. Zabbix Server

Path: **Zabbix → Servers → Add**

| Field | Value |
|---|---|
| Name | Zabbix Production |
| URL | *(production Zabbix URL)* |
| Token | *(API token)* |
| Validate certs | True |
| Sync enabled | True |
| Skip version check | False |

**Validate certs = True** requires an **HTTPS** URL with a certificate chain trusted by the NetBox host. With HTTP, or with HTTPS and an untrusted/self-signed cert and validation left on, the first sync fails in a confusing way. Production (Zabbix Cloud) must use HTTPS + validation on.

---

## 2. Proxies and proxy groups

Path: **Zabbix → Proxies → Add**, **Zabbix → Proxy Groups → Add**

**Why:** collectors are a geography decision. Binding proxy (or proxy group) on the country Site Group means every device under that country inherits the collector without per-host proxy rows. JP has no local proxy, so it uses KR; NL and US share the CH proxy group.

### 2.1 Proxy group

| Name | Zabbix server | Description |
|---|---|---|
| CH Proxy Group | Zabbix Production | Proxy group for CH-based monitoring (NL and US route through CH) |

### 2.2 Proxies

| Name | Mode | Proxy group | Local address | Local port |
|---|---|---|---|---|
| ch-proxy-1 | Active | CH Proxy Group | 127.0.0.1 | 10051 |
| hu-proxy-1 | Active | — | — | — |
| kr-proxy-1 | Active | — | — | — |
| cn-proxy-1 | Active | — | — | — |

Proxy IDs must match the proxies that already exist in Zabbix under these names.

---

## 3. Server assignment (per country Site Group)

Path: **Site Group → Zabbix tab → Zabbix Servers → Add**

Create one assignment per country Site Group. Set a **proxy or a proxy group** — not both. Assignment always flows NetBox → Zabbix.

| Site Group | Proxy | Proxy group | Sync enabled |
|---|---|---|---|
| CH | — | CH Proxy Group | Yes |
| HU | hu-proxy-1 | — | Yes |
| JP | kr-proxy-1 | — | Yes |
| KR | kr-proxy-1 | — | Yes |
| NL | — | CH Proxy Group | Yes |
| US | — | CH Proxy Group | Yes |
| CN | cn-proxy-1 | — | Yes |

---

## 4. Configuration groups

Path: **Zabbix → Configuration groups → Add**

**Why five groups:** each is one transport profile. Keeping Agent default, SNMP exception, dual-plane server BMC, per-VM SNMP, and OOB-only hardware as separate named profiles makes the effective profile obvious on the object and avoids mixing unrelated interface sets.

| Name | Description |
|---|---|
| SNMP Monitoring | SNMP v3 for network devices and SNMP-only storage |
| Agent Monitoring | Default agent transport (assigned on country Site Groups) |
| Server Agent+OOB | Server profile: agent on primary IP + SNMP on out-of-band IP |
| SNMP by tag | SNMP transport for selected Devices/VMs (pair with NetBox tag `snmp` for OS templates) |
| OOB SNMP Only | SNMP on out-of-band IP only — hardware without a primary IP (e.g. Cohesity nodes) |

---

## 5. Host interfaces (on configuration groups)

Path: **Zabbix → Configuration groups → [group] → Host Interfaces → Add**

**Why on the group, not on every device:** the interface *shape* (agent port, SNMPv3 credentials, OOB flag) is shared; only the IP is per device. Sync fills primary IP or out-of-band IP at runtime. Leave the IP field empty on the definition.

**Type** selects Agent or SNMP. **Interface type** = Default for the primary interface of that kind.

### Shared SNMPv3 settings

Use these on every SNMP interface in this checklist:

| Field | Value |
|---|---|
| SNMP version | 3 |
| SNMP bulk | True |
| SNMP max repetitions | 10 |
| SNMPv3 security name | MONITORING |
| SNMPv3 security level | authPriv |
| SNMPv3 auth protocol | SHA256 |
| SNMPv3 auth passphrase | `{$SNMP_AUTHPASS}` |
| SNMPv3 priv protocol | AES128 |
| SNMPv3 priv passphrase | `{$SNMP_PRIVPASS}` |
| SNMP push community | False |

Define the real passphrase values as global macros in Zabbix (Administration → General → Macros).

### 5.1 SNMP Monitoring

| Field | Value |
|---|---|
| Type | SNMP |
| Interface type | Default |
| Port | 161 |
| Use IP | Yes |
| Use OOB IP | No |
| + SNMPv3 settings above | |

### 5.2 Agent Monitoring

| Field | Value |
|---|---|
| Type | Agent |
| Interface type | Default |
| Port | 10050 |
| Use IP | Yes |
| TLS connect | No encryption |

### 5.3 Server Agent+OOB (two interfaces on the same group)

**Why both on one group:** a server is one monitoring profile with two planes (OS on the production network, BMC on the management network). One configuration group keeps that pairing atomic — you cannot inherit agent from one place and OOB SNMP from another and lose one side.

**Agent interface** (primary IP):

| Field | Value |
|---|---|
| Type | Agent |
| Interface type | Default |
| Port | 10050 |
| Use IP | Yes |
| Use OOB IP | No |
| TLS connect | No encryption |

**SNMP interface** (out-of-band IP):

| Field | Value |
|---|---|
| Type | SNMP |
| Interface type | Default |
| Port | 161 |
| Use IP | Yes |
| Use OOB IP | **Yes** |
| + SNMPv3 settings above | |

If a device has no out-of-band IP, the SNMP interface is skipped; the agent interface still syncs.

### 5.4 SNMP by tag

Same as §5.1 (SNMP, port 161, Use OOB IP = No). Do not attach templates to this configuration group — OS templates come from Template Rules in §6 when the object has NetBox tag `snmp`.

**Why split transport and template:** the same SNMP interface serves Linux and Windows (and both Devices and VMs); the correct OS SNMP template is chosen by platform + tag, not by a single generic template on the group. Use this whenever a host must be SNMP-monitored instead of agent — not only for VMs.

### 5.5 OOB SNMP Only

Same SNMPv3 as the Server Agent+OOB SNMP side (Use OOB IP = Yes). For hardware that only has an out-of-band IP (no primary IP to run an agent against).

---

## 5b. Configuration group assignments

Path: **Zabbix → Configuration groups → [group] → Assignments → Add**  
(or Site Group / Device Role → Zabbix tab)

Without these assignments, the group’s interfaces are not applied during sync.

### Agent Monitoring → each country Site Group

**Why on the Site Group:** almost every server-class and application role speaks the Zabbix agent. Putting the default on the country once means unknown or brand-new roles are still monitored. Roles that must use SNMP (or dual-plane BMC) override this at the Device Role level below.

| Configuration group | Assigned to |
|---|---|
| Agent Monitoring | Site Group CH |
| Agent Monitoring | Site Group HU |
| Agent Monitoring | Site Group JP |
| Agent Monitoring | Site Group KR |
| Agent Monitoring | Site Group NL |
| Agent Monitoring | Site Group US |
| Agent Monitoring | Site Group CN |

**Pure Storage** stays on this Agent default (plus its HTTP template in §7). It is polled over HTTP/agent paths, not as SNMP-only storage.

### SNMP Monitoring → Device Roles

**Why role exceptions:** switches, APs, firewalls, and SNMP-only storage have no useful agent. Assigning SNMP on the role overrides the country Agent default for those classes only.

| Configuration group | Device Role |
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

### Server Agent+OOB → Server

| Configuration group | Device Role |
|---|---|
| Server Agent+OOB | Server |

### OOB SNMP Only → Cohesity (physical)

| Configuration group | Device Role |
|---|---|
| OOB SNMP Only | Cohesity |

### Cohesity virtual machines with a primary IP

Active Cohesity VMs that have a primary IPv4 address need a **direct** assignment to **SNMP Monitoring** (they have no out-of-band IP, so OOB SNMP Only would not work). Assign each such VM individually.

This is a standing manual task until a cleaner NetBox signal exists (for example a dedicated role or tag that selects SNMP Monitoring). When you invent Cohesity VMs, check this list; put it on the recurring ops checklist in §15.

### SNMP by tag (per Device or VM)

For each host that must use SNMP instead of agent (including physical Linux/Windows servers):

1. Assign configuration group **SNMP by tag** to that Device or VM.
2. Add NetBox tag **`snmp`** (so §6 attaches Linux/Windows by SNMP).

### Manufacturer

Dell iDRAC is a **template** via TemplateRule Dell ∧ Server (§6 / §7 note), not a Manufacturer-wide assignment and not a configuration group. Transport for Dell servers already comes from Server Agent+OOB on the Server role.

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

| Template name in Zabbix |
|---|
| Windows by Zabbix agent |
| Linux by Zabbix agent |
| Linux by SNMP |
| Windows by SNMP |
| Extreme EXOS by SNMP |
| Network Generic Device by SNMP |
| FortiGate by SNMP |
| VMware FQDN |
| Storage Generic Device by SNMP |
| Dell iDRAC by SNMP |
| MSSQL by ODBC |
| Pure Storage FlashArray v1 by HTTP |
| GitLab by HTTP |

**Storage Generic Device by SNMP:** clone from Network Generic Device by SNMP **without** items that collide with Dell iDRAC (`snmptrap.fallback` and `zabbix[host,snmp,available]`). Preferred method in the Zabbix UI: **Export** the Network Generic template as YAML → delete those two items (and keep discovery rules, prototypes, triggers, value maps) → **Import** under the new name `Storage Generic Device by SNMP`. Do not recreate the template by copying items one-by-one in the UI — that drops LLD and related objects. Import Dell iDRAC from the Zabbix template library if it is not already installed.

**How matching works**

- The **pattern** is a **case-insensitive regular expression**, matched with `search` (substring of the platform name — **not** a full-string match, and **not** a plain text substring). Examples in the table (`Ubuntu|Debian|…`, `Other.*Linux`) are regex. A literal platform string pasted as the pattern (for example `Windows Server 2019 (x64)`) may never match or may be an invalid regex — write a real expression (for example `Windows Server`).
- **Every matching rule contributes** its template and optional hostgroup. Priority only sets **evaluation order** (`order_by priority, name`). A template (or hostgroup) already resolved by an earlier rule or an explicit assignment is not added twice. A higher-priority rule does **not** suppress a lower-priority rule that points at a *different* template. To stop a catch-all from also applying, narrow its pattern or disable it — do not assume “lower number wins exclusively.” (Today Windows Server and Windows catch-all both point at the same template, so the collision is invisible.)

Leave “require tags” empty unless noted.

### 6.1 Platform rules

| Name | Pattern | Template | Hostgroup | Require tags | Priority | Enabled |
|---|---|---|---|---|---|---|
| Windows Server | `Windows Server` | Windows by Zabbix agent | OS/Windows | — | 50 | Yes |
| Windows catch-all | `Windows` | Windows by Zabbix agent | OS/Windows | — | 200 | Yes |
| Linux | `Ubuntu\|Debian\|Linux\|Red Hat\|CentOS\|Alma\|SUSE\|Arch\|Photon\|Other.*Linux` | Linux by Zabbix agent | OS/Linux | — | 100 | Yes |
| Extreme EXOS | `EXOS` | Extreme EXOS by SNMP | OS/Network | — | 100 | Yes |
| Extreme VOSS | `VOSS` | Network Generic Device by SNMP | OS/Network | — | 100 | Yes |
| Extreme IQ Engine | `IQ ENGINE` | Network Generic Device by SNMP | OS/Network | — | 100 | Yes |
| FortiOS | `FORTIOS\|FortiOS` | FortiGate by SNMP | OS/Network | — | 100 | Yes |
| FortiAnalyzer/Manager | `FortiAnalyzer\|FortiManager` | Network Generic Device by SNMP | OS/Network | — | 50 | Yes |
| VMware ESXi | `ESXi\|VMware ESX\|vSphere` | VMware FQDN | OS/VMware | — | 100 | Yes |
| VMware Photon | `Photon` | Linux by Zabbix agent | OS/Linux | — | 50 | Yes |

### 6.2 SNMP OS rules (NetBox tag `snmp`)

Use together with configuration group **SNMP by tag** for the interface.

**Why a tag gate:** only selected hosts should switch from agent OS templates to SNMP OS templates. The tag is an explicit operator choice; the configuration group supplies the SNMP interface (Device or VM).

| Name | Pattern | Template | Hostgroup | Require tags | Priority | Enabled |
|---|---|---|---|---|---|---|
| SNMP Linux (tag) | *(same Linux pattern as above)* | Linux by SNMP | OS/Linux | snmp | 40 | Yes |
| SNMP Windows (tag) | `Windows` | Windows by SNMP | OS/Windows | snmp | 40 | Yes |

---

## 7. Template assignments (Role / Manufacturer)

Path: **Zabbix → Templates → [template] → Assigned objects → Add**  
(or Device Role / Manufacturer → Zabbix tab)

**Why here:** application and OEM templates are business knowledge (“MSSQL role gets MSSQL by ODBC”). They **merge** with OS templates from §6 and with Manufacturer templates — different template IDs all accumulate; nothing is subtracted. Role **floors** (Network Generic on switches, FortiGate on Firewall, Storage Generic on Storage/Cohesity) cover devices whose platform is missing or does not match a specialized rule; when the platform *does* match (e.g. EXOS, FortiOS), the Template Rule adds the specialized template as well.

**Interface requirements (silent drop):** each nbxsync Template can declare required interface types (Agent, SNMP, ANY, …). At sync, a template is **linked only if the host already has those interface types**. If the requirement is not met, the template is skipped with no dramatic error — it simply does not appear on the Zabbix host. That makes broad Manufacturer/Role assignment safer across transport classes. It does **not** prevent two SNMP templates from both linking and colliding on item keys — that still needs compatible templates or narrower assignment (see Storage Generic vs iDRAC).

| Template | Assigned to | Notes |
|---|---|---|
| MSSQL by ODBC | Device Role MSSQL | |
| MSSQL by ODBC | Device Role MSSQL Query Server | |
| VMware FQDN | Device Role vCenter | Used when a dedicated vCenter HTTP template is not available |
| Pure Storage FlashArray v1 by HTTP | Device Role Pure Storage | Pure stays on Agent transport |
| GitLab by HTTP | Device Role GitLab | |
| Linux by SNMP | Device Role Virtual Appliance | Baseline if platform does not match a rule |
| Network Generic Device by SNMP | Device Role Network Device | Baseline |
| Storage Generic Device by SNMP | Device Role Storage | Avoids item collision with iDRAC |
| Storage Generic Device by SNMP | Device Role Cohesity | |
| Network Generic Device by SNMP | Device Role Switch Core | Baseline if platform is missing |
| Network Generic Device by SNMP | Device Role Switch Dist | |
| Network Generic Device by SNMP | Device Role Switch Access | |
| Network Generic Device by SNMP | Device Role Switch Mgmt | |
| Network Generic Device by SNMP | Device Role Access Point | |
| FortiGate by SNMP | Device Role Firewall | Baseline; FortiOS rule still adds when platform matches |
| Dell iDRAC by SNMP | *(see note)* | Prefer TemplateRule: Manufacturer Dell ∧ role Server — not Manufacturer-wide |

**Dell iDRAC (scalable scoping):** do **not** assign iDRAC on Manufacturer Dell (additive merge pulls it onto Dell storage and other SNMP Dell hosts — lab-verified). Preferred pattern: TemplateRule with platform `.*`, `role_pattern=^Server$`, **Manufacturer = Dell**, template Dell iDRAC (no NetBox tag required). Transport stays **Server Agent+OOB** + `oob_ip`. OEM model templates stay on Device type (they **add**, they do not remove iDRAC). Full options analysis: `docs/dell-idrac-scoping-options.md`. Empty `oob_ip` skips the OOB SNMP interface only.

---

## 8. Hostgroups

Path: **Zabbix → Hostgroups → Add**, then assignments on each hostgroup or from the Site Group / tag Zabbix tab.

**Why these four axes:** location, function, OS, and criticality are the views operations actually use. Keeping them as hostgroups (not duplicated as tags) matches how Zabbix dashboards, permissions, and actions filter.

### 8.1 Sites

| Name | Value | Assign to |
|---|---|---|
| Sites | `Sites/{{ object.site.group.get_ancestors(include_self=True) \| map(attribute="name") \| join("/") }}/{{ object.site.name }}` | Site Groups CH, HU, JP, KR, NL, US, CN |

This is the configured Sites value. `get_ancestors(include_self=True)` walks the Site Group tree so the Zabbix path always includes the country:

| NetBox layout | Rendered hostgroup | Parents created |
|---|---|---|
| Site under campus CH-STA (parent CH) | `Sites/CH/CH-STA/CH-STA-L42` | `Sites`, `Sites/CH`, `Sites/CH-STA` |
| Site directly under country CH | `Sites/CH/<site>` | `Sites`, `Sites/CH` |

Hosts stay members of the **leaf** only. Country dashboards and location filters use parent `Sites/CH` (nested children included) — do not also put hosts in a flat country group. Monitoring access in Zabbix is **global** (flat organisation); nested Sites are for location views, not regional RBAC. A preview error when viewing the assignment on a Site Group is cosmetic and does not affect sync.

### 8.2 Roles

| Name | Value | Assign to |
|---|---|---|
| Roles | `Roles/{{ object.role.name }}` | Site Groups CH, HU, JP, KR, NL, US, CN |

Assigned on each country Site Group so every device under that country inherits the Roles template; the role *name* still comes from the device. See **Design** above.

### 8.3 OS hostgroups

Created in §6. Membership is applied by Template Rules when the platform matches.

### 8.4 Priority / Critical

**Why a tag → hostgroup:** criticality is an orthogonal overlay. Operators mark individual devices with NetBox tag `critical`; the single hostgroup assignment turns that into Zabbix membership for 24/7 escalation without maintaining per-device hostgroup rows.

| Name | Value | Assign to |
|---|---|---|
| Priority/Critical | `Priority/Critical` | NetBox tag `critical` |

To mark a device: add NetBox tag `critical`. To unmark: remove the tag.

---

## 9. Tags

**Why few tags:** team, site, role, OS, and priority already live in hostgroups. Tags carry only what is not derivable from those trees and is still useful for filtering or gating rules.

### 9.0 NetBox tags (create under NetBox → Tags)

| Name | Purpose |
|---|---|
| `do_not_monitor` | Exclude from monitoring (see §9.3 and plugin settings) |
| `critical` | Membership in hostgroup Priority/Critical |
| `snmp` | Selects Linux/Windows by SNMP Template Rules; does not change transport by itself — pair with configuration group **SNMP by tag** |

### 9.1 Environment (Jinja on Site Groups)

Path: **Zabbix → Tags → Add**, then assign to each country Site Group.

**Why Jinja from the hostname:** environment is encoded in naming conventions already; deriving it avoids a second manual taxonomy.

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

**Failure mode:** names that do not match the `-p-` / `-d-` / … conventions resolve to **`Unknown` with no alert**. That is silent. If environment tagging matters for routing, spot-check hosts that look odd in naming, or tighten the convention.

### 9.2 Cluster

| Tag | Value | Assign to |
|---|---|---|
| cluster | `{{ object.cluster.name }}` | each Cluster |

### 9.3 Exclusion

| Tag | Value | Assign to Device Role |
|---|---|---|
| do_not_monitor | *(empty)* | Messpc, Sd Wan Socket, VDI |

Plugin setting `exclude_tag` must be set to `do_not_monitor` (section 12).

---

## 10. Host inventory

Path: Site Group → Zabbix tab → Host Inventory → Add

**Why one payload on every country Site Group:** inventory fields are the same mapping everywhere; only the device data changes. Country assignment keeps inventory on the same control plane as Sites, Roles, proxy, and Agent default.

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

## 11. Macros (role thresholds)

Path: **Zabbix → Macros → Add**

**Why on the role:** thresholds and DSN names are class-wide policy. Secrets stay as Zabbix global macros so they are not copied into NetBox.

A macro is both definition and assignment (choose Device Role on the form).

| Macro | Value | Device Role |
|---|---|---|
| `{$CPU.UTIL.CRIT}` | 90 | MSSQL |
| `{$CPU.UTIL.CRIT}` | 80 | Server |
| `{$IF.UTIL.MAX}` | 80 | Switch Core |
| `{$IF.UTIL.MAX}` | 90 | Switch Dist |
| `{$MEM.UTIL.CRIT}` | 85 | VDI |
| `{$MSSQL.DSN}` | nbxsync | MSSQL |
| `{$VMWARE.URL}` | `https://{{ object.name }}/sdk` | vCenter |

Define secrets once as **global** macros in Zabbix:

- `{$MSSQL.USER}`, `{$MSSQL.PASSWORD}`
- `{$VMWARE.USER}`, `{$VMWARE.PASSWORD}`
- `{$PURESTORAGE.TOKEN}`
- `{$SNMP_AUTHPASS}`, `{$SNMP_PRIVPASS}`

---

## 12. Plugin settings

Ask the NetBox administrator to set the following under the nbxsync plugin configuration (adjust intervals if your environment differs).

| Setting | Intended value |
|---|---|
| Source of truth for host, hostgroup, interface, template, tag, macro, proxy, maintenance | NetBox |
| Exclude tag | `do_not_monitor` |
| No-alerting tag / value | `NO_ALERTING` / `1` |
| Attach object identity tags | Yes (`nb_type` / `nb_id`) |
| Allow inherited deletion | No |
| Adopt existing Zabbix hosts | No |
| Device status → Zabbix | active → enabled; planned/staged → disabled; failed/offline/inventory/decommissioning → deleted |
| VM status → Zabbix | active → enabled; planned → enabled in maintenance; paused → enabled with no-alerting tag; failed/offline → deleted |
| SNMP community / auth / priv macro names | `{$SNMP_COMMUNITY}`, `{$SNMP_AUTHPASS}`, `{$SNMP_PRIVPASS}` |

Keep Site / Site Group inheritance **after** role and platform in the inheritance order so country defaults do not override role SNMP or Server Agent+OOB.

---

## 13. What a typical host should look like

| Object | Configuration group | Typical templates | Interfaces | Hostgroups |
|---|---|---|---|---|
| Linux server (role Server) | Server Agent+OOB | Linux by agent (+ Dell iDRAC if Dell and oob IP set) | Agent on primary + SNMP on oob IP | Sites/CH/…, Roles/Server, OS/Linux |
| Linux or Windows VM | Agent Monitoring (from Site Group) | OS by agent (Template Rule) | Agent on primary | Sites/CH/…, Roles/…, OS/… |
| VM or Device with tag `snmp` + SNMP by tag | SNMP by tag | Linux or Windows by SNMP | SNMP only | Sites/CH/…, Roles/…, OS/… |
| Switch / AP / Firewall | SNMP Monitoring | Role baseline + specialized template if platform matches | SNMP on primary | Sites/CH/…, Roles/…, OS/Network |
| Storage | SNMP Monitoring | Storage Generic by SNMP | SNMP | Sites/CH/…, Roles/Storage |
| Pure Storage | Agent Monitoring (from Site Group) | Pure Storage by HTTP | Agent | Sites/CH/…, Roles/Pure Storage |
| Cohesity physical (oob only) | OOB SNMP Only | Storage Generic (+ iDRAC if Dell) | SNMP on oob IP | Sites/CH/…, Roles/Cohesity |
| Cohesity VM with primary IP | SNMP Monitoring (direct) | Storage Generic | SNMP on primary | … |
| Any of the above + tag `critical` | unchanged | unchanged | unchanged | + Priority/Critical |
| Brand-new role tomorrow | Agent Monitoring (from Site Group) unless listed in §5b | OS Template Rule if platform set | Agent | Roles/\<new name\> appears automatically |
| VM on a cluster with no site | none | — | — | Not profiled until the VM or cluster has a site |

---

## 14. After configuration (Zabbix side)

These hang off the hostgroups and tags above; they are configured in Zabbix, not in nbxsync:

1. Alert actions / escalations using `Priority/Critical`, `Roles/*`, and `Sites/*`
2. User group permissions — **global** across the estate (flat organisation); nested `Sites/CH` remains available for location-scoped views if ever needed, but we are not splitting access by continent/region
3. Dashboards filtered on parent groups (`Sites/CH`, `Roles/Switch Core`, `OS/Linux`, …) — nested site groups are included by the UI
4. Extra proxies in CH Proxy Group if you need high availability
5. Maintenance windows and trigger dependencies as needed

---

## 15. Day-2 operations (after go-live)

Initial build is §§1–14. After that, operators mostly do the following.

### 15.1 New Device Role appeared

1. Does it need a **transport exception**? If it is agent-class → nothing (Site Group Agent default). If SNMP-only network/storage → assign **SNMP Monitoring** (§5b). If dual-plane BMC server → **Server Agent+OOB**. If OOB-only → **OOB SNMP Only**.
2. Does it need an **application template**? Add a Template assignment on the role (§7).
3. Hostgroup `Roles/<name>` appears automatically from the Sites/Roles Jinja — do not create a per-role hostgroup assignment.

### 15.2 New Platform appeared

1. Does an existing Template Rule pattern already match? Check with the real platform name (regex `search`).
2. If not, add or extend a rule in §6 (remember: every matching rule contributes — do not rely on priority to suppress another rule’s different template).
3. Confirm the template’s **interface requirements** match the transport the host will have.

### 15.3 New application template

1. Import/create the template in Zabbix; create the nbxsync Template object.
2. Set interface requirements (Agent / SNMP / ANY).
3. Assign on the Device Role (or Device type / Manufacturer if that is the true scope) — §7.

### 15.4 This host is not monitored / has the wrong templates

Work top-down:

1. **Excluded?** NetBox tag `do_not_monitor` (or role with that Zabbix tag) and plugin `exclude_tag`.
2. **Site / Site Group?** Device or VM must resolve into a managed country (site set; cluster VMs need site or cluster site scope). No site → not profiled (§13).
3. **Effective configuration group?** On the device/VM Zabbix tab (or inherited from role / Site Group). Wrong CG → wrong interfaces.
4. **Interfaces present?** Agent and/or SNMP as expected; for BMC, is `oob_ip` set?
5. **Template interface requirements?** Template needing Agent will not link on an SNMP-only host (silent drop) — §7.
6. **Template Rules?** Platform name vs rule regex; `require_tags` (e.g. `snmp`); enabled flag. Remember all matching rules apply.
7. **Status mapping?** Planned/offline/etc. may disable or delete the Zabbix host (§12).
8. Re-sync the host and compare to the §13 expected-state row for that class.

### 15.5 Recurring manual checks

| Task | When |
|---|---|
| Cohesity VMs with primary IP → SNMP Monitoring (§5b) | When such VMs are created or found |
| Spot-check `environment=Unknown` | After naming-convention drift |
| Update “Last verified” stamp at top of this doc | After a production re-validation |

---

## 16. Verification

After the initial build, and after major changes, confirm coverage against §13.

**What “good” looks like (spot-check in GUI / Zabbix):**

| Check | Expect |
|---|---|
| Sample Linux server | Server Agent+OOB; agent + oob SNMP; OS/Linux; Roles/Server; leaf under `Sites/CH/…` |
| Sample switch | SNMP Monitoring; Network Generic and/or EXOS/FortiOS; OS/Network; leaf under `Sites/CH/…` |
| Sample Windows VM | Agent; Windows by agent; OS/Windows; leaf under `Sites/CH/…` |
| Country dashboard / ACL | Filter on parent `Sites/CH` for location views; hosts are leaf members only. Org access is global — no regional permission split |
| Host with `critical` | Also in Priority/Critical |
| Role not listed in §5b SNMP/OOB | Still has Agent via Site Group |
| VM without site | No useful profile until site/scope is set |

**Unprofiled / wrong template symptoms:** host missing in Zabbix, empty template list, or only partial stack vs §13. Use the §15.4 ladder.

**If you use the optional configure helper:** it can print a coverage census (`unprofiled`, hosts without templates, SNMP roles stuck on Agent, leftover shadow macros). Treat non-zero counts as tickets: map each metric back to §15.4. The GUI checklist remains the operator source of truth; the helper is a shortcut, not a second policy.

---

## One-line standard

**Country Site Group decides default transport and proxy; role decides transport exceptions; platform / manufacturer decide templates; tags only add overlays — never transport.**
