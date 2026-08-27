# FortiGate Observability (estate companion)

Nests stock **FortiGate by HTTP** (Cloud **Zabbix, 7.0-2**) and **ICMP Ping**.
`--apply-fortigate-http` imports **this** YAML (ours) and looks up the Cloud
parent by name. It never imports bundled 7.0-3 over Cloud.

Platform Template Rule **FortiOS** points here. Generic role **Firewall** does
not get this template (FortiManager / FortiAnalyzer share that role).
Do not also assign **ICMP Ping** or **FortiGate by HTTP** on the same host —
they are nested parents. FortiOS uses CG **FortiGate HTTP** (no ICMP Ping
template) so Agent Monitoring does not add a second copy.

Companion-only gaps: Health (Overview / HA), **Network interfaces**
(72×6 map + Port traffic navigator), and Path (member/health maps, Loss
honeycomb, Probe grouped by vdom with byte-rate navigation) in the same
chrome as EXOS; unsupported-item census; interface / SD-WAN / HA member
counts; configured memory-pressure alerting; estate macros (CPU/mem CRIT
101, SD-WAN MATCHES, health-check tickets opted in per VDOM — ``root``
by default). Do not put graph prototypes in this YAML: template
dashboards can reference only graph prototypes owned by the companion,
not the nested Cloud HTTP parent. HA role for path-ticket gating is a
surgical item on the Cloud HTTP parent so stock trigger prototypes can
reference it.
