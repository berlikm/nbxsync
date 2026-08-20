"""Strip stock Extreme link-down silence (no Django).

Stock EXOS/VOSS link-down only fires on an up→down edge
(``last(#1)<>last(#2)`` / ``.diff()``). Admin-up ports that never came up
show down on the honeycomb with no Average. Core/Dist/Mgmt contract is:
admin-up means it should be live.
"""

from __future__ import annotations

import re

LINKDOWN_HIGH_GATE = '{$LINKDOWN.HIGH:"{#IFALIAS}"}'
LINKDOWN_HIGH_MACRO_PREFIX = '{$LINKDOWN.HIGH'
LINKDOWN_TEMPLATES = ('Extreme EXOS by SNMP', 'Extreme VOSS by SNMP')

LINKDOWN_DIFF_RE = re.compile(
    r'\s+and\s+\(?\s*'
    r'last\([^)]*net\.if\.status\[ifOperStatus\.\{#SNMPINDEX\}\]\s*,\s*#1\)'
    r'\s*<>\s*'
    r'last\([^)]*net\.if\.status\[ifOperStatus\.\{#SNMPINDEX\}\]\s*,\s*#2\)'
    r'\s*\)?',
    re.I | re.S,
)


def ungate_linkdown_expr(expr: str) -> str:
    """Drop class High gate and stock up→down .diff() from a link-down expression."""
    out = expr
    for suffix in ('=0', '=1'):
        token = f' and {LINKDOWN_HIGH_GATE}{suffix}'
        out = out.replace(token, '')
    return LINKDOWN_DIFF_RE.sub('', out)


def linkdown_has_diff_guard(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    return bool(LINKDOWN_DIFF_RE.search(expr or '')) or '.diff()' in compact


def linkdown_manual_close_on(proto: dict) -> bool:
    raw = proto.get('manual_close')
    return str(raw).strip().lower() in {'1', 'yes', 'true'}
