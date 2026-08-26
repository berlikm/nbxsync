#!/usr/bin/env python3
"""YAML/JS contract tests for the Cato HTTP collector (no Django, no Zabbix)."""

from __future__ import annotations

import json
import unittest
import uuid
from pathlib import Path

import yaml

from cato_http import (
    EXPECTED_COLLECTOR_TRIGGER_NAMES,
    EXPECTED_DASHBOARD_NAMES,
    EXPECTED_DASHBOARD_ITEM_REFERENCES,
    EXPECTED_DASHBOARD_NAVIGATOR_GROUPS,
    EXPECTED_DISCOVERY_KEYS,
    EXPECTED_GRAPH_PROTOTYPES,
    EXPECTED_HEALTH_PAGES,
    EXPECTED_ITEM_PROTOTYPE_KEYS,
    EXPECTED_NETWORK_PAGES,
    EXPECTED_PATH_PAGES,
    EXPECTED_STATE_TRIGGER_PROTOTYPE_NAMES,
    EXPECTED_TEMPLATE_ITEM_KEYS,
    LLD_JS,
    METRICS_QUERY,
    SNAPSHOT_QUERY,
    TEMPLATE_MACROS,
    TEMPLATE_NAME,
    TEMPLATE_PATH,
    collector_host,
    graphql_posts,
    is_lan_transport,
    is_usb_identity,
    load_lld_js,
    metrics_lan_census,
    metrics_sla_census,
    normalize_socket_serial,
    run_lld_js,
    snapshot_census,
    snapshot_socket_serials,
)
from configure_cato_zabbix import (
    _legacy_usb_port_itemids,
    retire_legacy_usb_port_items,
)
from cato_http_template import char_from_path_js, render_template

ROOT = Path(__file__).resolve().parents[1]


def _template() -> dict:
    doc = yaml.safe_load(TEMPLATE_PATH.read_text(encoding='utf-8'))
    return doc['zabbix_export']['templates'][0]


def _js(rule: dict) -> str:
    return rule['preprocessing'][0]['parameters'][0]


SNAPSHOT_FIXTURE = {
    'data': {
        'accountSnapshot': {
            'sites': [
                {
                    'id': '10',
                    'connectivityStatus': 'connected',
                    'degradedStatus': {
                        'isDegraded': True,
                        'degradedDetails': [{'reason': 'WAN_DISCONNECTED'}],
                    },
                    'popName': 'ZRH',
                    'hostCount': 4,
                    'info': {
                        'name': 'Zurich',
                        'connType': 'SOCKET_X1500',
                        'isHA': True,
                    },
                    'devices': [
                        {
                            'name': 'zh-pri',
                            'connected': True,
                            'haRole': 'MASTER',
                            'deviceUptime': 86400,
                            'socketInfo': {
                                'id': 's1',
                                'serial': 'SOCK-A',
                                'isPrimary': True,
                                'platform': 'X1500',
                            },
                            'interfacesLinkState': [
                                {'id': 'WAN1', 'mediaIn': True, 'up': True, 'hasTunnel': True, 'hasInternet': True},
                                {'id': 'WAN2', 'mediaIn': True, 'up': True, 'hasTunnel': False, 'hasInternet': True},
                                {'id': 'LAN1', 'mediaIn': True, 'up': True, 'hasTunnel': False, 'hasInternet': False},
                                {'id': 'USB', 'mediaIn': False, 'up': False, 'hasTunnel': False, 'hasInternet': False},
                            ],
                            'interfaces': [
                                {
                                    'name': 'WAN1',
                                    'connected': True,
                                    'popName': 'ZRH',
                                    'tunnelUptime': 100,
                                    'physicalPort': 'WAN1',
                                    'tunnelRemoteIP': '203.0.113.10',
                                    'tunnelConnectionReason': 'Connected',
                                    'tunnelRemoteIPInfo': {'provider': 'ExampleISP'},
                                    'info': {'id': 'l1', 'name': 'WAN1', 'destType': 'CATO'},
                                },
                                {
                                    'name': 'WAN2',
                                    'connected': True,
                                    'info': {'id': 'l2', 'name': 'WAN2', 'destType': 'CATO'},
                                },
                                {
                                    'name': 'USB',
                                    'connected': False,
                                    'physicalPort': 'USB',
                                    'info': {'id': 'usb1', 'name': 'USB', 'destType': 'CATO'},
                                },
                            ],
                        },
                        {
                            'name': 'zh-sec',
                            'connected': True,
                            'haRole': 'BACKUP',
                            'socketInfo': {
                                'id': 's2',
                                'serial': 'SOCK-B',
                                'isPrimary': False,
                                'platform': 'X1500',
                            },
                            'interfacesLinkState': [
                                {'id': 'WAN1', 'mediaIn': False, 'up': False, 'hasTunnel': False, 'hasInternet': False},
                            ],
                            'interfaces': [
                                {
                                    'name': 'WAN1',
                                    'connected': True,
                                    'info': {'id': 'l1', 'name': 'WAN1', 'destType': 'CATO'},
                                },
                            ],
                        },
                    ],
                },
                {
                    'id': '20',
                    'connectivityStatus': 'connected',
                    'info': {
                        'name': 'Azure',
                        'connType': 'IPSEC_V2',
                        'isHA': False,
                    },
                    'devices': [
                        {
                            'name': 'azure',
                            'connected': True,
                            'socketInfo': {
                                'id': 's9',
                                'serial': 'IPSEC-1',
                                'isPrimary': True,
                            },
                            'interfaces': [
                                {'name': 'WAN1', 'info': {'id': 'x1', 'name': 'WAN1'}}
                            ],
                        }
                    ],
                },
            ]
        }
    }
}

