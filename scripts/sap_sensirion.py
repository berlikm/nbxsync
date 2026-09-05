#!/usr/bin/env python3
"""SAP template from Sensirion — LM-parity host SNMP + Promonitor/DNUS contract."""

from __future__ import annotations

import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / 'zabbix/templates/sap_sensirion'
TEMPLATE_YAML = TEMPLATE_DIR / 'template_sap_sensirion.yaml'

TEMPLATE_NAME = 'SAP template from Sensirion'
TPL = TEMPLATE_NAME
TEMPLATE_FILES = {TEMPLATE_NAME: TEMPLATE_YAML}
TEMPLATE_GROUP = 'Templates/Applications'
GROUP_UUID = '7c4e2b91a06f4d8e9b15c3a8d0e4f217'
APPLY_FLAG = '--apply-sap'
CHECK_FLAG = '--check-sap'
SAP_ROLES = ('SAP HANA', 'SAP ME')
CANARY_HOST = 'CH-STA-P-SH01'
LINUX_NETSNMP_SYSOBJECTID = '1.3.6.1.4.1.8072.3.2.10'
SAP_ENTERPRISE_OID = '1.3.6.1.4.1.2312'
LM_PROMONITOR_USER = 'C_PROMONITOR'
LM_SNMP_USER = 'SAPUSER'
LM_SAP_HOSTS = 11

_NS = uuid.UUID('8a1c0e22-91b4-4d7a-8c33-b7e2f4a1c908')


def uid(*parts: str) -> str:
    return uuid.UUID(bytes=uuid.uuid5(_NS, '|'.join(parts)).bytes, version=4).hex


class Doc:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def add(self, indent: int, text: str) -> None:
        self.lines.append('' if text == '' else ('  ' * indent) + text)

    def literal(self, indent: int, text: str) -> None:
        for line in text.replace('\r\n', '\n').split('\n'):
            self.add(indent, line)

    def dumps(self) -> str:
        return '\n'.join(self.lines) + '\n'


def q(value: str) -> str:
    if value == '' or any(ch in value for ch in ":{}[]#&*?|>!%@`'\" ,") or value.startswith('{'):
        return "'" + value.replace("'", "''") + "'"
    return value


def tags(doc: Doc, indent: int, component: str, extra: tuple[tuple[str, str], ...] = ()) -> None:
    doc.add(indent, 'tags:')
    doc.add(indent + 1, '- tag: component')
    doc.add(indent + 2, f'value: {component}')
    for tag, value in extra:
        doc.add(indent + 1, f'- tag: {tag}')
        doc.add(indent + 2, f'value: {q(value)}')


def scope(doc: Doc, indent: int, value: str) -> None:
    doc.add(indent, 'tags:')
    doc.add(indent + 1, '- tag: scope')
    doc.add(indent + 2, f'value: {value}')


SNMP_DOWN = 'SAP host: No SNMP data collection'
UNSUPPORTED = 'SAP host: Too many unsupported items'
RESTARTED = 'SAP host: Host has been restarted'
SYSNAME = 'SAP host: System name has changed'
MEM_WARN = 'SAP host: Memory utilization is high'
CPU_WARN = 'SAP host: CPU utilization is high'
LOAD_WARN = 'SAP host: Load average is high'
SWAP_WARN = 'SAP host: Swap utilization is high'
FS_WARN = 'SAP host: File system {#FSNAME}: Disk space is low'
IF_DOWN = 'SAP host: Interface {#IFDESCR}: Link down'
IF_ERR = 'SAP host: Interface {#IFDESCR}: High error rate'
APP_NODATA = 'SAP application: No Promonitor/DNUS data for 30m'
APP_ABAP = 'SAP application: ABAP dumps or runtime errors'
APP_IDOC = 'SAP application: IDoc errors'
APP_QRFC = 'SAP application: qRFC errors'
APP_JOB = 'SAP application: Job alerts'
APP_SYSLOG = 'SAP application: Syslog alerts'

SNMP_ITEM_KEYS = {
    'zabbix[host,snmp,available]',
    'zabbix[host,,items_unsupported]',
    'sap.host.snmp.available',
    'system.name',
    'system.descr',
    'system.objectid[sysObjectID.0]',
    'sap.host.netsnmp',
    'system.net.uptime[sysUpTime.0]',
    'sap.host.load[1m]',
    'sap.host.load[5m]',
    'sap.host.load[15m]',
    'sap.host.cpu.idle',
    'sap.host.cpu.util',
    'sap.host.memory.total',
    'sap.host.memory.avail',
    'sap.host.memory.pused',
    'sap.host.swap.total',
    'sap.host.swap.avail',
    'sap.host.swap.pused',
    'sap.host.processes',
}

APP_ITEM_KEYS = {
    'sap.app.promonitor',
    'sap.app.abap.errors',
    'sap.app.idoc.errors',
    'sap.app.qrfc.errors',
    'sap.app.job.alerts',
    'sap.app.syslog.alerts',
}

SNMP_LLD_KEYS = {
    'sap.host.net.if.discovery',
    'sap.host.vfs.fs.discovery',
}

SNMP_PROTOTYPE_KEYS = {
    'sap.host.net.if.status[ifOperStatus.{#SNMPINDEX}]',
    'sap.host.net.if.in[ifInOctets.{#SNMPINDEX}]',
    'sap.host.net.if.out[ifOutOctets.{#SNMPINDEX}]',
    'sap.host.net.if.in.errors[ifInErrors.{#SNMPINDEX}]',
    'sap.host.net.if.out.errors[ifOutErrors.{#SNMPINDEX}]',
    'sap.host.vfs.fs.size[{#SNMPINDEX},total]',
    'sap.host.vfs.fs.size[{#SNMPINDEX},used]',
    'sap.host.vfs.fs.pused[{#SNMPINDEX}]',
}

SNMP_TRIGGER_NAMES = {
    SNMP_DOWN,
    UNSUPPORTED,
    RESTARTED,
    SYSNAME,
    MEM_WARN,
    CPU_WARN,
    LOAD_WARN,
    SWAP_WARN,
}

