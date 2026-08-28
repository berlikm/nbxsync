#!/usr/bin/env python3
"""XIQ-SE / ExtremeControl Observability contract (no Django, no live NBI)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from extremecontrol_snmp import SNMP_TEMPLATE_NAME, SNMP_YAML

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / 'zabbix/templates/xiqse_observability'
NAC_TEMPLATE_DIR = ROOT / 'zabbix/templates/extremecontrol_observability'
JS_DIR = TEMPLATE_DIR / 'js'
FIXTURES = TEMPLATE_DIR / 'fixtures'
SE_YAML = TEMPLATE_DIR / 'template_xiqse_observability.yaml'
NAC_YAML = NAC_TEMPLATE_DIR / 'template_extremecontrol_observability.yaml'

SE_TEMPLATE_NAME = 'XIQ-SE Observability'
NAC_TEMPLATE_NAME = 'ExtremeControl Observability'
TEMPLATE_GROUP = 'Templates/Network devices'
SE_TEMPLATE_RULE = 'XIQ-SE'
SE_PLATFORM_PATTERN = r'XIQ.?SE|Site Engine|NetSight'
XIQSE_FQDN_MACRO = '{$XIQSE.API.FQDN}'
XIQSE_FQDN_JINJA = '{{ object.primary_ip4.address.ip }}'
NAC_PORTAL_FQDN_MACRO = '{$NAC.PORTAL.FQDN}'
NAC_ROLE = 'NAC'
APPLY_FLAG = '--apply-xiqse'
CHECK_FLAG = '--check-xiqse'

TEMPLATE_FILES = {
    SE_TEMPLATE_NAME: SE_YAML,
    NAC_TEMPLATE_NAME: NAC_YAML,
    SNMP_TEMPLATE_NAME: SNMP_YAML,
}

HEALTH_JS = ('nbi_metrics.js', 'http_nbi.js', 'collect_health.js')
LICENSES_JS = ('nbi_metrics.js', 'http_nbi.js', 'collect_licenses.js')
PILOT_JS = ('nbi_metrics.js', 'http_nbi.js', 'collect_pilot.js')
LLD_JS = ('nbi_metrics.js', 'lld_engines.js')

FORBIDDEN_SNIPPETS = (
    'mutation',
    'enforceNacEnginesAll',
    'net.udp.service',
    'system.run',
    'verify=False',
    'icmpping',
    '{HOST.HOST}',
    '{HOST.CONN}',
)

SE_ITEM_KEYS = {
    'xiqse.nbi.health',
    'xiqse.nbi.licenses',
    'xiqse.nbi.pilot',
    'xiqse.nbi.available',
    'xiqse.nbi.error',
    'xiqse.nbi.version',
    'xiqse.nbi.uptime',
    'xiqse.nbi.heap.used',
    'xiqse.nbi.heap.max',
    'xiqse.nbi.heap.pct',
    'xiqse.nbi.ram.free',
    'xiqse.nbi.ram.total',
    'xiqse.nbi.threads',
    'xiqse.engine.count',
    'xiqse.nac.used24h',
    'xiqse.nac.users24h',
    'xiqse.nac.remaining',
    'xiqse.nac.used.pct',
    'xiqse.nac.fetched',
    'xiqse.nac.truncated',
    'xiqse.nac.ok',
    'xiqse.nac.error',
    'xiqse.pilot.used',
    'xiqse.pilot.remaining',
    'xiqse.pilot.ok',
    'xiqse.nav.used',
    'xiqse.nav.remaining',
    'xiqse.lic.pending',
    'xiqse.lic.platformone',
    'net.tcp.service[tcp,{$XIQSE.API.FQDN},{$XIQSE.API.PORT}]',
    'web.certificate.get[{$XIQSE.API.FQDN},{$XIQSE.API.PORT}]',
    'xiqse.tls.not_after',
    'zabbix[host,,items_unsupported]',
}

SE_DISCOVERY_KEYS = {'xiqse.engine.discovery'}
SE_ITEM_PROTOTYPE_KEYS = {
    'xiqse.engine.licensed[{#ENGINE.IP}]',
    'xiqse.engine.connected[{#ENGINE.IP}]',
    'xiqse.engine.needs_enforce[{#ENGINE.IP}]',
    'xiqse.engine.freeradius[{#ENGINE.IP}]',
    'xiqse.engine.capacity[{#ENGINE.IP}]',
    'xiqse.engine.version[{#ENGINE.IP}]',
    'xiqse.engine.used24h[{#ENGINE.IP}]',
    'xiqse.engine.auth.age[{#ENGINE.IP}]',
}
SE_TRIGGER_NAMES = {
    'XIQ-SE: NBI unexpected response',
    'XIQ-SE: no NBI data for 15m',
    'XIQ-SE: HTTPS 8443 down',
    'XIQ-SE: no Control engines discovered',
    'XIQ-SE: 24h end-system census truncated',
    'XIQ-SE: NAC census failed',
    'XIQ-SE: NAC license seats exhausted',
    'XIQ-SE: NAC license seats high',
    'XIQ-SE: Pilot licenses exhausted',
    'XIQ-SE: few Pilot licenses remaining',
    'XIQ-SE: Navigator licenses exhausted',
    'XIQ-SE: few Navigator licenses remaining',
    'XIQ-SE: unplanned reboot',
    'XIQ-SE: TLS certificate expires soon',
    'XIQ-SE: version has changed',
    'XIQ-SE: unsupported items present',
    'XIQ-SE: Pilot census failed',
}
SE_TRIGGER_PROTOTYPE_NAMES = {
    'XIQ-SE engine {#ENGINE.NAME}: disconnected from Site Engine',
    'XIQ-SE engine {#ENGINE.NAME}: needs enforce',
    'XIQ-SE engine {#ENGINE.NAME}: FreeRADIUS disabled',
    'XIQ-SE engine {#ENGINE.NAME}: 24h unique MACs at hardware capacity',
    'XIQ-SE engine {#ENGINE.NAME}: not forwarding auth logs',
}
NAC_ITEM_KEYS = {
    'net.tcp.service[tcp,,{$NAC.PORTAL.PORT}]',
    'web.certificate.get[{$NAC.PORTAL.FQDN},{$NAC.PORTAL.PORT}]',
    'nac.tls.not_after',
}
NAC_TRIGGER_NAMES = {
    'ExtremeControl: portal TCP 8444 down',
    'ExtremeControl: TLS certificate expires soon',
}

DASHBOARD_NAMES = {'Health', 'Engines'}


def js_dir(*names: str) -> str:
    chunks = [(JS_DIR / name).read_text(encoding='utf-8').rstrip() for name in names]
    return '\n\n'.join(chunks) + '\n'


def health_script() -> str:
    return js_dir(*HEALTH_JS)


def licenses_script() -> str:
    return js_dir(*LICENSES_JS)


def pilot_script() -> str:
    return js_dir(*PILOT_JS)


def lld_script() -> str:
    return js_dir(*LLD_JS)


def extract_engine_script(field: str, missing: str) -> str:
    return (
        js_dir('extract_engine.js')
        + '\n'
        + 'var payload;\n'
        + 'try {\n'
        + '  payload = JSON.parse(value);\n'
        + "} catch (error) {\n"
        + "  throw 'XIQ-SE engine field: invalid JSON';\n"
        + '}\n'
        + f"return pickEngineField(payload, '{{#ENGINE.IP}}', '{field}', {missing});\n"
    )


def extract_license_engine_script(field: str, missing: str) -> str:
    return (
        js_dir('extract_engine.js')
        + '\n'
        + 'var payload;\n'
        + 'try {\n'
        + '  payload = JSON.parse(value);\n'
        + "} catch (error) {\n"
        + "  throw 'XIQ-SE engine license field: invalid JSON';\n"
        + '}\n'
        + f"return pickLicenseEngineField(payload, '{{#ENGINE.IP}}', '{field}', {missing});\n"
    )


def platform_is_xiqse(name: str | None) -> bool:
    return bool(name) and re.search(SE_PLATFORM_PATTERN, name, re.I) is not None


def load_se_template() -> dict:
    import yaml

    doc = yaml.safe_load(SE_YAML.read_text(encoding='utf-8'))
    return doc['zabbix_export']['templates'][0]


def load_nac_template() -> dict:
    import yaml

    doc = yaml.safe_load(NAC_YAML.read_text(encoding='utf-8'))
    return doc['zabbix_export']['templates'][0]


def zerotouch_source() -> str:
    return (ROOT / 'scripts/configure_nbxsync_zerotouch.py').read_text(encoding='utf-8')


def network_source() -> str:
    return (ROOT / 'scripts/configure_nbxsync_network.py').read_text(encoding='utf-8')


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))


def run_node(script: str, *, extra: str = '') -> str:
    import shutil
    import tempfile

    node = shutil.which('node') or '/exec-daemon/node'
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as handle:
        handle.write(script)
        handle.write('\n')
        handle.write(extra)
        path = handle.name
    proc = subprocess.run([node, path], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or 'node failed').strip())
    return (proc.stdout or '').strip()


def run_metrics_json(expr: str, *, prelude: str = '') -> object:
    metrics = (JS_DIR / 'nbi_metrics.js').read_text(encoding='utf-8')
    script = f'{metrics}\n{prelude}\nconsole.log(JSON.stringify({expr}));\n'
    return json.loads(run_node(script))


def run_lld(health: dict) -> list:
    metrics = (JS_DIR / 'nbi_metrics.js').read_text(encoding='utf-8')
    body = (JS_DIR / 'lld_engines.js').read_text(encoding='utf-8')
    wrapped = (
        metrics
        + '\nfunction __lld(value) {\n'
        + body
        + '\n}\nconsole.log(__lld('
        + json.dumps(json.dumps(health))
        + '));\n'
    )
    return json.loads(run_node(wrapped))


def bump(text: str, spaces: int = 4) -> str:
    pad = ' ' * spaces
    return '\n'.join(pad + line if line else line for line in text.split('\n'))


def yaml_literal(text: str, indent: int) -> str:
    pad = ' ' * indent
    lines = text.replace('\r\n', '\n').split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]
    return '\n'.join(pad + line if line else pad.rstrip() for line in lines)
