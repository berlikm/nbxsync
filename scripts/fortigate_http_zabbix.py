#!/usr/bin/env python3
"""Zabbix API patches for FortiGate by HTTP (no Django).

Surgical updates on the live Cloud parent (Zabbix 7.0-2). Do not
configuration.import the bundled 7.0-3 YAML.
"""

from __future__ import annotations

import logging

from fortigate_http import (
    FORTIGATE_HTTP_CLOUD_VENDOR,
    FORTIGATE_HTTP_TEMPLATE,
    FORTIGATE_OBSERVABILITY_TEMPLATE,
    FORTIOS_PLATFORM_MACROS,
    HA_ROLE_KEY,
    OVERLAY_INVENTORY_KEY,
    POLICY_DISCOVERY_KEY,
    POLICY_MASTER_KEY,
    RAW_MASTER_HISTORY,
    RAW_MASTER_HISTORY_KEYS,
    REQUIRED_HTTP_SCRIPT_KEYS,
    SLOW_ITEM_DELAYS,
    VDOM_STAR_SCRIPT_KEYS,
    format_vendor_label,
    forti_linkdown_problem_expr,
    forti_linkdown_recovery_expr,
    is_cloud_fortigate_http_vendor,
    netif_error_problem_expr,
    netif_error_recovery_expr,
    patch_vdom_star_script,
    patch_zbx27082_script,
    script_has_vdom_star,
    script_has_zbx27082,
    with_ha_role_gate,
)

logger = logging.getLogger(__name__)

# Zabbix 7 script item type.
_SCRIPT_TYPE = 21
_DISABLED = 1
_MANUAL_CLOSE_NO = 0
_MANUAL_CLOSE_YES = 1

NETIF_CENSUS_TRIGGER = 'FortiGate: fewer discovered interfaces than expected'
HA_VDOM_TRIGGER = 'FortiGate: HA VDOM configuration is out of sync'
HA_VDOM_PRIMARY_GATE = 'last(/FortiGate Observability/fgate.observability.ha.role)=1'

OBSERVABILITY_TRIGGER_DEPENDENCIES = (
    ('FortiGate: no API data for 10m', 'FortiGate: no ICMP data for 10m'),
    ('FortiGate: memory pressure is above the configured extreme threshold', 'FortiGate: no API data for 10m'),
    ('FortiGate: memory pressure is above the configured red threshold', 'FortiGate: memory pressure is above the configured extreme threshold'),
    ('FortiGate: memory pressure is above the configured red threshold', 'FortiGate: no API data for 10m'),
    ('FortiGate: unsupported items', 'FortiGate: no API data for 10m'),
    (NETIF_CENSUS_TRIGGER, 'FortiGate: no API data for 10m'),
    ('FortiGate: fewer SD-WAN members than expected', 'FortiGate: no API data for 10m'),
    ('FortiGate: HA member count unexpected', 'FortiGate: no API data for 10m'),
    (HA_VDOM_TRIGGER, 'FortiGate: no API data for 10m'),
    (HA_VDOM_TRIGGER, 'FortiGate: HA member count unexpected'),
)

HA_ROLE_SCRIPT = r'''var params = JSON.parse(value);

function getHttpData(url) {
	request = new HttpRequest();
	if (typeof params.http_proxy !== 'undefined' && params.http_proxy !== '{' + '$FGATE.HTTP.PROXY}' && params.http_proxy !== '') {
		request.setProxy(params.http_proxy);
	}
	request.addHeader('Accept: application/json');
	request.addHeader('Authorization: Bearer ' + params.token);
	response = request.get(url);
	if (request.getStatus() !== 200) {
		throw 'status ' + request.getStatus();
	}
	return JSON.parse(response);
}

function isTrue(value) {
	return value === true || value === 1 || value === '1';
}

var api_url = params.scheme + '://' + params.fqdn + ':' + params.port;
try {
	var status = getHttpData(api_url + '/api/v2/monitor/system/status');
	var serial = (status.serial || (status.results && status.results.serial) || '').toString();
	if (!serial) {
		throw 'system status has no local serial';
	}
	var ha;
	try {
		ha = getHttpData(api_url + '/api/v2/monitor/system/ha-peer');
	} catch (e) {
		var ha_error = String(e);
		if (ha_error.indexOf('status 404') !== -1 || ha_error.indexOf('status 424') !== -1) {
			return 1;
		}
		throw e;
	}
	var rows = ha.results || ha;
	if (!Array.isArray(rows)) {
		rows = rows && typeof rows === 'object' ? [rows] : [];
	}
	if (rows.length === 0) {
		return 1;
	}
	var localFound = false;
	var primarySerial = '';
	for (var i = 0; i < rows.length; i++) {
		var row = rows[i] || {};
		var rowSerial = (row.serial_no || row.serial || '').toString();
		if (rowSerial === serial) {
			localFound = true;
		}
		var roleFields = [
			row.primary,
			row.master,
			row.is_manage_primary,
			row.is_manage_master,
			row.is_root_primary,
			row.is_root_master
		];
		for (var j = 0; j < roleFields.length; j++) {
			if (!isTrue(roleFields[j])) {
				continue;
			}
			if (!rowSerial) {
				throw 'primary HA peer has no serial';
			}
			if (primarySerial && primarySerial !== rowSerial) {
				throw 'multiple HA peers claim primary';
			}
			primarySerial = rowSerial;
		}
	}
	if (!localFound) {
		throw 'local serial not present in HA peers';
	}
	if (rows.length === 1) {
		return 1;
	}
	if (!primarySerial) {
		throw 'HA peers have no authoritative primary';
	}
	return primarySerial === serial ? 1 : 0;
} catch (error) {
	throw 'HA role collection failed: ' + error;
}
'''

