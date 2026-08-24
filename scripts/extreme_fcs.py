"""EtherLike FCS / alignment counters (no Django)."""

from __future__ import annotations

import re

FCS_OID = '1.3.6.1.2.1.10.7.2.1.3'
ALIGN_OID = '1.3.6.1.2.1.10.7.2.1.2'
SYMBOL_OID = '1.3.6.1.2.1.10.7.2.1.18'
DISCONT_OID = '1.3.6.1.2.1.31.1.1.1.19'
FCS_KEY = 'net.if.in.fcs[dot3StatsFCSErrors.{#SNMPINDEX}]'
ALIGN_KEY = 'net.if.in.align[dot3StatsAlignmentErrors.{#SNMPINDEX}]'
SYMBOL_KEY = 'net.if.in.symbol[dot3StatsSymbolErrors.{#SNMPINDEX}]'
DISCONT_KEY = 'net.if.discontinuity[ifCounterDiscontinuityTime.{#SNMPINDEX}]'
FCS_WARN_MACRO = '{$IF.FCS.WARN}'
FCS_WARN_CTX = '{$IF.FCS.WARN:"{#IFNAME}"}'
FCS_WARN_DEFAULT = '2'


def fcs_rate_expr(template: str) -> str:
    fcs = f'/{template}/{FCS_KEY}'
    align = f'/{template}/{ALIGN_KEY}'
    disc = f'/{template}/{DISCONT_KEY}'
    return (
        f'(min({fcs},5m)>{FCS_WARN_CTX}'
        f' or min({align},5m)>{FCS_WARN_CTX})'
        f' and last({disc})=last({disc},#2)'
    )


def fcs_recovery_expr(template: str) -> str:
    fcs = f'/{template}/{FCS_KEY}'
    align = f'/{template}/{ALIGN_KEY}'
    return (
        f'max({fcs},5m)<{FCS_WARN_CTX}*0.8'
        f' and max({align},5m)<{FCS_WARN_CTX}*0.8'
    )


def fcs_expr_is_rate_with_hysteresis(expr: str) -> bool:
    compact = re.sub(r'\s+', '', expr or '')
    return (
        'dot3StatsFCSErrors' in compact
        and 'min(' in compact
        and '5m' in compact
        and 'ifCounterDiscontinuityTime' in compact
    )
