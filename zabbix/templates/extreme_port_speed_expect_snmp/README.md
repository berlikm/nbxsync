# Extreme Port Speed Expect by SNMP

Thin Zabbix **7.0** template: absolute speed expectation from the on-box label, plus later util-%-of-intended and outbound discards for ports labelled `USW` / `US` / `UP` / `MON`.

Design: [01-extreme-switching.md](../../01-extreme-switching.md) (Intended speed). Own LLD macros (`{$PORTID.LLD.*}`) — do not reuse `{$NET.IF.IFALIAS.*}`.

## Link with

Nested by `--apply` (not a Switch-role assignment):

| Platform template | Nests |
|---|---|
| Extreme EXOS Observability | stock **Extreme EXOS by SNMP** + this template |
| Extreme VOSS by SNMP | this template |

Do **not** also assign this template on Switch roles while nested — HostSync then tries to link it twice. IQ does not nest it.

Role scoping for the *stock* interface LLD stays on `{$NET.IF.*}`. This template uses `{$PORTID.LLD.*}` so the two LLDs can differ. Empty / unclassed `ifAlias` fails the filter → no items.

## Macros (template defaults)

```
{$PORTID.LLD.IFALIAS.MATCHES} = ^(USW|US|UP|MON)(-|$)
{$PORTID.LLD.IFTYPE.MATCHES}  = ^6$
{$IF.UTIL.MAX}                = 101          # off until stage 6
{$IF.UTIL.MAX:"USW"}          = 101          # off until stage 6; set 80 after history
{$IF.DISCARDS.WARN}           = 1
```

## Triggers (YAML)

| Trigger | Status | Why |
|---|---|---|
| Speed ≠ expected Mbps, oper-up 5m | **on** (Warning) | the product; silent until a class label exists |
| Sustained util vs intended | on, but `{$IF.UTIL.MAX}=101` | unreachable until USW is set to 80 |
| Link down (speed-expect) | **DISABLED** | platform already Average-tickets discovered link-down |
| Outbound discards | **DISABLED** | 1 pps is not gated by util 101; need a baseline |

## Keys (no collision with stock)

| Kind | Key |
|---|---|
| LLD | `net.if.speedexpect.discovery` |
| Live speed (Mbps) | `net.if.speedexpect.speed[{#SNMPINDEX}]` |
| Oper status | `net.if.speedexpect.status[{#SNMPINDEX}]` |
| Bits in/out | `net.if.speedexpect.in/out[{#SNMPINDEX}]` |
| Out discards | `net.if.speedexpect.outdiscards[{#SNMPINDEX}]` |
| Util % in/out | `net.if.speedexpect.util.in/out[{#SNMPINDEX}]` |

LLD JS preprocessing emits `{#IF.CLASS}`, `{#IF.SPEED.EXPECTED}` (Mbps), `{#IF.UTIL.MULT}`.

## Polling note

Design prefers **dependent items** on platform-template masters (`net.if.speed[…]`, etc.) to avoid extra SNMP. Zabbix template YAML cannot reliably declare cross-template masters for a platform-neutral template, so this scaffold uses uniquely keyed SNMP prototypes. Swap to dependents at host/template-link time once proven — same keys for triggers can stay. Compare in **Mbps**; never `min(speed,5m)` (platform speed uses discard-unchanged heartbeat 1h).

## Rollout

`--apply` nests this on every EXOS/VOSS switch. Unlabeled ports stay silent. A proper `display-string` / VOSS `name` starts items within 15m. Wrong token (Pure labelled `US-…` at 25G) is a Warning — fix the label. Access assigns the same `{$PORTID.LLD.IFALIAS.MATCHES}` = `^(USW|US|UP|MON)(-|$)` on the role (stock LLD also includes `UW`/`TMON` via `{$NET.IF.IFALIAS.MATCHES}`).
