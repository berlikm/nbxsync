# nbxSync Configuration Checklist

Step-by-step configuration in NetBox. Execute in order for the initial build. Day-2 procedures are in §15; verification in §16.

This checklist is for **GUI operators**. Fill in production URLs, tokens, and secrets when you apply it in the target environment.

**Last verified:** 2026-08-06 against NetBox 4.x / Zabbix 7.0.x (lab) — multi-credential SNMPv3 + Extreme EXOS/VOSS; §11.2 destination macros are the default. Update this stamp when you re-validate against production.

**Canonical copy:** keep one authoritative home (this repo file or Confluence). If both exist, the other must be a pointer only — do not maintain two full copies by hand.

**Extreme switching deep dive:** port grammar and LLD design live in `zabbix/port-identity.md` and `zabbix/01-extreme-switching.md`. This checklist only records the NetBox/nbxsync rows operators must create.

---

## Design (why it is built this way)

Monitoring membership and transport should follow **facts already in NetBox** (site, role, platform, manufacturer, a few tags). Operators encode business knowledge once; new devices onboard without new hand-maintained rows.

| Fact in NetBox | Encoded as | Effect in Zabbix |
|---|---|---|
| Country / site | Hostgroup template on each country Site Group | Nested full path `Sites/<country>/…/<site>` (Site Group ancestry) |
| Function (role) | Hostgroup template on each country Site Group | `Roles/<role name>` |
| Platform / OS | Template Rule (regex on platform name) | OS template + `OS/Linux`, `OS/Windows`, `OS/Network`, or `OS/VMware` |
| Criticality | NetBox tag `critical` | Hostgroup `Priority/Critical` |
| Default transport | Configuration group **Agent Monitoring** on each country Site Group | Zabbix agent :10050 on the primary IP |
| Network SNMP | **SNMP Monitoring** on Switch*/AP/Firewall/Network Device/Virtual Appliance | SNMPv3 `MONITORING` MD5/DES |
| Extreme platform | Template Rule: `EXOS` → Extreme EXOS, `VOSS` → Extreme VOSS | Platform template + `OS/Network` (never Network Generic on Switch*) |
| Extreme port scope | Role macros `{$NET.IF.IFALIAS.*}` / `{$NET.IF.IFTYPE.MATCHES}` on Switch* | Core/Dist/Mgmt = all ports except `X`; Access/Hybrid = labelled opt-in |
| Extreme thresholds | Global macros §11.2 (**destination** defaults) | Temp 90/100, optic DOM+value, MLT on; util% off until stage 6 |
| Linux SNMP opt-in | NetBox tag `snmp` → CG **SNMP Monitoring (Linux)** + Template Rules | SNMPv3 `MONITORING-LINUX` SHA/AES + Linux/Windows by SNMP |
| SAP SNMP opt-in | NetBox tag `snmp-sap` → CG **SNMP Monitoring (SAP)** | SNMPv3 `SAPUSER` (confirm auth/priv with Robert) |
| Server with Dell BMC | **Server Agent+OOB** on role Server | Agent :10050 + SNMPv3 `MONITORING-DELL` SHA/AES on `oob_ip` |
| Cohesity physical | **OOB SNMP Only** on role Cohesity | SNMPv3 `MONITORING` MD5/DES on `oob_ip` only |
| Space Server | **Agent Monitoring (SPACE)** on role Space Server | Agent **:10060** (camLine uses 10050) |
| Pure / Dell storage HTTP | Role template (HTTP), SiteGroup Agent transport | No SNMP CG |
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

### Why transport uses configuration groups

Exactly **one** configuration group decides how the host is reached (agent vs SNMP vs OOB). Hostgroups and templates can stack freely; transport cannot.

**SNMPv3 credentials are part of the interface shape** — different LogicMonitor accounts (`MONITORING`, `MONITORING-LINUX`, `MONITORING-DELL`, `SAPUSER`) need **different CGs**. Do not share one SNMP CG across network and Linux/SAP/iDRAC.

