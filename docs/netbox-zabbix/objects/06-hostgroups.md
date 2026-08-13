# Hostgroups

nbxSync models: `ZabbixHostgroup`, `ZabbixHostgroupAssignment`  
NetBox: **Zabbix → Hostgroups**, then assign on Site Group or Tag → Zabbix tab  
Zerotouch: step 8

## What this is

A hostgroup has a NetBox **name** and a **value** pushed to Zabbix. Value may be Jinja; it renders per Device/VM at sync.

Zabbix nesting is a naming convention (`Sites/CH/…`). nbxSync creates missing parent segments. Hosts are members of the **leaf** only. Parents exist so dashboards can filter on `Sites/CH`.

We use four axes: `Sites/…`, `Roles/…`, `OS/…`, optional `Priority/Critical`. No `Teams/*`, no `Managed`.

## Sites

| Name | Value | Assign to |
|---|---|---|
| Sites | `Sites/{{ object.site.group.get_ancestors(include_self=True) \| map(attribute="name") \| join("/") }}/{{ object.site.name }}` | Site Groups CH, HU, JP, KR, NL, US, CN |

| NetBox layout | Rendered | Parents |
|---|---|---|
| Site under campus CH-STA (parent CH) | `Sites/CH/CH-STA/CH-STA-L42` | `Sites`, `Sites/CH`, `Sites/CH/CH-STA` |
| Site directly under country CH | `Sites/CH/<site>` | `Sites`, `Sites/CH` |

A preview error when viewing the assignment **on a Site Group** is cosmetic (Site Group has no `object.site`). Sync on a Device is fine.

## Roles

| Name | Value | Assign to |
|---|---|---|
| Roles | `Roles/{{ object.role.name }}` | Same country Site Groups |

Assigned on the country so every device under it inherits the template; the role **name** still comes from the device. New roles appear as `Roles/<name>` automatically — do not create a per-role hostgroup assignment.

## OS

Created with Template Rules (`OS/Windows`, `OS/Linux`, `OS/Network`, `OS/VMware`). Membership is applied when a rule matches.

## Priority / Critical

| Name | Value | Assign to |
|---|---|---|
| Priority/Critical | `Priority/Critical` | NetBox tag `critical` |

Orthogonal overlay. Tag the Device/VM `critical`; no per-device hostgroup row.
