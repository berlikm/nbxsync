#!/usr/bin/env python3
"""FortiGate HTTP contract macros (no Django, no Zabbix).

``{$FGATE.API.TOKEN}`` is a **shared** secret on Device Role Firewall when
every unit uses the same REST key (``NBX_FGATE_TOKEN``). Empty env must not
wipe it. Optional per-device override: ``NBX_FGATE_TOKEN_<HOSTNAME>``.

``{$FGATE.API.FQDN}`` stays **per device** — that unit's OOB / ha-mgmt IP
(not a WAN VIP, not the role). Prefer ``oob_ip`` then ``primary_ip4``.

Fleet HTTP defaults (https/443, WAN/HA/mgmt LLD) also belong on Device Role
**Firewall**. Do not MATCH ``port``: on a 40F/100F ``port1`` is usually LAN.

Live cutover is ``configure_nbxsync_network.py --apply-fortigate-http``.
That **looks up** FortiGate by HTTP already in Zabbix Cloud (vendor
**Zabbix, 7.0-2**) and never imports YAML. Bundled 7.0-3 would
``updateExisting`` over 7.0-2. Do not re-run zerotouch.
"""

from __future__ import annotations

FIREWALL_ROLE = 'Firewall'
FORTIGATE_HTTP_TEMPLATE = 'FortiGate by HTTP'
# Confirmed live Zabbix Cloud template. Do not import bundled 7.0-3 over it.
FORTIGATE_HTTP_CLOUD_VENDOR_NAME = 'Zabbix'
FORTIGATE_HTTP_CLOUD_VENDOR_VERSION = '7.0-2'
FORTIGATE_HTTP_CLOUD_VENDOR = (
    f'{FORTIGATE_HTTP_CLOUD_VENDOR_NAME}, {FORTIGATE_HTTP_CLOUD_VENDOR_VERSION}'
)
FORTIGATE_SNMP_TEMPLATE = 'FortiGate by SNMP'
ICMP_PING_TEMPLATE = 'ICMP Ping'
SNMP_MONITORING_CG = 'SNMP Monitoring'
FORTIOS_TEMPLATE_RULE = 'FortiOS'
FORTIOS_PLATFORM_PATTERN = r'FORTIOS|FortiOS'

FGATE_TOKEN_MACRO = '{$FGATE.API.TOKEN}'
FGATE_FQDN_MACRO = '{$FGATE.API.FQDN}'
FGATE_TOKEN_ENV = 'NBX_FGATE_TOKEN'

# HostSync of a Firewall inherits the role macros onto the HTTP template LLD.
# Do not mass-HostSync until FortiOS is on HTTP and the role has a token.
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

# FQDN only — TOKEN is the shared role secret, not a per-device default.
FIREWALL_DEVICE_MACROS = (FGATE_FQDN_MACRO,)


def fgate_token_env(hostname: str) -> str:
    """Optional per-device override. Same shape as ``NBX_PURE_TOKEN_*``."""
    return f'NBX_FGATE_TOKEN_{hostname.upper().replace("-", "_")}'


def should_write_secret(value: str | None) -> bool:
    """Empty / whitespace env must not wipe an existing token assignment."""
    return bool((value or '').strip())


def preferred_mgmt_ip(oob_ip: str | None, primary_ip: str | None) -> str | None:
    """HA mgmt / OOB first so both cluster members are reachable; not a WAN VIP."""
    for ip in (oob_ip, primary_ip):
        if ip:
            return ip
    return None


def format_vendor_label(vendor_name: str | None, vendor_version: str | None) -> str:
    """Zabbix template vendor as ``Name, version`` (empty if both missing)."""
    return ', '.join(part for part in (vendor_name, vendor_version) if part)


def is_cloud_fortigate_http_vendor(vendor: str) -> bool:
    """True when the live template is the confirmed Cloud 7.0-2 vendor string."""
    return vendor == FORTIGATE_HTTP_CLOUD_VENDOR
