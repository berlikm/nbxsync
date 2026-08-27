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

Shared Zabbix monitoring token is the existing NetBox
``{$FGATE.API.TOKEN}`` assignment on **Platform FortiOS**, not role
Firewall and never ``NBX_FORTIGATE_TOKEN``. That environment variable is
reserved for NetBox inventory automation.

Companion **FortiGate Observability** nests stock FortiGate by HTTP + ICMP
Ping. Do not also assign those parents on FortiOS objects. Apply keeps the
Cloud parent version-pinned and installs only bounded compatibility fixes:
ZBX-27082 plus multi-VDOM interface/SD-WAN normalization. HA, memory pressure,
HA synchronization, and IPsec inventory remain organization-owned companion
signals. Apply never imports bundled 7.0-3 over Cloud **Zabbix, 7.0-2**.
Do not re-run zerotouch.
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path

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
FGATE_AUTOMATION_TOKEN_ENV = 'NBX_FORTIGATE_TOKEN'
FGATE_PATH_CONTROL_MACRO = '{$FGATE.PATH.CONTROL}'
# ha-mgmt GUI. 443 is SSL-VPN on these boxes; stock HTTP defaults to 80.
FGATE_API_PORT = '20443'
HA_ROLE_KEY = 'fgate.ha.role'
POLICY_MASTER_KEY = 'fgate.fwp.get_data'
POLICY_DISCOVERY_KEY = 'fgate.fwp.discovery'

MEMORY_GREEN_MACRO = '{$FGATE.MEMORY.GREEN}'
MEMORY_RED_MACRO = '{$FGATE.MEMORY.RED}'
MEMORY_EXTREME_MACRO = '{$FGATE.MEMORY.EXTREME}'
# Factory FortiGuard SLA is not an underlay WAN probe. Overlay members
# (v0665-trin*) flap FortiGuard reachability without meaning the circuit is
# down. LLD NAME.NOT_MATCHES drops the whole health-check (link-down and
# loss). CONTROL:"Default_FortiGuard"=0 would mute link-down only — loss
# keys off member {#IFNAME}. Do not set this to ``.*``.
SDWAN_HEALTH_NAME_NOT_MATCHES = '^Default_FortiGuard$'

# HostSync of a FortiOS device inherits platform defaults onto the companion.
# Apply writes a per-device exact-match IFNAME regex from enabled+cabled NetBox
# interfaces, and device-specific FortiOS memory thresholds when readable.
# NOT_MATCHES remains a denylist; setting it to ``.*`` excludes every interface.
# Estate FortiOS boxes are HA pairs; standalone needs a host override of 1.
FORTIOS_PLATFORM_MACROS = {
    '{$FGATE.SCHEME}': 'https',
    '{$FGATE.API.PORT}': FGATE_API_PORT,
    '{$NET.IF.IFNAME.MATCHES}': '^$',
    '{$NET.IF.IFNAME.NOT_MATCHES}': 'CHANGE_IF_NEEDED',
    '{$SDWAN.HEALTH.IFNAME.MATCHES}': '.*',
    '{$SDWAN.HEALTH.NAME.NOT_MATCHES}': SDWAN_HEALTH_NAME_NOT_MATCHES,
    '{$SDWAN.MEMBER.NAME.MATCHES}': '.*',
    '{$FWP.FWNAME.MATCHES}': '^$',
    '{$NET.IF.UTIL.MAX}': '101',
    '{$FIRMWARE.UPDATES.CONTROL}': '0',
    '{$DISK.FREE.CRIT}': '0',
    '{$CPU.UTIL.CRIT}': '101',
    '{$MEMORY.UTIL.CRIT}': '101',
    MEMORY_GREEN_MACRO: '82',
    MEMORY_RED_MACRO: '88',
    MEMORY_EXTREME_MACRO: '95',
    FGATE_PATH_CONTROL_MACRO: '1',
    '{$NET.IF.DISCOVERY.MIN}': '0',
    '{$FGATE.SDWAN.EXPECTED}': '1',
    '{$FGATE.HA.EXPECTED}': '2',
    FGATE_FQDN_MACRO: FGATE_FQDN_JINJA,
}

# Live Cloud HTTP scripts patched in place (not a YAML import).
VDOM_STAR_SCRIPT_KEYS = (
    'fgate.netif.get_data',
    'fgate.sdwan.get_data',
)

# Overlay census on FortiGate Observability — not a rewrite of stock HTTP scripts.
OVERLAY_INVENTORY_KEY = 'fgate.observability.inventory'

_BUNDLED_HTTP_YAML = (
    Path(__file__).resolve().parents[1]
    / 'zabbix/templates/fortinet_fortigate_http/template_net_fortigate_http.yaml'
)

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

# Stock Forti HTTP masters use history=0 (pass-through to dependents). item.get
# lastclock/lastvalue then stay empty even when the poller is running — that is
# why fgate.ha.role (default history) looked healthy while sdwan/netif/system
# looked uncollected. Keep 1h so Execute now is visible; do not store days of
# vdom=* JSON.
RAW_MASTER_HISTORY = '1h'
RAW_MASTER_HISTORY_KEYS = (
    'fgate.netif.get_data',
    'fgate.sdwan.get_data',
    'fgate.system.get_data',
)

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


