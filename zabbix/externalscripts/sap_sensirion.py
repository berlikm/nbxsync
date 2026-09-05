#!/usr/bin/env python3
"""SAP application collector — Host Agent / sapstartsrv, not Promonitor.

LogicMonitor's C_PROMONITOR / DNUS Groovy talked to the same local SAP
Start Service that is already on every HANA, NetWeaver ABAP, and ME Java
host. DNUS is gone. This script is the replacement: one JSON snapshot
from sapcontrol (preferred) or SOAP to localhost:5NN13.

What this is:
  GetProcessList  -> instance status, RFC/gateway process, HANA/ABAP/Java kind
  GetAlerts       -> CCMS-style counts mapped onto the old LM names

What this is not:
  ST22 / SM13 / SM37 / SM12 / SM58 / SM21 / EDIDS via RFC
  HANA SQL (indexserver memory, connections, savepoints)
  A Promonitor REST clone
  Groovy on the Zabbix proxy or arbitrary agent remote commands

Run on the SAP host via the Zabbix agent UserParameter (agent :10050 is
already on CG SAP Agent+SNMP). Stdlib only. No passwords.

Usage:
  sap_sensirion.py json [instance] [sid] [host]
  sap_sensirion.py instance.status [instance] [sid] [host]
"""

from __future__ import print_function

import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

try:
    from urllib.error import URLError
    from urllib.request import Request, urlopen
except ImportError:  # pragma: no cover - Py2 leftover, keep import-safe
    from urllib2 import Request, URLError, urlopen  # type: ignore


NOTSUPPORTED = 'ZBX_NOTSUPPORTED'
TIMEOUT_SEC = 8
HOSTCTRL_SAPCONTROL = '/usr/sap/hostctrl/exe/sapcontrol'
HOSTCTRL_SAPHOSTCTRL = '/usr/sap/hostctrl/exe/saphostctrl'
WIN_SAPCONTROL = (
    r'C:\Program Files\SAP\hostctrl\exe\sapcontrol.exe',
    r'C:\usr\sap\hostctrl\exe\sapcontrol.exe',
    r'C:\Program Files (x86)\SAP\hostctrl\exe\sapcontrol.exe',
)
WIN_SAPHOSTCTRL = (
    r'C:\Program Files\SAP\hostctrl\exe\saphostctrl.exe',
    r'C:\usr\sap\hostctrl\exe\saphostctrl.exe',
    r'C:\Program Files (x86)\SAP\hostctrl\exe\saphostctrl.exe',
)
SOAP_NS = 'urn:SAPControl'

METRIC_KEYS = (
    'promonitor',
    'instance_status',
    'abap_errors',
    'idoc_errors',
    'job_alerts',
    'locks',
    'qrfc_in',
    'qrfc_out',
    'rfc_status',
    'spool_errors',
    'syslog_alerts',
    'trfc_errors',
    'update_requests',
)

CLI_TO_JSON = {
    'promonitor': 'promonitor',
    'instance.status': 'instance_status',
    'abap.errors': 'abap_errors',
    'idoc.errors': 'idoc_errors',
    'job.alerts': 'job_alerts',
    'locks': 'locks',
    'qrfc.in': 'qrfc_in',
    'qrfc.out': 'qrfc_out',
    'rfc.status': 'rfc_status',
    'spool.errors': 'spool_errors',
    'syslog.alerts': 'syslog_alerts',
    'trfc.errors': 'trfc_errors',
    'update.requests': 'update_requests',
}

HANA_PROCS = (
    'hdbdaemon',
    'hdbnameserver',
    'hdbindexserver',
    'hdbcompileserver',
    'hdbpreprocessor',
    'hdbwebdispatcher',
    'hdbxsengine',
    'hdbdiserver',
    'hdbscriptserver',
    'hdbdpserver',
    'hdbxscontroller',
)
ABAP_PROCS = ('disp+work', 'msg_server', 'enserver', 'enrepserver', 'gwrd', 'icman', 'igswd')
JAVA_PROCS = ('jstart', 'jcontrol', 'jc00', 'jc01', 'jc02', 'sdm')

HANA_CRITICAL = ('hdbnameserver', 'hdbindexserver', 'hdbdaemon')
ABAP_CRITICAL = ('disp+work', 'msg_server')
JAVA_CRITICAL = ('jstart', 'jcontrol')

