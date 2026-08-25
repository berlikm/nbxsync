#!/usr/bin/env python3
"""Render ``template_cato_networks_http.yaml`` from the Cato HTTP contract."""

from __future__ import annotations

import uuid
from pathlib import Path

from cato_http import (
    EXPECTED_GRAPH_PROTOTYPES,
    LLD_JS,
    METRICS_QUERY,
    SNAPSHOT_QUERY,
    TEMPLATE_MACROS,
    TEMPLATE_NAME,
    TEMPLATE_PATH,
    graphql_posts,
    load_lld_js,
)

NS = uuid.UUID('8eaf4d5d-cc47-4db9-9c4e-84b02a47b5be')
TPL = TEMPLATE_NAME

# Stable IDs from the original collector YAML. New objects use uuid5.
UUID = {
    'group': '36bff6c29af64692839d077febfc7079',
    'template': '8eaf4d5dcc474db99c4e84b02a47b5be',
    'snapshot': 'e04b5f18f8da4c5cb38b5a48eefe601a',
    'metrics': '431c7bf7febc490ea998ecaf4f118b33',
    'snap_err': '74b3e7a912ec47939a5e8f193c602726',
    'snap_err_tr': 'a4695fe6acb34c6fade1c10280ce8362',
    'met_err': 'd6874a4d6dc043bea6b7940c549c4058',
    'met_err_tr': 'b66a55318b864751bbe9986bcd09c6c1',
    'snap_schema': '7c9cb63fa8e442998d1787a7ce84258f',
    'snap_schema_tr': 'cb99b6e4c3f442d497517e87a275edd2',
    'met_schema': '3b75236505e9440d8c6ce0a9366067a6',
    'met_schema_tr': 'a73987c6230246a3aa6b5b88fee80593',
    'unsupported': '1b2e04c322d942e78f70ab7b474240ca',
    'unsupported_tr': '51d3b6b5d9d4422b8ebc4161cee2fa68',
    'snap_avail': '761b05a86ee5498cb407b91d62458b59',
    'snap_nodata_tr': '3944821d0dd945698628d960ce1bc204',
    'met_avail': '0749ea23152e4b578fc8ad1269ac5ffc',
    'met_nodata_tr': '652cea1670a546f48da9f693b0614ef2',
    'site_lld': '22ad6215cbf846a6b7a1f7a332ecf02d',
    'site_conn': 'aa25334e124944128fd73970a5b2ae31',
    'site_conn_tr': '7cde94b309424911b9b91c057c80c335',
    'socket_lld': 'c4473b456a8640e6998d7b9f271801a2',
    'socket_conn': 'bc0349d5922d4d30a32f44ad10f94154',
    'socket_conn_tr': '484894fac52e42e1b01b857f2fa6296c',
    'socket_site': '09507f47ee9545ceb60ab918ba58dc8b',
    'socket_ver': '5f8c41b2a3bc44d7923de6a40569d8fd',
    'wan_lld': '621623bbad2e402aac2350e0ea74dd6b',
    'wan_conn': '9cb564ad02b042f580da8063fc330ba4',
    'wan_conn_tr': 'bf5a6efca8894a9ea0a3f88b84107d6a',
    'wan_site': '9e064d9dc7bc450d9f372d0d8ac44999',
    'wan_uptime': '1cc0eca59bd94725a44f227246c82de6',
    'wan_pop': '1982f6f59c5642369abecb152525b361',
    'sla_lld': '2439eeb702a34b04910337f3ae297140',
    'sla_rx': '1e6795a1afa543ee88fe00651034a4dd',
    'sla_tx': 'a8100b9a34eb45329a72b94606907c06',
    'sla_loss_rx': 'dd939f2e72bc42028a40a9fd2240293d',
    'sla_loss_tx': '9d0949f801ea423d968c6865fbb8b0cf',
    'sla_jit_rx': 'cbc353c2d2974df3aa2028fc45c3a14e',
    'sla_jit_tx': '2887ff26b2fb4f10b5f38978912c411b',
    'sla_rtt': '600f2c74742c4782876a4e75d3d9b306',
    'graph_bw': '822b1fdf634a49028f608f35023ab3fb',
    'graph_loss': '37ee3ca9378a4557876b22a83c17d39b',
    'graph_lat': '02f3f94cce42445c89e7c795fbf89517',
    'valuemap': '4c65ce16533446d78da1b96a2e1aad9a',
    'dash_health': '8806cd45dc714c0a9840b518f4472bb1',
}


def uid(name: str) -> str:
    return UUID.get(name) or uuid.uuid5(NS, name).hex


def q(text: str) -> str:
    return "'" + str(text).replace("'", "''") + "'"


def js_block(js: str, indent: int) -> list[str]:
    pad = ' ' * indent
    lines = [f'{pad}- |']
    for line in js.rstrip('\n').split('\n'):
        lines.append(f'{pad}  {line}')
    return lines


def tags(indent: int, *, scope: str, extra: list[tuple[str, str]] | None = None) -> list[str]:
    pad = ' ' * indent
    rows = [
        f'{pad}tags:',
        f'{pad}- tag: component',
        f'{pad}  value: cato',
        f'{pad}- tag: monitoring_domain',
        f'{pad}  value: cato_overlay',
        f'{pad}- tag: scope',
        f'{pad}  value: {scope}',
    ]
    for tag, value in extra or []:
        rows.append(f'{pad}- tag: {tag}')
        rows.append(f'{pad}  value: {q(value) if any(ch in value for ch in ":{}") else value}')
    return rows


def collector_tags(indent: int = 6) -> list[str]:
    return tags(indent, scope='collector')


def http_master(uid_key: str, name: str, key: str, delay: str, query: str) -> list[str]:
    return [
        f'    - uuid: {uid(uid_key)}',
        f'      name: {name}',
        '      type: HTTP_AGENT',
        f'      key: {key}',
        f'      delay: {delay}',
        '      history: 1d',
        '      value_type: TEXT',
        f'      url: {q("{$CATO.API.URL}")}',
        '      request_method: POST',
        '      post_type: JSON',
        f'      posts: {q(graphql_posts(query))}',
        '      headers:',
        '      - name: Content-Type',
        '        value: application/json',
        '      - name: x-api-key',
        f'        value: {q("{$CATO.API.TOKEN}")}',
        "      status_codes: '200'",
        '      follow_redirects: YES',
        '      retrieve_mode: BODY',
        '      timeout: 30s',
        '      verify_peer: YES',
        '      verify_host: YES',
        '      allow_traps: NO',
        *collector_tags(),
    ]


def dependent_counter(
    uid_key: str,
    name: str,
    key: str,
    master: str,
    js: str,
    trigger_uid: str,
    trigger_name: str,
    priority: str,
) -> list[str]:
    return [
        f'    - uuid: {uid(uid_key)}',
        f'      name: {name}',
        '      type: DEPENDENT',
        f'      key: {key}',
        "      delay: '0'",
        '      history: 30d',
        '      value_type: UNSIGNED',
        '      preprocessing:',
        '      - type: JAVASCRIPT',
        '        parameters:',
        *js_block(js, 8),
        '      master_item:',
        f'        key: {master}',
        *collector_tags(),
        '      triggers:',
        f'      - uuid: {uid(trigger_uid)}',
        f'        expression: {q(f"last(/{TPL}/{key})>0")}',
        f'        name: {q(trigger_name)}',
        f'        priority: {priority}',
        *collector_tags(8),
    ]