APP_TRIGGER_NAMES = {
    APP_NODATA,
    APP_ABAP,
    APP_IDOC,
    APP_QRFC,
    APP_JOB,
    APP_SYSLOG,
}

SNMP_TRIGGER_PROTOTYPE_NAMES = {IF_DOWN, IF_ERR, FS_WARN}

FORBIDDEN_SNIPPETS = (
    'icmpping',
    'net.udp.service',
    'system.run',
    'verify=False',
    '{HOST.HOST}',
    '{HOST.CONN}',
    SAP_ENTERPRISE_OID,
    '1.3.6.1.4.1.8072.1.3.2',
    'Linux by SNMP',
    'WinProcessStats_jstart',
)

LM_APP_METRICS = (
    ('sap.app.promonitor', 'Promonitor / C_PROMONITOR', '1 when DNUS reports the Promonitor session is up. LM API account C_PROMONITOR on 11 SAP hosts.'),
    ('sap.app.abap.errors', 'ABAP dumps / runtime errors', 'LM custom datasource on ch-sta-p-sh01: SAP ABAP runtime/errors. Count in the last poll.'),
    ('sap.app.idoc.errors', 'IDoc errors', 'LM custom datasource on ch-sta-p-sh01: IDoc.'),
    ('sap.app.qrfc.errors', 'qRFC errors', 'LM custom datasource on ch-sta-p-sh01: qRFC.'),
    ('sap.app.job.alerts', 'Job alerts', 'LM custom datasource on ch-sta-p-sh01: job alerts.'),
    ('sap.app.syslog.alerts', 'SAP syslog alerts', 'LM custom datasource on ch-sta-p-sh01: syslog.'),
)

MACROS = (
    ('{$SNMP.TIMEOUT}', '5m', 'SNMP availability trigger window.'),
    ('{$UNSUPPORTED.MAX}', '1', 'Average when unsupported SNMP items stay above this for 30m.'),
    ('{$SAP.MEMORY.UTIL.MAX}', '101', 'Host RAM used % Warning. 101 collects first.'),
    ('{$SAP.CPU.UTIL.MAX}', '101', 'Host CPU used % Warning. 101 collects first.'),
    ('{$SAP.CPU.LOAD.MAX}', '101', '15-minute load Warning. 101 collects first.'),
    ('{$SAP.SWAP.UTIL.MAX}', '101', 'Swap used % Warning. 101 collects first.'),
    ('{$SAP.VFS.FS.PUSED.MAX}', '101', 'Filesystem used % Warning. 101 collects first.'),
    ('{$SAP.NET.IF.ERRORS.WARN}', '2', 'IF-MIB in+out errors/s Warning.'),
    ('{$IFCONTROL}', '1', '1 tickets admin-up link-down. {$IFCONTROL:"eth0"}=0 mutes one NIC.'),
    ('{$NET.IF.IFDESCR.MATCHES}', '^.+$', 'Interface LLD include.'),
    ('{$NET.IF.IFDESCR.NOT_MATCHES}', '^(?i)(lo|loopback)(.*)$', 'Drop loopback. SH01 probe saw lo + eth0.'),
    ('{$NET.IF.IFTYPE.NOT_MATCHES}', '^24$', 'Drop softwareLoopback(24).'),
    ('{$VFS.FS.FSNAME.MATCHES}', '^.+$', 'Filesystem LLD include.'),
    (
        '{$VFS.FS.FSNAME.NOT_MATCHES}',
        '^(?i)(physical memory|virtual memory|memory buffers|cached memory|swap|/dev|/sys|/run|/proc).*$',
        'Keep mounted disks; UCD memory is scalars, not this LLD.',
    ),
    (
        '{$VFS.FS.FSTYPE.MATCHES}',
        r'^(\.iso\.org\.dod\.internet\.mgmt\.mib-2\.host\.hrStorage\.hrStorageTypes\.hrStorageFixedDisk|1\.3\.6\.1\.2\.1\.25\.2\.1\.4)$',
        'hrStorageFixedDisk only.',
    ),
    (
        '{$SAP.APP.CONTROL}',
        '0',
        '1 enables Promonitor/DNUS nodata and threshold triggers. 0 = collect-first (LM application gap).',
    ),
    ('{$SAP.APP.ABAP.MAX}', '0', 'ABAP dump/runtime-error count Warning when CONTROL=1.'),
    ('{$SAP.APP.IDOC.MAX}', '0', 'IDoc error count Warning when CONTROL=1.'),
    ('{$SAP.APP.QRFC.MAX}', '0', 'qRFC error count Warning when CONTROL=1.'),
    ('{$SAP.APP.JOB.MAX}', '0', 'Job alert count Warning when CONTROL=1.'),
    ('{$SAP.APP.SYSLOG.MAX}', '0', 'Syslog alert count Warning when CONTROL=1.'),
)


def dep_snmp(doc: Doc, indent: int) -> None:
    doc.add(indent, 'dependencies:')
    doc.add(indent + 1, f'- name: {q(SNMP_DOWN)}')
    doc.add(indent + 2, f'expression: max(/{TPL}/zabbix[host,snmp,available],' + '{$SNMP.TIMEOUT})=0')


def item_tile(doc: Doc, indent: int, key: str, x: int | None, y: int | None, width: int, ref: str, name: str) -> None:
    doc.add(indent, '- type: item')
    doc.add(indent + 1, f'name: {name}')
    if x:
        doc.add(indent + 1, f"x: '{x}'")
    if y:
        doc.add(indent + 1, f"y: '{y}'")
    doc.add(indent + 1, f"width: '{width}'")
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


