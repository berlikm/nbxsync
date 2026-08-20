#!/usr/bin/env python3
"""Stock .diff() must not silence discovered admin-up + oper-down (all switch roles)."""

from __future__ import annotations

import unittest

from extreme_linkdown import (
    linkdown_has_diff_guard,
    linkdown_manual_close_on,
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
    '{$IFCONTROL:"{#IFNAME}"}=1 and last(/Extreme VOSS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}])=2'
)
_WANT_EXOS = (
    '{$IFCONTROL:"{#IFNAME}"}=1 and last(/Extreme EXOS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}])=2'
)


class UngateLinkdownTests(unittest.TestCase):
    def test_strips_voss_stock_diff(self):
        self.assertTrue(linkdown_has_diff_guard(_VOSS))
        self.assertEqual(ungate_linkdown_expr(_VOSS), _WANT_VOSS)
        self.assertFalse(linkdown_has_diff_guard(_WANT_VOSS))

    def test_strips_exos_stock_diff(self):
        self.assertEqual(ungate_linkdown_expr(_EXOS), _WANT_EXOS)
        self.assertFalse(linkdown_has_diff_guard(_WANT_EXOS))

    def test_strips_linkdown_high_gate(self):
        expr = _WANT_VOSS + ' and {$LINKDOWN.HIGH:"{#IFALIAS}"}=1'
        self.assertEqual(ungate_linkdown_expr(expr), _WANT_VOSS)

    def test_yaml_newline_form(self):
        expr = (
            '{$IFCONTROL:"{#IFNAME}"}=1 and last(/Extreme VOSS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}])=2\n'
            '            and (last(/Extreme VOSS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}],#1)'
            '<>last(/Extreme VOSS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}],#2))'
        )
        self.assertEqual(ungate_linkdown_expr(expr).strip(), _WANT_VOSS)

    def test_manual_close_yes(self):
        self.assertTrue(linkdown_manual_close_on({'manual_close': 'YES'}))
        self.assertTrue(linkdown_manual_close_on({'manual_close': 1}))
        self.assertFalse(linkdown_manual_close_on({'manual_close': 0}))
        self.assertFalse(linkdown_manual_close_on({}))


if __name__ == '__main__':
    unittest.main()
