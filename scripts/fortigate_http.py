#!/usr/bin/env python3
"""FortiGate HTTP contract macros (no Django, no Zabbix).

``{$FGATE.API.TOKEN}`` and ``{$FGATE.API.FQDN}`` stay **per device** (that
unit's HA mgmt IP / token, Pure pattern). Empty env must not wipe them.
Look at the Device, not Device Role Firewall — the role never carries secrets.

Fleet defaults belong on Device Role **Firewall** — the same ZabbixMacroAssignment
lever Switch Access uses for IFALIAS. Do not put these on Switch* roles or as
Zabbix globals (CPU/disk macros would hit servers). Do not MATCH ``port``:
on a 40F/100F ``port1`` is usually LAN.

Live cutover is ``configure_nbxsync_network.py --apply-fortigate-http``.
Do not re-run zerotouch for that — zerotouch still floors FortiOS on
FortiGate by SNMP.
"""

from __future__ import annotations

FIREWALL_ROLE = 'Firewall'
FORTIGATE_HTTP_TEMPLATE = 'FortiGate by HTTP'
FORTIGATE_SNMP_TEMPLATE = 'FortiGate by SNMP'
ICMP_PING_TEMPLATE = 'ICMP Ping'
SNMP_MONITORING_CG = 'SNMP Monitoring'
FORTIOS_TEMPLATE_RULE = 'FortiOS'
FORTIOS_PLATFORM_PATTERN = r'FORTIOS|FortiOS'

# HostSync of a Firewall inherits the role macros onto the HTTP template LLD.
# Do not mass-HostSync until FortiOS is on HTTP and each unit has a token.
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

FGATE_TOKEN_MACRO, FGATE_FQDN_MACRO = FIREWALL_DEVICE_MACROS


def fgate_token_env(hostname: str) -> str:
    """Env key for a FortiGate REST token. Same shape as ``NBX_PURE_TOKEN_*``."""
    return f'NBX_FGATE_TOKEN_{hostname.upper().replace("-", "_")}'


def should_write_secret(value: str | None) -> bool:
    """Empty / whitespace env must not wipe an existing token assignment."""
    return bool((value or '').strip())
