#!/usr/bin/env python3
"""Emit MSSQL Observability Zabbix 7.0 YAML (named-instance Agent 2 companion)."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))

from mssql_observability import (  # noqa: E402
    AG_GET_KEY,
    BACKUP_DIFF_CRIT_EXPR,
    BACKUP_DIFF_KEY,
    BACKUP_DIFF_WARN_EXPR,
    BACKUP_FULL_CRIT_EXPR,
    BACKUP_FULL_KEY,
    BACKUP_FULL_WARN_EXPR,
    BACKUP_KEY,
    BACKUP_LOG_CRIT_EXPR,
    BACKUP_LOG_KEY,
    BACKUP_LOG_WARN_EXPR,
    BACKUP_RAW_KEY,
    BACKUP_RECOVERY_KEY,
    BATCH_RATE_KEY,
    BUFFER_CACHE_KEY,
    BUFFER_RAW_KEY,
    CENSUS_KEY,
    CENSUS_TRIGGER_EXPR,
    CENSUS_TRIGGER_NAME,
    DASHBOARD_UUID,
    DB_CATALOG_JS,
    DB_CATALOG_KEY,
    DB_CATALOG_SEED_KEY,
    DB_COUNT_KEY,
    DB_FOREACH_FORMULA,
    DB_KEY,
    DB_LLD_KEY,
    DB_LLDJSON_KEY,
    DB_PERF_RAW_KEY,
    DB_STATE_KEY,
    DISCOVERY_KEY,
    FAILED_JOBS_KEY,
    FLATTEN_LLD_JS,
    JOB_KEY,
    LOCAL_CATALOG_KEY,
    LOCAL_CATALOG_SEED_KEY,
    LOCAL_DB_CATALOG_JS,
    LOCAL_DB_GET_KEY,
    LOCAL_FOREACH_FORMULA,
    LOCAL_LLD_KEY,
    LOCAL_LLDJSON_KEY,
    LOCAL_STATE_KEY,
    LOCAL_SUSPENDED_KEY,
    LOCAL_SYNC_KEY,
    LOCK_TIMEOUTS_KEY,
    LOCKS_RAW_KEY,
    MACRO_BUFFER_CACHE_MIN,
    MACRO_DBNAME_MATCHES,
    MACRO_DBNAME_NOT_MATCHES,
    MACRO_DESCRIPTIONS,
    MACRO_INSTANCE_DISCOVERY_MIN,
    MACRO_INSTANCE_MATCHES,
    MACRO_INSTANCE_NOT_MATCHES,
    MACRO_PAGE_LIFE_MIN,
    NAMED_URI,
    PAGE_LIFE_KEY,
    PERCENT_LOG_KEY,
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


# Preserve the objects from the already-imported named-instance companion.
# New objects use a deterministic RFC 4122 v4 UUID because Zabbix 7.0 rejects
# v5 UUIDs during configuration import.
LEGACY_UUIDS = {
    f'item:{WMI_ITEM_KEY}': '3f55ba471ea249e6a93c97cc8e67baee',
    f'item:{CENSUS_KEY}': '3ecd3acbb9b04143a837cbc412cc20c1',
    f'trigger:{CENSUS_TRIGGER_NAME}:{CENSUS_TRIGGER_EXPR}': '33a0e2815f7245a9a40f8fffeec4c0c8',
    'discovery:named-instance': 'cb908a0bf4d64704b69907e919467af3',
    f'item:{VERSION_KEY}': '0625bb035bb240dbaac8b402852eeb93',
    f'trigger:{VERSION_NODATA_NAME}:{VERSION_NODATA_EXPR}': '70b0db2ec48940d2912ad06244c7fe17',
    f'item:{PERF_KEY}': '945c5894c04248aa9aafaf11d753df2f',
    f'item:{JOB_KEY}': 'b6b8df024f6140728afe38346cd4980b',
    f'item:{BACKUP_KEY}': '3e701a797e4e4c3a91227d823c504b00',
    f'item:{DB_KEY}': '45b50c5a4ea6461e82186d0a3b265ac5',
    f'item:{DB_COUNT_KEY}': 'cc5e55eea05e459ab565ebd64e119f82',
}


def uid(name: str) -> str:
    if name in LEGACY_UUIDS:
        return LEGACY_UUIDS[name]
    value = bytearray(uuid.uuid5(NS, name).bytes)
    value[6] = (value[6] & 0x0F) | 0x40
    value[8] = (value[8] & 0x3F) | 0x80
    return uuid.UUID(bytes=bytes(value)).hex


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
    opdata: str | None = None,
    extra_tags: list[tuple[str, str]] | None = None,
) -> None:
    doc.add(indent, '- uuid: ' + uid(f'trigger:{name}:{expression}'))
    doc.add(indent + 1, f'expression: {q(expression)}')
    if recovery:
        doc.add(indent + 1, 'recovery_mode: RECOVERY_EXPRESSION')
        doc.add(indent + 1, f'recovery_expression: {q(recovery)}')
    doc.add(indent + 1, f'name: {q(name)}')
    if event_name:
        doc.add(indent + 1, f'event_name: {q(event_name)}')
    if opdata:
        doc.add(indent + 1, f'opdata: {q(opdata)}')
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
    for tag, value in extra_tags or []:
        doc.add(indent + 2, f'- tag: {tag}')
        doc.add(indent + 3, f'value: {q(value)}')


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
        elif kind == 'MULTIPLIER':
            doc.add(indent + 2, 'parameters:')
            doc.add(indent + 3, f"- '{step[1]}'")
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
        doc.add(indent + 1, f'value: {q(str(value))}')


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
DB_TAGS = [('sql_instance', '{#MSSQL.INSTANCE}'), ('database', '{#DBNAME}')]
LOCAL_TAGS = [
    ('sql_instance', '{#MSSQL.INSTANCE}'),
    ('availability-group', '{#GROUP_NAME}'),
    ('local-db', '{#DBNAME}'),
]
PING_DEP = (PING_TRIGGER_NAME, PING_TRIGGER_EXPR)
BACKUP_OPDATA = 'Time since last backup: {ITEM.LASTVALUE1}'

DESC = f"""
Estate companion for stock {STOCK_TEMPLATE_NAME}. Link **alongside** stock on
roles MSSQL / MSSQL Query Server — do not nest stock (that would still be one
{{$MSSQL.URI}}). Stock keeps the default instance
(sqlserver://localhost:1433). This template LLD-discovers named Windows
instances (MSSQL$%) via WMI and calls the Agent 2 MSSQL plugin with
{NAMED_URI} (no port; plugin ≥ 7.0.6, template requires plugin ≥ 7.0.10).

Named-instance databases and Always On local DBs are a second, flattened LLD
({{#MSSQL.INSTANCE}}+{{#DBNAME}}). Zabbix 7.0 cannot nest discovery-under-discovery
on the same host. Keys include the instance so they cannot collide with stock.
Backup USED flags default to 1 on every environment — do not mute Test/Dev here.

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
    params: str | None = None,
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
    if params is not None:
        if '\n' in params:
            doc.add(indent + 1, 'params: |')
            for line in params.splitlines():
                doc.add(indent + 2, line)
        else:
            doc.add(indent + 1, f'params: {q(params)}')
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
    params: str | None = None,
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
        params=params,
    )
    if steps:
        preprocess(doc, indent + 1, steps)
    tags(doc, indent + 1, component, extra_tags)
    if triggers:
        doc.add(indent + 1, f'{trigger_section}:')
        for kwargs in triggers:
            trig(doc, indent + 2, **kwargs)


def emit_filter_pair(doc: Doc, indent: int, macro: str, matches: str, not_matches: str) -> None:
    doc.add(indent, 'filter:')
    doc.add(indent + 1, 'evaltype: AND')
    doc.add(indent + 1, 'conditions:')
    doc.add(indent + 2, f'- macro: {q(macro)}')
    doc.add(indent + 3, f'value: {q(matches)}')
    doc.add(indent + 3, 'formulaid: A')
    doc.add(indent + 2, f'- macro: {q(macro)}')
    doc.add(indent + 3, f'value: {q(not_matches)}')
    doc.add(indent + 3, 'operator: NOT_MATCHES_REGEX')
    doc.add(indent + 3, 'formulaid: B')


def emit_valuemap(doc: Doc, indent: int, name: str, mappings: list[tuple[str, str]]) -> None:
    doc.add(indent, '- uuid: ' + uid(f'valuemap:{name}'))
    doc.add(indent + 1, f'name: {q(name)}')
    doc.add(indent + 1, 'mappings:')
    for value, newvalue in mappings:
        doc.add(indent + 2, f"- value: '{value}'")
        doc.add(indent + 3, f'newvalue: {q(newvalue)}')


def emit_discovery_header(
    doc: Doc,
    *,
    uid_name: str,
    name: str,
    key: str,
    description: str,
    master_key: str,
) -> None:
    doc.add(4, '- uuid: ' + uid(uid_name))
    doc.add(5, f'name: {q(name)}')
    doc.add(5, 'type: DEPENDENT')
    doc.add(5, f'key: {key}')
    doc.add(5, "delay: '0'")
    doc.add(5, 'lifetime: 7d')
    doc.add(5, 'lifetime_type: DELETE_AFTER')
    doc.add(5, "enabled_lifetime: '0'")
    doc.add(5, 'enabled_lifetime_type: DISABLE_IMMEDIATELY')
    doc.add(5, f'description: {q(description)}')
    doc.add(5, 'master_item:')
    doc.add(6, f'key: {q(master_key)}')


def db_json(counter: str) -> str:
    return f"$[?(@.counter_name=='{counter}')].cntr_value.first()"


def emit_db_prototypes(doc: Doc) -> None:
    backup_ctx = '"{#DBNAME}"'
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Get last backup",
        BACKUP_RAW_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='TEXT',
        history='0',
        trends='0',
        master_key=BACKUP_KEY,
        description='Backup JSON for this named-instance database.',
        component='raw',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', "$[?(@.dbname=='{#DBNAME}')]", 'DISCARD_VALUE')],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Get performance counters",
        DB_PERF_RAW_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='TEXT',
        history='0',
        trends='0',
        master_key=PERF_KEY,
        description='Database perf counters for this named-instance database.',
        component='raw',
        extra_tags=DB_TAGS,
        steps=[
            (
                'JSONPATH',
                "$[?(@.object_name=~'.*Databases' && @.instance_name=='{#DBNAME}')]",
                'DISCARD_VALUE',
            )
        ],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Last diff backup duration",
        f'mssql.observability.backup.diff.duration[{{#MSSQL.INSTANCE}},{{#DBNAME}}]',
        item_type='DEPENDENT',
        delay='0',
        units='s',
        master_key=BACKUP_RAW_KEY,
        description='Duration of the last differential backup.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[
            ('JSONPATH', "$[?(@.type=='I')].duration.first()", 'CUSTOM_VALUE', '0'),
            ('DISCARD_UNCHANGED_HEARTBEAT', '12h'),
        ],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Last diff backup (time ago)",
        BACKUP_DIFF_KEY,
        item_type='DEPENDENT',
        delay='0',
        units='s',
        master_key=BACKUP_RAW_KEY,
        description='Time since the last differential backup.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', "$[?(@.type=='I')].time_since_last_backup.first()", 'CUSTOM_VALUE', '0')],
        trigger_section='trigger_prototypes',
        triggers=[
            {
                'name': "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Diff backup is old",
                'event_name': (
                    "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Diff backup older than "
                    f'{{$MSSQL.BACKUP_DIFF.CRIT:{backup_ctx}}}'
                ),
                'expression': BACKUP_DIFF_CRIT_EXPR,
                'priority': 'HIGH',
                'description': 'The differential backup has not been executed for a long time.',
                'manual_close': True,
                'opdata': BACKUP_OPDATA,
                'dependencies': [PING_DEP],
                'extra_tags': [('database', '{#DBNAME}'), ('sql_instance', '{#MSSQL.INSTANCE}')],
            },
            {
                'name': "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Diff backup is old",
                'event_name': (
                    "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Diff backup older than "
                    f'{{$MSSQL.BACKUP_DIFF.WARN:{backup_ctx}}}'
                ),
                'expression': BACKUP_DIFF_WARN_EXPR,
                'priority': 'WARNING',
                'description': 'The differential backup has not been executed for a long time.',
                'manual_close': True,
                'opdata': BACKUP_OPDATA,
                'dependencies': [
                    PING_DEP,
                    (
                        "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Diff backup is old",
                        BACKUP_DIFF_CRIT_EXPR,
                    ),
                ],
                'extra_tags': [('database', '{#DBNAME}'), ('sql_instance', '{#MSSQL.INSTANCE}')],
            },
        ],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Last full backup duration",
        f'mssql.observability.backup.full.duration[{{#MSSQL.INSTANCE}},{{#DBNAME}}]',
        item_type='DEPENDENT',
        delay='0',
        units='s',
        master_key=BACKUP_RAW_KEY,
        description='Duration of the last full backup.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[
            ('JSONPATH', "$[?(@.type=='D')].duration.first()", 'CUSTOM_VALUE', '0'),
            ('DISCARD_UNCHANGED_HEARTBEAT', '12h'),
        ],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Last full backup (time ago)",
        BACKUP_FULL_KEY,
        item_type='DEPENDENT',
        delay='0',
        units='s',
        master_key=BACKUP_RAW_KEY,
        description='Time since the last full backup.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', "$[?(@.type=='D')].time_since_last_backup.first()", 'CUSTOM_VALUE', '0')],
        trigger_section='trigger_prototypes',
        triggers=[
            {
                'name': "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Full backup is old",
                'event_name': (
                    "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Full backup older than "
                    f'{{$MSSQL.BACKUP_FULL.CRIT:{backup_ctx}}}'
                ),
                'expression': BACKUP_FULL_CRIT_EXPR,
                'priority': 'HIGH',
                'description': 'The full backup has not been executed for a long time.',
                'manual_close': True,
                'opdata': BACKUP_OPDATA,
                'dependencies': [PING_DEP],
                'extra_tags': [('database', '{#DBNAME}'), ('sql_instance', '{#MSSQL.INSTANCE}')],
            },
            {
                'name': "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Full backup is old",
                'event_name': (
                    "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Full backup older than "
                    f'{{$MSSQL.BACKUP_FULL.WARN:{backup_ctx}}}'
                ),
                'expression': BACKUP_FULL_WARN_EXPR,
                'priority': 'WARNING',
                'description': 'The full backup has not been executed for a long time.',
                'manual_close': True,
                'opdata': BACKUP_OPDATA,
                'dependencies': [
                    PING_DEP,
                    (
                        "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Full backup is old",
                        BACKUP_FULL_CRIT_EXPR,
                    ),
                ],
                'extra_tags': [('database', '{#DBNAME}'), ('sql_instance', '{#MSSQL.INSTANCE}')],
            },
        ],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Last log backup duration",
        f'mssql.observability.backup.log.duration[{{#MSSQL.INSTANCE}},{{#DBNAME}}]',
        item_type='DEPENDENT',
        delay='0',
        units='s',
        master_key=BACKUP_RAW_KEY,
        description='Duration of the last log backup.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[
            ('JSONPATH', "$[?(@.type=='L')].duration.first()", 'CUSTOM_VALUE', '0'),
            ('DISCARD_UNCHANGED_HEARTBEAT', '12h'),
        ],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Last log backup (time ago)",
        BACKUP_LOG_KEY,
        item_type='DEPENDENT',
        delay='0',
        units='s',
        master_key=BACKUP_RAW_KEY,
        description='Time since the last log backup.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', "$[?(@.type=='L')].time_since_last_backup.first()", 'CUSTOM_VALUE', '0')],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Recovery model",
        BACKUP_RECOVERY_KEY,
        item_type='DEPENDENT',
        delay='0',
        master_key=BACKUP_RAW_KEY,
        valuemap='MSSQL Recovery model',
        description='1 = Full, 2 = Bulk_logged, 3 = Simple.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[
            ('JSONPATH', '$[0].db_recovery_model', 'CUSTOM_VALUE', '1'),
            ('DISCARD_UNCHANGED_HEARTBEAT', '1d'),
        ],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Active transactions",
        f'mssql.observability.db.active_transactions[{{#MSSQL.INSTANCE}},{{#DBNAME}}]',
        item_type='DEPENDENT',
        delay='0',
        master_key=DB_PERF_RAW_KEY,
        description='Number of active transactions for the database.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', db_json('Active Transactions'))],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Data file size",
        f'mssql.observability.db.data_files_size[{{#MSSQL.INSTANCE}},{{#DBNAME}}]',
        item_type='DEPENDENT',
        delay='0',
        units='B',
        master_key=DB_PERF_RAW_KEY,
        description='Cumulative size of all data files including autogrowth.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', db_json('Data File(s) Size (KB)')), ('MULTIPLIER', '1024')],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Log bytes flushed per second",
        f'mssql.observability.db.log_bytes_flushed_sec.rate[{{#MSSQL.INSTANCE}},{{#DBNAME}}]',
        item_type='DEPENDENT',
        delay='0',
        value_type='FLOAT',
        units='Bps',
        master_key=DB_PERF_RAW_KEY,
        description='Log bytes flushed per second.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', db_json('Log Bytes Flushed/sec')), ('CHANGE_PER_SECOND',)],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Log file size",
        f'mssql.observability.db.log_files_size[{{#MSSQL.INSTANCE}},{{#DBNAME}}]',
        item_type='DEPENDENT',
        delay='0',
        units='B',
        master_key=DB_PERF_RAW_KEY,
        description='Cumulative size of all transaction log files.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', db_json('Log File(s) Size (KB)')), ('MULTIPLIER', '1024')],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Log file used size",
        f'mssql.observability.db.log_files_used_size[{{#MSSQL.INSTANCE}},{{#DBNAME}}]',
        item_type='DEPENDENT',
        delay='0',
        units='B',
        master_key=DB_PERF_RAW_KEY,
        description='Used size of all transaction log files.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', db_json('Log File(s) Used Size (KB)')), ('MULTIPLIER', '1024')],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Log flushes per second",
        f'mssql.observability.db.log_flushes_sec.rate[{{#MSSQL.INSTANCE}},{{#DBNAME}}]',
        item_type='DEPENDENT',
        delay='0',
        value_type='FLOAT',
        master_key=DB_PERF_RAW_KEY,
        description='Log flushes per second.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', db_json('Log Flushes/sec')), ('CHANGE_PER_SECOND',)],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Log flush waits per second",
        f'mssql.observability.db.log_flush_waits_sec.rate[{{#MSSQL.INSTANCE}},{{#DBNAME}}]',
        item_type='DEPENDENT',
        delay='0',
        value_type='FLOAT',
        master_key=DB_PERF_RAW_KEY,
        description='Commits per second waiting for the log flush.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', db_json('Log Flush Waits/sec')), ('CHANGE_PER_SECOND',)],
        trigger_section='trigger_prototypes',
        triggers=[
            {
                'name': (
                    "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': "
                    'Number of commits waiting for the log flush is high'
                ),
                'event_name': (
                    "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': "
                    'Number of commits waiting for the log flush is high '
                    f'(over {{$MSSQL.LOG_FLUSH_WAITS.MAX:{backup_ctx}}}/sec for 5m)'
                ),
                'expression': (
                    f'min(/{TEMPLATE_NAME}/'
                    f'mssql.observability.db.log_flush_waits_sec.rate[{{#MSSQL.INSTANCE}},{{#DBNAME}}]'
                    f',5m)>{{$MSSQL.LOG_FLUSH_WAITS.MAX:{backup_ctx}}}'
                ),
                'priority': 'WARNING',
                'description': 'Too many commits are waiting for the log flush.',
                'dependencies': [PING_DEP],
                'scope': 'performance',
                'extra_tags': [('database', '{#DBNAME}'), ('sql_instance', '{#MSSQL.INSTANCE}')],
            }
        ],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Log flush wait time",
        f'mssql.observability.db.log_flush_wait_time[{{#MSSQL.INSTANCE}},{{#DBNAME}}]',
        item_type='DEPENDENT',
        delay='0',
        value_type='FLOAT',
        units='ms',
        master_key=DB_PERF_RAW_KEY,
        description='Wait time to flush the log. On an AG secondary this is harden-to-disk wait.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', db_json('Log Flush Wait Time')), ('CHANGE_PER_SECOND',)],
        trigger_section='trigger_prototypes',
        triggers=[
            {
                'name': (
                    "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': "
                    'Total wait time to flush the log is high'
                ),
                'event_name': (
                    "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': "
                    'Total wait time to flush the log is high '
                    f'(over {{$MSSQL.LOG_FLUSH_WAIT_TIME.MAX:{backup_ctx}}}ms for 5m)'
                ),
                'expression': (
                    f'min(/{TEMPLATE_NAME}/'
                    f'mssql.observability.db.log_flush_wait_time[{{#MSSQL.INSTANCE}},{{#DBNAME}}]'
                    f',5m)>{{$MSSQL.LOG_FLUSH_WAIT_TIME.MAX:{backup_ctx}}}'
                ),
                'priority': 'WARNING',
                'description': 'The wait time to flush the log is too long.',
                'dependencies': [PING_DEP],
                'scope': 'performance',
                'extra_tags': [('database', '{#DBNAME}'), ('sql_instance', '{#MSSQL.INSTANCE}')],
            }
        ],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Log growths",
        f'mssql.observability.db.log_growths[{{#MSSQL.INSTANCE}},{{#DBNAME}}]',
        item_type='DEPENDENT',
        delay='0',
        master_key=DB_PERF_RAW_KEY,
        description='Times the transaction log has grown.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', db_json('Log Growths'))],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Log shrinks",
        f'mssql.observability.db.log_shrinks[{{#MSSQL.INSTANCE}},{{#DBNAME}}]',
        item_type='DEPENDENT',
        delay='0',
        master_key=DB_PERF_RAW_KEY,
        description='Times the transaction log has been shrunk.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', db_json('Log Shrinks'))],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Log truncations",
        f'mssql.observability.db.log_truncations[{{#MSSQL.INSTANCE}},{{#DBNAME}}]',
        item_type='DEPENDENT',
        delay='0',
        master_key=DB_PERF_RAW_KEY,
        description='Times the transaction log has been truncated.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', db_json('Log Truncations'))],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Percent log used",
        PERCENT_LOG_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='FLOAT',
        units='%',
        master_key=DB_PERF_RAW_KEY,
        description='Percentage of log space in use.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', db_json('Percent Log Used'))],
        trigger_section='trigger_prototypes',
        triggers=[
            {
                'name': "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Percent of log usage is high",
                'event_name': (
                    "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Percent of log usage is high "
                    f'(over {{$MSSQL.PERCENT_LOG_USED.MAX:{backup_ctx}}}% for 5m)'
                ),
                'expression': (
                    f'min(/{TEMPLATE_NAME}/{PERCENT_LOG_KEY},5m)>'
                    f'{{$MSSQL.PERCENT_LOG_USED.MAX:{backup_ctx}}}'
                ),
                'priority': 'WARNING',
                'description': "There's not enough space left in the log.",
                'dependencies': [PING_DEP],
                'scope': 'performance',
                'extra_tags': [('database', '{#DBNAME}'), ('sql_instance', '{#MSSQL.INSTANCE}')],
            }
        ],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': State",
        DB_STATE_KEY,
        item_type='DEPENDENT',
        delay='0',
        master_key=DB_PERF_RAW_KEY,
        valuemap='MSSQL DB state',
        description='0 = Online. Values above 1 are non-working states.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', db_json('State')), ('DISCARD_UNCHANGED_HEARTBEAT', '15m')],
        trigger_section='trigger_prototypes',
        triggers=[
            {
                'name': "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': State is {ITEM.VALUE}",
                'expression': f'last(/{TEMPLATE_NAME}/{DB_STATE_KEY})>1',
                'priority': 'HIGH',
                'description': 'The DB has a non-working state.',
                'dependencies': [PING_DEP],
                'extra_tags': [('database', '{#DBNAME}'), ('sql_instance', '{#MSSQL.INSTANCE}')],
            }
        ],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] DB '{#DBNAME}': Transactions per second",
        f'mssql.observability.db.transactions_sec.rate[{{#MSSQL.INSTANCE}},{{#DBNAME}}]',
        item_type='DEPENDENT',
        delay='0',
        value_type='FLOAT',
        master_key=DB_PERF_RAW_KEY,
        description='Transactions started for the database per second.',
        component='database',
        extra_tags=DB_TAGS,
        steps=[('JSONPATH', db_json('Transactions/sec')), ('CHANGE_PER_SECOND',)],
    )


