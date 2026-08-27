# FortiManager Observability (estate companion)

Nests **Fortinet FMG-FAZ by SNMP**. `--apply-fmg-faz` imports this YAML and
points platform Template Rule **FortiManager** here.

Do not also assign **Network Generic**, **ICMP Ping**, FortiGate templates, or
the SNMP parent on the same host — the parent is nested (own `icmpping`).
Generic role **Firewall** does not get this template (FortiGates share that
role).

Companion-only gap: host board **Devices** (FGFM connect honeycomb). The ADOM
tile is enabled/disabled (`fmAdomEnabled`) — `CH-STA-P-FWMG01` is disabled,
all devices in `root`. MIB ADOM number stays on the parent (includes factory
slots). Config out-of-sync stays collect-only (`{$FM.CONFIG.CONTROL}=0`) —
cfgit owns that ticket. Factory product ADOMs are excluded on the nested
parent. Health / Hardware / Cluster / Network interfaces come from the nested
parent. Do **not** mute FMG port2; it carries traffic.

Operator page: [`../../03-fortinet.md`](../../03-fortinet.md).
