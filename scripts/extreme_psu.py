"""Ticket installed PSUs that are not supplying power (no Django).

Stock EXOS/VOSS PSU Average only matches one enum:

* EXOS ``{$PSU_CRIT_STATUS}=3`` (``presentNotOK``) — ``presentPowerOff(4)``
  is a fitted PSU with no AC and stays silent.
* VOSS ``{$PSU_CRIT_STATUS}=4`` (``down``) — ``unknown(1)`` is a fitted PSU
  whose status cannot be determined (often unpowered) and stays silent.

VOSS ``empty(2)`` is **not installed**. Chassis firmware often fills the
serial field with ``--`` on every bay, including the empty one. That dummy
is not a FRU — CH-STA-L26-L02-MGMT03 has one PSU and still reports PSU 2
as empty(2) / ``--``. LLD skips empty even when serial looks set. The
Average is ``last()<>{$PSU.OK_STATUS} and last()<>{$PSU.EMPTY_STATUS}`` so
a leftover empty row recovers before LLD deletes it. Fitted-unplugged on
VOSS is ``unknown(1)`` or ``down(4)``, not empty.

EXOS padding is ``notPresent`` with no serial OID instance. LLD JS defaults
missing serial to empty and wipes dummy values. A serialled unplugged FRU
stays (OR: status not notPresent **or** a real serial). Average is
``last()<>{$PSU.OK_STATUS}`` on those discovered FRUs.
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
VOSS_TEMPLATE_NAME = 'Extreme VOSS by SNMP'

EXOS_PSU_NUMBER_OID = '1.3.6.1.4.1.1916.1.1.1.27.1.1'
EXOS_PSU_STATUS_OID = '1.3.6.1.4.1.1916.1.1.1.27.1.2'
EXOS_PSU_SERIAL_OID = '1.3.6.1.4.1.1916.1.1.1.27.1.4'
VOSS_PSU_ID_OID = '1.3.6.1.4.1.2272.1.4.8.1.1.1'
VOSS_PSU_STATUS_OID = '1.3.6.1.4.1.2272.1.4.8.1.1.2'
VOSS_PSU_SERIAL_OID = '1.3.6.1.4.1.2272.1.4.8.2.1.3'
VOSS_PSU_DETAIL_ID_OID = '1.3.6.1.4.1.2272.1.4.8.2.1.1'
VOSS_PSU_DETAIL_STATUS_OID = '1.3.6.1.4.1.2272.1.4.8.2.1.15'

# Firmware placeholders — not a FRU serial (VOSS empty bays use "--").
PSU_DUMMY_SERIAL_RE = re.compile(r'^(--|-|n/a|na|none|unknown|0+)$', re.I)

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
LLD_EVAL_AND = 1
LLD_EVAL_OR = 2


def psu_serial_is_dummy(serial: str) -> bool:
    """True when SNMP serial is missing or a firmware placeholder such as ``--``."""
    text = str(serial or '').strip()
    return not text or bool(PSU_DUMMY_SERIAL_RE.fullmatch(text))


def _filter_eval_is_or(filt: dict) -> bool:
    raw = str((filt or {}).get('evaltype') or '').upper()
    return raw in {'OR', '2'}


def _filter_eval_is_and(filt: dict) -> bool:
    raw = str((filt or {}).get('evaltype') or '').upper()
    return raw in {'AND', '1'}


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


def psu_lld_api_filter(
    empty_regex: str,
    existing_filter: dict | None = None,
    *,
    keep_serialled_empty: bool = True,
) -> dict:
    """AND/OR filter for ``discoveryrule.update``.

    Zabbix 7 rejects non-empty ``formulaid`` unless evaltype is a custom
    expression. ``discoveryrule.get`` still returns A/B and ``A or B``.
    YAML export may include formulaid; do not copy it back on API write.

    * EXOS (``keep_serialled_empty=True``): OR — status not empty **or**
      serial matches ``.+`` (after JS wipes dummy serials).
    * VOSS (``keep_serialled_empty=False``): AND — status not empty only.
      Dummy ``--`` serials must not keep an empty bay.
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
    if keep_serialled_empty:
        conditions.append(
            {
                'macro': PSU_SERIAL_MACRO,
                'value': PSU_SERIAL_PRESENT,
                'operator': LLD_MATCHES_REGEX,
            }
        )
        return {'evaltype': LLD_EVAL_OR, 'conditions': conditions}
    return {'evaltype': LLD_EVAL_AND, 'conditions': conditions}


