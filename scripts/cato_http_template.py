#!/usr/bin/env python3
"""Render ``template_cato_networks_http.yaml`` from the Cato HTTP contract."""

from __future__ import annotations

import hashlib
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

NAMESPACE_BYTES = uuid.UUID('8eaf4d5d-cc47-4db9-9c4e-84b02a47b5be').bytes
TPL = TEMPLATE_NAME

# Stable UUIDv4 values from the original collector YAML. Derived values keep
# deterministic identities while satisfying Zabbix's UUIDv4 import contract.
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
    'valuemap_ha': 'c3d8e1f04a6b4e1e9f2a7c5d8b1e4a90',
    'dash_health': '8806cd45dc714c0a9840b518f4472bb1',
}

LOSS_THRESHOLDS = [('0EC9AC', '0'), ('FFD54F', '2'), ('FF465C', '5')]
RTT_THRESHOLDS = [('0EC9AC', '0'), ('FFD54F', '80'), ('FF465C', '150')]
JITTER_THRESHOLDS = [('0EC9AC', '0'), ('FFD54F', '10'), ('FF465C', '30')]
UTIL_THRESHOLDS = [('0EC9AC', '0'), ('FFD54F', '70'), ('FF465C', '90')]
UP_THRESHOLDS = [('FF465C', '0'), ('0EC9AC', '1')]
ERROR_THRESHOLDS = [('0EC9AC', '0'), ('FF465C', '1')]
DEGRADED_THRESHOLDS = [('0EC9AC', '0'), ('FFD54F', '1')]
STATUS_THRESHOLDS = [('FF465C', '0'), ('0EC9AC', '1'), ('878787', '2')]
SITE_TAGS = [('site', '{#SITE.NAME}'), ('connection_type', '{#CONN.TYPE}')]
SOCKET_TAGS = [
    *SITE_TAGS,
    ('serial', '{#SERIAL}'),
    ('ha_role', '{#HA.ROLE}'),
    ('platform', '{#PLATFORM}'),
]
WAN_TAGS = [
    *SITE_TAGS,
    ('serial', '{#SERIAL}'),
    ('ha_role', '{#HA.ROLE}'),
    ('dest_type', '{#DEST.TYPE}'),
]
SLA_TAGS = [*SITE_TAGS, ('dest_type', '{#DEST.TYPE}')]
PORT_TAGS = [
    *SITE_TAGS,
    ('serial', '{#SERIAL}'),
    ('ha_role', '{#HA.ROLE}'),
    ('port_kind', '{#PORT.KIND}'),
]
SITE_DISCONNECTED = {
    'name': 'Cato site {#SITE.NAME}: Disconnected',
    'expression': f'max(/{TPL}/cato.site.connected[{{#SITE.ID}}],#3)=0',
}


def uid(name: str) -> str:
    stable = UUID.get(name)
    if stable:
        return stable
    value = bytearray(hashlib.sha256(NAMESPACE_BYTES + name.encode()).digest()[:16])
    value[6] = (value[6] & 0x0F) | 0x40
    value[8] = (value[8] & 0x3F) | 0x80
    return uuid.UUID(bytes=bytes(value)).hex


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


def seed_item(
    uid_key: str,
    name: str,
    key: str,
    value_type: str,
    *,
    value: str = '0',
) -> list[str]:
    return [
        f'    - uuid: {uid(uid_key)}',
        f'      name: {name}',
        '      type: CALCULATED',
        f'      key: {q(key) if "[" in key else key}',
        '      delay: 1m',
        '      history: 1d',
        "      trends: '0'",
        f'      value_type: {value_type}',
        f'      params: {q(value)}',
        '      description: Always-present seed for aggregate foreach formulas.',
        *tags(6, scope='collector', extra=[('cato_seed', 'seed')]),
    ]


def census_item(
    uid_key: str,
    name: str,
    key: str,
    foreach_filter: str,
    trigger_uid: str,
    trigger_name: str,
    expected_macro: str,
    available_key: str,
) -> list[str]:
    census_filter = f'//{foreach_filter}?[not (tag="cato_seed:seed")]'
    expr = (
        f'last(/{TPL}/{available_key})=1 and {expected_macro}>0 and '
        f'max(/{TPL}/{key},30m)<{expected_macro}'
    )
    return [
        f'    - uuid: {uid(uid_key)}',
        f'      name: {name}',
        '      type: CALCULATED',
        f'      key: {key}',
        '      delay: 1m',
        '      history: 7d',
        '      value_type: FLOAT',
        f'      params: {q(f"count(exists_foreach({census_filter}))")}',
        *collector_tags(),
        '      triggers:',
        f'      - uuid: {uid(trigger_uid)}',
        f'        expression: {q(expr)}',
        f'        name: {q(trigger_name)}',
        '        priority: AVERAGE',
        *collector_tags(8),
    ]


def calc_item(
    uid_key: str,
    name: str,
    key: str,
    params: str,
    *,
    units: str | None = None,
    value_type: str = 'FLOAT',
    history: str = '7d',
    trends: str = '365d',
) -> list[str]:
    lines = [
        f'    - uuid: {uid(uid_key)}',
        f'      name: {name}',
        '      type: CALCULATED',
        f'      key: {key}',
        '      delay: 1m',
        f'      history: {history}',
        f'      trends: {trends}',
        f'      value_type: {value_type}',
    ]
    if units:
        lines.append(f'      units: {q(units)}')
    lines.append(f'      params: {q(params)}')
    lines.extend(collector_tags())
    return lines


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


def find_port_js() -> str:
    return (
        SNAPSHOT_SITE_PREAMBLE
        + """var port = null;
for (var i = 0; i < sites.length && !port; i++) {
  if (String(sites[i].id) !== '{#SITE.ID}') {
    continue;
  }
  var devices = Array.isArray(sites[i].devices) ? sites[i].devices : [];
  for (var j = 0; j < devices.length && !port; j++) {
    if (!devices[j].socketInfo || String(devices[j].socketInfo.id) !== '{#SOCKET.ID}') {
      continue;
    }
    var states = Array.isArray(devices[j].interfacesLinkState) ? devices[j].interfacesLinkState : [];
    for (var k = 0; k < states.length; k++) {
      if (states[k] && String(states[k].id) === '{#PORT.ID}') {
        port = states[k];
        break;
      }
    }
  }
}
if (!port) {
  throw 'port missing';
}
"""
    )


def char_from_path_js(find_js: str, source: str, label: str, *, optional: bool = False) -> str:
    missing = "  return '';\n" if optional else f"  throw '{label} missing';\n"
    return (
        find_js
        + f'var state = {source};\n'
        + "if (state === undefined || state === null || state === '') {\n"
        + missing
        + '}\n'
        + 'return String(state);\n'
    )


def bool_item_js(find_js: str, source: str) -> str:
    return find_js + connectivity_from_bool_js(source)


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
    triggers: list[dict] | None = None,
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
        lines.extend(_trigger_prototypes(triggers, scope=scope, extra_tags=extra_tags))
    return lines


def _trigger_prototypes(
    triggers: list[dict],
    *,
    scope: str,
    extra_tags: list[tuple[str, str]] | None = None,
) -> list[str]:
    lines = ['        trigger_prototypes:']
    for trigger in triggers:
        lines.append(f'        - uuid: {uid(trigger["uid"])}')
        lines.append(f'          expression: {q(trigger["expression"])}')
        lines.append(f'          name: {q(trigger["name"])}')
        lines.append(f'          priority: {trigger["priority"]}')
        lines.extend(tags(10, scope=scope, extra=extra_tags))
        deps = trigger.get('dependencies') or []
        if deps:
            lines.append('          dependencies:')
            for dep in deps:
                lines.append(f'          - name: {q(dep["name"])}')
                lines.append(f'            expression: {q(dep["expression"])}')
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
    triggers: list[dict] | None = None,
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
        lines.extend(_trigger_prototypes(triggers, scope=scope, extra_tags=extra_tags))
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

