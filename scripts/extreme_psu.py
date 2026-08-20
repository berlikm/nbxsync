"""Ticket installed PSUs that are not supplying power (no Django).

Stock EXOS/VOSS PSU Average only matches one enum:

* EXOS ``{$PSU_CRIT_STATUS}=3`` (``presentNotOK``) — ``presentPowerOff(4)``
  is a fitted PSU with no AC and stays silent.
* VOSS ``{$PSU_CRIT_STATUS}=4`` (``down``) — ``unknown(1)`` is a fitted PSU
  whose status cannot be determined (often unpowered) and stays silent.

Some firmware reports a fitted-but-unplugged FRU as empty / notPresent.
LLD therefore keeps a row when status is **not** empty/notPresent **or**
the PSU serial is non-empty. Padding bays (empty + no serial) stay out.
The Average is ``last()<>{$PSU.OK_STATUS}`` on those discovered FRUs —
two present, one connected must ticket.
"""

from __future__ import annotations

import re

PSU_OK_MACRO = '{$PSU.OK_STATUS}'
PSU_EMPTY_MACRO = '{$PSU.EMPTY_STATUS}'
PSU_STATUS_MACRO = '{#PSU.STATUS}'
PSU_SERIAL_MACRO = '{#PSU.SERIAL}'
PSU_SERIAL_PRESENT = '.+'
PSU_OK_BY_TEMPLATE = {
    'Extreme EXOS by SNMP': '2',  # presentOK
    'Extreme VOSS by SNMP': '3',  # up — present and supplying power
}
PSU_EMPTY_BY_TEMPLATE = {
    'Extreme EXOS by SNMP': '1',  # notPresent
    'Extreme VOSS by SNMP': '2',  # empty — not installed
}
PSU_TEMPLATES = tuple(PSU_OK_BY_TEMPLATE)
PSU_DISCOVERY_KEYS = ('psu.discovery', 'psu.detail.discovery')
PSU_TRIGGER_NAME_HINTS = (
    'Power supply is in critical',
    'Power supply is not up',
    'Detail status critical',
    'Detail status not up',
)
PSU_POWER_OFF_NAME_HINTS = (
    'Power supply power off',
    'Power supply is powered off',
)

EXOS_PSU_NUMBER_OID = '1.3.6.1.4.1.1916.1.1.1.27.1.1'
EXOS_PSU_STATUS_OID = '1.3.6.1.4.1.1916.1.1.1.27.1.2'
EXOS_PSU_SERIAL_OID = '1.3.6.1.4.1.1916.1.1.1.27.1.4'
VOSS_PSU_ID_OID = '1.3.6.1.4.1.2272.1.4.8.1.1.1'
VOSS_PSU_STATUS_OID = '1.3.6.1.4.1.2272.1.4.8.1.1.2'
VOSS_PSU_SERIAL_OID = '1.3.6.1.4.1.2272.1.4.8.2.1.3'
VOSS_PSU_DETAIL_ID_OID = '1.3.6.1.4.1.2272.1.4.8.2.1.1'
VOSS_PSU_DETAIL_STATUS_OID = '1.3.6.1.4.1.2272.1.4.8.2.1.15'

_COUNT_CRIT = re.compile(
    r'count\(\s*(?P<item>/[^,]+?)\s*,\s*#1\s*,\s*"?eq"?\s*,\s*"?\{\$PSU_CRIT_STATUS\}"?\s*\)\s*=\s*1',
    re.I,
)
_LAST_ITEM = re.compile(r'last\(\s*(?P<item>/[^)]+?)\s*\)')


def psu_discovery_snmp_oid(id_oid: str, status_oid: str, serial_oid: str) -> str:
    return (
        f'discovery[{{#SNMPVALUE}},{id_oid},'
        f'{{#PSU.STATUS}},{status_oid},'
        f'{{#PSU.SERIAL}},{serial_oid}]'
    )


