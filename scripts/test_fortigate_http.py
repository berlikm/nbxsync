#!/usr/bin/env python3
"""Pure-helper tests for FortiGate Firewall-role macros."""

from __future__ import annotations

import unittest

from pathlib import Path

from fortigate_http import (
    FGATE_FQDN_MACRO,
    FGATE_TOKEN_ENV,
    FGATE_TOKEN_MACRO,
    FIREWALL_DEVICE_MACROS,
    FIREWALL_ROLE,
    FIREWALL_ROLE_MACROS,
    FORTIGATE_HTTP_CLOUD_VENDOR,
    FORTIGATE_HTTP_CLOUD_VENDOR_NAME,
    FORTIGATE_HTTP_CLOUD_VENDOR_VERSION,
    FORTIGATE_HTTP_TEMPLATE,
    FORTIGATE_SNMP_TEMPLATE,
    FORTIOS_PLATFORM_PATTERN,
    FORTIOS_TEMPLATE_RULE,
    ICMP_PING_TEMPLATE,
    SNMP_MONITORING_CG,
    fgate_token_env,
    format_vendor_label,
    is_cloud_fortigate_http_vendor,
    preferred_mgmt_ip,
    should_write_secret,
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
        self.assertNotIn(FGATE_TOKEN_MACRO, FIREWALL_ROLE_MACROS)
        self.assertEqual(FIREWALL_DEVICE_MACROS, (FGATE_FQDN_MACRO,))
        self.assertEqual(FGATE_TOKEN_ENV, 'NBX_FGATE_TOKEN')

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

    def test_cutover_names_are_stock_zabbix_and_netbox(self):
        self.assertEqual(FORTIGATE_HTTP_TEMPLATE, 'FortiGate by HTTP')
        self.assertEqual(FORTIGATE_SNMP_TEMPLATE, 'FortiGate by SNMP')
        self.assertEqual(ICMP_PING_TEMPLATE, 'ICMP Ping')
        self.assertEqual(SNMP_MONITORING_CG, 'SNMP Monitoring')
        self.assertEqual(FORTIOS_TEMPLATE_RULE, 'FortiOS')
        self.assertEqual(FORTIOS_PLATFORM_PATTERN, r'FORTIOS|FortiOS')

    def test_token_env_uppercases_and_underscores_dashes(self):
        self.assertEqual(
            fgate_token_env('ch-zrh-p-fw01'),
            'NBX_FGATE_TOKEN_CH_ZRH_P_FW01',
        )

    def test_empty_env_must_not_wipe_token(self):
        self.assertFalse(should_write_secret(None))
        self.assertFalse(should_write_secret(''))
        self.assertFalse(should_write_secret('   '))
        self.assertTrue(should_write_secret('abc'))

    def test_fqdn_prefers_oob_over_primary(self):
        self.assertEqual(preferred_mgmt_ip('10.1.1.1', '1.2.3.4'), '10.1.1.1')
        self.assertEqual(preferred_mgmt_ip(None, '1.2.3.4'), '1.2.3.4')
        self.assertIsNone(preferred_mgmt_ip(None, None))

    def test_cloud_vendor_is_zabbix_7_0_2(self):
        self.assertEqual(FORTIGATE_HTTP_CLOUD_VENDOR_NAME, 'Zabbix')
        self.assertEqual(FORTIGATE_HTTP_CLOUD_VENDOR_VERSION, '7.0-2')
        self.assertEqual(FORTIGATE_HTTP_CLOUD_VENDOR, 'Zabbix, 7.0-2')
        self.assertTrue(is_cloud_fortigate_http_vendor('Zabbix, 7.0-2'))
        self.assertFalse(is_cloud_fortigate_http_vendor('Zabbix, 7.0-3'))
        self.assertFalse(is_cloud_fortigate_http_vendor(''))
        self.assertEqual(format_vendor_label('Zabbix', '7.0-2'), 'Zabbix, 7.0-2')
        self.assertEqual(format_vendor_label(None, None), '')

    def test_bundled_yaml_is_7_0_3_not_cloud(self):
        yaml_path = (
            Path(__file__).resolve().parents[1]
            / 'zabbix/templates/fortinet_fortigate_http/template_net_fortigate_http.yaml'
        )
        text = yaml_path.read_text()
        self.assertIn('version: 7.0-3', text)
        self.assertNotEqual(FORTIGATE_HTTP_CLOUD_VENDOR_VERSION, '7.0-3')


if __name__ == '__main__':
    unittest.main()