def fortigate_ifname_regex(names) -> str:
    """Exact Zabbix LLD regex for NetBox-approved interface names."""
    unique = sorted({str(name).strip() for name in names if name is not None and str(name).strip()})
    if not unique:
        return '^$'
    return '^(?:' + '|'.join(re.escape(name) for name in unique) + ')$'


def fortigate_memory_thresholds(payload: dict | None) -> dict[str, str] | None:
    """Validated FortiOS green/red/extreme memory thresholds."""
    if not isinstance(payload, dict):
        return None
    results = payload.get('results', payload)
    if not isinstance(results, dict):
        return None
    keys = {
        MEMORY_GREEN_MACRO: 'memory-use-threshold-green',
        MEMORY_RED_MACRO: 'memory-use-threshold-red',
        MEMORY_EXTREME_MACRO: 'memory-use-threshold-extreme',
    }
    try:
        values = {macro: int(results[key]) for macro, key in keys.items()}
    except (KeyError, TypeError, ValueError):
        return None
    green = values[MEMORY_GREEN_MACRO]
    red = values[MEMORY_RED_MACRO]
    extreme = values[MEMORY_EXTREME_MACRO]
    if not (0 < green < red < extreme <= 100):
        return None
    return {macro: str(value) for macro, value in values.items()}


def fetch_fortigate_api(
    fqdn: str,
    token: str,
    path: str,
    *,
    scheme: str = 'https',
    port: str = FGATE_API_PORT,
    timeout: float = 10,
    opener=None,
) -> tuple[dict | list | None, str | None]:
    """Fetch one FortiOS JSON object or multi-VDOM array with an operator-safe error."""
    fqdn = (fqdn or '').strip()
    token = (token or '').strip()
    if not fqdn:
        return None, 'missing API FQDN'
    if not token:
        return None, 'missing API token'
    if not path.startswith('/'):
        return None, 'API path must start with /'

    request = urllib.request.Request(
        f'{scheme}://{fqdn}:{port}{path}',
        headers={
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}',
        },
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    open_request = opener or urllib.request.urlopen
    try:
        with open_request(request, context=context, timeout=timeout) as response:
            status = getattr(response, 'status', None) or response.getcode()
            body = response.read()
    except urllib.error.HTTPError as error:
        return None, f'HTTP {error.code}'
    except urllib.error.URLError as error:
        return None, f'connection failed: {error.reason}'
    except (OSError, TimeoutError) as error:
        return None, f'connection failed: {error}'

    if status != 200:
        return None, f'HTTP {status}'
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, 'HTTP 200 with invalid JSON'
    if not isinstance(payload, (dict, list)):
        return None, 'HTTP 200 with unexpected JSON payload'
    return payload, None


LINKDOWN_SAMPLES = 3
NETIF_STATUS_DOWN = '0'  # valuemap Link state: 0=down, 1=up
SDWAN_STATUS_DOWN = '1'  # JS indexOf up/down/error → 1=down
SDWAN_STATUS_ERROR = '2'




def probe_fortigate_api(
    fqdn: str,
    token: str,
    *,
    scheme: str = 'https',
    port: str = FGATE_API_PORT,
    timeout: float = 10,
    opener=None,
) -> str | None:
    """Return an operator-safe error, or ``None`` after a valid status response.

    This runs from the NetBox process with its inventory automation token. It
    proves that path, not the separate Zabbix monitoring token or proxy path.
    """
    payload, error = fetch_fortigate_api(
        fqdn,
        token,
        '/api/v2/monitor/system/status',
        scheme=scheme,
        port=port,
        timeout=timeout,
        opener=opener,
    )
    if error:
        return error
    if not isinstance(payload, dict):
        return 'HTTP 200 with unexpected JSON payload'
    return None


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


def bundled_http_script(key: str) -> str:
    """Script body from the bundled 7.0-3 YAML (reference only — never imported)."""
    text = _BUNDLED_HTTP_YAML.read_text(encoding='utf-8')
    marker = f'          key: {key}\n'
    start = 0
    while True:
        idx = text.find(marker, start)
        if idx < 0:
            raise ValueError(f'missing bundled HTTP script {key}')
        params = text.find('params: |', idx)
        next_item = text.find('\n          key:', idx + len(marker))
        if params < 0 or (next_item != -1 and params > next_item):
            start = idx + len(marker)
            continue
        end_at = text.find('\n          description:', params)
        if end_at < 0:
            end_at = text.find('\n          timeout:', params)
        block = text[params:end_at]
        lines = block.split('\n')[1:]
        out = []
        for line in lines:
            if line.startswith('            '):
                out.append(line[12:])
            else:
                out.append(line)
        return '\n'.join(out).strip('\n') + '\n'


def stock_http_collector_script(key: str) -> str:
    """Vendor collector + ZBX-27082 only. No vdom=* rewrite."""
    return patch_zbx27082_script(bundled_http_script(key))


def script_is_vdom_mutated(script: str) -> bool:
    """True when stock netif/SD-WAN JS was rewritten in place."""
    text = script or ''
    return (
        'function fortiFetchVdom' in text
        or 'function flattenFortiMonitorMap' in text
        or 'function fortiHttpRaw' in text
    )