# Standalone overlay census. Functions are program-scope — never splice into
# stock getHttpData. 424/404 on one endpoint leaves the others.
OVERLAY_INVENTORY_SCRIPT = r'''var params = JSON.parse(value);
var overlayErrors = [];

function overlayRaw(url) {
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
		return { code: 0, body: null, error: String(e) };
	}
	var parsed = null;
	if (raw !== null && String(raw) !== '') {
		try {
			parsed = JSON.parse(raw);
		} catch (e2) {
			return { code: code, body: null, error: 'invalid JSON' };
		}
	}
	if (parsed && typeof parsed === 'object' && !Array.isArray(parsed) && parsed.status == 'error' && typeof parsed.http_status !== 'undefined') {
		code = parsed.http_status;
	}
	return { code: code, body: parsed, error: '' };
}

function overlayOk(resp) {
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
	return true;
}

function overlayFailure(path, resp) {
	var detail = resp && resp.error ? resp.error : 'HTTP ' + (resp ? resp.code : 0);
	overlayErrors.push(path + ': ' + detail);
}

function overlayFetch(base, path) {
	var sep = path.indexOf('?') >= 0 ? '&' : '?';
	var star = overlayRaw(base + path + sep + 'vdom=*');
	if (overlayOk(star)) {
		return star.body;
	}
	if (star.code === 424 || star.code === 404) {
		return null;
	}
	if (star.code === 401 || star.code === 403 || star.code === 0) {
		overlayFailure(path, star);
		return null;
	}
	var plain = overlayRaw(base + path);
	if (overlayOk(plain)) {
		return plain.body;
	}
	overlayFailure(path, plain);
	return null;
}

function overlayBlocks(payload) {
	if (payload == null) {
		return [];
	}
	if (Array.isArray(payload)) {
		return payload;
	}
	if (typeof payload === 'object' && typeof payload.results !== 'undefined') {
		return [payload];
	}
	return [];
}

function overlayMemberRows(payload) {
	var out = [];
	function add(vdom, name, row) {
		row = row || {};
		out.push({
			vdom: vdom,
			interface: String(name),
			status: row.status !== undefined ? row.status : row.link,
			session: row.session !== undefined ? row.session : null,
			tx_bytes: row.tx_bytes !== undefined ? row.tx_bytes : null,
			rx_bytes: row.rx_bytes !== undefined ? row.rx_bytes : null,
			tx_bandwidth: row.tx_bandwidth !== undefined ? row.tx_bandwidth : null,
			rx_bandwidth: row.rx_bandwidth !== undefined ? row.rx_bandwidth : null
		});
	}
	overlayBlocks(payload).forEach(function (block) {
		if (!block || block.status == 'error') {
			return;
		}
		var vdom = block.vdom || '';
		var res = block.results;
		if (res == null) {
			return;
		}
		if (Array.isArray(res)) {
			res.forEach(function (row) {
				if (row && (row.interface || row.name)) {
					add(vdom, row.interface || row.name, row);
				}
			});
			return;
		}
		if (typeof res === 'object') {
			Object.keys(res).forEach(function (k) {
				var row = res[k] || {};
				add(vdom, row.interface || row.name || k, row);
			});
		}
	});
	return out;
}

function overlayHealthRows(payload) {
	var out = [];
	function add(vdom, name, row) {
		row = row || {};
		out.push({
			vdom: vdom,
			name: String(name),
			status: row.status !== undefined ? row.status : row.state,
			latency: row.latency !== undefined ? row.latency : null,
			jitter: row.jitter !== undefined ? row.jitter : null,
			packet_loss: row.packet_loss !== undefined ? row.packet_loss : null
		});
	}
	overlayBlocks(payload).forEach(function (block) {
		if (!block || block.status == 'error') {
			return;
		}
		var vdom = block.vdom || '';
		var res = block.results;
		if (!res || typeof res !== 'object') {
			return;
		}
		if (Array.isArray(res)) {
			res.forEach(function (row, i) {
				add(vdom, row && (row.name || row.q_origin_key) || String(i), row);
			});
			return;
		}
		Object.keys(res).forEach(function (name) {
			add(vdom, name, res[name]);
		});
	});
	return out;
}

function overlayIpsecRows(payload) {
	var out = [];
	function add(vdom, name, row) {
		row = row || {};
		out.push({
			vdom: vdom,
			name: String(name),
			phase1: row.p1name !== undefined ? row.p1name : null,
			phase2: row.p2name !== undefined ? row.p2name : (row.proxyid !== undefined ? row.proxyid : null),
			status: row.status !== undefined ? row.status : row.state,
			type: row.type !== undefined ? row.type : null,
			incoming_bytes: row.incoming_bytes !== undefined ? row.incoming_bytes : null,
			outgoing_bytes: row.outgoing_bytes !== undefined ? row.outgoing_bytes : null
		});
	}
	overlayBlocks(payload).forEach(function (block) {
		if (!block || block.status == 'error') {
			return;
		}
		var vdom = block.vdom || '';
		var res = block.results;
		if (res == null) {
			return;
		}
		if (Array.isArray(res)) {
			res.forEach(function (row) {
				var name = row && (row.p1name || row.name || row.proxyid || row.q_origin_key);
				if (name) {
					add(vdom, name, row);
				}
			});
			return;
		}
		if (typeof res === 'object') {
			Object.keys(res).forEach(function (k) {
				add(vdom, k, res[k]);
			});
		}
	});
	return out;
}

var out = { error: '', vdoms: [], sdwan_members: [], sdwan_health: [], ipsec: [] };
try {
	if (!params.scheme || !params.token || !params.fqdn || !params.port) {
		throw 'set FGATE scheme/token/fqdn/port';
	}
	var api = params.scheme + '://' + params.fqdn + ':' + params.port;
	var vd = overlayRaw(api + '/api/v2/cmdb/system/vdom');
	if (overlayOk(vd) && vd.body && Array.isArray(vd.body.results)) {
		vd.body.results.forEach(function (row) {
			var n = row && (row.name || row.q_origin_key);
			if (n) {
				out.vdoms.push(String(n));
			}
		});
	} else if (vd.code !== 404 && vd.code !== 424) {
		overlayFailure('/api/v2/cmdb/system/vdom', vd);
	}
	out.sdwan_members = overlayMemberRows(overlayFetch(api, '/api/v2/monitor/virtual-wan/members'));
	if (out.sdwan_members.length === 0) {
		overlayBlocks(overlayFetch(api, '/api/v2/cmdb/system/sdwan')).forEach(function (block) {
			if (!block || block.status == 'error' || !block.results) {
				return;
			}
			(block.results.members || []).forEach(function (row) {
				if (row && row.interface) {
					out.sdwan_members.push({ vdom: block.vdom || '', interface: String(row.interface) });
				}
			});
		});
	}
	out.sdwan_health = overlayHealthRows(overlayFetch(api, '/api/v2/monitor/virtual-wan/health-check'));
	out.ipsec = overlayIpsecRows(overlayFetch(api, '/api/v2/monitor/vpn/ipsec'));
} catch (e) {
	overlayErrors.push(String(e));
}
if (overlayErrors.length > 0) {
	throw 'overlay census failed: ' + overlayErrors.join('; ');
}
return JSON.stringify(out);
'''

