# DC services (AD + DNS + DHCP) vs stock Zabbix

Question: AD, DNS, and DHCP run on the **same** Domain Controller VMs. Does [windows_exporter](https://github.com/prometheus-community/windows_exporter/blob/master/docs/README.md) already have a Zabbix equivalent for that box, or do we need more templates?

**Answer: one additional companion, not three, and not Prometheus.** Stock **Windows by Zabbix agent** is the OS plus Automatic **service state**. Zabbix 7.0 has no official AD, DNS Server, or DHCP Server template. The exporter splits the same box across three collectors (`ad`, `dns`, `dhcp`). We would collect those counters with the agent we already run. Post-cutover. Not 01/02.

Role **Domain Controller** already gets Windows by agent + ICMP. That is box-up, not “directory / name / address services are healthy.”

---

## What Prometheus community actually ships

Three **separate** collectors. Only `dns` is on by default. None have alerting examples. Do not scrape them — every metric is a Windows perf/WMI object the Zabbix agent can read.

| Collector | Docs | Default | Object | Zabbix agent path |
|---|---|---|---|---|
| [`ad`](https://github.com/prometheus-community/windows_exporter/blob/master/docs/collector.ad.md) | NTDS / Directory Services | **off** | `Win32_PerfRawData_DirectoryServices_DirectoryServices` | `perf_counter_en["\NTDS\…"]` |
| [`dns`](https://github.com/prometheus-community/windows_exporter/blob/master/docs/collector.dns.md) | DNS Server | **on** | `Win32_PerfRawData_DNS_DNS` (+ optional `MicrosoftDNS_Statistic`) | `perf_counter_en["\DNS\…"]` |
| [`dhcp`](https://github.com/prometheus-community/windows_exporter/blob/master/docs/collector.dhcp.md) | DHCP Server + **per-scope** free/in-use | **off** | Perflib `DHCP Server` + DHCP Server API for scopes | server-wide: `perf_counter_en["\DHCP Server\…"]`; scopes: WMI/SCRIPT, not a single counter |
| [`dfsr`](https://github.com/prometheus-community/windows_exporter/blob/master/docs/collector.dfsr.md) | SYSVOL / DFS-R folders | **off**, experimental | DFSR connection/folder/volume | skip unless SYSVOL is a known pain — stock already has `DFSR` service state |
| [`time`](https://github.com/prometheus-community/windows_exporter/blob/master/docs/collector.time.md) | W32Time offset | **off** | W32Time PDH (2016+) | stock already has `system.localtime` fuzzytime vs the server |

Not this VM: `adcs` (role **PKI**), `adfs` (no NetBox role).

---

## What stock already covers on that VM

Official 7.0 **Windows by Zabbix agent**:

| Layer | Covered? |
|---|---|
| CPU / memory / disk / NIC / agent / clock skew | yes |
| Automatic service **state** (`NTDS`, `Kdc`, `Netlogon`, `DNS`, `DHCPServer`, `DFSR`, `W32Time`) | yes — `service.discovery` |
| NTDS LDAP / DRA / ATQ counters | **no** |
| DNS query / zone-transfer / dynamic-update counters | **no** |
| DHCP Acks/Nacks / packets expired / **scope free IPs** | **no** |
| `net.dns` / `net.dns.record` / `net.dns.perf` (agent keys exist in 7.0) | **not linked** on the OS template |
| `dcdiag`, FSMO, SYSVOL size | **no** |

`templates/app` on **release/7.0**: IIS, Exchange, SharePoint — **no** AD, **no** DNS Server, **no** DHCP Server.

LogicMonitor `CORP-UPA-Dom_Monitor` was a **WMI credential** on DCs. Agent replaced transport, not these role counters.

[06](../06-network-vms.md) lists DHCP/IPAM as a network-critical extra, but these DCs are still the **server estate** (one NetBox role). Do not invent a second host. The companion on **Domain Controller** is how DHCP on that VM gets watched. Agree ownership with whoever owns servers before fleet-link.

---

## One companion, not three templates

NetBox has **one** object and **one** role. Linking AD + DNS + DHCP as three templates would all attach to the same role anyway. One **DC Observability** (sit **next to** Windows by agent, unique keys) matches MSSQL Observability.

If a DC ever lacks DHCP, those items go `CHECK_NOT_SUPPORTED` — map-on-fail or a DHCP master that LLD-skips, do not leave them unsupported. User statement: **all three run on the same VM**, so a single template is the estate shape.

Do **not** re-add `service.info[NTDS|DNS|DHCPServer|…]` (stock already owns those keys).

---

## Do not import these as-is

| Source | Why not |
|---|---|
| windows_exporter on the DC | Second agent; we already have Zabbix agent |
| [community AD DS 5.4](https://github.com/zabbix/community-templates/tree/main/Operating_Systems/Windows/template_ad_ds_health_and_performance/5.4) | Numeric `perf_counter[\6956\…]` IDs; no triggers; duplicate services |
| [community DHCP scopes SNMP](https://github.com/zabbix/community-templates/tree/main/Operating_Systems/Windows/template_windows_dhcp_server_scopes_discovery_(snmp)) | Turns SNMP on Windows DCs; we are agent-only |
| PowerShell `Get-DhcpServerv4ScopeStatistics` UserParameter packs | Works, but UserParameters + scripts on every DC — last resort if WMI cannot LLD scopes |
| Clone **Windows by Zabbix agent** | Principle 7 |

There is **no** Windows DNS Server template in [zabbix/community-templates `Operating_Systems/Windows`](https://github.com/zabbix/community-templates/tree/main/Operating_Systems/Windows) (only the AD 5.4 pack, which includes DNS **service state** + eventlog, not `\DNS\` counters).

---

## If we build: companion **DC Observability**

Data path: Zabbix agent `perf_counter_en`. Confirm English object names on a live DC (`NTDS`, `DNS`, `DHCP Server`) before import. Role **Domain Controller** only. Soft-assign after YAML import. Collect first; every new trigger **DISABLED** until one canary is quiet.

### AD (`collector.ad`)

| Thing | Exporter metric | Counter | Alert | Sev |
|---|---|---|---|---|
| DRA pending replication synchronizations | `windows_ad_replication_pending_synchronizations` | `DRA Pending Replication Synchronizations` | after baseline | Average |
| ATQ estimated queue delay | `windows_ad_atq_estimated_delay_seconds` | `ATQ Estimated Queue Delay` | after baseline | Warning |
| LDAP bind time | `windows_ad_ldap_last_bind_time_seconds` | `LDAP Bind Time` | after baseline | Warning |
| NTDS / KDC / Netlogon down | exporter `service` | — | **already** stock | Average |

Graph: LDAP Client Sessions, Searches/sec, Writes/sec, Active Threads, ATQ outstanding, DRA bytes, inbound objects remaining.

Skip: address book, SAM create, phantom/tombstone, name-cache, SD propagation.

### DNS (`collector.dns`)

| Thing | Exporter metric | DNS counter | Alert | Sev |
|---|---|---|---|---|
| Recursive query failures | `windows_dns_recursive_query_failures_total` | `Recursive Query Failure` /sec | after baseline | Warning |
| Dynamic update failures | `windows_dns_dynamic_updates_failures_total` | `Dynamic Update Rejected` / `Secure Update Failure` | graph first | — |
| Zone transfer failures | `windows_dns_zone_transfer_failures_total` | `Zone Transfer Failure` | after baseline | Warning |
| DNS service down | — | — | **already** stock | Average |

Graph: Total Query Received/sec, Total Response Sent/sec, UDP vs TCP, dynamic updates queued, notifies.

Optional synthetic (not in the exporter; Zabbix agent 7.0 keys): `net.dns.record[{HOST.IP},{$DNS.TEST.NAME},A]` from the **proxy** — “this DC still answers.” That is a **symptom**. Keep it one check, depend on host ICMP. Do not also `net.udp.service` on 53.

Skip: full `MicrosoftDNS_Statistic` error-code dump (NxDomain / Refused / …) unless someone is hunting a specific fault.

### DHCP (`collector.dhcp`)

Server-wide is Perflib. **Scope free/in-use is the user-facing signal** and is **not** a single `\DHCP Server\` counter — the exporter uses the DHCP Server API for `windows_dhcp_scope_addresses_free` / `in_use` / `state`. Canary WMI (`root\standardcimv2` DHCP classes) before writing LLD; PowerShell UserParameter only if WMI cannot list scopes.

| Thing | Exporter metric | Alert | Sev |
|---|---|---|---|
| Scope addresses free (LLD) | `windows_dhcp_scope_addresses_free` | yes — `%` or count macro after baseline | Average |
| Scope disabled that should be enabled | `windows_dhcp_scope_state` | maybe | Warning |
| Packets expired in queue | `windows_dhcp_packets_expired_total` | after baseline | Warning |
| Nacks rate | `windows_dhcp_nacks_total` | graph first | — |
| Failover partner-down / communication interrupted | `windows_dhcp_failover_transitions_*` | only if the estate uses DHCP failover | Average |
| DHCPServer service down | — | **already** stock | Average |

Graph: Discovers / Offers / Requests / Acks / Releases.

Do **not** use `net.udp.service[udp,,67]` as DHCP health (UDP “open” is a false green).

---

## Cutover

Not a switch/AP cutover item. OS coverage on DCs stays ✅. AD + DNS + DHCP **role** counters are one post-cutover gap, one template, one role.