ALERT_KEYWORDS = {
    'abap_errors': ('shortdump', 'short dump', 'runtime error', 'abap dump', 'r3abap'),
    'idoc_errors': ('idoc',),
    'job_alerts': ('background job', 'job alert', 'btc job', 'sjob', 'job cancelled'),
    'locks': ('enqueue', 'lock entry', 'sm12', 'r3enqueue'),
    'qrfc_in': ('qrfc in', 'inbound queue', 'inbound qrfc', 'qin scheduler'),
    'qrfc_out': ('qrfc out', 'outbound queue', 'outbound qrfc', 'qout scheduler'),
    'spool_errors': ('spool', 'temse'),
    'syslog_alerts': ('syslog', 'r3syslog', 'system log'),
    'trfc_errors': ('trfc', 'transactional rfc', 'sm58'),
    'update_requests': ('update request', 'update record', 'sm13', 'v1 update', 'v2 update'),
}

_KV_LINE = re.compile(r'^\s*\d+\s*:\s*(.+)$')
_KV_PAIR = re.compile(r'(\w+)\s*:\s*(.*?)(?=,\s*\w+\s*:|$)')
_INST_INFO = re.compile(
    r'Inst Info\s*:\s*(\S+)\s*-\s*(\d{1,2})\s*-\s*(\S+)',
    re.IGNORECASE,
)
_SID_OK = re.compile(r'^[A-Za-z0-9]{0,3}$')
_NN_OK = re.compile(r'^\d{1,2}$')
_HOST_OK = re.compile(r'^[A-Za-z0-9._-]*$')


def _norm_status(value):
    text = (value or '').strip().upper()
    text = text.replace('SAPCONTROL-', '')
    if text in ('GREEN', 'YELLOW', 'GRAY', 'GREY', 'RED'):
        return 'GRAY' if text == 'GREY' else text
    return text or 'GRAY'


def _norm_name(value):
    return (value or '').strip().lower()


def _proc_kind(name):
    n = _norm_name(name)
    for prefix in HANA_PROCS:
        if n == prefix or n.startswith(prefix):
            return 'hana'
    for prefix in ABAP_PROCS:
        if n == prefix or n.startswith(prefix):
            return 'abap'
    for prefix in JAVA_PROCS:
        if n == prefix or n.startswith(prefix):
            return 'java'
    return 'other'


def detect_kind(processes):
    kinds = set(_proc_kind(p.get('name')) for p in processes)
    kinds.discard('other')
    if not kinds:
        return 'unknown'
    if kinds == {'hana'}:
        return 'hana'
    if kinds == {'abap'}:
        return 'abap'
    if kinds == {'java'}:
        return 'java'
    return 'mixed'


def _is_critical(name, kind):
    n = _norm_name(name)
    groups = []
    if kind in ('hana', 'mixed', 'unknown'):
        groups.append(HANA_CRITICAL)
    if kind in ('abap', 'mixed', 'unknown'):
        groups.append(ABAP_CRITICAL)
    if kind in ('java', 'mixed', 'unknown'):
        groups.append(JAVA_CRITICAL)
    for group in groups:
        for prefix in group:
            if n == prefix or n.startswith(prefix):
                return True
    return False


def instance_is_up(processes):
    """1 if the SAP/HANA/ME instance is running, 0 otherwise.

    YELLOW is up (degraded). GRAY/RED on a critical process is down.
    HANA: nameserver + indexserver (or daemon) must not be GRAY/RED.
    ABAP PAS: disp+work. ASCS: msg_server. ME Java: jstart.
    """
    if not processes:
        return 0
    kind = detect_kind(processes)
    critical = [p for p in processes if _is_critical(p.get('name'), kind)]
    watch = critical or list(processes)
    bad = [p for p in watch if _norm_status(p.get('dispstatus')) in ('GRAY', 'RED')]
    if bad:
        return 0
    good = [p for p in watch if _norm_status(p.get('dispstatus')) in ('GREEN', 'YELLOW')]
    return 1 if good else 0


def rfc_is_up(processes, instance_up):
    """Gateway process health. Not SM59 destination status.

    ABAP/ME with gwrd: 1 only when every gwrd is GREEN or YELLOW.
    HANA-only / Java-only have no ABAP gateway — 1 when the instance is up.
    """
    gateways = [p for p in processes if _norm_name(p.get('name')).startswith('gwrd')]
    if gateways:
        return 1 if all(_norm_status(p.get('dispstatus')) in ('GREEN', 'YELLOW') for p in gateways) else 0
    return 1 if instance_up else 0


