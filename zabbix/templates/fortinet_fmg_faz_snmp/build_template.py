#!/usr/bin/env python3
"""Emit Fortinet FMG-FAZ Zabbix 7.0 YAML (parent + two Observability companions)."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))

from fmg_faz_snmp import (  # noqa: E402
    FMG_FAZ_PARENT_MACROS,
    FMG_FAZ_SNMP_TEMPLATE,
    FMG_FAZ_SNMP_YAML,
    FM_MIB,
    FN_SYS_SERIAL,
    FORTIANALYZER_OBSERVABILITY_TEMPLATE,
    FORTIANALYZER_OBSERVABILITY_YAML,
    FORTIANALYZER_TEMPLATE_MACROS,
    FORTIMANAGER_OBSERVABILITY_TEMPLATE,
    FORTIMANAGER_OBSERVABILITY_YAML,
    PARENT_ICMP_EXPR,
    PARENT_ICMP_NAME,
    PARENT_SNMP_EXPR,
    PARENT_SNMP_NAME,
)

T = FMG_FAZ_SNMP_TEMPLATE
FMG = FORTIMANAGER_OBSERVABILITY_TEMPLATE
FAZ = FORTIANALYZER_OBSERVABILITY_TEMPLATE
GROUP_UUID = '36bff6c29af64692839d077febfc7079'
ICMP_DEP = (PARENT_ICMP_NAME, PARENT_ICMP_EXPR)
SNMP_DEP = (PARENT_SNMP_NAME, PARENT_SNMP_EXPR)
HEALTH_DEPS = [ICMP_DEP, SNMP_DEP]
FAZ_PARENT_HEALTH_GATE = (
    f'max(/{FAZ}/icmpping,#3)=1 and '
    f'max(/{FAZ}/zabbix[host,snmp,available],{{$SNMP.TIMEOUT}})=1'
)


def require_faz_parent_health(expression: str) -> str:
    """Gate FAZ product alerts on the nested parent's reachability."""
    return f'({expression}) and {FAZ_PARENT_HEALTH_GATE}'




def uid() -> str:
    return uuid.uuid4().hex


def q(value: str) -> str:
    if value == '':
        return "''"
    special = set(":{}[]&*?|>'!%@`#")
    if any(c in special for c in value) or value != value.strip() or '\n' in value:
        return "'" + value.replace("'", "''") + "'"
    if value.lower() in {'y', 'n', 'yes', 'no', 'true', 'false', 'on', 'off', 'null'}:
        return "'" + value + "'"
    try:
        float(value)
    except ValueError:
        pass
    else:
        return "'" + value.replace("'", "''") + "'"
    if value[:1].isdigit() and '/' in value:
        return "'" + value + "'"
    return value


class Doc:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def add(self, indent: int, text: str) -> None:
        self.lines.append(('  ' * indent) + text)

    def dump(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(self.lines) + '\n', encoding='utf-8')


def tags(doc: Doc, indent: int, component: str, extra: list[tuple[str, str]] | None = None) -> None:
    doc.add(indent, 'tags:')
    doc.add(indent + 1, '- tag: component')
    doc.add(indent + 2, f'value: {component}')
    for tag, value in extra or []:
        doc.add(indent + 1, f'- tag: {tag}')
        doc.add(indent + 2, f'value: {q(value)}')


def trig(
    doc: Doc,
    indent: int,
    name: str,
    expression: str,
    priority: str,
    description: str,
    dependencies: list[tuple[str, str]] | None = None,
    recovery: str | None = None,
    status: str | None = None,
    manual_close: bool = False,
    scope: str = 'availability',
) -> None:
    doc.add(indent, '- uuid: ' + uid())
    doc.add(indent + 1, f'expression: {q(expression)}')
    if recovery:
        doc.add(indent + 1, 'recovery_mode: RECOVERY_EXPRESSION')
        doc.add(indent + 1, f'recovery_expression: {q(recovery)}')
    doc.add(indent + 1, f'name: {q(name)}')
    if status:
        doc.add(indent + 1, f'status: {status}')
    doc.add(indent + 1, f'priority: {priority}')
    doc.add(indent + 1, f'description: {q(description)}')
    if manual_close:
        doc.add(indent + 1, "manual_close: 'YES'")
    if dependencies:
        doc.add(indent + 1, 'dependencies:')
        for dep_name, dep_expr in dependencies:
            doc.add(indent + 2, f'- name: {q(dep_name)}')
            doc.add(indent + 3, f'expression: {q(dep_expr)}')
    doc.add(indent + 1, 'tags:')
    doc.add(indent + 2, '- tag: scope')
    doc.add(indent + 3, f'value: {scope}')


def preprocess(doc: Doc, indent: int, steps: list[tuple]) -> None:
    doc.add(indent, 'preprocessing:')
    for step in steps:
        kind = step[0]
        doc.add(indent + 1, f'- type: {kind}')
        if kind == 'JAVASCRIPT':
            doc.add(indent + 2, 'parameters:')
            doc.add(indent + 3, '- |')
            for line in step[1].splitlines():
                doc.add(indent + 4, line)
        elif kind == 'CHECK_NOT_SUPPORTED':
            doc.add(indent + 2, 'parameters:')
            doc.add(indent + 3, f"- '{step[1]}'")
            doc.add(indent + 2, 'error_handler: CUSTOM_VALUE')
            doc.add(indent + 2, f"error_handler_params: '{step[2]}'")
        elif kind == 'DISCARD_UNCHANGED_HEARTBEAT':
            doc.add(indent + 2, 'parameters:')
            doc.add(indent + 3, f'- {step[1]}')
        elif kind == 'CHANGE_PER_SECOND':
            pass
        elif kind == 'MULTIPLIER':
            doc.add(indent + 2, 'parameters:')
            doc.add(indent + 3, f"- '{step[1]}'")
        else:
            if len(step) > 1:
                doc.add(indent + 2, 'parameters:')
                doc.add(indent + 3, f'- {q(str(step[1]))}')


def field(doc: Doc, indent: int, typ: str, name: str, value, *, item_host: str | None = None, item_key: str | None = None, graph_host: str | None = None, graph_name: str | None = None) -> None:
    doc.add(indent, f'- type: {typ}')
    doc.add(indent + 1, f'name: {name}')
    if typ == 'ITEM':
        doc.add(indent + 1, 'value:')
        doc.add(indent + 2, f'host: {item_host}')
        doc.add(indent + 2, f'key: {q(item_key or "")}')
    elif typ == 'GRAPH_PROTOTYPE':
        doc.add(indent + 1, 'value:')
        doc.add(indent + 2, f'host: {graph_host}')
        doc.add(indent + 2, f'name: {q(graph_name or "")}')
    else:
        doc.add(indent + 1, f"value: '{value}'")


def gauge_fields(doc: Doc, indent: int, host: str, key: str, *, max_v=None, min_v=None, units=None, thresholds=None, decimals='0') -> None:
    doc.add(indent, 'fields:')
    for name, val in (
        ('angle', '270'),
        ('decimal_places', decimals),
        ('show.0', '2'),
        ('show.1', '5'),
        ('th_arc_size', '6'),
        ('units_size', '14'),
        ('value_arc_size', '16'),
        ('value_bold', '1'),
        ('value_size', '25'),
    ):
        field(doc, indent + 1, 'INTEGER', name, val)
    field(doc, indent + 1, 'ITEM', 'itemid.0', None, item_host=host, item_key=key)
    if max_v is not None:
        field(doc, indent + 1, 'STRING', 'max', max_v)
    if min_v is not None:
        field(doc, indent + 1, 'STRING', 'min', min_v)
    for i, (color, thr) in enumerate(thresholds or []):
        field(doc, indent + 1, 'STRING', f'thresholds.{i}.color', color)
        field(doc, indent + 1, 'STRING', f'thresholds.{i}.threshold', thr)
    field(doc, indent + 1, 'INTEGER', 'th_show_arc', '1')
    field(doc, indent + 1, 'INTEGER', 'th_show_labels', '0')
    if units:
        field(doc, indent + 1, 'STRING', 'units', units)


def svg_time_period(doc: Doc, indent: int) -> None:
    """Zabbix 7.0 rejects svggraph widgets that omit time_period.to."""
    field(doc, indent, 'STRING', 'time_period.from', 'now-1d')
    field(doc, indent, 'STRING', 'time_period.to', 'now')


def widget_xy(doc: Doc, indent: int, typ: str, name: str, *, x=None, y=None, width='18', height='4') -> None:
    doc.add(indent, f'- type: {typ}')
    doc.add(indent + 1, f'name: {name}')
    if x is not None:
        doc.add(indent + 1, f"x: '{x}'")
    if y is not None:
        doc.add(indent + 1, f"y: '{y}'")
    doc.add(indent + 1, f"width: '{width}'")
    doc.add(indent + 1, f"height: '{height}'")


def lld_fill_js(fields: list[str], extra: str = '') -> str:
    listed = ','.join(f"'{f}'" for f in fields)
    extra_block = extra
    return (
        'try {\n'
        '\tvar data = JSON.parse(value);\n'
        '} catch (error) {\n'
        "\tthrow 'Failed to parse JSON of FMG/FAZ discovery.';\n"
        '}\n'
        f'var fields = [{listed}];\n'
        'data.forEach(function (element) {\n'
        '\tfields.forEach(function (field) {\n'
        "\t\telement[field] = element[field] || '';\n"
        '\t});\n'
        f'{extra_block}'
        '});\n'
        'return JSON.stringify(data);'
    )


def header(doc: Doc) -> None:
    doc.add(0, 'zabbix_export:')
    doc.add(1, "version: '7.0'")
    doc.add(1, 'template_groups:')
    doc.add(2, f'- uuid: {GROUP_UUID}')
    doc.add(3, 'name: Templates/Network devices')
    doc.add(1, 'templates:')


def template_head(doc: Doc, uuid_s: str, name: str, description: str, nested: list[str] | None = None) -> None:
    doc.add(2, f'- uuid: {uuid_s}')
    doc.add(3, f'template: {q(name)}')
    doc.add(3, f'name: {q(name)}')
    doc.add(3, 'description: |')
    for line in description.strip('\n').splitlines():
        doc.add(4, line)
    doc.add(3, 'groups:')
    doc.add(4, '- name: Templates/Network devices')
    if nested:
        doc.add(3, 'templates:')
        for n in nested:
            doc.add(4, f'- name: {q(n)}')
    doc.add(3, 'items:')


def macros_block(doc: Doc, mapping: dict[str, str], descriptions: dict[str, str]) -> None:
    doc.add(3, 'macros:')
    for macro, value in mapping.items():
        doc.add(4, f'- macro: {q(macro)}')
        doc.add(5, f'value: {q(value)}')
        if macro in descriptions:
            doc.add(5, f'description: {q(descriptions[macro])}')


def vmap(doc: Doc, name: str, mappings: list[tuple[str, str]]) -> None:
    doc.add(4, '- uuid: ' + uid())
    doc.add(5, f'name: {q(name)}')
    doc.add(5, 'mappings:')
    for value, newvalue in mappings:
        doc.add(6, f"- value: '{value}'")
        doc.add(7, f'newvalue: {newvalue}')


def snmp(
    doc: Doc,
    name: str,
    oid: str,
    key: str,
    *,
    delay='1m',
    units=None,
    value_type=None,
    description='',
    component='system',
    extra_tags=None,
    steps=None,
    history=None,
    trends=None,
    valuemap=None,
    inventory=None,
    triggers=None,
    ns=None,
) -> None:
    doc.add(3, '- uuid: ' + uid())
    doc.add(4, f'name: {q(name)}')
    doc.add(4, 'type: SNMP_AGENT')
    doc.add(4, f'snmp_oid: {oid}')
    doc.add(4, f'key: {q(key)}')
    doc.add(4, f'delay: {delay}')
    if value_type:
        doc.add(4, f'value_type: {value_type}')
    if history:
        doc.add(4, f'history: {history}')
    if trends is not None:
        doc.add(4, f"trends: '{trends}'" if str(trends) == '0' else f'trends: {trends}')
    if units:
        doc.add(4, f'units: {q(units) if units in {"%", "logs/s", "°C"} else units}')
    if description:
        doc.add(4, f'description: {q(description)}')
    if valuemap:
        doc.add(4, 'valuemap:')
        doc.add(5, f'name: {q(valuemap)}')
    if inventory:
        doc.add(4, f'inventory_link: {inventory}')
    all_steps = list(steps or [])
    if ns is not None:
        all_steps.insert(0, ('CHECK_NOT_SUPPORTED', '-1', ns))
    if all_steps:
        preprocess(doc, 4, all_steps)
    tags(doc, 4, component, extra_tags)
    if triggers:
        doc.add(4, 'triggers:')
        for kwargs in triggers:
            trig(doc, 5, **kwargs)


