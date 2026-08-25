#!/usr/bin/env python3
"""Helpers for the MSSQL Observability companion (YAML contract + LLD JS)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / 'zabbix/templates/mssql_observability'
TEMPLATE_YAML = TEMPLATE_DIR / 'template_mssql_observability.yaml'
LLD_JS = TEMPLATE_DIR / 'lld_named_instances.js'
FIXTURES = TEMPLATE_DIR / 'fixtures'

TEMPLATE_NAME = 'MSSQL Observability'
STOCK_MSSQL_TEMPLATE = 'MSSQL by Zabbix agent 2'
WMI_KEY = 'wmi.getall[root\\cimv2,"SELECT Name,DisplayName,State,StartMode FROM Win32_Service WHERE Name LIKE \'MSSQL%\'"]'
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


def lld_js_source() -> str:
    return LLD_JS.read_text(encoding='utf-8').strip()


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


def run_lld_js(value: str, *, script: str | None = None) -> str:
    body = (script if script is not None else lld_js_source()).strip()
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
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or 'node failed').strip()
        raise RuntimeError(err)
    return proc.stdout


def zerotouch_source() -> str:
    return _ZEROTOUCH.read_text(encoding='utf-8')
