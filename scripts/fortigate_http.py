#!/usr/bin/env python3
"""FortiGate HTTP contract (no Django, no Zabbix).

Cutover is ``configure_nbxsync_network.py --apply-fortigate-http``.

Scope is **platform FortiOS only** (Template Rule + Platform macros). Do not
put FortiGate templates, the REST token, or FGATE LLD macros on generic role
Firewall — that role is shared with FortiManager / FortiAnalyzer.

``{$FGATE.API.FQDN}`` is a **Platform FortiOS** Jinja assignment
(``{{ object.primary_ip4.address.ip }}``). HostSync renders it per device
from that unit's OOB / ha-mgmt. Do not write a literal IP on the Device —
that assignment wins over the platform and shows as not inherited.

FortiOS is HTTP + nested ICMP: do **not** inherit **SNMP Monitoring** from
role Firewall, and do **not** inherit Site Group **Agent Monitoring** (that
CG assigns ICMP Ping, which Observability already nests). Assign CG
**FortiGate HTTP** on Platform FortiOS instead — Agent @ primary for the
nested ICMP Ping IP, no ICMP Ping template on the CG. FMG/FAZ platforms
keep SNMP Monitoring. A leftover device-level FQDN or SNMP/Agent CG on a
FortiGate is pruned on apply.

Shared token (``NBX_FGATE_TOKEN``) lands on **Platform FortiOS**, not role
Firewall. Empty env must not wipe. Optional per-device override:
``NBX_FGATE_TOKEN_<HOSTNAME>``.

Companion **FortiGate Observability** nests stock FortiGate by HTTP + ICMP
Ping. Do not also assign those parents on FortiOS objects. Apply prunes
leftover ICMP/HTTP/SNMP from FortiOS devices, platforms, and device types.
Do not strip ICMP Ping from agent-plane CGs. Apply never imports bundled
7.0-3 over Cloud **Zabbix, 7.0-2**. Do not re-run zerotouch.
"""

from __future__ import annotations

import re

FIREWALL_ROLE = 'Firewall'
FORTIGATE_HTTP_TEMPLATE = 'FortiGate by HTTP'
FORTIGATE_OBSERVABILITY_TEMPLATE = 'FortiGate Observability'
# Confirmed live Zabbix Cloud parent. Do not import bundled 7.0-3 over it.
FORTIGATE_HTTP_CLOUD_VENDOR_NAME = 'Zabbix'
FORTIGATE_HTTP_CLOUD_VENDOR_VERSION = '7.0-2'
FORTIGATE_HTTP_CLOUD_VENDOR = (
    f'{FORTIGATE_HTTP_CLOUD_VENDOR_NAME}, {FORTIGATE_HTTP_CLOUD_VENDOR_VERSION}'
)
FORTIGATE_SNMP_TEMPLATE = 'FortiGate by SNMP'
ICMP_PING_TEMPLATE = 'ICMP Ping'
SNMP_MONITORING_CG = 'SNMP Monitoring'
AGENT_MONITORING_CG = 'Agent Monitoring'
# Winning CG for FortiOS after SNMP is pruned from role Firewall. Beats Site
# Group Agent Monitoring so ICMP Ping is not assigned twice (Observability
# already nests it). Not role Firewall — FMG/FAZ share that role.
FORTIGATE_HTTP_CG = 'FortiGate HTTP'
FORTIOS_TEMPLATE_RULE = 'FortiOS'
FORTIOS_PLATFORM_PATTERN = r'FORTIOS|FortiOS'
FMG_FAZ_PLATFORM_PATTERN = r'FortiAnalyzer|FortiManager'

FGATE_TOKEN_MACRO = '{$FGATE.API.TOKEN}'
FGATE_FQDN_MACRO = '{$FGATE.API.FQDN}'
FGATE_FQDN_JINJA = '{{ object.primary_ip4.address.ip }}'
FGATE_TOKEN_ENV = 'NBX_FGATE_TOKEN'
FGATE_PATH_CONTROL_MACRO = '{$FGATE.PATH.CONTROL}'
HA_ROLE_KEY = 'fgate.ha.role'
POLICY_MASTER_KEY = 'fgate.fwp.get_data'
POLICY_DISCOVERY_KEY = 'fgate.fwp.discovery'