def calc(
    doc: Doc,
    name: str,
    key: str,
    params: str,
    *,
    delay='1m',
    units=None,
    value_type='FLOAT',
    description='',
    component='health',
    valuemap=None,
    history=None,
    trends=None,
    triggers=None,
) -> None:
    doc.add(3, '- uuid: ' + uid())
    doc.add(4, f'name: {q(name)}')
    doc.add(4, 'type: CALCULATED')
    doc.add(4, f'key: {q(key)}')
    doc.add(4, f'delay: {delay}')
    doc.add(4, f'value_type: {value_type}')
    if history:
        doc.add(4, f'history: {history}')
    if trends is not None:
        doc.add(4, f"trends: '{trends}'" if str(trends) == '0' else f'trends: {trends}')
    if units == '%':
        doc.add(4, "units: '%'")
    elif units:
        doc.add(4, f'units: {units}')
    doc.add(4, f'params: {q(params)}')
    if description:
        doc.add(4, f'description: {q(description)}')
    if valuemap:
        doc.add(4, 'valuemap:')
        doc.add(5, f'name: {q(valuemap)}')
    tags(doc, 4, component)
    if triggers:
        doc.add(4, 'triggers:')
        for kwargs in triggers:
            trig(doc, 5, **kwargs)


def intern(
    doc: Doc,
    name: str,
    key: str,
    *,
    delay=None,
    units=None,
    value_type=None,
    description='',
    valuemap=None,
    item_type='INTERNAL',
    component='health',
    triggers=None,
) -> None:
    doc.add(3, '- uuid: ' + uid())
    doc.add(4, f'name: {q(name)}')
    doc.add(4, f'type: {item_type}')
    doc.add(4, f'key: {q(key)}')
    if delay:
        doc.add(4, f'delay: {delay}')
    if value_type:
        doc.add(4, f'value_type: {value_type}')
    if units == '%':
        doc.add(4, "units: '%'")
    elif units:
        doc.add(4, f'units: {units}')
    if description:
        doc.add(4, f'description: {q(description)}')
    if valuemap:
        doc.add(4, 'valuemap:')
        doc.add(5, f'name: {q(valuemap)}')
    tags(doc, 4, component)
    if triggers:
        doc.add(4, 'triggers:')
        for kwargs in triggers:
            trig(doc, 5, **kwargs)


def proto_item(
    doc: Doc,
    name: str,
    oid: str,
    key: str,
    *,
    delay='1m',
    units=None,
    value_type=None,
    component='hardware',
    extra_tags=None,
    steps=None,
    valuemap=None,
    history=None,
    trends=None,
    triggers=None,
    ns=None,
) -> None:
    doc.add(6, '- uuid: ' + uid())
    doc.add(7, f'name: {q(name)}')
    doc.add(7, 'type: SNMP_AGENT')
    doc.add(7, f'snmp_oid: {q(oid) if "{" in oid else oid}')
    doc.add(7, f'key: {q(key)}')
    doc.add(7, f'delay: {delay}')
    if value_type:
        doc.add(7, f'value_type: {value_type}')
    if history:
        doc.add(7, f'history: {history}')
    if trends is not None:
        doc.add(7, f"trends: '{trends}'" if str(trends) == '0' else f'trends: {trends}')
    if units:
        doc.add(7, f'units: {q(units) if units in {"%", "logs/s", "°C"} else units}')
    if valuemap:
        doc.add(7, 'valuemap:')
        doc.add(8, f'name: {q(valuemap)}')
    all_steps = list(steps or [])
    if ns is not None:
        all_steps.insert(0, ('CHECK_NOT_SUPPORTED', '-1', ns))
    if all_steps:
        preprocess(doc, 7, all_steps)
    tags(doc, 7, component, extra_tags)
    if triggers:
        doc.add(7, 'trigger_prototypes:')
        for kwargs in triggers:
            trig(doc, 8, **kwargs)


PARENT_DESC = f"""
SNMP template for FortiManager and FortiAnalyzer (shared FORTINET-FORTIMANAGER-FORTIANALYZER-MIB,
enterprises.12356.103, build 3737). There is no official Zabbix template (ZBXNEXT-10433).

Do not also link Network Generic or ICMP Ping (icmpping collision). Do not assign
FortiGate HTTP/SNMP. Platform Template Rules FortiManager / FortiAnalyzer point at
the Observability companions, which nest this parent.

Health (Overview / Hardware / Cluster) and Network interfaces ship here — same chrome
as EXOS/VOSS/IQ. Device and log product boards live on the companions.

Operator page: zabbix/03-fortinet.md. OIDs: templates/fortinet_fmg_faz_snmp/OID_MAPPING.md.
"""

MACRO_HELP = {
    '{$ICMP_LOSS_WARN}': 'Disabled trigger threshold. CH proxy loss is WAN.',
    '{$ICMP_RESPONSE_TIME_WARN}': 'Disabled trigger threshold. CH proxy RTT is WAN.',
    '{$SNMP.TIMEOUT}': 'Time interval for the SNMP availability trigger.',
    '{$CPU.UTIL.WARN}': 'CPU Warning. Not a page.',
    '{$CPU.UTIL.CRIT}': '101 silences CPU High (same bar as FortiGate HTTP).',
    '{$MEMORY.UTIL.MAX}': 'Memory Average % (5m).',
    '{$DISK.UTIL.WARN}': 'Disk Warning %.',
    '{$DISK.UTIL.CRIT}': 'Disk Average %. FAZ High lives on FortiAnalyzer Observability.',
    '{$IF.UTIL.MAX}': '101 silences interface util until a commit baseline exists.',
    '{$IF.ERRORS.WARN}': 'Warning threshold of in-or-out error rate (errors/s).',
    '{$IFCONTROL}': '1=alert discovered link-down. Context {#IFNAME} to mute.',
    '{$NET.IF.IFNAME.MATCHES}': 'Physical mgmt/HA ports. Override per device if needed.',
    '{$NET.IF.IFNAME.NOT_MATCHES}': 'Drop logical overlay ifaces.',
    '{$NET.IF.IFTYPE.MATCHES}': 'ethernetCsmacd only.',
    '{$NET.IF.IFADMINSTATUS.MATCHES}': 'Admin-up only.',
    '{$NET.IF.DISCOVERY.MIN}': 'Average when SNMP is up 1h and enabled IF items stay below this.',
    '{$UNSUPPORTED.MAX}': 'Average when unsupported items stay above this for 30m.',
    '{$FM.DEVICE.CONTROL}': '1=ticket managed-device connect down. Mute with 0.',
    '{$FM.DEVICE.EXPECTED}': '0 disables census. Set to the known managed-device count.',
    '{$FM.DEVICE.NAME.MATCHES}': 'Device LLD include.',
    '{$FM.DEVICE.NAME.NOT_MATCHES}': 'Device LLD exclude.',
    '{$FM.DEVICE.MODE.MATCHES}': 'Drop unregistered(0). fmg(1) faz(2) fmg-faz(3).',
    '{$FM.CONFIG.CONTROL}': '0=cfgit owns config drift. Do not enable here.',
    '{$FM.HA.CONTROL}': '1=ticket HA peer down. Standalone default 0.',
    '{$FM.HA.EXPECTED}': '0 disables peer-count census. Pair = 1 peer.',
    '{$FM.ADOM.NAME.MATCHES}': 'ADOM LLD include.',
    '{$FM.ADOM.NAME.NOT_MATCHES}': 'ADOM LLD exclude.',
    '{$FM.ADOM.ARCHIVE.WARN}': 'ADOM archive used-% Warning (FAZ).',
    '{$FM.ADOM.ARCHIVE.CRIT}': 'ADOM archive used-% Average (FAZ).',
}


