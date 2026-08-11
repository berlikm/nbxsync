# nbxSync configuration checklist

GUI / API steps to create **nbxSync** objects.  
Mental model and design rules: [`nbxsync-architecture.md`](nbxsync-architecture.md).  
Extreme / domain monitoring design: [`zabbix/`](../zabbix/README.md) (start with [`01-extreme-switching.md`](../zabbix/01-extreme-switching.md)).  
First-build scripts only: [`scripts/README.md`](../scripts/README.md) (Appendix A).

**Last verified:** 2026-08-06 (lab: NetBox 4.x / Zabbix 7.0.x). Update after a production re-check.  
**One home:** if Confluence mirrors this, that page is a pointer only.

| If you are… | Go to |
|---|---|
| New to the design | [`nbxsync-architecture.md`](nbxsync-architecture.md) |
| First estate build | **Before you start** → §§1–12 → §13 → §16 |
| Day-2 / new role or platform | §15 |
| Wrong or missing host | §15.4, then §13 |
| Extreme ports / stages / TEMP_* | [`zabbix/01-extreme-switching.md`](../zabbix/01-extreme-switching.md) |
| LM parity gaps | §17 |
| Bulk first build | [scripts/README.md](../scripts/README.md) |

Placeholders in tables are *(italic)*. Operate in the **GUI or API** after the first build.

### GUI map

Top menu **Zabbix**: Servers, Proxies, Proxy Groups, Templates, Macros, Tags, Hostgroups, Configuration groups, Maintenance, Template Rules. Most assignments and host interfaces are added from a parent’s **Zabbix** tab. Role templates → Role/Template page; `OS/*` membership → Template Rules.

---

## Before you start

In NetBox (not the Zabbix menu):

- [ ] Country Site Groups with slugs: `ch`, `hu`, `jp`, `kr`, `nl`, `us`, `cn`
- [ ] Device Roles named exactly as in this checklist (include **Switch Hybrid**)
- [ ] Platforms whose names match the Template Rule patterns (`EXOS` / `VOSS` in Extreme platform names)
- [ ] Servers that need BMC monitoring have **`oob_ip`** set
- [ ] Required templates already exist in Zabbix (import missing ones first)
- [ ] **Extreme VOSS by SNMP** and **Extreme IQ Engine by SNMP** imported (paths under `zabbix/templates/…`) before enabling those Template Rules in §6 — see Extreme docs for YAML and port grammar
- [ ] SNMP / VMware / Pure / MSSQL secrets available (see §5 and §11.4)

---

## Initial build

Work top to bottom. After §12, jump to §13 and §16 before declaring the estate ready.

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

Each group is one **transport + credential** profile. Why these groups exist and which NetBox facts select them: [`nbxsync-architecture.md`](nbxsync-architecture.md). SNMPv3 user/auth/priv differ by LogicMonitor account — keep them on separate groups.

| Name | Credential / port | Purpose |
|---|---|---|
| SNMP Monitoring | `MONITORING` MD5/DES | Extreme / Forti / AP / network roles |
| SNMP Monitoring (Linux) | `MONITORING-LINUX` SHA/AES | Opt-in Linux/Windows SNMP (tag `snmp`) |
| SNMP Monitoring (SAP) | `SAPUSER` (confirm auth/priv) | SAP HANA and SAP ME roles |
| Agent Monitoring | Agent :10050 | Default transport on country Site Groups |
| Agent Monitoring (SPACE) | Agent :10060 | Space Server role (camLine occupies 10050) |
| Server Agent+OOB | Agent :10050 + `MONITORING-DELL` SHA/AES @ oob | Dell iDRAC dual-plane servers |
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
| Dell iDRAC | Server Agent+OOB (SNMP side) | MONITORING-DELL | SHA1* | AES128 |
| SAP | SNMP Monitoring (SAP) | SAPUSER | *(confirm)* | *(confirm)* |

\*LM export says "SHA"; Zabbix offers SHA1 and SHA256 — use **SHA1** until confirmed.

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

### 5.6 SNMP Monitoring (SAP)

SAP SNMPv3 profile. Transport-only until Robert confirms auth/priv and whether SAP hosts use SNMP at all (many are agent + DNUS scripts only).

### 5.7 Agent Monitoring (SPACE)

| Field | Value |
|---|---|
| Type | Agent |
| Port | **10060** |
| TLS connect | No encryption |

### One-off overrides

