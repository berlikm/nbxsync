#!/usr/bin/env python3
"""Contract tests for XIQ-SE / ExtremeControl Observability (no live NBI)."""

from __future__ import annotations

import json
import re
import time
import unittest

import yaml

from xiqse_observability import (
    APPLY_FLAG,
    CHECK_FLAG,
    DASHBOARD_NAMES,
    FIXTURES,
    FORBIDDEN_SNIPPETS,
    JS_DIR,
    NAC_ITEM_KEYS,
    NAC_PORTAL_FQDN_MACRO,
    NAC_ROLE,
    NAC_TEMPLATE_NAME,
    NAC_TRIGGER_NAMES,
    NAC_YAML,
    SE_DISCOVERY_KEYS,
    SE_ITEM_KEYS,
    SE_ITEM_PROTOTYPE_KEYS,
    SE_PLATFORM_PATTERN,
    SE_TEMPLATE_NAME,
    SE_TEMPLATE_RULE,
    SE_TRIGGER_NAMES,
    SE_TRIGGER_PROTOTYPE_NAMES,
    SE_YAML,
    TEMPLATE_FILES,
    XIQSE_FQDN_JINJA,
    XIQSE_FQDN_MACRO,
    extract_engine_script,
    health_script,
    licenses_script,
    lld_script,
    load_fixture,
    network_source,
    pilot_script,
    platform_is_xiqse,
    run_lld,
    run_metrics_json,
    zerotouch_source,
)
from xiqse_observability_template import render_nac, render_se, write_yaml


UUID_RE = re.compile(r'^[0-9a-f]{32}$')
UUID4_RE = re.compile(r'^[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$')


def _walk_names(node, keys: tuple[str, ...], found: set[str] | None = None) -> set[str]:
    found = found if found is not None else set()
    if isinstance(node, dict):
        for key in keys:
            for row in node.get(key) or []:
                if isinstance(row, dict) and row.get('name'):
                    found.add(row['name'])
        for value in node.values():
            _walk_names(value, keys, found)
    elif isinstance(node, list):
        for value in node:
            _walk_names(value, keys, found)
    return found


def _walk_item_keys(node, found: set[str] | None = None) -> set[str]:
    found = found if found is not None else set()
    if isinstance(node, dict):
        if 'key' in node and 'type' in node:
            found.add(node['key'])
        for value in node.values():
            _walk_item_keys(value, found)
    elif isinstance(node, list):
        for value in node:
            _walk_item_keys(value, found)
    return found


def _fresh_endsystems() -> list[dict]:
    now = int(time.time() * 1000)
    rows = json.loads((FIXTURES / 'endsystems.json').read_text(encoding='utf-8'))
    for row in rows:
        if row.get('username') != 'stale':
            row['lastAuthEventTime'] = now
    return rows


class LicenseWindowTests(unittest.TestCase):
    def test_same_mac_on_two_engines_is_one_seat(self):
        counted = run_metrics_json(
            'countLicenseWindow(rows, Date.now(), 86400000)',
            prelude=f'var rows = {json.dumps(_fresh_endsystems())};',
        )
        self.assertEqual(counted['nacUsed24h'], 2)
        self.assertEqual(counted['users24h'], 1)
        self.assertEqual(counted['engines']['10.0.50.11']['used24h'], 2)
        self.assertEqual(counted['engines']['10.0.50.12']['used24h'], 1)

    def test_stale_auth_is_not_a_license_seat(self):
        counted = run_metrics_json(
            'countLicenseWindow(rows, Date.now(), 86400000)',
            prelude=f'var rows = {json.dumps(_fresh_endsystems())};',
        )
        self.assertNotIn('stale', json.dumps(counted))
        self.assertEqual(counted['nacUsed24h'], 2)

    def test_usernames_are_not_the_license(self):
        counted = run_metrics_json(
            'countLicenseWindow(rows, Date.now(), 86400000)',
            prelude=f'var rows = {json.dumps(_fresh_endsystems())};',
        )
        self.assertNotEqual(counted['nacUsed24h'], counted['users24h'])
        self.assertEqual(counted['users24h'], 1)

    def test_epoch_seconds_are_promoted_to_ms(self):
        now_s = int(time.time())
        rows = [{'macAddress': 'aa:aa:aa:aa:aa:aa', 'lastAuthEventTime': now_s, 'username': 'bob', 'nacApplianceIP': '10.0.0.1'}]
        counted = run_metrics_json(
            'countLicenseWindow(rows, Date.now(), 86400000)',
            prelude=f'var rows = {json.dumps(rows)};',
        )
        self.assertEqual(counted['nacUsed24h'], 1)


