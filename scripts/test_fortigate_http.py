#!/usr/bin/env python3
"""Pure-helper tests for FortiGate Firewall-role macros."""

from __future__ import annotations

import unittest

from fortigate_http import (
    FIREWALL_DEVICE_MACROS,
    FIREWALL_ROLE,
    FIREWALL_ROLE_MACROS,
)


class FirewallRoleMacroTests(unittest.TestCase):
    def test_role_is_firewall_not_a_switch(self):
        self.assertEqual(FIREWALL_ROLE, 'Firewall')
        self.assertFalse(FIREWALL_ROLE.startswith('Switch'))

    def test_https_not_stock_http_80(self):
        self.assertEqual(FIREWALL_ROLE_MACROS['{$FGATE.SCHEME}'], 'https')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$FGATE.API.PORT}'], '443')

    def test_role_macros_are_fleet_defaults_only(self):
        self.assertEqual(
            set(FIREWALL_ROLE_MACROS),
            {
                '{$FGATE.SCHEME}',
                '{$FGATE.API.PORT}',
                '{$NET.IF.IFNAME.MATCHES}',
                '{$NET.IF.IFNAME.NOT_MATCHES}',
                '{$FWP.FWNAME.MATCHES}',
                '{$NET.IF.UTIL.MAX}',
                '{$FIRMWARE.UPDATES.CONTROL}',
                '{$DISK.FREE.CRIT}',
            },
        )
        for macro in FIREWALL_DEVICE_MACROS:
            self.assertNotIn(macro, FIREWALL_ROLE_MACROS)

    def test_ifname_is_wan_ha_mgmt_not_port1(self):
        matches = FIREWALL_ROLE_MACROS['{$NET.IF.IFNAME.MATCHES}']
        self.assertEqual(matches, '^(wan|ha|mgmt|dmz)')
        self.assertNotIn('port', matches)

    def test_policy_lld_collects_none(self):
        self.assertEqual(FIREWALL_ROLE_MACROS['{$FWP.FWNAME.MATCHES}'], '^$')

    def test_util_and_firmware_and_disk_high_are_quiet(self):
        self.assertEqual(FIREWALL_ROLE_MACROS['{$NET.IF.UTIL.MAX}'], '101')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$FIRMWARE.UPDATES.CONTROL}'], '0')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$DISK.FREE.CRIT}'], '0')


if __name__ == '__main__':
    unittest.main()