def svg_graph(doc: Doc, indent: int, name: str, series: list[tuple[str, str]], *, x: int = 0, y: int = 0, width: int = 36, ref: str) -> None:
    doc.add(indent, '- type: svggraph')
    doc.add(indent + 1, f'name: {name}')
    if x:
        doc.add(indent + 1, f"x: '{x}'")
    if y:
        doc.add(indent + 1, f"y: '{y}'")
    doc.add(indent + 1, f"width: '{width}'")
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
        f"""Sensirion SAP pack. LogicMonitor parity from zabbix/logicmonitor-assessment.md
(LM account export Aug 2026) plus the 2026-09-05 SNMP probe of {CANARY_HOST}.

LM had two planes — this template covers both, without inventing a Promonitor API:

1. Host / SNMP — LM group credential {LM_SNMP_USER} (MD5/DES) on SAP systems.
   Probe of {CANARY_HOST} (10.0.105.112) proved Linux Net-SNMP only
   ({LINUX_NETSNMP_SYSOBJECTID}). The SAP enterprise tree and
   Net-SNMP extend were empty. Items here are IF-MIB / UCD / HOST-RESOURCES.

2. Application — LM API account {LM_PROMONITOR_USER} on {LM_SAP_HOSTS} SAP hosts,
   plus the custom datasource on ch-sta-p-sh01 (ABAP runtime/errors, IDoc,
   qRFC, job alerts, syslog). DNUS scripts (Robert) own that contract. This
   template exposes trapper keys for those exact LM rows. {{$SAP.APP.CONTROL}}=0
   keeps application triggers off until DNUS pushes values.

Not in this template: AS Java jstart process stats (ch-sta-p-as02 /
ch-sta-d-as01) — that is the AS Java agent stub, not SAP HANA / SAP ME.
Does not nest ICMP (SAP Agent+SNMP CG). Does not link the stock Linux SNMP
template. Does not walk the enterprise tree unbounded.

Operator notes: zabbix/notes/sap-snmp-walk.md,
zabbix/templates/sap_sensirion/LM_PARITY.md.
Refresh with configure_nbxsync_network.py {APPLY_FLAG}.""",
    )
    doc.add(3, 'groups:')
    doc.add(4, f'- name: {TEMPLATE_GROUP}')
    doc.add(3, 'macros:')
    for macro, value, descr in MACROS:
        doc.add(4, f'- macro: {q(macro)}')
        doc.add(5, f'value: {q(value)}')
        doc.add(5, f'description: {descr}')
    doc.add(3, 'items:')
    _host_items(doc)
    _app_items(doc)
    _discovery(doc)
    _dashboard(doc)
    _valuemaps(doc)
    return doc.dumps()


