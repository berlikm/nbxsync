#!/usr/bin/env python3
"""Create Zabbix country/role/OS dashboards from nested hostgroup parents.

Dashboards filter on parent hostgroups (e.g. ``Sites/CH``). The Zabbix UI
expands nested subgroups automatically, so a country dashboard shows every
site under that country without listing each leaf group.

Parent-first hostgroup creation is handled by the nbxsync sync engine
(PR #125 ``ensure_parent_hostgroups``). This script only creates dashboards
for groups that already exist in Zabbix (run after a full sync).

Usage::

    export NBX_ZABBIX_TOKEN=...
    python scripts/create_dashboards.py                  # all dashboards
    python scripts/create_dashboards.py --countries-only   # country boards
    python scripts/create_dashboards.py --dry-run         # preview only

    # Lab (prefixed groups)
    PYTHONPATH=/workspace/.deps/netbox/netbox:/workspace \\
      python scripts/create_dashboards.py --lab
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
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
from nbxsync.utils.zabbixconnection import ZabbixConnection  # noqa: E402

logger = logging.getLogger('create_dashboards')
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

COUNTRY_SLUGS = ['ch', 'hu', 'jp', 'kr', 'nl', 'us', 'cn']

# Widget layout: 2 columns × 2 rows (24-grid), each widget 12 wide × 5 tall.
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

PREFIX = ''  # '' for prod, 'ztc-' for lab


def _read_token() -> str:
    env = os.environ.get('NBX_ZABBIX_TOKEN')
    if env:
        return env.strip()
    p = Path('/tmp/nbxsync_token.txt')
    if p.exists():
        return p.read_text().strip()
    raise SystemExit('Set NBX_ZABBIX_TOKEN or provide /tmp/nbxsync_token.txt')


def _find_hostgroup(api, name: str) -> str | None:
    """Resolve a hostgroup name to its Zabbix groupid."""
    found = api.hostgroup.get(filter={'name': [name]}, output=['groupid', 'name'])
    return found[0]['groupid'] if found else None


def _build_widgets(layout: list, groupid: str) -> list[dict]:
    """Build Zabbix 7.0 dashboard widget payload with a hostgroup filter."""
    widgets = []
    for i, (wtype, wname, x, y, w, h) in enumerate(layout):
        # hostnavigator uses 'groupids' multi-field; problem widgets use 'hostgroupid'
        if wtype == 'hostnavigator':
            fields = [
                {'type': '20', 'name': 'groupids.0.hostgroupid', 'value': groupid},
                {'type': '0', 'name': 'status', 'value': ''},
                {'type': '0', 'name': 'maintenance', 'value': ''},
            ]
        else:
            fields = [
                {'type': '20', 'name': 'hostgroupid', 'value': groupid},
            ]
        widgets.append({
            'type': wtype,
            'name': wname,
            'x': x,
            'y': y,
            'width': w,
            'height': h,
            'view_mode': '0',
            'fields': fields,
        })
    return widgets


def create_dashboard(api, name: str, group_name: str, layout: list, *, dry_run: bool = False) -> bool:
    """Create a Zabbix dashboard filtering on a parent hostgroup.

    Returns True if created, False if already exists or group missing.
    """
    groupid = _find_hostgroup(api, group_name)
    if groupid is None:
        logger.warning('  SKIP: hostgroup %r not found — run sync first', group_name)
        return False

    existing = api.dashboard.get(filter={'name': [name]}, output=['dashboardid'])
    if existing:
        logger.info('  EXISTS: %r', name)
        return False

    if dry_run:
        logger.info('  DRY-RUN: would create %r (filter: %s gid=%s)', name, group_name, groupid)
        return True

    widgets = _build_widgets(layout, groupid)
    try:
        api.dashboard.create(
            name=name,
            userid=1,
            display_period=60,
            auto_start=1,
            pages=[{
                'widgets': widgets,
                'name': '',
                'display_period': 0,
                'private': 0,
            }],
        )
        logger.info('  CREATED: %r (filter: %s)', name, group_name)
        return True
    except Exception as e:
        logger.warning('  FAILED: %r: %s', name, str(e)[:200])
        return False


def run(*, countries_only: bool = False, dry_run: bool = False, lab: bool = False) -> int:
    global PREFIX
    if lab:
        PREFIX = 'ztc-'

    server = ZabbixServer.objects.first()
    if server is None:
        logger.error('No ZabbixServer found in NetBox')
        return 1

    logger.info('=' * 60)
    logger.info('Zabbix Dashboard Creation (nested hostgroup parents)')
    logger.info('=' * 60)

    created = 0
    with ZabbixConnection(server) as api:
        # Country dashboards: filter on Sites/<COUNTRY>
        logger.info('Country dashboards:')
        for slug in COUNTRY_SLUGS:
            code = slug.upper()
            hg_name = f'Sites/{code}'
            name = f'{code} — Country Overview'
            if create_dashboard(api, name, hg_name, WIDGET_LAYOUT, dry_run=dry_run):
                created += 1

        if countries_only:
            logger.info('Skipping role/OS dashboards (--countries-only)')
        else:
            # Role dashboards: filter on Roles/<role_name>
            from dcim.models import DeviceRole
            role_names = sorted(set(
                DeviceRole.objects.exclude(tags__slug='do_not_monitor')
                .values_list('name', flat=True)
            ))
            # Filter to roles that actually have hostgroups in Zabbix
            logger.info('Role dashboards:')
            for rn in role_names:
                hg_name = f'Roles/{rn}'
                name = f'{rn} — Role Overview'
                if create_dashboard(api, name, hg_name, ROLE_LAYOUT, dry_run=dry_run):
                    created += 1

            # OS dashboards: filter on OS/<os_name>
            logger.info('OS dashboards:')
            for os_name in ['Windows', 'Linux', 'Network', 'VMware']:
                hg_name = f'OS/{os_name}'
                name = f'{os_name} — OS Overview'
                if create_dashboard(api, name, hg_name, OS_LAYOUT, dry_run=dry_run):
                    created += 1

        total = len(api.dashboard.get(output=['dashboardid']))
    logger.info('=' * 60)
    logger.info('DONE: %d created, %d total dashboards', created, total)
    logger.info('=' * 60)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--countries-only', action='store_true', help='Only create country dashboards')
    parser.add_argument('--dry-run', action='store_true', help='Preview what would be created')
    parser.add_argument('--lab', action='store_true', help='Use prefixed lab hostgroups')
    args = parser.parse_args()
    return run(countries_only=args.countries_only, dry_run=args.dry_run, lab=args.lab)


if __name__ == '__main__':
    raise SystemExit(main())