_SCRIPT_PARAMETERS = [
    {'name': 'fqdn', 'value': '{$FGATE.API.FQDN}'},
    {'name': 'http_proxy', 'value': '{$FGATE.HTTP.PROXY}'},
    {'name': 'port', 'value': '{$FGATE.API.PORT}'},
    {'name': 'scheme', 'value': '{$FGATE.SCHEME}'},
    {'name': 'token', 'value': '{$FGATE.API.TOKEN}'},
]


def template_vendor_label(row: dict) -> str:
    return format_vendor_label(row.get('vendor_name'), row.get('vendor_version'))


def assert_cloud_http_template(row: dict) -> None:
    vendor = template_vendor_label(row) or ''
    if not is_cloud_fortigate_http_vendor(vendor):
        label = vendor or 'unknown'
        raise SystemExit(
            f'{FORTIGATE_HTTP_TEMPLATE} vendor is {label!r}; expected '
            f'{FORTIGATE_HTTP_CLOUD_VENDOR}. Refusing to patch an unexpected template.'
        )


def inspect_http_scripts(api, templateid) -> dict[str, str]:
    """Read-only ZBX-27082 / content check. missing = unexpected template."""
    items = {item['key_']: item for item in _script_items(api, templateid)}
    out: dict[str, str] = {}
    for key in REQUIRED_HTTP_SCRIPT_KEYS:
        item = items.get(key)
        if item is None:
            out[key] = 'missing'
        elif script_has_zbx27082(item.get('params') or ''):
            out[key] = 'vulnerable'
        else:
            out[key] = 'ok'
    return out


