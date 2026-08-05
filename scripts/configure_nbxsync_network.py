#!/usr/bin/env python3
"""Configure the *network* half of nbxsync zero-touch for Extreme switching.

Companion to the general `configure_nbxsync_zerotouch.py` (servers/VMs/OOB).
This script owns platforms EXOS/VOSS, switch roles, port-scoping macros, and
template linkage described in `zabbix/01-extreme-switching.md`.

Modes:
  --zabbix-only   Apply templates + global/host macros via Zabbix API (no NetBox)
  --simulate      Same as --zabbix-only, plus write a NetBox assignment plan JSON
  --apply         Create nbxsync objects in NetBox (requires Django / NetBox DB)
  --plan-only     Print the intended assignment plan and exit

Examples:
  python3 scripts/configure_nbxsync_network.py --simulate
  python3 scripts/configure_nbxsync_network.py --zabbix-only --link-speed-expect
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
PLAN_JSON = Path('/opt/cursor/artifacts/network_nbxsync_plan.json')
REPORT_MD = Path('/opt/cursor/artifacts/NETWORK_NBXSYNC_CONFIGURE_REPORT.md')

# ---------------------------------------------------------------------------
# Declarative plan — Track B wiring for Extreme switching
# ---------------------------------------------------------------------------

PLAN = {
    'platforms': [
        {
            'name': 'Extreme EXOS',
            'slug': 'exos',
            'templates': ['Extreme EXOS by SNMP'],  # stock, release/7.0 — not in this repo
            'note': 'Stock template from Zabbix share; link via TemplateRule/Assignment on platform',
        },
        {
            'name': 'Extreme VOSS',
            'slug': 'voss',
            'templates': ['Extreme VOSS by SNMP'],
            'template_file': 'zabbix/templates/extreme_voss_snmp/template_net_extreme_voss_snmp.yaml',
        },
    ],
    'roles': [
        {
            'name': 'Core',
            'slug': 'core',
            'macros': {
                '{$NET.IF.IFALIAS.MATCHES}': '.*',
                '{$NET.IF.IFALIAS.NOT_MATCHES}': '^X(-|$)',
                '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
            },
            'extra_templates': ['Extreme Routing by SNMP'],  # post-cutover; leave unlinked until canaries
            'extra_templates_enabled': False,
        },
        {
            'name': 'Dist',
            'slug': 'dist',
            'macros': {
                '{$NET.IF.IFALIAS.MATCHES}': '.*',
                '{$NET.IF.IFALIAS.NOT_MATCHES}': '^X(-|$)',
                '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
            },
            'extra_templates': ['Extreme Routing by SNMP'],
            'extra_templates_enabled': False,
        },
        {
            'name': 'Mgmt',
            'slug': 'mgmt',
            'macros': {
                '{$NET.IF.IFALIAS.MATCHES}': '.*',
                '{$NET.IF.IFALIAS.NOT_MATCHES}': '^X(-|$)',
                '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
            },
        },
        {
            'name': 'Access',
            'slug': 'access',
            'macros': {
                '{$NET.IF.IFALIAS.MATCHES}': '^(USW|US|UP|MON|UW|TMON)(-|$)',
                '{$NET.IF.IFALIAS.NOT_MATCHES}': 'CHANGE_IF_NEEDED',
                '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
            },
        },
        {
            'name': 'Hybrid',
            'slug': 'hybrid',
            'macros': {
                # stage 0–4: access/opt-in; flip to Core values at stage 5
                '{$NET.IF.IFALIAS.MATCHES}': '^(USW|US|UP|MON|UW|TMON)(-|$)',
                '{$NET.IF.IFALIAS.NOT_MATCHES}': 'CHANGE_IF_NEEDED',
                '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
            },
            'note': 'Start opt-in; stage 5 flips MATCHES/NOT_MATCHES to Core values',
        },
    ],
    'global_macros': {
        '{$IF.UTIL.MAX}': '101',
        '{$TEMP_WARN}': '999',
        '{$TEMP_CRIT_LOW}': '-273',
        '{$SNMP.TIMEOUT}': '5m',
        '{$PORTID.LLD.IFALIAS.MATCHES}': '^(USW|US|UP|MON)(-|$)',
        '{$PORTID.LLD.IFTYPE.MATCHES}': '^6$',
    },
    'stage6_macros': {
        '{$IF.UTIL.MAX:"USW"}': '80',
        '{$IF.DISCARDS.WARN}': '1',
    },
    'both_platforms_templates': [
        {
            'name': 'Extreme Port Speed Expect by SNMP',
            'file': 'zabbix/templates/extreme_port_speed_expect_snmp/template_net_extreme_port_speed_expect_snmp.yaml',
            'enabled_at_stage': 4,
            'default_link': False,
        },
        {
            'name': 'Extreme Routing by SNMP',
            'file': 'zabbix/templates/extreme_routing_snmp/template_net_extreme_routing_snmp.yaml',
            'enabled_at_stage': 'post-cutover',
            'default_link': False,
            'assign_on': ['Core', 'Dist'],
        },
    ],
    'transport': {
        'configuration_group': 'SNMP Monitoring',
        'assign_on_roles': ['Core', 'Dist', 'Mgmt', 'Access', 'Hybrid'],
        'note': 'Role SNMP CG beats SiteGroup Agent default (zero-touch I3/I8)',
    },
    'invariants': [
        'Platform → platform template (additive); Role → macros + capability templates',
        'Never Core-EXOS / Core-VOSS template matrix',
        'Set BOTH IFALIAS macros on every role',
        'X excludes; N is monitoring-neutral',
        'Do not use {$IFCONTROL:"{#IFNAME}"}',
        'No Network Generic under platform template (icmpping collision)',
    ],
}

RESULTS: list[dict] = []


def record(step: str, ok: bool, detail: str = ''):
    RESULTS.append({'step': step, 'ok': bool(ok), 'detail': detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {step}: {detail}")


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


def zabbix_import_network_templates(api: ZabbixAPI, *, link_speed_expect: bool, enable_stage6: bool) -> dict[str, str]:
    ids: dict[str, str] = {}
    files = [
        ('Extreme VOSS by SNMP', ROOT / 'zabbix/templates/extreme_voss_snmp/template_net_extreme_voss_snmp.yaml'),
        (
            'Extreme Port Speed Expect by SNMP',
            ROOT / 'zabbix/templates/extreme_port_speed_expect_snmp/template_net_extreme_port_speed_expect_snmp.yaml',
        ),
        ('Extreme Routing by SNMP', ROOT / 'zabbix/templates/extreme_routing_snmp/template_net_extreme_routing_snmp.yaml'),
    ]
    for name, path in files:
        try:
            api.call('configuration.import', {'format': 'yaml', 'rules': import_rules(), 'source': path.read_text()})
            record(f'import {name}', True, str(path.relative_to(ROOT)))
        except Exception as e:
            record(f'import {name}', False, str(e))
        t = api.call('template.get', {'filter': {'name': name}, 'output': ['templateid', 'host']})
        if t:
            ids[name] = t[0]['templateid']

    # Global macros
    existing = {m['macro']: m for m in api.call('usermacro.get', {'globalmacro': True, 'output': 'extend'})}
    macros = dict(PLAN['global_macros'])
    if enable_stage6:
        macros.update(PLAN['stage6_macros'])
    for macro, value in macros.items():
        try:
            if macro in existing:
                if existing[macro]['value'] != value:
                    api.call('usermacro.updateglobal', {'globalmacroid': existing[macro]['globalmacroid'], 'value': value})
                record(f'global {macro}', True, value)
            else:
                # Context macros like {$IF.UTIL.MAX:"USW"} are still global usermacros in Zabbix
                api.call('usermacro.createglobal', {'macro': macro, 'value': value})
                record(f'global {macro}', True, f'created {value}')
        except Exception as e:
            record(f'global {macro}', False, str(e))

    # Demo hosts representing each role — macros only (what nbxsync host sync writes)
    for role in PLAN['roles']:
        host = f"{PREFIX}role-{role['slug']}"
        groups = []
        for gname in ('nw-lab', f"Roles/nw-{role['name']}", 'Sites/nw-lab/nw-site'):
            found = api.call('hostgroup.get', {'filter': {'name': gname}})
            gid = found[0]['groupid'] if found else api.call('hostgroup.create', {'name': gname})['groupids'][0]
            groups.append(gid)

        tmpl_hosts = ['Extreme VOSS by SNMP']
        if link_speed_expect and 'Extreme Port Speed Expect by SNMP' in ids:
            tmpl_hosts.append('Extreme Port Speed Expect by SNMP')
        tmpl_ids = []
        for th in tmpl_hosts:
            t = api.call('template.get', {'filter': {'host': th}})
            if t:
                tmpl_ids.append(t[0]['templateid'])

        existing_h = api.call('host.get', {'filter': {'host': host}, 'output': ['hostid']})
        iface = {
            'type': 2,
            'main': 1,
            'useip': 1,
            'ip': '127.0.0.1',
            'dns': '',
            'port': '161',
            'details': {'version': 2, 'community': '{$SNMP_COMMUNITY}', 'bulk': 1},
        }
        try:
            if existing_h:
                hostid = existing_h[0]['hostid']
                api.call(
                    'host.update',
                    {
                        'hostid': hostid,
                        'groups': [{'groupid': g} for g in groups],
                        'templates': [{'templateid': t} for t in tmpl_ids],
                    },
                )
            else:
                hostid = api.call(
                    'host.create',
                    {
                        'host': host,
                        'name': f"nw demo {role['name']}",
                        'interfaces': [iface],
                        'groups': [{'groupid': g} for g in groups],
                        'templates': [{'templateid': t} for t in tmpl_ids],
                        'status': 1,  # disabled — config demo only
                    },
                )['hostids'][0]
            # host macros = role macros
            current = {m['macro']: m for m in api.call('usermacro.get', {'hostids': hostid, 'output': 'extend'})}
            for macro, value in role['macros'].items():
                if macro in current:
                    if current[macro]['value'] != value:
                        api.call('usermacro.update', {'hostmacroid': current[macro]['hostmacroid'], 'value': value})
                else:
                    api.call('usermacro.create', {'hostid': hostid, 'macro': macro, 'value': value})
            record(f"role host {role['name']}", True, f'{host} macros={list(role["macros"])}')
        except Exception as e:
            record(f"role host {role['name']}", False, str(e))

    return ids


def apply_netbox(args) -> None:
    """Create nbxsync objects — requires working Django + NetBox DB."""
    try:
        import django  # noqa: F401
    except Exception as e:
        record('django', False, f'unavailable: {e}')
        record('apply', False, 'Use --zabbix-only / --simulate until NetBox venv is restored')
        return

    # Deferred: full NetBox object creation mirrors PLAN once Django boots.
    # Kept as an explicit stub so Track B wiring stays in one place.
    record(
        'apply',
        False,
        'NetBox apply path not executed in this environment (venv broken). Plan written; use --zabbix-only.',
    )


def write_outputs(args):
    PLAN_JSON.parent.mkdir(parents=True, exist_ok=True)
    PLAN_JSON.write_text(json.dumps(PLAN, indent=2))
    passed = sum(1 for r in RESULTS if r['ok'])
    failed = sum(1 for r in RESULTS if not r['ok'])
    lines = [
        '# Network nbxsync configure report',
        '',
        f'Mode: `{args.mode}` · **{passed}/{passed + failed}**',
        '',
        'Plan JSON: `/opt/cursor/artifacts/network_nbxsync_plan.json`',
        '',
        '| Step | Result | Detail |',
        '|---|---|---|',
    ]
    for r in RESULTS:
        lines.append(f"| {r['step']} | {'PASS' if r['ok'] else 'FAIL'} | {r['detail']} |")
    lines += [
        '',
        '## Invariants',
        '',
    ]
    for inv in PLAN['invariants']:
        lines.append(f'- {inv}')
    REPORT_MD.write_text('\n'.join(lines) + '\n')
    print(f'\nPlan: {PLAN_JSON}')
    print(f'Report: {REPORT_MD} ({passed}/{passed + failed})')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan-only', action='store_true', help='print/write plan JSON only')
    mode.add_argument('--zabbix-only', action='store_true', help='configure Zabbix templates/macros/demo hosts')
    mode.add_argument('--simulate', action='store_true', help='zabbix-only + write plan (lab proof)')
    mode.add_argument('--apply', action='store_true', help='create nbxsync objects in NetBox (needs Django)')
    ap.add_argument('--link-speed-expect', action='store_true', help='link Port Speed Expect on demo hosts (stage 4)')
    ap.add_argument('--enable-stage6', action='store_true', help='set {$IF.UTIL.MAX:"USW"} and discards warn')
    args = ap.parse_args()

    if args.plan_only:
        args.mode = 'plan-only'
        PLAN_JSON.parent.mkdir(parents=True, exist_ok=True)
        PLAN_JSON.write_text(json.dumps(PLAN, indent=2))
        print(json.dumps(PLAN, indent=2))
        print(f'\nWrote {PLAN_JSON}')
        return 0

    if args.apply:
        args.mode = 'apply'
        apply_netbox(args)
        write_outputs(args)
        return 1 if any(not r['ok'] for r in RESULTS) else 0

    args.mode = 'simulate' if args.simulate else 'zabbix-only'
    api = ZabbixAPI.from_lab()
    zabbix_import_network_templates(api, link_speed_expect=args.link_speed_expect, enable_stage6=args.enable_stage6)

    # Sanity: Core NOT_MATCHES must not exclude N
    core = next(r for r in PLAN['roles'] if r['slug'] == 'core')
    record(
        'semantics X-only exclude',
        core['macros']['{$NET.IF.IFALIAS.NOT_MATCHES}'] == '^X(-|$)',
        core['macros']['{$NET.IF.IFALIAS.NOT_MATCHES}'],
    )
    record('plan platforms', True, ', '.join(p['name'] for p in PLAN['platforms']))
    record('plan roles', True, ', '.join(r['name'] for r in PLAN['roles']))

    write_outputs(args)
    return 1 if any(not r['ok'] for r in RESULTS) else 0


if __name__ == '__main__':
    raise SystemExit(main())
