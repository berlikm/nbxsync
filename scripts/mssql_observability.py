#!/usr/bin/env python3
"""Helpers for the MSSQL Observability companion and its preprocessors."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / 'zabbix/templates/mssql_observability'
TEMPLATE_YAML = TEMPLATE_DIR / 'template_mssql_observability.yaml'
LLD_JS = TEMPLATE_DIR / 'lld_named_instances.js'
DB_INVENTORY_JS = TEMPLATE_DIR / 'db_inventory.js'
BACKUP_INVENTORY_JS = TEMPLATE_DIR / 'backup_inventory.js'
FIXTURES = TEMPLATE_DIR / 'fixtures'

TEMPLATE_NAME = 'MSSQL Observability'
STOCK_MSSQL_TEMPLATE = 'MSSQL by Zabbix agent 2'
INSTANCE_HOST_GROUP = 'MSSQL instances'
INSTANCE_HOST_GROUP_UUID = '6f2c8a91d4b047e3b8c15a7e9d04f3c2'
HOST_PROTO_UUID = 'c8e4b17a9d5f4c2e8a6b3d0f1e7c5948'
HOST_PROTO_HOST = '{#MSSQL.PARENT}-mssql-{#MSSQL.INSTANCE}'
HOST_PROTO_VISIBLE = '{#MSSQL.PARENT} / {#MSSQL.INSTANCE}'
NAMED_URI = '{#MSSQL.URI}'
PARENT_MACRO = '{$MSSQL.PARENT.HOST}'
LISTEN_HOST_MACRO = '{$MSSQL.LISTEN.HOST}'
LISTEN_HOST_DEFAULT = 'localhost'
LISTEN_HOST_JINJA = '{{ object.primary_ip4.address.ip }}'
WMI_KEY = 'wmi.getall[root\\cimv2,"SELECT Name,DisplayName,State,StartMode,SystemName FROM Win32_Service WHERE Name LIKE \'MSSQL%\'"]'
PLUGIN_PROTOTYPE_PREFIXES = (
    'mssql.version[',
    'mssql.perfcounter.get[',
    'mssql.job.status.get[',
    'mssql.last.backup.get[',
    'mssql.db.get[',
)
NAMED_INSTANCE_PREFIX = 'MSSQL$'
URI_PREFIX = 'sqlserver://localhost/'

_ZEROTOUCH = ROOT / 'scripts/configure_nbxsync_zerotouch.py'


def load_template() -> dict:
    return yaml.safe_load(TEMPLATE_YAML.read_text(encoding='utf-8'))


def template_block(doc: dict | None = None) -> dict:
    payload = doc if doc is not None else load_template()
    templates = payload['zabbix_export']['templates']
    if len(templates) != 1:
        raise AssertionError(f'expected one template, got {len(templates)}')
    return templates[0]


def _javascript_source(path: Path) -> str:
    return path.read_text(encoding='utf-8').strip()


def lld_js_source() -> str:
    return _javascript_source(LLD_JS)


def db_inventory_js_source() -> str:
    return _javascript_source(DB_INVENTORY_JS)


def backup_inventory_js_source() -> str:
    return _javascript_source(BACKUP_INVENTORY_JS)


def javascript_steps(obj: dict) -> list[str]:
    scripts: list[str] = []
    for step in obj.get('preprocessing') or []:
        if str(step.get('type') or '').upper() == 'JAVASCRIPT':
            params = step.get('parameters') or []
            scripts.append(str(params[0] if params else '').strip())
    return scripts


def sanitize_parent_host(name: str) -> str:
    """Keep Zabbix host-name charset (letters, digits, _, ., space, -)."""
    cleaned = ''.join(ch if ch.isalnum() or ch in '_. -' else '_' for ch in name)
    return cleaned.strip()


def resolve_listen_host(listen_macro: str = LISTEN_HOST_MACRO) -> str:
    """Named-instance plugin host. Unresolved/empty/ported values stay localhost."""
    macro = (listen_macro or '').strip()
    if (
        not macro
        or macro.startswith('{$')
        or macro == 'CHANGE_IF_NEEDED'
        or ':' in macro
        or '/' in macro
    ):
        return LISTEN_HOST_DEFAULT
    return macro


def named_instance_uri(instance: str, listen_host: str = LISTEN_HOST_DEFAULT) -> str:
    """Plugin 7.0.6+ instance URI. Never put a port in the authority."""
    return f'sqlserver://{listen_host}/{instance}'


def resolve_parent_host(row: dict, parent_macro: str = PARENT_MACRO) -> str:
    macro = (parent_macro or '').strip()
    if macro and not macro.startswith('{$') and macro != 'CHANGE_IF_NEEDED':
        raw = macro
    else:
        sysname = row.get('SystemName')
        raw = sysname if isinstance(sysname, str) else ''
    return sanitize_parent_host(raw)


def named_instances_from_wmi(
    value: str,
    *,
    parent_macro: str = PARENT_MACRO,
    listen_macro: str = LISTEN_HOST_MACRO,
) -> list[dict]:
    """Python mirror of lld_named_instances.js (Duktape-safe behaviour).

    ``listen_macro`` is the preprocessed ``{$MSSQL.LISTEN.HOST}`` (NetBox
    primary IPv4 after HostSync Jinja). Empty / unresolved / ported values
    fall back to ``localhost``. Each row carries ``{#MSSQL.LISTEN}`` and
    ``{#MSSQL.URI}`` (``sqlserver://<listen>/<instance>``, no port).
    """
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
        parent = resolve_parent_host(row, parent_macro)
        if not parent:
            raise ValueError('MSSQL named-instance LLD: missing parent host name')
        listen = resolve_listen_host(listen_macro)
        display = row.get('DisplayName') or name
        out.append(
            {
                '{#MSSQL.SERVICE}': name,
                '{#MSSQL.INSTANCE}': instance,
                '{#MSSQL.LISTEN}': listen,
                '{#MSSQL.URI}': named_instance_uri(instance, listen),
                '{#MSSQL.DISPLAY}': display,
                '{#MSSQL.PARENT}': parent,
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
    return _ZEROTOUCH.read_text(encoding='utf-8')