def build_parent() -> Doc:
    doc = Doc()
    header(doc)
    template_head(doc, uid(), T, PARENT_DESC)

    intern(
        doc,
        'ICMP ping',
        'icmpping',
        item_type='SIMPLE',
        description='Host accessibility by ICMP ping. Do not also link Network Generic or ICMP Ping.',
        valuemap='Service state',
        triggers=[
            dict(
                name=PARENT_ICMP_NAME,
                expression=PARENT_ICMP_EXPR,
                priority='HIGH',
                description='Last three ICMP attempts failed. Per chassis, not a cluster VIP.',
            )
        ],
    )
    intern(
        doc,
        'ICMP loss',
        'icmppingloss',
        item_type='SIMPLE',
        value_type='FLOAT',
        units='%',
        triggers=[
            dict(
                name=f'{T}: High ICMP ping loss',
                expression=f'min(/{T}/icmppingloss,5m)>{{$ICMP_LOSS_WARN}} and min(/{T}/icmppingloss,5m)<100',
                priority='WARNING',
                status='DISABLED',
                description='CH proxy loss is WAN. Collect; do not page.',
                dependencies=[ICMP_DEP],
            )
        ],
    )
    intern(
        doc,
        'ICMP response time',
        'icmppingsec',
        item_type='SIMPLE',
        value_type='FLOAT',
        units='s',
        triggers=[
            dict(
                name=f'{T}: High ICMP ping response time',
                expression=f'avg(/{T}/icmppingsec,5m)>{{$ICMP_RESPONSE_TIME_WARN}}',
                priority='WARNING',
                status='DISABLED',
                description='CH proxy RTT is WAN. Collect; do not page.',
                dependencies=[ICMP_DEP],
                scope='performance',
            )
        ],
    )
    intern(
        doc,
        'SNMP agent availability',
        'zabbix[host,snmp,available]',
        description='0 not available, 1 available, 2 unknown. Mgmt blind; the product may still run.',
        valuemap='zabbix.host.available',
        triggers=[
            dict(
                name=PARENT_SNMP_NAME,
                expression=PARENT_SNMP_EXPR,
                priority='WARNING',
                description='Mgmt blind; FMG/FAZ may still manage devices or ingest logs. Next day, same as EXOS/VOSS/IQ.',
                dependencies=[ICMP_DEP],
            )
        ],
    )
    intern(
        doc,
        'Unsupported item count',
        'zabbix[host,,items_unsupported]',
        delay='15m',
        description='Watch the watcher — a required FMG-FAZ MIB object must not quietly become green. Optional scalar items map not-supported to zero; optional tables use native empty LLD.',
        triggers=[
            dict(
                name=f'{T}: Too many unsupported items',
                expression=f'min(/{T}/zabbix[host,,items_unsupported],30m)>{{$UNSUPPORTED.MAX}}',
                priority='AVERAGE',
                description='SNMP=1 but items unsupported — firmware/OID mismatch, not a cable.',
                dependencies=[ICMP_DEP],
            )
        ],
    )
    calc(
        doc,
        'ICMP',
        'fm.observability.icmp',
        'last(//icmpping)',
        valuemap='Service state',
        description='Headline ICMP for the Overview gauge and nodata watcher.',
        triggers=[
            dict(
                name=f'{T}: no ICMP data for 10m',
                expression=f'nodata(/{T}/fm.observability.icmp,10m)=1',
                priority='AVERAGE',
                description='Watcher — proxy/host unknown, not ICMP down. Dead box is ICMP High.',
            )
        ],
    )
    calc(
        doc,
        'SNMP',
        'fm.observability.snmp',
        'last(//zabbix[host,snmp,available])',
        valuemap='zabbix.host.available',
        description='Headline SNMP for the Overview gauge.',
    )
    calc(
        doc,
        'Interface discovery seed (not a port)',
        'net.if.status[ifOperStatus.__seed]',
        '0',
        history='1d',
        trends='0',
        description='Always-present net.if.status key so count(exists_foreach) never becomes unsupported. Subtracted in net.if.discovery.count. Do not graph.',
    )
    calc(
        doc,
        'Discovered interface count',
        'net.if.discovery.count',
        'count(exists_foreach(//net.if.status[*]))-1',
        history='7d',
        description='Enabled IF-MIB oper-status items minus the seed. Zero with SNMP up is the IFNAME/IFTYPE LLD break.',
        triggers=[
            dict(
                name=f'{T}: No discovered interfaces after SNMP is up',
                expression=f'min(/{T}/zabbix[host,snmp,available],1h)=1 and last(/{T}/net.if.discovery.count)<{{$NET.IF.DISCOVERY.MIN}}',
                priority='AVERAGE',
                description='SNMP has been up for 1h and LLD produced no enabled net.if.status items. Count stays 0 (supported) while empty.',
                dependencies=[ICMP_DEP],
            )
        ],
    )
    calc(
        doc,
        'Managed device discovery seed (not a device)',
        'fm.device.connect[__seed]',
        '0',
        history='1d',
        trends='0',
        description='Always-present fm.device.connect key so count(exists_foreach) never becomes unsupported. Subtracted in fm.device.discovery.count.',
        component='health',
    )
    calc(
        doc,
        'Discovered managed-device count',
        'fm.device.discovery.count',
        'count(exists_foreach(//fm.device.connect[*]))-1',
        history='7d',
        description='Enabled managed-device connect items minus the seed. Census uses fm.device.number against {$FM.DEVICE.EXPECTED}.',
        triggers=[
            dict(
                name=f'{T}: Managed device count unexpected',
                expression=f'{{$FM.DEVICE.EXPECTED}}>0 and min(/{T}/zabbix[host,snmp,available],1h)=1 and last(/{T}/fm.device.number)<>{{$FM.DEVICE.EXPECTED}}',
                priority='AVERAGE',
                description='SNMP up 1h and fmDeviceNumber differs from {$FM.DEVICE.EXPECTED}. Default 0 disables this. Set the known count after a quiet census.',
                dependencies=HEALTH_DEPS,
            )
        ],
    )

    snmp(doc, 'System name', '1.3.6.1.2.1.1.5.0', 'system.name', delay='1h', value_type='CHAR', trends='0', history='7d', inventory='NAME', steps=[('DISCARD_UNCHANGED_HEARTBEAT', '6h')], triggers=[
        dict(name=f'{T}: System name has changed', expression=f'last(/{T}/system.name,#1)<>last(/{T}/system.name,#2) and length(last(/{T}/system.name))>0', priority='INFO', description='Possible replacement or rename. Acknowledge to close.', manual_close=True, scope='notice')
    ])
    snmp(doc, 'System description', '1.3.6.1.2.1.1.1.0', 'system.descr', delay='1h', value_type='CHAR', trends='0', history='7d', steps=[('DISCARD_UNCHANGED_HEARTBEAT', '6h')])
    snmp(doc, 'Firmware version', f'{FM_MIB}.2.1.7.0', 'fm.sys.version', delay='1h', value_type='CHAR', trends='0', history='7d', inventory='OS', steps=[('DISCARD_UNCHANGED_HEARTBEAT', '6h')], description='MIB: fmSysVersion.', triggers=[
        dict(name=f'{T}: Firmware version has changed', expression=f'last(/{T}/fm.sys.version,#1)<>last(/{T}/fm.sys.version,#2) and length(last(/{T}/fm.sys.version))>0', priority='INFO', description='Firmware updated or box replaced. Acknowledge to close.', manual_close=True, dependencies=[(f'{T}: System name has changed', f'last(/{T}/system.name,#1)<>last(/{T}/system.name,#2) and length(last(/{T}/system.name))>0')], scope='notice')
    ])
    snmp(doc, 'Serial number', FN_SYS_SERIAL, 'system.hw.serialnumber', delay='1h', value_type='CHAR', trends='0', history='7d', inventory='SERIALNO_A', steps=[('DISCARD_UNCHANGED_HEARTBEAT', '6h')], description='MIB: FORTINET-CORE-MIB fnSysSerial.', triggers=[
        dict(name=f'{T}: Device has been replaced', expression=f'last(/{T}/system.hw.serialnumber,#1)<>last(/{T}/system.hw.serialnumber,#2) and length(last(/{T}/system.hw.serialnumber))>0', priority='INFO', description='Serial changed. Acknowledge to close.', manual_close=True, scope='notice'),
        dict(name=f'{T}: Serial number is missing while SNMP is up', expression=f'nodata(/{T}/system.hw.serialnumber,2h)=1 and last(/{T}/zabbix[host,snmp,available])=1', priority='WARNING', description='SNMP answers but fnSysSerial is silent.', dependencies=HEALTH_DEPS, scope='notice'),
    ])
    snmp(doc, 'Uptime (network)', 'get[1.3.6.1.2.1.1.3.0]', 'system.net.uptime[sysUpTime.0]', units='uptime', trends='0', description='SNMPv2-MIB sysUpTime. Overview 4th tile (same as EXOS/VOSS/IQ).', steps=[('MULTIPLIER', '0.01')])
    snmp(doc, 'Uptime (FMG/FAZ 64-bit)', f'{FM_MIB}.2.1.8.0', 'fm.sys.uptime', units='uptime', trends='0', description='MIB: fmSysUpTime. Counter64 hundredths. Reboot uses this (no wrap like sysUpTime).', steps=[('MULTIPLIER', '0.01')], triggers=[
        dict(name=f'{T}: Host has been restarted', expression=f'last(/{T}/fm.sys.uptime)<10m', priority='WARNING', description='fmSysUpTime under 10 minutes. Next day, same as EXOS unplanned reboot. Do not page.', dependencies=HEALTH_DEPS, scope='notice')
    ])
    snmp(doc, 'CPU utilization', f'{FM_MIB}.2.1.1.0', 'fm.sys.cpu.util', units='%', value_type='FLOAT', description='MIB: fmSysCpuUsage (0..100).', component='cpu', triggers=[
        dict(name=f'{T}: High CPU utilization', expression=f'min(/{T}/fm.sys.cpu.util,5m)>{{$CPU.UTIL.WARN}}', priority='WARNING', description='Ops threshold {$CPU.UTIL.WARN}. Not a page.', dependencies=HEALTH_DEPS, scope='performance'),
        dict(name=f'{T}: Critical CPU utilization', expression=f'min(/{T}/fm.sys.cpu.util,5m)>{{$CPU.UTIL.CRIT}}', priority='AVERAGE', status='DISABLED', description='{$CPU.UTIL.CRIT}=101 silences this. Enable only after a quiet pilot.', dependencies=[(f'{T}: High CPU utilization', f'min(/{T}/fm.sys.cpu.util,5m)>{{$CPU.UTIL.WARN}}')], scope='performance'),
    ])
    snmp(doc, 'CPU utilization (exclude nice)', f'{FM_MIB}.2.1.6.0', 'fm.sys.cpu.util.excl.nice', units='%', value_type='FLOAT', description='MIB: fmSysCpuUsageExcludedNice. Optional; not-supported maps to 0.', component='cpu', ns='0')
    snmp(doc, 'Memory used', f'{FM_MIB}.2.1.2.0', 'fm.sys.mem.used', units='B', description='MIB: fmSysMemUsed (KB).', component='memory', steps=[('MULTIPLIER', '1024')])
    snmp(doc, 'Memory capacity', f'{FM_MIB}.2.1.3.0', 'fm.sys.mem.capacity', units='B', description='MIB: fmSysMemCapacity (KB), physical+swap.', component='memory', steps=[('MULTIPLIER', '1024')])
    calc(
        doc,
        'Memory utilization',
        'fm.sys.mem.util',
        '(last(//fm.sys.mem.capacity)>0)*((last(//fm.sys.mem.used)/last(//fm.sys.mem.capacity))*100)',
        units='%',
        component='memory',
        description='fmSysMemUsed / fmSysMemCapacity. Capacity 0 stays 0, not unsupported.',
        triggers=[
            dict(name=f'{T}: High memory utilization', expression=f'min(/{T}/fm.sys.mem.util,5m)>{{$MEMORY.UTIL.MAX}}', priority='AVERAGE', description='Memory above {$MEMORY.UTIL.MAX} for 5m.', dependencies=HEALTH_DEPS, scope='performance'),
        ],
    )
    snmp(doc, 'Disk used', f'{FM_MIB}.2.1.4.0', 'fm.sys.disk.used', units='B', description='MIB: fmSysDiskUsage (MB). FAZ log disk is the product.', component='storage', steps=[('MULTIPLIER', '1048576')])
    snmp(doc, 'Disk capacity', f'{FM_MIB}.2.1.5.0', 'fm.sys.disk.capacity', units='B', description='MIB: fmSysDiskCapacity (MB).', component='storage', steps=[('MULTIPLIER', '1048576')])
    calc(
        doc,
        'Disk utilization',
        'fm.sys.disk.util',
        '(last(//fm.sys.disk.capacity)>0)*((last(//fm.sys.disk.used)/last(//fm.sys.disk.capacity))*100)',
        units='%',
        component='storage',
        description='fmSysDiskUsage / fmSysDiskCapacity. FAZ High is on FortiAnalyzer Observability.',
        triggers=[
            dict(name=f'{T}: High disk utilization', expression=f'min(/{T}/fm.sys.disk.util,15m)>{{$DISK.UTIL.WARN}} and min(/{T}/fm.sys.disk.util,15m)<={{$DISK.UTIL.CRIT}}', priority='WARNING', description='Disk above {$DISK.UTIL.WARN}. Next day on FMG; FAZ still has Average/High above this.', dependencies=HEALTH_DEPS, scope='capacity'),
            dict(name=f'{T}: Critically high disk utilization', expression=f'min(/{T}/fm.sys.disk.util,10m)>{{$DISK.UTIL.CRIT}}', priority='AVERAGE', description='Disk above {$DISK.UTIL.CRIT}. Ticket. FAZ Observability adds High at {$DISK.UTIL.HIGH}.', dependencies=HEALTH_DEPS, scope='capacity'),
        ],
    )
    snmp(doc, 'Log receive rate', f'{FM_MIB}.2.1.10.0', 'fm.sys.log.rate.hr', units='logs/s', value_type='FLOAT', description='MIB: fmSysLogRateHr (FmHundredths). FAZ product signal; FMG often 0.', component='log', ns='0', steps=[('MULTIPLIER', '0.01')])
    snmp(doc, 'Log indexing rate', f'{FM_MIB}.2.1.11.0', 'fm.sys.log.index.rate', units='logs/s', value_type='FLOAT', description='MIB: fmSysLogIndexingRate (FmHundredths).', component='log', ns='0', steps=[('MULTIPLIER', '0.01')])
    snmp(doc, 'Log lag', f'{FM_MIB}.2.1.12.0', 'fm.sys.log.lag', units='s', description='MIB: fmSysLogLagTime. Receive-to-index delay. Triggers live on FortiAnalyzer Observability.', component='log', ns='0')
    snmp(doc, 'License GB/day today', f'{FM_MIB}.2.1.13.0', 'fm.sys.lic.gbday.today', units='GB', value_type='FLOAT', description='MIB: fmSysLicGbDayToday (FmHundredths GiB).', component='license', ns='0', steps=[('MULTIPLIER', '0.01')])
    snmp(doc, 'License GB/day yesterday', f'{FM_MIB}.2.1.14.0', 'fm.sys.lic.gbday.yesterday', units='GB', value_type='FLOAT', component='license', ns='0', steps=[('MULTIPLIER', '0.01')])
    snmp(doc, 'License GB/day week average', f'{FM_MIB}.2.1.15.0', 'fm.sys.lic.gbday.weekavg', units='GB', value_type='FLOAT', component='license', ns='0', steps=[('MULTIPLIER', '0.01')])
    snmp(doc, 'Managed device number', f'{FM_MIB}.6.1.1.0', 'fm.device.number', description='MIB: fmDeviceNumber. FMG = managed FortiGates; FAZ = log devices.', component='inventory')
    snmp(doc, 'VDOM number', f'{FM_MIB}.6.1.2.0', 'fm.vdom.number', description='MIB: fmVdomNumber.', component='inventory', ns='0')
    snmp(doc, 'ADOM enabled', f'{FM_MIB}.5.1.1.0', 'fm.adom.enabled', valuemap='Fortinet FnBoolState', description='MIB: fmAdomEnabled.', component='inventory')
    snmp(doc, 'ADOM number', f'{FM_MIB}.5.1.2.0', 'fm.adom.number', description='MIB: fmAdomNumber.', component='inventory')
    snmp(doc, 'ADOM maximum', f'{FM_MIB}.5.1.3.0', 'fm.adom.max', description='MIB: fmAdomMax (license/hardware cap).', component='inventory', ns='0')
    snmp(doc, 'HA mode', f'{FM_MIB}.9.1.1.0', 'fm.ha.mode', valuemap='Fortinet fmHaMode', description='MIB: fmHaMode. standalone(0) is the estate default.', component='ha', ns='0')
    snmp(doc, 'HA cluster id', f'{FM_MIB}.9.1.2.0', 'fm.ha.cluster.id', description='MIB: fmHaClusterId.', component='ha', ns='0')
    snmp(doc, 'HA peer number', f'{FM_MIB}.9.1.3.0', 'fm.ha.peer.number', description='MIB: fmHaPeerNumber. Standalone is 0.', component='ha', ns='0', triggers=[
        dict(name=f'{T}: HA peer count unexpected', expression=f'{{$FM.HA.EXPECTED}}>0 and last(/{T}/fm.ha.peer.number)<>{{$FM.HA.EXPECTED}}', priority='AVERAGE', description='Peer count differs from {$FM.HA.EXPECTED}. Default 0 disables this (standalone). Pair typically expects 1.', dependencies=HEALTH_DEPS),
    ])
    snmp(doc, 'RAID level', f'{FM_MIB}.7.1.1.0', 'fm.raid.level', valuemap='Fortinet fmRaidLevel', description='MIB: fmRaidLevel. unavailable(0) is normal on VMs.', component='storage', ns='0')
    snmp(doc, 'RAID state', f'{FM_MIB}.7.1.2.0', 'fm.raid.state', valuemap='Fortinet fmRaidState', description='MIB: fmRaidState. unavailable(0) is not an alert (no RAID).', component='storage', ns='0', triggers=[
        dict(name=f'{T}: RAID array is degraded', expression=f'min(/{T}/fm.raid.state,5m)=2', priority='AVERAGE', description='RAID degraded. Ticket; not a 03:00 page. unavailable(0) stays silent.', dependencies=HEALTH_DEPS, scope='capacity'),
        dict(name=f'{T}: RAID array has failed', expression=f'min(/{T}/fm.raid.state,3m)=3', priority='AVERAGE', description='RAID failed. Ticket. FAZ log-disk High is a separate companion trigger when used% is extreme.', dependencies=HEALTH_DEPS, scope='capacity'),
        dict(name=f'{T}: RAID array is initializing', expression=f'min(/{T}/fm.raid.state,5m)=4', priority='WARNING', description='Background initialize. Next day unless it stalls in degraded/failed.', dependencies=HEALTH_DEPS, scope='capacity'),
        dict(name=f'{T}: RAID array is verifying', expression=f'min(/{T}/fm.raid.state,5m)=5', priority='WARNING', description='Background verify. Next day unless it stalls in degraded/failed.', dependencies=HEALTH_DEPS, scope='capacity'),
        dict(name=f'{T}: RAID array is rebuilding', expression=f'min(/{T}/fm.raid.state,5m)=6', priority='WARNING', description='Background rebuild. Next day unless it stalls.', dependencies=HEALTH_DEPS, scope='capacity'),
    ])
    snmp(doc, 'RAID size', f'{FM_MIB}.7.1.3.0', 'fm.raid.size', units='GB', description='MIB: fmRaidSize.', component='storage', ns='0')
    snmp(doc, 'RAID disk number', f'{FM_MIB}.7.1.4.0', 'fm.raid.disk.number', description='MIB: fmRaidDiskNumber.', component='storage', ns='0')

    emit_discovery(doc)
    doc.add(3, 'tags:')
    doc.add(4, '- tag: class')
    doc.add(5, 'value: network')
    doc.add(4, '- tag: target')
    doc.add(5, 'value: fmg-faz')
    doc.add(4, '- tag: target')
    doc.add(5, 'value: fortinet')
    macros_block(doc, FMG_FAZ_PARENT_MACROS, MACRO_HELP)
    emit_parent_dashboards(doc)
    emit_parent_valuemaps(doc)
    return doc


