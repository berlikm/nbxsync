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

from extreme_ascii_titles import yaml_title_fields_needing_ascii
from extreme_linkdown import (
    IFNAME_NOT_MATCHES,
    ifname_not_matches_excludes_oob,
    linkdown_is_not_up,
    linkdown_recovery_is_up,
)
from extreme_psu import (
    VOSS_PSU_SERIAL_OID,
    psu_expr_is_not_up,
    psu_lld_keeps_installed_fru,
)

TEMPLATES = {
    'Extreme Port Speed Expect by SNMP': ROOT / 'zabbix/templates/extreme_port_speed_expect_snmp/template_net_extreme_port_speed_expect_snmp.yaml',
    'Extreme VOSS by SNMP': ROOT / 'zabbix/templates/extreme_voss_snmp/template_net_extreme_voss_snmp.yaml',
    'Extreme IQ Engine by SNMP': ROOT / 'zabbix/templates/extreme_iq_engine_snmp/template_net_extreme_iq_engine_snmp.yaml',
    'Extreme EXOS Observability': ROOT / 'zabbix/templates/extreme_exos_observability_snmp/template_extreme_exos_observability_snmp.yaml',
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


def _item_by_key(tpl: dict, key: str) -> dict | None:
    for it in tpl.get('items') or []:
        if it.get('key') == key:
            return it
    return None


def validate_discovery_count_seed(
    label: str,
    tpl: dict,
    *,
    count_key: str,
    seed_key: str,
    trigger_name: str,
) -> None:
    """Empty foreach must not go Not supported — seed + subtract 1, no nodata."""
    keys = _walk_item_keys(tpl)
    record(f'{label} {count_key} seed', seed_key in keys, seed_key)
    item = _item_by_key(tpl, count_key) or {}
    params = item.get('params') or ''
    compact = params.replace(' ', '')
    record(
        f'{label} {count_key} subtracts seed',
        'exists_foreach' in compact and compact.endswith('-1'),
        params,
    )
    trig = next((t for t in _walk_triggers(tpl) if t.get('name') == trigger_name), None)
    expr = (trig or {}).get('expression') or ''
    record(
        f'{label} {trigger_name} has no nodata',
        bool(trig) and 'nodata(' not in expr,
        expr[:200],
    )


_VOSS_PSU_LLD_KEYS = frozenset({'psu.discovery', 'psu.detail.discovery'})


def _lld_lost_policy_ok(rule: dict) -> bool:
    return (
        str(rule.get('lifetime_type') or '') == 'DELETE_AFTER'
        and str(rule.get('lifetime') or '') in ('7d', '7d0h', '604800')
        and str(rule.get('enabled_lifetime_type') or '') == 'DISABLE_IMMEDIATELY'
        and str(rule.get('enabled_lifetime') or '0') in ('0', '0s', '0d', '0h')
    )


def _voss_psu_lost_policy_ok(rule: dict) -> bool:
    """Empty PSU hexes stay on Health until the item is deleted, not merely disabled."""
    lifetime = str(rule.get('lifetime') or '')
    lifetime_type = str(rule.get('lifetime_type') or '')
    enabled = str(rule.get('enabled_lifetime') or '0')
    enabled_type = str(rule.get('enabled_lifetime_type') or '')
    delete_now = lifetime_type in ('DELETE_IMMEDIATELY', '2') or (
        lifetime in ('0', '0s', '0d', '0h') and lifetime_type not in ('DELETE_NEVER', '1')
    )
    disable_now = enabled in ('0', '0s', '0d', '0h') and enabled_type in (
        'DISABLE_IMMEDIATELY',
        '2',
    )
    return delete_now and disable_now


def voss_psu_lld_keeps_installed_fru(rule: dict, status_oid: str) -> bool:
    """True when VOSS PSU LLD keeps serialled FRUs and deletes lost padding now."""
    return psu_lld_keeps_installed_fru(
        rule,
        status_oid=status_oid,
        serial_oid=VOSS_PSU_SERIAL_OID,
        empty_regex='^2$',
    ) and _voss_psu_lost_policy_ok(rule)


def validate_lld_lost_policy(name: str, tpl: dict) -> None:
    rules = tpl.get('discovery_rules') or []
    stated = [r for r in rules if r.get('lifetime') is not None or r.get('lifetime_type') is not None]
    if not stated:
        return
    bad = []
    for rule in stated:
        if name == 'Extreme VOSS by SNMP' and rule.get('key') in _VOSS_PSU_LLD_KEYS:
            continue
        if not _lld_lost_policy_ok(rule):
            bad.append(
                f"{rule.get('key')}: lifetime={rule.get('lifetime')} type={rule.get('lifetime_type')} "
                f"enabled={rule.get('enabled_lifetime')} enabled_type={rule.get('enabled_lifetime_type')}"
            )
    record(f'{name} LLD disable-now delete-7d', not bad, '; '.join(bad[:6]))


def _macro_map(tpl: dict) -> dict[str, str]:
    return {m['macro']: str(m.get('value', '')) for m in (tpl.get('macros') or []) if m.get('macro')}


def _honeycomb_threshold_map(widget: dict) -> dict[str, str]:
    """Map honeycomb threshold value to colour."""
    by_idx: dict[str, dict[str, str]] = {}
    for field in widget.get('fields') or []:
        name = str(field.get('name') or '')
        match = re.match(r'^thresholds\.(\d+)\.(color|threshold)$', name)
        if not match:
            continue
        by_idx.setdefault(match.group(1), {})[match.group(2)] = str(field.get('value') or '')
    return {
        row['threshold']: row.get('color', '')
        for row in by_idx.values()
        if 'threshold' in row
    }


def validate_health_dashboard(name: str, doc: dict, tpl: dict, *, pages: tuple[str, ...]) -> None:
    dashes = tpl.get('dashboards') or []
    health = [d for d in dashes if d.get('name') == 'Health']
    record(f'{name} Health dashboard', bool(health), f'count={len(health)} names={[d.get("name") for d in dashes]}')
    if not health:
        return
    dash = health[0]
    got_pages = [p.get('name') for p in (dash.get('pages') or [])]
    record(f'{name} Health pages', all(p in got_pages for p in pages), f'got={got_pages} want={list(pages)}')
    record(f'{name} Health has no Diagnostics', 'Diagnostics' not in got_pages, f'got={got_pages}')
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
                    # Template dashboards cannot reference graph prototypes on a nested
                    # template (Zabbix drops the widget on import). Keep Health graphs
                    # on this template, or use svggraph item patterns for nested items.
                    ok = gname in graphs
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
            and [w.get('name') for w in tiles] == ['ICMP', 'SNMP', 'CPU', 'Uptime']
            and [w.get('type') for w in tiles] == ['gauge', 'gauge', 'gauge', 'item'],
            f'tiles={[(w.get("name"), w.get("type"), w.get("width")) for w in tiles]}',
        )
        record(
            f'{name} Overview problems strip',
            len(problems) == 1
            and str(problems[0].get('width')) == '72'
            and str(problems[0].get('height')) == '3'
            and _wy(problems[0]) == '4',
            f'problems={[(w.get("width"), w.get("height"), _wy(w)) for w in problems]}',
        )
        history_names = [w.get('name') for w in histories]
        record(
            f'{name} Overview two-pane history',
            len(histories) == 2
            and all(str(w.get('width')) == '36' and str(w.get('height')) == '6' and _wy(w) == '7' for w in histories)
            and history_names[-1] == 'Uptime'
            and history_names[0] in ('CPU', 'CPU / memory'),
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
            shows = {str(f.get('value')) for f in (widget.get('fields') or []) if str(f.get('name')).startswith('show.')}
            identity_only = shows == {'1'}
            value_ok = shows == {'1', '2'}
            status_names = {'Fans', 'PSU', 'Interfaces'}
            metric_names = {'Radios', 'Temp', 'Power'}
            wname = widget.get('name')
            show_ok = (wname in status_names and identity_only) or (wname in metric_names and value_ok) or identity_only
            size_ok = (
                str(widget.get('height')) == '3'
                and str(hfields.get('primary_label_bold')) == '1'
                and str(hfields.get('primary_label_size_type')) == '1'
                and str(hfields.get('primary_label_size')) == '20'
            )
            secondary_ok = True
            if wname in metric_names:
                secondary_ok = (
                    str(hfields.get('secondary_label_size_type')) == '1'
                    and str(hfields.get('secondary_label_size')) == '22'
                )
            honey_ok = honey_ok and capture_ok and show_ok and size_ok and secondary_ok
            honey_detail.append((wname, capture_ok, show_ok, size_ok, secondary_ok))
    if honey_seen:
        record(f'{name} honeycomb labels', honey_ok, f'{honey_detail}')

    def fields(widget: dict) -> dict[str, object]:
        return {f.get('name'): f.get('value') for f in (widget.get('fields') or [])}

    hardware = pages_by_name.get('Hardware')
    if hardware is not None:
        hw_widgets = hardware.get('widgets') or []
        hw_honey = [w for w in hw_widgets if w.get('type') == 'honeycomb']
        hw_graphs = [w for w in hw_widgets if w.get('type') in ('graph', 'graphprototype')]
        hw_svg = [w for w in hw_widgets if w.get('type') == 'svggraph']
        if name == 'VOSS':
            temp_w = next((w for w in hw_honey if w.get('name') == 'Temp'), {})
            power_w = next((w for w in hw_honey if w.get('name') == 'Power'), {})
            record(
                f'{name} Hardware FRU row',
                [w.get('name') for w in hw_honey] == ['Fans', 'PSU', 'Temp', 'Power']
                and all(str(w.get('width')) == '18' for w in hw_honey),
                f'honey={[(w.get("name"), w.get("width")) for w in hw_honey]}',
            )
            record(
                f'{name} Hardware Temp is °C not status enum',
                str(fields(temp_w).get('items.0')) == 'Temperature sensor *'
                and str(fields(temp_w).get('interpolation')) == '1',
                f'items={fields(temp_w).get("items.0")}',
            )
            record(
                f'{name} Hardware Power is PSU output watts',
                str(fields(power_w).get('items.0')) == 'PSU *: Output watts'
                and str(fields(power_w).get('interpolation')) == '1',
                f'items={fields(power_w).get("items.0")}',
            )
        if name == 'EXOS companion':
            hw_gauges = [w for w in hw_widgets if w.get('type') == 'gauge']
            record(
                f'{name} Hardware FRU maps plus Temp',
                [w.get('name') for w in hw_honey] == ['Fans', 'PSU']
                and all(str(w.get('width')) == '36' for w in hw_honey)
                and not hw_graphs
                and [w.get('name') for w in hw_gauges] == ['Temp']
                and [w.get('name') for w in hw_svg] == ['Temp'],
                f'honey={[(w.get("name"), w.get("width")) for w in hw_honey]} '
                f'gauges={[w.get("name") for w in hw_gauges]} svg={[w.get("name") for w in hw_svg]}',
            )

    rf = pages_by_name.get('RF')
    if rf is not None:
        rf_graphs = [w for w in (rf.get('widgets') or []) if w.get('type') == 'graphprototype']
        cols = [fields(w).get('columns') for w in rf_graphs]
        record(
            f'{name} RF radio graphs 2-column',
            bool(rf_graphs) and all(str(c) == '2' for c in cols),
            f'columns={cols}',
        )
        rf_types = {w.get('type') for w in (rf.get('widgets') or [])}
        record(
            f'{name} RF has no item navigator',
            'itemnavigator' not in rf_types,
            f'got={sorted(str(t) for t in rf_types)}',
        )
        if name == 'IQ':
            rf_names = [w.get('name') for w in (rf.get('widgets') or [])]
            record(
                f'{name} RF has Clients census',
                rf_names.count('Clients') == 2,
                f'names={rf_names}',
            )


def validate_interface_dashboard(
    name: str,
    tpl: dict,
    *,
    port_page: bool = False,
    flaps: bool = False,
    compact_map: bool = False,
) -> None:
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
    # Zabbix honeycomb has a 32px floor and no max cell size: cells fill the
    # widget. Switches (many ports) need 72×6 so names survive a modest window.
    # IQ APs have ~2 eth — the same box paints giant hexes. Cap that map.
    if compact_map:
        map_ok = map_widget.get('width') == '12' and map_widget.get('height') == '3'
        grid_ok = grid_widget.get('height') == '14' and grid_widget.get('y') == '3'
    else:
        map_ok = map_widget.get('width') == '72' and map_widget.get('height') == '6'
        grid_ok = grid_widget.get('height') == '14' and grid_widget.get('y') == '6'
    unified = (
        map_ok
        and grid_ok
        and grid_widget.get('width') == '72'
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
        and str(map_fields.get('show.0')) == '1'
        and map_fields.get('show.1') is None
        and map_fields.get('primary_label_bold') is None
        and str(map_fields.get('primary_label_size_type') or '0') == '0'
        and '(?:' in label
    )
    names_ok = map_widget.get('name') == 'Interfaces' and grid_widget.get('name') == 'Traffic'
    record(f'{name} unified interface graph grid', unified, f'graph={graph_ref}')
    record(f'{name} interface map is scan-only', extra == [], f'extra={extra}')
    record(f'{name} interface map labels', labels_ok, f'label={label}')
    record(f'{name} interface wording', names_ok, f'map={map_widget.get("name")} grid={grid_widget.get("name")}')
    port = next((p for p in pages if p.get('name') == 'Port'), None)
    if not port_page:
        record(f'{name} Network interfaces has no Port page', port is None, f'pages={[p.get("name") for p in pages]}')
        return
    record(f'{name} Network interfaces Port page', bool(port), f'pages={[p.get("name") for p in pages]}')
    if not port:
        return
    pwidgets = port.get('widgets') or []
    ptypes = {w.get('type') for w in pwidgets}
    nav_widget = next((w for w in pwidgets if w.get('type') == 'itemnavigator'), {})
    graph_widget = next((w for w in pwidgets if w.get('type') == 'svggraph'), {})
    nav_fields = {f.get('name'): f.get('value') for f in (nav_widget.get('fields') or [])}
    graph_fields = {f.get('name'): f.get('value') for f in (graph_widget.get('fields') or [])}
    nav_ref = nav_fields.get('reference')
    patterns = {str(v) for key, v in nav_fields.items() if str(key).startswith('items.')}
    traffic = {'Interface *: Bits received', 'Interface *: Bits sent'}
    expected = {
        'Interface *: Operational status',
        'Interface *: Speed',
        'Interface *: Duplex status',
        'Interface *: Inbound packets with errors',
        'Interface *: Outbound packets with errors',
        'Interface *: Inbound packets discarded',
        'Interface *: Outbound packets discarded',
    }
    record(
        f'{name} Port is fault counters not traffic',
        ptypes == {'itemnavigator', 'svggraph'}
        and expected <= patterns
        and not (traffic & patterns)
        and (flaps == ('Interface *: State transitions' in patterns)),
        f'got={sorted(patterns)}',
    )
    record(
        f'{name} Port wiring',
        bool(nav_ref)
        and graph_fields.get('ds.0.itemids.0._reference') == f'{nav_ref}._itemid'
        and str(graph_widget.get('height')) == '11'
        and nav_widget.get('name') == 'Counters',
        f'navigator={nav_ref} name={nav_widget.get("name")}',
    )


def validate_voss(doc: dict) -> None:
    tpl = _tpl(doc)
    record('VOSS name', tpl.get('name') == 'Extreme VOSS by SNMP', str(tpl.get('name')))
    linked = {row.get('name') for row in (tpl.get('templates') or [])}
    record('VOSS nests Speed Expect', 'Extreme Port Speed Expect by SNMP' in linked, str(sorted(linked)))
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
    for n in ('Extreme VOSS: Too many unsupported items', 'Extreme VOSS: No discovered interfaces after SNMP is up'):
        record(f'VOSS has {n}', n in by_name, '')
    record(
        'VOSS {$NET.IF.DISCOVERY.MIN}',
        macros.get('{$NET.IF.DISCOVERY.MIN}') == '1',
        str(macros.get('{$NET.IF.DISCOVERY.MIN}')),
    )
    snmp = by_name.get('Extreme VOSS: No SNMP data collection')
    record(
        'VOSS SNMP-dead Warning',
        bool(snmp) and snmp.get('priority') == 'WARNING',
        str((snmp or {}).get('priority')),
    )
    avg_ld = next(
        (t for t in trigs if t.get('name') == 'Extreme VOSS: Interface {#IFNAME}({#IFALIAS}): Link down'),
        None,
    )
    usw_ld = next((t for t in trigs if 'Link down (USW)' in (t.get('name') or '')), None)
    record(
        'VOSS link-down one Average',
        bool(avg_ld)
        and avg_ld.get('priority') == 'AVERAGE'
        and 'LINKDOWN.HIGH' not in (avg_ld.get('expression') or '')
        and usw_ld is None
        and '{$LINKDOWN.HIGH}' not in macros,
        f'avg={bool(avg_ld)} usw={bool(usw_ld)}',
    )
    ld_expr = (avg_ld or {}).get('expression') or ''
    ld_rec = (avg_ld or {}).get('recovery_expression') or ''
    record(
        'VOSS link-down fires while oper not up (no .diff())',
        bool(avg_ld)
        and linkdown_is_not_up(ld_expr)
        and linkdown_recovery_is_up(ld_rec)
        and str((avg_ld or {}).get('manual_close') or 'NO').upper() != 'YES',
        ld_expr[:160],
    )
    record(
        'VOSS link-down Access ifAlias gate',
        '{$LINKDOWN.IFALIAS:"{#IFALIAS}"}=1' in ld_expr
        and '{$LINKDOWN.IFALIAS:"{#IFALIAS}"}=0' in ld_rec
        and macros.get('{$LINKDOWN.IFALIAS}') == '1',
        f'expr={ld_expr[:120]} rec={ld_rec[:80]} macro={macros.get("{$LINKDOWN.IFALIAS}")!r}',
    )
    record(
        'VOSS IFNAME skips chassis OOB mgmt',
        macros.get('{$NET.IF.IFNAME.NOT_MATCHES}') == IFNAME_NOT_MATCHES
        and ifname_not_matches_excludes_oob(macros.get('{$NET.IF.IFNAME.NOT_MATCHES}') or ''),
        str(macros.get('{$NET.IF.IFNAME.NOT_MATCHES}')),
    )
    record(
        'VOSS link-down description includes Access',
        'Access' in ((avg_ld or {}).get('description') or ''),
        ((avg_ld or {}).get('description') or '')[:120],
    )
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
    record('VOSS discovery count', 'net.if.discovery.count' in keys, '')
    validate_discovery_count_seed(
        'VOSS',
        tpl,
        count_key='net.if.discovery.count',
        seed_key='net.if.status[ifOperStatus.__seed]',
        trigger_name='Extreme VOSS: No discovered interfaces after SNMP is up',
    )
    flap_ok = shutdown_ok = False
    for rule in tpl.get('discovery_rules') or []:
        for it in rule.get('item_prototypes') or []:
            name = it.get('name') or ''
            tags = {t.get('tag'): t.get('value') for t in (it.get('tags') or [])}
            if 'State transitions' in name:
                flap_ok = tags.get('interface') == '{#IFNAME}'
            if 'Shutdown reason' in name:
                shutdown_ok = tags.get('interface') == '{#IFNAME}'
    record('VOSS flap items tagged interface', flap_ok, '')
    record('VOSS shutdown items tagged interface', shutdown_ok, '')
    temp_value_named = temp_status_index = False
    for rule in tpl.get('discovery_rules') or []:
        if rule.get('key') != 'temperature.discovery':
            continue
        for it in rule.get('item_prototypes') or []:
            iname = it.get('name') or ''
            if it.get('key', '').startswith('sensor.temp.value'):
                temp_value_named = '{#SENSOR_DESCR}' in iname
            if it.get('key', '').startswith('sensor.temp.status'):
                temp_status_index = '{#SNMPINDEX}' in iname
    record('VOSS temp value items named by SENSOR_DESCR', temp_value_named, '')
    record('VOSS temp status items keep SNMPINDEX', temp_status_index, '')
    by_key = {r.get('key'): r for r in (tpl.get('discovery_rules') or [])}
    psu = by_key.get('psu.discovery') or {}
    psu_detail = by_key.get('psu.detail.discovery') or {}
    record(
        'VOSS psu.discovery keeps installed FRUs',
        voss_psu_lld_keeps_installed_fru(psu, '1.3.6.1.4.1.2272.1.4.8.1.1.2'),
        str(psu.get('snmp_oid')),
    )
    record(
        'VOSS psu.detail.discovery keeps installed FRUs',
        voss_psu_lld_keeps_installed_fru(psu_detail, '1.3.6.1.4.1.2272.1.4.8.2.1.15'),
        str(psu_detail.get('snmp_oid')),
    )
    record(
        'VOSS {$PSU.OK_STATUS}',
        macros.get('{$PSU.OK_STATUS}') == '3',
        str(macros.get('{$PSU.OK_STATUS}')),
    )
    record(
        'VOSS {$PSU.EMPTY_STATUS}',
        macros.get('{$PSU.EMPTY_STATUS}') == '2',
        str(macros.get('{$PSU.EMPTY_STATUS}')),
    )
    record(
        'VOSS {$PSU_CRIT_STATUS} down(4)',
        macros.get('{$PSU_CRIT_STATUS}') == '4',
        str(macros.get('{$PSU_CRIT_STATUS}')),
    )
    psu_trigs = [
        t
        for t in trigs
        if 'Power supply is not up' in (t.get('name') or '')
        or 'Detail status not up' in (t.get('name') or '')
    ]
    record('VOSS PSU not-up triggers', len(psu_trigs) == 2, f'count={len(psu_trigs)}')
    record(
        'VOSS PSU tickets not-up including serialled empty',
        bool(psu_trigs) and all(psu_expr_is_not_up(t.get('expression') or '') for t in psu_trigs),
        (psu_trigs[0].get('expression') if psu_trigs else '')[:160],
    )
    leftover_crit = [
        t.get('name')
        for t in trigs
        if 'PSU' in (t.get('name') or '') and '{$PSU_CRIT_STATUS}' in (t.get('expression') or '')
    ]
    record('VOSS PSU trigger not only down(4)', not leftover_crit, str(leftover_crit))
    validate_health_dashboard('VOSS', doc, tpl, pages=('Overview', 'Hardware'))
    validate_interface_dashboard('VOSS', tpl, port_page=True, flaps=True)
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
    record(
        'IQ zero-interface trigger',
        'Extreme IQ Engine: No discovered interfaces after SNMP is up' in by_name,
        '',
    )
    record(
        'IQ zero-radio trigger',
        'Extreme IQ Engine: No discovered radios after SNMP is up' in by_name,
        '',
    )
    record(
        'IQ {$NET.IF.DISCOVERY.MIN}',
        macros.get('{$NET.IF.DISCOVERY.MIN}') == '1',
        str(macros.get('{$NET.IF.DISCOVERY.MIN}')),
    )
    validate_discovery_count_seed(
        'IQ',
        tpl,
        count_key='net.if.discovery.count',
        seed_key='net.if.status[ifOperStatus.__seed]',
        trigger_name='Extreme IQ Engine: No discovered interfaces after SNMP is up',
    )
    validate_discovery_count_seed(
        'IQ',
        tpl,
        count_key='ah.radio.discovery.count',
        seed_key='ah.radio.channel[__seed]',
        trigger_name='Extreme IQ Engine: No discovered radios after SNMP is up',
    )
    snmp = by_name.get('Extreme IQ Engine: No SNMP data collection')
    record(
        'IQ SNMP-dead Warning',
        bool(snmp) and snmp.get('priority') == 'WARNING',
        str((snmp or {}).get('priority')),
    )
    validate_health_dashboard('IQ', doc, tpl, pages=('Overview', 'RF'))
    validate_interface_dashboard('IQ', tpl, compact_map=True)


def validate_exos_observability(doc: dict) -> None:
    tpl = _tpl(doc)
    record('EXOS companion name', tpl.get('name') == 'Extreme EXOS Observability', str(tpl.get('name')))
    linked = {row.get('name') for row in (tpl.get('templates') or [])}
    record('EXOS companion links stock', 'Extreme EXOS by SNMP' in linked, str(sorted(linked)))
    record('EXOS companion nests Speed Expect', 'Extreme Port Speed Expect by SNMP' in linked, str(sorted(linked)))
    keys = _walk_item_keys(tpl)
    expected = {
        'exos.observability.cpu.util',
        'exos.observability.memory.util',
        'exos.observability.temperature',
        'exos.observability.icmp',
        'exos.observability.snmp',
    }
    record('EXOS companion calculated mirrors', expected <= keys, str(sorted(expected - keys)))
    record('EXOS companion discovery count', 'net.if.discovery.count' in keys, '')
    validate_discovery_count_seed(
        'EXOS companion',
        tpl,
        count_key='net.if.discovery.count',
        seed_key='net.if.status[ifOperStatus.__seed]',
        trigger_name='Extreme EXOS: No discovered interfaces after SNMP is up',
    )
    trigs = _walk_triggers(tpl)
    record(
        'EXOS companion zero-interface trigger',
        any(t.get('name') == 'Extreme EXOS: No discovered interfaces after SNMP is up' for t in trigs),
        '',
    )
    macros = _macro_map(tpl)
    record(
        'EXOS companion {$NET.IF.DISCOVERY.MIN}',
        macros.get('{$NET.IF.DISCOVERY.MIN}') == '1',
        str(macros.get('{$NET.IF.DISCOVERY.MIN}')),
    )
    validate_health_dashboard('EXOS companion', doc, tpl, pages=('Overview', 'Hardware'))
    psu_widget = None
    for dash in tpl.get('dashboards') or []:
        if dash.get('name') != 'Health':
            continue
        for page in dash.get('pages') or []:
            for widget in page.get('widgets') or []:
                if widget.get('type') == 'honeycomb' and widget.get('name') == 'PSU':
                    psu_widget = widget
    th = _honeycomb_threshold_map(psu_widget or {})
    record(
        'EXOS companion PSU honeycomb notPresent red',
        th.get('1') == 'FF465C' and th.get('2') == '0EC9AC' and th.get('3') == 'FF465C',
        str(th),
    )


def validate_ascii_trigger_titles(name: str, tpl: dict) -> None:
    """Problem titles (name / event_name / opdata) must not use ≠ — it becomes Γëá."""
    bad: list[str] = []
    for trig in _walk_triggers(tpl):
        bad.extend(yaml_title_fields_needing_ascii(trig))
    record(f'{name} ASCII trigger titles', not bad, '; '.join(bad[:4]))


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

    def _is_on(t: dict) -> bool:
        return str(t.get('status') or '').upper() not in ('DISABLED',)

    speed_mismatch = next((t for t in trigs if 'Speed not equal to expected' in (t.get('name') or '')), None)
    link_down = next((t for t in trigs if 'Link down (speed-expect)' in (t.get('name') or '')), None)
    discards = next((t for t in trigs if 'Outbound discards' in (t.get('name') or '')), None)
    record(
        'SpeedExpect mismatch Warning on',
        bool(speed_mismatch) and _is_on(speed_mismatch),
        (speed_mismatch or {}).get('status') or 'enabled',
    )
    event = (speed_mismatch or {}).get('event_name') or ''
    record(
        'SpeedExpect event_name ASCII !=',
        event.isascii() and '!=' in event,
        event,
    )
    record(
        'SpeedExpect link-down DISABLED',
        bool(link_down) and not _is_on(link_down),
        (link_down or {}).get('status'),
    )
    record(
        'SpeedExpect discards DISABLED',
        bool(discards) and not _is_on(discards),
        (discards or {}).get('status'),
    )


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
        try:
            validate_lld_lost_policy(name, _tpl(doc))
        except Exception as exc:
            record(f'{name} LLD policy', False, str(exc))
        try:
            validate_ascii_trigger_titles(name, _tpl(doc))
        except Exception as exc:
            record(f'{name} ASCII titles', False, str(exc))
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
    iq_map = str(patch.get('iq_interface_map'))
    record('patch iq_interface_map', iq_map in ('ok', 'patched', 'missing-template'), iq_map)

    ok, detail = assert_template_macros(api, 'Extreme VOSS by SNMP', VOSS_HEALTH_MACROS)
    record('zbx VOSS macros', ok, detail)
    ok, detail = assert_template_macros(api, 'Extreme Port Speed Expect by SNMP', SPEED_EXPECT_HEALTH_MACROS)
    record('zbx SpeedExpect macros', ok, detail)
    ok, detail = assert_template_macros(api, 'Extreme IQ Engine by SNMP', IQ_HEALTH_MACROS)
    record('zbx IQ macros', ok, detail)
    ok, detail = assert_template_dashboard(api, 'Extreme VOSS by SNMP', 'Health', ('Overview', 'Hardware'))
    record('zbx VOSS Health', ok, detail)
    ok, detail = assert_template_dashboard(api, 'Extreme IQ Engine by SNMP', 'Health', ('Overview', 'RF'))
    record('zbx IQ Health', ok, detail)
    ok, detail = assert_template_dashboard(api, 'Extreme EXOS Observability', 'Health', ('Overview', 'Hardware'))
    record('zbx EXOS companion Health', ok, detail)
    ok, detail = assert_template_dashboard(api, 'Extreme VOSS by SNMP', 'Network interfaces', ('Overview', 'Port'))
    record('zbx interface dashboard Extreme VOSS by SNMP', ok, detail)
    ok, detail = assert_template_dashboard(api, 'Extreme IQ Engine by SNMP', 'Network interfaces', ('Overview',))
    record('zbx interface dashboard Extreme IQ Engine by SNMP', ok, detail)
    ok, detail = assert_template_dashboard(api, 'Extreme EXOS by SNMP', 'Network interfaces', ('Overview', 'Port'))
    record('zbx interface dashboard Extreme EXOS by SNMP', ok, detail)
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