def _script_items(api, templateid) -> list[dict]:
    rows = api.item.get(
        hostids=templateid,
        filter={'type': [_SCRIPT_TYPE]},
        output=['itemid', 'key_', 'name', 'params', 'status'],
    ) or []
    return [r for r in rows if r.get('params')]


def patch_zbx27082_items(api, templateid) -> dict[str, str]:
    """Recreate HttpRequest inside getHttpData. Abort if anything stays vulnerable."""
    results: dict[str, str] = {}
    remaining = []
    for item in _script_items(api, templateid):
        key = item['key_']
        script = item.get('params') or ''
        if not script_has_zbx27082(script):
            results[key] = 'ok'
            continue
        patched = patch_zbx27082_script(script)
        if script_has_zbx27082(patched):
            remaining.append(key)
            results[key] = 'unpatched'
            continue
        api.item.update(itemid=item['itemid'], params=patched)
        results[key] = 'patched'
        logger.info('  %s: ZBX-27082 getHttpData HttpRequest-per-call', key)
    if remaining:
        raise SystemExit(
            'ZBX-27082 still present after patch on: ' + ', '.join(remaining)
            + '. Aborting — multi-request items (SD-WAN) would 401.'
        )
    return results




def patch_vdom_star_items(api, templateid) -> dict[str, str]:
    """Apply tested multi-VDOM compatibility; fail closed if normalization fails."""
    results: dict[str, str] = {}
    remaining = []
    items = {item['key_']: item for item in _script_items(api, templateid)}
    for key in VDOM_STAR_SCRIPT_KEYS:
        item = items.get(key)
        if item is None:
            remaining.append(key)
            results[key] = 'missing'
            continue
        script = item.get('params') or ''
        patched = patch_vdom_star_script(script)
        if not script_has_vdom_star(patched):
            remaining.append(key)
            results[key] = 'unpatched'
            continue
        if script_has_zbx27082(patched):
            remaining.append(key)
            results[key] = 'zbx27082'
            continue
        if patched == script:
            results[key] = 'ok'
            continue
        api.item.update(itemid=item['itemid'], params=patched)
        results[key] = 'patched'
        logger.info('  %s: vdom=* interface/SD-WAN collection', key)
    if remaining:
        raise SystemExit(
            'vdom=* patch failed on: ' + ', '.join(remaining)
            + '. Aborting — stock HTTP would keep current-VDOM-only LLD.'
        )
    return results


def ensure_ha_role_item(api, templateid) -> str:
    """Primary/standalone=1, secondary=0; collection failure stays unknown."""
    description = (
        '1 = primary or standalone (path tickets). 0 = secondary. '
        'Role comes from system/ha-peer matched to the local serial; '
        'unknown/error is unsupported, never primary.'
    )
    found = api.item.get(
        hostids=templateid,
        filter={'key_': HA_ROLE_KEY},
        output=['itemid', 'params', 'type', 'description'],
    ) or []
    if found:
        item = found[0]
        payload = {'itemid': item['itemid']}
        if (item.get('params') or '') != HA_ROLE_SCRIPT:
            payload['params'] = HA_ROLE_SCRIPT
        if (item.get('description') or '') != description:
            payload['description'] = description
        if len(payload) > 1:
            api.item.update(**payload)
            logger.info('  %s: authoritative ha-peer role script', HA_ROLE_KEY)
            return 'patched'
        return 'ok'
    api.item.create(
        name='HA role',
        key_=HA_ROLE_KEY,
        hostid=templateid,
        type=_SCRIPT_TYPE,
        value_type=0,
        delay='1m',
        params=HA_ROLE_SCRIPT,
        timeout='{$FGATE.DATA.TIMEOUT}',
        parameters=_SCRIPT_PARAMETERS,
        description=description,
    )
    logger.info('  created %s on %s', HA_ROLE_KEY, FORTIGATE_HTTP_TEMPLATE)
    return 'created'


def ensure_overlay_census_items(api, templateid) -> str:
    """All-VDOM SD-WAN/IPsec census; failures become unsupported and alert."""
    found = api.item.get(
        hostids=templateid,
        filter={'key_': OVERLAY_INVENTORY_KEY},
        output=['itemid', 'params', 'history'],
    ) or []
    if found:
        item = found[0]
        payload = {'itemid': item['itemid']}
        changed = False
        if (item.get('params') or '') != OVERLAY_INVENTORY_SCRIPT:
            payload['params'] = OVERLAY_INVENTORY_SCRIPT
            changed = True
        if str(item.get('history') or '') != '1h':
            payload['history'] = '1h'
            changed = True
        if changed:
            api.item.update(**payload)
            logger.info('  %s: overlay census script', OVERLAY_INVENTORY_KEY)
            return 'patched'
        return 'ok'
    api.item.create(
        name='SD-WAN / IPsec inventory (overlay)',
        key_=OVERLAY_INVENTORY_KEY,
        hostid=templateid,
        type=_SCRIPT_TYPE,
        value_type=4,
        delay='1m',
        history='1h',
        trends='0',
        params=OVERLAY_INVENTORY_SCRIPT,
        timeout='{$FGATE.DATA.TIMEOUT}',
        parameters=_SCRIPT_PARAMETERS,
        description=(
            'Census JSON for canary: VDOMs, SD-WAN members, health-check names, '
            'IPsec names. 404/424 is unavailable; other failures become unsupported.'
        ),
    )
    logger.info('  created %s on %s', OVERLAY_INVENTORY_KEY, FORTIGATE_OBSERVABILITY_TEMPLATE)
    return 'created'


