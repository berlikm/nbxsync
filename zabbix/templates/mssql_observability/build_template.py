#!/usr/bin/env python3
"""Emit MSSQL Observability Zabbix 7.0 YAML (named-instance Agent 2 companion)."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))

from mssql_observability import (  # noqa: E402
    BACKUP_KEY,
    BATCH_RATE_KEY,
    BUFFER_CACHE_KEY,
    BUFFER_RAW_KEY,
    CENSUS_KEY,
    CENSUS_TRIGGER_EXPR,
    CENSUS_TRIGGER_NAME,
    DASHBOARD_UUID,
    DB_COUNT_KEY,
    DB_KEY,
    DISCOVERY_KEY,
    FAILED_JOBS_KEY,
    JOB_KEY,
    LOCK_TIMEOUTS_KEY,
    LOCKS_RAW_KEY,
    MACRO_BUFFER_CACHE_MIN,
    MACRO_DESCRIPTIONS,
    MACRO_INSTANCE_DISCOVERY_MIN,
    MACRO_INSTANCE_MATCHES,
    MACRO_INSTANCE_NOT_MATCHES,
    MACRO_PAGE_LIFE_MIN,
    NAMED_URI,
    PAGE_LIFE_KEY,
    PERF_KEY,
    PING_KEY,
    PING_TRIGGER_EXPR,
    PING_TRIGGER_NAME,
    STATS_RAW_KEY,
    STOCK_TEMPLATE_NAME,
    TEMPLATE_GROUP,
    TEMPLATE_GROUP_UUID,
    TEMPLATE_MACROS,
    TEMPLATE_NAME,
    TEMPLATE_UUID,
    VERSION_KEY,
    VERSION_NODATA_EXPR,
    VERSION_NODATA_NAME,
    WMI_ITEM_KEY,
    WMI_LLD_JS,
    ZABBIX_TEMPLATE_PATH,
)

NS = uuid.UUID(TEMPLATE_UUID)


def uid(name: str) -> str:
    return uuid.uuid5(NS, name).hex


def q(value: str) -> str:
    if value == '':
        return "''"
    special = set(":{}[]&*?|>'!%@`#;")
    if value.isdigit() or any(c in special for c in value) or value != value.strip() or '\n' in value:
        return "'" + value.replace("'", "''") + "'"
    if value.lower() in {'y', 'n', 'yes', 'no', 'true', 'false', 'on', 'off', 'null'}:
        return "'" + value + "'"
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
    event_name: str | None = None,
) -> None:
    doc.add(indent, '- uuid: ' + uid(f'trigger:{name}:{expression}'))
    doc.add(indent + 1, f'expression: {q(expression)}')
    if recovery:
        doc.add(indent + 1, 'recovery_mode: RECOVERY_EXPRESSION')
        doc.add(indent + 1, f'recovery_expression: {q(recovery)}')
    doc.add(indent + 1, f'name: {q(name)}')
    if event_name:
        doc.add(indent + 1, f'event_name: {q(event_name)}')
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
            doc.add(indent + 2, 'parameters:')
            doc.add(indent + 3, "- ''")
        elif kind == 'JSONPATH':
            doc.add(indent + 2, 'parameters:')
            doc.add(indent + 3, f'- {q(str(step[1]))}')
            if len(step) > 2 and step[2] == 'DISCARD_VALUE':
                doc.add(indent + 2, 'error_handler: DISCARD_VALUE')
            elif len(step) > 2 and step[2] == 'CUSTOM_VALUE':
                doc.add(indent + 2, 'error_handler: CUSTOM_VALUE')
                doc.add(indent + 2, f"error_handler_params: '{step[3]}'")
        else:
            if len(step) > 1:
                doc.add(indent + 2, 'parameters:')
                doc.add(indent + 3, f'- {q(str(step[1]))}')


def field(
    doc: Doc,
    indent: int,
    typ: str,
    name: str,
    value,
    *,
    item_host: str | None = None,
    item_key: str | None = None,
) -> None:
    doc.add(indent, f'- type: {typ}')
    doc.add(indent + 1, f'name: {name}')
    if typ == 'ITEM':
        doc.add(indent + 1, 'value:')
        doc.add(indent + 2, f'host: {item_host}')
        doc.add(indent + 2, f'key: {q(item_key or "")}')
    else:
        doc.add(indent + 1, f"value: '{value}'")


def widget_xy(doc: Doc, indent: int, typ: str, name: str, *, x=None, y=None, width='18', height='4') -> None:
    doc.add(indent, f'- type: {typ}')
    doc.add(indent + 1, f'name: {name}')
    if x is not None:
        doc.add(indent + 1, f"x: '{x}'")
    if y is not None:
        doc.add(indent + 1, f"y: '{y}'")
    doc.add(indent + 1, f"width: '{width}'")
    doc.add(indent + 1, f"height: '{height}'")


INSTANCE_TAGS = [('sql_instance', '{#MSSQL.INSTANCE}')]
PING_DEP = (PING_TRIGGER_NAME, PING_TRIGGER_EXPR)

DESC = f"""
Estate companion for stock {STOCK_TEMPLATE_NAME}. Link **alongside** stock on
roles MSSQL / MSSQL Query Server — do not nest stock (that would still be one
{{$MSSQL.URI}}). Stock keeps the default instance
(sqlserver://localhost:1433). This template LLD-discovers named Windows
instances (MSSQL$%) via WMI and calls the Agent 2 MSSQL plugin with
{NAMED_URI} (no port; plugin ≥ 7.0.6, template requires plugin ≥ 7.0.10).

v1 is instance-level: ping, version, sparse perfcounters, job/backup/db
masters, database count. Per-database LLD on named instances is v2 (Zabbix
cannot nest discovery-under-discovery on the same host).

Do not reuse the Windows-by-agent service LLD key. Do not nest ICMP or
invent host prototypes. Do not put instance names in NetBox.

Operator spec: zabbix/notes/mssql-agent2-instances.md.
"""


def emit_item_head(
    doc: Doc,
    indent: int,
    name: str,
    key: str,
    *,
    item_type: str | None,
    delay: str | None,
    value_type: str | None,
    history: str | None,
    trends: str | None,
    units: str | None,
    description: str,
    timeout: str | None,
    valuemap: str | None,
    master_key: str | None,
) -> None:
    doc.add(indent, '- uuid: ' + uid(f'item:{key}'))
    doc.add(indent + 1, f'name: {q(name)}')
    if item_type:
        doc.add(indent + 1, f'type: {item_type}')
    doc.add(indent + 1, f'key: {q(key)}')
    if delay is not None:
        doc.add(indent + 1, f'delay: {q(delay) if ";" in delay or delay == "0" else delay}')
    if value_type:
        doc.add(indent + 1, f'value_type: {value_type}')
    if history:
        doc.add(indent + 1, f'history: {q(history) if history == "0" else history}')
    if trends is not None:
        doc.add(indent + 1, f"trends: '{trends}'" if str(trends) == '0' else f'trends: {trends}')
    if units:
        doc.add(indent + 1, f'units: {q(units)}')
    if timeout:
        doc.add(indent + 1, f'timeout: {timeout}')
    if description:
        doc.add(indent + 1, f'description: {q(description)}')
    if valuemap:
        doc.add(indent + 1, 'valuemap:')
        doc.add(indent + 2, f'name: {q(valuemap)}')
    if master_key:
        doc.add(indent + 1, 'master_item:')
        doc.add(indent + 2, f'key: {q(master_key)}')


def emit_item(
    doc: Doc,
    indent: int,
    name: str,
    key: str,
    *,
    item_type: str | None = None,
    delay: str | None = '1m',
    value_type: str | None = None,
    history: str | None = None,
    trends: str | None = None,
    units: str | None = None,
    description: str = '',
    timeout: str | None = None,
    valuemap: str | None = None,
    master_key: str | None = None,
    component: str = 'application',
    extra_tags: list[tuple[str, str]] | None = None,
    steps: list[tuple] | None = None,
    triggers: list[dict] | None = None,
    trigger_section: str = 'triggers',
) -> None:
    emit_item_head(
        doc,
        indent,
        name,
        key,
        item_type=item_type,
        delay=delay,
        value_type=value_type,
        history=history,
        trends=trends,
        units=units,
        description=description,
        timeout=timeout,
        valuemap=valuemap,
        master_key=master_key,
    )
    if steps:
        preprocess(doc, indent + 1, steps)
    tags(doc, indent + 1, component, extra_tags)
    if triggers:
        doc.add(indent + 1, f'{trigger_section}:')
        for kwargs in triggers:
            trig(doc, indent + 2, **kwargs)


def build() -> Doc:
    doc = Doc()
    doc.add(0, 'zabbix_export:')
    doc.add(1, "version: '7.0'")
    doc.add(1, 'template_groups:')
    doc.add(2, f'- uuid: {TEMPLATE_GROUP_UUID}')
    doc.add(3, f'name: {TEMPLATE_GROUP}')
    doc.add(1, 'templates:')
    doc.add(2, f'- uuid: {TEMPLATE_UUID}')
    doc.add(3, f'template: {q(TEMPLATE_NAME)}')
    doc.add(3, f'name: {q(TEMPLATE_NAME)}')
    doc.add(3, 'description: |')
    for line in DESC.strip('\n').splitlines():
        doc.add(4, line)
    doc.add(3, 'groups:')
    doc.add(4, f'- name: {TEMPLATE_GROUP}')
    doc.add(3, 'items:')

    emit_item(
        doc,
        3,
        'Named instance WMI',
        WMI_ITEM_KEY,
        delay='15m',
        value_type='TEXT',
        history='0',
        trends='0',
        timeout='30s',
        description=(
            'Win32_Service rows matching MSSQL$% (named instances only). '
            'MSSQLSERVER has no dollar and stays on stock. Not-supported becomes empty LLD.'
        ),
        component='raw',
        steps=[
            ('CHECK_NOT_SUPPORTED', '-1', '[]'),
            ('JAVASCRIPT', WMI_LLD_JS),
            ('DISCARD_UNCHANGED_HEARTBEAT', '1h'),
        ],
    )
    emit_item(
        doc,
        3,
        'Named instances',
        CENSUS_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='FLOAT',
        description='Count of MSSQL$% services from WMI (before LLD filters).',
        master_key=WMI_ITEM_KEY,
        component='health',
        steps=[('JSONPATH', '$.length()', 'CUSTOM_VALUE', '0')],
        triggers=[
            {
                'name': CENSUS_TRIGGER_NAME,
                'expression': CENSUS_TRIGGER_EXPR,
                'priority': 'AVERAGE',
                'description': (
                    'Named-instance census. Default MIN=0 so default-only hosts stay quiet. '
                    'Set {$MSSQL.INSTANCE.DISCOVERY.MIN} on the Device when you expect N instances.'
                ),
                'scope': 'availability',
            }
        ],
    )

    doc.add(3, 'discovery_rules:')
    doc.add(4, '- uuid: ' + uid('discovery:named-instance'))
    doc.add(5, 'name: Named instance discovery')
    doc.add(5, 'type: DEPENDENT')
    doc.add(5, f'key: {DISCOVERY_KEY}')
    doc.add(5, "delay: '0'")
    doc.add(5, 'lifetime: 7d')
    doc.add(5, 'lifetime_type: DELETE_AFTER')
    doc.add(5, "enabled_lifetime: '0'")
    doc.add(5, 'enabled_lifetime_type: DISABLE_IMMEDIATELY')
    doc.add(5, 'filter:')
    doc.add(6, 'evaltype: AND')
    doc.add(6, 'conditions:')
    doc.add(7, f'- macro: \'{{#MSSQL.INSTANCE}}\'')
    doc.add(8, f'value: {q(MACRO_INSTANCE_MATCHES)}')
    doc.add(8, 'formulaid: A')
    doc.add(7, f'- macro: \'{{#MSSQL.INSTANCE}}\'')
    doc.add(8, f'value: {q(MACRO_INSTANCE_NOT_MATCHES)}')
    doc.add(8, 'operator: NOT_MATCHES_REGEX')
    doc.add(8, 'formulaid: B')
    doc.add(5, 'description: Named SQL Server instances (MSSQL$%). Default instance is stock.')
    doc.add(5, 'master_item:')
    doc.add(6, f'key: {q(WMI_ITEM_KEY)}')
    doc.add(5, 'item_prototypes:')

    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Ping',
        PING_KEY,
        delay='1m',
        timeout='30s',
        valuemap='Service state',
        description='Plugin TDS ping for this named instance (1=alive). Not TCP 1433.',
        component='availability',
        extra_tags=INSTANCE_TAGS,
        trigger_section='trigger_prototypes',
        triggers=[
            {
                'name': PING_TRIGGER_NAME,
                'expression': PING_TRIGGER_EXPR,
                'priority': 'AVERAGE',
                'description': (
                    'Named instance is not answering TDS. Windows already tickets a stopped '
                    'MSSQL$ service. This is login/URI/Browser/plugin — not Disaster.'
                ),
                'scope': 'availability',
            }
        ],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Version',
        VERSION_KEY,
        delay='1m',
        value_type='CHAR',
        trends='0',
        timeout='30s',
        description='SQL Server version string for this named instance.',
        component='application',
        extra_tags=INSTANCE_TAGS,
        steps=[('DISCARD_UNCHANGED_HEARTBEAT', '1d')],
        trigger_section='trigger_prototypes',
        triggers=[
            {
                'name': VERSION_NODATA_NAME,
                'expression': VERSION_NODATA_EXPR,
                'priority': 'AVERAGE',
                'description': (
                    'No version for 15m — login missing on this instance, plugin, or Browser/port. '
                    'Depends on TDS unavailable so a down instance is one ticket.'
                ),
                'dependencies': [PING_DEP],
                'scope': 'availability',
            }
        ],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Get performance counters',
        PERF_KEY,
        delay='0;m0-59',
        value_type='TEXT',
        history='0',
        trends='0',
        timeout='30s',
        description='Sparse perfcounter master for this named instance (not the full stock pack).',
        component='raw',
        extra_tags=INSTANCE_TAGS,
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Buffer Manager counters',
        BUFFER_RAW_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='TEXT',
        history='0',
        trends='0',
        master_key=PERF_KEY,
        component='raw',
        extra_tags=INSTANCE_TAGS,
        steps=[('JSONPATH', "$[?(@.object_name=~'.*Buffer Manager')]", 'DISCARD_VALUE')],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: SQL Statistics counters',
        STATS_RAW_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='TEXT',
        history='0',
        trends='0',
        master_key=PERF_KEY,
        component='raw',
        extra_tags=INSTANCE_TAGS,
        steps=[('JSONPATH', "$[?(@.object_name=~'.*SQL Statistics')]", 'DISCARD_VALUE')],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Locks counters',
        LOCKS_RAW_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='TEXT',
        history='0',
        trends='0',
        master_key=PERF_KEY,
        component='raw',
        extra_tags=INSTANCE_TAGS,
        steps=[
            (
                'JSONPATH',
                "$[?(@.object_name=~'.*Locks' && @.instance_name=='_Total')]",
                'DISCARD_VALUE',
            )
        ],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Buffer cache hit ratio',
        BUFFER_CACHE_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='FLOAT',
        units='%',
        master_key=BUFFER_RAW_KEY,
        description='Pages found in buffer cache without a disk read.',
        component='cache',
        extra_tags=INSTANCE_TAGS,
        steps=[('JSONPATH', "$[?(@.counter_name=='BufferCacheHitRatio')].cntr_value.first()")],
        trigger_section='trigger_prototypes',
        triggers=[
            {
                'name': 'MSSQL [{#MSSQL.INSTANCE}]: Buffer cache hit ratio is low',
                'expression': (
                    f'max(/{TEMPLATE_NAME}/{BUFFER_CACHE_KEY},5m)<{MACRO_BUFFER_CACHE_MIN}'
                ),
                'event_name': (
                    'MSSQL [{#MSSQL.INSTANCE}]: Buffer cache hit ratio is low '
                    f'(below {MACRO_BUFFER_CACHE_MIN}% for 5m)'
                ),
                'priority': 'WARNING',
                'description': 'Estate Warning only — stock High on the default instance is too hot here.',
                'dependencies': [PING_DEP],
                'scope': 'performance',
            }
        ],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Page life expectancy',
        PAGE_LIFE_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='FLOAT',
        units='s',
        master_key=BUFFER_RAW_KEY,
        description='Seconds a page stays in the buffer pool without references.',
        component='page',
        extra_tags=INSTANCE_TAGS,
        steps=[('JSONPATH', "$[?(@.counter_name=='Page life expectancy')].cntr_value.first()")],
        trigger_section='trigger_prototypes',
        triggers=[
            {
                'name': 'MSSQL [{#MSSQL.INSTANCE}]: Page life expectancy is low',
                'expression': (
                    f'max(/{TEMPLATE_NAME}/{PAGE_LIFE_KEY},15m)<{MACRO_PAGE_LIFE_MIN}'
                ),
                'event_name': (
                    'MSSQL [{#MSSQL.INSTANCE}]: Page life expectancy is low '
                    f'(less {MACRO_PAGE_LIFE_MIN}s for 15m)'
                ),
                'priority': 'WARNING',
                'description': 'Estate Warning only — stock High on the default instance is too hot here.',
                'dependencies': [PING_DEP],
                'scope': 'performance',
            }
        ],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Batch requests per second',
        BATCH_RATE_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='FLOAT',
        units='rps',
        master_key=STATS_RAW_KEY,
        description='Transact-SQL batches received per second.',
        component='performance',
        extra_tags=INSTANCE_TAGS,
        steps=[
            ('JSONPATH', "$[?(@.counter_name=='Batch Requests/sec')].cntr_value.first()"),
            ('CHANGE_PER_SECOND',),
        ],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Lock timeouts per second',
        LOCK_TIMEOUTS_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='FLOAT',
        units='rps',
        master_key=LOCKS_RAW_KEY,
        description='Timed-out lock requests per second, including NOWAIT.',
        component='lock',
        extra_tags=INSTANCE_TAGS,
        steps=[
            ('JSONPATH', "$[?(@.counter_name=='Lock Timeouts/sec')].cntr_value.first()"),
            ('CHANGE_PER_SECOND',),
        ],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Get job status',
        JOB_KEY,
        delay='10m',
        value_type='TEXT',
        history='0',
        trends='0',
        timeout='30s',
        description='SQL Agent job status JSON for this named instance. Per-job LLD is v2.',
        component='raw',
        extra_tags=INSTANCE_TAGS,
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Failed jobs',
        FAILED_JOBS_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='FLOAT',
        master_key=JOB_KEY,
        description='Jobs whose last run_status is Failed (0). Collect-only in v1.',
        component='mssql-job',
        extra_tags=INSTANCE_TAGS,
        steps=[('JSONPATH', '$[?(@.run_status==0)].length()', 'CUSTOM_VALUE', '0')],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Get last backup',
        BACKUP_KEY,
        delay='10m',
        value_type='TEXT',
        history='0',
        trends='0',
        timeout='30s',
        description='Last-backup JSON for this named instance. Per-database backup age is v2.',
        component='raw',
        extra_tags=INSTANCE_TAGS,
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Get database',
        DB_KEY,
        delay='1h',
        value_type='TEXT',
        history='0',
        trends='0',
        timeout='30s',
        description='Database JSON for this named instance. No DB LLD in v1.',
        component='raw',
        extra_tags=INSTANCE_TAGS,
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Database count',
        DB_COUNT_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='FLOAT',
        master_key=DB_KEY,
        description='What SQL returned (includes system DBs). Not the stock MATCHES filter.',
        component='application',
        extra_tags=INSTANCE_TAGS,
        steps=[('JSONPATH', '$.length()', 'CUSTOM_VALUE', '0')],
    )

    doc.add(3, 'tags:')
    doc.add(4, '- tag: class')
    doc.add(5, 'value: database')
    doc.add(4, '- tag: target')
    doc.add(5, 'value: mssql')
    doc.add(3, 'macros:')
    for macro, value in TEMPLATE_MACROS.items():
        doc.add(4, f'- macro: {q(macro)}')
        doc.add(5, f'value: {q(value)}')
        if macro in MACRO_DESCRIPTIONS:
            doc.add(5, f'description: {q(MACRO_DESCRIPTIONS[macro])}')

    doc.add(3, 'dashboards:')
    doc.add(4, f'- uuid: {DASHBOARD_UUID}')
    doc.add(5, 'name: Health')
    doc.add(5, 'pages:')
    doc.add(6, '- name: Overview')
    doc.add(7, 'widgets:')
    widget_xy(doc, 8, 'item', 'Named instances', width='18', height='4')
    doc.add(9, 'fields:')
    field(doc, 10, 'ITEM', 'itemid.0', None, item_host=TEMPLATE_NAME, item_key=CENSUS_KEY)
    field(doc, 10, 'INTEGER', 'show.0', '2')
    field(doc, 10, 'INTEGER', 'value_bold', '1')
    field(doc, 10, 'INTEGER', 'value_size', '28')
    widget_xy(doc, 8, 'problems', 'Problems', x='18', width='54', height='4')
    doc.add(9, 'fields:')
    field(doc, 10, 'STRING', 'reference', 'MSSQLPRB')
    field(doc, 10, 'INTEGER', 'show', '3')
    widget_xy(doc, 8, 'honeycomb', 'Ping', y='4', width='72', height='6')
    doc.add(9, 'fields:')
    field(doc, 10, 'STRING', 'items.0', 'MSSQL [*]: Ping')
    field(
        doc,
        10,
        'STRING',
        'primary_label',
        '{{ITEM.NAME}.regsub("^MSSQL \\[(.*)\\]: Ping$","\\1")}',
    )
    field(doc, 10, 'INTEGER', 'interpolation', '0')
    field(doc, 10, 'INTEGER', 'primary_label_bold', '1')
    field(doc, 10, 'INTEGER', 'primary_label_size_type', '1')
    field(doc, 10, 'INTEGER', 'primary_label_size', '20')
    field(doc, 10, 'INTEGER', 'show.0', '1')
    field(doc, 10, 'STRING', 'reference', 'MSSQLPNG')
    field(doc, 10, 'STRING', 'thresholds.0.color', 'FF465C')
    field(doc, 10, 'STRING', 'thresholds.0.threshold', '0')
    field(doc, 10, 'STRING', 'thresholds.1.color', '0EC9AC')
    field(doc, 10, 'STRING', 'thresholds.1.threshold', '1')

    doc.add(3, 'valuemaps:')
    doc.add(4, '- uuid: ' + uid('valuemap:service-state'))
    doc.add(5, 'name: Service state')
    doc.add(5, 'mappings:')
    doc.add(6, "- value: '0'")
    doc.add(7, 'newvalue: Down')
    doc.add(6, "- value: '1'")
    doc.add(7, 'newvalue: Up')
    return doc


def main() -> int:
    build().dump(ZABBIX_TEMPLATE_PATH)
    print(f'wrote {ZABBIX_TEMPLATE_PATH}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
