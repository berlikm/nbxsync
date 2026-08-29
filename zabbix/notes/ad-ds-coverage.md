# Active Directory DS vs stock Zabbix

Question: does [windows_exporter `ad`](https://github.com/prometheus-community/windows_exporter/blob/master/docs/collector.ad.md) already have a Zabbix equivalent, or do we need another template?

**Answer: need an additional companion.** Stock **Windows by Zabbix agent** (7.0) is the OS. It does not collect Directory Services counters. Zabbix 7.0 ships no official AD DS template. Do not scrape windows_exporter. Do not fork the OS template. Post-cutover, not 01/02.

Role **Domain Controller** already gets Windows by agent (platform rule) + ICMP (Agent Monitoring CG). That is box-up, not “AD is healthy.”

---

## What the exporter actually is

`collector.ad` is **not** a special AD protocol. It reads WMI `Win32_PerfRawData_DirectoryServices_DirectoryServices` — the same **NTDS** object as `perfmon`. Zabbix agent already speaks those counters as `perf_counter_en["\NTDS\…"]` (same style as stock CPU/memory). No Prometheus, no UserParameter, no extra agent.

The collector is **off by default** in windows_exporter. ~60 counters; almost none documented; **no alerting examples**. Dumping the lot violates “signal with no trigger and no dashboard → delete it.”

Related exporters that are **not** this collector:

| Collector | Object | Ours |
|---|---|---|
| `ad` | NTDS / Directory Services | this note |
| `dns` | DNS Server | service **state** only today (Automatic `DNS` via `service.discovery`) |
| `dfsr` | DFSR | same — `DFSR` service state |
| `adcs` | AD CS | role **PKI** — separate, later |
| `adfs` | AD FS | not a NetBox role today |

---

## What stock already covers

Official 7.0 **Windows by Zabbix agent** ([git.zabbix.com `templates/os/windows_agent`](https://git.zabbix.com/projects/ZBX/repos/zabbix/browse/templates/os/windows_agent?at=refs%2Fheads%2Frelease%2F7.0)):

| Layer | Covered? |
|---|---|
| CPU / memory / disk / NIC / agent | yes |
| Automatic service **state** (`NTDS`, `Kdc`, `Netlogon`, `DNS`, `DFSR`, `W32Time`, …) | yes — `service.discovery` |
| LDAP / DRA / ATQ / SAM **counters** | **no** |
| Replication backlog, bind time, LDAP sessions | **no** |
| `dcdiag`, FSMO, SYSVOL, NTDS.dit size | **no** |
| Directory Service / DFSR event logs | **no** |

`templates/app` on **release/7.0** has IIS, Exchange, SharePoint — **no** Active Directory / NTDS. Same on master as of this note.

LogicMonitor `CORP-UPA-Dom_Monitor` was a **WMI credential override** on DCs. Transport is replaced by the agent. That is **not** LM datasource parity for Directory Services.

DCs are **not** [06](../06-network-vms.md) (06 is NetBox / Zabbix / XIQ-SE / jump / collectors). They are the server estate. Overlap with whoever owns servers before linking anything fleet-wide.

---

## Do not import these as-is

| Source | Why not |
|---|---|
| windows_exporter + HTTP scrape | Second agent on every DC; we already have Zabbix agent |
| [community `template_ad_ds_health_and_performance` 5.4](https://github.com/zabbix/community-templates/tree/main/Operating_Systems/Windows/template_ad_ds_health_and_performance/5.4) | Numeric `perf_counter[\6956\…]` IDs (break across Windows builds); **no triggers**; duplicates `service.info` keys stock already owns |
| [ffurlanetti ADDS Health](https://github.com/ffurlanetti/Zabbix-Microsoft-Active-Directory-Health-Template) | 7.0-capable but UserParameters + PowerShell + GPO audit — too heavy for this bar |
| Clone **Windows by Zabbix agent** | Principle 7 — macros / companion, not a fork |

Useful *ideas* from the 5.4 community set (English names, not IDs): LDAP Client Sessions, LDAP Searches/sec, LDAP Writes/sec, LDAP Bind Time, DRA Pending Replication Synchronizations, DRA Inbound Object Updates Remaining in Packet, DRA inbound/outbound bytes. Kerberos/NTLM auths are **Security System-Wide Statistics**, not `collector.ad`.

---

## If we build: companion **AD DS Observability**

Same pattern as [MSSQL Observability](mssql-agent2-instances.md): sit **next to** Windows by agent, unique keys, role **Domain Controller** only after a canary import.

Data path: Zabbix agent `perf_counter_en["\NTDS\<English counter>"]`. Confirm the object is `NTDS` on a live DC (not `DirectoryServices`) before import. Items that `CHECK_NOT_SUPPORTED` on a non-DC must not exist — that is why this is a **role** template, not a Windows overlay.

### Page / ticket (symptoms)

| Thing | windows_exporter | NTDS counter | Alert | Sev |
|---|---|---|---|---|
| DRA pending replication synchronizations | `windows_ad_replication_pending_synchronizations` | `DRA Pending Replication Synchronizations` | yes after baseline | Average |
| ATQ estimated queue delay | `windows_ad_atq_estimated_delay_seconds` | `ATQ Estimated Queue Delay` | yes after baseline | Warning |
| LDAP last bind time | `windows_ad_ldap_last_bind_time_seconds` | `LDAP Bind Time` | yes after baseline | Warning |
| NTDS / KDC / Netlogon not running | (exporter `service`) | — | **already** stock `service.info` | Average |

LDAP 389/636 as `net.tcp.service` is optional. Stock already pages the **host** (ICMP) and the **NTDS service**. Do not also page “LDAP port down” unless the service check is a false green.

### Graph only (causes)

LDAP Client Sessions, LDAP Searches/sec, LDAP Writes/sec, LDAP Active Threads, ATQ outstanding requests, DRA inbound/outbound bytes, DRA inbound objects remaining. Plus Kerberos/NTLM authentications/sec from `\Security System-Wide Statistics\` if we want auth *rate* (not in `collector.ad`).

### Skip (exporter noise)

Address book, SAM computer/user creation, phantom/tombstone walkers, name-cache hits, security-descriptor propagation, approximate highest DN tag — unless a ticket later names them.

Do **not** re-add `service.info[NTDS|Kdc|DNS|DFSR|…]` on the companion (key collision with stock).

**Collect first.** Every AD trigger **DISABLED** until one DC has a quiet week. Macros for thresholds, not cloned templates.

Zerotouch: **soft-assign** on role Domain Controller only after YAML is imported (same as MSSQL Observability). Do not HostSync the DC fleet from a docs-only change.

---

## Cutover

Not a switch/AP cutover item. [logicmonitor-assessment.md](../logicmonitor-assessment.md) previously marked DCs ✅ because the **agent replaced WMI**. That remains true for OS. AD DS counters are a **post-cutover gap**.
