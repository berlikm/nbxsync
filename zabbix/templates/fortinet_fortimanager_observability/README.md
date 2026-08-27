# FortiManager Observability (estate companion)

Nests **Fortinet FMG-FAZ by SNMP**. `--apply-fmg-faz` imports this YAML and
points platform Template Rule **FortiManager** here.

Do not also assign **Network Generic**, **ICMP Ping**, FortiGate templates, or
the SNMP parent on the same host — the parent is nested (own `icmpping`).
Generic role **Firewall** does not get this template (FortiGates share that
role).

Companion-only gap: host board **Devices** (FGFM connect honeycomb). Config
out-of-sync stays collect-only (`{$FM.CONFIG.CONTROL}=0`) — cfgit owns that
ticket. Health / Hardware / Cluster / Network interfaces come from the nested
parent.

Operator page: [`../../03-fortinet.md`](../../03-fortinet.md).