def emit_discovery(doc: Doc) -> None:
    doc.add(3, 'discovery_rules:')
    emit_if_discovery(doc)
    emit_sensor_discovery(doc)
    emit_raid_disk_discovery(doc)
    emit_ha_peer_discovery(doc)
    emit_disk_discovery(doc)
    emit_adom_discovery(doc)
    emit_device_discovery(doc)
    emit_logfwd_discovery(doc)


def discovery_head(doc: Doc, name: str, oid: str, key: str, delay: str, description: str, js: str) -> None:
    doc.add(4, '- uuid: ' + uid())
    doc.add(5, f'name: {q(name)}')
    doc.add(5, 'type: SNMP_AGENT')
    doc.add(5, f'snmp_oid: {oid}')
    doc.add(5, f'key: {key}')
    doc.add(5, f'delay: {delay}')
    doc.add(5, 'lifetime: 7d')
    doc.add(5, 'lifetime_type: DELETE_AFTER')
    doc.add(5, "enabled_lifetime: '0'")
    doc.add(5, 'enabled_lifetime_type: DISABLE_IMMEDIATELY')
    doc.add(5, f'description: {q(description)}')
    doc.add(5, 'preprocessing:')
    doc.add(6, '- type: JAVASCRIPT')
    doc.add(7, 'parameters:')
    doc.add(8, '- |')
    for line in js.splitlines():
        doc.add(9, line)


def emit_if_discovery(doc: Doc) -> None:
    oid = (
        'discovery[{#IFNAME},1.3.6.1.2.1.31.1.1.1.1,{#IFTYPE},1.3.6.1.2.1.2.2.1.3,'
        '{#IFADMINSTATUS},1.3.6.1.2.1.2.2.1.7,{#IFOPERSTATUS},1.3.6.1.2.1.2.2.1.8,'
        '{#IFALIAS},1.3.6.1.2.1.31.1.1.1.18]'
    )
    discovery_head(
        doc,
        'Network interface discovery',
        oid,
        'net.if.discovery',
        '1h',
        'Admin-up ethernet only. Unused ports must be admin-down. Mute with {$IFCONTROL:"{#IFNAME}"}=0.',
        lld_fill_js(['{#IFNAME}', '{#IFTYPE}', '{#IFADMINSTATUS}', '{#IFOPERSTATUS}', '{#IFALIAS}']),
    )
    doc.add(5, 'filter:')
    doc.add(6, 'evaltype: AND')
    doc.add(6, 'conditions:')
    for macro, value, fid in (
        ('{#IFNAME}', '{$NET.IF.IFNAME.MATCHES}', 'A'),
        ('{#IFNAME}', '{$NET.IF.IFNAME.NOT_MATCHES}', 'B'),
        ('{#IFTYPE}', '{$NET.IF.IFTYPE.MATCHES}', 'C'),
        ('{#IFADMINSTATUS}', '{$NET.IF.IFADMINSTATUS.MATCHES}', 'D'),
    ):
        doc.add(7, f'- macro: {q(macro)}')
        doc.add(8, f'value: {q(value)}')
        if macro == '{#IFNAME}' and 'NOT_MATCHES' in value:
            doc.add(8, 'operator: NOT_MATCHES_REGEX')
        doc.add(8, f'formulaid: {fid}')
    doc.add(5, 'item_prototypes:')
    proto_item(
        doc,
        'Interface {#IFNAME}: Operational status',
        '1.3.6.1.2.1.2.2.1.8.{#SNMPINDEX}',
        'net.if.status[ifOperStatus.{#SNMPINDEX}]',
        valuemap='IF-MIB::ifStatus',
        history='7d',
        trends='0',
        component='network',
        extra_tags=[('interface', '{#IFNAME}')],
        triggers=[
            dict(
                name=f'{T}: Interface {{#IFNAME}}: Link down',
                expression=f'{{$IFCONTROL}}=1 and min(/{T}/net.if.status[ifOperStatus.{{#SNMPINDEX}}],#3)<>1',
                recovery=f'last(/{T}/net.if.status[ifOperStatus.{{#SNMPINDEX}}])=1 or {{$IFCONTROL}}=0',
                priority='AVERAGE',
                description='Admin-up ethernet not up for 3×1m, including never-up and lowerLayerDown. Unused ports must be admin-down. Mute with {$IFCONTROL:"{#IFNAME}"}=0.',
                dependencies=HEALTH_DEPS,
            )
        ],
    )
    proto_item(
        doc,
        'Interface {#IFNAME}: Bits received',
        '1.3.6.1.2.1.31.1.1.1.6.{#SNMPINDEX}',
        'net.if.in[ifHCInOctets.{#SNMPINDEX}]',
        units='bps',
        history='7d',
        trends='365d',
        component='network',
        extra_tags=[('interface', '{#IFNAME}')],
        steps=[('CHANGE_PER_SECOND',), ('MULTIPLIER', '8')],
    )
    proto_item(
        doc,
        'Interface {#IFNAME}: Bits sent',
        '1.3.6.1.2.1.31.1.1.1.10.{#SNMPINDEX}',
        'net.if.out[ifHCOutOctets.{#SNMPINDEX}]',
        units='bps',
        history='7d',
        trends='365d',
        component='network',
        extra_tags=[('interface', '{#IFNAME}')],
        steps=[('CHANGE_PER_SECOND',), ('MULTIPLIER', '8')],
    )
    proto_item(
        doc,
        'Interface {#IFNAME}: Inbound packets with errors',
        '1.3.6.1.2.1.2.2.1.14.{#SNMPINDEX}',
        'net.if.in.errors[ifInErrors.{#SNMPINDEX}]',
        history='7d',
        component='network',
        extra_tags=[('interface', '{#IFNAME}')],
        steps=[('CHANGE_PER_SECOND',)],
        triggers=[
            dict(
                name=f'{T}: Interface {{#IFNAME}}: High error rate',
                expression=(
                    f'{{$IFCONTROL}}=1 and '
                    f'(min(/{T}/net.if.in.errors[ifInErrors.{{#SNMPINDEX}}],5m)>{{$IF.ERRORS.WARN}} '
                    f'or min(/{T}/net.if.out.errors[ifOutErrors.{{#SNMPINDEX}}],5m)>{{$IF.ERRORS.WARN}})'
                ),
                priority='WARNING',
                description='In or out error rate above {$IF.ERRORS.WARN}. Next day.',
                dependencies=HEALTH_DEPS,
                scope='performance',
            )
        ],
    )
    proto_item(
        doc,
        'Interface {#IFNAME}: Outbound packets with errors',
        '1.3.6.1.2.1.2.2.1.20.{#SNMPINDEX}',
        'net.if.out.errors[ifOutErrors.{#SNMPINDEX}]',
        history='7d',
        component='network',
        extra_tags=[('interface', '{#IFNAME}')],
        steps=[('CHANGE_PER_SECOND',)],
    )
    proto_item(
        doc,
        'Interface {#IFNAME}: Speed',
        '1.3.6.1.2.1.31.1.1.1.15.{#SNMPINDEX}',
        'net.if.speed[ifHighSpeed.{#SNMPINDEX}]',
        units='bps',
        history='7d',
        trends='0',
        component='network',
        extra_tags=[('interface', '{#IFNAME}')],
        steps=[('MULTIPLIER', '1000000')],
    )
    doc.add(5, 'graph_prototypes:')
    doc.add(6, '- uuid: ' + uid())
    doc.add(7, "name: 'Interface {#IFNAME}: Network traffic'")
    doc.add(7, 'graph_items:')
    doc.add(8, '- drawtype: GRADIENT_LINE')
    doc.add(9, 'color: 199C0D')
    doc.add(9, 'item:')
    doc.add(10, f'host: {T}')
    doc.add(10, "key: 'net.if.in[ifHCInOctets.{#SNMPINDEX}]'")
    doc.add(8, "- sortorder: '1'")
    doc.add(9, 'drawtype: BOLD_LINE')
    doc.add(9, 'color: F63100')
    doc.add(9, 'item:')
    doc.add(10, f'host: {T}')
    doc.add(10, "key: 'net.if.out[ifHCOutOctets.{#SNMPINDEX}]'")