def _host_items(doc: Doc) -> None:
    doc.add(4, f'- uuid: {uid("item", "snmp")}')
    doc.add(5, 'name: SNMP agent availability')
    doc.add(5, 'type: INTERNAL')
    doc.add(5, "key: 'zabbix[host,snmp,available]'")
    doc.add(5, 'description: |')
    doc.literal(6, f'LM {LM_SNMP_USER} plane. 0/1/2. ICMP High from the SAP Agent+SNMP CG pages if the box is gone.')
    doc.add(5, 'valuemap:')
    doc.add(6, 'name: zabbix.host.available')
    tags(doc, 5, 'health')
    doc.add(5, 'triggers:')
    doc.add(6, f'- uuid: {uid("tr", "snmp")}')
    doc.add(7, f'expression: max(/{TPL}/zabbix[host,snmp,available],' + '{$SNMP.TIMEOUT})=0')
    doc.add(7, f'name: {q(SNMP_DOWN)}')
    doc.add(7, f'event_name: {q(SNMP_DOWN)}')
    doc.add(7, 'priority: WARNING')
    doc.add(7, 'description: |')
    doc.literal(8, f'SNMP {LM_SNMP_USER} MD5/DES failed from the assigned proxy. Host infra, not an ABAP dump. Canary {CANARY_HOST}.')
    scope(doc, 7, 'availability')

    doc.add(4, f'- uuid: {uid("item", "unsup")}')
    doc.add(5, 'name: Unsupported item count')
    doc.add(5, 'type: INTERNAL')
    doc.add(5, "key: 'zabbix[host,,items_unsupported]'")
    doc.add(5, 'delay: 15m')
    doc.add(5, 'description: Watch the watcher for the SNMP plane only. Trapper application items do not go unsupported.')
    tags(doc, 5, 'health')
    doc.add(5, 'triggers:')
    doc.add(6, f'- uuid: {uid("tr", "unsup")}')
    doc.add(7, f'expression: min(/{TPL}/zabbix[host,,items_unsupported],30m)>' + '{$UNSUPPORTED.MAX}')
    doc.add(7, f'name: {q(UNSUPPORTED)}')
    doc.add(7, f'event_name: {q(UNSUPPORTED)}')
    doc.add(7, 'priority: AVERAGE')
    doc.add(7, 'description: SNMP=1 but host items unsupported — OID/view mismatch.')
    dep_snmp(doc, 7)
    scope(doc, 7, 'availability')

    doc.add(4, f'- uuid: {uid("item", "snmp.hl")}')
    doc.add(5, 'name: SNMP')
    doc.add(5, 'type: CALCULATED')
    doc.add(5, 'key: sap.host.snmp.available')
    doc.add(5, 'delay: 1m')
    doc.add(5, 'value_type: FLOAT')
    doc.add(5, "params: 'last(//zabbix[host,snmp,available])'")
    doc.add(5, 'valuemap:')
    doc.add(6, 'name: zabbix.host.available')
    tags(doc, 5, 'health')

    _char_item(doc, 'system.name', 'System name', '1.3.6.1.2.1.1.5.0')
    doc.add(5, 'triggers:')
    doc.add(6, f'- uuid: {uid("tr", "sysname")}')
    doc.add(7, f'expression: last(/{TPL}/system.name,#1)<>last(/{TPL}/system.name,#2) and length(last(/{TPL}/system.name))>0')
    doc.add(7, f'name: {q(SYSNAME)}')
    doc.add(7, f'event_name: {q(SYSNAME)}')
    doc.add(7, 'priority: INFO')
    doc.add(7, "manual_close: 'YES'")
    scope(doc, 7, 'notice')

    _char_item(doc, 'system.descr', 'System description', '1.3.6.1.2.1.1.1.0', inventory='TYPE')
    _char_item(
        doc,
        'system.objectid[sysObjectID.0]',
        'System object ID',
        '1.3.6.1.2.1.1.2.0',
        description=f'{CANARY_HOST} is Linux Net-SNMP {LINUX_NETSNMP_SYSOBJECTID}.',
    )

    doc.add(4, f'- uuid: {uid("item", "netsnmp")}')
    doc.add(5, 'name: Linux Net-SNMP identity')
    doc.add(5, 'type: DEPENDENT')
    doc.add(5, 'key: sap.host.netsnmp')
    doc.add(5, "delay: '0'")
    doc.add(5, 'history: 7d')
    doc.add(5, 'trends: 365d')
    doc.add(5, 'value_type: UNSIGNED')
    doc.add(5, 'valuemap:')
    doc.add(6, 'name: SAP host identity')
    doc.add(5, 'preprocessing:')
    doc.add(6, '- type: JAVASCRIPT')
    doc.add(7, 'parameters:')
    doc.add(8, '- |')
    doc.literal(
        10,
        "var oid = String(value || '').replace(/^\\\\.+/, '');\n"
        f"var expect = '{LINUX_NETSNMP_SYSOBJECTID}';\n"
        'return oid === expect || oid === "." + expect ? 1 : 0;\n',
    )
    doc.add(5, 'master_item:')
    doc.add(6, "key: 'system.objectid[sysObjectID.0]'")
    tags(doc, 5, 'system')

    doc.add(4, f'- uuid: {uid("item", "uptime")}')
    doc.add(5, 'name: Uptime')
    doc.add(5, 'type: SNMP_AGENT')
    doc.add(5, 'snmp_oid: 1.3.6.1.2.1.1.3.0')
    doc.add(5, "key: 'system.net.uptime[sysUpTime.0]'")
    doc.add(5, 'delay: 1m')
    doc.add(5, 'units: uptime')
    doc.add(5, 'preprocessing:')
    doc.add(6, '- type: MULTIPLIER')
    doc.add(7, 'parameters:')
    doc.add(8, "- '0.01'")
    tags(doc, 5, 'system')
    doc.add(5, 'triggers:')
    doc.add(6, f'- uuid: {uid("tr", "restart")}')
    doc.add(7, f'expression: last(/{TPL}/system.net.uptime[sysUpTime.0])>0 and last(/{TPL}/system.net.uptime[sysUpTime.0])<10m')
    doc.add(7, f'name: {q(RESTARTED)}')
    doc.add(7, f'event_name: {q(RESTARTED)}')
    doc.add(7, 'priority: INFO')
    doc.add(7, "manual_close: 'YES'")
    dep_snmp(doc, 7)
    scope(doc, 7, 'notice')

    for minutes, idx, trig in (('1m', 1, False), ('5m', 2, False), ('15m', 3, True)):
        doc.add(4, f'- uuid: {uid("item", f"load.{minutes}")}')
        doc.add(5, f'name: Load average ({minutes})')
        doc.add(5, 'type: SNMP_AGENT')
        doc.add(5, f'snmp_oid: 1.3.6.1.4.1.2021.10.1.3.{idx}')
        doc.add(5, f'key: {q(f"sap.host.load[{minutes}]")}')
        doc.add(5, 'delay: 1m')
        doc.add(5, 'value_type: FLOAT')
        doc.add(5, 'description: UCD laLoad. Host infra, not SAP dialog response time.')
        tags(doc, 5, 'os')
        if trig:
            doc.add(5, 'triggers:')
            doc.add(6, f'- uuid: {uid("tr", "load")}')
            doc.add(7, f'expression: min(/{TPL}/sap.host.load[15m],15m)>' + '{$SAP.CPU.LOAD.MAX}')
            doc.add(7, f'name: {q(LOAD_WARN)}')
            doc.add(7, f'event_name: {q(LOAD_WARN)}')
            doc.add(7, 'priority: WARNING')
            dep_snmp(doc, 7)
            scope(doc, 7, 'performance')

    doc.add(4, f'- uuid: {uid("item", "cpu.idle")}')
    doc.add(5, 'name: CPU idle')
    doc.add(5, 'type: SNMP_AGENT')
    doc.add(5, 'snmp_oid: 1.3.6.1.4.1.2021.11.11.0')
    doc.add(5, 'key: sap.host.cpu.idle')
    doc.add(5, 'delay: 1m')
    doc.add(5, 'units: "%"')
    tags(doc, 5, 'os')

    doc.add(4, f'- uuid: {uid("item", "cpu.util")}')
    doc.add(5, 'name: CPU utilization')
    doc.add(5, 'type: CALCULATED')
    doc.add(5, 'key: sap.host.cpu.util')
    doc.add(5, 'delay: 1m')
    doc.add(5, 'value_type: FLOAT')
    doc.add(5, 'units: "%"')
    doc.add(5, "params: '100-last(//sap.host.cpu.idle)'")
    doc.add(5, 'description: 100 − UCD ssCpuIdle. Not ST06 SAP CPU.')
    tags(doc, 5, 'os')
    doc.add(5, 'triggers:')
    doc.add(6, f'- uuid: {uid("tr", "cpu")}')
    doc.add(7, f'expression: min(/{TPL}/sap.host.cpu.util,15m)>' + '{$SAP.CPU.UTIL.MAX}')
    doc.add(7, f'name: {q(CPU_WARN)}')
    doc.add(7, f'event_name: {q(CPU_WARN)}')
    doc.add(7, 'priority: WARNING')
    dep_snmp(doc, 7)
    scope(doc, 7, 'performance')

    for key, name, oid in (
        ('sap.host.memory.total', 'Memory total', '1.3.6.1.4.1.2021.4.5.0'),
        ('sap.host.memory.avail', 'Memory available', '1.3.6.1.4.1.2021.4.6.0'),
        ('sap.host.swap.total', 'Swap total', '1.3.6.1.4.1.2021.4.3.0'),
        ('sap.host.swap.avail', 'Swap available', '1.3.6.1.4.1.2021.4.4.0'),
    ):
        doc.add(4, f'- uuid: {uid("item", key)}')
        doc.add(5, f'name: {name}')
        doc.add(5, 'type: SNMP_AGENT')
        doc.add(5, f'snmp_oid: {oid}')
        doc.add(5, f'key: {key}')
        doc.add(5, 'delay: 1m')
        doc.add(5, 'units: B')
        doc.add(5, 'preprocessing:')
        doc.add(6, '- type: MULTIPLIER')
        doc.add(7, 'parameters:')
        doc.add(8, "- '1024'")
        tags(doc, 5, 'os')

    _pused(
        doc,
        key='sap.host.memory.pused',
        name='Memory utilization',
        total='sap.host.memory.total',
        avail='sap.host.memory.avail',
        trigger=MEM_WARN,
        macro='{$SAP.MEMORY.UTIL.MAX}',
        uid_key='mem',
        descr='Host RAM (total−avail)/total. Not HANA allocation.',
    )
    _pused(
        doc,
        key='sap.host.swap.pused',
        name='Swap utilization',
        total='sap.host.swap.total',
        avail='sap.host.swap.avail',
        trigger=SWAP_WARN,
        macro='{$SAP.SWAP.UTIL.MAX}',
        uid_key='swap',
        descr='0 when the host has no swap.',
    )

    doc.add(4, f'- uuid: {uid("item", "procs")}')
    doc.add(5, 'name: Process count')
    doc.add(5, 'type: SNMP_AGENT')
    doc.add(5, 'snmp_oid: 1.3.6.1.2.1.25.1.6.0')
    doc.add(5, 'key: sap.host.processes')
    doc.add(5, 'delay: 5m')
    doc.add(5, 'description: hrSystemProcesses. Does not LLD disp+work or treat process names as SAP health.')
    tags(doc, 5, 'os')


