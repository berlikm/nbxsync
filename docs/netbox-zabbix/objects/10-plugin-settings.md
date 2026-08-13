# Plugin settings

nbxSync: NetBox **Admin → Plugins → nbxSync** (not a Zabbix-menu object)  
Zerotouch does not write these; a NetBox admin sets them once.

## What this is

Global behaviour: source of truth, who is excluded, how NetBox status maps to Zabbix enabled/disabled/deleted, inheritance order.

## What we set

| Setting | Value |
|---|---|
| Source of truth (host, hostgroup, interface, template, tag, macro, proxy, maintenance) | NetBox |
| Exclude tag | `do_not_monitor` |
| Soft-state tag / value | `NO_ALERTING` / `1` (paused VMs) |
| Attach object identity tags | Yes (`nb_type` / `nb_id`) |
| Allow inherited deletion | No |
| Adopt existing Zabbix hosts | No |
| Device status → Zabbix | active → enabled; planned/staged → disabled; failed/offline/inventory/decommissioning → deleted |
| VM status → Zabbix | active → enabled; planned → enabled in maintenance; paused → enabled + soft-state tag; failed/offline → deleted |
| SNMP community / auth / priv macro names | `{$SNMP_COMMUNITY}`, `{$SNMP_AUTHPASS}`, `{$SNMP_PRIVPASS}` |

Keep **Site / Site Group after Role / Platform** in the inheritance chain so country Agent default does not override role SNMP or iDRAC CGs.
