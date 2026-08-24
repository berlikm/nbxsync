"""VOSS fabric / MLT / optional LLD / reboot helpers (no Django)."""

from __future__ import annotations

import re

VOSS_TEMPLATE = 'Extreme VOSS by SNMP'
VIST_CONTROL = '{$VIST.CONTROL}'
ISIS_CONTROL = '{$ISIS.CONTROL}'
CARD_CONTROL = '{$CARD.CONTROL}'
MLT_CONTROL = '{$MLT.CONTROL}'
MLT_EXPECTED = '{$MLT.EXPECTED}'
ISIS_EXPECTED = '{$ISIS.EXPECTED}'
ISIS_EXPECTED_GATE = '{$ISIS.EXPECTED:"{#SNMPINDEX}"}=1'
MLT_EXPECTED_GATE = '{$MLT.EXPECTED:"{#SNMPINDEX}"}=1'
VIST_UP = '{$VIST.UP_STATUS}'
VIST_DOWN = '{$VIST.DOWN_STATUS}'
ISIS_UP = '{$ISIS.CIRCUIT.UP_STATUS}'
ISIS_DOWN = '{$ISIS.CIRCUIT.DOWN_STATUS}'
MLT_UP = '{$MLT.AGG.UP_STATUS}'
MLT_DOWN = '{$MLT.AGG.DOWN_STATUS}'
UNSUPPORTED_MAX = '{$UNSUPPORTED.MAX}'
UNSUPPORTED_WARN = '{$UNSUPPORTED.WARN}'
UPTIME_WRAP_MAX = '{$UPTIME.WRAP.MAX}'

VOSS_OPTIONAL_LLD_KEYS = (
    'card.discovery',
    'isis.circuit.discovery',
    'isis.adj.discovery',
    'spbm.node.discovery',
    'spbm.plsbstate.discovery',
    'smlt.discovery',
)

# VOSS Core/Dist/Mgmt fabric members are BASE-1 and BASE-2. EXOS stacks also
# use -1/-2; callers must filter platform VOSS|Fabric Engine.
FABRIC_MEMBER_RE = re.compile(r'^(?P<base>.+)-(?P<member>[12])$')
VOSS_PLATFORM_RE = re.compile(r'VOSS|Fabric Engine', re.I)
FABRIC_ROLES = frozenset(
    {
        'Switch Core',
        'Switch Dist',
        'Switch Distribution',
        'Distribution',
        'Dist',
        'Switch DIST',
        'Switch Mgmt',
        'Switch Management',
        'Mgmt',
        'Management',
    }
)

LLD_EMPTY_JSON = '[]'


def is_voss_platform(platform_name: str | None) -> bool:
    return bool(VOSS_PLATFORM_RE.search(platform_name or ''))


def fabric_pair_hostnames(
    devices: list[tuple[str, str, str]],
) -> list[str]:
    """Return names that have a VOSS Core/Dist/Mgmt twin (BASE-1 and BASE-2).

    Each row is ``(name, platform, role)``. Access and EXOS stacks are ignored.
    """
    grouped: dict[tuple[str, str], dict[str, str]] = {}
    for name, platform, role in devices:
        if not is_voss_platform(platform):
            continue
        if (role or '') not in FABRIC_ROLES:
            continue
        match = FABRIC_MEMBER_RE.match(name or '')
        if not match:
            continue
        site_key = (match.group('base'), role or '')
        grouped.setdefault(site_key, {})[match.group('member')] = name
    names: list[str] = []
    for members in grouped.values():
        if '1' in members and '2' in members:
            names.extend(members[m] for m in ('1', '2'))
    return sorted(set(names))


def fabric_pair_macros(*, silence: bool = False) -> dict[str, str]:
    """Host macros for a known VOSS fabric pair. Card stays collect-only.

    ``silence=True`` is ``--cutover-silence``: host macros would otherwise
    beat the global MLT/VIST overlay and arm fabric High during LM migration.
    """
    value = '0' if silence else '1'
    return {
        VIST_CONTROL: value,
        ISIS_CONTROL: value,
        ISIS_EXPECTED: value,
    }


