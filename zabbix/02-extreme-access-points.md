# Extreme access points

HiveOS / IQ Engine APs. One Zabbix host per AP, not per XIQ tenant. Same observability bar as [01-extreme-switching.md](01-extreme-switching.md): page symptoms, never fail silent, **one** page per cable cut.

The switch port toward the AP is `UP-…`. OID map: `templates/extreme_iq_engine_snmp/`.

---

## Observability

| Rule | Here |
|---|---|
| Page symptoms | ICMP down, SNMP dead, eth down (Warning), CPU/mem after canary |
| Graph causes | Client count, radio noise/Tx, retries/drops, eth traffic |
| One incident | Cable/PoE → switch `UP-` **High**; AP ICMP depends on it. AP hung, eth still up → AP **High**. Until mapping exists: AP ICMP **Average** if we cannot tell |
| Never silent | Unsupported items; AP with zero radios discovered; SNMP down while `UP-` is up usually means XIQ **manage SNMP** was skipped |
| Collect first | Radio retry alerts and client-count warn stay off until a pilot |
| Severity | Same scale as [_template.md](_template.md). No Disaster on the AP template |

Do **not** stack Network Generic.

---

## What we alert

| Thing | Alert | Sev |
|---|---|---|
| ICMP down | yes | **High** — depends on switch `UP-` when we can |
| SNMP dead (ICMP still up) | yes | **Average** — usually XIQ SNMP not enabled |
| CPU high | yes | Warning — 90 / 95 ops default; high CPU alone is not a fault |
| Memory high | yes | Average |
| Temperature | yes | Average — canary; many APs stub the OID |
| Eth link down | yes | Warning — the plant page is switch `UP-` **High** |
| Client count | **no** | graph |
| Radio channel / Tx / noise | **no** | RF graphs |
| Radio retries / drops | **no** | graphs until baselined |
| Per-client association | **no** | later |
| Firmware / serial | **no** | inventory |

---

## Scope

| Object | In | Out |
|---|---|---|
| AP chassis | Every Access Point device | XIQ tenant as a host |
| Radios | Physical wifi (`ahIfType=0`; AP305C `wifi0` / `wifi1`) | VAP / SSID virtual ifaces |
| Ethernet | Physical eth / mgt | wifi IF-MIB rows |
| Clients | Scalar count only | Association table |

---

## Ops

XIQ must **manage SNMP** on eth0 (and eth1 if used), then Delta update. Without that, the AP is green on the switch and red in Zabbix.

AP `{$TEMP_*}` is **this** template, not the switch 95/100 internals.

---

## Watch the watcher

| Check | Why |
|---|---|
| Unsupported items | OID missing on this AP class |
| Zero radio LLD | filter too tight or SNMP empty |
| SNMP down + `UP-` up | XIQ prerequisite, not a cable |

---

## Templates

| Template | Where |
|---|---|
| Extreme IQ Engine by SNMP | Platform matching `IQ ENGINE` |

CG **SNMP Monitoring** on role Access Point. No role-level template floor.

```
{$CPU.UTIL.WARN}     = 90
{$CPU.UTIL.CRIT}     = 95
{$ICMP_LOSS_WARN}    = 10
{$TEMP_WARN}         = canary first
{$TEMP_CRIT}         = canary first
```

---

## Later

Trigger dependency to switch `UP-` via NetBox/LLDP; per-client LLD; traps; XIQ REST; mesh. FortiGate / VMs: same bar, different doc.