def disable_policy_collection(api, templateid) -> dict[str, str]:
    """{$FWP.FWNAME.MATCHES}=^$ does not stop fgate.fwp.get_data API calls."""
    out: dict[str, str] = {}
    items = api.item.get(
        hostids=templateid,
        filter={'key_': POLICY_MASTER_KEY},
        output=['itemid', 'status'],
    ) or []
    for item in items:
        if str(item.get('status')) == str(_DISABLED):
            out[POLICY_MASTER_KEY] = 'already-disabled'
            continue
        api.item.update(itemid=item['itemid'], status=_DISABLED)
        out[POLICY_MASTER_KEY] = 'disabled'
        logger.info('  disabled %s (policy LLD master)', POLICY_MASTER_KEY)
    rules = api.discoveryrule.get(
        hostids=templateid,
        filter={'key_': POLICY_DISCOVERY_KEY},
        output=['itemid', 'status'],
    ) or []
    for rule in rules:
        if str(rule.get('status')) == str(_DISABLED):
            out[POLICY_DISCOVERY_KEY] = 'already-disabled'
            continue
        api.discoveryrule.update(itemid=rule['itemid'], status=_DISABLED)
        out[POLICY_DISCOVERY_KEY] = 'disabled'
        logger.info('  disabled %s', POLICY_DISCOVERY_KEY)
    return out

def disable_unavailable_capacity_items(api, templateid) -> dict[str, str]:
    """Disable stock absolute capacity items absent from FortiOS 7.6 responses."""
    keys = ('fgate.cpu.num', 'fgate.memory.total')
    out: dict[str, str] = {}
    for key in keys:
        items = api.item.get(
            hostids=templateid,
            filter={'key_': key},
            output=['itemid', 'status'],
        ) or []
        if not items:
            out[key] = 'missing'
            continue
        item = items[0]
        if str(item.get('status')) == str(_DISABLED):
            out[key] = 'already-disabled'
            continue
        api.item.update(itemid=item['itemid'], status=_DISABLED)
        out[key] = 'disabled'
        logger.info('  disabled %s (FortiOS 7.6 API exposes utilization, not absolute capacity)', key)
    return out


def upsert_http_template_macros(api, templateid) -> str:
    """CPU/mem CRIT 101 on the parent so stock High never pages."""
    tpls = api.template.get(
        templateids=[templateid],
        output=['templateid'],
        selectMacros='extend',
    ) or []
    if not tpls:
        return 'missing'
    wanted = {
        k: v
        for k, v in FORTIOS_PLATFORM_MACROS.items()
        if k in {
            '{$CPU.UTIL.CRIT}',
            '{$MEMORY.UTIL.CRIT}',
            '{$DISK.FREE.CRIT}',
            '{$NET.IF.UTIL.MAX}',
            '{$FIRMWARE.UPDATES.CONTROL}',
            '{$FGATE.SCHEME}',
            '{$FGATE.API.PORT}',
            '{$FWP.FWNAME.MATCHES}',
            '{$NET.IF.IFNAME.MATCHES}',
            '{$NET.IF.IFNAME.NOT_MATCHES}',
            '{$SDWAN.HEALTH.IFNAME.MATCHES}',
            '{$SDWAN.MEMBER.NAME.MATCHES}',
            '{$FGATE.PATH.CONTROL}',
            '{$NET.IF.DISCOVERY.MIN}',
            '{$FGATE.SDWAN.EXPECTED}',
            '{$FGATE.HA.EXPECTED}',
            '{$FGATE.MEMORY.GREEN}',
            '{$FGATE.MEMORY.RED}',
            '{$FGATE.MEMORY.EXTREME}',
        }
    }
    existing = list(tpls[0].get('macros') or [])
    by_name = {m['macro']: dict(m) for m in existing if isinstance(m, dict) and m.get('macro')}
    current = {k: by_name[k].get('value', '') for k in wanted if k in by_name}
    if all(current.get(k) == v for k, v in wanted.items()) and len(current) == len(wanted):
        return 'ok'
    for macro, value in wanted.items():
        if macro in by_name:
            by_name[macro]['value'] = value
        else:
            by_name[macro] = {'macro': macro, 'value': value}
    payload = []
    for m in by_name.values():
        entry = {'macro': m['macro'], 'value': m.get('value', '')}
        if m.get('hostmacroid'):
            entry['hostmacroid'] = m['hostmacroid']
        if m.get('description') is not None:
            entry['description'] = m.get('description', '')
        if m.get('type') is not None:
            entry['type'] = m['type']
        payload.append(entry)
    api.template.update(templateid=templateid, macros=payload)
    logger.info('  %s: estate macros (CPU/mem CRIT 101, https/%s)', FORTIGATE_HTTP_TEMPLATE, FORTIOS_PLATFORM_MACROS['{$FGATE.API.PORT}'])
    return 'patched'


