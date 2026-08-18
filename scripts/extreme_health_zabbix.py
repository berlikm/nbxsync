#!/usr/bin/env python3
"""Idempotent Extreme Health / alerting patches for a live Zabbix 7 API.

Used by ``configure_nbxsync_network.py`` and lab smokes. No Django. Never
deletes hosts. EXOS Health ships on the ``Extreme EXOS Observability``
companion; the stock interface dashboard receives a layout-only Overview + Port
patch. Leftover Health Diagnostics pages are dropped on ``--apply``.
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
EXOS_PORT_COUNTERS = (
    'Interface *: Operational status',
    'Interface *: Speed',
    'Interface *: Duplex status',
    'Interface *: Inbound packets with errors',
    'Interface *: Outbound packets with errors',
    'Interface *: Inbound packets discarded',
    'Interface *: Outbound packets discarded',
)
HEALTH_TEMPLATES = (
    'Extreme VOSS by SNMP',
    'Extreme IQ Engine by SNMP',
    'Extreme EXOS Observability',
)
IQ_TEMPLATE = 'Extreme IQ Engine by SNMP'
IQ_INTERFACE_DASHBOARD = 'Network interfaces'


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


def _exos_overview_widgets(graphid: str) -> list[dict]:
    return [
        {
            'type': 'honeycomb',
            'name': 'Interfaces',
            'x': '0',
            'y': '0',
            'width': '72',
            'height': '6',
            'view_mode': '0',
            'fields': [
                {'type': '1', 'name': 'items.0', 'value': 'Interface *: Operational status'},
                {'type': '1', 'name': 'primary_label', 'value': '{{ITEM.NAME}.regsub("^Interface (.*)(?:\\(|: Operational status).*","\\1")}'},
                {'type': '0', 'name': 'interpolation', 'value': '0'},
                {'type': '0', 'name': 'show.0', 'value': '1'},
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
            'type': 'graphprototype',
            'name': 'Traffic',
            'x': '0',
            'y': '6',
            'width': '72',
            'height': '8',
            'view_mode': '0',
            'fields': [
                {'type': '0', 'name': 'columns', 'value': '3'},
                {'type': '7', 'name': 'graphid.0', 'value': graphid},
                {'type': '1', 'name': 'reference', 'value': 'ETGRD'},
                {'type': '0', 'name': 'rows', 'value': '2'},
            ],
        },
    ]


def _exos_port_widgets() -> list[dict]:
    fields = [
        {'type': '0', 'name': 'group_by.0.attribute', 'value': '3'},
        {'type': '1', 'name': 'group_by.0.tag_name', 'value': 'interface'},
    ]
    for index, pattern in enumerate(EXOS_PORT_COUNTERS):
        fields.append({'type': '1', 'name': f'items.{index}', 'value': pattern})
    fields.append({'type': '1', 'name': 'reference', 'value': 'EINAV'})
    return [
        {
            'type': 'itemnavigator',
            'name': 'Counters',
            'x': '0',
            'y': '0',
            'width': '28',
            'height': '11',
            'view_mode': '0',
            'fields': fields,
        },
        {
            'type': 'svggraph',
            'name': 'History',
            'x': '28',
            'y': '0',
            'width': '44',
            'height': '11',
            'view_mode': '0',
            'fields': [
                {'type': '1', 'name': 'ds.0.color.0', 'value': '42A5F5'},
                {'type': '0', 'name': 'ds.0.dataset_type', 'value': '0'},
                {'type': '1', 'name': 'ds.0.itemids.0._reference', 'value': 'EINAV._itemid'},
                {'type': '1', 'name': 'reference', 'value': 'EIGRF'},
                {'type': '0', 'name': 'legend', 'value': '0'},
                {'type': '0', 'name': 'righty', 'value': '0'},
            ],
        },
    ]


def drop_health_diagnostics_page(api: Any, template_name: str) -> str:
    """Remove a leftover Health Diagnostics page (YAML import does not delete pages)."""
    tid = _template_id(api, template_name)
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
    dashboard = next((d for d in dashboards if d.get('name') == 'Health'), None)
    if not dashboard:
        return 'missing-dashboard'
    pages = dashboard.get('pages') or []
    keep = [p for p in pages if p.get('name') != 'Diagnostics']
    if len(keep) == len(pages):
        return 'ok'
    if not keep:
        return 'refused-empty'
    api_call(
        api,
        'templatedashboard.update',
        {
            'dashboardid': dashboard['dashboardid'],
            'pages': [
                {
                    'dashboard_pageid': p['dashboard_pageid'],
                    'name': p.get('name') or '',
                    'display_period': p.get('display_period', '0'),
                    'widgets': p.get('widgets') or [],
                }
                for p in keep
            ],
        },
    )
    logger.info('  %s: dropped leftover Health Diagnostics page', template_name)
    return 'dropped'


def patch_exos_stock_interface_dashboard(api: Any) -> str:
    """Make the stock EXOS interface dashboard match VOSS: map + 3x2 grid + Port page."""
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
    overview = pages[0]
    widgets = overview.get('widgets') or []
    port_page = next((p for p in pages if p.get('name') == 'Port'), None)

    def field_map(widget: dict) -> dict[str, str]:
        return {str(f.get('name')): str(f.get('value')) for f in (widget.get('fields') or [])}

    map_widget = next((w for w in widgets if w.get('type') == 'honeycomb'), {})
    grid_widget = next((w for w in widgets if w.get('type') == 'graphprototype'), {})
    grid_fields = field_map(grid_widget)
    map_fields = field_map(map_widget)
    overview_ok = (
        overview.get('name') == 'Overview'
        and map_widget.get('width') == '72'
        and map_widget.get('height') == '6'
        and map_fields.get('show.0') == '1'
        and map_fields.get('primary_label_bold') is None
        and str(map_fields.get('primary_label_size_type') or '0') == '0'
        and '(?:' in str(map_fields.get('primary_label') or '')
        and grid_widget.get('width') == '72'
        and grid_widget.get('height') == '8'
        and grid_widget.get('y') == '6'
        and grid_fields.get('columns') == '3'
        and grid_fields.get('rows') == '2'
        and grid_fields.get('graphid.0') == graphid
        and not any(w.get('type') in ('item', 'svggraph') for w in widgets)
    )
    port_ok = False
    if port_page:
        pwidgets = port_page.get('widgets') or []
        nav = next((w for w in pwidgets if w.get('type') == 'itemnavigator'), {})
        nav_fields = field_map(nav)
        patterns = {nav_fields[k] for k in nav_fields if k.startswith('items.')}
        port_ok = (
            nav.get('name') == 'Counters'
            and 'Interface *: Operational status' in patterns
            and 'Interface *: Bits received' not in patterns
            and any(w.get('type') == 'svggraph' for w in pwidgets)
        )
    if overview_ok and port_ok:
        return 'ok'

    pages_payload: list[dict] = [
        {
            'dashboard_pageid': overview['dashboard_pageid'],
            'name': 'Overview',
            'display_period': overview.get('display_period', '0'),
            'widgets': _exos_overview_widgets(graphid),
        },
        {
            'name': 'Port',
            'display_period': '0',
            'widgets': _exos_port_widgets(),
        },
    ]
    if port_page and port_page.get('dashboard_pageid'):
        pages_payload[1]['dashboard_pageid'] = port_page['dashboard_pageid']
    api_call(
        api,
        'templatedashboard.update',
        {
            'dashboardid': dashboard['dashboardid'],
            'pages': pages_payload,
        },
    )
    logger.info('  %s: interface dashboard updated to map + 3x2 grid + Port', EXOS_STOCK_TEMPLATE)
    return 'patched'


def assert_exos_stock_interface_grid(api: Any) -> tuple[bool, str]:
    status = patch_exos_stock_interface_dashboard(api)
    return status in ('ok', 'patched', 'missing-template'), status


def _dim(value: Any) -> str:
    return str(value if value is not None else '0')


def patch_iq_interface_honeycomb(api: Any) -> str:
    """Cap IQ interface honeycomb. Zabbix has no max cell size; eth0+mgt0 in 72x6 are ~340px hexes."""
    tid = _template_id(api, IQ_TEMPLATE)
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
    dashboard = next((d for d in dashboards if d.get('name') == IQ_INTERFACE_DASHBOARD), None)
    if not dashboard:
        return 'missing-dashboard'
    pages = dashboard.get('pages') or []
    overview = next((p for p in pages if p.get('name') == 'Overview'), pages[0] if pages else None)
    if not overview:
        return 'missing-page'
    widgets = overview.get('widgets') or []
    map_widget = next((w for w in widgets if w.get('type') == 'honeycomb'), {})
    grid_widget = next((w for w in widgets if w.get('type') == 'graphprototype'), {})
    if (
        _dim(map_widget.get('width')) == '12'
        and _dim(map_widget.get('height')) == '3'
        and _dim(grid_widget.get('y')) == '3'
        and _dim(grid_widget.get('height')) == '11'
    ):
        return 'ok'

    def payload(widget: dict, **geom: str) -> dict:
        out = {
            'type': widget.get('type'),
            'name': widget.get('name') or '',
            'x': geom.get('x', _dim(widget.get('x'))),
            'y': geom.get('y', _dim(widget.get('y'))),
            'width': geom.get('width', _dim(widget.get('width'))),
            'height': geom.get('height', _dim(widget.get('height'))),
            'view_mode': widget.get('view_mode', '0'),
            'fields': widget.get('fields') or [],
        }
        if widget.get('widgetid'):
            out['widgetid'] = widget['widgetid']
        return out

    new_widgets = []
    for widget in widgets:
        if widget.get('type') == 'honeycomb':
            new_widgets.append(payload(widget, x='0', y='0', width='12', height='3'))
        elif widget.get('type') == 'graphprototype':
            new_widgets.append(payload(widget, x='0', y='3', width='72', height='11'))
        else:
            new_widgets.append(payload(widget))
    api_call(
        api,
        'templatedashboard.update',
        {
            'dashboardid': dashboard['dashboardid'],
            'pages': [
                {
                    'dashboard_pageid': overview['dashboard_pageid'],
                    'name': overview.get('name') or 'Overview',
                    'display_period': overview.get('display_period', '0'),
                    'widgets': new_widgets,
                }
            ]
            + [
                {
                    'dashboard_pageid': p['dashboard_pageid'],
                    'name': p.get('name') or '',
                    'display_period': p.get('display_period', '0'),
                    'widgets': p.get('widgets') or [],
                }
                for p in pages
                if p is not overview
            ],
        },
    )
    logger.info('  %s: interface honeycomb capped to 12x3', IQ_TEMPLATE)
    return 'patched'


def apply_extreme_health_patches(api: Any) -> dict[str, Any]:
    """Apply idempotent Health and stock EXOS interface-layout patches."""
    icmp = patch_disable_wan_icmp_noise(api)
    exos_grid = patch_exos_stock_interface_dashboard(api)
    iq_map = patch_iq_interface_honeycomb(api)
    diagnostics = {name: drop_health_diagnostics_page(api, name) for name in HEALTH_TEMPLATES}
    return {
        'icmp_noise': icmp,
        'exos_health': 'companion-yaml',
        'exos_stock_grid': exos_grid,
        'iq_interface_map': iq_map,
        'health_diagnostics': diagnostics,
    }
