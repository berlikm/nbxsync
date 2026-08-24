#!/usr/bin/env python3
"""Zabbix API patches for FortiGate by HTTP (no Django).

Surgical updates on the live Cloud parent (Zabbix 7.0-2). Do not
configuration.import the bundled 7.0-3 YAML.
"""

from __future__ import annotations

import logging

from fortigate_http import (
    FORTIGATE_HTTP_TEMPLATE,
    FORTIOS_PLATFORM_MACROS,
    HA_ROLE_KEY,
    POLICY_DISCOVERY_KEY,
    POLICY_MASTER_KEY,
    FORTIGATE_HTTP_CLOUD_VENDOR,
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
    """Fail closed: ZBX-27082 must be gone, then vdom=* iface/SD-WAN, before NetBox writes."""
    logger.info('Network: patch live %s (no YAML import)', FORTIGATE_HTTP_TEMPLATE)
    zbx = patch_zbx27082_items(api, templateid)
    remaining = inspect_http_scripts(api, templateid)
    still = [key for key, state in remaining.items() if state == 'vulnerable']
    if still:
        raise SystemExit(
            'ZBX-27082 still present after patch on: ' + ', '.join(still)
            + '. Aborting — multi-request items (SD-WAN) would 401.'
        )
    vdom = patch_vdom_star_items(api, templateid)
    ha = ensure_ha_role_item(api, templateid)
    if script_has_zbx27082(HA_ROLE_SCRIPT):
        raise SystemExit('HA role script is itself ZBX-27082-vulnerable — abort')
    macros = upsert_http_template_macros(api, templateid)
    policy = disable_policy_collection(api, templateid)
    wan = patch_wan_state_triggers(api, templateid)
    delays = patch_slow_item_delays(api, templateid)
    return {
        'zbx27082': zbx,
        'vdom_star': vdom,
        'ha_role': ha,
        'macros': macros,
        'policy': policy,
        'wan_triggers': wan,
        'delays': delays,
    }
