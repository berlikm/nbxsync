import logging

from django.contrib.contenttypes.models import ContentType

from nbxsync.models import ZabbixServerAssignment
from nbxsync.utils import get_assigned_zabbixobjects
from nbxsync.utils.host_binding import HostBindingDeleteProxy, delete_host_binding, iter_host_bindings
from nbxsync.utils.sync import HostSync
from nbxsync.utils.sync.safe_delete import safe_delete

logger = logging.getLogger(__name__)

__all__ = ('DeleteHostJob',)


class DeleteHostJob:
    def __init__(self, **kwargs):
        self.instance = kwargs.get('instance')  # This is the Device or VirtualMachine object

    def run(self):
        extra_args = {'all_objects': {'_instance': self.instance}}
        servers_seen = set()

        # Primary path: delete every durable binding for this instance.
        for binding in iter_host_bindings(self.instance):
            servers_seen.add(binding.zabbixserver_id)
            proxy = HostBindingDeleteProxy(
                zabbixserver=binding.zabbixserver,
                hostid=binding.hostid,
                assigned_object=self.instance,
            )
            try:
                safe_delete(HostSync, proxy, extra_args=extra_args)
            except Exception as e:
                logger.warning('Failed to delete bound host %s for %s: %s', binding, self.instance, e)

        # Legacy fallback: direct assignments that still carry a hostid but
        # have no binding yet. Inherited assignments are also handled here when
        # the binding is missing for any reason.
        try:
            all_objects = get_assigned_zabbixobjects(self.instance)
            server_assignments = all_objects.get('server_assignments', [])
        except Exception:
            logger.exception('Failed to resolve inherited assignments for %s; using direct assignments only.', self.instance)
            instance_ct = ContentType.objects.get_for_model(self.instance)
            server_assignments = ZabbixServerAssignment.objects.filter(
                assigned_object_type=instance_ct,
                assigned_object_id=self.instance.pk,
            ).select_related('zabbixserver')

        for assignment in server_assignments:
            if assignment.zabbixserver_id in servers_seen:
                continue
            if not assignment.sync_enabled or not assignment.zabbixserver.sync_enabled:
                continue
            servers_seen.add(assignment.zabbixserver_id)
            try:
                safe_delete(HostSync, assignment, extra_args=extra_args)
            except Exception as e:
                logger.warning('Failed to delete host for %s via assignment %s: %s', self.instance, assignment, e)

        # Make sure no stale bindings remain for the now-deleted object.
        delete_host_binding(self.instance)
