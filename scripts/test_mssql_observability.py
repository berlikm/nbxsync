#!/usr/bin/env python3
"""YAML + helper contract for MSSQL Observability (no Django, no Zabbix)."""

from __future__ import annotations

import subprocess
import sys
import unittest
import uuid
from pathlib import Path

import yaml

from mssql_observability import (
    BUFFER_CACHE_KEY,
    CENSUS_KEY,
    CENSUS_TRIGGER_EXPR,
    CENSUS_TRIGGER_NAME,
    DISCOVERY_KEY,
    MACRO_INSTANCE_DISCOVERY_MIN,
    NAMED_URI,
    PAGE_LIFE_KEY,
    PING_KEY,
    PING_TRIGGER_EXPR,
    PING_TRIGGER_NAME,
    ROLE_NAMES,
    STOCK_TEMPLATE_NAME,
    TEMPLATE_FILES,
    TEMPLATE_GROUP,
    TEMPLATE_GROUP_UUID,
    TEMPLATE_MACROS,
    TEMPLATE_NAME,
    TEMPLATE_UUID,
    VERSION_KEY,
    VERSION_NODATA_EXPR,
    VERSION_NODATA_NAME,
    WMI_ITEM_KEY,
    WMI_LLD_JS,
    ZABBIX_TEMPLATE_PATH,
)

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / 'zabbix' / 'templates' / 'mssql_observability' / 'build_template.py'


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def _template() -> dict:
    return _load(ZABBIX_TEMPLATE_PATH)['zabbix_export']['templates'][0]


def _walk(node, visitor) -> None:
    if isinstance(node, dict):
        visitor(node)
        for value in node.values():
            _walk(value, visitor)
    elif isinstance(node, list):
        for item in node:
            _walk(item, visitor)


def _collect_triggers(doc: dict) -> list[dict]:
    found: list[dict] = []

    def visit(node: dict) -> None:
        if 'expression' in node and 'priority' in node and 'name' in node:
            found.append(node)

    _walk(doc, visit)
    return found


def _collect_keys(doc: dict) -> list[str]:
    keys: list[str] = []

    def visit(node: dict) -> None:
        if 'key' in node and 'name' in node:
            keys.append(str(node['key']))

    _walk(doc, visit)
    return keys


class MssqlObservabilityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc = _load(ZABBIX_TEMPLATE_PATH)
        cls.tpl = _template()
        cls.text = ZABBIX_TEMPLATE_PATH.read_text(encoding='utf-8')
        cls.triggers = _collect_triggers(cls.tpl)
        cls.keys = _collect_keys(cls.tpl)

    def test_export_version_and_official_group(self):
        self.assertEqual(self.doc['zabbix_export']['version'], '7.0')
        groups = self.doc['zabbix_export']['template_groups']
        self.assertEqual(groups[0]['uuid'], TEMPLATE_GROUP_UUID)
        self.assertEqual(groups[0]['name'], TEMPLATE_GROUP)
        self.assertEqual(self.tpl['groups'][0]['name'], TEMPLATE_GROUP)

    def test_name_has_no_slash(self):
        self.assertEqual(TEMPLATE_NAME, 'MSSQL Observability')
        self.assertNotIn('/', TEMPLATE_NAME)
        self.assertEqual(self.tpl['name'], TEMPLATE_NAME)
        self.assertEqual(self.tpl['uuid'], TEMPLATE_UUID)

    def test_does_not_nest_stock_or_icmp(self):
        self.assertFalse(self.tpl.get('templates'))
        nested = [row.get('name') for row in (self.tpl.get('templates') or [])]
        self.assertNotIn(STOCK_TEMPLATE_NAME, nested)
        self.assertNotIn('ICMP Ping', nested)

    def test_no_service_discovery_or_icmpping(self):
        self.assertNotIn('service.discovery', self.keys)
        self.assertNotIn('icmpping', self.keys)
        self.assertTrue(all('net.tcp.service' not in key for key in self.keys))
        self.assertNotIn('Plugins.MSSQL.Sessions', self.text)
        self.assertNotIn('service.discovery', self.text)

    def test_wmi_key_is_unique_named_instances_only(self):
        self.assertIn(WMI_ITEM_KEY, self.keys)
        self.assertIn("Name LIKE 'MSSQL$%'", WMI_ITEM_KEY)
        self.assertNotIn('MSSQLSERVER', WMI_ITEM_KEY)
        self.assertEqual(self.tpl['discovery_rules'][0]['key'], DISCOVERY_KEY)
        self.assertEqual(self.tpl['discovery_rules'][0]['type'], 'DEPENDENT')
        self.assertEqual(self.tpl['discovery_rules'][0]['master_item']['key'], WMI_ITEM_KEY)

    def test_lld_js_builds_named_uri_without_port(self):
        self.assertIn('sqlserver://localhost/', WMI_LLD_JS)
        self.assertIn('+ instance', WMI_LLD_JS)
        self.assertNotIn(':1433', WMI_LLD_JS)
        self.assertIn(NAMED_URI, self.text)
        self.assertNotRegex(self.text, r'sqlserver://localhost:\d+/')

    def test_plugin_prototypes_use_lld_uri_not_stock_macro(self):
        for key in (PING_KEY, VERSION_KEY):
            self.assertIn(key, self.keys)
            self.assertIn('{#MSSQL.URI}', key)
            self.assertNotIn('{$MSSQL.URI}', key)

    def test_dependent_keys_include_instance(self):
        for key in (BUFFER_CACHE_KEY, PAGE_LIFE_KEY):
            self.assertIn('{#MSSQL.INSTANCE}', key)
            self.assertIn(key, self.keys)
        self.assertNotIn('mssql.buffer_cache_hit_ratio\n', self.text)
        self.assertNotIn('key: mssql.page_life_expectancy\n', self.text)

    def test_no_stock_secret_macros_on_companion(self):
        macros = {row['macro'] for row in self.tpl['macros']}
        self.assertEqual(set(TEMPLATE_MACROS), macros)
        self.assertNotIn('{$MSSQL.URI}', macros)
        self.assertNotIn('{$MSSQL.USER}', macros)
        self.assertNotIn('{$MSSQL.PASSWORD}', macros)
        self.assertEqual(TEMPLATE_MACROS[MACRO_INSTANCE_DISCOVERY_MIN], '0')

    def test_no_disaster_and_no_tcp_1433_clone(self):
        for trigger in self.triggers:
            self.assertNotEqual(trigger['priority'], 'DISASTER', trigger.get('name'))
            self.assertNotIn('net.tcp.service', trigger['expression'])

    def test_ping_average_version_nodata_depends(self):
        ping = next(t for t in self.triggers if t['name'] == PING_TRIGGER_NAME)
        version = next(t for t in self.triggers if t['name'] == VERSION_NODATA_NAME)
        self.assertEqual(ping['priority'], 'AVERAGE')
        self.assertEqual(ping['expression'], PING_TRIGGER_EXPR)
        self.assertEqual(version['priority'], 'AVERAGE')
        self.assertEqual(version['expression'], VERSION_NODATA_EXPR)
        deps = version.get('dependencies') or []
        self.assertEqual(deps[0]['name'], PING_TRIGGER_NAME)
        self.assertEqual(deps[0]['expression'], PING_TRIGGER_EXPR)

    def test_buffer_and_page_life_are_warning_only(self):
        from mssql_observability import MACRO_HYGIENE_CONTROL

        buffer = next(t for t in self.triggers if 'Buffer cache' in t['name'])
        page = next(t for t in self.triggers if 'Page life' in t['name'])
        self.assertEqual(buffer['priority'], 'WARNING')
        self.assertEqual(page['priority'], 'WARNING')
        self.assertIn(f'{MACRO_HYGIENE_CONTROL}=1', buffer['expression'])
        self.assertIn(f'{MACRO_HYGIENE_CONTROL}=1', page['expression'])

    def test_nonprod_backup_and_hygiene_are_jinja_gated(self):
        from mssql_observability import (
            BACKUP_USED_MACROS,
            PRODUCTION_ONE_ELSE_ZERO_JINJA,
            ROLE_ENV_MACROS,
            MACRO_HYGIENE_CONTROL,
        )

        self.assertIn('-p-', PRODUCTION_ONE_ELSE_ZERO_JINJA)
        self.assertIn('{%- else -%}0', PRODUCTION_ONE_ELSE_ZERO_JINJA)
        for macro in BACKUP_USED_MACROS:
            self.assertEqual(ROLE_ENV_MACROS[macro], PRODUCTION_ONE_ELSE_ZERO_JINJA)
            self.assertNotIn(macro, {row['macro'] for row in self.tpl['macros']})
        self.assertEqual(ROLE_ENV_MACROS[MACRO_HYGIENE_CONTROL], PRODUCTION_ONE_ELSE_ZERO_JINJA)
        self.assertIn(MACRO_HYGIENE_CONTROL, {row['macro'] for row in self.tpl['macros']})
        ping = next(t for t in self.triggers if t['name'] == PING_TRIGGER_NAME)
        self.assertNotIn(MACRO_HYGIENE_CONTROL, ping['expression'])

    def test_census_gated_on_min(self):
        census = next(t for t in self.triggers if t['name'] == CENSUS_TRIGGER_NAME)
        self.assertEqual(census['priority'], 'AVERAGE')
        self.assertEqual(census['expression'], CENSUS_TRIGGER_EXPR)
        self.assertIn(f'{MACRO_INSTANCE_DISCOVERY_MIN}>0', census['expression'])
        self.assertIn(CENSUS_KEY, self.keys)

    def test_wmi_maps_not_supported_to_empty_lld(self):
        self.assertIn('CHECK_NOT_SUPPORTED', self.text)
        self.assertIn("error_handler_params: '[]'", self.text)
        self.assertIn('{#MSSQL.SERVICE}', WMI_LLD_JS)
        self.assertIn('{#MSSQL.INSTANCE}', WMI_LLD_JS)
        self.assertIn('{#MSSQL.URI}', WMI_LLD_JS)
        self.assertIn('{#MSSQL.DISPLAY}', WMI_LLD_JS)

    def test_health_honeycomb(self):
        boards = [d['name'] for d in self.tpl['dashboards']]
        self.assertEqual(boards, ['Health'])
        overview = self.tpl['dashboards'][0]['pages'][0]
        self.assertEqual(overview['name'], 'Overview')
        names = [w['name'] for w in overview['widgets']]
        self.assertEqual(names, ['Named instances', 'Problems', 'Ping'])
        ping = overview['widgets'][2]
        self.assertEqual(ping['type'], 'honeycomb')

    def test_no_graph_prototypes(self):
        self.assertNotIn('graph_prototypes', self.text)
        self.assertNotIn('type: GRAPH_PROTOTYPE', self.text)

    def test_uuids_unique_and_valid(self):
        found: list[str] = []

        def visit(node: dict) -> None:
            if 'uuid' in node:
                found.append(str(node['uuid']))

        _walk(self.doc, visit)
        self.assertGreater(len(found), 15)
        self.assertEqual(len(found), len(set(found)))
        for value in found:
            parsed = uuid.UUID(hex=value)
            self.assertIn(parsed.version, (4, 5), value)

    def test_roles_keep_stock(self):
        self.assertEqual(ROLE_NAMES, ('MSSQL', 'MSSQL Query Server'))
        from mssql_observability import KEEP_TEMPLATES_ON_ROLE

        self.assertEqual(KEEP_TEMPLATES_ON_ROLE, (STOCK_TEMPLATE_NAME, TEMPLATE_NAME))

    def test_template_files_exist(self):
        self.assertEqual(list(TEMPLATE_FILES), [TEMPLATE_NAME])
        self.assertTrue(ZABBIX_TEMPLATE_PATH.is_file())

    def test_builder_is_deterministic(self):
        first = ZABBIX_TEMPLATE_PATH.read_text(encoding='utf-8')
        subprocess.check_call([sys.executable, str(BUILDER)], cwd=str(ROOT))
        second = ZABBIX_TEMPLATE_PATH.read_text(encoding='utf-8')
        self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()
