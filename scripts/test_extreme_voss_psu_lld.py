#!/usr/bin/env python3
"""VOSS PSU LLD must skip empty(2), including dummy serial --."""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

from extreme_psu import (
    PSU_SERIAL_MACRO,
    VOSS_PSU_DETAIL_DISCOVERY_OID,
    VOSS_PSU_DISCOVERY_OID,
    VOSS_PSU_SERIAL_OID,
    psu_expr_is_not_up,
    psu_lld_defaults_missing_macros,
    psu_lld_js_clears_dummy_serials,
    psu_lld_js_default_macros,
)
from validate_extreme_templates import _tpl, voss_psu_lld_keeps_installed_fru

ROOT = Path(__file__).resolve().parents[1]
VOSS_YAML = ROOT / 'zabbix/templates/extreme_voss_snmp/template_net_extreme_voss_snmp.yaml'
_STATUS_OID = '1.3.6.1.4.1.2272.1.4.8.1.1.2'
_DETAIL_STATUS_OID = '1.3.6.1.4.1.2272.1.4.8.2.1.15'


def _rules() -> dict[str, dict]:
    doc = yaml.safe_load(VOSS_YAML.read_text())
    tpl = _tpl(doc)
    return {r.get('key'): r for r in (tpl.get('discovery_rules') or [])}


def _legacy_or_filter() -> dict:
    return {
        'evaltype': 'OR',
        'conditions': [
            {'macro': '{#PSU.STATUS}', 'value': '^2$', 'operator': 'NOT_MATCHES_REGEX'},
            {'macro': PSU_SERIAL_MACRO, 'value': '.+', 'operator': 'MATCHES_REGEX'},
        ],
    }