def emit_sensor_discovery(doc: Doc) -> None:
    oid = (
        f'discovery[{{#SENSOR_NAME}},{FM_MIB}.8.2.1.2,{{#SENSOR_TYPE}},{FM_MIB}.8.2.1.4,'
        f'{{#SENSOR_STATE}},{FM_MIB}.8.2.1.5]'
    )
    extra = (
        "\tvar kinds = {'0':'Power','1':'Fan','2':'Temp','3':'Voltage'};\n"
        "\telement['{#SENSOR_KIND}'] = kinds[String(element['{#SENSOR_TYPE}'])] || 'Sensor';\n"
    )
    discovery_head(
        doc,
        'Hardware sensor discovery',
        oid,
        'fm.sensor.discovery',
        '15m',
        'MIB: fmSensorTable. Empty on VMs (maps to []). State is the alert; value is DisplayString inventory.',
        lld_fill_js(['{#SENSOR_NAME}', '{#SENSOR_TYPE}', '{#SENSOR_STATE}'], extra),
    )
    doc.add(5, 'item_prototypes:')
    proto_item(
        doc,
        '{#SENSOR_KIND} {#SENSOR_NAME}: Sensor status',
        f'{FM_MIB}.8.2.1.5.{{#SNMPINDEX}}',
        'fm.sensor.state[{#SNMPINDEX}]',
        valuemap='Fortinet fmSensorEntState',
        history='7d',
        trends='0',
        extra_tags=[('sensor', '{#SENSOR_NAME}'), ('sensor_kind', '{#SENSOR_KIND}')],
        triggers=[
            dict(
                name=f'{T}: {{#SENSOR_KIND}} {{#SENSOR_NAME}} is failed',
                expression=f'min(/{T}/fm.sensor.state[{{#SNMPINDEX}}],#3)=1 or min(/{T}/fm.sensor.state[{{#SNMPINDEX}}],#3)=5',
                recovery=f'last(/{T}/fm.sensor.state[{{#SNMPINDEX}}])=0',
                priority='AVERAGE',
                description='Sensor failed(1) or input-lost(5). not-present(6) is not this ticket. PSU/fan Average, same as EXOS.',
                dependencies=HEALTH_DEPS,
            ),
            dict(
                name=f'{T}: {{#SENSOR_KIND}} {{#SENSOR_NAME}} is critical',
                expression=f'(min(/{T}/fm.sensor.state[{{#SNMPINDEX}}],#3)=3 or min(/{T}/fm.sensor.state[{{#SNMPINDEX}}],#3)=4) and {{#SENSOR_TYPE}}=2',
                recovery=f'last(/{T}/fm.sensor.state[{{#SNMPINDEX}}])=0',
                priority='HIGH',
                description='Temperature out-of-range-critical or not-recoverable. 03:00 page, same as switch chassis overtemp. Vendor state, not a guessed °C.',
                dependencies=HEALTH_DEPS,
                scope='capacity',
            ),
            dict(
                name=f'{T}: {{#SENSOR_KIND}} {{#SENSOR_NAME}} is out of range',
                expression=f'min(/{T}/fm.sensor.state[{{#SNMPINDEX}}],5m)=2',
                recovery=f'last(/{T}/fm.sensor.state[{{#SNMPINDEX}}])=0',
                priority='WARNING',
                description='Out of range, not critical. Next day.',
                dependencies=HEALTH_DEPS,
                scope='capacity',
            ),
        ],
    )
    proto_item(
        doc,
        '{#SENSOR_KIND} {#SENSOR_NAME}: Sensor value',
        f'{FM_MIB}.8.2.1.3.{{#SNMPINDEX}}',
        'fm.sensor.value[{#SNMPINDEX}]',
        delay='5m',
        value_type='CHAR',
        trends='0',
        history='7d',
        extra_tags=[('sensor', '{#SENSOR_NAME}'), ('sensor_kind', '{#SENSOR_KIND}')],
    )


def emit_raid_disk_discovery(doc: Doc) -> None:
    oid = f'discovery[{{#RAID.DISK.STATE}},{FM_MIB}.7.2.1.2,{{#RAID.DISK.SIZE}},{FM_MIB}.7.2.1.3]'
    discovery_head(
        doc,
        'RAID disk discovery',
        oid,
        'fm.raid.disk.discovery',
        '15m',
        'MIB: fmRaidDiskTable. Empty/unavailable on VMs. unused/spare/unavailable are not alerts.',
        lld_fill_js(['{#RAID.DISK.STATE}', '{#RAID.DISK.SIZE}']),
    )
    doc.add(5, 'item_prototypes:')
    proto_item(
        doc,
        'RAID disk {#SNMPINDEX}: State',
        f'{FM_MIB}.7.2.1.2.{{#SNMPINDEX}}',
        'fm.raid.disk.state[{#SNMPINDEX}]',
        valuemap='Fortinet fmRaidDiskEntState',
        history='7d',
        trends='0',
        extra_tags=[('disk', '{#SNMPINDEX}')],
        triggers=[
            dict(
                name=f'{T}: RAID disk {{#SNMPINDEX}} has failed',
                expression=f'min(/{T}/fm.raid.disk.state[{{#SNMPINDEX}}],#3)=1',
                recovery=f'last(/{T}/fm.raid.disk.state[{{#SNMPINDEX}}])=3 or last(/{T}/fm.raid.disk.state[{{#SNMPINDEX}}])=5',
                priority='AVERAGE',
                description='Disk failed(1). unused/spare/unavailable stay silent.',
                dependencies=HEALTH_DEPS,
                scope='capacity',
            )
        ],
    )
    proto_item(
        doc,
        'RAID disk {#SNMPINDEX}: Size',
        f'{FM_MIB}.7.2.1.3.{{#SNMPINDEX}}',
        'fm.raid.disk.size[{#SNMPINDEX}]',
        units='GB',
        delay='1h',
        extra_tags=[('disk', '{#SNMPINDEX}')],
    )


def emit_ha_peer_discovery(doc: Doc) -> None:
    oid = (
        f'discovery[{{#HA.PEER.HOST}},{FM_MIB}.9.2.1.5,{{#HA.PEER.IP}},{FM_MIB}.9.2.1.2,'
        f'{{#HA.PEER.SN}},{FM_MIB}.9.2.1.3,{{#HA.PEER.STATE}},{FM_MIB}.9.2.1.6]'
    )
    discovery_head(
        doc,
        'HA peer discovery',
        oid,
        'fm.ha.peer.discovery',
        '5m',
        'MIB: fmHaPeerTable. Standalone is empty. {$FM.HA.CONTROL}=0 keeps peer-down silent.',
        lld_fill_js(['{#HA.PEER.HOST}', '{#HA.PEER.IP}', '{#HA.PEER.SN}', '{#HA.PEER.STATE}']),
    )
    doc.add(5, 'item_prototypes:')
    proto_item(
        doc,
        'HA peer {#HA.PEER.HOST}: State',
        f'{FM_MIB}.9.2.1.6.{{#SNMPINDEX}}',
        'fm.ha.peer.state[{#SNMPINDEX}]',
        valuemap='Fortinet fmHaPeerEntState',
        history='7d',
        trends='0',
        component='ha',
        extra_tags=[('peer', '{#HA.PEER.HOST}')],
        triggers=[
            dict(
                name=f'{T}: HA peer {{#HA.PEER.HOST}} is down',
                expression=f'{{$FM.HA.CONTROL}}=1 and min(/{T}/fm.ha.peer.state[{{#SNMPINDEX}}],#3)=0',
                recovery=f'last(/{T}/fm.ha.peer.state[{{#SNMPINDEX}}])=3 or {{$FM.HA.CONTROL}}=0',
                priority='AVERAGE',
                description='Peer down(0) while {$FM.HA.CONTROL}=1. Standalone default is 0 (silent). negotiating/synchronizing are not this ticket.',
                dependencies=HEALTH_DEPS,
            )
        ],
    )
    proto_item(
        doc,
        'HA peer {#HA.PEER.HOST}: Enabled',
        f'{FM_MIB}.9.2.1.4.{{#SNMPINDEX}}',
        'fm.ha.peer.enabled[{#SNMPINDEX}]',
        delay='5m',
        valuemap='Fortinet FnBoolState',
        component='ha',
        extra_tags=[('peer', '{#HA.PEER.HOST}')],
        trends='0',
    )


def emit_disk_discovery(doc: Doc) -> None:
    oid = (
        f'discovery[{{#DISK.NAME}},{FM_MIB}.2.1.17.1.2,{{#DISK.USAGE}},{FM_MIB}.2.1.17.1.3,'
        f'{{#DISK.CAPACITY}},{FM_MIB}.2.1.17.1.4]'
    )
    discovery_head(
        doc,
        'Logical disk discovery',
        oid,
        'fm.disk.discovery',
        '15m',
        'MIB: fmSysDiskTable (per-volume usage/capacity/IO). Headline disk % remains the scalar.',
        lld_fill_js(['{#DISK.NAME}', '{#DISK.USAGE}', '{#DISK.CAPACITY}']),
    )
    doc.add(5, 'item_prototypes:')
    proto_item(
        doc,
        'Disk {#DISK.NAME}: Used',
        f'{FM_MIB}.2.1.17.1.3.{{#SNMPINDEX}}',
        'fm.disk.used[{#SNMPINDEX}]',
        units='B',
        component='storage',
        extra_tags=[('disk', '{#DISK.NAME}')],
        steps=[('MULTIPLIER', '1048576')],
    )
    proto_item(
        doc,
        'Disk {#DISK.NAME}: Capacity',
        f'{FM_MIB}.2.1.17.1.4.{{#SNMPINDEX}}',
        'fm.disk.capacity[{#SNMPINDEX}]',
        units='B',
        delay='1h',
        component='storage',
        extra_tags=[('disk', '{#DISK.NAME}')],
        steps=[('MULTIPLIER', '1048576')],
    )
    proto_item(
        doc,
        'Disk {#DISK.NAME}: IO utilization',
        f'{FM_MIB}.2.1.17.1.5.{{#SNMPINDEX}}',
        'fm.disk.io.util[{#SNMPINDEX}]',
        units='%',
        value_type='FLOAT',
        component='storage',
        extra_tags=[('disk', '{#DISK.NAME}')],
        steps=[('MULTIPLIER', '0.1')],
    )


def emit_adom_discovery(doc: Doc) -> None:
    oid = (
        f'discovery[{{#FM.ADOM.NAME}},{FM_MIB}.5.2.1.2,{{#FM.ADOM.STATE}},{FM_MIB}.5.2.1.3,'
        f'{{#FM.ADOM.FGT}},{FM_MIB}.5.2.1.5]'
    )
    discovery_head(
        doc,
        'ADOM discovery',
        oid,
        'fm.adom.discovery',
        '1h',
        'MIB: fmAdomTable. Inventory + FAZ archive/analytics used %. Config drift is cfgit, not these items.',
        lld_fill_js(['{#FM.ADOM.NAME}', '{#FM.ADOM.STATE}', '{#FM.ADOM.FGT}']),
    )
    doc.add(5, 'filter:')
    doc.add(6, 'evaltype: AND')
    doc.add(6, 'conditions:')
    doc.add(7, "- macro: '{#FM.ADOM.NAME}'")
    doc.add(8, 'value: "{$FM.ADOM.NAME.MATCHES}"')
    doc.add(8, 'formulaid: A')
    doc.add(7, "- macro: '{#FM.ADOM.NAME}'")
    doc.add(8, 'value: "{$FM.ADOM.NAME.NOT_MATCHES}"')
    doc.add(8, 'operator: NOT_MATCHES_REGEX')
    doc.add(8, 'formulaid: B')
    doc.add(5, 'item_prototypes:')
    proto_item(
        doc,
        'ADOM {#FM.ADOM.NAME}: FortiGate count',
        f'{FM_MIB}.5.2.1.5.{{#SNMPINDEX}}',
        'fm.adom.fgt.count[{#SNMPINDEX}]',
        delay='15m',
        component='inventory',
        extra_tags=[('adom', '{#FM.ADOM.NAME}')],
    )
    proto_item(
        doc,
        'ADOM {#FM.ADOM.NAME}: Archive used %',
        f'{FM_MIB}.5.2.1.14.{{#SNMPINDEX}}',
        'fm.adom.archive.used.pct[{#SNMPINDEX}]',
        units='%',
        value_type='FLOAT',
        delay='15m',
        component='log',
        extra_tags=[('adom', '{#FM.ADOM.NAME}')],
        steps=[('MULTIPLIER', '0.1')],
        ns='0',
        triggers=[
            dict(
                name=f'{T}: ADOM {{#FM.ADOM.NAME}} archive quota high',
                expression=f'min(/{T}/fm.adom.archive.used.pct[{{#SNMPINDEX}}],15m)>{{$FM.ADOM.ARCHIVE.WARN}} and min(/{T}/fm.adom.archive.used.pct[{{#SNMPINDEX}}],15m)<={{$FM.ADOM.ARCHIVE.CRIT}}',
                priority='WARNING',
                description='Archive used % of quota. Meaningful on FAZ; FMG often 0.',
                dependencies=HEALTH_DEPS,
                scope='capacity',
            ),
            dict(
                name=f'{T}: ADOM {{#FM.ADOM.NAME}} archive quota critical',
                expression=f'min(/{T}/fm.adom.archive.used.pct[{{#SNMPINDEX}}],10m)>{{$FM.ADOM.ARCHIVE.CRIT}}',
                priority='AVERAGE',
                description='Archive quota exhausted — FAZ will drop or overwrite archive logs.',
                dependencies=HEALTH_DEPS,
                scope='capacity',
            ),
        ],
    )
    proto_item(
        doc,
        'ADOM {#FM.ADOM.NAME}: Analytics used %',
        f'{FM_MIB}.5.2.1.18.{{#SNMPINDEX}}',
        'fm.adom.analytics.used.pct[{#SNMPINDEX}]',
        units='%',
        value_type='FLOAT',
        delay='15m',
        component='log',
        extra_tags=[('adom', '{#FM.ADOM.NAME}')],
        steps=[('MULTIPLIER', '0.1')],
        ns='0',
        triggers=[
            dict(
                name=f'{T}: ADOM {{#FM.ADOM.NAME}} analytics quota high',
                expression=f'min(/{T}/fm.adom.analytics.used.pct[{{#SNMPINDEX}}],15m)>{{$FM.ADOM.ARCHIVE.WARN}}',
                priority='WARNING',
                description='Analytics used % of quota. Reports/search suffer before archive does.',
                dependencies=HEALTH_DEPS,
                scope='capacity',
            )
        ],
    )
    proto_item(
        doc,
        'ADOM {#FM.ADOM.NAME}: Log rate',
        f'{FM_MIB}.5.2.1.10.{{#SNMPINDEX}}',
        'fm.adom.log.rate[{#SNMPINDEX}]',
        units='logs/s',
        value_type='FLOAT',
        delay='5m',
        component='log',
        extra_tags=[('adom', '{#FM.ADOM.NAME}')],
        steps=[('MULTIPLIER', '0.01')],
        ns='0',
    )


