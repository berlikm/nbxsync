# Onboarding scripts (optional)

**Day-to-day operations use the NetBox GUI or API.** These scripts accelerate a **first build** (or a rare full re-apply).

Policy (what we set) lives in [`docs/netbox-zabbix/configuration.md`](../docs/netbox-zabbix/configuration.md) — one document, GUI click order.

If a script and that document disagree, **fix the script or the document so they match**.

| Order | Script | Applies |
|---|---|---|
| 1 | `configure_nbxsync_zerotouch.py` | Configuration §§1–11. Sets proxy `tls_accept=Certificate` only — not proxy PEM / Cloud portal TLS. |
| 2 | `configure_nbxsync_network.py` | Extreme YAML import, companion EXOS Observability, Switch* IFALIAS, destination globals, stock EXOS LLD + TEMP_* + ICMP-noise + interface grid + PSU check-now cleanup |
| — | `create_dashboards.py` | Country/role hostgroup boards — **not** part of `--apply`; host **Health** and **Network interfaces** ship from platform templates/runtime patch |
| — | `setup_zabbix.sh` | Podman Zabbix 7 lab bootstrap |
| — | `run_network_zabbix_sim.py` | Zabbix-API-only smoke (no NetBox) |
| — | `validate_extreme_templates.py` | YAML contract + optional `--zabbix` double-import |
| — | `zabbix_api.py` | Shared JSON-RPC helper |

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

```bash
python3 scripts/validate_extreme_templates.py --zabbix   # lab: YAML contract + double import
```


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

Optional: `--verify` (census), `--cutover-silence` (temporary LM overlay). Do **not** pass `--link-speed-expect` until an `ifAlias` vs `ifHighSpeed` census is quiet.

## Who writes which rows

| Concern | Zerotouch | Network |
|---|---|---|
| Country SiteGroup Agent default | yes | assumes present |
| SNMP Monitoring on Switch Core/Dist/Access/Mgmt + AP | yes | assumes present |
| Linux SNMP CG on tag `snmp`; SAP CG on SAP HANA / SAP ME | yes | — |
| Dell iDRAC SNMPv3 / SPACE :10060 | yes | — |
| Extreme TemplateRules (EXOS/VOSS/IQ) | ensure when template exists; **never** fall back to Network Generic | import + retarget if a rule still points at Network Generic |
| Switch* IFALIAS / IFTYPE macros | — | yes |
| Stock EXOS EtherLike IFALIAS + IF LLD 15m + TEMP_* + ICMP loss off + 3×2 interface grid; companion owns Health | — | yes |
| Extreme destination globals | — | yes |
