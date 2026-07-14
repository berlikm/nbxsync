from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from utilities.testing import create_test_device

from nbxsync.models import ZabbixHostBinding, ZabbixServer, ZabbixServerAssignment
from nbxsync.utils.host_binding import HostBindingDeleteProxy
from nbxsync.utils.sync import HostSync


class HostBindingTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix', url='http://zabbix.local', token='t')
        cls.device = create_test_device(name='binding-test')
        cls.device_ct = ContentType.objects.get_for_model(cls.device)
        cls.assignment = ZabbixServerAssignment.objects.create(
            zabbixserver=cls.server,
            assigned_object_type=cls.device_ct,
            assigned_object_id=cls.device.pk,
        )

    def _all_objects(self):
        return {
            'hostgroups': [],
            'tags': [],
            'macros': [],
            'hostinterfaces': [],
            'templates': [],
            'hostinventory': None,
            '_instance': self.device,
        }

    def _api(self, host_get=None):
        api = MagicMock()
        api.host.get.return_value = host_get if host_get is not None else []
        api.host.create.return_value = {'hostids': ['100']}
        api.host.update.return_value = {'hostids': ['100']}
        api.hostinterface.get.return_value = []
        api.template.get.return_value = []
        api.maintenance.get.return_value = []
        return api

    def _attach_assigned_objects(self, assignment):
        assignment.assigned_objects = self._all_objects()

    def test_inherited_creation_persists_binding(self):
        inherited = MagicMock()
        inherited.zabbixserver = self.server
        inherited.hostid = None
        inherited.assigned_object = self.device
        inherited.assigned_object_type = self.device_ct
        inherited.assigned_object_id = self.device.pk
        inherited._is_inherited_copy = True
        inherited.pk = None
        inherited.update_sync_info = MagicMock()
        inherited.assigned_objects = self._all_objects()

        api = self._api()
        sync = HostSync(api=api, netbox_obj=inherited, all_objects=self._all_objects())
        sync.sync()

        binding = ZabbixHostBinding.objects.get(
            assigned_object_id=self.device.pk, zabbixserver=self.server
        )
        self.assertEqual(binding.hostid, 100)

    def test_second_sync_uses_same_hostid(self):
        api = self._api()
        self._attach_assigned_objects(self.assignment)
        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        sync.sync()

        api.host.get.return_value = [{'hostid': '100', 'host': 'binding-test', 'name': 'binding-test'}]
        api.host.create.reset_mock()

        sync2 = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        self._attach_assigned_objects(self.assignment)
        sync2.sync()

        api.host.create.assert_not_called()
        binding = ZabbixHostBinding.objects.get(
            assigned_object_id=self.device.pk, zabbixserver=self.server
        )
        self.assertEqual(binding.hostid, 100)

    def test_rename_updates_same_hostid(self):
        api = self._api()
        self._attach_assigned_objects(self.assignment)
        HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects()).sync()

        self.device.name = 'renamed-binding-test'
        self.device.save()

        api.host.get.return_value = [{'hostid': '100', 'host': 'binding-test', 'name': 'binding-test'}]
        api.host.create.reset_mock()

        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        self._attach_assigned_objects(self.assignment)
        sync.sync()

        binding = ZabbixHostBinding.objects.get(
            assigned_object_id=self.device.pk, zabbixserver=self.server
        )
        self.assertEqual(binding.hostid, 100)
        self.assertEqual(binding.hostname, 'renamed-binding-test')

    def test_unmanaged_same_name_conflict(self):
        def host_get(**kwargs):
            if kwargs.get('hostids'):
                return []
            if kwargs.get('filter', {}).get('host'):
                return [{'hostid': '200', 'host': 'binding-test', 'name': 'binding-test', 'tags': []}]
            return []

        api = MagicMock()
        api.host.get.side_effect = host_get
        self._attach_assigned_objects(self.assignment)

        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        with self.assertRaises(RuntimeError):
            sync.sync()

    def test_duplicate_managed_identity_conflict(self):
        other_device = create_test_device(name='other-binding-test')
        ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=other_device.pk,
            hostid=777,
            hostname='other',
        )
        self.assignment.hostid = 777
        self.assignment.save()

        api = self._api(host_get=[{'hostid': '777', 'host': 'binding-test', 'name': 'binding-test'}])
        self._attach_assigned_objects(self.assignment)

        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        with self.assertRaises(RuntimeError):
            sync.sync()

    def test_decommission_deletes_by_hostid(self):
        ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=100,
            hostname='binding-test',
        )
        api = self._api()
        self._attach_assigned_objects(self.assignment)

        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        sync.delete()

        api.host.delete.assert_called_once_with([100])
        self.assertFalse(
            ZabbixHostBinding.objects.filter(
                assigned_object_id=self.device.pk, zabbixserver=self.server
            ).exists()
        )

    def test_missing_remote_host_is_idempotent(self):
        ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=999,
            hostname='binding-test',
        )
        api = self._api()
        self._attach_assigned_objects(self.assignment)

        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        sync.sync()

        binding = ZabbixHostBinding.objects.get(
            assigned_object_id=self.device.pk, zabbixserver=self.server
        )
        self.assertEqual(binding.hostid, 100)

    def test_direct_assignment_hostid_migrates_to_binding(self):
        self.assignment.hostid = 222
        self.assignment.save()

        def host_get(**kwargs):
            if kwargs.get('hostids') == ['222']:
                return [{'hostid': '222', 'host': 'binding-test', 'name': 'binding-test'}]
            return []

        api = MagicMock()
        api.host.get.side_effect = host_get
        api.host.create.return_value = {'hostids': ['222']}
        api.host.update.return_value = {'hostids': ['222']}
        api.hostinterface.get.return_value = []
        api.template.get.return_value = []
        api.maintenance.get.return_value = []
        self._attach_assigned_objects(self.assignment)

        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        sync.sync()

        binding = ZabbixHostBinding.objects.get(
            assigned_object_id=self.device.pk, zabbixserver=self.server
        )
        self.assertEqual(binding.hostid, 222)
        self.assignment.refresh_from_db()
        self.assertIsNone(self.assignment.hostid)

    def test_existing_hosts_backfill(self):
        def host_get(**kwargs):
            if kwargs.get('hostids'):
                return []
            if kwargs.get('filter', {}).get('host'):
                return [{
                    'hostid': '300',
                    'host': 'binding-test',
                    'name': 'binding-test',
                    'tags': [
                        {'tag': 'nb_type', 'value': 'device'},
                        {'tag': 'nb_id', 'value': str(self.device.pk)},
                    ],
                }]
            return []

        api = MagicMock()
        api.host.get.side_effect = host_get
        api.hostinterface.get.return_value = []
        api.template.get.return_value = []
        api.maintenance.get.return_value = []
        self._attach_assigned_objects(self.assignment)

        sync = HostSync(api=api, netbox_obj=self.assignment, all_objects=self._all_objects())
        sync.sync()

        binding = ZabbixHostBinding.objects.get(
            assigned_object_id=self.device.pk, zabbixserver=self.server
        )
        self.assertEqual(binding.hostid, 300)


class BindingJobTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.server = ZabbixServer.objects.create(name='Zabbix', url='http://zabbix.local', token='t')
        cls.device = create_test_device(name='binding-job-test')
        cls.device_ct = ContentType.objects.get_for_model(cls.device)

    def test_deletejob_hard_deletes_by_binding(self):
        ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=888,
            hostname='binding-job-test',
        )

        from nbxsync.jobs.deletehost import DeleteHostJob

        with patch('nbxsync.jobs.deletehost.safe_delete') as mock_safe_delete:
            job = DeleteHostJob(instance=self.device)
            job.run()

        self.assertEqual(mock_safe_delete.call_count, 1)
        proxy = mock_safe_delete.call_args[0][1]
        self.assertIsInstance(proxy, HostBindingDeleteProxy)
        self.assertEqual(proxy.hostid, 888)
        self.assertFalse(
            ZabbixHostBinding.objects.filter(
                assigned_object_id=self.device.pk, zabbixserver=self.server
            ).exists()
        )

    def test_retire_unassigned_bindings(self):
        binding = ZabbixHostBinding.objects.create(
            zabbixserver=self.server,
            assigned_object_type=self.device_ct,
            assigned_object_id=self.device.pk,
            hostid=555,
            hostname='binding-job-test',
        )

        from nbxsync.jobs.synchost import SyncHostJob

        with patch('nbxsync.jobs.synchost.safe_delete') as mock_safe_delete:
            job = SyncHostJob(instance=self.device)
            job._retire_unassigned_bindings(set())

        mock_safe_delete.assert_called_once()
        proxy = mock_safe_delete.call_args[0][1]
        self.assertIsInstance(proxy, HostBindingDeleteProxy)
        self.assertEqual(proxy.zabbixserver, self.server)
        self.assertEqual(proxy.hostid, binding.hostid)
        self.assertEqual(proxy.assigned_object, self.device)