| Case | How |
|---|---|
| `HU-DEB-SAN01` (Huawei storage, `LogicMonitor` SHA/AES) | Per-device `ZabbixHostInterface` on that Device — the **Huawei Storage (SNMP)** TemplateRule (§6.3, manufacturer=Huawei) links the template automatically, but this device uses a different SNMPv3 credential (`LogicMonitor`) than any fleet CG. The per-device interface provides the transport with the right credentials. No CG assignment needed on the Storage role for this device. |

---

## 5b. Configuration group assignments

Path: **Zabbix → Configuration groups → [group] → Assignments → Add**  
(or Site Group / Device Role / Tag → Zabbix tab)

Without these assignments, the group’s interfaces are not applied during sync.

### Agent Monitoring → each country Site Group

| Configuration group | Assigned to |
|---|---|
| Agent Monitoring | Site Group CH / HU / JP / KR / NL / US / CN |

**Pure Storage** and generic **Storage** stay on this Agent default (HTTP templates in §7 — not network SNMP).

### SNMP Monitoring → network Device Roles

| Configuration group | Assigned to |
|---|---|
| SNMP Monitoring | Switch Core / Dist / Access / Mgmt / **Hybrid** |
| SNMP Monitoring | Access Point |
| SNMP Monitoring | Firewall |
| SNMP Monitoring | Network Device |
| SNMP Monitoring | Virtual Appliance |

**Do not** assign Storage here. Switch Hybrid uses the same SNMP Monitoring CG as other Switch* roles; only its IFALIAS macros differ (values in `zabbix/01-extreme-switching.md`; create assignments per §11).

### Server / Cohesity / SPACE roles

| Configuration group | Assigned to |
|---|---|
| Server Agent+OOB | Server |
| OOB SNMP Only | Cohesity |
| Agent Monitoring (SPACE) | Space Server |
| SNMP Monitoring (SAP) | SAP HANA |
| SNMP Monitoring (SAP) | SAP ME |

### Zero-touch tag opt-ins

| Configuration group | Assigned to | Operator action |
|---|---|---|
| SNMP Monitoring (Linux) | NetBox tag **`snmp`** | Tag the Device/VM — no per-host CG row |

### Cohesity VMs with a primary IP

Active Cohesity VMs with `primary_ip4` need a **direct** assignment to **SNMP Monitoring** (network profile) — they have no `oob_ip`. Track in §15 until a cleaner signal exists.

### Manufacturer

Do **not** assign Dell iDRAC on Manufacturer Dell. Use Template Rule §6.3 (Dell ∧ Server). OOB SNMP credentials come from **Server Agent+OOB** (`MONITORING-DELL`).

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
| Extreme EXOS by SNMP | Stock (Zabbix 7.0 branch) |
| Extreme VOSS by SNMP | **Import** `zabbix/templates/extreme_voss_snmp/` — not stock |
| Extreme Port Speed Expect by SNMP | Import thin LLD YAML — stage 4 |
| Extreme Routing by SNMP | Import OSPF YAML — post-cutover, Core/Dist |
| Network Generic Device by SNMP | Network Device / FortiAnalyzer fallback only — **not** Switch* or AP (those use Extreme/Forti platform templates) |
| FortiGate by SNMP | |
| VMware FQDN | |
| Storage Generic Device by SNMP | Cohesity (see §7) |
| Dell iDRAC by SNMP | |
| MSSQL by Zabbix agent 2 (or MSSQL by ODBC) | |
| Pure Storage FlashArray v1 by HTTP | |
| Dell Storage by HTTP (optional) | |
| GitLab by HTTP | |

**Storage Generic Device by SNMP:** clone from Network Generic Device by SNMP **without** items that collide with Dell iDRAC (`snmptrap.fallback` and `zabbix[host,snmp,available]`). Preferred method in the Zabbix UI: **Export** the Network Generic template as YAML → delete those two items (and keep discovery rules, prototypes, triggers, value maps) → **Import** under the new name `Storage Generic Device by SNMP`. Do not recreate the template by copying items one-by-one in the UI — that drops LLD and related objects. Import Dell iDRAC from the Zabbix template library if it is not already installed.

**How matching works**

