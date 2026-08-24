# FortiGate by HTTP (official, unmodified)

Stock Zabbix **7.0** template. **Do not edit this YAML.**

**Zabbix Cloud already has this template: vendor Zabbix, version 7.0-2.**
`--apply-fortigate-http` **reuses it** and does **not** re-import. 7.0-2 already
sends `Authorization: Bearer {$FGATE.API.TOKEN}`.

This file is a **missing-only fallback** (empty lab). It is vendor **7.0-3** from
the 7.0 tree. Do not use it to overwrite Cloud 7.0-2.

| | |
|---|---|
| Template name | FortiGate by HTTP |
| Live Cloud | **Zabbix, 7.0-2** — keep |
| Bundled fallback | 7.0-3 |
| Auth | `Authorization: Bearer {$FGATE.API.TOKEN}` |
| Upstream | [git.zabbix.com fortigate_http](https://git.zabbix.com/projects/ZBX/repos/zabbix/browse/templates/net/fortinet/fortigate_http?at=refs%2Fheads%2Frelease%2F7.0) |

Known stock bug in 7.0-2 and 7.0-3: script items reuse one `HttpRequest` and
`addHeader` on every `getHttpData` ([ZBX-27082](https://support.zabbix.com/browse/ZBX-27082)).
SD-WAN does several GETs. Canary that item. Do **not** fork the YAML to patch it.
