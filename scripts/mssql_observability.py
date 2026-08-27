"""MSSQL Observability companion — named-instance Agent 2 coverage.

Stock ``MSSQL by Zabbix agent 2`` is one ``{$MSSQL.URI}`` (the default instance).
This companion discovers ``MSSQL$%`` Windows services via WMI and talks to each
named instance with ``sqlserver://localhost/{#MSSQL.INSTANCE}`` (plugin ≥ 7.0.6).

Do **not** nest the stock template (URI remains a single host macro).
Do **not** use ``service.discovery`` (collides with Windows by Zabbix agent).
Do **not** invent host prototypes, ODBC, or ICMP (Windows already has ping).
Do **not** modify zerotouch — apply via ``configure_nbxsync_network.py --apply-mssql``.

Per-database LLD on named instances is v2. v1 ships instance-level items plus
a database *count* from ``mssql.db.get``.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

TEMPLATE_NAME = 'MSSQL Observability'
TEMPLATE_GROUP = 'Templates/Databases'
TEMPLATE_GROUP_UUID = '748ad4d098d447d492bb935c907f652f'
TEMPLATE_UUID = 'a8c4e91b2d7f4063b15a9e0c4d6f82a1'
DASHBOARD_UUID = 'b91d7e04c3a8456f8e12f6a0b4c8d931'

STOCK_TEMPLATE_NAME = 'MSSQL by Zabbix agent 2'

ZABBIX_TEMPLATE_PATH = (
    REPO_ROOT / 'zabbix' / 'templates' / 'mssql_observability' / 'template_mssql_observability.yaml'
)
TEMPLATE_FILES = {TEMPLATE_NAME: ZABBIX_TEMPLATE_PATH}

# Unique vs Windows-by-agent ``service.discovery``. This *is* the collect key
# (WMI); LLD is a dependent rule with DISCOVERY_KEY.
WMI_ITEM_KEY = (
    'wmi.getall[root\\cimv2,"SELECT Name,DisplayName,State,StartMode '
    "FROM Win32_Service WHERE Name LIKE 'MSSQL$%'\"]"
)
WMI_DISCOVERY_KEY = WMI_ITEM_KEY
DISCOVERY_KEY = 'mssql.observability.instance.discovery'
CENSUS_KEY = 'mssql.observability.instance.count'

PLUGIN_ARGS = '["{#MSSQL.URI}","{$MSSQL.USER}","{$MSSQL.PASSWORD}"]'
PING_KEY = f'mssql.ping{PLUGIN_ARGS}'
VERSION_KEY = f'mssql.version{PLUGIN_ARGS}'
PERF_KEY = f'mssql.perfcounter.get{PLUGIN_ARGS}'
JOB_KEY = f'mssql.job.status.get{PLUGIN_ARGS}'
BACKUP_KEY = f'mssql.last.backup.get{PLUGIN_ARGS}'
DB_KEY = f'mssql.db.get{PLUGIN_ARGS}'

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

MACRO_INSTANCE_MATCHES = '{$MSSQL.INSTANCE.MATCHES}'
MACRO_INSTANCE_NOT_MATCHES = '{$MSSQL.INSTANCE.NOT_MATCHES}'
MACRO_INSTANCE_DISCOVERY_MIN = '{$MSSQL.INSTANCE.DISCOVERY.MIN}'
MACRO_BUFFER_CACHE_MIN = '{$MSSQL.BUFFER_CACHE.MIN}'
MACRO_PAGE_LIFE_MIN = '{$MSSQL.PAGE_LIFE.MIN}'

TEMPLATE_MACROS = {
    MACRO_INSTANCE_MATCHES: '.*',
    MACRO_INSTANCE_NOT_MATCHES: 'CHANGE_IF_NEEDED',
    MACRO_INSTANCE_DISCOVERY_MIN: '0',
    MACRO_BUFFER_CACHE_MIN: '50',
    MACRO_PAGE_LIFE_MIN: '300',
}

MACRO_DESCRIPTIONS = {
    MACRO_INSTANCE_MATCHES: 'Allowlist for named-instance LLD ({#MSSQL.INSTANCE}).',
    MACRO_INSTANCE_NOT_MATCHES: 'Denylist for named-instance LLD. Example: SQLEXPRESS.',
    MACRO_INSTANCE_DISCOVERY_MIN: (
        'Census floor. 0 is valid (default-only hosts). Set per Device if you expect N named instances.'
    ),
    MACRO_BUFFER_CACHE_MIN: 'Buffer cache hit ratio Warning floor (percent). Estate uses Warning only.',
    MACRO_PAGE_LIFE_MIN: 'Page life expectancy Warning floor (seconds). Estate uses Warning only.',
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

WMI_LLD_JS = """\
try {
	var data = JSON.parse(value);
} catch (error) {
	return '[]';
}
if (data == null || data === '') {
	return '[]';
}
if (!Array.isArray(data)) {
	data = [data];
}
var out = [];
for (var i = 0; i < data.length; i++) {
	var row = data[i] || {};
	var name = String(row.Name || row.name || '');
	if (name.indexOf('MSSQL$') !== 0) {
		continue;
	}
	var instance = name.substring(6);
	if (!instance) {
		continue;
	}
	out.push({
		'{#MSSQL.SERVICE}': name,
		'{#MSSQL.INSTANCE}': instance,
		'{#MSSQL.URI}': 'sqlserver://localhost/' + instance,
		'{#MSSQL.DISPLAY}': String(row.DisplayName || row.displayname || name)
	});
}
return JSON.stringify(out);
"""
