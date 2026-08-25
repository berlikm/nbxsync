#!/usr/bin/env python3
"""
Tag devices/VMs with 'onboarding' to exclude them from Zabbix sync.

Run AFTER configure_nbxsync_zerotouch.py has created the onboarding tag
and the do_not_monitor → onboarding Tag→exclude assignment.

Only infrastructure roles are left untagged (they go to Zabbix immediately):
  - Switches (Core/Dist/Access/Mgmt)
  - Access Points
  - Network Device
  - Virtual Appliance
  - ESXi Hypervisor
  - Zabbix Proxy
  - vCenter

Everything else (Server, Cohesity, MSSQL, Storage, Firewall, Domain Controller,
Database, etc.) gets the 'onboarding' tag → excluded from Zabbix until the tag
is removed per-wave. `Sd Wan Socket` is a controlled-release role: this utility
never adds or removes its onboarding hold.

Usage on NetBox host (dev or prod):
  sudo -n bash -c 'set -a; source /etc/netbox.env; set +a; \
    cd /opt/netbox/netbox && PYTHONPATH=. DJANGO_SETTINGS_MODULE=netbox.settings \
    /opt/netbox/venv/bin/python3 scripts/tag_onboarding_exclude.py [--dry-run]'

Options:
  --dry-run  Show counts without changing tags
  --untag    REMOVE onboarding tag from ordinary hosts; leave controlled-release roles held
"""
from __future__ import annotations

import argparse
import sys

import django
django.setup()

from dcim.models import Device
from virtualization.models import VirtualMachine
from extras.models import Tag
from django.db.models import Q

# Roles that stay in Zabbix from the start (infrastructure + already-verified)
INFRASTRUCTURE_ROLES = [
    'Switch Core',
    'Switch Dist',
    'Switch Access',
    'Switch Mgmt',
    'Access Point',
    'Network Device',
    'Virtual Appliance',
    'ESXi Hypervisor',
    'Zabbix Proxy',
    'vCenter',
]

# Roles that are permanently excluded (do_not_monitor on role)
PERMANENT_EXCLUDE = [
    'Messpc',
    'VDI',
]

# Cato Socket onboarding is an explicit operator operation. Generic bulk
# sweep/untag actions must neither hold a released Socket nor release a held one.
CONTROLLED_RELEASE_ROLES = [
    'Sd Wan Socket',
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Tag devices/VMs with onboarding to exclude from Zabbix sync.',
    )
    parser.add_argument('--dry-run', action='store_true', help='Show counts without tagging')
    parser.add_argument(
        '--untag',
        action='store_true',
        help='Remove onboarding from ordinary hosts only',
    )
    args = parser.parse_args()

    tag = Tag.objects.filter(slug='onboarding').first()
    if tag is None:
        print('ERROR: onboarding tag not found. Run configure_nbxsync_zerotouch.py first.')
        return 1

    if args.untag:
        # Never release a controlled Socket through a broad --untag operation.
        devs = Device.objects.filter(tags=tag).exclude(
            role__name__in=CONTROLLED_RELEASE_ROLES
        )
        vms = VirtualMachine.objects.filter(tags=tag).exclude(
            role__name__in=CONTROLLED_RELEASE_ROLES
        )
        dev_count = devs.count()
        vm_count = vms.count()
        if not args.dry_run:
            for dev in devs:
                dev.tags.remove(tag)
            for vm in vms:
                vm.tags.remove(tag)
        action = 'Would remove' if args.dry_run else 'Removed'
        print(f'{action} onboarding tag from {dev_count} devices + {vm_count} VMs')
        print(f'Controlled release (unchanged): {", ".join(CONTROLLED_RELEASE_ROLES)}')
        if not args.dry_run:
            print('Run a sync to bring released hosts back into Zabbix.')
        return 0

    # Tag everything EXCEPT infrastructure, permanent exclusions, and
    # controlled-release roles.
    exclude_q = (
        Q(role__name__in=INFRASTRUCTURE_ROLES)
        | Q(role__name__in=PERMANENT_EXCLUDE)
        | Q(role__name__in=CONTROLLED_RELEASE_ROLES)
        | Q(role__isnull=True)
    )

    # Devices
    devs = Device.objects.exclude(exclude_q)
    dev_count = 0
    for dev in devs:
        if not dev.tags.filter(pk=tag.pk).exists():
            dev_count += 1
            if not args.dry_run:
                dev.tags.add(tag)

    vms = VirtualMachine.objects.exclude(exclude_q)
    vm_count = 0
    for vm in vms:
        if not vm.tags.filter(pk=tag.pk).exists():
            vm_count += 1
            if not args.dry_run:
                vm.tags.add(tag)

    mode = 'DRY RUN' if args.dry_run else 'TAGGED'
    print(f'{mode}: {dev_count} devices + {vm_count} VMs with onboarding tag')
    print(f'Excluded (stay in Zabbix): {", ".join(INFRASTRUCTURE_ROLES)}')
    print(f'Permanent exclude (do_not_monitor): {", ".join(PERMANENT_EXCLUDE)}')
    print(
        f'Controlled release (manual onboarding only): {", ".join(CONTROLLED_RELEASE_ROLES)}'
    )
    if not args.dry_run:
        print('\nNext: sync all hosts to exclude tagged hosts from Zabbix.')
        print('  sudo -n bash -c \'set -a; source /etc/netbox.env; set +a; \\')
        print('    cd /opt/netbox/netbox && PYTHONPATH=. DJANGO_SETTINGS_MODULE=netbox.settings \\')
        print('    /opt/netbox/venv/bin/python3 scripts/sync_all_hosts.py\'')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