def _pused(doc: Doc, *, key: str, name: str, total: str, avail: str, trigger: str, macro: str, uid_key: str, descr: str) -> None:
    doc.add(4, f'- uuid: {uid("item", key)}')
    doc.add(5, f'name: {name}')
    doc.add(5, 'type: CALCULATED')
    doc.add(5, f'key: {key}')
    doc.add(5, 'delay: 1m')
    doc.add(5, 'value_type: FLOAT')
    doc.add(5, 'units: "%"')
    doc.add(5, f"params: '(last(//{total})>0)*100*(last(//{total})-last(//{avail}))/(last(//{total})+(last(//{total})=0))'")
    doc.add(5, f'description: {descr}')
    tags(doc, 5, 'os')
    doc.add(5, 'triggers:')
    doc.add(6, f'- uuid: {uid("tr", uid_key)}')
    doc.add(7, f'expression: min(/{TPL}/{key},15m)>{macro}')
    doc.add(7, f'name: {q(trigger)}')
    doc.add(7, f'event_name: {q(trigger)}')
    doc.add(7, 'priority: WARNING')
    dep_snmp(doc, 7)
    scope(doc, 7, 'performance')


def _char_item(doc: Doc, key: str, name: str, oid: str, *, inventory: str | None = None, description: str | None = None) -> None:
    doc.add(4, f'- uuid: {uid("item", key)}')
    doc.add(5, f'name: {name}')
    doc.add(5, 'type: SNMP_AGENT')
    doc.add(5, f'snmp_oid: {oid}')
    doc.add(5, f'key: {q(key)}')
    doc.add(5, 'delay: 1h')
    doc.add(5, 'value_type: CHAR')
    doc.add(5, 'history: 7d')
    doc.add(5, "trends: '0'")
    if description:
        doc.add(5, f'description: {description}')
    if inventory:
        doc.add(5, f'inventory_link: {inventory}')
    doc.add(5, 'preprocessing:')
    doc.add(6, '- type: DISCARD_UNCHANGED_HEARTBEAT')
    doc.add(7, 'parameters:')
    doc.add(8, '- 6h')
    tags(doc, 5, 'system')


def _app_items(doc: Doc) -> None:
    thresholds = {
        'sap.app.abap.errors': ('{$SAP.APP.ABAP.MAX}', APP_ABAP),
        'sap.app.idoc.errors': ('{$SAP.APP.IDOC.MAX}', APP_IDOC),
        'sap.app.qrfc.errors': ('{$SAP.APP.QRFC.MAX}', APP_QRFC),
        'sap.app.job.alerts': ('{$SAP.APP.JOB.MAX}', APP_JOB),
        'sap.app.syslog.alerts': ('{$SAP.APP.SYSLOG.MAX}', APP_SYSLOG),
    }
    for key, name, descr in LM_APP_METRICS:
        doc.add(4, f'- uuid: {uid("item", key)}')
        doc.add(5, f'name: {name}')
        doc.add(5, 'type: TRAP')
        doc.add(5, f'key: {key}')
        doc.add(5, 'delay: 1m')
        doc.add(5, 'description: |')
        doc.literal(
            6,
            descr
            + f'\nDNUS/Robert pushes zabbix_sender to this trapper. Not SNMP. Not UserParameter until that contract exists.',
        )
        if key == 'sap.app.promonitor':
            doc.add(5, 'valuemap:')
            doc.add(6, 'name: Service state')
        tags(doc, 5, 'sap-application')
        doc.add(5, 'triggers:')
        if key == 'sap.app.promonitor':
            doc.add(6, f'- uuid: {uid("tr", "app.nodata")}')
            doc.add(7, 'expression: ' + q(f'{{$SAP.APP.CONTROL}}=1 and nodata(/{TPL}/sap.app.promonitor,30m)=1'))
            doc.add(7, f'name: {q(APP_NODATA)}')
            doc.add(7, f'event_name: {q(APP_NODATA)}')
            doc.add(7, 'priority: WARNING')
            doc.add(7, 'description: |')
            doc.literal(8, 'CONTROL=1 after DNUS ships. Default 0 so an empty trapper does not page.')
            scope(doc, 7, 'availability')
            continue
        macro, trig = thresholds[key]
        doc.add(6, f'- uuid: {uid("tr", key)}')
        doc.add(7, 'expression: ' + q(f'{{$SAP.APP.CONTROL}}=1 and min(/{TPL}/{key},15m)>{macro}'))
        doc.add(7, f'name: {q(trig)}')
        doc.add(7, f'event_name: {q(trig)}')
        doc.add(7, 'priority: AVERAGE')
        doc.add(7, 'description: |')
        doc.literal(8, f'LM custom datasource row. Disabled while CONTROL=0. Ticket, not SMS, until a quiet baseline.')
        doc.add(7, 'dependencies:')
        doc.add(8, f'- name: {q(APP_NODATA)}')
        doc.add(9, 'expression: ' + q(f'{{$SAP.APP.CONTROL}}=1 and nodata(/{TPL}/sap.app.promonitor,30m)=1'))
        scope(doc, 7, 'sap-application')


