#!/usr/bin/env python3
"""Contract tests for SAP template from Sensirion (no live sapcontrol / SNMP)."""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

import yaml

from sap_sensirion import (
    APP_ITEM_KEYS,
    APP_JSTART,
    APP_MASTER_KEY,
    CANARY_FQDN,
    ME_APP_MASTER_KEY,
    APP_TRIGGER_NAMES,
    APPLY_FLAG,
    CANARY_HOST,
    CERT_ITEM_KEYS,
    CERT_TRIGGER_NAMES,
    CHECK_FLAG,
    FORBIDDEN_SNIPPETS,
    HANA_TLS_PORT,
    JSTART_ITEM_KEY,
    LINUX_AGENT_ROLE_PATTERN,
    LINUX_AGENT_TEMPLATE_NAMES,
    LINUX_NETSNMP_SYSOBJECTID,
    LINUX_SNMP_ICMP_KEYS,
    LINUX_SNMP_TEMPLATE_NAME,
    LINUX_TEMPLATE_RULE,
    LM_APP_METRICS,
    LM_ME_WINDOWS_COLLECTOR,
    LM_PROMONITOR_USER,
    LM_SAP_HOSTS,
    LM_SNMP_USER,
    ME05_LM_ABSENT_SAP_DS,
    ME05_LM_DATASOURCES,
    ME_ASJAVA_HTTPS_PORT,
    ME_CANARY_FQDN,
    ME_CANARY_HOSTS,
    ME_SSL_PORTS,
    ME_STARTSRV_HTTPS_PORTS,
    ME_TEMPLATE_NAME,
    ME_TEMPLATE_YAML,
    ME_TRIGGER_NAMES,
    SH01_LM_DATASOURCES,
    SH01_LM_SAP_DS,
    ST22_DEFAULT_PATH,
    ST22_DEFAULT_PORT,
    ST22_FM,
    ST22_HOST_MACRO_NAMES,
    ST22_HOST_MACROS,
    ST22_SECRET_MACROS,
    PORT_ITEM_KEY,
    PORT_TRIGGER_NAMES,
    ROLE_TEMPLATES,
    SAP_ENTERPRISE_OID,
    SAP_ROLES,
    SNMP_ITEM_KEYS,
    SNMP_LLD_KEYS,
    SNMP_PROTOTYPE_KEYS,
    SNMP_TRIGGER_NAMES,
    SNMP_TRIGGER_PROTOTYPE_NAMES,
    TEMPLATE_FILES,
    TEMPLATE_NAME,
    TEMPLATE_YAML,
    TPL,
    macros_for,
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
        self.assertEqual(self.yaml_text, render('hana'))
        self.assertEqual(ME_TEMPLATE_YAML.read_text(encoding='utf-8'), render('me'))
        self.assertEqual(set(TEMPLATE_FILES), {TEMPLATE_NAME, ME_TEMPLATE_NAME})
        self.assertEqual(ROLE_TEMPLATES['SAP HANA'], TEMPLATE_NAME)
        self.assertEqual(ROLE_TEMPLATES['SAP ME'], ME_TEMPLATE_NAME)

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

    def test_hana_yaml_has_no_os_snmp(self):
        self.assertTrue(SNMP_ITEM_KEYS.isdisjoint(self.keys))
        self.assertTrue(SNMP_LLD_KEYS.isdisjoint(self.keys))
        self.assertTrue(SNMP_PROTOTYPE_KEYS.isdisjoint(self.keys))
        self.assertNotIn('discovery_rules', self.template)
        snmp_items = [item for item in self.template['items'] if item.get('type') == 'SNMP_AGENT']
        self.assertEqual(snmp_items, [])
        self.assertIn(LINUX_NETSNMP_SYSOBJECTID, self.yaml_text)
        self.assertNotIn('1.3.6.1.4.1.2021', self.yaml_text)
        self.assertNotIn('ifHCInOctets', self.yaml_text)
        self.assertNotIn('ifInOctets', self.yaml_text)
        self.assertNotIn('sap.host.cpu.util', self.yaml_text)
        self.assertNotIn('sap.host.vfs.fs', self.yaml_text)
        self.assertNotIn('zabbix[host,snmp,available]', self.yaml_text)

    def test_lm_application_sapcontrol(self):
        self.assertTrue(APP_ITEM_KEYS.issubset(self.keys))
        self.assertIn(APP_MASTER_KEY, self.keys)
        self.assertIn('{$SAP.API.HOST}', APP_MASTER_KEY)
        self.assertIn('{$SAP.API.PASS}', APP_MASTER_KEY)
        self.assertEqual(ST22_FM, 'Z_GET_ST22')
        self.assertEqual(ST22_DEFAULT_PORT, '44301')
        self.assertEqual(ST22_DEFAULT_PATH, '/abapruntimeerror')
        self.assertIn(ST22_FM, self.yaml_text)
        self.assertIn(ST22_DEFAULT_PORT, self.yaml_text)
        self.assertIn(ST22_DEFAULT_PATH, self.yaml_text)
        self.assertIn(CANARY_FQDN, self.yaml_text)
        self.assertIn('device CH-STA-P-SH01 only', self.template['description'])
        self.assertIn('not role SAP HANA', self.template['description'])
        api_host = next(row for row in self.template['macros'] if row['macro'] == '{$SAP.API.HOST}')
        self.assertEqual(api_host.get('value', ''), '')
        self.assertIn('CH-STA-P-SH01 only', api_host['description'])
        self.assertNotIn('santaba/rest', self.yaml_text)
        hana_macros = {row['macro'] for row in self.template['macros']}
        self.assertIn('{$SAP.API.HOST}', hana_macros)
        trap_keys = {item['key'] for item in self.template['items'] if item.get('type') == 'TRAP'}
        self.assertEqual(trap_keys, set())
        master = next(item for item in self.template['items'] if item['key'] == APP_MASTER_KEY)
        self.assertEqual(master['type'], 'ZABBIX_PASSIVE')
        dependents = {
            item['key']
            for item in self.template['items']
            if item.get('type') == 'DEPENDENT' and item.get('key') in APP_ITEM_KEYS
        }
        self.assertEqual(dependents, APP_ITEM_KEYS)
        self.assertEqual({row[0] for row in LM_APP_METRICS}, APP_ITEM_KEYS)
        self.assertEqual({row[5] for row in LM_APP_METRICS}, {
            'promonitor',
            'instance_status',
            'abap_errors',
            'idoc_errors',
            'job_alerts',
            'locks',
            'qrfc_in',
            'qrfc_out',
            'rfc_status',
            'spool_errors',
            'syslog_alerts',
            'trfc_errors',
            'update_requests',
        })
        self.assertIn(LM_PROMONITOR_USER, self.yaml_text)
        self.assertIn(LM_SNMP_USER, self.yaml_text)
        self.assertIn(str(LM_SAP_HOSTS), self.template['description'])
        self.assertIn('ch-sta-p-sh01', self.template['description'].lower())
        self.assertIn('sapcontrol', self.template['description'])
        self.assertIn('openSUSE', self.template['description'])
        self.assertIn('official openSUSE template', self.template['description'])
        self.assertIn('attach Linux by Zabbix agent', self.template['description'])
        self.assertIn('stock Linux SNMP OS template', self.template['description'])
        self.assertIn('ST22', self.template['description'])
        self.assertNotIn('openSUSE matches the Linux platform rule', self.template['description'])
        self.assertNotIn('Agent-only OS extras', self.template['description'])
        self.assertIn('Linux SNMP', self.template['description'])
        self.assertIn(ME_TEMPLATE_NAME, self.template['description'])
        self.assertIn(SH01_LM_SAP_DS, self.template['description'])
        self.assertEqual(SH01_LM_DATASOURCES[0], SH01_LM_SAP_DS)
        me_desc = yaml.safe_load(ME_TEMPLATE_YAML.read_text(encoding='utf-8'))['zabbix_export']['templates'][0]['description']
        self.assertNotIn(SH01_LM_SAP_DS, me_desc)
        self.assertIn('UserParameter', self.yaml_text)
        self.assertNotIn(JSTART_ITEM_KEY, self.keys)
        self.assertIn('{$SAP.INSTANCE}', self.yaml_text)
        self.assertNotIn('zabbix_sender', self.yaml_text)
        for needle in (
            'ABAP runtime errors',
            'Application server instance',
            'IDoc errors',
            'Job alerts',
            'Lock entries',
            'qRFC inbound',
            'qRFC outbound',
            'RFC status',
            'Spool errors',
            'Transactional RFC',
            'Update requests',
        ):
            self.assertIn(needle, self.yaml_text, needle)

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

    def test_agent_certificate_and_port(self):
        self.assertTrue(CERT_ITEM_KEYS.issubset(self.keys))
        self.assertIn(PORT_ITEM_KEY, self.keys)
        cert = next(item for item in self.template['items'] if item['key'].startswith('web.certificate.get['))
        self.assertEqual(cert['type'], 'ZABBIX_PASSIVE')
        self.assertIn('CHECK_NOT_SUPPORTED', self.yaml_text)
        self.assertTrue(CERT_TRIGGER_NAMES.issubset(self.triggers))
        self.assertTrue(PORT_TRIGGER_NAMES.issubset(self.triggers))
        cert_triggers = [
            trig
            for item in self.template['items']
            if item.get('key') == 'sap.host.cert.not_after'
            for trig in item.get('triggers') or []
        ]
        self.assertEqual(len(cert_triggers), 2)
        for trig in cert_triggers:
            self.assertIn('{$SAP.CERT.CONTROL}=1', trig['expression'])
        port = next(item for item in self.template['items'] if item['key'] == PORT_ITEM_KEY)
        self.assertEqual(port['type'], 'SIMPLE')
        self.assertIn('{$SAP.PORT.CONTROL}=1', port['triggers'][0]['expression'])
        hana_macros = {row[0]: row[1] for row in macros_for('hana')}
        self.assertEqual(hana_macros['{$SAP.CERT.PORT}'], HANA_TLS_PORT)
        self.assertEqual(hana_macros['{$SAP.PORT.TCP}'], HANA_TLS_PORT)
        self.assertNotEqual(HANA_TLS_PORT, ME_ASJAVA_HTTPS_PORT)

    def test_host_os_triggers_stripped(self):
        self.assertTrue(SNMP_TRIGGER_NAMES.isdisjoint(self.triggers))
        self.assertTrue(SNMP_TRIGGER_PROTOTYPE_NAMES.isdisjoint(self.trigger_prototypes))
        self.assertNotIn('{$UNSUPPORTED.CONTROL}', self.yaml_text)
        hana_macros = {row[0] for row in macros_for('hana')}
        self.assertNotIn('{$UNSUPPORTED.CONTROL}', hana_macros)
        self.assertNotIn('{$SAP.CPU.UTIL.MAX}', hana_macros)
        self.assertIn('{$SAP.API.HOST}', hana_macros)

    def test_forbidden_and_no_fake_sap_snmp(self):
        for snippet in FORBIDDEN_SNIPPETS:
            self.assertNotIn(snippet, self.yaml_text, snippet)
        self.assertNotIn(SAP_ENTERPRISE_OID, self.yaml_text)
        self.assertNotIn('icmpping', self.yaml_text)
        self.assertNotIn('Linux by SNMP', self.yaml_text)
        self.assertNotIn('tls_certificate_expiry.sh', self.yaml_text)
        self.assertIn('collector methods', self.yaml_text)

    def test_health_pages(self):
        pages = {page['name'] for page in self.template['dashboards'][0]['pages']}
        self.assertEqual(pages, {'Overview', 'Application'})
        self.assertNotIn('Interfaces', pages)

    def test_no_os_calculated_items(self):
        self.assertNotIn('sap.host.memory.total', self.yaml_text)
        self.assertNotIn('sap.host.swap.total', self.yaml_text)

    def test_zerotouch_soft_assigns_os_specific(self):
        src = (ROOT / 'scripts/configure_nbxsync_zerotouch.py').read_text(encoding='utf-8')
        self.assertIn(f"'{TEMPLATE_NAME}'", src)
        self.assertIn(f"'{ME_TEMPLATE_NAME}'", src)
        self.assertIn("('sap_me', 'SAP ME')", src)
        self.assertIn("('sap_hana', 'SAP HANA')", src)
        self.assertIn("'sap_hana': [HostInterfaceRequirementChoices.AGENT]", src)
        self.assertIn("'sap_me': [HostInterfaceRequirementChoices.AGENT]", src)
        self.assertIn(
            "make_template(*TPL['linux_snmp'], req=[HostInterfaceRequirementChoices.SNMP]), 'SAP HANA'",
            src,
        )
        optional = re.search(r'OPTIONAL_TPL_KEYS = frozenset\(\{([^}]+)\}\)', src, re.S)
        self.assertIsNotNone(optional)
        self.assertIn("'sap_hana'", optional.group(1))
        self.assertIn("'sap_me'", optional.group(1))
        self.assertNotIn("'sap_agent'", optional.group(1))
        self.assertNotIn('import_yaml_templates', src)

    def test_linux_agent_role_pattern_excludes_hana(self):
        pat = re.compile(LINUX_AGENT_ROLE_PATTERN, re.I)
        self.assertEqual(LINUX_TEMPLATE_RULE, 'Linux')
        self.assertFalse(pat.search('SAP HANA'))
        self.assertFalse(pat.search('vCenter'))
        self.assertTrue(pat.search('Server'))
        self.assertTrue(pat.search('Zabbix Proxy'))
        ztc = (ROOT / 'scripts/configure_nbxsync_zerotouch.py').read_text(encoding='utf-8')
        self.assertIn(LINUX_AGENT_ROLE_PATTERN, ztc)
        self.assertNotIn("'^(?!vCenter$).*'", ztc)

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
        exclude_fn = _function_source(src, '_exclude_linux_os_agent_from_hana') or ''
        assign_os = _function_source(src, '_assign_linux_snmp_os_to_hana') or ''
        disable_fn = _function_source(src, '_disable_linux_snmp_icmpping') or ''
        for role in SAP_ROLES:
            self.assertIn(role, assign_fn)
        self.assertIn('HostInterfaceRequirementChoices.SNMP', assign_os)
        self.assertIn('HostInterfaceRequirementChoices.AGENT', assign_fn)
        self.assertIn('ME_TEMPLATE_NAME', assign_fn)
        self.assertIn('_exclude_linux_os_agent_from_hana', assign_fn)
        self.assertIn('_assign_linux_snmp_os_to_hana', assign_fn)
        self.assertIn('_disable_linux_snmp_icmpping', assign_fn)
        self.assertIn('LINUX_AGENT_ROLE_PATTERN', exclude_fn)
        self.assertIn('LINUX_TEMPLATE_RULE', exclude_fn)
        self.assertIn('OS_LINUX_HOSTGROUP', exclude_fn)
        self.assertIn('LINUX_AGENT_TEMPLATE_NAMES', assign_fn)
        self.assertTrue(LINUX_AGENT_TEMPLATE_NAMES)
        self.assertEqual(LINUX_SNMP_TEMPLATE_NAME, 'Linux by SNMP')
        self.assertEqual(LINUX_SNMP_ICMP_KEYS, ('icmpping', 'icmppingloss', 'icmppingsec'))
        self.assertIn('LINUX_SNMP_TEMPLATE_NAME', assign_os)
        self.assertIn('LINUX_SNMP_ICMP_KEYS', disable_fn)
        self.assertIn('item.update', disable_fn)
        self.assertIn('trigger.update', disable_fn)
        st22_fn = _function_source(src, '_assign_st22_macros_on_sh01_only') or ''
        self.assertIn('_assign_st22_macros_on_sh01_only', assign_fn)
        self.assertIn('ST22_HOST_MACROS', st22_fn)
        self.assertIn('CANARY_HOST', st22_fn)
        self.assertIn('DeviceRole', st22_fn)
        self.assertIn('ST22_SECRET_MACROS', st22_fn)
        self.assertNotIn("value=_sap.ST22_SECRET", st22_fn)
        self.assertEqual(dict(ST22_HOST_MACROS)['{$SAP.API.HOST}'], CANARY_FQDN)
        self.assertEqual(ST22_HOST_MACRO_NAMES, ('{$SAP.API.HOST}', '{$SAP.API.PORT}', '{$SAP.API.PATH}'))
        self.assertEqual(ST22_SECRET_MACROS, ('{$SAP.API.USER}', '{$SAP.API.PASS}'))


class SapMeSensirionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        write_yaml()
        cls.yaml_text = ME_TEMPLATE_YAML.read_text(encoding='utf-8')
        cls.tpl = yaml.safe_load(cls.yaml_text)
        cls.template = cls.tpl['zabbix_export']['templates'][0]
        cls.keys = _walk_item_keys(cls.template)
        cls.triggers = _walk_names(cls.template, ('triggers',))

    def test_me_identity_and_no_linux_snmp(self):
        self.assertEqual(self.template['name'], ME_TEMPLATE_NAME)
        self.assertIn('Windows', self.template['description'])
        self.assertIn('AS Java', self.template['description'])
        for host in ME_CANARY_HOSTS:
            self.assertIn(host, self.template['description'])
        self.assertNotIn('1.3.6.1.4.1.2021', self.yaml_text)
        self.assertNotIn('ifHCInOctets', self.yaml_text)
        self.assertNotIn('sap.host.cpu.util', self.keys)
        self.assertNotIn('sap.host.net.if.discovery', self.keys)
        for snippet in FORBIDDEN_SNIPPETS:
            self.assertNotIn(snippet, self.yaml_text, snippet)

    def test_me_application_and_jstart(self):
        self.assertTrue(APP_ITEM_KEYS.issubset(self.keys))
        self.assertIn(ME_APP_MASTER_KEY, self.keys)
        self.assertNotIn(APP_MASTER_KEY, self.keys)
        self.assertIn(JSTART_ITEM_KEY, self.keys)
        self.assertTrue(APP_TRIGGER_NAMES.issubset(self.triggers))
        self.assertTrue(ME_TRIGGER_NAMES.issubset(self.triggers))
        self.assertIn(APP_JSTART, self.triggers)
        jstart = next(item for item in self.template['items'] if item['key'] == JSTART_ITEM_KEY)
        self.assertEqual(jstart['type'], 'ZABBIX_PASSIVE')
        pages = {page['name'] for page in self.template['dashboards'][0]['pages']}
        self.assertEqual(pages, {'Overview', 'Application'})
        self.assertNotIn('Interfaces', pages)
        self.assertIn(ME_APP_MASTER_KEY, self.keys)
        self.assertNotIn(APP_MASTER_KEY, self.keys)
        me_macros = {row['macro'] for row in self.template['macros']}
        self.assertNotIn('{$SAP.API.HOST}', me_macros)
        self.assertNotIn('{$SAP.API.PASS}', me_macros)
        self.assertIn(PORT_ITEM_KEY, self.keys)
        self.assertTrue(CERT_ITEM_KEYS.issubset(self.keys))

    def test_me_ssl_ports_from_lm_resource(self):
        self.assertEqual(ME_SSL_PORTS, ('50001', '50014', '51014'))
        self.assertEqual(ME_ASJAVA_HTTPS_PORT, '50001')
        self.assertEqual(ME_STARTSRV_HTTPS_PORTS, ('50014', '51014'))
        self.assertIn('ch-sta-p-me05', ME_CANARY_HOSTS)
        macros = {row['macro']: str(row['value']) for row in self.template['macros']}
        self.assertEqual(macros['{$SAP.CERT.PORT}'], ME_ASJAVA_HTTPS_PORT)
        self.assertEqual(macros['{$SAP.PORT.TCP}'], ME_ASJAVA_HTTPS_PORT)
        self.assertIn(ME_CANARY_FQDN, self.template['description'])
        self.assertIn(LM_ME_WINDOWS_COLLECTOR, self.template['description'])
        for port in ME_SSL_PORTS:
            self.assertIn(port, self.template['description'])
        self.assertIn('PCoIP', self.template['description'])
        self.assertIn('host card', self.template['description'])
        self.assertIn(LM_PROMONITOR_USER, self.template['description'])
        self.assertIn('NoDataMonitoring', self.template['description'])
        for name in ME05_LM_DATASOURCES:
            self.assertIn(name, self.template['description'], name)
        for name in ME05_LM_ABSENT_SAP_DS:
            self.assertIn(name, self.template['description'], name)
        self.assertIn('additive', self.template['description'])


if __name__ == '__main__':
    unittest.main()
