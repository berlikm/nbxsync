#!/usr/bin/env python3
"""Installed PSU not supplying power must Average; empty padding must not."""

from __future__ import annotations

import unittest

from extreme_psu import (
    PSU_SERIAL_MACRO,
    VOSS_PSU_DISCOVERY_OID,
    VOSS_PSU_SERIAL_OID,
    VOSS_PSU_STATUS_OID,
    psu_expr_is_not_up,
    psu_lld_keeps_installed_fru,
    psu_not_up_expr,
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
_VOSS_WANT = (
    'last(/Extreme VOSS by SNMP/sensor.psu.status[rcChasPowerSupplyOperStatus.{#SNMPINDEX}])'
    '<>{$PSU.OK_STATUS}'
)
_EXOS_WANT = (
    'last(/Extreme EXOS by SNMP/sensor.psu.status[extremePowerSupplyStatus.{#SNMPINDEX}])'
    '<>{$PSU.OK_STATUS}'
)
_VOSS_OLD_EMPTY_EXCL = (
    'last(/Extreme VOSS by SNMP/sensor.psu.status[rcChasPowerSupplyOperStatus.{#SNMPINDEX}])'
    '<>{$PSU.OK_STATUS} and last(/Extreme VOSS by SNMP/sensor.psu.status'
    '[rcChasPowerSupplyOperStatus.{#SNMPINDEX}])<>{$PSU.EMPTY_STATUS}'
)


class RewritePsuNotUpTests(unittest.TestCase):
    def test_rewrites_voss_count_eq_down(self):
        got = rewrite_psu_not_up_expr(_VOSS_COUNT)
        self.assertEqual(got, _VOSS_WANT)
        self.assertTrue(psu_expr_is_not_up(got))
        self.assertNotIn('{$PSU_CRIT_STATUS}', got)
        self.assertNotIn('{$PSU.EMPTY_STATUS}', got)

    def test_rewrites_exos_count_eq_present_not_ok(self):
        got = rewrite_psu_not_up_expr(_EXOS_COUNT)
        self.assertEqual(got, _EXOS_WANT)
        self.assertTrue(psu_expr_is_not_up(got))

    def test_strips_empty_exclusion_so_unpowered_empty_tickets(self):
        self.assertFalse(psu_expr_is_not_up(_VOSS_OLD_EMPTY_EXCL))
        self.assertEqual(rewrite_psu_not_up_expr(_VOSS_OLD_EMPTY_EXCL), _VOSS_WANT)

    def test_idempotent(self):
        self.assertEqual(rewrite_psu_not_up_expr(_VOSS_WANT), _VOSS_WANT)

    def test_stock_count_is_not_enough(self):
        self.assertFalse(psu_expr_is_not_up(_VOSS_COUNT))
        self.assertFalse(psu_expr_is_not_up(_EXOS_COUNT))

    def test_helper_builds_same_shape(self):
        path = '/Extreme VOSS by SNMP/sensor.psu.status[rcChasPowerSupplyOperStatus.{#SNMPINDEX}]'
        self.assertEqual(psu_not_up_expr(path), _VOSS_WANT)

    def test_fru_filter_keeps_empty_with_serial(self):
        rule = {
            'snmp_oid': VOSS_PSU_DISCOVERY_OID,
            'filter': {
                'evaltype': 'OR',
                'conditions': [
                    {'macro': '{#PSU.STATUS}', 'value': '^2$', 'operator': 'NOT_MATCHES_REGEX'},
                    {'macro': PSU_SERIAL_MACRO, 'value': '.+', 'operator': 'MATCHES_REGEX'},
                ],
            },
        }
        self.assertTrue(
            psu_lld_keeps_installed_fru(
                rule,
                status_oid=VOSS_PSU_STATUS_OID,
                serial_oid=VOSS_PSU_SERIAL_OID,
                empty_regex='^2$',
            )
        )

    def test_status_only_skip_empty_is_not_enough(self):
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
        }
        self.assertFalse(
            psu_lld_keeps_installed_fru(
                rule,
                status_oid=VOSS_PSU_STATUS_OID,
                serial_oid=VOSS_PSU_SERIAL_OID,
                empty_regex='^2$',
            )
        )


if __name__ == '__main__':
    unittest.main()
