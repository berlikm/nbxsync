import logging

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError

from nbxsync.models import ZabbixHostBinding
from nbxsync.settings import get_plugin_settings

logger = logging.getLogger(__name__)

__all__ = (
    'get_host_binding',
    'set_host_binding',
    'delete_host_binding',
    'iter_host_bindings',
    'backfill_or_resolve_conflict',
    'HostBindingDeleteProxy',
)


def get_host_binding(instance, zabbixserver):
    """Return the ZabbixHostBinding for a given NetBox object and server, if any."""
    ct = ContentType.objects.get_for_model(instance)
    return ZabbixHostBinding.objects.filter(
        zabbixserver=zabbixserver,
        assigned_object_type=ct,
        assigned_object_id=instance.pk,
    ).first()


def set_host_binding(instance, zabbixserver, hostid, hostname=''):
    """Create or update the binding for ``instance`` -> ``hostid``.

    Raises ``RuntimeError`` if the hostid is already bound to another object
    on the same server (duplicate managed identity).
    """
    ct = ContentType.objects.get_for_model(instance)
    try:
        binding, _ = ZabbixHostBinding.objects.update_or_create(
            zabbixserver=zabbixserver,
            assigned_object_type=ct,
            assigned_object_id=instance.pk,
            defaults={'hostid': hostid, 'hostname': hostname},
        )
    except IntegrityError as exc:
        raise RuntimeError(f'Host binding conflict for {instance} on {zabbixserver}: ' f'hostid {hostid} or object is already bound to another host') from exc
    return binding


def delete_host_binding(instance, zabbixserver=None):
    """Remove all bindings for ``instance``, optionally scoped to one server."""
    ct = ContentType.objects.get_for_model(instance)
    qs = ZabbixHostBinding.objects.filter(assigned_object_type=ct, assigned_object_id=instance.pk)
    if zabbixserver is not None:
        qs = qs.filter(zabbixserver=zabbixserver)
    qs.delete()


def iter_host_bindings(instance):
    """Iterate over all bindings for ``instance``."""
    ct = ContentType.objects.get_for_model(instance)
    return ZabbixHostBinding.objects.filter(
        assigned_object_type=ct,
        assigned_object_id=instance.pk,
    ).select_related('zabbixserver')


def _host_tags_to_dict(host):
    return {tag['tag']: tag['value'] for tag in host.get('tags', [])}


def _expected_source_tags(instance):
    pluginsettings = get_plugin_settings()
    return {
        pluginsettings.objtag_type: str(type(instance).__name__).lower(),
        pluginsettings.objtag_id: str(instance.pk),
    }


def backfill_or_resolve_conflict(instance, zabbixserver, api):
    """Adopt an existing Zabbix host by its managed source tags.

    If no host with the same technical name exists, returns ``None`` so the
    caller can create a new one. If an unmanaged host with the same name
    exists, or if the matching host belongs to another NetBox object, a
    ``RuntimeError`` is raised.
    """
    name = str(instance.name) if hasattr(instance, 'name') else str(instance)
    hosts = api.host.get(filter={'host': name}, selectTags='extend')
    if isinstance(hosts, dict):
        hosts = hosts.get('result', [])

    if not hosts:
        return None

    expected = _expected_source_tags(instance)
    matches = [host for host in hosts if all(_host_tags_to_dict(host).get(k) == v for k, v in expected.items())]

    if len(matches) == 1:
        return int(matches[0]['hostid'])

    if len(hosts) == 1 and not matches:
        raise RuntimeError(f'Unmanaged host conflict: a Zabbix host named "{name}" exists ' f'but does not match the managed identity for {instance}.')

    raise RuntimeError(f'Ambiguous host conflict: {len(hosts)} Zabbix hosts found with name "{name}".')


class HostBindingDeleteProxy:
    """Minimal stand-in for ``ZabbixServerAssignment`` when deleting by binding.

    ``HostSync.delete`` expects an assignment-like object with ``zabbixserver``,
    ``hostid``, ``assigned_object``, and update/sync methods. This proxy lets us
    reuse the same delete path when only a ``ZabbixHostBinding`` is available.
    """

    _is_inherited_copy = False

    def __init__(self, zabbixserver, hostid, assigned_object):
        self.zabbixserver = zabbixserver
        self.hostid = hostid
        self.assigned_object = assigned_object
        self.assigned_object_type = ContentType.objects.get_for_model(assigned_object)
        self.assigned_object_id = assigned_object.pk

    def update_sync_info(self, *args, **kwargs):
        pass

    def save(self, *args, **kwargs):
        pass
