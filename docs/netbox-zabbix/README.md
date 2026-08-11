# NetBox ↔ Zabbix (nbxSync) — Sensirion

**This folder is the integration set.** It configures how existing NetBox inventory becomes Zabbix hosts via nbxSync.

It is **not** the upstream nbxSync product manual (that stays under [`../`](../index.md) — Installation, Models, …) and **not** the monitoring-domain packs ([`../../zabbix/`](../../zabbix/README.md)).

## What belongs where

| Layer | Owns | Home |
|---|---|---|
| **NetBox inventory** | Sites, roles, platforms, IPs, tags | Assumed already populated — not documented here |
| **Integration (this folder)** | Servers, proxies, CGs, Template Rules, hostgroups, macros, sync lifecycle | `architecture` → `configuration` → `runbooks/` |
| **Monitoring domain** | What to poll, port grammar, stages, templates content | [`zabbix/`](../../zabbix/README.md) |
| **First-build accelerator** | Optional scripts that apply the configuration once | [`scripts/README.md`](../../scripts/README.md) |

## Documents

| Doc | Role | When you open it |
|---|---|---|
| [`architecture.md`](architecture.md) | Mental model — layers, control plane, rules of thumb | First read / design discussion |
| [`configuration.md`](configuration.md) | Authoritative nbxSync GUI/API rows + host matrix + verify | Building or changing policy |
| [`runbooks/day2.md`](runbooks/day2.md) | Operator procedures after go-live | New role/platform, broken host, recurring checks |
| [`runbooks/onboarding.md`](runbooks/onboarding.md) | Phased cutover — exclude most, enable one-by-one | Agent not ready / wave enablement |

One fact has **one home**. Link across tracks; do not copy tables.

## Reader path

```
understand  →  architecture.md
build       →  configuration.md  (§§1–13, then verify)
onboard     →  runbooks/onboarding.md   (exclude fleet, open hosts one-by-one)
operate     →  runbooks/day2.md
signals     →  ../../zabbix/   (Extreme, Forti, …)
speed-run   →  ../../scripts/README.md   (optional, first build only)
```

## Assumptions

- NetBox already has country Site Groups, sites, roles, platforms, primary IP / `oob_ip`, and tags used by the configuration.
- Day-to-day changes are GUI or API. Scripts are onboarding only.
- Alerting, media, dashboards, and signal design live under `zabbix/`, not here.
