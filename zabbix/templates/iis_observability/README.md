# IIS Observability

Sits **next to** stock **IIS by Zabbix agent** (not nested). Stock still owns W3SVC / WAS / port / app pools. This companion only does **HTTPS bindings**: read `applicationHost.config`, LLD every `https` `<binding>`, TLS-handshake it on the box with Agent 2 `web.certificate.get`.

There is **no FQDN inventory**. Host header = SNI. Empty host header = default SSL binding (connect `127.0.0.1`); expiry still alerts. Identity is `not_evaluated_no_host_header` (not Agent 2 `invalid` against loopback). High invalid only when the host header is set. Do not choose SNI from the certificate SAN.

Import `template_iis_observability.yaml` into Zabbix **7.0** (Templates/Applications). Assign on the IIS **Device** (a couple of hosts; no zerotouch role). Needs **Zabbix agent 2**. Do not also link **Website certificate by Zabbix agent 2** for these sites (7.0 is one hostname per host).

Do not add `service.discovery` or `service.info[W3SVC]` (stock IIS already pages those). Do not scrape windows_exporter. Do not put site names in NetBox.

Tests (no live IIS): `python3 scripts/test_iis_observability.py`. Spec: [`../../notes/iis-coverage.md`](../../notes/iis-coverage.md).
