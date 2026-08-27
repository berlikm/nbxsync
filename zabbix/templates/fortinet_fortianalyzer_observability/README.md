# FortiAnalyzer Observability (estate companion)

Nests **Fortinet FMG-FAZ by SNMP**. `--apply-fmg-faz` imports this YAML and
points platform Template Rule **FortiAnalyzer** here.

Do not also assign **Network Generic**, **ICMP Ping**, FortiGate templates, or
the SNMP parent on the same host — the parent is nested (own `icmpping`).
Generic role **Firewall** does not get this template.

Companion-only gaps: host board **Logs**; log-indexing lag Warning/Average;
log-disk **High** at `{$DISK.UTIL.HIGH}=95` (log loss — documented exception
to “High is site only”); licensed GB/day Average once
`{$FAZ.LIC.GBDAY.MAX}` is set. Factory product ADOMs (FortiMail, FortiWeb, …)
are excluded on the shared parent (`{$FM.ADOM.NAME.NOT_MATCHES}`). Unused
factory NICs **port2/3/4** are muted (`{$IFCONTROL:"portN"}=0`); set `1` on
the host if a FAZ actually uses that port. Device
connect-down stays on the parent (mute FAZ-native duplicates). Health /
Hardware / Cluster / Network interfaces come from the nested parent.

Operator page: [`../../03-fortinet.md`](../../03-fortinet.md).