def emit_device_discovery(doc: Doc) -> None:
    oid = (
        f'discovery[{{#FM.DEVICE.NAME}},{FM_MIB}.6.2.1.2,{{#FM.DEVICE.SN}},{FM_MIB}.6.2.1.3,'
        f'{{#FM.DEVICE.MODE}},{FM_MIB}.6.2.1.4,{{#FM.DEVICE.ADOM}},{FM_MIB}.6.2.1.5,'
        f'{{#FM.DEVICE.CONNECT}},{FM_MIB}.6.2.1.12,{{#FM.DEVICE.CONFIG}},{FM_MIB}.6.2.1.14]'
    )
    discovery_head(
        doc,
        'Managed device discovery',
        oid,
        'fm.device.discovery',
        '5m',
        'MIB: fmDeviceTable. FMG = FGFM management; FAZ = log device. Config out-of-sync is collected; cfgit owns that ticket ({$FM.CONFIG.CONTROL}=0).',
        lld_fill_js(
            [
                '{#FM.DEVICE.NAME}',
                '{#FM.DEVICE.SN}',
                '{#FM.DEVICE.MODE}',
                '{#FM.DEVICE.ADOM}',
                '{#FM.DEVICE.CONNECT}',
                '{#FM.DEVICE.CONFIG}',
            ]
        ),
    )
    doc.add(5, 'filter:')
    doc.add(6, 'evaltype: AND')
    doc.add(6, 'conditions:')
    doc.add(7, "- macro: '{#FM.DEVICE.NAME}'")
    doc.add(8, 'value: "{$FM.DEVICE.NAME.MATCHES}"')
    doc.add(8, 'formulaid: A')
    doc.add(7, "- macro: '{#FM.DEVICE.NAME}'")
    doc.add(8, 'value: "{$FM.DEVICE.NAME.NOT_MATCHES}"')
    doc.add(8, 'operator: NOT_MATCHES_REGEX')
    doc.add(8, 'formulaid: B')
    doc.add(7, "- macro: '{#FM.DEVICE.MODE}'")
    doc.add(8, 'value: "{$FM.DEVICE.MODE.MATCHES}"')
    doc.add(8, 'formulaid: C')
    doc.add(5, 'item_prototypes:')
    proto_item(
        doc,
        'Device {#FM.DEVICE.NAME}: Connect state',
        f'{FM_MIB}.6.2.1.12.{{#SNMPINDEX}}',
        'fm.device.connect[{#SNMPINDEX}]',
        valuemap='Fortinet fmDeviceEntConnectState',
        history='7d',
        trends='0',
        component='inventory',
        extra_tags=[('device', '{#FM.DEVICE.NAME}'), ('adom', '{#FM.DEVICE.ADOM}')],
        triggers=[
            dict(
                name=f'{T}: Managed device {{#FM.DEVICE.NAME}} is offline',
                expression=f'{{$FM.DEVICE.CONTROL}}=1 and min(/{T}/fm.device.connect[{{#SNMPINDEX}}],#3)=2',
                recovery=f'last(/{T}/fm.device.connect[{{#SNMPINDEX}}])=1 or {{$FM.DEVICE.CONTROL}}=0',
                priority='AVERAGE',
                description='Connect down(2) for 3×1m. FMG = FGFM tunnel; FAZ = log device stopped sending. Zabbix owns this ticket — mute FAZ-native device-down duplicates. unknown(0) is not this trigger.',
                dependencies=HEALTH_DEPS,
            )
        ],
    )
    proto_item(
        doc,
        'Device {#FM.DEVICE.NAME}: Config state',
        f'{FM_MIB}.6.2.1.14.{{#SNMPINDEX}}',
        'fm.device.config[{#SNMPINDEX}]',
        delay='15m',
        valuemap='Fortinet fmDeviceEntConfigState',
        history='7d',
        trends='0',
        component='inventory',
        extra_tags=[('device', '{#FM.DEVICE.NAME}'), ('adom', '{#FM.DEVICE.ADOM}')],
        triggers=[
            dict(
                name=f'{T}: Managed device {{#FM.DEVICE.NAME}} config is out of sync',
                expression=f'{{$FM.CONFIG.CONTROL}}=1 and min(/{T}/fm.device.config[{{#SNMPINDEX}}],15m)=2',
                recovery=f'last(/{T}/fm.device.config[{{#SNMPINDEX}}])=1 or {{$FM.CONFIG.CONTROL}}=0',
                priority='AVERAGE',
                status='DISABLED',
                description='cfgit owns config drift. Default {$FM.CONFIG.CONTROL}=0. Do not enable both.',
                dependencies=HEALTH_DEPS,
            )
        ],
    )
    proto_item(
        doc,
        'Device {#FM.DEVICE.NAME}: Log rate (hour)',
        f'{FM_MIB}.6.2.1.25.{{#SNMPINDEX}}',
        'fm.device.log.rate.hour[{#SNMPINDEX}]',
        units='logs/s',
        value_type='FLOAT',
        delay='15m',
        component='log',
        extra_tags=[('device', '{#FM.DEVICE.NAME}'), ('adom', '{#FM.DEVICE.ADOM}')],
        steps=[('MULTIPLIER', '0.01')],
        ns='0',
    )


def emit_logfwd_discovery(doc: Doc) -> None:
    oid = f'discovery[{{#FM.LOGFWD.NAME}},{FM_MIB}.2.1.19.1.2,{{#FM.LOGFWD.RATE}},{FM_MIB}.2.1.19.1.3]'
    discovery_head(
        doc,
        'Log-forward target discovery',
        oid,
        'fm.logfwd.discovery',
        '15m',
        'MIB: fmSysLogForwardTable. Empty when no log-forward is configured.',
        lld_fill_js(['{#FM.LOGFWD.NAME}', '{#FM.LOGFWD.RATE}']),
    )
    doc.add(5, 'item_prototypes:')
    proto_item(
        doc,
        'Log forward {#FM.LOGFWD.NAME}: Rate',
        f'{FM_MIB}.2.1.19.1.3.{{#SNMPINDEX}}',
        'fm.logfwd.rate[{#SNMPINDEX}]',
        units='logs/s',
        value_type='FLOAT',
        component='log',
        extra_tags=[('target', '{#FM.LOGFWD.NAME}')],
        steps=[('MULTIPLIER', '0.01')],
        ns='0',
    )