**Tag `snmp` / `snmp-sap` are intentional transport selectors.** Inheritance resolves tag-targeted CG assignments *before* role/site, so tagging a host is zero-touch opt-in to Linux or SAP SNMP (and beats the SiteGroup Agent default). Other tags (`critical`, `do_not_monitor`) stay overlays only — never put a Host Interface directly on a tag.

Role-level network SNMP / Server Agent+OOB / SPACE **override** the country Site Group’s Agent default. Assign Agent Monitoring on **country** Site Groups only — not on campus mid-levels.

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
- Device Roles named exactly as listed in this checklist (include **Switch Hybrid** for core∩access Extreme boxes)
- Platforms whose names match the Template Rule patterns (Extreme platforms must contain `EXOS` or `VOSS`)
- For BMC monitoring: each server’s **out-of-band IP** (`oob_ip`) filled in; without it the OOB SNMP interface is skipped
- Required Zabbix templates already present in Zabbix (import any that are missing before assigning them here)
- **Extreme VOSS by SNMP** YAML imported from `zabbix/templates/extreme_voss_snmp/` **before** enabling the Extreme VOSS Template Rule (§6.1) — stock Zabbix has EXOS, not VOSS

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

Each group is one **transport + credential** profile. SNMPv3 user/auth/priv differ by LogicMonitor account — keep them on separate groups.

| Name | Credential / port | Purpose |
|---|---|---|
| SNMP Monitoring | `MONITORING` MD5/DES | Extreme / Forti / AP / network roles |
| SNMP Monitoring (Linux) | `MONITORING-LINUX` SHA/AES | Opt-in Linux/Windows SNMP (tag `snmp`) |
| SNMP Monitoring (SAP) | `SAPUSER` (confirm auth/priv) | Opt-in SAP SNMP (tag `snmp-sap`) |
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

| Profile | CG | Security name | Auth | Priv | Script env (auth / priv) |
|---|---|---|---|---|---|
| Network | SNMP Monitoring, OOB SNMP Only | MONITORING | MD5 | DES | `NBX_SNMP_AUTHPASS_MON` / `NBX_SNMP_PRIVPASS_MON` (aliases: `NBX_SNMP_AUTHPASS` / `NBX_SNMP_PRIVPASS`) |
| Linux | SNMP Monitoring (Linux) | MONITORING-LINUX | SHA1* | AES128 | `NBX_SNMP_AUTHPASS_LINUX` / `NBX_SNMP_PRIVPASS_LINUX` |
| Dell iDRAC | Server Agent+OOB (SNMP side) | MONITORING-DELL | SHA1* | AES128 | `NBX_SNMP_AUTHPASS_DELL` / `NBX_SNMP_PRIVPASS_DELL` |
| SAP | SNMP Monitoring (SAP) | SAPUSER | *(confirm)* | *(confirm)* | `NBX_SNMP_AUTHPASS_SAP` / `NBX_SNMP_PRIVPASS_SAP` |

\*LM export says “SHA”; Zabbix offers SHA1 and SHA256 — default in the configure script is **SHA1** until confirmed.

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
| BMC | SNMP | 161, Use OOB = **Yes** | Dell profile (`MONITORING-DELL`) |

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
| `hu-deb-san01` (`LogicMonitor` SHA/AES) | Per-device `ZabbixHostInterface` on that Device (do not change fleet CGs) |

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

**Do not** assign Storage here. Switch Hybrid uses the same SNMP Monitoring CG as other Switch* roles; only its IFALIAS macros differ (§11.1).

### Server / Cohesity / SPACE roles

| Configuration group | Assigned to |
|---|---|
| Server Agent+OOB | Server |
| OOB SNMP Only | Cohesity |
| Agent Monitoring (SPACE) | Space Server |

### Zero-touch tag opt-ins

