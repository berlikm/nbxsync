"""Report (and optionally purge) empty Zabbix host groups known to nbxsync.

Nested host groups are a naming convention in Zabbix: renaming a path segment
never cascades, so editing a Jinja template or title-casing a site can leave
the old path behind as an empty group once nbxsync migrated every host to the
new path. Zabbix itself never removes empty groups.

nbxsync deliberately follows an additive model and never deletes groups from
Zabbix in core code. This contrib script provides the housekeeping step as an
explicit operator-run action instead:

- Reports all host groups that nbxsync created/knows (any ZabbixHostgroup row
  with a stored groupid) that currently contain no hosts.
- With --delete, removes them. Zabbix refuses to delete a group that is the
  only group of a host, so this cannot strand a host.

Usage (dry run — reports only):

    cd /opt/netbox/netbox
    python manage.py nbshell < purge_empty_hostgroups.py

Usage (delete):

    python manage.py nbshell -- --delete < purge_empty_hostgroups.py

Requires the plugin to be installed and configured; one report per
ZabbixServer row is produced.
"""

import sys

from nbxsync.models import ZabbixHostgroup, ZabbixServer
from nbxsync.utils.zabbixconnection import ZabbixConnection

dry_run = '--delete' not in sys.argv


def purge_server(server):
    known_groupids = set(ZabbixHostgroup.objects.filter(zabbixserver=server, groupid__isnull=False).values_list('groupid', flat=True))
    if not known_groupids:
        print(f'[{server.name}] no plugin-known host groups, skipping')
        return 0

    removed = 0
    with ZabbixConnection(server) as api:
        groups = {group['groupid']: group['name'] for group in api.hostgroup.get(output=['groupid', 'name'])}
        for groupid in sorted(known_groupids, key=str):
            gid = str(groupid)
            name = groups.get(gid)
            if name is None:
                print(f'[{server.name}] {gid}: group no longer exists in Zabbix (local row: consider deleting the ZabbixHostgroup)')
                continue
            members = api.host.get(groupids=[gid], output=['hostid'])
            if members:
                print(f'[{server.name}] {name} ({gid}): {len(members)} host(s), keeping')
                continue
            if dry_run:
                print(f'[{server.name}] {name} ({gid}): EMPTY — would delete (rerun with --delete)')
                continue
            api.hostgroup.delete([gid])
            print(f'[{server.name}] {name} ({gid}): deleted')
            removed += 1
    return removed


total = 0
for zabbixserver in ZabbixServer.objects.all():
    total += purge_server(zabbixserver)

print()
print('DRY RUN — no groups were deleted. Rerun with --delete to remove the listed groups.' if dry_run else f'Done — {total} empty group(s) deleted.')
