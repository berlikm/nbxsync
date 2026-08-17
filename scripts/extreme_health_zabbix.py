#!/usr/bin/env python3
"""Idempotent Extreme Health / alerting patches for a live Zabbix 7 API.

Used by ``configure_nbxsync_network.py`` (pyzabbix) and lab smokes
(``zabbix_api.ZabbixAPI.call``). No Django. Never deletes hosts.

Stock Extreme EXOS is not forked: ICMP loss/RTT triggers are disabled via
``trigger.update``, and host dashboard **Health** is upserted beside the
upstream **Network interfaces** board.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger('extreme_health_zabbix')

# Zabbix 7.0 dashboard widget field types (include/classes/widgets).
_FIELD_INT32 = 0
_FIELD_STR = 1
_FIELD_ITEM = 4
_FIELD_GRAPH = 6
_FIELD_GRAPH_PROTOTYPE = 7

_TRIGGER_DISABLED = 1

ICMP_NOISE_TRIGGER_NAMES = {
    'Extreme EXOS by SNMP': (
        'Extreme EXOS: High ICMP ping loss',
        'Extreme EXOS: High ICMP ping response time',
    ),
    'Extreme VOSS by SNMP': (
        'Extreme VOSS: High ICMP ping loss',
        'Extreme VOSS: High ICMP ping response time',
    ),
    'Extreme IQ Engine by SNMP': (
        'Extreme IQ Engine: High ICMP ping loss',
        'Extreme IQ Engine: High ICMP ping response time',
    ),
}

VOSS_HEALTH_MACROS = {
    '{$ISIS.CONTROL}': '0',
    '{$CARD.CONTROL}': '0',
    '{$UNSUPPORTED.MAX}': '5',
    '{$IF.UTIL.MAX}': '101',
    '{$VIST.CONTROL}': '0',
}

SPEED_EXPECT_HEALTH_MACROS = {
    '{$IF.UTIL.MAX}': '101',
    '{$IF.UTIL.MAX:"USW"}': '101',
}

IQ_HEALTH_MACROS = {
    '{$UNSUPPORTED.MAX}': '5',
}

EXOS_CPU_KEY = 'system.cpu.util[extremeCpuMonitorTotalUtilization.0]'
EXOS_SNMP_KEY = 'zabbix[host,snmp,available]'
EXOS_ICMP_KEY = 'icmpping'
EXOS_CPU_GRAPH = 'Extreme EXOS: CPU utilization'
EXOS_MEM_GRAPH_PROTO = '#{#SNMPVALUE}: Memory utilization'
EXOS_IF_GRAPH_PROTO = 'Interface {#IFNAME}({#IFALIAS}): Network traffic'


def api_call(api: Any, method: str, params: dict | None = None) -> Any:
    """Call a Zabbix method on either pyzabbix or ``ZabbixAPI.call``."""
    params = params or {}
    # scripts.zabbix_api.ZabbixAPI has .call and no dotted method objects.
    if hasattr(api, 'call') and callable(api.call) and not hasattr(api, 'template'):
        return api.call(method, params)
    obj_name, meth_name = method.split('.', 1)
    return getattr(getattr(api, obj_name), meth_name)(**params)


def _template_id(api: Any, name: str) -> str | None:
    found = api_call(api, 'template.get', {'filter': {'name': [name]}, 'output': ['templateid', 'name']}) or []
    if not found:
        return None
    return str(found[0]['templateid'])


def _macro_map(api: Any, hostid: str) -> dict[str, str]:
    rows = api_call(api, 'usermacro.get', {'hostids': hostid, 'output': ['macro', 'value']}) or []
    return {m['macro']: m.get('value', '') for m in rows if isinstance(m, dict) and m.get('macro')}


def _trigger_name(trig: dict) -> str:
    """Zabbix API stores the visible trigger name in ``description`` (YAML uses ``name``)."""
    return str(trig.get('description') or trig.get('name') or '')


def patch_disable_wan_icmp_noise(
    api: Any,
    template_names: tuple[str, ...] | None = None,
) -> dict[str, str]:
    """Disable ICMP loss/RTT triggers. Items stay for the Health dashboard.

    CH proxy RTT/loss is a WAN signal, not chassis health. Idempotent.
    Matches on the API ``description`` field only (that is the visible name;
    YAML ``name``). Never bulk-disable: ``trigger.get`` ``filter.name`` is not
    reliable and would mute ICMP-down / temp / SNMP-dead on stock EXOS.
    """
    logger.info('Network: disable WAN ICMP loss/RTT triggers')
    names = template_names or tuple(ICMP_NOISE_TRIGGER_NAMES)
    results: dict[str, str] = {}
    for name in names:
        tid = _template_id(api, name)
        if not tid:
            results[name] = 'missing'
            logger.info('  %s: template not found — skip ICMP noise patch', name)
            continue
        wanted = set(ICMP_NOISE_TRIGGER_NAMES.get(name, ()))
        if not wanted:
            results[name] = 'no-names'
            continue
        all_tr = api_call(
            api,
            'trigger.get',
            {'hostids': tid, 'output': ['triggerid', 'status', 'description']},
        ) or []
        triggers = [t for t in all_tr if _trigger_name(t) in wanted]
        if not triggers:
            results[name] = 'no-triggers'
            logger.info('  %s: ICMP loss/RTT triggers absent — skip', name)
            continue
        patched = 0
        already = 0
        for trig in triggers:
            if str(trig.get('status')) == str(_TRIGGER_DISABLED):
                already += 1
                continue
            api_call(api, 'trigger.update', {'triggerid': trig['triggerid'], 'status': _TRIGGER_DISABLED})
            patched += 1
        results[name] = 'ok' if patched == 0 else 'patched'
        logger.info('  %s: ICMP noise triggers disabled (patched=%s already=%s)', name, patched, already)
    return results


def assert_wan_icmp_noise_disabled(api: Any, template_name: str) -> tuple[bool, str]:
    tid = _template_id(api, template_name)
    if not tid:
        return True, 'template absent — n/a'
    wanted = ICMP_NOISE_TRIGGER_NAMES.get(template_name, ())
    if not wanted:
        return True, 'no-names'
    all_tr = api_call(api, 'trigger.get', {'hostids': tid, 'output': ['triggerid', 'status', 'description']}) or []
    by_name = {_trigger_name(t): t for t in all_tr}
    missing = [n for n in wanted if n not in by_name]
    if missing:
        # Stock stub / YAML not yet imported
        return True, f'triggers absent {missing} — n/a'
    enabled = [n for n in wanted if str(by_name[n].get('status')) != str(_TRIGGER_DISABLED)]
    return not enabled, f'enabled={enabled or "none"}'


def assert_template_macros(api: Any, template_name: str, expected: dict[str, str]) -> tuple[bool, str]:
    tid = _template_id(api, template_name)
    if not tid:
        return True, 'template absent — n/a'
    have = _macro_map(api, tid)
    detail = {k: have.get(k) for k in expected}
    ok = all(have.get(k) == v for k, v in expected.items())
    return ok, str(detail)


def assert_template_dashboard(
    api: Any,
    template_name: str,
    dash_name: str = 'Health',
    pages: tuple[str, ...] = ('Health',),
) -> tuple[bool, str]:
    tid = _template_id(api, template_name)
    if not tid:
        return True, 'template absent — n/a'
    dashes = api_call(
        api,
        'templatedashboard.get',
        {
            'templateids': tid,
            'output': ['dashboardid', 'name'],
            'selectPages': ['name'],
        },
    ) or []
    match = [d for d in dashes if d.get('name') == dash_name]
    if not match:
        return False, f'no {dash_name!r} dashboard; have={[d.get("name") for d in dashes]}'
    got_pages = [p.get('name') for p in (match[0].get('pages') or [])]
    # First page may be unnamed on some imports; require named pages we care about.
    ok = all(p in got_pages for p in pages)
    return ok, f'pages={got_pages}'


def _item_id(api: Any, templateid: str, key: str) -> str | None:
    rows = api_call(
        api,
        'item.get',
        {'hostids': templateid, 'filter': {'key_': key}, 'output': ['itemid', 'key_']},
    ) or []
    return str(rows[0]['itemid']) if rows else None


def _graph_id(api: Any, templateid: str, name: str) -> str | None:
    rows = api_call(
        api,
        'graph.get',
        {'hostids': templateid, 'filter': {'name': name}, 'output': ['graphid', 'name']},
    ) or []
    return str(rows[0]['graphid']) if rows else None


def _graphproto_id(api: Any, templateid: str, name: str) -> str | None:
    rows = api_call(
        api,
        'graphprototype.get',
        {'hostids': templateid, 'filter': {'name': name}, 'output': ['graphid', 'name']},
    ) or []
    return str(rows[0]['graphid']) if rows else None


def _field(ftype: int, name: str, value: Any) -> dict:
    return {'type': ftype, 'name': name, 'value': str(value)}


def _exos_health_pages(ids: dict[str, str]) -> list[dict]:
    health_widgets = [
        {
            'type': 'item',
            'name': 'ICMP',
            'x': 0,
            'y': 0,
            'width': 18,
            'height': 4,
            'fields': [
                _field(_FIELD_INT32, 'decimal_places', 0),
                _field(_FIELD_ITEM, 'itemid.0', ids['icmp']),
                _field(_FIELD_INT32, 'show.0', 2),
                _field(_FIELD_INT32, 'show.1', 4),
                _field(_FIELD_STR, 'reference', 'EICMP'),
            ],
        },
        {
            'type': 'item',
            'name': 'SNMP',
            'x': 18,
            'y': 0,
            'width': 18,
            'height': 4,
            'fields': [
                _field(_FIELD_INT32, 'decimal_places', 0),
                _field(_FIELD_ITEM, 'itemid.0', ids['snmp']),
                _field(_FIELD_INT32, 'show.0', 2),
                _field(_FIELD_INT32, 'show.1', 4),
                _field(_FIELD_STR, 'reference', 'ESNMP'),
            ],
        },
        {
            'type': 'item',
            'name': 'CPU',
            'x': 36,
            'y': 0,
            'width': 18,
            'height': 4,
            'fields': [
                _field(_FIELD_INT32, 'decimal_places', 0),
                _field(_FIELD_ITEM, 'itemid.0', ids['cpu']),
                _field(_FIELD_INT32, 'show.0', 2),
                _field(_FIELD_INT32, 'show.1', 4),
                _field(_FIELD_STR, 'reference', 'ECPU0'),
            ],
        },
        {
            'type': 'graph',
            'name': 'CPU',
            'x': 0,
            'y': 4,
            'width': 36,
            'height': 5,
            'fields': [
                _field(_FIELD_GRAPH, 'graphid', ids['cpu_graph']),
                _field(_FIELD_STR, 'reference', 'ECPUG'),
            ],
        },
    ]
    if ids.get('mem_gp'):
        health_widgets.append(
            {
                'type': 'graphprototype',
                'name': 'Memory',
                'x': 36,
                'y': 4,
                'width': 36,
                'height': 5,
                'fields': [
                    _field(_FIELD_INT32, 'columns', 1),
                    _field(_FIELD_GRAPH_PROTOTYPE, 'graphid.0', ids['mem_gp']),
                    _field(_FIELD_STR, 'reference', 'EMEMG'),
                ],
            }
        )
    pages = [{'name': 'Health', 'widgets': health_widgets}]
    if ids.get('if_gp'):
        pages.append(
            {
                'name': 'Path',
                'widgets': [
                    {
                        'type': 'graphprototype',
                        'x': 0,
                        'y': 0,
                        'width': 72,
                        'height': 5,
                        'fields': [
                            _field(_FIELD_INT32, 'columns', 2),
                            _field(_FIELD_GRAPH_PROTOTYPE, 'graphid.0', ids['if_gp']),
                            _field(_FIELD_STR, 'reference', 'EIFTR'),
                        ],
                    }
                ],
            }
        )
    return pages


def upsert_exos_health_dashboard(api: Any, template_name: str = 'Extreme EXOS by SNMP') -> str:
    """Create or update host dashboard Health on stock EXOS. Never fails the caller.

    Keeps upstream **Network interfaces**. Returns a status token; logs errors.
    """
    logger.info('Network: upsert EXOS Health dashboard')
    try:
        tid = _template_id(api, template_name)
        if not tid:
            logger.warning('  %s: template not found — skip Health dashboard', template_name)
            return 'missing'
        ids = {
            'icmp': _item_id(api, tid, EXOS_ICMP_KEY),
            'snmp': _item_id(api, tid, EXOS_SNMP_KEY),
            'cpu': _item_id(api, tid, EXOS_CPU_KEY),
            'cpu_graph': _graph_id(api, tid, EXOS_CPU_GRAPH),
            'mem_gp': _graphproto_id(api, tid, EXOS_MEM_GRAPH_PROTO),
            'if_gp': _graphproto_id(api, tid, EXOS_IF_GRAPH_PROTO),
        }
        required = ('icmp', 'snmp', 'cpu', 'cpu_graph')
        missing = [k for k in required if not ids.get(k)]
        if missing:
            logger.info('  %s: Health skip — missing %s (lab stub?)', template_name, missing)
            return 'no-items'
        pages = _exos_health_pages({k: v for k, v in ids.items() if v})
        existing = api_call(
            api,
            'templatedashboard.get',
            {
                'templateids': tid,
                'filter': {'name': 'Health'},
                'output': ['dashboardid', 'name'],
                'selectPages': ['name'],
            },
        ) or []
        payload_pages = pages
        if existing:
            dashid = existing[0]['dashboardid']
            api_call(
                api,
                'templatedashboard.update',
                {'dashboardid': dashid, 'name': 'Health', 'pages': payload_pages},
            )
            logger.info('  %s: updated Health dashboard id=%s', template_name, dashid)
            return 'ok'
        api_call(
            api,
            'templatedashboard.create',
            {'templateid': tid, 'name': 'Health', 'pages': payload_pages},
        )
        logger.info('  %s: created Health dashboard', template_name)
        return 'created'
    except Exception as exc:  # noqa: BLE001 — apply must not fail on dashboard UX
        logger.warning('  EXOS Health dashboard upsert failed (non-fatal): %s', exc)
        return f'error:{exc}'


def apply_extreme_health_patches(api: Any) -> dict[str, Any]:
    """Run the Health/alerting API patches used by ``--apply`` / lab import."""
    icmp = patch_disable_wan_icmp_noise(api)
    dash = upsert_exos_health_dashboard(api)
    return {'icmp_noise': icmp, 'exos_health': dash}
