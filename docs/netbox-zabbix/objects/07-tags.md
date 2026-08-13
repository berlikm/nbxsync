# Tags

nbxSync models: `ZabbixTag`, `ZabbixTagAssignment`  
NetBox: **Zabbix → Tags**, plus **Organization → Tags** (NetBox inventory tags) → Zabbix tab  
Zerotouch: step 0 (create NetBox tags), step 9 (Zabbix tag assignments)

## What this is

Two different things named “tag”:

1. **NetBox tags** — already on Devices/VMs. Sync **reads** them. They are not copied to Zabbix as host tags.
2. **Zabbix tags** — written onto the Zabbix host (environment, cluster) or used as the plugin **exclude** (`do_not_monitor`).

A Zabbix tag assignment on a **NetBox Tag** object applies to every Device/VM that carries that inventory tag.

## NetBox tags we use as inputs

Zerotouch creates `critical`, `snmp`, `onboarding` if missing. `oracle` is created when needed.

| NetBox tag | Effect |
|---|---|
| `critical` | Hostgroup `Priority/Critical` |
| `snmp` | CG SNMP Monitoring (by tag) + Linux/Windows by SNMP Template Rules |
| `oracle` | Oracle by Zabbix agent 2 Template Rule |
| `onboarding` | Inherits Zabbix `do_not_monitor` — **remove this tag to start monitoring** |

Do not use leftover `snmp-sap`. SAP transport is roles SAP HANA / SAP ME → CG SAP Agent+SNMP.

## Zabbix tag: environment (Jinja on country Site Groups)

Renders from the hostname at sync. Name-pattern only.

```
{% set n = (object.name or "") | lower -%}
{% if "-p-" in n or n.endswith("-p") or "-p0" in n or "-p1" in n -%}Production
{%- elif "-d-" in n -%}Development
{%- elif "-q-" in n -%}QA
{%- elif "-s-" in n -%}Sandbox
{%- elif "-t-" in n -%}Test
{%- elif "vdi" in n -%}VDI
{%- else -%}Unknown
{%- endif -%}
```

Assigned to Site Groups CH … CN.

Names without `-p-` / `-d-` / … become **`Unknown`**. Extreme switches (`…-CORE01`, `…-MGMT01`) normally have no `-p-` token — `Unknown` on them is expected.

## Zabbix tag: cluster

| Tag | Value | Assign to |
|---|---|---|
| cluster | `{{ object.cluster.name }}` | each Cluster |

## Exclude: `do_not_monitor`

Plugin setting `exclude_tag` = `do_not_monitor`. Sync skips the object and **deletes** an existing Zabbix host.

| Assign Zabbix tag to | Intent |
|---|---|
| Device Role Messpc, Sd Wan Socket, VDI | Permanent never-monitor |
| NetBox Tag **onboarding** | Cutover waves — tag/untag Devices/VMs |

Do **not** put `do_not_monitor` on role Server or on a Site Group for waves — you cannot open one child while the parent excludes.

Zerotouch may also create a NetBox inventory tag named `do_not_monitor` (`--mutate-netbox`). That is **not** the wave switch. Waves use NetBox tag **`onboarding`** only.
