# Response to configuration review

Thank you for the detailed review. Below we answer each section in turn.

---

## Tenancy section

**Recommendation:** Create a primary Tenant (e.g. “Sensirion”).

**Our position:** We will not create a Tenant at this stage.

Tenancy in NetBox is not yet defined for our processes, and Zabbix does not need a tenant dimension for the current scope. Location, function, OS, and criticality are already expressed as hostgroups and cover dashboards, permissions, and alert routing. We can revisit Tenants when NetBox ownership of that model is clear and there is a concrete Zabbix use case that hostgroups cannot cover.

---

## Sites / Regions section

**Recommendation:** Separate regions by continent (Asia, Europe, Americas) for hostgroup structure and user permissions.

**Our position:** We will not introduce continent or regional layers (NetBox Regions, continent Site Groups, or Zabbix-only continent hostgroups).

Our organisation is flat for monitoring access: permissions are global across resources, not split by APAC / EMEA / AMER. Country Site Groups already produce nested location hostgroups (`Sites/CH/…/<site>`). Country- and campus-level boards and filters use those parents; we do not need a permission node between `Sites/` and `Sites/CH`.

If that ever changes, parent Site Groups above countries would be the natural fit. It is not in scope now.

---

## Sites / Site Groups section

**Feedback:** Site Groups are working well; proxy and related Zabbix settings can be set on them.

**Our position:** Agreed. We keep country Site Groups as the control plane for proxy, Zabbix server assignment, default Agent configuration group, Sites and Roles hostgroup templates, environment tag, and host inventory.

The Sites hostgroup value uses the full Site Group ancestry so the path always includes the country (e.g. `Sites/CH/CH-STA/CH-STA-L42`). Hosts stay in the leaf only; dashboards filter on the parent.

---

## Devices / Manufacturers / Device types (templates)

**Recommendation:** Do not assign templates on Manufacturer; link templates on Device type (or per device). Example: Dell M5224 storage needs the HP MSA 2060 template, not a Dell template.

**Our position:** We agree that Manufacturer-wide templates are often too broad, and that Device type is the right place for model- or OEM-specific templates (including the HP MSA case).

Important clarification: templates **merge**; they never override. A Device type assignment **adds** a template; it does **not** remove one inherited from Manufacturer. We verified this in the lab (HP MSA on Device type + iDRAC on Manufacturer → both linked).

Therefore:

- **Device type** — OEM / model-specific templates (e.g. HP MSA 2060 on the Dell M5224 type).
- **Device Role** — application or class baselines (MSSQL, storage floors, …).
- **Template Rules** — OS from platform name, and compound cases.
- **Individual device** — exceptions only; not the mass pattern.
- **Dell iDRAC** — not on Manufacturer Dell (too wide). Configured as a Template Rule: platform `.*`, role `^Server$`, Manufacturer Dell → Dell iDRAC by SNMP. Transport stays Server Agent+OOB (`oob_ip`).

We will not solve “wrong template at Manufacturer” by implying Device type replaces it.

---

## Zabbix section (server)

**Feedback:** Token auth and template sync look correct.  
**Recommendation (production / Zabbix Cloud):** enable HTTPS certificate validation; disable “Skip version check”; keep automatic synchronization.

**Our position:** Agreed for production. Lab or temporary HTTP environments may differ.

---

## Zabbix / Proxies and Proxy groups

**Feedback:** Lab setup is fine. Production: CH uses a proxy group of two proxies; other sites use a single proxy.

**Our position:** Agreed. We keep that model (JP via KR; NL and US via the CH group as planned).

---

## Zabbix / Template Rules

**Feedback:** Well executed for Windows (and similar). Keep it. Devices must be able to belong to multiple hostgroups.

**Our position:** Agreed. We keep Template Rules for platform → OS template and `OS/…` hostgroup, plus SNMP-by-tag OS templates and Dell iDRAC (above). Multi-group membership is already in place (`Sites/…`, `Roles/…`, `OS/…`, optional `Priority/Critical`).

---

## Zabbix / Tags

**Recommendation:** Reconsider how many tags are used; if expanding, include hostgroup names as tags for dashboards and filtering.

**Our position:** We keep tags lean and do **not** duplicate hostgroup names as tags — that would be two sources of truth for the same dimension.

Hostgroups remain the primary axis for dashboards and permissions. Tags in use today: NetBox `critical`, `snmp`, `do_not_monitor`; Zabbix `environment`, `cluster`. If a specific Zabbix action or widget can only use tag operators (not hostgroup filters), we can add a targeted tag for that case.

---

## Zabbix / Configuration groups

**Recommendation:** Add separate “SNMP Linux Monitoring” and “SNMP Windows Monitoring” configuration groups; pre-assign the Zabbix server on the configuration group.

**Our position:** We do not create separate SNMP Linux / SNMP Windows configuration groups.

Transport (the SNMP interface) is the same for Linux and Windows; only the OS template differs:

- Configuration group **SNMP by tag** (SNMP interface only) on Device or VM that must use SNMP instead of agent.
- Template Rules “SNMP Linux” / “SNMP Windows”, gated by NetBox tag `snmp`, attach the correct OS SNMP template.

Zabbix server affinity continues to come from the country Site Group server assignment, not from the configuration group.

---

## Zabbix / Hostgroups (nesting, continents, permissions)

**Recommendation:** Multi-group membership; continent groups; nested hostgroups (Zabbix docs); Database (not only Team Database); use nesting for dashboards and user permissions.

**Our position:** Nested hostgroups are already the model: `Sites/…`, `Roles/…`, `OS/…`, optional `Priority/Critical`. A device is a member of several groups at once.

Dashboards and permissions do **not** need the host to be a direct member of every level. Zabbix nesting means a board or permission on a **parent** includes nested children. Hosts stay in the leaf; a country board filters on `Sites/CH`.

Continent groups are out of scope (see Regions above) — access is global. For function we use `Roles/…` (e.g. `Roles/MSSQL`). If permissions later need a team-shaped group that is not a Device Role, we can add that then.

Zabbix user permissions stay designed in Zabbix. Nested `Sites/CH/…` is for location dashboards and filters, not a regional RBAC tree.

---

## Short summary

| Topic | Decision |
|---|---|
| Tenant | Not now |
| Continents / regional ACL | Not needed — access is global |
| Site Groups | Keep as control plane; nested Sites for location |
| Templates | Merge only; Device type adds; iDRAC = Template Rule Dell ∧ Server |
| Certs / version check | As recommended for production |
| Proxies | Keep current CH group plan |
| Template Rules | Keep; multi-group already in place |
| Tags | Lean; do not mirror hostgroup names |
| SNMP override | One **SNMP by tag** CG + tag `snmp` (not separate Linux/Windows CGs) |
| Nested groups | Parent filter; hosts stay in leaf |