def timeseries_metric_js(label: str, description: str) -> str:
    """Average the latest Cato last-mile probe readings for one discovered link."""
    return (
        METRICS_IFACE_PREAMBLE
        + f"""var series = iface && Array.isArray(iface.timeseries) ? iface.timeseries : [];
var values = [];
for (var i = 0; i < series.length; i++) {{
  var entry = series[i];
  if (!entry || String(entry.label) !== '{label}') {{
    continue;
  }}
  var data = Array.isArray(entry.data) ? entry.data : [];
  if (!data.length) {{
    continue;
  }}
  var point = data[data.length - 1];
  var raw = null;
  if (Array.isArray(point)) {{
    raw = point.length > 1 ? point[1] : point[0];
  }} else if (point && typeof point === 'object') {{
    raw = point.value !== undefined ? point.value : point.y;
  }} else {{
    raw = point;
  }}
  var numeric = Number(raw);
  if (raw !== null && raw !== '' && isFinite(numeric)) {{
    values.push(numeric);
  }}
}}
if (!values.length) {{
  throw '{description} missing';
}}
var sum = 0;
for (var v = 0; v < values.length; v++) {{
  sum += values[v];
}}
return sum / values.length;
"""
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
                text = str(val)
                needs_quote = any(ch in text for ch in ' :[]{},*\\\'')
                lines.append(f'              {key}: {q(text) if needs_quote else text}')
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


def honeycomb_label(kind: str, metric: str) -> str:
    return '{{ITEM.NAME}.regsub("^' + kind + ' (.*): ' + metric + '$","\\1")}'


def _threshold_fields(thresholds: list[tuple[str, str]]) -> list[dict]:
    fields = []
    for idx, (color, threshold) in enumerate(thresholds):
        fields.append({'type': 'STRING', 'name': f'thresholds.{idx}.color', 'value': color})
        fields.append({'type': 'STRING', 'name': f'thresholds.{idx}.threshold', 'value': threshold})
    return fields


def honeycomb_status(
    name: str,
    items: str,
    label: str,
    *,
    reference: str,
    label_size: str = '20',
    thresholds: list[tuple[str, str]] | None = None,
    **pos,
) -> list[str]:
    fields = [
        {'type': 'STRING', 'name': 'items.0', 'value': items},
        {'type': 'STRING', 'name': 'primary_label', 'value': label},
        {'type': 'INTEGER', 'name': 'interpolation', 'value': '0'},
        {'type': 'INTEGER', 'name': 'primary_label_bold', 'value': '1'},
        {'type': 'INTEGER', 'name': 'primary_label_size_type', 'value': '1'},
        {'type': 'INTEGER', 'name': 'primary_label_size', 'value': label_size},
        {'type': 'INTEGER', 'name': 'show.0', 'value': '1'},
        {'type': 'STRING', 'name': 'reference', 'value': reference},
        *_threshold_fields(thresholds or STATUS_THRESHOLDS),
    ]
    return widget(
        'honeycomb',
        name,
        width=pos.get('width', '72'),
        height=pos.get('height', '6'),
        x=pos.get('x'),
        y=pos.get('y'),
        fields=fields,
    )


def honeycomb_metric(
    name: str,
    items: str,
    label: str,
    thresholds: list[tuple[str, str]],
    *,
    reference: str,
    label_size: str = '20',
    **pos,
) -> list[str]:
    fields = [
        {'type': 'STRING', 'name': 'items.0', 'value': items},
        {'type': 'STRING', 'name': 'primary_label', 'value': label},
        {'type': 'INTEGER', 'name': 'interpolation', 'value': '1'},
        {'type': 'INTEGER', 'name': 'primary_label_bold', 'value': '1'},
        {'type': 'INTEGER', 'name': 'primary_label_size_type', 'value': '1'},
        {'type': 'INTEGER', 'name': 'primary_label_size', 'value': label_size},
        {'type': 'INTEGER', 'name': 'secondary_label_size_type', 'value': '1'},
        {'type': 'INTEGER', 'name': 'secondary_label_size', 'value': '22'},
        {'type': 'INTEGER', 'name': 'show.0', 'value': '1'},
        {'type': 'INTEGER', 'name': 'show.1', 'value': '2'},
        {'type': 'STRING', 'name': 'reference', 'value': reference},
        *_threshold_fields(thresholds),
    ]
    return widget(
        'honeycomb',
        name,
        width=pos.get('width', '36'),
        height=pos.get('height', '6'),
        x=pos.get('x'),
        y=pos.get('y'),
        fields=fields,
    )


def item_tile(
    name: str,
    key: str,
    *,
    thresholds: list[tuple[str, str]] | None = None,
    decimal_places: str | None = None,
    **pos,
) -> list[str]:
    fields: list[dict] = [
        {'type': 'ITEM', 'name': 'itemid.0', 'value': {'host': TPL, 'key': key}},
        {'type': 'INTEGER', 'name': 'show.0', 'value': '2'},
        {'type': 'INTEGER', 'name': 'value_bold', 'value': '1'},
        {'type': 'INTEGER', 'name': 'value_size', 'value': pos.get('value_size', '28')},
    ]
    if decimal_places is not None:
        fields.append({'type': 'INTEGER', 'name': 'decimal_places', 'value': decimal_places})
    if thresholds:
        fields.extend(_threshold_fields(thresholds))
    return widget(
        'item',
        name,
        width=pos.get('width', '18'),
        height=pos.get('height', '4'),
        x=pos.get('x'),
        y=pos.get('y'),
        fields=fields,
    )


def gauge_tile(
    name: str,
    key: str,
    *,
    min_val: str | None = '0',
    max_val: str | None = '1',
    units: str | None = None,
    thresholds: list[tuple[str, str]] | None = None,
    decimal_places: str = '0',
    **pos,
) -> list[str]:
    if thresholds is None:
        thresholds = [('FF465C', '0'), ('0EC9AC', '1')]
    fields: list[dict] = [
        {'type': 'INTEGER', 'name': 'angle', 'value': '270'},
        {'type': 'INTEGER', 'name': 'decimal_places', 'value': decimal_places},
        {'type': 'INTEGER', 'name': 'show.0', 'value': '2'},
        {'type': 'INTEGER', 'name': 'show.1', 'value': '5'},
        {'type': 'INTEGER', 'name': 'th_arc_size', 'value': '6'},
        {'type': 'INTEGER', 'name': 'units_size', 'value': '14'},
        {'type': 'INTEGER', 'name': 'value_arc_size', 'value': '16'},
        {'type': 'INTEGER', 'name': 'value_bold', 'value': '1'},
        {'type': 'INTEGER', 'name': 'value_size', 'value': '25'},
        {'type': 'ITEM', 'name': 'itemid.0', 'value': {'host': TPL, 'key': key}},
    ]
    if max_val is not None:
        fields.append({'type': 'STRING', 'name': 'max', 'value': max_val})
    if min_val is not None:
        fields.append({'type': 'STRING', 'name': 'min', 'value': min_val})
    fields.extend(_threshold_fields(thresholds))
    fields.append({'type': 'INTEGER', 'name': 'th_show_arc', 'value': '1'})
    fields.append({'type': 'INTEGER', 'name': 'th_show_labels', 'value': '0'})
    if units:
        fields.append({'type': 'STRING', 'name': 'units', 'value': units})
    return widget(
        'gauge',
        name,
        width=pos.get('width', '18'),
        height=pos.get('height', '4'),
        x=pos.get('x'),
        y=pos.get('y'),
        fields=fields,
    )


def svggraph(
    name: str,
    series: list[tuple[str, str]],
    *,
    reference: str,
    lefty_min: str | None = None,
    lefty_max: str | None = None,
    legend: str = '1',
    show_problems: str = '1',
    **pos,
) -> list[str]:
    fields: list[dict] = []
    for idx, (_key, color) in enumerate(series):
        fields.append({'type': 'STRING', 'name': f'ds.0.color.{idx}', 'value': color})
    fields.append({'type': 'INTEGER', 'name': 'ds.0.dataset_type', 'value': '0'})
    for idx, (key, _color) in enumerate(series):
        fields.append({'type': 'ITEM', 'name': f'ds.0.itemids.{idx}', 'value': {'host': TPL, 'key': key}})
    if lefty_max is not None:
        fields.append({'type': 'STRING', 'name': 'lefty_max', 'value': lefty_max})
    if lefty_min is not None:
        fields.append({'type': 'STRING', 'name': 'lefty_min', 'value': lefty_min})
    fields.append({'type': 'STRING', 'name': 'reference', 'value': reference})
    fields.append({'type': 'INTEGER', 'name': 'show_problems', 'value': show_problems})
    fields.append({'type': 'INTEGER', 'name': 'legend', 'value': legend})
    return widget('svggraph', name, width=pos.get('width', '36'), height=pos.get('height', '6'), x=pos.get('x'), y=pos.get('y'), fields=fields)


def problems_strip(*, y: str = '4', reference: str = 'CPROB') -> list[str]:
    return widget(
        'problems',
        'Problems',
        y=y,
        width='72',
        height='3',
        fields=[
            {'type': 'STRING', 'name': 'reference', 'value': reference},
            {'type': 'INTEGER', 'name': 'show', 'value': '3'},
            {'type': 'INTEGER', 'name': 'show_opdata', 'value': '2'},
            {'type': 'INTEGER', 'name': 'show_tags', 'value': '1'},
            {'type': 'STRING', 'name': 'tag_priority', 'value': 'site, connection_type, ha_role, port_kind, dest_type'},
        ],
    )


def navigator_and_history(
    *,
    items: list[str],
    nav_ref: str,
    graph_ref: str,
    group_tag: str = 'site',
    group_tags: list[str] | None = None,
    nav_name: str = 'Counters',
    y: str | None = None,
    height: str = '11',
    nav_width: str = '28',
) -> list[str]:
    tags = list(group_tags or [group_tag])
    nav_fields: list[dict] = []
    for idx, tag in enumerate(tags):
        nav_fields.append({'type': 'INTEGER', 'name': f'group_by.{idx}.attribute', 'value': '3'})
        nav_fields.append({'type': 'STRING', 'name': f'group_by.{idx}.tag_name', 'value': tag})
    for idx, item in enumerate(items):
        nav_fields.append({'type': 'STRING', 'name': f'items.{idx}', 'value': item})
    nav_fields.append({'type': 'STRING', 'name': 'reference', 'value': nav_ref})
    graph_width = str(72 - int(nav_width))
    return [
        *widget(
            'itemnavigator',
            nav_name,
            width=nav_width,
            height=height,
            y=y,
            fields=nav_fields,
        ),
        *widget(
            'svggraph',
            'History',
            x=nav_width,
            y=y,
            width=graph_width,
            height=height,
            fields=[
                {'type': 'STRING', 'name': 'ds.0.color.0', 'value': '42A5F5'},
                {'type': 'INTEGER', 'name': 'ds.0.dataset_type', 'value': '0'},
                {'type': 'STRING', 'name': 'ds.0.itemids.0._reference', 'value': f'{nav_ref}._itemid'},
                {'type': 'STRING', 'name': 'reference', 'value': graph_ref},
                {'type': 'INTEGER', 'name': 'legend', 'value': '0'},
                {'type': 'INTEGER', 'name': 'righty', 'value': '0'},
            ],
        ),
    ]


def navigator_and_latest(
    *,
    items: list[str],
    nav_ref: str,
    item_ref: str,
    group_tags: list[str],
    nav_name: str = 'Details',
    latest_name: str = 'Latest',
    y: str | None = None,
    height: str = '6',
    nav_width: str = '28',
    desc_size: str = '11',
    value_size: str = '20',
) -> list[str]:
    """CHAR/identity navigator. Latest value is text, never a graph."""
    nav_fields: list[dict] = []
    for idx, tag in enumerate(group_tags):
        nav_fields.append({'type': 'INTEGER', 'name': f'group_by.{idx}.attribute', 'value': '3'})
        nav_fields.append({'type': 'STRING', 'name': f'group_by.{idx}.tag_name', 'value': tag})
    for idx, item in enumerate(items):
        nav_fields.append({'type': 'STRING', 'name': f'items.{idx}', 'value': item})
    nav_fields.append({'type': 'STRING', 'name': 'reference', 'value': nav_ref})
    graph_width = str(72 - int(nav_width))
    return [
        *widget(
            'itemnavigator',
            nav_name,
            width=nav_width,
            height=height,
            y=y,
            fields=nav_fields,
        ),
        *widget(
            'item',
            latest_name,
            x=nav_width,
            y=y,
            width=graph_width,
            height=height,
            fields=[
                {'type': 'STRING', 'name': 'itemid._reference', 'value': f'{nav_ref}._itemid'},
                {'type': 'INTEGER', 'name': 'show.0', 'value': '1'},
                {'type': 'INTEGER', 'name': 'show.1', 'value': '2'},
                {'type': 'INTEGER', 'name': 'desc_size', 'value': desc_size},
                {'type': 'INTEGER', 'name': 'value_bold', 'value': '1'},
                {'type': 'INTEGER', 'name': 'value_size', 'value': value_size},
                {'type': 'STRING', 'name': 'reference', 'value': item_ref},
            ],
        ),
    ]


def health_overview_widgets() -> list[str]:
    return [
        *gauge_tile('Snapshot', 'cato.api.snapshot.available'),
        *gauge_tile('Metrics', 'cato.api.metrics.available', x='18'),
        *item_tile('Sites up', 'cato.site.up.count', x='36', thresholds=UP_THRESHOLDS, decimal_places='0'),
        *item_tile('Sockets up', 'cato.socket.up.count', x='54', thresholds=UP_THRESHOLDS, decimal_places='0'),
        *problems_strip(),
        *honeycomb_status(
            'Sites',
            'Cato site *: Connectivity',
            honeycomb_label('Cato site', 'Connectivity'),
            reference='CHSIT',
            y='7',
            height='6',
        ),
        *svggraph(
            'Census',
            [
                ('cato.site.discovery.count', '199C0D'),
                ('cato.socket.discovery.count', '2774A4'),
                ('cato.wan.discovery.count', 'F7941D'),
            ],
            reference='CHCEN',
            lefty_min='0',
            y='13',
        ),
        *svggraph(
            'Worst overlay loss',
            [('cato.wan.loss.worst.pct', 'FF465C')],
            reference='CHLOS',
            lefty_min='0',
            lefty_max='10',
            legend='0',
            x='36',
            y='13',
        ),
    ]


def health_census_widgets() -> list[str]:
    return [
        *item_tile('Sites', 'cato.site.discovery.count', decimal_places='0'),
        *item_tile('Sockets', 'cato.socket.discovery.count', x='18', decimal_places='0'),
        *item_tile('WAN links', 'cato.wan.discovery.count', x='36', decimal_places='0'),
        *item_tile('SLA rows', 'cato.wan.metrics.discovery.count', x='54', decimal_places='0'),
        *item_tile('Sites up', 'cato.site.up.count', y='4', thresholds=UP_THRESHOLDS, decimal_places='0'),
        *item_tile('Sockets up', 'cato.socket.up.count', x='18', y='4', thresholds=UP_THRESHOLDS, decimal_places='0'),
        *item_tile('WAN up', 'cato.wan.up.count', x='36', y='4', thresholds=UP_THRESHOLDS, decimal_places='0'),
        *item_tile('Degraded', 'cato.site.degraded.count', x='54', y='4', thresholds=DEGRADED_THRESHOLDS, decimal_places='0'),
        *gauge_tile(
            'Worst overlay loss',
            'cato.wan.loss.worst.pct',
            y='8',
            min_val='0',
            max_val='10',
            units='%',
            thresholds=LOSS_THRESHOLDS,
            decimal_places='1',
        ),
        *gauge_tile(
            'Worst overlay RTT',
            'cato.wan.rtt.worst.ms',
            x='18',
            y='8',
            min_val='0',
            max_val='200',
            units='ms',
            thresholds=RTT_THRESHOLDS,
            decimal_places='0',
        ),
        *gauge_tile(
            'Worst last-mile loss',
            'cato.wan.lastmile.loss.worst.pct',
            x='36',
            y='8',
            min_val='0',
            max_val='10',
            units='%',
            thresholds=LOSS_THRESHOLDS,
            decimal_places='1',
        ),
        *gauge_tile(
            'Worst RX util',
            'cato.wan.rx.util.worst.pct',
            x='54',
            y='8',
            min_val='0',
            max_val='100',
            units='%',
            thresholds=UTIL_THRESHOLDS,
            decimal_places='0',
        ),
        *svggraph(
            'Discovery',
            [
                ('cato.site.discovery.count', '199C0D'),
                ('cato.socket.discovery.count', '2774A4'),
                ('cato.wan.discovery.count', 'F7941D'),
                ('cato.wan.metrics.discovery.count', '42A5F5'),
            ],
            reference='CCDIS',
            lefty_min='0',
            y='12',
        ),
        *svggraph(
            'Connected',
            [
                ('cato.site.up.count', '0EC9AC'),
                ('cato.socket.up.count', '199C0D'),
                ('cato.wan.up.count', '2774A4'),
            ],
            reference='CCUP',
            lefty_min='0',
            x='36',
            y='12',
        ),
    ]


def health_degraded_widgets() -> list[str]:
    return [
        *gauge_tile('Snapshot', 'cato.api.snapshot.available'),
        *gauge_tile('Metrics', 'cato.api.metrics.available', x='18'),
        *item_tile('Sites up', 'cato.site.up.count', x='36', thresholds=UP_THRESHOLDS, decimal_places='0'),
        *item_tile('Degraded', 'cato.site.degraded.count', x='54', thresholds=DEGRADED_THRESHOLDS, decimal_places='0'),
        *problems_strip(),
        *honeycomb_status(
            'Degraded',
            'Cato site *: Degraded',
            honeycomb_label('Cato site', 'Degraded'),
            reference='CHDEG',
            y='7',
            height='6',
            thresholds=DEGRADED_THRESHOLDS,
        ),
        *navigator_and_history(
            nav_name='Degraded',
            group_tags=['site', 'connection_type'],
            nav_ref='CDEGN',
            graph_ref='CDEGG',
            y='13',
            height='5',
            items=[
                'Cato site *: Degraded',
                'Cato site *: Connectivity',
                'Cato site *: Host count',
                'Cato site *: HA ready',
            ],
        ),
        *navigator_and_latest(
            items=[
                'Cato site *: Degraded reasons',
                'Cato site *: Operational status',
                'Cato site *: POP',
            ],
            nav_ref='DGDET',
            item_ref='DGVAL',
            group_tags=['site', 'connection_type'],
            y='18',
            height='5',
        ),
    ]


def health_api_widgets() -> list[str]:
    return [
        *item_tile('Snapshot GraphQL', 'cato.api.snapshot.error_count', thresholds=ERROR_THRESHOLDS),
        *item_tile('Metrics GraphQL', 'cato.api.metrics.error_count', x='18', thresholds=ERROR_THRESHOLDS),
        *item_tile('Snapshot schema', 'cato.api.snapshot.schema_violation_count', x='36', thresholds=ERROR_THRESHOLDS),
        *item_tile('Metrics schema', 'cato.api.metrics.schema_violation_count', x='54', thresholds=ERROR_THRESHOLDS),
        *item_tile(
            'Unsupported items',
            'zabbix[host,,items_unsupported]',
            y='4',
            thresholds=ERROR_THRESHOLDS,
        ),
        *gauge_tile('Snapshot', 'cato.api.snapshot.available', x='18', y='4'),
        *gauge_tile('Metrics', 'cato.api.metrics.available', x='36', y='4'),
        *svggraph(
            'GraphQL errors',
            [
                ('cato.api.snapshot.error_count', 'FF465C'),
                ('cato.api.metrics.error_count', 'F7941D'),
            ],
            reference='CAPIE',
            lefty_min='0',
            y='8',
            width='36',
        ),
        *svggraph(
            'Schema violations',
            [
                ('cato.api.snapshot.schema_violation_count', 'FFD54F'),
                ('cato.api.metrics.schema_violation_count', 'FF9800'),
            ],
            reference='CAPIS',
            lefty_min='0',
            x='36',
            y='8',
            width='36',
        ),
    ]


def path_overview_widgets() -> list[str]:
    return [
        *honeycomb_metric(
            'Overlay loss',
            'Cato WAN *: Overlay loss',
            honeycomb_label('Cato WAN', 'Overlay loss'),
            LOSS_THRESHOLDS,
            reference='PLOSS',
            width='72',
            height='6',
        ),
        *honeycomb_metric(
            'Overlay RTT',
            'Cato WAN *: RTT',
            honeycomb_label('Cato WAN', 'RTT'),
            RTT_THRESHOLDS,
            reference='PRTT',
            y='6',
            height='5',
        ),
        *honeycomb_metric(
            'Overlay jitter',
            'Cato WAN *: Overlay jitter',
            honeycomb_label('Cato WAN', 'Overlay jitter'),
            JITTER_THRESHOLDS,
            reference='PJIT',
            x='36',
            y='6',
            height='5',
        ),
    ]


def path_lastmile_widgets() -> list[str]:
    return [
        *honeycomb_metric(
            'Last-mile loss',
            'Cato WAN *: Last-mile loss',
            honeycomb_label('Cato WAN', 'Last-mile loss'),
            LOSS_THRESHOLDS,
            reference='PLMLS',
            width='72',
            height='6',
        ),
        *honeycomb_metric(
            'Last-mile latency',
            'Cato WAN *: Last-mile latency',
            honeycomb_label('Cato WAN', 'Last-mile latency'),
            RTT_THRESHOLDS,
            reference='PLMLT',
            y='6',
            height='5',
        ),
        *honeycomb_metric(
            'RX utilization',
            'Cato WAN *: RX utilization',
            honeycomb_label('Cato WAN', 'RX utilization'),
            UTIL_THRESHOLDS,
            reference='PRXUT',
            x='36',
            y='6',
            height='5',
        ),
        *honeycomb_metric(
            'TX utilization',
            'Cato WAN *: TX utilization',
            honeycomb_label('Cato WAN', 'TX utilization'),
            UTIL_THRESHOLDS,
            reference='PTXUT',
            y='11',
            width='72',
            height='5',
        ),
    ]


def path_probe_widgets() -> list[str]:
    return navigator_and_history(
        group_tags=['site', 'connection_type', 'dest_type'],
        nav_ref='CNAVP',
        graph_ref='CGRFP',
        items=[
            'Cato WAN *: Overlay loss',
            'Cato WAN *: RTT',
            'Cato WAN *: Overlay jitter',
            'Cato WAN *: Last-mile loss',
            'Cato WAN *: Last-mile latency',
            'Cato WAN *: RX bandwidth',
            'Cato WAN *: TX bandwidth',
            'Cato WAN *: RX utilization',
            'Cato WAN *: TX utilization',
            'Cato WAN *: RX discarded',
            'Cato WAN *: TX discarded',
        ],
    )


def network_overview_widgets() -> list[str]:
    return [
        *honeycomb_status(
            'WAN links',
            'Cato WAN *: Connectivity',
            honeycomb_label('Cato WAN', 'Connectivity'),
            reference='NWAN',
            label_size='16',
            height='6',
        ),
        *honeycomb_status(
            'Sockets',
            'Cato Socket *: Connectivity',
            honeycomb_label('Cato Socket', 'Connectivity'),
            reference='NSOCK',
            y='6',
            height='5',
        ),
    ]


def network_tunnels_widgets() -> list[str]:
    tunnel_groups = ['site', 'connection_type', 'ha_role', 'dest_type']
    return [
        *navigator_and_history(
            nav_name='Tunnels',
            group_tags=tunnel_groups,
            nav_ref='CNNAV',
            graph_ref='CNGRA',
            height='6',
            items=[
                'Cato WAN *: Connectivity',
                'Cato WAN *: Tunnel uptime',
            ],
        ),
        *navigator_and_latest(
            items=[
                'Cato WAN *: POP',
                'Cato WAN *: Dest type',
                'Cato WAN *: Physical port',
                'Cato WAN *: ISP provider',
                'Cato WAN *: Tunnel remote IP',
                'Cato WAN *: Connection reason',
            ],
            nav_ref='CNDET',
            item_ref='CNVAL',
            group_tags=tunnel_groups,
            y='6',
            height='5',
        ),
    ]


def network_ha_widgets() -> list[str]:
    return [
        *honeycomb_status(
            'HA ready',
            'Cato site *: HA ready',
            honeycomb_label('Cato site', 'HA ready'),
            reference='NHAM',
            height='5',
        ),
        *navigator_and_history(
            nav_name='HA',
            group_tags=['site', 'connection_type'],
            nav_ref='NHAV',
            graph_ref='NHAG',
            y='5',
            height='6',
            items=[
                'Cato site *: HA ready',
                'Cato site *: HA enabled',
                'Cato Socket *: Uptime',
            ],
        ),
        *navigator_and_latest(
            items=[
                'Cato site *: HA readiness',
                'Cato site *: HA socket version',
                'Cato site *: Operational status',
            ],
            nav_ref='NHDET',
            item_ref='NHVAL',
            group_tags=['site', 'connection_type'],
            y='11',
            height='5',
        ),
    ]


def network_ports_widgets() -> list[str]:
    return [
        *honeycomb_status(
            'WAN media',
            'Cato wan port *: Media in',
            honeycomb_label('Cato wan port', 'Media in'),
            reference='NPWAN',
            label_size='16',
            height='6',
        ),
        *honeycomb_status(
            'LAN media',
            'Cato lan port *: Media in',
            honeycomb_label('Cato lan port', 'Media in'),
            reference='NPLAN',
            y='6',
            height='5',
        ),
        *navigator_and_history(
            nav_name='Ports',
            group_tags=['site', 'port_kind', 'ha_role', 'connection_type'],
            nav_ref='NPNAV',
            graph_ref='NPGRA',
            y='11',
            height='8',
            items=[
                'Cato wan port *: Media in',
                'Cato lan port *: Media in',
                'Cato wan port *: Link up',
                'Cato lan port *: Link up',
                'Cato wan port *: Has tunnel',
                'Cato wan port *: Has internet',
            ],
        ),
    ]


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
    site_conn_js = find_site_js() + connectivity_from_status_js('found.connectivityStatus')
    site_op_js = char_from_path_js(
        find_site_js(), 'found.operationalStatus', 'operationalStatus', optional=True
    )
    site_deg_js = (
        find_site_js()
        + 'var ds = found.degradedStatus || {};\n'
        + "if (ds.isDegraded === true || String(ds.isDegraded).toLowerCase() === 'true') {\n"
        + '  return 1;\n'
        + '}\n'
        + 'return 0;\n'
    )
    site_deg_reasons_js = (
        find_site_js()
        + 'var ds = found.degradedStatus || {};\n'
        + 'var details = Array.isArray(ds.degradedDetails) ? ds.degradedDetails : [];\n'
        + 'var reasons = [];\n'
        + 'for (var i = 0; i < details.length; i++) {\n'
        + '  if (details[i] && details[i].reason) {\n'
        + '    reasons.push(String(details[i].reason));\n'
        + '  }\n'
        + '}\n'
        + "return reasons.join(',');\n"
    )
    site_pop_js = char_from_path_js(find_site_js(), 'found.popName', 'POP', optional=True)
    site_hosts_js = (
        find_site_js()
        + 'var raw = found.hostCount;\n'
        + 'var numeric = Number(raw);\n'
        + "if (raw === undefined || raw === null || raw === '' || !isFinite(numeric)) {\n"
        + "  throw 'hostCount missing';\n"
        + '}\n'
        + 'return numeric;\n'
    )
    site_ha_js = (
        find_site_js()
        + 'var info = found.info || {};\n'
        + "if (info.isHA === true || String(info.isHA).toLowerCase() === 'true') {\n"
        + '  return 1;\n'
        + '}\n'
        + 'return 0;\n'
    )
    site_ready_js = char_from_path_js(
        find_site_js(), '(found.haStatus || {}).readiness', 'HA readiness', optional=True
    )
    site_ver_js = char_from_path_js(
        find_site_js(), '(found.haStatus || {}).socketVersion', 'HA socketVersion', optional=True
    )
    site_ready_code_js = (
        find_site_js()
        + 'var info = found.info || {};\n'
        + 'var ha = found.haStatus || {};\n'
        + "if (info.isHA === true || String(info.isHA).toLowerCase() === 'true') {\n"
        + "  return String(ha.readiness || '').toLowerCase() === 'ready' ? 1 : 0;\n"
        + '}\n'
        + 'return 1;\n'
    )
    sock_conn_js = find_device_js() + connectivity_from_bool_js('device.connected')
    sock_site_js = find_site_js() + connectivity_from_status_js('found.connectivityStatus')
    sock_ver_js = char_from_path_js(
        find_device_js(),
        'device.version || (device.socketInfo && device.socketInfo.version)',
        'socket version',
        optional=True,
    )
    sock_up_js = (
        find_device_js()
        + "if (device.deviceUptime === undefined || device.deviceUptime === null || device.deviceUptime === '') {\n"
        + "  throw 'deviceUptime missing';\n"
        + '}\n'
        + 'return device.deviceUptime;\n'
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
    wan_pop_js = char_from_path_js(find_iface_js(), 'iface.popName', 'POP', optional=True)
    wan_dest_js = char_from_path_js(
        find_iface_js(),
        '(iface.info && iface.info.destType) || iface.destType',
        'destType',
        optional=True,
    )
    wan_phys_js = char_from_path_js(
        find_iface_js(), 'iface.physicalPort', 'physicalPort', optional=True
    )
    wan_prov_js = char_from_path_js(
        find_iface_js(),
        'iface.tunnelRemoteIPInfo && iface.tunnelRemoteIPInfo.provider',
        'provider',
        optional=True,
    )
    wan_ip_js = char_from_path_js(
        find_iface_js(), 'iface.tunnelRemoteIP', 'tunnelRemoteIP', optional=True
    )
    wan_reason_js = char_from_path_js(
        find_iface_js(),
        'iface.tunnelConnectionReason',
        'tunnelConnectionReason',
        optional=True,
    )
    port_media_js = bool_item_js(find_port_js(), 'port.mediaIn')
    port_up_js = bool_item_js(find_port_js(), 'port.up')
    port_tunnel_js = bool_item_js(find_port_js(), 'port.hasTunnel')
    port_inet_js = bool_item_js(find_port_js(), 'port.hasInternet')
    port_kind_js = (
        "var kind = '{#PORT.KIND}';\n"
        "if (kind === 'wan') {\n"
        '  return 1;\n'
        '}\n'
        "if (kind === 'lan') {\n"
        '  return 2;\n'
        '}\n'
        'return 0;\n'
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
        *seed_item('site_deg_seed', 'Cato site degraded seed', 'cato.site.degraded[__seed]', 'UNSIGNED'),
        *seed_item('socket_seed', 'Cato Socket discovery seed', 'cato.socket.connected[__seed]', 'UNSIGNED'),
        *seed_item('wan_seed', 'Cato WAN discovery seed', 'cato.wan.connected[__seed]', 'UNSIGNED'),
        *seed_item(
            'site_ha_seed',
            'Cato site HA readiness seed',
            'cato.site.ha.readiness.code[__seed]',
            'UNSIGNED',
            value='1',
        ),
        *seed_item('sla_seed', 'Cato WAN SLA discovery seed', 'cato.wan.rx.bps[__seed]', 'FLOAT'),
        *seed_item('loss_seed', 'Cato overlay loss seed', 'cato.wan.loss.max.pct[__seed]', 'FLOAT'),
        *seed_item('rtt_seed', 'Cato overlay RTT seed', 'cato.wan.rtt.ms[__seed]', 'FLOAT'),
        *seed_item('jit_seed', 'Cato overlay jitter seed', 'cato.wan.jitter.max.ms[__seed]', 'FLOAT'),
        *seed_item(
            'lm_loss_seed',
            'Cato last-mile loss seed',
            'cato.wan.lastmile.loss.pct[__seed]',
            'FLOAT',
        ),
        *seed_item(
            'lm_lat_seed',
            'Cato last-mile latency seed',
            'cato.wan.lastmile.latency.ms[__seed]',
            'FLOAT',
        ),
        *seed_item('rx_util_seed', 'Cato RX utilization seed', 'cato.wan.rx.util.pct[__seed]', 'FLOAT'),
        *seed_item('tx_util_seed', 'Cato TX utilization seed', 'cato.wan.tx.util.pct[__seed]', 'FLOAT'),
        *census_item('site_count', 'Cato discovered Socket site count', 'cato.site.discovery.count', 'cato.site.connected[*]', 'site_count_tr', 'Cato census: fewer Socket sites than expected', '{$CATO.SITES.EXPECTED}', 'cato.api.snapshot.available'),
        *census_item('socket_count', 'Cato discovered Socket count', 'cato.socket.discovery.count', 'cato.socket.connected[*,*]', 'socket_count_tr', 'Cato census: fewer Sockets than expected', '{$CATO.SOCKETS.EXPECTED}', 'cato.api.snapshot.available'),
        *census_item('wan_count', 'Cato discovered WAN link count', 'cato.wan.discovery.count', 'cato.wan.connected[*,*,*]', 'wan_count_tr', 'Cato census: fewer WAN links than expected', '{$CATO.WAN.EXPECTED}', 'cato.api.snapshot.available'),
        *census_item('sla_count', 'Cato discovered WAN SLA row count', 'cato.wan.metrics.discovery.count', 'cato.wan.rx.bps[*,*]', 'sla_count_tr', 'Cato census: fewer WAN SLA rows than expected', '{$CATO.SLA.EXPECTED}', 'cato.api.metrics.available'),
        *calc_item('site_up', 'Cato connected Socket site count', 'cato.site.up.count', 'sum(last_foreach(//cato.site.connected[*]))'),
        *calc_item('socket_up', 'Cato connected Socket count', 'cato.socket.up.count', 'sum(last_foreach(//cato.socket.connected[*,*]))'),
        *calc_item('wan_up', 'Cato connected WAN link count', 'cato.wan.up.count', 'sum(last_foreach(//cato.wan.connected[*,*,*]))'),
        *calc_item('site_degraded', 'Cato degraded Socket site count', 'cato.site.degraded.count', 'sum(last_foreach(//cato.site.degraded[*]))'),
        *calc_item('ha_not_ready', 'Cato HA not-ready site count', 'cato.site.ha.not_ready.count', 'count(exists_foreach(//cato.site.ha.readiness.code[*]?[not (tag="cato_seed:seed")]))-sum(last_foreach(//cato.site.ha.readiness.code[*]?[not (tag="cato_seed:seed")]))'),
        *calc_item('wan_loss_worst', 'Cato worst overlay loss', 'cato.wan.loss.worst.pct', 'max(last_foreach(//cato.wan.loss.max.pct[*,*]))', units='%'),
        *calc_item('wan_rtt_worst', 'Cato worst overlay RTT', 'cato.wan.rtt.worst.ms', 'max(last_foreach(//cato.wan.rtt.ms[*,*]))', units='ms'),
        *calc_item('wan_jit_worst', 'Cato worst overlay jitter', 'cato.wan.jitter.worst.ms', 'max(last_foreach(//cato.wan.jitter.max.ms[*,*]))', units='ms'),
        *calc_item('wan_lm_loss_worst', 'Cato worst last-mile loss', 'cato.wan.lastmile.loss.worst.pct', 'max(last_foreach(//cato.wan.lastmile.loss.pct[*,*]))', units='%'),
        *calc_item('wan_lm_lat_worst', 'Cato worst last-mile latency', 'cato.wan.lastmile.latency.worst.ms', 'max(last_foreach(//cato.wan.lastmile.latency.ms[*,*]))', units='ms'),
        *calc_item('wan_rx_util_worst', 'Cato worst RX utilization', 'cato.wan.rx.util.worst.pct', 'max(last_foreach(//cato.wan.rx.util.pct[*,*]))', units='%'),
        *calc_item('wan_tx_util_worst', 'Cato worst TX utilization', 'cato.wan.tx.util.worst.pct', 'max(last_foreach(//cato.wan.tx.util.pct[*,*]))', units='%'),
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
            extra_tags=SITE_TAGS,
            triggers=[{
                'uid': 'site_conn_tr',
                'expression': f'max(/{TPL}/cato.site.connected[{{#SITE.ID}}],#3)=0',
                'name': 'Cato site {#SITE.NAME}: Disconnected',
                'priority': 'HIGH',
            }],
        ),
        *proto_item(
            uid_key='site_op',
            name='Cato site {#SITE.NAME}: Operational status',
            key='cato.site.operational_status[{#SITE.ID}]',
            master='cato.account.snapshot',
            js=site_op_js,
            scope='site',
            value_type='CHAR',
            valuemap=None,
            extra_tags=SITE_TAGS,
        ),
        *proto_item(
            uid_key='site_deg',
            name='Cato site {#SITE.NAME}: Degraded',
            key='cato.site.degraded[{#SITE.ID}]',
            master='cato.account.snapshot',
            js=site_deg_js,
            scope='site',
            valuemap='Cato degraded',
            extra_tags=SITE_TAGS,
            triggers=[{
                'uid': 'site_deg_tr',
                'expression': (
                    f'last(/{TPL}/cato.site.connected[{{#SITE.ID}}])=1 and '
                    f'last(/{TPL}/cato.site.degraded[{{#SITE.ID}}])=1'
                ),
                'name': 'Cato site {#SITE.NAME}: Degraded',
                'priority': 'AVERAGE',
                'dependencies': [SITE_DISCONNECTED],
            }],
        ),
        *proto_item(
            uid_key='site_deg_reasons',
            name='Cato site {#SITE.NAME}: Degraded reasons',
            key='cato.site.degraded.reasons[{#SITE.ID}]',
            master='cato.account.snapshot',
            js=site_deg_reasons_js,
            scope='site',
            value_type='CHAR',
            valuemap=None,
            extra_tags=SITE_TAGS,
        ),
        *proto_item(
            uid_key='site_pop',
            name='Cato site {#SITE.NAME}: POP',
            key='cato.site.pop[{#SITE.ID}]',
            master='cato.account.snapshot',
            js=site_pop_js,
            scope='site',
            value_type='CHAR',
            valuemap=None,
            extra_tags=SITE_TAGS,
        ),
        *proto_item(
            uid_key='site_hosts',
            name='Cato site {#SITE.NAME}: Host count',
            key='cato.site.host_count[{#SITE.ID}]',
            master='cato.account.snapshot',
            js=site_hosts_js,
            scope='site',
            valuemap=None,
            extra_tags=SITE_TAGS,
        ),
        *proto_item(
            uid_key='site_ha',
            name='Cato site {#SITE.NAME}: HA enabled',
            key='cato.site.ha[{#SITE.ID}]',
            master='cato.account.snapshot',
            js=site_ha_js,
            scope='site',
            valuemap=None,
            extra_tags=SITE_TAGS,
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
            extra_tags=SITE_TAGS,
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
            uid_key='site_ready_code',
            name='Cato site {#SITE.NAME}: HA ready',
            key='cato.site.ha.readiness.code[{#SITE.ID}]',
            master='cato.account.snapshot',
            js=site_ready_code_js,
            scope='site',
            valuemap='Cato HA readiness',
            extra_tags=SITE_TAGS,
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
            extra_tags=SITE_TAGS,
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
            extra_tags=SOCKET_TAGS,
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
        *proto_item(
            uid_key='socket_site',
            name='Cato Socket {#SITE.NAME} / {#SERIAL}: Site connectivity',
            key='cato.socket.site_connected[{#SITE.ID},{#SOCKET.ID}]',
            master='cato.account.snapshot',
            js=sock_site_js,
            scope='socket',
            extra_tags=SOCKET_TAGS,
        ),
        *proto_item(
            uid_key='socket_ver',
            name='Cato Socket {#SITE.NAME} / {#SERIAL}: Version',
            key='cato.socket.version[{#SITE.ID},{#SOCKET.ID}]',
            master='cato.account.snapshot',
            js=sock_ver_js,
            scope='socket',
            value_type='CHAR',
            valuemap=None,
            extra_tags=SOCKET_TAGS,
        ),
        *proto_item(
            uid_key='socket_uptime',
            name='Cato Socket {#SITE.NAME} / {#SERIAL}: Uptime',
            key='cato.socket.uptime[{#SITE.ID},{#SOCKET.ID}]',
            master='cato.account.snapshot',
            js=sock_up_js,
            scope='socket',
            valuemap=None,
            units='uptime',
            extra_tags=SOCKET_TAGS,
        ),
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
            extra_tags=WAN_TAGS,
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
        *proto_item(uid_key='wan_site', name='Cato WAN {#SITE.NAME} / {#SERIAL} / {#LINK.NAME}: Site connectivity', key='cato.wan.site_connected[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]', master='cato.account.snapshot', js=wan_site_js, scope='wan', extra_tags=WAN_TAGS),
        *proto_item(uid_key='wan_uptime', name='Cato WAN {#SITE.NAME} / {#SERIAL} / {#LINK.NAME}: Tunnel uptime', key='cato.wan.tunnel_uptime[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]', master='cato.account.snapshot', js=wan_up_js, scope='wan', valuemap=None, units='uptime', extra_tags=WAN_TAGS),
        *proto_item(uid_key='wan_pop', name='Cato WAN {#SITE.NAME} / {#SERIAL} / {#LINK.NAME}: POP', key='cato.wan.pop[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]', master='cato.account.snapshot', js=wan_pop_js, scope='wan', value_type='CHAR', valuemap=None, extra_tags=WAN_TAGS),
        *proto_item(uid_key='wan_dest', name='Cato WAN {#SITE.NAME} / {#SERIAL} / {#LINK.NAME}: Dest type', key='cato.wan.dest_type[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]', master='cato.account.snapshot', js=wan_dest_js, scope='wan', value_type='CHAR', valuemap=None, extra_tags=WAN_TAGS),
        *proto_item(uid_key='wan_phys', name='Cato WAN {#SITE.NAME} / {#SERIAL} / {#LINK.NAME}: Physical port', key='cato.wan.physical_port[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]', master='cato.account.snapshot', js=wan_phys_js, scope='wan', value_type='CHAR', valuemap=None, extra_tags=WAN_TAGS),
        *proto_item(uid_key='wan_prov', name='Cato WAN {#SITE.NAME} / {#SERIAL} / {#LINK.NAME}: ISP provider', key='cato.wan.provider[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]', master='cato.account.snapshot', js=wan_prov_js, scope='wan', value_type='CHAR', valuemap=None, extra_tags=WAN_TAGS),
        *proto_item(uid_key='wan_ip', name='Cato WAN {#SITE.NAME} / {#SERIAL} / {#LINK.NAME}: Tunnel remote IP', key='cato.wan.remote_ip[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]', master='cato.account.snapshot', js=wan_ip_js, scope='wan', value_type='CHAR', valuemap=None, extra_tags=WAN_TAGS),
        *proto_item(uid_key='wan_reason', name='Cato WAN {#SITE.NAME} / {#SERIAL} / {#LINK.NAME}: Connection reason', key='cato.wan.connection_reason[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]', master='cato.account.snapshot', js=wan_reason_js, scope='wan', value_type='CHAR', valuemap=None, extra_tags=WAN_TAGS),
        f'    - uuid: {uid("port_lld")}',
        '      name: Cato Socket port discovery',
        '      type: DEPENDENT',
        '      key: cato.port.discovery',
        "      delay: '0'",
        '      lifetime: 7d',
        '      preprocessing:',
        '      - type: JAVASCRIPT',
        '        parameters:',
        *js_block(load_lld_js('cato.port.discovery'), 8),
        '      master_item:',
        '        key: cato.account.snapshot',
        '      item_prototypes:',
        *proto_item(
            uid_key='port_media',
            name='Cato {#PORT.KIND} port {#SITE.NAME} / {#SERIAL} / {#PORT.ID}: Media in',
            key='cato.port.media_in[{#SITE.ID},{#SOCKET.ID},{#PORT.ID}]',
            master='cato.account.snapshot',
            js=port_media_js,
            scope='port',
            extra_tags=PORT_TAGS,
            triggers=[
                {
                    'uid': 'port_wan_media_tr',
                    'expression': (
                        f'max(/{TPL}/cato.port.media_in[{{#SITE.ID}},{{#SOCKET.ID}},{{#PORT.ID}}],#3)=0 and '
                        f'last(/{TPL}/cato.port.kind.code[{{#SITE.ID}},{{#SOCKET.ID}},{{#PORT.ID}}])=1'
                    ),
                    'name': 'Cato wan port {#SITE.NAME} / {#SERIAL} / {#PORT.ID}: Media down',
                    'priority': 'AVERAGE',
                    'dependencies': [SITE_DISCONNECTED],
                },
                {
                    'uid': 'port_lan_media_tr',
                    'expression': (
                        f'max(/{TPL}/cato.port.media_in[{{#SITE.ID}},{{#SOCKET.ID}},{{#PORT.ID}}],#3)=0 and '
                        f'last(/{TPL}/cato.port.kind.code[{{#SITE.ID}},{{#SOCKET.ID}},{{#PORT.ID}}])=2'
                    ),
                    'name': 'Cato lan port {#SITE.NAME} / {#SERIAL} / {#PORT.ID}: Media down',
                    'priority': 'WARNING',
                    'dependencies': [SITE_DISCONNECTED],
                },
            ],
        ),
        *proto_item(
            uid_key='port_up',
            name='Cato {#PORT.KIND} port {#SITE.NAME} / {#SERIAL} / {#PORT.ID}: Link up',
            key='cato.port.up[{#SITE.ID},{#SOCKET.ID},{#PORT.ID}]',
            master='cato.account.snapshot',
            js=port_up_js,
            scope='port',
            extra_tags=PORT_TAGS,
        ),
        *proto_item(
            uid_key='port_tunnel',
            name='Cato {#PORT.KIND} port {#SITE.NAME} / {#SERIAL} / {#PORT.ID}: Has tunnel',
            key='cato.port.has_tunnel[{#SITE.ID},{#SOCKET.ID},{#PORT.ID}]',
            master='cato.account.snapshot',
            js=port_tunnel_js,
            scope='port',
            extra_tags=PORT_TAGS,
            triggers=[{
                'uid': 'port_wan_tunnel_tr',
                'expression': (
                    f'last(/{TPL}/cato.port.media_in[{{#SITE.ID}},{{#SOCKET.ID}},{{#PORT.ID}}])=1 and '
                    f'max(/{TPL}/cato.port.has_tunnel[{{#SITE.ID}},{{#SOCKET.ID}},{{#PORT.ID}}],#3)=0 and '
                    f'last(/{TPL}/cato.port.kind.code[{{#SITE.ID}},{{#SOCKET.ID}},{{#PORT.ID}}])=1 and '
                    '{#TUNNEL.ALERT}=1'
                ),
                'name': 'Cato wan port {#SITE.NAME} / {#SERIAL} / {#PORT.ID}: No tunnel while media is up',
                'priority': 'AVERAGE',
                'dependencies': [SITE_DISCONNECTED],
            }],
        ),
        *proto_item(
            uid_key='port_inet',
            name='Cato {#PORT.KIND} port {#SITE.NAME} / {#SERIAL} / {#PORT.ID}: Has internet',
            key='cato.port.has_internet[{#SITE.ID},{#SOCKET.ID},{#PORT.ID}]',
            master='cato.account.snapshot',
            js=port_inet_js,
            scope='port',
            extra_tags=PORT_TAGS,
        ),
        *proto_item(
            uid_key='port_kind',
            name='Cato {#PORT.KIND} port {#SITE.NAME} / {#SERIAL} / {#PORT.ID}: Kind',
            key='cato.port.kind.code[{#SITE.ID},{#SOCKET.ID},{#PORT.ID}]',
            master='cato.account.snapshot',
            js=port_kind_js,
            scope='port',
            valuemap='Cato port kind',
            extra_tags=PORT_TAGS,
        ),
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
        *proto_item(uid_key='sla_rx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: RX bandwidth', key='cato.wan.rx.bps[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('bytesDownstream', 'RX rate', '8'), scope='wan_sla', extra_tags=SLA_TAGS, value_type='FLOAT', valuemap=None, units='bps', trends='365d'),
        *proto_item(uid_key='sla_tx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: TX bandwidth', key='cato.wan.tx.bps[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('bytesUpstream', 'TX rate', '8'), scope='wan_sla', extra_tags=SLA_TAGS, value_type='FLOAT', valuemap=None, units='bps', trends='365d'),
        *proto_item(uid_key='sla_loss_rx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: RX packet loss', key='cato.wan.loss.rx.pct[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('lostDownstreamPcnt', 'RX loss'), scope='wan_sla', extra_tags=SLA_TAGS, value_type='FLOAT', valuemap=None, units='%', trends='365d'),
        *proto_item(uid_key='sla_loss_tx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: TX packet loss', key='cato.wan.loss.tx.pct[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('lostUpstreamPcnt', 'TX loss'), scope='wan_sla', extra_tags=SLA_TAGS, value_type='FLOAT', valuemap=None, units='%', trends='365d'),
        *calc_proto(
            uid_key='sla_loss_max',
            name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: Overlay loss',
            key='cato.wan.loss.max.pct[{#SITE.ID},{#LINK.ID}]',
            params=f'max(last(//cato.wan.loss.rx.pct[{{#SITE.ID}},{{#LINK.ID}}]),last(//cato.wan.loss.tx.pct[{{#SITE.ID}},{{#LINK.ID}}]))',
            scope='wan_sla', extra_tags=SLA_TAGS,
            units='%',
        ),
        *proto_item(uid_key='sla_jit_rx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: RX jitter', key='cato.wan.jitter.rx.ms[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('jitterDownstream', 'RX jitter'), scope='wan_sla', extra_tags=SLA_TAGS, value_type='FLOAT', valuemap=None, units='ms', trends='365d'),
        *proto_item(uid_key='sla_jit_tx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: TX jitter', key='cato.wan.jitter.tx.ms[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('jitterUpstream', 'TX jitter'), scope='wan_sla', extra_tags=SLA_TAGS, value_type='FLOAT', valuemap=None, units='ms', trends='365d'),
        *calc_proto(
            uid_key='sla_jit_max',
            name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: Overlay jitter',
            key='cato.wan.jitter.max.ms[{#SITE.ID},{#LINK.ID}]',
            params='max(last(//cato.wan.jitter.rx.ms[{#SITE.ID},{#LINK.ID}]),last(//cato.wan.jitter.tx.ms[{#SITE.ID},{#LINK.ID}]))',
            scope='wan_sla', extra_tags=SLA_TAGS,
            units='ms',
        ),
        *proto_item(
            uid_key='sla_rtt',
            name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: RTT',
            key='cato.wan.rtt.ms[{#SITE.ID},{#LINK.ID}]',
            master='cato.account.metrics',
            js=metric_js('rtt', 'RTT'),
            scope='wan_sla', extra_tags=SLA_TAGS,
            value_type='FLOAT',
            valuemap=None,
            units='ms',
            trends='365d',
        ),
        *proto_item(
            uid_key='sla_lm_loss',
            name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: Last-mile loss',
            key='cato.wan.lastmile.loss.pct[{#SITE.ID},{#LINK.ID}]',
            master='cato.account.metrics',
            js=timeseries_metric_js('lastMilePacketLoss', 'last-mile loss'),
            scope='wan_sla', extra_tags=SLA_TAGS,
            value_type='FLOAT',
            valuemap=None,
            units='%',
            trends='365d',
        ),
        *proto_item(uid_key='sla_lm_lat', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: Last-mile latency', key='cato.wan.lastmile.latency.ms[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=timeseries_metric_js('lastMileLatency', 'last-mile latency'), scope='wan_sla', extra_tags=SLA_TAGS, value_type='FLOAT', valuemap=None, units='ms', trends='365d'),
        *proto_item(uid_key='sla_disc_rx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: RX discarded', key='cato.wan.discard.rx.pps[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('packetsDiscardedDownstream', 'RX discarded'), scope='wan_sla', extra_tags=SLA_TAGS, value_type='FLOAT', valuemap=None, units='pps', trends='365d'),
        *proto_item(uid_key='sla_disc_tx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: TX discarded', key='cato.wan.discard.tx.pps[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=metric_js('packetsDiscardedUpstream', 'TX discarded'), scope='wan_sla', extra_tags=SLA_TAGS, value_type='FLOAT', valuemap=None, units='pps', trends='365d'),
        *proto_item(uid_key='sla_util_rx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: RX utilization', key='cato.wan.rx.util.pct[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=util_js('RX', 'downstreamBandwidth', 'bytesDownstream'), scope='wan_sla', extra_tags=SLA_TAGS, value_type='FLOAT', valuemap=None, units='%', trends='365d'),
        *proto_item(uid_key='sla_util_tx', name='Cato WAN {#SITE.NAME} / {#LINK.NAME}: TX utilization', key='cato.wan.tx.util.pct[{#SITE.ID},{#LINK.ID}]', master='cato.account.metrics', js=util_js('TX', 'upstreamBandwidth', 'bytesUpstream'), scope='wan_sla', extra_tags=SLA_TAGS, value_type='FLOAT', valuemap=None, units='%', trends='365d'),
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
            f'    - uuid: {uid("valuemap_ha")}',
            '      name: Cato HA readiness',
            '      mappings:',
            "      - value: '0'",
            '        newvalue: Not ready',
            "      - value: '1'",
            '        newvalue: Ready',
            f'    - uuid: {uid("valuemap_deg")}',
            '      name: Cato degraded',
            '      mappings:',
            "      - value: '0'",
            '        newvalue: OK',
            "      - value: '1'",
            '        newvalue: Degraded',
            f'    - uuid: {uid("valuemap_port")}',
            '      name: Cato port kind',
            '      mappings:',
            "      - value: '0'",
            '        newvalue: Other',
            "      - value: '1'",
            '        newvalue: WAN',
            "      - value: '2'",
            '        newvalue: LAN',
            '    dashboards:',
            f'    - uuid: {uid("dash_health")}',
            '      name: Health',
            '      pages:',
            '      - name: Overview',
            '        widgets:',
            *health_overview_widgets(),
            '      - name: Census',
            '        widgets:',
            *health_census_widgets(),
            '      - name: Degraded',
            '        widgets:',
            *health_degraded_widgets(),
            '      - name: API',
            '        widgets:',
            *health_api_widgets(),
            f'    - uuid: {uid("dash_path")}',
            '      name: Path',
            '      pages:',
            '      - name: Overview',
            '        widgets:',
            *path_overview_widgets(),
            '      - name: Last mile',
            '        widgets:',
            *path_lastmile_widgets(),
            '      - name: Probe',
            '        widgets:',
            *path_probe_widgets(),
            f'    - uuid: {uid("dash_net")}',
            '      name: Network',
            '      pages:',
            '      - name: Overview',
            '        widgets:',
            *network_overview_widgets(),
            '      - name: Tunnels',
            '        widgets:',
            *network_tunnels_widgets(),
            '      - name: Ports',
            '        widgets:',
            *network_ports_widgets(),
            '      - name: HA',
            '        widgets:',
            *network_ha_widgets(),
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
