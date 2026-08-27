#!/usr/bin/env python3
"""YAML + helper contract for MSSQL Observability (no Django, no Zabbix)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

import yaml

from mssql_observability import (
    BACKUP_FULL_KEY,
    BACKUP_KEY,
    BUFFER_CACHE_KEY,
    CENSUS_KEY,
    CENSUS_TRIGGER_EXPR,
    CENSUS_TRIGGER_NAME,
    DB_CATALOG_KEY,
    DB_KEY,
    DB_LLD_KEY,
    DB_LLDJSON_KEY,
    DB_STATE_KEY,
    DISCOVERY_KEY,
    flatten_lld_catalogs,
    LOCAL_LLD_KEY,
    LOCAL_STATE_KEY,
    LOCAL_SYNC_KEY,
    MACRO_BACKUP_FULL_USED,
    MACRO_BACKUP_LOG_USED,
    MACRO_DBNAME_NOT_MATCHES,
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
    URI_PREFIX,
    VERSION_KEY,
    VERSION_NODATA_EXPR,
    VERSION_NODATA_NAME,
    WMI_ITEM_KEY,
    WMI_LLD_JS,
    ZABBIX_TEMPLATE_PATH,
    db_catalog_js_source,
    flatten_lld_js_source,
    local_db_catalog_js_source,
    named_instances_from_wmi,
    run_javascript,
    run_lld_js,
    zerotouch_source,
)
from mssql_observability import FIXTURES as TEMPLATE_FIXTURES

MSSQL10_INSTANCES = ('PAPDB01', 'PCONF02', 'PITDV02', 'PJIRA01', 'PWARE01')
URI_RE = re.compile(r'^sqlserver://localhost/[^:/]+$')

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / 'zabbix' / 'templates' / 'mssql_observability' / 'build_template.py'


def _fixture(name: str) -> str:
    return (TEMPLATE_FIXTURES / name).read_text(encoding='utf-8')


def _lld_rows(name: str) -> list[dict]:
    raw = _fixture(name)
    js_out = json.loads(run_lld_js(raw))
    py_out = named_instances_from_wmi(raw)
    if js_out != py_out:
        raise AssertionError(f'JS/Python LLD mismatch for {name}: {js_out!r} vs {py_out!r}')
    return js_out


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

    def test_preserves_deployed_template_and_instance_lld_identities(self):
        self.assertEqual(TEMPLATE_UUID, '52bd809ec8a54feb8364f3d13a9c8074')
        self.assertEqual(DISCOVERY_KEY, 'mssql.named.instance.discovery')

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
        self.assertIn("Name LIKE 'MSSQL%'", WMI_ITEM_KEY)
        self.assertNotIn("Name LIKE 'MSSQL$%'", WMI_ITEM_KEY)
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
        buffer = next(t for t in self.triggers if 'Buffer cache' in t['name'])
        page = next(t for t in self.triggers if 'Page life' in t['name'])
        self.assertEqual(buffer['priority'], 'WARNING')
        self.assertEqual(page['priority'], 'WARNING')
        self.assertNotEqual(buffer['priority'], 'HIGH')
        self.assertNotEqual(page['priority'], 'HIGH')

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
        pages = self.tpl['dashboards'][0]['pages']
        self.assertEqual([p['name'] for p in pages], ['Overview', 'Databases'])
        overview = pages[0]
        names = [w['name'] for w in overview['widgets']]
        self.assertEqual(names, ['Named instances', 'Problems', 'Ping'])
        ping = overview['widgets'][2]
        self.assertEqual(ping['type'], 'honeycomb')
        db_page = pages[1]
        self.assertEqual([w['name'] for w in db_page['widgets']], ['Database state', 'AG local DB sync'])

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
            self.assertEqual(parsed.version, 4, value)
            self.assertEqual(parsed.variant, uuid.RFC_4122, value)

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

    def test_flattened_database_discovery_does_not_nest(self):
        rules = self.tpl['discovery_rules']
        self.assertEqual(
            [row['key'] for row in rules],
            [DISCOVERY_KEY, DB_LLD_KEY, LOCAL_LLD_KEY],
        )
        self.assertTrue(all(row['type'] == 'DEPENDENT' for row in rules))
        self.assertNotIn('discovery_prototypes', self.text)
        self.assertIn('last_foreach(//mssql.observability.db.catalog[*])', self.text)
        self.assertIn(DB_LLDJSON_KEY, self.keys)
        self.assertIn(DB_CATALOG_KEY, self.keys)
        self.assertIn('{#MSSQL.INSTANCE}', DB_CATALOG_KEY)
        self.assertIn('{#DBNAME}', DB_STATE_KEY)
        self.assertIn('{#MSSQL.INSTANCE}', DB_STATE_KEY)
        self.assertIn(DB_STATE_KEY, self.keys)
        self.assertNotIn('key: mssql.db.state["{#DBNAME}"]', self.text)
        self.assertIn("'{#' + 'MSSQL.INSTANCE}'", self.text)
        self.assertIn("'{#' + 'DBNAME}'", self.text)

    def test_named_instance_db_and_ag_tags(self):
        self.assertIn('tag: database', self.text)
        self.assertIn("value: '{#DBNAME}'", self.text)
        self.assertIn('tag: local-db', self.text)
        self.assertIn('tag: availability-group', self.text)
        self.assertIn(LOCAL_STATE_KEY, self.keys)
        self.assertIn(LOCAL_SYNC_KEY, self.keys)
        self.assertIn(BACKUP_FULL_KEY, self.keys)

    def test_backup_used_defaults_on_for_every_environment(self):
        self.assertEqual(TEMPLATE_MACROS[MACRO_BACKUP_FULL_USED], '1')
        self.assertEqual(TEMPLATE_MACROS[MACRO_BACKUP_LOG_USED], '1')
        self.assertEqual(TEMPLATE_MACROS[MACRO_DBNAME_NOT_MATCHES], 'master|tempdb|model|msdb')
        self.assertNotIn('{% ', self.text)
        self.assertNotIn('-t-', self.text)
        self.assertNotIn('-d-', self.text)
        self.assertNotIn('HYGIENE', self.text)
        self.assertNotIn('PRODUCTION_ONE', self.text)
        self.assertIn('{$MSSQL.BACKUP_FULL.USED:"{#DBNAME}"}=1', self.text)

    def test_flatten_merges_same_dbname_on_two_instances(self):
        import json

        catalogs = json.dumps(
            [
                json.dumps(
                    [
                        {
                            '{#MSSQL.INSTANCE}': 'PITDV02',
                            '{#DBNAME}': 'HADB',
                            '{#MSSQL.URI}': 'sqlserver://localhost/PITDV02',
                        }
                    ]
                ),
                json.dumps(
                    [
                        {
                            '{#MSSQL.INSTANCE}': 'PCONF02',
                            '{#DBNAME}': 'HADB',
                            '{#MSSQL.URI}': 'sqlserver://localhost/PCONF02',
                        }
                    ]
                ),
                '[]',
            ]
        )
        rows = json.loads(flatten_lld_catalogs(catalogs))
        self.assertEqual(
            [(row['{#MSSQL.INSTANCE}'], row['{#DBNAME}']) for row in rows],
            [('PITDV02', 'HADB'), ('PCONF02', 'HADB')],
        )

    def test_version_delay_fits_nodata_window(self):
        version = next(
            item for item in self.tpl['discovery_rules'][0]['item_prototypes'] if item['key'] == VERSION_KEY
        )
        self.assertEqual(version['delay'], '5m')
        ping = next(item for item in self.tpl['discovery_rules'][0]['item_prototypes'] if item['key'] == PING_KEY)
        steps = ping.get('preprocessing') or []
        self.assertEqual(steps[0]['type'], 'CHECK_NOT_SUPPORTED')
        self.assertEqual(steps[0]['error_handler_params'], '0')
        db_raw = next(
            item for item in self.tpl['discovery_rules'][0]['item_prototypes'] if item['key'] == DB_KEY
        )
        backup_raw = next(
            item
            for item in self.tpl['discovery_rules'][0]['item_prototypes']
            if item['key'] == BACKUP_KEY
        )
        self.assertEqual(db_raw['history'], '7d')
        self.assertEqual(backup_raw['history'], '7d')


class LldNamedInstanceFixtureTests(unittest.TestCase):
    def test_default_only_host_is_empty(self):
        rows = _lld_rows('wmi_msql01.json')
        self.assertEqual(rows, [])

    def test_mssql10_discovers_five_named_uris_without_port(self):
        rows = _lld_rows('wmi_mssql10.json')
        instances = tuple(sorted(r['{#MSSQL.INSTANCE}'] for r in rows))
        self.assertEqual(instances, MSSQL10_INSTANCES)
        uris = {r['{#MSSQL.URI}'] for r in rows}
        self.assertEqual(uris, {URI_PREFIX + name for name in MSSQL10_INSTANCES})
        for row in rows:
            self.assertRegex(row['{#MSSQL.URI}'], URI_RE)
            self.assertTrue(row['{#MSSQL.SERVICE}'].startswith('MSSQL$'))
            self.assertNotIn(':', row['{#MSSQL.URI}'].split('localhost', 1)[1])
            self.assertEqual(
                row['{#MSSQL.URI}'],
                'sqlserver://localhost/' + row['{#MSSQL.INSTANCE}'],
            )

    def test_rejects_fdlauncher_sqlagent_and_browser(self):
        rows = _lld_rows('wmi_mssql10.json')
        names = {r['{#MSSQL.SERVICE}'] for r in rows}
        self.assertNotIn('MSSQLSERVER', names)
        self.assertNotIn('SQLBrowser', names)
        self.assertNotIn('SQLSERVERAGENT', names)
        self.assertNotIn('SQLAgent$PITDV02', names)
        self.assertNotIn('MSSQLFDLauncher', names)
        self.assertNotIn('MSSQLFDLauncher$PITDV02', names)
        self.assertNotIn('SQLTELEMETRY$PITDV02', names)
        self.assertNotIn('SQLWriter', names)
        self.assertEqual(_lld_rows('wmi_fdlauncher_only.json'), [])

    def test_single_wmi_object_is_treated_as_one_row(self):
        rows = _lld_rows('wmi_single_named_object.json')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['{#MSSQL.INSTANCE}'], 'SQLEXPRESS')
        self.assertEqual(rows[0]['{#MSSQL.URI}'], 'sqlserver://localhost/SQLEXPRESS')

    def test_empty_array_and_null_are_empty(self):
        self.assertEqual(json.loads(run_lld_js('[]')), [])
        self.assertEqual(json.loads(run_lld_js('null')), [])

    def test_empty_instance_suffix_is_dropped(self):
        raw = json.dumps([{'Name': 'MSSQL$', 'DisplayName': 'bogus'}])
        self.assertEqual(json.loads(run_lld_js(raw)), [])

    def test_invalid_json_is_unsupported_not_silent_empty(self):
        with self.assertRaises(RuntimeError):
            run_lld_js('not-json')
        with self.assertRaises(ValueError):
            named_instances_from_wmi('not-json')

    def test_uri_never_includes_a_port(self):
        rows = _lld_rows('wmi_mssql10.json')
        dumped = json.dumps(rows)
        self.assertNotIn('1433', dumped)
        self.assertNotIn('localhost:', dumped)

    def test_yaml_js_matches_source_file(self):
        from mssql_observability import javascript_steps, load_template, template_block

        tpl = template_block(load_template())
        wmi = next(i for i in tpl['items'] if i['key'] == WMI_ITEM_KEY)
        scripts = javascript_steps(wmi)
        self.assertEqual(scripts, [WMI_LLD_JS])
        self.assertEqual(
            json.loads(run_lld_js(_fixture('wmi_mssql10.json'), script=scripts[0])),
            json.loads(run_lld_js(_fixture('wmi_mssql10.json'))),
        )


class DatabaseCatalogFixtureTests(unittest.TestCase):
    def test_db_get_sample_stamps_instance_and_dbname(self):
        actual = json.loads(
            run_javascript(
                _fixture('db_get_sample.json'),
                script=db_catalog_js_source(instance='PITDV02', uri='sqlserver://localhost/PITDV02'),
            )
        )
        names = [row['{#DBNAME}'] for row in actual]
        self.assertEqual(names, ['master', 'tempdb', 'model', 'msdb', 'ASP'])
        self.assertTrue(all(row['{#MSSQL.INSTANCE}'] == 'PITDV02' for row in actual))
        asp = next(row for row in actual if row['{#DBNAME}'] == 'ASP')
        self.assertEqual(asp['{#RECOVERY_MODEL}'], '1')
        self.assertEqual(asp['{#MSSQL.URI}'], 'sqlserver://localhost/PITDV02')

    def test_local_db_catalog_requires_group_and_dbname(self):
        raw = json.dumps(
            [
                {'dbname': 'HADB', 'group_name': 'CH-STA-T-AOHA25'},
                {'dbname': 'orphan'},
                {'group_name': 'missing-db'},
            ]
        )
        actual = json.loads(
            run_javascript(
                raw,
                script=local_db_catalog_js_source(
                    instance='PITDV02', uri='sqlserver://localhost/PITDV02'
                ),
            )
        )
        self.assertEqual(len(actual), 1)
        self.assertEqual(actual[0]['{#DBNAME}'], 'HADB')
        self.assertEqual(actual[0]['{#GROUP_NAME}'], 'CH-STA-T-AOHA25')

    def test_flatten_js_matches_python_helper(self):
        catalogs = json.dumps(
            [
                json.dumps(
                    [
                        {
                            '{#MSSQL.INSTANCE}': 'PITDV02',
                            '{#DBNAME}': 'HADB',
                        }
                    ]
                ),
                json.dumps(
                    [
                        {
                            '{#MSSQL.INSTANCE}': 'PCONF02',
                            '{#DBNAME}': 'HADB',
                        }
                    ]
                ),
                '[]',
            ]
        )
        js_rows = json.loads(run_javascript(catalogs, script=flatten_lld_js_source()))
        py_rows = json.loads(flatten_lld_catalogs(catalogs))
        self.assertEqual(js_rows, py_rows)


class ZerotouchSoftAssignTests(unittest.TestCase):
    def test_observability_is_optional_and_not_imported_by_zerotouch(self):
        src = zerotouch_source()
        self.assertIn("'mssql_observability': 'MSSQL Observability'", src)
        optional = re.search(r'OPTIONAL_TPL_KEYS = frozenset\(\{([^}]+)\}\)', src, re.S)
        self.assertIsNotNone(optional)
        self.assertIn("'mssql_observability'", optional.group(1))
        self.assertIn("('mssql_observability', 'MSSQL')", src)
        self.assertIn("('mssql_observability', 'MSSQL Query Server')", src)
        self.assertNotIn('template_mssql_observability.yaml', src)
        self.assertNotIn('apply-mssql', src)
        self.assertIn("'{$MSSQL.URI}', 'sqlserver://localhost:1433', 'MSSQL'", src)
        self.assertIn("'{$MSSQL.URI}', 'sqlserver://localhost:1433', 'MSSQL Query Server'", src)


if __name__ == '__main__':
    unittest.main()