def _alert_text(alert):
    return ' '.join(
        (
            alert.get('name') or '',
            alert.get('description') or '',
            alert.get('value') or '',
        )
    ).lower()


def _alert_weight(alert):
    value = (alert.get('value') or '').strip()
    if re.fullmatch(r'\d+', value):
        return int(value)
    return 1


def count_alerts(alerts, field):
    keys = ALERT_KEYWORDS[field]
    total = 0
    for alert in alerts:
        blob = _alert_text(alert)
        if any(key in blob for key in keys):
            total += _alert_weight(alert)
    return total


def metrics_from_snapshot(processes, alerts, source='sapcontrol'):
    instance_up = instance_is_up(processes)
    kind = detect_kind(processes)
    data = {
        'promonitor': 1 if processes or alerts or source in ('sapcontrol', 'soap') else 0,
        'instance_status': instance_up,
        'rfc_status': rfc_is_up(processes, instance_up),
        'kind': kind,
        'source': source,
        'processes': len(processes),
        'alerts': len(alerts),
    }
    if processes or alerts:
        data['promonitor'] = 1
    for field in ALERT_KEYWORDS:
        data[field] = count_alerts(alerts, field)
    return data


def empty_metrics():
    data = {key: 0 for key in METRIC_KEYS}
    data['kind'] = 'unknown'
    data['source'] = 'none'
    data['processes'] = 0
    data['alerts'] = 0
    return data


def merge_metrics(rows):
    if not rows:
        return empty_metrics()
    out = empty_metrics()
    kinds = set()
    sources = set()
    out['promonitor'] = 1
    out['instance_status'] = 1
    out['rfc_status'] = 1
    for row in rows:
        kinds.add(row.get('kind') or 'unknown')
        sources.add(row.get('source') or 'none')
        out['instance_status'] = 1 if out['instance_status'] and row.get('instance_status') else 0
        out['rfc_status'] = 1 if out['rfc_status'] and row.get('rfc_status') else 0
        out['processes'] += int(row.get('processes') or 0)
        out['alerts'] += int(row.get('alerts') or 0)
        for field in ALERT_KEYWORDS:
            out[field] += int(row.get(field) or 0)
    kinds.discard('unknown')
    if len(kinds) == 1:
        out['kind'] = next(iter(kinds))
    elif kinds:
        out['kind'] = 'mixed'
    if 'sapcontrol' in sources:
        out['source'] = 'sapcontrol'
    elif 'soap' in sources:
        out['source'] = 'soap'
    return out


def _strip_ns(tag):
    if tag and '}' in tag:
        return tag.rsplit('}', 1)[-1]
    return tag or ''


def _row_from_pairs(pairs):
    row = {}
    for key, value in pairs:
        row[key.strip().lower()] = value.strip()
    return row


def _parse_kv_body(text, required):
    rows = []
    header = None
    for raw in (text or '').splitlines():
        line = raw.strip()
        if not line:
            continue
        kv_match = _KV_LINE.match(line)
        if kv_match:
            pairs = _KV_PAIR.findall(kv_match.group(1))
            row = _row_from_pairs(pairs)
            if any(row.get(key) for key in required):
                rows.append(row)
            continue
        if ',' in line and header is None and any(key in line.lower() for key in required):
            header = [part.strip().lower() for part in line.split(',')]
            continue
        if header and ',' in line:
            parts = [part.strip() for part in line.split(',')]
            row = {}
            for idx, key in enumerate(header):
                if idx < len(parts):
                    row[key] = parts[idx]
            if any(row.get(key) for key in required):
                rows.append(row)
    return rows


def parse_process_list(text):
    rows = _parse_kv_body(text, ('name',))
    out = []
    for row in rows:
        name = row.get('name')
        if not name or name.lower() == 'name':
            continue
        out.append(
            {
                'name': name,
                'description': row.get('description') or '',
                'dispstatus': _norm_status(row.get('dispstatus')),
                'textstatus': row.get('textstatus') or '',
            }
        )
    return out