def lld_allowlists_unsupported(rule: dict) -> bool:
    """True when LLD maps not-supported to an empty JSON array."""
    for step in rule.get('preprocessing') or []:
        raw = str(step.get('type') or '').upper()
        if raw not in {'CHECK_NOT_SUPPORTED', '26'}:
            continue
        handler = str(step.get('error_handler') or '').upper()
        params = step.get('error_handler_params')
        if params is None:
            params = step.get('params')
        text = params[0] if isinstance(params, list) and params else str(params or '')
        if handler in {'CUSTOM_VALUE', '1'} and LLD_EMPTY_JSON in text:
            return True
        if text.strip() == LLD_EMPTY_JSON:
            return True
    return False


def mlt_down_expr(*, template: str = VOSS_TEMPLATE) -> str:
    item = f'/{template}/net.mlt.agg.state[rcMltAggOperState.{{#SNMPINDEX}}]'
    return (
        f'{MLT_CONTROL}=1 and min({item},#3)={MLT_DOWN} and '
        f'(max({item},#15)={MLT_UP} or {MLT_EXPECTED_GATE})'
    )


def mlt_recovery_expr(*, template: str = VOSS_TEMPLATE) -> str:
    item = f'/{template}/net.mlt.agg.state[rcMltAggOperState.{{#SNMPINDEX}}]'
    return f'last({item})={MLT_UP} or {MLT_CONTROL}=0'


def mlt_expr_is_persistent_down(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    return (
        f'{MLT_CONTROL}=1' in compact
        and 'min(' in compact
        and '#3' in compact
        and 'max(' in compact
        and '#15' in compact
        and 'diff(' not in compact.lower()
        and 'last(#1)<>last(#2)' not in compact
    )


def vist_down_expr(*, template: str = VOSS_TEMPLATE) -> str:
    item = f'/{template}/fabric.vist.status[rcVirtualIstSessionStatus.0]'
    return (
        f'{VIST_CONTROL}=1 and min({item},#3)={VIST_DOWN} and max({item},#15)={VIST_UP}'
    )


def vist_recovery_expr(*, template: str = VOSS_TEMPLATE) -> str:
    item = f'/{template}/fabric.vist.status[rcVirtualIstSessionStatus.0]'
    return f'last({item})={VIST_UP} or {VIST_CONTROL}=0'


def vist_expr_is_loss(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    return (
        f'{VIST_CONTROL}=1' in compact
        and 'min(' in compact
        and '#3' in compact
        and 'max(' in compact
        and '#15' in compact
    )


def isis_down_expr(*, template: str = VOSS_TEMPLATE) -> str:
    item = f'/{template}/fabric.isis.circuit.oper[rcIsisCircuitOperState.{{#SNMPINDEX}}]'
    return (
        f'{ISIS_CONTROL}=1 and {ISIS_EXPECTED_GATE} and '
        f'min({item},#3)={ISIS_DOWN} and max({item},#15)={ISIS_UP}'
    )


def isis_recovery_expr(*, template: str = VOSS_TEMPLATE) -> str:
    item = f'/{template}/fabric.isis.circuit.oper[rcIsisCircuitOperState.{{#SNMPINDEX}}]'
    return f'last({item})={ISIS_UP} or {ISIS_CONTROL}=0'


def isis_expr_is_expected_loss(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    return (
        f'{ISIS_CONTROL}=1' in compact
        and '{$ISIS.EXPECTED:"{#SNMPINDEX}"}=1' in compact
        and 'min(' in compact
        and '#3' in compact
        and 'max(' in compact
        and '#15' in compact
    )


def reboot_expr(*, template: str = VOSS_TEMPLATE) -> str:
    boots = f'/{template}/system.snmp.engine.boots[snmpEngineBoots.0]'
    hw = f'/{template}/system.hw.uptime[hrSystemUptime.0]'
    net = f'/{template}/system.net.uptime[sysUpTime.0]'
    return (
        f'(last({boots})>0 and last({boots})>last({boots},#2)) or '
        f'(last({boots})=0 and last({hw})=0 and last({net})<10m and '
        f'last({net},#2)<{UPTIME_WRAP_MAX})'
    )


def reboot_expr_uses_engine_boots(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    return 'snmpEngineBoots' in compact and UPTIME_WRAP_MAX.replace(' ', '') in compact