def _proto_name(row: dict) -> str:
    return str(row.get('description') or row.get('name') or '')

def _license_problem_expr(name: str, current: str) -> str:
    """Restore stock context macros before adding the HA-primary gate."""
    control = '{$SERVICE.LICENSE.CONTROL:"{#KEY}"}'
    if 'License expires soon' in name:
        expiry = 'last(/FortiGate by HTTP/fgate.service.expire["{#KEY}"])'
        base = (
            f'{control}=1 and ({expiry} - now()) / 86400 < '
            '{$SERVICE.EXPIRY.WARN:"{#KEY}"}'
            f' and {expiry} > now()'
        )
        return with_ha_role_gate(base)
    if 'License status is unsuccessful' in name:
        return with_ha_role_gate(
            f'{control}=1 and '
            'last(/FortiGate by HTTP/fgate.service.license["{#KEY}"])>5'
        )
    return with_ha_role_gate(current)



def patch_wan_state_triggers(api, templateid) -> dict[str, int]:
    """Replace .diff()+manual close with sustained down; gate on ha.role."""
    changed = 0
    protos = api.triggerprototype.get(
        hostids=templateid,
        output=[
            'triggerid',
            'description',
            'expression',
            'recovery_expression',
            'recovery_mode',
            'manual_close',
        ],
        expandExpression=False,
    ) or []
    for proto in protos:
        name = _proto_name(proto)
        expr = str(proto.get('expression') or '')
        payload: dict = {}
        if 'High error rate' in name and 'fgate.netif.in_errors' in expr:
            wanted = netif_error_problem_expr()
            recovery = netif_error_recovery_expr()
            if expr != wanted:
                payload['expression'] = wanted
            if str(proto.get('recovery_expression') or '') != recovery:
                payload['recovery_expression'] = recovery
            if str(proto.get('manual_close')) not in {'0', str(_MANUAL_CLOSE_NO)}:
                payload['manual_close'] = _MANUAL_CLOSE_NO
        elif 'Link down' in name and 'fgate.netif.status' in expr:
            item = f'{FORTIGATE_HTTP_TEMPLATE}/fgate.netif.status[{{#IFKEY}}]'
            control = '{$NET.IF.CONTROL:"{#IFNAME}"}'
            payload.update(
                _linkdown_payload(proto, item, control, '0')
            )
        elif 'Link down' in name and 'fgate.sdwan_health.status' in expr:
            item = f'{FORTIGATE_HTTP_TEMPLATE}/fgate.sdwan_health.status["{{#HID}}.{{#MID}}"]'
            control = '{$SDWAN.HEALTH.IF.CONTROL:"{#NAME}"}'
            payload.update(
                _linkdown_payload(proto, item, control, '1')
            )
        elif 'Link down' in name and 'fgate.sdwan_member.link_status' in expr:
            item = f'{FORTIGATE_HTTP_TEMPLATE}/fgate.sdwan_member.link_status[{{#ID}}]'
            control = '{$SDWAN.MEMBER.IF.CONTROL:"{#NAME}"}'
            payload.update(
                _linkdown_payload(proto, item, control, '1')
            )
        elif 'Link state is error' in name and 'fgate.sdwan_health.status' in expr:
            item = f'{FORTIGATE_HTTP_TEMPLATE}/fgate.sdwan_health.status["{{#HID}}.{{#MID}}"]'
            control = '{$SDWAN.HEALTH.IF.CONTROL:"{#IFNAME}"}'
            payload.update(
                _linkdown_payload(proto, item, control, '2')
            )
        elif 'License' in name:
            wanted = _license_problem_expr(name, expr)
            if expr != wanted:
                payload['expression'] = wanted
            if str(proto.get('manual_close')) not in {'1', str(_MANUAL_CLOSE_YES)}:
                payload['manual_close'] = _MANUAL_CLOSE_YES
        if not payload:
            continue
        api.triggerprototype.update(triggerid=proto['triggerid'], **payload)
        changed += 1
        logger.info('  trigger prototype %s: controls updated', name)
    return {'patched': changed, 'seen': len(protos)}