- The **pattern** is a **case-insensitive regular expression**, matched with `search` (substring of the platform name — **not** a full-string match, and **not** a plain text substring). Examples in the table (`Ubuntu|Debian|…`, `Other.*Linux`) are regex. A literal platform string pasted as the pattern (for example `Windows Server 2019 (x64)`) may never match or may be an invalid regex — write a real expression (for example `Windows Server`).
- **Every matching rule contributes** its template and optional hostgroup. Priority only sets **evaluation order** (`order_by priority, name`). A template (or hostgroup) already resolved by an earlier rule or an explicit assignment is not added twice. A higher-priority rule does **not** suppress a lower-priority rule that points at a *different* template. To stop a catch-all from also applying, narrow its pattern or disable it — do not assume “lower number wins exclusively.” (Today Windows Server and Windows catch-all both point at the same template, so the collision is invisible.)

Leave “require tags”, “role pattern”, and “manufacturer” empty unless noted. Criteria are AND: every set field must match (missing role/manufacturer on the object fails closed).

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
| VMware ESXi | `ESXi\|VMware ESX\|vSphere` | VMware FQDN | OS/VMware | — | 100 | Yes |
| VMware Photon | `Photon` | Linux by Zabbix agent | OS/Linux | — | 50 | Yes |

**Extreme:** platform rules above attach EXOS / VOSS / IQ Engine — never Network Generic on Switch* (`icmpping` collision). Macro values, stages, LLD patches → [`zabbix/01-extreme-switching.md`](../zabbix/01-extreme-switching.md); labels → [`port-identity.md`](../zabbix/port-identity.md); nbxSync macro assignment clicks → §11.1.

### 6.2 SNMP OS rules (NetBox tag `snmp`)

Use together with configuration group **SNMP Monitoring (Linux)** (assigned on NetBox tag `snmp`) for the interface.

**Why a tag gate:** only selected hosts should switch from agent OS templates to SNMP OS templates. The tag is an explicit operator choice; the configuration group supplies the SNMP interface (Device or VM).

| Name | Pattern | Template | Hostgroup | Require tags | Priority | Enabled |
|---|---|---|---|---|---|---|
| SNMP Linux (tag) | *(same Linux pattern as above)* | Linux by SNMP | OS/Linux | snmp | 40 | Yes |
| SNMP Windows (tag) | `Windows` | Windows by SNMP | OS/Windows | snmp | 40 | Yes |
| Oracle (tag) | `.*` | Oracle by Zabbix agent 2 | — | oracle | 40 | Yes |

### 6.3 Manufacturer ∧ role rules

**Do not** assign Dell iDRAC on Manufacturer Dell — merge is additive and would attach iDRAC to Dell storage and other SNMP Dell hosts. Scope it here instead. Transport stays **Server Agent+OOB** (`oob_ip`); empty `oob_ip` skips the OOB SNMP interface only. OEM model templates stay on Device type (they add; they do not remove iDRAC).

| Name | Pattern | Role pattern | Manufacturer | Template | Hostgroup | Require tags | Priority | Enabled |
|---|---|---|---|---|---|---|---|---|
| Dell iDRAC (Server) | `.*` | `^Server$` | Dell | Dell iDRAC by SNMP | — | — | 80 | Yes |
| Pure Storage (HTTP) | `.*` | — | Pure Storage | Pure Storage FlashArray v1 by HTTP | — | — | 80 | Yes |
| Dell Storage (HTTP) | `.*` | `^Storage$` | Dell | Dell Storage by HTTP | — | — | 80 | Yes |
| Huawei Storage (SNMP) | `.*` | `^Storage$` | Huawei | Huawei Storage by SNMP | — | — | 80 | Yes |
| Synology NAS (SNMP) | `.*` | `^Storage$` | Synology | Synology NAS by SNMP | — | — | 80 | Yes |

---

## 7. Template assignments (Role / Manufacturer)

Path: **Zabbix → Templates → [template] → Assigned objects → Add**  
(or Device Role / Manufacturer → Zabbix tab)

**Why here:** application and OEM templates are business knowledge (“MSSQL role gets MSSQL by Agent 2”). They **merge** with OS / platform templates from §6 — different template IDs all accumulate; nothing is subtracted. Do **not** put Network Generic on Switch*/AP roles: those roles already get Extreme EXOS / VOSS / IQ Engine / FortiOS (etc.) from §6, and Network Generic + EXOS both define `icmpping` so Zabbix rejects the link. Use **Network Device** only as the no-platform fallback. Firewall keeps FortiGate on the role. Storage Generic stays on **Cohesity only** — generic Storage uses HTTP (Dell) when available, not network SNMP.

