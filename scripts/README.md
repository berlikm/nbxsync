# Lab / configure scripts

| Script | Purpose |
|---|---|
| `run_network_zabbix_sim.py` | Import Extreme templates into Zabbix 7, apply design macros, create Core/Access VOSS pilots, verify cutover checklist |
| `configure_nbxsync_network.py` | Declarative network half of zero-touch (platforms, roles, macros). `--simulate` / `--zabbix-only` now; `--apply` when NetBox Django works |
| `zabbix_api.py` | Shared JSON-RPC helper (`/home/ubuntu/zabbix-docker/lab.json`) |

General (server/VM) zero-touch lives in artifacts / a separate `configure_nbxsync_zerotouch.py` — these scripts own **Extreme switching only**.

```bash
python3 scripts/run_network_zabbix_sim.py --with-speed-expect
python3 scripts/configure_nbxsync_network.py --simulate
python3 scripts/configure_nbxsync_network.py --plan-only   # JSON only
```
