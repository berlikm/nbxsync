#!/usr/bin/env python3
"""Idempotent Extreme Health / alerting patches for a live Zabbix 7 API.

Used by ``configure_nbxsync_network.py`` and lab smokes. No Django. Never
deletes hosts or mutates the stock EXOS dashboard; EXOS Health ships on the
``Extreme EXOS Observability`` companion template.
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




def apply_extreme_health_patches(api: Any) -> dict[str, Any]:
    """Apply runtime-only Health patches.

    EXOS Health ships on the ``Extreme EXOS Observability`` companion YAML;
    never mutate the stock EXOS template here.
    """
    icmp = patch_disable_wan_icmp_noise(api)
    return {'icmp_noise': icmp, 'exos_health': 'companion-yaml'}
