# nbxSync at Sensirion

This folder is **our** nbxSync configuration: the same objects you see under NetBox **Zabbix**, with the values we actually set.

It is not the plugin source manual (`docs/models.md` in this repo) and not the Extreme switching signals (`zabbix/01-extreme-switching.md`).

## How to use this

1. Read [How sync works](how-sync-works.md) once (plugin model: inheritance, one configuration group, templates merge).
2. Open the article that matches the **Zabbix** menu item you are looking at.
3. When you change something in NetBox, update **that one article**. Do not scatter the same row across files.

First-time apply order is the zerotouch script (`scripts/configure_nbxsync_zerotouch.py` steps 1–11). The table below is that order.

## Map: NetBox Zabbix menu → article

| # | NetBox path | nbxSync model | Our article | Zerotouch |
|---|---|---|---|---|
| 1 | **Zabbix → Servers** | `ZabbixServer` | [Server](objects/01-server.md) | step 1 |
| 2 | **Zabbix → Proxies / Proxy Groups** + Site Group → Zabbix Servers | `ZabbixProxy`, `ZabbixProxyGroup`, `ZabbixServerAssignment` | [Proxies](objects/02-proxies.md) | steps 2–3 |
| 3 | **Zabbix → Configuration groups** (group + Host Interfaces + Assignments) | `ZabbixConfigurationGroup`, `ZabbixHostInterface`, `ZabbixConfigurationGroupAssignment` | [Configuration groups](objects/03-configuration-groups.md) | steps 4–5b |
| 4 | **Zabbix → Template Rules** | `ZabbixTemplateRule` | [Template Rules](objects/04-template-rules.md) | step 6 |
| 5 | **Zabbix → Templates** (and Role → Zabbix tab) | `ZabbixTemplate`, `ZabbixTemplateAssignment` | [Templates](objects/05-templates.md) | step 7 |
| 6 | **Zabbix → Hostgroups** | `ZabbixHostgroup`, `ZabbixHostgroupAssignment` | [Hostgroups](objects/06-hostgroups.md) | step 8 |
| 7 | **Zabbix → Tags** (and NetBox tags as inputs) | `ZabbixTag`, `ZabbixTagAssignment` | [Tags](objects/07-tags.md) | step 9 |
| 8 | Site Group → Host Inventory | `ZabbixHostInventory` | [Inventory](objects/08-inventory.md) | step 10 |
| 9 | **Zabbix → Macros** | `ZabbixMacro`, `ZabbixMacroAssignment` | [Macros](objects/09-macros.md) | step 11 |
| 10 | NetBox plugin config (admin) | plugin settings | [Plugin settings](objects/10-plugin-settings.md) | — |
| — | After sync: the Zabbix host | (result, not a model) | [What a host looks like](objects/11-host-result.md) | — |

Each article has the same shape: **what the object is** (learn the plugin) → **what we set** (tables) → **where it is assigned**.

## Also here

| File | When |
|---|---|
| [runbooks/day2.md](runbooks/day2.md) | New role, broken host, recurring checks |
| [runbooks/onboarding.md](runbooks/onboarding.md) | Tag `onboarding` hold during cutover |

## Updating

| You changed in NetBox… | Edit |
|---|---|
| A configuration group, its interface, or who it is assigned to | `objects/03-configuration-groups.md` |
| A Template Rule regex / template / hostgroup | `objects/04-template-rules.md` |
| A template linked on a Device Role | `objects/05-templates.md` |
| Sites/Roles Jinja or Priority/Critical | `objects/06-hostgroups.md` |
| `onboarding` / `snmp` / `do_not_monitor` / environment Jinja | `objects/07-tags.md` |
| A secret or threshold macro | `objects/09-macros.md` |
| Proxy or country routing | `objects/02-proxies.md` |
| Plugin inheritance / exclude / status map | `objects/10-plugin-settings.md` |

Then re-apply zerotouch (and `configure_nbxsync_network.py` if the change is Extreme TemplateRules or Switch* IFALIAS).
