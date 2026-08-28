#!/usr/bin/env python3
"""ExtremeControl by SNMP contract (ENTERASYS-NAC-APPLIANCE-MIB, live canary)."""

from __future__ import annotations

import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / 'zabbix/templates/extremecontrol_snmp'
JS_DIR = TEMPLATE_DIR / 'js'
FIXTURES = TEMPLATE_DIR / 'fixtures'
SNMP_YAML = TEMPLATE_DIR / 'template_net_extremecontrol_snmp.yaml'
MIB_PATH = ROOT / 'zabbix/mibs/enterasys-nac-appliance-mib.txt'

SNMP_TEMPLATE_NAME = 'ExtremeControl by SNMP'
TEMPLATE_GROUP = 'Templates/Network devices'
GROUP_UUID = '36bff6c29af64692839d077febfc7079'
OID_BASE = '1.3.6.1.4.1.5624.1.2.73.1'
TPL = SNMP_TEMPLATE_NAME
_NS = uuid.UUID('3e7c0a11-57d2-4c8b-9e01-a1b2c3d4e5f6')


def uid(*parts: str) -> str:
    return uuid.uuid5(_NS, '|'.join(parts)).hex


# Live walk 2026-08-28 from NetBox Dev (MONITORING MD5/DES): five ENACs, all 16
# Counter64 scalars under .73.1.1.0 .. .73.1.16.0. contact.lost and
# connected.agents were 0 on every engine (gauge-like despite Counter64).
APPL = (
    ('auth.requests', 'etsysNacApplAuthenticationRequests', 1, 'Authentication requests', True),
    ('auth.successes', 'etsysNacApplAuthenticationSuccesses', 2, 'Authentication successes', True),
    ('auth.failures', 'etsysNacApplAuthenticationFailures', 3, 'Authentication failures', True),
    ('auth.challenges', 'etsysNacApplRadiusChallenges', 4, 'RADIUS challenges', True),
    ('auth.invalid', 'etsysNacApplAuthenticationInvalidRequests', 5, 'Invalid authentication requests', True),
    ('auth.duplicate', 'etsysNacApplAuthenticationDuplicateRequests', 6, 'Duplicate authentication requests', True),
    ('auth.malformed', 'etsysNacApplAuthenticationMalformedRequests', 7, 'Malformed authentication requests', True),
    ('auth.bad', 'etsysNacApplAuthenticationBadRequests', 8, 'Bad authentication requests', True),
    ('auth.dropped', 'etsysNacApplAuthenticationDroppedPackets', 9, 'Dropped authentication packets', True),
    ('auth.unknown', 'etsysNacApplAuthenticationUnknownTypes', 10, 'Unknown authentication types', True),
    ('assessment', 'etsysNacApplAssessmentRequests', 11, 'Assessment requests', True),
    ('captive.portal', 'etsysNacApplCaptivePortalRequests', 12, 'Captive portal requests', True),
    ('contact.lost', 'etsysNacApplContactLostSwitches', 13, 'Contact-lost switches', False),
    ('ip.res.failures', 'etsysNacApplIPResolutionFailures', 14, 'IP resolution failures', True),
    ('ip.res.timeouts', 'etsysNacApplIPResolutionTimeouts', 15, 'IP resolution timeouts', True),
    ('connected.agents', 'etsysNacApplConnectedAgents', 16, 'Connected assessment agents', False),
)

APPL_KEYS = {f'nac.appl.{key}' for key, *_ in APPL}
APPL_RATE_KEYS = {f'nac.appl.{key}.rate' for key, *_, rate in APPL if rate}

SNMP_ITEM_KEYS = {
    'zabbix[host,snmp,available]',
    'zabbix[host,,items_unsupported]',
    'nac.snmp.available',
    'system.name',
    'system.descr',
    'system.objectid[sysObjectID.0]',
    'nac.snmp.product',
    'nac.snmp.identity',
    'system.net.uptime[sysUpTime.0]',
    'nac.appl.auth.fail.pct',
    *APPL_KEYS,
    *APPL_RATE_KEYS,
}

