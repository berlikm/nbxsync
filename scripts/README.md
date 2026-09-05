# Onboarding scripts (optional)

**Day-to-day operations use the NetBox GUI or API.** These scripts accelerate a **first build** (or a rare full re-apply).

Policy (what we set) lives in [`docs/netbox-zabbix/configuration.md`](../docs/netbox-zabbix/configuration.md) — one document, GUI click order.

If a script and that document disagree, **fix the script or the document so they match**.

| Order | Script | Applies |
|---|---|---|
| 1 | `configure_nbxsync_zerotouch.py` | Configuration §§1–11. Sets proxy `tls_accept=Certificate` only — not proxy PEM / Cloud portal TLS. |
| 2 | `configure_nbxsync_network.py` | Extreme YAML import, companion EXOS Observability, Switch* IFALIAS, Access host `{$LINKDOWN.IFALIAS}` grammar gate, destination globals, stock EXOS LLD + TEMP_* + ICMP-noise + interface grid + PSU check-now cleanup. `--apply-firewall-macros` writes **Platform FortiOS** FortiGate HTTP defaults (Jinja `{$FGATE.API.FQDN}` on `primary_ip4`, not role Firewall). `--apply-fortigate-http` is the Forti HTTP cutover (FortiOS Observability companion, prune Forti leftovers **and SNMP Monitoring** from role Firewall, keep SNMP Monitoring on FMG/FAZ **platforms**) — **do not re-run zerotouch** for that. `--apply-fmg-faz` / `--check-fmg-faz` import **Fortinet FMG-FAZ by SNMP** plus Observability companions, split FortiManager / FortiAnalyzer platform rules, and disable leftover Network Generic — **do not re-run zerotouch** for that. `--apply-cato` / `--check-cato` refresh the Cato account collector (GraphQL preflight, import **Cato Networks by HTTP**, converge `cato-account-*`) — **do not re-run zerotouch** for that. `--apply-xiqse` / `--check-xiqse` import **XIQ-SE Observability**, **ExtremeControl Observability**, and **ExtremeControl by SNMP**, soft Site Engine TemplateRule, role **NAC** (ANY + SNMP) — **do not re-run zerotouch** for that. `--apply-sap` / `--check-sap` import **SAP template from Sensirion**, assign on SAP HANA / SAP ME, and HostSync only `CH-STA-P-SH01` if present and not onboarding — **do not re-run zerotouch** for that. |
| — | `create_dashboards.py` | Country/role hostgroup boards — **not** part of `--apply`; host **Health** and **Network interfaces** ship from platform templates/runtime patch |
| — | `setup_zabbix.sh` | Podman Zabbix 7 lab bootstrap |
| — | `run_network_zabbix_sim.py` | Zabbix-API-only smoke (no NetBox) |
| — | `validate_extreme_templates.py` | YAML contract + optional `--zabbix` double-import |
| — | `test_mssql_observability.py` | MSSQL Observability named-instance LLD, host-prototype YAML contract, and database/backup-inventory fixtures (no live SQL) |
| — | `test_xiqse_observability.py` | XIQ-SE / ExtremeControl Observability: 24h unique MAC license count, engine LLD, YAML contract (no live NBI) |
| — | `test_extremecontrol_snmp.py` | ExtremeControl by SNMP: live ENAC canary counters, ENTERASYS-NAC-APPLIANCE-MIB OIDs, YAML contract |
| — | `test_sap_sensirion.py` | SAP HANA + SAP ME templates: openSUSE UCD vs Windows jstart (no live sapcontrol / SNMP) |
| — | `test_sap_sensirion_control.py` | sapcontrol collector fixtures (HANA / ABAP / Java / CCMS / SOAP; no live Host Agent) |
| — | `zabbix_api.py` | Shared JSON-RPC helper |
| — | `configure_cato_zabbix.py` | Zabbix-API implementation for the Cato collector (lab `--simulate`, used by `--apply-cato`). Never manages NetBox Socket hosts |

