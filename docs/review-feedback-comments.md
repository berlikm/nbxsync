# Comments on review feedback (vs zero-touch checklist)

Position comments for the reviewer. Aligned with the current GUI checklist (`Sites/*` × `Roles/*` × `OS/*`, country Site Groups as control plane).

---

## Tenancy

**We are not introducing Tenants (e.g. “Sensirion”) at this stage.**

- NetBox tenancy usage is not decided yet (how tenants map to orgs, contracts, or ownership is still open).
- Zabbix does not need a tenant dimension for the current goals: location, function, OS, and criticality already cover dashboards, permissions, and alert routing via hostgroups.
- Adding a Tenant now would be a NetBox data-model commitment without a clear consumer in either NetBox or Zabbix.

**Revisit** when tenancy has a concrete NetBox process and a Zabbix use case (e.g. multi-org RBAC) that hostgroups cannot express.

---

## Sites / Regions (continents)

**We are not introducing continent Regions (Europe / Asia / Americas) for Zabbix grouping.**

- Same reason as tenancy: Region trees are not required for Zabbix today, and we do not want to invent a geography layer in NetBox solely for monitoring.
- Country **Site Groups** already give nested location hostgroups: `Sites/<country>/<site>` (e.g. `Sites/CH/CH-STA-L26`). Parent `Sites/CH` is enough for country dashboards and “apply permissions to subgroups” in Zabbix.
- Continent groups would duplicate the Site Group tree unless Regions are maintained as first-class NetBox truth for other teams — which is not the case yet.

**If** continent-level permissions become mandatory later, prefer deriving them from an agreed NetBox Region model — not from hand-built Zabbix-only groups.

---

## Sites / Site Groups

**Agree — this is the control plane.**

Proxy, server assignment, default Agent configuration group, Sites/Roles Jinja hostgroups, environment tag, and inventory all hang on country Site Groups. That matches the reviewer’s positive assessment; the checklist keeps and extends that pattern.

---

## Manufacturers vs Device types (templates)

**Partially agree with the concern; we do not move templates to per-device.**

| Level | When we use it | Example |
|---|---|---|
| **Manufacturer** | Only when the template is true for *every* device of that vendor in scope | Dell → Dell iDRAC by SNMP (BMC), together with Server Agent+OOB |
| **Device type** | When the template is model-/OEM-specific | Dell M5224 → HP MSA 2060 template (same internals, different badge) |
| **Role** | Application or class baseline | MSSQL → MSSQL by ODBC; Switch* → Network Generic floor |
| **Platform (Template Rule)** | OS / network OS from platform name | Linux / Windows / EXOS / FortiOS → template + `OS/*` |
| **Per-device** | Exceptions only | Avoid for the happy path — recreates hand membership |

Assigning *everything* at Manufacturer is wrong (reviewer is right about M5224). Assigning *everything* per device is also wrong for zero-touch. **Policy: most specific level that is still generally true** — never prefer per-device for normal onboarding.

iDRAC stays on Manufacturer **as a template**, not as a transport configuration group.

---

## Zabbix server (certs / version check)

**Agree for production (Zabbix Cloud).**

Checklist: Validate certs = **True**, Skip version check = **False**, sync enabled. Dev/lab may relax temporarily; production must not.

---

## Proxies / Proxy groups

**Agree.**

CH → proxy group (plan: two proxies in production); other countries → single proxy (JP via KR; NL/US via CH group). Already reflected in the checklist.

---

## Template Rules

**Agree — keep as-is for OS/platform.**

A host is already in **multiple** hostgroups by design: `Sites/…` + `Roles/…` + `OS/…` (+ `Priority/Critical` when tagged). Nested groups follow Zabbix’s `Sites/CH/…` parent/child model; no change needed to “allow multi-group membership” — that is already how sync works.

---

## Tags

**Lean tags — do not copy hostgroup names into tags.**

Hostgroups are the primary axis for dashboards and permissions (`Sites/*`, `Roles/*`, `OS/*`, `Priority/Critical`). Duplicating those names as tags adds noise and two sources of truth.

Checklist tags stay minimal:

- NetBox `critical` → Priority/Critical hostgroup  
- NetBox `snmp` → gates SNMP OS Template Rules (with VM by SNMP transport)  
- NetBox `do_not_monitor` → exclusion  
- Zabbix `environment` (Jinja from hostname), `cluster` (Jinja)

Expand tags only for data that is **not** already in hostgroups.

---

## Configuration groups (SNMP Linux / SNMP Windows)

**Handled without separate “SNMP Linux Monitoring” / “SNMP Windows Monitoring” groups.**

Reason: transport (SNMP interface) is the same for Linux and Windows; only the **OS template** differs.

| Need | How |
|---|---|
| SNMP interface on a VM | Configuration group **VM by SNMP** (transport only) |
| Correct OS SNMP template | Template Rules “SNMP Linux (tag)” / “SNMP Windows (tag)” gated by NetBox tag `snmp` |

That avoids two nearly identical configuration groups and keeps “one effective transport profile” clear. Pre-populating Zabbix server on every configuration group is optional UX; server affinity already comes from the Site Group server assignment for all devices in scope.

---

## Hostgroups (continents, Database vs Teams, nesting)

**Nesting — agree; we already use it.**  
`Sites/<country>/<site>`, `Roles/<role>`, `OS/<family>`, `Priority/Critical`. Zabbix parent filters and “apply to subgroups” work on `Sites/CH` without putting every host in a flat country group.

**Continent groups — skip for now** (see Regions above).

**“Database” vs “Team Database” — we use `Roles/…` as the function axis**, not a parallel Teams tree. A database host is in `Roles/MSSQL` (or similar) plus `Sites/…` plus `OS/…`. If Zabbix RBAC later needs a team-shaped group that is not equal to a Device Role, add that as an explicit second axis then — not by default.

Multi-group membership is already the model; the checklist does not limit a device to one group.

---

## User permissions (Zabbix)

**Agree this is Zabbix-native follow-up**, not nbxsync configuration.

Grant user groups rights on parent hostgroups (`Sites/CH`, optionally `Roles/…`) with “Apply permissions and tag filters to all subgroups.” That depends on nested `Sites/*` existing — which the checklist produces — not on Tenants or continent Regions.

---

## Summary table

| Review topic | Disposition |
|---|---|
| Tenant “Sensirion” | **Skip** — NetBox use unclear; not needed for Zabbix yet |
| Continent Regions | **Skip** — same; country Site Groups + nested `Sites/*` suffice |
| Site Groups as control plane | **Keep / praise** |
| Templates at Manufacturer | **Only vendor-uniform** (e.g. iDRAC); OEM/model → Device type; not per-device by default |
| Cert validation / no skip version | **Accept** for production |
| Proxies / CH proxy group | **Keep** |
| Template Rules | **Keep**; multi-group already true |
| Many tags / tag = hostgroup name | **Keep lean**; hostgroups are the dashboard/RBAC axis |
| Separate SNMP Linux/Windows CGs | **No** — VM by SNMP + tag-gated Template Rules |
| Continent + Teams hostgroups | **No continents for now**; function = `Roles/*` |
| Nested hostgroups / permissions | **Yes** — already in design; finish in Zabbix user groups |

**One line:** we only add NetBox dimensions (tenant, region) when both NetBox ownership and a Zabbix consumer are clear; until then country Site Groups + Roles + OS + Priority cover integration needs.