def parse_alerts(text):
    rows = _parse_kv_body(text, ('name', 'description'))
    out = []
    for row in rows:
        name = row.get('name') or ''
        if name.lower() == 'name':
            continue
        out.append(
            {
                'name': name,
                'value': row.get('value') or '',
                'description': row.get('description') or '',
            }
        )
    return out


def parse_list_instances(text):
    rows = []
    for match in _INST_INFO.finditer(text or ''):
        rows.append(
            {
                'sid': match.group(1).upper(),
                'nr': match.group(2).zfill(2),
                'host': match.group(3),
            }
        )
    return rows


def parse_soap_items(xml_text, item_tag):
    if not (xml_text or '').strip():
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    rows = []
    for node in root.iter():
        if _strip_ns(node.tag).lower() != item_tag:
            continue
        row = {}
        for child in list(node):
            row[_strip_ns(child.tag).lower()] = (child.text or '').strip()
        if row:
            rows.append(row)
    return rows


def parse_soap_process_list(xml_text):
    rows = []
    for row in parse_soap_items(xml_text, 'item'):
        name = row.get('name')
        if not name:
            continue
        rows.append(
            {
                'name': name,
                'description': row.get('description') or '',
                'dispstatus': _norm_status(row.get('dispstatus')),
                'textstatus': row.get('textstatus') or '',
            }
        )
    return rows


def parse_soap_alerts(xml_text):
    rows = []
    for row in parse_soap_items(xml_text, 'item'):
        if not (row.get('name') or row.get('description')):
            continue
        rows.append(
            {
                'name': row.get('name') or '',
                'value': row.get('value') or '',
                'description': row.get('description') or '',
            }
        )
    return rows


def _cli_ok(text):
    blob = text or ''
    if re.search(r'^\s*FAIL\b', blob, re.MULTILINE | re.IGNORECASE):
        return False
    return bool(re.search(r'^\s*OK\b', blob, re.MULTILINE | re.IGNORECASE)) or (
        'name' in blob.lower() and 'dispstatus' in blob.lower()
    )


def _which(path):
    if not path or not os.path.isfile(path):
        return None
    if os.name == 'nt' or os.access(path, os.X_OK):
        return path
    return None


def find_sapcontrol():
    for path in (HOSTCTRL_SAPCONTROL,) + WIN_SAPCONTROL:
        found = _which(path)
        if found:
            return found
    return shutil.which('sapcontrol.exe' if os.name == 'nt' else 'sapcontrol')


def find_saphostctrl():
    for path in (HOSTCTRL_SAPHOSTCTRL,) + WIN_SAPHOSTCTRL:
        found = _which(path)
        if found:
            return found
    return shutil.which('saphostctrl.exe' if os.name == 'nt' else 'saphostctrl')


def run_cmd(argv, timeout=TIMEOUT_SEC):
    try:
        proc = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            universal_newlines=True,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.returncode, proc.stdout or '', proc.stderr or ''


def _prefix_cmds(binary):
    prefixes = [[]]
    if os.name != 'nt' and os.geteuid() != 0:
        prefixes.append(['sudo', '-n', '-u', 'sapadm'])
        prefixes.append(['sudo', '-n'])
    out = []
    for prefix in prefixes:
        out.append(prefix + [binary])
    return out


def sapcontrol_function(nr, function, host=''):
    binary = find_sapcontrol()
    if not binary:
        return None
    extra = []
    if host and host not in ('127.0.0.1', 'localhost'):
        extra.extend(['-host', host])
    for base in _prefix_cmds(binary):
        argv = base + ['-nr', nr, '-function', function] + extra
        result = run_cmd(argv)
        if result is None:
            continue
        _code, stdout, _stderr = result
        if _cli_ok(stdout):
            return stdout
    return None


def list_instances_cli(sid=''):
    binary = find_saphostctrl()
    if not binary:
        return []
    for base in _prefix_cmds(binary):
        result = run_cmd(base + ['-function', 'ListInstances'])
        if result is None:
            continue
        _code, stdout, _stderr = result
        rows = parse_list_instances(stdout)
        if rows:
            if sid:
                want = sid.upper()
                rows = [row for row in rows if row['sid'] == want]
            return rows
    return []