**Interface requirements (silent drop):** each nbxsync Template can declare required interface types (Agent, SNMP, ANY, …). At sync, a template is **linked only if the host already has those interface types**. If the requirement is not met, the template is skipped with no dramatic error — it simply does not appear on the Zabbix host. That makes broad Role assignment safer across transport classes. It does **not** prevent two SNMP templates from both linking and colliding on item keys — avoid overlapping assignments (Switch+Network Generic vs EXOS; Storage Generic vs iDRAC).

| Template | Assigned to | Notes |
|---|---|---|
| MSSQL by Zabbix agent 2 | Device Role MSSQL | Prefer Agent 2 + MSSQL plugin; fallback name `MSSQL by ODBC` |
| MSSQL by Zabbix agent 2 | Device Role MSSQL Query Server | |
| VMware FQDN | Device Role vCenter | `{$VMWARE.URL}` / `{$VMWARE.USER}` / `{$VMWARE.PASSWORD}` via §11.4 |
| Pure Storage FlashArray v1 by HTTP | Manufacturer TemplateRule (Pure Storage) | Pure arrays have role=Storage, not Pure Storage; manufacturer rule catches them; `{$PURESTORAGE.TOKEN}` via §11.4 |
| Dell Storage by HTTP | **Manufacturer TemplateRule (Dell ∧ role Storage)** — §6.3 | Not a role assignment; keeps Dell servers (role Server → iDRAC) unaffected |
| GitLab by HTTP | Device Role GitLab | |
| Linux by SNMP | Device Role Virtual Appliance | Baseline if platform does not match a rule |
| Network Generic Device by SNMP | Device Role Network Device | Fallback when platform does not match a §6 rule |
| Storage Generic Device by SNMP | Device Role **Cohesity only** | Removed from Storage role — manufacturer-specific templates (Dell HTTP, Huawei SNMP, Pure HTTP, Synology SNMP) now cover Storage via §6.3 |
| FortiGate by SNMP | Device Role Firewall | Baseline; FortiOS rule adds the same template when platform matches |
| **Tableau Bridge by Zabbix agent** | Device Role Tableau | Placeholder — LM parity, items built post-cutover |
| **CellMap by Zabbix agent** | Device Role CellMap | Placeholder — LM parity (WinProcessStats_cellmap) |
| **SAP by Zabbix agent** | Device Role SAP ME and SAP HANA | Placeholder — DNUS scripts integrated by Robert post-cutover |
| **Acronis by Zabbix agent** | Device Role Acronis Management | Placeholder — LM parity |
| **SCCM by Zabbix agent** | Device Role SCCM | Placeholder — LM parity |
| **Print Spool by Zabbix agent** | Device Role Print Server | Placeholder — LM parity (print spool monitoring for ME) |
| **Oracle by Zabbix agent 2** | **Tag-gated TemplateRule (tag `oracle`)** — §6.2 | Placeholder — LM parity (`ch-sta-p-disc04` confirmed; check for others); see §9.0a tagging guide |

Do **not** assign Network Generic to Switch Core / Dist / Access / Mgmt / Hybrid or Access Point. Dell iDRAC is **not** in this table — use §6.3.

**AS Java by Zabbix agent** is intentionally unassigned: only two hosts (`ch-sta-*-as01/02`) carry it and they share role `Server`, so a role assignment would over-apply. Link it per device.

### 7.1 Extreme capability templates (nbxSync assignments)

These **merge** with the platform template from §6.1. Assign on the **role**, not on the platform. **When** to enable each stage is defined in [`zabbix/01-extreme-switching.md`](../zabbix/01-extreme-switching.md) §7 — not repeated here.

| Template | Assigned to | When (see Extreme §7) |
|---|---|---|
| Extreme Port Speed Expect by SNMP | Switch Core / Dist / Access / Mgmt / Hybrid (or globally on template) | Stage 4 — after stock LLD is stable. Uses own macros `{$PORTID.LLD.*}`, not `{$NET.IF.*}` |
| Extreme Routing by SNMP | Switch Core, Switch Dist | Post-cutover — after `ospfNbrTable` canary. Always assigned by hand, never in bulk |

Do **not** put Speed Expect / Routing on the platform Template Rule — role is the capability axis.

---

## 8. Hostgroups

Path: **Zabbix → Hostgroups → Add**, then assignments on each hostgroup or from the Site Group / tag Zabbix tab.

