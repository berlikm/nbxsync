#!/usr/bin/env python3
"""Contract tests for IIS Observability (applicationHost fixtures, no live IIS)."""

from __future__ import annotations

import json
import unittest

from iis_observability import (
    CERT_GET_PREFIX,
    CONFIG_KEY,
    FIXTURES,
    STOCK_CERT_TEMPLATE,
    STOCK_IIS_TEMPLATE,
    TEMPLATE_NAME,
    javascript_steps,
    lld_js_source,
    load_template,
    template_block,
)
from mssql_observability import run_javascript


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding='utf-8')


def _lld(name: str) -> list[dict]:
    return json.loads(run_javascript(_fixture(name), script=lld_js_source()))


class HttpsBindingLldTests(unittest.TestCase):
    def test_http_only_is_empty(self):
        self.assertEqual(_lld('http_only.xml'), [])

    def test_commented_https_site_is_ignored(self):
        rows = _lld('mixed_https.xml')
        sites = {row['{#IIS.SITE}'] for row in rows}
        self.assertNotIn('Commented HTTPS', sites)

    def test_mixed_https_discovers_star_sni_and_ipv6(self):
        rows = _lld('mixed_https.xml')
        by_bind = {row['{#IIS.BIND}']: row for row in rows}
        self.assertEqual(len(rows), 4)
        self.assertEqual(
            by_bind['Default Web Site/*/443/_'],
            {
                '{#IIS.SITE}': 'Default Web Site',
                '{#IIS.IP}': '*',
                '{#IIS.PORT}': '443',
                '{#IIS.HOST}': '',
                '{#IIS.SNI}': '127.0.0.1',
                '{#IIS.CONNECT}': '127.0.0.1',
                '{#IIS.HAS_HOST}': '0',
                '{#IIS.BIND}': 'Default Web Site/*/443/_',
            },
        )
        self.assertEqual(by_bind['Intranet/*/443/intranet.corp.local']['{#IIS.HAS_HOST}'], '1')
        self.assertEqual(by_bind['Intranet/*/443/intranet.corp.local']['{#IIS.SNI}'], 'intranet.corp.local')
        self.assertEqual(by_bind['Intranet/*/443/intranet.corp.local']['{#IIS.CONNECT}'], '127.0.0.1')
        self.assertEqual(by_bind['Intranet/10.0.8.21/8443/intranet.corp.local']['{#IIS.CONNECT}'], '10.0.8.21')
        self.assertEqual(by_bind['Intranet/10.0.8.21/8443/intranet.corp.local']['{#IIS.PORT}'], '8443')
        ipv6 = by_bind['IPv6 App/[fe80::1]/443/ipv6.corp.local']
        self.assertEqual(ipv6['{#IIS.CONNECT}'], 'fe80::1')
        self.assertEqual(ipv6['{#IIS.SNI}'], 'ipv6.corp.local')


class YamlContractTests(unittest.TestCase):
    def setUp(self):
        self.tpl = template_block(load_template())

    def test_companion_not_stock(self):
        self.assertEqual(self.tpl['template'], TEMPLATE_NAME)
        self.assertNotIn('templates', self.tpl)
        keys = json.dumps([i.get('key') for i in self.tpl.get('items') or []])
        self.assertNotIn('service.discovery', keys)
        self.assertNotIn('service.info[W3SVC]', keys)
        self.assertNotIn(STOCK_IIS_TEMPLATE, json.dumps(self.tpl.get('templates') or []))
        self.assertNotIn(STOCK_CERT_TEMPLATE, json.dumps(self.tpl.get('templates') or []))

    def test_lld_js_matches_file(self):
        expected = lld_js_source()
        count = next(i for i in self.tpl['items'] if i['key'] == 'iis.ssl.binding.count')
        discovery = self.tpl['discovery_rules'][0]
        self.assertEqual(javascript_steps(count), [expected])
        self.assertEqual(javascript_steps(discovery), [expected])

    def test_master_and_handshake_keys(self):
        self.assertEqual(self.tpl['items'][0]['key'], CONFIG_KEY)
        proto = self.tpl['discovery_rules'][0]['item_prototypes'][0]
        self.assertTrue(proto['key'].startswith(CERT_GET_PREFIX))
        self.assertIn('{#IIS.SNI}', proto['key'])
        self.assertIn('{#IIS.CONNECT}', proto['key'])

    def test_expiry_default_is_30_days(self):
        macros = {m['macro']: m['value'] for m in self.tpl['macros']}
        self.assertEqual(macros['{$IIS.CERT.EXPIRY.WARN}'], '30')

    def test_invalid_skips_empty_host_header(self):
        validation = next(
            p
            for p in self.tpl['discovery_rules'][0]['item_prototypes']
            if p['key'].startswith('iis.ssl.cert.validation[')
        )
        expr = validation['trigger_prototypes'][0]['expression']
        self.assertIn('{#IIS.HAS_HOST}=1', expr)
        self.assertEqual(validation['trigger_prototypes'][0]['priority'], 'HIGH')

    def test_expiry_is_warning(self):
        not_after = next(
            p
            for p in self.tpl['discovery_rules'][0]['item_prototypes']
            if p['key'].startswith('iis.ssl.cert.not_after[')
        )
        trig = not_after['trigger_prototypes'][0]
        self.assertEqual(trig['priority'], 'WARNING')
        self.assertIn('{$IIS.CERT.EXPIRY.WARN}', trig['expression'])


if __name__ == '__main__':
    unittest.main()
