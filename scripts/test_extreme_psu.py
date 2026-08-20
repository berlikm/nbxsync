#!/usr/bin/env python3
"""Installed PSU not supplying power must Average; empty bays must not."""

from __future__ import annotations

import unittest

from extreme_psu import (
    psu_expr_is_not_up,
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
    '<>{$PSU.OK_STATUS} and last(/Extreme VOSS by SNMP/sensor.psu.status'
    '[rcChasPowerSupplyOperStatus.{#SNMPINDEX}])<>{$PSU.EMPTY_STATUS}'
)
_EXOS_WANT = (
    'last(/Extreme EXOS by SNMP/sensor.psu.status[extremePowerSupplyStatus.{#SNMPINDEX}])'
    '<>{$PSU.OK_STATUS} and last(/Extreme EXOS by SNMP/sensor.psu.status'
    '[extremePowerSupplyStatus.{#SNMPINDEX}])<>{$PSU.EMPTY_STATUS}'
)


class RewritePsuNotUpTests(unittest.TestCase):
    def test_rewrites_voss_count_eq_down(self):
        got = rewrite_psu_not_up_expr(_VOSS_COUNT)
        self.assertEqual(got, _VOSS_WANT)
        self.assertTrue(psu_expr_is_not_up(got))
        self.assertNotIn('{$PSU_CRIT_STATUS}', got)

    def test_rewrites_exos_count_eq_present_not_ok(self):
        got = rewrite_psu_not_up_expr(_EXOS_COUNT)
        self.assertEqual(got, _EXOS_WANT)
        self.assertTrue(psu_expr_is_not_up(got))

    def test_idempotent(self):
        self.assertEqual(rewrite_psu_not_up_expr(_VOSS_WANT), _VOSS_WANT)

    def test_stock_count_is_not_enough(self):
        self.assertFalse(psu_expr_is_not_up(_VOSS_COUNT))
        self.assertFalse(psu_expr_is_not_up(_EXOS_COUNT))

    def test_not_up_without_empty_exclusion_is_rejected(self):
        only_ok = (
            'last(/Extreme VOSS by SNMP/sensor.psu.status[rcChasPowerSupplyOperStatus.{#SNMPINDEX}])'
            '<>{$PSU.OK_STATUS}'
        )
        self.assertFalse(psu_expr_is_not_up(only_ok))
        self.assertEqual(rewrite_psu_not_up_expr(only_ok), _VOSS_WANT)

    def test_helper_builds_same_shape(self):
        path = '/Extreme VOSS by SNMP/sensor.psu.status[rcChasPowerSupplyOperStatus.{#SNMPINDEX}]'
        self.assertEqual(psu_not_up_expr(path), _VOSS_WANT)


if __name__ == '__main__':
    unittest.main()
