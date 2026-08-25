#!/usr/bin/env python3
"""Pure-helper tests for FortiGate Firewall-role macros."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

from fortigate_http import (
    AGENT_MONITORING_CG,
    DEVICE_DUAL_LINK_TEMPLATES,
    FGATE_API_PORT,
    FGATE_AUTOMATION_TOKEN_ENV,
    FGATE_FQDN_JINJA,
    FGATE_FQDN_MACRO,
    FGATE_PATH_CONTROL_MACRO,
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
    MEMORY_EXTREME_MACRO,
    MEMORY_GREEN_MACRO,
    MEMORY_RED_MACRO,
    OVERLAY_INVENTORY_KEY,
    RAW_MASTER_HISTORY,
    RAW_MASTER_HISTORY_KEYS,
    REQUIRED_HTTP_SCRIPT_KEYS,
    SLOW_ITEM_DELAYS,
    SNMP_MONITORING_CG,
    VDOM_STAR_SCRIPT_KEYS,
    _helpers_nested_in_gethttp,
    _js_function_span,
    flatten_forti_cmdb_list,
    flatten_forti_monitor_map,
    flatten_forti_sdwan_cmdb,
    fetch_fortigate_api,
    format_vendor_label,
    fortigate_ifname_regex,
    fortigate_memory_thresholds,
    forti_linkdown_problem_expr,
    ha_role_gate_expr,
    is_cloud_fortigate_http_vendor,
    netif_error_problem_expr,
    patch_vdom_star_script,
    patch_zbx27082_script,
    platform_is_fmg_faz,
    platform_is_fortios,
    preferred_mgmt_ip,
    probe_fortigate_api,
    script_has_vdom_star,
    script_has_zbx27082,
    with_ha_role_gate,
)

_COMPANION_YAML = (
    Path(__file__).resolve().parents[1]
    / 'zabbix/templates/fortinet_fortigate_observability/template_fortigate_observability.yaml'
)


def _companion_template() -> dict:
    doc = yaml.safe_load(_COMPANION_YAML.read_text(encoding='utf-8'))
    return doc['zabbix_export']['templates'][0]


def _zabbix_regsub(macro: str, item_name: str) -> str | None:
    match = re.search(r'\.regsub\("(.+)","(.*)"\)}$', macro)
    if not match:
        return None
    found = re.search(match.group(1), item_name)
    if not found:
        return None
    return found.expand(match.group(2))


def _widget_fields(widget: dict) -> dict:
    return {field.get('name'): field.get('value') for field in widget.get('fields') or []}


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
                MEMORY_GREEN_MACRO,
                MEMORY_RED_MACRO,
                MEMORY_EXTREME_MACRO,
                FGATE_FQDN_MACRO,
            },
        )
        for macro in FIREWALL_DEVICE_MACROS:
            self.assertNotIn(macro, FIREWALL_ROLE_MACROS)
        self.assertNotIn(FGATE_TOKEN_MACRO, FIREWALL_ROLE_MACROS)
        self.assertEqual(FIREWALL_DEVICE_MACROS, ())
        self.assertEqual(FORTIOS_PLATFORM_MACROS[FGATE_FQDN_MACRO], FGATE_FQDN_JINJA)
        self.assertIn('object.primary_ip4.address.ip', FGATE_FQDN_JINJA)
        self.assertEqual(FGATE_AUTOMATION_TOKEN_ENV, 'NBX_FORTIGATE_TOKEN')

    def test_ifname_lld_defaults_closed_until_netbox_scope_is_rendered(self):
        self.assertEqual(FIREWALL_ROLE_MACROS['{$NET.IF.IFNAME.MATCHES}'], '^$')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$NET.IF.IFNAME.NOT_MATCHES}'], 'CHANGE_IF_NEEDED')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$NET.IF.DISCOVERY.MIN}'], '0')
        self.assertEqual(
            fortigate_ifname_regex(['port1', 'ssl.root', 'port1', 'x+1']),
            r'^(?:port1|ssl\.root|x\+1)$',
        )
        self.assertEqual(fortigate_ifname_regex([]), '^$')

    def test_sdwan_lld_is_open_and_ha_expected_is_two(self):
        self.assertEqual(FIREWALL_ROLE_MACROS['{$SDWAN.HEALTH.IFNAME.MATCHES}'], '.*')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$SDWAN.MEMBER.NAME.MATCHES}'], '.*')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$FGATE.SDWAN.EXPECTED}'], '1')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$FGATE.HA.EXPECTED}'], '2')
        self.assertNotEqual(
            FIREWALL_ROLE_MACROS['{$SDWAN.MEMBER.NAME.MATCHES}'],
            FIREWALL_ROLE_MACROS['{$NET.IF.IFNAME.MATCHES}'],
        )

    def test_policy_lld_collects_none(self):
        self.assertEqual(FIREWALL_ROLE_MACROS['{$FWP.FWNAME.MATCHES}'], '^$')

    def test_util_and_firmware_and_disk_high_are_quiet(self):
        self.assertEqual(FIREWALL_ROLE_MACROS['{$NET.IF.UTIL.MAX}'], '101')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$FIRMWARE.UPDATES.CONTROL}'], '0')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$DISK.FREE.CRIT}'], '0')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$CPU.UTIL.CRIT}'], '101')
        self.assertEqual(FIREWALL_ROLE_MACROS['{$MEMORY.UTIL.CRIT}'], '101')
        self.assertEqual(FIREWALL_ROLE_MACROS[MEMORY_GREEN_MACRO], '82')
        self.assertEqual(FIREWALL_ROLE_MACROS[MEMORY_RED_MACRO], '88')
        self.assertEqual(FIREWALL_ROLE_MACROS[MEMORY_EXTREME_MACRO], '95')
        self.assertEqual(
            fortigate_memory_thresholds(
                {
                    'results': {
                        'memory-use-threshold-green': 82,
                        'memory-use-threshold-red': 88,
                        'memory-use-threshold-extreme': 95,
                    }
                }
            ),
            {
                MEMORY_GREEN_MACRO: '82',
                MEMORY_RED_MACRO: '88',
                MEMORY_EXTREME_MACRO: '95',
            },
        )
        self.assertIsNone(
            fortigate_memory_thresholds(
                {
                    'results': {
                        'memory-use-threshold-green': 90,
                        'memory-use-threshold-red': 88,
                        'memory-use-threshold-extreme': 95,
                    }
                }
            )
        )

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


    def test_api_probe_requires_endpoint_and_token(self):
        self.assertEqual(probe_fortigate_api('', 'token'), 'missing API FQDN')
        self.assertEqual(probe_fortigate_api('10.0.0.1', ''), 'missing API token')

    def test_api_probe_requires_http_200_json_object(self):
        class Response:
            def __init__(self, status, body):
                self.status = status
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return self.body

        def open_ok(request, **_kwargs):
            self.assertEqual(request.get_header('Authorization'), 'Bearer token')
            return Response(200, b'{"status":"success"}')

        def open_unauthorized(_request, **_kwargs):
            return Response(401, b'')

        def open_bad_json(_request, **_kwargs):
            return Response(200, b'not-json')
        def open_array(_request, **_kwargs):
            return Response(200, b'[{"status":"success","vdom":"root","results":[]}]')


        self.assertIsNone(probe_fortigate_api('10.0.0.1', 'token', opener=open_ok))
        self.assertEqual(
            probe_fortigate_api('10.0.0.1', 'token', opener=open_unauthorized),
            'HTTP 401',
        )
        self.assertEqual(
            probe_fortigate_api('10.0.0.1', 'token', opener=open_bad_json),
            'HTTP 200 with invalid JSON',
        )
        payload, error = fetch_fortigate_api(
            '10.0.0.1',
            'token',
            '/api/v2/cmdb/system/interface?vdom=*',
            opener=open_array,
        )
        self.assertIsNone(error)
        self.assertIsInstance(payload, list)
        self.assertEqual(
            probe_fortigate_api('10.0.0.1', 'token', opener=open_array),
            'HTTP 200 with unexpected JSON payload',
        )

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
        self.assertEqual(VDOM_STAR_SCRIPT_KEYS, ('fgate.netif.get_data', 'fgate.sdwan.get_data'))
        self.assertEqual(SLOW_ITEM_DELAYS['fgate.firmware.get_data'], '12h')
        self.assertEqual(SLOW_ITEM_DELAYS['fgate.service.get_data'], '1h')
        self.assertEqual(OVERLAY_INVENTORY_KEY, 'fgate.observability.inventory')
        self.assertEqual(RAW_MASTER_HISTORY, '1h')
        self.assertEqual(
            RAW_MASTER_HISTORY_KEYS,
            (
                'fgate.netif.get_data',
                'fgate.sdwan.get_data',
                'fgate.system.get_data',
            ),
        )

    def test_ha_role_script_is_not_zbx27082(self):
        from fortigate_http_zabbix import HA_ROLE_SCRIPT

        self.assertFalse(script_has_zbx27082(HA_ROLE_SCRIPT))
        self.assertIn('new HttpRequest()', HA_ROLE_SCRIPT)
        self.assertIn('/api/v2/monitor/system/ha-peer', HA_ROLE_SCRIPT)
        self.assertIn("throw 'HA role collection failed: ' + error", HA_ROLE_SCRIPT)
        self.assertNotIn('} catch (error) {\n\treturn 1;', HA_ROLE_SCRIPT)
        self.assertIn('row.primary', HA_ROLE_SCRIPT)
        self.assertIn('primarySerial === serial ? 1 : 0', HA_ROLE_SCRIPT)
        self.assertNotIn('local HA peer has no role fields', HA_ROLE_SCRIPT)

    def test_companion_yaml_has_authoritative_health_and_path(self):
        companion = (
            Path(__file__).resolve().parents[1]
            / 'zabbix/templates/fortinet_fortigate_observability/template_fortigate_observability.yaml'
        ).read_text(encoding='utf-8')
        self.assertIn('zabbix[host,,items_unsupported]', companion)
        self.assertIn('fgate.observability.netif.count', companion)
        self.assertIn('fgate.observability.sdwan.count', companion)
        self.assertNotIn('fgate.observability.conserve', companion)
        self.assertIn('fgate.observability.ha.member.count', companion)
        self.assertIn('fgate.observability.ha.vdom_mismatches', companion)
        self.assertIn('/api/v2/monitor/system/ha-peer', companion)
        self.assertIn('/api/v2/monitor/system/ha-checksums', companion)
        self.assertNotIn('/api/v2/monitor/system/ha-nonsync-checksums', companion)
        self.assertIn("typeof maps[j][vdom] === 'undefined'", companion)
        self.assertIn('name: Path', companion)
        self.assertIn("name: 'Network interfaces'", companion)
        self.assertIn('- name: Loss', companion)
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
        self.assertIn("value: '0'", companion)
        self.assertIn("macro: '{$FGATE.HA.EXPECTED}'", companion)
        self.assertIn("value: '2'", companion)
        self.assertIn("macro: '{$FGATE.MEMORY.GREEN}'", companion)
        self.assertIn("macro: '{$FGATE.MEMORY.RED}'", companion)
        self.assertIn("macro: '{$FGATE.MEMORY.EXTREME}'", companion)
        self.assertIn('CHANGE_IF_NEEDED', companion)
        self.assertIn('Object.keys', companion)
        self.assertIn('fgate.observability.inventory', companion)
        self.assertNotIn('dependencies:', companion)
        self.assertLess(
            companion.index("name: 'FortiGate: memory pressure is above the configured extreme threshold'"),
            companion.index("name: 'FortiGate: memory pressure is above the configured red threshold'"),
        )
        from fortigate_http_zabbix import OBSERVABILITY_TRIGGER_DEPENDENCIES

        self.assertEqual(len(OBSERVABILITY_TRIGGER_DEPENDENCIES), 10)
        self.assertIn(
            (
                'FortiGate: memory pressure is above the configured red threshold',
                'FortiGate: memory pressure is above the configured extreme threshold',
            ),
            OBSERVABILITY_TRIGGER_DEPENDENCIES,
        )
        self.assertIn(
            (
                'FortiGate: HA VDOM configuration is out of sync',
                'FortiGate: HA member count unexpected',
            ),
            OBSERVABILITY_TRIGGER_DEPENDENCIES,
        )
        self.assertIn(
            'last(/FortiGate Observability/fgate.observability.ha.role)=1',
            companion,
        )
        self.assertIn('fgate.observability.uptime', companion)
        self.assertIn("name: 'HA role'", companion)

    def test_observability_health_matches_exos_overview_chrome(self):
        tpl = _companion_template()
        keys = {item['key'] for item in tpl.get('items') or []}
        self.assertIn('fgate.observability.uptime', keys)
        valuemaps = {row['name'] for row in tpl.get('valuemaps') or []}
        self.assertEqual(valuemaps, {'Service state', 'HA role'})
        ha_item = next(item for item in tpl['items'] if item['key'] == 'fgate.observability.ha.role')
        self.assertEqual((ha_item.get('valuemap') or {}).get('name'), 'HA role')

        dashes = {dash['name']: dash for dash in tpl.get('dashboards') or []}
        self.assertEqual(set(dashes), {'Health', 'Network interfaces', 'Path'})
        health_pages = [page['name'] for page in dashes['Health']['pages']]
        self.assertEqual(health_pages, ['Overview', 'HA'])
        self.assertNotIn('Path', health_pages)
        self.assertNotIn('Diagnostics', health_pages)

        overview = next(page for page in dashes['Health']['pages'] if page['name'] == 'Overview')
        widgets = overview['widgets']
        self.assertFalse(any(True in widget and 'y' not in widget for widget in widgets))

        def _wy(widget):
            if 'y' in widget:
                return str(widget.get('y'))
            if True in widget:
                return str(widget.get(True))
            return '0'

        tiles = [widget for widget in widgets if _wy(widget) == '0']
        self.assertEqual([widget.get('name') for widget in tiles], ['ICMP', 'API', 'CPU', 'Uptime'])
        self.assertEqual([widget.get('type') for widget in tiles], ['gauge', 'gauge', 'gauge', 'item'])
        self.assertTrue(all(str(widget.get('width')) == '18' for widget in tiles))

        problems = [widget for widget in widgets if widget.get('type') == 'problems']
        self.assertEqual(len(problems), 1)
        self.assertEqual((str(problems[0].get('width')), str(problems[0].get('height')), _wy(problems[0])), ('72', '3', '4'))

        histories = [widget for widget in widgets if widget.get('type') == 'svggraph']
        self.assertEqual([widget.get('name') for widget in histories], ['CPU / memory', 'Uptime'])
        self.assertTrue(all(str(widget.get('width')) == '36' and str(widget.get('height')) == '6' and _wy(widget) == '7' for widget in histories))
        history_keys = []
        for widget in histories:
            for field in widget.get('fields') or []:
                value = field.get('value')
                if isinstance(value, dict) and value.get('key'):
                    history_keys.append(value['key'])
        self.assertEqual(history_keys, ['fgate.observability.cpu.util', 'fgate.observability.memory.util', 'fgate.observability.uptime'])

        gauges = [widget for widget in widgets if widget.get('type') == 'gauge']
        for gauge in gauges:
            fields = {field.get('name'): field.get('value') for field in gauge.get('fields') or []}
            shows = {str(field.get('value')) for field in gauge.get('fields') or [] if str(field.get('name')).startswith('show.')}
            self.assertEqual(shows, {'2', '5'}, gauge.get('name'))
            self.assertEqual(str(fields.get('th_show_labels')), '0', gauge.get('name'))
            self.assertEqual(str(fields.get('angle')), '270', gauge.get('name'))
            self.assertEqual(str(fields.get('value_size')), '25', gauge.get('name'))
            self.assertEqual(str(fields.get('value_bold')), '1', gauge.get('name'))

        cpu_fields = {field.get('name'): field.get('value') for field in tiles[2].get('fields') or []}
        self.assertEqual(cpu_fields.get('thresholds.1.threshold'), '80')
        self.assertEqual(cpu_fields.get('thresholds.2.threshold'), '90')

        ha_page = next(page for page in dashes['Health']['pages'] if page['name'] == 'HA')
        ha_names = [widget.get('name') for widget in ha_page['widgets']]
        self.assertEqual(ha_names, ['Memory', 'Memory', 'HA role', 'HA members', 'VDOM mismatches'])
        memory_gauge = next(widget for widget in ha_page['widgets'] if widget.get('type') == 'gauge')
        memory_fields = {field.get('name'): field.get('value') for field in memory_gauge.get('fields') or []}
        self.assertEqual(memory_fields.get('thresholds.1.threshold'), '82')
        self.assertEqual(memory_fields.get('thresholds.2.threshold'), '88')
        self.assertEqual(memory_fields.get('thresholds.3.threshold'), '95')

    def test_observability_path_and_interfaces_are_vdom_maps(self):
        tpl = _companion_template()
        dashes = {dash['name']: dash for dash in tpl.get('dashboards') or []}
        self.assertEqual(
            [page['name'] for page in dashes['Network interfaces']['pages']],
            ['Overview', 'Port'],
        )
        self.assertEqual(
            [page['name'] for page in dashes['Path']['pages']],
            ['Overview', 'Loss', 'Probe'],
        )
        self.assertFalse(
            any(
                widget.get('type') == 'graphprototype'
                for dash in tpl['dashboards']
                for page in dash['pages']
                for widget in page['widgets']
            )
        )

        ni_overview = next(
            page for page in dashes['Network interfaces']['pages'] if page['name'] == 'Overview'
        )
        self.assertEqual([widget.get('type') for widget in ni_overview['widgets']], ['honeycomb'])
        ni_map = ni_overview['widgets'][0]
        self.assertEqual(ni_map.get('name'), 'Interfaces')
        self.assertEqual((str(ni_map.get('width')), str(ni_map.get('height'))), ('72', '6'))
        ni_fields = _widget_fields(ni_map)
        self.assertEqual(ni_fields.get('items.0'), 'Interface *: Link status')
        self.assertEqual(str(ni_fields.get('interpolation')), '0')
        self.assertIsNone(ni_fields.get('show.1'))
        self.assertIn('(?:', str(ni_fields.get('primary_label')))
        self.assertEqual(
            _zabbix_regsub(
                str(ni_fields.get('primary_label')),
                'Interface [root]:[wan1(WAN)]: Link status',
            ),
            'root/wan1',
        )
        self.assertEqual(
            _zabbix_regsub(
                str(ni_fields.get('primary_label')),
                'Interface [Untrust]:[wan2]: Link status',
            ),
            'Untrust/wan2',
        )

        port = next(page for page in dashes['Network interfaces']['pages'] if page['name'] == 'Port')
        nav = next(widget for widget in port['widgets'] if widget.get('type') == 'itemnavigator')
        port_fields = _widget_fields(nav)
        self.assertEqual(port_fields.get('group_by.0.tag_name'), 'interface')
        self.assertEqual(port_fields.get('items.0'), 'Interface *: Link status')
        self.assertEqual(port_fields.get('items.1'), 'Interface *: Speed')
        self.assertEqual(port_fields.get('items.4'), 'Interface *: Bits received')
        self.assertEqual(port_fields.get('items.5'), 'Interface *: Bits sent')

        path_overview = next(page for page in dashes['Path']['pages'] if page['name'] == 'Overview')
        honey = [widget for widget in path_overview['widgets'] if widget.get('type') == 'honeycomb']
        self.assertEqual([widget.get('name') for widget in honey], ['SD-WAN members', 'SD-WAN health'])
        self.assertEqual(
            [widget.get('type') for widget in path_overview['widgets']],
            ['honeycomb', 'honeycomb'],
        )
        self.assertTrue(
            all(str(widget.get('width')) == '36' and str(widget.get('height')) == '6' for widget in honey)
        )
        self.assertNotIn('Interfaces', [widget.get('name') for widget in honey])

        member_fields = _widget_fields(honey[0])
        health_fields = _widget_fields(honey[1])
        self.assertEqual(member_fields.get('items.0'), 'SD-WAN *: Link status')
        self.assertEqual(health_fields.get('items.0'), 'SD-WAN *: Interface status')
        self.assertEqual(str(member_fields.get('interpolation')), '0')
        self.assertEqual(str(health_fields.get('interpolation')), '0')
        self.assertIsNone(member_fields.get('show.1'))
        self.assertIsNone(health_fields.get('show.1'))
        self.assertIn('(?:', str(member_fields.get('primary_label')))
        self.assertIn('(?:', str(health_fields.get('primary_label')))
        self.assertEqual(
            _zabbix_regsub(
                str(member_fields.get('primary_label')),
                'SD-WAN [root]:[virtual-wan-link]:[wan1]: Link status',
            ),
            'root/wan1',
        )
        self.assertEqual(
            _zabbix_regsub(
                str(member_fields.get('primary_label')),
                'SD-WAN [Untrust]:[virtual-wan-link]:[wan2]: Link status',
            ),
            'Untrust/wan2',
        )
        self.assertEqual(
            _zabbix_regsub(
                str(health_fields.get('primary_label')),
                'SD-WAN [root]:[Google]:[wan1]: Interface status',
            ),
            'root/Google/wan1',
        )
        self.assertEqual(
            _zabbix_regsub(
                str(health_fields.get('primary_label')),
                'SD-WAN [Untrust]:[Google]:[wan2]: Interface status',
            ),
            'Untrust/Google/wan2',
        )
        self.assertNotEqual(
            _zabbix_regsub(
                str(health_fields.get('primary_label')),
                'SD-WAN [root]:[Google]:[wan1]: Interface status',
            ),
            _zabbix_regsub(
                str(health_fields.get('primary_label')),
                'SD-WAN [root]:[Google]:[wan2]: Interface status',
            ),
        )

        loss = next(page for page in dashes['Path']['pages'] if page['name'] == 'Loss')
        loss_map = loss['widgets'][0]
        self.assertEqual(loss_map.get('type'), 'honeycomb')
        loss_fields = _widget_fields(loss_map)
        self.assertEqual(loss_fields.get('items.0'), 'SD-WAN *: Packets loss')
        self.assertEqual(str(loss_fields.get('interpolation')), '1')
        self.assertEqual(str(loss_fields.get('show.0')), '1')
        self.assertEqual(str(loss_fields.get('show.1')), '2')
        self.assertEqual(str(loss_fields.get('thresholds.1.threshold')), '5')
        self.assertEqual(str(loss_fields.get('thresholds.2.threshold')), '20')
        self.assertEqual(
            _zabbix_regsub(
                str(loss_fields.get('primary_label')),
                'SD-WAN [root]:[Google]:[wan1]: Packets loss',
            ),
            'root/Google/wan1',
        )
        self.assertEqual(
            _zabbix_regsub(
                str(loss_fields.get('primary_label')),
                'SD-WAN [Untrust]:[Google]:[wan1]: Packets loss',
            ),
            'Untrust/Google/wan1',
        )

        probe = next(page for page in dashes['Path']['pages'] if page['name'] == 'Probe')
        nav = next(widget for widget in probe['widgets'] if widget.get('type') == 'itemnavigator')
        graph = next(widget for widget in probe['widgets'] if widget.get('type') == 'svggraph')
        nav_fields = _widget_fields(nav)
        graph_fields = _widget_fields(graph)
        self.assertEqual(nav_fields.get('group_by.0.tag_name'), 'vdom')
        self.assertEqual(nav_fields.get('items.0'), 'SD-WAN *: Interface status')
        self.assertEqual(nav_fields.get('items.2'), 'SD-WAN *: Packets loss')
        self.assertEqual(nav_fields.get('items.3'), 'SD-WAN *: Latency')
        self.assertEqual(nav_fields.get('items.4'), 'SD-WAN *: Jitter')
        self.assertEqual(nav_fields.get('items.5'), 'SD-WAN *: Bytes received per second')
        self.assertEqual(nav_fields.get('items.6'), 'SD-WAN *: Bytes sent per second')
        self.assertEqual(graph_fields.get('ds.0.itemids.0._reference'), 'FNAVP._itemid')

    def test_observability_dependencies_are_idempotent(self):
        from types import SimpleNamespace
        from fortigate_http_zabbix import (
            OBSERVABILITY_TRIGGER_DEPENDENCIES,
            ensure_observability_trigger_dependencies,
        )

        names = sorted({name for pair in OBSERVABILITY_TRIGGER_DEPENDENCIES for name in pair})

        class TriggerAPI:
            def __init__(self):
                self.rows = [
                    {'triggerid': str(index), 'description': name, 'dependencies': []}
                    for index, name in enumerate(names, start=1)
                ]
                self.updated = []

            def get(self, **kwargs):
                return self.rows

            def update(self, **kwargs):
                self.updated.append(kwargs)

        trigger = TriggerAPI()
        api = SimpleNamespace(trigger=trigger)
        first = ensure_observability_trigger_dependencies(api, '123')
        second = ensure_observability_trigger_dependencies(api, '123')
        self.assertEqual(first, {'created': 10, 'existing': 0})
        self.assertEqual(second, {'created': 0, 'existing': 10})
        self.assertEqual(len(trigger.updated), 10)

    def test_ha_vdom_trigger_is_primary_gated_idempotently(self):
        from types import SimpleNamespace
        from fortigate_http_zabbix import (
            HA_VDOM_PRIMARY_GATE,
            HA_VDOM_TRIGGER,
            ensure_observability_primary_trigger_gates,
        )

        class TriggerAPI:
            def __init__(self):
                self.row = {
                    'triggerid': '42',
                    'description': HA_VDOM_TRIGGER,
                    'expression': 'min(/FortiGate Observability/fgate.observability.ha.vdom_mismatches,15m)>0',
                }
                self.updated = []

            def get(self, **_kwargs):
                return [self.row]

            def update(self, **kwargs):
                self.updated.append(kwargs)
                self.row['expression'] = kwargs['expression']

        trigger = TriggerAPI()
        api = SimpleNamespace(trigger=trigger)
        self.assertEqual(ensure_observability_primary_trigger_gates(api, '123'), 'updated')
        self.assertEqual(ensure_observability_primary_trigger_gates(api, '123'), 'existing')
        self.assertEqual(len(trigger.updated), 1)
        self.assertIn(HA_VDOM_PRIMARY_GATE, trigger.updated[0]['expression'])

    def test_license_patch_preserves_context_macro(self):
        from types import SimpleNamespace
        from fortigate_http_zabbix import patch_wan_state_triggers

        class TriggerPrototypeAPI:
            def __init__(self):
                self.get_kwargs = {}
                self.updated = []

            def get(self, **kwargs):
                self.get_kwargs = kwargs
                return [{
                    'triggerid': '7',
                    'description': 'FortiGate: Service [{#NAME}]: License status is unsuccessful',
                    'expression': (
                        '{$SERVICE.LICENSE.CONTROL:"{#KEY}"}=1 and '
                        'last(/FortiGate by HTTP/fgate.service.license["{#KEY}"])>5'
                    ),
                    'recovery_expression': '',
                    'recovery_mode': '0',
                    'manual_close': '0',
                }]

            def update(self, **kwargs):
                self.updated.append(kwargs)

        triggerprototype = TriggerPrototypeAPI()
        api = SimpleNamespace(triggerprototype=triggerprototype)
        self.assertEqual(
            patch_wan_state_triggers(api, '123'),
            {'patched': 1, 'seen': 1},
        )
        self.assertFalse(triggerprototype.get_kwargs['expandExpression'])
        self.assertIn(
            '{$SERVICE.LICENSE.CONTROL:"{#KEY}"}=1',
            triggerprototype.updated[0]['expression'],
        )
        self.assertNotIn('1=1 and', triggerprototype.updated[0]['expression'])

    def test_vdom_labels_and_tags_are_unambiguous_and_idempotent(self):
        from fortigate_http_zabbix import _with_vdom_label, _with_vdom_tag

        self.assertEqual(
            _with_vdom_label('Interface [{#IFNAME}]: Network traffic'),
            'Interface [{#VDOM}]:[{#IFNAME}]: Network traffic',
        )
        self.assertEqual(
            _with_vdom_label('FortiGate: SD-WAN [{#NAME}]: Link down'),
            'FortiGate: SD-WAN [{#VDOM}]:[{#NAME}]: Link down',
        )
        self.assertEqual(
            _with_vdom_label('SD-WAN [{#VDOM}]:[{#NAME}]: Network traffic'),
            'SD-WAN [{#VDOM}]:[{#NAME}]: Network traffic',
        )
        expected = [
            {'tag': 'component', 'value': 'sd_wan'},
            {'tag': 'vdom', 'value': '{#VDOM}'},
        ]
        self.assertEqual(
            _with_vdom_tag([{'tag': 'component', 'value': 'sd_wan'}]),
            expected,
        )
        self.assertEqual(_with_vdom_tag(expected), expected)
        self.assertEqual(
            _with_vdom_tag(expected + [{'tag': 'vdom', 'value': 'wrong'}]),
            expected,
        )


    def test_dashboard_time_period_patch_is_complete_and_idempotent(self):
        from copy import deepcopy
        from types import SimpleNamespace
        from fortigate_http_zabbix import patch_dashboard_time_periods

        class TemplateDashboardAPI:
            def __init__(self):
                self.rows = [{
                    'dashboardid': '302',
                    'name': 'FortiGate: General',
                    'pages': [{
                        'dashboard_pageid': '10',
                        'name': 'Overview',
                        'display_period': '0',
                        'widgets': [{
                            'widgetid': '20',
                            'type': 'svggraph',
                            'name': 'Disk usage',
                            'x': '0',
                            'y': '8',
                            'width': '36',
                            'height': '5',
                            'view_mode': '0',
                            'fields': [{
                                'type': '1',
                                'name': 'time_period.from',
                                'value': 'now-1d',
                            }],
                        }],
                    }],
                }]
                self.updated = []

            def get(self, **_kwargs):
                return deepcopy(self.rows)

            def update(self, **kwargs):
                self.updated.append(kwargs)
                self.rows[0]['pages'] = deepcopy(kwargs['pages'])

        templatedashboard = TemplateDashboardAPI()
        api = SimpleNamespace(templatedashboard=templatedashboard)
        self.assertEqual(
            patch_dashboard_time_periods(api, '123'),
            {'dashboards': 1, 'widgets': 1},
        )
        fields = templatedashboard.updated[0]['pages'][0]['widgets'][0]['fields']
        self.assertIn(
            {'type': '1', 'name': 'time_period.to', 'value': 'now'},
            fields,
        )
        self.assertEqual(
            patch_dashboard_time_periods(api, '123'),
            {'dashboards': 0, 'widgets': 0},
        )

    def test_reboot_warning_patch_is_idempotent(self):
        from types import SimpleNamespace
        from fortigate_http_zabbix import REBOOT_TRIGGER, patch_reboot_warning

        class TriggerAPI:
            def __init__(self):
                self.row = {
                    'triggerid': '9',
                    'description': REBOOT_TRIGGER,
                    'priority': '1',
                }
                self.updated = []

            def get(self, **_kwargs):
                return [self.row]

            def update(self, **kwargs):
                self.updated.append(kwargs)
                self.row['priority'] = str(kwargs['priority'])

        trigger = TriggerAPI()
        api = SimpleNamespace(trigger=trigger)
        self.assertEqual(patch_reboot_warning(api, '123'), 'updated')
        self.assertEqual(patch_reboot_warning(api, '123'), 'existing')
        self.assertEqual(len(trigger.updated), 1)
        self.assertEqual(trigger.updated[0]['priority'], 2)

        trigger.row = {'triggerid': '9', 'description': 'other', 'priority': '1'}
        with self.assertRaises(SystemExit):
            patch_reboot_warning(api, '123')


    def test_stock_collectors_are_not_vdom_rewrites(self):
        from fortigate_http import script_is_vdom_mutated, stock_http_collector_script

        for key in ('fgate.netif.get_data', 'fgate.sdwan.get_data'):
            stock = stock_http_collector_script(key)
            self.assertFalse(script_has_zbx27082(stock))
            self.assertFalse(script_is_vdom_mutated(stock))
            self.assertIn('function getHttpData', stock)
            self.assertNotIn('fortiFetchVdom', stock)

    def test_overlay_inventory_script_is_standalone(self):
        from fortigate_http_zabbix import OVERLAY_INVENTORY_SCRIPT

        self.assertIn('function overlayRaw', OVERLAY_INVENTORY_SCRIPT)
        self.assertTrue(
            OVERLAY_INVENTORY_SCRIPT.find('function overlayRaw')
            < OVERLAY_INVENTORY_SCRIPT.find('try {')
        )
        self.assertIn('code === 424', OVERLAY_INVENTORY_SCRIPT)
        self.assertIn('/api/v2/monitor/vpn/ipsec', OVERLAY_INVENTORY_SCRIPT)
        self.assertIn('/api/v2/monitor/virtual-wan/members', OVERLAY_INVENTORY_SCRIPT)
        self.assertNotIn('function getHttpData', OVERLAY_INVENTORY_SCRIPT)
        self.assertFalse(script_has_zbx27082(OVERLAY_INVENTORY_SCRIPT))
        self.assertIn('overlayErrors.join', OVERLAY_INVENTORY_SCRIPT)
        self.assertIn('star.code === 401', OVERLAY_INVENTORY_SCRIPT)
        self.assertIn("throw 'overlay census failed: '", OVERLAY_INVENTORY_SCRIPT)


def _http_yaml() -> str:
    return (
        Path(__file__).resolve().parents[1]
        / 'zabbix/templates/fortinet_fortigate_http/template_net_fortigate_http.yaml'
    ).read_text(encoding='utf-8')


def _yaml_script(text: str, key: str) -> str:
    marker = f'          key: {key}\n'
    start = 0
    while True:
        idx = text.find(marker, start)
        if idx < 0:
            raise AssertionError(f'missing YAML script key {key}')
        params = text.find('params: |', idx)
        next_item = text.find('\n          key:', idx + len(marker))
        if params < 0 or (next_item != -1 and params > next_item):
            start = idx + len(marker)
            continue
        end_at = text.find('\n          description:', params)
        if end_at < 0:
            end_at = text.find('\n          timeout:', params)
        block = text[params:end_at]
        lines = block.split('\n')[1:]
        out = []
        for line in lines:
            if line.startswith('            '):
                out.append(line[12:])
            else:
                out.append(line)
        return '\n'.join(out).strip('\n') + '\n'


# Live Cloud scripts after the first vdom=* patch: getHttpData throws on any
# non-200, then walks every VDOM. ZH5 health-check 424 × N VDOMs times out.
_LIVE_THROW_AND_WALK = r'''
function fortiVdomNames(base) {
	if (typeof fortiVdomNames._cache !== 'undefined') {
		return fortiVdomNames._cache;
	}
	var names = [];
	try {
		var payload = getHttpData(base + '/api/v2/cmdb/system/vdom');
		var rows = [];
		if (payload && Array.isArray(payload.results)) {
			rows = payload.results;
		}
		for (var i = 0; i < rows.length; i++) {
			var row = rows[i];
			if (!row) {
				continue;
			}
			var n = row.name || row.q_origin_key;
			if (n) {
				names.push(String(n));
			}
		}
	} catch (e) {
		names = [];
	}
	if (names.length > 16) {
		names = names.slice(0, 16);
	}
	fortiVdomNames._cache = names;
	return names;
}

function fortiFetchVdom(base, path) {
	var sep = path.indexOf('?') >= 0 ? '&' : '?';
	try {
		return getHttpData(base + path + sep + 'vdom=*');
	} catch (e1) {
		var blocks = [];
		var names = fortiVdomNames(base);
		for (var i = 0; i < names.length; i++) {
			try {
				var one = getHttpData(base + path + sep + 'vdom=' + names[i]);
				if (Array.isArray(one)) {
					for (var j = 0; j < one.length; j++) {
						blocks.push(one[j]);
					}
				} else if (one && typeof one === 'object') {
					if (!one.vdom) {
						one.vdom = names[i];
					}
					blocks.push(one);
				}
			} catch (e3) {
				continue;
			}
		}
		if (blocks.length > 0) {
			return blocks;
		}
		try {
			return getHttpData(base + path);
		} catch (e2) {
			return { status: 'error', results: {} };
		}
	}
}
'''


def _drop_js_function(text: str, name: str) -> str:
    span = _js_function_span(text, name)
    if not span:
        return text
    start, end = span
    while end < len(text) and text[end] == '\n':
        end += 1
    return text[:start] + text[end:]


def _as_live_throw_and_walk(script: str) -> str:
    live = script
    for name in (
        'fortiEmpty',
        'fortiHttpRaw',
        'fortiHttpOk',
        'fortiFetchPerVdom',
        'fortiVdomNames',
        'fortiFetchVdom',
    ):
        live = _drop_js_function(live, name)
    span = _js_function_span(live, 'flattenFortiSdwanCmdb')
    if span is None:
        span = _js_function_span(live, 'flattenFortiCmdbList')
    if span is None:
        raise AssertionError('missing flatten helper to reattach live fetch')
    return live[: span[1]] + '\n' + _LIVE_THROW_AND_WALK + live[span[1] :]


class FortiVdomStarTests(unittest.TestCase):
    def test_script_keys_are_netif_and_sdwan(self):
        self.assertEqual(
            VDOM_STAR_SCRIPT_KEYS,
            ('fgate.netif.get_data', 'fgate.sdwan.get_data'),
        )

    def test_single_vdom_cmdb_keeps_root_prefix(self):
        payload = {
            'status': 'success',
            'vdom': 'root',
            'results': [
                {'q_origin_key': 'ha', 'name': 'ha'},
                {'q_origin_key': 'port1', 'name': 'port1'},
            ],
        }
        rows = flatten_forti_cmdb_list(payload)
        self.assertEqual([r['id'] for r in rows], ['root:ha', 'root:port1'])

    def test_multi_vdom_cmdb_does_not_collide_on_port1(self):
        payload = [
            {
                'status': 'success',
                'vdom': 'root',
                'results': [{'q_origin_key': 'port1', 'name': 'port1'}],
            },
            {
                'status': 'success',
                'vdom': 'corp',
                'results': [{'q_origin_key': 'port1', 'name': 'port1'}],
            },
        ]
        rows = flatten_forti_cmdb_list(payload)
        self.assertEqual({r['id'] for r in rows}, {'root:port1', 'corp:port1'})

    def test_cmdb_star_duplicate_blocks_collapse_by_interface_id(self):
        row = {'q_origin_key': 'port1', 'name': 'port1', 'vdom': 'root'}
        payload = [
            {'status': 'success', 'vdom': 'root', 'results': [row]},
            {'status': 'success', 'vdom': 'corp', 'results': [row]},
        ]
        rows = flatten_forti_cmdb_list(payload)
        self.assertEqual([r['id'] for r in rows], ['root:port1'])

    def test_multi_vdom_monitor_map_keys_are_prefixed(self):
        payload = [
            {
                'status': 'success',
                'vdom': 'root',
                'results': {'port1': {'link': True, 'rx_bytes': 1}},
            },
            {
                'status': 'success',
                'vdom': 'corp',
                'results': {'port1': {'link': False, 'rx_bytes': 2}},
            },
        ]
        mapped = flatten_forti_monitor_map(payload)
        self.assertEqual(mapped['root:port1']['rx_bytes'], 1)
        self.assertEqual(mapped['corp:port1']['rx_bytes'], 2)
        self.assertNotIn('port1', mapped)

    def test_failed_vdom_block_is_skipped(self):
        payload = [
            {'status': 'error', 'vdom': 'broken', 'results': {'x': {}}},
            {
                'status': 'success',
                'vdom': 'root',
                'results': [{'q_origin_key': 'ha', 'name': 'ha'}],
            },
        ]
        rows = flatten_forti_cmdb_list(payload)
        self.assertEqual([r['id'] for r in rows], ['root:ha'])

    def test_sdwan_cmdb_prefixes_member_ids(self):
        payload = [
            {
                'status': 'success',
                'vdom': 'root',
                'results': {
                    'members': [{'q_origin_key': 1, 'interface': 'port1'}],
                    'health-check': [
                        {
                            'q_origin_key': 'ISP',
                            'name': 'ISP',
                            'members': [{'q_origin_key': 1}],
                        }
                    ],
                },
            },
            {
                'status': 'success',
                'vdom': 'corp',
                'results': {
                    'members': [{'q_origin_key': 1, 'interface': 'port1'}],
                    'health-check': [],
                },
            },
        ]
        merged = flatten_forti_sdwan_cmdb(payload)
        self.assertEqual(
            [m['q_origin_key'] for m in merged['members']],
            ['root:1', 'corp:1'],
        )
        self.assertEqual(merged['health-check'][0]['q_origin_key'], 'root:ISP')
        self.assertEqual(merged['health-check'][0]['members'][0]['q_origin_key'], 'root:1')

    def test_bundled_netif_script_gets_vdom_star(self):
        raw = _yaml_script(_http_yaml(), 'fgate.netif.get_data')
        self.assertIn('/api/v2/monitor/system/interface', raw)
        self.assertNotIn('vdom=*', raw)
        self.assertTrue(script_has_zbx27082(raw))
        patched = patch_vdom_star_script(patch_zbx27082_script(raw))
        self.assertTrue(script_has_vdom_star(patched))
        self.assertFalse(script_has_zbx27082(patched))
        self.assertIn("fortiFetchVdom(api_url, '/api/v2/monitor/system/interface?include_vlan=true')", patched)
        self.assertIn("fortiFetchVdom(api_url, '/api/v2/cmdb/system/interface')", patched)
        self.assertIn('{"data": [], "error": ""}', patched)
        self.assertIn('(netif_list.results || []).map', patched)
        self.assertIn('flattenFortiCmdbList(netif_list)', patched)
        self.assertIn('item.id = fortiIfaceId(item);', patched)
        self.assertIn('var byId = {};', patched)
        self.assertIn('function fortiHttpRaw', patched)
        self.assertIn('code === 424', patched)
        self.assertEqual(patched.count('function fortiFetchVdom('), 1)
        self.assertFalse(_helpers_nested_in_gethttp(patched))
        gend = _js_function_span(patched, 'getHttpData')[1]
        self.assertGreaterEqual(_js_function_span(patched, 'flattenFortiMonitorMap')[0], gend)
        self.assertGreaterEqual(_js_function_span(patched, 'fortiFetchVdom')[0], gend)
        self.assertEqual(patch_vdom_star_script(patched), patched)

    def test_existing_vdom_patch_upgrades_interface_identity(self):
        raw = _yaml_script(_http_yaml(), 'fgate.netif.get_data')
        patched = patch_vdom_star_script(patch_zbx27082_script(raw))
        legacy = patched.replace(
            'item.id = fortiIfaceId(item);',
            'item.id = item.q_origin_key;',
            1,
        )
        self.assertTrue(script_has_vdom_star(legacy))
        upgraded = patch_vdom_star_script(legacy)
        self.assertIn('item.id = fortiIfaceId(item);', upgraded)
        self.assertNotIn('item.id = item.q_origin_key;', upgraded)
        self.assertEqual(patch_vdom_star_script(upgraded), upgraded)

    def test_netif_vdom_star_500_keeps_data_array(self):
        raw = _yaml_script(_http_yaml(), 'fgate.netif.get_data')
        patched = patch_vdom_star_script(patch_zbx27082_script(raw))
        naive = patched.replace('{"data": [], "error": ""}', '{"data": {}, "error": ""}', 1)
        naive = naive.replace('function fortiHttpRaw', 'function fortiHttpRawMissing', 1)
        self.assertFalse(script_has_vdom_star(naive))
        upgraded = patch_vdom_star_script(naive)
        self.assertTrue(script_has_vdom_star(upgraded))
        self.assertIn('{"data": [], "error": ""}', upgraded)
        self.assertIn('function fortiHttpRaw', upgraded)
        self.assertIn("fortiFetchVdom(api_url, '/api/v2/cmdb/system/interface')", upgraded)

    def test_bundled_sdwan_script_gets_vdom_star(self):
        raw = _yaml_script(_http_yaml(), 'fgate.sdwan.get_data')
        self.assertIn('/api/v2/cmdb/system/sdwan', raw)
        self.assertNotIn('vdom=*', raw)
        patched = patch_vdom_star_script(patch_zbx27082_script(raw))
        self.assertTrue(script_has_vdom_star(patched))
        self.assertFalse(script_has_zbx27082(patched))
        self.assertIn('flattenFortiSdwanCmdb(sdwan_list)', patched)
        self.assertIn("fortiFetchVdom(api_url, '/api/v2/monitor/virtual-wan/members')", patched)
        self.assertIn("fortiFetchVdom(api_url, '/api/v2/cmdb/system/sdwan')", patched)
        self.assertNotIn(
            "api_url + '/api/v2/monitor/virtual-wan/members?vdom=*'",
            patched,
        )
        self.assertIn('"member_lld": []', patched)
        self.assertIn('(sdwan_list.results.members || []).filter', patched)
        self.assertIn('fortiMonitorLookup(sdwan_member_data.results', patched)
        self.assertIn("'vdom': item.vdom", patched)
        self.assertIn('function fortiHttpRaw', patched)
        self.assertIn('code === 424', patched)
        self.assertIn('code === 500', patched)
        self.assertEqual(patched.count('function fortiFetchVdom('), 1)
        self.assertGreaterEqual(patched.count('fortiFetchVdom(api_url'), 3)
        self.assertFalse(_helpers_nested_in_gethttp(patched))
        gend = _js_function_span(patched, 'getHttpData')[1]
        self.assertGreaterEqual(_js_function_span(patched, 'flattenFortiMonitorMap')[0], gend)
        self.assertGreaterEqual(_js_function_span(patched, 'fortiFetchVdom')[0], gend)
        self.assertEqual(patch_vdom_star_script(patched), patched)

    def test_existing_sdwan_patch_adds_health_lld_vdom(self):
        raw = _yaml_script(_http_yaml(), 'fgate.sdwan.get_data')
        patched = patch_vdom_star_script(patch_zbx27082_script(raw))
        legacy = patched.replace("\t\t\t\t'vdom': item.vdom,\n", '', 1)
        self.assertFalse(script_has_vdom_star(legacy))
        upgraded = patch_vdom_star_script(legacy)
        self.assertTrue(script_has_vdom_star(upgraded))
        self.assertIn("'vdom': item.vdom", upgraded)
        self.assertEqual(patch_vdom_star_script(upgraded), upgraded)

    def test_lifts_helpers_nested_inside_gethttpdata(self):
        raw = _yaml_script(_http_yaml(), 'fgate.sdwan.get_data')
        patched = patch_vdom_star_script(patch_zbx27082_script(raw))
        start = _js_function_span(patched, 'isFortiVdomBlock')[0]
        end = _js_function_span(patched, 'fortiFetchVdom')[1]
        helpers = patched[start:end]
        without = patched[:start] + patched[end:]
        gend = _js_function_span(without, 'getHttpData')[1]
        nested = without[: gend - 1] + '\n' + helpers + '\n' + without[gend - 1 :]
        self.assertTrue(_helpers_nested_in_gethttp(nested))
        self.assertFalse(script_has_vdom_star(nested))
        lifted = patch_vdom_star_script(nested)
        self.assertTrue(script_has_vdom_star(lifted))
        self.assertFalse(_helpers_nested_in_gethttp(lifted))
        self.assertGreaterEqual(
            _js_function_span(lifted, 'fortiFetchVdom')[0],
            _js_function_span(lifted, 'getHttpData')[1],
        )
        self.assertEqual(lifted.count('function fortiFetchVdom('), 1)

    def test_sdwan_health_check_424_does_not_walk_vdoms(self):
        raw = _yaml_script(_http_yaml(), 'fgate.sdwan.get_data')
        patched = patch_vdom_star_script(patch_zbx27082_script(raw))
        fetch = patched.split('function fortiFetchVdom')[1].split('function ')[0]
        self.assertIn('code === 424', fetch)
        self.assertIn('fortiEmpty(code)', fetch)
        self.assertIn('code === 500', fetch)
        self.assertTrue(fetch.find('code === 424') < fetch.find('fortiFetchPerVdom'))
        self.assertIn('Do not walk VDOMs', fetch)

    def test_upgrades_live_throw_and_walk_sdwan_script(self):
        raw = _yaml_script(_http_yaml(), 'fgate.sdwan.get_data')
        patched = patch_vdom_star_script(patch_zbx27082_script(raw))
        live = _as_live_throw_and_walk(patched)
        self.assertFalse(script_has_vdom_star(live))
        self.assertIn("getHttpData(base + path + sep + 'vdom=*')", live)
        self.assertEqual(live.count('function fortiFetchVdom('), 1)
        upgraded = patch_vdom_star_script(live)
        self.assertTrue(script_has_vdom_star(upgraded))
        self.assertEqual(upgraded.count('function fortiFetchVdom('), 1)
        self.assertNotIn("getHttpData(base + path + sep + 'vdom=*')", upgraded)
        self.assertIn('function fortiHttpRaw', upgraded)
        self.assertIn('code === 424', upgraded)
        self.assertIn("fortiFetchVdom(api_url, '/api/v2/monitor/virtual-wan/members')", upgraded)
        self.assertIn("fortiFetchVdom(api_url, '/api/v2/monitor/virtual-wan/health-check')", upgraded)
        self.assertIn("fortiFetchVdom(api_url, '/api/v2/cmdb/system/sdwan')", upgraded)
        fetch = upgraded.split('function fortiFetchVdom')[1].split('function ')[0]
        self.assertTrue(fetch.find('code === 424') < fetch.find('fortiFetchPerVdom'))
        self.assertEqual(patch_vdom_star_script(upgraded), upgraded)

    def test_http_424_envelope_is_skipped(self):
        payload = {
            'status': 'error',
            'http_status': 424,
            'vdom': 'root',
            'path': 'virtual-wan',
            'name': 'health-check',
            'results': {},
        }
        self.assertEqual(flatten_forti_monitor_map(payload), {})
        self.assertEqual(
            flatten_forti_sdwan_cmdb(payload),
            {'members': [], 'health-check': []},
        )

    def test_sdwan_vdom_star_500_keeps_member_lld_path(self):
        raw = _yaml_script(_http_yaml(), 'fgate.sdwan.get_data')
        patched = patch_vdom_star_script(patch_zbx27082_script(raw))
        naive = patched.replace(
            '{"data": {"member_lld": [], "health_lld": [], "health_data": []}, "error": ""}',
            '{"data": {}, "error": ""}',
            1,
        )
        naive = naive.replace('function fortiHttpRaw', 'function fortiHttpRawMissing', 1)
        self.assertFalse(script_has_vdom_star(naive))
        upgraded = patch_vdom_star_script(naive)
        self.assertTrue(script_has_vdom_star(upgraded))
        self.assertIn('function fortiHttpRaw', upgraded)
        self.assertIn('"member_lld": []', upgraded)

    def test_monitor_map_accepts_array_results(self):
        payload = {
            'status': 'success',
            'vdom': 'root',
            'results': [{'interface': 'port1', 'link': True}],
        }
        mapped = flatten_forti_monitor_map(payload)
        self.assertEqual(mapped['root:port1']['link'], True)


if __name__ == '__main__':
    unittest.main()
