#!/usr/bin/env python3
"""Helpers for the IIS Observability companion."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / 'zabbix/templates/iis_observability'
TEMPLATE_YAML = TEMPLATE_DIR / 'template_iis_observability.yaml'
LLD_JS = TEMPLATE_DIR / 'lld_https_bindings.js'
CERT_VALIDATION_JS = TEMPLATE_DIR / 'cert_validation.js'
FIXTURES = TEMPLATE_DIR / 'fixtures'
NO_HOST_VALIDATION = 'not_evaluated_no_host_header'

TEMPLATE_NAME = 'IIS Observability'
STOCK_IIS_TEMPLATE = 'IIS by Zabbix agent'
STOCK_CERT_TEMPLATE = 'Website certificate by Zabbix agent 2'
CONFIG_KEY = 'vfs.file.contents["{$IIS.CONFIG.PATH}"]'
CERT_GET_PREFIX = 'web.certificate.get['


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


def cert_validation_js_source() -> str:
    return CERT_VALIDATION_JS.read_text(encoding='utf-8').strip()


def user_facing_validation_script() -> str:
    return (
        cert_validation_js_source()
        + '\n\n'
        + 'var payload = parseCertPayload(value);\n'
        + "return userFacingValidation(payload, '{#IIS.HAS_HOST}');\n"
    )


def raw_validation_script() -> str:
    return (
        cert_validation_js_source()
        + '\n\n'
        + 'var payload = parseCertPayload(value);\n'
        + 'return rawValidationDisplay(payload);\n'
    )


def javascript_steps(obj: dict) -> list[str]:
    scripts: list[str] = []
    for step in obj.get('preprocessing') or []:
        if str(step.get('type') or '').upper() == 'JAVASCRIPT':
            params = step.get('parameters') or []
            scripts.append(str(params[0] if params else '').strip())
    return scripts
