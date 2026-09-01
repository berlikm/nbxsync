#!/usr/bin/env python3
"""ExtremeCloud IQ by HTTP contract (no Django, no live Cloud API)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / 'zabbix/templates/extremecloud_iq_http'
JS_DIR = TEMPLATE_DIR / 'js'
FIXTURES = TEMPLATE_DIR / 'fixtures'
CLOUD_YAML = TEMPLATE_DIR / 'template_extremecloud_iq_http.yaml'

CLOUD_TEMPLATE_NAME = 'ExtremeCloud IQ by HTTP'
TEMPLATE_GROUP = 'Templates/Network devices'
CLOUD_TEMPLATE_RULE = 'ExtremeCloud IQ'
APPLY_FLAG = '--apply-xiq-cloud'
CHECK_FLAG = '--check-xiq-cloud'

TOKEN_CG_NAME = 'ExtremeCloud IQ API'
TOKEN_MACRO = '{$XIQ.CLOUD.API.TOKEN}'
API_URL_MACRO = '{$XIQ.CLOUD.API.URL}'
API_URL_DEFAULT = 'https://api.extremecloudiq.com'

TEMPLATE_FILES = {
    CLOUD_TEMPLATE_NAME: CLOUD_YAML,
}

ACCOUNT_JS = ('http_xiq.js', 'collect_account.js')
OPS_JS = ('http_xiq.js', 'collect_ops.js')

FORBIDDEN_SNIPPETS = (
    'mutation',
    '/account/viq/:backup',
    '/:reset',
    '/:unmanage',
    'net.udp.service',
    'system.run',
    'verify=False',
    'icmpping',
    '{HOST.HOST}',
    '{HOST.CONN}',
    '/nbi/graphql',
    'collect_health.js',
    '581-320',
    '581 − 320',
    'request.post(',
    '{$XIQ.PILOT.TOTAL}-last(',
)

CLOUD_ITEM_KEYS = {
    'xiq.cloud.account',
    'xiq.cloud.ops',
    'xiq.cloud.available',
    'xiq.cloud.error',
    'xiq.cloud.customer',
    'xiq.cloud.expired',
    'xiq.cloud.vhm.status',
    'xiq.cloud.vhm.active',
    'xiq.cloud.token.ttl',
    'xiq.cloud.token.known',
    'xiq.cloud.license.count',
    'xiq.cloud.license.types',
    'xiq.cloud.pilot.present',
    'xiq.cloud.pilot.have',
    'xiq.cloud.pilot.activated',
    'xiq.cloud.pilot.available',
    'xiq.cloud.pilot.expire',
    'xiq.cloud.nav.present',
    'xiq.cloud.nav.have',
    'xiq.cloud.nav.activated',
    'xiq.cloud.nav.available',
    'xiq.cloud.nav.expire',
    'xiq.cloud.copilot.have',
    'xiq.cloud.copilot.activated',
    'xiq.cloud.copilot.available',
    'xiq.cloud.nac.present',
    'xiq.cloud.nac.have',
    'xiq.cloud.nac.activated',
    'xiq.cloud.nac.available',
    'xiq.cloud.backup.time',
    'xiq.cloud.backup.age',
    'xiq.cloud.backup.name',
    'xiq.cloud.devices.total',
    'xiq.cloud.devices.managed',
    'xiq.cloud.devices.connected',
    'xiq.cloud.devices.disconnected',
    'xiq.cloud.ops.ok',
    'xiq.cloud.ops.error',
    'zabbix[host,,items_unsupported]',
}

CLOUD_TRIGGER_NAMES = {
    'ExtremeCloud IQ: API unexpected response',
    'ExtremeCloud IQ: no API data for 20m',
    'ExtremeCloud IQ: API token expires soon',
    'ExtremeCloud IQ: VIQ expired',
    'ExtremeCloud IQ: VHM not ACTIVE',
    'ExtremeCloud IQ: no license rows',
    'ExtremeCloud IQ: last CONFIG backup stale',
    'ExtremeCloud IQ: Pilot Cloud available is 0',
    'ExtremeCloud IQ: Navigator Cloud available is 0',
    'ExtremeCloud IQ: Pilot SKU expires soon',
    'ExtremeCloud IQ: Navigator SKU expires soon',
    'ExtremeCloud IQ: unsupported items present',
}

DASHBOARD_NAMES = {'Health'}


def js_dir(*names: str) -> str:
    chunks = [(JS_DIR / name).read_text(encoding='utf-8').rstrip() for name in names]
    return '\n\n'.join(chunks) + '\n'


def account_script() -> str:
    return js_dir(*ACCOUNT_JS)


def ops_script() -> str:
    return js_dir(*OPS_JS)


def load_cloud_template() -> dict:
    import yaml

    doc = yaml.safe_load(CLOUD_YAML.read_text(encoding='utf-8'))
    return doc['zabbix_export']['templates'][0]


def zerotouch_source() -> str:
    return (ROOT / 'scripts/configure_nbxsync_zerotouch.py').read_text(encoding='utf-8')


def network_source() -> str:
    return (ROOT / 'scripts/configure_nbxsync_network.py').read_text(encoding='utf-8')


def nbi_health_source() -> str:
    return (ROOT / 'zabbix/templates/xiqse_observability/js/collect_health.js').read_text(encoding='utf-8')


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


def run_cloud_json(expr: str, *, prelude: str = '') -> object:
    metrics = (JS_DIR / 'http_xiq.js').read_text(encoding='utf-8')
    script = f'{metrics}\n{prelude}\nconsole.log(JSON.stringify({expr}));\n'
    return json.loads(run_node(script))


def bump(text: str, spaces: int = 4) -> str:
    pad = ' ' * spaces
    return '\n'.join(pad + line if line else line for line in text.split('\n'))


def yaml_literal(text: str, indent: int) -> str:
    pad = ' ' * indent
    lines = text.replace('\r\n', '\n').split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]
    return '\n'.join(pad + line if line else pad.rstrip() for line in lines)
