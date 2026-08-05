# Extreme Routing by SNMP

Zabbix **7.0** template for OSPF adjacency health (OSPF-MIB). Platform-neutral ΓÇö link on **Core / Dist** device roles alongside Extreme EXOS or Extreme VOSS by SNMP.

Design: `docs/extreme-switching-zabbix.md` ┬ºC.

## Alerting model

| Item | Alerts? |
|---|---|
| `ospf.nbr.full.count` ΓÇö count of neighbours in state **full (8)** | **yes** |
| Per-neighbour LLD (state / IP / router ID) | **no** ΓÇö diagnosis only |

Per-neighbour LLD cannot detect a missing neighbour (item disappears ΓåÆ trigger clears). Count is the alert.

## Macros

| Macro | Default | Meaning |
|---|---|---|
| `{$OSPF.NBR.MIN}` | `1` | Minimum full adjacencies; **set per device** from topology |
| `{$OSPF.ENABLED}` | `1` | Expected `ospfAdminStat` (enabled) |

## Canary first

Confirm `ospfNbrTable` populates on the target EXOS/VOSS versions before enabling triggers ΓÇö unsupported items fail silently.

## Dependencies

OSPF triggers ΓåÆ depend on ΓåÆ no SNMP / ICMP unavailable (platform template). **Not** dependent on link-down (protocol-only failures are the point).
