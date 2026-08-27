#!/usr/bin/env python3
"""YAML + helper contract for FortiManager / FortiAnalyzer SNMP (no Django, no Zabbix)."""

from __future__ import annotations

import re
import unittest
import uuid
from pathlib import Path

import yaml

from fmg_faz_snmp import (
    FAZ_TEMPLATE_RULE,
    FMG_FAZ_COLLIDING_TEMPLATES,
    FMG_FAZ_PARENT_MACROS,
    FMG_FAZ_SNMP_TEMPLATE,
    FMG_FAZ_SNMP_YAML,
    FMG_TEMPLATE_RULE,
    FORTIANALYZER_OBSERVABILITY_TEMPLATE,
    FORTIANALYZER_OBSERVABILITY_YAML,
    FORTIANALYZER_TEMPLATE_MACROS,
    FORTIMANAGER_OBSERVABILITY_TEMPLATE,
    FORTIMANAGER_OBSERVABILITY_YAML,
    ICMP_PING_TEMPLATE,
    LEGACY_FMG_FAZ_TEMPLATE_RULE,
    NETWORK_GENERIC_TEMPLATE,
    PARENT_ICMP_EXPR,
    PARENT_ICMP_NAME,
    PARENT_SNMP_EXPR,
    PARENT_SNMP_NAME,
    TEMPLATE_FILES,
    fmg_faz_rule_specs,
    platform_is_fortianalyzer,
    platform_is_fortimanager,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def _template(path: Path) -> dict:
    return _load(path)['zabbix_export']['templates'][0]


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
        if 'key' in node and 'type' in node and 'name' in node:
            keys.append(str(node['key']))

    _walk(doc, visit)
    return keys


def _widget_names(dashboard: dict, page: str) -> list[str]:
    for pg in dashboard.get('pages') or []:
        if pg.get('name') == page:
            return [w.get('name') for w in pg.get('widgets') or []]
    return []


class FmgFazContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = _template(FMG_FAZ_SNMP_YAML)
        cls.fmg = _template(FORTIMANAGER_OBSERVABILITY_YAML)
        cls.faz = _template(FORTIANALYZER_OBSERVABILITY_YAML)
        cls.parent_triggers = _collect_triggers(cls.parent)
        cls.fmg_triggers = _collect_triggers(cls.fmg)
        cls.faz_triggers = _collect_triggers(cls.faz)

    def test_names_have_no_slash(self):
        self.assertEqual(FMG_FAZ_SNMP_TEMPLATE, 'Fortinet FMG-FAZ by SNMP')
        self.assertNotIn('/', FMG_FAZ_SNMP_TEMPLATE)
        self.assertEqual(self.parent['name'], FMG_FAZ_SNMP_TEMPLATE)
        self.assertEqual(self.fmg['name'], FORTIMANAGER_OBSERVABILITY_TEMPLATE)
        self.assertEqual(self.faz['name'], FORTIANALYZER_OBSERVABILITY_TEMPLATE)

    def test_companions_nest_parent_not_generic(self):
        for companion in (self.fmg, self.faz):
            nested = [row['name'] for row in companion.get('templates') or []]
            self.assertEqual(nested, [FMG_FAZ_SNMP_TEMPLATE])
            self.assertNotIn(NETWORK_GENERIC_TEMPLATE, nested)
            self.assertNotIn(ICMP_PING_TEMPLATE, nested)

    def test_icmpping_once_on_parent_never_on_companions(self):
        parent_keys = _collect_keys(self.parent)
        self.assertEqual(parent_keys.count('icmpping'), 1)
        for companion in (self.fmg, self.faz):
            self.assertNotIn('icmpping', _collect_keys(companion))

    def test_no_disaster_priority(self):
        for trigger in (*self.parent_triggers, *self.fmg_triggers, *self.faz_triggers):
            self.assertNotEqual(trigger['priority'], 'DISASTER', trigger.get('name'))

    def test_config_sync_trigger_is_disabled(self):
        matches = [
            t
            for t in self.parent_triggers
            if 'config is out of sync' in t['name']
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['status'], 'DISABLED')
        self.assertIn('{$FM.CONFIG.CONTROL}', matches[0]['expression'])

    def test_icmp_loss_and_rtt_are_disabled(self):
        names = {
            f'{FMG_FAZ_SNMP_TEMPLATE}: High ICMP ping loss',
            f'{FMG_FAZ_SNMP_TEMPLATE}: High ICMP ping response time',
        }
        found = [t for t in self.parent_triggers if t['name'] in names]
        self.assertEqual(len(found), 2)
        for trigger in found:
            self.assertEqual(trigger['status'], 'DISABLED')

    def test_cpu_crit_is_silenced(self):
        self.assertEqual(FMG_FAZ_PARENT_MACROS['{$CPU.UTIL.CRIT}'], '101')
        crit = [t for t in self.parent_triggers if t['name'].endswith('Critical CPU utilization')]
        self.assertEqual(len(crit), 1)
        self.assertEqual(crit[0]['status'], 'DISABLED')

    def test_icmp_high_snmp_warning(self):
        icmp = next(t for t in self.parent_triggers if t['name'] == PARENT_ICMP_NAME)
        snmp = next(t for t in self.parent_triggers if t['name'] == PARENT_SNMP_NAME)
        self.assertEqual(icmp['priority'], 'HIGH')
        self.assertEqual(icmp['expression'], PARENT_ICMP_EXPR)
        self.assertEqual(snmp['priority'], 'WARNING')
        self.assertEqual(snmp['expression'], PARENT_SNMP_EXPR)

    def test_health_overview_four_tiles(self):
        health = next(d for d in self.parent['dashboards'] if d['name'] == 'Health')
        names = _widget_names(health, 'Overview')
        self.assertEqual(names[:4], ['ICMP', 'SNMP', 'CPU', 'Uptime'])
        pages = [p['name'] for p in health['pages']]
        self.assertEqual(pages, ['Overview', 'Hardware', 'Cluster'])

    def test_network_interfaces_board(self):
        nets = next(d for d in self.parent['dashboards'] if d['name'] == 'Network interfaces')
        self.assertEqual([p['name'] for p in nets['pages']], ['Overview', 'Port'])

    def test_fmg_devices_board(self):
        boards = [d['name'] for d in self.fmg['dashboards']]
        self.assertEqual(boards, ['Devices'])

    def test_faz_logs_board_and_disk_high(self):
        boards = [d['name'] for d in self.faz['dashboards']]
        self.assertEqual(boards, ['Logs'])
        high = [t for t in self.faz_triggers if t['name'].endswith('Log disk is critically full')]
        self.assertEqual(len(high), 1)
        self.assertEqual(high[0]['priority'], 'HIGH')
        self.assertIn('{$DISK.UTIL.HIGH}', high[0]['expression'])
        self.assertEqual(FORTIANALYZER_TEMPLATE_MACROS['{$DISK.UTIL.HIGH}'], '95')

    def test_faz_triggers_depend_on_parent_health(self):
        for trigger in self.faz_triggers:
            deps = trigger.get('dependencies') or []
            names = {d['name'] for d in deps}
            exprs = {d['expression'] for d in deps}
            self.assertIn(PARENT_ICMP_NAME, names, trigger['name'])
            self.assertIn(PARENT_SNMP_NAME, names, trigger['name'])
            self.assertIn(PARENT_ICMP_EXPR, exprs)
            self.assertIn(PARENT_SNMP_EXPR, exprs)

    def test_uuidv4(self):
        found: list[str] = []

        def visit(node: dict) -> None:
            if 'uuid' in node:
                found.append(str(node['uuid']))

        for doc in (self.parent, self.fmg, self.faz):
            _walk(doc, visit)
        self.assertGreater(len(found), 20)
        for value in found:
            parsed = uuid.UUID(hex=value)
            self.assertEqual(parsed.version, 4, value)

    def test_optional_oids_map_not_supported(self):
        text = FMG_FAZ_SNMP_YAML.read_text(encoding='utf-8')
        self.assertIn('CHECK_NOT_SUPPORTED', text)
        self.assertIn('fm.raid.state', text)
        self.assertIn('fm.sensor.discovery', text)

    def test_managed_device_offline_is_average(self):
        matches = [
            t
            for t in self.parent_triggers
            if 'Managed device' in t['name'] and 'offline' in t['name']
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['priority'], 'AVERAGE')
        self.assertIn('{$FM.DEVICE.CONTROL}', matches[0]['expression'])

    def test_temp_critical_is_high_psu_average(self):
        temp = next(t for t in self.parent_triggers if 'is critical' in t['name'])
        psu = next(t for t in self.parent_triggers if t['name'].endswith('is failed'))
        self.assertEqual(temp['priority'], 'HIGH')
        self.assertEqual(psu['priority'], 'AVERAGE')

    def test_raid_unavailable_is_silent(self):
        raid = [t for t in self.parent_triggers if 'RAID array' in t['name']]
        self.assertTrue(raid)
        for trigger in raid:
            self.assertNotIn('=0', trigger['expression'])

    def test_watchers_present(self):
        names = {t['name'] for t in self.parent_triggers}
        self.assertIn(f'{FMG_FAZ_SNMP_TEMPLATE}: Too many unsupported items', names)
        self.assertIn(f'{FMG_FAZ_SNMP_TEMPLATE}: no ICMP data for 10m', names)
        self.assertIn(f'{FMG_FAZ_SNMP_TEMPLATE}: No discovered interfaces after SNMP is up', names)
        self.assertIn(f'{FMG_FAZ_SNMP_TEMPLATE}: Managed device count unexpected', names)

    def test_svggraph_time_period_is_string(self):
        periods: list[tuple[str, object]] = []

        def visit(node: dict) -> None:
            name = node.get('name')
            if name in {'time_period.from', 'time_period.to'}:
                periods.append((name, node.get('value')))

        _walk(self.parent, visit)
        _walk(self.faz, visit)
        self.assertTrue(periods)
        for name, value in periods:
            self.assertIsInstance(value, str, name)
            self.assertRegex(str(value), r'^now')

    def test_rule_specs_and_platforms(self):
        specs = fmg_faz_rule_specs()
        self.assertEqual(specs[0][0], FMG_TEMPLATE_RULE)
        self.assertEqual(specs[1][0], FAZ_TEMPLATE_RULE)
        self.assertEqual(LEGACY_FMG_FAZ_TEMPLATE_RULE, 'FortiAnalyzer/Manager')
        self.assertTrue(platform_is_fortimanager('FortiManager 7.4'))
        self.assertTrue(platform_is_fortianalyzer('FortiAnalyzer 7.2'))
        self.assertFalse(platform_is_fortimanager('FortiAnalyzer 7.2'))
        self.assertFalse(platform_is_fortianalyzer('FortiOS 7.4'))

    def test_colliding_templates_include_nested_parent(self):
        self.assertIn(NETWORK_GENERIC_TEMPLATE, FMG_FAZ_COLLIDING_TEMPLATES)
        self.assertIn(ICMP_PING_TEMPLATE, FMG_FAZ_COLLIDING_TEMPLATES)
        self.assertIn(FMG_FAZ_SNMP_TEMPLATE, FMG_FAZ_COLLIDING_TEMPLATES)
        self.assertIn('FortiGate by HTTP', FMG_FAZ_COLLIDING_TEMPLATES)

    def test_template_files_exist_in_import_order(self):
        names = list(TEMPLATE_FILES)
        self.assertEqual(
            names,
            [
                FMG_FAZ_SNMP_TEMPLATE,
                FORTIMANAGER_OBSERVABILITY_TEMPLATE,
                FORTIANALYZER_OBSERVABILITY_TEMPLATE,
            ],
        )
        for path in TEMPLATE_FILES.values():
            self.assertTrue(path.is_file(), path)
            self.assertTrue(str(path).startswith(str(ROOT)))

    def test_export_version_70(self):
        for path in TEMPLATE_FILES.values():
            doc = _load(path)
            self.assertEqual(doc['zabbix_export']['version'], '7.0')

    def test_calculated_params_and_macro_values_are_strings(self):
        for template in (self.parent, self.fmg, self.faz):
            fields: list[tuple[str, object]] = []

            def visit(node: dict) -> None:
                if 'params' in node:
                    fields.append(('params', node['params']))
                if 'macro' in node and 'value' in node:
                    fields.append((f"macro {node['macro']}", node['value']))

            _walk(template, visit)
            for field_name, value in fields:
                with self.subTest(template=template['name'], field=field_name):
                    self.assertIsInstance(value, str)

if __name__ == '__main__':
    unittest.main()