## Lab first build

```bash
cp scripts/setup_zabbix.env.example scripts/setup_zabbix.env
# edit: NBX_ZABBIX_URL, SNMP / VMware / Pure / MSSQL secrets as needed

./scripts/setup_zabbix.sh   # optional local Zabbix

PYTHONPATH=/workspace/.deps/netbox/netbox:/workspace \
  /workspace/.deps/venv/bin/python scripts/configure_nbxsync_zerotouch.py --simulate

PYTHONPATH=/workspace/.deps/netbox/netbox:/workspace \
  /workspace/.deps/venv/bin/python scripts/configure_nbxsync_network.py --simulate
```

Reports: `/opt/cursor/artifacts/` (`ZEROTOUCH_*`, `NETWORK_*`).

## Production first build

```bash
export NBX_ZABBIX_TOKEN=...
python scripts/configure_nbxsync_zerotouch.py
python scripts/configure_nbxsync_network.py --apply
```

Always finish with the network script so VOSS / IQ Engine Template Rules are not left unresolved. Re-running both scripts on an estate that **already has** switches and APs in Zabbix is the maintenance path: YAML `deleteMissing: false`, no host delete, no mass `SyncHostJob`. Template Health dashboards and trigger status inherit in Zabbix without touching hostids.

FortiGate HTTP cutover is **not** zerotouch and **not** Extreme `--apply`. Zabbix Cloud already has **FortiGate by HTTP** vendor **Zabbix, 7.0-2**. The flag never imports 7.0-3; it applies bounded ZBX-27082 and multi-VDOM interface/SD-WAN compatibility fixes to that parent, imports companion **FortiGate Observability** with VDOM-aware traffic navigators, and retargets **FortiOS only**. Before any write it requires HTTP 200 JSON from every FortiOS `primary_ip4` using NetBox automation’s `NBX_FORTIGATE_TOKEN` and separately verifies the nbxSync monitoring token. Apply intersects enabled+cabled NetBox interfaces with FortiOS-observable CMDB names for each device, sets the exact configured SD-WAN…

```bash
# NBX_FORTIGATE_TOKEN is already the NetBox inventory automation credential.
# Set the separate Zabbix monitoring token in nbxSync on Platform FortiOS.
python3 scripts/configure_nbxsync_network.py --check-fortigate-http  # read-only
python3 scripts/configure_nbxsync_network.py --apply-fortigate-http
```

Then verify API 200 from the assigned Swiss proxies and HostSync **both members** of the first cluster. Confirm authoritative HA role/member count, zero VDOM checksum mismatches, NetBox-scoped interface discovery, populated SD-WAN LLD, and no unexpected unsupported items before expanding. Do not skip the backup, mass-HostSync the fleet, or rerun zerotouch.

## FortiManager / FortiAnalyzer SNMP pack

There is no official Zabbix template. Cutover is the network script, same
isolation as FortiGate HTTP: **do not re-run zerotouch**.

```bash
python3 scripts/configure_nbxsync_network.py --check-fmg-faz
python3 scripts/configure_nbxsync_network.py --apply-fmg-faz
```

That fail-closes on missing YAML / platforms / SNMP Monitoring, imports
**Fortinet FMG-FAZ by SNMP** plus both Observability companions, splits
platform Template Rules **FortiManager** / **FortiAnalyzer**, and disables
leftover **FortiAnalyzer/Manager** → Network Generic. No HostSync, no Extreme
import, no FortiOS retarget. Then HostSync the FMG/FAZ hosts. If zerotouch is
re-run by mistake, run `--apply-fmg-faz` again.

```bash
python3 scripts/validate_extreme_templates.py --zabbix   # lab: YAML contract + double import
```

## Cato collector refresh

The production account collector is live. Refresh it with the network script,
same pattern as FortiGate HTTP: **do not re-run zerotouch**.

```bash
export NBX_CATO_API_KEY=...
python3 scripts/configure_nbxsync_network.py --check-cato
python3 scripts/configure_nbxsync_network.py --apply-cato
```