def _linkdown_payload(proto: dict, item_ref: str, control: str, down_value: str) -> dict:
    wanted = forti_linkdown_problem_expr(item_ref, control, down_value)
    recovery = forti_linkdown_recovery_expr(item_ref, control, down_value)
    payload: dict = {}
    if str(proto.get('expression') or '') != wanted:
        payload['expression'] = wanted
    if str(proto.get('recovery_expression') or '') != recovery:
        payload['recovery_expression'] = recovery
        payload['recovery_mode'] = 1
    if str(proto.get('manual_close')) not in {'0', str(_MANUAL_CLOSE_NO)}:
        payload['manual_close'] = _MANUAL_CLOSE_NO
    return payload


def patch_raw_master_history(api, templateid) -> dict[str, str]:
    """Stock history=0 hides lastclock on the masters operators debug."""
    out: dict[str, str] = {}
    for key in RAW_MASTER_HISTORY_KEYS:
        items = api.item.get(
            hostids=templateid,
            filter={'key_': key},
            output=['itemid', 'history'],
        ) or []
        if not items:
            out[key] = 'missing'
            continue
        item = items[0]
        if str(item.get('history') or '') == RAW_MASTER_HISTORY:
            out[key] = 'ok'
            continue
        api.item.update(itemid=item['itemid'], history=RAW_MASTER_HISTORY)
        out[key] = RAW_MASTER_HISTORY
        logger.info('  %s history=%s', key, RAW_MASTER_HISTORY)
    return out


def patch_slow_item_delays(api, templateid) -> dict[str, str]:
    """Firmware/license are not 1-minute signals. Policy stays disabled separately."""
    out: dict[str, str] = {}
    for key, delay in SLOW_ITEM_DELAYS.items():
        items = api.item.get(
            hostids=templateid,
            filter={'key_': key},
            output=['itemid', 'delay', 'status'],
        ) or []
        if not items:
            out[key] = 'missing'
            continue
        item = items[0]
        if str(item.get('delay') or '') == delay:
            out[key] = 'ok'
            continue
        api.item.update(itemid=item['itemid'], delay=delay)
        out[key] = delay
        logger.info('  %s delay=%s', key, delay)
    return out


def ensure_observability_trigger_dependencies(api, templateid) -> dict[str, int]:
    """Create companion trigger dependencies after import so a fresh import is valid."""
    rows = api.trigger.get(
        templateids=[str(templateid)],
        output=['triggerid', 'description'],
        selectDependencies=['triggerid'],
    )
    by_name: dict[str, dict] = {}
    duplicates: set[str] = set()
    for row in rows:
        name = str(row.get('description') or '')
        if name in by_name:
            duplicates.add(name)
        by_name[name] = row
    required_names = {name for pair in OBSERVABILITY_TRIGGER_DEPENDENCIES for name in pair}
    missing = sorted(required_names - by_name.keys())
    if missing or duplicates:
        details = []
        if missing:
            details.append('missing=' + ', '.join(missing))
        if duplicates:
            details.append('duplicate=' + ', '.join(sorted(duplicates)))
        raise SystemExit('FortiGate Observability trigger dependency resolution failed: ' + '; '.join(details))

    created = 0
    existing = 0
    for child_name, parent_name in OBSERVABILITY_TRIGGER_DEPENDENCIES:
        child = by_name[child_name]
        parent = by_name[parent_name]
        parent_id = str(parent['triggerid'])
        dependency_ids = {str(dep['triggerid']) for dep in child.get('dependencies') or []}
        if parent_id in dependency_ids:


            existing += 1
            continue
        dependency_ids.add(parent_id)
        api.trigger.update(
            triggerid=str(child['triggerid']),
            dependencies=[{'triggerid': triggerid} for triggerid in sorted(dependency_ids, key=int)],
        )
        child.setdefault('dependencies', []).append({'triggerid': parent_id})
        created += 1
        logger.info('  trigger dependency: %s -> %s', child_name, parent_name)
    return {'created': created, 'existing': existing}


def ensure_observability_primary_trigger_gates(api, templateid) -> str:
    """HA-cluster state tickets live on the current primary, not both members."""
    rows = api.trigger.get(
        templateids=[str(templateid)],
        output=['triggerid', 'description', 'expression'],
        expandExpression=True,
    )
    matches = [row for row in rows if row.get('description') == HA_VDOM_TRIGGER]
    if len(matches) != 1:
        raise SystemExit(
            f'FortiGate Observability primary-gate resolution expected one {HA_VDOM_TRIGGER!r}, '
            f'found {len(matches)}'
        )
    trigger = matches[0]
    expression = str(trigger.get('expression') or '')
    if HA_VDOM_PRIMARY_GATE in expression:
        return 'existing'
    if not expression:
        raise SystemExit(f'{HA_VDOM_TRIGGER} has an empty expression')
    api.trigger.update(
        triggerid=str(trigger['triggerid']),
        expression=f'{HA_VDOM_PRIMARY_GATE} and ({expression})',
    )
    logger.info('  trigger primary gate: %s', HA_VDOM_TRIGGER)
    return 'updated'