def availability_item(uid_key: str, name: str, key: str, master: str, field: str, trigger_uid: str, trigger_name: str, window: str) -> list[str]:
    js = (
        'var root = JSON.parse(value);\n'
        f'return root && root.data && root.data.{field} ? 1 : 0;\n'
    )
    return [
        f'    - uuid: {uid(uid_key)}',
        f'      name: {name}',
        '      type: DEPENDENT',
        f'      key: {key}',
        "      delay: '0'",
        '      history: 30d',
        '      value_type: UNSIGNED',
        '      preprocessing:',
        '      - type: JAVASCRIPT',
        '        parameters:',
        *js_block(js, 8),
        '      master_item:',
        f'        key: {master}',
        *collector_tags(),
        '      triggers:',
        f'      - uuid: {uid(trigger_uid)}',
        f'        expression: {q(f"nodata(/{TPL}/{master},{window})=1")}',
        f'        name: {q(trigger_name)}',
        '        priority: AVERAGE',
        *collector_tags(8),
    ]


def seed_item(uid_key: str, name: str, key: str, value_type: str) -> list[str]:
    return [
        f'    - uuid: {uid(uid_key)}',
        f'      name: {name}',
        '      type: CALCULATED',
        f'      key: {q(key) if "[" in key else key}',
        '      delay: 1m',
        '      history: 1d',
        "      trends: '0'",
        f'      value_type: {value_type}',
        "      params: '0'",
        '      description: Always-present seed so count(exists_foreach) stays supported at 0.',
        *collector_tags(),
    ]


def census_item(
    uid_key: str,
    name: str,
    key: str,
    foreach_key: str,
    trigger_uid: str,
    trigger_name: str,
    expected_macro: str,
    available_key: str,
) -> list[str]:
    expr = (
        f'last(/{TPL}/{available_key})=1 and {expected_macro}>0 and '
        f'last(/{TPL}/{key})<{expected_macro}'
    )
    return [
        f'    - uuid: {uid(uid_key)}',
        f'      name: {name}',
        '      type: CALCULATED',
        f'      key: {key}',
        '      delay: 1m',
        '      history: 7d',
        '      value_type: FLOAT',
        f'      params: {q(f"count(exists_foreach(//{foreach_key}[*]))-1")}',
        *collector_tags(),
        '      triggers:',
        f'      - uuid: {uid(trigger_uid)}',
        f'        expression: {q(expr)}',
        f'        name: {q(trigger_name)}',
        '        priority: AVERAGE',
        *collector_tags(8),
    ]


SNAPSHOT_SITE_PREAMBLE = """\
var root = JSON.parse(value);
var snapshot = root && root.data && root.data.accountSnapshot;
var sites = snapshot && Array.isArray(snapshot.sites) ? snapshot.sites : null;
if (!sites) {
  throw 'accountSnapshot missing';
}
"""

METRICS_IFACE_PREAMBLE = """\
var root = JSON.parse(value);
var metrics = root && root.data && root.data.accountMetrics;
var sites = metrics && Array.isArray(metrics.sites) ? metrics.sites : null;
if (!sites) {
  throw 'accountMetrics missing';
}
var iface = null;
for (var i = 0; i < sites.length && !iface; i++) {
  if (String(sites[i].id) !== '{#SITE.ID}') {
    continue;
  }
  var interfaces = Array.isArray(sites[i].interfaces) ? sites[i].interfaces : [];
  for (var j = 0; j < interfaces.length; j++) {
    if (interfaces[j].interfaceInfo && String(interfaces[j].interfaceInfo.id) === '{#LINK.ID}') {
      iface = interfaces[j];
      break;
    }
  }
}
"""


def find_site_js() -> str:
    return (
        SNAPSHOT_SITE_PREAMBLE
        + """var found = null;
for (var i = 0; i < sites.length; i++) {
  if (String(sites[i].id) === '{#SITE.ID}') {
    found = sites[i];
    break;
  }
}
if (!found) {
  throw 'site missing';
}
"""
    )


def find_device_js() -> str:
    return (
        SNAPSHOT_SITE_PREAMBLE
        + """var device = null;
for (var i = 0; i < sites.length && !device; i++) {
  if (String(sites[i].id) !== '{#SITE.ID}') {
    continue;
  }
  var devices = Array.isArray(sites[i].devices) ? sites[i].devices : [];
  for (var j = 0; j < devices.length; j++) {
    if (devices[j].socketInfo && String(devices[j].socketInfo.id) === '{#SOCKET.ID}') {
      device = devices[j];
      break;
    }
  }
}
if (!device) {
  throw 'socket missing';
}
"""
    )


def find_iface_js() -> str:
    return (
        SNAPSHOT_SITE_PREAMBLE
        + """var iface = null;
for (var i = 0; i < sites.length && !iface; i++) {
  if (String(sites[i].id) !== '{#SITE.ID}') {
    continue;
  }
  var devices = Array.isArray(sites[i].devices) ? sites[i].devices : [];
  for (var j = 0; j < devices.length && !iface; j++) {
    if (!devices[j].socketInfo || String(devices[j].socketInfo.id) !== '{#SOCKET.ID}') {
      continue;
    }
    var interfaces = Array.isArray(devices[j].interfaces) ? devices[j].interfaces : [];
    for (var k = 0; k < interfaces.length; k++) {
      if (interfaces[k].info && String(interfaces[k].info.id) === '{#LINK.ID}') {
        iface = interfaces[k];
        break;
      }
    }
  }
}
if (!iface) {
  throw 'WAN interface missing';
}
"""
    )


def connectivity_from_status_js(source: str) -> str:
    return (
        f'var state = String({source} || \'\').toLowerCase();\n'
        "if (state === 'connected') {\n"
        '  return 1;\n'
        "}\n"
        "if (state === 'disconnected') {\n"
        '  return 0;\n'
        '}\n'
        'return 2;\n'
    )


def connectivity_from_bool_js(source: str) -> str:
    return (
        f'if ({source} === true || String({source}).toLowerCase() === \'true\') {{\n'
        '  return 1;\n'
        '}\n'
        f'if ({source} === false || String({source}).toLowerCase() === \'false\') {{\n'
        '  return 0;\n'
        '}\n'
        'return 2;\n'
    )


def proto_item(
    *,
    uid_key: str,
    name: str,
    key: str,
    master: str,
    js: str,
    scope: str,
    value_type: str = 'UNSIGNED',
    valuemap: str | None = 'Cato connectivity',
    units: str | None = None,
    history: str = '30d',
    trends: str | None = None,
    extra_tags: list[tuple[str, str]] | None = None,
    triggers: list[dict[str, str]] | None = None,
) -> list[str]:
    quoted_key = q(key) if any(ch in key for ch in '[]{},') else key
    lines = [
        f'      - uuid: {uid(uid_key)}',
        f'        name: {q(name)}',
        '        type: DEPENDENT',
        f'        key: {quoted_key}',
        "        delay: '0'",
        f'        history: {history}',
    ]
    if trends:
        lines.append(f'        trends: {trends}')
    lines.append(f'        value_type: {value_type}')
    if units:
        lines.append(f'        units: {q(units)}')
    if valuemap:
        lines.append('        valuemap:')
        lines.append(f'          name: {valuemap}')
    lines.extend(
        [
            '        preprocessing:',
            '        - type: JAVASCRIPT',
            '          parameters:',
            *js_block(js, 10),
            '          error_handler: DISCARD_VALUE',
            '        master_item:',
            f'          key: {master}',
            *tags(8, scope=scope, extra=extra_tags),
        ]
    )
    if triggers:
        lines.append('        trigger_prototypes:')
        for trigger in triggers:
            lines.append(f'        - uuid: {uid(trigger["uid"])}')
            lines.append(f'          expression: {q(trigger["expression"])}')
            lines.append(f'          name: {q(trigger["name"])}')
            lines.append(f'          priority: {trigger["priority"]}')
            lines.extend(tags(10, scope=scope))
    return lines