SNMP_TRIGGER_NAMES = {
    'ExtremeControl SNMP: No SNMP data collection',
    'ExtremeControl SNMP: Too many unsupported items',
    'ExtremeControl SNMP: Host has been restarted',
    'ExtremeControl SNMP: System name has changed',
    'ExtremeControl SNMP: contact-lost switches',
    'ExtremeControl SNMP: authentication failure ratio high',
}

FORBIDDEN_SNIPPETS = (
    'icmpping',
    'net.udp.service',
    'mutation',
    'enforceNacEnginesAll',
    'verify=False',
    '{HOST.HOST}',
    '{HOST.CONN}',
    '1.3.6.1.4.1.1916.1',
    'net.if.discovery',
)


class Doc:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def add(self, indent: int, text: str) -> None:
        if text == '':
            self.lines.append('')
            return
        self.lines.append(('  ' * indent) + text)

    def literal(self, indent: int, text: str) -> None:
        for line in text.replace('\r\n', '\n').split('\n'):
            self.add(indent, line)

    def dumps(self) -> str:
        return '\n'.join(self.lines) + '\n'


def q(value: str) -> str:
    if value == '' or any(ch in value for ch in ":{}[]#&*?|>!%@`'\" ,") or value.startswith('{'):
        return "'" + value.replace("'", "''") + "'"
    return value


def product_js() -> str:
    body = (JS_DIR / 'classify_product.js').read_text(encoding='utf-8').rstrip()
    return body + '\n\nreturn classifyControlProduct(value);\n'


def identity_js() -> str:
    body = (JS_DIR / 'classify_product.js').read_text(encoding='utf-8').rstrip()
    return body + '\n\nreturn controlProductIdentity(value);\n'


def tags(doc: Doc, indent: int, component: str) -> None:
    doc.add(indent, 'tags:')
    doc.add(indent + 1, '- tag: component')
    doc.add(indent + 2, f'value: {component}')


def dep_snmp(doc: Doc, indent: int) -> None:
    doc.add(indent, 'dependencies:')
    doc.add(indent + 1, f'- name: {q("ExtremeControl SNMP: No SNMP data collection")}')
    doc.add(
        indent + 2,
        f'expression: max(/{TPL}/zabbix[host,snmp,available],' + '{$SNMP.TIMEOUT})=0',
    )


def scope(doc: Doc, indent: int, value: str) -> None:
    doc.add(indent, 'tags:')
    doc.add(indent + 1, '- tag: scope')
    doc.add(indent + 2, f'value: {value}')


def item_field(doc: Doc, indent: int, key: str, x: int | None, y: int | None, width: int, ref: str, name: str) -> None:
    doc.add(indent, '- type: item')
    doc.add(indent + 1, f'name: {name}')
    if x:
        doc.add(indent + 1, f'x: {x!r}')
    if y:
        doc.add(indent + 1, f'y: {y!r}')
    doc.add(indent + 1, f'width: {width!r}')
    doc.add(indent + 1, "height: '4'")
    doc.add(indent + 1, 'fields:')
    doc.add(indent + 2, '- type: ITEM')
    doc.add(indent + 3, 'name: itemid.0')
    doc.add(indent + 3, 'value:')
    doc.add(indent + 4, f'host: {TPL}')
    doc.add(indent + 4, f'key: {q(key)}')
    doc.add(indent + 2, '- type: INTEGER')
    doc.add(indent + 3, 'name: show.0')
    doc.add(indent + 3, "value: '2'")
    doc.add(indent + 2, '- type: INTEGER')
    doc.add(indent + 3, 'name: value_bold')
    doc.add(indent + 3, "value: '1'")
    doc.add(indent + 2, '- type: INTEGER')
    doc.add(indent + 3, 'name: value_size')
    doc.add(indent + 3, "value: '28'")
    doc.add(indent + 2, '- type: STRING')
    doc.add(indent + 3, 'name: reference')
    doc.add(indent + 3, f'value: {ref}')