Axes (Sites / Roles / OS / Priority): [`nbxsync-architecture.md`](nbxsync-architecture.md). Below are the Jinja values and assignment clicks only.

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

Assigned on each country Site Group so every device under that country inherits the Roles template; the role *name* still comes from the device.

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

There are **two different tag systems** that work together but must not be confused:

1. **NetBox tags** — applied to devices/VMs/roles in NetBox. These are the *trigger*: when sync runs, nbxsync reads them and decides what to do.
2. **Zabbix tags** — applied to Zabbix hosts during sync, derived from Jinja templates (§9.1, §9.2) or from the NetBox tags above. These end up on the Zabbix host for filtering in dashboards, actions, and problem views.

**§9.0–9.0a and §9.3 are about NetBox tags** (what you apply in NetBox to control monitoring behaviour).
**§9.1–9.2 are about Zabbix tags** (what nbxsync writes to Zabbix hosts automatically — you do not touch these).

### 9.0 NetBox tags (create under NetBox → Tags)

These NetBox tags control monitoring behaviour. Apply them in NetBox → Device/VM → Tags, or on a Device Role to affect all devices with that role.

| NetBox tag | What it does when a device/VM has it | Apply where |
|---|---|---|
| `do_not_monitor` | Host is **completely skipped** during sync. Existing Zabbix host is deleted. See §9.3 for details. | Per device/VM or per Device Role (Messpc, Sd Wan Socket, VDI) |
| `critical` | Adds the host to Zabbix hostgroup `Priority/Critical` (for 24/7 alert escalation). | Per device/VM |
| `snmp` | Switches transport from Agent to **SNMP Monitoring (Linux)** CG (MONITORING-LINUX SHA/AES) and links Linux/Windows by SNMP templates instead of agent templates. | Per device/VM — for Linux hosts that should be SNMP-polled instead of agent-polled |
| `oracle` | Links **Oracle by Zabbix agent 2** template (merges with OS template from platform rule). | Per device/VM — `ch-sta-p-disc04` confirmed; check for others |

**NetBox tags do not appear in Zabbix as tags.** They are read by nbxsync during sync and translated into Zabbix objects (interfaces, templates, hostgroups). Zabbix tags (§9.1–§9.2) are separate and auto-generated.

### 9.0a Which devices to tag — LogicMonitor mapping

Below maps the LM account export to the NetBox tags or roles this checklist uses. For SAP, no tag is needed — the role is set automatically by netbox-sync.

| LM signal | Known hosts | What to do in NetBox | Result |
|---|---|---|---|
| LM used `MONITORING-LINUX` SHA/AES (Linux servers group + resource overrides) | `ch-sta-p-disc04`, `ch-sta-p-lega01`, `ch-sta-p-dell04`, `CH-STA-P-ESD01`, `ch-sta-p-vmli01/02/03/09/13`, `hu-deb-p-dock01`, `nl-ens-d-serv01`, `CH-STA-P-M300` | Add NetBox tag `snmp` | SNMP Monitoring (Linux) CG + Linux by SNMP template |
| LM used `SAPUSER` (SAP Systems group) | `ch-sta-d-sh01`, `ch-sta-p-sh01`, `ch-sta-q-sh01`, `ch-sta-p-me05/06/07/08` | **Nothing** — netbox-sync maps `-SH\d+` to `SAP HANA` role and `-ME\d+` to `SAP ME` role automatically | SNMP Monitoring (SAP) CG + SAP by Zabbix agent template |
| LM used JDBC `C##logicmonitor` (Oracle) | `ch-sta-p-disc04` (confirmed); check with DB team for others | Add NetBox tag `oracle` | Oracle by Zabbix agent 2 template |
| LM 24×7 escalation list | Per operational priority | Add NetBox tag `critical` | Priority/Critical hostgroup membership |
| LM monitoring disabled / excluded by policy | VDI (22 VMs), Messpc (1421), Sd Wan Socket (21) | Automated by Device Role in §9.3; per-device by tag `do_not_monitor` | Host excluded from Zabbix entirely |

**How to tag:** In NetBox, open the Device or VM → Tags → Add tag. Re-sync the host. The tag takes effect on the next sync cycle.

### 9.1 Zabbix host tags — Environment (auto-generated, Jinja on Site Groups)

**You do not create these manually.** nbxsync creates the Zabbix tag definition and assigns it on each country Site Group. During sync, the Jinja template renders a value per host (e.g. `Production`, `Development`) and writes it as a Zabbix host tag.

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

