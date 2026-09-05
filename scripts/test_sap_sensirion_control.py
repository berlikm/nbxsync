#!/usr/bin/env python3
"""Unit tests for the sapcontrol collector (no live SAP Host Agent)."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / 'zabbix/externalscripts/sap_sensirion.py'
COLLECTOR_WIN = ROOT / 'zabbix/externalscripts/sap_sensirion.ps1'
USERPARAMETER = ROOT / 'zabbix/userparameters/sap_sensirion.conf'
USERPARAMETER_WIN = ROOT / 'zabbix/userparameters/sap_sensirion.win.conf'

HANA_CLI = """\
05.09.2026 17:00:00
GetProcessList
OK
name, description, dispstatus, textstatus, starttime, elapsedtime, pid
hdbdaemon, HDB Daemon, GREEN, Running, 2026 01 01 00:00:00, 100:00:00, 100
hdbnameserver, HDB Nameserver, GREEN, Running, 2026 01 01 00:00:00, 100:00:00, 101
hdbindexserver, HDB Indexserver-HDB, GREEN, Running, 2026 01 01 00:00:00, 100:00:00, 102
"""

HANA_DOWN = """\
GetProcessList
OK
0 : name: hdbdaemon, description: HDB Daemon, dispstatus: GRAY, textstatus: Stopped, pid: 0
0 : name: hdbnameserver, description: HDB Nameserver, dispstatus: GRAY, textstatus: Stopped, pid: 0
"""

ABAP_CLI = """\
GetProcessList
OK
0 : name: disp+work, description: Dispatcher, dispstatus: GREEN, textstatus: Running, pid: 200
0 : name: msg_server, description: MessageServer, dispstatus: GREEN, textstatus: Running, pid: 201
0 : name: enserver, description: EnqueueServer, dispstatus: GREEN, textstatus: Running, pid: 202
0 : name: gwrd, description: Gateway, dispstatus: GREEN, textstatus: Running, pid: 203
"""

ABAP_GATEWAY_DOWN = """\
GetProcessList
OK
0 : name: disp+work, description: Dispatcher, dispstatus: GREEN, textstatus: Running, pid: 200
0 : name: gwrd, description: Gateway, dispstatus: GRAY, textstatus: Stopped, pid: 0
"""

JAVA_CLI = """\
GetProcessList
OK
0 : name: jstart, description: J2EE Server, dispstatus: YELLOW, textstatus: Starting, pid: 300
"""

ALERTS_CLI = """\
GetAlerts
OK
name, value, description, time
R3Abap Shortdumps, 3, ABAP runtime errors, 2026
IDoc Errors, 2, inbound IDoc, 2026
Background job cancelled, 1, Job alert, 2026
R3Enqueue Lock entries, 4, SM12, 2026
qRFC inbound queue, 5, inbound qRFC, 2026
qRFC outbound queue, 6, outbound qRFC, 2026
Spool errors, 1, TemSe, 2026
R3Syslog, 7, System log, 2026
Transactional RFC SM58, 8, tRFC, 2026
SM13 update requests, 9, V1 update, 2026
"""

INSTANCES = """
Inst Info : HDB - 00 - ch-sta-p-sh01 - 749, patch 211
Inst Info : MEP - 1 - ch-sta-p-me01 - 753, patch 100
"""

SOAP_PROCS = """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
  <SOAP-ENV:Body>
    <n0:GetProcessListResponse xmlns:n0="urn:SAPControl">
      <process>
        <item>
          <name>hdbnameserver</name>
          <description>HDB Nameserver</description>
          <dispstatus>SAPControl-GREEN</dispstatus>
          <textstatus>Running</textstatus>
        </item>
        <item>
          <name>hdbindexserver</name>
          <description>HDB Indexserver</description>
          <dispstatus>SAPControl-GREEN</dispstatus>
          <textstatus>Running</textstatus>
        </item>
      </process>
    </n0:GetProcessListResponse>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
"""

SOAP_ALERTS = """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
  <SOAP-ENV:Body>
    <n0:GetAlertsResponse xmlns:n0="urn:SAPControl">
      <alert>
        <item>
          <name>R3Abap Shortdumps</name>
          <value>2</value>
          <description>ABAP runtime errors</description>
        </item>
      </alert>
    </n0:GetAlertsResponse>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