def _discovery(doc: Doc) -> None:
    doc.add(3, 'discovery_rules:')
    doc.add(4, f'- uuid: {uid("lld", "if")}')
    doc.add(5, 'name: Network interfaces')
    doc.add(5, 'type: SNMP_AGENT')
    doc.add(5, "snmp_oid: 'discovery[{#IFDESCR},1.3.6.1.2.1.2.2.1.2,{#IFOPERSTATUS},1.3.6.1.2.1.2.2.1.8,{#IFADMINSTATUS},1.3.6.1.2.1.2.2.1.7,{#IFTYPE},1.3.6.1.2.1.2.2.1.3]'")
    doc.add(5, 'key: sap.host.net.if.discovery')
    doc.add(5, 'delay: 1h')
    doc.add(5, 'description: IF-MIB ifTable from the SH01 probe. 32-bit octet counters. Drops lo.')
    doc.add(5, 'filter:')
    doc.add(6, 'evaltype: AND')
    doc.add(6, 'conditions:')
    doc.add(7, "- macro: '{#IFDESCR}'")
    doc.add(8, "value: '{$NET.IF.IFDESCR.MATCHES}'")
    doc.add(8, 'formulaid: A')
    doc.add(7, "- macro: '{#IFDESCR}'")
    doc.add(8, "value: '{$NET.IF.IFDESCR.NOT_MATCHES}'")
    doc.add(8, 'operator: NOT_MATCHES_REGEX')
    doc.add(8, 'formulaid: B')
    doc.add(7, "- macro: '{#IFTYPE}'")
    doc.add(8, "value: '{$NET.IF.IFTYPE.NOT_MATCHES}'")
    doc.add(8, 'operator: NOT_MATCHES_REGEX')
    doc.add(8, 'formulaid: C')
    doc.add(5, 'item_prototypes:')

    doc.add(6, f'- uuid: {uid("proto", "if.status")}')
    doc.add(7, "name: 'Interface {#IFDESCR}: Operational status'")
    doc.add(7, 'type: SNMP_AGENT')
    doc.add(7, "snmp_oid: '1.3.6.1.2.1.2.2.1.8.{#SNMPINDEX}'")
    doc.add(7, "key: 'sap.host.net.if.status[ifOperStatus.{#SNMPINDEX}]'")
    doc.add(7, 'delay: 1m')
    doc.add(7, 'history: 7d')
    doc.add(7, "trends: '0'")
    doc.add(7, 'valuemap:')
    doc.add(8, 'name: IF-MIB::ifStatus')
    tags(doc, 7, 'network', (('interface', '{#IFDESCR}'),))
    doc.add(7, 'trigger_prototypes:')
    doc.add(8, f'- uuid: {uid("trp", "if.down")}')
    doc.add(9, 'expression: ' + q(f'{{$IFCONTROL:"{{#IFDESCR}}"}}=1 and min(/{TPL}/sap.host.net.if.status[ifOperStatus.{{#SNMPINDEX}}],#3)<>1'))
    doc.add(9, 'recovery_mode: RECOVERY_EXPRESSION')
    doc.add(9, 'recovery_expression: ' + q(f'last(/{TPL}/sap.host.net.if.status[ifOperStatus.{{#SNMPINDEX}}])=1 or {{$IFCONTROL:"{{#IFDESCR}}"}}=0'))
    doc.add(9, f'name: {q(IF_DOWN)}')
    doc.add(9, 'priority: AVERAGE')
    doc.add(9, 'description: Host NIC, not SAP RFC. Mute with {$IFCONTROL:"eth0"}=0.')
    dep_snmp(doc, 9)
    scope(doc, 9, 'availability')

    for key, name, oid, units, extra_mult in (
        ('sap.host.net.if.in[ifInOctets.{#SNMPINDEX}]', 'Interface {#IFDESCR}: Bits received', '1.3.6.1.2.1.2.2.1.10.{#SNMPINDEX}', 'bps', True),
        ('sap.host.net.if.out[ifOutOctets.{#SNMPINDEX}]', 'Interface {#IFDESCR}: Bits sent', '1.3.6.1.2.1.2.2.1.16.{#SNMPINDEX}', 'bps', True),
        ('sap.host.net.if.in.errors[ifInErrors.{#SNMPINDEX}]', 'Interface {#IFDESCR}: In errors', '1.3.6.1.2.1.2.2.1.14.{#SNMPINDEX}', 'eps', False),
        ('sap.host.net.if.out.errors[ifOutErrors.{#SNMPINDEX}]', 'Interface {#IFDESCR}: Out errors', '1.3.6.1.2.1.2.2.1.20.{#SNMPINDEX}', 'eps', False),
    ):
        doc.add(6, f'- uuid: {uid("proto", key)}')
        doc.add(7, f'name: {q(name)}')
        doc.add(7, 'type: SNMP_AGENT')
        doc.add(7, f'snmp_oid: {q(oid)}')
        doc.add(7, f'key: {q(key)}')
        doc.add(7, 'delay: 1m')
        doc.add(7, 'value_type: FLOAT')
        doc.add(7, f'units: {units}')
        doc.add(7, 'preprocessing:')
        doc.add(8, '- type: CHANGE_PER_SECOND')
        if extra_mult:
            doc.add(8, '- type: MULTIPLIER')
            doc.add(9, 'parameters:')
            doc.add(10, "- '8'")
        tags(doc, 7, 'network', (('interface', '{#IFDESCR}'),))
        if 'ifInErrors' in key:
            doc.add(7, 'trigger_prototypes:')
            doc.add(8, f'- uuid: {uid("trp", "if.err")}')
            doc.add(
                9,
                'expression: '
                + q(
                    f'min(/{TPL}/sap.host.net.if.in.errors[ifInErrors.{{#SNMPINDEX}}],5m)'
                    f'+min(/{TPL}/sap.host.net.if.out.errors[ifOutErrors.{{#SNMPINDEX}}],5m)'
                    '>{$SAP.NET.IF.ERRORS.WARN}'
                ),
            )
            doc.add(9, f'name: {q(IF_ERR)}')
            doc.add(9, 'priority: WARNING')
            dep_snmp(doc, 9)
            scope(doc, 9, 'performance')

    doc.add(5, 'graph_prototypes:')
    doc.add(6, f'- uuid: {uid("gproto", "if")}')
    doc.add(7, "name: 'Interface {#IFDESCR}: Traffic'")
    doc.add(7, 'graph_items:')
    doc.add(8, '- drawtype: GRADIENT_LINE')
    doc.add(9, 'color: 199C0D')
    doc.add(9, 'item:')
    doc.add(10, f'host: {TPL}')
    doc.add(10, "key: 'sap.host.net.if.in[ifInOctets.{#SNMPINDEX}]'")
    doc.add(8, "- sortorder: '1'")
    doc.add(9, 'drawtype: BOLD_LINE')
    doc.add(9, 'color: F63100')
    doc.add(9, 'item:')
    doc.add(10, f'host: {TPL}')
    doc.add(10, "key: 'sap.host.net.if.out[ifOutOctets.{#SNMPINDEX}]'")

    doc.add(4, f'- uuid: {uid("lld", "fs")}')
    doc.add(5, 'name: Filesystems')
    doc.add(5, 'type: SNMP_AGENT')
    doc.add(5, "snmp_oid: 'discovery[{#FSNAME},1.3.6.1.2.1.25.2.3.1.3,{#FSTYPE},1.3.6.1.2.1.25.2.3.1.2]'")
    doc.add(5, 'key: sap.host.vfs.fs.discovery')
    doc.add(5, 'delay: 1h')
    doc.add(5, 'description: HOST-RESOURCES fixed disks. Memory/swap stay on UCD scalars.')
    doc.add(5, 'filter:')
    doc.add(6, 'evaltype: AND')
    doc.add(6, 'conditions:')
    doc.add(7, "- macro: '{#FSNAME}'")
    doc.add(8, "value: '{$VFS.FS.FSNAME.MATCHES}'")
    doc.add(8, 'formulaid: A')
    doc.add(7, "- macro: '{#FSNAME}'")
    doc.add(8, "value: '{$VFS.FS.FSNAME.NOT_MATCHES}'")
    doc.add(8, 'operator: NOT_MATCHES_REGEX')
    doc.add(8, 'formulaid: B')
    doc.add(7, "- macro: '{#FSTYPE}'")
    doc.add(8, "value: '{$VFS.FS.FSTYPE.MATCHES}'")
    doc.add(8, 'formulaid: C')
    doc.add(5, 'item_prototypes:')
    doc.add(6, f'- uuid: {uid("proto", "fs.total")}')
    doc.add(7, "name: 'Filesystem {#FSNAME}: Total blocks'")
    doc.add(7, 'type: SNMP_AGENT')
    doc.add(7, "snmp_oid: '1.3.6.1.2.1.25.2.3.1.5.{#SNMPINDEX}'")
    doc.add(7, "key: 'sap.host.vfs.fs.size[{#SNMPINDEX},total]'")
    doc.add(7, 'delay: 5m')
    tags(doc, 7, 'storage', (('filesystem', '{#FSNAME}'),))
    doc.add(6, f'- uuid: {uid("proto", "fs.used")}')
    doc.add(7, "name: 'Filesystem {#FSNAME}: Used blocks'")
    doc.add(7, 'type: SNMP_AGENT')
    doc.add(7, "snmp_oid: '1.3.6.1.2.1.25.2.3.1.6.{#SNMPINDEX}'")
    doc.add(7, "key: 'sap.host.vfs.fs.size[{#SNMPINDEX},used]'")
    doc.add(7, 'delay: 5m')
    tags(doc, 7, 'storage', (('filesystem', '{#FSNAME}'),))
    doc.add(6, f'- uuid: {uid("proto", "fs.pused")}')
    doc.add(7, "name: 'Filesystem {#FSNAME}: Used %'")
    doc.add(7, 'type: CALCULATED')
    doc.add(7, "key: 'sap.host.vfs.fs.pused[{#SNMPINDEX}]'")
    doc.add(7, 'delay: 5m')
    doc.add(7, 'value_type: FLOAT')
    doc.add(7, 'units: "%"')
    doc.add(7, "params: '(last(//sap.host.vfs.fs.size[{#SNMPINDEX},total])>0)*100*last(//sap.host.vfs.fs.size[{#SNMPINDEX},used])/(last(//sap.host.vfs.fs.size[{#SNMPINDEX},total])+(last(//sap.host.vfs.fs.size[{#SNMPINDEX},total])=0))'")
    tags(doc, 7, 'storage', (('filesystem', '{#FSNAME}'),))
    doc.add(7, 'trigger_prototypes:')
    doc.add(8, f'- uuid: {uid("trp", "fs")}')
    doc.add(9, f'expression: min(/{TPL}/sap.host.vfs.fs.pused[{{#SNMPINDEX}}],15m)>' + '{$SAP.VFS.FS.PUSED.MAX}')
    doc.add(9, f'name: {q(FS_WARN)}')
    doc.add(9, 'priority: WARNING')
    dep_snmp(doc, 9)
    scope(doc, 9, 'capacity')
    doc.add(5, 'graph_prototypes:')
    doc.add(6, f'- uuid: {uid("gproto", "fs")}')
    doc.add(7, "name: 'Filesystem {#FSNAME}: Used %'")
    doc.add(7, 'graph_items:')
    doc.add(8, '- color: 2774A4')
    doc.add(9, 'item:')
    doc.add(10, f'host: {TPL}')
    doc.add(10, "key: 'sap.host.vfs.fs.pused[{#SNMPINDEX}]'")