**Failure mode:** names that do not match the `-p-` / `-d-` / … conventions resolve to **`Unknown` with no alert**. That is silent. **Extreme switches** (`CH-STA-…-CORE01`, `…-MGMT01`, `…-ACCE01`, …) normally have no `-p-` token — `environment=Unknown` on them is expected, not a sync bug. If alert routing needs a value later, extend the Jinja (e.g. treat `Switch*` roles as Production) rather than renaming the fleet.

### 9.2 Zabbix host tags — Cluster (auto-generated, Jinja on Clusters)

| Tag | Value | Assign to |
|---|---|---|
| cluster | `{{ object.cluster.name }}` | each Cluster |

### 9.3 NetBox exclusion tag (do_not_monitor)

| Tag | Value | Assign to Device Role |
|---|---|---|
| do_not_monitor | *(empty)* | Messpc, Sd Wan Socket, VDI |

Plugin setting `exclude_tag` must be set to `do_not_monitor` (section 12).

**VDI** and **Sd Wan Socket** are excluded here but *are* monitored in LogicMonitor (Horizon View / Cato API). Both are open items — see §17.

**What happens when a device/VM has the `do_not_monitor` tag:**

| Stage | Effect |
|---|---|
| **Sync** | The host is **completely skipped** — no Zabbix host is created, no interfaces, no templates, no macros. If a Zabbix host already exists from a previous sync (before the tag was added), it is **deleted** from Zabbix. |
| **Host binding** | Any existing `ZabbixHostBinding` is removed. The device will not appear in Zabbix at all. |
| **Day-2 removal** | Tag a device `do_not_monitor` and re-sync: the Zabbix host disappears within one sync cycle. No manual deletion needed. The device stays in NetBox — only the Zabbix monitoring is removed. |
| **Untag** | Remove the `do_not_monitor` tag and re-sync: the host is recreated in Zabbix with full template/interface/hostgroup configuration. |

This works on both **Devices** and **Virtual Machines**. The tag can be applied at the individual object level or at the **Device Role** level (e.g., all Messpc and VDI hosts excluded by default — see the role assignment above).

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

## 11. Macros

Path: **Zabbix → Macros → Add** (definition on Zabbix Server, then Macro Assignment on the role / or assign from the Role Zabbix tab)

**Why on the role:** class-wide thresholds and (for switches) Extreme port filters. Application secrets (VMware, Pure Storage, MSSQL) are role-level secret macros — see §11.4. Extreme *values* → `zabbix/01-extreme-switching.md`.

### 11.1 Extreme switch macros (nbxSync rows; values in Extreme docs)

**Path:** Zabbix → Macros → Add, then Macro Assignment on each Switch* Device Role (or Role → Zabbix tab).

Stock Extreme LLD evaluates **both** IFALIAS macros — set both on every Switch* role, plus `{$NET.IF.IFTYPE.MATCHES}`.

| What to create in nbxSync | Where values and meaning live |
|---|---|
| Role macros `{$NET.IF.IFALIAS.MATCHES}`, `{$NET.IF.IFALIAS.NOT_MATCHES}`, `{$NET.IF.IFTYPE.MATCHES}` on Switch Core / Dist / Mgmt / Access / Hybrid | [`zabbix/01-extreme-switching.md`](../zabbix/01-extreme-switching.md) §5 Role model and §8 Macro assignments |
| Fleet / template destination macros (`{$TEMP_WARN}`, optics, MLT, Speed Expect `{$PORTID.LLD.*}`, …) | Same doc §8 (including temporary cutover-silence overlay) |
| On-box port label grammar | [`zabbix/port-identity.md`](../zabbix/port-identity.md) |
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


### 11.4 Application secrets (role-level)

Create these as **role-level ZabbixMacros** with type `SECRET`. During sync, `hostsync` resolves the inheritance chain and pushes them as secret host macros to each Zabbix host.

| Macro | Role | Type | Notes |
|---|---|---|---|
| `{$VMWARE.USER}` | vCenter | Secret | Same user on all vCenters |
| `{$VMWARE.PASSWORD}` | vCenter | Secret | Same password on all vCenters |
| `{$PURESTORAGE.TOKEN}` | Pure Storage | Secret | One API token for all arrays (generate on each array) |
| `{$MSSQL.USER}` | MSSQL | Secret | |
| `{$MSSQL.PASSWORD}` | MSSQL | Secret | |