def emit_local_db_prototypes(doc: Doc) -> None:
    local_path = (
        "$[?(@.dbname=='{#DBNAME}' && @.group_name=='{#GROUP_NAME}')]"
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] AG '{#GROUP_NAME}' Local DB '{#DBNAME}': Suspended",
        LOCAL_SUSPENDED_KEY,
        item_type='DEPENDENT',
        delay='0',
        master_key=LOCAL_DB_GET_KEY,
        description='0 = Resumed, 1 = Suspended.',
        component='local-db',
        extra_tags=LOCAL_TAGS,
        steps=[
            ('JSONPATH', f'{local_path}.is_suspended.first()'),
            ('DISCARD_UNCHANGED_HEARTBEAT', '1h'),
        ],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] AG '{#GROUP_NAME}' Local DB '{#DBNAME}': State",
        LOCAL_STATE_KEY,
        item_type='DEPENDENT',
        delay='0',
        master_key=LOCAL_DB_GET_KEY,
        valuemap='MSSQL DB state',
        description='Local availability database state (0 = Online).',
        component='local-db',
        extra_tags=LOCAL_TAGS,
        steps=[
            ('JSONPATH', f'{local_path}.database_state.first()'),
            ('DISCARD_UNCHANGED_HEARTBEAT', '1h'),
        ],
        trigger_section='trigger_prototypes',
        triggers=[
            {
                'name': (
                    "MSSQL [{#MSSQL.INSTANCE}]: AG '{#GROUP_NAME}' Local DB '{#DBNAME}': "
                    '"{#DBNAME}" is {ITEM.VALUE}'
                ),
                'expression': f'last(/{TEMPLATE_NAME}/{LOCAL_STATE_KEY})>0',
                'priority': 'WARNING',
                'description': 'The local availability database has a non-working state.',
                'dependencies': [PING_DEP],
                'extra_tags': [
                    ('availability-group', '{#GROUP_NAME}'),
                    ('local-db', '{#DBNAME}'),
                    ('sql_instance', '{#MSSQL.INSTANCE}'),
                ],
            }
        ],
    )
    emit_item(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}] AG '{#GROUP_NAME}' Local DB '{#DBNAME}': Synchronization health",
        LOCAL_SYNC_KEY,
        item_type='DEPENDENT',
        delay='0',
        master_key=LOCAL_DB_GET_KEY,
        valuemap='MSSQL AG Synchronization health',
        description='0 = Not healthy, 1 = Partially healthy, 2 = Healthy.',
        component='local-db',
        extra_tags=LOCAL_TAGS,
        steps=[
            ('JSONPATH', f'{local_path}.synchronization_health.first()'),
            ('DISCARD_UNCHANGED_HEARTBEAT', '1h'),
        ],
        trigger_section='trigger_prototypes',
        triggers=[
            {
                'name': (
                    "MSSQL [{#MSSQL.INSTANCE}]: AG '{#GROUP_NAME}' Local DB '{#DBNAME}': "
                    '"{#DBNAME}" is Not healthy'
                ),
                'expression': f'last(/{TEMPLATE_NAME}/{LOCAL_SYNC_KEY})=0',
                'priority': 'HIGH',
                'description': 'The local availability database is not synchronizing.',
                'dependencies': [PING_DEP],
                'extra_tags': [
                    ('availability-group', '{#GROUP_NAME}'),
                    ('local-db', '{#DBNAME}'),
                    ('sql_instance', '{#MSSQL.INSTANCE}'),
                ],
            },
            {
                'name': (
                    "MSSQL [{#MSSQL.INSTANCE}]: AG '{#GROUP_NAME}' Local DB '{#DBNAME}': "
                    '"{#DBNAME}" is Partially healthy'
                ),
                'expression': f'last(/{TEMPLATE_NAME}/{LOCAL_SYNC_KEY})=1',
                'priority': 'AVERAGE',
                'description': 'The local availability database is only partially healthy.',
                'dependencies': [PING_DEP],
                'extra_tags': [
                    ('availability-group', '{#GROUP_NAME}'),
                    ('local-db', '{#DBNAME}'),
                    ('sql_instance', '{#MSSQL.INSTANCE}'),
                ],
            },
        ],
    )