# Stock FortiGate-by-HTTP calls interface/SD-WAN APIs with no vdom=*, so LLD is
# the REST admin's current VDOM only (usually root). ?vdom=* returns an array
# of {vdom, results} blocks; stock JS assumes one object and would throw.
# {#IFKEY} becomes vdom:ifName so port1 in two VDOMs does not collide.
_VDOM_STAR_MARK = 'function fortiApiBlocks'
_NOT_OBJECT_RE = re.compile(
    r"(if \(typeof response !== 'object' \|\| response === null\) \{[\s\S]*?"
    r"received data is not an object\.[\s\S]*?\}\s*\n)"
)
_NETIF_LIST_GET = re.compile(r'(var netif_list = [^;]+;\s*\n)')
_SDWAN_LIST_GET = re.compile(r'(var sdwan_list = [^;]+;\s*\n)')
_NETIF_LOOKUP_RE = re.compile(
    r"if \(typeof item\.q_origin_key !== 'undefined' && "
    r"typeof netif_data\.results\[String\(item\.q_origin_key\)\] !== 'undefined'\) \{\s*"
    r"Object\.assign\(item, netif_data\.results\[String\(item\.q_origin_key\)\]\);\s*"
    r"\}"
)
_NETIF_ID_RE = re.compile(
    r"if \(typeof item\.id === 'undefined'\) \{\s*"
    r"item\.id = item\.q_origin_key;\s*"
    r"\}"
)
_SDWAN_MEM_RE = re.compile(
    r"if \(typeof v\.interface !== 'undefined' && "
    r"typeof sdwan_member_data\.results\[v\.interface\] !== 'undefined'\) \{\s*"
    r"Object\.assign\(v, sdwan_member_data\.results\[v\.interface\]\);\s*"
    r"\}"
)
_SDWAN_HEALTH_RE = re.compile(
    r"if \(typeof v\.name !== 'undefined' && "
    r"typeof sdwan_health_data\.results\[v\.name\] !== 'undefined'\) \{\s*"
    r"Object\.assign\(v, sdwan_health_data\.results\[v\.name\]\);\s*"
    r"\}"
)
_VDOM_URLS = ()
_NETIF_EMPTY_DATA = '{"data": [], "error": ""}'
_NETIF_FETCHES = (
    (
        re.compile(
            r"var netif_data = getHttpData\(\s*"
            r"api_url \+ '/api/v2/monitor/system/interface(?:\?[^']*)?'\s*"
            r"\);"
        ),
        "var netif_data = fortiFetchVdom(api_url, '/api/v2/monitor/system/interface?include_vlan=true');",
    ),
    (
        re.compile(
            r"var netif_list = getHttpData\(\s*"
            r"api_url \+ '/api/v2/cmdb/system/interface(?:\?[^']*)?'\s*"
            r"\);"
        ),
        "var netif_list = fortiFetchVdom(api_url, '/api/v2/cmdb/system/interface');",
    ),
)
_NETIF_KEYS = "['q_origin_key', 'name', 'mode', 'type', 'description']"
_NETIF_KEYS_VDOM = "['q_origin_key', 'name', 'mode', 'type', 'description', 'vdom']"
_ARRAY_GUARD = (
    "\t\t\tif (Array.isArray(response)) {\n"
    "\t\t\t\treturn response;\n"
    "\t\t\t}\n"
)
_NETIF_NORMALIZE = (
    "\n"
    "\t\t\tnetif_data = { results: flattenFortiMonitorMap(netif_data) };\n"
    "\t\t\tnetif_list = { results: flattenFortiCmdbList(netif_list) };\n"
)
_SDWAN_NORMALIZE = (
    "\n"
    "\t\t\tsdwan_member_data = { results: flattenFortiMonitorMap(sdwan_member_data) };\n"
    "\t\t\tsdwan_health_data = { results: flattenFortiMonitorMap(sdwan_health_data) };\n"
    "\t\t\tsdwan_list = { results: flattenFortiSdwanCmdb(sdwan_list) };\n"
)
_SDWAN_HEALTH_NAME_LINE = "\t\t\t\t'health_name': item.name,\n"
_SDWAN_HEALTH_VDOM_LINE = "\t\t\t\t'vdom': item.vdom,\n"
_SDWAN_EMPTY_DATA = (
    '{"data": {"member_lld": [], "health_lld": [], "health_data": []}, "error": ""}'
)
_SDWAN_STOCK_DATA = '{"data": {}, "error": ""}'
_SDWAN_FETCHES = (
    (
        re.compile(
            r"var sdwan_member_data = getHttpData\(\s*"
            r"api_url \+ '/api/v2/monitor/virtual-wan/members(?:\?[^']*)?'\s*"
            r"\);"
        ),
        "var sdwan_member_data = fortiFetchVdom(api_url, '/api/v2/monitor/virtual-wan/members');",
    ),
    (
        re.compile(
            r"var sdwan_health_data = getHttpData\(\s*"
            r"api_url \+ '/api/v2/monitor/virtual-wan/health-check(?:\?[^']*)?'\s*"
            r"\);"
        ),
        "var sdwan_health_data = fortiFetchVdom(api_url, '/api/v2/monitor/virtual-wan/health-check');",
    ),
    (
        re.compile(
            r"var sdwan_list = getHttpData\(\s*"
            r"api_url \+ '/api/v2/cmdb/system/sdwan(?:\?[^']*)?'\s*"
            r"\);"
        ),
        "var sdwan_list = fortiFetchVdom(api_url, '/api/v2/cmdb/system/sdwan');",
    ),
)
_SDWAN_FOREACH = (
    (
        "sdwan_list.results['health-check'].forEach",
        "(sdwan_list.results['health-check'] || []).forEach",
    ),
    (
        'sdwan_list.results.members.forEach',
        '(sdwan_list.results.members || []).forEach',
    ),
    (
        'sdwan_list.results.members.filter',
        '(sdwan_list.results.members || []).filter',
    ),
    (
        "sdwan_list.results['health-check'].filter",
        "(sdwan_list.results['health-check'] || []).filter",
    ),
)
_FLATTEN_SDWAN_END = re.compile(
    r"(function flattenFortiSdwanCmdb\(payload\) \{[\s\S]*?"
    r"return \{ members: members, 'health-check': health \};\n\})"
)
_NETIF_LOOKUP = (
    "var _mon = fortiMonitorLookup(netif_data.results, item.vdom, item.q_origin_key);\n"
    "\t\t\t\tif (typeof item.q_origin_key !== 'undefined' && _mon) {\n"
    "\t\t\t\t\tObject.assign(item, _mon);\n"
    "\t\t\t\t}"
)
_SDWAN_MEM_LOOKUP = (
    "var _mm = fortiMonitorLookup(sdwan_member_data.results, v.vdom, v.interface);\n"
    "\t\t\t\t\tif (typeof v.interface !== 'undefined' && _mm) {\n"
    "\t\t\t\t\t\tObject.assign(v, _mm);\n"
    "\t\t\t\t\t}"
)
_SDWAN_HEALTH_LOOKUP = (
    "var _hm = fortiMonitorLookup(sdwan_health_data.results, v.vdom, v.name);\n"
    "\t\t\t\t\tif (typeof v.name !== 'undefined' && _hm) {\n"
    "\t\t\t\t\t\tObject.assign(v, _hm);\n"
    "\t\t\t\t\t}"
)
FORTI_VDOM_HELPERS = r'''
function isFortiVdomBlock(obj) {
	return obj && typeof obj === 'object' && typeof obj.results !== 'undefined';
}

function fortiApiBlocks(payload) {
	var blocks;
	if (payload == null) {
		return [];
	}
	if (Array.isArray(payload)) {
		blocks = payload;
	} else if (isFortiVdomBlock(payload) && Array.isArray(payload.results) && payload.results.length > 0 && isFortiVdomBlock(payload.results[0])) {
		blocks = payload.results;
	} else if (isFortiVdomBlock(payload)) {
		blocks = [payload];
	} else {
		return [];
	}
	var out = [];
	for (var i = 0; i < blocks.length; i++) {
		var b = blocks[i];
		if (!isFortiVdomBlock(b)) {
			continue;
		}
		if (typeof b.status !== 'undefined' && b.status != 'success') {
			continue;
		}
		out.push(b);
	}
	return out;
}

function fortiIfaceId(item) {
	var name = (item && (item.q_origin_key || item.name)) || '';
	var vdom = (item && item.vdom) || '';
	return vdom ? String(vdom) + ':' + name : name;
}

function fortiMonitorLookup(map, vdom, name) {
	if (!map || name === undefined || name === null) {
		return null;
	}
	var key = (vdom ? String(vdom) + ':' : '') + String(name);
	if (typeof map[key] !== 'undefined') {
		return map[key];
	}
	if (typeof map[String(name)] !== 'undefined') {
		return map[String(name)];
	}
	return null;
}

function flattenFortiMonitorMap(payload) {
	var out = {};
	var blocks = fortiApiBlocks(payload);
	for (var i = 0; i < blocks.length; i++) {
		var block = blocks[i];
		var vdom = block.vdom || '';
		var results = block.results;
		if (Array.isArray(results)) {
			var mapped = {};
			results.forEach(function (row) {
				if (!row || typeof row !== 'object') {
					return;
				}
				var name = row.interface || row.name || row.q_origin_key;
				if (name !== undefined && name !== null && String(name) !== '') {
					mapped[String(name)] = row;
				}
			});
			results = mapped;
		}
		if (!results || typeof results !== 'object' || Array.isArray(results)) {
			continue;
		}
		Object.keys(results).forEach(function (name) {
			var row = results[name];
			if (!row || typeof row !== 'object') {
				return;
			}
			if (vdom && !row.vdom) {
				row.vdom = vdom;
			}
			var key = (row.vdom ? String(row.vdom) + ':' : '') + name;
			out[key] = row;
		});
	}
	return out;
}

function flattenFortiCmdbList(payload) {
	var byId = {};
	var order = [];
	var blocks = fortiApiBlocks(payload);
	for (var i = 0; i < blocks.length; i++) {
		var block = blocks[i];
		var vdom = block.vdom || '';
		var results = block.results;
		if (!Array.isArray(results)) {
			continue;
		}
		results.forEach(function (row) {
			if (!row || typeof row !== 'object') {
				return;
			}
			if (vdom && !row.vdom) {
				row.vdom = vdom;
			}
			row.id = fortiIfaceId(row);
			if (typeof byId[row.id] === 'undefined') {
				order.push(row.id);
			}
			byId[row.id] = row;
		});
	}
	return order.map(function (id) { return byId[id]; });
}

function flattenFortiSdwanCmdb(payload) {
	var members = [];
	var health = [];
	var blocks = fortiApiBlocks(payload);
	for (var bi = 0; bi < blocks.length; bi++) {
		var block = blocks[bi];
		var vdom = block.vdom || '';
		var results = block.results;
		if (!results || typeof results !== 'object' || Array.isArray(results)) {
			continue;
		}
		(results.members || []).forEach(function (row) {
			if (!row || typeof row !== 'object') {
				return;
			}
			if (vdom && !row.vdom) {
				row.vdom = vdom;
			}
			if (row.vdom && row.q_origin_key !== undefined) {
				row.q_origin_key = String(row.vdom) + ':' + row.q_origin_key;
			}
			members.push(row);
		});
		(results['health-check'] || []).forEach(function (row) {
			if (!row || typeof row !== 'object') {
				return;
			}
			if (vdom && !row.vdom) {
				row.vdom = vdom;
			}
			if (row.vdom && row.q_origin_key !== undefined) {
				row.q_origin_key = String(row.vdom) + ':' + row.q_origin_key;
			}
			if (row.vdom && Array.isArray(row.members)) {
				row.members.forEach(function (m) {
					if (m && m.q_origin_key !== undefined) {
						m.q_origin_key = String(row.vdom) + ':' + m.q_origin_key;
					}
				});
			}
			health.push(row);
		});
	}
	return { members: members, 'health-check': health };
}

function fortiEmpty(code) {
	return { status: 'error', http_status: code || 0, results: {} };
}

function fortiHttpRaw(url) {
	var req = new HttpRequest();
	if (typeof params.http_proxy !== 'undefined' && params.http_proxy !== '{' + '$FGATE.HTTP.PROXY}' && params.http_proxy !== '') {
		req.setProxy(params.http_proxy);
	}
	req.addHeader('Accept: application/json');
	req.addHeader('Authorization: Bearer ' + params.token);
	var raw = null;
	var code = 0;
	try {
		raw = req.get(url);
		code = req.getStatus();
	} catch (e) {
		Zabbix.log(4, '[ FortiGate ] [ ' + url + ' ] request failed: ' + e);
		return { code: 0, body: null };
	}
	var parsed = null;
	if (raw !== null && String(raw) !== '') {
		try {
			parsed = JSON.parse(raw);
		} catch (e) {
			parsed = null;
		}
	}
	if (parsed && typeof parsed === 'object' && !Array.isArray(parsed) && parsed.status == 'error' && typeof parsed.http_status !== 'undefined') {
		code = parsed.http_status;
	}
	Zabbix.log(4, '[ FortiGate ] [ ' + url + ' ] status ' + code);
	return { code: code, body: parsed };
}

function fortiHttpOk(resp) {
	if (!resp || resp.code !== 200 || resp.body == null) {
		return false;
	}
	var b = resp.body;
	if (Array.isArray(b)) {
		return true;
	}
	if (typeof b !== 'object') {
		return false;
	}
	if (typeof b.status !== 'undefined' && b.status != 'success') {
		return false;
	}
	if (typeof b.http_status !== 'undefined' && b.http_status !== 200) {
		return false;
	}
	return typeof b.results !== 'undefined';
}

function fortiVdomNames(base) {
	if (typeof fortiVdomNames._cache !== 'undefined') {
		return fortiVdomNames._cache;
	}
	var names = [];
	var resp = fortiHttpRaw(base + '/api/v2/cmdb/system/vdom');
	if (fortiHttpOk(resp) && resp.body && Array.isArray(resp.body.results)) {
		var rows = resp.body.results;
		for (var i = 0; i < rows.length; i++) {
			var row = rows[i];
			if (!row) {
				continue;
			}
			var n = row.name || row.q_origin_key;
			if (n) {
				names.push(String(n));
			}
		}
	}
	if (names.length > 16) {
		names = names.slice(0, 16);
	}
	fortiVdomNames._cache = names;
	return names;
}

function fortiFetchPerVdom(base, path, sep) {
	var blocks = [];
	var names = fortiVdomNames(base);
	for (var i = 0; i < names.length; i++) {
		var one = fortiHttpRaw(base + path + sep + 'vdom=' + names[i]);
		if (!fortiHttpOk(one)) {
			continue;
		}
		var body = one.body;
		if (Array.isArray(body)) {
			for (var j = 0; j < body.length; j++) {
				blocks.push(body[j]);
			}
		} else if (body && typeof body === 'object') {
			if (!body.vdom) {
				body.vdom = names[i];
			}
			blocks.push(body);
		}
	}
	return blocks;
}

function fortiFetchVdom(base, path) {
	var sep = path.indexOf('?') >= 0 ? '&' : '?';
	var star = fortiHttpRaw(base + path + sep + 'vdom=*');
	if (fortiHttpOk(star)) {
		return star.body;
	}
	var code = star.code || 0;
	// 424/404: endpoint absent (ZH5 health-check). Do not walk VDOMs — timeout.
	if (code === 424 || code === 404) {
		return fortiEmpty(code);
	}
	if (code === 500) {
		var blocks = fortiFetchPerVdom(base, path, sep);
		if (blocks.length > 0) {
			return blocks;
		}
	}
	var plain = fortiHttpRaw(base + path);
	if (fortiHttpOk(plain)) {
		return plain.body;
	}
	return fortiEmpty(plain.code || code);
}

'''