METRICS_FIXTURE = {
    'data': {
        'accountMetrics': {
            'sites': [
                {
                    'id': '10',
                    'name': 'Zurich',
                    'info': {'connType': 'SOCKET_X1500'},
                    'interfaces': [
                        {
                            'name': 'WAN1',
                            'interfaceInfo': {'id': 'l1', 'name': 'WAN1', 'destType': 'CATO'},
                            'metrics': {'bytesDownstream': 1},
                            'timeseries': [
                                {
                                    'label': 'lastMilePacketLoss',
                                    'data': [[100, 1], [200, 2]],
                                },
                                {
                                    'label': 'lastMilePacketLoss',
                                    'data': [[100, 3], [200, 4]],
                                },
                                {
                                    'label': 'lastMileLatency',
                                    'data': [[100, 10], [200, 20]],
                                },
                            ],
                        },
                        {
                            'name': 'WAN2',
                            'interfaceInfo': {'id': 'l2', 'name': 'WAN2', 'destType': 'CATO'},
                            'metrics': {'bytesDownstream': 1},
                            'timeseries': [
                                {
                                    'label': 'lastMilePacketLoss',
                                    'data': [[100, 5], [200, 6]],
                                },
                                {
                                    'label': 'lastMileLatency',
                                    'data': [[100, 30], [200, 40]],
                                },
                            ],
                        },
                        {
                            'name': 'USB',
                            'interfaceInfo': {'id': 'usb1', 'name': 'USB', 'destType': 'CATO'},
                            'metrics': {'bytesDownstream': 1},
                        },
                    ],
                },
                {
                    'id': '20',
                    'name': 'Azure',
                    'info': {'connType': 'IPSEC_V2'},
                    'interfaces': [
                        {
                            'name': 'WAN1',
                            'interfaceInfo': {'id': 'x1', 'name': 'WAN1'},
                        }
                    ],
                },
            ]
        },
        'socketPortMetrics': {
            'records': [
                {
                    'fieldsMap': {
                        'site_id': '10',
                        'site_name': 'Zurich',
                        'socket_interface': 'LAN1',
                        'transport_type': 'LAN',
                        'throughput_upstream': '10',
                        'throughput_downstream': '20',
                    }
                },
                {
                    'fieldsMap': {
                        'site_id': '10',
                        'site_name': 'Zurich',
                        'socket_interface': 'WAN1',
                        'transport_type': 'WAN',
                        'throughput_upstream': '30',
                        'throughput_downstream': '40',
                    }
                },
                {
                    'fieldsMap': {
                        'site_id': '10',
                        'site_name': 'Zurich',
                        'socket_interface': 'USB1',
                        'transport_type': 'LAN',
                        'throughput_upstream': '1',
                        'throughput_downstream': '2',
                    }
                },
                {
                    'fieldsMap': {
                        'site_id': '20',
                        'site_name': 'Azure',
                        'socket_interface': 'LAN1',
                        'transport_type': 'LAN',
                        'throughput_upstream': '5',
                        'throughput_downstream': '6',
                    }
                },
                {
                    'fieldsMap': {
                        'site_id': '10',
                        'site_name': 'Zurich',
                        'socket_interface': 'LAN2',
                        'transport_type': 'wired',
                        'throughput_upstream': '7',
                        'throughput_downstream': '8',
                    }
                },
            ]
        },
    }
}


