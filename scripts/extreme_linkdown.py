"""Strip stock Extreme link-down silence (no Django).

Stock EXOS/VOSS link-down only fires on an up→down edge
(``last(#1)<>last(#2)`` / ``.diff()``) and only when ``ifOperStatus=down(2)``.
Admin-up ports that never came up, or that SNMP reports as
``lowerLayerDown(7)``, show red on the honeycomb with no Average.

Health honeycomb thresholds are ``>=``, so 2–7 all paint red. The trigger
must be **not up** (``last()<>1``). Recovery is ``last()=1`` — leaving
stock ``<>2`` would recover a ``lowerLayerDown`` immediately.

Same trigger on every switch role. Core/Dist/Mgmt: admin-up means live.
Access: a grammar display-string (``USW``/``US``/``UP``/``MON``/``UW``/``TMON``)
means live — unlabelled desk ports stay undiscovered.
"""

from __future__ import annotations

import re

LINKDOWN_HIGH_GATE = '{$LINKDOWN.HIGH:"{#IFALIAS}"}'
LINKDOWN_HIGH_MACRO_PREFIX = '{$LINKDOWN.HIGH'
LINKDOWN_TEMPLATES = ('Extreme EXOS by SNMP', 'Extreme VOSS by SNMP')
LINKDOWN_RECOVERY_MODE = 1  # RECOVERY_EXPRESSION

LINKDOWN_DIFF_RE = re.compile(
    r'\s+and\s+\(?\s*'
    r'last\([^)]*net\.if\.status\[ifOperStatus\.\{#SNMPINDEX\}\]\s*,\s*#1\)'
    r'\s*<>\s*'
    r'last\([^)]*net\.if\.status\[ifOperStatus\.\{#SNMPINDEX\}\]\s*,\s*#2\)'
    r'\s*\)?',
    re.I | re.S,
)
LINKDOWN_ITEM_RE = re.compile(
    r'last\((/[^)]+/net\.if\.status\[ifOperStatus\.\{#SNMPINDEX\}\])\)',
    re.I,
)
LINKDOWN_EQ_DOWN_RE = re.compile(
    r'last\((/[^)]+/net\.if\.status\[ifOperStatus\.\{#SNMPINDEX\}\])\)\s*=\s*2\b',
    re.I,
)
LINKDOWN_NOT_UP_RE = re.compile(
    r'last\(/[^)]+/net\.if\.status\[ifOperStatus\.\{#SNMPINDEX\}\]\)<>1',
    re.I,
)


def ungate_linkdown_expr(expr: str) -> str:
    """Drop class High gate and stock up→down .diff() from a link-down expression."""
    out = expr or ''
    for suffix in ('=0', '=1'):
        token = f' and {LINKDOWN_HIGH_GATE}{suffix}'
        out = out.replace(token, '')
    return LINKDOWN_DIFF_RE.sub('', out)


def canonicalize_linkdown_problem(expr: str) -> str:
    """PROBLEM: IFCONTROL on and oper-status not up. No .diff()."""
    out = ungate_linkdown_expr(expr)
    out = LINKDOWN_EQ_DOWN_RE.sub(r'last(\1)<>1', out)
    return out.strip()


def canonicalize_linkdown_recovery(problem_expr: str) -> str:
    """OK when the discovered port is up, or IFCONTROL muted."""
    m = LINKDOWN_ITEM_RE.search(problem_expr or '')
    if not m:
        return ''
    item = m.group(1)
    return f'last({item})=1 or {{$IFCONTROL:"{{#IFNAME}}"}}=0'


def linkdown_has_diff_guard(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    return bool(LINKDOWN_DIFF_RE.search(expr or '')) or '.diff()' in compact


def linkdown_is_not_up(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    if linkdown_has_diff_guard(expr) or 'LINKDOWN.HIGH' in compact:
        return False
    return bool(LINKDOWN_NOT_UP_RE.search(compact))


def linkdown_recovery_is_up(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    return bool(
        re.search(
            r'last\(/[^)]*net\.if\.status\[ifOperStatus\.\{#SNMPINDEX\}\]\)=1',
            compact,
        )
    ) and '<>2' not in compact


def _norm_expr(expr: str) -> str:
    return re.sub(r'\s+', '', expr or '')


def linkdown_expr_equal(left: str, right: str) -> bool:
    return _norm_expr(left) == _norm_expr(right)


def linkdown_manual_close_on(proto: dict) -> bool:
    raw = proto.get('manual_close')
    return str(raw).strip().lower() in {'1', 'yes', 'true'}


def is_platform_linkdown_name(name: str) -> bool:
    """True for EXOS/VOSS discovered-port Average — not Speed Expect or leftover USW High."""
    if 'Link down' not in (name or ''):
        return False
    if '(USW)' in name or '(speed-expect)' in name:
        return False
    return True
