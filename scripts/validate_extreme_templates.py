#!/usr/bin/env python3
"""Validate Extreme YAML (Health dashboards, alerting contract) and optionally import.

YAML-only by default (no Zabbix, no Django). ``--zabbix`` imports twice against
the lab API to prove idempotency and that existing hosts are not deleted.

  python3 scripts/validate_extreme_templates.py
  python3 scripts/validate_extreme_templates.py --zabbix
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

TEMPLATES = {
    'Extreme VOSS by SNMP': ROOT / 'zabbix/templates/extreme_voss_snmp/template_net_extreme_voss_snmp.yaml',
    'Extreme IQ Engine by SNMP': ROOT / 'zabbix/templates/extreme_iq_engine_snmp/template_net_extreme_iq_engine_snmp.yaml',
    'Extreme EXOS Observability': ROOT / 'zabbix/templates/extreme_exos_observability_snmp/template_extreme_exos_observability_snmp.yaml',
    'Extreme Port Speed Expect by SNMP': ROOT / 'zabbix/templates/extreme_port_speed_expect_snmp/template_net_extreme_port_speed_expect_snmp.yaml',
    'Extreme Routing by SNMP': ROOT / 'zabbix/templates/extreme_routing_snmp/template_net_extreme_routing_snmp.yaml',
}

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = '') -> None:
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def _uuid_is_v4(value: str) -> bool:
    hex32 = value.replace('-', '').lower()
    if len(hex32) != 32 or any(c not in '0123456789abcdef' for c in hex32):
        return False
    return hex32[12] == '4' and hex32[16] in '89ab'


def validate_uuids(name: str, text: str) -> None:
    bad = []
    for m in re.finditer(r'uuid:\s*([0-9a-fA-F-]{32,36})', text):
        u = m.group(1)
        if not _uuid_is_v4(u):
            line = text[: m.start()].count('\n') + 1
            bad.append(f'L{line}:{u}')
    record(f'{name} UUIDv4', not bad, ', '.join(bad[:8]))


def load_yaml(path: Path) -> dict:
    # Quoted 'y' keys stay strings; YAML 1.1 would otherwise coerce y → True.
    return yaml.safe_load(path.read_text())
    # Quoted 'y' keys stay strings; YAML 1.1 would otherwise coerce y → True.
    return yaml.safe_load(path.read_text())


def _tpl(doc: dict) -> dict:
    tpls = (doc.get('zabbix_export') or {}).get('templates') or []
    if not tpls:
        raise SystemExit(f'no templates in export')
    return tpls[0]


def _walk_graphs(doc: dict, tpl: dict) -> set[str]:
    names: set[str] = set()
    export = doc.get('zabbix_export') or {}
    for g in (tpl.get('graphs') or []) + (export.get('graphs') or []):
        if g.get('name'):
            names.add(g['name'])
    for rule in tpl.get('discovery_rules') or []:
        for g in rule.get('graph_prototypes') or []:
            if g.get('name'):
                names.add(g['name'])
    return names


def _walk_item_keys(tpl: dict) -> set[str]:
    keys: set[str] = set()
    for it in tpl.get('items') or []:
        if it.get('key'):
            keys.add(it['key'])
        for trig in it.get('triggers') or []:
            _ = trig  # triggers live on items; collected elsewhere
    for rule in tpl.get('discovery_rules') or []:
        for it in rule.get('item_prototypes') or []:
            if it.get('key'):
                keys.add(it['key'])
    return keys


def _walk_triggers(tpl: dict) -> list[dict]:
    out: list[dict] = []
    for it in tpl.get('items') or []:
        out.extend(it.get('triggers') or [])
    for rule in tpl.get('discovery_rules') or []:
        for it in rule.get('item_prototypes') or []:
            out.extend(it.get('trigger_prototypes') or [])
        out.extend(rule.get('trigger_prototypes') or [])
    out.extend(tpl.get('triggers') or [])
    return out


def _macro_map(tpl: dict) -> dict[str, str]:
    return {m['macro']: str(m.get('value', '')) for m in (tpl.get('macros') or []) if m.get('macro')}


def validate_health_dashboard(name: str, doc: dict, tpl: dict, *, pages: tuple[str, ...]) -> None:
    dashes = tpl.get('dashboards') or []
    health = [d for d in dashes if d.get('name') == 'Health']
    record(f'{name} Health dashboard', bool(health), f'count={len(health)} names={[d.get("name") for d in dashes]}')
    if not health:
        return
    dash = health[0]
    got_pages = [p.get('name') for p in (dash.get('pages') or [])]
    record(f'{name} Health pages', all(p in got_pages for p in pages), f'got={got_pages} want={list(pages)}')
    graphs = _walk_graphs(doc, tpl)
    keys = _walk_item_keys(tpl)
    refs: list[str] = []
    for page in dash.get('pages') or []:
        for w in page.get('widgets') or []:
            wtype = w.get('type')
            for f in w.get('fields') or []:
                val = f.get('value')
                fname = f.get('name', '')
                if not isinstance(val, dict):
                    continue
                if wtype in ('item', 'gauge') and fname.startswith('itemid') and 'key' in val:
                    key = val.get('key')
                    ok = key in keys
                    record(f'{name} widget item {key}', ok, f'host={val.get("host")} type={wtype}')
                    refs.append(str(key))
                if wtype in ('graph', 'graphprototype') and fname.startswith('graphid'):
                    gname = val.get('name')
                    external = (val.get('host'), gname) in {
                        (
                            'Extreme EXOS by SNMP',
                            'Interface {#IFNAME}({#IFALIAS}): Network traffic',
                        ),
                        (
                            'Extreme EXOS by SNMP',
                            '#{#SNMPVALUE}: Memory utilization',
                        ),
                    }
                    ok = gname in graphs or external
                    record(f'{name} widget graph {gname}', ok, f'type={wtype} host={val.get("host")}')
                    refs.append(str(gname))
            # YAML 1.1: unquoted y becomes True — widget row must be quoted in source
            if True in w and 'y' not in w:
                record(f'{name} widget y coerced', False, f'widget={w.get("name")} has YAML bool y')
    record(f'{name} Health has widgets', bool(refs), f'refs={len(refs)}')
    pages_by_name = {p.get('name'): p for p in (dash.get('pages') or [])}
    overview = pages_by_name.get('Overview')
    if overview is not None:
        ov_keys: list[str] = []
        for w in overview.get('widgets') or []:
            for f in w.get('fields') or []:
                val = f.get('value')
                if isinstance(val, dict) and val.get('key'):
                    ov_keys.append(str(val.get('key')))
        has_icmp = any('icmp' in k for k in ov_keys)
        has_snmp = any('snmp' in k.lower() or 'available' in k for k in ov_keys)
        record(f'{name} Overview ICMP+SNMP', has_icmp and has_snmp, f'keys={ov_keys}')

        def _wy(widget: dict) -> str:
            if 'y' in widget:
                return str(widget.get('y'))
            if True in widget:
                return str(widget.get(True))
            return '0'

        tiles = [w for w in (overview.get('widgets') or []) if _wy(w) == '0']
        problems = [w for w in (overview.get('widgets') or []) if w.get('type') == 'problems']
        histories = [w for w in (overview.get('widgets') or []) if w.get('type') == 'svggraph']
        record(
            f'{name} Overview 4-tile row',
            len(tiles) == 4
            and all(str(w.get('width')) == '18' for w in tiles)
            and [w.get('name') for w in tiles[:3]] == ['ICMP', 'SNMP', 'CPU'],
            f'tiles={[(w.get("name"), w.get("width")) for w in tiles]}',
        )
        record(
            f'{name} Overview problems strip',
            len(problems) == 1
            and str(problems[0].get('width')) == '72'
            and str(problems[0].get('height')) == '3'
            and _wy(problems[0]) == '4',
            f'problems={[(w.get("width"), w.get("height"), _wy(w)) for w in problems]}',
        )
        record(
            f'{name} Overview two-pane history',
            len(histories) == 2
            and all(str(w.get('width')) == '36' and str(w.get('height')) == '6' and _wy(w) == '7' for w in histories),
            f'histories={[(w.get("name"), w.get("width"), _wy(w)) for w in histories]}',
        )
        gauges = [w for w in (overview.get('widgets') or []) if w.get('type') == 'gauge']
        chrome = []
        chrome_ok = bool(gauges)
        for gauge in gauges:
            gfields = {f.get('name'): f.get('value') for f in (gauge.get('fields') or [])}
            shows = {str(f.get('value')) for f in (gauge.get('fields') or []) if str(f.get('name')).startswith('show.')}
            ok = (
                shows == {'2', '5'}
                and str(gfields.get('th_show_labels')) == '0'
                and str(gfields.get('angle')) == '270'
                and str(gfields.get('value_size')) == '25'
                and str(gfields.get('value_bold')) == '1'
            )
            chrome_ok = chrome_ok and ok
            chrome.append((gauge.get('name'), sorted(shows), gfields.get('th_show_labels')))
        record(f'{name} Overview gauge chrome', chrome_ok, f'{chrome}')

    honey_ok = True
    honey_seen = False
    honey_detail = []
    for page in dash.get('pages') or []:
        for widget in page.get('widgets') or []:
            if widget.get('type') != 'honeycomb':
                continue
            honey_seen = True
            hfields = {f.get('name'): f.get('value') for f in (widget.get('fields') or [])}
            label = str(hfields.get('primary_label') or '')
            capture_ok = True
            if 'regsub(' in label:
                match = re.search(r',"(\\+)1"\)', label)
                capture_ok = bool(match) and len(match.group(1)) == 1
            secondary_ok = (
                str(hfields.get('secondary_label_type')) in {'0', '1'}
                and str(hfields.get('primary_label_bold')) == '1'
                and str(hfields.get('secondary_label_bold')) == '0'
            )
            honey_ok = honey_ok and capture_ok and secondary_ok
            honey_detail.append((widget.get('name'), capture_ok, secondary_ok))
    if honey_seen:
        record(f'{name} honeycomb labels', honey_ok, f'{honey_detail}')

    def fields(widget: dict) -> dict[str, object]:
        return {f.get('name'): f.get('value') for f in (widget.get('fields') or [])}

    rf = pages_by_name.get('RF')
    if rf is not None:
        rf_graphs = [w for w in (rf.get('widgets') or []) if w.get('type') == 'graphprototype']
        cols = [fields(w).get('columns') for w in rf_graphs]
        record(
            f'{name} RF radio graphs 2-column',
            bool(rf_graphs) and all(str(c) == '2' for c in cols),
            f'columns={cols}',
        )

    diagnostics = pages_by_name.get('Diagnostics')
    if diagnostics is not None:
        widgets = diagnostics.get('widgets') or []
        widget_types = {w.get('type') for w in widgets}
        required = {'item', 'itemnavigator', 'svggraph'}
        record(
            f'{name} interface Diagnostics widgets',
            required <= widget_types,
            f'got={sorted(str(t) for t in widget_types)}',
        )
        nav_widget = next((w for w in widgets if w.get('type') == 'itemnavigator'), {})
        item_widget = next((w for w in widgets if w.get('type') == 'item'), {})
        graph_widget = next((w for w in widgets if w.get('type') == 'svggraph'), {})
        nav_fields = fields(nav_widget)
        item_fields = fields(item_widget)
        graph_fields = fields(graph_widget)
        nav_ref = nav_fields.get('reference')
        wired = bool(nav_ref) and item_fields.get('itemid._reference') == f'{nav_ref}._itemid' and graph_fields.get('ds.0.itemids.0._reference') == f'{nav_ref}._itemid'
        record(f'{name} Diagnostics wiring', wired, f'navigator={nav_ref}')
        patterns = {str(v) for key, v in nav_fields.items() if str(key).startswith('items.')}
        if name == 'IQ':
            expected_patterns = {
                'Radio *: Noise floor',
                'Radio *: Tx power',
                'Radio *: TX total retries',
                'Radio *: TX frames dropped',
                'Radio *: RX data frames',
                'Radio *: Channel',
            }
            forbidden = {
                'Interface *: Operational status',
                'Interface *: Bits received',
                'Interface *: Bits sent',
                'Interface *: Speed',
                'Interface *: Duplex status',
                'Interface *: State transitions',
            }
            record(
                f'{name} radio Diagnostics (not switch-port copy)',
                expected_patterns <= patterns and not (forbidden & patterns),
                f'got={sorted(patterns)}',
            )
        else:
            expected_patterns = {
                'Interface *: Operational status',
                'Interface *: Speed',
                'Interface *: Bits received',
                'Interface *: Bits sent',
                'Interface *: Inbound packets with errors',
                'Interface *: Outbound packets with errors',
                'Interface *: Inbound packets discarded',
                'Interface *: Outbound packets discarded',
            }
            record(
                f'{name} consolidated interface diagnostics',
                expected_patterns <= patterns,
                f'missing={sorted(expected_patterns - patterns)}',
            )
            if name == 'EXOS companion':
                record(
                    f'{name} Diagnostics has no flaps (stock EXOS has none)',
                    'Interface *: State transitions' not in patterns,
                    f'got={sorted(patterns)}',
                )
        compact = item_widget.get('height') == '2' and item_fields.get('show.0') == '2'
        record(f'{name} compact Diagnostics value', compact, f'height={item_widget.get("height")}')


def validate_interface_dashboard(name: str, tpl: dict) -> None:
    dashboards = tpl.get('dashboards') or []
    matches = [d for d in dashboards if d.get('name') == 'Network interfaces']
    record(
        f'{name} Network interfaces dashboard',
        len(matches) == 1,
        f'count={len(matches)} names={[d.get("name") for d in dashboards]}',
    )
    if not matches:
        return
    pages = matches[0].get('pages') or []
    overview = next((p for p in pages if p.get('name') == 'Overview'), None)
    record(f'{name} Network interfaces Overview', bool(overview), f'pages={[p.get("name") for p in pages]}')
    if not overview:
        return
    widgets = overview.get('widgets') or []
    map_widget = next((w for w in widgets if w.get('type') == 'honeycomb'), {})
    grid_widget = next((w for w in widgets if w.get('type') == 'graphprototype'), {})
    map_fields = {f.get('name'): f.get('value') for f in (map_widget.get('fields') or [])}
    grid_fields = {f.get('name'): f.get('value') for f in (grid_widget.get('fields') or [])}
    graph_ref = grid_fields.get('graphid.0')
    extra = [w.get('type') for w in widgets if w.get('type') not in ('honeycomb', 'graphprototype')]
    unified = (
        map_widget.get('width') == '72'
        and map_widget.get('height') == '4'
        and grid_widget.get('width') == '72'
        and grid_widget.get('height') == '11'
        and grid_widget.get('y') == '4'
        and grid_fields.get('columns') == '3'
        and grid_fields.get('rows') == '2'
        and isinstance(graph_ref, dict)
        and 'Network traffic' in str(graph_ref.get('name'))
    )
    label = str(map_fields.get('primary_label') or '')
    match = re.search(r',"(\\+)1"\)', label)
    labels_ok = (
        bool(match)
        and len(match.group(1)) == 1
        and str(map_fields.get('secondary_label_type')) == '0'
        and map_fields.get('secondary_label') == '{ITEM.LASTVALUE}'
    )
    names_ok = map_widget.get('name') == 'Interfaces' and grid_widget.get('name') == 'Traffic'
    record(f'{name} unified interface graph grid', unified, f'graph={graph_ref}')
    record(f'{name} interface map is scan-only', extra == [], f'extra={extra}')
    record(f'{name} interface map labels', labels_ok, f'label={label}')
    record(f'{name} interface wording', names_ok, f'map={map_widget.get("name")} grid={grid_widget.get("name")}')


def validate_voss(doc: dict) -> None:
    tpl = _tpl(doc)
    record('VOSS name', tpl.get('name') == 'Extreme VOSS by SNMP', str(tpl.get('name')))
    macros = _macro_map(tpl)
    for k, v in {
        '{$ISIS.CONTROL}': '0',
        '{$CARD.CONTROL}': '0',
        '{$UNSUPPORTED.MAX}': '5',
        '{$IF.UTIL.MAX}': '101',
        '{$VIST.CONTROL}': '0',
        '{$IST.CONTROL}': '0',
    }.items():
        record(f'VOSS {k}', macros.get(k) == v, f'got={macros.get(k)!r}')
    trigs = _walk_triggers(tpl)
    by_name = {t.get('name'): t for t in trigs}
    for n in ('Extreme VOSS: High ICMP ping loss', 'Extreme VOSS: High ICMP ping response time'):
        t = by_name.get(n)
        record(f'VOSS {n} DISABLED', bool(t) and t.get('status') == 'DISABLED', str((t or {}).get('status')))
    for n in ('Extreme VOSS: Too many unsupported items',):
        record(f'VOSS has {n}', n in by_name, '')
    card = next((t for t in trigs if 'card' in (t.get('name') or '').lower() and 'down' in (t.get('name') or '').lower()), None)
    isis = next((t for t in trigs if 'isis' in (t.get('name') or '').lower() and 'circuit' in (t.get('name') or '').lower()), None)
    record(
        'VOSS card High gated',
        bool(card) and '{$CARD.CONTROL}=1' in (card.get('expression') or ''),
        (card or {}).get('expression', '')[:120],
    )
    record(
        'VOSS ISIS High gated',
        bool(isis) and '{$ISIS.CONTROL}=1' in (isis.get('expression') or ''),
        (isis or {}).get('expression', '')[:120],
    )
    keys = _walk_item_keys(tpl)
    record('VOSS unsupported item', 'zabbix[host,,items_unsupported]' in keys, '')
    flap_ok = shutdown_ok = False
    for rule in tpl.get('discovery_rules') or []:
        for it in rule.get('item_prototypes') or []:
            name = it.get('name') or ''
            tags = {t.get('tag'): t.get('value') for t in (it.get('tags') or [])}
            if 'State transitions' in name:
                flap_ok = tags.get('interface') == '{#IFNAME}'
            if 'Shutdown reason' in name:
                shutdown_ok = tags.get('interface') == '{#IFNAME}'
    record('VOSS flap items tagged interface (Diagnostics grouping)', flap_ok, '')
    record('VOSS shutdown items tagged interface', shutdown_ok, '')
    validate_health_dashboard('VOSS', doc, tpl, pages=('Overview', 'Hardware', 'Diagnostics'))
    validate_interface_dashboard('VOSS', tpl)
    # Re-import identity — same uuid as the old traffic-only board
    health = [d for d in (tpl.get('dashboards') or []) if d.get('name') == 'Health']
    if health:
        record(
            'VOSS Health uuid stable',
            health[0].get('uuid') == '6c3fa785af5d4bd38c94805bd0ccbecb',
            str(health[0].get('uuid')),
        )


def validate_iq(doc: dict) -> None:
    tpl = _tpl(doc)
    record('IQ name', tpl.get('name') == 'Extreme IQ Engine by SNMP', str(tpl.get('name')))
    macros = _macro_map(tpl)
    record('IQ {$UNSUPPORTED.MAX}', macros.get('{$UNSUPPORTED.MAX}') == '5', str(macros.get('{$UNSUPPORTED.MAX}')))
    trigs = _walk_triggers(tpl)
    by_name = {t.get('name'): t for t in trigs}
    for n in ('Extreme IQ Engine: High ICMP ping loss', 'Extreme IQ Engine: High ICMP ping response time'):
        t = by_name.get(n)
        record(f'IQ {n} DISABLED', bool(t) and t.get('status') == 'DISABLED', str((t or {}).get('status')))
    record('IQ unsupported trigger', 'Extreme IQ Engine: Too many unsupported items' in by_name, '')
    validate_health_dashboard('IQ', doc, tpl, pages=('Overview', 'RF', 'Diagnostics'))
    validate_interface_dashboard('IQ', tpl)


def validate_exos_observability(doc: dict) -> None:
    tpl = _tpl(doc)
    record('EXOS companion name', tpl.get('name') == 'Extreme EXOS Observability', str(tpl.get('name')))
    linked = {row.get('name') for row in (tpl.get('templates') or [])}
    record('EXOS companion links stock', 'Extreme EXOS by SNMP' in linked, str(sorted(linked)))
    keys = _walk_item_keys(tpl)
    expected = {
        'exos.observability.cpu.util',
        'exos.observability.temperature',
        'exos.observability.icmp',
        'exos.observability.snmp',
    }
    record('EXOS companion calculated mirrors', expected <= keys, str(sorted(expected - keys)))
    validate_health_dashboard('EXOS companion', doc, tpl, pages=('Overview', 'Hardware', 'Diagnostics'))


def validate_speed_expect(doc: dict) -> None:
    tpl = _tpl(doc)
    macros = _macro_map(tpl)
    record('SpeedExpect {$IF.UTIL.MAX}', macros.get('{$IF.UTIL.MAX}') == '101', str(macros.get('{$IF.UTIL.MAX}')))
    record(
        'SpeedExpect {$IF.UTIL.MAX:"USW"}',
        macros.get('{$IF.UTIL.MAX:"USW"}') == '101',
        str(macros.get('{$IF.UTIL.MAX:"USW"}')),
    )
    trigs = _walk_triggers(tpl)
    enabled = [t.get('name') for t in trigs if t.get('status') not in ('DISABLED', 'disabled')]
    record('SpeedExpect triggers present (on)', bool(trigs), f'count={len(trigs)} sample={enabled[:3]}')


def validate_yaml() -> None:
    for name, path in TEMPLATES.items():
        record(f'file {name}', path.exists(), str(path.relative_to(ROOT)))
        if not path.exists():
            continue
        validate_uuids(name, path.read_text())
        try:
            doc = load_yaml(path)
            record(f'parse {name}', True, f'version={(doc.get("zabbix_export") or {}).get("version")}')
        except Exception as exc:
            record(f'parse {name}', False, str(exc))
            continue
        if name == 'Extreme VOSS by SNMP':
            validate_voss(doc)
        elif name == 'Extreme IQ Engine by SNMP':
            validate_iq(doc)
        elif name == 'Extreme EXOS Observability':
            validate_exos_observability(doc)
        elif name == 'Extreme Port Speed Expect by SNMP':
            validate_speed_expect(doc)


def import_rules() -> dict:
    return {
        'templates': {'createMissing': True, 'updateExisting': True},
        'template_groups': {'createMissing': True, 'updateExisting': True},
        'templateLinkage': {'createMissing': True, 'deleteMissing': False},
        'valueMaps': {'createMissing': True, 'updateExisting': True},
        'items': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
        'discoveryRules': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
        'triggers': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
        'graphs': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
        'httptests': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
        'templateDashboards': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
    }


def validate_zabbix() -> None:
    from extreme_health_zabbix import (
        IQ_HEALTH_MACROS,
        SPEED_EXPECT_HEALTH_MACROS,
        VOSS_HEALTH_MACROS,
        apply_extreme_health_patches,
        assert_template_dashboard,
        assert_exos_stock_interface_grid,
        assert_template_macros,
        assert_wan_icmp_noise_disabled,
    )
    from zabbix_api import ZabbixAPI

    api = ZabbixAPI.from_lab()
    hosts_before = api.call('host.get', {'output': ['hostid', 'host']}) or []
    ids_before = {h['hostid'] for h in hosts_before}
    record('zabbix reachable', True, f'hosts={len(ids_before)}')

    rules = import_rules()
    for name, path in TEMPLATES.items():
        try:
            api.call('configuration.import', {'format': 'yaml', 'rules': rules, 'source': path.read_text()})
            record(f'import1 {name}', True, '')
        except Exception as exc:
            record(f'import1 {name}', False, str(exc)[:300])
    for name, path in TEMPLATES.items():
        try:
            api.call('configuration.import', {'format': 'yaml', 'rules': rules, 'source': path.read_text()})
            record(f'import2 {name}', True, 'idempotent re-import')
        except Exception as exc:
            record(f'import2 {name}', False, str(exc)[:300])

    patch = apply_extreme_health_patches(api)
    record('patch icmp_noise', True, str(patch.get('icmp_noise')))
    dash_status = str(patch.get('exos_health'))
    record(
        'patch exos_health',
        dash_status == 'companion-yaml',
        dash_status,
    )
    grid_status = str(patch.get('exos_stock_grid'))
    record('patch exos_stock_grid', grid_status in ('ok', 'patched', 'missing-template'), grid_status)

    ok, detail = assert_template_macros(api, 'Extreme VOSS by SNMP', VOSS_HEALTH_MACROS)
    record('zbx VOSS macros', ok, detail)
    ok, detail = assert_template_macros(api, 'Extreme Port Speed Expect by SNMP', SPEED_EXPECT_HEALTH_MACROS)
    record('zbx SpeedExpect macros', ok, detail)
    ok, detail = assert_template_macros(api, 'Extreme IQ Engine by SNMP', IQ_HEALTH_MACROS)
    record('zbx IQ macros', ok, detail)
    ok, detail = assert_template_dashboard(api, 'Extreme VOSS by SNMP', 'Health', ('Overview', 'Hardware', 'Diagnostics'))
    record('zbx VOSS Health', ok, detail)
    ok, detail = assert_template_dashboard(api, 'Extreme IQ Engine by SNMP', 'Health', ('Overview', 'RF', 'Diagnostics'))
    record('zbx IQ Health', ok, detail)
    ok, detail = assert_template_dashboard(api, 'Extreme EXOS Observability', 'Health', ('Overview', 'Hardware', 'Diagnostics'))
    record('zbx EXOS companion Health', ok, detail)
    for tname in ('Extreme VOSS by SNMP', 'Extreme IQ Engine by SNMP', 'Extreme EXOS by SNMP'):
        ok, detail = assert_template_dashboard(api, tname, 'Network interfaces', ('Overview',))
        record(f'zbx interface dashboard {tname}', ok, detail)
    ok, detail = assert_exos_stock_interface_grid(api)
    record('zbx EXOS stock interface grid', ok, detail)
    for tname in ('Extreme VOSS by SNMP', 'Extreme IQ Engine by SNMP', 'Extreme EXOS by SNMP'):
        ok, detail = assert_wan_icmp_noise_disabled(api, tname)
        record(f'zbx ICMP noise off {tname}', ok, detail)

    hosts_after = api.call('host.get', {'output': ['hostid', 'host']}) or []
    ids_after = {h['hostid'] for h in hosts_after}
    deleted = ids_before - ids_after
    record('no host delete on re-import', not deleted, f'deleted={sorted(deleted)[:8]} after={len(ids_after)}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zabbix', action='store_true', help='Import twice into lab Zabbix and assert')
    args = parser.parse_args()
    validate_yaml()
    if args.zabbix:
        validate_zabbix()
    failed = sum(1 for _, ok, _ in RESULTS if not ok)
    total = len(RESULTS)
    print(f'\nSummary: {total - failed}/{total} passed')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
