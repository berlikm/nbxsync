# Lab / configure scripts

This branch carries the full zero-touch stack from
`cursor/zerotouch-configure-script-e7f8` plus the Extreme network half.

| Script | Purpose |
|---|---|
| `setup_zabbix.sh` | Podman Zabbix 7 lab bootstrap + optional nbxsync configure/sync |
| `setup_zabbix.env.example` | Lab inputs template (URLs, paths, SNMP passwords) → copy to `setup_zabbix.env` |
| `configure_nbxsync_zerotouch.py` | General zero-touch: SiteGroup Agent, SNMP roles, TemplateRules, hostgroups, SyncHostJob lab |
| `configure_nbxsync_network.py` | **Network half** — Extreme VOSS/EXOS templates, Switch* IFALIAS macros, VOSS≠Network Generic |
| `create_dashboards.py` | Zabbix country/role/OS dashboards from nested hostgroup parents |
| `run_network_zabbix_sim.py` | Zabbix-API-only smoke (no NetBox graph) |
| `zabbix_api.py` | Shared JSON-RPC helper for the Zabbix-only smoke |

## Zabbix lab (`setup_zabbix.sh`)

```bash
cp scripts/setup_zabbix.env.example scripts/setup_zabbix.env
# edit setup_zabbix.env — NBX_ZABBIX_URL, SNMP passwords, script paths
./scripts/setup_zabbix.sh
```

EXOS IF LLD (15m) and TEMP_* template macros are applied by `configure_nbxsync_network.py --apply` (safe full-macro merge). Do not patch those from the shell with a partial `template.update`.

Operator checklist: `docs/nbxsync-configuration-checklist-zerotouch.md`

## Network simulate (NetBox + Zabbix)

```bash
PYTHONPATH=/workspace/.deps/netbox/netbox:/workspace \
  /workspace/.deps/venv/bin/python scripts/configure_nbxsync_network.py --simulate

# Stage 4: also assign Port Speed Expect on Switch roles
PYTHONPATH=/workspace/.deps/netbox/netbox:/workspace \
  /workspace/.deps/venv/bin/python scripts/configure_nbxsync_network.py --simulate --link-speed-expect
```

Uses the same patterns as zerotouch: `ensure()`, prefixed lab estate (`nwn-`), `ZabbixTemplateRule`, `ZabbixMacroAssignment`, `SyncHostJob`, live asserts.

Reports: `/opt/cursor/artifacts/NETWORK_NBXSYNC_SIM_REPORT.md`

## Zero-touch (servers / VMs / OOB)

```bash
PYTHONPATH=/workspace/.deps/netbox/netbox:/workspace \
  /workspace/.deps/venv/bin/python scripts/configure_nbxsync_zerotouch.py --simulate
```

Network script assumes SNMP CG on Switch* (zerotouch step 5b) and only layers Extreme-specific templates + macros.

## Dashboards

```bash
PYTHONPATH=/workspace/.deps/netbox/netbox:/workspace \
  /workspace/.deps/venv/bin/python scripts/create_dashboards.py
```
