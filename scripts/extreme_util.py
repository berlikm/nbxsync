"""Stock EXOS {$IF.UTIL.MAX}=90 beats global 101 (no Django)."""

from __future__ import annotations

IF_UTIL_MAX_MACRO = '{$IF.UTIL.MAX}'
IF_UTIL_MAX_OFF = '101'
IF_UTIL_TEMPLATE_NAMES = ('Extreme EXOS by SNMP', 'Extreme VOSS by SNMP')
IF_UTIL_DESCRIPTION = (
    'Silence stock bandwidth trigger (101=off). Template macros beat globals; '
    'stock Extreme EXOS ships 90 which created capacity Warnings.'
)


def if_util_is_off(value: str | None) -> bool:
    return str(value or '') == IF_UTIL_MAX_OFF


def effective_macro_from_layers(
    *,
    host: dict[str, str],
    inherited: dict[str, str],
    template: dict[str, str],
    global_macros: dict[str, str],
    name: str,
) -> tuple[str | None, str]:
    """Host > inherited/template > global. Returns (value, source)."""
    if name in host:
        return host[name], 'host'
    if name in inherited:
        return inherited[name], 'inherited'
    if name in template:
        return template[name], 'template'
    if name in global_macros:
        return global_macros[name], 'global'
    return None, 'missing'
