# Extreme Port Speed Expect by SNMP

Thin Zabbix **7.0** template: absolute speed expectation, sustained utilisation, and outbound discards for ports labelled `USW` / `US` / `UP` / `MON`.

Design: `docs/extreme-switching-zabbix.md` §A.5 / §A.6.4.

## Link with

| Platform | Also link |
|---|---|
| EXOS | `Extreme EXOS by SNMP` (release/7.0) |
| VOSS | `Extreme VOSS by SNMP` |

Assigned on **both platforms** (not per role). Role scoping for the *stock* interface LLD stays on `{$NET.IF.*}` macros from nbxsync. This template uses its **own** filter macros so the two LLDs can differ.

## Macros (template defaults)

```
{$PORTID.LLD.IFALIAS.MATCHES} = ^(USW|US|UP|MON)(-|$)
{$PORTID.LLD.IFTYPE.MATCHES}  = ^6$
{$IF.UTIL.MAX}                = 101          # off until stage 6
{$IF.UTIL.MAX:"USW"}          = 80           # enable when history exists
{$IF.DISCARDS.WARN}           = 1
```

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

Design prefers **dependent items** on platform-template masters (`net.if.speed[…]`, etc.) to avoid extra SNMP. Zabbix template YAML cannot reliably declare cross-template masters for a platform-neutral template, so this scaffold uses uniquely keyed SNMP prototypes. Swap to dependents at host/template-link time once proven — same keys for triggers can stay.

## Rollout

Enable triggers at **stage 4** (speed-expect) and **stage 6** (discards, then util). Keep `{$IF.UTIL.MAX}=101` until thresholds are baselined.