def emit_honeycomb(
    doc: Doc,
    name: str,
    items: str,
    label: str,
    *,
    y: str,
    reference: str,
    t0_color: str,
    t0: str,
    t1_color: str,
    t1: str,
) -> None:
    widget_xy(doc, 8, 'honeycomb', name, y=y, width='72', height='6')
    doc.add(9, 'fields:')
    field(doc, 10, 'STRING', 'items.0', items)
    field(doc, 10, 'STRING', 'primary_label', label)
    field(doc, 10, 'INTEGER', 'interpolation', '0')
    field(doc, 10, 'INTEGER', 'primary_label_bold', '1')
    field(doc, 10, 'INTEGER', 'primary_label_size_type', '1')
    field(doc, 10, 'INTEGER', 'primary_label_size', '20')
    field(doc, 10, 'INTEGER', 'show.0', '1')
    field(doc, 10, 'STRING', 'reference', reference)
    field(doc, 10, 'STRING', 'thresholds.0.color', t0_color)
    field(doc, 10, 'STRING', 'thresholds.0.threshold', t0)
    field(doc, 10, 'STRING', 'thresholds.1.color', t1_color)
    field(doc, 10, 'STRING', 'thresholds.1.threshold', t1)


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
            'Win32_Service rows matching MSSQL% (JS keeps MSSQL$ named instances). '
            'MSSQLSERVER and MSSQLFDLauncher are dropped. Not-supported becomes empty LLD.'
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
        value_type='UNSIGNED',
        description='Count of named MSSQL$ instances from WMI after JS (before LLD filters).',
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
    emit_item(
        doc,
        3,
        'Named-instance database catalog seed',
        DB_CATALOG_SEED_KEY,
        item_type='CALCULATED',
        delay='1h',
        value_type='TEXT',
        history='0',
        trends='0',
        params='"[]"',
        description='Keeps last_foreach of database catalogs from going unsupported when LLD is empty.',
        component='raw',
        extra_tags=[('mssql_seed', 'seed')],
    )
    emit_item(
        doc,
        3,
        'Named-instance database LLD JSON',
        DB_LLDJSON_KEY,
        item_type='CALCULATED',
        delay='5m',
        value_type='TEXT',
        history='0',
        trends='0',
        params=DB_FOREACH_FORMULA,
        description=(
            'Flattened {#MSSQL.INSTANCE}+{#DBNAME} catalog from every named-instance db.get. '
            'Zabbix 7.0 cannot nest database LLD under instance LLD.'
        ),
        component='raw',
        steps=[
            ('JAVASCRIPT', FLATTEN_LLD_JS),
            ('DISCARD_UNCHANGED_HEARTBEAT', '1h'),
        ],
    )
    emit_item(
        doc,
        3,
        'Named-instance AG local-DB catalog seed',
        LOCAL_CATALOG_SEED_KEY,
        item_type='CALCULATED',
        delay='1h',
        value_type='TEXT',
        history='0',
        trends='0',
        params='"[]"',
        description='Keeps last_foreach of AG local-DB catalogs from going unsupported when LLD is empty.',
        component='raw',
        extra_tags=[('mssql_seed', 'seed')],
    )
    emit_item(
        doc,
        3,
        'Named-instance AG local-DB LLD JSON',
        LOCAL_LLDJSON_KEY,
        item_type='CALCULATED',
        delay='5m',
        value_type='TEXT',
        history='0',
        trends='0',
        params=LOCAL_FOREACH_FORMULA,
        description='Flattened {#MSSQL.INSTANCE}+{#GROUP_NAME}+{#DBNAME} catalog from local.db.get.',
        component='raw',
        steps=[
            ('JAVASCRIPT', FLATTEN_LLD_JS),
            ('DISCARD_UNCHANGED_HEARTBEAT', '1h'),
        ],
    )

    doc.add(3, 'discovery_rules:')
    emit_discovery_header(
        doc,
        uid_name='discovery:named-instance',
        name='Named instance discovery',
        key=DISCOVERY_KEY,
        description='Named SQL Server instances (MSSQL$*). Default instance is stock.',
        master_key=WMI_ITEM_KEY,
    )
    emit_filter_pair(
        doc,
        5,
        '{#MSSQL.INSTANCE}',
        MACRO_INSTANCE_MATCHES,
        MACRO_INSTANCE_NOT_MATCHES,
    )
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
        steps=[('CHECK_NOT_SUPPORTED', '-1', '0')],
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
        delay='5m',
        value_type='CHAR',
        trends='0',
        timeout='30s',
        description='SQL Server version string for this named instance. Delay 5m so nodata 15m is three misses.',
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
        description='Perfcounter master for this named instance (same interval as stock).',
        component='raw',
        extra_tags=INSTANCE_TAGS,
        steps=[('CHECK_NOT_SUPPORTED', '-1', '[]')],
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
        description='SQL Agent job status JSON for this named instance.',
        component='raw',
        extra_tags=INSTANCE_TAGS,
        steps=[('CHECK_NOT_SUPPORTED', '-1', '[]')],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Failed jobs',
        FAILED_JOBS_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='UNSIGNED',
        master_key=JOB_KEY,
        description='Jobs whose last run_status is Failed (0).',
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
        history='7d',
        trends='0',
        timeout='30s',
        description='Last-backup JSON for this named instance. Per-database age is flattened LLD.',
        component='raw',
        extra_tags=INSTANCE_TAGS,
        steps=[('CHECK_NOT_SUPPORTED', '-1', '[]')],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Get database',
        DB_KEY,
        delay='10m',
        value_type='TEXT',
        history='7d',
        trends='0',
        timeout='30s',
        description='Database JSON for this named instance. Feeds flattened database LLD.',
        component='raw',
        extra_tags=INSTANCE_TAGS,
        steps=[('CHECK_NOT_SUPPORTED', '-1', '[]')],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Database catalog',
        DB_CATALOG_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='TEXT',
        history='0',
        trends='0',
        master_key=DB_KEY,
        description='LLD rows for this instance stamped with {#MSSQL.INSTANCE} and {#MSSQL.URI}.',
        component='raw',
        extra_tags=INSTANCE_TAGS,
        steps=[
            ('JAVASCRIPT', DB_CATALOG_JS),
            ('DISCARD_UNCHANGED_HEARTBEAT', '1h'),
        ],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Database count',
        DB_COUNT_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='UNSIGNED',
        master_key=DB_KEY,
        description='What SQL returned (includes system DBs). User-DB visibility is flattened LLD.',
        component='application',
        extra_tags=INSTANCE_TAGS,
        steps=[('JSONPATH', '$.length()', 'CUSTOM_VALUE', '0')],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Get availability groups',
        AG_GET_KEY,
        delay='5m',
        value_type='TEXT',
        history='0',
        trends='0',
        timeout='30s',
        description='Availability-group JSON for this named instance.',
        component='raw',
        extra_tags=INSTANCE_TAGS,
        steps=[('CHECK_NOT_SUPPORTED', '-1', '[]')],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: Get local DB',
        LOCAL_DB_GET_KEY,
        delay='5m',
        value_type='TEXT',
        history='0',
        trends='0',
        timeout='30s',
        description='Always On local-database JSON for this named instance. Feeds flattened AG LLD.',
        component='raw',
        extra_tags=INSTANCE_TAGS,
        steps=[('CHECK_NOT_SUPPORTED', '-1', '[]')],
    )
    emit_item(
        doc,
        6,
        'MSSQL [{#MSSQL.INSTANCE}]: AG local-DB catalog',
        LOCAL_CATALOG_KEY,
        item_type='DEPENDENT',
        delay='0',
        value_type='TEXT',
        history='0',
        trends='0',
        master_key=LOCAL_DB_GET_KEY,
        description='AG local-DB LLD rows stamped with instance, group, and database.',
        component='raw',
        extra_tags=INSTANCE_TAGS,
        steps=[
            ('JAVASCRIPT', LOCAL_DB_CATALOG_JS),
            ('DISCARD_UNCHANGED_HEARTBEAT', '1h'),
        ],
    )

    emit_discovery_header(
        doc,
        uid_name='discovery:named-database',
        name='Named instance database discovery',
        key=DB_LLD_KEY,
        description=(
            'User databases on every named instance. Flattened from mssql.db.get catalogs. '
            'System DBs filtered by {$MSSQL.DBNAME.NOT_MATCHES} (not an environment mute).'
        ),
        master_key=DB_LLDJSON_KEY,
    )
    emit_filter_pair(doc, 5, '{#DBNAME}', MACRO_DBNAME_MATCHES, MACRO_DBNAME_NOT_MATCHES)
    doc.add(5, 'item_prototypes:')
    emit_db_prototypes(doc)
    doc.add(5, 'trigger_prototypes:')
    trig(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Log backup is old",
        BACKUP_LOG_CRIT_EXPR,
        'HIGH',
        'The log backup has not been executed for a long time.',
        event_name=(
            "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Log backup older than "
            '{$MSSQL.BACKUP_LOG.CRIT:"{#DBNAME}"}'
        ),
        opdata=BACKUP_OPDATA,
        manual_close=True,
        dependencies=[PING_DEP],
        extra_tags=[('database', '{#DBNAME}'), ('sql_instance', '{#MSSQL.INSTANCE}')],
    )
    trig(
        doc,
        6,
        "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Log backup is old",
        BACKUP_LOG_WARN_EXPR,
        'WARNING',
        'The log backup has not been executed for a long time.',
        event_name=(
            "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Log backup older than "
            '{$MSSQL.BACKUP_LOG.WARN:"{#DBNAME}"}'
        ),
        opdata=BACKUP_OPDATA,
        manual_close=True,
        dependencies=[
            PING_DEP,
            (
                "MSSQL [{#MSSQL.INSTANCE}]: DB '{#DBNAME}': Log backup is old",
                BACKUP_LOG_CRIT_EXPR,
            ),
        ],
        extra_tags=[('database', '{#DBNAME}'), ('sql_instance', '{#MSSQL.INSTANCE}')],
    )
    doc.add(5, 'overrides:')
    doc.add(6, '- name: Log backup')
    doc.add(7, "step: '1'")
    doc.add(7, 'filter:')
    doc.add(8, 'conditions:')
    doc.add(9, "- macro: '{#RECOVERY_MODEL}'")
    doc.add(10, "value: '3'")
    doc.add(10, 'formulaid: A')
    doc.add(7, 'operations:')
    doc.add(8, '- operationobject: TRIGGER_PROTOTYPE')
    doc.add(9, 'operator: LIKE')
    doc.add(9, 'value: Log backup is old')
    doc.add(9, 'discover: NO_DISCOVER')

    emit_discovery_header(
        doc,
        uid_name='discovery:named-local-db',
        name='Named instance AG local database discovery',
        key=LOCAL_LLD_KEY,
        description=(
            'Always On local databases on every named instance. Flattened from mssql.local.db.get.'
        ),
        master_key=LOCAL_LLDJSON_KEY,
    )
    doc.add(5, 'item_prototypes:')
    emit_local_db_prototypes(doc)

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
    emit_honeycomb(
        doc,
        'Ping',
        'MSSQL [*]: Ping',
        '{{ITEM.NAME}.regsub("^MSSQL \\[(.*)\\]: Ping$","\\1")}',
        y='4',
        reference='MSSQLPNG',
        t0_color='FF465C',
        t0='0',
        t1_color='0EC9AC',
        t1='1',
    )
    doc.add(6, '- name: Databases')
    doc.add(7, 'widgets:')
    emit_honeycomb(
        doc,
        'Database state',
        "MSSQL [*] DB *: State",
        '{{ITEM.NAME}.regsub("^MSSQL \\[(.*)\\] DB \'(.*)\': State$","\\1 / \\2")}',
        y='0',
        reference='MSSQLDBS',
        t0_color='0EC9AC',
        t0='0',
        t1_color='FF465C',
        t1='2',
    )
    emit_honeycomb(
        doc,
        'AG local DB sync',
        'MSSQL [*] AG * Local DB *: Synchronization health',
        '{{ITEM.NAME}.regsub("^MSSQL \\[(.*)\\] AG \'(.*)\' Local DB \'(.*)\': Synchronization health$","\\1 / \\3")}',
        y='6',
        reference='MSSQLAGD',
        t0_color='FF465C',
        t0='0',
        t1_color='0EC9AC',
        t1='2',
    )

    doc.add(3, 'valuemaps:')
    emit_valuemap(
        doc,
        4,
        'Service state',
        [('0', 'Down'), ('1', 'Up')],
    )
    emit_valuemap(
        doc,
        4,
        'MSSQL DB state',
        [
            ('0', 'ONLINE'),
            ('1', 'RESTORING'),
            ('2', 'RECOVERING'),
            ('3', 'RECOVERY_PENDING'),
            ('4', 'SUSPECT'),
            ('5', 'EMERGENCY'),
            ('6', 'OFFLINE'),
            ('7', 'COPYING'),
            ('10', 'OFFLINE_SECONDARY'),
        ],
    )
    emit_valuemap(
        doc,
        4,
        'MSSQL Recovery model',
        [('1', 'FULL'), ('2', 'BULK_LOGGED'), ('3', 'SIMPLE')],
    )
    emit_valuemap(
        doc,
        4,
        'MSSQL AG Synchronization health',
        [('0', 'Not healthy'), ('1', 'Partially healthy'), ('2', 'Healthy')],
    )
    return doc


def main() -> int:
    build().dump(ZABBIX_TEMPLATE_PATH)
    print(f'wrote {ZABBIX_TEMPLATE_PATH}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
