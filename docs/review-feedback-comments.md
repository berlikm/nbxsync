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

Templates should sit at the most specific level that is still generally true—not on every individual device by default, and not on Manufacturer when the template is only true for some models.

| Level | When we use it | Example |
|---|---|---|
| Manufacturer | Only when the template applies to that vendor’s devices in scope as a class | Dell → Dell iDRAC by SNMP (BMC), together with the Server Agent+OOB profile |
| Device type | Model- or OEM-specific templates | Dell M5224 → HP MSA 2060 template (same internals, different badge) |
| Device Role | Application or class baseline | MSSQL → MSSQL by ODBC; switches → Network Generic as a floor |
| Platform (Template Rule) | OS / network OS from platform name | Linux / Windows / EXOS / FortiOS → template + `OS/…` hostgroup |
| Individual device | Exceptions only | Avoid for normal onboarding |

Your M5224 example is exactly why OEM/model templates belong on **Device type**, not on Manufacturer. Per-device assignment remains available for true one-offs; it is not the default path, because that recreates hand-maintained membership.

### Dell iDRAC on Manufacturer — and servers where we do *not* want iDRAC

Default: Dell iDRAC by SNMP is assigned on **Manufacturer Dell**, and transport for the BMC plane comes from configuration group **Server Agent+OOB** (SNMP with “use OOB IP”). That covers the normal Dell server fleet without listing every device.

If a specific server must **not** be monitored via iDRAC, use one of these (in order of preference):

1. **No out-of-band IP in NetBox** — leave `oob_ip` empty on that device. The OOB SNMP interface is then skipped at sync, so there is nothing to poll on the BMC network. Prefer this when the host simply has no management IP we should use.
2. **Device-type scope instead of Manufacturer** — if only some Dell models should get iDRAC, move the template assignment from Manufacturer Dell to those Device types, and do not assign it on Manufacturer. Servers of other Dell types then never receive the template.
3. **Device-level exception** — for a small number of outliers that would otherwise inherit iDRAC, remove or override the assignment on that device (or exclude BMC monitoring by local convention). This is intentional exception handling, not the mass pattern.

What we will not do is put iDRAC on every device by hand, or keep a Manufacturer assignment and expect operators to maintain a long deny-list without a clear NetBox signal (`oob_ip` or Device type).

iDRAC remains a **template** on Dell (or on selected Device types). It is not a separate “OOB Management” configuration group on the manufacturer—transport stays on the Server Agent+OOB role profile.

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

## Hostgroups (continents, database groups, nesting)

We already use nested hostgroups: `Sites/<country>/<site>`, `Roles/<role>`, `OS/<family>`, `Priority/Critical`. Filtering and permissions on parent `Sites/CH` work with Zabbix’s “apply to subgroups” without putting every host into a flat country group.

We are not adding continent hostgroups for now (see Regions above).

For function we use `Roles/…` (for example `Roles/MSSQL`), not a parallel “Teams / Database” tree. If permissions later need a team-shaped group that is not the same as a Device Role, we can add that as an explicit extra axis then.

Multi-group membership is already the design; a device is not limited to one hostgroup.

---

## User permissions (Zabbix)

Permission design stays in Zabbix: user groups get rights on parent hostgroups such as `Sites/CH` (and optionally `Roles/…`) with apply-to-subgroups enabled. That depends on the nested `Sites/*` tree nbxSync creates. It does not require Tenants or continent Regions in NetBox.

---

## Short summary

| Topic | Decision |
|---|---|
| Tenant | Not now — NetBox use unclear; not required for Zabbix yet |
| Continent Regions | Not now — country Site Groups + nested `Sites/*` are enough |
| Site Groups | Keep as control plane |
| Templates | Manufacturer only when vendor-wide; OEM/model on Device type; per-device for exceptions only |
| iDRAC opt-out | Empty `oob_ip`, or Device-type scope, or rare device-level exception |
| Certs / version check | On / off as recommended for production |
| Proxies | Keep CH proxy group plan |
| Template Rules | Keep; multi-group already in place |
| Tags | Lean; do not mirror hostgroup names |
| SNMP Linux/Windows | VM by SNMP + tag-gated Template Rules |
| Nested groups / Zabbix permissions | Yes — finish in Zabbix user groups |

Country Site Group decides default transport and proxy; role decides transport exceptions; platform / manufacturer / device type decide templates at the right level; tags only add overlays.