| Configuration group | Assigned to | Operator action |
|---|---|---|
| SNMP Monitoring (Linux) | NetBox tag **`snmp`** | Tag the Device/VM — no per-host CG row |
| SNMP Monitoring (SAP) | NetBox tag **`snmp-sap`** | Tag SAP hosts that need SNMP (after Robert confirms) |

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
| Network Generic Device by SNMP | Network Device / IQ Engine / FortiAnalyzer only — **not** Switch* |
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

**Extreme EXOS / VOSS (orthogonal to role):**

- Platform picks the **platform template** (`Extreme EXOS by SNMP` or `Extreme VOSS by SNMP`). Role picks **port-scoping macros** (§11.1) and, later, capability templates (Speed Expect / Routing — §7.1).
- A VOSS core and an EXOS core share the same Core IFALIAS macros — never build a Core-EXOS / Core-VOSS matrix.
- **VOSS must not use Network Generic** — both define `icmpping` and Zabbix rejects the link. Import the custom VOSS YAML before enabling the rule (zerotouch / network helper will import + retarget a leftover Network Generic VOSS rule).
- **Switch Hybrid** starts Access-like (opt-in labels); flip to Core macros at stage 5 (§11.1 / §15.1c).
- On-box labels: EXOS → `display-string` (max **20** chars; leave `description-string` empty). VOSS → port `name` → `ifAlias`. Grammar: `zabbix/port-identity.md`.
- **Stock EXOS — EtherLike duplex LLD:** stock only keeps oper-up ports (bypasses Access IFALIAS). `configure_nbxsync_network.py` (`--apply` / `--simulate`) patches `net.if.duplex.discovery` on **Extreme EXOS by SNMP** (and verifies VOSS) to add the same `{#IFALIAS}` MATCHES / NOT_MATCHES macros as `net.if.discovery`. After apply, execute duplex discovery (or wait) so lost resources drop (`lifetime` / keep-lost 0 during rollout).
- **Stock EXOS — `net.if.discovery` rollout:** stock delay is **1h** (VOSS YAML is 15m). Script patches EXOS IF LLD to **15m / lifetime 0**. Then **Execute now** on DIST/ACCE hosts (or wait). Macro names already match stock (`{$NET.IF.IFALIAS.*}` etc.) — Dist/Access scope is role values, not different macro names.
- **EXOS LLD empty checklist:** (1) **Access** with no `USW|US|UP|MON|…` labels → **0 `net.if.*` is expected** (opt-in). (2) **Dist/Core** should use `MATCHES=.*` / `NOT_MATCHES=^X(-|$)` — if still 0, open host → Discovery rules → `net.if.discovery` **error** (often SNMP timeout on the heavy IF-MIB walk) and check `{$NET.IF.IFTYPE.MATCHES}=^(6|161)$` is present. Fan/PSU LLD can succeed while IF LLD fails.
- **Stock EXOS — chassis TEMP_* macros:** stock template macros `{$TEMP_WARN}=55` / `{$TEMP_CRIT}=65` **override** globals. `configure_nbxsync_network.py` merges destination values (`90` / `100` / `-273`, or cutover-silence `999`) onto **Extreme EXOS by SNMP** and **Extreme VOSS by SNMP** via `template.update` (full macro merge — never send only TEMP_*). IQ Engine keeps AP-specific 70/85.

### 6.2 SNMP OS rules (NetBox tag `snmp`)

Use together with configuration group **SNMP Monitoring (Linux)** (assigned on NetBox tag `snmp`) for the interface.

**Why a tag gate:** only selected hosts should switch from agent OS templates to SNMP OS templates. The tag is an explicit operator choice; the configuration group supplies the SNMP interface (Device or VM).

| Name | Pattern | Template | Hostgroup | Require tags | Priority | Enabled |
|---|---|---|---|---|---|---|
| SNMP Linux (tag) | *(same Linux pattern as above)* | Linux by SNMP | OS/Linux | snmp | 40 | Yes |
| SNMP Windows (tag) | `Windows` | Windows by SNMP | OS/Windows | snmp | 40 | Yes |

### 6.3 Dell iDRAC (Manufacturer ∧ role)