def script_has_vdom_star(script: str) -> bool:
    """True when interface/SD-WAN collection already requests every VDOM.

    Live Cloud scripts from the first vdom=* patch still have
    ``fortiFetchVdom`` that throws and walks every VDOM on any non-200
    (ZH5 ``health-check`` 424 × N VDOMs blows ``{$FGATE.DATA.TIMEOUT}``
    and leaves ``lastclock=0``). Those must keep looking unpatched until
    ``fortiHttpRaw`` short-circuits 424/404. Helpers nested inside
    ``getHttpData`` (array-guard ``return response`` fooled the old inserter)
    must keep looking unpatched — Duktape cannot see those names from ``try``.
    """
    if (
        not script
        or _VDOM_STAR_MARK not in script
        or 'function fortiHttpRaw' not in script
        or 'code === 424' not in script
        or _helpers_nested_in_gethttp(script)
    ):
        return False
    if 'virtual-wan/members' in script or '/cmdb/system/sdwan' in script:
        return (
            '"member_lld": []' in script
            and _SDWAN_HEALTH_VDOM_LINE in script
        )
    if '/monitor/system/interface' in script or '/cmdb/system/interface' in script:
        return (
            "fortiFetchVdom(api_url, '/api/v2/cmdb/system/interface')" in script
            and '{"data": [], "error": ""}' in script
        )
    return 'vdom=*' in script


