#!/usr/bin/env python3
"""VOSS fabric pairs, MLT persistence, optional LLD, reboot authority."""

from __future__ import annotations

import unittest

from extreme_fabric import (
    fabric_pair_hostnames,
    fabric_pair_macros,
    isis_down_expr,
    isis_expr_is_expected_loss,
    lld_allowlists_unsupported,
    mlt_down_expr,
    mlt_expr_is_persistent_down,
    reboot_expr,
    reboot_expr_uses_engine_boots,
    vist_down_expr,
    vist_expr_is_loss,
)


class FabricPairTests(unittest.TestCase):
    def test_voss_core_twins(self):
        devices = [
            ('CH-NKN-G08-L02-CORE01-1', 'VOSS', 'Switch Core'),
            ('CH-NKN-G08-L02-CORE01-2', 'Fabric Engine', 'Switch Core'),
            ('CH-STA-L26-L02-MGMT03', 'VOSS', 'Switch Mgmt'),
            ('CH-NKN-G08-L02-CORE01-1', 'EXOS', 'Switch Core'),
        ]
        # The EXOS duplicate name would be a second row; use distinct EXOS stack.
        devices[-1] = ('CH-NKN-G08-L02-ACCE01-1', 'EXOS', 'Switch Core')
        self.assertEqual(
            fabric_pair_hostnames(devices),
            ['CH-NKN-G08-L02-CORE01-1', 'CH-NKN-G08-L02-CORE01-2'],
        )

    def test_exos_stack_ignored(self):
        devices = [
            ('CH-NKN-G08-L02-CORE01-1', 'Switch Engine', 'Switch Core'),
            ('CH-NKN-G08-L02-CORE01-2', 'EXOS', 'Switch Core'),
        ]
        self.assertEqual(fabric_pair_hostnames(devices), [])

    def test_single_member_ignored(self):
        devices = [('CN-SHA-JIU-L03-CORE03-1', 'VOSS', 'Switch Core')]
        self.assertEqual(fabric_pair_hostnames(devices), [])

    def test_pair_macros_do_not_arm_cards(self):
        macros = fabric_pair_macros()
        self.assertEqual(macros['{$VIST.CONTROL}'], '1')
        self.assertEqual(macros['{$ISIS.CONTROL}'], '1')
        self.assertEqual(macros['{$ISIS.EXPECTED}'], '1')
        self.assertNotIn('{$CARD.CONTROL}', macros)

    def test_cutover_silence_disarms_pairs(self):
        macros = fabric_pair_macros(silence=True)
        self.assertEqual(macros['{$VIST.CONTROL}'], '0')
        self.assertEqual(macros['{$ISIS.CONTROL}'], '0')
        self.assertEqual(macros['{$ISIS.EXPECTED}'], '0')
        self.assertNotIn('{$CARD.CONTROL}', macros)


class TriggerShapeTests(unittest.TestCase):
    def test_mlt_not_diff(self):
        expr = mlt_down_expr()
        self.assertTrue(mlt_expr_is_persistent_down(expr))
        self.assertNotIn('diff', expr.lower())
        self.assertIn('#3', expr)
        self.assertIn('#15', expr)

    def test_legacy_mlt_diff_rejected(self):
        legacy = (
            '{$MLT.CONTROL}=1 and last(/Extreme VOSS by SNMP/net.mlt.agg.state'
            '[rcMltAggOperState.{#SNMPINDEX}])={$MLT.AGG.DOWN_STATUS} and '
            '(last(/Extreme VOSS by SNMP/net.mlt.agg.state[rcMltAggOperState.{#SNMPINDEX}],#1)'
            '<>last(/Extreme VOSS by SNMP/net.mlt.agg.state[rcMltAggOperState.{#SNMPINDEX}],#2))'
        )
        self.assertFalse(mlt_expr_is_persistent_down(legacy))

    def test_vist_loss_not_never_down(self):
        self.assertTrue(vist_expr_is_loss(vist_down_expr()))

    def test_isis_expected_and_was_up(self):
        expr = isis_down_expr()
        self.assertTrue(isis_expr_is_expected_loss(expr))
        self.assertIn('{$ISIS.EXPECTED:"{#SNMPINDEX}"}=1', expr)

    def test_reboot_uses_engine_boots(self):
        expr = reboot_expr()
        self.assertTrue(reboot_expr_uses_engine_boots(expr))
        self.assertIn('snmpEngineBoots', expr)
        self.assertIn('{$UPTIME.WRAP.MAX}', expr)


class OptionalLldTests(unittest.TestCase):
    def test_empty_json_allowlist(self):
        rule = {
            'preprocessing': [
                {
                    'type': 'CHECK_NOT_SUPPORTED',
                    'parameters': ['-1'],
                    'error_handler': 'CUSTOM_VALUE',
                    'error_handler_params': '[]',
                }
            ]
        }
        self.assertTrue(lld_allowlists_unsupported(rule))

    def test_missing_allowlist(self):
        self.assertFalse(lld_allowlists_unsupported({'preprocessing': []}))


if __name__ == '__main__':
    unittest.main()
