#!/usr/bin/env python3
"""Stock .diff() / down(2)-only must not silence discovered admin-up + not-up."""

from __future__ import annotations

import unittest

from extreme_linkdown import (
    canonicalize_linkdown_problem,
    canonicalize_linkdown_recovery,
    is_platform_linkdown_name,
    linkdown_has_diff_guard,
    linkdown_is_not_up,
    linkdown_manual_close_on,
    linkdown_recovery_is_up,
    ungate_linkdown_expr,
)


_VOSS = (
    '{$IFCONTROL:"{#IFNAME}"}=1 and last(/Extreme VOSS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}])=2'
    ' and (last(/Extreme VOSS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}],#1)'
    '<>last(/Extreme VOSS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}],#2))'
)
_EXOS = (
    '{$IFCONTROL:"{#IFNAME}"}=1 and last(/Extreme EXOS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}])=2'
    ' and (last(/Extreme EXOS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}],#1)'
    '<>last(/Extreme EXOS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}],#2))'
)
_WANT_VOSS = (
    '{$IFCONTROL:"{#IFNAME}"}=1 and last(/Extreme VOSS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}])<>1'
)
_WANT_EXOS = (
    '{$IFCONTROL:"{#IFNAME}"}=1 and last(/Extreme EXOS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}])<>1'
)
_REC_VOSS = (
    'last(/Extreme VOSS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}])=1'
    ' or {$IFCONTROL:"{#IFNAME}"}=0'
)
_REC_EXOS = (
    'last(/Extreme EXOS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}])=1'
    ' or {$IFCONTROL:"{#IFNAME}"}=0'
)


class UngateLinkdownTests(unittest.TestCase):
    def test_strips_voss_stock_diff(self):
        self.assertTrue(linkdown_has_diff_guard(_VOSS))
        self.assertFalse(linkdown_has_diff_guard(ungate_linkdown_expr(_VOSS)))

    def test_canonical_voss_is_not_up(self):
        got = canonicalize_linkdown_problem(_VOSS)
        self.assertEqual(got, _WANT_VOSS)
        self.assertTrue(linkdown_is_not_up(got))
        self.assertEqual(canonicalize_linkdown_recovery(got), _REC_VOSS)
        self.assertTrue(linkdown_recovery_is_up(_REC_VOSS))

    def test_canonical_exos_is_not_up(self):
        self.assertEqual(canonicalize_linkdown_problem(_EXOS), _WANT_EXOS)
        self.assertEqual(canonicalize_linkdown_recovery(_WANT_EXOS), _REC_EXOS)

    def test_strips_linkdown_high_gate(self):
        expr = (
            '{$IFCONTROL:"{#IFNAME}"}=1 and last(/Extreme VOSS by SNMP/net.if.status'
            '[ifOperStatus.{#SNMPINDEX}])=2 and {$LINKDOWN.HIGH:"{#IFALIAS}"}=1'
        )
        self.assertEqual(canonicalize_linkdown_problem(expr), _WANT_VOSS)

    def test_yaml_newline_form(self):
        expr = (
            '{$IFCONTROL:"{#IFNAME}"}=1 and last(/Extreme VOSS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}])=2\n'
            '            and (last(/Extreme VOSS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}],#1)'
            '<>last(/Extreme VOSS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}],#2))'
        )
        self.assertEqual(canonicalize_linkdown_problem(expr), _WANT_VOSS)

    def test_already_not_up_is_idempotent(self):
        self.assertEqual(canonicalize_linkdown_problem(_WANT_VOSS), _WANT_VOSS)

    def test_eq_down_is_not_enough(self):
        eq2 = (
            '{$IFCONTROL:"{#IFNAME}"}=1 and last(/Extreme VOSS by SNMP/net.if.status'
            '[ifOperStatus.{#SNMPINDEX}])=2'
        )
        self.assertFalse(linkdown_is_not_up(eq2))
        self.assertFalse(linkdown_recovery_is_up(
            'last(/Extreme VOSS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}])<>2'
            ' or {$IFCONTROL:"{#IFNAME}"}=0'
        ))

    def test_manual_close_yes(self):
        self.assertTrue(linkdown_manual_close_on({'manual_close': 'YES'}))
        self.assertTrue(linkdown_manual_close_on({'manual_close': 1}))
        self.assertFalse(linkdown_manual_close_on({'manual_close': 0}))
        self.assertFalse(linkdown_manual_close_on({}))

    def test_platform_name_skips_speed_expect_and_usw(self):
        self.assertTrue(is_platform_linkdown_name(
            'Extreme VOSS: Interface {#IFNAME}({#IFALIAS}): Link down'
        ))
        self.assertFalse(is_platform_linkdown_name(
            'Extreme VOSS: Interface {#IFNAME}({#IFALIAS}): Link down (USW)'
        ))
        self.assertFalse(is_platform_linkdown_name(
            'Port identity: Interface {#IFNAME}({#IFALIAS}): Link down (speed-expect)'
        ))


if __name__ == '__main__':
    unittest.main()
