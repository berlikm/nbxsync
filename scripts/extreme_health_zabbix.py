#!/usr/bin/env python3
"""Idempotent Extreme Health / alerting patches for a live Zabbix 7 API.

Used by ``configure_nbxsync_network.py`` and lab smokes. No Django. Never
deletes hosts. EXOS Health ships on the ``Extreme EXOS Observability``
companion; the stock interface dashboard receives a layout-only grid patch.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger('extreme_health_zabbix')


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
EXOS_STOCK_TEMPLATE = 'Extreme EXOS by SNMP'
EXOS_INTERFACE_DASHBOARD = 'Network interfaces'
EXOS_TRAFFIC_GRAPH = 'Interface {#IFNAME}({#IFALIAS}): Network traffic'


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
        all_tr = (
            api_call(
                api,
                'trigger.get',
                {'hostids': tid, 'output': ['triggerid', 'status', 'description']},
            )
            or []
        )
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
    dashes = (
        api_call(
            api,
            'templatedashboard.get',
            {
                'templateids': tid,
                'output': ['dashboardid', 'name'],
                'selectPages': ['name'],
            },
        )
        or []
    )
    match = [d for d in dashes if d.get('name') == dash_name]
    if not match:
        return False, f'no {dash_name!r} dashboard; have={[d.get("name") for d in dashes]}'
    got_pages = [p.get('name') for p in (match[0].get('pages') or [])]
    # First page may be unnamed on some imports; require named pages we care about.
    ok = all(p in got_pages for p in pages)
    return ok, f'pages={got_pages}'


def patch_exos_stock_interface_dashboard(api: Any) -> str:
    """Make the stock EXOS interface dashboard match the VOSS/IQ map + click-history + grid."""
    tid = _template_id(api, EXOS_STOCK_TEMPLATE)
    if not tid:
        return 'missing-template'
    dashboards = (
        api_call(
            api,
            'templatedashboard.get',
            {
                'templateids': tid,
                'output': ['dashboardid', 'name'],
                'selectPages': 'extend',
            },
        )
        or []
    )
    dashboard = next((d for d in dashboards if d.get('name') == EXOS_INTERFACE_DASHBOARD), None)
    if not dashboard:
        return 'missing-dashboard'
    pages = dashboard.get('pages') or []
    if not pages:
        return 'missing-page'
    graphs = (
        api_call(
            api,
            'graphprototype.get',
            {
                'templateids': tid,
                'output': ['graphid', 'name'],
                'filter': {'name': [EXOS_TRAFFIC_GRAPH]},
            },
        )
        or []
    )
    if not graphs:
        return 'missing-graph'
    graphid = str(graphs[0]['graphid'])
    page = pages[0]
    widgets = page.get('widgets') or []

    def field_map(widget: dict) -> dict[str, str]:
        return {str(f.get('name')): str(f.get('value')) for f in (widget.get('fields') or [])}

    map_widget = next((w for w in widgets if w.get('type') == 'honeycomb'), {})
    item_widget = next((w for w in widgets if w.get('type') == 'item'), {})
    svg_widget = next((w for w in widgets if w.get('type') == 'svggraph'), {})
    grid_widget = next((w for w in widgets if w.get('type') == 'graphprototype'), {})
    grid_fields = field_map(grid_widget)
    item_fields = field_map(item_widget)
    svg_fields = field_map(svg_widget)
    already = (
        page.get('name') == 'Overview'
        and map_widget.get('width') == '36'
        and map_widget.get('height') == '8'
        and item_fields.get('itemid._reference') == 'EIMAP._itemid'
        and svg_fields.get('ds.0.itemids.0._reference') == 'EIMAP._itemid'
        and grid_widget.get('width') == '72'
        and grid_widget.get('height') == '11'
        and grid_widget.get('y') == '8'
        and grid_fields.get('columns') == '3'
        and grid_fields.get('rows') == '2'
        and grid_fields.get('graphid.0') == graphid
    )
    if already:
        return 'ok'

    desired_widgets = [
        {
            'type': 'honeycomb',
            'name': 'Interface map',
            'x': '0',
            'y': '0',
            'width': '36',
            'height': '8',
            'view_mode': '0',
            'fields': [
                {'type': '1', 'name': 'items.0', 'value': 'Interface *: Operational status'},
                {
                    'type': '1',
                    'name': 'primary_label',
                    'value': '{{ITEM.NAME}.regsub("^Interface (.*): Operational status$","\\1")}',
                },
                {'type': '1', 'name': 'reference', 'value': 'EIMAP'},
                {'type': '1', 'name': 'thresholds.0.color', 'value': '878787'},
                {'type': '1', 'name': 'thresholds.0.threshold', 'value': '0'},
                {'type': '1', 'name': 'thresholds.1.color', 'value': '0EC9AC'},
                {'type': '1', 'name': 'thresholds.1.threshold', 'value': '1'},
                {'type': '1', 'name': 'thresholds.2.color', 'value': 'FF465C'},
                {'type': '1', 'name': 'thresholds.2.threshold', 'value': '2'},
            ],
        },
        {
            'type': 'item',
            'name': 'Selected interface',
            'x': '36',
            'y': '0',
            'width': '36',
            'height': '2',
            'view_mode': '0',
            'fields': [
                {'type': '1', 'name': 'itemid._reference', 'value': 'EIMAP._itemid'},
                {'type': '0', 'name': 'show.0', 'value': '1'},
                {'type': '0', 'name': 'show.1', 'value': '2'},
                {'type': '0', 'name': 'value_size', 'value': '25'},
            ],
        },
        {
            'type': 'svggraph',
            'name': 'Selected interface history',
            'x': '36',
            'y': '2',
            'width': '36',
            'height': '6',
            'view_mode': '0',
            'fields': [
                {'type': '1', 'name': 'ds.0.color.0', 'value': '42A5F5'},
                {'type': '0', 'name': 'ds.0.dataset_type', 'value': '0'},
                {'type': '1', 'name': 'ds.0.itemids.0._reference', 'value': 'EIMAP._itemid'},
                {'type': '1', 'name': 'reference', 'value': 'EIHST'},
                {'type': '0', 'name': 'righty', 'value': '0'},
            ],
        },
        {
            'type': 'graphprototype',
            'name': 'Interface traffic and errors',
            'x': '0',
            'y': '8',
            'width': '72',
            'height': '11',
            'view_mode': '0',
            'fields': [
                {'type': '0', 'name': 'columns', 'value': '3'},
                {'type': '7', 'name': 'graphid.0', 'value': graphid},
                {'type': '1', 'name': 'reference', 'value': 'ETGRD'},
                {'type': '0', 'name': 'rows', 'value': '2'},
            ],
        },
    ]
    api_call(
        api,
        'templatedashboard.update',
        {
            'dashboardid': dashboard['dashboardid'],
            'pages': [
                {
                    'dashboard_pageid': page['dashboard_pageid'],
                    'name': 'Overview',
                    'display_period': page.get('display_period', '0'),
                    'widgets': desired_widgets,
                }
            ],
        },
    )
    logger.info('  %s: interface dashboard updated to map + click-history + 3x2 grid', EXOS_STOCK_TEMPLATE)
    return 'patched'


def assert_exos_stock_interface_grid(api: Any) -> tuple[bool, str]:
    status = patch_exos_stock_interface_dashboard(api)
    return status in ('ok', 'patched', 'missing-template'), status


def apply_extreme_health_patches(api: Any) -> dict[str, Any]:
    """Apply idempotent Health and stock EXOS interface-layout patches."""
    icmp = patch_disable_wan_icmp_noise(api)
    exos_grid = patch_exos_stock_interface_dashboard(api)
    return {
        'icmp_noise': icmp,
        'exos_health': 'companion-yaml',
        'exos_stock_grid': exos_grid,
    }