If a macro is not set, the template will show "no data" until the credential is provided.

SNMPv3 auth/priv passphrases are **not** global or role macros: they live on the SNMP Host Interface (§5) and are pushed as secret **host** macros when SNMP push community is True.

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
| Access Point | SNMP Monitoring | Platform `IQ ENGINE` → **Extreme IQ Engine by SNMP** | SNMP `MONITORING` MD5/DES | Sites/CH/…, Roles/Access Point, OS/Network |
| Firewall | SNMP Monitoring | Platform/role template (FortiGate, …) | SNMP `MONITORING` MD5/DES | Sites/CH/…, Roles/…, OS/Network |
| Space Server | Agent Monitoring (SPACE) | OS by agent | Agent **:10060** | Sites/CH/…, Roles/Space Server, OS/… |
| Storage (Dell) | Agent Monitoring | Dell Storage by HTTP (when imported) | Agent / HTTP | Sites/CH/…, Roles/Storage |
| Pure Storage | Agent Monitoring | Pure Storage by HTTP | Agent / HTTP | Sites/CH/…, Roles/Pure Storage |
| Cohesity physical (oob only) | OOB SNMP Only | Storage Generic | SNMP `MONITORING` on oob | Sites/CH/…, Roles/Cohesity |
| Cohesity VM with primary IP | SNMP Monitoring (direct) | Storage Generic | SNMP `MONITORING` on primary | … |
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

1. Does it need a **transport exception**? If it is agent-class → nothing (Site Group Agent default). If network SNMP → **SNMP Monitoring**. If SPACE → **Agent Monitoring (SPACE)**. If dual-plane BMC server → **Server Agent+OOB**. If OOB-only → **OOB SNMP Only**. If Linux SNMP opt-in → tag `snmp` (no new role CG).
2. Does it need an **application template**? Add a Template assignment on the role (§7).
3. New **Switch*** role? Copy IFALIAS / IFTYPE macros from the closest peer (`zabbix/01-extreme-switching.md` §5 / §8; create nbxSync assignments per §11.1). Platform Template Rules already cover EXOS/VOSS.
4. Hostgroup `Roles/<name>` appears automatically from the Sites/Roles Jinja — do not create a per-role hostgroup assignment.

### 15.1b New Extreme switch (day-2)

On-box labels and stages: [`zabbix/01-extreme-switching.md`](../zabbix/01-extreme-switching.md), [`port-identity.md`](../zabbix/port-identity.md).  
After NetBox role / platform / site / primary IP are set, sync should match the Extreme switch rows in **§13**. IFALIAS assignments: §11.1. If VOSS still gets Network Generic, fix §6.1 (YAML missing or onboarding re-run left the placeholder — see [scripts/README.md](../scripts/README.md)).

### 15.1c Extreme staged enablement

Stages and Hybrid flip: Extreme doc §7. nbxSync clicks at those stages: §7.1 and §11.1.

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
| Extreme port labels / Hybrid flip / stage gates | Per [`zabbix/01-extreme-switching.md`](../zabbix/01-extreme-switching.md) and [`port-identity.md`](../zabbix/port-identity.md) |
| Spot-check `environment=Unknown` | After naming-convention drift |
| Update “Last verified” stamp at top of this doc | After a production re-validation |

---

## 16. Verification

After the initial build, and after major changes, confirm coverage against §13.

**What “good” looks like (spot-check in GUI / Zabbix):**

| Check | Expect |
|---|---|
| Sample Linux server | Server Agent+OOB; agent + oob SNMP; OS/Linux; Roles/Server; leaf under `Sites/CH/…` |
| Sample EXOS switch | SNMP Monitoring; **Extreme EXOS by SNMP**; role IFALIAS macros (§11.1 / Extreme doc); no Network Generic; single `icmpping`; OS/Network |
| Sample VOSS switch | SNMP Monitoring; **Extreme VOSS by SNMP** (imported YAML); same role IFALIAS as EXOS peer role; no Network Generic; single `icmpping` |
| Sample Switch Hybrid (pre–stage 5) | Same platform template as peer EXOS/VOSS; IFALIAS macros still Access-like (`USW\|…` opt-in), not Core `.*` |
| Sample Windows VM | Agent; Windows by agent; OS/Windows; leaf under `Sites/CH/…` |
| Country dashboard / ACL | Filter on parent `Sites/CH` for location views; hosts are leaf members only. Org access is global — no regional permission split |
| Host with `critical` | Also in Priority/Critical |
| Role not listed in §5b SNMP/OOB | Still has Agent via Site Group |
| VM without site | No useful profile until site/scope is set |

