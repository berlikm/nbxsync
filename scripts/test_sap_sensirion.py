#!/usr/bin/env python3
"""Contract tests for SAP template from Sensirion (no live Promonitor / SNMP)."""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

import yaml

from sap_sensirion import (
    APP_ITEM_KEYS,
    APP_TRIGGER_NAMES,
    APPLY_FLAG,
    CANARY_HOST,
    CHECK_FLAG,
    FORBIDDEN_SNIPPETS,
    LINUX_NETSNMP_SYSOBJECTID,
    LM_APP_METRICS,
    LM_PROMONITOR_USER,
    LM_SAP_HOSTS,
    LM_SNMP_USER,
    SAP_ENTERPRISE_OID,
    SAP_ROLES,
    SNMP_ITEM_KEYS,
    SNMP_LLD_KEYS,
    SNMP_PROTOTYPE_KEYS,
    SNMP_TRIGGER_NAMES,
    SNMP_TRIGGER_PROTOTYPE_NAMES,
    TEMPLATE_NAME,
    TEMPLATE_YAML,
    TPL,
    render,
    write_yaml,
)

ROOT = Path(__file__).resolve().parents[1]
UUID_RE = re.compile(r'^[0-9a-f]{12}4[0-9a-f]{3}[89ab][0-9a-f]{15}$')


def _walk_item_keys(node, found: set[str] | None = None) -> set[str]:
    found = found if found is not None else set()
    if isinstance(node, dict):
        if 'key' in node and ('type' in node or 'snmp_oid' in node or 'params' in node):
            found.add(node['key'])
        for value in node.values():
            _walk_item_keys(value, found)
    elif isinstance(node, list):
        for value in node:
            _walk_item_keys(value, found)
    return found


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


def _function_source(src: str, name: str) -> str | None:
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node)
    return None


class SapSensirionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        write_yaml()
        cls.yaml_text = TEMPLATE_YAML.read_text(encoding='utf-8')
        cls.tpl = yaml.safe_load(cls.yaml_text)
        cls.template = cls.tpl['zabbix_export']['templates'][0]
        cls.keys = _walk_item_keys(cls.template)
        cls.triggers = _walk_names(cls.template, ('triggers',))
        cls.trigger_prototypes = _walk_names(cls.template, ('trigger_prototypes',))

    def test_render_matches_written_yaml(self):
        self.assertEqual(self.yaml_text, render())

    def test_template_identity(self):
        self.assertEqual(self.tpl['zabbix_export']['version'], '7.0')
        self.assertEqual(self.template['name'], TEMPLATE_NAME)
        self.assertEqual(self.template['template'], TPL)
        self.assertEqual(self.tpl['zabbix_export']['template_groups'][0]['name'], 'Templates/Applications')

    def test_uuids_look_stable(self):
        uuids = re.findall(r'uuid: ([0-9a-f]{32})', self.yaml_text)
        self.assertGreater(len(uuids), 20)
        self.assertEqual(len(uuids), len(set(uuids)))
        for value in uuids:
            self.assertRegex(value, UUID_RE)

    def test_host_snmp_keys_from_probe(self):
        self.assertTrue(SNMP_ITEM_KEYS.issubset(self.keys))
        self.assertTrue(SNMP_LLD_KEYS.issubset(self.keys))
        self.assertTrue(SNMP_PROTOTYPE_KEYS.issubset(self.keys))
        self.assertIn(LINUX_NETSNMP_SYSOBJECTID, self.yaml_text)
        self.assertIn('1.3.6.1.4.1.2021.10.1.3', self.yaml_text)
        self.assertIn('1.3.6.1.4.1.2021.4.5.0', self.yaml_text)
        self.assertIn('1.3.6.1.2.1.2.2.1.10', self.yaml_text)

    def test_lm_application_trappers(self):
        self.assertTrue(APP_ITEM_KEYS.issubset(self.keys))
        trap_keys = {item['key'] for item in self.template['items'] if item.get('type') == 'TRAP'}
        self.assertEqual(trap_keys, APP_ITEM_KEYS)
        self.assertEqual({row[0] for row in LM_APP_METRICS}, APP_ITEM_KEYS)
        self.assertIn(LM_PROMONITOR_USER, self.yaml_text)
        self.assertIn(LM_SNMP_USER, self.yaml_text)
        self.assertIn(str(LM_SAP_HOSTS), self.template['description'])
        self.assertIn('ch-sta-p-sh01', self.template['description'].lower())

    def test_application_triggers_gated(self):
        self.assertTrue(APP_TRIGGER_NAMES.issubset(self.triggers))
        app_triggers = [
            trig
            for item in self.template['items']
            if item.get('key') in APP_ITEM_KEYS
            for trig in item.get('triggers') or []
        ]
        self.assertEqual(len(app_triggers), len(APP_TRIGGER_NAMES))
        for trig in app_triggers:
            self.assertIn('{$SAP.APP.CONTROL}=1', trig['expression'])

    def test_host_triggers_present(self):
        self.assertTrue(SNMP_TRIGGER_NAMES.issubset(self.triggers))
        self.assertTrue(SNMP_TRIGGER_PROTOTYPE_NAMES.issubset(self.trigger_prototypes))

    def test_forbidden_and_no_fake_sap_snmp(self):
        for snippet in FORBIDDEN_SNIPPETS:
            self.assertNotIn(snippet, self.yaml_text, snippet)
        self.assertNotIn(SAP_ENTERPRISE_OID, self.yaml_text)
        self.assertNotIn('icmpping', self.yaml_text)
        self.assertNotIn('Linux by SNMP', self.yaml_text)

    def test_health_pages(self):
        pages = {page['name'] for page in self.template['dashboards'][0]['pages']}
        self.assertEqual(pages, {'Overview', 'Application', 'Interfaces'})

    def test_divzero_guards(self):
        self.assertIn('+(last(//sap.host.memory.total)=0)', self.yaml_text)
        self.assertIn('+(last(//sap.host.swap.total)=0)', self.yaml_text)

    def test_zerotouch_soft_assigns_snmp(self):
        src = (ROOT / 'scripts/configure_nbxsync_zerotouch.py').read_text(encoding='utf-8')
        self.assertIn(f"'{TEMPLATE_NAME}'", src)
        self.assertIn("('sap_agent', 'SAP ME')", src)
        self.assertIn("('sap_agent', 'SAP HANA')", src)
        self.assertIn("'sap_agent': [HostInterfaceRequirementChoices.SNMP]", src)
        optional = re.search(r'OPTIONAL_TPL_KEYS = frozenset\(\{([^}]+)\}\)', src, re.S)
        self.assertIsNotNone(optional)
        self.assertIn("'sap_agent'", optional.group(1))
        self.assertNotIn('import_yaml_templates', src)

    def test_network_apply_sap_imports_without_fleet_sync(self):
        src = (ROOT / 'scripts/configure_nbxsync_network.py').read_text(encoding='utf-8')
        self.assertIn(APPLY_FLAG, src)
        self.assertIn(CHECK_FLAG, src)
        apply_fn = _function_source(src, 'run_apply_sap') or ''
        self.assertIn('import_sap_templates', apply_fn)
        self.assertIn('strict=True', _function_source(src, 'import_sap_templates') or '')
        self.assertNotIn('configure_nbxsync_zerotouch', apply_fn)
        self.assertIn(CANARY_HOST, apply_fn)
        self.assertIn('SyncHostJob', apply_fn)
        self.assertIn("name__iexact=_sap.CANARY_HOST", apply_fn)
        assign_fn = _function_source(src, '_step_sap_nbxsync') or ''
        for role in SAP_ROLES:
            self.assertIn(role, assign_fn)
        self.assertIn('HostInterfaceRequirementChoices.SNMP', assign_fn)


if __name__ == '__main__':
    unittest.main()