**Do not** assign Dell iDRAC on Manufacturer Dell — merge is additive and would attach iDRAC to Dell storage and other SNMP Dell hosts. Scope it here instead. Transport stays **Server Agent+OOB** (`oob_ip`); empty `oob_ip` skips the OOB SNMP interface only. OEM model templates stay on Device type (they add; they do not remove iDRAC).

| Name | Pattern | Role pattern | Manufacturer | Template | Hostgroup | Require tags | Priority | Enabled |
|---|---|---|---|---|---|---|---|---|
| Dell iDRAC (Server) | `.*` | `^Server$` | Dell | Dell iDRAC by SNMP | — | — | 80 | Yes |

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
| VMware FQDN | Device Role vCenter | Per-vCenter `{$VMWARE.USER}` / `{$VMWARE.PASSWORD}` as needed |
| Pure Storage FlashArray v1 by HTTP | Device Role Pure Storage | Pure stays on Agent transport; per-array token macros |
| Dell Storage by HTTP | Device Role Storage | When template imported; replaces Storage Generic on Storage |
| GitLab by HTTP | Device Role GitLab | |
| Linux by SNMP | Device Role Virtual Appliance | Baseline if platform does not match a rule |
| Network Generic Device by SNMP | Device Role Network Device | Fallback when platform does not match a §6 rule |
| Storage Generic Device by SNMP | Device Role Cohesity | Keep until a Cohesity-specific template exists |
| FortiGate by SNMP | Device Role Firewall | Baseline; FortiOS rule adds the same template when platform matches |

Do **not** assign Network Generic to Switch Core / Dist / Access / Mgmt / Hybrid or Access Point. Dell iDRAC is **not** in this table — use §6.3.

### 7.1 Extreme capability templates (stage / post-cutover)

These **merge** with the platform template from §6.1. Assign on the **role**, not on the platform.

| Template | Assigned to | When |
|---|---|---|
| Extreme Port Speed Expect by SNMP | Switch Core / Dist / Access / Mgmt / Hybrid (or globally on template) | Stage 4 — after stock LLD is stable. Uses own macros `{$PORTID.LLD.*}`, not `{$NET.IF.*}` |
| Extreme Routing by SNMP | Switch Core, Switch Dist | Post-cutover — after `ospfNbrTable` canary |

Do **not** put Speed Expect / Routing on the platform Template Rule — role is the capability axis.

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
| `snmp` | Zero-touch Linux SNMP: selects **SNMP Monitoring (Linux)** CG + Linux/Windows by SNMP Template Rules |
| `snmp-sap` | Zero-touch SAP SNMP: selects **SNMP Monitoring (SAP)** CG (after Robert confirms) |

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

**Failure mode:** names that do not match the `-p-` / `-d-` / … conventions resolve to **`Unknown` with no alert**. That is silent. **Extreme switches** (`CH-STA-…-CORE01`, `…-MGMT01`, `…-ACCE01`, …) normally have no `-p-` token — `environment=Unknown` on them is expected, not a sync bug. If alert routing needs a value later, extend the Jinja (e.g. treat `Switch*` roles as Production) rather than renaming the fleet.

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

## 11. Macros

Path: **Zabbix → Macros → Add** (definition on Zabbix Server, then Macro Assignment on the role / or assign from the Role Zabbix tab)

**Why on the role:** thresholds and Extreme port filters are class-wide policy. Secrets stay as Zabbix global macros (or Host Interface push for SNMPv3) so they are not copied into NetBox.

### 11.1 Extreme switch port-scoping (required for EXOS/VOSS)

Stock Extreme LLD evaluates **both** IFALIAS macros — set both on every Switch* role. `{$NET.IF.IFTYPE.MATCHES}` excludes EXOS VLAN pseudo-interfaces. Design detail: `zabbix/01-extreme-switching.md` §A.5 / §A.8.