class CatoTemplateContractTests(unittest.TestCase):
    def setUp(self):
        self.tpl = _template()

    def test_generated_yaml_matches_renderer(self):
        self.assertEqual(TEMPLATE_PATH.read_text(encoding='utf-8'), render_template())

    def test_lld_js_files_are_embedded(self):
        by_key = {rule['key']: rule for rule in self.tpl['discovery_rules']}
        self.assertEqual(set(by_key), EXPECTED_DISCOVERY_KEYS)
        for key, path in LLD_JS.items():
            self.assertTrue(path.exists(), path)
            self.assertEqual(_js(by_key[key]), load_lld_js(key))

    def test_masters_use_expanded_queries_and_omit_wan_role(self):
        items = {item['key']: item for item in self.tpl['items']}
        self.assertEqual(items['cato.account.snapshot']['posts'], graphql_posts(SNAPSHOT_QUERY))
        self.assertEqual(items['cato.account.metrics']['posts'], graphql_posts(METRICS_QUERY))
        self.assertIn('haStatus', items['cato.account.snapshot']['posts'])
        self.assertIn('degradedStatus', items['cato.account.snapshot']['posts'])
        self.assertIn('interfacesLinkState', items['cato.account.snapshot']['posts'])
        self.assertIn('physicalPort', items['cato.account.snapshot']['posts'])
        self.assertIn('tunnelRemoteIP', items['cato.account.snapshot']['posts'])
        self.assertIn('deviceUptime', items['cato.account.snapshot']['posts'])
        self.assertIn('lastMilePacketLoss', items['cato.account.metrics']['posts'])
        self.assertIn('lastMileLatency', items['cato.account.metrics']['posts'])
        self.assertIn('timeseries(', items['cato.account.metrics']['posts'])
        self.assertIn('packetsDiscardedDownstream', items['cato.account.metrics']['posts'])
        self.assertIn('destType', items['cato.account.metrics']['posts'])
        self.assertNotIn('wanRole', items['cato.account.snapshot']['posts'])
        self.assertNotIn('altWanStatus', items['cato.account.snapshot']['posts'])
        posts = items['cato.account.metrics']['posts']
        self.assertIn('socketPortMetrics(', posts)
        self.assertIn('throughput_upstream', posts)
        self.assertIn('transport_type', posts)
        self.assertIn('} socketPortMetrics(', posts)
        self.assertGreater(posts.find('socketPortMetrics('), posts.find('accountMetrics('))
        self.assertIn('groupDevices: true', items['cato.account.metrics']['posts'])

    def test_all_template_uuids_are_v4(self):
        def walk(value):
            if isinstance(value, dict):
                if 'uuid' in value:
                    yield value['uuid']
                for child in value.values():
                    yield from walk(child)
            elif isinstance(value, list):
                for child in value:
                    yield from walk(child)

        values = list(walk(self.tpl))
        self.assertTrue(values)
        self.assertTrue(all(uuid.UUID(value).version == 4 for value in values))

    def test_template_item_keys_and_macros(self):
        keys = {item['key'] for item in self.tpl['items']}
        self.assertTrue(EXPECTED_TEMPLATE_ITEM_KEYS <= keys)
        macros = {row['macro']: row['value'] for row in self.tpl['macros']}
        self.assertEqual(macros, TEMPLATE_MACROS)
        self.assertEqual(macros['{$CATO.LOSS.WARN}'], '2')
        self.assertEqual(macros['{$CATO.RTT.WARN}'], '101')

    def test_no_icmp_or_nested_service_discovery(self):
        blob = TEMPLATE_PATH.read_text(encoding='utf-8')
        self.assertNotIn('icmpping', blob)
        self.assertNotIn('service.discovery', blob)
        self.assertNotIn('type: ICMPPING', blob)
        self.assertNotIn('priority: DISASTER', blob)

    def test_site_disconnected_is_high(self):
        site = next(
            rule for rule in self.tpl['discovery_rules'] if rule['key'] == 'cato.site.discovery'
        )
        conn = next(item for item in site['item_prototypes'] if item['key'] == 'cato.site.connected[{#SITE.ID}]')
        trigger = conn['trigger_prototypes'][0]
        self.assertEqual(trigger['priority'], 'HIGH')
        self.assertNotIn('nodata(', trigger['expression'].lower())
        self.assertEqual(trigger['name'], 'Cato site {#SITE.NAME}: Disconnected')

    def test_state_trigger_names_and_no_nodata(self):
        names = set()
        for rule in self.tpl['discovery_rules']:
            for item in rule.get('item_prototypes') or []:
                for trigger in item.get('trigger_prototypes') or []:
                    names.add(trigger['name'])
                    self.assertNotIn('nodata(', trigger['expression'].lower(), trigger['name'])
        self.assertTrue(EXPECTED_STATE_TRIGGER_PROTOTYPE_NAMES <= names)

    def test_item_prototype_keys(self):
        keys = {
            item['key']
            for rule in self.tpl['discovery_rules']
            for item in rule.get('item_prototypes') or []
        }
        self.assertTrue(EXPECTED_ITEM_PROTOTYPE_KEYS <= keys)

    def test_socket_and_wan_names_include_site_and_serial(self):
        socket = next(
            rule for rule in self.tpl['discovery_rules'] if rule['key'] == 'cato.socket.discovery'
        )
        wan = next(rule for rule in self.tpl['discovery_rules'] if rule['key'] == 'cato.wan.discovery')
        sock_conn = next(item for item in socket['item_prototypes'] if 'socket.connected[' in item['key'])
        wan_conn = next(item for item in wan['item_prototypes'] if item['key'].startswith('cato.wan.connected['))
        self.assertEqual(sock_conn['name'], 'Cato Socket {#SITE.NAME} / {#SERIAL}: Connectivity')
        self.assertEqual(
            wan_conn['name'],
            'Cato WAN {#SITE.NAME} / {#SERIAL} / {#LINK.NAME}: Connectivity',
        )

    def test_graph_prototypes_split_rtt_and_jitter(self):
        names = {
            graph['name']
            for rule in self.tpl['discovery_rules']
            for graph in rule.get('graph_prototypes') or []
        }
        self.assertEqual(names, EXPECTED_GRAPH_PROTOTYPES)
        self.assertNotIn('Latency and jitter', ' '.join(names))
        sla = next(
            rule
            for rule in self.tpl['discovery_rules']
            if rule['key'] == 'cato.wan.metrics.discovery'
        )
        lan = next(
            rule
            for rule in self.tpl['discovery_rules']
            if rule['key'] == 'cato.lan.metrics.discovery'
        )
        self.assertIn(
            'Cato WAN {#SITE.NAME} / {#LINK.NAME}: Bandwidth',
            {graph['name'] for graph in sla.get('graph_prototypes') or []},
        )
        self.assertEqual(
            {graph['name'] for graph in lan.get('graph_prototypes') or []},
            {'Cato LAN {#SITE.NAME} / {#PORT.ID}: Bandwidth'},
        )

    def test_dashboards_health_path_network(self):
        by_name = {dash['name']: dash for dash in self.tpl['dashboards']}
        self.assertEqual(set(by_name), EXPECTED_DASHBOARD_NAMES)
        self.assertEqual({page['name'] for page in by_name['Health']['pages']}, EXPECTED_HEALTH_PAGES)
        self.assertEqual({page['name'] for page in by_name['Path']['pages']}, EXPECTED_PATH_PAGES)
        self.assertEqual({page['name'] for page in by_name['Network']['pages']}, EXPECTED_NETWORK_PAGES)
        health_types = [
            widget['type']
            for page in by_name['Health']['pages']
            for widget in page['widgets']
        ]
        self.assertNotIn('graphprototype', health_types)
        self.assertIn('honeycomb', health_types)
        self.assertIn('svggraph', health_types)
        path_pages = {page['name']: page for page in by_name['Path']['pages']}
        overview_names = [widget['name'] for widget in path_pages['Overview']['widgets']]
        self.assertEqual(overview_names, ['Overlay loss', 'Overlay RTT', 'Overlay jitter'])
        self.assertNotIn('Last-mile loss', overview_names)
        last_mile_names = [widget['name'] for widget in path_pages['Last mile']['widgets']]
        self.assertIn('Last-mile loss', last_mile_names)
        self.assertIn('RX utilization', last_mile_names)
        network_pages = {page['name']: page for page in by_name['Network']['pages']}
        self.assertIn('HA', network_pages)
        self.assertIn('Tunnels', network_pages)
        self.assertIn('Ports', network_pages)
        self.assertIn('Degraded', {page['name'] for page in by_name['Health']['pages']})
        ports = network_pages['Ports']
        self.assertEqual(
            [widget['name'] for widget in ports['widgets'] if widget['type'] == 'graphprototype'],
            ['WAN traffic', 'LAN traffic'],
        )
        for widget in ports['widgets']:
            if widget['type'] != 'graphprototype':
                continue
            fields = {field['name']: field['value'] for field in widget['fields']}
            self.assertEqual(str(fields['columns']), '3')
            self.assertEqual(str(fields['rows']), '2')

    def test_health_overview_matches_forti_chrome(self):
        health = next(dash for dash in self.tpl['dashboards'] if dash['name'] == 'Health')
        overview = next(page for page in health['pages'] if page['name'] == 'Overview')

        def wy(widget):
            if 'y' in widget:
                return str(widget['y'])
            if True in widget:
                return str(widget[True])
            return '0'

        tiles = [widget for widget in overview['widgets'] if wy(widget) == '0']
        self.assertEqual([widget['name'] for widget in tiles], ['Snapshot', 'Metrics', 'Sites up', 'Sockets up'])
        self.assertEqual([widget['type'] for widget in tiles], ['gauge', 'gauge', 'item', 'item'])
        self.assertTrue(all(str(widget['width']) == '18' for widget in tiles))
        problems = [widget for widget in overview['widgets'] if widget['type'] == 'problems']
        self.assertEqual(len(problems), 1)
        self.assertEqual(str(problems[0]['width']), '72')
        self.assertEqual(wy(problems[0]), '4')
        pfields = {field['name']: field['value'] for field in problems[0]['fields']}
        self.assertEqual(str(pfields['show_tags']), '1')
        self.assertEqual(pfields['tag_priority'], 'site, connection_type, ha_role, port_kind, dest_type')
        honey = next(widget for widget in overview['widgets'] if widget['type'] == 'honeycomb')
        self.assertEqual(honey['name'], 'Sites')
        self.assertEqual(str(honey['width']), '72')
        graphs = [widget for widget in overview['widgets'] if widget['type'] == 'svggraph']
        self.assertEqual([widget['name'] for widget in graphs], ['Census', 'Worst overlay loss'])
        self.assertTrue(all(str(widget['width']) == '36' for widget in graphs))

    def test_path_overlay_loss_is_full_width_interpolated(self):
        path = next(dash for dash in self.tpl['dashboards'] if dash['name'] == 'Path')
        overview = next(page for page in path['pages'] if page['name'] == 'Overview')
        loss = next(widget for widget in overview['widgets'] if widget['name'] == 'Overlay loss')
        fields = {field['name']: field['value'] for field in loss['fields']}
        self.assertEqual(str(loss['width']), '72')
        self.assertEqual(str(fields['interpolation']), '1')
        self.assertEqual(str(fields['show.1']), '2')
        self.assertEqual(str(fields['thresholds.1.threshold']), '2')
        label = str(fields['primary_label'])
        self.assertIn('Cato WAN (.*): Overlay loss', label)
        self.assertRegex(label, r',"\\1"\)')

    def test_estate_rollup_items_use_foreach(self):
        by_key = {item['key']: item for item in self.tpl['items']}
        self.assertEqual(by_key['cato.site.up.count']['params'], 'sum(last_foreach(//cato.site.connected[*]))')
        self.assertEqual(by_key['cato.wan.loss.worst.pct']['params'], 'max(last_foreach(//cato.wan.loss.max.pct[*]))')
        self.assertEqual(
            by_key['cato.site.ha.not_ready.count']['params'],
            'count(exists_foreach(//cato.site.ha.readiness.code[*]))-sum(last_foreach(//cato.site.ha.readiness.code[*]))',
        )
        self.assertEqual(by_key['cato.site.degraded.count']['params'], 'sum(last_foreach(//cato.site.degraded[*]))')


    def test_last_mile_prototypes_use_timeseries_values(self):
        sla = next(
            rule
            for rule in self.tpl['discovery_rules']
            if rule['key'] == 'cato.wan.metrics.discovery'
        )
        prototypes = {item['key']: item for item in sla['item_prototypes']}
        loss_js = _js(
            prototypes['cato.wan.lastmile.loss.pct[{#SITE.ID},{#LINK.ID}]']
        ).replace('{#SITE.ID}', '10').replace('{#LINK.ID}', 'l1')
        latency_js = _js(
            prototypes['cato.wan.lastmile.latency.ms[{#SITE.ID},{#LINK.ID}]']
        ).replace('{#SITE.ID}', '10').replace('{#LINK.ID}', 'l1')
        payload = json.dumps(METRICS_FIXTURE)
        self.assertEqual(run_lld_js(loss_js, payload), 3)
        self.assertEqual(run_lld_js(latency_js, payload), 20)
        sla_names = {
            trigger['name']
            for item in sla.get('item_prototypes') or []
            for trigger in item.get('trigger_prototypes') or []
        }
        self.assertNotIn(
            'Cato WAN {#SITE.NAME} / {#LINK.NAME}: High last-mile packet loss',
            sla_names,
        )
        self.assertNotIn(
            'Cato WAN {#SITE.NAME} / {#LINK.NAME}: High overlay packet loss',
            sla_names,
        )
        self.assertNotIn(
            'Cato WAN {#SITE.NAME} / {#LINK.NAME}: High overlay RTT',
            sla_names,
        )

    def test_collector_trigger_names(self):
        names = {
            trigger['name']
            for item in self.tpl['items']
            for trigger in item.get('triggers') or []
        }
        self.assertTrue(EXPECTED_COLLECTOR_TRIGGER_NAMES <= names)

    def test_census_uses_exists_foreach_and_availability(self):
        by_key = {item['key']: item for item in self.tpl['items']}
        site = by_key['cato.site.discovery.count']
        self.assertIn('count(exists_foreach(//cato.site.connected[*]))-count(exists_foreach(//cato.site.connected[__seed]))', site['params'])
        expr = site['triggers'][0]['expression']
        self.assertIn('cato.api.snapshot.available', expr)
        self.assertIn('{$CATO.SITES.EXPECTED}>0', expr)
        self.assertIn('max(/Cato Networks by HTTP/cato.site.discovery.count,30m)', expr)
        sla = by_key['cato.wan.metrics.discovery.count']
        self.assertIn('cato.api.metrics.available', sla['triggers'][0]['expression'])

    def test_host_name_uses_account_id(self):
        self.assertEqual(collector_host('964'), 'cato-account-964')
        self.assertEqual(collector_host('12'), 'cato-account-12')

    def test_template_name_stable(self):
        self.assertEqual(self.tpl['name'], TEMPLATE_NAME)

    def test_all_item_prototypes_have_site_tag(self):
        for rule in self.tpl['discovery_rules']:
            for item in rule.get('item_prototypes') or []:
                tags = {row['tag']: row['value'] for row in item.get('tags') or []}
                self.assertEqual(tags.get('site'), '{#SITE.NAME}', item['key'])
                self.assertEqual(tags.get('connection_type'), '{#CONN.TYPE}', item['key'])

    def test_site_degraded_depends_on_disconnected(self):
        site = next(rule for rule in self.tpl['discovery_rules'] if rule['key'] == 'cato.site.discovery')
        deg = next(item for item in site['item_prototypes'] if item['key'] == 'cato.site.degraded[{#SITE.ID}]')
        trigger = deg['trigger_prototypes'][0]
        self.assertEqual(trigger['name'], 'Cato site {#SITE.NAME}: Degraded')
        self.assertEqual(trigger['priority'], 'AVERAGE')
        self.assertIn('cato.site.connected', trigger['expression'])
        deps = {row['name'] for row in trigger.get('dependencies') or []}
        self.assertIn('Cato site {#SITE.NAME}: Disconnected', deps)

    def test_navigators_group_by_site_not_serial(self):
        expected = EXPECTED_DASHBOARD_NAVIGATOR_GROUPS
        found: dict[tuple[str, str, str], list[str]] = {}
        for dash in self.tpl['dashboards']:
            for page in dash['pages']:
                for widget in page['widgets']:
                    if widget['type'] != 'itemnavigator':
                        continue
                    fields = {field['name']: field['value'] for field in widget['fields']}
                    tags = []
                    idx = 0
                    while f'group_by.{idx}.tag_name' in fields:
                        tags.append(fields[f'group_by.{idx}.tag_name'])
                        idx += 1
                    key = (dash['name'], page['name'], str(widget.get('name')))
                    found[key] = tags
                    self.assertEqual(tags[0], 'site', key)
                    self.assertNotIn('serial', tags, key)
        self.assertEqual(found, expected)

    def test_health_degraded_and_network_ports_pages(self):
        health = next(dash for dash in self.tpl['dashboards'] if dash['name'] == 'Health')
        degraded = next(page for page in health['pages'] if page['name'] == 'Degraded')
        self.assertIn('Degraded', [widget['name'] for widget in degraded['widgets']])
        network = next(dash for dash in self.tpl['dashboards'] if dash['name'] == 'Network')
        ports = next(page for page in network['pages'] if page['name'] == 'Ports')
        honey = [widget for widget in ports['widgets'] if widget['type'] == 'honeycomb']
        self.assertEqual([widget['name'] for widget in honey], ['WAN media', 'LAN media'])
        self.assertEqual(str(honey[0]['width']), '36')
        self.assertEqual(str(honey[1]['width']), '36')
        self.assertEqual(str(honey[1].get('x')), '36')
        graphs = [widget for widget in ports['widgets'] if widget['type'] == 'graphprototype']
        self.assertEqual([widget['name'] for widget in graphs], ['WAN traffic', 'LAN traffic'])
        wan_fields = {field['name']: field['value'] for field in graphs[0]['fields']}
        lan_fields = {field['name']: field['value'] for field in graphs[1]['fields']}
        self.assertEqual(
            wan_fields['graphid.0']['name'],
            'Cato WAN {#SITE.NAME} / {#LINK.NAME}: Bandwidth',
        )
        self.assertEqual(
            lan_fields['graphid.0']['name'],
            'Cato LAN {#SITE.NAME} / {#PORT.ID}: Bandwidth',
        )

    def test_tunnels_char_identity_uses_latest_not_graph(self):
        network = next(dash for dash in self.tpl['dashboards'] if dash['name'] == 'Network')
        tunnels = next(page for page in network['pages'] if page['name'] == 'Tunnels')
        navs = {
            str(widget.get('name')): widget
            for widget in tunnels['widgets']
            if widget['type'] == 'itemnavigator'
        }
        self.assertEqual(set(navs), {'Tunnels', 'Details'})
        tunnel_items = [
            field['value']
            for field in navs['Tunnels']['fields']
            if str(field['name']).startswith('items.')
        ]
        detail_items = [
            field['value']
            for field in navs['Details']['fields']
            if str(field['name']).startswith('items.')
        ]
        self.assertEqual(tunnel_items, ['Cato WAN *: Connectivity', 'Cato WAN *: Tunnel uptime'])
        self.assertIn('Cato WAN *: ISP provider', detail_items)
        self.assertNotIn('ISP provider', ' '.join(tunnel_items))
        graphs = [widget for widget in tunnels['widgets'] if widget['type'] == 'svggraph']
        latest = [widget for widget in tunnels['widgets'] if widget['type'] == 'item']
        self.assertEqual(len(graphs), 1)
        self.assertEqual(len(latest), 1)
        graph_fields = {field['name']: field['value'] for field in graphs[0]['fields']}
        latest_fields = {field['name']: field['value'] for field in latest[0]['fields']}
        self.assertEqual(graph_fields['ds.0.itemids.0._reference'], 'CNNAV._itemid')
        self.assertEqual(latest_fields['itemid._reference'], 'CNDET._itemid')
        self.assertNotIn('show.2', latest_fields)

    def test_dynamic_item_widgets_use_documented_item_reference_field(self):
        expected = EXPECTED_DASHBOARD_ITEM_REFERENCES
        actual = {}
        invalid = []
        for dashboard in self.tpl['dashboards']:
            for page in dashboard['pages']:
                for widget in page['widgets']:
                    if widget['type'] != 'item':
                        continue
                    fields = {
                        field['name']: field['value'] for field in widget['fields']
                    }
                    key = (dashboard['name'], page['name'], widget['name'])
                    if 'itemid._reference' in fields:
                        actual[key] = fields['itemid._reference']
                    if 'itemid.0._reference' in fields:
                        invalid.append(key)
        self.assertEqual(actual, expected)
        self.assertEqual(invalid, [])

    def test_worst_rollup_seeds_exist(self):
        keys = {item['key'] for item in self.tpl['items']}
        for key in (
            'cato.wan.loss.max.pct[__seed]',
            'cato.wan.lastmile.loss.pct[__seed]',
            'cato.wan.lastmile.latency.ms[__seed]',
            'cato.wan.rx.util.pct[__seed]',
            'cato.wan.tx.util.pct[__seed]',
        ):
            self.assertIn(key, keys)

    def test_standby_wan_tunnel_trigger_requires_active_port(self):
        ports = next(
            rule for rule in self.tpl['discovery_rules'] if rule['key'] == 'cato.port.discovery'
        )
        tunnel = next(
            item for item in ports['item_prototypes'] if 'has_tunnel[' in item['key']
        )
        names = {trigger['name'] for trigger in tunnel.get('trigger_prototypes') or []}
        self.assertIn(
            'Cato wan port {#SITE.NAME} / {#SERIAL} / {#PORT.ID}: No tunnel while media is up',
            names,
        )
        expr = tunnel['trigger_prototypes'][0]['expression']
        self.assertIn('{#TUNNEL.ALERT}=1', expr)

    def test_optional_identity_char_does_not_throw(self):
        optional = char_from_path_js('var found = {};\n', 'found.provider', 'provider', optional=True)
        required = char_from_path_js('var found = {};\n', 'found.provider', 'provider')
        self.assertIn("return '';", optional)
        self.assertNotIn("throw 'provider missing'", optional)
        self.assertIn("throw 'provider missing'", required)
        wan = next(rule for rule in self.tpl['discovery_rules'] if rule['key'] == 'cato.wan.discovery')
        prov = next(item for item in wan['item_prototypes'] if 'cato.wan.provider[' in item['key'])
        self.assertIn("return '';", _js(prov))
        self.assertNotIn("throw 'provider missing'", _js(prov))