ZBX_PREPROC_JAVASCRIPT = 21


def psu_lld_js_default_macros() -> str:
    """Fill missing LLD macros and wipe dummy serials before the filter.

    EXOS ``extremePowerSupplyTable`` has a row per stack slot. Padding
    ``notPresent`` indexes often have **no** serial OID instance, so Zabbix
    omits ``{#PSU.SERIAL}`` and refuses the filter with
    ``no value received for macro "{#PSU.SERIAL}"``. Empty string is padding.

    VOSS empty bays still emit a serial OID, usually ``--``. That matches
    ``.+`` and would keep the empty bay if LLD ORed on serial — wipe it.
    """
    return (
        "try {\n"
        "\tvar data = JSON.parse(value);\n"
        "}\n"
        "catch (error) {\n"
        "\tthrow 'Failed to parse JSON of PSU discovery.';\n"
        "}\n"
        "var fields = ['{#PSU.STATUS}','{#PSU.SERIAL}'];\n"
        "var dummy = /^(--|-|n\\/a|na|none|unknown|0+)$/i;\n"
        "data.forEach(function (element) {\n"
        "\tfields.forEach(function (field) {\n"
        "\t\telement[field] = element[field] || '';\n"
        "\t});\n"
        "\tvar serial = String(element['{#PSU.SERIAL}'] || '').trim();\n"
        "\tif (!serial || dummy.test(serial)) {\n"
        "\t\telement['{#PSU.SERIAL}'] = '';\n"
        "\t} else {\n"
        "\t\telement['{#PSU.SERIAL}'] = serial;\n"
        "\t}\n"
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


def psu_lld_js_clears_dummy_serials(rule: dict) -> bool:
    """True when LLD JS treats firmware placeholders such as ``--`` as empty."""
    for step in rule.get('preprocessing') or []:
        raw = str(step.get('type') or '').upper()
        if raw not in {'JAVASCRIPT', '21'}:
            continue
        text = _preprocessing_script(step)
        if PSU_SERIAL_MACRO in text and 'dummy' in text and '--' in text:
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
    keep_serialled_empty: bool = True,
) -> bool:
    """True when LLD walks status+serial, defaults missing serial, keeps a FRU."""
    oid = str(rule.get('snmp_oid') or '')
    if PSU_STATUS_MACRO not in oid or PSU_SERIAL_MACRO not in oid:
        return False
    if status_oid not in oid or serial_oid not in oid:
        return False
    if not psu_lld_defaults_missing_macros(rule):
        return False
    if not psu_lld_js_clears_dummy_serials(rule):
        return False
    filt = rule.get('filter') or {}
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
    if keep_serialled_empty:
        return _filter_eval_is_or(filt) and has_status and has_serial
    # VOSS: empty(2) is not installed even when serial is "--".
    return _filter_eval_is_and(filt) and has_status and not has_serial


def _expr_is_voss(text: str) -> bool:
    compact = re.sub(r'\s+', '', text or '')
    return 'ExtremeVOSSbySNMP' in compact


def psu_not_up_expr(item_path: str, *, exclude_empty: bool | None = None) -> str:
    path = item_path.strip()
    if exclude_empty is None:
        exclude_empty = _expr_is_voss(path)
    base = f'last({path})<>{PSU_OK_MACRO}'
    if exclude_empty:
        return f'{base} and last({path})<>{PSU_EMPTY_MACRO}'
    return base


def psu_expr_is_not_up(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    if not compact:
        return False
    exclude_empty = _expr_is_voss(compact)
    has_empty = PSU_EMPTY_MACRO.replace(' ', '') in compact
    if exclude_empty != has_empty:
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
    """Turn stock count==crit / last()<>OK into the platform canonical form.

    VOSS adds ``and last()<>{$PSU.EMPTY_STATUS}`` so dummy empty bays recover.
    EXOS stays ``last()<>{$PSU.OK_STATUS}``.
    """
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