That fail-closes on GraphQL preflight, imports `Cato Networks by HTTP`, and
converges `cato-account-964`. No HostSync, no Extreme import, no Socket role
change.

All 21 production `Sd Wan Socket` devices are live through the controlled
per-device onboarding model. The one-time role-to-onboarding migration is
complete; do **not** run it again merely to refresh the collector, because it
would re-hold the released Socket fleet.

```bash
# One-time migration reference only — do not use for a normal collector refresh.
python scripts/configure_nbxsync_zerotouch.py --enable-cato --mutate-netbox
```

`configure_cato_zabbix.py --simulate` requires `NBX_CATO_API_KEY` and a local
Zabbix lab. `--verify --require-sockets` validates the 21/21 Socket ICMP
identity census. The collector also tickets when CMA Socket LLD stays above
the count of `cato_socket`-tagged ICMP hosts (`{$CATO.NETBOX.SOCKET.CONTROL}`).


## XIQ-SE / ExtremeControl Observability

There is no official Zabbix template. Cutover is the network script:
**do not re-run zerotouch**.

```bash
python3 scripts/configure_nbxsync_network.py --check-xiqse
python3 scripts/configure_nbxsync_network.py --apply-xiqse
```

That fail-closes on missing YAML, stock Cloud Pilot items, credentials, or the
shared SNMP interface. It imports **XIQ-SE Observability**,
**ExtremeControl Observability**, and **ExtremeControl by SNMP**. The Site
Engine uses exact platform **ExtremeCloud IQ Site Engine**, receives its NBI
credentials and FQDN through platform inheritance, and keeps an address
interface only for inherited ICMP (no Linux agent checks). Role **NAC** gets
the no-interface companion plus the SNMP pack and shared SNMPv3 configuration;
the five Control engines retain only SNMP interfaces. Apply runs HostSync only
for those six VMs. It never imports the general Extreme pack or runs zerotouch.
If zerotouch is re-run by mistake, run `--apply-xiqse` again.
Tests: `python3 scripts/test_xiqse_observability.py` and
`python3 scripts/test_extremecontrol_snmp.py`.


## SAP template from Sensirion

LogicMonitor watched host SNMP (`SAPUSER` MD5/DES), Promonitor application
rows (ABAP, instance, IDoc, jobs, locks, qRFC in/out, RFC, spool, syslog,
tRFC, updates), SSL certificate expiry, and Port. There is no item-level LM
export. The SH01 walk proved Linux Net-SNMP only. Certificate is the Zabbix
agent (`web.certificate.get`), not a proxy script. Application rows are
local sapcontrol. HANA is openSUSE (Python UserParameter). ME is Windows
(PowerShell + `jstart.exe`). `--apply-sap` cannot push those files; see
[`zabbix/templates/sap_sensirion/SAPCONTROL.md`](../zabbix/templates/sap_sensirion/SAPCONTROL.md).

```bash
python3 scripts/configure_nbxsync_network.py --check-sap
python3 scripts/configure_nbxsync_network.py --apply-sap
```

That imports **SAP template from Sensirion** (HANA, SNMP req) and **SAP ME
from Sensirion** (Windows, AGENT req), assigns each on its role, and
HostSyncs only `CH-STA-P-SH01` when that
device exists and is not onboarding. It never imports the Extreme pack, never
runs zerotouch, and never fleet-syncs. Application triggers stay off until
`{$SAP.APP.CONTROL}=1` after the UserParameter works. Tests:
`python3 scripts/test_sap_sensirion.py` and
`python3 scripts/test_sap_sensirion_control.py`.


## Re-syncing a single host (testing)

To test a configuration change on **one host** without wiping all Zabbix Cloud hosts:

1. Re-run zerotouch (idempotent — updates NetBox plugin objects only):
   ```bash
   export NBX_ZABBIX_TOKEN=... (and all env vars)
   python scripts/configure_nbxsync_zerotouch.py
   ```