EXOS_PSU_DISCOVERY_OID = psu_discovery_snmp_oid(
    EXOS_PSU_NUMBER_OID, EXOS_PSU_STATUS_OID, EXOS_PSU_SERIAL_OID
)
VOSS_PSU_DISCOVERY_OID = psu_discovery_snmp_oid(
    VOSS_PSU_ID_OID, VOSS_PSU_STATUS_OID, VOSS_PSU_SERIAL_OID
)
VOSS_PSU_DETAIL_DISCOVERY_OID = psu_discovery_snmp_oid(
    VOSS_PSU_DETAIL_ID_OID, VOSS_PSU_DETAIL_STATUS_OID, VOSS_PSU_SERIAL_OID
)


LLD_MATCHES_REGEX = 8
LLD_NOT_MATCHES_REGEX = 9
LLD_EVAL_OR = 2


def _filter_eval_is_or(filt: dict) -> bool:
    raw = str((filt or {}).get('evaltype') or '').upper()
    return raw in {'OR', '2'}


def _op_is_not_matches(op) -> bool:
    try:
        return int(op) == LLD_NOT_MATCHES_REGEX
    except (TypeError, ValueError):
        return str(op).upper() in {'NOT_MATCHES_REGEX', 'NOT_MATCHES'}


def _op_is_matches(op) -> bool:
    try:
        return int(op) == LLD_MATCHES_REGEX
    except (TypeError, ValueError):
        return str(op).upper() in {'MATCHES_REGEX', 'MATCHES'}


def _lld_operator(op) -> int:
    try:
        return int(op)
    except (TypeError, ValueError):
        return LLD_MATCHES_REGEX


def psu_lld_api_filter(empty_regex: str, existing_filter: dict | None = None) -> dict:
    """OR filter for ``discoveryrule.update``.

    Zabbix 7 rejects non-empty ``formulaid`` unless evaltype is a custom
    expression. ``discoveryrule.get`` still returns A/B and ``A or B``.
    YAML export may include formulaid; do not copy it back on API write.
    """
    conditions = []
    for c in (existing_filter or {}).get('conditions') or []:
        if c.get('macro') in (PSU_STATUS_MACRO, PSU_SERIAL_MACRO):
            continue
        conditions.append(
            {
                'macro': c['macro'],
                'value': c.get('value', ''),
                'operator': _lld_operator(c.get('operator', LLD_MATCHES_REGEX)),
            }
        )
    conditions.append(
        {
            'macro': PSU_STATUS_MACRO,
            'value': empty_regex,
            'operator': LLD_NOT_MATCHES_REGEX,
        }
    )
    conditions.append(
        {
            'macro': PSU_SERIAL_MACRO,
            'value': PSU_SERIAL_PRESENT,
            'operator': LLD_MATCHES_REGEX,
        }
    )
    return {'evaltype': LLD_EVAL_OR, 'conditions': conditions}


ZBX_PREPROC_JAVASCRIPT = 21


def psu_lld_js_default_macros() -> str:
    """Fill missing LLD macros so the serial filter can run.

    EXOS ``extremePowerSupplyTable`` has a row per stack slot. Padding
    ``notPresent`` indexes often have **no** serial OID instance, so Zabbix
    omits ``{#PSU.SERIAL}`` and refuses the filter with
    ``no value received for macro "{#PSU.SERIAL}"``. Empty string is padding.
    """
    return (
        "try {\n"
        "\tvar data = JSON.parse(value);\n"
        "}\n"
        "catch (error) {\n"
        "\tthrow 'Failed to parse JSON of PSU discovery.';\n"
        "}\n"
        "var fields = ['{#PSU.STATUS}','{#PSU.SERIAL}'];\n"
        "data.forEach(function (element) {\n"
        "\tfields.forEach(function (field) {\n"
        "\t\telement[field] = element[field] || '';\n"
        "\t});\n"
        "});\n"
        "return JSON.stringify(data);\n"
    )


def _preprocessing_script(step: dict) -> str:
    params = step.get('params')
    if params is None:
        params = step.get('parameters')
    if isinstance(params, list):
        return '\n'.join(str(p) for p in params)
    return str(params or '')


