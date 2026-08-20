#!/usr/bin/env python3
"""Stock .diff() / down(2)-only must not silence discovered admin-up + not-up.

Access still needs a grammar ifAlias (USW|US|UP|MON|UW|TMON) before the Average
can fire. Core/Dist/Mgmt keep template {$LINKDOWN.IFALIAS}=1.
"""

from __future__ import annotations

import re
import unittest

from extreme_linkdown import (
    ACCESS_IFALIAS_MATCHES,
    IFNAME_NOT_MATCHES,
    IFNAME_NOT_MATCHES_MACRO,
    LINKDOWN_IFALIAS_ACCESS_DEFAULT,
    LINKDOWN_IFALIAS_GATE,
    LINKDOWN_IFALIAS_MACRO,
    LINKDOWN_IFALIAS_RECOVERY,
    LINKDOWN_IFALIAS_TEMPLATE_VALUE,
    access_zabbix_host_macros,
    canonicalize_linkdown_problem,
    canonicalize_linkdown_recovery,
    ifname_not_matches_excludes_oob,
    is_platform_linkdown_name,
    linkdown_has_diff_guard,
    linkdown_has_ifalias_gate,
    linkdown_is_not_up,
    linkdown_ifalias_regex_macro,
    linkdown_manual_close_on,
    linkdown_recovery_is_up,
    ungate_linkdown_expr,
    zabbix_regex_macro_name,
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
    f' and {LINKDOWN_IFALIAS_GATE}'
)
_WANT_EXOS = (
    '{$IFCONTROL:"{#IFNAME}"}=1 and last(/Extreme EXOS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}])<>1'
    f' and {LINKDOWN_IFALIAS_GATE}'
)
_REC_VOSS = (
    'last(/Extreme VOSS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}])=1'
    ' or {$IFCONTROL:"{#IFNAME}"}=0'
    f' or {LINKDOWN_IFALIAS_RECOVERY}'
)
_REC_EXOS = (
    'last(/Extreme EXOS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}])=1'
    ' or {$IFCONTROL:"{#IFNAME}"}=0'
    f' or {LINKDOWN_IFALIAS_RECOVERY}'
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
        self.assertTrue(linkdown_is_not_up(_WANT_EXOS))
        self.assertTrue(linkdown_recovery_is_up(_REC_EXOS))

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
        self.assertEqual(canonicalize_linkdown_recovery(_WANT_VOSS), _REC_VOSS)

    def test_eq_down_is_not_enough(self):
        eq2 = (
            '{$IFCONTROL:"{#IFNAME}"}=1 and last(/Extreme VOSS by SNMP/net.if.status'
            '[ifOperStatus.{#SNMPINDEX}])=2'
        )
        self.assertFalse(linkdown_is_not_up(eq2))
        self.assertFalse(linkdown_has_ifalias_gate(eq2))
        self.assertFalse(linkdown_recovery_is_up(
            'last(/Extreme VOSS by SNMP/net.if.status[ifOperStatus.{#SNMPINDEX}])<>2'
            ' or {$IFCONTROL:"{#IFNAME}"}=0'
        ))

    def test_not_up_without_ifalias_gate_is_incomplete(self):
        ungated = (
            '{$IFCONTROL:"{#IFNAME}"}=1 and last(/Extreme VOSS by SNMP/net.if.status'
            '[ifOperStatus.{#SNMPINDEX}])<>1'
        )
        self.assertFalse(linkdown_is_not_up(ungated))

    def test_manual_close_yes(self):
        self.assertTrue(linkdown_manual_close_on({'manual_close': 'YES'}))
        self.assertTrue(linkdown_manual_close_on({'manual_close': 1}))
        self.assertFalse(linkdown_manual_close_on({'manual_close': 0}))
        self.assertFalse(linkdown_manual_close_on({}))

    def test_platform_name_skips_speed_expect_and_usw(self):
        self.assertTrue(is_platform_linkdown_name(
            'Extreme VOSS: Interface {#IFNAME}({#IFALIAS}): Link down'
        ))
        self.assertTrue(is_platform_linkdown_name(
            'Extreme EXOS: Interface {#IFNAME}({#IFALIAS}): Link down'
        ))
        self.assertFalse(is_platform_linkdown_name(
            'Extreme VOSS: Interface {#IFNAME}({#IFALIAS}): Link down (USW)'
        ))
        self.assertFalse(is_platform_linkdown_name(
            'Port identity: Interface {#IFNAME}({#IFALIAS}): Link down (speed-expect)'
        ))

    def test_access_ifalias_regex_keeps_usw_before_us(self):
        self.assertEqual(ACCESS_IFALIAS_MATCHES, '^(USW|US|UP|MON|UW|TMON)(-|$)')
        self.assertLess(ACCESS_IFALIAS_MATCHES.index('USW'), ACCESS_IFALIAS_MATCHES.index('|US|'))
        name = linkdown_ifalias_regex_macro()
        self.assertEqual(
            name,
            zabbix_regex_macro_name(LINKDOWN_IFALIAS_MACRO, ACCESS_IFALIAS_MATCHES),
        )
        self.assertIn('USW|US|UP|MON|UW|TMON', name)

    def test_access_host_macros_deny_unlabelled(self):
        role = {
            '{$NET.IF.IFALIAS.MATCHES}': ACCESS_IFALIAS_MATCHES,
            LINKDOWN_IFALIAS_MACRO: LINKDOWN_IFALIAS_ACCESS_DEFAULT,
        }
        got = access_zabbix_host_macros(role)
        self.assertEqual(got[LINKDOWN_IFALIAS_MACRO], '0')
        self.assertEqual(got[linkdown_ifalias_regex_macro()], '1')
        self.assertEqual(LINKDOWN_IFALIAS_TEMPLATE_VALUE, '1')
        self.assertEqual(got['{$NET.IF.IFALIAS.MATCHES}'], ACCESS_IFALIAS_MATCHES)


class ChassisOobIfnameTests(unittest.TestCase):
    def test_excludes_voss_mgmt_and_exos_management(self):
        self.assertTrue(ifname_not_matches_excludes_oob(IFNAME_NOT_MATCHES))
        self.assertEqual(IFNAME_NOT_MATCHES_MACRO, '{$NET.IF.IFNAME.NOT_MATCHES}')
        self.assertIsNotNone(re.search(IFNAME_NOT_MATCHES, 'mgmt'))
        self.assertIsNotNone(re.search(IFNAME_NOT_MATCHES, 'Management'))
        self.assertIsNotNone(re.search(IFNAME_NOT_MATCHES, 'Mgmt-oob'))

    def test_keeps_data_ports_and_ap_mgmt0(self):
        for name in ('1/1', '1:24', 'mgmt0', 'eth0', 'MgmtPort'):
            self.assertIsNone(re.search(IFNAME_NOT_MATCHES, name), name)

    def test_old_voss_mgmthyphen_only_is_not_enough(self):
        old = (
            '(^Software Loopback Interface|^NULL[0-9.]*$|^[Ll]o[0-9.]*$|^[Ss]ystem$'
            '|^Nu[0-9.]*$|^veth[0-9a-z]+$|docker[0-9]+|br-[a-z0-9]{12}|^Mgmt-)'
        )
        self.assertFalse(ifname_not_matches_excludes_oob(old))
        self.assertIsNone(re.search(old, 'mgmt'))
        self.assertIsNone(re.search(old, 'Management'))


if __name__ == '__main__':
    unittest.main()
