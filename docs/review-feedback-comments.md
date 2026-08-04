# Response to configuration review

Thank you for the detailed feedback. Below is how we are taking each point into the zero-touch nbxSync design.

---

## Tenancy

We will not create a Tenant (for example “Sensirion”) at this stage.

Tenancy in NetBox is not yet defined for our processes, and Zabbix does not need a tenant dimension for the current scope. Location, function, OS, and criticality are already expressed as hostgroups and cover dashboards, permissions, and alert routing.

We can revisit Tenants when NetBox ownership of that model is clear and there is a concrete Zabbix use case that hostgroups cannot cover.

---

## Sites / Regions (continents)

We will **not** introduce continent or regional layers (NetBox Regions, continent Site Groups, or Zabbix-only continent hostgroups).

Our organisation is flat for monitoring access: permissions are global across resources, not split by APAC / EMEA / AMER (or similar). Country Site Groups already produce nested location hostgroups (`Sites/CH/…/<site>`). Country- and campus-level boards and filters use those parents; we do not need a permission node between `Sites/` and `Sites/CH`.

If that ever changes, parent Site Groups above countries would be the natural fit (ancestry Jinja already supports them). It is not in scope now.

---

## Sites / Site Groups

We keep country Site Groups as the control plane. Proxy, Zabbix server assignment, default Agent configuration group, Sites and Roles hostgroup templates, environment tag, and host inventory hang on the country groups. That matches your assessment that Site Groups are working well.

---

## Manufacturers vs Device types (templates)

Templates should sit at the most specific level that is still generally true — not by listing every device by hand.

| Level | When we use it | Example |
|---|---|---|
| Manufacturer | When the template is true for that vendor class in the happy path | Dell → Dell iDRAC by SNMP (BMC) with Server Agent+OOB |
| Device type | Model- or OEM-specific **additional** templates | Dell M5224 → HP MSA 2060 |
| Device Role | Application or class baseline | MSSQL → MSSQL by ODBC; switches → Network Generic floor |
| Platform (Template Rule) | OS / network OS from platform name | Linux / Windows / EXOS / FortiOS → template + `OS/…` |
| Individual device | Exceptions only | Avoid for normal onboarding |

**Important: templates merge; they never override.**  
Resolution is additive by template ID. A Device type assignment does **not** remove a Manufacturer template. A Dell M5224 with HP MSA 2060 on Device type **still receives Dell iDRAC by SNMP** from Manufacturer Dell whenever that host has an SNMP interface (for example from OOB SNMP Only or Server Agent+OOB).

So Device type is a deliberate **add**, not an overwrite. Where two templates are incompatible (item-key collisions — the same class of problem that led us to **Storage Generic Device by SNMP** instead of Network Generic alongside iDRAC), we must either:

1. Confirm the pair is safe together, or  
2. Remove iDRAC from Manufacturer and place it only on Device types / roles / tags that should have BMC — keeping automation where it is safe.

We will not answer “wrong template at Manufacturer” by implying Device type replaces it. Per-device assignment remains for true one-offs only; mass per-device linking is the hand-maintained membership pattern we are leaving behind.

**Interface requirements (safety net):** each nbxsync Template can require Agent, SNMP, ANY, etc. At sync, a template is linked only if the host has those interface types; otherwise it is skipped silently. That is why broad Manufacturer or Role assignment is structurally safer than it looks: an SNMP-only template does not attach to an agent-only host. It does **not** solve two SNMP templates colliding with each other — that still needs compatibility checks or narrower assignment (as with Storage Generic vs iDRAC).

### Dell iDRAC on Manufacturer

**Default: we want iDRAC monitored automatically for Dell servers.**  
Dell iDRAC by SNMP stays on **Manufacturer Dell**, with BMC transport from **Server Agent+OOB**. New Dell servers with `oob_ip` pick up iDRAC without per-device rows.

For Dell storage / OEM models we add the correct model template on **Device type**. Because inheritance is additive, we will verify that template against iDRAC (or drop Manufacturer iDRAC for those models) before relying on both. If Manufacturer-level iDRAC proves too broad in practice, we move iDRAC off Manufacturer onto Device types or a tag — automate first, then narrow what does not work.

Without `oob_ip`, the OOB SNMP interface is skipped, so there is nothing to poll on the BMC network for that host. iDRAC remains a **template**, not a Manufacturer transport configuration group.

---

## Zabbix server (certificate / version check)

For production (Zabbix Cloud) we will enable HTTPS certificate validation and disable “Skip version check.” Automatic synchronization stays on. Lab or temporary HTTP environments may differ; production must not.

---

## Proxies / Proxy groups

We keep the current model: CH uses a proxy group (two proxies in production as planned); other countries use a single proxy (JP via KR; NL and US via the CH group).

---

## Template Rules

We keep Template Rules for platform → OS template and `OS/…` hostgroup. No change needed there.