def svg_graph(
    doc: Doc,
    indent: int,
    name: str,
    series: list[tuple[str, str]],
    *,
    x: int = 0,
    y: int = 0,
    width: int = 36,
    ref: str,
) -> None:
    doc.add(indent, '- type: svggraph')
    doc.add(indent + 1, f'name: {name}')
    if x:
        doc.add(indent + 1, f'x: {x!r}')
    if y:
        doc.add(indent + 1, f'y: {y!r}')
    doc.add(indent + 1, f'width: {width!r}')
    doc.add(indent + 1, "height: '6'")
    doc.add(indent + 1, 'fields:')
    doc.add(indent + 2, '- type: INTEGER')
    doc.add(indent + 3, 'name: ds.0.dataset_type')
    doc.add(indent + 3, "value: '0'")
    for idx, (color, key) in enumerate(series):
        doc.add(indent + 2, '- type: STRING')
        doc.add(indent + 3, f'name: ds.0.color.{idx}')
        doc.add(indent + 3, f'value: {color}')
        doc.add(indent + 2, '- type: ITEM')
        doc.add(indent + 3, f'name: ds.0.itemids.{idx}')
        doc.add(indent + 3, 'value:')
        doc.add(indent + 4, f'host: {TPL}')
        doc.add(indent + 4, f'key: {q(key)}')
    doc.add(indent + 2, '- type: STRING')
    doc.add(indent + 3, 'name: reference')
    doc.add(indent + 3, f'value: {ref}')
    doc.add(indent + 2, '- type: INTEGER')
    doc.add(indent + 3, 'name: show_problems')
    doc.add(indent + 3, "value: '1'")
    doc.add(indent + 2, '- type: INTEGER')
    doc.add(indent + 3, 'name: legend')
    doc.add(indent + 3, "value: '1'")
    doc.add(indent + 2, '- type: STRING')
    doc.add(indent + 3, 'name: time_period.from')
    doc.add(indent + 3, 'value: now-1d')
    doc.add(indent + 2, '- type: STRING')
    doc.add(indent + 3, 'name: time_period.to')
    doc.add(indent + 3, 'value: now')


