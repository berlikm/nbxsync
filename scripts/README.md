# Lab / configure scripts

Aligned with the zero-touch model on `cursor/zerotouch-configure-script-e7f8`.

| Script | Purpose |
|---|---|
| `configure_nbxsync_zerotouch.py` | General zero-touch: SiteGroup Agent, SNMP roles, TemplateRules, hostgroups, SyncHostJob lab |
| `configure_nbxsync_network.py` | **Network half** — Extreme VOSS/EXOS templates, Switch* IFALIAS macros, VOSS≠Network Generic |
| `run_network_zabbix_sim.py` | Zabbix-API-only smoke (no NetBox graph) |
| `zabbix_api.py` | Shared JSON-RPC helper for the Zabbix-only smoke |

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