def emit_parent_dashboards(doc: Doc) -> None:
    up_down = [('FF465C', '0'), ('0EC9AC', '1')]
    cpu_thr = [('0EC9AC', '0'), ('FFD54F', '80'), ('FF465C', '90')]
    disk_thr = [('0EC9AC', '0'), ('FFD54F', '80'), ('FF465C', '90')]
    doc.add(3, 'dashboards:')
    doc.add(4, '- uuid: ' + uid())
    doc.add(5, 'name: Health')
    doc.add(5, 'pages:')
    doc.add(6, '- name: Overview')
    doc.add(7, 'widgets:')
    widget_xy(doc, 8, 'gauge', 'ICMP', width='18', height='4')
    gauge_fields(doc, 9, T, 'fm.observability.icmp', max_v='1', min_v='0', thresholds=up_down)
    widget_xy(doc, 8, 'gauge', 'SNMP', x='18', width='18', height='4')
    gauge_fields(doc, 9, T, 'fm.observability.snmp', max_v='1', min_v='0', thresholds=up_down)
    widget_xy(doc, 8, 'gauge', 'CPU', x='36', width='18', height='4')
    gauge_fields(doc, 9, T, 'fm.sys.cpu.util', units='%', thresholds=cpu_thr)
    widget_xy(doc, 8, 'item', 'Uptime', x='54', width='18', height='4')
    doc.add(9, 'fields:')
    field(doc, 10, 'ITEM', 'itemid.0', None, item_host=T, item_key='system.net.uptime[sysUpTime.0]')
    field(doc, 10, 'INTEGER', 'show.0', '2')
    field(doc, 10, 'INTEGER', 'value_bold', '1')
    field(doc, 10, 'INTEGER', 'value_size', '28')
    widget_xy(doc, 8, 'problems', 'Problems', y='4', width='72', height='3')
    doc.add(9, 'fields:')
    field(doc, 10, 'STRING', 'reference', 'FPROB')
    field(doc, 10, 'INTEGER', 'show', '3')
    field(doc, 10, 'INTEGER', 'show_opdata', '2')
    widget_xy(doc, 8, 'svggraph', 'CPU / memory', y='7', width='36', height='6')
    doc.add(9, 'fields:')
    field(doc, 10, 'STRING', 'ds.0.color.0', '199C0D')
    field(doc, 10, 'STRING', 'ds.0.color.1', '2774A4')
    field(doc, 10, 'INTEGER', 'ds.0.dataset_type', '0')
    field(doc, 10, 'ITEM', 'ds.0.itemids.0', None, item_host=T, item_key='fm.sys.cpu.util')
    field(doc, 10, 'ITEM', 'ds.0.itemids.1', None, item_host=T, item_key='fm.sys.mem.util')
    field(doc, 10, 'STRING', 'lefty_max', '100')
    field(doc, 10, 'STRING', 'lefty_min', '0')
    field(doc, 10, 'STRING', 'reference', 'FCPUH')
    field(doc, 10, 'INTEGER', 'show_problems', '1')
    field(doc, 10, 'INTEGER', 'legend', '1')
    svg_time_period(doc, 10)
    widget_xy(doc, 8, 'svggraph', 'Uptime', x='36', y='7', width='36', height='6')
    doc.add(9, 'fields:')
    field(doc, 10, 'STRING', 'ds.0.color.0', '2774A4')
    field(doc, 10, 'INTEGER', 'ds.0.dataset_type', '0')
    field(doc, 10, 'ITEM', 'ds.0.itemids.0', None, item_host=T, item_key='system.net.uptime[sysUpTime.0]')
    field(doc, 10, 'STRING', 'reference', 'FUPTH')
    field(doc, 10, 'INTEGER', 'show_problems', '1')
    field(doc, 10, 'INTEGER', 'legend', '0')
    svg_time_period(doc, 10)

    doc.add(6, '- name: Hardware')
    doc.add(7, 'widgets:')
    # Fans / PSU / Temp honeycombs + memory/disk gauges
    emit_honeycomb(
        doc,
        'Fans',
        'Fan *: Sensor status',
        '{{ITEM.NAME}.regsub("^Fan (.*): Sensor status$","\\1")}',
        'FFANS',
        [('878787', '0'), ('FF465C', '1'), ('FFD54F', '2'), ('FF465C', '3')],
        width='36',
        height='3',
    )
    emit_honeycomb(
        doc,
        'PSU',
        'Power *: Sensor status',
        '{{ITEM.NAME}.regsub("^Power (.*): Sensor status$","\\1")}',
        'FPSUS',
        [('878787', '0'), ('FF465C', '1'), ('FFD54F', '2'), ('FF465C', '3'), ('FF465C', '4'), ('FF465C', '5')],
        x='36',
        width='36',
        height='3',
    )
    widget_xy(doc, 8, 'gauge', 'Memory', y='3', width='18', height='4')
    gauge_fields(doc, 9, T, 'fm.sys.mem.util', units='%', thresholds=cpu_thr)
    widget_xy(doc, 8, 'gauge', 'Disk', x='18', y='3', width='18', height='4')
    gauge_fields(doc, 9, T, 'fm.sys.disk.util', units='%', thresholds=disk_thr)
    emit_honeycomb(
        doc,
        'Temp',
        'Temp *: Sensor status',
        '{{ITEM.NAME}.regsub("^Temp (.*): Sensor status$","\\1")}',
        'FTEMP',
        [('0EC9AC', '0'), ('FF465C', '1'), ('FFD54F', '2'), ('FF465C', '3')],
        x='36',
        y='3',
        width='36',
        height='4',
    )
    widget_xy(doc, 8, 'svggraph', 'Disk', y='7', width='72', height='5')
    doc.add(9, 'fields:')
    field(doc, 10, 'STRING', 'ds.0.color.0', '2774A4')
    field(doc, 10, 'INTEGER', 'ds.0.dataset_type', '0')
    field(doc, 10, 'ITEM', 'ds.0.itemids.0', None, item_host=T, item_key='fm.sys.disk.util')
    field(doc, 10, 'STRING', 'lefty_max', '100')
    field(doc, 10, 'STRING', 'lefty_min', '0')
    field(doc, 10, 'STRING', 'reference', 'FDSKH')
    field(doc, 10, 'INTEGER', 'show_problems', '1')
    field(doc, 10, 'INTEGER', 'legend', '0')
    svg_time_period(doc, 10)

    doc.add(6, '- name: Cluster')
    doc.add(7, 'widgets:')
    widget_xy(doc, 8, 'item', 'HA mode', width='18', height='4')
    doc.add(9, 'fields:')
    field(doc, 10, 'ITEM', 'itemid.0', None, item_host=T, item_key='fm.ha.mode')
    field(doc, 10, 'INTEGER', 'show.0', '2')
    field(doc, 10, 'INTEGER', 'value_bold', '1')
    field(doc, 10, 'INTEGER', 'value_size', '24')
    widget_xy(doc, 8, 'item', 'HA peers', x='18', width='18', height='4')
    doc.add(9, 'fields:')
    field(doc, 10, 'ITEM', 'itemid.0', None, item_host=T, item_key='fm.ha.peer.number')
    field(doc, 10, 'INTEGER', 'show.0', '2')
    field(doc, 10, 'INTEGER', 'value_bold', '1')
    field(doc, 10, 'INTEGER', 'value_size', '28')
    widget_xy(doc, 8, 'item', 'RAID', x='36', width='18', height='4')
    doc.add(9, 'fields:')
    field(doc, 10, 'ITEM', 'itemid.0', None, item_host=T, item_key='fm.raid.state')
    field(doc, 10, 'INTEGER', 'show.0', '2')
    field(doc, 10, 'INTEGER', 'value_bold', '1')
    field(doc, 10, 'INTEGER', 'value_size', '24')
    widget_xy(doc, 8, 'item', 'Devices', x='54', width='18', height='4')
    doc.add(9, 'fields:')
    field(doc, 10, 'ITEM', 'itemid.0', None, item_host=T, item_key='fm.device.number')
    field(doc, 10, 'INTEGER', 'show.0', '2')
    field(doc, 10, 'INTEGER', 'value_bold', '1')
    field(doc, 10, 'INTEGER', 'value_size', '28')
    emit_honeycomb(
        doc,
        'HA peers',
        'HA peer *: State',
        '{{ITEM.NAME}.regsub("^HA peer (.*): State$","\\1")}',
        'FHAPE',
        [('FF465C', '0'), ('FFD54F', '1'), ('FFD54F', '2'), ('0EC9AC', '3')],
        y='4',
        width='36',
        height='4',
    )
    emit_honeycomb(
        doc,
        'RAID disks',
        'RAID disk *: State',
        '{{ITEM.NAME}.regsub("^RAID disk (.*): State$","\\1")}',
        'FRDSK',
        [('878787', '0'), ('FF465C', '1'), ('878787', '2'), ('0EC9AC', '3'), ('FFD54F', '4'), ('2774A4', '5')],
        x='36',
        y='4',
        width='36',
        height='4',
    )

    doc.add(4, '- uuid: ' + uid())
    doc.add(5, 'name: Network interfaces')
    doc.add(5, 'pages:')
    doc.add(6, '- name: Overview')
    doc.add(7, 'widgets:')
    emit_honeycomb(
        doc,
        'Interfaces',
        'Interface *: Operational status',
        '{{ITEM.NAME}.regsub("^Interface (.*): Operational status$","\\1")}',
        'FIMAP',
        [('878787', '0'), ('0EC9AC', '1'), ('FF465C', '2')],
        width='24',
        height='4',
    )
    widget_xy(doc, 8, 'graphprototype', 'Traffic', y='4', width='72', height='14')
    doc.add(9, 'fields:')
    field(doc, 10, 'INTEGER', 'columns', '3')
    field(doc, 10, 'GRAPH_PROTOTYPE', 'graphid.0', None, graph_host=T, graph_name='Interface {#IFNAME}: Network traffic')
    field(doc, 10, 'STRING', 'reference', 'FTGRD')
    field(doc, 10, 'INTEGER', 'rows', '2')
    doc.add(6, '- name: Port')
    doc.add(7, 'widgets:')
    widget_xy(doc, 8, 'itemnavigator', 'Counters', width='28', height='11')
    doc.add(9, 'fields:')
    field(doc, 10, 'INTEGER', 'group_by.0.attribute', '3')
    field(doc, 10, 'STRING', 'group_by.0.tag_name', 'interface')
    field(doc, 10, 'STRING', 'items.0', 'Interface *: Operational status')
    field(doc, 10, 'STRING', 'items.1', 'Interface *: Speed')
    field(doc, 10, 'STRING', 'items.2', 'Interface *: Inbound packets with errors')
    field(doc, 10, 'STRING', 'items.3', 'Interface *: Outbound packets with errors')
    field(doc, 10, 'STRING', 'items.4', 'Interface *: Bits received')
    field(doc, 10, 'STRING', 'items.5', 'Interface *: Bits sent')
    field(doc, 10, 'STRING', 'reference', 'FINAV')
    widget_xy(doc, 8, 'graph', 'History', x='28', width='44', height='11')
    doc.add(9, 'fields:')
    field(doc, 10, 'INTEGER', 'source', '2')
    field(doc, 10, 'STRING', 'reference', 'FIPTH')
    field(doc, 10, 'INTEGER', 'override_host', '1')
    field(doc, 10, 'STRING', 'override_host_reference', 'FINAV')
    field(doc, 10, 'STRING', 'time_period.from', 'now-1d')
    field(doc, 10, 'STRING', 'time_period.to', 'now')


def emit_honeycomb(doc: Doc, name, items, label, reference, thresholds, *, x=None, y=None, width='36', height='3') -> None:
    widget_xy(doc, 8, 'honeycomb', name, x=x, y=y, width=width, height=height)
    doc.add(9, 'fields:')
    field(doc, 10, 'STRING', 'items.0', items)
    field(doc, 10, 'STRING', 'primary_label', label)
    field(doc, 10, 'INTEGER', 'interpolation', '0')
    field(doc, 10, 'INTEGER', 'primary_label_bold', '1')
    field(doc, 10, 'INTEGER', 'primary_label_size_type', '1')
    field(doc, 10, 'INTEGER', 'primary_label_size', '20')
    field(doc, 10, 'INTEGER', 'show.0', '1')
    field(doc, 10, 'STRING', 'reference', reference)
    for i, (color, thr) in enumerate(thresholds):
        field(doc, 10, 'STRING', f'thresholds.{i}.color', color)
        field(doc, 10, 'STRING', f'thresholds.{i}.threshold', thr)


def emit_parent_valuemaps(doc: Doc) -> None:
    doc.add(3, 'valuemaps:')
    vmap(doc, 'Service state', [('0', 'Down'), ('1', 'Up')])
    vmap(doc, 'zabbix.host.available', [('0', 'Down'), ('1', 'Up'), ('2', 'Unknown')])
    vmap(doc, 'IF-MIB::ifStatus', [('1', 'up'), ('2', 'down'), ('3', 'testing'), ('4', 'unknown'), ('5', 'dormant'), ('6', 'notPresent'), ('7', 'lowerLayerDown')])
    vmap(doc, 'Fortinet FnBoolState', [('1', 'disabled'), ('2', 'enabled')])
    vmap(doc, 'Fortinet fmHaMode', [('0', 'standalone'), ('1', 'master'), ('2', 'slave')])
    vmap(
        doc,
        'Fortinet fmRaidState',
        [
            ('0', 'unavailable'),
            ('1', 'ok'),
            ('2', 'degraded'),
            ('3', 'failed'),
            ('4', 'background-initializing'),
            ('5', 'background-verifying'),
            ('6', 'background-rebuilding'),
        ],
    )
    vmap(
        doc,
        'Fortinet fmRaidLevel',
        [
            ('0', 'unavailable'),
            ('1', 'linear'),
            ('2', 'raid-0'),
            ('3', 'raid-1'),
            ('4', 'raid-1s'),
            ('5', 'raid-5'),
            ('6', 'raid-5s'),
            ('7', 'raid-6'),
            ('8', 'raid-6s'),
            ('9', 'raid-10'),
            ('10', 'raid-10s'),
            ('11', 'raid-50'),
            ('12', 'raid-50s'),
            ('13', 'raid-60'),
            ('14', 'raid-60s'),
        ],
    )
    vmap(
        doc,
        'Fortinet fmRaidDiskEntState',
        [
            ('0', 'unavailable'),
            ('1', 'failed'),
            ('2', 'unused'),
            ('3', 'ok'),
            ('4', 'rebuilding'),
            ('5', 'spare'),
        ],
    )
    vmap(
        doc,
        'Fortinet fmSensorEntState',
        [
            ('0', 'ok'),
            ('1', 'failed'),
            ('2', 'out-of-range-not-critical'),
            ('3', 'out-of-range-critical'),
            ('4', 'out-of-range-not-recoverable'),
            ('5', 'input-lost'),
            ('6', 'not-present'),
        ],
    )
    vmap(doc, 'Fortinet fmHaPeerEntState', [('0', 'down'), ('1', 'negotiating'), ('2', 'synchronizing'), ('3', 'up')])
    vmap(doc, 'Fortinet fmDeviceEntConnectState', [('0', 'unknown'), ('1', 'up'), ('2', 'down')])
    vmap(doc, 'Fortinet fmDeviceEntConfigState', [('0', 'unknown'), ('1', 'in-sync'), ('2', 'out-of-sync')])
    vmap(doc, 'Fortinet fmDeviceEntMode', [('0', 'unregistered'), ('1', 'fmg'), ('2', 'faz'), ('3', 'fmg-faz')])


def build_fmg() -> Doc:
    doc = Doc()
    header(doc)
    template_head(
        doc,
        uid(),
        FMG,
        f"""
FortiManager companion for {T}. Nests the shared SNMP parent (do not also
link Network Generic, ICMP Ping, or FortiGate templates).

Platform Template Rule FortiManager points here. Devices board is the product
page (FGFM connect-state map). Config out-of-sync stays collect-only — cfgit
owns that ticket. Health / Hardware / Cluster / Network interfaces come from
the nested parent.

Operator page: zabbix/03-fortinet.md.
""",
        nested=[T],
    )
    calc(doc, 'Managed devices', 'fmg.observability.device.count', 'last(//fm.device.number)', description='Headline managed-device count for the Devices board.')
    calc(doc, 'ADOMs', 'fmg.observability.adom.count', 'last(//fm.adom.number)', description='Headline ADOM count.')
    calc(doc, 'HA peers', 'fmg.observability.ha.peers', 'last(//fm.ha.peer.number)', description='Headline HA peer count.')
    doc.add(3, 'tags:')
    doc.add(4, '- tag: class')
    doc.add(5, 'value: network')
    doc.add(4, '- tag: target')
    doc.add(5, 'value: fortimanager')
    doc.add(3, 'macros:')
    doc.add(4, "- macro: '{$FM.DEVICE.CONTROL}'")
    doc.add(5, "value: '1'")
    doc.add(5, 'description: Ticket FGFM connect-down on this companion.')
    doc.add(4, "- macro: '{$FM.CONFIG.CONTROL}'")
    doc.add(5, "value: '0'")
    doc.add(5, 'description: cfgit owns config drift. Do not enable.')
    emit_fmg_dashboard(doc)
    doc.add(3, 'valuemaps:')
    vmap(doc, 'Service state', [('0', 'Down'), ('1', 'Up')])
    return doc