def render() -> str:
    doc = Doc()
    doc.add(0, 'zabbix_export:')
    doc.add(1, "version: '7.0'")
    doc.add(1, 'template_groups:')
    doc.add(2, f'- uuid: {GROUP_UUID}')
    doc.add(3, f'name: {TEMPLATE_GROUP}')
    doc.add(1, 'templates:')
    doc.add(2, f'- uuid: {uid("template")}')
    doc.add(3, f'template: {TPL}')
    doc.add(3, f'name: {TPL}')
    doc.add(3, 'description: |')
    doc.literal(
        4,
        """ExtremeControl / IA-V engine via SNMP. MIB: ENTERASYS-NAC-APPLIANCE-MIB
(etsysModules 73, 1.3.6.1.4.1.5624.1.2.73). Canary 2026-08-28: all five
ENACs answered 16 Counter64 scalars with the switch MONITORING SNMPv3
profile (MD5/DES).

Does not nest ICMP (06 / existing ping owns it). Does not speak RADIUS
UDP. Does not clone EXOS/VOSS/IQ templates. License seats stay on
XIQ-SE Observability GraphQL.

Operator page: zabbix/07-extreme-control.md.
OIDs: templates/extremecontrol_snmp/OID_MAPPING.md.
Refresh with configure_nbxsync_network.py --apply-xiqse.""",
    )
    doc.add(3, 'groups:')
    doc.add(4, f'- name: {TEMPLATE_GROUP}')
    doc.add(3, 'macros:')
    for macro, value, descr in (
        ('{$SNMP.TIMEOUT}', '5m', 'Time interval for the SNMP availability trigger.'),
        ('{$UNSUPPORTED.MAX}', '1', 'Average when unsupported items stay above this for 30m.'),
        (
            '{$NAC.SNMP.CONTACTLOST.CONTROL}',
            '0',
            'Ticket contact-lost switches > 0. Default off until the Counter64-as-gauge reading is trusted.',
        ),
        (
            '{$NAC.SNMP.FAIL.WARN}',
            '101',
            'Decided-auth failure % Warning. 101 silences until a quiet baseline.',
        ),
    ):
        doc.add(4, f'- macro: {q(macro)}')
        doc.add(5, f"value: '{value}'")
        doc.add(5, f'description: {descr}')
    doc.add(3, 'items:')

    # SNMP availability
    doc.add(4, f'- uuid: {uid("item", "snmp")}')
    doc.add(5, 'name: SNMP agent availability')
    doc.add(5, 'type: INTERNAL')
    doc.add(5, "key: 'zabbix[host,snmp,available]'")
    doc.add(5, 'description: |')
    doc.literal(6, '0 not available, 1 available, 2 unknown. Mgmt blind; RADIUS may still work.')
    doc.add(5, 'valuemap:')
    doc.add(6, 'name: zabbix.host.available')
    tags(doc, 5, 'health')
    doc.add(5, 'triggers:')
    doc.add(6, f'- uuid: {uid("tr", "snmp")}')
    doc.add(7, 'expression: max(/' + TPL + '/zabbix[host,snmp,available],{$SNMP.TIMEOUT})=0')
    doc.add(7, f'name: {q("ExtremeControl SNMP: No SNMP data collection")}')
    doc.add(7, f'event_name: {q("ExtremeControl SNMP: No SNMP data collection")}')
    doc.add(7, 'priority: WARNING')
    doc.add(7, 'description: |')
    doc.literal(
        8,
        """Mgmt blind; 802.1X may still work. ICMP High from 06 is the page
if the box is gone. Same SNMPv3 profile as switches (MONITORING).""",
    )
    scope(doc, 7, 'availability')

    doc.add(4, f'- uuid: {uid("item", "unsup")}')
    doc.add(5, 'name: Unsupported item count')
    doc.add(5, 'type: INTERNAL')
    doc.add(5, "key: 'zabbix[host,,items_unsupported]'")
    doc.add(5, 'delay: 15m')
    doc.add(5, 'description: Watch the watcher — the 16 canary OIDs must not go silent.')
    tags(doc, 5, 'health')
    doc.add(5, 'triggers:')
    doc.add(6, f'- uuid: {uid("tr", "unsup")}')
    doc.add(7, 'expression: min(/' + TPL + '/zabbix[host,,items_unsupported],30m)>{$UNSUPPORTED.MAX}')
    doc.add(7, f'name: {q("ExtremeControl SNMP: Too many unsupported items")}')
    doc.add(7, f'event_name: {q("ExtremeControl SNMP: Too many unsupported items")}')
    doc.add(7, 'priority: AVERAGE')
    doc.add(7, 'description: SNMP=1 but items unsupported — view/OID mismatch, not a cable.')
    dep_snmp(doc, 7)
    scope(doc, 7, 'availability')

    doc.add(4, f'- uuid: {uid("item", "snmp.hl")}')
    doc.add(5, 'name: SNMP')
    doc.add(5, 'type: CALCULATED')
    doc.add(5, 'key: nac.snmp.available')
    doc.add(5, 'delay: 1m')
    doc.add(5, 'value_type: FLOAT')
    doc.add(5, "params: 'last(//zabbix[host,snmp,available])'")
    doc.add(5, 'description: Headline SNMP for the Overview tile.')
    doc.add(5, 'valuemap:')
    doc.add(6, 'name: zabbix.host.available')
    tags(doc, 5, 'health')

    doc.add(4, f'- uuid: {uid("item", "sysname")}')
    doc.add(5, 'name: System name')
    doc.add(5, 'type: SNMP_AGENT')
    doc.add(5, 'snmp_oid: 1.3.6.1.2.1.1.5.0')
    doc.add(5, 'key: system.name')
    doc.add(5, 'delay: 1h')
    doc.add(5, 'value_type: CHAR')
    doc.add(5, 'history: 7d')
    doc.add(5, "trends: '0'")
    doc.add(5, 'inventory_link: NAME')
    doc.add(5, 'preprocessing:')
    doc.add(6, '- type: DISCARD_UNCHANGED_HEARTBEAT')
    doc.add(7, 'parameters:')
    doc.add(8, '- 6h')
    tags(doc, 5, 'system')
    doc.add(5, 'triggers:')
    doc.add(6, f'- uuid: {uid("tr", "sysname")}')
    doc.add(
        7,
        f'expression: last(/{TPL}/system.name,#1)<>last(/{TPL}/system.name,#2) and length(last(/{TPL}/system.name))>0',
    )
    doc.add(7, f'name: {q("ExtremeControl SNMP: System name has changed")}')
    doc.add(7, f'event_name: {q("ExtremeControl SNMP: System name has changed")}')
    doc.add(7, 'priority: INFO')
    doc.add(7, 'description: Possible replacement or rename. Acknowledge to close.')
    doc.add(7, "manual_close: 'YES'")
    scope(doc, 7, 'notice')

    doc.add(4, f'- uuid: {uid("item", "sysdescr")}')
    doc.add(5, 'name: System description')
    doc.add(5, 'type: SNMP_AGENT')
    doc.add(5, 'snmp_oid: 1.3.6.1.2.1.1.1.0')
    doc.add(5, 'key: system.descr')
    doc.add(5, 'delay: 1h')
    doc.add(5, 'value_type: CHAR')
    doc.add(5, 'history: 7d')
    doc.add(5, "trends: '0'")
    doc.add(5, 'inventory_link: TYPE')
    doc.add(5, 'preprocessing:')
    doc.add(6, '- type: DISCARD_UNCHANGED_HEARTBEAT')
    doc.add(7, 'parameters:')
    doc.add(8, '- 6h')
    tags(doc, 5, 'system')

    doc.add(4, f'- uuid: {uid("item", "sysoid")}')
    doc.add(5, 'name: System object ID')
    doc.add(5, 'type: SNMP_AGENT')
    doc.add(5, 'snmp_oid: 1.3.6.1.2.1.1.2.0')
    doc.add(5, "key: 'system.objectid[sysObjectID.0]'")
    doc.add(5, 'delay: 1h')
    doc.add(5, 'value_type: CHAR')
    doc.add(5, 'history: 7d')
    doc.add(5, "trends: '0'")
    doc.add(5, 'description: |')
    doc.literal(
        6,
        """IA-V is 1.3.6.1.4.1.1916.2.252 when Extreme set sysObjectID.
Stock net-snmp Linux is 1.3.6.1.4.1.8072.3.2.10 — still a Control
engine if ENTERASYS-NAC-APPLIANCE-MIB answers.""",
    )
    tags(doc, 5, 'system')

    doc.add(4, f'- uuid: {uid("item", "product")}')
    doc.add(5, 'name: ExtremeControl product')
    doc.add(5, 'type: DEPENDENT')
    doc.add(5, 'key: nac.snmp.product')
    doc.add(5, "delay: '0'")
    doc.add(5, 'history: 7d')
    doc.add(5, "trends: '0'")
    doc.add(5, 'value_type: CHAR')
    doc.add(5, 'preprocessing:')
    doc.add(6, '- type: JAVASCRIPT')
    doc.add(7, 'parameters:')
    doc.add(8, '- |')
    doc.literal(10, product_js())
    doc.add(5, 'master_item:')
    doc.add(6, "key: 'system.objectid[sysObjectID.0]'")
    tags(doc, 5, 'system')

    doc.add(4, f'- uuid: {uid("item", "identity")}')
    doc.add(5, 'name: ExtremeControl product identity')
    doc.add(5, 'type: DEPENDENT')
    doc.add(5, 'key: nac.snmp.identity')
    doc.add(5, "delay: '0'")
    doc.add(5, 'history: 7d')
    doc.add(5, 'trends: 365d')
    doc.add(5, 'value_type: UNSIGNED')
    doc.add(
        5,
        'description: 1 when sysObjectID is an Extreme Access Control product. 0 for net-snmp Linux is OK.',
    )
    doc.add(5, 'valuemap:')
    doc.add(6, 'name: ExtremeControl identity')
    doc.add(5, 'preprocessing:')
    doc.add(6, '- type: JAVASCRIPT')
    doc.add(7, 'parameters:')
    doc.add(8, '- |')
    doc.literal(10, identity_js())
    doc.add(5, 'master_item:')
    doc.add(6, "key: 'system.objectid[sysObjectID.0]'")
    tags(doc, 5, 'system')

    doc.add(4, f'- uuid: {uid("item", "uptime")}')
    doc.add(5, 'name: Uptime (network)')
    doc.add(5, 'type: SNMP_AGENT')
    doc.add(5, "snmp_oid: 'get[1.3.6.1.2.1.1.3.0]'")
    doc.add(5, "key: 'system.net.uptime[sysUpTime.0]'")
    doc.add(5, 'delay: 1m')
    doc.add(5, "trends: '0'")
    doc.add(5, 'units: uptime')
    doc.add(5, 'description: SNMPv2-MIB sysUpTime.')
    doc.add(5, 'preprocessing:')
    doc.add(6, '- type: MULTIPLIER')
    doc.add(7, 'parameters:')
    doc.add(8, "- '0.01'")
    tags(doc, 5, 'system')
    doc.add(5, 'triggers:')
    doc.add(6, f'- uuid: {uid("tr", "reboot")}')
    doc.add(7, f'expression: last(/{TPL}/system.net.uptime[sysUpTime.0])<10m')
    doc.add(7, f'name: {q("ExtremeControl SNMP: Host has been restarted")}')
    doc.add(7, f'event_name: {q("ExtremeControl SNMP: Host has been restarted")}')
    doc.add(7, 'priority: WARNING')
    doc.add(7, 'description: sysUpTime under 10 minutes. Next day, not a page.')
    dep_snmp(doc, 7)
    scope(doc, 7, 'notice')

    for key, mib, index, title, rate in APPL:
        oid = f'{OID_BASE}.{index}.0'
        item_key = f'nac.appl.{key}'
        doc.add(4, f'- uuid: {uid("item", key)}')
        doc.add(5, f'name: ExtremeControl {title}')
        doc.add(5, 'type: SNMP_AGENT')
        doc.add(5, f'snmp_oid: {oid}')
        doc.add(5, f'key: {item_key}')
        doc.add(5, 'delay: 1m')
        doc.add(5, 'history: 7d')
        doc.add(5, 'trends: 365d')
        doc.add(5, 'value_type: UNSIGNED')
        doc.add(5, 'description: |')
        doc.literal(
            6,
            f"""MIB: {mib} ({oid}).
ENTERASYS-NAC-APPLIANCE-MIB. Live on five ENACs 2026-08-28.""",
        )
        tags(doc, 5, 'nac')
        if key == 'contact.lost':
            doc.add(5, 'triggers:')
            doc.add(6, f'- uuid: {uid("tr", "contact")}')
            doc.add(
                7,
                'expression: \'{$NAC.SNMP.CONTACTLOST.CONTROL}=1 and min(/'
                + TPL
                + '/'
                + item_key
                + ',15m)>0\'',
            )
            doc.add(7, f'name: {q("ExtremeControl SNMP: contact-lost switches")}')
            doc.add(7, f'event_name: {q("ExtremeControl SNMP: contact-lost switches")}')
            doc.add(7, 'priority: WARNING')
            doc.add(7, 'description: |')
            doc.literal(
                8,
                """Engine lost SNMP to one or more configured switches (the other
SNMP direction). Fleet canary 2026-08-28 was 0 on all five ENACs.
Enable {$NAC.SNMP.CONTACTLOST.CONTROL} after confirming this
object stays a gauge (MIB syntax is Counter64).""",
            )
            dep_snmp(doc, 7)
            scope(doc, 7, 'availability')
        if rate:
            doc.add(4, f'- uuid: {uid("rate", key)}')
            doc.add(5, f'name: ExtremeControl {title} per second')
            doc.add(5, 'type: DEPENDENT')
            doc.add(5, f'key: nac.appl.{key}.rate')
            doc.add(5, "delay: '0'")
            doc.add(5, 'history: 7d')
            doc.add(5, 'trends: 365d')
            doc.add(5, 'value_type: FLOAT')
            doc.add(5, 'units: pps')
            doc.add(5, 'preprocessing:')
            doc.add(6, '- type: CHANGE_PER_SECOND')
            doc.add(5, 'master_item:')
            doc.add(6, f'key: {item_key}')
            tags(doc, 5, 'nac')

    fail_params = (
        '(last(//nac.appl.auth.successes.rate)+last(//nac.appl.auth.failures.rate)>0)'
        '*((last(//nac.appl.auth.failures.rate)'
        '/(last(//nac.appl.auth.successes.rate)+last(//nac.appl.auth.failures.rate)))*100)'
    )
    doc.add(4, f'- uuid: {uid("item", "failpct")}')
    doc.add(5, 'name: ExtremeControl decided-auth failure ratio')
    doc.add(5, 'type: CALCULATED')
    doc.add(5, 'key: nac.appl.auth.fail.pct')
    doc.add(5, 'delay: 1m')
    doc.add(5, 'history: 7d')
    doc.add(5, 'trends: 365d')
    doc.add(5, 'value_type: FLOAT')
    doc.add(5, "units: '%'")
    doc.add(5, f'params: {q(fail_params)}')
    doc.add(5, 'description: |')
    doc.literal(
        6,
        """Failures / (successes + failures). Challenges are EAP and are not
failures. Collect first — STA canary decided-fail was ~30%.""",
    )
    tags(doc, 5, 'nac')
    doc.add(5, 'triggers:')
    doc.add(6, f'- uuid: {uid("tr", "failpct")}')
    doc.add(
        7,
        "expression: '{$NAC.SNMP.FAIL.WARN}<101 and min(/"
        + TPL
        + "/nac.appl.auth.fail.pct,15m)>{$NAC.SNMP.FAIL.WARN}'",
    )
    doc.add(7, f'name: {q("ExtremeControl SNMP: authentication failure ratio high")}')
    doc.add(7, f'event_name: {q("ExtremeControl SNMP: authentication failure ratio high")}')
    doc.add(7, 'priority: WARNING')
    doc.add(7, 'description: |')
    doc.literal(
        8,
        """Decided-auth failure % above {$NAC.SNMP.FAIL.WARN}. Default 101
silences until a quiet baseline. Not RADIUS-dead.""",
    )
    dep_snmp(doc, 7)
    scope(doc, 7, 'performance')

    doc.add(3, 'tags:')
    doc.add(4, '- tag: class')
    doc.add(5, 'value: network')
    doc.add(4, '- tag: target')
    doc.add(5, 'value: extremecontrol')
    doc.add(3, 'dashboards:')
    doc.add(4, f'- uuid: {uid("dash", "health")}')
    doc.add(5, 'name: Health')
    doc.add(5, 'pages:')
    doc.add(6, '- name: Overview')
    doc.add(7, 'widgets:')
    item_field(doc, 8, 'nac.snmp.available', None, None, 18, 'NSNMP', 'SNMP')
    item_field(doc, 8, 'nac.appl.auth.requests.rate', 18, None, 18, 'NREQ', 'Auth requests/s')
    item_field(doc, 8, 'nac.appl.auth.failures.rate', 36, None, 18, 'NFAIL', 'Auth failures/s')
    item_field(doc, 8, 'nac.appl.contact.lost', 54, None, 18, 'NCL', 'Contact lost')
    doc.add(8, '- type: problems')
    doc.add(9, 'name: Problems')
    doc.add(9, "y: '4'")
    doc.add(9, "width: '72'")
    doc.add(9, "height: '3'")
    doc.add(9, 'fields:')
    doc.add(10, '- type: STRING')
    doc.add(11, 'name: reference')
    doc.add(11, 'value: NPROB')
    doc.add(10, '- type: INTEGER')
    doc.add(11, 'name: show')
    doc.add(11, "value: '3'")
    svg_graph(
        doc,
        8,
        'Authentication',
        [
            ('2774A4', 'nac.appl.auth.requests.rate'),
            ('199C0D', 'nac.appl.auth.successes.rate'),
            ('FF465C', 'nac.appl.auth.failures.rate'),
        ],
        y=7,
        ref='NAUTH',
    )
    svg_graph(
        doc,
        8,
        'Challenges / dropped',
        [
            ('F2B90D', 'nac.appl.auth.challenges.rate'),
            ('E97659', 'nac.appl.auth.dropped.rate'),
        ],
        x=36,
        y=7,
        ref='NDROP',
    )
    doc.add(6, '- name: Auth')
    doc.add(7, 'widgets:')
    item_field(doc, 8, 'nac.appl.auth.fail.pct', None, None, 18, 'NPCT', 'Fail %')
    item_field(doc, 8, 'nac.appl.auth.successes.rate', 18, None, 18, 'NOK', 'Successes/s')
    item_field(doc, 8, 'nac.appl.auth.challenges.rate', 36, None, 18, 'NCHAL', 'Challenges/s')
    item_field(doc, 8, 'system.net.uptime[sysUpTime.0]', 54, None, 18, 'NUPT', 'Uptime')
    svg_graph(
        doc,
        8,
        'Invalid / duplicate / dropped',
        [
            ('FF465C', 'nac.appl.auth.invalid.rate'),
            ('F2B90D', 'nac.appl.auth.duplicate.rate'),
            ('E97659', 'nac.appl.auth.dropped.rate'),
        ],
        y=4,
        ref='NERR',
    )
    svg_graph(
        doc,
        8,
        'IP resolution',
        [
            ('2774A4', 'nac.appl.ip.res.failures.rate'),
            ('F2B90D', 'nac.appl.ip.res.timeouts.rate'),
        ],
        x=36,
        y=4,
        ref='NIP',
    )
    svg_graph(
        doc,
        8,
        'Captive portal / assessment',
        [
            ('199C0D', 'nac.appl.captive.portal.rate'),
            ('2774A4', 'nac.appl.assessment.rate'),
        ],
        y=10,
        ref='NPORT',
    )
    item_field(doc, 8, 'nac.snmp.product', 36, 10, 18, 'NPROD', 'Product')
    item_field(doc, 8, 'nac.appl.connected.agents', 54, 10, 18, 'NAGT', 'Agents')

    doc.add(3, 'valuemaps:')
    doc.add(4, f'- uuid: {uid("vm", "service")}')
    doc.add(5, 'name: Service state')
    doc.add(5, 'mappings:')
    doc.add(6, "- value: '0'")
    doc.add(7, 'newvalue: Down')
    doc.add(6, "- value: '1'")
    doc.add(7, 'newvalue: Up')
    doc.add(4, f'- uuid: {uid("vm", "avail")}')
    doc.add(5, 'name: zabbix.host.available')
    doc.add(5, 'mappings:')
    doc.add(6, "- value: '0'")
    doc.add(7, 'newvalue: Down')
    doc.add(6, "- value: '1'")
    doc.add(7, 'newvalue: Up')
    doc.add(6, "- value: '2'")
    doc.add(7, 'newvalue: Unknown')
    doc.add(4, f'- uuid: {uid("vm", "ident")}')
    doc.add(5, 'name: ExtremeControl identity')
    doc.add(5, 'mappings:')
    doc.add(6, "- value: '0'")
    doc.add(7, 'newvalue: Other / net-snmp')
    doc.add(6, "- value: '1'")
    doc.add(7, 'newvalue: Access Control')
    return doc.dumps()


def write_yaml() -> Path:
    SNMP_YAML.parent.mkdir(parents=True, exist_ok=True)
    SNMP_YAML.write_text(render(), encoding='utf-8')
    return SNMP_YAML


if __name__ == '__main__':
    print(write_yaml())
