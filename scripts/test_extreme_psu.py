#!/usr/bin/env python3
"""Installed PSU not supplying power must Average; empty padding must not."""

from __future__ import annotations

import unittest

from extreme_psu import (
    EXOS_PSU_DISCOVERY_OID,
    EXOS_PSU_SERIAL_OID,
    EXOS_PSU_STATUS_OID,
    LLD_EVAL_AND,
    LLD_EVAL_OR,
    PSU_SERIAL_MACRO,
    VOSS_PSU_DISCOVERY_OID,
    VOSS_PSU_SERIAL_OID,
    VOSS_PSU_STATUS_OID,
    psu_expr_is_not_up,
    psu_lld_api_filter,
    psu_lld_defaults_missing_macros,
    psu_lld_js_clears_dummy_serials,
    psu_lld_js_default_macros,
    psu_lld_keeps_installed_fru,
    psu_lld_preprocessing_payload,
    psu_not_up_expr,
    psu_serial_is_dummy,
    rewrite_psu_not_up_expr,
)

_VOSS_COUNT = (
    'count(/Extreme VOSS by SNMP/sensor.psu.status[rcChasPowerSupplyOperStatus.{#SNMPINDEX}],'
    '#1,"eq","{$PSU_CRIT_STATUS}")=1'
)
_EXOS_COUNT = (
    'count(/Extreme EXOS by SNMP/sensor.psu.status[extremePowerSupplyStatus.{#SNMPINDEX}],'
    '#1,"eq","{$PSU_CRIT_STATUS}")=1'
)
_VOSS_PATH = (
    '/Extreme VOSS by SNMP/sensor.psu.status[rcChasPowerSupplyOperStatus.{#SNMPINDEX}]'
)
_EXOS_PATH = (
    '/Extreme EXOS by SNMP/sensor.psu.status[extremePowerSupplyStatus.{#SNMPINDEX}]'
)
_VOSS_LAST_ONLY = f'last({_VOSS_PATH})<>{{$PSU.OK_STATUS}}'
_VOSS_WANT = (
    f'last({_VOSS_PATH})<>{{$PSU.OK_STATUS}} and last({_VOSS_PATH})<>{{$PSU.EMPTY_STATUS}}'
)
_EXOS_WANT = f'last({_EXOS_PATH})<>{{$PSU.OK_STATUS}}'