**Unprofiled / wrong template symptoms:** host missing in Zabbix, empty template list, or only partial stack vs §13. Use the §15.4 ladder.

**Optional onboarding census:** see [`scripts/README.md`](../scripts/README.md) (`--verify`). Map gaps to §15.4.

---

## 17. Scope boundary and open items

Everything in §§1–16 is driven from NetBox through nbxsync. Some things LogicMonitor watches today are **not** — either because there is no NetBox object to hang them on, or because we have not decided yet. Parity source: `zabbix/logicmonitor-assessment.md`.

### 17.1 Monitored in Zabbix, but never modelled in NetBox

nbxsync will never create these. Build them directly in Zabbix and do not expect them in §13.

| Area | Why not in NetBox | Where it lives instead |
|---|---|---|
| **Website checks** (JIRA, Confluence, Sensinet + 2.0, Space Server CH/HU test+prod, Libellus, Nubo Sphere, Nubo Sensor API — 11 LM checks) | A URL is not a device or VM; there is no NetBox object to inherit from | Zabbix **web scenarios**, configured by hand in Zabbix |
| **Cato SD-WAN** (LM API account 964) | Sockets are excluded from monitoring in §9.3; the data is an account-level API, not a per-device poll | Cato portal today; a Zabbix **HTTP agent** template if we decide to pull it in |

Note that **Space Server** therefore has split coverage: the host itself is a normal Zabbix host on Agent `:10060` (§5.7), but the four LM web checks against it are not represented anywhere yet.

### 17.2 Open questions — decide before declaring parity

| # | Item | Question to answer | Blocks |
|---|---|---|---|
| 1 | **`hu-deb-san01`** (Huawei storage, HU) | Device exists in NetBox as `HU-DEB-SAN01` (role Storage, manufacturer Huawei, model Dorado 3000 V6, site HU-DEB-NAG-A, IP 10.40.101.61). Per-device `ZabbixHostInterface` created with `LogicMonitor` SHA1/AES128 credentials. Synced in Zabbix with `Huawei Storage by SNMP` template (manufacturer TemplateRule). | Resolved — device in NetBox, interface created, synced |
| 2 | **Horizon View / VDI** | LM monitors VDI globally with `CH-UPA-Monitor`. What does it actually collect, and at what level — Connection Broker / Session Host, or individual desktops? Zabbix has no Horizon template. Decide: build one, cover it from the broker, or accept the loss | §9.3 excludes role VDI outright; §11.3 still sets `{$MEM.UTIL.CRIT}` on VDI — one of the two is dead |
| 3 | **CH-STA-P-ENSA01 traps** | LM has an event source `SNMP Receive - Netsight` on this host. Capture what traps it is actually sending before deciding whether to build a Zabbix SNMP trapper for it. Same host is also the only **SNMPv2c** device in LM — the §5 CG model is v3-only | No trap handling anywhere in this checklist; no v2c profile in §5 |
| 4 | **Cato** | What do we want from Cato in Zabbix — socket up/down, tunnel health, nothing? See 17.1: whatever we choose is not NetBox-driven | §9.3 `do_not_monitor` on Sd Wan Socket is currently an unexplained exclusion |
| 5 | **Oracle JDBC** | LM uses account `C##logicmonitor`; resource override on `ch-sta-p-disc04`. Host identified: `ch-sta-p-disc04` (RHEL 7.9, role Server). Tag it `oracle` in NetBox (§9.0a) to link the Oracle by Zabbix agent 2 template. Check with DB team for other Oracle hosts. | Resolved — tag-gated TemplateRule in §6.2 |

### 17.3 Also not covered here

| Area | Owner |
|---|---|
| Media types, actions, escalation (cutover blocker #6) | Zabbix side — §14 |
| Monitor-the-monitoring: unsupported items, proxy last-seen (cutover blocker #7) | Zabbix side — not yet designed |
| SAP custom datasources / DNUS scripts | Robert, post-cutover |
| Configuration backup | cfgit, not Zabbix |

---

## Appendix A — Optional onboarding scripts

First-build helpers only — not day-2. Commands, env vars, flags, and run order: [`scripts/README.md`](../scripts/README.md).  
This checklist remains authoritative for the objects those scripts create.