def _dashboard(doc: Doc) -> None:
    doc.add(3, 'dashboards:')
    doc.add(4, f'- uuid: {uid("dash", "health")}')
    doc.add(5, 'name: Health')
    doc.add(5, 'pages:')
    doc.add(6, '- name: Overview')
    doc.add(7, 'widgets:')
    item_tile(doc, 8, 'sap.host.snmp.available', None, None, 18, 'SSNMP', 'SNMP')
    item_tile(doc, 8, 'sap.host.cpu.util', 18, None, 18, 'SCPU', 'CPU')
    item_tile(doc, 8, 'sap.host.memory.pused', 36, None, 18, 'SMEM', 'Memory')
    item_tile(doc, 8, 'sap.host.load[15m]', 54, None, 18, 'SLOAD', 'Load 15m')
    doc.add(8, '- type: problems')
    doc.add(9, 'name: Problems')
    doc.add(9, "y: '4'")
    doc.add(9, "width: '72'")
    doc.add(9, "height: '3'")
    doc.add(9, 'fields:')
    doc.add(10, '- type: STRING')
    doc.add(11, 'name: reference')
    doc.add(11, 'value: SPROB')
    doc.add(10, '- type: INTEGER')
    doc.add(11, 'name: show')
    doc.add(11, "value: '3'")
    svg_graph(doc, 8, 'CPU / load', [('2774A4', 'sap.host.cpu.util'), ('F2B90D', 'sap.host.load[15m]')], y=7, ref='SCPUG')
    svg_graph(doc, 8, 'Memory / swap', [('199C0D', 'sap.host.memory.pused'), ('E97659', 'sap.host.swap.pused')], x=36, y=7, ref='SMEMG')

    doc.add(6, '- name: Application')
    doc.add(7, 'widgets:')
    item_tile(doc, 8, 'sap.app.promonitor', None, None, 18, 'SPROMO', 'Promonitor')
    item_tile(doc, 8, 'sap.app.abap.errors', 18, None, 18, 'SABAP', 'ABAP errors')
    item_tile(doc, 8, 'sap.app.idoc.errors', 36, None, 18, 'SIDOC', 'IDoc errors')
    item_tile(doc, 8, 'sap.app.qrfc.errors', 54, None, 18, 'SQRFC', 'qRFC errors')
    item_tile(doc, 8, 'sap.app.job.alerts', None, 4, 18, 'SJOB', 'Job alerts')
    item_tile(doc, 8, 'sap.app.syslog.alerts', 18, 4, 18, 'SLOG', 'Syslog')
    doc.add(8, '- type: problems')
    doc.add(9, 'name: Application problems')
    doc.add(9, "x: '36'")
    doc.add(9, "y: '4'")
    doc.add(9, "width: '36'")
    doc.add(9, "height: '4'")
    doc.add(9, 'fields:')
    doc.add(10, '- type: STRING')
    doc.add(11, 'name: reference')
    doc.add(11, 'value: SAPPROB')
    doc.add(10, '- type: INTEGER')
    doc.add(11, 'name: show')
    doc.add(11, "value: '3'")
    doc.add(10, '- type: STRING')
    doc.add(11, 'name: tags.0.tag')
    doc.add(11, 'value: component')
    doc.add(10, '- type: STRING')
    doc.add(11, 'name: tags.0.value')
    doc.add(11, 'value: sap-application')

    doc.add(6, '- name: Interfaces')
    doc.add(7, 'widgets:')
    doc.add(8, '- type: graphprototype')
    doc.add(9, 'name: Interface traffic')
    doc.add(9, "width: '72'")
    doc.add(9, "height: '5'")
    doc.add(9, 'fields:')
    doc.add(10, '- type: GRAPH_PROTOTYPE')
    doc.add(11, 'name: graphid.0')
    doc.add(11, 'value:')
    doc.add(12, f'host: {TPL}')
    doc.add(12, "name: 'Interface {#IFDESCR}: Traffic'")
    doc.add(10, '- type: STRING')
    doc.add(11, 'name: reference')
    doc.add(11, 'value: SIFG')


