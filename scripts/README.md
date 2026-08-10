# Lab / configure scripts

These helpers apply the same policy as
[`docs/nbxsync-configuration-checklist-zerotouch.md`](../docs/nbxsync-configuration-checklist-zerotouch.md).
**The checklist is the operator source of truth.** Run scripts in order; do not treat them as a second design doc.

| Order | Script | Covers checklist |
|---|---|---|
| 1 | `configure_nbxsync_zerotouch.py` | §§1–12 fleet (server, proxies, CGs + SNMPv3 profiles, Template Rules, hostgroups, tags, inventory, app secrets) |
| 2 | `configure_nbxsync_network.py` | Extreme half: VOSS/IQ/Speed Expect imports, Switch* IFALIAS (§11.1), §11.2 globals, stock EXOS LLD + TEMP_* patches |
| — | `create_dashboards.py` | Zabbix dashboards from nested `Sites/*` / `Roles/*` / `OS/*` parents |
| — | `setup_zabbix.sh` | Podman Zabbix 7 lab bootstrap (+ optional configure/sync) |
| — | `run_network_zabbix_sim.py` | Zabbix-API-only smoke (no NetBox graph) |
| — | `zabbix_api.py` | Shared JSON-RPC helper for the Zabbix-only smoke |

## Quick start (lab)

```bash
cp scripts/setup_zabbix.env.example scripts/setup_zabbix.env
# edit: NBX_ZABBIX_URL, NBX_SNMP_* / NBX_VMWARE_* / NBX_PURE_* / NBX_MSSQL_* as needed

./scripts/setup_zabbix.sh   # optional — brings up local Zabbix

PYTHONPATH=/workspace/.deps/netbox/netbox:/workspace \
  /workspace/.deps/venv/bin/python scripts/configure_nbxsync_zerotouch.py --simulate

PYTHONPATH=/workspace/.deps/netbox/netbox:/workspace \
  /workspace/.deps/venv/bin/python scripts/configure_nbxsync_network.py --simulate
```

Reports land under `/opt/cursor/artifacts/` (`ZEROTOUCH_*`, `NETWORK_*`).

## Production apply

```bash
export NBX_ZABBIX_TOKEN=...
# SNMP / app secrets — see setup_zabbix.env.example and checklist §5 / §11.4
python scripts/configure_nbxsync_zerotouch.py
python scripts/configure_nbxsync_network.py --apply

# Optional during LogicMonitor cutover noise only (not the end state):
python scripts/configure_nbxsync_network.py --apply --cutover-silence

# Stage 4 — link Port Speed Expect on Switch* roles:
python scripts/configure_nbxsync_network.py --apply --link-speed-expect
```

Read-only coverage census:

```bash
python scripts/configure_nbxsync_zerotouch.py --verify
```

## Who owns which rows

| Concern | Zerotouch | Network |
|---|---|---|
| Country SiteGroup Agent default | yes | assumes present |
| SNMP Monitoring on Switch* (incl. Hybrid) | yes | assumes present |
| Linux/SAP SNMP CGs on tags `snmp` / `snmp-sap` | yes | — |
| Server Agent+OOB / SPACE :10060 / OOB SNMP Only | yes | — |
| Extreme TemplateRules (EXOS/VOSS/IQ) | yes (also ensured) | yes |
| Switch* IFALIAS / IFTYPE macros | — | yes |
| Stock EXOS EtherLike IFALIAS + IF LLD 15m + TEMP_* | — | yes |
| §11.2 destination globals | — | yes |

## Related docs

- Operator checklist: `docs/nbxsync-configuration-checklist-zerotouch.md`
- Cutover order / Extreme stages: `zabbix/00-monitoring-plan.md`, `zabbix/01-extreme-switching.md`
- Port labels: `zabbix/port-identity.md`
- LM credential map: `zabbix/logicmonitor-assessment.md`
