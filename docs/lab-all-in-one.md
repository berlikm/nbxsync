# Lab tip: `cursor/all-in-one-e7f8`

Single branch for local/dev testing. It is **not** an upstream merge vehicle.

## Contents
- Full restacked product tip (`feature/oob-ip-support` / upstream PR stack through `#129`)
- CI triggers for `development` (from `#122`) plus this lab branch
- Lab-only helpers: zero-touch configure script and checklists

## Not included (keep separate if needed)
- Extreme VOSS/EXOS Zabbix template work (`cursor/extreme-voss-snmp-template-e7f8`)
- Upstream PR tips themselves (still required while those PRs are open)

## Fresh lab DB
Migration numbers follow the upstream stack order. Prefer a fresh NetBox DB / plugin migrate when leaving `integration-test`.