def emit_fmg_dashboard(doc: Doc) -> None:
    doc.add(3, 'dashboards:')
    doc.add(4, '- uuid: ' + uid())
    doc.add(5, 'name: Devices')
    doc.add(5, 'pages:')
    doc.add(6, '- name: Overview')
    doc.add(7, 'widgets:')
    widget_xy(doc, 8, 'item', 'Devices', width='18', height='4')
    doc.add(9, 'fields:')
    field(doc, 10, 'ITEM', 'itemid.0', None, item_host=FMG, item_key='fmg.observability.device.count')
    field(doc, 10, 'INTEGER', 'show.0', '2')
    field(doc, 10, 'INTEGER', 'value_bold', '1')
    field(doc, 10, 'INTEGER', 'value_size', '28')
    widget_xy(doc, 8, 'item', 'ADOMs', x='18', width='18', height='4')
    doc.add(9, 'fields:')
    field(doc, 10, 'ITEM', 'itemid.0', None, item_host=FMG, item_key='fmg.observability.adom.count')
    field(doc, 10, 'INTEGER', 'show.0', '2')
    field(doc, 10, 'INTEGER', 'value_bold', '1')
    field(doc, 10, 'INTEGER', 'value_size', '28')
    widget_xy(doc, 8, 'item', 'HA peers', x='36', width='18', height='4')
    doc.add(9, 'fields:')
    field(doc, 10, 'ITEM', 'itemid.0', None, item_host=FMG, item_key='fmg.observability.ha.peers')
    field(doc, 10, 'INTEGER', 'show.0', '2')
    field(doc, 10, 'INTEGER', 'value_bold', '1')
    field(doc, 10, 'INTEGER', 'value_size', '28')
    widget_xy(doc, 8, 'problems', 'Problems', x='54', width='18', height='4')
    doc.add(9, 'fields:')
    field(doc, 10, 'STRING', 'reference', 'FDPRB')
    field(doc, 10, 'INTEGER', 'show', '3')
    emit_honeycomb(
        doc,
        'Connect',
        'Device *: Connect state',
        '{{ITEM.NAME}.regsub("^Device (.*): Connect state$","\\1")}',
        'FDCON',
        [('878787', '0'), ('0EC9AC', '1'), ('FF465C', '2')],
        y='4',
        width='72',
        height='6',
    )
    emit_honeycomb(
        doc,
        'Config (cfgit owns tickets)',
        'Device *: Config state',
        '{{ITEM.NAME}.regsub("^Device (.*): Config state$","\\1")}',
        'FDCNF',
        [('878787', '0'), ('0EC9AC', '1'), ('FFD54F', '2')],
        y='10',
        width='72',
        height='5',
    )


def build_faz() -> Doc:
    doc = Doc()
    header(doc)
    template_head(
        doc,
        uid(),
        FAZ,
        f"""
FortiAnalyzer companion for {T}. Nests the shared SNMP parent (do not also
link Network Generic, ICMP Ping, or FortiGate templates).

Platform Template Rule FortiAnalyzer points here. Logs board is the product
page. Log disk High is justified here (log loss) — unlike FortiGate.
Device connect-down on the parent is the Zabbix choice for "device stopped
sending logs". FAZ product alerts gate on inherited parent ICMP/SNMP health
because Zabbix rejects child-template dependencies on parent triggers.

Operator page: zabbix/03-fortinet.md.
""",
        nested=[T],
    )
    calc(doc, 'Log rate', 'faz.observability.log.rate', 'last(//fm.sys.log.rate.hr)', units='logs/s', component='log', description='Headline log receive rate.')
    calc(
        doc,
        'Log lag',
        'faz.observability.log.lag',
        'last(//fm.sys.log.lag)',
        units='s',
        component='log',
        description='Receive-to-index delay. This is the FAZ product failure mode.',
        triggers=[
            dict(
                name=f'{FAZ}: Log indexing lag is high',
                expression=require_faz_parent_health(
                    f'min(/{FAZ}/faz.observability.log.lag,10m)>{{$FAZ.LOG.LAG.WARN}} and min(/{FAZ}/faz.observability.log.lag,10m)<={{$FAZ.LOG.LAG.CRIT}}'
                ),
                priority='WARNING',
                description='Indexing is falling behind receive. Reports/search will lag. Next day unless it climbs to Average.',
                scope='capacity',
            ),
            dict(
                name=f'{FAZ}: Log indexing lag is critical',
                expression=require_faz_parent_health(
                    f'min(/{FAZ}/faz.observability.log.lag,5m)>{{$FAZ.LOG.LAG.CRIT}}'
                ),
                priority='AVERAGE',
                description='Log lag above {$FAZ.LOG.LAG.CRIT} seconds. Ticket — FAZ is not keeping up. Disk/CPU/ingest path.',
                scope='capacity',
            ),
        ],
    )
    calc(
        doc,
        'Disk utilization',
        'faz.observability.disk.util',
        'last(//fm.sys.disk.util)',
        units='%',
        component='storage',
        description='FAZ log disk. High is justified — this is the product.',
        triggers=[
            dict(
                name=f'{FAZ}: Log disk is critically full',
                expression=require_faz_parent_health(
                    f'min(/{FAZ}/faz.observability.disk.util,5m)>{{$DISK.UTIL.HIGH}}'
                ),
                priority='HIGH',
                description='Log disk above {$DISK.UTIL.HIGH}. 03:00 page — FAZ will stop ingesting. Exception to site-only High: the product is about to drop data.',
                scope='capacity',
            )
        ],
    )
    calc(
        doc,
        'License GB/day today',
        'faz.observability.lic.gbday',
        'last(//fm.sys.lic.gbday.today)',
        units='GB',
        component='license',
        description='GiB received today. Trigger off while {$FAZ.LIC.GBDAY.MAX}=0.',
        triggers=[
            dict(
                name=f'{FAZ}: Licensed GB/day threshold exceeded',
                expression=require_faz_parent_health(
                    f'{{$FAZ.LIC.GBDAY.MAX}}>0 and min(/{FAZ}/faz.observability.lic.gbday,30m)>{{$FAZ.LIC.GBDAY.MAX}}'
                ),
                priority='AVERAGE',
                description="Today's ingest above {$FAZ.LIC.GBDAY.MAX}. Default 0 disables this until the licensed cap is known.",
                scope='capacity',
            )
        ],
    )
    calc(doc, 'Managed log devices', 'faz.observability.device.count', 'last(//fm.device.number)', description='Registered log devices.')
    doc.add(3, 'tags:')
    doc.add(4, '- tag: class')
    doc.add(5, 'value: network')
    doc.add(4, '- tag: target')
    doc.add(5, 'value: fortianalyzer')
    macros_block(
        doc,
        FORTIANALYZER_TEMPLATE_MACROS,
        {
            '{$FAZ.LOG.LAG.WARN}': 'Log lag Warning (seconds).',
            '{$FAZ.LOG.LAG.CRIT}': 'Log lag Average (seconds).',
            '{$FAZ.LIC.GBDAY.MAX}': '0 disables GB/day license Average. Set to the licensed cap.',
            '{$DISK.UTIL.HIGH}': 'FAZ log-disk High. 95 is log-loss territory.',
        },
    )
    emit_faz_dashboard(doc)
    doc.add(3, 'valuemaps:')
    vmap(doc, 'Service state', [('0', 'Down'), ('1', 'Up')])
    return doc


def emit_faz_dashboard(doc: Doc) -> None:
    doc.add(3, 'dashboards:')
    doc.add(4, '- uuid: ' + uid())
    doc.add(5, 'name: Logs')
    doc.add(5, 'pages:')
    doc.add(6, '- name: Overview')
    doc.add(7, 'widgets:')
    widget_xy(doc, 8, 'gauge', 'Disk', width='18', height='4')
    gauge_fields(doc, 9, FAZ, 'faz.observability.disk.util', units='%', thresholds=[('0EC9AC', '0'), ('FFD54F', '80'), ('FF465C', '90'), ('E53935', '95')])
    widget_xy(doc, 8, 'item', 'Log lag', x='18', width='18', height='4')
    doc.add(9, 'fields:')
    field(doc, 10, 'ITEM', 'itemid.0', None, item_host=FAZ, item_key='faz.observability.log.lag')
    field(doc, 10, 'INTEGER', 'show.0', '2')
    field(doc, 10, 'INTEGER', 'value_bold', '1')
    field(doc, 10, 'INTEGER', 'value_size', '28')
    widget_xy(doc, 8, 'item', 'Log rate', x='36', width='18', height='4')
    doc.add(9, 'fields:')
    field(doc, 10, 'ITEM', 'itemid.0', None, item_host=FAZ, item_key='faz.observability.log.rate')
    field(doc, 10, 'INTEGER', 'show.0', '2')
    field(doc, 10, 'INTEGER', 'value_bold', '1')
    field(doc, 10, 'INTEGER', 'value_size', '24')
    widget_xy(doc, 8, 'item', 'GB/day', x='54', width='18', height='4')
    doc.add(9, 'fields:')
    field(doc, 10, 'ITEM', 'itemid.0', None, item_host=FAZ, item_key='faz.observability.lic.gbday')
    field(doc, 10, 'INTEGER', 'show.0', '2')
    field(doc, 10, 'INTEGER', 'value_bold', '1')
    field(doc, 10, 'INTEGER', 'value_size', '24')
    widget_xy(doc, 8, 'problems', 'Problems', y='4', width='72', height='3')
    doc.add(9, 'fields:')
    field(doc, 10, 'STRING', 'reference', 'FLPRB')
    field(doc, 10, 'INTEGER', 'show', '3')
    field(doc, 10, 'INTEGER', 'show_opdata', '2')
    widget_xy(doc, 8, 'svggraph', 'Log rate / lag', y='7', width='36', height='6')
    doc.add(9, 'fields:')
    field(doc, 10, 'STRING', 'ds.0.color.0', '199C0D')
    field(doc, 10, 'STRING', 'ds.0.color.1', 'FF9800')
    field(doc, 10, 'INTEGER', 'ds.0.dataset_type', '0')
    field(doc, 10, 'ITEM', 'ds.0.itemids.0', None, item_host=FAZ, item_key='faz.observability.log.rate')
    field(doc, 10, 'ITEM', 'ds.0.itemids.1', None, item_host=FAZ, item_key='faz.observability.log.lag')
    field(doc, 10, 'STRING', 'reference', 'FLRATE')
    field(doc, 10, 'INTEGER', 'show_problems', '1')
    field(doc, 10, 'INTEGER', 'legend', '1')
    svg_time_period(doc, 10)
    widget_xy(doc, 8, 'svggraph', 'Disk', x='36', y='7', width='36', height='6')
    doc.add(9, 'fields:')
    field(doc, 10, 'STRING', 'ds.0.color.0', '2774A4')
    field(doc, 10, 'INTEGER', 'ds.0.dataset_type', '0')
    field(doc, 10, 'ITEM', 'ds.0.itemids.0', None, item_host=FAZ, item_key='faz.observability.disk.util')
    field(doc, 10, 'STRING', 'lefty_max', '100')
    field(doc, 10, 'STRING', 'lefty_min', '0')
    field(doc, 10, 'STRING', 'reference', 'FLDSK')
    field(doc, 10, 'INTEGER', 'show_problems', '1')
    field(doc, 10, 'INTEGER', 'legend', '0')
    svg_time_period(doc, 10)
    emit_honeycomb(
        doc,
        'ADOM archive %',
        'ADOM *: Archive used %',
        '{{ITEM.NAME}.regsub("^ADOM (.*): Archive used %$","\\1")}',
        'FLARC',
        [('0EC9AC', '0'), ('FFD54F', '80'), ('FF465C', '90')],
        y='13',
        width='36',
        height='5',
    )
    emit_honeycomb(
        doc,
        'Log devices',
        'Device *: Connect state',
        '{{ITEM.NAME}.regsub("^Device (.*): Connect state$","\\1")}',
        'FLDEV',
        [('878787', '0'), ('0EC9AC', '1'), ('FF465C', '2')],
        x='36',
        y='13',
        width='36',
        height='5',
    )


def main() -> int:
    parent = build_parent()
    parent.dump(FMG_FAZ_SNMP_YAML)
    build_fmg().dump(FORTIMANAGER_OBSERVABILITY_YAML)
    build_faz().dump(FORTIANALYZER_OBSERVABILITY_YAML)
    print(f'wrote {FMG_FAZ_SNMP_YAML}')
    print(f'wrote {FORTIMANAGER_OBSERVABILITY_YAML}')
    print(f'wrote {FORTIANALYZER_OBSERVABILITY_YAML}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
