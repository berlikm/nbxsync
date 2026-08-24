#!/usr/bin/env python3
"""Pure-helper tests for FortiGate Firewall-role macros."""

from __future__ import annotations

import unittest
from pathlib import Path

from fortigate_http import (
    AGENT_MONITORING_CG,
    DEVICE_DUAL_LINK_TEMPLATES,
    FGATE_API_PORT,
    FGATE_FQDN_JINJA,
    FGATE_FQDN_MACRO,
    FGATE_PATH_CONTROL_MACRO,
    FGATE_TOKEN_ENV,
    FGATE_TOKEN_MACRO,
    FIREWALL_DEVICE_MACROS,
    FIREWALL_ROLE,
    FIREWALL_ROLE_FORTI_TEMPLATES,
    FIREWALL_ROLE_MACROS,
    FORTIGATE_HTTP_CG,
    FORTIGATE_HTTP_CLOUD_VENDOR,
    FORTIGATE_HTTP_CLOUD_VENDOR_NAME,
    FORTIGATE_HTTP_CLOUD_VENDOR_VERSION,
    FORTIGATE_HTTP_TEMPLATE,
    FORTIGATE_OBSERVABILITY_TEMPLATE,
    FORTIGATE_SNMP_TEMPLATE,
    FORTIOS_COLLIDING_TEMPLATES,
    FORTIOS_NESTED_PARENT_TEMPLATES,
    FORTIOS_PLATFORM_MACROS,
    FORTIOS_PLATFORM_PATTERN,
    FORTIOS_TEMPLATE_RULE,
    ICMP_PING_TEMPLATE,
    REQUIRED_HTTP_SCRIPT_KEYS,
    SLOW_ITEM_DELAYS,
    SNMP_MONITORING_CG,
    fgate_token_env,
    format_vendor_label,
    forti_linkdown_problem_expr,
    ha_role_gate_expr,
    is_cloud_fortigate_http_vendor,
    netif_error_problem_expr,
    patch_zbx27082_script,
    platform_is_fmg_faz,
    platform_is_fortios,
    preferred_mgmt_ip,
    script_has_zbx27082,
    should_write_secret,
    with_ha_role_gate,
)