def calc_proto(
    *,
    uid_key: str,
    name: str,
    key: str,
    params: str,
    scope: str,
    units: str | None = None,
    extra_tags: list[tuple[str, str]] | None = None,
    triggers: list[dict[str, str]] | None = None,
) -> list[str]:
    lines = [
        f'      - uuid: {uid(uid_key)}',
        f'        name: {q(name)}',
        '        type: CALCULATED',
        f'        key: {q(key)}',
        '        delay: 1m',
        '        history: 30d',
        '        trends: 365d',
        '        value_type: FLOAT',
    ]
    if units:
        lines.append(f'        units: {q(units)}')
    lines.append(f'        params: {q(params)}')
    lines.extend(tags(8, scope=scope, extra=extra_tags))
    if triggers:
        lines.append('        trigger_prototypes:')
        for trigger in triggers:
            lines.append(f'        - uuid: {uid(trigger["uid"])}')
            lines.append(f'          expression: {q(trigger["expression"])}')
            lines.append(f'          name: {q(trigger["name"])}')
            lines.append(f'          priority: {trigger["priority"]}')
            lines.extend(tags(10, scope=scope))
    return lines


def metric_js(field: str, label: str, scale: str = '') -> str:
    multiply = f' * {scale}' if scale else ''
    return (
        METRICS_IFACE_PREAMBLE
        + f'var raw = iface && iface.metrics ? iface.metrics.{field} : null;\n'
        + 'var numeric = Number(raw);\n'
        + "if (raw === null || raw === '' || !isFinite(numeric)) {\n"
        + f"  throw '{label} missing';\n"
        + '}\n'
        + f'return numeric{multiply};\n'
    )


def util_js(direction: str, cap_field: str, byte_field: str) -> str:
    return (
        METRICS_IFACE_PREAMBLE
        + f'var cap = iface && iface.interfaceInfo ? Number(iface.interfaceInfo.{cap_field}) : 0;\n'
        + 'if (!isFinite(cap) || cap <= 0) {\n'
        + f"  throw '{direction} cap missing';\n"
        + '}\n'
        + f'var raw = iface && iface.metrics ? iface.metrics.{byte_field} : null;\n'
        + 'var numeric = Number(raw);\n'
        + "if (raw === null || raw === '' || !isFinite(numeric)) {\n"
        + f"  throw '{direction} rate missing';\n"
        + '}\n'
        + 'return (numeric * 8) / (cap * 1000000) * 100;\n'
    )


def gauge_fields(host: str, key: str) -> list[tuple[str, str, str]]:
    return [
        ('INTEGER', 'angle', '270'),
        ('INTEGER', 'decimal_places', '0'),
        ('INTEGER', 'show.0', '2'),
        ('INTEGER', 'show.1', '5'),
        ('INTEGER', 'th_arc_size', '6'),
        ('INTEGER', 'units_size', '14'),
        ('INTEGER', 'value_arc_size', '16'),
        ('INTEGER', 'value_bold', '1'),
        ('INTEGER', 'value_size', '25'),
        ('ITEM', 'itemid.0', None),  # placeholder
        ('STRING', 'max', '1'),
        ('STRING', 'min', '0'),
        ('STRING', 'thresholds.0.color', 'FF465C'),
        ('STRING', 'thresholds.0.threshold', '0'),
        ('STRING', 'thresholds.1.color', '0EC9AC'),
        ('STRING', 'thresholds.1.threshold', '1'),
        ('INTEGER', 'th_show_arc', '1'),
        ('INTEGER', 'th_show_labels', '0'),
    ]


def widget_fields(fields: list[dict]) -> list[str]:
    lines = ['          fields:']
    for field in fields:
        lines.append(f'          - type: {field["type"]}')
        lines.append(f'            name: {field["name"]}')
        value = field['value']
        if isinstance(value, dict):
            lines.append('            value:')
            for key, val in value.items():
                lines.append(f'              {key}: {q(val) if " " in str(val) or ":" in str(val) else val}')
        else:
            text = str(value)
            needs_quote = field['type'] == 'STRING' or any(ch in text for ch in ":{}[]*\\'")
            if field['type'] == 'INTEGER':
                lines.append(f"            value: '{text}'")
            elif needs_quote:
                lines.append(f'            value: {q(text)}')
            else:
                lines.append(f'            value: {text}')
    return lines


def widget(
    wtype: str,
    name: str,
    *,
    x: str | None = None,
    y: str | None = None,
    width: str = '18',
    height: str = '4',
    fields: list[dict],
) -> list[str]:
    lines = [
        f'        - type: {wtype}',
        f'          name: {q(name) if " " in name else name}',
    ]
    if x:
        lines.append(f"          x: '{x}'")
    if y:
        lines.append(f"          'y': '{y}'")
    lines.append(f"          width: '{width}'")
    lines.append(f"          height: '{height}'")
    lines.extend(widget_fields(fields))
    return lines


def honeycomb_status(name: str, items: str, label: str, **pos) -> list[str]:
    return widget(
        'honeycomb',
        name,
        width=pos.get('width', '72'),
        height=pos.get('height', '5'),
        x=pos.get('x'),
        y=pos.get('y'),
        fields=[
            {'type': 'STRING', 'name': 'items.0', 'value': items},
            {'type': 'STRING', 'name': 'primary_label', 'value': label},
            {'type': 'INTEGER', 'name': 'interpolation', 'value': '0'},
            {'type': 'INTEGER', 'name': 'show.0', 'value': '1'},
            {'type': 'STRING', 'name': 'thresholds.0.color', 'value': 'FF465C'},
            {'type': 'STRING', 'name': 'thresholds.0.threshold', 'value': '0'},
            {'type': 'STRING', 'name': 'thresholds.1.color', 'value': '0EC9AC'},
            {'type': 'STRING', 'name': 'thresholds.1.threshold', 'value': '1'},
            {'type': 'STRING', 'name': 'thresholds.2.color', 'value': '878787'},
            {'type': 'STRING', 'name': 'thresholds.2.threshold', 'value': '2'},
        ],
    )


def honeycomb_metric(name: str, items: str, label: str, thresholds: list[tuple[str, str]], **pos) -> list[str]:
    fields = [
        {'type': 'STRING', 'name': 'items.0', 'value': items},
        {'type': 'STRING', 'name': 'primary_label', 'value': label},
        {'type': 'INTEGER', 'name': 'interpolation', 'value': '1'},
        {'type': 'INTEGER', 'name': 'show.0', 'value': '1'},
        {'type': 'INTEGER', 'name': 'show.1', 'value': '2'},
    ]
    for idx, (color, threshold) in enumerate(thresholds):
        fields.append({'type': 'STRING', 'name': f'thresholds.{idx}.color', 'value': color})
        fields.append({'type': 'STRING', 'name': f'thresholds.{idx}.threshold', 'value': threshold})
    return widget('honeycomb', name, width=pos.get('width', '36'), height=pos.get('height', '5'), x=pos.get('x'), y=pos.get('y'), fields=fields)