"""


def load_collector():
    spec = importlib.util.spec_from_file_location('sap_sensirion_control', COLLECTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load collector')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SapControlCollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = load_collector()

    def test_files_ship_in_repo(self):
        self.assertTrue(COLLECTOR.is_file())
        self.assertTrue(COLLECTOR_WIN.is_file())
        self.assertTrue(USERPARAMETER.is_file())
        self.assertTrue(USERPARAMETER_WIN.is_file())
        conf = USERPARAMETER.read_text(encoding='utf-8')
        self.assertIn('UserParameter=sap.sensirion[*]', conf)
        self.assertNotIn('system.run', conf)
        win = USERPARAMETER_WIN.read_text(encoding='utf-8')
        self.assertIn('UserParameter=sap.sensirion[*]', win)
        self.assertIn('sap_sensirion.ps1', win)
        self.assertNotIn('system.run', win)
        self.assertNotIn('system.run', COLLECTOR_WIN.read_text(encoding='utf-8'))
        src = COLLECTOR.read_text(encoding='utf-8')
        self.assertNotIn('verify=False', src)
        self.assertNotIn('system.run', src)
        self.assertNotIn('RFC_READ_TABLE', src)
        self.assertNotIn('hdbsql', src.lower())
        self.assertNotIn('-pwd', src)
        self.assertIn('Z_GET_ST22', src)
        self.assertIn('44301', src)
        self.assertIn('/abapruntimeerror', src)
        self.assertNotIn('santaba/rest', src)
        win_src = COLLECTOR_WIN.read_text(encoding='utf-8')
        self.assertIn('Z_GET_ST22', win_src)
        self.assertNotIn('santaba/rest', win_src)
        self.assertIn('"$9"', conf)
        self.assertIn('"$9"', win)

    def test_hana_process_list_up(self):
        procs = self.c.parse_process_list(HANA_CLI)
        self.assertEqual(len(procs), 3)
        self.assertEqual(self.c.detect_kind(procs), 'hana')
        snap = self.c.metrics_from_snapshot(procs, [])
        self.assertEqual(snap['promonitor'], 1)
        self.assertEqual(snap['instance_status'], 1)
        self.assertEqual(snap['rfc_status'], 1)
        self.assertEqual(snap['kind'], 'hana')
        self.assertEqual(snap['abap_errors'], 0)

    def test_hana_gray_is_down(self):
        procs = self.c.parse_process_list(HANA_DOWN)
        self.assertEqual(self.c.instance_is_up(procs), 0)
        snap = self.c.metrics_from_snapshot(procs, [])
        self.assertEqual(snap['instance_status'], 0)
        self.assertEqual(snap['rfc_status'], 0)

    def test_abap_gateway_and_instance(self):
        up = self.c.parse_process_list(ABAP_CLI)
        self.assertEqual(self.c.detect_kind(up), 'abap')
        self.assertEqual(self.c.instance_is_up(up), 1)
        self.assertEqual(self.c.rfc_is_up(up, 1), 1)
        down = self.c.parse_process_list(ABAP_GATEWAY_DOWN)
        self.assertEqual(self.c.instance_is_up(down), 1)
        self.assertEqual(self.c.rfc_is_up(down, 1), 0)

    def test_java_yellow_counts_as_up(self):
        procs = self.c.parse_process_list(JAVA_CLI)
        self.assertEqual(self.c.detect_kind(procs), 'java')
        self.assertEqual(self.c.instance_is_up(procs), 1)

    def test_ccms_alert_mapping(self):
        alerts = self.c.parse_alerts(ALERTS_CLI)
        snap = self.c.metrics_from_snapshot(self.c.parse_process_list(ABAP_CLI), alerts)
        self.assertEqual(snap['abap_errors'], 3)
        self.assertEqual(snap['idoc_errors'], 2)
        self.assertEqual(snap['job_alerts'], 1)
        self.assertEqual(snap['locks'], 4)
        self.assertEqual(snap['qrfc_in'], 5)
        self.assertEqual(snap['qrfc_out'], 6)
        self.assertEqual(snap['spool_errors'], 1)
        self.assertEqual(snap['syslog_alerts'], 7)
        self.assertEqual(snap['trfc_errors'], 8)
        self.assertEqual(snap['update_requests'], 9)

    def test_list_instances_and_sid_filter(self):
        rows = self.c.parse_list_instances(INSTANCES)
        self.assertEqual(
            [(row['sid'], row['nr']) for row in rows],
            [('HDB', '00'), ('MEP', '01')],
        )

    def test_soap_parsers(self):
        procs = self.c.parse_soap_process_list(SOAP_PROCS)
        self.assertEqual(self.c.detect_kind(procs), 'hana')
        self.assertEqual(self.c.instance_is_up(procs), 1)
        alerts = self.c.parse_soap_alerts(SOAP_ALERTS)
        self.assertEqual(self.c.count_alerts(alerts, 'abap_errors'), 2)

    def test_merge_worst_instance(self):
        hana = self.c.metrics_from_snapshot(self.c.parse_process_list(HANA_CLI), [])
        down = self.c.metrics_from_snapshot(self.c.parse_process_list(HANA_DOWN), [])
        merged = self.c.merge_metrics([hana, down])
        self.assertEqual(merged['instance_status'], 0)
        self.assertEqual(merged['promonitor'], 1)
        self.assertEqual(merged['kind'], 'hana')

    def test_json_roundtrip_keys(self):
        snap = self.c.metrics_from_snapshot(self.c.parse_process_list(HANA_CLI), [])
        payload = json.loads(self.c.format_value(snap, 'json'))
        for key in self.c.METRIC_KEYS:
            self.assertIn(key, payload)
        self.assertEqual(self.c.format_value(snap, 'instance.status'), '1')
        self.assertIsNone(self.c.format_value(snap, 'nope'))

    def test_validate_rejects_shell_meta(self):
        self.assertIsNone(self.c._validate('00;id', '', ''))
        self.assertIsNone(self.c._validate('00', 'HD;B', ''))
        self.assertIsNone(self.c._validate('00', 'HDB', '127.0.0.1;id'))
        self.assertEqual(self.c._validate('0', 'hdb', ''), ('0', 'hdb', ''))
        self.assertEqual(self.c._validate('{$SAP.INSTANCE}', '{$SAP.SID}', ''), ('', '', ''))

    def test_st22_count_and_api_validate(self):
        xml_text = """<?xml version="1.0"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
          <soapenv:Body>
            <n0:Z_GET_ST22Response xmlns:n0="urn:sap-com:document:sap:rfc:functions">
              <ET_INFOTAB>
                <item><PROGRAMNAME>ZTEST</PROGRAMNAME><DUMPID>TIME_OUT</DUMPID></item>
                <item><PROGRAMNAME></PROGRAMNAME></item>
                <item><PROGRAMNAME>SAPMSSY1</PROGRAMNAME></item>
              </ET_INFOTAB>
            </n0:Z_GET_ST22Response>
          </soapenv:Body>
        </soapenv:Envelope>"""
        self.assertEqual(self.c.count_st22_dumps(xml_text), 2)
        self.assertIsNone(self.c.st22_call('', '44301', '/abapruntimeerror', 'USER', 'x'))
        self.assertIsNone(self.c.st22_call('host', '44301', '/abapruntimeerror', '', 'x'))
        self.assertIsNone(self.c._validate_api('bad;host', '44301', '/abapruntimeerror', 'USER'))
        api = self.c._validate_api('ch-sta-p-sh01', '', '', 'C_PROMONITOR')
        self.assertEqual(api['port'], '44301')
        self.assertEqual(api['path'], '/abapruntimeerror')
        self.assertEqual(api['user'], 'C_PROMONITOR')

    def test_st22_overrides_ccms_when_soap_returns(self):
        snap = self.c.metrics_from_snapshot(self.c.parse_process_list(HANA_CLI), self.c.parse_alerts(ALERTS_CLI))
        self.assertEqual(snap['abap_errors'], 3)

        def fake_st22(*_args, **_kwargs):
            return '<x><item><PROGRAMNAME>ZTEST</PROGRAMNAME></item></x>'

        self.c.st22_call = fake_st22
        data = self.c.merge_metrics([snap])
        data['abap_source'] = 'ccms'
        xml_text = fake_st22()
        data['abap_errors'] = self.c.count_st22_dumps(xml_text)
        data['abap_source'] = 'st22'
        self.assertEqual(data['abap_errors'], 1)
        self.assertEqual(data['abap_source'], 'st22')

    def test_main_unknown_metric(self):
        from io import StringIO
        from contextlib import redirect_stdout

        buf = StringIO()
        with redirect_stdout(buf):
            rc = self.c.main(['sap_sensirion.py', 'not-a-metric'])
        self.assertEqual(rc, 0)
        self.assertIn('ZBX_NOTSUPPORTED', buf.getvalue())


if __name__ == '__main__':
    unittest.main()