class FirewallRoleMacroTests(unittest.TestCase):
    def test_role_is_firewall_not_a_switch(self):
        self.assertEqual(FIREWALL_ROLE, 'Firewall')
        self.assertFalse(FIREWALL_ROLE.startswith('Switch'))

    def test_https_not_stock_http_80(self):
        self.assertEqual(FIREWALL_ROLE_MACROS['{$FGATE.SCHEME}'], 'https')
        self.assertEqual(FGATE_API_PORT, '20443')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$FGATE.API.PORT}'], FGATE_API_PORT)
        self.assertNotEqual(FIREWALL_ROLE_MACROS['{$FGATE.API.PORT}'], '443')
        self.assertNotEqual(FIREWALL_ROLE_MACROS['{$FGATE.API.PORT}'], '80')

    def test_role_macros_are_fleet_defaults_only(self):
        self.assertEqual(
            set(FIREWALL_ROLE_MACROS),
            {
                '{$FGATE.SCHEME}',
                '{$FGATE.API.PORT}',
                '{$NET.IF.IFNAME.MATCHES}',
                '{$NET.IF.IFNAME.NOT_MATCHES}',
                '{$SDWAN.HEALTH.IFNAME.MATCHES}',
                '{$SDWAN.MEMBER.NAME.MATCHES}',
                '{$FWP.FWNAME.MATCHES}',
                '{$NET.IF.UTIL.MAX}',
                '{$FIRMWARE.UPDATES.CONTROL}',
                '{$DISK.FREE.CRIT}',
                '{$CPU.UTIL.CRIT}',
                '{$MEMORY.UTIL.CRIT}',
                '{$FGATE.PATH.CONTROL}',
                '{$NET.IF.DISCOVERY.MIN}',
                '{$FGATE.SDWAN.EXPECTED}',
                '{$FGATE.HA.EXPECTED}',
                FGATE_FQDN_MACRO,
            },
        )
        for macro in FIREWALL_DEVICE_MACROS:
            self.assertNotIn(macro, FIREWALL_ROLE_MACROS)
        self.assertNotIn(FGATE_TOKEN_MACRO, FIREWALL_ROLE_MACROS)
        self.assertEqual(FIREWALL_DEVICE_MACROS, ())
        self.assertEqual(FORTIOS_PLATFORM_MACROS[FGATE_FQDN_MACRO], FGATE_FQDN_JINJA)
        self.assertIn('object.primary_ip4.address.ip', FGATE_FQDN_JINJA)
        self.assertEqual(FGATE_TOKEN_ENV, 'NBX_FGATE_TOKEN')

    def test_ifname_lld_is_open_for_canary(self):
        self.assertEqual(FIREWALL_ROLE_MACROS['{$NET.IF.IFNAME.MATCHES}'], '.*')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$NET.IF.IFNAME.NOT_MATCHES}'], 'CHANGE_IF_NEEDED')

    def test_policy_lld_collects_none(self):
        self.assertEqual(FIREWALL_ROLE_MACROS['{$FWP.FWNAME.MATCHES}'], '^$')

    def test_util_and_firmware_and_disk_high_are_quiet(self):
        self.assertEqual(FIREWALL_ROLE_MACROS['{$NET.IF.UTIL.MAX}'], '101')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$FIRMWARE.UPDATES.CONTROL}'], '0')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$DISK.FREE.CRIT}'], '0')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$CPU.UTIL.CRIT}'], '101')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$MEMORY.UTIL.CRIT}'], '101')

    def test_cutover_names_are_stock_zabbix_and_netbox(self):
        self.assertEqual(FORTIGATE_HTTP_TEMPLATE, 'FortiGate by HTTP')
        self.assertEqual(FORTIGATE_OBSERVABILITY_TEMPLATE, 'FortiGate Observability')
        self.assertEqual(FORTIGATE_SNMP_TEMPLATE, 'FortiGate by SNMP')
        self.assertEqual(ICMP_PING_TEMPLATE, 'ICMP Ping')
        self.assertEqual(SNMP_MONITORING_CG, 'SNMP Monitoring')
        self.assertEqual(FORTIOS_TEMPLATE_RULE, 'FortiOS')
        self.assertEqual(FORTIOS_PLATFORM_PATTERN, r'FORTIOS|FortiOS')
        self.assertNotIn(SNMP_MONITORING_CG, FIREWALL_ROLE_FORTI_TEMPLATES)
        self.assertIn(ICMP_PING_TEMPLATE, FIREWALL_ROLE_FORTI_TEMPLATES)
        self.assertEqual(FGATE_PATH_CONTROL_MACRO, '{$FGATE.PATH.CONTROL}')

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

    def test_fqdn_prefers_primary_ip4(self):
        self.assertEqual(preferred_mgmt_ip('1.2.3.4', '10.1.1.1'), '1.2.3.4')
        self.assertEqual(preferred_mgmt_ip('1.2.3.4', None), '1.2.3.4')
        self.assertEqual(preferred_mgmt_ip(None, '10.1.1.1'), '10.1.1.1')
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
        text = yaml_path.read_text(encoding='utf-8')
        self.assertIn('version: 7.0-3', text)
        self.assertNotEqual(FORTIGATE_HTTP_CLOUD_VENDOR_VERSION, '7.0-3')
        self.assertTrue(script_has_zbx27082(text))
        companion = (
            Path(__file__).resolve().parents[1]
            / 'zabbix/templates/fortinet_fortigate_observability/template_fortigate_observability.yaml'
        ).read_text(encoding='utf-8')
        self.assertIn('FortiGate Observability', companion)
        self.assertIn('FortiGate by HTTP', companion)
        self.assertIn('ICMP Ping', companion)

    def test_platform_scope_is_fortios_not_firewall(self):
        self.assertTrue(platform_is_fortios('FortiOS 7.4'))
        self.assertTrue(platform_is_fortios('FORTIOS'))
        self.assertFalse(platform_is_fortios('FortiManager'))
        self.assertTrue(platform_is_fmg_faz('FortiAnalyzer 7.2'))
        self.assertFalse(platform_is_fortios('FortiAnalyzer 7.2'))

    def test_zbx27082_patch_recreates_httprequest_inside_gethttpdata(self):
        vuln = (
            "var params = JSON.parse(value),\n"
            "\trequest = new HttpRequest(),\n"
            "\tresult = {};\n"
            "\n"
            "function getHttpData(url) {\n"
            "\trequest.addHeader('Authorization: Bearer ' + params.token);\n"
            "\treturn request.get(url);\n"
            "}\n"
        )
        self.assertTrue(script_has_zbx27082(vuln))
        fixed = patch_zbx27082_script(vuln)
        self.assertFalse(script_has_zbx27082(fixed))
        self.assertIn('request = new HttpRequest();', fixed.split('function getHttpData')[1])

    def test_netif_error_expr_covers_outbound(self):
        expr = netif_error_problem_expr()
        self.assertEqual(expr.count('in_errors'), 1)
        self.assertEqual(expr.count('out_errors'), 1)

    def test_sdwan_lld_is_open_and_expected_is_one(self):
        self.assertEqual(FIREWALL_ROLE_MACROS['{$SDWAN.HEALTH.IFNAME.MATCHES}'], '.*')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$SDWAN.MEMBER.NAME.MATCHES}'], '.*')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$FGATE.SDWAN.EXPECTED}'], '1')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$FGATE.HA.EXPECTED}'], '1')
        self.assertEqual(
            FIREWALL_ROLE_MACROS['{$SDWAN.MEMBER.NAME.MATCHES}'],
            FIREWALL_ROLE_MACROS['{$NET.IF.IFNAME.MATCHES}'],
        )

    def test_device_dual_link_is_snmp_only_not_nested_parents(self):
        self.assertEqual(DEVICE_DUAL_LINK_TEMPLATES, (FORTIGATE_SNMP_TEMPLATE,))
        self.assertNotIn(FORTIGATE_HTTP_TEMPLATE, DEVICE_DUAL_LINK_TEMPLATES)
        self.assertNotIn(ICMP_PING_TEMPLATE, DEVICE_DUAL_LINK_TEMPLATES)
        self.assertNotIn(FORTIGATE_OBSERVABILITY_TEMPLATE, DEVICE_DUAL_LINK_TEMPLATES)
        self.assertNotIn(SNMP_MONITORING_CG, DEVICE_DUAL_LINK_TEMPLATES)
        self.assertEqual(
            FORTIOS_NESTED_PARENT_TEMPLATES,
            (FORTIGATE_HTTP_TEMPLATE, ICMP_PING_TEMPLATE),
        )
        self.assertNotIn(FORTIGATE_OBSERVABILITY_TEMPLATE, FORTIOS_NESTED_PARENT_TEMPLATES)
        self.assertNotIn(FORTIGATE_SNMP_TEMPLATE, FORTIOS_NESTED_PARENT_TEMPLATES)
        self.assertEqual(
            FORTIOS_COLLIDING_TEMPLATES,
            FORTIOS_NESTED_PARENT_TEMPLATES + DEVICE_DUAL_LINK_TEMPLATES,
        )

    def test_fortigate_http_cg_beats_agent_monitoring_and_has_no_icmp(self):
        self.assertEqual(FORTIGATE_HTTP_CG, 'FortiGate HTTP')
        self.assertEqual(AGENT_MONITORING_CG, 'Agent Monitoring')
        self.assertNotEqual(FORTIGATE_HTTP_CG, AGENT_MONITORING_CG)
        self.assertNotEqual(FORTIGATE_HTTP_CG, SNMP_MONITORING_CG)
        self.assertNotIn(ICMP_PING_TEMPLATE, (FORTIGATE_HTTP_CG,))

    def test_empty_vendor_is_not_cloud_compatible(self):
        self.assertFalse(is_cloud_fortigate_http_vendor(''))
        self.assertFalse(is_cloud_fortigate_http_vendor('Zabbix, 7.0-3'))

    def test_linkdown_is_sustained_state_gated_on_ha_role(self):
        expr = forti_linkdown_problem_expr(
            'FortiGate by HTTP/fgate.netif.status[{#IFKEY}]',
            '{$NET.IF.CONTROL:"{#IFNAME}"}',
            '0',
        )
        self.assertNotIn('.diff()', expr)
        self.assertNotIn('last(#1)<>last(#2)', expr)
        self.assertIn('max(/FortiGate by HTTP/fgate.netif.status[{#IFKEY}],#3)=0', expr)
        self.assertIn('min(/FortiGate by HTTP/fgate.netif.status[{#IFKEY}],#3)=0', expr)
        self.assertIn('fgate.ha.role', expr)
        self.assertEqual(with_ha_role_gate('x=1'), f'x=1 and {ha_role_gate_expr()}')
        self.assertEqual(with_ha_role_gate('last(/FortiGate by HTTP/fgate.ha.role)=1'), 'last(/FortiGate by HTTP/fgate.ha.role)=1')

    def test_required_scripts_and_slow_delays(self):
        self.assertIn('fgate.netif.get_data', REQUIRED_HTTP_SCRIPT_KEYS)
        self.assertIn('fgate.sdwan.get_data', REQUIRED_HTTP_SCRIPT_KEYS)
        self.assertEqual(SLOW_ITEM_DELAYS['fgate.firmware.get_data'], '12h')
        self.assertEqual(SLOW_ITEM_DELAYS['fgate.service.get_data'], '1h')

    def test_ha_role_script_is_not_zbx27082(self):
        from fortigate_http_zabbix import HA_ROLE_SCRIPT

        self.assertFalse(script_has_zbx27082(HA_ROLE_SCRIPT))
        self.assertIn('new HttpRequest()', HA_ROLE_SCRIPT)
        self.assertIn('/api/v2/monitor/system/ha/checksums', HA_ROLE_SCRIPT)

    def test_companion_yaml_has_census_conserve_and_path(self):
        companion = (
            Path(__file__).resolve().parents[1]
            / 'zabbix/templates/fortinet_fortigate_observability/template_fortigate_observability.yaml'
        ).read_text(encoding='utf-8')
        self.assertIn('zabbix[host,,items_unsupported]', companion)
        self.assertIn('fgate.observability.netif.count', companion)
        self.assertIn('fgate.observability.sdwan.count', companion)
        self.assertIn('fgate.observability.conserve', companion)
        self.assertIn('fgate.observability.ha.member.count', companion)
        self.assertIn('name: Path', companion)
        self.assertIn('request = new HttpRequest();', companion)
        self.assertNotIn('FortiGate by SNMP', companion)
        self.assertIn('{$CPU.UTIL.CRIT}', companion)
        self.assertIn('101', companion)
        self.assertIn("macro: '{$FGATE.API.PORT}'", companion)
        self.assertIn("value: '20443'", companion)
        self.assertNotIn("value: '443'", companion)
        self.assertIn("macro: '{$SDWAN.MEMBER.NAME.MATCHES}'", companion)
        self.assertIn("value: '.*'", companion)
        self.assertIn("macro: '{$FGATE.SDWAN.EXPECTED}'", companion)
        self.assertIn("value: '1'", companion)
        self.assertIn('CHANGE_IF_NEEDED', companion)
        self.assertIn('Object.keys', companion)


if __name__ == '__main__':
    unittest.main()
