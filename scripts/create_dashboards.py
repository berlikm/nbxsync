#!/usr/bin/env python3
"""Create Zabbix country/role/OS dashboards from nested hostgroup parents."""
from __future__ import annotations

import argparse
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


def _build_widgets(layout, groupids):
    """Build Zabbix 7.0 dashboard widget payload with hostgroup filter."""
    widgets = []
    for wtype, wname, x, y, w, h in layout:
        if wtype == 'hostnavigator':
            fields = []
            for j, gid in enumerate(groupids):
                fields.append({'type': 0, 'name': f'groupids.{j}.hostgroupid', 'value': int(gid)})
            fields.append({'type': 0, 'name': 'status', 'value': 0})
            fields.append({'type': 0, 'name': 'maintenance', 'value': 0})
        else:
            if len(groupids) == 1:
                fields = [{'type': 0, 'name': 'hostgroupid', 'value': int(groupids[0])}]
            else:
                fields = []
                for j, gid in enumerate(groupids):
                    fields.append({'type': 0, 'name': f'hostgroupids.{j}.reference', 'value': int(gid)})
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


def create_dashboard(api, name, groupids, layout, *, dry_run=False):
    existing = api.dashboard.get(filter={'name': [name]}, output=['dashboardid'])
    if existing:
        logger.info('  EXISTS: %r', name)
        return False
    if dry_run:
        logger.info('  DRY-RUN: would create %r (%d groups)', name, len(groupids))
        return True
    widgets = _build_widgets(layout, groupids)
    try:
        api.dashboard.create(
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
    prefix = f'Sites/{country_code}-'
    groups = api.hostgroup.get(search={'name': prefix}, output=['groupid', 'name'], sortfield='name')
    top_level = []
    for g in groups:
        remainder = g['name'][len(prefix):]
        if '/' not in remainder:
            top_level.append(g['groupid'])
    return top_level


def _find_single_group(api, name):
    found = api.hostgroup.get(filter={'name': [name]}, output=['groupid'])
    return found[0]['groupid'] if found else None


def run(*, countries_only=False, dry_run=False, lab=False):
    server = ZabbixServer.objects.first()
    if server is None:
        logger.error('No ZabbixServer found in NetBox')
        return 1

    logger.info('=' * 60)
    logger.info('Zabbix Dashboard Creation (nested hostgroup parents)')
    logger.info('=' * 60)

    created = 0
    with ZabbixConnection(server) as api:
        logger.info('Country dashboards:')
        for slug in COUNTRY_SLUGS:
            code = slug.upper()
            groupids = _find_country_groups(api, code)
            if not groupids:
                logger.warning('  SKIP: no Sites/%s-* hostgroups found', code)
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

        total = len(api.dashboard.get(output=['dashboardid']))
    logger.info('=' * 60)
    logger.info('DONE: %d created, %d total dashboards', created, total)
    logger.info('=' * 60)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--countries-only', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--lab', action='store_true')
    args = parser.parse_args()
    return run(countries_only=args.countries_only, dry_run=args.dry_run, lab=args.lab)


if __name__ == '__main__':
    raise SystemExit(main())