def _valuemaps(doc: Doc) -> None:
    doc.add(3, 'valuemaps:')
    doc.add(4, f'- uuid: {uid("vm", "avail")}')
    doc.add(5, 'name: zabbix.host.available')
    doc.add(5, 'mappings:')
    for value, label in (('0', 'Down'), ('1', 'Up'), ('2', 'Unknown')):
        doc.add(6, f"- value: '{value}'")
        doc.add(7, f'newvalue: {label}')
    doc.add(4, f'- uuid: {uid("vm", "svc")}')
    doc.add(5, 'name: Service state')
    doc.add(5, 'mappings:')
    doc.add(6, "- value: '0'")
    doc.add(7, 'newvalue: Down')
    doc.add(6, "- value: '1'")
    doc.add(7, 'newvalue: Up')
    doc.add(4, f'- uuid: {uid("vm", "ident")}')
    doc.add(5, 'name: SAP host identity')
    doc.add(5, 'mappings:')
    doc.add(6, "- value: '0'")
    doc.add(7, 'newvalue: Other SNMP agent')
    doc.add(6, "- value: '1'")
    doc.add(7, 'newvalue: Linux Net-SNMP')
    doc.add(4, f'- uuid: {uid("vm", "if")}')
    doc.add(5, 'name: IF-MIB::ifStatus')
    doc.add(5, 'mappings:')
    for value, label in (
        ('1', 'up'),
        ('2', 'down'),
        ('3', 'testing'),
        ('4', 'unknown'),
        ('5', 'dormant'),
        ('6', 'notPresent'),
        ('7', 'lowerLayerDown'),
    ):
        doc.add(6, f"- value: '{value}'")
        doc.add(7, f'newvalue: {label}')


def write_yaml() -> Path:
    TEMPLATE_YAML.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE_YAML.write_text(render(), encoding='utf-8')
    return TEMPLATE_YAML


if __name__ == '__main__':
    print(write_yaml())
