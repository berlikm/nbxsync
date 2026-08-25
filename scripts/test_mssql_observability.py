#!/usr/bin/env python3
"""Contract tests for MSSQL Observability (fixtures + YAML, no live SQL)."""

from __future__ import annotations

import json
import re
import unittest

from mssql_observability import (
    FIXTURES,
    LLD_JS,
    PLUGIN_PROTOTYPE_PREFIXES,
    STOCK_MSSQL_TEMPLATE,
    TEMPLATE_NAME,
    TEMPLATE_YAML,
    URI_PREFIX,
    WMI_KEY,
    javascript_steps,
    lld_js_source,
    load_template,
    named_instances_from_wmi,
    run_lld_js,
    template_block,
    zerotouch_source,
)

MSSQL10_INSTANCES = ('PAPDB01', 'PCONF02', 'PITDV02', 'PJIRA01', 'PWARE01')
URI_RE = re.compile(r'^sqlserver://localhost/[^:/]+$')


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding='utf-8')


def _lld_rows(name: str) -> list[dict]:
    raw = _fixture(name)
    js_out = json.loads(run_lld_js(raw))
    py_out = named_instances_from_wmi(raw)
    if js_out != py_out:
        raise AssertionError(f'JS/Python LLD mismatch for {name}: {js_out!r} vs {py_out!r}')
    return js_out


class LldNamedInstanceTests(unittest.TestCase):
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


class YamlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = load_template()
        cls.tpl = template_block(cls.doc)
        cls.text = TEMPLATE_YAML.read_text(encoding='utf-8')

    def test_export_is_zabbix_70_databases_group(self):
        export = self.doc['zabbix_export']
        self.assertEqual(str(export['version']), '7.0')
        groups = export['template_groups']
        self.assertEqual(groups[0]['uuid'], '748ad4d098d447d492bb935c907f652f')
        self.assertEqual(groups[0]['name'], 'Templates/Databases')
        self.assertEqual(self.tpl['template'], TEMPLATE_NAME)
        self.assertEqual(self.tpl['name'], TEMPLATE_NAME)
        self.assertEqual(self.tpl['groups'], [{'name': 'Templates/Databases'}])

    def test_does_not_nest_stock_or_ship_dashboards_or_hosts(self):
        self.assertNotIn('templates', self.tpl)
        self.assertNotIn('dashboards', self.tpl)
        self.assertNotIn('graphs', self.tpl)
        self.assertNotIn('graph_prototypes', self.tpl)
        self.assertNotIn('httptests', self.tpl)
        self.assertNotIn('host_prototypes', self.tpl)
        self.assertNotIn('graphprototype', self.text)
        self.assertNotIn(STOCK_MSSQL_TEMPLATE, json.dumps(self.tpl.get('templates')))

    def test_does_not_reuse_windows_service_discovery_or_tcp_disaster(self):
        keys = [item['key'] for item in self.tpl['items']]
        keys.append(self.tpl['discovery_rules'][0]['key'])
        keys.extend(p['key'] for p in self.tpl['discovery_rules'][0]['item_prototypes'])
        self.assertNotIn('service.discovery', keys)
        self.assertFalse(any('service.discovery' in k for k in keys))
        self.assertFalse(any('net.tcp.service' in k for k in keys))
        dumped = json.dumps(self.tpl)
        self.assertNotIn('"priority": "DISASTER"', dumped.replace("'", '"'))
        priorities = []
        for item in self.tpl['items']:
            for trig in item.get('triggers') or []:
                priorities.append(trig.get('priority'))
        for proto in self.tpl['discovery_rules'][0]['item_prototypes']:
            for trig in proto.get('trigger_prototypes') or []:
                priorities.append(trig.get('priority'))
                self.assertNotIn('net.tcp.service', trig.get('expression', ''))
        self.assertTrue(priorities)
        self.assertNotIn('DISASTER', priorities)
        self.assertNotIn('host_prototypes', self.tpl)

    def test_wmi_master_key_has_no_dollar_and_is_shared(self):
        items = {item['key']: item for item in self.tpl['items']}
        self.assertIn(WMI_KEY, items)
        self.assertNotIn('$', WMI_KEY)
        self.assertIn("LIKE 'MSSQL%'", WMI_KEY)
        census = items['mssql.observability.instance.count']
        self.assertEqual(census['type'], 'DEPENDENT')
        self.assertEqual(census['master_item']['key'], WMI_KEY)
        rule = self.tpl['discovery_rules'][0]
        self.assertEqual(rule['type'], 'DEPENDENT')
        self.assertEqual(rule['master_item']['key'], WMI_KEY)
        self.assertEqual(rule['key'], 'mssql.named.instance.discovery')

    def test_yaml_js_matches_source_file(self):
        want = lld_js_source()
        self.assertTrue(LLD_JS.is_file())
        census = next(i for i in self.tpl['items'] if i['key'] == 'mssql.observability.instance.count')
        rule = self.tpl['discovery_rules'][0]
        scripts = javascript_steps(census) + javascript_steps(rule)
        self.assertEqual(scripts, [want, want])
        yaml_js = run_lld_js(_fixture('wmi_mssql10.json'), script=scripts[0])
        file_js = run_lld_js(_fixture('wmi_mssql10.json'))
        self.assertEqual(json.loads(yaml_js), json.loads(file_js))

    def test_lld_filters_and_min_default_zero(self):
        macros = {m['macro']: m for m in self.tpl['macros']}
        self.assertEqual(macros['{$MSSQL.INSTANCE.MATCHES}']['value'], '.*')
        self.assertEqual(macros['{$MSSQL.INSTANCE.NOT_MATCHES}']['value'], 'CHANGE_IF_NEEDED')
        self.assertEqual(str(macros['{$MSSQL.INSTANCE.DISCOVERY.MIN}']['value']), '0')
        self.assertNotIn('{$MSSQL.URI}', macros)
        self.assertNotIn('{$MSSQL.USER}', macros)
        self.assertNotIn('{$MSSQL.PASSWORD}', macros)
        self.assertNotIn('{$MSSQL.DSN}', macros)
        filt = self.tpl['discovery_rules'][0]['filter']
        self.assertEqual(str(filt['evaltype']).upper(), 'AND')
        self.assertEqual({c['macro'] for c in filt['conditions']}, {'{#MSSQL.INSTANCE}'})
        macros_used = [c['value'] for c in filt['conditions']]
        self.assertEqual(
            set(macros_used),
            {'{$MSSQL.INSTANCE.MATCHES}', '{$MSSQL.INSTANCE.NOT_MATCHES}'},
        )
        operators = {c.get('operator') for c in filt['conditions']}
        self.assertIn('NOT_MATCHES_REGEX', operators)

    def test_plugin_prototypes_use_lld_uri_not_stock_macro(self):
        protos = self.tpl['discovery_rules'][0]['item_prototypes']
        keys = [p['key'] for p in protos]
        for prefix in PLUGIN_PROTOTYPE_PREFIXES:
            match = [k for k in keys if k.startswith(prefix)]
            self.assertEqual(len(match), 1, prefix)
            key = match[0]
            self.assertIn('{#MSSQL.URI}', key)
            self.assertNotIn('{$MSSQL.URI}', key)
            self.assertIn('{$MSSQL.USER}', key)
            self.assertIn('{$MSSQL.PASSWORD}', key)
        db_count = next(p for p in protos if p['key'].startswith('mssql.observability.db.count'))
        self.assertEqual(db_count['type'], 'DEPENDENT')
        self.assertIn('{#MSSQL.URI}', db_count['master_item']['key'])
        self.assertEqual(db_count['preprocessing'][0]['parameters'][0], '$.length()')
        for proto in protos:
            tags = {t['tag']: t['value'] for t in proto.get('tags') or []}
            self.assertEqual(tags.get('sql_instance'), '{#MSSQL.INSTANCE}')

    def test_version_nodata_is_average_and_census_requires_min(self):
        version = next(
            p
            for p in self.tpl['discovery_rules'][0]['item_prototypes']
            if p['key'].startswith('mssql.version[')
        )
        trig = version['trigger_prototypes'][0]
        self.assertEqual(trig['priority'], 'AVERAGE')
        self.assertIn('nodata(', trig['expression'])
        self.assertIn('{#MSSQL.URI}', trig['expression'])
        self.assertNotIn('net.tcp.service', trig['expression'])
        census = next(i for i in self.tpl['items'] if i['key'] == 'mssql.observability.instance.count')
        ctrig = census['triggers'][0]
        self.assertEqual(ctrig['priority'], 'AVERAGE')
        self.assertIn('{$MSSQL.INSTANCE.DISCOVERY.MIN}>0', ctrig['expression'])
        self.assertIn('mssql.observability.instance.count', ctrig['expression'])

    def test_db_get_sample_length_matches_jsonpath_contract(self):
        rows = json.loads(_fixture('db_get_sample.json'))
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[-1]['dbname'], 'ASP')


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
        self.assertNotIn('import_yaml_templates', src)
        self.assertIn("'{$MSSQL.URI}', 'sqlserver://localhost:1433', 'MSSQL'", src)
        self.assertIn("'{$MSSQL.URI}', 'sqlserver://localhost:1433', 'MSSQL Query Server'", src)


if __name__ == '__main__':
    unittest.main()