class VossPsuInstalledFruTests(unittest.TestCase):
    def test_status_discovery_skips_empty_even_with_dummy_serial(self):
        rule = _rules()['psu.discovery']
        self.assertTrue(voss_psu_lld_keeps_installed_fru(rule, _STATUS_OID))
        self.assertEqual(rule['snmp_oid'], VOSS_PSU_DISCOVERY_OID)
        self.assertIn(VOSS_PSU_SERIAL_OID, rule['snmp_oid'])
        filt = rule.get('filter') or {}
        self.assertEqual(str(filt.get('evaltype') or '').upper(), 'AND')
        values = [c.get('value') for c in filt.get('conditions') or []]
        self.assertIn('^2$', values)
        self.assertNotIn('.+', values)
        self.assertNotIn('^4$', values)
        self.assertTrue(psu_lld_defaults_missing_macros(rule))
        self.assertTrue(psu_lld_js_clears_dummy_serials(rule))

    def test_detail_discovery_skips_empty_even_with_dummy_serial(self):
        rule = _rules()['psu.detail.discovery']
        self.assertTrue(voss_psu_lld_keeps_installed_fru(rule, _DETAIL_STATUS_OID))
        self.assertEqual(rule['snmp_oid'], VOSS_PSU_DETAIL_DISCOVERY_OID)
        values = [c.get('value') for c in (rule.get('filter') or {}).get('conditions') or []]
        self.assertIn('^2$', values)
        self.assertNotIn('.+', values)
        self.assertNotIn('^4$', values)
        self.assertTrue(psu_lld_defaults_missing_macros(rule))
        self.assertTrue(psu_lld_js_clears_dummy_serials(rule))

    def test_yaml_js_matches_helper(self):
        want = psu_lld_js_default_macros().strip()
        for key in ('psu.discovery', 'psu.detail.discovery'):
            rule = _rules()[key]
            params = (rule.get('preprocessing') or [{}])[0].get('parameters') or []
            got = str(params[0] if params else '').strip()
            self.assertEqual(got, want, key)

    def test_empty_without_status_walk_is_rejected(self):
        rule = {
            'snmp_oid': 'discovery[{#SNMPVALUE},1.3.6.1.4.1.2272.1.4.8.1.1.1]',
            'lifetime': '0',
            'lifetime_type': 'DELETE_IMMEDIATELY',
            'enabled_lifetime': '0',
            'enabled_lifetime_type': 'DISABLE_IMMEDIATELY',
            'filter': {
                'evaltype': 'AND',
                'conditions': [
                    {'macro': '{#PSU.STATUS}', 'value': '^2$', 'operator': 'NOT_MATCHES_REGEX'},
                ],
            },
            'preprocessing': [{'type': 'JAVASCRIPT', 'params': psu_lld_js_default_macros()}],
        }
        self.assertFalse(voss_psu_lld_keeps_installed_fru(rule, _STATUS_OID))

    def test_skipping_down_is_not_the_empty_filter(self):
        rule = {
            'snmp_oid': VOSS_PSU_DISCOVERY_OID,
            'lifetime': '0',
            'lifetime_type': 'DELETE_IMMEDIATELY',
            'enabled_lifetime': '0',
            'enabled_lifetime_type': 'DISABLE_IMMEDIATELY',
            'filter': {
                'evaltype': 'AND',
                'conditions': [
                    {'macro': '{#PSU.STATUS}', 'value': '^4$', 'operator': 'NOT_MATCHES_REGEX'},
                ],
            },
            'preprocessing': [{'type': 'JAVASCRIPT', 'params': psu_lld_js_default_macros()}],
        }
        self.assertFalse(voss_psu_lld_keeps_installed_fru(rule, _STATUS_OID))

    def test_legacy_or_serial_keep_is_rejected(self):
        rule = {
            'snmp_oid': VOSS_PSU_DISCOVERY_OID,
            'lifetime': '0',
            'lifetime_type': 'DELETE_IMMEDIATELY',
            'enabled_lifetime': '0',
            'enabled_lifetime_type': 'DISABLE_IMMEDIATELY',
            'filter': _legacy_or_filter(),
            'preprocessing': [{'type': 'JAVASCRIPT', 'params': psu_lld_js_default_macros()}],
        }
        self.assertFalse(voss_psu_lld_keeps_installed_fru(rule, _STATUS_OID))

    def test_filter_without_dummy_serial_js_is_not_enough(self):
        rule = {
            'snmp_oid': VOSS_PSU_DISCOVERY_OID,
            'lifetime': '0',
            'lifetime_type': 'DELETE_IMMEDIATELY',
            'enabled_lifetime': '0',
            'enabled_lifetime_type': 'DISABLE_IMMEDIATELY',
            'filter': {
                'evaltype': 'AND',
                'conditions': [
                    {'macro': '{#PSU.STATUS}', 'value': '^2$', 'operator': 'NOT_MATCHES_REGEX'},
                ],
            },
            'preprocessing': [
                {
                    'type': 'JAVASCRIPT',
                    'params': (
                        "try {\n\tvar data = JSON.parse(value);\n}\n"
                        "catch (error) {\n\tthrow 'Failed to parse JSON of PSU discovery.';\n}\n"
                        "var fields = ['{#PSU.STATUS}','{#PSU.SERIAL}'];\n"
                        "data.forEach(function (element) {\n"
                        "\tfields.forEach(function (field) {\n"
                        "\t\telement[field] = element[field] || '';\n"
                        "\t});\n"
                        "});\n"
                        "return JSON.stringify(data);\n"
                    ),
                }
            ],
        }
        self.assertFalse(voss_psu_lld_keeps_installed_fru(rule, _STATUS_OID))

    def test_lifetime_7d_is_not_enough(self):
        rule = {
            'snmp_oid': VOSS_PSU_DISCOVERY_OID,
            'lifetime': '7d',
            'lifetime_type': 'DELETE_AFTER',
            'enabled_lifetime': '0',
            'enabled_lifetime_type': 'DISABLE_IMMEDIATELY',
            'filter': {
                'evaltype': 'AND',
                'conditions': [
                    {'macro': '{#PSU.STATUS}', 'value': '^2$', 'operator': 'NOT_MATCHES_REGEX'},
                ],
            },
            'preprocessing': [{'type': 'JAVASCRIPT', 'params': psu_lld_js_default_macros()}],
        }
        self.assertFalse(voss_psu_lld_keeps_installed_fru(rule, _STATUS_OID))

    def test_yaml_deletes_lost_psu_rows_immediately(self):
        for key in ('psu.discovery', 'psu.detail.discovery'):
            rule = _rules()[key]
            self.assertEqual(str(rule.get('lifetime')), '0')
            self.assertEqual(rule.get('lifetime_type'), 'DELETE_IMMEDIATELY')
            self.assertEqual(str(rule.get('enabled_lifetime')), '0')

    def test_yaml_tickets_not_up_but_not_empty_padding(self):
        rule = _rules()['psu.discovery']
        trigs = []
        for it in rule.get('item_prototypes') or []:
            trigs.extend(it.get('trigger_prototypes') or [])
        self.assertTrue(trigs)
        expr = trigs[0].get('expression') or ''
        self.assertTrue(psu_expr_is_not_up(expr))
        self.assertNotIn('{$PSU_CRIT_STATUS}', expr)
        self.assertIn('{$PSU.EMPTY_STATUS}', expr)
        self.assertIn('not up', (trigs[0].get('name') or '').lower())


if __name__ == '__main__':
    unittest.main()