def _is_vdom_block(obj) -> bool:
    return isinstance(obj, dict) and 'results' in obj


def forti_api_blocks(payload) -> list:
    """Array-or-object FortiOS ?vdom=* envelope → per-VDOM blocks."""
    if payload is None:
        return []
    if isinstance(payload, list):
        blocks = payload
    elif (
        _is_vdom_block(payload)
        and isinstance(payload.get('results'), list)
        and payload['results']
        and _is_vdom_block(payload['results'][0])
    ):
        blocks = payload['results']
    elif _is_vdom_block(payload):
        blocks = [payload]
    else:
        return []
    out = []
    for block in blocks:
        if not _is_vdom_block(block):
            continue
        status = block.get('status')
        if status is not None and status != 'success':
            continue
        out.append(block)
    return out


def flatten_forti_monitor_map(payload) -> dict:
    """Monitor iface/SD-WAN maps keyed by vdom:name."""
    out: dict = {}
    for block in forti_api_blocks(payload):
        vdom = block.get('vdom') or ''
        results = block.get('results')
        if isinstance(results, list):
            mapped = {}
            for row in results:
                if not isinstance(row, dict):
                    continue
                name = row.get('interface') or row.get('name') or row.get('q_origin_key')
                if name is not None and str(name) != '':
                    mapped[str(name)] = row
            results = mapped
        if not isinstance(results, dict):
            continue
        for name, row in results.items():
            if not isinstance(row, dict):
                continue
            row = dict(row)
            if vdom and not row.get('vdom'):
                row['vdom'] = vdom
            key = f'{row["vdom"]}:{name}' if row.get('vdom') else str(name)
            out[key] = row
    return out