A single device is already a member of multiple hostgroups: `Sites/…`, `Roles/…`, `OS/…`, and optionally `Priority/Critical`. Nested groups follow Zabbix’s parent/child model (for example under `Sites/CH`).

---

## Tags

We keep tags lean and do **not** duplicate hostgroup names as tags by default — that would be two sources of truth for the same dimension.

Hostgroups remain the primary axis for dashboards and permissions (`Sites/*`, `Roles/*`, `OS/*`, `Priority/Critical`).

Tags we use:

- NetBox `critical` → hostgroup Priority/Critical  
- NetBox `snmp` → selects Linux/Windows by SNMP Template Rules (with **SNMP by tag** transport)  
- NetBox `do_not_monitor` → exclusion from sync  
- Zabbix `environment` (from hostname) and `cluster` (from cluster name)

If a specific Zabbix **action condition** or widget can only be expressed with tag operators and not with hostgroup filters, tell us which one — we can add a targeted tag for that case cheaper than mirroring the whole group tree.

---

## Configuration groups (SNMP Linux / SNMP Windows)

We do not create separate “SNMP Linux Monitoring” and “SNMP Windows Monitoring” configuration groups.

Transport (the SNMP interface) is the same for Linux and Windows; only the OS template differs:

- Configuration group **SNMP by tag** (SNMP interface only) — assign on any Device or VM that must use SNMP instead of agent.  
- Template Rules “SNMP Linux” / “SNMP Windows”, gated by NetBox tag `snmp`, attach the correct OS SNMP template.

(The group was previously named “VM by SNMP”; the mechanism was never VM-only. Physical Linux/Windows servers that must be SNMP-monitored use the same pair: **SNMP by tag** + tag `snmp`.)

That keeps one clear transport profile per host. Zabbix server affinity continues to come from the country Site Group server assignment.

---

## Hostgroups (continents, database groups, nesting, dashboards)

We use nested Zabbix hostgroups: location (`Sites/…`), function (`Roles/…`), OS (`OS/…`), and optionally `Priority/Critical`. A device is already in several groups at once; it is not limited to one.

**Dashboards do not need the host to be a direct member of every level.**  
Zabbix nesting means a dashboard (or permission) on a **parent** group includes nested children. Hosts stay in the leaf only. A country- or campus-level board filters on the parent (`Sites/CH` or `Sites/CH/CH-STA`); you do not also assign the host into flat duplicate groups.

Regional (continent) nesting is out of scope — organisation access is flat/global (see Regions above).

For function we use `Roles/…` (for example `Roles/MSSQL`). If permissions later need a team-shaped group that is not the same as a Device Role, we can add that as an explicit extra axis then.

### Nested Sites path (includes country)

The Sites hostgroup value uses the full Site Group ancestry:

```
Sites/{{ object.site.group.get_ancestors(include_self=True) | map(attribute="name") | join("/") }}/{{ object.site.name }}
```

A site under campus **CH-STA** (parent **CH**) becomes `Sites/CH/CH-STA/CH-STA-L42`. Parent-first create materializes each segment. Sites hanging directly under **CH** render as `Sites/CH/<site>`.

Hosts remain in the leaf only; dashboards filter on the appropriate parent. Do not also assign hosts into a flat country group.

---

## User permissions (Zabbix)

Permission design stays in Zabbix. Access is **global** across the monitored estate (flat organisation) — we are not splitting user groups by continent or region. Nested `Sites/CH/…` remains useful for **dashboards and filters** by location; it is not a regional RBAC tree. Optional tighter scopes (e.g. a single country parent) remain available if a team ever needs them, without introducing continent layers.

---

## Short summary

| Topic | Decision |
|---|---|
| Tenant | Not now — NetBox use unclear; not required for Zabbix yet |
| Continent / regional permissions | Not needed — org is flat; access is global. No continent Site Groups or Regions for monitoring |
| Site Groups | Country control plane; nested `Sites/CH/…` for location dashboards/filters |
| Templates | Merge only — Device type **adds**, never replaces Manufacturer |
| iDRAC | Manufacturer default for servers; verify compatibility where Device type adds OEM; narrow if needed |
| Interface requirements | Structural safety net for wrong transport; not a fix for two SNMP templates colliding |
| Certs / version check | On / off as recommended for production |
| Proxies | Keep CH proxy group plan |
| Template Rules | Keep; multi-group already in place |
| Tags | Lean; add only for concrete action/widget gaps |
| SNMP transport override | **SNMP by tag** + tag `snmp` (Device or VM) |
| Nested groups / dashboards | Parent filter; hosts stay in leaf |
| Nested Sites path | Full Site Group ancestry so country parents exist for location boards |

Country Site Group decides default transport and proxy; role decides transport exceptions; platform / manufacturer / device type **add** templates at the right level (they do not override each other); tags only add overlays.
