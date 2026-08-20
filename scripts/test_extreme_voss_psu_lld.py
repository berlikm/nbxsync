#!/usr/bin/env python3
"""VOSS PSU LLD must skip empty chassis bays and still ticket a failed FRU."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

from validate_extreme_templates import _tpl, voss_psu_lld_skips_empty

ROOT = Path(__file__).resolve().parents[1]
VOSS_YAML = ROOT / 'zabbix/templates/extreme_voss_snmp/template_net_extreme_voss_snmp.yaml'
_STATUS_OID = '1.3.6.1.4.1.2272.1.4.8.1.1.2'
_DETAIL_STATUS_OID = '1.3.6.1.4.1.2272.1.4.8.2.1.15'


def _rules() -> dict[str, dict]:
    doc = yaml.safe_load(VOSS_YAML.read_text())
    tpl = _tpl(doc)
    return {r.get('key'): r for r in (tpl.get('discovery_rules') or [])}


class VossPsuEmptySkipTests(unittest.TestCase):
    def test_status_discovery_skips_empty_keeps_down(self):
        rule = _rules()['psu.discovery']
        self.assertTrue(voss_psu_lld_skips_empty(rule, _STATUS_OID))
        self.assertIn(_STATUS_OID, rule['snmp_oid'])
        values = [c.get('value') for c in (rule.get('filter') or {}).get('conditions') or []]
        self.assertIn('^2$', values)
        self.assertNotIn('^4$', values)

    def test_detail_discovery_skips_empty_keeps_down(self):
        rule = _rules()['psu.detail.discovery']
        self.assertTrue(voss_psu_lld_skips_empty(rule, _DETAIL_STATUS_OID))
        self.assertIn(_DETAIL_STATUS_OID, rule['snmp_oid'])
        values = [c.get('value') for c in (rule.get('filter') or {}).get('conditions') or []]
        self.assertIn('^2$', values)
        self.assertNotIn('^4$', values)

    def test_empty_without_status_walk_is_rejected(self):
        rule = {
            'snmp_oid': 'discovery[{#SNMPVALUE},1.3.6.1.4.1.2272.1.4.8.1.1.1]',
            'lifetime': '7d',
            'lifetime_type': 'DELETE_AFTER',
            'enabled_lifetime': '0',
            'enabled_lifetime_type': 'DISABLE_IMMEDIATELY',
            'filter': {
                'conditions': [
                    {'macro': '{#PSU.STATUS}', 'value': '^2$', 'operator': 'NOT_MATCHES_REGEX'},
                ]
            },
        }
        self.assertFalse(voss_psu_lld_skips_empty(rule, _STATUS_OID))

    def test_skipping_down_is_not_the_empty_filter(self):
        rule = {
            'snmp_oid': (
                'discovery[{#SNMPVALUE},1.3.6.1.4.1.2272.1.4.8.1.1.1,'
                '{#PSU.STATUS},1.3.6.1.4.1.2272.1.4.8.1.1.2]'
            ),
            'lifetime': '7d',
            'lifetime_type': 'DELETE_AFTER',
            'enabled_lifetime': '0',
            'enabled_lifetime_type': 'DISABLE_IMMEDIATELY',
            'filter': {
                'conditions': [
                    {'macro': '{#PSU.STATUS}', 'value': '^4$', 'operator': 'NOT_MATCHES_REGEX'},
                ]
            },
        }
        self.assertFalse(voss_psu_lld_skips_empty(rule, _STATUS_OID))

    def test_yaml_tickets_unknown_and_down(self):
        from extreme_psu import psu_expr_is_not_up

        rule = _rules()['psu.discovery']
        trigs = []
        for it in rule.get('item_prototypes') or []:
            trigs.extend(it.get('trigger_prototypes') or [])
        self.assertTrue(trigs)
        expr = trigs[0].get('expression') or ''
        self.assertTrue(psu_expr_is_not_up(expr))
        self.assertNotIn('{$PSU_CRIT_STATUS}', expr)
        self.assertIn('not up', (trigs[0].get('name') or '').lower())


if __name__ == '__main__':
    unittest.main()
