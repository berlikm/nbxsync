from django.test import TestCase

from extras.models import Tag as NetBoxTag
from utilities.testing import create_test_device

from nbxsync.models import ZabbixHostgroup, ZabbixServer, ZabbixTemplate, ZabbixTemplateRule
from nbxsync.utils.inheritance import get_assigned_zabbixobjects


class TemplateRuleCompoundCriteriaTestCase(TestCase):
    """Rule criteria are conjunctive: every configured criterion must match."""

    def setUp(self):
        self.server = ZabbixServer.objects.create(name='Criteria Zabbix', url='http://zabbix.local', token='abc123', validate_certs=True)
        self.template = ZabbixTemplate.objects.create(name='Rule Template', zabbixserver=self.server, templateid=42)
        self.tag = NetBoxTag.objects.create(name='critical', slug='critical')
        self.device = create_test_device(name='CompoundDev')

    def _rule(self, pattern='.*', role_pattern='', require_tags=''):
        return ZabbixTemplateRule(name='test-rule', pattern=pattern, zabbixtemplate=self.template, role_pattern=role_pattern, require_tags=require_tags)

    # --- matches() matrix ---

    def test_all_criteria_empty_matches_platform_only(self):
        rule = self._rule(pattern='Ubuntu')
        self.assertTrue(rule.matches('Ubuntu 22.04'))
        self.assertFalse(rule.matches('Windows'))

    def test_backward_compatible_single_arg_signature(self):
        rule = self._rule(pattern='Linux')
        self.assertTrue(rule.matches('Arch Linux'))

    def test_role_pattern_constrains(self):
        rule = self._rule(pattern='.*', role_pattern='^Switch')
        self.assertTrue(rule.matches('anything', role_name='Switch Core'))
        self.assertFalse(rule.matches('anything', role_name='Server'))

    def test_role_pattern_set_but_object_roleless_fails_closed(self):
        rule = self._rule(pattern='.*', role_pattern='^Switch')
        self.assertFalse(rule.matches('anything', role_name=None))

    def test_require_tags_all_must_be_present(self):
        rule = self._rule(pattern='.*', require_tags='critical,prod')
        self.assertTrue(rule.matches('x', netbox_tags={'critical', 'prod', 'extra'}))
        self.assertFalse(rule.matches('x', netbox_tags={'critical'}))
        self.assertFalse(rule.matches('x', netbox_tags=None))

    def test_all_three_criteria_anded(self):
        rule = self._rule(pattern='Linux', role_pattern='^Server', require_tags='critical')
        self.assertTrue(rule.matches('Ubuntu Linux', role_name='Server', netbox_tags={'critical'}))
        self.assertFalse(rule.matches('Windows', role_name='Server', netbox_tags={'critical'}))
        self.assertFalse(rule.matches('Ubuntu Linux', role_name='Switch', netbox_tags={'critical'}))
        self.assertFalse(rule.matches('Ubuntu Linux', role_name='Server', netbox_tags={'other'}))

    def test_platformless_object_matches_catchall_only(self):
        self.assertTrue(self._rule(pattern='.*').matches(None))
        self.assertFalse(self._rule(pattern='Windows').matches(None))

    def test_disabled_or_garbage_never_raises_and_never_matches(self):
        r = self._rule(pattern='.*')
        r.enabled = False
        self.assertFalse(r.matches('Ubuntu'))


class TemplateRuleCompoundCriteriaCleanTestCase(TestCase):
    def test_role_pattern_nested_quantifier_rejected(self):
        from django.core.exceptions import ValidationError

        rule = ZabbixTemplateRule(name='bad', pattern='.*', role_pattern='(a+)+$', require_tags='')
        with self.assertRaises(ValidationError):
            rule.clean()

    def test_require_tags_rejects_non_slug(self):
        from django.core.exceptions import ValidationError

        rule = ZabbixTemplateRule(name='bad', pattern='.*', role_pattern='', require_tags='Critical!')
        with self.assertRaises(ValidationError):
            rule.clean()


class TemplateRuleCompoundResolutionTestCase(TestCase):
    """End-to-end through the resolver: criteria compound against the object."""

    def setUp(self):
        self.server = ZabbixServer.objects.create(name='Res Zabbix', url='http://zabbix.local', token='abc123', validate_certs=True)
        self.hostgroup = ZabbixHostgroup.objects.create(name='Rule Group', value='Rule Group', zabbixserver=self.server)
        self.template = ZabbixTemplate.objects.create(name='T', zabbixserver=self.server, templateid=43)
        self.tag = NetBoxTag.objects.create(name='critical', slug='critical')

    def test_rule_fires_only_when_all_criteria_match(self):
        rule = ZabbixTemplateRule.objects.create(name='combo', pattern='.*', zabbixtemplate=self.template, role_pattern=f'^{self.tag.slug[:2]}', require_tags=str(self.tag.slug))
        # device role is 'Device Role' from create_test_device, platform None
        device = create_test_device(name='ComboDev')
        result = get_assigned_zabbixobjects(device)
        self.assertNotIn(rule.zabbixtemplate_id, [t.zabbixtemplate_id for t in result['templates']])

        # tag the device -> tag criterion still fails (role pattern does not match role name)
        device.tags.add(self.tag)
        result = get_assigned_zabbixobjects(device)
        self.assertNotIn(rule.zabbixtemplate_id, [t.zabbixtemplate_id for t in result['templates']])

        # role pattern that matches the test device's role + tag present -> fires
        rule.role_pattern = '.*'
        rule.save()
        result = get_assigned_zabbixobjects(device)
        self.assertIn(rule.zabbixtemplate_id, [t.zabbixtemplate_id for t in result['templates']])
