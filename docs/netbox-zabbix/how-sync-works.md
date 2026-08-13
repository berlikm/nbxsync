# How sync works

Read this once. Object values live in `objects/` — this page is only the plugin model.

nbxSync turns a NetBox Device or VM into a Zabbix **host**. You do not configure that host by hand in Zabbix. You hang policy on NetBox objects; a sync job pushes the **effective** result.

## Objects you will see in NetBox

Top menu **Zabbix** lists plugin objects: Servers, Proxies, Proxy Groups, Templates, Macros, Tags, Hostgroups, Configuration groups, Template Rules.

Most **assignments** are not only on those pages. Open a Site Group, Device Role, Device, Tag, or Cluster → **Zabbix** tab. That is the same data.

## Inheritance

A host collects assignments from more than one place. Direct (on the Device) wins over inherited (Role, Platform, Site Group, Tag, Manufacturer).

Country **Site Group** is the default control plane: proxy, Agent configuration group, Sites/Roles hostgroups, environment tag, inventory.

A **Device Role** overrides transport when that class is not a normal agent host (SNMP switches, SPACE :10060, SAP dual-plane, iDRAC).

**Templates merge.** Role + Platform Template Rule + Manufacturer rule all accumulate. They do not replace each other. If two templates both define `icmpping`, Zabbix rejects the host — avoid that in assignment design.

## Configuration group = transport

A configuration group (CG) is a reusable **how we reach the host** profile: Agent and/or SNMP interface, ports, SNMPv3 user.

**One CG decides transport.** Hostgroups and templates can stack; two CGs on the same host do not give you two transports. The plugin expands Host Interfaces from a single winning CG (device assignment beats role, role beats Site Group).

Put Host Interfaces **on the CG**, not on every device and not on a tag. Sync fills IP from `primary_ip` or, if **Use OOB IP** is set, from `oob_ip`.

Different SNMPv3 users need different CGs (`MONITORING` vs `MONITORING-LINUX` vs `MONITORING-IDRAC` vs `SAPUSER`).

## Template Rules vs template assignments

| Mechanism | Typical use |
|---|---|
| **Template Rule** | Regex on platform name (and optional role / manufacturer / tag). Attaches OS template + `OS/…` hostgroup. |
| **Template assignment** | Explicit link on a Role (MSSQL, vCenter, GitLab, …). |

Both apply. Rules are for “this OS/platform”; assignments are for “this function”.

## What sync writes to Zabbix

- Host name = NetBox object name
- Interfaces from the winning CG
- Templates from rules + assignments (dropped silently if the host lacks the required interface type)
- Hostgroups from Jinja (Sites, Roles) + OS from rules + optional Priority/Critical
- Macros from assignments (and SNMPv3 passphrases as secret host macros when push-community is on)
- Inventory fields from Site Group Jinja
- Proxy from the country Site Group server assignment

If the host carries Zabbix tag `do_not_monitor` (from role or from NetBox tag `onboarding`), sync **skips** it and deletes an existing Zabbix host.

## What this is not

- Filling NetBox inventory (sites, roles, IPs) — assumed already there
- Alert messages, dashboards, Extreme port grammar — those are monitoring content, not nbxSync objects
- Agent/proxy **TLS certificates on the OS**. Proxy↔Cloud mTLS is on the proxy. Host Encryption (proxy↔agent) is a host field; we currently set Agent TLS to **No encryption**
