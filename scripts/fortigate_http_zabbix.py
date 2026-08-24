#!/usr/bin/env python3
"""Zabbix API patches for FortiGate by HTTP (no Django).

Surgical updates on the live Cloud parent (Zabbix 7.0-2). Do not
configuration.import the bundled 7.0-3 YAML.
"""

from __future__ import annotations

import logging

from fortigate_http import (
    FORTIGATE_HTTP_TEMPLATE,
    FORTIGATE_OBSERVABILITY_TEMPLATE,
    FORTIOS_PLATFORM_MACROS,
    HA_ROLE_KEY,
    OVERLAY_INVENTORY_KEY,
    POLICY_DISCOVERY_KEY,
    POLICY_MASTER_KEY,
    FORTIGATE_HTTP_CLOUD_VENDOR,
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
    script_is_vdom_mutated,
    stock_http_collector_script,
    with_ha_role_gate,
)

logger = logging.getLogger(__name__)

# Zabbix 7 script item type.
_SCRIPT_TYPE = 21
_DISABLED = 1
_MANUAL_CLOSE_NO = 0

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

var api_url = params.scheme + '://' + params.fqdn + ':' + params.port;
try {
	var status = getHttpData(api_url + '/api/v2/monitor/system/status');
	var serial = (status.serial || (status.results && status.results.serial) || '').toString();
	var ha;
	try {
		ha = getHttpData(api_url + '/api/v2/monitor/system/ha/checksums');
	} catch (e) {
		return 1;
	}
	var rows = ha.results || ha;
	if (!rows || (Array.isArray(rows) && rows.length === 0)) {
		return 1;
	}
	if (!Array.isArray(rows)) {
		if (rows.mode === 'standalone' || typeof rows.is_manage_master === 'undefined') {
			return 1;
		}
		rows = [rows];
	}
	for (var i = 0; i < rows.length; i++) {
		var row = rows[i];
		var row_serial = (row.serial_no || row.serial || '').toString();
		if (serial && row_serial && row_serial === serial) {
			return (row.is_manage_master === true || row.is_manage_master === 1) ? 1 : 0;
		}
	}
	return 1;
} catch (error) {
	return 1;
}
'''

# Standalone overlay census. Functions are program-scope — never splice into
# stock getHttpData. 424/404 on one endpoint leaves the others.
OVERLAY_INVENTORY_SCRIPT = r'''var params = JSON.parse(value);

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
		return { code: 0, body: null };
	}
	var parsed = null;
	if (raw !== null && String(raw) !== '') {
		try {
			parsed = JSON.parse(raw);
		} catch (e2) {
			parsed = null;
		}
	}
	if (parsed && typeof parsed === 'object' && !Array.isArray(parsed) && parsed.status == 'error' && typeof parsed.http_status !== 'undefined') {
		code = parsed.http_status;
	}
	return { code: code, body: parsed };
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

function overlayFetch(base, path) {
	var sep = path.indexOf('?') >= 0 ? '&' : '?';
	var star = overlayRaw(base + path + sep + 'vdom=*');
	if (overlayOk(star)) {
		return star.body;
	}
	if (star.code === 424 || star.code === 404) {
		return null;
	}
	var plain = overlayRaw(base + path);
	return overlayOk(plain) ? plain.body : null;
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
					out.push({ vdom: vdom, interface: String(row.interface || row.name) });
				}
			});
			return;
		}
		if (typeof res === 'object') {
			Object.keys(res).forEach(function (k) {
				var row = res[k] || {};
				var name = row.interface || row.name || k;
				out.push({ vdom: vdom, interface: String(name) });
			});
		}
	});
	return out;
}

function overlayHealthRows(payload) {
	var out = [];
	overlayBlocks(payload).forEach(function (block) {
		if (!block || block.status == 'error') {
			return;
		}
		var vdom = block.vdom || '';
		var res = block.results;
		if (!res || typeof res !== 'object') {
			return;
		}
		var keys = Array.isArray(res) ? res.map(function (row, i) { return row && (row.name || row.q_origin_key) || String(i); }) : Object.keys(res);
		keys.forEach(function (name) {
			if (name) {
				out.push({ vdom: vdom, name: String(name) });
			}
		});
	});
	return out;
}

