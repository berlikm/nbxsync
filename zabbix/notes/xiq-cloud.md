# ExtremeCloud IQ tenant — analysis

Operator page: [08-extremecloud-iq.md](../08-extremecloud-iq.md).  
**Do not** treat this as a second policy. YAML lives in [`templates/extremecloud_iq_http/`](../templates/extremecloud_iq_http/).

---

## Decision

Watch the **VIQ** (cloud tenant) as a companion template on the **same Site Engine host** so Portal seats and SE used seats sit in one Latest data. Keep the Cloud REST client out of [XIQ-SE Observability](../07-extreme-control.md).

Do **not**: a Cato-style extra host while there is one SE + one CUID; `GET /devices` LLD; replay the Cloud alert inbox; mutations (`/:backup`, `/:reset`, `/:unmanage`); ICMP to SaaS; `Portal total − SE used`.

---

## Why not one SCRIPT

| | Site Engine NBI | Cloud IQ |
|---|---|---|
| Base | `https://{$XIQSE.API.FQDN}:8443` | `https://api.extremecloudiq.com` |
| Auth | OAuth client-credentials (SE Client API Access) | Bearer API token (`POST /auth/apitoken`) |
| Inventory | This SE’s devices / 24h MACs | CUID pool, all Connected-mode SEs |
| Failure | SE upgrade, 8443, token | Extreme SaaS, egress, Portal unlink |

One NBI error payload already unsported heap dependents. Mixing a second HTTP client into `collect_health.js` would couple Cloud outages to SE health JSON. Two masters on one host is the FortiGate HTTP + ICMP pattern, not two products in one JS file.

---

## What the instance actually is

There is no Cloud IQ CPU/heap. Tenant health is:

1. API answers (`GET /account/viq` or `/account/vhm/status`)
2. VHM `current_status=ACTIVE_STATUS`
3. VIQ `expired=false`
4. Last `backup_units=CONFIG` row on `GET /backup/history/grid` is fresh
5. Token `expire_time` not imminent (`GET /auth/apitoken/info`)
6. License rows present (`licenses:r`)

That is FortiManager-shaped (management plane), not FortiGate-shaped (the box).

Connected mode: ExtremeCloud IQ holds the subscription pool; Site Engines onboard into it. Air-gap SE stores licenses locally and would not use this template.

---

## API (query only)

Docs: [API reference](https://extremecloudiq.com/api-docs/api-reference.html). OpenAPI: `https://api.extremecloudiq.com/openapi`.

| Call | Why |
|---|---|
| `GET /account/viq` | `customer_id`, `expired`, `licenses[]` (`devices`, `activated`, `available`, `expire_date`, `license_type`, `status`) |
| `GET /account/vhm/status` | `current_status` |
| `GET /backup/history/grid?page=1&limit=10` | newest `backup_date` (epoch ms), `backup_units`, `backup_file_name` |
| `GET /auth/apitoken/info` | token TTL |
| `GET /devices/stats` | `total_device_count`, `managed_device_count`, `connected_device_count` |

`licenses[].entitlement_type` is EVALUATION / PERMANENT / RENEW — **not** the SKU. SKU-ish string is `license_type` (Gemalto). Canary before LLD keys.

NAC (`XIQ-NAC-S` 3000) may be absent from `licenses[]`. Platform ONE has `GET /nac-entitlements/stats` on `https://cloudapi.extremecloudiq.com/subscription/v1`. Do not guess.

Rate-limit header is present. Few masters, 5–15m, same as Cato: do not add polls on 429.

---

## Live numbers (why remaining must not cross inventories)

Extreme Portal CUID vs `ch-sta-p-ensa01` NBI:

| Pool | Portal | SE NBI used |
|---|---|---|
| Pilot `XIQ-PIL-S-C` | 581 total, 578 used, 3 avail | **320** `XIQ_PILOT` in SE `network.devices` only (switches + engines). APs are not on that NBI list — Cloud 578 is consume |
| NAC `XIQ-NAC-S` | 3000 | 24h unique MACs (this is the real NAC used) |

578 vs 320 is **APs (and other Cloud-onboarded devices)** vs this SE’s switch/engine inventory. `581 − 320 = 261` is not the 3 seats Portal shows. Pilot remaining is Cloud `available`.

---

## Explicitly out of v1 YAML

| Item | Why |
|---|---|
| Per-device Cloud host / LLD | 01/02 |
| Cloud alert API | alert-on-alert |
| Mutations | blast radius |
| Locations / floor plans / clients | not tenant health |
| Copilot / HIQ | later |
| Filling 07 `{$XIQ.*.TOTAL}` from Cloud | only after SKU map is proven |
