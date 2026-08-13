# Onboarding scripts (optional)

**Day-to-day operations use the NetBox GUI or API.** These scripts accelerate a **first build** (or a rare full re-apply).

Policy (what we set) lives under [`docs/netbox-zabbix/README.md`](../docs/netbox-zabbix/README.md) — one article per nbxSync object, same order as zerotouch.

If a script and those articles disagree, **fix the script or the article so they match**. The articles are what people read.

| Order | Script | Applies |
|---|---|---|
| 1 | `configure_nbxsync_zerotouch.py` | Objects 01–09 (server through macros). Sets proxy `tls_accept=Certificate` only — not proxy PEM / Cloud portal TLS. |
| 2 | `configure_nbxsync_network.py` | Extreme YAML import, Switch* IFALIAS, destination globals, stock EXOS LLD + TEMP_* patches |
| — | `create_dashboards.py` | Zabbix dashboards from nested hostgroups |
| — | `setup_zabbix.sh` | Podman Zabbix 7 lab bootstrap |
| — | `run_network_zabbix_sim.py` | Zabbix-API-only smoke (no NetBox) |
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

Always finish with the network script so VOSS / IQ Engine Template Rules are not left on Network Generic.

Optional: `--verify` (census), `--link-speed-expect` (Extreme stage 4), `--cutover-silence` (temporary LM overlay).

## Who writes which rows

| Concern | Zerotouch | Network |
|---|---|---|
| Country SiteGroup Agent default | yes | assumes present |
| SNMP Monitoring on Switch* (incl. Hybrid) | yes | assumes present |
| Linux SNMP CG on tag `snmp`; SAP CG on SAP HANA / SAP ME | yes | — |
| Dell iDRAC SNMPv3 / SPACE :10060 | yes | — |
| Extreme TemplateRules (EXOS/VOSS/IQ) | placeholder / ensure | import + retarget |
| Switch* IFALIAS / IFTYPE macros | — | yes |
| Stock EXOS EtherLike IFALIAS + IF LLD 15m + TEMP_* | — | yes |
| Extreme destination globals | — | yes |
