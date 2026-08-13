# Proxies, proxy groups, server assignment

nbxSync models: `ZabbixProxy`, `ZabbixProxyGroup`, `ZabbixServerAssignment`  
NetBox: **Zabbix → Proxies**, **Zabbix → Proxy Groups**, then **Site Group → Zabbix tab → Zabbix Servers**  
Zerotouch: steps 2–3

## What this is

- **Proxy** — a Zabbix proxy nbxSync knows by name/`proxyid`. TLS fields here are the **proxy↔server** encryption Zabbix stores on the proxy object (not agent TLS on each host).
- **Proxy group** — HA pair; a host is monitored by the group, not a single member.
- **Server assignment** — which Zabbix server (and which proxy or group) monitors objects under that NetBox object. We put this on each **country Site Group**. Children inherit it.

Set **either** a proxy **or** a proxy group — not both. Flow is always NetBox → Zabbix.

Proxy VMs themselves are inventory: `netbox-sync` sets `role=Zabbix Proxy` (`-ZABP\d+`). They inherit the country proxy assignment and poll their own localhost agent (no loop).

## Topology

- Proxy → Cloud: **active**, TCP 10051, mTLS (Sensirion PKI). PEM files and Cloud portal TLS are **not** in nbxSync. We only record `tls_accept=Certificate` so a NetBox→Zabbix proxy sync does not reset encryption to none.
- Proxy → Agent: **passive**, TCP 10050. Host Encryption (agent TLS) is currently **No encryption** on the Agent configuration group.

## Proxy group

| Name | Zabbix server | Description |
|---|---|---|
| Swiss proxy group | Zabbix Production | CH pair; NL and US route through CH |

## Proxies

| Name | Mode | Proxy group | TLS accept | Local address | Local port |
|---|---|---|---|---|---|
| ch-sta-p-zabp01 | Active | Swiss proxy group | Certificate | 10.0.104.235 | 10051 |
| ch-sta-p-zabp02 | Active | Swiss proxy group | Certificate | 10.0.105.235 | 10051 |
| hu-deb-p-zabp01 | Active | — | Certificate | — | — |
| kr-sel-p-zabp01 | Active | — | Certificate | — | — |
| cn-sha-p-zabp01 | Active | — | Certificate | — | — |

## Server assignment (country Site Groups)

| Site Group | Proxy | Proxy group | Sync enabled |
|---|---|---|---|
| CH | — | Swiss proxy group | Yes |
| HU | hu-deb-p-zabp01 | — | Yes |
| JP | kr-sel-p-zabp01 | — | Yes |
| KR | kr-sel-p-zabp01 | — | Yes |
| NL | — | Swiss proxy group | Yes |
| US | — | Swiss proxy group | Yes |
| CN | cn-sha-p-zabp01 | — | Yes |

Assign only on **country** Site Groups, not campus mid-levels.

## Proxy self-monitoring templates

Role **Zabbix Proxy** gets Linux by agent (platform rule), ICMP Ping, and Remote Zabbix proxy health (Template Rules).