def item_tile(name: str, key: str, **pos) -> list[str]:
    return widget(
        'item',
        name,
        width=pos.get('width', '18'),
        height=pos.get('height', '4'),
        x=pos.get('x'),
        y=pos.get('y'),
        fields=[
            {'type': 'ITEM', 'name': 'itemid.0', 'value': {'host': TPL, 'key': key}},
            {'type': 'INTEGER', 'name': 'show.0', 'value': '2'},
        ],
    )


def gauge_tile(name: str, key: str, **pos) -> list[str]:
    return widget(
        'gauge',
        name,
        width=pos.get('width', '18'),
        height=pos.get('height', '4'),
        x=pos.get('x'),
        y=pos.get('y'),
        fields=[
            {'type': 'INTEGER', 'name': 'angle', 'value': '270'},
            {'type': 'INTEGER', 'name': 'decimal_places', 'value': '0'},
            {'type': 'INTEGER', 'name': 'show.0', 'value': '2'},
            {'type': 'INTEGER', 'name': 'show.1', 'value': '5'},
            {'type': 'INTEGER', 'name': 'th_arc_size', 'value': '6'},
            {'type': 'INTEGER', 'name': 'units_size', 'value': '14'},
            {'type': 'INTEGER', 'name': 'value_arc_size', 'value': '16'},
            {'type': 'INTEGER', 'name': 'value_bold', 'value': '1'},
            {'type': 'INTEGER', 'name': 'value_size', 'value': '25'},
            {'type': 'ITEM', 'name': 'itemid.0', 'value': {'host': TPL, 'key': key}},
            {'type': 'STRING', 'name': 'max', 'value': '1'},
            {'type': 'STRING', 'name': 'min', 'value': '0'},
            {'type': 'STRING', 'name': 'thresholds.0.color', 'value': 'FF465C'},
            {'type': 'STRING', 'name': 'thresholds.0.threshold', 'value': '0'},
            {'type': 'STRING', 'name': 'thresholds.1.color', 'value': '0EC9AC'},
            {'type': 'STRING', 'name': 'thresholds.1.threshold', 'value': '1'},
            {'type': 'INTEGER', 'name': 'th_show_arc', 'value': '1'},
            {'type': 'INTEGER', 'name': 'th_show_labels', 'value': '0'},
        ],
    )


