# Zabbix Server

nbxSync model: `ZabbixServer`  
NetBox: **Zabbix → Servers**  
Zerotouch: step 1

## What this is

The API endpoint nbxSync talks to. Every template, proxy, and host in the plugin is anchored on this object. Without it, nothing syncs.

This is **not** proxy↔Cloud encryption. Validate-certs is only whether NetBox trusts the HTTPS certificate of the Zabbix API URL.

## What we set

| Field | Value |
|---|---|
| Name | Zabbix Production |
| URL | `https://sensirion.zabbix.cloud` |
| Token | API token (secret) |
| Validate certs | True |
| Sync enabled | True |
| Skip version check | False |

Lab / HTTP environments may differ. Production keeps cert validation on and version check on.