def flatten_forti_cmdb_list(payload) -> list:
    """CMDB interface rows deduplicated by vdom:ifName."""
    out: dict[str, dict] = {}
    for block in forti_api_blocks(payload):
        vdom = block.get('vdom') or ''
        results = block.get('results')
        if not isinstance(results, list):
            continue
        for row in results:
            if not isinstance(row, dict):
                continue
            row = dict(row)
            if vdom and not row.get('vdom'):
                row['vdom'] = vdom
            name = row.get('q_origin_key') or row.get('name') or ''
            row['id'] = f'{row["vdom"]}:{name}' if row.get('vdom') else name
            out[row['id']] = row
    return list(out.values())


def flatten_forti_sdwan_cmdb(payload) -> dict:
    """Merge per-VDOM SD-WAN cmdb; prefix q_origin_key so LLD ids stay unique."""
    members: list = []
    health: list = []
    for block in forti_api_blocks(payload):
        vdom = block.get('vdom') or ''
        results = block.get('results')
        if not isinstance(results, dict):
            continue
        for row in results.get('members') or []:
            if not isinstance(row, dict):
                continue
            row = dict(row)
            if vdom and not row.get('vdom'):
                row['vdom'] = vdom
            if row.get('vdom') and row.get('q_origin_key') is not None:
                row['q_origin_key'] = f'{row["vdom"]}:{row["q_origin_key"]}'
            members.append(row)
        for row in results.get('health-check') or []:
            if not isinstance(row, dict):
                continue
            row = dict(row)
            if vdom and not row.get('vdom'):
                row['vdom'] = vdom
            if row.get('vdom') and row.get('q_origin_key') is not None:
                row['q_origin_key'] = f'{row["vdom"]}:{row["q_origin_key"]}'
            nested = []
            for member in row.get('members') or []:
                if not isinstance(member, dict):
                    nested.append(member)
                    continue
                member = dict(member)
                if row.get('vdom') and member.get('q_origin_key') is not None:
                    member['q_origin_key'] = f'{row["vdom"]}:{member["q_origin_key"]}'
                nested.append(member)
            row['members'] = nested
            health.append(row)
    return {'members': members, 'health-check': health}


