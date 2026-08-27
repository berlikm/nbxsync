"""MSSQL Observability companion — named-instance Agent 2 coverage.

Stock ``MSSQL by Zabbix agent 2`` is one ``{$MSSQL.URI}`` (the default instance).
This companion discovers ``MSSQL$%`` Windows services via WMI and talks to each
named instance with ``sqlserver://localhost/{#MSSQL.INSTANCE}`` (plugin ≥ 7.0.6).

Do **not** nest the stock template (URI remains a single host macro).
Do **not** use ``service.discovery`` (collides with Windows by Zabbix agent).
Do **not** invent host prototypes, ODBC, or ICMP (Windows already has ping).
Import via ``configure_nbxsync_network.py --apply-mssql``. Zerotouch only
soft-assigns the companion after that YAML exists (optional, no HostSync).
Do **not** mute Test/Dev — backup USED flags stay ``1`` on every environment.

Zabbix 7.0 cannot nest discovery-under-discovery on the same host. Database and
Always On local-DB LLD is flattened: each named instance stamps
``{#MSSQL.INSTANCE}+{#DBNAME}`` (and AG group) into a catalog item, a host-level
``last_foreach`` merges those JSON catalogs, and a second LLD rule creates the
per-database items. Keys always include the instance name so they cannot collide
with stock ``mssql.db.*["{#DBNAME}"]``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

TEMPLATE_NAME = 'MSSQL Observability'
TEMPLATE_GROUP = 'Templates/Databases'
TEMPLATE_GROUP_UUID = '748ad4d098d447d492bb935c907f652f'
# Preserve the identity already imported in Zabbix Cloud so imports update it.
TEMPLATE_UUID = '52bd809ec8a54feb8364f3d13a9c8074'
DASHBOARD_UUID = 'b91d7e04c3a8456f8e12f6a0b4c8d931'

STOCK_TEMPLATE_NAME = 'MSSQL by Zabbix agent 2'

ZABBIX_TEMPLATE_PATH = (
    REPO_ROOT / 'zabbix' / 'templates' / 'mssql_observability' / 'template_mssql_observability.yaml'
)
TEMPLATE_FILES = {TEMPLATE_NAME: ZABBIX_TEMPLATE_PATH}

TEMPLATE_DIR = ZABBIX_TEMPLATE_PATH.parent
LLD_JS_PATH = TEMPLATE_DIR / 'lld_named_instances.js'
DB_CATALOG_JS_PATH = TEMPLATE_DIR / 'db_catalog.js'
LOCAL_DB_CATALOG_JS_PATH = TEMPLATE_DIR / 'local_db_catalog.js'
FLATTEN_LLD_JS_PATH = TEMPLATE_DIR / 'flatten_lld.js'
FIXTURES = TEMPLATE_DIR / 'fixtures'

# Unique vs Windows-by-agent ``service.discovery``. No ``$`` in the key
# (Zabbix treats ``$`` as end-of-line in some regex paths). JS then keeps
# only ``MSSQL$…`` and drops ``MSSQLSERVER`` / ``MSSQLFDLauncher``.
WMI_ITEM_KEY = (
    'wmi.getall[root\\cimv2,"SELECT Name,DisplayName,State,StartMode '
    "FROM Win32_Service WHERE Name LIKE 'MSSQL%'\"]"
)
WMI_DISCOVERY_KEY = WMI_ITEM_KEY
NAMED_INSTANCE_PREFIX = 'MSSQL$'
URI_PREFIX = 'sqlserver://localhost/'
# Preserve the deployed named-instance LLD rather than creating a second tree.
DISCOVERY_KEY = 'mssql.named.instance.discovery'
CENSUS_KEY = 'mssql.observability.instance.count'
DB_LLD_KEY = 'mssql.observability.database.discovery'
DB_LLDJSON_KEY = 'mssql.observability.database.lldjson'
DB_CATALOG_KEY = 'mssql.observability.db.catalog[{#MSSQL.INSTANCE}]'
DB_CATALOG_SEED_KEY = 'mssql.observability.db.catalog[_seed]'
LOCAL_LLD_KEY = 'mssql.observability.local_db.discovery'
LOCAL_LLDJSON_KEY = 'mssql.observability.local_db.lldjson'
LOCAL_CATALOG_KEY = 'mssql.observability.local_db.catalog[{#MSSQL.INSTANCE}]'
LOCAL_CATALOG_SEED_KEY = 'mssql.observability.local_db.catalog[_seed]'

PLUGIN_ARGS = '["{#MSSQL.URI}","{$MSSQL.USER}","{$MSSQL.PASSWORD}"]'
PING_KEY = f'mssql.ping{PLUGIN_ARGS}'
VERSION_KEY = f'mssql.version{PLUGIN_ARGS}'
PERF_KEY = f'mssql.perfcounter.get{PLUGIN_ARGS}'
JOB_KEY = f'mssql.job.status.get{PLUGIN_ARGS}'
BACKUP_KEY = f'mssql.last.backup.get{PLUGIN_ARGS}'
DB_KEY = f'mssql.db.get{PLUGIN_ARGS}'
LOCAL_DB_GET_KEY = f'mssql.local.db.get{PLUGIN_ARGS}'
AG_GET_KEY = f'mssql.availability.group.get{PLUGIN_ARGS}'

NAMED_URI = 'sqlserver://localhost/{#MSSQL.INSTANCE}'

BUFFER_RAW_KEY = 'mssql.observability.buffer_manager.raw[{#MSSQL.INSTANCE}]'
STATS_RAW_KEY = 'mssql.observability.sql_statistics.raw[{#MSSQL.INSTANCE}]'
LOCKS_RAW_KEY = 'mssql.observability.locks.raw[{#MSSQL.INSTANCE}]'
BUFFER_CACHE_KEY = 'mssql.observability.buffer_cache_hit_ratio[{#MSSQL.INSTANCE}]'
BATCH_RATE_KEY = 'mssql.observability.batch_requests_rate[{#MSSQL.INSTANCE}]'
PAGE_LIFE_KEY = 'mssql.observability.page_life_expectancy[{#MSSQL.INSTANCE}]'
LOCK_TIMEOUTS_KEY = 'mssql.observability.lock_timeouts_rate[{#MSSQL.INSTANCE}]'
DB_COUNT_KEY = 'mssql.observability.db.count[{#MSSQL.INSTANCE}]'
FAILED_JOBS_KEY = 'mssql.observability.failed_jobs[{#MSSQL.INSTANCE}]'

DB_PERF_RAW_KEY = 'mssql.observability.db.perf_raw[{#MSSQL.INSTANCE},{#DBNAME}]'
BACKUP_RAW_KEY = 'mssql.observability.backup.raw[{#MSSQL.INSTANCE},{#DBNAME}]'
DB_STATE_KEY = 'mssql.observability.db.state[{#MSSQL.INSTANCE},{#DBNAME}]'
BACKUP_FULL_KEY = 'mssql.observability.backup.full[{#MSSQL.INSTANCE},{#DBNAME}]'
BACKUP_DIFF_KEY = 'mssql.observability.backup.diff[{#MSSQL.INSTANCE},{#DBNAME}]'
BACKUP_LOG_KEY = 'mssql.observability.backup.log[{#MSSQL.INSTANCE},{#DBNAME}]'
BACKUP_RECOVERY_KEY = 'mssql.observability.backup.recovery_model[{#MSSQL.INSTANCE},{#DBNAME}]'
PERCENT_LOG_KEY = 'mssql.observability.db.percent_log_used[{#MSSQL.INSTANCE},{#DBNAME}]'
LOCAL_STATE_KEY = (
    'mssql.observability.local_db.state[{#MSSQL.INSTANCE},{#GROUP_NAME},{#DBNAME}]'
)
LOCAL_SUSPENDED_KEY = (
    'mssql.observability.local_db.is_suspended[{#MSSQL.INSTANCE},{#GROUP_NAME},{#DBNAME}]'
)
LOCAL_SYNC_KEY = (
    'mssql.observability.local_db.synchronization_health'
    '[{#MSSQL.INSTANCE},{#GROUP_NAME},{#DBNAME}]'
)

MACRO_INSTANCE_MATCHES = '{$MSSQL.INSTANCE.MATCHES}'
MACRO_INSTANCE_NOT_MATCHES = '{$MSSQL.INSTANCE.NOT_MATCHES}'
MACRO_INSTANCE_DISCOVERY_MIN = '{$MSSQL.INSTANCE.DISCOVERY.MIN}'
MACRO_BUFFER_CACHE_MIN = '{$MSSQL.BUFFER_CACHE.MIN}'
MACRO_PAGE_LIFE_MIN = '{$MSSQL.PAGE_LIFE.MIN}'
MACRO_DBNAME_MATCHES = '{$MSSQL.DBNAME.MATCHES}'
MACRO_DBNAME_NOT_MATCHES = '{$MSSQL.DBNAME.NOT_MATCHES}'
MACRO_BACKUP_FULL_USED = '{$MSSQL.BACKUP_FULL.USED}'
MACRO_BACKUP_LOG_USED = '{$MSSQL.BACKUP_LOG.USED}'
MACRO_BACKUP_DIFF_USED = '{$MSSQL.BACKUP_DIFF.USED}'

# Same defaults as stock 7.0-6. USED=1 on every environment (no Test/Dev mute).
TEMPLATE_MACROS = {
    MACRO_INSTANCE_MATCHES: '.*',
    MACRO_INSTANCE_NOT_MATCHES: 'CHANGE_IF_NEEDED',
    MACRO_INSTANCE_DISCOVERY_MIN: '0',
    MACRO_BUFFER_CACHE_MIN: '50',
    MACRO_PAGE_LIFE_MIN: '300',
    MACRO_DBNAME_MATCHES: '.*',
    MACRO_DBNAME_NOT_MATCHES: 'master|tempdb|model|msdb',
    MACRO_BACKUP_FULL_USED: '1',
    '{$MSSQL.BACKUP_FULL.WARN}': '9d',
    '{$MSSQL.BACKUP_FULL.CRIT}': '10d',
    MACRO_BACKUP_DIFF_USED: '1',
    '{$MSSQL.BACKUP_DIFF.WARN}': '3d',
    '{$MSSQL.BACKUP_DIFF.CRIT}': '6d',
    MACRO_BACKUP_LOG_USED: '1',
    '{$MSSQL.BACKUP_LOG.WARN}': '4h',
    '{$MSSQL.BACKUP_LOG.CRIT}': '8h',
    '{$MSSQL.PERCENT_LOG_USED.MAX}': '80',
    '{$MSSQL.LOG_FLUSH_WAITS.MAX}': '1',
    '{$MSSQL.LOG_FLUSH_WAIT_TIME.MAX}': '1',
}

MACRO_DESCRIPTIONS = {
    MACRO_INSTANCE_MATCHES: 'Allowlist for named-instance LLD ({#MSSQL.INSTANCE}).',
    MACRO_INSTANCE_NOT_MATCHES: 'Denylist for named-instance LLD. Example: SQLEXPRESS.',
    MACRO_INSTANCE_DISCOVERY_MIN: (
        'Census floor. 0 is valid (default-only hosts). Set per Device if you expect N named instances.'
    ),
    MACRO_BUFFER_CACHE_MIN: 'Buffer cache hit ratio Warning floor (percent). Estate uses Warning only.',
    MACRO_PAGE_LIFE_MIN: 'Page life expectancy Warning floor (seconds). Estate uses Warning only.',
    MACRO_DBNAME_MATCHES: 'Allowlist for named-instance database LLD ({#DBNAME}). Same default as stock.',
    MACRO_DBNAME_NOT_MATCHES: (
        'Denylist for named-instance database LLD. System databases only — not an environment mute.'
    ),
    MACRO_BACKUP_FULL_USED: (
        '1 = fire full-backup age triggers. Default 1 on every environment. '
        'Override per database with context, not per Test/Dev role.'
    ),
    '{$MSSQL.BACKUP_FULL.WARN}': 'Full backup age Warning (stock default).',
    '{$MSSQL.BACKUP_FULL.CRIT}': 'Full backup age High (stock default).',
    MACRO_BACKUP_DIFF_USED: (
        '1 = fire diff-backup age triggers. Default 1 on every environment.'
    ),
    '{$MSSQL.BACKUP_DIFF.WARN}': 'Diff backup age Warning (stock default).',
    '{$MSSQL.BACKUP_DIFF.CRIT}': 'Diff backup age High (stock default).',
    MACRO_BACKUP_LOG_USED: (
        '1 = fire log-backup age triggers. Default 1 on every environment. Simple recovery is skipped.'
    ),
    '{$MSSQL.BACKUP_LOG.WARN}': 'Log backup age Warning (stock default).',
    '{$MSSQL.BACKUP_LOG.CRIT}': 'Log backup age High (stock default).',
    '{$MSSQL.PERCENT_LOG_USED.MAX}': 'Percent log used Warning ceiling (stock default 80).',
    '{$MSSQL.LOG_FLUSH_WAITS.MAX}': 'Log flush waits/sec Warning (stock default).',
    '{$MSSQL.LOG_FLUSH_WAIT_TIME.MAX}': 'Log flush wait time ms Warning (stock default).',
}

ROLE_NAMES = ('MSSQL', 'MSSQL Query Server')

KEEP_TEMPLATES_ON_ROLE = (
    STOCK_TEMPLATE_NAME,
    TEMPLATE_NAME,
)

PING_TRIGGER_NAME = 'MSSQL [{#MSSQL.INSTANCE}]: TDS unavailable'
PING_TRIGGER_EXPR = f'max(/{TEMPLATE_NAME}/{PING_KEY},#3)=0'
VERSION_NODATA_NAME = 'MSSQL [{#MSSQL.INSTANCE}]: no version data for 15m'
VERSION_NODATA_EXPR = f'nodata(/{TEMPLATE_NAME}/{VERSION_KEY},15m)=1'
CENSUS_TRIGGER_NAME = f'{TEMPLATE_NAME}: Named instance count unexpected'
CENSUS_TRIGGER_EXPR = (
    f'last(/{TEMPLATE_NAME}/{CENSUS_KEY})<{MACRO_INSTANCE_DISCOVERY_MIN}'
    f' and {MACRO_INSTANCE_DISCOVERY_MIN}>0'
)

BACKUP_FULL_CRIT_EXPR = (
    f'last(/{TEMPLATE_NAME}/{BACKUP_FULL_KEY})>'
    f'{{$MSSQL.BACKUP_FULL.CRIT:"{{#DBNAME}}"}} and '
    f'{{$MSSQL.BACKUP_FULL.USED:"{{#DBNAME}}"}}=1'
)
BACKUP_FULL_WARN_EXPR = (
    f'last(/{TEMPLATE_NAME}/{BACKUP_FULL_KEY})>'
    f'{{$MSSQL.BACKUP_FULL.WARN:"{{#DBNAME}}"}} and '
    f'{{$MSSQL.BACKUP_FULL.USED:"{{#DBNAME}}"}}=1'
)
BACKUP_DIFF_CRIT_EXPR = (
    f'last(/{TEMPLATE_NAME}/{BACKUP_DIFF_KEY})>'
    f'{{$MSSQL.BACKUP_DIFF.CRIT:"{{#DBNAME}}"}} and '
    f'{{$MSSQL.BACKUP_DIFF.USED:"{{#DBNAME}}"}}=1'
)
BACKUP_DIFF_WARN_EXPR = (
    f'last(/{TEMPLATE_NAME}/{BACKUP_DIFF_KEY})>'
    f'{{$MSSQL.BACKUP_DIFF.WARN:"{{#DBNAME}}"}} and '
    f'{{$MSSQL.BACKUP_DIFF.USED:"{{#DBNAME}}"}}=1'
)
BACKUP_LOG_CRIT_EXPR = (
    f'last(/{TEMPLATE_NAME}/{BACKUP_LOG_KEY})>'
    f'{{$MSSQL.BACKUP_LOG.CRIT:"{{#DBNAME}}"}} and '
    f'{{$MSSQL.BACKUP_LOG.USED:"{{#DBNAME}}"}}=1 and '
    f'last(/{TEMPLATE_NAME}/{BACKUP_RECOVERY_KEY})<>3'
)
BACKUP_LOG_WARN_EXPR = (
    f'last(/{TEMPLATE_NAME}/{BACKUP_LOG_KEY})>'
    f'{{$MSSQL.BACKUP_LOG.WARN:"{{#DBNAME}}"}} and '
    f'{{$MSSQL.BACKUP_LOG.USED:"{{#DBNAME}}"}}=1 and '
    f'last(/{TEMPLATE_NAME}/{BACKUP_RECOVERY_KEY})<>3'
)

def _javascript_source(path: Path) -> str:
    return path.read_text(encoding='utf-8').strip()


WMI_LLD_JS = _javascript_source(LLD_JS_PATH)
DB_CATALOG_JS = _javascript_source(DB_CATALOG_JS_PATH)
LOCAL_DB_CATALOG_JS = _javascript_source(LOCAL_DB_CATALOG_JS_PATH)
FLATTEN_LLD_JS = _javascript_source(FLATTEN_LLD_JS_PATH)

DB_FOREACH_FORMULA = f'last_foreach(//{DB_CATALOG_KEY.replace("{#MSSQL.INSTANCE}", "*")})'
LOCAL_FOREACH_FORMULA = f'last_foreach(//{LOCAL_CATALOG_KEY.replace("{#MSSQL.INSTANCE}", "*")})'


def flatten_lld_catalogs(value: str) -> str:
    """Merge last_foreach JSON catalogs into one LLD array (mirrors FLATTEN_LLD_JS)."""
    try:
        parsed: Any = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return '[]'
    if parsed is None or parsed == '':
        return '[]'
    if not isinstance(parsed, list):
        parsed = [parsed]
    out: list[Any] = []
    for chunk in parsed:
        if chunk is None or chunk == '':
            continue
        if isinstance(chunk, str):
            try:
                chunk = json.loads(chunk)
            except json.JSONDecodeError:
                continue
        if not isinstance(chunk, list):
            chunk = [chunk]
        for row in chunk:
            if isinstance(row, dict):
                out.append(row)
    return json.dumps(out, separators=(',', ':'))


def lld_js_source() -> str:
    return WMI_LLD_JS


def db_catalog_js_source(*, instance: str, uri: str) -> str:
    """Catalog JS with only value-side LLD macros substituted (for Node tests)."""
    return (
        DB_CATALOG_JS.replace("var instance = '{#MSSQL.INSTANCE}';", f"var instance = '{instance}';")
        .replace("var uri = '{#MSSQL.URI}';", f"var uri = '{uri}';")
    )


def local_db_catalog_js_source(*, instance: str, uri: str) -> str:
    return (
        LOCAL_DB_CATALOG_JS.replace(
            "var instance = '{#MSSQL.INSTANCE}';", f"var instance = '{instance}';"
        ).replace("var uri = '{#MSSQL.URI}';", f"var uri = '{uri}';")
    )


def flatten_lld_js_source() -> str:
    return FLATTEN_LLD_JS


def load_template() -> dict:
    return yaml.safe_load(ZABBIX_TEMPLATE_PATH.read_text(encoding='utf-8'))


def template_block(doc: dict | None = None) -> dict:
    payload = doc if doc is not None else load_template()
    templates = payload['zabbix_export']['templates']
    if len(templates) != 1:
        raise AssertionError(f'expected one template, got {len(templates)}')
    return templates[0]


def javascript_steps(obj: dict) -> list[str]:
    scripts: list[str] = []
    for step in obj.get('preprocessing') or []:
        if str(step.get('type') or '').upper() == 'JAVASCRIPT':
            params = step.get('parameters') or []
            scripts.append(str(params[0] if params else '').strip())
    return scripts


def named_instances_from_wmi(value: str) -> list[dict]:
    """Python mirror of lld_named_instances.js (Duktape-safe behaviour)."""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError('MSSQL named-instance LLD: invalid WMI JSON') from exc
    if parsed is None:
        return []
    if isinstance(parsed, list):
        rows = parsed
    elif isinstance(parsed, dict):
        rows = [parsed]
    else:
        return []
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get('Name')
        if not isinstance(name, str):
            continue
        if not name.startswith(NAMED_INSTANCE_PREFIX):
            continue
        if name.startswith('MSSQLFDLauncher'):
            continue
        instance = name[len(NAMED_INSTANCE_PREFIX) :]
        if not instance:
            continue
        display = row.get('DisplayName') or name
        out.append(
            {
                '{#MSSQL.SERVICE}': name,
                '{#MSSQL.INSTANCE}': instance,
                '{#MSSQL.URI}': URI_PREFIX + instance,
                '{#MSSQL.DISPLAY}': display,
            }
        )
    return out


def run_javascript(value: str, *, script: str) -> str:
    body = script.strip()
    wrapped = (
        'function __run(value) {\n'
        f'{body}\n'
        '}\n'
        'const fs = require("fs");\n'
        'process.stdout.write(String(__run(fs.readFileSync(0, "utf8"))));\n'
    )
    proc = subprocess.run(
        ['node', '-e', wrapped],
        input=value,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        err = (proc.stderr or proc.stdout or 'JavaScript preprocessor returned no JSON').strip()
        raise RuntimeError(err)
    return proc.stdout


def run_lld_js(value: str, *, script: str | None = None) -> str:
    return run_javascript(value, script=script if script is not None else lld_js_source())


def zerotouch_source() -> str:
    return (REPO_ROOT / 'scripts' / 'configure_nbxsync_zerotouch.py').read_text(encoding='utf-8')