def psu_lld_defaults_missing_macros(rule: dict) -> bool:
    """True when LLD JS defaults missing {#PSU.SERIAL} before the filter."""
    for step in rule.get('preprocessing') or []:
        raw = str(step.get('type') or '').upper()
        if raw not in {'JAVASCRIPT', '21'}:
            continue
        text = _preprocessing_script(step)
        if PSU_SERIAL_MACRO in text and 'JSON.parse' in text and '||' in text:
            return True
    return False


def psu_lld_preprocessing_payload(existing: list | None = None) -> list[dict]:
    """API preprocessing list: keep unrelated steps, ensure serial default JS."""
    kept: list[dict] = []
    for step in existing or []:
        script = _preprocessing_script(step)
        if PSU_SERIAL_MACRO in script and 'JSON.parse' in script:
            continue
        entry = {
            'type': step.get('type', ZBX_PREPROC_JAVASCRIPT),
            'params': step.get('params', script),
        }
        if step.get('error_handler') is not None:
            entry['error_handler'] = step['error_handler']
        if step.get('error_handler_params') is not None:
            entry['error_handler_params'] = step['error_handler_params']
        kept.append(entry)
    kept.append(
        {
            'type': ZBX_PREPROC_JAVASCRIPT,
            'params': psu_lld_js_default_macros(),
            'error_handler': 0,
            'error_handler_params': '',
        }
    )
    return kept


def psu_lld_keeps_installed_fru(
    rule: dict,
    *,
    status_oid: str,
    serial_oid: str,
    empty_regex: str,
) -> bool:
    """True when LLD walks status+serial, defaults missing serial, keeps a FRU."""
    oid = str(rule.get('snmp_oid') or '')
    if PSU_STATUS_MACRO not in oid or PSU_SERIAL_MACRO not in oid:
        return False
    if status_oid not in oid or serial_oid not in oid:
        return False
    if not psu_lld_defaults_missing_macros(rule):
        return False
    filt = rule.get('filter') or {}
    if not _filter_eval_is_or(filt):
        return False
    has_status = False
    has_serial = False
    for c in filt.get('conditions') or []:
        if (
            c.get('macro') == PSU_STATUS_MACRO
            and _op_is_not_matches(c.get('operator', 0))
            and c.get('value') == empty_regex
        ):
            has_status = True
        if (
            c.get('macro') == PSU_SERIAL_MACRO
            and _op_is_matches(c.get('operator', 0))
            and c.get('value') == PSU_SERIAL_PRESENT
        ):
            has_serial = True
    return has_status and has_serial


def psu_not_up_expr(item_path: str) -> str:
    path = item_path.strip()
    return f'last({path})<>{PSU_OK_MACRO}'


def psu_expr_is_not_up(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    if PSU_EMPTY_MACRO.replace(' ', '') in compact:
        return False
    return (
        'last(' in compact
        and f'<>{PSU_OK_MACRO}' in compact
        and 'count(' not in compact
        and ',#1' not in compact
        and ',#2' not in compact
        and 'diff(' not in compact.lower()
    )


def rewrite_psu_not_up_expr(expr: str) -> str:
    """Turn stock count==crit / empty-excluded last() into last()<>OK."""
    if psu_expr_is_not_up(expr):
        return expr
    compact_src = re.sub(r'\s+', ' ', expr or '').strip()
    m = _COUNT_CRIT.search(compact_src)
    if m:
        return psu_not_up_expr(m.group('item'))
    lasts = _LAST_ITEM.findall(compact_src)
    if lasts:
        return psu_not_up_expr(lasts[0])
    return expr


def psu_trigger_name_match(name: str) -> bool:
    n = name or ''
    return any(h in n for h in PSU_TRIGGER_NAME_HINTS)


def psu_power_off_name_match(name: str) -> bool:
    n = (name or '').lower()
    return any(h.lower() in n for h in PSU_POWER_OFF_NAME_HINTS)