def soap_call(host, port, function, timeout=5):
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"'
        ' xmlns:s="%s"><SOAP-ENV:Body><s:%s/></SOAP-ENV:Body></SOAP-ENV:Envelope>'
    ) % (SOAP_NS, function)
    url = 'http://%s:%s/' % (host, port)
    req = Request(url, data=body.encode('utf-8'))
    req.add_header('Content-Type', 'text/xml; charset=utf-8')
    req.add_header('SOAPAction', '')
    try:
        resp = urlopen(req, timeout=timeout)
        payload = resp.read()
        if isinstance(payload, bytes):
            payload = payload.decode('utf-8', 'replace')
        return payload
    except (URLError, OSError, ValueError):
        return None


def instance_port(nr):
    return 50013 + int(nr) * 100


def collect_instance(nr, host=''):
    peer = host or '127.0.0.1'
    text = sapcontrol_function(nr, 'GetProcessList', host=host)
    alerts_text = sapcontrol_function(nr, 'GetAlerts', host=host) if text is not None else None
    source = 'sapcontrol'
    processes = parse_process_list(text or '')
    alerts = parse_alerts(alerts_text or '')
    if not processes:
        xml_procs = soap_call(peer, instance_port(nr), 'GetProcessList')
        xml_alerts = soap_call(peer, instance_port(nr), 'GetAlerts')
        processes = parse_soap_process_list(xml_procs or '')
        alerts = parse_soap_alerts(xml_alerts or '')
        source = 'soap'
    if not processes and not alerts:
        return None
    return metrics_from_snapshot(processes, alerts, source=source)


def resolve_instances(instance, sid):
    if instance:
        return [{'sid': (sid or '').upper(), 'nr': instance.zfill(2), 'host': ''}]
    return list_instances_cli(sid=sid)


def collect(instance='', sid='', host=''):
    rows = []
    targets = resolve_instances(instance, sid)
    if not targets and not instance:
        # Last resort: common HANA / NetWeaver instance numbers on the box.
        targets = [{'sid': (sid or '').upper(), 'nr': nn, 'host': ''} for nn in ('00', '01', '02')]
        guessed = True
    else:
        guessed = False
    for target in targets:
        row = collect_instance(target['nr'], host=host)
        if row:
            rows.append(row)
        elif not guessed and instance:
            return None
    if not rows:
        return None
    return merge_metrics(rows)


def _validate(instance, sid, host):
    instance = (instance or '').strip()
    sid = (sid or '').strip()
    host = (host or '').strip()
    if instance in ('-', '--', '{$SAP.INSTANCE}'):
        instance = ''
    if sid in ('-', '--', '{$SAP.SID}'):
        sid = ''
    if host in ('-', '--', '{$SAP.CONTROL.HOST}', 'localhost'):
        host = '' if host != 'localhost' else '127.0.0.1'
    if instance and not _NN_OK.match(instance):
        return None
    if sid and not _SID_OK.match(sid):
        return None
    if host and not _HOST_OK.match(host):
        return None
    return instance, sid, host


def format_value(data, metric):
    if metric == 'json':
        payload = {key: data.get(key, 0) for key in METRIC_KEYS}
        payload['kind'] = data.get('kind') or 'unknown'
        payload['source'] = data.get('source') or 'none'
        return json.dumps(payload, separators=(',', ':'), sort_keys=True)
    field = CLI_TO_JSON.get(metric)
    if field is None:
        return None
    return str(int(data.get(field) or 0))


def main(argv):
    if len(argv) < 2 or argv[1] in ('-h', '--help'):
        print('usage: sap_sensirion.py <json|metric> [instance] [sid] [host]', file=sys.stderr)
        return 2
    metric = argv[1].strip()
    if metric != 'json' and metric not in CLI_TO_JSON:
        print('%s: unknown metric' % NOTSUPPORTED)
        return 0
    parsed = _validate(
        argv[2] if len(argv) > 2 else '',
        argv[3] if len(argv) > 3 else '',
        argv[4] if len(argv) > 4 else '',
    )
    if parsed is None:
        print('%s: bad instance/sid/host' % NOTSUPPORTED)
        return 0
    instance, sid, host = parsed
    data = collect(instance=instance, sid=sid, host=host)
    if data is None:
        print('%s: sapcontrol not available' % NOTSUPPORTED)
        return 0
    text = format_value(data, metric)
    if text is None:
        print('%s: unknown metric' % NOTSUPPORTED)
        return 0
    print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