class EngineLldTests(unittest.TestCase):
    def test_health_fixture_discovers_both_engines(self):
        health = load_fixture('health.json')
        rows = run_lld(health)
        self.assertEqual(
            rows,
            [
                {'{#ENGINE.IP}': '10.0.50.11', '{#ENGINE.NAME}': 'NAC-SITE-A', '{#ENGINE.CAPACITY}': '3000'},
                {'{#ENGINE.IP}': '10.0.50.12', '{#ENGINE.NAME}': 'NAC-SITE-B', '{#ENGINE.CAPACITY}': '3000'},
            ],
        )

    def test_disconnected_and_freeradius_fields(self):
        health = load_fixture('health.json')
        self.assertEqual(
            run_metrics_json(
                "pickEngineField(payload, '10.0.50.12', 'connected', 2)",
                prelude=f'var payload = {json.dumps(health)};',
            ),
            0,
        )
        self.assertEqual(
            run_metrics_json(
                "pickEngineField(payload, '10.0.50.12', 'freeRadiusEnabled', 2)",
                prelude=f'var payload = {json.dumps(health)};',
            ),
            0,
        )
        self.assertEqual(
            run_metrics_json(
                "pickEngineField(payload, '10.0.50.11', 'connected', 2)",
                prelude=f'var payload = {json.dumps(health)};',
            ),
            1,
        )

    def test_pilot_counts_xiq_pilot_only(self):
        devices = [
            {'deviceData': {'xiqLicenseState': 'XIQ_PILOT'}},
            {'deviceData': {'xiqLicenseState': 'XIQ_NAVIGATOR'}},
            {'deviceData': {'xiqLicenseState': 'XIQ_PILOT'}},
            {},
        ]
        self.assertEqual(
            run_metrics_json('countPilot(devices)', prelude=f'var devices = {json.dumps(devices)};'),
            2,
        )

    def test_device_license_census_splits_pilot_navigator_and_platform_one(self):
        devices = [
            {'deviceData': {'xiqLicenseState': 'XIQ_PILOT'}},
            {'deviceData': {'xiqLicenseState': 'XIQ_NAVIGATOR'}},
            {'deviceData': {'xiqLicenseState': 'XIQ_NAVIGATOR'}},
            {'deviceData': {'xiqLicenseState': 'XIQ_PENDING'}},
            {'deviceData': {'xiqLicenseState': 'XIQ_UNMANAGED'}},
            {'deviceData': {'xiqLicenseState': 'XIQ_ADVANCED_TIER_A'}},
            {'deviceData': {'xiqLicenseState': 'XIQ_STANDARD_TIER_C'}},
            {'deviceData': {'xiqLicenseState': 'XIQ_TRIAL'}},
            {},
        ]
        counted = run_metrics_json(
            'countDeviceLicenses(devices)',
            prelude=f'var devices = {json.dumps(devices)};',
        )
        self.assertEqual(counted['pilotUsed'], 1)
        self.assertEqual(counted['navigatorUsed'], 2)
        self.assertEqual(counted['pending'], 1)
        self.assertEqual(counted['unmanaged'], 1)
        self.assertEqual(counted['platformOne'], 2)
        self.assertEqual(counted['other'], 1)


class YamlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        write_yaml()
        cls.se_text = SE_YAML.read_text(encoding='utf-8')
        cls.nac_text = NAC_YAML.read_text(encoding='utf-8')
        cls.se_doc = yaml.safe_load(cls.se_text)
        cls.nac_doc = yaml.safe_load(cls.nac_text)
        cls.se = cls.se_doc['zabbix_export']['templates'][0]
        cls.nac = cls.nac_doc['zabbix_export']['templates'][0]

    def test_committed_yaml_matches_renderer(self):
        self.assertEqual(self.se_text, render_se())
        self.assertEqual(self.nac_text, render_nac())

    def test_export_version_and_single_template(self):
        self.assertEqual(self.se_doc['zabbix_export']['version'], '7.0')
        self.assertEqual(self.nac_doc['zabbix_export']['version'], '7.0')
        self.assertEqual(len(self.se_doc['zabbix_export']['templates']), 1)
        self.assertEqual(len(self.nac_doc['zabbix_export']['templates']), 1)
        self.assertEqual(self.se['template'], SE_TEMPLATE_NAME)
        self.assertEqual(self.nac['template'], NAC_TEMPLATE_NAME)

    def test_uuids_are_32_hex(self):
        blob = self.se_text + '\n' + self.nac_text
        uuids = re.findall(r'uuid: ([0-9a-f]+)', blob)
        self.assertTrue(uuids)
        for value in uuids:
            self.assertRegex(value, UUID_RE)

    def test_nac_census_uuids_are_v4(self):
        items = {item['key']: item for item in self.se['items']}
        self.assertRegex(items['xiqse.nac.error']['uuid'], UUID4_RE)
        nac_ok_trigger = next(trigger for trigger in items['xiqse.nac.ok']['triggers'] if trigger['name'] == 'XIQ-SE: NAC census failed')
        self.assertRegex(nac_ok_trigger['uuid'], UUID4_RE)

    def test_se_item_and_prototype_keys(self):
        keys = _walk_item_keys(self.se)
        self.assertTrue(SE_ITEM_KEYS <= keys)
        self.assertTrue(SE_ITEM_PROTOTYPE_KEYS <= keys)
        self.assertTrue(SE_DISCOVERY_KEYS <= {rule['key'] for rule in self.se['discovery_rules']})

    def test_trigger_names(self):
        names = _walk_names(self.se, ('triggers', 'trigger_prototypes'))
        self.assertTrue(SE_TRIGGER_NAMES <= names)
        self.assertTrue(SE_TRIGGER_PROTOTYPE_NAMES <= names)
        nac_names = _walk_names(self.nac, ('triggers', 'trigger_prototypes'))
        self.assertTrue(NAC_TRIGGER_NAMES <= nac_names)

    def test_forbidden_snippets_stay_out(self):
        blob = self.se_text + '\n' + self.nac_text
        for snippet in FORBIDDEN_SNIPPETS:
            self.assertNotIn(snippet, blob, snippet)

    def test_templates_stay_agentless(self):
        self.assertNotIn('web.certificate.get[', self.se_text + self.nac_text)

    def test_calculated_item_formulas_avoid_unsupported_ternaries(self):
        for item in self.se['items']:
            if item['type'] == 'CALCULATED':
                self.assertNotIn('?', item['params'], item['key'])

    def test_scripts_are_embedded_from_js_files(self):
        items = {item['key']: item for item in self.se['items']}
        self.assertIn(health_script().strip(), items['xiqse.nbi.health']['params'])
        self.assertIn(licenses_script().strip(), items['xiqse.nbi.licenses']['params'])
        self.assertIn(pilot_script().strip(), items['xiqse.nbi.pilot']['params'])
        lld = self.se['discovery_rules'][0]
        self.assertIn(lld_script().strip(), lld['preprocessing'][0]['parameters'][0])

    def test_http_uses_new_request_per_call_and_oauth(self):
        health = health_script()
        self.assertGreaterEqual(health.count('new HttpRequest()'), 2)
        self.assertIn('grant_type=client_credentials', health)
        self.assertIn('/nbi/graphql', health)
        self.assertIn("JSON.stringify({ query: query })", health)
        self.assertNotIn('variables', (JS_DIR / 'http_nbi.js').read_text(encoding='utf-8'))

    def test_end_systems_query_is_inlined(self):
        licenses = licenses_script()
        self.assertIn('endSystems(maxResults: ', licenses)
        self.assertNotIn('$maxResults', licenses)
        self.assertIn('rows.length >= maxResults', licenses)

    def test_engines_query_tries_connected_then_falls_back(self):
        health = health_script()
        self.assertIn('connected', health)
        self.assertIn('isConnected', health)
        self.assertIn('freeRadiusEnabled', health)

    def test_item_prototypes_use_compact_extract_js(self):
        proto = next(
            row
            for row in self.se['discovery_rules'][0]['item_prototypes']
            if row['key'] == 'xiqse.engine.licensed[{#ENGINE.IP}]'
        )
        js = proto['preprocessing'][0]['parameters'][0]
        self.assertIn('function pickEngineField', js)
        self.assertNotIn('countLicenseWindow', js)
        self.assertNotIn('new HttpRequest', js)
        self.assertIn(extract_engine_script('licensed', '2').strip(), js)
        self.assertIn('trigger_prototypes', self.se['discovery_rules'][0]['item_prototypes'][1])
        self.assertNotIn('triggers', self.se['discovery_rules'][0]['item_prototypes'][1])

    def test_nbi_average_depends_on_8443_not_icmp(self):
        avail = next(item for item in self.se['items'] if item['key'] == 'xiqse.nbi.available')
        nbi = next(tr for tr in avail['triggers'] if tr['name'] == 'XIQ-SE: NBI unexpected response')
        self.assertEqual(nbi['priority'], 'AVERAGE')
        self.assertEqual(nbi['dependencies'][0]['name'], 'XIQ-SE: HTTPS 8443 down')
        self.assertNotIn('icmpping', nbi['expression'])

    def test_heap_has_no_trigger(self):
        heap = next(item for item in self.se['items'] if item['key'] == 'xiqse.nbi.heap.pct')
        self.assertFalse(heap.get('triggers'))
        self.assertEqual(heap['units'], '%')

    def test_nac_cap_requires_purchased_total(self):
        used = next(item for item in self.se['items'] if item['key'] == 'xiqse.nac.used24h')
        names = {tr['name']: tr for tr in used['triggers']}
        self.assertIn('{$XIQ.NAC.TOTAL}>0', names['XIQ-SE: NAC license seats exhausted']['expression'])
        self.assertIn('{$XIQ.NAC.TOTAL}>0', names['XIQ-SE: NAC license seats high']['expression'])

    def test_navigator_cap_requires_purchased_total(self):
        used = next(item for item in self.se['items'] if item['key'] == 'xiqse.nav.used')
        names = {tr['name']: tr for tr in used['triggers']}
        self.assertIn('{$XIQ.NAV.TOTAL}>0', names['XIQ-SE: Navigator licenses exhausted']['expression'])
        remain = next(item for item in self.se['items'] if item['key'] == 'xiqse.nav.remaining')
        low = next(tr for tr in remain['triggers'] if tr['name'] == 'XIQ-SE: few Navigator licenses remaining')
        self.assertIn('{$XIQ.NAV.TOTAL}>0', low['expression'])

    def test_log_forward_trigger_is_elapsed_not_clock_and_has_age_graph(self):
        proto = next(
            row
            for row in self.se['discovery_rules'][0]['item_prototypes']
            if row['key'] == 'xiqse.engine.auth.age[{#ENGINE.IP}]'
        )
        stale = proto['trigger_prototypes'][0]
        self.assertEqual(stale['name'], 'XIQ-SE engine {#ENGINE.NAME}: not forwarding auth logs')
        self.assertEqual(stale['priority'], 'AVERAGE')
        self.assertIn('{$XIQ.NAC.FRESH.CONTROL}=1', stale['expression'])
        self.assertIn('{$XIQ.NAC.FRESH:"{#ENGINE.IP}"}', stale['expression'])
        self.assertNotIn('dayofweek()', stale['expression'])
        self.assertNotIn('time()', stale['expression'])
        graphs = {row['name'] for row in self.se['discovery_rules'][0]['graph_prototypes']}
        self.assertIn('Engine {#ENGINE.NAME}: last auth age', graphs)

    def test_overview_shows_used_not_remaining(self):
        overview = self.se['dashboards'][0]['pages'][0]
        self.assertEqual(overview['name'], 'Overview')
        keys = []
        for widget in overview['widgets']:
            for field in widget.get('fields') or []:
                value = field.get('value')
                if isinstance(value, dict) and value.get('key'):
                    keys.append(value['key'])
        self.assertEqual(
            keys[:4],
            ['xiqse.nbi.available', 'xiqse.nac.used24h', 'xiqse.pilot.used', 'xiqse.nav.used'],
        )
        self.assertNotIn('xiqse.nac.remaining', keys[:4])

    def test_remaining_is_zero_until_purchased_total_is_set(self):
        remain = next(item for item in self.se['items'] if item['key'] == 'xiqse.nac.remaining')
        self.assertIn('*({$XIQ.NAC.TOTAL}>0)', remain['params'])
        self.assertNotIn('?', remain['params'])
        macros = {row['macro'] for row in self.se['macros']}
        self.assertNotIn('{$XIQ.NAC.FRESH.TIME.START}', macros)
        self.assertNotIn('{$XIQ.NAC.FRESH.TIME.END}', macros)

    def test_dashboards_and_valuemaps_live_on_the_template(self):
        self.assertEqual({d['name'] for d in self.se['dashboards']}, DASHBOARD_NAMES)
        maps = {row['name'] for row in self.se['valuemaps']}
        self.assertTrue({'XIQ-SE NBI', 'XIQ-SE tri-state', 'XIQ-SE truncated', 'Service state'} <= maps)
        self.assertNotIn('valuemaps', self.se_doc['zabbix_export'])

    def test_nac_template_is_thin_and_disabled(self):
        keys = _walk_item_keys(self.nac)
        self.assertTrue(NAC_ITEM_KEYS <= keys)
        for item in self.nac['items']:
            for tr in item.get('triggers') or []:
                if tr['name'] in NAC_TRIGGER_NAMES:
                    self.assertEqual(tr['status'], 'DISABLED')
        self.assertNotIn('net.udp.service', self.nac_text)
        self.assertNotIn('icmpping', self.nac_text)

    def test_secret_macros_are_empty_in_yaml(self):
        secret = next(m for m in self.se['macros'] if m['macro'] == '{$XIQSE.API.CLIENT.SECRET}')
        self.assertEqual(secret['type'], 'SECRET_TEXT')
        self.assertEqual(secret['value'], '')
        fqdn = next(m for m in self.se['macros'] if m['macro'] == XIQSE_FQDN_MACRO)
        self.assertEqual(fqdn['value'], '')