# HostSync of a FortiOS device inherits platform macros onto the companion.
# SD-WAN LLD is a separate filter family from NET.IF.*; leave NAME/ZONE
# MATCHES on wan/ha/mgmt/dmz until the first canary names the real
# health-checks. {$FGATE.SDWAN.EXPECTED}=0 keeps zero-member census quiet
# on standalone boxes without SD-WAN.
FORTIOS_PLATFORM_MACROS = {
    '{$FGATE.SCHEME}': 'https',
    '{$FGATE.API.PORT}': '443',
    '{$NET.IF.IFNAME.MATCHES}': '^(wan|ha|mgmt|dmz)',
    '{$NET.IF.IFNAME.NOT_MATCHES}': r'^(ssl\.|npu|fortilink|loopback|vlan)',
    '{$SDWAN.HEALTH.IFNAME.MATCHES}': '^(wan|ha|mgmt|dmz)',
    '{$SDWAN.MEMBER.NAME.MATCHES}': '^(wan|ha|mgmt|dmz)',
    '{$FWP.FWNAME.MATCHES}': '^$',
    '{$NET.IF.UTIL.MAX}': '101',
    '{$FIRMWARE.UPDATES.CONTROL}': '0',
    '{$DISK.FREE.CRIT}': '0',
    '{$CPU.UTIL.CRIT}': '101',
    '{$MEMORY.UTIL.CRIT}': '101',
    FGATE_PATH_CONTROL_MACRO: '1',
    '{$NET.IF.DISCOVERY.MIN}': '1',
    '{$FGATE.SDWAN.EXPECTED}': '0',
    '{$FGATE.HA.EXPECTED}': '1',
    FGATE_FQDN_MACRO: FGATE_FQDN_JINJA,
}

# Back-compat name used by older tests / Extreme --apply comments.
FIREWALL_ROLE_MACROS = FORTIOS_PLATFORM_MACROS

# No per-device Forti defaults. FQDN is platform Jinja. TOKEN is the shared
# FortiOS-platform secret (optional per-host override via env).
FIREWALL_DEVICE_MACROS = ()
FORTIOS_DEVICE_MACROS = FIREWALL_DEVICE_MACROS

# Templates that must not sit on generic role Firewall after HTTP cutover.
FIREWALL_ROLE_FORTI_TEMPLATES = (
    FORTIGATE_HTTP_TEMPLATE,
    FORTIGATE_SNMP_TEMPLATE,
    FORTIGATE_OBSERVABILITY_TEMPLATE,
    ICMP_PING_TEMPLATE,
)

# Nested parents of Observability. Assigned again → Zabbix "parent would be
# linked twice". Apply prunes them from FortiOS devices / platforms / device
# types. Do **not** strip ICMP Ping from shared agent-plane CGs. FortiOS uses
# CG FortiGate HTTP (no ICMP Ping template) so Site Group Agent Monitoring
# does not win.
FORTIOS_NESTED_PARENT_TEMPLATES = (
    FORTIGATE_HTTP_TEMPLATE,
    ICMP_PING_TEMPLATE,
)

# Sibling icmpping collision — cannot nest. Device-level leftover is an abort.
# Observability itself is the target, not an abort.
DEVICE_DUAL_LINK_TEMPLATES = (FORTIGATE_SNMP_TEMPLATE,)

# FortiOS-owned objects: prune nested parents and leftover SNMP together.
FORTIOS_COLLIDING_TEMPLATES = FORTIOS_NESTED_PARENT_TEMPLATES + DEVICE_DUAL_LINK_TEMPLATES

REQUIRED_HTTP_SCRIPT_KEYS = (
    'fgate.netif.get_data',
    'fgate.sdwan.get_data',
    'fgate.resources.get_data',
    'fgate.service.get_data',
)

SLOW_ITEM_DELAYS = {
    'fgate.firmware.get_data': '12h',
    'fgate.service.get_data': '1h',
}

# ZBX-27082: getHttpData reuses one HttpRequest and addHeader()s Authorization
# on every call. Fixed upstream for 7.0.30rc1 (not 7.0.29rc1). Vendor 7.0-2
# still has the bug; detect the script, do not trust the version string.
_NEW_HTTP_REQUEST = re.compile(r'new\s+HttpRequest\s*\(\s*\)')
_AUTH_HEADER = re.compile(r"addHeader\s*\(\s*['\"]Authorization:", re.I)
_FUNC_START = re.compile(r'function\s+getHttpData\s*\(\s*url\s*\)\s*\{')
_OUTER_REQUEST_DECL = re.compile(
    r'^[ \t]*request\s*=\s*new\s+HttpRequest\s*\(\s*\)\s*,\s*$',
    re.MULTILINE,
)
_OUTER_SET_PROXY = re.compile(
    r"\n[ \t]*if\s*\(\s*typeof params\.http_proxy[\s\S]*?request\.setProxy\(params\.http_proxy\);\s*\}\s*\n",
    re.MULTILINE,
)

GET_HTTP_DATA_FIXED_PREFIX = """
	request = new HttpRequest();
	if (typeof params.http_proxy !== 'undefined' && params.http_proxy !== '{' + '$FGATE.HTTP.PROXY}' && params.http_proxy !== '') {
		request.setProxy(params.http_proxy);
	}
"""

LINKDOWN_SAMPLES = 3
NETIF_STATUS_DOWN = '0'  # valuemap Link state: 0=down, 1=up
SDWAN_STATUS_DOWN = '1'  # JS indexOf up/down/error → 1=down
SDWAN_STATUS_ERROR = '2'


def fgate_token_env(hostname: str) -> str:
    """Optional per-device override. Same shape as ``NBX_PURE_TOKEN_*``."""
    return f'NBX_FGATE_TOKEN_{hostname.upper().replace("-", "_")}'


