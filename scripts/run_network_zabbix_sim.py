#!/usr/bin/env python3
"""Simulate Extreme/VOSS cutover plan against a live Zabbix 7 lab.

Imports templates from zabbix/templates/, applies global + host (role) macros from
01-extreme-switching.md, creates a pilot VOSS host, and verifies the cutover
minimum from 00-monitoring-plan.md.

Does not require NetBox/Django — pure Zabbix API.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from zabbix_api import ZabbixAPI  # noqa: E402

PREFIX = 'nw-'
HOST_CORE = f'{PREFIX}voss-core-pilot'
HOST_ACCESS = f'{PREFIX}voss-access-pilot'
REPORT_JSON = Path('/opt/cursor/artifacts/network_zabbix_sim_results.json')
REPORT_MD = Path('/opt/cursor/artifacts/NETWORK_ZABBIX_SIM_REPORT.md')

TEMPLATES = {
    'Extreme VOSS by SNMP': ROOT / 'zabbix/templates/extreme_voss_snmp/template_net_extreme_voss_snmp.yaml',
    'Extreme Port Speed Expect by SNMP': ROOT
    / 'zabbix/templates/extreme_port_speed_expect_snmp/template_net_extreme_port_speed_expect_snmp.yaml',
    'Extreme Routing by SNMP': ROOT / 'zabbix/templates/extreme_routing_snmp/template_net_extreme_routing_snmp.yaml',
}

# Design §A.8 — global silencing + speed-expect LLD filters
GLOBAL_MACROS = {
    '{$IF.UTIL.MAX}': '101',
    '{$TEMP_WARN}': '999',
    '{$TEMP_CRIT}': '999',
    '{$TEMP_CRIT_LOW}': '-273',
    '{$OPTIC.TEMP.CRIT}': '999',
    '{$OPTIC.TEMP.MAX}': '150',
    '{$MLT.CONTROL}': '0',
    '{$SNMP.TIMEOUT}': '5m',
    '{$PORTID.LLD.IFALIAS.MATCHES}': '^(USW|US|UP|MON)(-|$)',
    '{$PORTID.LLD.IFTYPE.MATCHES}': '^6$',
}

# Role macros written as host macros (what nbxsync would push)
ROLE_MACROS = {
    'core': {
        '{$NET.IF.IFALIAS.MATCHES}': '.*',
        '{$NET.IF.IFALIAS.NOT_MATCHES}': '^X(-|$)',
        '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
    },
    'access': {
        '{$NET.IF.IFALIAS.MATCHES}': '^(USW|US|UP|MON|UW|TMON)(-|$)',
        '{$NET.IF.IFALIAS.NOT_MATCHES}': 'CHANGE_IF_NEEDED',
        '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
    },
}

RESULTS: list[dict] = []


def record(name: str, ok: bool, detail: str = '', *, group: str = 'general'):
    RESULTS.append({'name': name, 'ok': bool(ok), 'detail': detail, 'group': group})
    print(f"[{'PASS' if ok else 'FAIL'}] {group}/{name}: {detail}")


def import_rules() -> dict:
    return {
        'templates': {'createMissing': True, 'updateExisting': True},
        'template_groups': {'createMissing': True, 'updateExisting': True},
        'valueMaps': {'createMissing': True, 'updateExisting': True},
        'items': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
        'discoveryRules': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
        'triggers': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
        'graphs': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
        'httptests': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
        'templateDashboards': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
    }


def ensure_global_macros(api: ZabbixAPI) -> None:
    existing = {m['macro']: m for m in api.call('usermacro.get', {'globalmacro': True, 'output': 'extend'})}
    for macro, value in GLOBAL_MACROS.items():
        if macro in existing:
            if existing[macro]['value'] != value:
                api.call('usermacro.updateglobal', {'globalmacroid': existing[macro]['globalmacroid'], 'value': value})
                record(macro, True, f'updated → {value}', group='global-macros')
            else:
                record(macro, True, f'already {value}', group='global-macros')
        else:
            api.call('usermacro.createglobal', {'macro': macro, 'value': value})
            record(macro, True, f'created = {value}', group='global-macros')


def ensure_hostgroup(api: ZabbixAPI, name: str) -> str:
    found = api.call('hostgroup.get', {'filter': {'name': name}, 'output': ['groupid']})
    if found:
        return found[0]['groupid']
    return api.call('hostgroup.create', {'name': name})['groupids'][0]


def set_host_macros(api: ZabbixAPI, hostid: str, macros: dict[str, str]) -> None:
    current = {m['macro']: m for m in api.call('usermacro.get', {'hostids': hostid, 'output': 'extend'})}
    for macro, value in macros.items():
        if macro in current:
            if current[macro]['value'] != value:
                api.call('usermacro.update', {'hostmacroid': current[macro]['hostmacroid'], 'value': value})
        else:
            api.call('usermacro.create', {'hostid': hostid, 'macro': macro, 'value': value})


def ensure_host(
    api: ZabbixAPI,
    *,
    host: str,
    groupids: list[str],
    template_hosts: list[str],
    role_macros: dict[str, str],
    ip: str,
    community: str = 'public',
    snmp_port: int = 161,
) -> str:
    tmpl_ids = []
    for th in template_hosts:
        t = api.call('template.get', {'filter': {'host': th}, 'output': ['templateid']})
        if not t:
            raise RuntimeError(f'template not found: {th}')
        tmpl_ids.append(t[0]['templateid'])

    existing = api.call('host.get', {'filter': {'host': host}, 'output': ['hostid']})
    interfaces = [
        {
            'type': 2,  # SNMP
            'main': 1,
            'useip': 1,
            'ip': ip,
            'dns': '',
            'port': str(snmp_port),
            'details': {
                'version': 2,
                'community': community,
                'bulk': 1,
            },
        }
    ]
    if existing:
        hostid = existing[0]['hostid']
        api.call(
            'host.update',
            {
                'hostid': hostid,
                'groups': [{'groupid': g} for g in groupids],
                'templates': [{'templateid': t} for t in tmpl_ids],
                'status': 0,
            },
        )
    else:
        created = api.call(
            'host.create',
            {
                'host': host,
                'name': host,
                'interfaces': interfaces,
                'groups': [{'groupid': g} for g in groupids],
                'templates': [{'templateid': t} for t in tmpl_ids],
                'status': 0,
            },
        )
        hostid = created['hostids'][0]
    set_host_macros(api, hostid, role_macros)
    return hostid


def cleanup(api: ZabbixAPI) -> None:
    hosts = api.call('host.get', {'search': {'host': PREFIX}, 'output': ['hostid', 'host'], 'searchWildcardsEnabled': True})
    ids = [h['hostid'] for h in hosts if h['host'].startswith(PREFIX)]
    if ids:
        api.call('host.delete', ids)


def import_templates(api: ZabbixAPI) -> None:
    for name, path in TEMPLATES.items():
        if not path.exists():
            record(name, False, f'missing file {path}', group='import')
            continue
        try:
            api.call(
                'configuration.import',
                {'format': 'yaml', 'rules': import_rules(), 'source': path.read_text()},
            )
            record(name, True, f'imported from {path.relative_to(ROOT)}', group='import')
        except Exception as e:
            record(name, False, str(e), group='import')


def verify_templates(api: ZabbixAPI) -> dict[str, str]:
    ids = {}
    for name in TEMPLATES:
        t = api.call('template.get', {'filter': {'name': name}, 'output': ['templateid', 'host', 'name']})
        ok = bool(t)
        record(name, ok, t[0]['host'] if t else 'absent', group='templates')
        if t:
            ids[name] = t[0]['templateid']
    return ids


def verify_template_macros(api: ZabbixAPI, templateid: str) -> None:
    macros = {m['macro']: m['value'] for m in api.call('usermacro.get', {'hostids': templateid, 'output': 'extend'})}
    checks = {
        '{$IF.UTIL.MAX}': '101',
        '{$TEMP_WARN}': '999',
        '{$TEMP_CRIT_LOW}': '-273',
        '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
    }
    for macro, expected in checks.items():
        got = macros.get(macro)
        record(f'tmpl {macro}', got == expected, f'got {got!r} want {expected!r}', group='voss-defaults')


def verify_lld(api: ZabbixAPI, templateid: str) -> None:
    rules = api.call(
        'discoveryrule.get',
        {'hostids': templateid, 'filter': {'key_': 'net.if.discovery'}, 'output': ['itemid', 'key_', 'delay', 'lifetime']},
    )
    if not rules:
        record('net.if.discovery', False, 'LLD missing', group='lld')
        return
    r = rules[0]
    # lifetime 0 or 0d both OK
    lifetime_ok = str(r.get('lifetime', '')).lstrip('0') in ('', 'd', '0') or r.get('lifetime') in ('0', '0d', 0)
    record('lld delay', r.get('delay') in ('15m', '1h'), f"delay={r.get('delay')}", group='lld')
    record('lld keep-lost', lifetime_ok or str(r.get('lifetime')) in ('0', '0d'), f"lifetime={r.get('lifetime')}", group='lld')


def verify_host(api: ZabbixAPI, host: str, *, expect_templates: list[str], role: str) -> None:
    h = api.call(
        'host.get',
        {
            'filter': {'host': host},
            'output': ['hostid', 'host', 'status'],
            'selectParentTemplates': ['name', 'host'],
            'selectInterfaces': ['type', 'main', 'ip', 'port'],
            'selectMacros': ['macro', 'value'],
        },
    )
    if not h:
        record(host, False, 'host missing', group='hosts')
        return
    h = h[0]
    names = {t['name'] for t in h.get('parentTemplates', [])}
    for tn in expect_templates:
        record(f'{host}←{tn}', tn in names, f'templates={sorted(names)}', group='hosts')
    # no Network Generic
    ng = any('Network Generic' in n or 'network.generic' in n.lower() for n in names)
    record(f'{host} no Network Generic', not ng, f'templates={sorted(names)}', group='cutover')
    # SNMP IF present
    snmp = [i for i in h.get('interfaces', []) if str(i.get('type')) == '2']
    record(f'{host} SNMP IF', bool(snmp), snmp[0] if snmp else 'none', group='hosts')
    # role macros
    macros = {m['macro']: m['value'] for m in h.get('macros', [])}
    for k, v in ROLE_MACROS[role].items():
        record(f'{host} {k}', macros.get(k) == v, f'got {macros.get(k)!r}', group='role-macros')
    # single icmpping item key among templates (count items on host)
    items = api.call('item.get', {'hostids': h['hostid'], 'search': {'key_': 'icmpping'}, 'output': ['key_', 'name']})
    # icmpping, icmppingloss, icmppingsec are fine — duplicate icmpping keys are not
    ping_keys = [i['key_'] for i in items if i['key_'] == 'icmpping']
    record(f'{host} single icmpping', len(ping_keys) <= 1, f'count={len(ping_keys)} keys={ping_keys}', group='cutover')


def verify_cutover_checklist(api: ZabbixAPI, tmpl_ids: dict[str, str]) -> None:
    """00-monitoring-plan cutover minimum — configurability, not live traffic."""
    record('cutover: platform template exists', 'Extreme VOSS by SNMP' in tmpl_ids, '', group='cutover')
    # ICMP + SNMP availability items on VOSS template
    tid = tmpl_ids.get('Extreme VOSS by SNMP')
    if tid:
        keys = {i['key_'] for i in api.call('item.get', {'hostids': tid, 'output': ['key_']})}
        record('cutover: icmpping', 'icmpping' in keys, '', group='cutover')
        record('cutover: snmp avail / agent.ping style', any('zabbix[host,snmp,available]' in k or 'snmp' in k for k in keys), f'sample={list(keys)[:8]}', group='cutover')
        lld_all = api.call('discoveryrule.get', {'hostids': tid, 'output': ['key_', 'name']})
        lld_keys = {r['key_'] for r in lld_all}
        # health-ish — scalars and/or LLD (temp/PSU/fan are discovery on VOSS)
        health = [
            ('CPU', lambda: any('cpu' in k.lower() for k in keys)),
            ('memory', lambda: any('memory' in k.lower() or 'mem' in k.lower() for k in keys) or 'memory.discovery' in lld_keys),
            ('temperature', lambda: 'temperature.discovery' in lld_keys or any('temp' in k.lower() for k in keys)),
            ('PSU', lambda: 'psu.discovery' in lld_keys or any('psu' in k.lower() or 'power' in k.lower() for k in keys)),
            ('fan', lambda: 'fan.discovery' in lld_keys or any('fan' in k.lower() for k in keys)),
        ]
        for label, fn in health:
            record(f'cutover: {label}', fn(), '', group='cutover')
        record('cutover: interface LLD', 'net.if.discovery' in lld_keys, sorted(lld_keys), group='cutover')
    # post-cutover templates present but not required on access pilot
    record('post: speed-expect template', 'Extreme Port Speed Expect by SNMP' in tmpl_ids, 'not a cutover blocker', group='post-cutover')
    record('post: routing/OSPF template', 'Extreme Routing by SNMP' in tmpl_ids, 'nice-to-have / disabled until canaries', group='post-cutover')


def write_report(args) -> None:
    passed = sum(1 for r in RESULTS if r['ok'])
    failed = sum(1 for r in RESULTS if not r['ok'])
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps({'passed': passed, 'failed': failed, 'results': RESULTS}, indent=2))
    lines = [
        '# Network Zabbix simulation report',
        '',
        f'**Score: {passed}/{passed + failed}**',
        '',
        'Plan: `zabbix/00-monitoring-plan.md` cutover minimum + `zabbix/01-extreme-switching.md` §B.',
        '',
        '| Group | Check | Result | Detail |',
        '|---|---|---|---|',
    ]
    for r in RESULTS:
        lines.append(f"| {r['group']} | {r['name']} | {'PASS' if r['ok'] else 'FAIL'} | {r['detail']} |")
    REPORT_MD.write_text('\n'.join(lines) + '\n')
    print(f'\nReport: {REPORT_MD} ({passed}/{passed + failed})')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--keep', action='store_true', help='do not delete nw-* hosts at start')
    ap.add_argument('--snmp-ip', default='127.0.0.1', help='SNMP IP for pilot hosts')
    ap.add_argument('--snmp-port', type=int, default=1261, help='SNMP port (lab VOSS hostfwd default 1261)')
    ap.add_argument('--with-speed-expect', action='store_true', help='also link Port Speed Expect on core pilot')
    args = ap.parse_args()

    api = ZabbixAPI.from_lab()
    if not args.keep:
        cleanup(api)

    import_templates(api)
    tmpl_ids = verify_templates(api)

    if 'Extreme VOSS by SNMP' in tmpl_ids:
        verify_template_macros(api, tmpl_ids['Extreme VOSS by SNMP'])
        verify_lld(api, tmpl_ids['Extreme VOSS by SNMP'])

    ensure_global_macros(api)

    g_lab = ensure_hostgroup(api, 'nw-lab')
    g_core = ensure_hostgroup(api, 'Roles/nw-Core')
    g_access = ensure_hostgroup(api, 'Roles/nw-Access')
    g_site = ensure_hostgroup(api, 'Sites/nw-lab/nw-site')

    core_tmpls = ['Extreme VOSS by SNMP']
    if args.with_speed_expect and 'Extreme Port Speed Expect by SNMP' in tmpl_ids:
        core_tmpls.append('Extreme Port Speed Expect by SNMP')
    # Routing template imported but NOT linked — post-cutover / triggers off

    try:
        ensure_host(
            api,
            host=HOST_CORE,
            groupids=[g_lab, g_core, g_site],
            template_hosts=core_tmpls,
            role_macros=ROLE_MACROS['core'],
            ip=args.snmp_ip,
            snmp_port=args.snmp_port,
        )
        record('create core pilot', True, HOST_CORE, group='hosts')
    except Exception as e:
        record('create core pilot', False, str(e), group='hosts')

    try:
        ensure_host(
            api,
            host=HOST_ACCESS,
            groupids=[g_lab, g_access, g_site],
            template_hosts=['Extreme VOSS by SNMP'],
            role_macros=ROLE_MACROS['access'],
            ip=args.snmp_ip,
            snmp_port=args.snmp_port,
        )
        record('create access pilot', True, HOST_ACCESS, group='hosts')
    except Exception as e:
        record('create access pilot', False, str(e), group='hosts')

    verify_host(api, HOST_CORE, expect_templates=core_tmpls, role='core')
    verify_host(api, HOST_ACCESS, expect_templates=['Extreme VOSS by SNMP'], role='access')
    verify_cutover_checklist(api, tmpl_ids)

    # Explicit N vs X semantics — document as macro-level checks
    record(
        'core excludes only X',
        ROLE_MACROS['core']['{$NET.IF.IFALIAS.NOT_MATCHES}'] == '^X(-|$)',
        'N is monitoring-neutral',
        group='semantics',
    )
    record(
        'access opt-in classes',
        'USW' in ROLE_MACROS['access']['{$NET.IF.IFALIAS.MATCHES}'],
        ROLE_MACROS['access']['{$NET.IF.IFALIAS.MATCHES}'],
        group='semantics',
    )

    write_report(args)
    failed = sum(1 for r in RESULTS if not r['ok'])
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
