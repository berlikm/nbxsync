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
# ha-mgmt GUI. 443 is SSL-VPN on these boxes; stock HTTP defaults to 80.
FGATE_API_PORT = '20443'
HA_ROLE_KEY = 'fgate.ha.role'
POLICY_MASTER_KEY = 'fgate.fwp.get_data'
POLICY_DISCOVERY_KEY = 'fgate.fwp.discovery'

# HostSync of a FortiOS device inherits platform macros onto the companion.
# Canary LLD is wide open (stock ``.*`` / ``CHANGE_IF_NEEDED``) so ZH4 names
# every iface and SD-WAN member. Tighten NET.IF after the dump; do not MATCH
# ``port`` long-term (LAN on 200F). Do **not** set NOT_MATCHES to ``.*`` —
# LLD is MATCHES AND NOT_MATCHES, so that excludes every interface.
# {$FGATE.SDWAN.EXPECTED}=1 tickets empty member LLD while API is up.
# Estate FortiOS boxes are HA pairs; standalone needs a host override of 1.
FORTIOS_PLATFORM_MACROS = {
    '{$FGATE.SCHEME}': 'https',
    '{$FGATE.API.PORT}': FGATE_API_PORT,
    '{$NET.IF.IFNAME.MATCHES}': '.*',
    '{$NET.IF.IFNAME.NOT_MATCHES}': 'CHANGE_IF_NEEDED',
    '{$SDWAN.HEALTH.IFNAME.MATCHES}': '.*',
    '{$SDWAN.MEMBER.NAME.MATCHES}': '.*',
    '{$FWP.FWNAME.MATCHES}': '^$',
    '{$NET.IF.UTIL.MAX}': '101',
    '{$FIRMWARE.UPDATES.CONTROL}': '0',
    '{$DISK.FREE.CRIT}': '0',
    '{$CPU.UTIL.CRIT}': '101',
    '{$MEMORY.UTIL.CRIT}': '101',
    FGATE_PATH_CONTROL_MACRO: '1',
    '{$NET.IF.DISCOVERY.MIN}': '1',
    '{$FGATE.SDWAN.EXPECTED}': '1',
    '{$FGATE.HA.EXPECTED}': '2',
    FGATE_FQDN_MACRO: FGATE_FQDN_JINJA,
}

# Live Cloud HTTP scripts patched in place (not a YAML import).
VDOM_STAR_SCRIPT_KEYS = (
    'fgate.netif.get_data',
    'fgate.sdwan.get_data',
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


# Stock FortiGate-by-HTTP calls interface/SD-WAN APIs with no vdom=*, so LLD is
# the REST admin's current VDOM only (usually root). ?vdom=* returns an array
# of {vdom, results} blocks; stock JS assumes one object and would throw.
# {#IFKEY} becomes vdom:ifName so port1 in two VDOMs does not collide.
_VDOM_STAR_MARK = 'function fortiApiBlocks'
_AFTER_GETHTTP = re.compile(
    r'(function\s+getHttpData\s*\(\s*url\s*\)\s*\{[\s\S]*?return response;\s*\n\s*\};?\s*\n)'
)
_NOT_OBJECT_RE = re.compile(
    r"(if \(typeof response !== 'object' \|\| response === null\) \{[\s\S]*?"
    r"received data is not an object\.[\s\S]*?\}\s*\n)"
)
_NETIF_LIST_GET = re.compile(r'(var netif_list = getHttpData\([\s\S]*?\);\s*\n)')
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
_VDOM_URLS = (
    (
        re.compile(r"api_url \+ '/api/v2/monitor/system/interface(?:\?[^']*)?'"),
        "api_url + '/api/v2/monitor/system/interface?include_vlan=true&vdom=*'",
    ),
    (
        re.compile(r"api_url \+ '/api/v2/cmdb/system/interface(?:\?[^']*)?'"),
        "api_url + '/api/v2/cmdb/system/interface?vdom=*'",
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
	var out = [];
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
			out.push(row);
		});
	}
	return out;
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

function fortiVdomNames(base) {
	if (typeof fortiVdomNames._cache !== 'undefined') {
		return fortiVdomNames._cache;
	}
	var names = [];
	try {
		var payload = getHttpData(base + '/api/v2/cmdb/system/vdom');
		var rows = [];
		if (payload && Array.isArray(payload.results)) {
			rows = payload.results;
		}
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
	} catch (e) {
		names = [];
	}
	if (names.length > 16) {
		names = names.slice(0, 16);
	}
	fortiVdomNames._cache = names;
	return names;
}