class ApplyWiringTests(unittest.TestCase):
    def test_yaml_paths_exist(self):
        self.assertEqual(
            set(TEMPLATE_FILES),
            {SE_TEMPLATE_NAME, NAC_TEMPLATE_NAME, 'ExtremeControl by SNMP'},
        )
        for path in TEMPLATE_FILES.values():
            self.assertTrue(path.exists(), path)

    def test_platform_pattern_matches_site_engine_names(self):
        self.assertTrue(platform_is_xiqse('XIQ-SE'))
        self.assertTrue(platform_is_xiqse('XIQSE'))
        self.assertTrue(platform_is_xiqse('ExtremeCloud IQ Site Engine'))
        self.assertTrue(platform_is_xiqse('NetSight'))
        self.assertFalse(platform_is_xiqse('EXOS'))
        self.assertIn('XIQ.?SE', SE_PLATFORM_PATTERN)

    def test_network_script_owns_apply_and_skips_hostsync(self):
        src = network_source()
        self.assertIn(APPLY_FLAG, src)
        self.assertIn(CHECK_FLAG, src)
        self.assertIn('run_apply_xiqse', src)
        apply_fn = _function_source(src, 'run_apply_xiqse')
        import_fn = _function_source(src, 'import_xiqse_templates')
        self.assertIsNotNone(apply_fn)
        self.assertIsNotNone(import_fn)
        self.assertNotIn('import_extreme_templates', apply_fn)
        self.assertNotIn('SyncHostJob', apply_fn)
        self.assertNotIn('configure_nbxsync_zerotouch', apply_fn)
        self.assertIn('strict=True', import_fn)
        self.assertIn(SE_TEMPLATE_RULE, src)
        self.assertIn('_xiqse.XIQSE_FQDN_JINJA', src)
        self.assertIn('_xiqse.XIQSE_FQDN_MACRO', src)
        self.assertIn('_xiqse.NAC_PORTAL_FQDN_MACRO', src)
        self.assertIn("'deleteMissing': False", src)

    def test_zerotouch_soft_assigns_nac_with_any(self):
        src = zerotouch_source()
        self.assertNotIn(APPLY_FLAG, src)
        self.assertIn("'extremecontrol_observability': 'ExtremeControl Observability'", src)
        self.assertIn("'xiqse_observability': 'XIQ-SE Observability'", src)
        optional = re.search(r'OPTIONAL_TPL_KEYS = frozenset\(\{([^}]+)\}\)', src, re.S)
        self.assertIsNotNone(optional)
        self.assertIn("'extremecontrol_observability'", optional.group(1))
        self.assertIn("'xiqse_observability'", optional.group(1))
        self.assertIn("'extremecontrol_snmp'", optional.group(1))
        self.assertNotIn('template_xiqse_observability.yaml', src)
        self.assertNotIn('import_yaml_templates', src)
        self.assertIn(f"'{NAC_PORTAL_FQDN_MACRO}', '{XIQSE_FQDN_JINJA}', '{NAC_ROLE}'", src)
        self.assertIn("'extremecontrol_observability': [HostInterfaceRequirementChoices.ANY]", src)
        self.assertIn("'extremecontrol_snmp': 'ExtremeControl by SNMP'", src)
        self.assertIn("'extremecontrol_snmp': [HostInterfaceRequirementChoices.SNMP]", src)


def _function_source(src: str, name: str) -> str | None:
    import ast

    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node)
    return None


if __name__ == '__main__':
    unittest.main()
