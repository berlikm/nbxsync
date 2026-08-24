#!/usr/bin/env python3
"""FortiGate HTTP contract macros (no Django, no Zabbix).

``{$FGATE.API.TOKEN}`` and ``{$FGATE.API.FQDN}`` stay **per device** (that
unit's HA mgmt IP / token, Pure pattern). Empty env must not wipe them.

Fleet defaults belong on Device Role **Firewall** — the same ZabbixMacroAssignment
lever Switch Access uses for IFALIAS. Do not put these on Switch* roles or as
Zabbix globals (CPU/disk macros would hit servers). Do not MATCH ``port``:
on a 40F/100F ``port1`` is usually LAN.
"""

from __future__ import annotations

FIREWALL_ROLE = 'Firewall'

# HostSync of a Firewall inherits these. --apply does **not** write them onto
# live Zabbix hosts (SNMP FortiGate uses {$NET.IF.IFNAME.MATCHES} too).
FIREWALL_ROLE_MACROS = {
    '{$FGATE.SCHEME}': 'https',
    '{$FGATE.API.PORT}': '443',
    '{$NET.IF.IFNAME.MATCHES}': '^(wan|ha|mgmt|dmz)',
    '{$NET.IF.IFNAME.NOT_MATCHES}': r'^(ssl\.|npu|fortilink|loopback|vlan)',
    '{$FWP.FWNAME.MATCHES}': '^$',
    '{$NET.IF.UTIL.MAX}': '101',
    '{$FIRMWARE.UPDATES.CONTROL}': '0',
    '{$DISK.FREE.CRIT}': '0',
}

FIREWALL_DEVICE_MACROS = (
    '{$FGATE.API.TOKEN}',
    '{$FGATE.API.FQDN}',
)