2. Force a re-sync of the specific host from NetBox → Zabbix Cloud:
   ```bash
   cd /opt/netbox/netbox
   sudo bash -c 'set -a; source /etc/netbox.env; set +a; \
     PYTHONPATH=. DJANGO_SETTINGS_MODULE=netbox.settings \
     /opt/netbox/venv/bin/python3 -c "
       import django; django.setup()
       from dcim.models import Device
       from nbxsync.jobs.synchost import SyncHostJob
       dev = Device.objects.filter(name__iexact=\"HOSTNAME\").first()
       SyncHostJob(instance=dev).run()
       print(\"Synced %s\" % dev.name)
     "'
   ```

The sync **overwrites** the existing Zabbix host in place — templates, interfaces,
macros, and tags are re-applied from the current NetBox configuration. No need to
delete and re-create the host. Use this for testing template/CG changes on one host.

**Do NOT delete all hosts from Zabbix Cloud for testing.** Only delete + re-sync
the specific host you are changing.

Optional: `--verify` (census), `--cutover-silence` (temporary LM overlay). Do **not** pass `--link-speed-expect` — Speed Expect already nests on VOSS / Observability; empty display-strings stay silent.

## Who writes which rows

| Concern | Zerotouch | Network |
|---|---|---|
| Country SiteGroup Agent default | yes | assumes present |
| SNMP Monitoring on Switch Core/Dist/Access/Mgmt + AP | yes | assumes present |
| Linux SNMP CG on tag `snmp`; SAP CG on SAP HANA / SAP ME | yes | — |
| Dell iDRAC SNMPv3 / SPACE :10060 | yes | — |
| Extreme TemplateRules (EXOS/VOSS/IQ) | ensure when template exists; **never** fall back to Network Generic. Patterns: `EXOS\|Switch Engine`, `VOSS\|Fabric Engine`, `IQ ENGINE\|IQEngine\|IQ-ENGINE` | import + retarget if a rule still points at Network Generic |
| Switch* IFALIAS / IFTYPE macros | — | yes |
| Firewall FortiGate HTTP fleet macros (https/20443, WAN/HA/mgmt LLD with `mgmt` link trigger context-disabled, CPU/mem CRIT 101, FQDN Jinja) | — | yes on **Platform FortiOS** (`--apply-firewall-macros` or `--apply`; no Forti HostSync). Not role Firewall. |
| FortiOS → FortiGate Observability (nests Cloud **Zabbix, 7.0-2**, never import 7.0-3), ZBX-27082 patch, prune Forti/ICMP **and SNMP Monitoring** from role Firewall, CG **FortiGate HTTP** on Platform FortiOS, SNMP Monitoring on FMG/FAZ platforms, Zabbix monitoring TOKEN + FQDN Jinja on Platform FortiOS | **do not re-run** (still SNMP on role Firewall) | `--apply-fortigate-http` (fail-closed preflight, no Extreme YAML, no HostSync) |
| Cato account collector (`Cato Networks by HTTP`, GraphQL preflight, `cato-account-*`) | **do not re-run** | `--apply-cato` / `--check-cato` (no HostSync, no Socket role mutation) |
| XIQ-SE / ExtremeControl Observability (GraphQL NBI, 24h unique MAC license, engine LLD; thin role NAC companion) | soft-assign ExtremeControl on role **NAC** if the template exists | `--apply-xiqse` / `--check-xiqse` (no HostSync, no Extreme import) |
| SAP HANA + SAP ME from Sensirion (openSUSE SNMP OS vs Windows agent) | soft-assign HANA / ME templates on the matching role; Linux rule excludes SAP HANA | `--apply-sap` / `--check-sap` (HostSync only `CH-STA-P-SH01` if present and not onboarding; no Extreme import) |
| Stock EXOS EtherLike IFALIAS + IF LLD 15m + TEMP_* + ICMP loss off + 3×2 interface grid; companion owns Health | — | yes |
| Extreme destination globals | — | yes |
