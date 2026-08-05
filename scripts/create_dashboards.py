#!/usr/bin/env python3
"""Create Zabbix country/role/OS dashboards from nested hostgroup parents.

Uses raw HTTP (not zabbix_utils) so widget field ``value`` stays numeric —
Zabbix 7.0 type=2 (HOST_GROUP) fields require integers.

Widget field names follow Zabbix 7.0 docs (``groupids.N``, not
``groupids.N.hostgroupid``). Host Navigator also requires a unique
5-character ``reference`` field.

Usage::

    export NBX_ZABBIX_TOKEN=...   # or use ZabbixServer.token from NetBox
    python scripts/create_dashboards.py
    python scripts/create_dashboards.py --countries-only
    python scripts/create_dashboards.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.request
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
os.environ.setdefault('NETBOX_CONFIGURATION', os.environ.get('NETBOX_CONFIGURATION', 'netbox.configuration_nbxsync'))

_NETBOX = Path('/workspace/.deps/netbox/netbox')
if _NETBOX.exists() and str(_NETBOX) not in sys.path:
    sys.path.insert(0, str(_NETBOX))
if '/workspace' not in sys.path:
    sys.path.insert(0, '/workspace')

import django  # noqa: E402

django.setup()

from nbxsync.models import ZabbixServer  # noqa: E402

logger = logging.getLogger('create_dashboards')
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

COUNTRY_SLUGS = ['ch', 'hu', 'jp', 'kr', 'nl', 'us', 'cn']

WIDGET_LAYOUT = [
    ('problemsbyseverity', 'Problems by Severity', 0, 0, 12, 5),
    ('problemhosts', 'Problem Hosts', 12, 0, 12, 5),
    ('problems', 'Active Problems', 0, 5, 12, 5),
    ('hostnavigator', 'Host Navigator', 12, 5, 12, 5),
]

ROLE_LAYOUT = [
    ('problemsbyseverity', 'Problems by Severity', 0, 0, 12, 5),
    ('problems', 'Active Problems', 12, 0, 12, 5),
    ('hostnavigator', 'Host Navigator', 0, 5, 24, 5),
]

OS_LAYOUT = [
    ('problemsbyseverity', 'Problems by Severity', 0, 0, 12, 5),
    ('problems', 'Active Problems', 12, 0, 12, 5),
    ('hostnavigator', 'Host Navigator', 0, 5, 24, 5),
]

# Zabbix 7.0 dashboard widget field types
HG_TYPE = 2  # host group
INT_TYPE = 0
STR_TYPE = 1


class RawZabbixAPI:
    """Minimal Zabbix JSON-RPC client that preserves integer types."""

    def __init__(self, url, token):
        self._url = url.rstrip('/') + '/api_jsonrpc.php'
        self._token = token
        self._id = 0

    def _call(self, method, params):
        self._id += 1
        payload = json.dumps({
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'auth': self._token,
            'id': self._id,
        }).encode('utf-8')
        req = urllib.request.Request(
            self._url, data=payload,
            headers={'Content-Type': 'application/json'},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        if 'error' in data:
            raise Exception(f"{method}: {data['error'].get('data', data['error'])}")
        return data.get('result')

    def hostgroup_get(self, **params):
        return self._call('hostgroup.get', params)

    def dashboard_get(self, **params):
        return self._call('dashboard.get', params)

    def dashboard_create(self, **params):
        return self._call('dashboard.create', params)

    def dashboard_delete(self, ids):
        return self._call('dashboard.delete', ids)


def _ref(prefix: str, index: int) -> str:
    """Unique 5-char widget reference (required by several Zabbix 7 widgets)."""
    # A-Z0-9 only, exactly 5 chars, unique within the dashboard.
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    base = (abs(hash(prefix)) + index * 17) % (len(alphabet) ** 5)
    chars = []
    for _ in range(5):
        chars.append(alphabet[base % len(alphabet)])
        base //= len(alphabet)
    return ''.join(chars)


def _groupid_fields(groupids: list[int]) -> list[dict]:
    """Zabbix 7 docs: Host groups → type 2, name groupids.N, value = id."""
    return [
        {'type': HG_TYPE, 'name': f'groupids.{j}', 'value': int(gid)}
        for j, gid in enumerate(groupids)
    ]


def _build_widgets(layout, groupids, dash_key: str) -> list[dict]:
    """Build widget payload with docs-correct field names and integer values."""
    widgets = []
    for i, (wtype, wname, x, y, w, h) in enumerate(layout):
        fields = _groupid_fields(groupids)
        # Most filter widgets require a unique 5-char reference in Zabbix 7.
        fields.append({'type': STR_TYPE, 'name': 'reference', 'value': _ref(dash_key + wtype, i)})
        if wtype == 'hostnavigator':
            # status: -1 = Any; maintenance: 0 = hide maintenance hosts (docs default)
            fields.append({'type': INT_TYPE, 'name': 'status', 'value': -1})
            fields.append({'type': INT_TYPE, 'name': 'maintenance', 'value': 0})
            fields.append({'type': INT_TYPE, 'name': 'show_problems', 'value': 1})
        widgets.append({
            'type': wtype,
            'name': wname,
            'x': x,
            'y': y,
            'width': w,
            'height': h,
            'view_mode': 0,
            'fields': fields,
        })
    return widgets


def create_dashboard(api, name, groupids, layout, *, dry_run=False):
    existing = api.dashboard_get(filter={'name': [name]}, output=['dashboardid'])
    if existing:
        logger.info('  EXISTS: %r', name)
        return False
    if dry_run:
        logger.info('  DRY-RUN: would create %r (%d groups)', name, len(groupids))
        return True
    widgets = _build_widgets(layout, groupids, dash_key=name)
    try:
        api.dashboard_create(
            name=name,
            userid=1,
            display_period=60,
            auto_start=1,
            pages=[{'widgets': widgets, 'name': '', 'display_period': 0}],
        )
        logger.info('  CREATED: %r (%d groups)', name, len(groupids))
        return True
    except Exception as e:
        logger.warning('  FAILED: %r: %s', name, str(e)[:200])
        return False


def _find_country_groups(api, country_code):
    """Prefer parent ``Sites/CH`` (nested UI expands children); else Sites/CH-* leaves."""
    parent = _find_single_group(api, f'Sites/{country_code}')
    if parent:
        return [parent]
    prefix = f'Sites/{country_code}-'
    groups = api.hostgroup_get(search={'name': prefix}, output=['groupid', 'name'], sortfield='name')
    top_level = []
    for g in groups:
        remainder = g['name'][len(prefix):]
        if '/' not in remainder:
            top_level.append(g['groupid'])
    return top_level


def _find_single_group(api, name):
    found = api.hostgroup_get(filter={'name': [name]}, output=['groupid'])
    return found[0]['groupid'] if found else None


def run(*, countries_only=False, dry_run=False, recreate=False):
    server = ZabbixServer.objects.first()
    if server is None:
        logger.error('No ZabbixServer found in NetBox')
        return 1

    logger.info('=' * 60)
    logger.info('Zabbix Dashboard Creation (Zabbix 7 groupids.N + reference)')
    logger.info('=' * 60)

    api = RawZabbixAPI(server.url, server.token)
    if recreate:
        stock = {'Global view', 'Zabbix server health', 'Zabbix server'}
        all_dashes = api.dashboard_get(output=['dashboardid', 'name'])
        custom = [d for d in all_dashes if d['name'] not in stock]
        if custom:
            api.dashboard_delete([d['dashboardid'] for d in custom])
            logger.info('Deleted %d old custom dashboards (--recreate)', len(custom))

    created = 0
    logger.info('Country dashboards:')
    for slug in COUNTRY_SLUGS:
        code = slug.upper()
        groupids = _find_country_groups(api, code)
        if not groupids:
            logger.warning('  SKIP: no Sites/%s (or Sites/%s-*) hostgroups found', code, code)
            continue
        name = f'{code} - Country Overview'
        if create_dashboard(api, name, groupids, WIDGET_LAYOUT, dry_run=dry_run):
            created += 1

    if countries_only:
        logger.info('Skipping role/OS dashboards (--countries-only)')
    else:
        from dcim.models import DeviceRole
        role_names = sorted(set(
            DeviceRole.objects.exclude(tags__slug='do_not_monitor')
            .values_list('name', flat=True)
        ))
        logger.info('Role dashboards:')
        for rn in role_names:
            gid = _find_single_group(api, f'Roles/{rn}')
            if not gid:
                continue
            name = f'{rn} - Role Overview'
            if create_dashboard(api, name, [gid], ROLE_LAYOUT, dry_run=dry_run):
                created += 1

        logger.info('OS dashboards:')
        for os_name in ['Windows', 'Linux', 'Network', 'VMware']:
            gid = _find_single_group(api, f'OS/{os_name}')
            if not gid:
                continue
            name = f'{os_name} - OS Overview'
            if create_dashboard(api, name, [gid], OS_LAYOUT, dry_run=dry_run):
                created += 1

    total = len(api.dashboard_get(output=['dashboardid']))
    logger.info('=' * 60)
    logger.info('DONE: %d created, %d total dashboards', created, total)
    logger.info('=' * 60)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--countries-only', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--recreate', action='store_true', help='Delete non-stock dashboards before creating')
    parser.add_argument('--lab', action='store_true', help='(compat) unused — hostgroups are resolved by name')
    args = parser.parse_args()
    return run(countries_only=args.countries_only, dry_run=args.dry_run, recreate=args.recreate)


if __name__ == '__main__':
    raise SystemExit(main())