function overlayIpsecRows(payload) {
	var out = [];
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
					out.push({ vdom: vdom, name: String(name) });
				}
			});
			return;
		}
		if (typeof res === 'object') {
			Object.keys(res).forEach(function (k) {
				out.push({ vdom: vdom, name: String(k) });
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
	out.error = String(e);
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


def restore_stock_http_scripts(api, templateid) -> dict[str, str]:
    """Put vendor netif/SD-WAN collectors back (ZBX-27082 only).

    In-place vdom=* rewrites hid names from Duktape and emptied LLD. All-VDOM
    census belongs on FortiGate Observability, not on the stock parent.
    """
    results: dict[str, str] = {}
    remaining = []
    items = {item['key_']: item for item in _script_items(api, templateid)}
    for key in VDOM_STAR_SCRIPT_KEYS:
        item = items.get(key)
        if item is None:
            remaining.append(key)
            results[key] = 'missing'
            continue
        stock = stock_http_collector_script(key)
        if script_has_zbx27082(stock):
            remaining.append(key)
            results[key] = 'zbx27082'
            continue
        current = item.get('params') or ''
        if current == stock:
            results[key] = 'ok'
            continue
        api.item.update(itemid=item['itemid'], params=stock)
        results[key] = 'restored' if script_is_vdom_mutated(current) else 'aligned'
        logger.info('  %s: stock HTTP collector (ZBX-27082 only)', key)
    if remaining:
        raise SystemExit(
            'stock HTTP restore failed on: ' + ', '.join(remaining)
            + '. Aborting — mutated collectors would keep empty LLD.'
        )
    return results


def patch_vdom_star_items(api, templateid) -> dict[str, str]:
    """Stock HTTP is current-VDOM only. Fail closed if vdom=* cannot be applied."""
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
        if script_has_vdom_star(script):
            results[key] = 'ok'
            continue
        patched = patch_vdom_star_script(script)
        if not script_has_vdom_star(patched):
            remaining.append(key)
            results[key] = 'unpatched'
            continue
        if script_has_zbx27082(patched):
            remaining.append(key)
            results[key] = 'zbx27082'
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
    """Primary/standalone=1 on the HTTP parent so path triggers can gate."""
    found = api.item.get(
        hostids=templateid,
        filter={'key_': HA_ROLE_KEY},
        output=['itemid', 'params', 'type'],
    ) or []
    if found:
        item = found[0]
        if script_has_zbx27082(item.get('params') or ''):
            api.item.update(itemid=item['itemid'], params=HA_ROLE_SCRIPT)
            logger.info('  %s: replaced vulnerable HA role script', HA_ROLE_KEY)
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
        description=(
            '1 = primary or standalone (path tickets). 0 = secondary. '
            'New HttpRequest per call (ZBX-27082).'
        ),
    )
    logger.info('  created %s on %s', HA_ROLE_KEY, FORTIGATE_HTTP_TEMPLATE)
    return 'created'


def ensure_overlay_census_items(api, templateid) -> str:
    """All-VDOM SD-WAN + IPsec names on Observability. See first, trigger later."""
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
            'IPsec names. Not a path trigger. 424 on one endpoint keeps the rest.'
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
        expandExpression='true',
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
            wanted = with_ha_role_gate(expr)
            if expr != wanted:
                payload['expression'] = wanted
            if str(proto.get('manual_close')) not in {'0', str(_MANUAL_CLOSE_NO)}:
                payload['manual_close'] = _MANUAL_CLOSE_NO
        if not payload:
            continue
        api.triggerprototype.update(triggerid=proto['triggerid'], **payload)
        changed += 1
        logger.info('  trigger prototype %s: sustained state, no manual close', name)
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


def apply_fortigate_http_patches(api, templateid) -> dict:
    """Fail closed: ZBX-27082 gone, stock collectors restored, before NetBox writes."""
    logger.info('Network: patch live %s (no YAML import)', FORTIGATE_HTTP_TEMPLATE)
    restored = restore_stock_http_scripts(api, templateid)
    zbx = patch_zbx27082_items(api, templateid)
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
    policy = disable_policy_collection(api, templateid)
    wan = patch_wan_state_triggers(api, templateid)
    delays = patch_slow_item_delays(api, templateid)
    history = patch_raw_master_history(api, templateid)
    return {
        'zbx27082': zbx,
        'stock_scripts': restored,
        'ha_role': ha,
        'macros': macros,
        'policy': policy,
        'wan_triggers': wan,
        'delays': delays,
        'history': history,
    }
