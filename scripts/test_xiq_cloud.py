#!/usr/bin/env python3
"""Contract tests for ExtremeCloud IQ by HTTP (no live Cloud API)."""

from __future__ import annotations

import json
import re
import unittest

import yaml

from xiq_cloud import (
    APPLY_FLAG,
    CHECK_FLAG,
    CLOUD_ITEM_KEYS,
    CLOUD_TEMPLATE_NAME,
    CLOUD_TEMPLATE_RULE,
    CLOUD_TRIGGER_NAMES,
    CLOUD_YAML,
    DASHBOARD_NAMES,
    FORBIDDEN_SNIPPETS,
    JS_DIR,
    TEMPLATE_FILES,
    TOKEN_CG_NAME,
    TOKEN_MACRO,
    account_script,
    load_fixture,
    nbi_health_source,
    network_source,
    ops_script,
    run_cloud_json,
    zerotouch_source,
)
from xiq_cloud_template import render_cloud, write_yaml


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


def _function_source(src: str, name: str) -> str | None:
    import ast

    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node)
    return None


def _mock_prelude() -> str:
    return (
        f'var VIQ = {json.dumps(load_fixture("viq.json"))};\n'
        f'var VHM = {json.dumps(load_fixture("vhm.json"))};\n'
        f'var TOKEN = {json.dumps(load_fixture("token_info.json"))};\n'
        f'var GRID = {json.dumps(load_fixture("backup_grid.json"))};\n'
        f'var STATS = {json.dumps(load_fixture("device_stats.json"))};\n'
        'function mockGet(params, path) {\n'
        "  if (path === '/account/viq') return { ok: 1, error: '', status: 200, data: VIQ };\n"
        "  if (path === '/account/vhm/status') return { ok: 1, error: '', status: 200, data: VHM };\n"
        "  if (path === '/auth/apitoken/info') return { ok: 1, error: '', status: 200, data: TOKEN };\n"
        "  if (path.indexOf('/backup/history/grid') === 0) return { ok: 1, error: '', status: 200, data: GRID };\n"
        "  if (path === '/devices/stats') return { ok: 1, error: '', status: 200, data: STATS };\n"
        "  return { ok: 0, error: 'unexpected ' + path, status: 0, data: null };\n"
        '}\n'
    )


class LicenseClassifyTests(unittest.TestCase):
    def test_pilot_sku_matches_pil_needles(self):
        self.assertEqual(run_cloud_json("classifyLicense({license_type: 'XIQ-PIL-S-C'})"), 'pilot')
        self.assertEqual(run_cloud_json("classifyLicense({license_type: 'PILOT'})"), 'pilot')

    def test_copilot_is_not_pilot(self):
        self.assertEqual(run_cloud_json("classifyLicense({license_type: 'XIQ-COPILOT'})"), 'copilot')
        self.assertEqual(run_cloud_json("classifyLicense({license_type: 'Co-Pilot'})"), 'copilot')

    def test_navigator_and_nac(self):
        self.assertEqual(run_cloud_json("classifyLicense({license_type: 'XIQ-NAV-S'})"), 'nav')
        self.assertEqual(run_cloud_json("classifyLicense({license_type: 'XIQ-NAC-S'})"), 'nac')

    def test_legacy_and_blank_are_other(self):
        self.assertEqual(run_cloud_json("classifyLicense({license_type: 'Legacy'})"), 'other')
        self.assertEqual(run_cloud_json("classifyLicense({license_type: ''})"), 'other')
        self.assertEqual(
            run_cloud_json("classifyLicense({license_type: '', entitlement_type: 'PERMANENT'})"),
            'other',
        )

    def test_entitlement_type_is_not_the_sku(self):
        self.assertEqual(
            run_cloud_json("classifyLicense({license_type: '', entitlement_type: 'PILOT'})"),
            'other',
        )


