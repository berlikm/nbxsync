# FortiGate Observability (estate companion)

Nests stock **FortiGate by HTTP** (Cloud **Zabbix, 7.0-2**) and **ICMP Ping**.
`--apply-fortigate-http` imports **this** YAML (ours) and looks up the Cloud
parent by name. It never imports bundled 7.0-3 over Cloud.

Platform Template Rule **FortiOS** points here. Generic role **Firewall** does
not get this template (FortiManager / FortiAnalyzer share that role).

Companion-only gaps: Health + Path dashboards, unsupported-item census, zero
interface / SD-WAN member / HA member counts, conserve mode, estate macros
(CPU/mem CRIT 101, SD-WAN MATCHES). HA role for path-ticket gating is a
surgical item on the Cloud HTTP parent so stock trigger prototypes can
reference it.