function fortiFetchVdom(base, path) {
	var sep = path.indexOf('?') >= 0 ? '&' : '?';
	try {
		return getHttpData(base + path + sep + 'vdom=*');
	} catch (e1) {
		var blocks = [];
		var names = fortiVdomNames(base);
		for (var i = 0; i < names.length; i++) {
			try {
				var one = getHttpData(base + path + sep + 'vdom=' + names[i]);
				if (Array.isArray(one)) {
					for (var j = 0; j < one.length; j++) {
						blocks.push(one[j]);
					}
				} else if (one && typeof one === 'object') {
					if (!one.vdom) {
						one.vdom = names[i];
					}
					blocks.push(one);
				}
			} catch (e3) {
				continue;
			}
		}
		if (blocks.length > 0) {
			return blocks;
		}
		try {
			return getHttpData(base + path);
		} catch (e2) {
			return { status: 'error', results: {} };
		}
	}
}

'''


def script_has_vdom_star(script: str) -> bool:
    """True when interface/SD-WAN collection already requests every VDOM."""
    if not script or _VDOM_STAR_MARK not in script or 'vdom=*' not in script:
        return False
    if 'virtual-wan/members' in script or '/cmdb/system/sdwan' in script:
        return (
            'function fortiFetchVdom' in script
            and '"member_lld": []' in script
        )
    return True


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
    """CMDB interface rows with id = vdom:ifName when vdom is present."""
    out: list = []
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
            out.append(row)
    return out


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


def _forti_fetch_vdom_js() -> str:
    start = FORTI_VDOM_HELPERS.find('function fortiVdomNames')
    if start < 0:
        return ''
    return '\n' + FORTI_VDOM_HELPERS[start:].lstrip('\n')


def _ensure_sdwan_vdom_resilience(script: str) -> str:
    """Upgrade SD-WAN collection so a vdom=* 500 does not empty $.data."""
    patched = script
    if 'function fortiFetchVdom' not in patched:
        if 'function flattenFortiSdwanCmdb' in patched:
            patched, n_fn = _FLATTEN_SDWAN_END.subn(
                lambda m: m.group(1) + _forti_fetch_vdom_js(), patched, count=1
            )
            if n_fn != 1:
                return script
        else:
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
    if _SDWAN_STOCK_DATA in patched and '"member_lld": []' not in patched:
        patched = patched.replace(_SDWAN_STOCK_DATA, _SDWAN_EMPTY_DATA, 1)
    for old, new in _SDWAN_FOREACH:
        if old in patched and new not in patched:
            patched = patched.replace(old, new, 1)
    return patched


def patch_vdom_star_script(script: str) -> str:
    """Request vdom=* and flatten multi-VDOM payloads. Idempotent."""
    if not script or script_has_vdom_star(script):
        return script
    patched = script
    if 'Array.isArray(response)' not in patched:
        patched, n_guard = _NOT_OBJECT_RE.subn(
            lambda m: m.group(1) + _ARRAY_GUARD, patched, count=1
        )
        if n_guard != 1:
            return script
    if _VDOM_STAR_MARK not in patched:
        patched, n_help = _AFTER_GETHTTP.subn(
            lambda m: m.group(1) + FORTI_VDOM_HELPERS, patched, count=1
        )
        if n_help != 1:
            return script
    for rx, repl in _VDOM_URLS:
        patched = rx.sub(repl, patched)
    if '/api/v2/monitor/system/interface' in script:
        if 'flattenFortiCmdbList(netif_list)' not in patched:
            patched, n_norm = _NETIF_LIST_GET.subn(
                lambda m: m.group(1) + _NETIF_NORMALIZE, patched, count=1
            )
            if n_norm != 1:
                return script
        patched = patched.replace(_NETIF_KEYS, _NETIF_KEYS_VDOM, 1)
        patched, n_lookup = _NETIF_LOOKUP_RE.subn(_NETIF_LOOKUP, patched, count=1)
        if n_lookup != 1:
            return script
        patched, n_id = _NETIF_ID_RE.subn('item.id = fortiIfaceId(item);', patched, count=1)
        if n_id != 1:
            return script
    if '/api/v2/cmdb/system/sdwan' in script:
        patched = _ensure_sdwan_vdom_resilience(patched)
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