class AccountSnapshotTests(unittest.TestCase):
    def test_portal_like_pilot_is_581_578_3(self):
        snap = run_cloud_json(
            "collectAccount({url: 'https://api.extremecloudiq.com', token: 't'}, mockGet)",
            prelude=_mock_prelude(),
        )
        self.assertEqual(snap['ok'], 1)
        self.assertEqual(snap['customerId'], 'sApsGq3wp')
        self.assertEqual(snap['expired'], 0)
        self.assertEqual(snap['vhmActive'], 1)
        self.assertEqual(snap['vhmStatus'], 'ACTIVE_STATUS')
        self.assertEqual(snap['tokenKnown'], 1)
        self.assertEqual(snap['tokenTtl'], 1209600)
        self.assertEqual(snap['pilotPresent'], 1)
        self.assertEqual(snap['pilotHave'], 581)
        self.assertEqual(snap['pilotActivated'], 578)
        self.assertEqual(snap['pilotAvailable'], 3)
        self.assertEqual(snap['navPresent'], 1)
        self.assertEqual(snap['navHave'], 0)
        self.assertEqual(snap['navAvailable'], 0)
        self.assertEqual(snap['copilotHave'], 50)
        self.assertEqual(snap['nacPresent'], 0)
        self.assertEqual(snap['nacHave'], 0)
        self.assertEqual(snap['licenseCount'], 5)
        self.assertIn('XIQ-PIL-S-C', snap['licenseTypes'])
        self.assertIn('Legacy', snap['licenseTypes'])
        self.assertEqual(snap['pilotExpire'], run_cloud_json("parseExpireEpoch('2026-11-15T00:00:00.000+0000')"))

    def test_missing_token_does_not_call_http(self):
        snap = run_cloud_json(
            "collectAccount({url: 'https://api.extremecloudiq.com', token: ''}, function() { throw 'called'; })"
        )
        self.assertEqual(snap['ok'], 0)
        self.assertEqual(snap['error'], 'missing token')
        self.assertEqual(snap['pilotHave'], 0)
        self.assertEqual(snap['vhmActive'], 2)

    def test_viq_failure_keeps_numeric_fields(self):
        prelude = (
            'function boom(params, path) { return { ok: 0, error: "HTTP 401", status: 401, data: null }; }\n'
        )
        snap = run_cloud_json(
            "collectAccount({token: 't'}, boom)",
            prelude=prelude,
        )
        self.assertEqual(snap['ok'], 0)
        self.assertEqual(snap['pilotAvailable'], 0)
        self.assertEqual(snap['licenseCount'], 0)
        self.assertIn('HTTP 401', snap['error'])

    def test_vhm_failure_is_unknown_not_down(self):
        prelude = _mock_prelude() + (
            'function mockGet2(params, path) {\n'
            "  if (path === '/account/vhm/status') return { ok: 0, error: 'HTTP 500', status: 500, data: null };\n"
            '  return mockGet(params, path);\n'
            '}\n'
        )
        snap = run_cloud_json(
            "collectAccount({token: 't'}, mockGet2)",
            prelude=prelude,
        )
        self.assertEqual(snap['ok'], 1)
        self.assertEqual(snap['vhmActive'], 2)
        self.assertEqual(snap['pilotHave'], 581)

    def test_active_without_status_suffix_still_counts(self):
        self.assertEqual(run_cloud_json("vhmIsActive('ACTIVE')"), 1)
        self.assertEqual(run_cloud_json("vhmIsActive('SUSPENDED')"), 0)


class OpsSnapshotTests(unittest.TestCase):
    def test_newest_config_backup_ignores_full(self):
        now = 1721111111 + 86400
        snap = run_cloud_json(
            f"collectOps({{token: 't'}}, mockGet, {now})",
            prelude=_mock_prelude(),
        )
        self.assertEqual(snap['ok'], 1)
        self.assertEqual(snap['lastConfigBackup'], 1721111111)
        self.assertEqual(snap['lastConfigBackupAge'], 86400)
        self.assertEqual(snap['lastConfigBackupName'], 'viq-config-new.tar.gz')
        self.assertEqual(snap['backupCount'], 3)
        self.assertEqual(snap['deviceTotal'], 610)
        self.assertEqual(snap['deviceManaged'], 600)
        self.assertEqual(snap['deviceConnected'], 578)
        self.assertEqual(snap['deviceDisconnected'], 22)
        self.assertEqual(snap['deviceUnmanaged'], 10)

    def test_empty_grid_stays_zero_age(self):
        prelude = (
            'function emptyGet(params, path) {\n'
            "  if (path.indexOf('/backup/history/grid') === 0) return { ok: 1, error: '', status: 200, data: { data: [] } };\n"
            "  if (path === '/devices/stats') return { ok: 1, error: '', status: 200, data: { total_device_count: 0, managed_device_count: 0, connected_device_count: 0 } };\n"
            "  return { ok: 0, error: 'no', status: 0, data: null };\n"
            '}\n'
        )
        snap = run_cloud_json("collectOps({token: 't'}, emptyGet, 1700000000)", prelude=prelude)
        self.assertEqual(snap['ok'], 1)
        self.assertEqual(snap['lastConfigBackup'], 0)
        self.assertEqual(snap['lastConfigBackupAge'], 0)


class YamlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        write_yaml()
        cls.text = CLOUD_YAML.read_text(encoding='utf-8')
        cls.doc = yaml.safe_load(cls.text)
        cls.tpl = cls.doc['zabbix_export']['templates'][0]

    def test_committed_yaml_matches_renderer(self):
        self.assertEqual(self.text, render_cloud())

    def test_export_version_and_name(self):
        self.assertEqual(self.doc['zabbix_export']['version'], '7.0')
        self.assertEqual(self.tpl['template'], CLOUD_TEMPLATE_NAME)
        self.assertEqual({d['name'] for d in self.tpl['dashboards']}, DASHBOARD_NAMES)

    def test_uuids_are_hex_and_template_uuids_are_v4(self):
        uuids = re.findall(r'uuid: ([0-9a-f]+)', self.text)
        self.assertTrue(uuids)
        group = '36bff6c29af64692839d077febfc7079'
        for value in uuids:
            self.assertRegex(value, UUID_RE)
            if value != group:
                self.assertRegex(value, UUID4_RE)
        self.assertEqual(len(uuids), len(set(uuids)))

    def test_item_and_trigger_keys(self):
        keys = _walk_item_keys(self.tpl)
        self.assertTrue(CLOUD_ITEM_KEYS <= keys)
        names = _walk_names(self.tpl, ('triggers',))
        self.assertTrue(CLOUD_TRIGGER_NAMES <= names)

    def test_forbidden_snippets_stay_out(self):
        blob = self.text + '\n' + account_script() + '\n' + ops_script()
        for snippet in FORBIDDEN_SNIPPETS:
            self.assertNotIn(snippet, blob, snippet)
        js = (JS_DIR / 'http_xiq.js').read_text(encoding='utf-8')
        self.assertEqual(js.count('/auth/apitoken'), js.count('/auth/apitoken/info'))
        self.assertNotIn('.post(', js)
        self.assertIn('request.get(', js)
        self.assertNotIn('/devices?', js)

    def test_not_folded_into_nbi(self):
        health = nbi_health_source()
        self.assertNotIn('extremecloudiq', health)
        self.assertNotIn('xiq.cloud', health)
        self.assertNotIn('/account/viq', self.tpl.get('description', '') + health)
        self.assertNotIn('xiqse.nbi', self.text)

    def test_no_calculated_no_lld_no_icmp(self):
        self.assertFalse(self.tpl.get('discovery_rules'))
        calculated = [item['key'] for item in self.tpl['items'] if item['type'] == 'CALCULATED']
        self.assertEqual(calculated, [])
        self.assertNotIn('icmpping', self.text)
        self.assertNotIn('net.tcp.service', self.text)

    def test_scripts_are_embedded(self):
        items = {item['key']: item for item in self.tpl['items']}
        self.assertIn(account_script().strip(), items['xiq.cloud.account']['params'])
        self.assertIn(ops_script().strip(), items['xiq.cloud.ops']['params'])
        self.assertEqual(items['xiq.cloud.account']['delay'], '5m')
        self.assertEqual(items['xiq.cloud.ops']['delay'], '15m')

    def test_token_macro_is_secret_and_empty(self):
        secret = next(m for m in self.tpl['macros'] if m['macro'] == TOKEN_MACRO)
        self.assertEqual(secret['type'], 'SECRET_TEXT')
        self.assertEqual(secret['value'], '')
        url = next(m for m in self.tpl['macros'] if m['macro'] == '{$XIQ.CLOUD.API.URL}')
        self.assertEqual(url['value'], 'https://api.extremecloudiq.com')

    def test_cloud_tickets_do_not_depend_on_nbi(self):
        blob = json.dumps(self.tpl)
        self.assertNotIn('xiqse.nbi', blob)
        self.assertNotIn('8443', blob)
        avail = next(item for item in self.tpl['items'] if item['key'] == 'xiq.cloud.available')
        for tr in avail['triggers']:
            self.assertNotIn('dependencies', tr)
            self.assertEqual(tr['priority'], 'AVERAGE')

    def test_nac_available_has_no_trigger(self):
        nac = next(item for item in self.tpl['items'] if item['key'] == 'xiq.cloud.nac.available')
        self.assertFalse(nac.get('triggers'))
        self.assertIn('No trigger', nac.get('description') or '')

    def test_disconnected_census_has_no_trigger(self):
        disc = next(item for item in self.tpl['items'] if item['key'] == 'xiq.cloud.devices.disconnected')
        self.assertFalse(disc.get('triggers'))

    def test_pilot_available_zero_requires_have(self):
        item = next(row for row in self.tpl['items'] if row['key'] == 'xiq.cloud.pilot.available')
        tr = next(row for row in item['triggers'] if 'Pilot Cloud available is 0' in row['name'])
        self.assertEqual(tr['priority'], 'WARNING')
        self.assertIn('xiq.cloud.pilot.have)>0', tr['expression'])
        self.assertNotIn('581', tr['expression'])

    def test_backup_stale_requires_a_first_backup(self):
        item = next(row for row in self.tpl['items'] if row['key'] == 'xiq.cloud.backup.age')
        tr = item['triggers'][0]
        self.assertIn('xiq.cloud.backup.time)>0', tr['expression'])
        self.assertIn('{$XIQ.CLOUD.BACKUP.MAX}', tr['expression'])
        self.assertEqual(tr['priority'], 'AVERAGE')

    def test_overview_shows_cloud_pilot_not_se_320(self):
        overview = self.tpl['dashboards'][0]['pages'][0]
        keys = []
        for widget in overview['widgets']:
            for field in widget.get('fields') or []:
                value = field.get('value')
                if isinstance(value, dict) and value.get('key'):
                    keys.append(value['key'])
        self.assertEqual(
            keys[:4],
            [
                'xiq.cloud.available',
                'xiq.cloud.pilot.available',
                'xiq.cloud.pilot.have',
                'xiq.cloud.pilot.activated',
            ],
        )
        self.assertNotIn('xiqse.pilot.used', keys)

    def test_dependents_are_jsonpath_not_calculated(self):
        remain = next(item for item in self.tpl['items'] if item['key'] == 'xiq.cloud.pilot.available')
        self.assertEqual(remain['type'], 'DEPENDENT')
        self.assertEqual(remain['preprocessing'][0]['parameters'][0], '$.pilotAvailable')


