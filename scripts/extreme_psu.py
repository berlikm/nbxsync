"""Ticket installed PSUs that are not supplying power (no Django).

Stock EXOS/VOSS PSU Average only matches one enum:

* EXOS ``{$PSU_CRIT_STATUS}=3`` (``presentNotOK``) — ``presentPowerOff(4)``
  is a fitted PSU with no AC and stays silent.
* VOSS ``{$PSU_CRIT_STATUS}=4`` (``down``) — ``unknown(1)`` is a fitted PSU
  whose status cannot be determined (often unpowered) and stays silent.

Empty / ``notPresent`` bays are LLD-filtered, but stale rows can linger until
check-now, so the trigger also excludes ``{$PSU.EMPTY_STATUS}``.
"""

from __future__ import annotations

import re

PSU_OK_MACRO = '{$PSU.OK_STATUS}'
PSU_EMPTY_MACRO = '{$PSU.EMPTY_STATUS}'
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

_COUNT_CRIT = re.compile(
    r'count\(\s*(?P<item>/[^,]+?)\s*,\s*#1\s*,\s*"?eq"?\s*,\s*"?\{\$PSU_CRIT_STATUS\}"?\s*\)\s*=\s*1',
    re.I,
)
_LAST_ITEM = re.compile(r'last\(\s*(?P<item>/[^)]+?)\s*\)')


def psu_not_up_expr(item_path: str) -> str:
    path = item_path.strip()
    return (
        f'last({path})<>{PSU_OK_MACRO}'
        f' and last({path})<>{PSU_EMPTY_MACRO}'
    )


def psu_expr_is_not_up(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    return (
        'last(' in compact
        and f'<>{PSU_OK_MACRO}' in compact
        and f'<>{PSU_EMPTY_MACRO}' in compact
        and 'count(' not in compact
        and ',#1' not in compact
        and ',#2' not in compact
        and 'diff(' not in compact.lower()
    )


def rewrite_psu_not_up_expr(expr: str) -> str:
    """Turn stock count==crit into last()<>OK and last()<>empty."""
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