def should_write_secret(value: str | None) -> bool:
    """Empty / whitespace env must not wipe an existing token assignment."""
    return bool((value or '').strip())


def preferred_mgmt_ip(primary_ip: str | None, oob_ip: str | None = None) -> str | None:
    """Forti OOB / ha-mgmt is NetBox ``primary_ip4``, not the BMC ``oob_ip`` field."""
    for ip in (primary_ip, oob_ip):
        if ip:
            return ip
    return None


def format_vendor_label(vendor_name: str | None, vendor_version: str | None) -> str:
    """Zabbix template vendor as ``Name, version`` (empty if both missing)."""
    return ', '.join(part for part in (vendor_name, vendor_version) if part)


def is_cloud_fortigate_http_vendor(vendor: str) -> bool:
    """True when the live parent is the confirmed Cloud 7.0-2 vendor string.

    Empty / unknown vendor is not compatible (fail closed).
    """
    return vendor == FORTIGATE_HTTP_CLOUD_VENDOR


def platform_is_fortios(name: str | None) -> bool:
    return bool(name) and re.search(FORTIOS_PLATFORM_PATTERN, name, re.I) is not None


def platform_is_fmg_faz(name: str | None) -> bool:
    return bool(name) and re.search(FMG_FAZ_PLATFORM_PATTERN, name, re.I) is not None


def script_has_zbx27082(script: str) -> bool:
    """True when getHttpData addHeader()s Authorization on a reused HttpRequest."""
    if not script:
        return False
    func = _FUNC_START.search(script)
    auth = _AUTH_HEADER.search(script)
    if func is None or auth is None or auth.start() < func.start():
        return False
    outer = script[: func.start()]
    until_auth = script[func.start() : auth.start()]
    return bool(_NEW_HTTP_REQUEST.search(outer)) and _NEW_HTTP_REQUEST.search(until_auth) is None


def patch_zbx27082_script(script: str) -> str:
    """Recreate HttpRequest inside getHttpData (ZBX-27082 / 7.0.30rc1)."""
    if not script_has_zbx27082(script):
        return script
    patched = _OUTER_REQUEST_DECL.sub('', script)
    patched = _OUTER_SET_PROXY.sub('\n', patched)
    patched = _FUNC_START.sub(
        lambda m: m.group(0) + GET_HTTP_DATA_FIXED_PREFIX,
        patched,
        count=1,
    )
    return patched


def ha_role_gate_expr() -> str:
    """Primary/standalone, or fail-open for 30m while the new item is still nodata."""
    return (
        f'(last(/{FORTIGATE_HTTP_TEMPLATE}/{HA_ROLE_KEY})=1 '
        f'or nodata(/{FORTIGATE_HTTP_TEMPLATE}/{HA_ROLE_KEY},30m)=1)'
    )


def with_ha_role_gate(expr: str) -> str:
    """Append ha.role gating unless the expression already references the item."""
    if HA_ROLE_KEY in (expr or ''):
        return expr
    return f'{expr} and {ha_role_gate_expr()}'


def forti_linkdown_problem_expr(
    item_ref: str,
    control_macro: str,
    down_value: str,
    *,
    samples: int = LINKDOWN_SAMPLES,
    gate_ha_role: bool = True,
) -> str:
    """Sustained down (all of N samples), not .diff(). Optional primary-only gate."""
    core = (
        f'{control_macro}=1 and '
        f'max(/{item_ref},#{samples})={down_value} and '
        f'min(/{item_ref},#{samples})={down_value}'
    )
    if gate_ha_role:
        core += f' and {ha_role_gate_expr()}'
    return core


def forti_linkdown_recovery_expr(item_ref: str, control_macro: str, down_value: str) -> str:
    return f'last(/{item_ref})<>{down_value} or {control_macro}=0'


def netif_error_problem_expr(ifkey: str = '{#IFKEY}') -> str:
    """Inbound or outbound errors — stock checks in_errors twice."""
    inbound = f'min(/{FORTIGATE_HTTP_TEMPLATE}/fgate.netif.in_errors[{ifkey}],5m)'
    outbound = f'min(/{FORTIGATE_HTTP_TEMPLATE}/fgate.netif.out_errors[{ifkey}],5m)'
    return (
        f'{inbound}>{{$NET.IF.ERRORS.WARN:"{ifkey}"}} or '
        f'{outbound}>{{$NET.IF.ERRORS.WARN:"{ifkey}"}}'
    )


def netif_error_recovery_expr(ifkey: str = '{#IFKEY}') -> str:
    inbound = f'max(/{FORTIGATE_HTTP_TEMPLATE}/fgate.netif.in_errors[{ifkey}],5m)'
    outbound = f'max(/{FORTIGATE_HTTP_TEMPLATE}/fgate.netif.out_errors[{ifkey}],5m)'
    return (
        f'{inbound}<{{$NET.IF.ERRORS.WARN:"{ifkey}"}}*0.8 and '
        f'{outbound}<{{$NET.IF.ERRORS.WARN:"{ifkey}"}}*0.8'
    )