class CatoLldJsTests(unittest.TestCase):
    def test_sites_filter_socket_and_drop_ipsec(self):
        rows = run_lld_js(load_lld_js('cato.site.discovery'), json.dumps(SNAPSHOT_FIXTURE))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['{#SITE.NAME}'], 'Zurich')
        self.assertEqual(rows[0]['{#IS.HA}'], '1')
        self.assertTrue(all(not row['{#CONN.TYPE}'].startswith('IPSEC') for row in rows))

    def test_sockets_ha_roles_and_site_name(self):
        rows = run_lld_js(load_lld_js('cato.socket.discovery'), json.dumps(SNAPSHOT_FIXTURE))
        by_serial = {row['{#SERIAL}']: row for row in rows}
        self.assertEqual(set(by_serial), {'SOCK-A', 'SOCK-B'})
        self.assertEqual(by_serial['SOCK-A']['{#HA.ROLE}'], 'MASTER')
        self.assertEqual(by_serial['SOCK-B']['{#HA.ROLE}'], 'BACKUP')
        self.assertEqual(by_serial['SOCK-A']['{#SITE.NAME}'], 'Zurich')
        self.assertNotIn('IPSEC-1', by_serial)

    def test_wan_snapshot_is_per_socket(self):
        rows = run_lld_js(load_lld_js('cato.wan.discovery'), json.dumps(SNAPSHOT_FIXTURE))
        self.assertEqual(len(rows), 3)
        labels = {(row['{#SERIAL}'], row['{#LINK.NAME}']) for row in rows}
        self.assertEqual(labels, {('SOCK-A', 'WAN1'), ('SOCK-A', 'WAN2'), ('SOCK-B', 'WAN1')})

    def test_wan_metrics_ha_merge(self):
        rows = run_lld_js(load_lld_js('cato.wan.metrics.discovery'), json.dumps(METRICS_FIXTURE))
        self.assertEqual(len(rows), 2)
        self.assertEqual({row['{#LINK.NAME}'] for row in rows}, {'WAN1', 'WAN2'})
        self.assertTrue(all('{#SERIAL}' not in row for row in rows))
        self.assertEqual({row['{#DEST.TYPE}'] for row in rows}, {'CATO'})

    def test_usb_ports_and_wans_are_excluded(self):
        ports = run_lld_js(load_lld_js('cato.port.discovery'), json.dumps(SNAPSHOT_FIXTURE))
        wans = run_lld_js(load_lld_js('cato.wan.discovery'), json.dumps(SNAPSHOT_FIXTURE))
        sla = run_lld_js(load_lld_js('cato.wan.metrics.discovery'), json.dumps(METRICS_FIXTURE))
        lan = run_lld_js(load_lld_js('cato.lan.metrics.discovery'), json.dumps(METRICS_FIXTURE))
        self.assertTrue(all('USB' not in row['{#PORT.ID}'].upper() for row in ports))
        self.assertTrue(all('USB' not in row['{#LINK.NAME}'].upper() for row in wans))
        self.assertTrue(all('USB' not in row['{#LINK.NAME}'].upper() for row in sla))
        self.assertTrue(all('USB' not in row['{#PORT.ID}'].upper() for row in lan))
        self.assertEqual(len(wans), 3)
        self.assertEqual(len(sla), 2)
        self.assertTrue(is_usb_identity('USB', 'WAN USB'))
        self.assertFalse(is_usb_identity('WAN1', 'LTE'))
        rows = run_lld_js(load_lld_js('cato.port.discovery'), json.dumps(SNAPSHOT_FIXTURE))
        labels = {(row['{#SERIAL}'], row['{#PORT.ID}'], row['{#PORT.KIND}']) for row in rows}
        self.assertEqual(
            labels,
            {
                ('SOCK-A', 'WAN1', 'wan'),
                ('SOCK-A', 'WAN2', 'wan'),
                ('SOCK-A', 'LAN1', 'lan'),
                ('SOCK-B', 'WAN1', 'wan'),
            },
        )
        by_port = {(row['{#SERIAL}'], row['{#PORT.ID}']): row['{#TUNNEL.ALERT}'] for row in rows}
        self.assertEqual(by_port[('SOCK-A', 'WAN1')], '1')
        self.assertEqual(by_port[('SOCK-A', 'WAN2')], '0')
        self.assertEqual(by_port[('SOCK-A', 'LAN1')], '0')
        self.assertTrue(all(row['{#SITE.NAME}'] == 'Zurich' for row in rows))
        self.assertEqual({row['{#HA.ROLE}'] for row in rows}, {'MASTER', 'BACKUP'})

    def test_wan_snapshot_carries_dest_type_and_cma_ha_role(self):
        rows = run_lld_js(load_lld_js('cato.wan.discovery'), json.dumps(SNAPSHOT_FIXTURE))
        self.assertTrue(all(row['{#DEST.TYPE}'] == 'CATO' for row in rows))
        self.assertEqual({row['{#HA.ROLE}'] for row in rows}, {'MASTER', 'BACKUP'})

    def test_missing_snapshot_returns_empty(self):
        empty = json.dumps({'data': {}})
        for key in (
            'cato.site.discovery',
            'cato.socket.discovery',
            'cato.wan.discovery',
            'cato.port.discovery',
        ):
            self.assertEqual(run_lld_js(load_lld_js(key), empty), [])

    def test_lan_metrics_keeps_socket_lan_and_converts_bytes_to_bits(self):
        rows = run_lld_js(load_lld_js('cato.lan.metrics.discovery'), json.dumps(METRICS_FIXTURE))
        by_port = {row['{#PORT.ID}']: row for row in rows}
        self.assertEqual(set(by_port), {'LAN1', 'LAN2'})
        self.assertEqual(by_port['LAN1']['{#SITE.NAME}'], 'Zurich')
        self.assertEqual(by_port['LAN1']['{#PORT.KIND}'], 'lan')
        self.assertEqual(by_port['LAN1']['{#TRANSPORT}'], 'LAN')
        self.assertEqual(by_port['LAN2']['{#TRANSPORT}'], 'wired')
        self.assertTrue(all(row['{#CONN.TYPE}'].startswith('SOCKET_') for row in rows))
        self.assertFalse(is_lan_transport('WAN', 'WAN1'))
        self.assertTrue(is_lan_transport('LAN', 'LAN1'))
        self.assertTrue(is_lan_transport('wired', 'LAN2'))
        self.assertFalse(is_lan_transport('LAN', 'USB1'))
        lan = next(
            rule
            for rule in _template()['discovery_rules']
            if rule['key'] == 'cato.lan.metrics.discovery'
        )
        rx = next(item for item in lan['item_prototypes'] if item['key'].startswith('cato.lan.rx.bps['))
        tx = next(item for item in lan['item_prototypes'] if item['key'].startswith('cato.lan.tx.bps['))
        rx_js = _js(rx).replace('{#SITE.ID}', '10').replace('{#PORT.ID}', 'LAN1')
        tx_js = _js(tx).replace('{#SITE.ID}', '10').replace('{#PORT.ID}', 'LAN1')
        payload = json.dumps(METRICS_FIXTURE)
        self.assertEqual(run_lld_js(rx_js, payload), 160)
        self.assertEqual(run_lld_js(tx_js, payload), 80)

    def test_missing_metrics_returns_empty_lan(self):
        empty = json.dumps({'data': {}})
        self.assertEqual(run_lld_js(load_lld_js('cato.wan.metrics.discovery'), empty), [])
        self.assertEqual(run_lld_js(load_lld_js('cato.lan.metrics.discovery'), empty), [])

    def test_invalid_json_throws(self):
        with self.assertRaises(RuntimeError):
            run_lld_js(load_lld_js('cato.site.discovery'), 'not-json')

    def test_python_census_matches_lld_counts(self):
        census = snapshot_census(SNAPSHOT_FIXTURE)
        self.assertEqual(census, {'sites': 1, 'sockets': 2, 'wan_rows': 3})
        self.assertEqual(metrics_sla_census(METRICS_FIXTURE), 2)
        self.assertEqual(metrics_lan_census(METRICS_FIXTURE), 2)
        self.assertEqual(snapshot_socket_serials(SNAPSHOT_FIXTURE), {'SOCK-A', 'SOCK-B'})
        self.assertEqual(
            normalize_socket_serial('08:35:71:ff:94:6d'),
            '08:35:71:FF:94:6D',
        )


