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
    'Extreme IQ Engine by SNMP': ROOT
    / 'zabbix/templates/extreme_iq_engine_snmp/template_net_extreme_iq_engine_snmp.yaml',
    'Extreme EXOS Observability': ROOT
    / 'zabbix/templates/extreme_exos_observability_snmp/template_extreme_exos_observability_snmp.yaml',
    'Extreme Port Speed Expect by SNMP': ROOT
    / 'zabbix/templates/extreme_port_speed_expect_snmp/template_net_extreme_port_speed_expect_snmp.yaml',
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
                if wtype == 'item' and fname.startswith('itemid'):
                    key = val.get('key')
                    ok = key in keys
                    record(f'{name} widget item {key}', ok, f'host={val.get("host")}')
                    refs.append(str(key))
                if wtype in ('graph', 'graphprototype') and fname.startswith('graphid'):
                    gname = val.get('name')
                    ok = gname in graphs
                    record(f'{name} widget graph {gname}', ok, f'type={wtype}')
                    refs.append(str(gname))
            # YAML 1.1: unquoted y becomes True — widget row must be quoted in source
            if True in w and 'y' not in w:
                record(f'{name} widget y coerced', False, f'widget={w.get("name")} has YAML bool y')
    record(f'{name} Health has widgets', bool(refs), f'refs={len(refs)}')
    traffic = next((p for p in (dash.get('pages') or []) if p.get('name') == 'Traffic'), None)
    if traffic is not None:
        widgets = traffic.get('widgets') or []
        widget_types = {w.get('type') for w in widgets}
        required = {'honeycomb', 'item', 'itemnavigator', 'svggraph'}
        record(
            f'{name} interactive Traffic widgets',
            required <= widget_types,
            f'got={sorted(str(t) for t in widget_types)}',
        )

        def fields(widget_type: str) -> dict[str, object]:
            widget = next((w for w in widgets if w.get('type') == widget_type), {})
            return {f.get('name'): f.get('value') for f in (widget.get('fields') or [])}

        map_fields = fields('honeycomb')
        item_fields = fields('item')
        nav_fields = fields('itemnavigator')
        graph_fields = fields('svggraph')
        map_ref = map_fields.get('reference')
        nav_ref = nav_fields.get('reference')
        wired = (
            bool(map_ref)
            and item_fields.get('itemid._reference') == f'{map_ref}._itemid'
            and bool(nav_ref)
            and graph_fields.get('ds.0.itemids.0._reference') == f'{nav_ref}._itemid'
        )
        record(f'{name} interactive Traffic wiring', wired, f'map={map_ref} navigator={nav_ref}')


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
    validate_health_dashboard('VOSS', doc, tpl, pages=('Overview', 'Hardware', 'Traffic'))
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
    validate_health_dashboard('IQ', doc, tpl, pages=('Overview', 'RF', 'Traffic'))


def validate_exos_observability(doc: dict) -> None:
    tpl = _tpl(doc)
    record('EXOS companion name', tpl.get('name') == 'Extreme EXOS Observability', str(tpl.get('name')))
    linked = {row.get('name') for row in (tpl.get('templates') or [])}
    record('EXOS companion links stock', 'Extreme EXOS by SNMP' in linked, str(sorted(linked)))
    keys = _walk_item_keys(tpl)
    expected = {
        'exos.observability.cpu.util',
        'exos.observability.temperature',
        'exos.observability.uptime',
    }
    record('EXOS companion calculated mirrors', expected <= keys, str(sorted(expected - keys)))
    validate_health_dashboard('EXOS companion', doc, tpl, pages=('Overview', 'Hardware', 'Traffic'))


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

    ok, detail = assert_template_macros(api, 'Extreme VOSS by SNMP', VOSS_HEALTH_MACROS)
    record('zbx VOSS macros', ok, detail)
    ok, detail = assert_template_macros(api, 'Extreme Port Speed Expect by SNMP', SPEED_EXPECT_HEALTH_MACROS)
    record('zbx SpeedExpect macros', ok, detail)
    ok, detail = assert_template_macros(api, 'Extreme IQ Engine by SNMP', IQ_HEALTH_MACROS)
    record('zbx IQ macros', ok, detail)
    ok, detail = assert_template_dashboard(api, 'Extreme VOSS by SNMP', 'Health', ('Overview', 'Hardware', 'Traffic'))
    record('zbx VOSS Health', ok, detail)
    ok, detail = assert_template_dashboard(api, 'Extreme IQ Engine by SNMP', 'Health', ('Overview', 'RF', 'Traffic'))
    record('zbx IQ Health', ok, detail)
    ok, detail = assert_template_dashboard(
        api, 'Extreme EXOS Observability', 'Health', ('Overview', 'Hardware', 'Traffic')
    )
    record('zbx EXOS companion Health', ok, detail)
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