| Device Role | `{$NET.IF.IFALIAS.MATCHES}` | `{$NET.IF.IFALIAS.NOT_MATCHES}` | `{$NET.IF.IFTYPE.MATCHES}` | Meaning |
|---|---|---|---|---|
| Switch Core | `.*` | `^X(-\|$)` | `^(6\|161)$` | All ethernet/LAG ports except `X` exclude |
| Switch Dist | `.*` | `^X(-\|$)` | `^(6\|161)$` | **Same as Core — all ethernet/LAG except `X`** (not Access opt-in). Role aliases: Distribution / Dist |
| Switch Mgmt | `.*` | `^X(-\|$)` | `^(6\|161)$` | Same as Core |
| Switch Access | `^(USW\|US\|UP\|MON\|UW\|TMON)(-\|$)` | `CHANGE_IF_NEEDED` | `^(6\|161)$` | Opt-in labelled ports only |
| Switch Hybrid | `^(USW\|US\|UP\|MON\|UW\|TMON)(-\|$)` | `CHANGE_IF_NEEDED` | `^(6\|161)$` | **Start** Access-like (stage 0–4); flip to Core values at stage 5 |

**Label semantics (ops):** `X` / `X-<note>` = exclude from monitoring. `N` / `N-<text>` = note only — **not** an exclude (still monitored on Core). Unlabelled admin-up ports: monitored on Core/Dist/Mgmt; not discovered on Access/Hybrid until labelled. Prefer **admin-down** for unused ports; reserve `X` for up links that must stay quiet (stack/ISC/MLAG/SPAN).

**Hybrid stage 5:** after that site’s `X`-fill and admin-down hygiene are clean, copy Core IFALIAS values onto Switch Hybrid (same three macros). Do not invent a Hybrid-EXOS / Hybrid-VOSS matrix — platform still picks the template.

### 11.2 Extreme / fleet globals — destination standard

These are the **production end-state** values. `configure_nbxsync_network.py` applies them by default (`--apply` / `--simulate`). Do **not** leave the estate on temporary silence macros.

Speed Expect uses its own filter namespace (`{$PORTID.LLD.*}`) — do **not** reuse `{$NET.IF.*}`.

| Macro | Destination | Notes |
|---|---|---|
| `{$IF.UTIL.MAX}` | `101` | Stock util% off until stage 6; then raise via **context** macros (e.g. `{$IF.UTIL.MAX:"USW"}`) |
| `{$TEMP_WARN}` | **90** | EXOS G2+ / VOSS chassis — **not** stock 55 |
| `{$TEMP_CRIT}` | **100** | **Not** stock 65 (fires while Extreme still says Normal) |
| `{$TEMP_CRIT_LOW}` | `-273` | Silence 0 °C stack/VM false positive |
| `{$OPTIC.TEMP.CRIT}` | **70** | Optic °C value trigger; prefer DOM status |
| `{$OPTIC.TEMP.MAX}` | `150` | Drops garbage DOM readings |
| `{$OPTIC.RX.DBM.MIN}` | `-100` | RX dBm value trigger **removed** (flooded on dark/unused DDM); DOM status only |
| `{$OPTIC.RX.DBM.FLOOR}` | `-39` | Legacy; unused for alerts |
| `{$OPTIC.DOM.ALARM_HIGH}` / `LOW` | `3` / `5` | Vendor DOM highAlarm / lowAlarm — primary optic alerts |
| `{$MLT.CONTROL}` | **1** | Agg-down on *transition* (`.diff()`); unused MLTs that stay down stay quiet |
| `{$VIST.CONTROL}` | `0` global | Set **host** macro `1` on VOSS fabric pairs that run V-IST |
| `{$IST.CONTROL}` | `0` | Classic IST unused on Fabric Engine |
| `{$SNMP.TIMEOUT}` | `5m` | |
| `{$PORTID.LLD.IFALIAS.MATCHES}` | `^(USW\|US\|UP\|MON)(-\|$)` | Speed Expect thin template only |
| `{$PORTID.LLD.IFTYPE.MATCHES}` | `^6$` | Speed Expect thin template only |

**Also destination (not only macros):**

