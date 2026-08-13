# Host inventory

nbxSync model: `ZabbixHostInventory`  
NetBox: **Site Group → Zabbix tab → Host Inventory**  
Zerotouch: step 10

## What this is

Maps NetBox fields into Zabbix host inventory (serial, hardware, URL back to NetBox, …). One Jinja payload on every **country Site Group** — same control plane as proxy, Agent CG, and Sites/Roles hostgroups.

Inventory mode **Automatic** lets templates also fill `os` / `os_full`.

## What we set

Assign to Site Groups: CH, HU, JP, KR, NL, US, CN.

| Field | Value |
|---|---|
| Inventory mode | Automatic |
| type | `{{ object.__class__.__name__ }}` |
| serialno_a | `{{ object.serial }}` |
| hardware | `{{ object.device_type.model if object.device_type else "" }}` |
| hardware_full | `{{ object.device_type.manufacturer.name if object.device_type else "" }} {{ object.device_type.model if object.device_type else "" }}` |
| tag | `{{ object.asset_tag }}` |
| location | `{{ object.site.name }}` |
| site_rack | `{{ object.rack.name if object.rack else "" }}` |
| name | `{{ object.name }}` |
| url_a | `{% if object.device_type %}https://netbox.sensirion.lokal/dcim/devices/{{ object.id }}/{% else %}https://netbox.sensirion.lokal/virtualization/virtual-machines/{{ object.id }}/{% endif %}` |
| deployment_status | `{{ object.status }}` |