_FETCH_HELPER_NAMES = (
    'fortiEmpty',
    'fortiHttpRaw',
    'fortiHttpOk',
    'fortiVdomNames',
    'fortiFetchPerVdom',
    'fortiFetchVdom',
)
_VDOM_HELPER_LIFT_NAMES = (
    'isFortiVdomBlock',
    'fortiApiBlocks',
    'fortiIfaceId',
    'fortiMonitorLookup',
    'flattenFortiMonitorMap',
    'flattenFortiCmdbList',
    'flattenFortiSdwanCmdb',
) + _FETCH_HELPER_NAMES


def _js_function_span(text: str, name: str) -> tuple[int, int] | None:
    """Start/end of ``function name(...) { ... }``, brace-matched."""
    needle = f'function {name}('
    start = text.find(needle)
    if start < 0:
        return None
    brace = text.find('{', start)
    if brace < 0:
        return None
    depth = 0
    i = brace
    n = len(text)
    quote = None
    while i < n:
        c = text[i]
        if quote:
            if c == '\\' and i + 1 < n:
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in '"\'':
            quote = c
            i += 1
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return start, i + 1
        i += 1
    return None


def _helpers_nested_in_gethttp(script: str) -> bool:
    """True when vdom helpers were inserted inside getHttpData (Duktape-invisible)."""
    span = _js_function_span(script, 'getHttpData')
    if not span:
        return False
    inner = script[span[0] : span[1]]
    return any(f'function {name}(' in inner for name in _VDOM_HELPER_LIFT_NAMES)


def _lift_vdom_helpers_out_of_gethttp(script: str) -> str:
    """Move nested helper declarations to program scope after getHttpData."""
    span = _js_function_span(script, 'getHttpData')
    if not span:
        return script
    gstart, gend = span
    inner = script[gstart:gend]
    found: list[tuple[int, int, str]] = []
    for name in _VDOM_HELPER_LIFT_NAMES:
        ispan = _js_function_span(inner, name)
        if ispan:
            found.append((ispan[0], ispan[1], inner[ispan[0] : ispan[1]]))
    if not found:
        return script
    found.sort(key=lambda t: t[0], reverse=True)
    for start, end, _src in found:
        if end < len(inner) and inner[end] == '\n':
            end += 1
        inner = inner[:start] + inner[end:]
    extracted = '\n\n'.join(
        src.rstrip() for _s, _e, src in sorted(found, key=lambda t: t[0])
    )
    rest_at = gend
    semi = ''
    if rest_at < len(script) and script[rest_at] == ';':
        semi = ';'
        rest_at += 1
    return script[:gstart] + inner + semi + '\n' + extracted + '\n' + script[rest_at:]


def _insert_after_gethttp(script: str, block: str) -> str:
    span = _js_function_span(script, 'getHttpData')
    if not span:
        return script + '\n' + block
    end = span[1]
    if end < len(script) and script[end] == ';':
        end += 1
    return script[:end] + '\n' + block + script[end:]


def _extract_js_function(blob: str, name: str) -> str:
    span = _js_function_span(blob, name)
    if not span:
        return ''
    return blob[span[0] : span[1]]


def _replace_js_function(text: str, name: str, new_fn: str) -> tuple[str, bool]:
    span = _js_function_span(text, name)
    if not span:
        return text, False
    start, end = span
    if end < len(text) and text[end] == '\n':
        end += 1
    return text[:start] + new_fn.rstrip() + '\n' + text[end:], True


def _insert_js_before_fetch(text: str, block: str) -> str:
    return _insert_after_gethttp(text, block)


def _ensure_fetch_helper(script: str) -> str:
    """Install/upgrade fetch helpers. 424 must not walk every VDOM (timeout).

    Live scripts already define ``fortiFetchVdom``. Prepending a new copy is
    not enough: JS last-declaration-wins would keep the throw-and-walk body.
    Replace each helper in place; insert only names that are missing.
    """
    text = script
    missing: list[str] = []
    for name in _VDOM_HELPER_LIFT_NAMES:
        src = _extract_js_function(FORTI_VDOM_HELPERS, name)
        if not src:
            return script
        if f'function {name}(' in text:
            text, ok = _replace_js_function(text, name, src)
            if not ok:
                return script
        else:
            missing.append(src)
    if missing:
        text = _insert_js_before_fetch(
            text, '\n' + '\n\n'.join(s.rstrip() for s in missing) + '\n\n'
        )
    if 'function fortiHttpRaw' not in text or 'code === 424' not in text:
        return script
    return text


