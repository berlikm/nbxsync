# Response to configuration review

Thank you for the detailed feedback. Below is how we are taking each point into the zero-touch nbxSync design.

---

## Tenancy

We will not create a Tenant (for example “Sensirion”) at this stage.

Tenancy in NetBox is not yet defined for our processes, and Zabbix does not need a tenant dimension for the current scope. Location, function, OS, and criticality are already expressed as hostgroups and cover dashboards, permissions, and alert routing.

We can revisit Tenants when NetBox ownership of that model is clear and there is a concrete Zabbix use case that hostgroups cannot cover.

---

## Sites / Regions (continents)

We will not introduce continent Regions (Europe / Asia / Americas) for monitoring groups at this stage.

The same rationale as tenancy applies: we do not want to invent a geography layer in NetBox only for Zabbix. Country Site Groups already produce nested location hostgroups such as `Sites/CH/CH-STA-L26`. Parent group `Sites/CH` is sufficient for country dashboards and for Zabbix permissions with “apply to subgroups.”

If continent-level permissions become a hard requirement later, they should follow an agreed NetBox Region model used by the business—not Zabbix-only groups.

---

## Sites / Site Groups

We keep country Site Groups as the control plane. Proxy, Zabbix server assignment, default Agent configuration group, Sites and Roles hostgroup templates, environment tag, and host inventory all hang there. That matches your assessment that Site Groups are working well.

---

## Manufacturers vs Device types (templates)

Templates should sit at the most specific level that is still generally true. We automate at the highest safe level, then overwrite where a class of device needs something different—not by listing every server by hand.

| Level | When we use it | Example |
|---|---|---|
| Manufacturer | Only when the template applies to that vendor’s devices in scope as a class | Dell → Dell iDRAC by SNMP (BMC), together with the Server Agent+OOB profile |
| Device type | Model- or OEM-specific templates | Dell M5224 → HP MSA 2060 template (same internals, different badge) |
| Device Role | Application or class baseline | MSSQL → MSSQL by ODBC; switches → Network Generic as a floor |
| Platform (Template Rule) | OS / network OS from platform name | Linux / Windows / EXOS / FortiOS → template + `OS/…` hostgroup |
| Individual device | Exceptions only | Avoid for normal onboarding |

Your M5224 example is exactly why OEM/model templates belong on **Device type**, not on Manufacturer. Per-device assignment remains available for true one-offs; it is not the default path, because that recreates hand-maintained membership.

### Dell iDRAC on Manufacturer

**Default: we want iDRAC monitored automatically for Dell servers.**  
Dell iDRAC by SNMP is assigned on **Manufacturer Dell**. Transport for the BMC plane comes from configuration group **Server Agent+OOB** (SNMP with “use OOB IP”). When a new Dell server is introduced in NetBox with an out-of-band IP, iDRAC monitoring comes with it—no per-device template row.

**Other Dell hardware (for example storage)** does not stay on a blind Manufacturer-only story. At **Device type** we assign the correct template for that model (for example Dell M5224 → HP MSA 2060). That is the deliberate overwrite for devices where iDRAC is the wrong template. Inheritance is additive, so OEM/storage templates live on Device type; we do not rely on Manufacturer for those model-specific stacks.

**If something misbehaves**, we prefer to keep the automated Manufacturer default and correct the exception at Device type (or, for a rare host, at the device). Only if Manufacturer-level iDRAC proves too noisy in practice would we remove it from Manufacturer and switch to Device-type lists or tag-based assignment instead. Start as automated as possible; narrow or relocate what does not work.

iDRAC stays a **template** assignment (Manufacturer by default). It is not a separate “OOB Management” configuration group on the manufacturer—transport stays on the Server Agent+OOB role profile. Without `oob_ip`, the OOB SNMP interface is skipped, so there is nothing to poll on the BMC network for that host.

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

We keep tags lean and do **not** duplicate hostgroup names as tags.

Hostgroups are the primary axis for dashboards and permissions (`Sites/*`, `Roles/*`, `OS/*`, `Priority/Critical`). Copying those names into tags creates two sources of truth.

Tags we use:

- NetBox `critical` → hostgroup Priority/Critical  
- NetBox `snmp` → selects Linux/Windows by SNMP Template Rules (together with VM by SNMP transport)  
- NetBox `do_not_monitor` → exclusion from sync  
- Zabbix `environment` (from hostname) and `cluster` (from cluster name)

We only add further tags for information that is not already expressed in hostgroups.

---

## Configuration groups (SNMP Linux / SNMP Windows)

We do not create separate “SNMP Linux Monitoring” and “SNMP Windows Monitoring” configuration groups.

Transport (the SNMP interface) is the same for Linux and Windows; only the OS template differs:

- Configuration group **VM by SNMP** supplies the SNMP interface (transport only).
- Template Rules “SNMP Linux” / “SNMP Windows”, gated by NetBox tag `snmp`, attach the correct OS SNMP template.

That keeps one clear transport profile per host and avoids two nearly identical configuration groups. Zabbix server affinity continues to come from the country Site Group server assignment, which already applies to all devices under that country.

---

## Hostgroups (continents, database groups, nesting, dashboards)

We use nested Zabbix hostgroups: location (`Sites/…`), function (`Roles/…`), OS (`OS/…`), and optionally `Priority/Critical`. A device is already in several groups at once; it is not limited to one.

**Dashboards do not need the host to be a direct member of every level.**  
Zabbix nesting means a dashboard (or permission) on a **parent** group includes nested children. Hosts stay in the leaf only (for example `Sites/CH-STA/CH-STA-L42`). A country- or campus-level board filters on the parent (`Sites/CH` or `Sites/CH-STA`); you do not also assign the host into flat `CH` and `CH-STA` groups. That dual membership is unnecessary and would fight the nested model.

We are not adding continent hostgroups for now (see Regions above).

For function we use `Roles/…` (for example `Roles/MSSQL`), not a parallel “Teams / Database” tree. If permissions later need a team-shaped group that is not the same as a Device Role, we can add that as an explicit extra axis then.

### Nested Sites path (includes country)

The Sites hostgroup value uses the full Site Group ancestry:

```
Sites/{{ object.site.group.get_ancestors(include_self=True) | map(attribute="name") | join("/") }}/{{ object.site.name }}
```

A site under campus **CH-STA** (parent **CH**) therefore becomes `Sites/CH/CH-STA/CH-STA-L42`. Parent-first create materializes `Sites`, `Sites/CH`, and `Sites/CH-STA`. Sites hanging directly under **CH** render as `Sites/CH/<site>`.

Hosts remain in the leaf only; country dashboards and permissions filter on parent `Sites/CH` (nested children included). Do not also assign hosts into a flat `CH` group.

*(A shorter template that only uses `object.site.group.name` would skip the country segment when the site’s group is a campus — that is not what we configure.)*

---

## User permissions (Zabbix)

Permission design stays in Zabbix: user groups get rights on parent hostgroups such as `Sites/CH` or `Sites/CH-STA` (and optionally `Roles/…`) with apply-to-subgroups enabled. That depends on the nested `Sites/*` tree nbxSync creates from the rendered path. It does not require Tenants or continent Regions in NetBox.

---

## Short summary

| Topic | Decision |
|---|---|
| Tenant | Not now — NetBox use unclear; not required for Zabbix yet |
| Continent Regions | Not now — country Site Groups + nested `Sites/*` are enough |
| Site Groups | Keep as control plane |
| Templates | Automate at Manufacturer when true for the class; overwrite OEM/model on Device type; per-device only for rare cases |
| iDRAC | Manufacturer Dell by default for servers; Device type overwrite for storage/OEM; narrow later only if needed |
| Certs / version check | On / off as recommended for production |
| Proxies | Keep CH proxy group plan |
| Template Rules | Keep; multi-group already in place |
| Tags | Lean; do not mirror hostgroup names |
| SNMP Linux/Windows | VM by SNMP + tag-gated Template Rules |
| Nested groups / Zabbix permissions | Yes — dashboard/ACL on parent; hosts stay in leaf |
| Nested Sites path | Full Site Group ancestry (`get_ancestors`) so `Sites/CH/…` exists for country boards |

Country Site Group decides default transport and proxy; role decides transport exceptions; platform / manufacturer / device type decide templates at the right level; tags only add overlays.
