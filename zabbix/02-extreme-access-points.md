# Extreme access points

HiveOS / IQ Engine APs. One Zabbix host per AP (NetBox Device), not per XIQ tenant. The switch port toward the AP is `UP-…` in [01-extreme-switching.md](01-extreme-switching.md) — a cable cut pages on the switch, not twice.

NetBox: CG **SNMP Monitoring** on role Access Point; Template Rule `IQ ENGINE` → **Extreme IQ Engine by SNMP**. Checklist: [`docs/netbox-zabbix/configuration.md`](../docs/netbox-zabbix/configuration.md) §5b / §6.1. OID map: `templates/extreme_iq_engine_snmp/`.

---

## What we alert

| Thing | Alert | Sev |
|---|---|---|
| ICMP down | yes | High |
| SNMP dead (ICMP still up) | yes | High — usually means XIQ has not enabled SNMP on eth |
| CPU high | yes | Average — ops default 90 / 95; high CPU alone is not a fault |
| Memory high | yes | Average |
| Temperature | yes | Average — canary first; many APs stub the OID |
| Eth link down | yes | Warning — lower than switch `UP-` for the same cable |
| Client count | **no** | graph; optional soft warn later |
| Radio channel / Tx / noise | **no** | RF graphs |
| Radio retries / drops | **no** | graphs until baselined |
| Per-client association | **no** | later |
| Firmware / serial | **no** | inventory |

Do **not** alert on: two High pages for one cable cut (switch `UP-` + AP ICMP), mesh/MRP, XIQ cloud API, per-client RSSI, Network Generic (`icmpping` collision).

---

## Scope

| Object | In | Out |
|---|---|---|
| AP chassis | Every Access Point device | XIQ tenant as a host |
| Radios | Physical wifi (`ahIfType=0`; AP305C `wifi0` / `wifi1`) | VAP / SSID virtual ifaces |
| Ethernet | Physical eth / mgt | wifi IF-MIB rows |
| Clients | Scalar count only | Association table (later) |

---

## Ops

SNMP answers only if XIQ has **manage SNMP** on the AP wired interface (eth0, and eth1 if used), then a Delta update. Without that, the AP is up on the switch `UP-` port and Zabbix shows SNMP unavailable.

Prefer: AP unavailable **depends on** the matching switch port not down, once NetBox/LLDP mapping is reliable. Until then, different severities — not two High pages.

---

## Templates

| Template | Where |
|---|---|
| Extreme IQ Engine by SNMP | Platform matching `IQ ENGINE` |

Do **not** stack Network Generic. No role-level template floor on Access Point.

CPU / ICMP-loss macros are estate ops defaults (Extreme does not publish AP SNMP alert points). Chassis `{$TEMP_*}` on this template, not global.

---

## Later

Per-client LLD, HiveOS traps, XIQ REST, mesh/MRP, trigger dependency to switch `UP-`.
