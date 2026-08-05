# Extreme Routing by SNMP

Zabbix **7.0** template for OSPF adjacency health (OSPF-MIB). Platform-neutral — link on **Core / Dist** device roles alongside Extreme EXOS or Extreme VOSS by SNMP.

Design: `docs/extreme-switching-zabbix.md` §C.

## Alerting model

| Item | Alerts? |
|---|---|
| `ospf.nbr.full.count` — count of neighbours in state **full (8)** | **yes** |
| Per-neighbour LLD (state / IP / router ID) | **no** — diagnosis only |

Per-neighbour LLD cannot detect a missing neighbour (item disappears → trigger clears). Count is the alert.

## Macros

| Macro | Default | Meaning |
|---|---|---|
| `{$OSPF.NBR.MIN}` | `1` | Minimum full adjacencies; **set per device** from topology |
| `{$OSPF.ENABLED}` | `1` | Expected `ospfAdminStat` (enabled) |

## Canary first

Confirm `ospfNbrTable` populates on the target EXOS/VOSS versions before enabling triggers — unsupported items fail silently.

## Dependencies

OSPF triggers → depend on → no SNMP / ICMP unavailable (platform template). **Not** dependent on link-down (protocol-only failures are the point).