def _with_vdom_label(name: str) -> str:
    """Make all-VDOM discovered entities unambiguous without renaming unrelated rows."""
    if not name or '{#VDOM}' in name:
        return name
    for prefix in ('FortiGate: Interface ', 'Interface ', 'FortiGate: SD-WAN ', 'SD-WAN '):
        if name.startswith(prefix):
            return prefix + '[{#VDOM}]:' + name[len(prefix):]
    return name


def patch_vdom_lld_metadata(api, templateid) -> dict[str, int]:
    """Expose {#VDOM} and include it in all interface/SD-WAN prototype labels."""
    keys = ('fgate.netif.discovery', 'fgate.sdwan_health.discovery', 'fgate.sdwan_member.discovery')
    rules = api.discoveryrule.get(
        templateids=[str(templateid)],
        filter={'key_': list(keys)},
        output=['itemid', 'key_'],
        selectLLDMacroPaths='extend',
    )
    found = {str(rule.get('key_')) for rule in rules}
    missing = sorted(set(keys) - found)
    if missing:
        raise SystemExit('FortiGate VDOM LLD metadata rules missing: ' + ', '.join(missing))

    updated = {'rules': 0, 'items': 0, 'graphs': 0, 'triggers': 0}
    for rule in rules:
        paths = list(rule.get('lld_macro_paths') or [])
        if not any(path.get('lld_macro') == '{#VDOM}' for path in paths):
            paths.append({'lld_macro': '{#VDOM}', 'path': '$.vdom'})
            api.discoveryrule.update(itemid=rule['itemid'], lld_macro_paths=paths)
            updated['rules'] += 1

        for item in api.itemprototype.get(
            discoveryids=[str(rule['itemid'])],
            output=['itemid', 'name'],
        ):
            wanted = _with_vdom_label(str(item.get('name') or ''))
            if wanted != item.get('name'):
                api.itemprototype.update(itemid=item['itemid'], name=wanted)
                updated['items'] += 1

        for graph in api.graphprototype.get(
            discoveryids=[str(rule['itemid'])],
            output=['graphid', 'name'],
        ):
            wanted = _with_vdom_label(str(graph.get('name') or ''))
            if wanted != graph.get('name'):
                api.graphprototype.update(graphid=graph['graphid'], name=wanted)
                updated['graphs'] += 1

        for trigger in api.triggerprototype.get(
            discoveryids=[str(rule['itemid'])],
            output=['triggerid', 'description', 'event_name'],
        ):
            payload = {}
            description = _with_vdom_label(str(trigger.get('description') or ''))
            event_name = _with_vdom_label(str(trigger.get('event_name') or ''))
            if description != trigger.get('description'):
                payload['description'] = description
            if event_name != trigger.get('event_name'):
                payload['event_name'] = event_name
            if payload:
                api.triggerprototype.update(triggerid=trigger['triggerid'], **payload)
                updated['triggers'] += 1
    logger.info('  VDOM LLD labels: %s', updated)
    return updated


def apply_fortigate_http_patches(api, templateid) -> dict:
    """Fail closed: version-pinned HTTP compatibility fixes before NetBox writes."""
    logger.info('Network: patch live %s (no YAML import)', FORTIGATE_HTTP_TEMPLATE)
    zbx = patch_zbx27082_items(api, templateid)
    collectors = patch_vdom_star_items(api, templateid)
    vdom_metadata = patch_vdom_lld_metadata(api, templateid)
    remaining = inspect_http_scripts(api, templateid)
    still = [key for key, state in remaining.items() if state == 'vulnerable']
    if still:
        raise SystemExit(
            'ZBX-27082 still present after patch on: ' + ', '.join(still)
            + '. Aborting — multi-request items (SD-WAN) would 401.'
        )
    ha = ensure_ha_role_item(api, templateid)
    if script_has_zbx27082(HA_ROLE_SCRIPT):
        raise SystemExit('HA role script is itself ZBX-27082-vulnerable — abort')
    macros = upsert_http_template_macros(api, templateid)
    capacity = disable_unavailable_capacity_items(api, templateid)
    policy = disable_policy_collection(api, templateid)
    wan = patch_wan_state_triggers(api, templateid)
    delays = patch_slow_item_delays(api, templateid)
    history = patch_raw_master_history(api, templateid)
    return {
        'zbx27082': zbx,
        'collector_compatibility': collectors,
        'vdom_metadata': vdom_metadata,
        'ha_role': ha,
        'macros': macros,
        'policy': policy,
        'capacity_items': capacity,
        'wan_triggers': wan,
        'delays': delays,
        'history': history,
    }
