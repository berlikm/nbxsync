"""Strip stock Extreme link-down silence (no Django).

Stock EXOS/VOSS link-down only fires on an up→down edge
(``last(#1)<>last(#2)`` / ``.diff()``) and only when ``ifOperStatus=down(2)``.
Admin-up ports that never came up, or that SNMP reports as
``lowerLayerDown(7)``, show red on the honeycomb with no Average.

Health honeycomb thresholds are ``>=``, so 2–7 all paint red. The trigger
must be **not up** (``last()<>1``). Recovery is ``last()=1`` — leaving
stock ``<>2`` would recover a ``lowerLayerDown`` immediately.

Same trigger on Extreme EXOS by SNMP and Extreme VOSS by SNMP. Core/Dist/Mgmt:
admin-up means live. Access: a grammar display-string
(``USW``/``US``/``UP``/``MON``/``UW``/``TMON``) means live — unlabelled desk
ports stay undiscovered, and ``{$LINKDOWN.IFALIAS:"{#IFALIAS}"}`` refuses the
Average when the alias is not that grammar even if LLD still has the row.
"""

from __future__ import annotations

import re

ACCESS_IFALIAS_MATCHES = '^(USW|US|UP|MON|UW|TMON)(-|$)'
ACCESS_PORTID_MATCHES = '^(USW|US|UP|MON)(-|$)'

# Chassis OOB is not a labelled data port. VOSS ifName ``mgmt`` (empty alias),
# EXOS ifName ``Management`` (vendor alias MgmtPort). Mute with LLD, not
# {$IFCONTROL} and not X. Keep stock loopback/docker skips and VOSS ``Mgmt-``.
IFNAME_NOT_MATCHES_MACRO = '{$NET.IF.IFNAME.NOT_MATCHES}'
IFNAME_NOT_MATCHES = (
    '(^Software Loopback Interface|^NULL[0-9.]*$|^[Ll]o[0-9.]*$|^[Ss]ystem$'
    '|^Nu[0-9.]*$|^veth[0-9a-z]+$|docker[0-9]+|br-[a-z0-9]{12}'
    '|^Mgmt-|^mgmt$|^Management$)'
)
IFNAME_OOB_ITEM_NEEDLES = (
    'Interface mgmt(',
    'Interface Management(',
)

LINKDOWN_HIGH_GATE = '{$LINKDOWN.HIGH:"{#IFALIAS}"}'
LINKDOWN_HIGH_MACRO_PREFIX = '{$LINKDOWN.HIGH'
LINKDOWN_IFALIAS_MACRO = '{$LINKDOWN.IFALIAS}'
LINKDOWN_IFALIAS_GATE = '{$LINKDOWN.IFALIAS:"{#IFALIAS}"}=1'
LINKDOWN_IFALIAS_RECOVERY = '{$LINKDOWN.IFALIAS:"{#IFALIAS}"}=0'
LINKDOWN_IFALIAS_TEMPLATE_VALUE = '1'
LINKDOWN_IFALIAS_ACCESS_DEFAULT = '0'
LINKDOWN_TEMPLATES = ('Extreme EXOS by SNMP', 'Extreme VOSS by SNMP')
LINKDOWN_RECOVERY_MODE = 1  # RECOVERY_EXPRESSION
LINKDOWN_TRIGGER_DESCRIPTION = (
    'Admin-up + oper-down on a discovered port, including never-up. '
    'Same Average on Extreme EXOS by SNMP and Extreme VOSS by SNMP. '
    'Core/Dist/Mgmt: every admin-up ethernet/LAG except X. '
    'Access: only a grammar display-string / ifAlias matching '
    'USW|US|UP|MON|UW|TMON. Unlabelled Access desk ports must not ticket '
    '(LLD plus {$LINKDOWN.IFALIAS:"{#IFALIAS}"}). Mute with X (or admin-down), '
    'not ACK and not {$IFCONTROL}. Average ticket — dayside, not a page.'
)

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
LINKDOWN_IFALIAS_GATE_RE = re.compile(
    r'\s+and\s+\{\$LINKDOWN\.IFALIAS:"\{\#IFALIAS\}"\}=1',
    re.I,
)


def ifname_not_matches_excludes_oob(value: str) -> bool:
    compact = value or ''
    return '^mgmt$' in compact and '^Management$' in compact


def zabbix_regex_macro_name(base: str, pattern: str) -> str:
    """``{$FOO}`` + pattern → ``{$FOO:regex:"pattern"}`` (nbxsync assignment __str__)."""
    if not (base.startswith('{$') and base.endswith('}')):
        raise ValueError(f'not a Zabbix user macro: {base!r}')
    return f'{base[:-1]}:regex:"{pattern}"}}'


def linkdown_ifalias_regex_macro(pattern: str = ACCESS_IFALIAS_MATCHES) -> str:
    return zabbix_regex_macro_name(LINKDOWN_IFALIAS_MACRO, pattern)


def access_zabbix_host_macros(
    role_macros: dict[str, str],
    *,
    ifalias_matches: str = ACCESS_IFALIAS_MATCHES,
) -> dict[str, str]:
    """Zabbix host macros that keep Access link-down on grammar labels only."""
    out = dict(role_macros)
    out[linkdown_ifalias_regex_macro(ifalias_matches)] = '1'
    return out


def ungate_linkdown_expr(expr: str) -> str:
    """Drop class High gate and stock up→down .diff() from a link-down expression."""
    out = expr or ''
    for suffix in ('=0', '=1'):
        token = f' and {LINKDOWN_HIGH_GATE}{suffix}'
        out = out.replace(token, '')
    return LINKDOWN_DIFF_RE.sub('', out)


def canonicalize_linkdown_problem(expr: str) -> str:
    """PROBLEM: IFCONTROL on, oper-status not up, Access ifAlias grammar gate."""
    out = ungate_linkdown_expr(expr)
    out = LINKDOWN_EQ_DOWN_RE.sub(r'last(\1)<>1', out)
    out = LINKDOWN_IFALIAS_GATE_RE.sub('', out)
    return f'{out.strip()} and {LINKDOWN_IFALIAS_GATE}'


def canonicalize_linkdown_recovery(problem_expr: str) -> str:
    """OK when the discovered port is up, IFCONTROL muted, or Access ifAlias gate off."""
    m = LINKDOWN_ITEM_RE.search(problem_expr or '')
    if not m:
        return ''
    item = m.group(1)
    return (
        f'last({item})=1 or {{$IFCONTROL:"{{#IFNAME}}"}}=0'
        f' or {LINKDOWN_IFALIAS_RECOVERY}'
    )


def linkdown_has_diff_guard(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    return bool(LINKDOWN_DIFF_RE.search(expr or '')) or '.diff()' in compact


def linkdown_has_ifalias_gate(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    return LINKDOWN_IFALIAS_GATE.replace(' ', '') in compact


def linkdown_is_not_up(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    if linkdown_has_diff_guard(expr) or 'LINKDOWN.HIGH' in compact:
        return False
    return bool(LINKDOWN_NOT_UP_RE.search(compact)) and linkdown_has_ifalias_gate(expr)


def linkdown_recovery_is_up(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    return bool(
        re.search(
            r'last\(/[^)]*net\.if\.status\[ifOperStatus\.\{#SNMPINDEX\}\]\)=1',
            compact,
        )
    ) and '<>2' not in compact and LINKDOWN_IFALIAS_RECOVERY.replace(' ', '') in compact


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
