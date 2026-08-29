#!/usr/bin/env python3
"""Contract tests for ExtremeControl by SNMP (no live walk)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml

from extremecontrol_snmp import (
    APPL,
    APPL_KEYS,
    APPL_RATE_KEYS,
    FIXTURES,
    FORBIDDEN_SNIPPETS,
    JS_DIR,
    MIB_PATH,
    OID_BASE,
    SNMP_ITEM_KEYS,
    SNMP_TEMPLATE_NAME,
    SNMP_TRIGGER_NAMES,
    SNMP_YAML,
    TPL,
    render,
    write_yaml,
)
from xiqse_observability import (
    APPLY_FLAG,
    NAC_TEMPLATE_NAME,
    SE_TEMPLATE_NAME,
    TEMPLATE_FILES,
    network_source,
    zerotouch_source,
)

UUID_RE = re.compile(r'^[0-9a-f]{32}$')


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


def _run_js(script: str) -> str:
    node = shutil.which('node') or '/exec-daemon/node'
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as handle:
        handle.write(script)
        path = handle.name
    proc = subprocess.run([node, path], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or 'node failed').strip())
    return (proc.stdout or '').strip()


class CanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canary = json.loads((FIXTURES / 'canary_enac.json').read_text(encoding='utf-8'))
        cls.classify = (JS_DIR / 'classify_product.js').read_text(encoding='utf-8')

    def test_five_engines_have_sixteen_counters(self):
        self.assertEqual(len(self.canary['order']), 16)
        self.assertEqual(len(self.canary['engines']), 5)
        for name, row in self.canary['engines'].items():
            self.assertEqual(len(row['values']), 16, name)

    def test_success_fail_challenge_fit_inside_requests(self):
        for name, row in self.canary['engines'].items():
            req, ok, fail, chal = row['values'][:4]
            self.assertLessEqual(ok + fail + chal, req, name)

    def test_contact_lost_and_agents_were_zero(self):
        for name, row in self.canary['engines'].items():
            self.assertEqual(row['values'][12], 0, name)
            self.assertEqual(row['values'][15], 0, name)

    def test_assessment_unused_captive_portal_present(self):
        for row in self.canary['engines'].values():
            self.assertEqual(row['values'][10], 0)
        self.assertGreater(self.canary['engines']['kr-sel-p-enac01']['values'][11], 1000)

    def test_ia_v_sysobjectid_maps(self):
        out = _run_js(
            self.classify
            + "\nconsole.log(JSON.stringify({p: classifyControlProduct('1.3.6.1.4.1.1916.2.252'),"
            + " n: classifyControlProduct('.1.3.6.1.4.1.1916.2.252'),"
            + " linux: classifyControlProduct('1.3.6.1.4.1.8072.3.2.10'),"
            + " id: controlProductIdentity('1.3.6.1.4.1.1916.2.252')}));\n"
        )
        data = json.loads(out)
        self.assertEqual(data['p'], 'IA-V')
        self.assertEqual(data['n'], 'IA-V')
        self.assertEqual(data['linux'], '')
        self.assertEqual(data['id'], 1)


class YamlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        write_yaml()
        cls.text = SNMP_YAML.read_text(encoding='utf-8')
        cls.doc = yaml.safe_load(cls.text)
        cls.tpl = cls.doc['zabbix_export']['templates'][0]

    def test_committed_yaml_matches_renderer(self):
        self.assertEqual(self.text, render())

    def test_export_shape(self):
        self.assertEqual(self.doc['zabbix_export']['version'], '7.0')
        self.assertEqual(len(self.doc['zabbix_export']['templates']), 1)
        self.assertEqual(self.tpl['template'], SNMP_TEMPLATE_NAME)
        self.assertEqual(self.tpl['template'], TPL)

    def test_uuids_are_version_four(self):
        for value in re.findall(r'uuid: ([0-9a-f]+)', self.text):
            self.assertRegex(value, UUID_RE)
            self.assertEqual(value[12], '4')
            self.assertIn(value[16], '89ab')

    def test_item_keys_and_triggers(self):
        keys = _walk_item_keys(self.tpl)
        self.assertTrue(SNMP_ITEM_KEYS <= keys)
        self.assertTrue(APPL_KEYS <= keys)
        self.assertTrue(APPL_RATE_KEYS <= keys)
        names = _walk_names(self.tpl, ('triggers',))
        self.assertTrue(SNMP_TRIGGER_NAMES <= names)

    def test_all_sixteen_oids_are_present(self):
        for _key, mib, index, _title, _rate in APPL:
            oid = f'{OID_BASE}.{index}.0'
            self.assertIn(oid, self.text, mib)
            self.assertIn(mib, self.text)

    def test_mib_file_matches_oids(self):
        mib = MIB_PATH.read_text(encoding='utf-8')
        self.assertIn('ENTERASYS-NAC-APPLIANCE-MIB', mib)
        self.assertIn('etsysModules 73', mib)
        for _key, name, _index, _title, _rate in APPL:
            self.assertIn(name, mib)

    def test_forbidden_snippets_stay_out(self):
        for snippet in FORBIDDEN_SNIPPETS:
            self.assertNotIn(snippet, self.text, snippet)

    def test_no_icmp_and_no_radius_udp(self):
        self.assertNotIn('icmpping', self.text)
        self.assertNotIn('net.udp.service', self.text)
        snmp = next(item for item in self.tpl['items'] if item['key'] == 'zabbix[host,snmp,available]')
        trig = snmp['triggers'][0]
        self.assertEqual(trig['priority'], 'WARNING')
        self.assertNotIn('icmpping', trig['expression'])
        self.assertFalse(trig.get('dependencies'))

    def test_unsupported_threshold_allows_only_one_remaining_calculated_item(self):
        unsupported = next(row for row in self.tpl['items'] if row['key'] == 'zabbix[host,,items_unsupported]')
        trigger = unsupported['triggers'][0]
        threshold = next(m for m in self.tpl['macros'] if m['macro'] == '{$UNSUPPORTED.MAX}')
        self.assertEqual(threshold['value'], '1')
        self.assertIn('>{$UNSUPPORTED.MAX}', trigger['expression'])

    def test_snmp_dashboard_uses_the_supported_internal_item(self):
        self.assertNotIn('nac.snmp.available', _walk_item_keys(self.tpl))
        self.assertIn("'zabbix[host,snmp,available]'", self.text)

    def test_fail_ratio_default_is_silent(self):
        item = next(row for row in self.tpl['items'] if row['key'] == 'nac.appl.auth.fail.pct')
        trig = item['triggers'][0]
        self.assertIn('{$NAC.SNMP.FAIL.WARN}<101', trig['expression'])
        warn = next(m for m in self.tpl['macros'] if m['macro'] == '{$NAC.SNMP.FAIL.WARN}')
        self.assertEqual(warn['value'], '101')

    def test_contact_lost_is_gated(self):
        item = next(row for row in self.tpl['items'] if row['key'] == 'nac.appl.contact.lost')
        trig = item['triggers'][0]
        self.assertIn('{$NAC.SNMP.CONTACTLOST.CONTROL}=1', trig['expression'])
        control = next(m for m in self.tpl['macros'] if m['macro'] == '{$NAC.SNMP.CONTACTLOST.CONTROL}')
        self.assertEqual(control['value'], '0')

    def test_health_dashboard_exists(self):
        self.assertEqual({d['name'] for d in self.tpl['dashboards']}, {'Health'})
        pages = {p['name'] for p in self.tpl['dashboards'][0]['pages']}
        self.assertEqual(pages, {'Overview', 'Auth'})

    def test_dashboard_coordinates_are_strings(self):
        for dashboard in self.tpl['dashboards']:
            for page in dashboard['pages']:
                for widget in page['widgets']:
                    for coordinate in ('x', 'y', 'width', 'height'):
                        if coordinate in widget:
                            self.assertIsInstance(widget[coordinate], str)
    def test_javascript_is_indented_under_block_scalar(self):
        product = next(row for row in self.tpl['items'] if row['key'] == 'nac.snmp.product')
        js = product['preprocessing'][0]['parameters'][0]
        self.assertIn('function classifyControlProduct', js)
        self.assertIn('IA-V', js)


class ApplyWiringTests(unittest.TestCase):
    def test_template_files_include_snmp(self):
        self.assertIn(SNMP_TEMPLATE_NAME, TEMPLATE_FILES)
        self.assertIn(SE_TEMPLATE_NAME, TEMPLATE_FILES)
        self.assertIn(NAC_TEMPLATE_NAME, TEMPLATE_FILES)
        self.assertTrue(TEMPLATE_FILES[SNMP_TEMPLATE_NAME].exists())

    def test_apply_imports_snmp_and_assigns_snmp_interface(self):
        src = network_source()
        self.assertIn(APPLY_FLAG, src)
        step = _function_source(src, '_step_xiqse_nbxsync')
        self.assertIsNotNone(step)
        self.assertIn('SNMP_TEMPLATE_NAME', step)
        self.assertIn('HostInterfaceRequirementChoices.SNMP', step)
        self.assertIn('ZabbixConfigurationGroupAssignment', step)
        self.assertIn('_SNMP_MONITORING_CG', step)
        self.assertNotIn('import_extreme_templates', step)
        self.assertNotIn('SyncHostJob', step)

    def test_zerotouch_soft_assigns_snmp_on_nac(self):
        src = zerotouch_source()
        self.assertIn("'extremecontrol_snmp': 'ExtremeControl by SNMP'", src)
        self.assertIn("'extremecontrol_snmp'", src)
        self.assertIn("'extremecontrol_snmp': [HostInterfaceRequirementChoices.SNMP]", src)


if __name__ == '__main__':
    unittest.main()