class RewritePsuNotUpTests(unittest.TestCase):
    def test_rewrites_voss_count_eq_down(self):
        got = rewrite_psu_not_up_expr(_VOSS_COUNT)
        self.assertEqual(got, _VOSS_WANT)
        self.assertTrue(psu_expr_is_not_up(got))
        self.assertNotIn('{$PSU_CRIT_STATUS}', got)
        self.assertIn('{$PSU.EMPTY_STATUS}', got)

    def test_rewrites_exos_count_eq_present_not_ok(self):
        got = rewrite_psu_not_up_expr(_EXOS_COUNT)
        self.assertEqual(got, _EXOS_WANT)
        self.assertTrue(psu_expr_is_not_up(got))
        self.assertNotIn('{$PSU.EMPTY_STATUS}', got)

    def test_voss_adds_empty_exclusion_so_padding_recovers(self):
        self.assertFalse(psu_expr_is_not_up(_VOSS_LAST_ONLY))
        self.assertEqual(rewrite_psu_not_up_expr(_VOSS_LAST_ONLY), _VOSS_WANT)

    def test_idempotent(self):
        self.assertEqual(rewrite_psu_not_up_expr(_VOSS_WANT), _VOSS_WANT)
        self.assertEqual(rewrite_psu_not_up_expr(_EXOS_WANT), _EXOS_WANT)

    def test_stock_count_is_not_enough(self):
        self.assertFalse(psu_expr_is_not_up(_VOSS_COUNT))
        self.assertFalse(psu_expr_is_not_up(_EXOS_COUNT))

    def test_helper_builds_same_shape(self):
        self.assertEqual(psu_not_up_expr(_VOSS_PATH), _VOSS_WANT)
        self.assertEqual(psu_not_up_expr(_EXOS_PATH), _EXOS_WANT)

    def test_dummy_serials(self):
        self.assertTrue(psu_serial_is_dummy('--'))
        self.assertTrue(psu_serial_is_dummy('-'))
        self.assertTrue(psu_serial_is_dummy('n/a'))
        self.assertTrue(psu_serial_is_dummy(''))
        self.assertTrue(psu_serial_is_dummy('  '))
        self.assertFalse(psu_serial_is_dummy('PS123456'))

    def _fru_rule(self, *, snmp_oid, empty_regex, with_js=True, keep_serialled_empty=True):
        if keep_serialled_empty:
            filt = {
                'evaltype': 'OR',
                'conditions': [
                    {'macro': '{#PSU.STATUS}', 'value': empty_regex, 'operator': 'NOT_MATCHES_REGEX'},
                    {'macro': PSU_SERIAL_MACRO, 'value': '.+', 'operator': 'MATCHES_REGEX'},
                ],
            }
        else:
            filt = {
                'evaltype': 'AND',
                'conditions': [
                    {'macro': '{#PSU.STATUS}', 'value': empty_regex, 'operator': 'NOT_MATCHES_REGEX'},
                ],
            }
        rule = {'snmp_oid': snmp_oid, 'filter': filt}
        if with_js:
            rule['preprocessing'] = [
                {'type': 'JAVASCRIPT', 'params': psu_lld_js_default_macros()},
            ]
        return rule

    def test_voss_filter_skips_empty_even_with_dummy_serial_walk(self):
        self.assertTrue(
            psu_lld_keeps_installed_fru(
                self._fru_rule(
                    snmp_oid=VOSS_PSU_DISCOVERY_OID,
                    empty_regex='^2$',
                    keep_serialled_empty=False,
                ),
                status_oid=VOSS_PSU_STATUS_OID,
                serial_oid=VOSS_PSU_SERIAL_OID,
                empty_regex='^2$',
                keep_serialled_empty=False,
            )
        )

    def test_voss_or_serial_keep_is_not_enough(self):
        """OR + serial .+ is what kept MGMT03 PSU 2 (empty + --)."""
        self.assertFalse(
            psu_lld_keeps_installed_fru(
                self._fru_rule(
                    snmp_oid=VOSS_PSU_DISCOVERY_OID,
                    empty_regex='^2$',
                    keep_serialled_empty=True,
                ),
                status_oid=VOSS_PSU_STATUS_OID,
                serial_oid=VOSS_PSU_SERIAL_OID,
                empty_regex='^2$',
                keep_serialled_empty=False,
            )
        )

    def test_exos_fru_filter_keeps_serialled_notpresent(self):
        self.assertTrue(
            psu_lld_keeps_installed_fru(
                self._fru_rule(snmp_oid=EXOS_PSU_DISCOVERY_OID, empty_regex='^1$'),
                status_oid=EXOS_PSU_STATUS_OID,
                serial_oid=EXOS_PSU_SERIAL_OID,
                empty_regex='^1$',
            )
        )

    def test_fru_filter_without_serial_default_js_is_not_enough(self):
        """EXOS padding slots omit the serial OID; filter-only LLD errors."""
        self.assertFalse(
            psu_lld_keeps_installed_fru(
                self._fru_rule(
                    snmp_oid=EXOS_PSU_DISCOVERY_OID,
                    empty_regex='^1$',
                    with_js=False,
                ),
                status_oid=EXOS_PSU_STATUS_OID,
                serial_oid=EXOS_PSU_SERIAL_OID,
                empty_regex='^1$',
            )
        )

    def test_lld_js_defaults_missing_serial_and_wipes_dummy(self):
        js = psu_lld_js_default_macros()
        self.assertIn('{#PSU.SERIAL}', js)
        self.assertIn('{#PSU.STATUS}', js)
        self.assertIn("|| ''", js)
        self.assertIn('--', js)
        self.assertTrue(psu_lld_defaults_missing_macros({'preprocessing': [{'type': 21, 'params': js}]}))
        self.assertTrue(psu_lld_js_clears_dummy_serials({'preprocessing': [{'type': 21, 'params': js}]}))
        self.assertFalse(psu_lld_defaults_missing_macros({'preprocessing': [{'type': 21, 'params': 'return value;'}]}))
        self.assertFalse(psu_lld_js_clears_dummy_serials({'preprocessing': [{'type': 21, 'params': "element[field] = element[field] || '';"}]}))

    def test_preprocessing_payload_replaces_serial_default_js(self):
        payload = psu_lld_preprocessing_payload([{'type': 21, 'params': psu_lld_js_default_macros()}])
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['type'], 21)
        self.assertIn('{#PSU.SERIAL}', payload[0]['params'])
        self.assertIn('--', payload[0]['params'])

    def test_api_or_filter_omits_formulaid(self):
        """Zabbix 7 rejects formulaid on AND/OR; GET still canonicalizes to A or B."""
        existing = {
            'evaltype': '2',
            'eval_formula': 'A or B',
            'conditions': [
                {
                    'macro': '{#PSU.STATUS}',
                    'value': '^1$',
                    'operator': '9',
                    'formulaid': 'A',
                },
                {
                    'macro': PSU_SERIAL_MACRO,
                    'value': '.+',
                    'operator': '8',
                    'formulaid': 'B',
                },
                {
                    'macro': '{#SNMPVALUE}',
                    'value': '.+',
                    'operator': '8',
                    'formulaid': 'C',
                },
            ],
        }
        filt = psu_lld_api_filter('^1$', existing)
        self.assertEqual(filt['evaltype'], LLD_EVAL_OR)
        self.assertNotIn('formula', filt)
        self.assertNotIn('eval_formula', filt)
        self.assertEqual(len(filt['conditions']), 3)
        macros = [c['macro'] for c in filt['conditions']]
        self.assertEqual(macros[0], '{#SNMPVALUE}')
        self.assertEqual(macros[1], '{#PSU.STATUS}')
        self.assertEqual(macros[2], PSU_SERIAL_MACRO)
        for c in filt['conditions']:
            self.assertNotIn('formulaid', c)

    def test_api_voss_filter_is_status_only_and(self):
        existing = {
            'evaltype': '2',
            'conditions': [
                {'macro': '{#PSU.STATUS}', 'value': '^2$', 'operator': '9', 'formulaid': 'A'},
                {'macro': PSU_SERIAL_MACRO, 'value': '.+', 'operator': '8', 'formulaid': 'B'},
            ],
        }
        filt = psu_lld_api_filter('^2$', existing, keep_serialled_empty=False)
        self.assertEqual(filt['evaltype'], LLD_EVAL_AND)
        self.assertEqual(len(filt['conditions']), 1)
        self.assertEqual(filt['conditions'][0]['macro'], '{#PSU.STATUS}')
        self.assertNotIn('formulaid', filt['conditions'][0])

    def test_get_canonical_formulaid_is_not_required_to_keep_fru(self):
        rule = self._fru_rule(snmp_oid=EXOS_PSU_DISCOVERY_OID, empty_regex='^1$')
        rule['filter']['eval_formula'] = 'A or B'
        rule['filter']['conditions'][0]['formulaid'] = 'A'
        rule['filter']['conditions'][1]['formulaid'] = 'B'
        self.assertTrue(
            psu_lld_keeps_installed_fru(
                rule,
                status_oid=EXOS_PSU_STATUS_OID,
                serial_oid=EXOS_PSU_SERIAL_OID,
                empty_regex='^1$',
            )
        )

    def test_status_only_skip_empty_without_serial_walk_is_not_enough(self):
        rule = {
            'snmp_oid': (
                'discovery[{#SNMPVALUE},1.3.6.1.4.1.2272.1.4.8.1.1.1,'
                '{#PSU.STATUS},1.3.6.1.4.1.2272.1.4.8.1.1.2]'
            ),
            'filter': {
                'evaltype': 'AND',
                'conditions': [
                    {'macro': '{#PSU.STATUS}', 'value': '^2$', 'operator': 'NOT_MATCHES_REGEX'},
                ],
            },
            'preprocessing': [{'type': 'JAVASCRIPT', 'params': psu_lld_js_default_macros()}],
        }
        self.assertFalse(
            psu_lld_keeps_installed_fru(
                rule,
                status_oid=VOSS_PSU_STATUS_OID,
                serial_oid=VOSS_PSU_SERIAL_OID,
                empty_regex='^2$',
                keep_serialled_empty=False,
            )
        )


if __name__ == '__main__':
    unittest.main()