| Area | End-state |
|---|---|
| Platform template | EXOS → Extreme EXOS; VOSS → Extreme VOSS — **never** Network Generic on Switch* |
| Port scope | §11.1 role macros; EtherLike duplex LLD uses same IFALIAS filters as traffic LLD |
| Hybrid | Access-like until stage 5, then Core IFALIAS values per site |
| Speed Expect | Stage 4 role link |
| Routing / OSPF | Post-canary on Core/Dist |
| SNMP credentials | `MONITORING` MD5/DES on network CG (zerotouch) |
| Optic power | Template JS → dBm; LLD `SupportsDDM=true`; prefer DOM status |

**EXOS temperature:** `extremeCurrentTemperature` is an **internal** sensor, not closet ambient. Extreme GTAC [000088439](https://extreme-networks.my.site.com/ExtrArticleDetail?an=000088439): Switch Engine / Summit G2 / Universal (e.g. 5720) report **~70–85 °C as Status=Normal** (Normal often **10–100**, Max **110**). Prefer vendor `extremeOverTemperatureAlarm` for hard critical. Ambient rack rating (~0–50 °C) is a different number — do not use it for this OID.

**Macro precedence:** stock EXOS template macros (`55`/`65`) beat globals. Globals alone are not enough — `configure_nbxsync_network.py` must also patch template `{$TEMP_WARN}`/`{$TEMP_CRIT}`/`{$TEMP_CRIT_LOW}` (see EtherLike / TEMP_* bullets above).

#### Temporary cutover silence (optional overlay only)

During LogicMonitor migration noise, operators may pass `--cutover-silence` to the network script. That overlays **only**:

| Macro | Silence value |
|---|---|
| `{$TEMP_WARN}` / `{$TEMP_CRIT}` | `999` |
| `{$OPTIC.TEMP.CRIT}` | `999` |
| `{$OPTIC.RX.DBM.MIN}` | `-100` |
| `{$MLT.CONTROL}` | `0` |

Remove the overlay and re-apply **destination** as soon as first-light noise is understood — silence is not the target architecture.

### 11.3 Application / threshold macros (role)

| Macro | Value | Device Role |
|---|---|---|
| `{$CPU.UTIL.CRIT}` | 90 | MSSQL |
| `{$CPU.UTIL.CRIT}` | 80 | Server |
| `{$MEM.UTIL.CRIT}` | 85 | VDI |
| `{$MSSQL.DSN}` | nbxsync | MSSQL |
| `{$VMWARE.URL}` | `https://{{ object.name }}/sdk` | vCenter |

Define application secrets once as **global** macros in Zabbix:

- `{$MSSQL.USER}`, `{$MSSQL.PASSWORD}`
- `{$VMWARE.USER}`, `{$VMWARE.PASSWORD}`
- `{$PURESTORAGE.TOKEN}`

SNMPv3 auth/priv passphrases are **not** global macros: they live on the SNMP Host Interface (§5) and are pushed as secret **host** macros when SNMP push community is True.

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
| Linux server (role Server) | Server Agent+OOB | Linux by agent (+ Dell iDRAC if Dell and oob IP set) | Agent :10050 + SNMP `MONITORING-DELL` on oob | Sites/CH/…, Roles/Server, OS/Linux |
| Linux or Windows VM | Agent Monitoring (from Site Group) | OS by agent (Template Rule) | Agent :10050 | Sites/CH/…, Roles/…, OS/… |
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
3. New **Switch*** role? Copy IFALIAS / IFTYPE macros from the closest peer in §11.1 (Core-like vs Access-like). Platform Template Rules already cover EXOS/VOSS.
4. Hostgroup `Roles/<name>` appears automatically from the Sites/Roles Jinja — do not create a per-role hostgroup assignment.

### 15.1b New Extreme switch (day-2)

1. NetBox: correct **role** (Core/Dist/Access/Mgmt/Hybrid), **platform** containing `EXOS` or `VOSS`, primary IP, site under a country Site Group.
2. On-box: port labels per `zabbix/port-identity.md` — EXOS grammar in `display-string` (max **20**; leave `description-string` empty — it wins `ifAlias` if set). VOSS grammar in port `name`.
3. Sync: expect SNMP Monitoring + Extreme EXOS/VOSS template + role IFALIAS macros from §11.1 — **not** Network Generic; exactly one `icmpping`; hostgroup `OS/Network`.
4. If VOSS and the host still gets Network Generic: the Template Rule is wrong or the YAML was never imported — fix §6.1 before re-syncing.

### 15.1c Extreme staged enablement (ops reminder)

Full stage gates live in `zabbix/01-extreme-switching.md` §A.7. Checklist hooks:

| Stage | Checklist action |
|---|---|
| 0–3 | Templates + §11.1 + §11.2 **destination** macros (optional `--cutover-silence` only during LM migration) |
| 4 | Assign **Extreme Port Speed Expect** on Switch* roles (§7.1); confirm `{$PORTID.LLD.*}` globals |
| 5 | Flip **Switch Hybrid** macros from Access-like → Core values (§11.1), per site |
| Post-canary | Assign **Extreme Routing** on Core/Dist after OSPF canary (§7.1); set `{$VIST.CONTROL}=1` on VOSS fabric pairs |
| 6 | Capacity: context `{$IF.UTIL.MAX:"…"}` — global stays `101` until then |

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
| Spot-check Extreme port labels (EXOS `display-string` ≤20; no `description-string`; VOSS `name`) | After label campaigns / before stage 4–5 |
| Flip Hybrid macros site-by-site (§15.1c stage 5) | When that site’s `X`-fill / admin-down hygiene is clean |
| Spot-check `environment=Unknown` | After naming-convention drift |
| Update “Last verified” stamp at top of this doc | After a production re-validation |

---

## 16. Verification

After the initial build, and after major changes, confirm coverage against §13.

**What “good” looks like (spot-check in GUI / Zabbix):**

| Check | Expect |
|---|---|
| Sample Linux server | Server Agent+OOB; agent + oob SNMP; OS/Linux; Roles/Server; leaf under `Sites/CH/…` |
| Sample EXOS switch | SNMP Monitoring; **Extreme EXOS by SNMP**; role IFALIAS macros from §11.1; no Network Generic; single `icmpping`; OS/Network |
| Sample VOSS switch | SNMP Monitoring; **Extreme VOSS by SNMP** (imported YAML); same role IFALIAS as EXOS peer role; no Network Generic; single `icmpping` |
| Sample Switch Hybrid (pre–stage 5) | Same platform template as peer EXOS/VOSS; IFALIAS macros still Access-like (`USW\|…` opt-in), not Core `.*` |
| Sample Windows VM | Agent; Windows by agent; OS/Windows; leaf under `Sites/CH/…` |
| Country dashboard / ACL | Filter on parent `Sites/CH` for location views; hosts are leaf members only. Org access is global — no regional permission split |
| Host with `critical` | Also in Priority/Critical |
| Role not listed in §5b SNMP/OOB | Still has Agent via Site Group |
| VM without site | No useful profile until site/scope is set |

**Unprofiled / wrong template symptoms:** host missing in Zabbix, empty template list, or only partial stack vs §13. Use the §15.4 ladder.

**If you use the optional configure helper:** it can print a coverage census (`unprofiled`, hosts without templates, SNMP roles stuck on Agent, leftover shadow macros). Treat non-zero counts as tickets: map each metric back to §15.4. The GUI checklist remains the operator source of truth; the helper is a shortcut, not a second policy.

---

## One-line standard

**Country Site Group decides default transport and proxy; role decides transport exceptions and Extreme port macros; platform decides Extreme EXOS vs VOSS (and other OS templates); tags opt into Linux/SAP SNMP or overlays (`critical`, `do_not_monitor`).**

**Helper scripts:** `scripts/configure_nbxsync_zerotouch.py` (fleet) then `scripts/configure_nbxsync_network.py` (Extreme templates + §11.1 macros + stock EXOS EtherLike IFALIAS + TEMP_* template macro patches).