def _ensure_netif_vdom_resilience(script: str) -> str:
    """Upgrade iface collection so a vdom=* 500 does not leave data as {}."""
    patched = _ensure_fetch_helper(script)
    if 'function fortiHttpRaw' not in patched:
        return script
    for rx, repl in _NETIF_FETCHES:
        patched = rx.sub(repl, patched, count=1)
    if 'flattenFortiCmdbList(netif_list)' not in patched:
        patched, n_norm = _NETIF_LIST_GET.subn(
            lambda m: m.group(1) + _NETIF_NORMALIZE, patched, count=1
        )
        if n_norm != 1:
            return script
    if _NETIF_KEYS_VDOM not in patched and _NETIF_KEYS in patched:
        patched = patched.replace(_NETIF_KEYS, _NETIF_KEYS_VDOM, 1)
    if 'fortiMonitorLookup(netif_data.results' not in patched:
        patched, n_lookup = _NETIF_LOOKUP_RE.subn(_NETIF_LOOKUP, patched, count=1)
        if n_lookup != 1:
            return script
    if 'item.id = fortiIfaceId(item);' not in patched:
        patched, n_id = _NETIF_ID_RE.subn('item.id = fortiIfaceId(item);', patched, count=1)
        if n_id == 0 and 'item.id = item.q_origin_key;' in patched:
            patched = patched.replace('item.id = item.q_origin_key;', 'item.id = fortiIfaceId(item);', 1)
            n_id = 1
        if n_id != 1:
            return script
    if 'netif_list.results.map' in patched and '(netif_list.results || []).map' not in patched:
        patched = patched.replace('netif_list.results.map', '(netif_list.results || []).map', 1)
    if _SDWAN_STOCK_DATA in patched and '"member_lld": []' not in patched:
        patched = patched.replace(_SDWAN_STOCK_DATA, _NETIF_EMPTY_DATA, 1)
    return patched


def _ensure_sdwan_vdom_resilience(script: str) -> str:
    """Upgrade SD-WAN collection so a vdom=* 500 does not empty $.data."""
    patched = _ensure_fetch_helper(script)
    if 'function fortiHttpRaw' not in patched:
        return script
    for rx, repl in _SDWAN_FETCHES:
        patched = rx.sub(repl, patched, count=1)
    if 'flattenFortiSdwanCmdb(sdwan_list)' not in patched:
        patched, n_norm = _SDWAN_LIST_GET.subn(
            lambda m: m.group(1) + _SDWAN_NORMALIZE, patched, count=1
        )
        if n_norm != 1:
            return script
    if 'fortiMonitorLookup(sdwan_member_data.results' not in patched:
        patched, n_mem = _SDWAN_MEM_RE.subn(_SDWAN_MEM_LOOKUP, patched, count=1)
        if n_mem != 1:
            return script
    if 'fortiMonitorLookup(sdwan_health_data.results' not in patched:
        patched, n_health = _SDWAN_HEALTH_RE.subn(_SDWAN_HEALTH_LOOKUP, patched, count=1)
        if n_health != 1:
            return script
    if _SDWAN_HEALTH_VDOM_LINE not in patched:
        if patched.count(_SDWAN_HEALTH_NAME_LINE) != 1:
            return script
        patched = patched.replace(
            _SDWAN_HEALTH_NAME_LINE,
            _SDWAN_HEALTH_NAME_LINE + _SDWAN_HEALTH_VDOM_LINE,
            1,
        )
    if _SDWAN_STOCK_DATA in patched and '"member_lld": []' not in patched:
        patched = patched.replace(_SDWAN_STOCK_DATA, _SDWAN_EMPTY_DATA, 1)
    for old, new in _SDWAN_FOREACH:
        if old in patched and new not in patched:
            patched = patched.replace(old, new, 1)
    return patched


def patch_vdom_star_script(script: str) -> str:
    """Request vdom=* and flatten multi-VDOM payloads. Idempotent."""
    if not script:
        return script
    patched = script
    if _helpers_nested_in_gethttp(patched):
        patched = _lift_vdom_helpers_out_of_gethttp(patched)
    if 'Array.isArray(response)' not in patched:
        patched, n_guard = _NOT_OBJECT_RE.subn(
            lambda m: m.group(1) + _ARRAY_GUARD, patched, count=1
        )
        if n_guard != 1:
            return script
    if _VDOM_STAR_MARK not in patched:
        inserted = _insert_after_gethttp(patched, FORTI_VDOM_HELPERS)
        if inserted == patched or _VDOM_STAR_MARK not in inserted:
            return script
        patched = inserted
    for rx, repl in _VDOM_URLS:
        patched = rx.sub(repl, patched)
    if '/api/v2/monitor/system/interface' in script:
        patched = _ensure_netif_vdom_resilience(patched)
    if '/api/v2/cmdb/system/sdwan' in script:
        patched = _ensure_sdwan_vdom_resilience(patched)
    if _helpers_nested_in_gethttp(patched):
        return script
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