def render_template() -> str:
    err_js = 'var root = JSON.parse(value);\nreturn Array.isArray(root.errors) ? root.errors.length : 0;\n'
    schema_js = (
        'var root = JSON.parse(value);\n'
        'var errors = Array.isArray(root.errors) ? root.errors : [];\n'
        'var count = 0;\n'
        'for (var i = 0; i < errors.length; i++) {\n'
        '  var extensions = errors[i] && errors[i].extensions;\n'
        '  if (extensions && Array.isArray(extensions.schemaViolations)) {\n'
        '    count += extensions.schemaViolations.length;\n'
        '  }\n'
        '}\n'
        'return count;\n'
    )
    sla_extra = [('scope_note', 'wan_sla')]
    socket_tags = [
        ('serial', '{#SERIAL}'),
        ('ha_role', '{#HA.ROLE}'),
        ('platform', '{#PLATFORM}'),
    ]
    wan_tags = [('serial', '{#SERIAL}')]
    sla_tags = [('scope_metric', 'sla')]

    site_conn_js = find_site_js() + connectivity_from_status_js('found.connectivityStatus')
    site_op_js = (
        find_site_js()
        + "var state = found.operationalStatus;\n"
        + "if (state === undefined || state === null || state === '') {\n"
        + "  throw 'operationalStatus missing';\n"
        + '}\n'
        + 'return String(state);\n'
    )
    site_ha_js = (
        find_site_js()
        + 'var info = found.info || {};\n'
        + "if (info.isHA === true || String(info.isHA).toLowerCase() === 'true') {\n"
        + '  return 1;\n'
        + '}\n'
        + 'return 0;\n'
    )
    site_ready_js = (
        find_site_js()
        + 'var ha = found.haStatus || {};\n'
        + "var state = ha.readiness;\n"
        + "if (state === undefined || state === null || state === '') {\n"
        + "  throw 'HA readiness missing';\n"
        + '}\n'
        + 'return String(state);\n'
    )
    site_ver_js = (
        find_site_js()
        + 'var ha = found.haStatus || {};\n'
        + "var state = ha.socketVersion;\n"
        + "if (state === undefined || state === null || state === '') {\n"
        + "  throw 'HA socketVersion missing';\n"
        + '}\n'
        + 'return String(state);\n'
    )
    sock_conn_js = find_device_js() + connectivity_from_bool_js('device.connected')
    sock_site_js = find_site_js() + connectivity_from_status_js('found.connectivityStatus')
    sock_ver_js = (
        find_device_js()
        + 'var version = device.version || (device.socketInfo && device.socketInfo.version);\n'
        + "if (version === undefined || version === null || version === '') {\n"
        + "  throw 'socket version missing';\n"
        + '}\n'
        + 'return String(version);\n'
    )
    wan_conn_js = find_iface_js() + connectivity_from_bool_js('iface.connected')
    wan_site_js = find_site_js() + connectivity_from_status_js('found.connectivityStatus')
    wan_up_js = (
        find_iface_js()
        + "if (iface.tunnelUptime === undefined || iface.tunnelUptime === null || iface.tunnelUptime === '') {\n"
        + "  throw 'tunnel uptime missing';\n"
        + '}\n'
        + 'return iface.tunnelUptime;\n'
    )
    wan_pop_js = (
        find_iface_js()
        + "if (iface.popName === undefined || iface.popName === null || iface.popName === '') {\n"
        + "  throw 'POP missing';\n"
        + '}\n'
        + 'return String(iface.popName);\n'
    )

    lines: list[str] = [
        'zabbix_export:',
        "  version: '7.0'",
        '  template_groups:',
        f'  - uuid: {uid("group")}',
        '    name: Templates/Network devices',
        '  templates:',
        f'  - uuid: {uid("template")}',
        f'    template: {TPL}',
        f'    name: {TPL}',
        "    description: |",
        '      One account-scoped HTTP collector for Cato Socket overlay state and SLA.',
        '',
        '      NetBox Socket hosts remain ICMP-only. This template owns no ICMP item',
        '      and never turns collector loss into a site, Socket, or WAN outage.',
        '',
        '      Refresh with configure_nbxsync_network.py --apply-cato. Do not re-run',
        '      zerotouch to update this pack.',
        '    groups:',
        '    - name: Templates/Network devices',
        '    items:',
        *http_master('snapshot', 'Cato account snapshot', 'cato.account.snapshot', '1m', SNAPSHOT_QUERY),
        *http_master('metrics', 'Cato account metrics', 'cato.account.metrics', '5m', METRICS_QUERY),
        *dependent_counter('snap_err', 'Cato API snapshot GraphQL error count', 'cato.api.snapshot.error_count', 'cato.account.snapshot', err_js, 'snap_err_tr', 'Cato API: Snapshot GraphQL errors', 'AVERAGE'),
        *dependent_counter('met_err', 'Cato API metrics GraphQL error count', 'cato.api.metrics.error_count', 'cato.account.metrics', err_js, 'met_err_tr', 'Cato API: Metrics GraphQL errors', 'AVERAGE'),
        *dependent_counter('snap_schema', 'Cato API snapshot schema violation count', 'cato.api.snapshot.schema_violation_count', 'cato.account.snapshot', schema_js, 'snap_schema_tr', 'Cato API: Snapshot GraphQL schema violations', 'WARNING'),
        *dependent_counter('met_schema', 'Cato API metrics schema violation count', 'cato.api.metrics.schema_violation_count', 'cato.account.metrics', schema_js, 'met_schema_tr', 'Cato API: Metrics GraphQL schema violations', 'WARNING'),
        f'    - uuid: {uid("unsupported")}',
        '      name: Cato API unsupported item count',
        '      type: INTERNAL',
        "      key: 'zabbix[host,,items_unsupported]'",
        '      delay: 15m',
        '      history: 30d',
        '      value_type: UNSIGNED',
        *collector_tags(),
        '      triggers:',
        f'      - uuid: {uid("unsupported_tr")}',
        f"        expression: {q(f'min(/{TPL}/zabbix[host,,items_unsupported],30m)>0')}",
        "        name: 'Cato API: Unsupported items present'",
        '        priority: AVERAGE',
        '        dependencies:',
        "        - name: 'Cato API: No snapshot data for 5m'",
        f"          expression: {q(f'nodata(/{TPL}/cato.account.snapshot,5m)=1')}",
        "        - name: 'Cato API: No metrics data for 15m'",
        f"          expression: {q(f'nodata(/{TPL}/cato.account.metrics,15m)=1')}",
        *collector_tags(8),
        *availability_item('snap_avail', 'Cato API snapshot availability', 'cato.api.snapshot.available', 'cato.account.snapshot', 'accountSnapshot', 'snap_nodata_tr', 'Cato API: No snapshot data for 5m', '5m'),
        *availability_item('met_avail', 'Cato API metrics availability', 'cato.api.metrics.available', 'cato.account.metrics', 'accountMetrics', 'met_nodata_tr', 'Cato API: No metrics data for 15m', '15m'),
        *seed_item('site_seed', 'Cato site discovery seed', 'cato.site.connected[__seed]', 'UNSIGNED'),
        *seed_item('socket_seed', 'Cato Socket discovery seed', 'cato.socket.connected[__seed]', 'UNSIGNED'),
        *seed_item('wan_seed', 'Cato WAN discovery seed', 'cato.wan.connected[__seed]', 'UNSIGNED'),
        *seed_item('sla_seed', 'Cato WAN SLA discovery seed', 'cato.wan.rx.bps[__seed]', 'FLOAT'),
        *census_item('site_count', 'Cato discovered Socket site count', 'cato.site.discovery.count', 'cato.site.connected', 'site_count_tr', 'Cato census: fewer Socket sites than expected', '{$CATO.SITES.EXPECTED}', 'cato.api.snapshot.available'),
        *census_item('socket_count', 'Cato discovered Socket count', 'cato.socket.discovery.count', 'cato.socket.connected', 'socket_count_tr', 'Cato census: fewer Sockets than expected', '{$CATO.SOCKETS.EXPECTED}', 'cato.api.snapshot.available'),
        *census_item('wan_count', 'Cato discovered WAN link count', 'cato.wan.discovery.count', 'cato.wan.connected', 'wan_count_tr', 'Cato census: fewer WAN links than expected', '{$CATO.WAN.EXPECTED}', 'cato.api.snapshot.available'),
        *census_item('sla_count', 'Cato discovered WAN SLA row count', 'cato.wan.metrics.discovery.count', 'cato.wan.rx.bps', 'sla_count_tr', 'Cato census: fewer WAN SLA rows than expected', '{$CATO.SLA.EXPECTED}', 'cato.api.metrics.available'),
        '    discovery_rules:',
        f'    - uuid: {uid("site_lld")}',
        '      name: Cato Socket site discovery',
        '      type: DEPENDENT',
        '      key: cato.site.discovery',
        "      delay: '0'",
        '      lifetime: 7d',
        '      preprocessing:',
        '      - type: JAVASCRIPT',
        '        parameters:',
        *js_block(load_lld_js('cato.site.discovery'), 8),
        '      master_item:',
        '        key: cato.account.snapshot',
        '      filter:',
        '        evaltype: AND',
        '        conditions:',
        "        - macro: '{#CONN.TYPE}'",
        f"          value: {q('{$CATO.SITE.CONN_TYPE.MATCHES}')}",
        '          formulaid: A',
        '      item_prototypes:',
        *proto_item(
            uid_key='site_conn',
            name='Cato site {#SITE.NAME}: Connectivity',
            key='cato.site.connected[{#SITE.ID}]',
            master='cato.account.snapshot',
            js=site_conn_js,
            scope='site',
            extra_tags=[('connection_type', '{#CONN.TYPE}')],
            triggers=[{
                'uid': 'site_conn_tr',
                'expression': f'max(/{TPL}/cato.site.connected[{{#SITE.ID}}],#3)=0',
                'name': 'Cato site {#SITE.NAME}: Disconnected',
                'priority': 'HIGH',
            }],
        ),
        *proto_item(uid_key='site_op', name='Cato site {#SITE.NAME}: Operational status', key='cato.site.operational_status[{#SITE.ID}]', master='cato.account.snapshot', js=site_op_js, scope='site', value_type='CHAR', valuemap=None),
        *proto_item(
            uid_key='site_ha',
            name='Cato site {#SITE.NAME}: HA enabled',
            key='cato.site.ha[{#SITE.ID}]',
            master='cato.account.snapshot',
            js=site_ha_js,
            scope='site',
            valuemap=None,
        ),
        *proto_item(
            uid_key='site_ready',
            name='Cato site {#SITE.NAME}: HA readiness',
            key='cato.site.ha.readiness[{#SITE.ID}]',
            master='cato.account.snapshot',
            js=site_ready_js,
            scope='site',
            value_type='CHAR',
            valuemap=None,
            triggers=[{
                'uid': 'site_ready_tr',
                'expression': (
                    f'last(/{TPL}/cato.site.connected[{{#SITE.ID}}])=1 and '
                    f'last(/{TPL}/cato.site.ha[{{#SITE.ID}}])=1 and '
                    f'last(/{TPL}/cato.site.ha.readiness[{{#SITE.ID}}])<>{{$CATO.HA.READINESS.OK}}'
                ),
                'name': 'Cato site {#SITE.NAME}: HA not ready',
                'priority': 'AVERAGE',
            }],
        ),
        *proto_item(
            uid_key='site_ha_ver',
            name='Cato site {#SITE.NAME}: HA socket version',
            key='cato.site.ha.socket_version[{#SITE.ID}]',
            master='cato.account.snapshot',
            js=site_ver_js,
            scope='site',
            value_type='CHAR',
            valuemap=None,
            triggers=[{
                'uid': 'site_ha_ver_tr',
                'expression': (
                    f'last(/{TPL}/cato.site.connected[{{#SITE.ID}}])=1 and '
                    f'last(/{TPL}/cato.site.ha[{{#SITE.ID}}])=1 and '
                    f'last(/{TPL}/cato.site.ha.socket_version[{{#SITE.ID}}])<>{{$CATO.HA.VERSION.OK}}'
                ),
                'name': 'Cato site {#SITE.NAME}: HA socket version not ok',
                'priority': 'WARNING',
            }],
        ),
        f'    - uuid: {uid("socket_lld")}',
        '      name: Cato Socket discovery',
        '      type: DEPENDENT',
        '      key: cato.socket.discovery',
        "      delay: '0'",
        '      lifetime: 7d',
        '      preprocessing:',
        '      - type: JAVASCRIPT',
        '        parameters:',
        *js_block(load_lld_js('cato.socket.discovery'), 8),
        '      master_item:',
        '        key: cato.account.snapshot',
        '      item_prototypes:',
        *proto_item(
            uid_key='socket_conn',
            name='Cato Socket {#SITE.NAME} / {#SERIAL}: Connectivity',
            key='cato.socket.connected[{#SITE.ID},{#SOCKET.ID}]',
            master='cato.account.snapshot',
            js=sock_conn_js,
            scope='socket',
            extra_tags=socket_tags,
            triggers=[{
                'uid': 'socket_conn_tr',
                'expression': (
                    f'max(/{TPL}/cato.socket.connected[{{#SITE.ID}},{{#SOCKET.ID}}],#3)=0 and '
                    f'last(/{TPL}/cato.socket.site_connected[{{#SITE.ID}},{{#SOCKET.ID}}])=1'
                ),
                'name': 'Cato Socket {#SITE.NAME} / {#SERIAL}: Disconnected while site is up',
                'priority': 'AVERAGE',
            }],
        ),
        *proto_item(uid_key='socket_site', name='Cato Socket {#SITE.NAME} / {#SERIAL}: Site connectivity', key='cato.socket.site_connected[{#SITE.ID},{#SOCKET.ID}]', master='cato.account.snapshot', js=sock_site_js, scope='socket', extra_tags=[('serial', '{#SERIAL}')]),
        *proto_item(uid_key='socket_ver', name='Cato Socket {#SITE.NAME} / {#SERIAL}: Version', key='cato.socket.version[{#SITE.ID},{#SOCKET.ID}]', master='cato.account.snapshot', js=sock_ver_js, scope='socket', value_type='CHAR', valuemap=None, extra_tags=[('serial', '{#SERIAL}'), ('platform', '{#PLATFORM}')]),
        f'    - uuid: {uid("wan_lld")}',
        '      name: Cato Socket WAN discovery',
        '      type: DEPENDENT',
        '      key: cato.wan.discovery',
        "      delay: '0'",
        '      lifetime: 7d',
        '      preprocessing:',
        '      - type: JAVASCRIPT',
        '        parameters:',
        *js_block(load_lld_js('cato.wan.discovery'), 8),
        '      master_item:',
        '        key: cato.account.snapshot',
        '      item_prototypes:',
        *proto_item(
            uid_key='wan_conn',
            name='Cato WAN {#SITE.NAME} / {#SERIAL} / {#LINK.NAME}: Connectivity',
            key='cato.wan.connected[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]',
            master='cato.account.snapshot',
            js=wan_conn_js,
            scope='wan',
            extra_tags=wan_tags,
            triggers=[{
                'uid': 'wan_conn_tr',
                'expression': (
                    f'max(/{TPL}/cato.wan.connected[{{#SITE.ID}},{{#SOCKET.ID}},{{#LINK.ID}}],#3)=0 and '
                    f'last(/{TPL}/cato.wan.site_connected[{{#SITE.ID}},{{#SOCKET.ID}},{{#LINK.ID}}])=1'
                ),
                'name': 'Cato WAN {#SITE.NAME} / {#SERIAL} / {#LINK.NAME}: Disconnected while site is up',
                'priority': 'AVERAGE',
            }],
        ),
        *proto_item(uid_key='wan_site', name='Cato WAN {#SITE.NAME} / {#SERIAL} / {#LINK.NAME}: Site connectivity', key='cato.wan.site_connected[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]', master='cato.account.snapshot', js=wan_site_js, scope='wan', extra_tags=wan_tags),
        *proto_item(uid_key='wan_uptime', name='Cato WAN {#SITE.NAME} / {#SERIAL} / {#LINK.NAME}: Tunnel uptime', key='cato.wan.tunnel_uptime[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]', master='cato.account.snapshot', js=wan_up_js, scope='wan', valuemap=None, units='uptime', extra_tags=wan_tags),
        *proto_item(uid_key='wan_pop', name='Cato WAN {#SITE.NAME} / {#SERIAL} / {#LINK.NAME}: POP', key='cato.wan.pop[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]', master='cato.account.snapshot', js=wan_pop_js, scope='wan', value_type='CHAR', valuemap=None, extra_tags=wan_tags),
        f'    - uuid: {uid("sla_lld")}',
        '      name: Cato WAN SLA discovery',
        '      type: DEPENDENT',
        '      key: cato.wan.metrics.discovery',
        "      delay: '0'",
        '      lifetime: 7d',
        '      preprocessing:',
        '      - type: JAVASCRIPT',
        '        parameters:',
        *js_block(load_lld_js('cato.wan.metrics.discovery'), 8),
        '      master_item:',
        '        key: cato.account.metrics',
        '      item_prototypes:',
        *proto_item(uid_key='sla_rx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: RX bandwidth', key='cato.wan.rx.bps[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('bytesDownstream', 'RX rate', '8'), scope='wan_sla', value_type='FLOAT', valuemap=None, units='bps', trends='365d'),
        *proto_item(uid_key='sla_tx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: TX bandwidth', key='cato.wan.tx.bps[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('bytesUpstream', 'TX rate', '8'), scope='wan_sla', value_type='FLOAT', valuemap=None, units='bps', trends='365d'),
        *proto_item(uid_key='sla_loss_rx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: RX packet loss', key='cato.wan.loss.rx.pct[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('lostDownstreamPcnt', 'RX loss'), scope='wan_sla', value_type='FLOAT', valuemap=None, units='%', trends='365d'),
        *proto_item(uid_key='sla_loss_tx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: TX packet loss', key='cato.wan.loss.tx.pct[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('lostUpstreamPcnt', 'TX loss'), scope='wan_sla', value_type='FLOAT', valuemap=None, units='%', trends='365d'),
        *calc_proto(
            uid_key='sla_loss_max',
            name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: Overlay loss',
            key='cato.wan.loss.max.pct[{#SITE.ID},{#LINK.ID}]',
            params=f'max(last(//cato.wan.loss.rx.pct[{{#SITE.ID}},{{#LINK.ID}}]),last(//cato.wan.loss.tx.pct[{{#SITE.ID}},{{#LINK.ID}}]))',
            scope='wan_sla',
            units='%',
            triggers=[{
                'uid': 'sla_loss_tr',
                'expression': f'min(/{TPL}/cato.wan.loss.max.pct[{{#SITE.ID}},{{#LINK.ID}}],15m)>{{$CATO.LOSS.WARN}}',
                'name': 'Cato WAN {#SITE.NAME} / {#LINK.NAME}: High overlay packet loss',
                'priority': 'WARNING',
            }],
        ),
        *proto_item(uid_key='sla_jit_rx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: RX jitter', key='cato.wan.jitter.rx.ms[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('jitterDownstream', 'RX jitter'), scope='wan_sla', value_type='FLOAT', valuemap=None, units='ms', trends='365d'),
        *proto_item(uid_key='sla_jit_tx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: TX jitter', key='cato.wan.jitter.tx.ms[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('jitterUpstream', 'TX jitter'), scope='wan_sla', value_type='FLOAT', valuemap=None, units='ms', trends='365d'),
        *calc_proto(
            uid_key='sla_jit_max',
            name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: Overlay jitter',
            key='cato.wan.jitter.max.ms[{#SITE.ID},{#LINK.ID}]',
            params='max(last(//cato.wan.jitter.rx.ms[{#SITE.ID},{#LINK.ID}]),last(//cato.wan.jitter.tx.ms[{#SITE.ID},{#LINK.ID}]))',
            scope='wan_sla',
            units='ms',
        ),
        *proto_item(
            uid_key='sla_rtt',
            name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: RTT',
            key='cato.wan.rtt.ms[{#SITE.ID},{#LINK.ID}]',
            master='cato.account.metrics',
            js=metric_js('rtt', 'RTT'),
            scope='wan_sla',
            value_type='FLOAT',
            valuemap=None,
            units='ms',
            trends='365d',
            triggers=[{
                'uid': 'sla_rtt_tr',
                'expression': f'min(/{TPL}/cato.wan.rtt.ms[{{#SITE.ID}},{{#LINK.ID}}],15m)>{{$CATO.RTT.WARN}}',
                'name': 'Cato WAN {#SITE.NAME} / {#LINK.NAME}: High overlay RTT',
                'priority': 'WARNING',
            }],
        ),
        *proto_item(
            uid_key='sla_lm_loss',
            name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: Last-mile loss',
            key='cato.wan.lastmile.loss.pct[{#SITE.ID},{#LINK.ID}]',
            master='cato.account.metrics',
            js=metric_js('lastmilePacketLoss', 'last-mile loss'),
            scope='wan_sla',
            value_type='FLOAT',
            valuemap=None,
            units='%',
            trends='365d',
            triggers=[{
                'uid': 'sla_lm_loss_tr',
                'expression': f'min(/{TPL}/cato.wan.lastmile.loss.pct[{{#SITE.ID}},{{#LINK.ID}}],15m)>{{$CATO.LASTMILE.LOSS.WARN}}',
                'name': 'Cato WAN {#SITE.NAME} / {#LINK.NAME}: High last-mile packet loss',
                'priority': 'WARNING',
            }],
        ),
        *proto_item(uid_key='sla_lm_lat', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: Last-mile latency', key='cato.wan.lastmile.latency.ms[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('lastmileLatency', 'last-mile latency'), scope='wan_sla', value_type='FLOAT', valuemap=None, units='ms', trends='365d'),
        *proto_item(uid_key='sla_disc_rx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: RX discarded', key='cato.wan.discard.rx.pps[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('packetsDiscardedDownstream', 'RX discarded'), scope='wan_sla', value_type='FLOAT', valuemap=None, units='pps', trends='365d'),
        *proto_item(uid_key='sla_disc_tx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: TX discarded', key='cato.wan.discard.tx.pps[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('packetsDiscardedUpstream', 'TX discarded'), scope='wan_sla', value_type='FLOAT', valuemap=None, units='pps', trends='365d'),
        *proto_item(uid_key='sla_util_rx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: RX utilization', key='cato.wan.rx.util.pct[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=util_js('RX', 'downstreamBandwidth', 'bytesDownstream'), scope='wan_sla', value_type='FLOAT', valuemap=None, units='%', trends='365d'),
        *proto_item(uid_key='sla_util_tx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: TX utilization', key='cato.wan.tx.util.pct[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=util_js('TX', 'upstreamBandwidth', 'bytesUpstream'), scope='wan_sla', value_type='FLOAT', valuemap=None, units='%', trends='365d'),
        '      graph_prototypes:',
        f'      - uuid: {uid("graph_bw")}',
        f"        name: {q('Cato WAN {#SITE.NAME} / {#LINK.NAME}: Bandwidth')}",
        '        graph_items:',
        '        - color: 199C0D',
        '          item:',
        f'            host: {TPL}',
        f"            key: {q('cato.wan.rx.bps[{#SITE.ID},{#LINK.ID}]')}",
        "        - sortorder: '1'",
        '          color: 2774A4',
        '          item:',
        f'            host: {TPL}',
        f"            key: {q('cato.wan.tx.bps[{#SITE.ID},{#LINK.ID}]')}",
        f'      - uuid: {uid("graph_loss")}',
        f"        name: {q('Cato WAN {#SITE.NAME} / {#LINK.NAME}: Packet loss')}",
        '        graph_items:',
        '        - color: F63100',
        '          item:',
        f'            host: {TPL}',
        f"            key: {q('cato.wan.loss.rx.pct[{#SITE.ID},{#LINK.ID}]')}",
        "        - sortorder: '1'",
        '          color: F7941D',
        '          item:',
        f'            host: {TPL}',
        f"            key: {q('cato.wan.loss.tx.pct[{#SITE.ID},{#LINK.ID}]')}",
        f'      - uuid: {uid("graph_rtt")}',
        f"        name: {q('Cato WAN {#SITE.NAME} / {#LINK.NAME}: RTT')}",
        '        graph_items:',
        '        - color: 2774A4',
        '          item:',
        f'            host: {TPL}',
        f"            key: {q('cato.wan.rtt.ms[{#SITE.ID},{#LINK.ID}]')}",
        f'      - uuid: {uid("graph_jit")}',
        f"        name: {q('Cato WAN {#SITE.NAME} / {#LINK.NAME}: Jitter')}",
        '        graph_items:',
        '        - color: 199C0D',
        '          item:',
        f'            host: {TPL}',
        f"            key: {q('cato.wan.jitter.rx.ms[{#SITE.ID},{#LINK.ID}]')}",
        "        - sortorder: '1'",
        '          color: F7941D',
        '          item:',
        f'            host: {TPL}',
        f"            key: {q('cato.wan.jitter.tx.ms[{#SITE.ID},{#LINK.ID}]')}",
        '    macros:',
    ]
    for macro, value in TEMPLATE_MACROS.items():
        lines.append(f'    - macro: {q(macro)}')
        lines.append(f'      value: {q(value)}')
    lines.extend(
        [
            '    valuemaps:',
            f'    - uuid: {uid("valuemap")}',
            '      name: Cato connectivity',
            '      mappings:',
            "      - value: '0'",
            '        newvalue: Disconnected',
            "      - value: '1'",
            '        newvalue: Connected',
            "      - value: '2'",
            '        newvalue: Unknown',
            '    dashboards:',
            f'    - uuid: {uid("dash_health")}',
            '      name: Health',
            '      pages:',
            '      - name: Overview',
            '        widgets:',
            *gauge_tile('Snapshot', 'cato.api.snapshot.available'),
            *gauge_tile('Metrics', 'cato.api.metrics.available', x='18'),
            *item_tile('Sites', 'cato.site.discovery.count', x='36'),
            *item_tile('Sockets', 'cato.socket.discovery.count', x='54'),
            *widget(
                'problems',
                'Problems',
                y='4',
                width='72',
                height='3',
                fields=[
                    {'type': 'STRING', 'name': 'reference', 'value': 'CPROB'},
                    {'type': 'INTEGER', 'name': 'show', 'value': '3'},
                    {'type': 'INTEGER', 'name': 'show_opdata', 'value': '2'},
                ],
            ),
            *honeycomb_status(
                'Sites',
                'Cato site *: Connectivity',
                '{{ITEM.NAME}.regsub("^Cato site (.*): Connectivity$","\\\\1")}',
                y='7',
                width='72',
                height='5',
            ),
            *item_tile('Snapshot GraphQL errors', 'cato.api.snapshot.error_count', y='12', height='3'),
            *item_tile('Metrics GraphQL errors', 'cato.api.metrics.error_count', x='18', y='12', height='3'),
            *item_tile('Snapshot schema violations', 'cato.api.snapshot.schema_violation_count', x='36', y='12', height='3'),
            *item_tile('Unsupported items', 'zabbix[host,,items_unsupported]', x='54', y='12', height='3'),
            f'    - uuid: {uid("dash_path")}',
            '      name: Path',
            '      pages:',
            '      - name: Overview',
            '        widgets:',
            *honeycomb_metric(
                'Overlay loss',
                'Cato WAN *: Overlay loss',
                '{{ITEM.NAME}.regsub("^Cato WAN (.*): Overlay loss$","\\\\1")}',
                [('0EC9AC', '0'), ('FFD54F', '2'), ('FF465C', '5')],
            ),
            *honeycomb_metric(
                'Overlay RTT',
                'Cato WAN *: RTT',
                '{{ITEM.NAME}.regsub("^Cato WAN (.*): RTT$","\\\\1")}',
                [('0EC9AC', '0'), ('FFD54F', '80'), ('FF465C', '150')],
                x='36',
            ),
            *honeycomb_metric(
                'Overlay jitter',
                'Cato WAN *: Overlay jitter',
                '{{ITEM.NAME}.regsub("^Cato WAN (.*): Overlay jitter$","\\\\1")}',
                [('0EC9AC', '0'), ('FFD54F', '10'), ('FF465C', '30')],
                y='5',
            ),
            *honeycomb_metric(
                'Last-mile loss',
                'Cato WAN *: Last-mile loss',
                '{{ITEM.NAME}.regsub("^Cato WAN (.*): Last-mile loss$","\\\\1")}',
                [('0EC9AC', '0'), ('FFD54F', '2'), ('FF465C', '5')],
                x='36',
                y='5',
            ),
            *honeycomb_metric(
                'Last-mile latency',
                'Cato WAN *: Last-mile latency',
                '{{ITEM.NAME}.regsub("^Cato WAN (.*): Last-mile latency$","\\\\1")}',
                [('0EC9AC', '0'), ('FFD54F', '80'), ('FF465C', '150')],
                y='10',
                width='72',
            ),
            '      - name: Probe',
            '        widgets:',
            *widget(
                'itemnavigator',
                'Counters',
                width='28',
                height='11',
                fields=[
                    {'type': 'INTEGER', 'name': 'group_by.0.attribute', 'value': '3'},
                    {'type': 'STRING', 'name': 'group_by.0.tag_name', 'value': 'scope'},
                    {'type': 'STRING', 'name': 'items.0', 'value': 'Cato WAN *: Overlay loss'},
                    {'type': 'STRING', 'name': 'items.1', 'value': 'Cato WAN *: RTT'},
                    {'type': 'STRING', 'name': 'items.2', 'value': 'Cato WAN *: Overlay jitter'},
                    {'type': 'STRING', 'name': 'items.3', 'value': 'Cato WAN *: Last-mile loss'},
                    {'type': 'STRING', 'name': 'items.4', 'value': 'Cato WAN *: Last-mile latency'},
                    {'type': 'STRING', 'name': 'items.5', 'value': 'Cato WAN *: RX bandwidth'},
                    {'type': 'STRING', 'name': 'items.6', 'value': 'Cato WAN *: TX bandwidth'},
                    {'type': 'STRING', 'name': 'reference', 'value': 'CNAVP'},
                ],
            ),
            *widget(
                'svggraph',
                'History',
                x='28',
                width='44',
                height='11',
                fields=[
                    {'type': 'STRING', 'name': 'ds.0.color.0', 'value': '42A5F5'},
                    {'type': 'INTEGER', 'name': 'ds.0.dataset_type', 'value': '0'},
                    {'type': 'STRING', 'name': 'ds.0.itemids.0._reference', 'value': 'CNAVP._itemid'},
                    {'type': 'STRING', 'name': 'reference', 'value': 'CGRFP'},
                    {'type': 'INTEGER', 'name': 'legend', 'value': '0'},
                    {'type': 'INTEGER', 'name': 'righty', 'value': '0'},
                ],
            ),
            f'    - uuid: {uid("dash_net")}',
            '      name: Network',
            '      pages:',
            '      - name: Overview',
            '        widgets:',
            *honeycomb_status(
                'WAN links',
                'Cato WAN *: Connectivity',
                '{{ITEM.NAME}.regsub("^Cato WAN (.*): Connectivity$","\\\\1")}',
                width='36',
                height='6',
            ),
            *honeycomb_status(
                'Sockets',
                'Cato Socket *: Connectivity',
                '{{ITEM.NAME}.regsub("^Cato Socket (.*): Connectivity$","\\\\1")}',
                x='36',
                width='36',
                height='6',
            ),
            *widget(
                'itemnavigator',
                'Tunnels',
                y='6',
                width='28',
                height='8',
                fields=[
                    {'type': 'INTEGER', 'name': 'group_by.0.attribute', 'value': '3'},
                    {'type': 'STRING', 'name': 'group_by.0.tag_name', 'value': 'serial'},
                    {'type': 'STRING', 'name': 'items.0', 'value': 'Cato WAN *: Connectivity'},
                    {'type': 'STRING', 'name': 'items.1', 'value': 'Cato WAN *: Tunnel uptime'},
                    {'type': 'STRING', 'name': 'items.2', 'value': 'Cato WAN *: POP'},
                    {'type': 'STRING', 'name': 'reference', 'value': 'CNNAV'},
                ],
            ),
            *widget(
                'svggraph',
                'History',
                x='28',
                y='6',
                width='44',
                height='8',
                fields=[
                    {'type': 'STRING', 'name': 'ds.0.color.0', 'value': '42A5F5'},
                    {'type': 'INTEGER', 'name': 'ds.0.dataset_type', 'value': '0'},
                    {'type': 'STRING', 'name': 'ds.0.itemids.0._reference', 'value': 'CNNAV._itemid'},
                    {'type': 'STRING', 'name': 'reference', 'value': 'CNGRA'},
                    {'type': 'INTEGER', 'name': 'legend', 'value': '0'},
                    {'type': 'INTEGER', 'name': 'righty', 'value': '0'},
                ],
            ),
        ]
    )
    return '\n'.join(lines) + '\n'


def write_template(path: Path | None = None) -> Path:
    target = path or TEMPLATE_PATH
    target.write_text(render_template(), encoding='utf-8')
    return target


if __name__ == '__main__':
    write_template()
    print(f'wrote {TEMPLATE_PATH}')