class ApplyWiringTests(unittest.TestCase):
    def test_yaml_path_exists(self):
        self.assertEqual(set(TEMPLATE_FILES), {CLOUD_TEMPLATE_NAME})
        self.assertTrue(CLOUD_YAML.exists())

    def test_network_script_owns_apply_and_skips_hostsync(self):
        src = network_source()
        self.assertIn(APPLY_FLAG, src)
        self.assertIn(CHECK_FLAG, src)
        apply_fn = _function_source(src, 'run_apply_xiq_cloud')
        import_fn = _function_source(src, 'import_xiq_cloud_templates')
        step_fn = _function_source(src, '_step_xiq_cloud_nbxsync')
        token_fn = _function_source(src, '_step_xiq_cloud_token_scope')
        self.assertIsNotNone(apply_fn)
        self.assertIsNotNone(import_fn)
        self.assertNotIn('import_extreme_templates', apply_fn)
        self.assertNotIn('import_xiqse_templates', apply_fn)
        self.assertNotIn('SyncHostJob', apply_fn)
        self.assertNotIn('configure_nbxsync_zerotouch', apply_fn)
        self.assertIn('strict=True', import_fn)
        self.assertIn("'deleteMissing': False", src)
        self.assertIn(CLOUD_TEMPLATE_RULE, src)
        self.assertIn('TOKEN_CG_NAME', src)
        self.assertIn('_ensure_macro_assignment_if_absent', token_fn)
        self.assertIn('_mirror_license_totals_to_platform', token_fn)
        self.assertIn('ZabbixMacroTypeChoices.SECRET', token_fn)
        self.assertNotIn('SyncHostJob', token_fn)
        self.assertIn('HostInterfaceRequirementChoices.ANY', step_fn)
        self.assertNotIn('icmpping', step_fn)
        self.assertEqual(TOKEN_CG_NAME, 'ExtremeCloud IQ API')
        self.assertEqual(TOKEN_MACRO, '{$XIQ.CLOUD.API.TOKEN}')

    def test_zerotouch_soft_resolves_without_importing(self):
        src = zerotouch_source()
        self.assertNotIn(APPLY_FLAG, src)
        self.assertIn("'xiq_cloud_http': 'ExtremeCloud IQ by HTTP'", src)
        optional = re.search(r'OPTIONAL_TPL_KEYS = frozenset\(\{([^}]+)\}\)', src, re.S)
        self.assertIsNotNone(optional)
        self.assertIn("'xiq_cloud_http'", optional.group(1))
        self.assertNotIn('template_extremecloud_iq_http.yaml', src)
        self.assertNotIn('import_xiq_cloud_templates', src)
        self.assertNotIn('import_yaml_templates', src)


if __name__ == '__main__':
    unittest.main()