class CatoUsbRetirementTests(unittest.TestCase):
    class _Api:
        def __init__(self):
            self.deleted: list[list[str]] = []
            self.items = [
                {
                    'itemid': '10',
                    'name': 'Cato wan port Site / Serial / USB2: Link up',
                    'key_': 'cato.port.up[10,serial,USB2]',
                    'flags': '4',
                    'discoveryRule': {'key_': 'cato.port.discovery'},
                },
                {
                    'itemid': '2',
                    'name': 'Cato lan port Site / Serial / USB1: Media in',
                    'key_': 'cato.port.media_in[10,serial,USB1]',
                    'flags': '4',
                    'discoveryRule': {'key_': 'cato.port.discovery'},
                },
                {
                    'itemid': '3',
                    'name': 'Cato wan port USB Site / Serial / WAN1: Link up',
                    'key_': 'cato.port.up[10,serial,WAN1]',
                    'flags': '4',
                    'discoveryRule': {'key_': 'cato.port.discovery'},
                },
                {
                    'itemid': '4',
                    'name': 'Cato wan port Site / Serial / USB1: Link up',
                    'key_': 'cato.port.up[10,serial,USB1]',
                    'flags': '0',
                    'discoveryRule': {'key_': 'cato.port.discovery'},
                },
                {
                    'itemid': '5',
                    'name': 'Cato wan port Site / Serial / USB1: Link up',
                    'key_': 'cato.port.up[10,serial,USB1]',
                    'flags': '4',
                    'discoveryRule': {'key_': 'other.discovery'},
                },
            ]

        def call(self, method, params):
            if method == 'item.get':
                return self.items
            self.assertEqual(method, 'item.delete')
            self.deleted.append(params)
            return {'itemids': params}

        def assertEqual(self, left, right):
            if left != right:
                raise AssertionError(f'{left!r} != {right!r}')

    def test_retires_only_discovered_usb_port_items(self):
        api = self._Api()
        self.assertEqual(_legacy_usb_port_itemids(api, '42'), ['2', '10'])
        self.assertEqual(retire_legacy_usb_port_items(api, '42'), 2)
        self.assertEqual(api.deleted, [['2', '10']])


class CatoApplyWiringTests(unittest.TestCase):
    def test_network_script_documents_apply_cato(self):
        src = (ROOT / 'scripts/configure_nbxsync_network.py').read_text(encoding='utf-8')
        self.assertIn('--apply-cato', src)
        self.assertIn('--check-cato', src)
        self.assertIn('run_apply_cato', src)
        self.assertIn('collect_cato_preflight', src)
        self.assertIn('skip_preflight', src)

    def test_zerotouch_is_not_the_collector_refresh(self):
        src = (ROOT / 'scripts/configure_nbxsync_zerotouch.py').read_text(encoding='utf-8')
        self.assertNotIn('--apply-cato', src)
        self.assertNotIn('apply_cato_pack', src)


if __name__ == '__main__':
    unittest.main()
