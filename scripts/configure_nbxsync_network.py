#!/usr/bin/env python3
"""
nbxSync Network Configuration Script (Extreme switching)

Sibling of ``configure_nbxsync_zerotouch.py``. Same runtime shape:

  * Django + NetBox lab bootstrap
  * ``ensure()`` / ``get_or_create`` idempotent rows
  * ``--simulate`` → prefixed synthetic estate + SyncHostJob + live Zabbix asserts
  * Production apply uses ``NBX_ZABBIX_TOKEN`` (lab: ``--simulate`` reads lab.json)

Owns the Extreme switching half of Track B (see ``zabbix/01-extreme-switching.md``):

  * Import Extreme VOSS / IQ Engine / EXOS Observability / Port Speed Expect / Routing templates into Zabbix
  * Patch stock Extreme EXOS EtherLike duplex LLD with the same IFALIAS filters as net.if.discovery
  * Patch stock EXOS ``net.if.discovery`` rollout (15m / disable-lost immediately / delete after 7d).
    Per-rule ``timeout`` stays empty: classic SNMP OID LLD is not ``walk[``/``get[``, so Zabbix
    requires the proxy/global SNMP timeout.
  * Patch stock EXOS ``psu.discovery`` to keep installed FRUs (status not
    ``notPresent`` **or** a real serial) and queue check-now so padding leaves and
    serialled unplugged units appear (no fork, no host sync). Dummy serials
    such as ``--`` are wiped in LLD JS.
  * Patch VOSS ``psu.discovery`` / ``psu.detail.discovery`` to skip ``empty(2)``
    even when firmware fills serial with ``--``, delete lost padding immediately,
    and queue check-now
  * PSU Average is ``last()<>{$PSU.OK_STATUS}`` (VOSS also
    ``and last()<>{$PSU.EMPTY_STATUS}``) so two present / one connected
    tickets (EXOS ``presentPowerOff`` / serialled ``notPresent``, VOSS
    ``unknown`` / ``down``). VOSS empty bays stay silent.
  * Discovered link-down stays **Average** (drop leftover USW High if a prior apply created it).
    Stock ``.diff()`` / ``last(#1)<>last(#2)`` is stripped so an admin-up port that
    never came up still tickets. Oper-status **not up** (``<>1``) so
    ``lowerLayerDown(7)`` matches the honeycomb, not only ``down(2)``.
    Recovery is ``last()=1``. Manual close is off so ACK cannot mute a
    still-down port. Same prototype on EXOS and VOSS. Core/Dist/Mgmt every
    admin-up except X. Access only a grammar display-string: LLD plus
    ``{$LINKDOWN.IFALIAS:"{#IFALIAS}"}``. ``--apply`` writes those Access
    host macros (not HostSync, not Core). Chassis OOB ifName ``mgmt`` /
    ``Management`` is skipped in ``{$NET.IF.IFNAME.NOT_MATCHES}`` (unused,
    not connected) — not ``{$IFCONTROL}``.
  * Rewrite Unicode operators in Extreme trigger / prototype ``event_name`` to
    ASCII (``!=`` not ``≠`` / ``Γëá``). YAML import can leave the old glyph on
    live prototypes; LLD check-now copies the ASCII title onto discovered
    Speed Expect triggers. Open Problems keep the title from create.
  * Override stock Extreme EXOS/VOSS template ``{$TEMP_*}`` macros (stock 55/65 wins over globals)
  * Patch stock Extreme EXOS/VOSS template ``{$IF.UTIL.MAX}=101`` so stock EXOS ``90`` cannot beat the global off-switch (effective-macro assert on Access/Core)
  * Disable ICMP loss/RTT triggers on EXOS/VOSS/IQ (items stay for Health; CH proxy RTT is WAN)
  * Health dashboards ship in YAML (VOSS/IQ + EXOS Observability companion). ``--apply`` patches the stock EXOS **Network interfaces** Overview + Port layout and drops leftover Health Diagnostics pages.
  * Platform TemplateRules: EXOS → Observability companion (nests stock); VOSS / IQ Engine → Extreme * by SNMP
  * Switch role IFALIAS / IFTYPE macros via ZabbixMacroAssignment (inheritance resolves these)
  * FortiGate HTTP: companion **FortiGate Observability** (nests Cloud 7.0-2 HTTP +
    ICMP Ping) via platform Template Rule **FortiOS**. Fleet macros + shared
    ``{$FGATE.API.TOKEN}`` on **Platform FortiOS**, not role Firewall.
    ``{$FGATE.API.FQDN}`` is Platform FortiOS Jinja on ``primary_ip4``.
    Fail-closed preflight. FortiOS does not inherit SNMP Monitoring.
    After SNMP Monitoring is pruned from role Firewall, assign CG
    **FortiGate HTTP** on Platform FortiOS so Site Group Agent Monitoring
    (ICMP Ping) does not win. Observability already nests ICMP. Apply prunes
    leftover ICMP/HTTP/SNMP from FortiOS devices/platforms/device types —
    not from agent CGs. Operator path is ``--apply-fortigate-http`` — do
    **not** re-run zerotouch. Do not dual-link HTTP+SNMP.
  * Cato account collector: ``--apply-cato`` / ``--check-cato`` import
    **Cato Networks by HTTP**, fail-close on GraphQL preflight, and converge
    the one owned interface-free host. No HostSync, no Extreme import, no
    Socket role mutation. Do **not** re-run zerotouch to refresh the collector.
  * Global **destination** macros on the Zabbix server object (production end-state).
    ``{$PORTID.LLD.*}`` defaults live on Extreme Port Speed Expect — not globals.
  * Optional ``--cutover-silence`` overlay (999 / MLT=0) for temporary LM migration only
  * Optional Speed Expect **role** assignment (``--link-speed-expect``). Prefer nesting
    on VOSS / EXOS Observability so unlabeled ports stay silent and labels start
    working on the next LLD without HostSync. Do not also role-assign if nested
    (Zabbix rejects a template linked both directly and through a parent).

Stage matrix (what each flag enables):
  ``--apply``                     = stages 0–3: template imports + EXOS/VOSS/IQ rules + IFALIAS + destination globals + TEMP/util/ICMP/Health patches.
                                    Speed Expect is nested on VOSS and EXOS Observability (empty ifAlias = not discovered).
                                    Writes VOSS fabric-pair V-IST/ISIS host macros (loss of an established session).
                                    Also writes FortiOS platform FortiGate HTTP macros (no Forti HostSync, no FortiOS retarget).
  ``--apply-firewall-macros``     = NetBox-only FortiOS platform macros. No Extreme import, no Zabbix API, no HostSync, no FortiOS retarget.
  ``--apply-fortigate-http``      = FortiGate HTTP cutover without zerotouch: lookup Cloud **Zabbix, 7.0-2**, patch ZBX-27082 / WAN state, import Observability companion, FortiOS rule only (not role Firewall). Fail-closed preflight. No HostSync.
  ``--check-cato`` / ``--apply-cato`` = Cato collector refresh without zerotouch: GraphQL preflight, import **Cato Networks by HTTP**, converge ``cato-account-*``. No HostSync, no Socket hold/release.
  ``--apply --link-speed-expect`` = extra NetBox role assignment. Skip while nested — duplicate link on HostSync.
  ``--apply --cutover-silence``   = cutover overlay: TEMP/OPTIC=999, MLT/VIST=0 (temporary, re-run without to restore)
  Routing / Stage 6 context macros = manual (Extreme switching page)

Re-apply safety (estate already has switches/APs in Zabbix):
  * Does **not** delete hosts, interfaces, history, or hostids
  * Does **not** mass-sync every device (template updates inherit in Zabbix)
  * After role macros, writes Switch Access Zabbix **host** macros (IFALIAS /
    PORTID / ``{$LINKDOWN.IFALIAS}`` grammar regex) and logs remaining Switch*
    drift. Does not mass-HostSync. Does not rewrite Core/Dist/Mgmt IFALIAS.
    Also writes ``{$VIST.CONTROL}`` / ``{$ISIS.CONTROL}`` / ``{$ISIS.EXPECTED}``
    on VOSS Core/Dist/Mgmt ``BASE-1``/``BASE-2`` name twins (not EXOS stacks,
    not Access, not card). Cutover-silence writes those three to ``0``.
  * YAML ``deleteMissing: false`` — retired items linger; LLD is not wiped
  * ``--apply`` without ``--link-speed-expect`` does **not** unlink a leftover role assignment
    (Speed Expect is nested on the platform templates; skip the flag).
  * Empty SNMP secrets are zerotouch's job and must not blank existing CG passphrases

Import policy:
  YAML imports use deleteMissing=False (safe — retired items linger but templates don't lose content).
  Re-run ``--apply`` after Extreme template upgrades to re-assert TEMP/EtherLike/ICMP/Health/PSU-empty/ASCII-title patches.
  Speed Expect nests on VOSS / Observability. Do not pass ``--link-speed-expect`` while nested.

Does **not** re-implement SiteGroup Agent / hostgroup-first / Server OOB — call
``configure_nbxsync_zerotouch.py`` for that. This script assumes SNMP CG on Switch*
roles (zerotouch step 5b) and only layers Extreme-specific templates + macros.

Usage::

  # Lab proof (NetBox + live Zabbix) — destination macros
  PYTHONPATH=/workspace/.deps/netbox/netbox:/workspace \\
    /workspace/.deps/venv/bin/python scripts/configure_nbxsync_network.py --simulate

  # Apply destination network deltas (production token)
  export NBX_ZABBIX_TOKEN=...
  # If NetBox has no row named "Zabbix Production", also set NBX_ZABBIX_URL.
  python scripts/configure_nbxsync_network.py --apply

  # FortiOS platform macros only (no Extreme YAML / check-now / HostSync / FortiOS retarget)
  python scripts/configure_nbxsync_network.py --apply-firewall-macros

  # FortiGate HTTP cutover (no zerotouch, no Extreme YAML, no HostSync)
  # Looks up FortiGate by HTTP already in Zabbix Cloud (vendor Zabbix, 7.0-2).
  # Never imports bundled 7.0-3 — that would overwrite Cloud.
  python scripts/configure_nbxsync_network.py --check-fortigate-http  # read-only
  python scripts/configure_nbxsync_network.py --apply-fortigate-http

  # Cato account collector refresh (no zerotouch, no Extreme YAML, no HostSync)
  python scripts/configure_nbxsync_network.py --check-cato   # GraphQL preflight + collector shape
  python scripts/configure_nbxsync_network.py --apply-cato

  # Temporary LM cutover silence only (not the long-term target)
  python scripts/configure_nbxsync_network.py --apply --cutover-silence

  # Zabbix API only (no NetBox) — thin smoke, not the real path
  python scripts/configure_nbxsync_network.py --zabbix-only
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import traceback
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')

_NETBOX = Path('/workspace/.deps/netbox/netbox')
if _NETBOX.exists() and str(_NETBOX) not in sys.path:
    sys.path.insert(0, str(_NETBOX))
if '/workspace' not in sys.path:
    sys.path.insert(0, '/workspace')
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import django

django.setup()

from django.contrib.contenttypes.models import ContentType
from dcim.models import Device, DeviceRole, DeviceType, Interface, Manufacturer, Platform, Site, SiteGroup
from extras.models import Tag
from ipam.models import IPAddress

from nbxsync import models as M
from nbxsync.choices import (
    HostInterfaceRequirementChoices,
    ZabbixHostInterfaceSNMPVersionChoices,
    ZabbixHostInterfaceTypeChoices,
    ZabbixInterfaceTypeChoices,
    ZabbixInterfaceUseChoices,
    ZabbixMacroTypeChoices,
    ZabbixTLSChoices,
)
from nbxsync.jobs.synchost import SyncHostJob
from nbxsync.utils import get_assigned_zabbixobjects
from nbxsync.utils.zabbixconnection import ZabbixConnection

from fortigate_http import (
    AGENT_MONITORING_CG as _AGENT_MONITORING_CG,
    DEVICE_DUAL_LINK_TEMPLATES as _DEVICE_DUAL_LINK_TEMPLATES,
    FGATE_API_PORT as _FGATE_API_PORT,
    FGATE_AUTOMATION_TOKEN_ENV as _FGATE_AUTOMATION_TOKEN_ENV,
    FGATE_FQDN_JINJA as _FGATE_FQDN_JINJA,
    FGATE_FQDN_MACRO as _FGATE_FQDN_MACRO,
    FGATE_TOKEN_MACRO as _FGATE_TOKEN_MACRO,
    FIREWALL_ROLE as _FIREWALL_ROLE,
    FIREWALL_ROLE_FORTI_TEMPLATES as _FIREWALL_ROLE_FORTI_TEMPLATES,
    FMG_FAZ_PLATFORM_PATTERN as _FMG_FAZ_PLATFORM_PATTERN,
    FORTIGATE_HTTP_CG as _FORTIGATE_HTTP_CG,
    FORTIGATE_HTTP_CLOUD_VENDOR as _FORTIGATE_HTTP_CLOUD_VENDOR,
    FORTIGATE_HTTP_TEMPLATE as _FORTIGATE_HTTP_TEMPLATE,
    FORTIGATE_OBSERVABILITY_TEMPLATE as _FORTIGATE_OBSERVABILITY_TEMPLATE,
    FORTIGATE_SNMP_TEMPLATE as _FORTIGATE_SNMP_TEMPLATE,
    FORTIOS_COLLIDING_TEMPLATES as _FORTIOS_COLLIDING_TEMPLATES,
    FORTIOS_PLATFORM_MACROS as _FORTIOS_PLATFORM_MACROS,
    FORTIOS_PLATFORM_PATTERN as _FORTIOS_PLATFORM_PATTERN,
    FORTIOS_TEMPLATE_RULE as _FORTIOS_TEMPLATE_RULE,
    ICMP_PING_TEMPLATE as _ICMP_PING_TEMPLATE,
    SNMP_MONITORING_CG as _SNMP_MONITORING_CG,
    MEMORY_EXTREME_MACRO as _MEMORY_EXTREME_MACRO,
    MEMORY_GREEN_MACRO as _MEMORY_GREEN_MACRO,
    MEMORY_RED_MACRO as _MEMORY_RED_MACRO,
    format_vendor_label as _format_vendor_label,
    fetch_fortigate_api as _fetch_fortigate_api,
    flatten_forti_cmdb_list as _flatten_forti_cmdb_list,
    flatten_forti_sdwan_cmdb as _flatten_forti_sdwan_cmdb,
    fortigate_ifname_regex as _fortigate_ifname_regex,
    fortigate_memory_thresholds as _fortigate_memory_thresholds,
    is_cloud_fortigate_http_vendor as _is_cloud_fortigate_http_vendor,
    platform_is_fmg_faz as _platform_is_fmg_faz,
    platform_is_fortios as _platform_is_fortios,
    probe_fortigate_api as _probe_fortigate_api,
)
from fortigate_http_zabbix import (
    apply_fortigate_http_patches,
    ensure_overlay_census_items,
    ensure_observability_trigger_dependencies,
    ensure_observability_primary_trigger_gates,
    inspect_http_scripts,
)
from extreme_ascii_titles import title_payload as _title_payload
from extreme_health_zabbix import (
    IQ_HEALTH_MACROS,
    SPEED_EXPECT_HEALTH_MACROS,
    VOSS_HEALTH_MACROS,
    apply_extreme_health_patches,
    assert_template_dashboard,
    assert_exos_stock_interface_grid,
    assert_template_macros,
    assert_wan_icmp_noise_disabled,
)
from extreme_linkdown import (
    ACCESS_IFALIAS_MATCHES,
    ACCESS_PORTID_MATCHES,
    IFNAME_NOT_MATCHES as _IFNAME_NOT_MATCHES,
    IFNAME_NOT_MATCHES_MACRO as _IFNAME_NOT_MATCHES_MACRO,
    IFNAME_OOB_ITEM_NEEDLES as _IFNAME_OOB_ITEM_NEEDLES,
    LINKDOWN_HIGH_GATE as _LINKDOWN_HIGH_GATE,
    LINKDOWN_HIGH_MACRO_PREFIX as _LINKDOWN_HIGH_MACRO_PREFIX,
    LINKDOWN_IFALIAS_ACCESS_DEFAULT as _LINKDOWN_IFALIAS_ACCESS_DEFAULT,
    LINKDOWN_IFALIAS_MACRO as _LINKDOWN_IFALIAS_MACRO,
    LINKDOWN_IFALIAS_TEMPLATE_VALUE as _LINKDOWN_IFALIAS_TEMPLATE_VALUE,
    LINKDOWN_RECOVERY_MODE as _LINKDOWN_RECOVERY_MODE,
    LINKDOWN_TEMPLATES as _LINKDOWN_TEMPLATES,
    LINKDOWN_TRIGGER_DESCRIPTION as _LINKDOWN_TRIGGER_DESCRIPTION,
    access_zabbix_host_macros as _access_zabbix_host_macros,
    canonicalize_linkdown_problem as _canonicalize_linkdown_problem,
    canonicalize_linkdown_recovery as _canonicalize_linkdown_recovery,
    is_platform_linkdown_name as _is_platform_linkdown_name,
    linkdown_has_diff_guard as _linkdown_has_diff_guard,
    linkdown_has_ifalias_gate as _linkdown_has_ifalias_gate,
    linkdown_ifalias_regex_macro as _linkdown_ifalias_regex_macro,
    linkdown_is_not_up as _linkdown_is_not_up,
    linkdown_manual_close_on as _linkdown_manual_close_on,
    linkdown_recovery_is_up as _linkdown_recovery_is_up,
    linkdown_expr_equal as _linkdown_expr_equal,
    ifname_not_matches_excludes_oob as _ifname_not_matches_excludes_oob,
)
from extreme_psu import (
    EXOS_PSU_DISCOVERY_OID as _PSU_DISCOVERY_OID,
    EXOS_PSU_SERIAL_OID as _PSU_SERIAL_OID,
    EXOS_PSU_STATUS_OID as _PSU_STATUS_OID,
    PSU_DISCOVERY_KEYS as _PSU_NOT_UP_DISCOVERY_KEYS,
    PSU_EMPTY_BY_TEMPLATE as _PSU_EMPTY_BY_TEMPLATE,
    PSU_EMPTY_MACRO as _PSU_EMPTY_MACRO,
    PSU_OK_BY_TEMPLATE as _PSU_OK_BY_TEMPLATE,
    PSU_OK_MACRO as _PSU_OK_MACRO,
    PSU_TEMPLATES as _PSU_NOT_UP_TEMPLATES,
    VOSS_PSU_DETAIL_DISCOVERY_OID as _VOSS_PSU_DETAIL_DISCOVERY_OID,
    VOSS_PSU_DETAIL_STATUS_OID as _VOSS_PSU_DETAIL_STATUS_OID,
    VOSS_PSU_DISCOVERY_OID as _VOSS_PSU_DISCOVERY_OID,
    VOSS_PSU_SERIAL_OID as _VOSS_PSU_SERIAL_OID,
    VOSS_PSU_STATUS_OID as _VOSS_PSU_STATUS_OID,
    psu_expr_is_not_up as _psu_expr_is_not_up,
    psu_lld_api_filter as _psu_lld_api_filter,
    psu_lld_keeps_installed_fru as _psu_lld_keeps_installed_fru,
    psu_lld_preprocessing_payload as _psu_lld_preprocessing_payload,
    psu_power_off_name_match as _psu_power_off_name_match,
    psu_trigger_name_match as _psu_trigger_name_match,
    rewrite_psu_not_up_expr as _rewrite_psu_not_up_expr,
)
from extreme_util import (
    IF_UTIL_DESCRIPTION as _IF_UTIL_DESCRIPTION,
    IF_UTIL_MAX_MACRO as _IF_UTIL_MAX_MACRO,
    IF_UTIL_MAX_OFF as _IF_UTIL_MAX_OFF,
    IF_UTIL_TEMPLATE_NAMES as _IF_UTIL_TEMPLATE_NAMES,
    effective_macro_from_layers as _effective_macro_from_layers,
    if_util_is_off as _if_util_is_off,
)
from extreme_fabric import (
    fabric_pair_hostnames as _fabric_pair_hostnames,
    fabric_pair_macros as _fabric_pair_macros,
)

# Reuse zerotouch helpers when present (same ensure/ct/slugify contract).
try:
    import configure_nbxsync_zerotouch as ztc
except ImportError:  # pragma: no cover
    ztc = None

logger = logging.getLogger('configure_nbxsync_network')
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

ROOT = Path(__file__).resolve().parents[1]
LAB_JSON = Path('/home/ubuntu/zabbix-docker/lab.json')
REPORT_JSON = Path('/opt/cursor/artifacts/network_nbxsync_sim_results.json')
REPORT_MD = Path('/opt/cursor/artifacts/NETWORK_NBXSYNC_SIM_REPORT.md')
PREFIX = 'nwn-'
SIM_SERVER_NAME = 'Network Configure Lab'
RESULTS: list[dict] = []

TEMPLATE_FILES = {
    # Speed Expect first — VOSS and EXOS Observability nest it.
    'Extreme Port Speed Expect by SNMP': ROOT / 'zabbix/templates/extreme_port_speed_expect_snmp/template_net_extreme_port_speed_expect_snmp.yaml',
    'Extreme VOSS by SNMP': ROOT / 'zabbix/templates/extreme_voss_snmp/template_net_extreme_voss_snmp.yaml',
    'Extreme EXOS Observability': ROOT / 'zabbix/templates/extreme_exos_observability_snmp/template_extreme_exos_observability_snmp.yaml',
    'Extreme Routing by SNMP': ROOT / 'zabbix/templates/extreme_routing_snmp/template_net_extreme_routing_snmp.yaml',
    'Extreme IQ Engine by SNMP': ROOT / 'zabbix/templates/extreme_iq_engine_snmp/template_net_extreme_iq_engine_snmp.yaml',
}

# Bundled stock YAML is vendor 7.0-3. Cloud is Zabbix, 7.0-2. Apply looks up
# Cloud and never calls configuration.import_ on this file.
FORTIGATE_HTTP_YAML = ROOT / 'zabbix/templates/fortinet_fortigate_http/template_net_fortigate_http.yaml'
FORTIGATE_OBSERVABILITY_YAML = (
    ROOT / 'zabbix/templates/fortinet_fortigate_observability/template_fortigate_observability.yaml'
)
CATO_HTTP_YAML = ROOT / 'zabbix/templates/cato_http/template_cato_networks_http.yaml'

_SPEED_EXPECT_TEMPLATE = 'Extreme Port Speed Expect by SNMP'
_SPEED_EXPECT_DISCOVERY_KEY = 'net.if.speedexpect.discovery'
_ASCII_TITLE_TEMPLATES = tuple(TEMPLATE_FILES) + ('Extreme EXOS by SNMP',)

# Role → port-scoping macros (zabbix/01-extreme-switching.md).
# Core / Dist / Mgmt = every admin-up ethernet/LAG except X*.
# Access = opt-in grammar classes (USW/US/UP/MON/UW/TMON). Unlabelled desk
# ports, N, and X still produce no items. Speed Expect uses PORTID.* (no UW/TMON
# — those have no PHY token / no speed Warning).
CORE_LIKE_IF_MACROS = {
    '{$NET.IF.IFALIAS.MATCHES}': '.*',
    '{$NET.IF.IFALIAS.NOT_MATCHES}': '^X(-|$)',
    '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
}
ROLE_MACROS = {
    'Switch Core': dict(CORE_LIKE_IF_MACROS),
    'Switch Dist': dict(CORE_LIKE_IF_MACROS),
    'Switch Mgmt': dict(CORE_LIKE_IF_MACROS),
    'Switch Access': {
        '{$NET.IF.IFALIAS.MATCHES}': ACCESS_IFALIAS_MATCHES,
        '{$NET.IF.IFALIAS.NOT_MATCHES}': 'CHANGE_IF_NEEDED',
        '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
        '{$PORTID.LLD.IFALIAS.MATCHES}': ACCESS_PORTID_MATCHES,
        _LINKDOWN_IFALIAS_MACRO: _LINKDOWN_IFALIAS_ACCESS_DEFAULT,
    },
}

# Extra ZabbixMacroAssignment rows (same macro, regex context). HostSync / --apply
# host-macro write both need the full name ``{$LINKDOWN.IFALIAS:regex:"…"}``.
ROLE_REGEX_MACRO_ASSIGNMENTS = {
    'Switch Access': (
        {
            'macro': _LINKDOWN_IFALIAS_MACRO,
            'context': ACCESS_IFALIAS_MATCHES,
            'value': '1',
        },
    ),
}

# There is no Switch Hybrid role.

# NetBox role name variants → ROLE_MACROS key (Dist must get Core-like all-ports scope).
ROLE_NAME_ALIASES = {
    'Switch Dist': (
        'Switch Dist',
        'Switch Distribution',
        'Distribution',
        'Dist',
        'Switch DIST',
    ),
}

# Production end-state (default). Stock EXOS 55/65 is wrong for G2+ internal sensors
# (GTAC 000088439: Normal often 10–100, Max 110). Prefer vendor overTemp *status*
# as the hard alarm; value macros warn 95 / crit 100 on Extreme templates only.
# TEMP_* are NOT global — they would affect servers/storage/APs too.
DESTINATION_GLOBAL_MACROS = {
    '{$IF.UTIL.MAX}': '101',  # stock util% off until stage-6 context macros
    '{$OPTIC.TEMP.CRIT}': '70',
    '{$OPTIC.TEMP.MAX}': '150',
    '{$OPTIC.RX.DBM.MIN}': '-100',  # RX dBm value trigger removed; -100 quiets leftovers
    '{$OPTIC.RX.DBM.FLOOR}': '-39',
    '{$OPTIC.DOM.ALARM_HIGH}': '3',
    '{$OPTIC.DOM.ALARM_LOW}': '5',
    '{$MLT.CONTROL}': '1',  # three-sample down after the MLT was up; unused stay silent; recover on up
    '{$VIST.CONTROL}': '0',  # --apply sets host 1 on VOSS BASE-1/BASE-2 pairs
    '{$IST.CONTROL}': '0',  # classic IST unused on FE fabric
    '{$SNMP.TIMEOUT}': '5m',
}

# Extreme EXOS/VOSS template-only macros (NOT global — scoped to switch templates).
# Stock EXOS ships {$TEMP_WARN}=55 / {$TEMP_CRIT}=65 — way too low for G2+.
EXTREME_TEMPLATE_TEMP_MACROS = {
    '{$TEMP_WARN}': '95',
    '{$TEMP_CRIT}': '100',
    '{$TEMP_CRIT_LOW}': '-273',
}

# Temporary LM-migration overlay only — never the long-term target.
# TEMP_* stay template-scoped (EXOS/VOSS). Putting them in GLOBAL_MACROS would
# create Zabbix *global* macros and mute AP/server temperature as well.
CUTOVER_SILENCE_OVERLAY = {
    '{$OPTIC.TEMP.CRIT}': '999',
    '{$OPTIC.RX.DBM.MIN}': '-100',
    '{$MLT.CONTROL}': '0',
}
CUTOVER_TEMPLATE_TEMP_MACROS = {
    '{$TEMP_WARN}': '999',
    '{$TEMP_CRIT}': '999',
}

GLOBAL_MACROS = dict(DESTINATION_GLOBAL_MACROS)
_CUTOVER_SILENCE = False


def apply_macro_mode(*, cutover_silence: bool = False) -> None:
    """Set module GLOBAL_MACROS to destination, optionally overlay cutover silence."""
    global _CUTOVER_SILENCE
    _CUTOVER_SILENCE = cutover_silence
    GLOBAL_MACROS.clear()
    GLOBAL_MACROS.update(DESTINATION_GLOBAL_MACROS)
    if cutover_silence:
        GLOBAL_MACROS.update(CUTOVER_SILENCE_OVERLAY)
        logger.info('Macro mode: DESTINATION + cutover-silence overlay')
    else:
        logger.info('Macro mode: DESTINATION (production end-state)')


SWITCH_SNMP_ROLES = list(ROLE_MACROS.keys())
# Firewall is not a Switch* SNMP-CG role. Forti HTTP lives on platform FortiOS
# (Observability companion + CG FortiGate HTTP). SNMP Monitoring stays on
# FMG/FAZ platforms, not on FortiGates (role Firewall used to leak that CG
# onto HTTP boxes). ``--apply-fortigate-http`` (not zerotouch, not Extreme
# ``--apply``).


def ct(model):
    return ContentType.objects.get_for_model(model)


def record(name: str, ok: bool, detail: str = '', *, group: str = 'general') -> None:
    RESULTS.append({'name': name, 'ok': bool(ok), 'detail': detail, 'group': group})
    print(f"[{'PASS' if ok else 'FAIL'}] {group}/{name}: {detail}")


def slugify(name: str) -> str:
    return PREFIX + name.lower().replace(' ', '-').replace('/', '-')


def ensure(model, defaults=None, update_fields=None, **lookup):
    """Same contract as zerotouch ``ensure``."""
    if ztc is not None:
        return ztc.ensure(model, defaults=defaults, update_fields=update_fields, **lookup)
    defaults = defaults or {}
    obj, created = model.objects.get_or_create(defaults=defaults, **lookup)
    if created:
        return obj, True
    dirty = []
    for field in update_fields or defaults.keys():
        if field in defaults and getattr(obj, field) != defaults[field]:
            setattr(obj, field, defaults[field])
            dirty.append(field)
    if dirty:
        obj.save(update_fields=dirty)
    return obj, False


def _lab_server_names() -> set[str]:
    names = {SIM_SERVER_NAME}
    if ztc is not None and hasattr(ztc, 'KNOWN_LAB_SERVER_NAMES'):
        names.update(ztc.KNOWN_LAB_SERVER_NAMES)
    else:
        names.update({'ZeroTouch Configure Lab', 'Network Configure Lab'})
    return names


def _rule_kwargs():
    return {'prefix': PREFIX, 'sim_server_name': SIM_SERVER_NAME}


def template_rules_for_server(server):
    if ztc is None:
        raise SystemExit('configure_nbxsync_zerotouch.py is required for TemplateRule server scoping')
    return ztc.template_rules_for_server(server)


def ensure_template_rule(server, name: str, defaults: dict, update_fields=None):
    return ztc.ensure_template_rule(
        server,
        name,
        defaults,
        update_fields=update_fields,
        **_rule_kwargs(),
    )


def get_template_rule(server, name: str):
    return ztc.get_template_rule(server, name, **_rule_kwargs())


def simulation_rule_name(server, name: str) -> str:
    return ztc.simulation_rule_name(server, name, **_rule_kwargs())


def get_role(name: str) -> DeviceRole:
    if ztc is not None and hasattr(ztc, 'get_role'):
        try:
            return ztc.get_role(name)
        except DeviceRole.DoesNotExist:
            pass
    return DeviceRole.objects.get(slug=slugify(name))


def import_rules() -> dict:
    return {
        'templates': {'createMissing': True, 'updateExisting': True},
        'template_groups': {'createMissing': True, 'updateExisting': True},
        'templateLinkage': {'createMissing': True, 'deleteMissing': False},
        'valueMaps': {'createMissing': True, 'updateExisting': True},
        'items': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
        'discoveryRules': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
        'triggers': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
        'graphs': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
        'httptests': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
        'templateDashboards': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
    }


def import_yaml_templates(api, files: dict[str, Path], *, strict: bool = False) -> dict[str, tuple[int, str]]:
    """Import YAML templates; strict callers never reuse stale state after failure."""
    out: dict[str, tuple[int, str]] = {}
    for name, path in files.items():
        if not path.exists():
            logger.error('Missing template file: %s', path)
            continue
        import_error = None
        try:
            api.configuration.import_(
                format='yaml',
                rules=import_rules(),
                source=path.read_text(encoding='utf-8'),
            )
        except Exception as exc:
            import_error = exc
            if strict:
                raise RuntimeError(f'Import failed for required template: {name}') from exc
            logger.warning('  Import failed for %s; checking for an existing exact template: %s', name, exc)
        found = api.template.get(filter={'name': [name]}, output=['templateid', 'host', 'name'])
        if not found:
            found = api.template.get(search={'name': name}, output=['templateid', 'host', 'name'])
            found = [t for t in (found or []) if t.get('name') == name]
        if found:
            out[name] = (int(found[0]['templateid']), name)
            if import_error is not None:
                logger.warning('  Reusing existing %s (id=%s) after import failure', name, found[0]['templateid'])
            else:
                logger.info('  Imported/found %s (id=%s)', name, found[0]['templateid'])
        elif import_error is not None:
            raise RuntimeError(f'Import failed and template is unavailable: {name}') from import_error
        else:
            logger.error('  Template missing after import: %s', name)
    return out


def import_extreme_templates(api) -> dict[str, tuple[int, str]]:
    """Import Extreme YAML templates; return name → (templateid, name)."""
    out = import_yaml_templates(api, TEMPLATE_FILES)
    exos = api.template.get(filter={'name': ['Extreme EXOS by SNMP']}, output=['templateid', 'name'])
    if exos:
        out['Extreme EXOS by SNMP'] = (int(exos[0]['templateid']), 'Extreme EXOS by SNMP')
    return out


def import_fortigate_http_template(api) -> tuple[int, str]:
    """Look up FortiGate by HTTP. Never import YAML over the Cloud template.

    Missing template or unexpected vendor is a hard abort (fail closed).
    """
    logger.info('Network: resolve %s', _FORTIGATE_HTTP_TEMPLATE)
    existing = _template_row(api, _FORTIGATE_HTTP_TEMPLATE)
    if existing is None:
        raise SystemExit(
            f'{_FORTIGATE_HTTP_TEMPLATE} missing in Zabbix. Cloud is vendor '
            f'{_FORTIGATE_HTTP_CLOUD_VENDOR}; do not import {FORTIGATE_HTTP_YAML} '
            '(bundled 7.0-3).'
        )
    tid, name, vendor = existing
    extra = f', vendor {vendor}' if vendor else ', vendor unknown'
    if not _is_cloud_fortigate_http_vendor(vendor):
        raise SystemExit(
            f'{name} vendor is {vendor or "unknown"!r}; expected {_FORTIGATE_HTTP_CLOUD_VENDOR}. '
            'Refusing to patch an unexpected template.'
        )
    logger.info(
        '  %s already in Zabbix (id=%s%s) — not re-importing',
        name,
        tid,
        extra,
    )
    return tid, name


def import_fortigate_observability_template(api) -> tuple[int, str]:
    """Import the estate companion (nests Cloud HTTP + ICMP Ping)."""
    logger.info('Network: import %s', _FORTIGATE_OBSERVABILITY_TEMPLATE)
    out = import_yaml_templates(
        api,
        {_FORTIGATE_OBSERVABILITY_TEMPLATE: FORTIGATE_OBSERVABILITY_YAML},
        strict=True,
    )
    found = out.get(_FORTIGATE_OBSERVABILITY_TEMPLATE)
    if found is None:
        raise SystemExit(f'{_FORTIGATE_OBSERVABILITY_TEMPLATE} missing after import')
    return found


def _template_row(api, name: str) -> tuple[int, str, str] | None:
    """templateid, name, vendor label (may be empty)."""
    output = ['templateid', 'name', 'vendor_name', 'vendor_version']
    try:
        found = api.template.get(filter={'name': [name]}, output=output) or []
    except Exception:
        found = api.template.get(filter={'name': [name]}, output=['templateid', 'name']) or []
    if not found:
        return None
    row = found[0]
    vendor = _format_vendor_label(row.get('vendor_name'), row.get('vendor_version'))
    return int(row['templateid']), row['name'], vendor


def _lookup_zabbix_template(api, name: str) -> tuple[int, str] | None:
    """Exact template name in Zabbix, or None. Soft like VOSS — never invent a fallback."""
    row = _template_row(api, name)
    if row is None:
        return None
    return row[0], row[1]


# Zabbix LLD filter operators (API)
_LLD_MATCHES_REGEX = 8
_LLD_NOT_MATCHES_REGEX = 9
_LLD_EVAL_AND = 1
_IFALIAS_MATCHES = '{$NET.IF.IFALIAS.MATCHES}'
_IFALIAS_NOT_MATCHES = '{$NET.IF.IFALIAS.NOT_MATCHES}'
_ETHERLIKE_KEY = 'net.if.duplex.discovery'


def _etherlike_has_ifalias_filters(conditions: list) -> bool:
    has_m = has_n = False
    for c in conditions or []:
        if c.get('macro') != '{#IFALIAS}':
            continue
        op = int(c.get('operator', _LLD_MATCHES_REGEX))
        val = c.get('value', '')
        if op == _LLD_MATCHES_REGEX and val == _IFALIAS_MATCHES:
            has_m = True
        if op == _LLD_NOT_MATCHES_REGEX and val == _IFALIAS_NOT_MATCHES:
            has_n = True
    return has_m and has_n


def patch_etherlike_ifalias_filters(api, template_names: tuple[str, ...] | None = None) -> dict[str, str]:
    """Ensure EtherLike duplex LLD uses the same IFALIAS macros as net.if.discovery.

    Stock Extreme EXOS only keeps oper-up ports on duplex discovery, so Access
    still monitors unlabelled ports for half-duplex. Idempotent via Zabbix API —
    production ``--apply`` covers EXOS without forking the stock template YAML.
    """
    logger.info('Network: EtherLike duplex IFALIAS filters')
    names = template_names or ('Extreme EXOS by SNMP', 'Extreme VOSS by SNMP')
    results: dict[str, str] = {}
    for name in names:
        tpls = api.template.get(filter={'name': [name]}, output=['templateid', 'name'])
        if not tpls:
            results[name] = 'missing'
            logger.warning('  %s: template not found — skip EtherLike patch', name)
            continue
        tid = tpls[0]['templateid']
        rules = api.discoveryrule.get(
            hostids=tid,
            filter={'key_': _ETHERLIKE_KEY},
            output=['itemid', 'name', 'key_'],
            selectFilter='extend',
        )
        if not rules:
            results[name] = 'no-duplex-lld'
            logger.info('  %s: no %s — skip', name, _ETHERLIKE_KEY)
            continue
        rule = rules[0]
        filt = rule.get('filter') or {}
        conditions = list(filt.get('conditions') or [])
        if _etherlike_has_ifalias_filters(conditions):
            results[name] = 'ok'
            logger.info('  %s: EtherLike IFALIAS filters already present', name)
            continue
        kept = []
        for c in conditions:
            if c.get('macro') == '{#IFALIAS}':
                continue  # replace any prior IFALIAS conditions
            kept.append(
                {
                    'macro': c['macro'],
                    'value': c.get('value', ''),
                    'operator': int(c.get('operator', _LLD_MATCHES_REGEX)),
                }
            )
        kept.append({'macro': '{#IFALIAS}', 'value': _IFALIAS_MATCHES, 'operator': _LLD_MATCHES_REGEX})
        kept.append({'macro': '{#IFALIAS}', 'value': _IFALIAS_NOT_MATCHES, 'operator': _LLD_NOT_MATCHES_REGEX})
        api.discoveryrule.update(
            itemid=rule['itemid'],
            filter={'evaltype': _LLD_EVAL_AND, 'conditions': kept},
        )
        results[name] = 'patched'
        logger.info('  %s: patched EtherLike IFALIAS filters (itemid=%s)', name, rule['itemid'])
    return results


def assert_etherlike_ifalias_filters(api, template_name: str) -> tuple[bool, str]:
    """Return (ok, detail) for simulate asserts."""
    tpls = api.template.get(filter={'name': [template_name]}, output=['templateid'])
    if not tpls:
        return True, 'template absent — n/a'
    rules = api.discoveryrule.get(
        hostids=tpls[0]['templateid'],
        filter={'key_': _ETHERLIKE_KEY},
        output=['itemid'],
        selectFilter='extend',
    )
    if not rules:
        return True, 'no duplex LLD — n/a'
    ok = _etherlike_has_ifalias_filters((rules[0].get('filter') or {}).get('conditions') or [])
    return ok, str((rules[0].get('filter') or {}).get('conditions'))


_IF_DISCOVERY_KEY = 'net.if.discovery'
_IF_LLD_ROLLOUT_DELAY = '15m'
# Per-rule timeout is only valid for SNMP LLD whose snmp_oid starts with walk[ or get[.
# Stock Extreme EXOS uses classic discovery[{#SNMPVALUE},…] — Zabbix then requires
# timeout="" and uses the proxy/global SNMP timeout. Sending 30s yields
# Invalid parameter "/1/timeout": value must be empty.
_IF_LLD_WALK_TIMEOUT = '30s'

# Zabbix 7 discoveryrule API. Immediate *delete* wipes history on a truncated
# GETBULK or a wrong IFALIAS filter. A rule that goes not-supported (SNMP
# timeout) does not process lost resources — a full outage is a graph gap.
# Interface LLD: disable immediately so X-ports leave the honeycomb; delete
# after 7d so rediscovery re-enables with history intact.
# VOSS PSU LLD: delete immediately. Health honeycomb keeps lastvalue on a
# disabled item, so a 7d lifetime leaves padding hexes visible.
_LLD_DELETE_AFTER = 0
_LLD_DELETE_IMMEDIATELY = 2
_LLD_DISABLE_IMMEDIATELY = 2
_LLD_DELETE_LIFETIME = '7d'
_LLD_DISABLE_LIFETIME = '0'
_LLD_DELETE_NOW_LIFETIME = '0'


def _lld_lost_resources_fields() -> dict:
    return {
        'lifetime': _LLD_DELETE_LIFETIME,
        'lifetime_type': _LLD_DELETE_AFTER,
        'enabled_lifetime': _LLD_DISABLE_LIFETIME,
        'enabled_lifetime_type': _LLD_DISABLE_IMMEDIATELY,
    }


def _voss_psu_lost_resources_fields() -> dict:
    return {
        'lifetime': _LLD_DELETE_NOW_LIFETIME,
        'lifetime_type': _LLD_DELETE_IMMEDIATELY,
        'enabled_lifetime': _LLD_DISABLE_LIFETIME,
        'enabled_lifetime_type': _LLD_DISABLE_IMMEDIATELY,
    }


def _lld_disable_now(rule: dict) -> bool:
    enabled = str(rule.get('enabled_lifetime') if rule.get('enabled_lifetime') is not None else '0')
    enabled_type = str(rule.get('enabled_lifetime_type') if rule.get('enabled_lifetime_type') is not None else '')
    return enabled in ('0', '0s', '0d', '0h', '') and enabled_type in (
        '',
        str(_LLD_DISABLE_IMMEDIATELY),
        'DISABLE_IMMEDIATELY',
    )


def _lld_lost_resources_ok(rule: dict) -> bool:
    """Disable lost immediately; delete after 7d — never delete-immediately."""
    lifetime = str(rule.get('lifetime') or '')
    lifetime_type = str(rule.get('lifetime_type') if rule.get('lifetime_type') is not None else '')
    if lifetime_type in (str(_LLD_DELETE_IMMEDIATELY), 'DELETE_IMMEDIATELY'):
        return False
    if lifetime in ('0', '0s', '0d', '0h') and lifetime_type not in ('1', 'DELETE_NEVER'):
        return False
    delete_after = lifetime in (_LLD_DELETE_LIFETIME, '7d0h', '604800') and lifetime_type in (
        '',
        str(_LLD_DELETE_AFTER),
        'DELETE_AFTER',
    )
    return delete_after and _lld_disable_now(rule)


def _voss_psu_lost_resources_ok(rule: dict) -> bool:
    """Delete lost VOSS PSU rows immediately so empty hexes leave Health."""
    lifetime = str(rule.get('lifetime') or '')
    lifetime_type = str(rule.get('lifetime_type') if rule.get('lifetime_type') is not None else '')
    delete_now = lifetime_type in (str(_LLD_DELETE_IMMEDIATELY), 'DELETE_IMMEDIATELY') or (
        lifetime in ('0', '0s', '0d', '0h') and lifetime_type not in ('1', 'DELETE_NEVER')
    )
    return delete_now and _lld_disable_now(rule)


_PSU_DISCOVERY_KEY = 'psu.discovery'
_PSU_DETAIL_DISCOVERY_KEY = 'psu.detail.discovery'
_PSU_NOTPRESENT = '^1$'
_VOSS_TEMPLATE = 'Extreme VOSS by SNMP'
_VOSS_PSU_EMPTY = '^2$'
_VOSS_PSU_RULES = (
    (_PSU_DISCOVERY_KEY, _VOSS_PSU_DISCOVERY_OID, _VOSS_PSU_STATUS_OID, _VOSS_PSU_SERIAL_OID),
    (_PSU_DETAIL_DISCOVERY_KEY, _VOSS_PSU_DETAIL_DISCOVERY_OID, _VOSS_PSU_DETAIL_STATUS_OID, _VOSS_PSU_SERIAL_OID),
)
_PSU_LLD_RULE_OUTPUT = [
    'itemid',
    'key_',
    'snmp_oid',
    'lifetime',
    'lifetime_type',
    'enabled_lifetime',
    'enabled_lifetime_type',
]
_PSU_LLD_GET_KW = {
    'output': _PSU_LLD_RULE_OUTPUT,
    'selectFilter': 'extend',
    'selectPreprocessing': 'extend',
}


def _lld_operator_is_not_matches(op) -> bool:
    try:
        return int(op) == _LLD_NOT_MATCHES_REGEX
    except (TypeError, ValueError):
        return str(op).upper() in ('NOT_MATCHES_REGEX', 'NOT_MATCHES')


def _lld_operator_is_matches(op) -> bool:
    try:
        return int(op) == _LLD_MATCHES_REGEX
    except (TypeError, ValueError):
        return str(op).upper() in ('MATCHES_REGEX', 'MATCHES')


def _patch_psu_lld_rule(
    api,
    rule: dict,
    *,
    snmp_oid: str,
    empty_regex: str,
    lost_fields: dict | None = None,
    keep_serialled_empty: bool = True,
) -> None:
    # AND/OR updates must omit formulaid. GET still returns A/B; echoing those
    # IDs is what Zabbix 7 rejects with "formulaid must be empty".
    api.discoveryrule.update(
        itemid=rule['itemid'],
        snmp_oid=snmp_oid,
        filter=_psu_lld_api_filter(
            empty_regex,
            rule.get('filter'),
            keep_serialled_empty=keep_serialled_empty,
        ),
        preprocessing=_psu_lld_preprocessing_payload(rule.get('preprocessing')),
        **(lost_fields or _lld_lost_resources_fields()),
    )


def patch_exos_psu_lld_present_only(api, template_name: str = 'Extreme EXOS by SNMP') -> str:
    """Discover installed EXOS PSUs, including presentPowerOff and serialled notPresent.

    ``extremePowerSupplyTable`` has a row for every possible stack member slot.
    Padding is ``notPresent`` with no serial OID instance — Zabbix then omits
    ``{#PSU.SERIAL}`` and the filter errors. LLD JS defaults that macro to
    empty so padding skips and a serialled unplugged FRU stays. A fitted PSU
    with no AC is ``presentPowerOff(4)`` or, on some code, ``notPresent`` with
    a serial; both stay so two present / one connected tickets Average.
    Disable lost immediately; delete after 7d. Does not fork the stock YAML.
    """
    logger.info('Network: EXOS psu.discovery installed FRUs (serial or not notPresent)')
    tpls = api.template.get(filter={'name': [template_name]}, output=['templateid', 'name'])
    if not tpls:
        logger.warning('  %s: template not found — skip PSU LLD patch', template_name)
        return 'missing'
    tid = tpls[0]['templateid']
    rules = api.discoveryrule.get(
        hostids=tid,
        filter={'key_': _PSU_DISCOVERY_KEY},
        **_PSU_LLD_GET_KW,
    )
    if not rules:
        logger.warning('  %s: no %s — skip', template_name, _PSU_DISCOVERY_KEY)
        return 'no-psu-lld'
    rule = rules[0]
    if _psu_lld_keeps_installed_fru(
        rule,
        status_oid=_PSU_STATUS_OID,
        serial_oid=_PSU_SERIAL_OID,
        empty_regex=_PSU_NOTPRESENT,
    ) and _lld_lost_resources_ok(rule):
        logger.info('  %s: PSU LLD already keeps installed FRUs', template_name)
        return 'ok'
    _patch_psu_lld_rule(api, rule, snmp_oid=_PSU_DISCOVERY_OID, empty_regex=_PSU_NOTPRESENT)
    logger.info('  %s: patched PSU LLD for installed FRUs (itemid=%s)', template_name, rule['itemid'])
    return 'patched'


def patch_voss_psu_lld_present_only(api, template_name: str = _VOSS_TEMPLATE) -> dict[str, str]:
    """Discover installed VOSS PSUs; skip empty(2) even with dummy serial ``--``.

    ``rcChasPowerSupplyTable`` keeps a row per bay. ``empty(2)`` is not
    installed. Chassis firmware often fills serial with ``--`` on every bay
    (CH-STA-L26-L02-MGMT03), which used to keep the empty bay via OR+serial.
    Fitted-unplugged is ``unknown(1)`` or ``down(4)``. Delete lost immediately.
    """
    logger.info('Network: VOSS psu.discovery skip empty(2) including dummy serial')
    tpls = api.template.get(filter={'name': [template_name]}, output=['templateid', 'name'])
    if not tpls:
        logger.warning('  %s: template not found — skip VOSS PSU LLD patch', template_name)
        return {'status': 'missing'}
    tid = tpls[0]['templateid']
    results: dict[str, str] = {}
    for key, snmp_oid, status_oid, serial_oid in _VOSS_PSU_RULES:
        rules = api.discoveryrule.get(
            hostids=tid,
            filter={'key_': key},
            **_PSU_LLD_GET_KW,
        )
        if not rules:
            results[key] = 'no-psu-lld'
            logger.warning('  %s: no %s — skip', template_name, key)
            continue
        rule = rules[0]
        if _psu_lld_keeps_installed_fru(
            rule,
            status_oid=status_oid,
            serial_oid=serial_oid,
            empty_regex=_VOSS_PSU_EMPTY,
            keep_serialled_empty=False,
        ) and _voss_psu_lost_resources_ok(rule):
            results[key] = 'ok'
            logger.info('  %s: %s already skips empty bays and deletes lost now', template_name, key)
            continue
        _patch_psu_lld_rule(
            api,
            rule,
            snmp_oid=snmp_oid,
            empty_regex=_VOSS_PSU_EMPTY,
            lost_fields=_voss_psu_lost_resources_fields(),
            keep_serialled_empty=False,
        )
        results[key] = 'patched'
        logger.info('  %s: patched %s skip empty / delete-now (itemid=%s)', template_name, key, rule['itemid'])
    return results


_EXOS_STOCK_TEMPLATE = 'Extreme EXOS by SNMP'
_EXOS_OBSERVABILITY_TEMPLATE = 'Extreme EXOS Observability'
_CHECK_NOW_TASK_TYPE = 6


def _queue_psu_lld_checks(
    api,
    *,
    template_names: tuple[str, ...],
    discovery_keys: tuple[str, ...],
    log_label: str,
) -> dict[str, int | str]:
    """Queue check-now PSU LLD for every host on the templates.

    Padding rows leave and EXOS serialled unplugged FRUs appear without
    waiting for the 1h discovery delay. Not HostSync; does not write NetBox.
    """
    template_ids: set[str] = set()
    for name in template_names:
        found = api.template.get(filter={'name': [name]}, output=['templateid']) or []
        template_ids.update(str(t['templateid']) for t in found)
    if not template_ids:
        return {'status': 'missing-template', 'hosts': 0, 'tasks': 0}

    host_ids: set[str] = set()
    for template_id in sorted(template_ids):
        hosts = api.host.get(templateids=[template_id], output=['hostid']) or []
        host_ids.update(str(h['hostid']) for h in hosts)
    if not host_ids:
        return {'status': 'no-hosts', 'hosts': 0, 'tasks': 0}

    rules = []
    ordered_hosts = sorted(host_ids)
    for start in range(0, len(ordered_hosts), 100):
        rules.extend(
            api.discoveryrule.get(
                hostids=ordered_hosts[start:start + 100],
                filter={'key_': list(discovery_keys)},
                output=['itemid', 'hostid'],
            )
            or []
        )
    tasks = [
        {'type': _CHECK_NOW_TASK_TYPE, 'request': {'itemid': rule['itemid']}}
        for rule in rules
    ]
    if not tasks:
        return {'status': 'no-discovery-rules', 'hosts': len(host_ids), 'tasks': 0}

    task_ids: list[str] = []
    for start in range(0, len(tasks), 20):
        result = api.task.create(tasks[start:start + 20]) or {}
        task_ids.extend(str(task_id) for task_id in result.get('taskids', []))
    logger.info(
        '  %s check-now queued: hosts=%s rules=%s tasks=%s',
        log_label,
        len(host_ids),
        len(rules),
        len(task_ids),
    )
    return {'status': 'queued', 'hosts': len(host_ids), 'tasks': len(task_ids)}


def queue_exos_psu_lld_checks(api, template_names: tuple[str, ...] | None = None) -> dict[str, int | str]:
    """Queue immediate PSU LLD checks on stock EXOS and the Observability companion.

    LLD filters do not remove already-discovered rows or invent skipped FRUs
    until discovery runs. Check-now converges an apply without HostSync.
    ``-2`` stack hosts have neither template and are skipped.
    """
    names = template_names or (_EXOS_STOCK_TEMPLATE, _EXOS_OBSERVABILITY_TEMPLATE)
    return _queue_psu_lld_checks(
        api,
        template_names=names,
        discovery_keys=(_PSU_DISCOVERY_KEY,),
        log_label='EXOS PSU LLD',
    )


def queue_voss_psu_lld_checks(api, template_names: tuple[str, ...] | None = None) -> dict[str, int | str]:
    """Queue immediate PSU LLD checks for status and detail tables.

    Same converge-without-HostSync path as EXOS. Does not write NetBox.
    """
    names = template_names or (_VOSS_TEMPLATE,)
    return _queue_psu_lld_checks(
        api,
        template_names=names,
        discovery_keys=(_PSU_DISCOVERY_KEY, _PSU_DETAIL_DISCOVERY_KEY),
        log_label='VOSS PSU LLD',
    )


def assert_exos_psu_lld_present_only(api, template_name: str = 'Extreme EXOS by SNMP') -> tuple[bool, str]:
    tpls = api.template.get(filter={'name': [template_name]}, output=['templateid'])
    if not tpls:
        return True, 'template absent — n/a'
    rules = api.discoveryrule.get(
        hostids=tpls[0]['templateid'],
        filter={'key_': _PSU_DISCOVERY_KEY},
        **_PSU_LLD_GET_KW,
    )
    if not rules:
        return True, 'no PSU LLD — n/a'
    ok = _psu_lld_keeps_installed_fru(
        rules[0],
        status_oid=_PSU_STATUS_OID,
        serial_oid=_PSU_SERIAL_OID,
        empty_regex=_PSU_NOTPRESENT,
    ) and _lld_lost_resources_ok(rules[0])
    return ok, str({'snmp_oid': rules[0].get('snmp_oid'), 'filter': rules[0].get('filter')})


def assert_voss_psu_lld_present_only(api, template_name: str = _VOSS_TEMPLATE) -> tuple[bool, str]:
    tpls = api.template.get(filter={'name': [template_name]}, output=['templateid'])
    if not tpls:
        return True, 'template absent — n/a'
    details = {}
    ok = True
    for key, _snmp_oid, status_oid, serial_oid in _VOSS_PSU_RULES:
        rules = api.discoveryrule.get(
            hostids=tpls[0]['templateid'],
            filter={'key_': key},
            **_PSU_LLD_GET_KW,
        )
        if not rules:
            details[key] = 'missing'
            continue
        rule_ok = _psu_lld_keeps_installed_fru(
            rules[0],
            status_oid=status_oid,
            serial_oid=serial_oid,
            empty_regex=_VOSS_PSU_EMPTY,
            keep_serialled_empty=False,
        ) and _voss_psu_lost_resources_ok(rules[0])
        ok = ok and rule_ok
        details[key] = {
            'ok': rule_ok,
            'snmp_oid': rules[0].get('snmp_oid'),
            'filter': rules[0].get('filter'),
        }
    if details and all(v == 'missing' for v in details.values()):
        return True, 'no PSU LLD — n/a'
    return ok, str(details)


def patch_psu_not_up(api) -> dict[str, str]:
    """Average when a discovered PSU is not supplying power.

    Stock EXOS matches ``presentNotOK(3)`` only, so ``presentPowerOff(4)`` is
    silent. VOSS matches ``down(4)`` only, so ``unknown(1)`` is silent. Some
    firmware reports a fitted unplugged EXOS FRU as notPresent with a real
    serial; LLD keeps those. VOSS ``empty(2)`` is not installed even when
    serial is ``--``. ``last()<>{$PSU.OK_STATUS}`` tickets two present / one
    connected; VOSS also excludes empty so leftover padding recovers.
    Drops a leftover separate power-off prototype so we do not double-ticket.
    Does not host-sync or write NetBox.
    """
    logger.info('Network: PSU Average for installed-not-up')
    results: dict[str, str] = {}
    descriptions = {
        _PSU_OK_MACRO: 'Present and supplying power (EXOS presentOK / VOSS up).',
        _PSU_EMPTY_MACRO: (
            'Bay not installed (EXOS notPresent / VOSS empty). '
            'VOSS LLD skips empty even when firmware fills serial with --. '
            'EXOS LLD skips padding unless a real serial is set.'
        ),
    }
    for template_name in _PSU_NOT_UP_TEMPLATES:
        wanted = {
            _PSU_OK_MACRO: _PSU_OK_BY_TEMPLATE[template_name],
            _PSU_EMPTY_MACRO: _PSU_EMPTY_BY_TEMPLATE[template_name],
        }
        macro_status = _upsert_template_macros(api, template_name, wanted, descriptions)
        tpls = api.template.get(filter={'name': [template_name]}, output=['templateid'])
        if not tpls:
            results[template_name] = 'missing'
            continue
        tid = tpls[0]['templateid']
        rules = api.discoveryrule.get(
            hostids=tid,
            filter={'key_': list(_PSU_NOT_UP_DISCOVERY_KEYS)},
            output=['itemid', 'key_'],
        ) or []
        if not rules:
            results[template_name] = macro_status if macro_status != 'patched' else 'no-psu-lld'
            continue
        changed = macro_status == 'patched'
        for rule in rules:
            protos = api.triggerprototype.get(
                discoveryids=rule['itemid'],
                output=['triggerid', 'description', 'expression', 'comments', 'manual_close'],
            ) or []
            drop_ids = [
                p['triggerid']
                for p in protos
                if _psu_power_off_name_match(_triggerproto_name(p))
            ]
            if drop_ids:
                api.triggerprototype.delete(*drop_ids)
                changed = True
                logger.info('  %s: deleted leftover PSU power-off prototype (%s)', template_name, drop_ids)
            for proto in protos:
                if proto['triggerid'] in drop_ids:
                    continue
                name = _triggerproto_name(proto)
                if not _psu_trigger_name_match(name):
                    continue
                expr = str(proto.get('expression') or '')
                payload: dict = {}
                rewritten = _rewrite_psu_not_up_expr(expr)
                if rewritten != expr:
                    payload['expression'] = rewritten
                if 'not up' not in name.lower():
                    payload['description'] = name.replace(
                        'Power supply is in critical state',
                        'Power supply is not up',
                    ).replace('Detail status critical', 'Detail status not up')
                comments = str(proto.get('comments') or '')
                want_comments = (
                    'Installed PSU is not supplying power. Two present and one '
                    'connected must Average. VOSS empty(2) bays (including dummy '
                    'serial --) are not discovered. EXOS padding (notPresent, no '
                    'real serial) is not discovered.'
                )
                if comments != want_comments:
                    payload['comments'] = want_comments
                if str(proto.get('manual_close') or '0') in ('1', 'YES'):
                    payload['manual_close'] = 0
                if payload:
                    api.triggerprototype.update(triggerid=proto['triggerid'], **payload)
                    changed = True
                    logger.info(
                        '  %s: patched PSU not-up (%s itemid=%s)',
                        template_name,
                        ', '.join(payload),
                        proto['triggerid'],
                    )
        results[template_name] = 'patched' if changed else 'ok'
    return results


def assert_psu_not_up(api, template_name: str) -> tuple[bool, str]:
    tpls = api.template.get(
        filter={'name': [template_name]},
        output=['templateid'],
        selectMacros='extend',
    )
    if not tpls:
        return True, 'template absent — n/a'
    have = {m.get('macro'): str(m.get('value', '')) for m in (tpls[0].get('macros') or [])}
    if have.get(_PSU_OK_MACRO) != _PSU_OK_BY_TEMPLATE[template_name]:
        return False, f'ok_status={have.get(_PSU_OK_MACRO)!r}'
    if have.get(_PSU_EMPTY_MACRO) != _PSU_EMPTY_BY_TEMPLATE[template_name]:
        return False, f'empty_status={have.get(_PSU_EMPTY_MACRO)!r}'
    rules = api.discoveryrule.get(
        hostids=tpls[0]['templateid'],
        filter={'key_': list(_PSU_NOT_UP_DISCOVERY_KEYS)},
        output=['itemid', 'key_'],
    ) or []
    if not rules:
        return True, 'no PSU LLD — n/a'
    details = {}
    ok = True
    for rule in rules:
        protos = api.triggerprototype.get(
            discoveryids=rule['itemid'],
            output=['triggerid', 'description', 'expression'],
        ) or []
        matched = [p for p in protos if _psu_trigger_name_match(_triggerproto_name(p))]
        if not matched:
            details[rule.get('key_')] = 'no-psu-trigger'
            continue
        for proto in matched:
            expr_ok = _psu_expr_is_not_up(str(proto.get('expression') or ''))
            ok = ok and expr_ok
            details[_triggerproto_name(proto)] = {
                'ok': expr_ok,
                'expression': proto.get('expression'),
            }
    return ok, str(details)


def _triggerproto_name(proto: dict) -> str:
    return str(proto.get('description') or proto.get('name') or '')


def _template_macro_payload(existing: list[dict], wanted: dict[str, str], descriptions: dict[str, str] | None = None) -> list[dict]:
    """Merge ``wanted`` into a template.update macros list without dropping others."""
    by_name = {m['macro']: dict(m) for m in existing if isinstance(m, dict) and m.get('macro')}
    for macro, value in wanted.items():
        if macro in by_name:
            by_name[macro]['value'] = value
            if descriptions and macro in descriptions:
                by_name[macro]['description'] = descriptions[macro]
        else:
            entry = {'macro': macro, 'value': value}
            if descriptions and macro in descriptions:
                entry['description'] = descriptions[macro]
            by_name[macro] = entry
    payload = []
    for m in by_name.values():
        entry = {'macro': m['macro'], 'value': m.get('value', '')}
        if m.get('hostmacroid'):
            entry['hostmacroid'] = m['hostmacroid']
        if m.get('description') is not None:
            entry['description'] = m.get('description', '')
        if m.get('type') is not None:
            entry['type'] = m['type']
        payload.append(entry)
    return payload


def _upsert_template_macros(
    api,
    template_name: str,
    wanted: dict[str, str],
    descriptions: dict[str, str] | None = None,
) -> str:
    tpls = api.template.get(
        filter={'name': [template_name]},
        output=['templateid'],
        selectMacros='extend',
    )
    if not tpls:
        return 'missing'
    existing = list(tpls[0].get('macros') or [])
    by_name = {m['macro']: m for m in existing if isinstance(m, dict) and m.get('macro')}
    current = {k: str(by_name[k].get('value', '')) for k in wanted if k in by_name}
    values_ok = all(current.get(k) == v for k, v in wanted.items()) and len(current) == len(wanted)
    descriptions_ok = True
    if descriptions:
        for macro, description in descriptions.items():
            row = by_name.get(macro)
            if row is None or str(row.get('description') or '') != description:
                descriptions_ok = False
                break
    if values_ok and descriptions_ok:
        return 'ok'
    payload = _template_macro_payload(existing, wanted, descriptions)
    api.template.update(templateid=tpls[0]['templateid'], macros=payload)
    return 'patched'


def _drop_template_macros(api, template_name: str, prefixes: tuple[str, ...]) -> str:
    tpls = api.template.get(
        filter={'name': [template_name]},
        output=['templateid'],
        selectMacros='extend',
    )
    if not tpls:
        return 'missing'
    existing = list(tpls[0].get('macros') or [])
    kept = [
        m for m in existing
        if not any(str(m.get('macro') or '').startswith(p) for p in prefixes)
    ]
    if len(kept) == len(existing):
        return 'ok'
    payload = []
    for m in kept:
        entry = {'macro': m['macro'], 'value': m.get('value', '')}
        if m.get('hostmacroid'):
            entry['hostmacroid'] = m['hostmacroid']
        if m.get('description') is not None:
            entry['description'] = m.get('description', '')
        if m.get('type') is not None:
            entry['type'] = m['type']
        payload.append(entry)
    api.template.update(templateid=tpls[0]['templateid'], macros=payload)
    return 'patched'


def patch_linkdown_one_average(api) -> dict[str, str]:
    """One Average for every discovered link-down. Drop leftover USW High.

    YAML ``deleteMissing: false`` would leave the class-scoped sibling in Zabbix.
    Scope is LLD (Access USW+UP; Core/Dist everything except X), not a second
    severity map. ICMP High still pages a dead box.

    Drop stock ``last(#1)<>last(#2)`` so never-up ports ticket. Match oper
    **not up** (``<>1``), not only ``down(2)`` — honeycomb is ``>=2`` and VOSS
    unused SFPs often report ``lowerLayerDown(7)``. Recovery is ``last()=1``
    (stock ``<>2`` would clear 7 immediately). Manual close off.

    Same prototype on EXOS and VOSS. Access also requires
    ``{$LINKDOWN.IFALIAS:"{#IFALIAS}"}=1`` (grammar display-string). Template
    default is 1 so Core/Dist/Mgmt unlabelled admin-up still tickets.
    """
    logger.info('Network: discovered link-down stays Average (not-up, no .diff(), Access ifAlias gate)')
    results: dict[str, str] = {}
    proto_output = [
        'triggerid',
        'description',
        'expression',
        'recovery_expression',
        'recovery_mode',
        'manual_close',
        'comments',
    ]
    for template_name in _LINKDOWN_TEMPLATES:
        tpls = api.template.get(filter={'name': [template_name]}, output=['templateid'])
        if not tpls:
            results[template_name] = 'missing'
            continue
        tid = tpls[0]['templateid']
        changed = _drop_template_macros(api, template_name, (_LINKDOWN_HIGH_MACRO_PREFIX,)) == 'patched'
        macro_status = _upsert_template_macros(
            api,
            template_name,
            {_LINKDOWN_IFALIAS_MACRO: _LINKDOWN_IFALIAS_TEMPLATE_VALUE},
            {
                _LINKDOWN_IFALIAS_MACRO: (
                    'Allow discovered-port link-down Average for this ifAlias. '
                    'Template default 1 (Core/Dist/Mgmt). Access host default 0 + '
                    'regex USW|US|UP|MON|UW|TMON = 1.'
                ),
            },
        )
        if macro_status == 'patched':
            changed = True
        rules = api.discoveryrule.get(
            hostids=tid,
            filter={'key_': _IF_DISCOVERY_KEY},
            output=['itemid'],
        )
        if not rules:
            results[template_name] = 'no-if-lld'
            continue
        protos = api.triggerprototype.get(
            discoveryids=rules[0]['itemid'],
            output=proto_output,
        ) or []
        drop_ids = [
            p['triggerid']
            for p in protos
            if 'Link down' in _triggerproto_name(p) and '(USW)' in _triggerproto_name(p)
        ]
        if drop_ids:
            api.triggerprototype.delete(*drop_ids)
            changed = True
            logger.info('  %s: deleted leftover USW High link-down (%s)', template_name, drop_ids)
        for proto in protos:
            if proto['triggerid'] in drop_ids:
                continue
            if not _is_platform_linkdown_name(_triggerproto_name(proto)):
                continue
            expr = str(proto.get('expression') or '')
            recovery = str(proto.get('recovery_expression') or '')
            payload: dict = {}
            ungated = _canonicalize_linkdown_problem(expr)
            if not _linkdown_expr_equal(ungated, expr):
                payload['expression'] = ungated
            want_rec = _canonicalize_linkdown_recovery(ungated)
            if want_rec and not _linkdown_expr_equal(want_rec, recovery):
                payload['recovery_expression'] = want_rec
                payload['recovery_mode'] = _LINKDOWN_RECOVERY_MODE
            if _linkdown_manual_close_on(proto):
                payload['manual_close'] = 0
            comments = str(proto.get('comments') or '')
            if 'LINKDOWN.IFALIAS' not in comments:
                payload['comments'] = _LINKDOWN_TRIGGER_DESCRIPTION
            if payload:
                api.triggerprototype.update(triggerid=proto['triggerid'], **payload)
                changed = True
                logger.info(
                    '  %s: patched Average link-down (%s)',
                    template_name,
                    ', '.join(payload),
                )
        results[template_name] = 'patched' if changed else 'ok'
    return results


def assert_linkdown_one_average(api, template_name: str) -> tuple[bool, str]:
    tpls = api.template.get(
        filter={'name': [template_name]},
        output=['templateid'],
        selectMacros='extend',
    )
    if not tpls:
        return True, 'template absent — n/a'
    macros = [str(m.get('macro') or '') for m in (tpls[0].get('macros') or [])]
    macro_vals = {
        str(m.get('macro') or ''): str(m.get('value') or '')
        for m in (tpls[0].get('macros') or [])
        if isinstance(m, dict)
    }
    if any(m.startswith(_LINKDOWN_HIGH_MACRO_PREFIX) for m in macros):
        return False, f'leftover macros={[m for m in macros if m.startswith(_LINKDOWN_HIGH_MACRO_PREFIX)]}'
    rules = api.discoveryrule.get(
        hostids=tpls[0]['templateid'],
        filter={'key_': _IF_DISCOVERY_KEY},
        output=['itemid'],
    )
    if not rules:
        return True, 'no IF LLD — n/a'
    protos = api.triggerprototype.get(
        discoveryids=rules[0]['itemid'],
        output=['triggerid', 'description', 'expression', 'recovery_expression', 'manual_close'],
    ) or []
    linkdown = [p for p in protos if _is_platform_linkdown_name(_triggerproto_name(p))]
    names = [_triggerproto_name(p) for p in linkdown]
    exprs = [str(p.get('expression') or '') for p in linkdown]
    recs = [str(p.get('recovery_expression') or '') for p in linkdown]
    leftover = [p for p in protos if 'Link down' in _triggerproto_name(p) and '(USW)' in _triggerproto_name(p)]
    ok = (
        not leftover
        and bool(linkdown)
        and not any(_LINKDOWN_HIGH_GATE in e for e in exprs)
        and all(_linkdown_is_not_up(e) for e in exprs)
        and all(_linkdown_has_ifalias_gate(e) for e in exprs)
        and all(_linkdown_recovery_is_up(r) for r in recs)
        and not any(_linkdown_has_diff_guard(e) for e in exprs)
        and not any(_linkdown_manual_close_on(p) for p in linkdown)
        and macro_vals.get(_LINKDOWN_IFALIAS_MACRO) == _LINKDOWN_IFALIAS_TEMPLATE_VALUE
    )
    return ok, f'linkdown={names} ifalias={macro_vals.get(_LINKDOWN_IFALIAS_MACRO)!r}'


_IFNAME_NOT_MATCHES_DESCRIPTION = (
    'Skip loopbacks/docker, VOSS Mgmt-clip/oob, and unused chassis OOB '
    '(VOSS ifName mgmt, EXOS ifName Management). Not {$IFCONTROL}.'
)


def patch_ifname_skip_chassis_oob(api) -> dict[str, str]:
    """Do not discover unused chassis OOB (VOSS mgmt, EXOS Management).

    Core/Dist IFALIAS is ``.*`` except X, so empty ``mgmt()`` and vendor
    ``Management(MgmtPort)`` ticket Average. Skip by ifName on the template
    so every role inherits it. Does not host-sync or write NetBox.
    """
    logger.info('Network: skip chassis OOB ifName mgmt / Management')
    results: dict[str, str] = {}
    for template_name in _LINKDOWN_TEMPLATES:
        results[template_name] = _upsert_template_macros(
            api,
            template_name,
            {_IFNAME_NOT_MATCHES_MACRO: _IFNAME_NOT_MATCHES},
            {_IFNAME_NOT_MATCHES_MACRO: _IFNAME_NOT_MATCHES_DESCRIPTION},
        )
        logger.info('  %s: IFNAME.NOT_MATCHES %s', template_name, results[template_name])
    return results


def assert_ifname_skip_chassis_oob(api, template_name: str) -> tuple[bool, str]:
    tpls = api.template.get(
        filter={'name': [template_name]},
        output=['templateid'],
        selectMacros='extend',
    )
    if not tpls:
        return True, 'template absent — n/a'
    have = {m.get('macro'): str(m.get('value', '')) for m in (tpls[0].get('macros') or [])}
    value = have.get(_IFNAME_NOT_MATCHES_MACRO, '')
    ok = _ifname_not_matches_excludes_oob(value)
    return ok, value


def _discovery_item_timeout_supported(rule: dict) -> bool:
    """Zabbix allows discoveryrule.timeout for SNMP only on walk[/get[ OIDs."""
    oid = str(rule.get('snmp_oid') or '')
    return oid.startswith('walk[') or oid.startswith('get[')


def patch_exos_interface_lld_rollout(api, template_name: str = 'Extreme EXOS by SNMP') -> str:
    """Align stock EXOS net.if.discovery with VOSS rollout settings.

    Stock Extreme EXOS ships delay=1h, a long lost-resources period, and the
    default SNMP timeout. Dist/Access EXOS boxes with many VLAN ifaces then
    show EtherLike duplex (small table) and **zero** ``net.if.*`` traffic
    items (full IF-MIB walk). Idempotent API patch; does not fork the stock YAML.
    Lost resources: disable immediately, delete after 7d — not delete-now.
    Do not set discoveryrule.timeout on classic SNMP OID LLD.
    """
    logger.info('Network: EXOS net.if.discovery rollout (delay/lifetime)')
    tpls = api.template.get(filter={'name': [template_name]}, output=['templateid', 'name'])
    if not tpls:
        logger.warning('  %s: template not found — skip IF LLD rollout patch', template_name)
        return 'missing'
    tid = tpls[0]['templateid']
    rules = api.discoveryrule.get(
        hostids=tid,
        filter={'key_': _IF_DISCOVERY_KEY},
        output=[
            'itemid',
            'key_',
            'delay',
            'lifetime',
            'lifetime_type',
            'enabled_lifetime',
            'enabled_lifetime_type',
            'timeout',
            'snmp_oid',
        ],
    )
    if not rules:
        logger.warning('  %s: no %s — skip', template_name, _IF_DISCOVERY_KEY)
        return 'no-if-lld'
    rule = rules[0]
    delay = str(rule.get('delay') or '')
    lifetime = str(rule.get('lifetime') or '')
    timeout = str(rule.get('timeout') or '')
    timeout_ok = _discovery_item_timeout_supported(rule)
    already = delay == _IF_LLD_ROLLOUT_DELAY and _lld_lost_resources_ok(rule)
    if already and (not timeout_ok or timeout == _IF_LLD_WALK_TIMEOUT):
        logger.info(
            '  %s: IF LLD rollout already set (delay=%s lifetime=%s timeout=%s)',
            template_name,
            delay,
            lifetime,
            timeout or '(proxy/global)',
        )
        return 'ok'
    payload = {
        'itemid': rule['itemid'],
        'delay': _IF_LLD_ROLLOUT_DELAY,
        **_lld_lost_resources_fields(),
    }
    if timeout_ok:
        payload['timeout'] = _IF_LLD_WALK_TIMEOUT
    api.discoveryrule.update(**payload)
    logger.info(
        '  %s: patched IF LLD delay=%s lifetime=%s timeout=%s (was delay=%s lifetime=%s timeout=%s)',
        template_name,
        _IF_LLD_ROLLOUT_DELAY,
        _LLD_DELETE_LIFETIME,
        payload.get('timeout', timeout or '(proxy/global)'),
        delay,
        lifetime,
        timeout or '(empty)',
    )
    return 'patched'


def assert_exos_interface_lld_rollout(api, template_name: str = 'Extreme EXOS by SNMP') -> tuple[bool, str]:
    tpls = api.template.get(filter={'name': [template_name]}, output=['templateid'])
    if not tpls:
        return True, 'template absent — n/a'
    rules = api.discoveryrule.get(
        hostids=tpls[0]['templateid'],
        filter={'key_': _IF_DISCOVERY_KEY},
        output=['delay', 'lifetime', 'lifetime_type', 'enabled_lifetime', 'enabled_lifetime_type', 'timeout', 'snmp_oid'],
    )
    if not rules:
        return True, 'no IF LLD — n/a'
    r = rules[0]
    timeout = str(r.get('timeout') or '')
    timeout_note = timeout or '(proxy/global)'
    detail = (
        f"delay={r.get('delay')} lifetime={r.get('lifetime')} lifetime_type={r.get('lifetime_type')} "
        f"enabled_lifetime={r.get('enabled_lifetime')} enabled_lifetime_type={r.get('enabled_lifetime_type')} "
        f"timeout={timeout_note}"
    )
    ok = str(r.get('delay')) == _IF_LLD_ROLLOUT_DELAY and _lld_lost_resources_ok(r)
    if ok and _discovery_item_timeout_supported(r):
        ok = timeout == _IF_LLD_WALK_TIMEOUT
    return ok, detail


# Stock Extreme EXOS ships {$TEMP_WARN}=55 / {$TEMP_CRIT}=65. Template macros beat globals,
# so setting globals alone never stops the G2+ "Normal @ 70°C" false critical.
_TEMP_TEMPLATE_MACRO_KEYS = ('{$TEMP_WARN}', '{$TEMP_CRIT}', '{$TEMP_CRIT_LOW}')
_TEMP_TEMPLATE_NAMES = ('Extreme EXOS by SNMP', 'Extreme VOSS by SNMP')
# Speed Expect template owns defaults. A leftover Zabbix *global* forces a
# config-cache bump on every host. Access override stays a role host macro.
_PORTID_TEMPLATE_MACRO_KEYS = (
    '{$PORTID.LLD.IFALIAS.MATCHES}',
    '{$PORTID.LLD.IFTYPE.MATCHES}',
)


def _template_macro_map(macros: list) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in macros or []:
        if isinstance(m, dict) and m.get('macro'):
            out[m['macro']] = m.get('value', '')
    return out


def _wanted_temp_template_macros() -> dict[str, str]:
    """Chassis TEMP_* for EXOS/VOSS templates only — never Zabbix globals."""
    wanted = dict(EXTREME_TEMPLATE_TEMP_MACROS)
    if _CUTOVER_SILENCE:
        wanted.update(CUTOVER_TEMPLATE_TEMP_MACROS)
    return wanted


def patch_extreme_template_temp_macros(api, template_names: tuple[str, ...] | None = None) -> dict[str, str]:
    """Align chassis TEMP_* macros on Extreme switch templates with GLOBAL_MACROS.

    Idempotent. ``template.update`` macros **replace** the full set — fetch, merge
    TEMP_*, rewrite all macros so other stock macros are preserved.
    Does not touch IQ Engine (AP-specific 70/85 thresholds).
    """
    logger.info('Network: Extreme template TEMP_* macros')
    names = template_names or _TEMP_TEMPLATE_NAMES
    wanted = _wanted_temp_template_macros()
    if not wanted:
        return {n: 'no-wanted' for n in names}
    results: dict[str, str] = {}
    for name in names:
        tpls = api.template.get(
            filter={'name': [name]},
            output=['templateid', 'name'],
            selectMacros='extend',
        )
        if not tpls:
            results[name] = 'missing'
            logger.warning('  %s: template not found — skip TEMP_* patch', name)
            continue
        tid = tpls[0]['templateid']
        existing = list(tpls[0].get('macros') or [])
        by_name = {m['macro']: dict(m) for m in existing if isinstance(m, dict) and m.get('macro')}
        current = {k: by_name[k].get('value', '') for k in wanted if k in by_name}
        if all(current.get(k) == v for k, v in wanted.items()) and len(current) == len(wanted):
            results[name] = 'ok'
            logger.info('  %s: TEMP_* already aligned (%s)', name, wanted)
            continue
        for macro, value in wanted.items():
            if macro in by_name:
                by_name[macro]['value'] = value
            else:
                by_name[macro] = {'macro': macro, 'value': value}
        # Preserve hostmacroid / description when present; strip empty optional fields.
        payload = []
        for m in by_name.values():
            entry = {'macro': m['macro'], 'value': m.get('value', '')}
            if m.get('hostmacroid'):
                entry['hostmacroid'] = m['hostmacroid']
            if m.get('description') is not None:
                entry['description'] = m.get('description', '')
            if m.get('type') is not None:
                entry['type'] = m['type']
            payload.append(entry)
        api.template.update(templateid=tid, macros=payload)
        results[name] = 'patched'
        logger.info('  %s: patched TEMP_* → %s', name, wanted)
    return results


def assert_extreme_template_temp_macros(api, template_name: str) -> tuple[bool, str]:
    """Return (ok, detail) — template TEMP_* match GLOBAL_MACROS (or template absent)."""
    wanted = _wanted_temp_template_macros()
    tpls = api.template.get(
        filter={'name': [template_name]},
        output=['templateid'],
        selectMacros='extend',
    )
    if not tpls:
        return True, 'template absent — n/a'
    have = _template_macro_map(tpls[0].get('macros') or [])
    detail = {k: have.get(k) for k in wanted}
    ok = all(have.get(k) == v for k, v in wanted.items())
    return ok, str(detail)


def patch_extreme_template_util_macros(api, template_names: tuple[str, ...] | None = None) -> dict[str, str]:
    """Set {$IF.UTIL.MAX}=101 on switch templates so stock EXOS 90 cannot beat global 101."""
    logger.info('Network: Extreme template {$IF.UTIL.MAX}=101')
    names = template_names or _IF_UTIL_TEMPLATE_NAMES
    wanted = {_IF_UTIL_MAX_MACRO: _IF_UTIL_MAX_OFF}
    descriptions = {_IF_UTIL_MAX_MACRO: _IF_UTIL_DESCRIPTION}
    results: dict[str, str] = {}
    for name in names:
        results[name] = _upsert_template_macros(api, name, wanted, descriptions)
        logger.info('  %s: {$IF.UTIL.MAX} %s', name, results[name])
    return results


def assert_extreme_template_util_macros(api, template_name: str) -> tuple[bool, str]:
    tpls = api.template.get(
        filter={'name': [template_name]},
        output=['templateid'],
        selectMacros='extend',
    )
    if not tpls:
        return True, 'template absent — n/a'
    have = _template_macro_map(tpls[0].get('macros') or [])
    value = have.get(_IF_UTIL_MAX_MACRO)
    return _if_util_is_off(value), f'template={value!r}'


def zabbix_effective_macro(api, hostid: str, macro: str) -> tuple[str | None, str]:
    """Resolve host > inherited/template > global. Live Zabbix, not NetBox."""
    kwargs = {
        'hostids': [hostid],
        'output': ['hostid'],
        'selectMacros': ['macro', 'value'],
        'selectParentTemplates': ['templateid', 'name'],
    }
    host_row = None
    inherited: dict[str, str] = {}
    try:
        rows = api.host.get(selectInheritedMacros=['macro', 'value'], **kwargs) or []
        if rows:
            host_row = rows[0]
            inherited = _template_macro_map(host_row.get('inheritedMacros') or [])
    except Exception as exc:
        logger.info('  inherited macros unavailable (%s) — walk templates', exc)
        rows = api.host.get(**kwargs) or []
        host_row = rows[0] if rows else None
    if not host_row:
        return None, 'missing-host'
    host_macros = _template_macro_map(host_row.get('macros') or [])
    template_macros: dict[str, str] = {}
    for tpl in host_row.get('parentTemplates') or []:
        tid = tpl.get('templateid')
        if not tid:
            continue
        full = api.template.get(
            templateids=[tid],
            output=['templateid'],
            selectMacros='extend',
            selectParentTemplates=['templateid'],
        ) or []
        if full:
            template_macros.update(_template_macro_map(full[0].get('macros') or []))
            for parent in full[0].get('parentTemplates') or []:
                nested = api.template.get(
                    templateids=[parent['templateid']],
                    output=['templateid'],
                    selectMacros='extend',
                ) or []
                if nested:
                    # Nested (stock EXOS) fills gaps; direct companion wins if already set.
                    for key, val in _template_macro_map(nested[0].get('macros') or []).items():
                        template_macros.setdefault(key, val)
    gmacros = {
        m['macro']: m.get('value', '')
        for m in (api.usermacro.get(globalmacro=True, output='extend') or [])
        if isinstance(m, dict) and m.get('macro')
    }
    return _effective_macro_from_layers(
        host=host_macros,
        inherited=inherited,
        template=template_macros,
        global_macros=gmacros,
        name=macro,
    )


def assert_effective_if_util(api, hostid: str) -> tuple[bool, str]:
    value, source = zabbix_effective_macro(api, hostid, _IF_UTIL_MAX_MACRO)
    return _if_util_is_off(value), f'{source}={value!r}'


def patch_voss_fabric_pair_host_macros(api) -> dict[str, int | str]:
    """Write {$VIST.CONTROL}=1 / ISIS on Zabbix hosts for VOSS BASE-1/BASE-2 pairs.

    Not HostSync. Not Access. Card stays 0. Triggers require a prior up sample
    so never-configured V-IST/ISIS stays silent.
    """
    logger.info(
        'Network: VOSS fabric-pair host macros (V-IST / ISIS, not card%s)',
        '; cutover-silence=0' if _CUTOVER_SILENCE else '',
    )
    devices = list(
        Device.objects.filter(status='active').select_related('platform', 'role').order_by('name')
    )
    rows = [
        (
            d.name,
            getattr(d.platform, 'name', None) or '',
            getattr(d.role, 'name', None) or '',
        )
        for d in devices
    ]
    names = _fabric_pair_hostnames(rows)
    if not names:
        logger.info('  No VOSS CORE/DIST/MGMT BASE-1/BASE-2 pairs — skip')
        return {'status': 'no-pairs', 'patched': 0, 'missing': 0, 'in_sync': 0}
    wanted = _fabric_pair_macros(silence=_CUTOVER_SILENCE)
    by_host = _zabbix_hosts_by_name(api, names)
    patched: list[str] = []
    missing: list[str] = []
    in_sync = 0
    for name in names:
        row = by_host.get(name)
        if row is None:
            missing.append(name)
            continue
        changed = _upsert_host_macros(api, str(row['hostid']), wanted)
        if changed:
            patched.append(name)
            logger.info('  %s: wrote %s', name, ', '.join(changed))
        else:
            in_sync += 1
    logger.info(
        '  Fabric pairs: patched=%s in_sync=%s missing_in_zabbix=%s sample=%s',
        len(patched),
        in_sync,
        len(missing),
        patched[:8],
    )
    if missing:
        logger.warning('  Fabric-pair devices not in Zabbix (sample): %s', missing[:12])
    return {
        'status': 'ok',
        'patched': len(patched),
        'in_sync': in_sync,
        'missing': len(missing),
        'hosts': len(names),
        'sample': patched[:12],
    }


def _patch_template_ascii_titles(api, templateid) -> int:
    """Rewrite Unicode operators on template triggers and trigger prototypes."""
    changed = 0
    for row in api.trigger.get(
        hostids=templateid,
        inherited=False,
        output=['triggerid', 'description', 'event_name'],
    ) or []:
        payload = _title_payload(row)
        if not payload:
            continue
        api.trigger.update(triggerid=row['triggerid'], **payload)
        changed += 1
    rules = api.discoveryrule.get(hostids=templateid, output=['itemid']) or []
    for rule in rules:
        for proto in api.triggerprototype.get(
            discoveryids=rule['itemid'],
            output=['triggerid', 'description', 'event_name'],
        ) or []:
            payload = _title_payload(proto)
            if not payload:
                continue
            api.triggerprototype.update(triggerid=proto['triggerid'], **payload)
            changed += 1
            logger.info(
                '  trigger prototype %s ASCII title (%s)',
                proto['triggerid'],
                ', '.join(payload),
            )
    return changed


def _patch_discovered_port_identity_titles(api) -> tuple[int, int]:
    """Try host-level Port identity titles; discovered rows often need LLD instead."""
    tpls = api.template.get(filter={'name': [_SPEED_EXPECT_TEMPLATE]}, output=['templateid'])
    if not tpls:
        return 0, 0
    hosts = api.host.get(templateids=[tpls[0]['templateid']], output=['hostid']) or []
    hostids = [h['hostid'] for h in hosts]
    patched = 0
    lld_pending = 0
    for start in range(0, len(hostids), 100):
        rows = api.trigger.get(
            hostids=hostids[start:start + 100],
            search={'description': 'Port identity'},
            output=['triggerid', 'description', 'event_name'],
        ) or []
        for row in rows:
            payload = _title_payload(row)
            if not payload:
                continue
            try:
                api.trigger.update(triggerid=row['triggerid'], **payload)
                patched += 1
            except Exception as exc:
                lld_pending += 1
                logger.info(
                    '  discovered trigger %s event_name left for LLD (%s)',
                    row['triggerid'],
                    exc,
                )
    return patched, lld_pending


def queue_speed_expect_lld_checks(api) -> dict[str, int | str]:
    """Check-now Port speed-expect LLD so discovered triggers copy ASCII event_name."""
    return _queue_psu_lld_checks(
        api,
        template_names=(
            _SPEED_EXPECT_TEMPLATE,
            'Extreme VOSS by SNMP',
            _EXOS_OBSERVABILITY_TEMPLATE,
        ),
        discovery_keys=(_SPEED_EXPECT_DISCOVERY_KEY,),
        log_label='Speed Expect LLD',
    )


def patch_ascii_trigger_titles(api) -> dict[str, str]:
    """Force ASCII ``!=`` on Extreme trigger titles. YAML import can skip event_name.

    Does not close open Problems — those names freeze at create. Does not
    HostSync or write NetBox.
    """
    logger.info('Network: ASCII trigger event names (no Unicode operators)')
    results: dict[str, str] = {}
    need_lld = False
    for name in _ASCII_TITLE_TEMPLATES:
        tpls = api.template.get(filter={'name': [name]}, output=['templateid'])
        if not tpls:
            results[name] = 'missing'
            continue
        changed = _patch_template_ascii_titles(api, tpls[0]['templateid'])
        results[name] = f'patched:{changed}' if changed else 'ok'
        if changed:
            need_lld = True
    discovered, pending = _patch_discovered_port_identity_titles(api)
    if discovered:
        results['discovered Port identity'] = f'patched:{discovered}'
        need_lld = True
    elif pending:
        results['discovered Port identity'] = f'lld-pending:{pending}'
        need_lld = True
    else:
        results['discovered Port identity'] = 'ok'
    if need_lld:
        queued = queue_speed_expect_lld_checks(api)
        results['speedexpect_lld_check_now'] = str(queued.get('status') or '')
    return results


def assert_ascii_trigger_titles(api, template_name: str) -> tuple[bool, str]:
    tpls = api.template.get(filter={'name': [template_name]}, output=['templateid'])
    if not tpls:
        return True, 'template absent — n/a'
    tid = tpls[0]['templateid']
    bad: list[str] = []
    for row in api.trigger.get(
        hostids=tid,
        inherited=False,
        output=['triggerid', 'description', 'event_name'],
    ) or []:
        if _title_payload(row):
            bad.append(str(row.get('event_name') or row.get('description') or ''))
    rules = api.discoveryrule.get(hostids=tid, output=['itemid']) or []
    for rule in rules:
        for proto in api.triggerprototype.get(
            discoveryids=rule['itemid'],
            output=['triggerid', 'description', 'event_name'],
        ) or []:
            if _title_payload(proto):
                bad.append(str(proto.get('event_name') or proto.get('description') or ''))
    return not bad, ('; '.join(bad[:5]) or 'ok')


def step_health_patches(api) -> dict:
    """ICMP noise off + EXOS Health dashboard. Fail closed — a silent skip hid broken Health."""
    logger.info('Network: Health / ICMP-noise patches')
    return apply_extreme_health_patches(api)


def ensure_nbx_template(server, templateid: int, name: str, *, req=None) -> M.ZabbixTemplate:
    if req is None:
        req = [HostInterfaceRequirementChoices.SNMP]
    obj, _ = ensure(
        M.ZabbixTemplate,
        name=name,
        zabbixserver=server,
        defaults={
            'templateid': templateid,
            'interface_requirements': req,
        },
        update_fields=['templateid', 'interface_requirements'],
    )
    return obj


def step_global_macros_zabbix(api) -> None:
    existing = {m['macro']: m for m in api.usermacro.get(globalmacro=True, output='extend') or []}
    wanted = dict(GLOBAL_MACROS)
    wanted.setdefault('{$SNMP_COMMUNITY}', 'public')
    for macro, value in wanted.items():
        if macro in existing:
            if existing[macro]['value'] != value:
                api.usermacro.updateglobal(globalmacroid=existing[macro]['globalmacroid'], value=value)
                logger.info('  Updated global %s=%s', macro, value)
        else:
            api.usermacro.createglobal(macro=macro, value=value)
            logger.info('  Created global %s=%s', macro, value)
    # Older --cutover-silence wrote chassis TEMP_* as globals and muted APs/servers.
    # PORTID.* on the global layer forced a config update for every host; defaults
    # live on Extreme Port Speed Expect by SNMP.
    for macro in (*_TEMP_TEMPLATE_MACRO_KEYS, *_PORTID_TEMPLATE_MACRO_KEYS):
        if macro in existing and macro not in wanted:
            api.usermacro.deleteglobal([existing[macro]['globalmacroid']])
            logger.info('  Deleted leaked global %s (template/role-scoped, not global)', macro)


def step_server_macros(server) -> None:
    """Define macros on the ZabbixServer so MacroAssignments can reference them."""
    for macro_name, value in GLOBAL_MACROS.items():
        ensure(
            M.ZabbixMacro,
            macro=macro_name,
            assigned_object_type=ct(M.ZabbixServer),
            assigned_object_id=server.id,
            defaults={
                'value': value,
                'type': ZabbixMacroTypeChoices.TEXT,
                'description': f'nwn:global:{macro_name}',
            },
            update_fields=['value', 'type', 'description'],
        )


def resolve_roles_for_macros(canonical_name: str) -> list:
    """All NetBox DeviceRoles that should receive ROLE_MACROS[canonical_name]."""
    found: list = []
    seen: set = set()
    candidates = [canonical_name, *ROLE_NAME_ALIASES.get(canonical_name, ())]
    for name in dict.fromkeys(candidates):
        role = None
        try:
            role = get_role(name)
        except DeviceRole.DoesNotExist:
            role = (
                DeviceRole.objects.filter(name=name).first()
                or DeviceRole.objects.filter(name__iexact=name).first()
                or DeviceRole.objects.filter(slug=slugify(name)).first()
            )
        if role is None or role.pk in seen:
            continue
        seen.add(role.pk)
        found.append(role)
    if not found and canonical_name == 'Switch Dist':
        for role in DeviceRole.objects.filter(name__icontains='Dist').exclude(name__icontains='Access'):
            if role.pk not in seen:
                seen.add(role.pk)
                found.append(role)
        for role in DeviceRole.objects.filter(name__icontains='Distribution'):
            if role.pk not in seen:
                seen.add(role.pk)
                found.append(role)
    return found


def resolve_role_for_macros(canonical_name: str) -> DeviceRole | None:
    """Resolve NetBox DeviceRole for a ROLE_MACROS key, including Dist aliases."""
    roles = resolve_roles_for_macros(canonical_name)
    return roles[0] if roles else None


def _upsert_role_macro_assignment(server, role, macro_name: str, value: str, *, context: str = '', is_regex: bool = False) -> None:
    zmacro, _ = ensure(
        M.ZabbixMacro,
        macro=macro_name,
        assigned_object_type=ct(M.ZabbixServer),
        assigned_object_id=server.id,
        defaults={
            'value': value,
            'type': ZabbixMacroTypeChoices.TEXT,
            'description': f'nwn:{macro_name}',
        },
        update_fields=['type', 'description'],
    )
    ma = M.ZabbixMacroAssignment.objects.filter(
        zabbixmacro=zmacro,
        assigned_object_type=ct(DeviceRole),
        assigned_object_id=role.id,
        context=context,
        is_regex=is_regex,
    ).first()
    if ma is None:
        M.ZabbixMacroAssignment.objects.create(
            zabbixmacro=zmacro,
            assigned_object_type=ct(DeviceRole),
            assigned_object_id=role.id,
            value=value,
            context=context,
            is_regex=is_regex,
        )
    elif ma.value != value:
        ma.value = value
        ma.save(update_fields=['value'])
    extra = f':regex:"{context}"' if is_regex else (f':{context}' if context else '')
    logger.info('  %s %s%s = %s', role.name, macro_name, extra, value)


def step_role_macros(server) -> None:
    """ZabbixMacroAssignment on Switch* and Firewall roles — inheritance / HostSync."""
    logger.info('=' * 60)
    logger.info('Network: role IFALIAS / IFTYPE / FortiGate HTTP macros')
    logger.info('=' * 60)
    if server is None:
        raise SystemExit('No ZabbixServer — run with --simulate or create a server first')

    for role_name, macros in ROLE_MACROS.items():
        roles = resolve_roles_for_macros(role_name)
        if not roles:
            logger.warning('  Role not found: %s — skipping', role_name)
            continue
        for role in roles:
            if role.name != role_name:
                logger.info('  Resolved %s → NetBox role %r', role_name, role.name)
            for macro_name, value in macros.items():
                _upsert_role_macro_assignment(server, role, macro_name, value)
            for spec in ROLE_REGEX_MACRO_ASSIGNMENTS.get(role_name, ()):
                _upsert_role_macro_assignment(
                    server,
                    role,
                    spec['macro'],
                    spec['value'],
                    context=spec['context'],
                    is_regex=True,
                )
    _step_firewall_role_macros(server)


def _step_firewall_role_macros(server, *, required: bool = False) -> int:
    """FortiOS platform macros (not generic role Firewall)."""
    return _step_fortios_platform_macros(server, required=required)


def _fortios_platforms() -> list:
    return list(Platform.objects.filter(name__iregex=_FORTIOS_PLATFORM_PATTERN))


def _fmg_faz_platforms() -> list:
    return list(Platform.objects.filter(name__iregex=_FMG_FAZ_PLATFORM_PATTERN))


def _fortios_devices():
    return (
        Device.objects.filter(platform__name__iregex=_FORTIOS_PLATFORM_PATTERN)
        .select_related('platform', 'role', 'site', 'oob_ip', 'primary_ip4')
        .order_by('name')
    )


def _step_fortios_platform_macros(server, *, required: bool = False) -> int:
    """HTTPS / WAN LLD / quiet CPU-mem High + FQDN Jinja; preserve monitoring token."""
    platforms = _fortios_platforms()
    if not platforms:
        msg = 'No FortiOS platform in NetBox — FortiGate HTTP macros not applied'
        if required:
            raise SystemExit(msg)
        logger.warning('  %s', msg)
        return 0
    skip = {_FGATE_TOKEN_MACRO}
    for plat in platforms:
        for macro_name, value in _FORTIOS_PLATFORM_MACROS.items():
            if macro_name in skip:
                continue
            _upsert_object_macro_assignment(
                server,
                plat,
                macro_name,
                value,
                mtype=ZabbixMacroTypeChoices.TEXT,
                description=f'nwn:fortios:{macro_name}',
            )
        _upsert_object_macro_assignment(
            server,
            plat,
            '{$SERVICE.LICENSE.CONTROL}',
            '0',
            mtype=ZabbixMacroTypeChoices.TEXT,
            description='nwn:fortios:unused-forticloud-license',
            context='forticloud',
        )
        logger.info(
            '  Platform %s FortiGate HTTP macros (%s Jinja; no HostSync)',
            plat.name,
            _FGATE_FQDN_MACRO,
        )
    pruned = _prune_fortios_device_fqdn()
    if pruned:
        logger.info('  PRUNED: %s FortiOS device-level %s (platform Jinja wins)', pruned, _FGATE_FQDN_MACRO)
    _step_fortios_platform_token(server, platforms)
    return len(platforms)


def _step_fortios_platform_token(server, platforms) -> None:
    """Preserve the Zabbix monitoring secret stored in NetBox."""
    for plat in platforms:
        current = _assignment_value(server, plat, _FGATE_TOKEN_MACRO)
        if current:
            logger.info(
                '  Platform %s existing %s preserved (NetBox is authoritative)',
                plat.name,
                _FGATE_TOKEN_MACRO,
            )
            continue
        logger.warning(
            '  Platform %s has no %s; set the Zabbix monitoring token in nbxSync',
            plat.name,
            _FGATE_TOKEN_MACRO,
        )


def _os_network_hostgroup(server):
    name = f'{PREFIX}OS/Network' if server.name == SIM_SERVER_NAME else 'OS/Network'
    hg, _ = ensure(
        M.ZabbixHostgroup,
        zabbixserver=server,
        name=name,
        defaults={'value': 'OS/Network'},
        update_fields=['value'],
    )
    return hg


def _firewall_roles(*, required: bool = False) -> list:
    roles = resolve_roles_for_macros(_FIREWALL_ROLE)
    if not roles:
        msg = f'Role not found: {_FIREWALL_ROLE}'
        if required:
            raise SystemExit(msg)
        logger.warning('  %s', msg)
    return roles


def _prune_role_template_names(role, names: set[str]) -> int:
    deleted, _ = M.ZabbixTemplateAssignment.objects.filter(
        zabbixtemplate__name__in=names,
        assigned_object_type=ct(DeviceRole),
        assigned_object_id=role.id,
    ).delete()
    return deleted


def _prune_role_cg_names(role, names: set[str]) -> int:
    deleted, _ = M.ZabbixConfigurationGroupAssignment.objects.filter(
        zabbixconfigurationgroup__name__in=names,
        assigned_object_type=ct(DeviceRole),
        assigned_object_id=role.id,
    ).delete()
    return deleted


def _prune_template_names_from_model(model, ids, names: set[str]) -> int:
    if not ids:
        return 0
    deleted, _ = M.ZabbixTemplateAssignment.objects.filter(
        zabbixtemplate__name__in=names,
        assigned_object_type=ct(model),
        assigned_object_id__in=list(ids),
    ).delete()
    return deleted


def _fortios_device_type_ids() -> list[int]:
    return list(
        _fortios_devices()
        .exclude(device_type_id__isnull=True)
        .values_list('device_type_id', flat=True)
        .distinct()
    )


def _prune_fortios_colliding_templates() -> int:
    """Drop leftover ICMP/HTTP/SNMP assignments on FortiOS-owned objects.

    Observability already nests ICMP Ping and FortiGate by HTTP. Linking them
    again makes HostSync fail (parent linked twice). FortiGate by SNMP is a
    sibling ``icmpping`` collision, not a nested parent.

    Do not prune ICMP Ping from agent-plane CGs, manufacturers, or sites —
    servers still need the direct ICMP link, and FMG/FAZ may too.
    FortiOS uses CG FortiGate HTTP so Agent Monitoring does not win.
    """
    names = set(_FORTIOS_COLLIDING_TEMPLATES)
    total = 0
    n = _prune_template_names_from_model(Device, list(_fortios_devices().values_list('id', flat=True)), names)
    if n:
        logger.info('  PRUNED: %s colliding template assignment(s) from FortiOS devices', n)
    total += n
    n = _prune_template_names_from_model(Platform, [p.id for p in _fortios_platforms()], names)
    if n:
        logger.info('  PRUNED: %s colliding template assignment(s) from FortiOS platforms', n)
    total += n
    n = _prune_template_names_from_model(DeviceType, _fortios_device_type_ids(), names)
    if n:
        logger.info('  PRUNED: %s colliding template assignment(s) from FortiOS device types', n)
    total += n
    return total


def _prune_firewall_role_forti_templates() -> int:
    """Remove Forti/ICMP templates from role Firewall. SNMP CG is moved separately."""
    total = 0
    for role in _firewall_roles(required=False):
        n = _prune_role_template_names(role, set(_FIREWALL_ROLE_FORTI_TEMPLATES))
        if n:
            logger.info(
                '  PRUNED: %s Forti/ICMP template assignment(s) from role %s',
                n,
                role.name,
            )
        total += n
        _prune_firewall_role_forti_macros(role)
    return total


def _prune_firewall_role_forti_macros(role) -> int:
    names = set(_FORTIOS_PLATFORM_MACROS) | {_FGATE_TOKEN_MACRO, _FGATE_FQDN_MACRO}
    deleted, _ = M.ZabbixMacroAssignment.objects.filter(
        zabbixmacro__macro__in=names,
        assigned_object_type=ct(DeviceRole),
        assigned_object_id=role.id,
    ).delete()
    if deleted:
        logger.info('  PRUNED: %s Forti macro assignment(s) from role %s', deleted, role.name)
    return deleted


def _prune_fortios_device_fqdn() -> int:
    """Device-level {$FGATE.API.FQDN} wins over Platform Jinja. Delete leftovers."""
    ids = list(_fortios_devices().values_list('id', flat=True))
    if not ids:
        return 0
    deleted, _ = M.ZabbixMacroAssignment.objects.filter(
        zabbixmacro__macro=_FGATE_FQDN_MACRO,
        assigned_object_type=ct(Device),
        assigned_object_id__in=ids,
    ).delete()
    return deleted


def _snmp_monitoring_group():
    return M.ZabbixConfigurationGroup.objects.filter(name=_SNMP_MONITORING_CG).first()


def _agent_monitoring_group():
    return M.ZabbixConfigurationGroup.objects.filter(name=_AGENT_MONITORING_CG).first()


def _ensure_fortigate_http_group():
    group, _ = ensure(
        M.ZabbixConfigurationGroup,
        name=_FORTIGATE_HTTP_CG,
        defaults={
            'description': (
                'FortiOS HTTP transport. Agent @ primary so nested ICMP Ping '
                'has an address. No ICMP Ping template — Observability nests it. '
                'Assigned on Platform FortiOS; beats Site Group Agent Monitoring.'
            ),
        },
        update_fields=['description'],
    )
    return group


def _ensure_fortigate_http_agent_interface(server, group) -> None:
    ensure(
        M.ZabbixHostInterface,
        zabbixserver=server,
        assigned_object_type=ct(M.ZabbixConfigurationGroup),
        assigned_object_id=group.id,
        type=ZabbixHostInterfaceTypeChoices.AGENT,
        defaults={
            'zabbixconfigurationgroup': group,
            'interface_type': ZabbixInterfaceTypeChoices.DEFAULT,
            'port': 10050,
            'useip': ZabbixInterfaceUseChoices.IP,
            'tls_connect': ZabbixTLSChoices.NO_ENCRYPTION,
            'dns': '',
            'use_oob_ip': False,
        },
        update_fields=[
            'zabbixconfigurationgroup',
            'interface_type',
            'port',
            'useip',
            'tls_connect',
            'dns',
            'use_oob_ip',
        ],
    )


def _prune_icmp_from_fortigate_http_group(group) -> int:
    deleted, _ = M.ZabbixTemplateAssignment.objects.filter(
        zabbixtemplate__name=_ICMP_PING_TEMPLATE,
        assigned_object_type=ct(M.ZabbixConfigurationGroup),
        assigned_object_id=group.id,
    ).delete()
    if deleted:
        logger.info('  PRUNED: ICMP Ping from CG %s (Observability nests it)', group.name)
    return deleted


def _prune_cg_from_fortios_objects(group) -> tuple[int, int]:
    """Drop a CG from FortiOS devices and platforms so it cannot beat FortiGate HTTP."""
    device_n = 0
    platform_n = 0
    if group is None:
        return device_n, platform_n
    fortios_ids = list(_fortios_devices().values_list('id', flat=True))
    if fortios_ids:
        device_n, _ = M.ZabbixConfigurationGroupAssignment.objects.filter(
            zabbixconfigurationgroup=group,
            assigned_object_type=ct(Device),
            assigned_object_id__in=fortios_ids,
        ).delete()
    for plat in _fortios_platforms():
        n, _ = M.ZabbixConfigurationGroupAssignment.objects.filter(
            zabbixconfigurationgroup=group,
            assigned_object_type=ct(Platform),
            assigned_object_id=plat.id,
        ).delete()
        platform_n += n
    return device_n, platform_n


def _step_fortigate_http_transport(server) -> dict[str, int]:
    """FortiOS winning CG is FortiGate HTTP. FMG/FAZ keep SNMP Monitoring."""
    logger.info('Network: FortiOS HTTP transport (FortiGate HTTP CG, no SNMP/Agent Monitoring)')
    stats = {
        'fmg_faz_platforms': 0,
        'role_cg_pruned': 0,
        'fortios_device_cg_pruned': 0,
        'fortios_platform_cg_pruned': 0,
        'forti_http_platforms': 0,
        'icmp_pruned_from_forti_cg': 0,
    }
    forti_cg = _ensure_fortigate_http_group()
    _ensure_fortigate_http_agent_interface(server, forti_cg)
    stats['icmp_pruned_from_forti_cg'] = _prune_icmp_from_fortigate_http_group(forti_cg)
    for plat in _fortios_platforms():
        ensure(
            M.ZabbixConfigurationGroupAssignment,
            zabbixconfigurationgroup=forti_cg,
            assigned_object_type=ct(Platform),
            assigned_object_id=plat.id,
            defaults={},
        )
        stats['forti_http_platforms'] += 1
        logger.info('  Platform %s → %s (beats Site Group Agent Monitoring)', plat.name, _FORTIGATE_HTTP_CG)

    snmp = _snmp_monitoring_group()
    if snmp is None:
        logger.warning('  %s CG missing — skip SNMP prune / FMG-FAZ assign', _SNMP_MONITORING_CG)
    else:
        for plat in _fmg_faz_platforms():
            ensure(
                M.ZabbixConfigurationGroupAssignment,
                zabbixconfigurationgroup=snmp,
                assigned_object_type=ct(Platform),
                assigned_object_id=plat.id,
                defaults={},
            )
            stats['fmg_faz_platforms'] += 1
            logger.info('  Platform %s → %s (FMG/FAZ keep SNMP)', plat.name, _SNMP_MONITORING_CG)
        for role in _firewall_roles(required=False):
            n = _prune_role_cg_names(role, {_SNMP_MONITORING_CG})
            stats['role_cg_pruned'] += n
            if n:
                logger.info(
                    '  PRUNED: %s from role %s (FortiOS is HTTP; FMG/FAZ use platform)',
                    _SNMP_MONITORING_CG,
                    role.name,
                )
        d, p = _prune_cg_from_fortios_objects(snmp)
        stats['fortios_device_cg_pruned'] += d
        stats['fortios_platform_cg_pruned'] += p
        if d:
            logger.info('  PRUNED: %s FortiOS device-level %s', d, _SNMP_MONITORING_CG)
        if p:
            logger.info('  PRUNED: %s FortiOS platform-level %s', p, _SNMP_MONITORING_CG)

    agent = _agent_monitoring_group()
    d, p = _prune_cg_from_fortios_objects(agent)
    stats['fortios_device_cg_pruned'] += d
    stats['fortios_platform_cg_pruned'] += p
    if d:
        logger.info('  PRUNED: %s FortiOS device-level %s', d, _AGENT_MONITORING_CG)
    if p:
        logger.info('  PRUNED: %s FortiOS platform-level %s', p, _AGENT_MONITORING_CG)
    return stats


def _upsert_object_macro_assignment(
    server,
    obj,
    macro_name: str,
    value: str,
    *,
    mtype,
    description: str,
    context: str = '',
) -> None:
    """Server-level ZabbixMacro + assignment on Device/Role/Platform. Empty callers must skip."""
    zmacro, _ = ensure(
        M.ZabbixMacro,
        macro=macro_name,
        assigned_object_type=ct(M.ZabbixServer),
        assigned_object_id=server.id,
        defaults={
            'value': '',
            'type': mtype,
            'description': description,
        },
        update_fields=['type', 'description'],
    )
    ma = M.ZabbixMacroAssignment.objects.filter(
        zabbixmacro=zmacro,
        assigned_object_type=ct(type(obj)),
        assigned_object_id=obj.id,
        context=context,
        is_regex=False,
    ).first()
    if ma is None:
        M.ZabbixMacroAssignment.objects.create(
            zabbixmacro=zmacro,
            assigned_object_type=ct(type(obj)),
            assigned_object_id=obj.id,
            value=value,
            context=context,
            is_regex=False,
        )
        return
    if ma.value != value:
        ma.value = value
        ma.save(update_fields=['value'])


def _assignment_value(server, obj, macro_name: str) -> str:
    zmacro = M.ZabbixMacro.objects.filter(
        macro=macro_name,
        assigned_object_type=ct(M.ZabbixServer),
        assigned_object_id=server.id,
    ).first()
    if zmacro is None:
        return ''
    ma = M.ZabbixMacroAssignment.objects.filter(
        zabbixmacro=zmacro,
        assigned_object_type=ct(type(obj)),
        assigned_object_id=obj.id,
        context='',
        is_regex=False,
    ).first()
    return (ma.value or '').strip() if ma is not None else ''


def _effective_fortigate_token(server, dev) -> str:
    """Resolve the Zabbix monitoring token that HostSync renders."""
    device_token = _assignment_value(server, dev, _FGATE_TOKEN_MACRO)
    if device_token:
        return device_token
    platform = getattr(dev, 'platform', None)
    if platform is None:
        return ''
    return _assignment_value(server, platform, _FGATE_TOKEN_MACRO)


def _nb_ip_addr(ipobj) -> str | None:
    if ipobj is None:
        return None
    addr = getattr(ipobj, 'address', None)
    if addr is None:
        return None
    ip = getattr(addr, 'ip', None)
    return str(ip) if ip is not None else None


def _has_zabbix_server_assignment(dev, server) -> bool:
    objs = [dev]
    site = getattr(dev, 'site', None)
    if site is not None:
        objs.append(site)
        group = getattr(site, 'group', None)
        while group is not None:
            objs.append(group)
            group = getattr(group, 'parent', None)
    for obj in objs:
        if M.ZabbixServerAssignment.objects.filter(
            assigned_object_type=ct(type(obj)),
            assigned_object_id=obj.id,
            zabbixserver=server,
        ).exists():
            return True
    return False


def _device_has_template(dev, name: str) -> bool:
    return M.ZabbixTemplateAssignment.objects.filter(
        zabbixtemplate__name=name,
        assigned_object_type=ct(Device),
        assigned_object_id=dev.id,
    ).exists()


def _preflight_fortigate_http_zabbix(api, templateid) -> tuple[list[str], dict[str, str]]:
    """Read-only Cloud parent check. Empty vendor already aborted at lookup."""
    scripts = inspect_http_scripts(api, templateid)
    errors = [
        f'{_FORTIGATE_HTTP_TEMPLATE} missing script {key} — unexpected template content'
        for key, state in scripts.items()
        if state == 'missing'
    ]
    return errors, scripts


def _print_fortigate_http_plan(
    server,
    *,
    scripts: dict[str, str],
    icmp_ok: bool,
    errors: list[str],
) -> None:
    """Print the exact mutation set before any write. Always runs, even on abort."""
    logger.info('=' * 60)
    logger.info('FortiGate HTTP proposed writes (nothing written yet)')
    logger.info('=' * 60)
    vuln = [key for key, state in scripts.items() if state == 'vulnerable']
    ok_scripts = [key for key, state in scripts.items() if state == 'ok']
    missing = [key for key, state in scripts.items() if state == 'missing']
    logger.info('Zabbix Cloud %s:', _FORTIGATE_HTTP_TEMPLATE)
    logger.info('  ZBX-27082 patch: %s', ', '.join(vuln) or 'none (already fixed)')
    logger.info('  scripts already ok: %s', ', '.join(ok_scripts) or 'none')
    if missing:
        logger.info('  missing scripts: %s', ', '.join(missing))
    logger.info('  ensure %s; disable %s + discovery; WAN/SD-WAN state; CRIT 101; delays', 'fgate.ha.role', 'fgate.fwp.get_data')
    logger.info('  import companion %s (not bundled 7.0-3)', _FORTIGATE_OBSERVABILITY_TEMPLATE)
    logger.info('  ICMP Ping present: %s', 'yes' if icmp_ok else 'NO')
    existing = get_template_rule(server, _FORTIOS_TEMPLATE_RULE)
    current = getattr(getattr(existing, 'zabbixtemplate', None), 'name', None) or '(missing)'
    logger.info('NetBox TemplateRule %s: %s → %s', _FORTIOS_TEMPLATE_RULE, current, _FORTIGATE_OBSERVABILITY_TEMPLATE)
    logger.info(
        '  Platform FortiOS %s is the Zabbix monitoring token; %s remains '
        'the separate NetBox automation token',
        _FGATE_TOKEN_MACRO,
        _FGATE_AUTOMATION_TOKEN_ENV,
    )
    logger.info('  prune Forti/ICMP templates from role %s', _FIREWALL_ROLE)
    logger.info(
        '  prune nested ICMP/HTTP and leftover SNMP from FortiOS devices/platforms/device types (not agent CGs)',
    )
    logger.info('  CG %s on Platform FortiOS (Agent :10050, no ICMP Ping template)', _FORTIGATE_HTTP_CG)
    logger.info('  prune %s / %s from FortiOS devices and platforms (not Site Groups)', _SNMP_MONITORING_CG, _AGENT_MONITORING_CG)
    logger.info('  prune %s from role %s; assign it on FMG/FAZ platforms', _SNMP_MONITORING_CG, _FIREWALL_ROLE)
    logger.info('  Platform FortiOS %s = %s', _FGATE_FQDN_MACRO, _FGATE_FQDN_JINJA)
    logger.info(
        '  require HTTP 200 from every FortiOS primary_ip4 using the NetBox '
        '%s automation token; verify the separate monitoring token from each Zabbix proxy',
        _FGATE_AUTOMATION_TOKEN_ENV,
    )
    logger.info('FortiOS mutation set:')
    for dev in _fortios_devices():
        plat = getattr(getattr(dev, 'platform', None), 'name', '') or ''
        fqdn = _nb_ip_addr(dev.primary_ip4) or '(no primary_ip4)'
        logger.info('  %s platform=%s %s→%s', dev.name, plat or '-', _FGATE_FQDN_MACRO, fqdn)
    logger.info('Skipped (not FortiOS):')
    skipped = 0
    for role in _firewall_roles(required=False):
        for dev in Device.objects.filter(role=role).select_related('platform'):
            plat = getattr(getattr(dev, 'platform', None), 'name', '') or ''
            if _platform_is_fortios(plat):
                continue
            kind = 'FMG/FAZ' if _platform_is_fmg_faz(plat) else (plat or 'no-platform')
            logger.info('  %s (%s)', dev.name, kind)
            skipped += 1
    if skipped == 0:
        logger.info('  (none)')
    if errors:
        logger.info('Preflight errors (%s) — abort, no writes:', len(errors))
        for err in errors:
            logger.info('  %s', err)


def _preflight_fortigate_http(server, *, icmp_ok: bool) -> list[str]:
    """Validate inventory structure, NetBox automation access, and Zabbix token presence."""
    errors: list[str] = []
    devices = list(_fortios_devices())
    if not devices:
        errors.append('no FortiOS-platform devices in NetBox')
    if not icmp_ok:
        errors.append(f'{_ICMP_PING_TEMPLATE} missing in Zabbix')
    automation_token = (os.environ.get(_FGATE_AUTOMATION_TOKEN_ENV) or '').strip()
    if not automation_token:
        errors.append(
            f'{_FGATE_AUTOMATION_TOKEN_ENV} is missing; '
            'NetBox inventory automation preflight cannot authenticate'
        )
    seen_ip: dict[str, list[str]] = {}
    for dev in devices:
        plat = getattr(getattr(dev, 'platform', None), 'name', '') or ''
        if not _platform_is_fortios(plat):
            errors.append(f'{dev.name}: in FortiOS queryset but platform {plat!r} is not FortiOS')
            continue
        fqdn = _nb_ip_addr(dev.primary_ip4)
        if not fqdn:
            errors.append(f'{dev.name}: no primary_ip4 (OOB / ha-mgmt)')
        else:
            seen_ip.setdefault(fqdn, []).append(dev.name)
        if not _has_zabbix_server_assignment(dev, server):
            errors.append(f'{dev.name}: no Zabbix server/proxy assignment (device/site/sitegroup)')
        for name in _DEVICE_DUAL_LINK_TEMPLATES:
            if _device_has_template(dev, name):
                errors.append(
                    f'{dev.name}: device-level {name} would dual-link Observability '
                    f'(icmpping collision; SNMP is not a nested parent) — remove it first'
                )
        if not _effective_fortigate_token(server, dev):
            errors.append(
                f'{dev.name}: no effective Zabbix monitoring {_FGATE_TOKEN_MACRO} '
                '(Device or Platform assignment)'
            )
        if fqdn and automation_token:
            probe_error = _probe_fortigate_api(fqdn, automation_token)
            if probe_error:
                errors.append(
                    f'{dev.name}: NetBox automation API preflight '
                    f'{fqdn}:{_FGATE_API_PORT} failed: {probe_error}'
                )
            if not probe_error:
                interface_payload, interface_error = _fetch_fortigate_api(
                    fqdn,
                    automation_token,
                    '/api/v2/cmdb/system/interface?vdom=*',
                    port=_FGATE_API_PORT,
                )
                if interface_error:
                    errors.append(f'{dev.name}: FortiOS interface inventory failed: {interface_error}')
                elif not _flatten_forti_cmdb_list(interface_payload):
                    errors.append(f'{dev.name}: FortiOS interface inventory returned no rows')
                _sdwan_payload, sdwan_error = _fetch_fortigate_api(
                    fqdn,
                    automation_token,
                    '/api/v2/cmdb/system/sdwan?vdom=*',
                    port=_FGATE_API_PORT,
                )
                if sdwan_error:
                    errors.append(f'{dev.name}: FortiOS SD-WAN inventory failed: {sdwan_error}')
    for ip, names in seen_ip.items():
        if len(names) > 1:
            errors.append(f'duplicate management IP {ip}: {", ".join(names)}')
    for role in _firewall_roles(required=False):
        for dev in Device.objects.filter(role=role).select_related('platform'):
            plat = getattr(getattr(dev, 'platform', None), 'name', '') or ''
            if _platform_is_fortios(plat):
                continue
            for name in _FIREWALL_ROLE_FORTI_TEMPLATES:
                if _device_has_template(dev, name):
                    errors.append(
                        f'{dev.name}: non-FortiOS ({plat or "no-platform"}) has device-level {name}'
                    )
    return errors


def _step_fortigate_http_nbxsync(
    server,
    *,
    observability: tuple[int, str],
    http: tuple[int, str],
    snmp: tuple[int, str] | None,
    icmp: tuple[int, str] | None,
) -> None:
    """Retarget FortiOS to Observability companion. No Firewall role floor. No HostSync."""
    logger.info('=' * 60)
    logger.info('Network: FortiGate Observability nbxSync levers (FortiOS only, no HostSync)')
    logger.info('=' * 60)
    tpl_obs = ensure_nbx_template(
        server,
        observability[0],
        observability[1],
        req=[HostInterfaceRequirementChoices.ANY],
    )
    ensure_nbx_template(
        server,
        http[0],
        http[1],
        req=[HostInterfaceRequirementChoices.ANY],
    )
    if snmp is not None:
        ensure_nbx_template(
            server,
            snmp[0],
            snmp[1],
            req=[HostInterfaceRequirementChoices.SNMP],
        )
    if icmp is not None:
        ensure_nbx_template(
            server,
            icmp[0],
            icmp[1],
            req=[HostInterfaceRequirementChoices.ANY],
        )

    existing = get_template_rule(server, _FORTIOS_TEMPLATE_RULE)
    hg = existing.zabbixhostgroup if existing is not None and existing.zabbixhostgroup_id else _os_network_hostgroup(server)
    rule_defaults = {
        'pattern': _FORTIOS_PLATFORM_PATTERN,
        'zabbixtemplate': tpl_obs,
        'enabled': True,
        'priority': 100,
        'zabbixtag': None,
        'zabbixhostgroup': hg,
        'require_tags': '',
        'role_pattern': '',
        'manufacturer': None,
    }
    update_fields = ['zabbixtemplate'] if existing is not None else None
    ensure_template_rule(
        server,
        _FORTIOS_TEMPLATE_RULE,
        rule_defaults,
        update_fields=update_fields,
    )
    logger.info(
        '  TemplateRule %s → %s (ANY; nests %s + %s)',
        simulation_rule_name(server, _FORTIOS_TEMPLATE_RULE),
        tpl_obs.name,
        _FORTIGATE_HTTP_TEMPLATE,
        _ICMP_PING_TEMPLATE,
    )
    _prune_firewall_role_forti_templates()
    _prune_fortios_colliding_templates()


def _fortigate_desired_ifnames(dev, *, observable_names=None) -> list[str]:
    """Enabled+cabled NetBox links intersected with FortiOS-observable names."""
    names = list(
        Interface.objects.filter(device=dev, enabled=True, cable__isnull=False)
        .exclude(name='')
        .order_by('name')
        .values_list('name', flat=True)
    )
    if observable_names is None:
        return names
    observable = {str(name) for name in observable_names}
    return [name for name in names if name in observable]


def _step_fortios_device_macros(server) -> dict[str, int]:
    """Write observable NetBox link scope plus FortiOS thresholds per device."""
    logger.info('=' * 60)
    logger.info('Network: FortiOS per-device discovery and threshold macros')
    logger.info('=' * 60)
    devices = list(_fortios_devices())
    automation_token = (os.environ.get(_FGATE_AUTOMATION_TOKEN_ENV) or '').strip()
    inventory: dict[int, dict] = {}
    errors: list[str] = []
    for dev in devices:
        fqdn = _nb_ip_addr(dev.primary_ip4)
        if not fqdn or not automation_token:
            errors.append(f'{dev.name}: cannot derive FortiOS interface/SD-WAN scope')
            continue
        interface_payload, interface_error = _fetch_fortigate_api(
            fqdn,
            automation_token,
            '/api/v2/cmdb/system/interface?vdom=*',
            port=_FGATE_API_PORT,
        )
        sdwan_payload, sdwan_error = _fetch_fortigate_api(
            fqdn,
            automation_token,
            '/api/v2/cmdb/system/sdwan?vdom=*',
            port=_FGATE_API_PORT,
        )
        memory_payload, memory_error = _fetch_fortigate_api(
            fqdn,
            automation_token,
            '/api/v2/cmdb/system/global',
            port=_FGATE_API_PORT,
        )
        interface_rows = _flatten_forti_cmdb_list(interface_payload)
        if interface_error or not interface_rows:
            errors.append(
                f'{dev.name}: FortiOS interface inventory failed: '
                f'{interface_error or "no interface rows"}'
            )
        if sdwan_error:
            errors.append(f'{dev.name}: FortiOS SD-WAN inventory failed: {sdwan_error}')
        inventory[dev.pk] = {
            'interface_rows': interface_rows,
            'sdwan': _flatten_forti_sdwan_cmdb(sdwan_payload) if not sdwan_error else None,
            'thresholds': _fortigate_memory_thresholds(memory_payload),
            'threshold_error': memory_error,
        }
    if errors:
        raise SystemExit(
            'FortiOS device macro inventory failed — no per-device macros written:\n  '
            + '\n  '.join(errors)
        )

    stats = {
        'devices': 0,
        'token_assignment': 0,
        'fqdn_pruned': _prune_fortios_device_fqdn(),
        'interface_macros': 0,
        'sdwan_expectations': 0,
        'memory_thresholds': 0,
    }
    for dev in devices:
        stats['devices'] += 1
        if _assignment_value(server, dev, _FGATE_TOKEN_MACRO):
            stats['token_assignment'] += 1

        data = inventory[dev.pk]
        observable = {
            row.get('name') or row.get('q_origin_key')
            for row in data['interface_rows']
            if row.get('name') or row.get('q_origin_key')
        }
        netbox_ifnames = _fortigate_desired_ifnames(dev)
        ifnames = _fortigate_desired_ifnames(dev, observable_names=observable)
        unobservable = sorted(set(netbox_ifnames) - set(ifnames))
        scoped = {
            '{$NET.IF.IFNAME.MATCHES}': _fortigate_ifname_regex(ifnames),
            '{$NET.IF.DISCOVERY.MIN}': str(len(ifnames)),
        }
        for macro_name, macro_value in scoped.items():
            _upsert_object_macro_assignment(
                server,
                dev,
                macro_name,
                macro_value,
                mtype=ZabbixMacroTypeChoices.TEXT,
                description='nwn:fortios:netbox-observable-interface-scope',
            )
        stats['interface_macros'] += len(scoped)
        _upsert_object_macro_assignment(
            server,
            dev,
            '{$NET.IF.CONTROL}',
            '0',
            mtype=ZabbixMacroTypeChoices.TEXT,
            description='nwn:fortios:mgmt-link-state-unavailable',
            context='mgmt',
        )
        stats['interface_macros'] += 1

        sdwan_members = data['sdwan']['members']
        sdwan_expected = len(
            {
                str(row.get('q_origin_key') or row.get('interface'))
                for row in sdwan_members
                if row.get('q_origin_key') is not None or row.get('interface')
            }
        )
        _upsert_object_macro_assignment(
            server,
            dev,
            '{$FGATE.SDWAN.EXPECTED}',
            str(sdwan_expected),
            mtype=ZabbixMacroTypeChoices.TEXT,
            description='nwn:fortios:configured-sdwan-member-count',
        )
        stats['sdwan_expectations'] += 1

        thresholds = data['thresholds']
        threshold_error = data['threshold_error']
        if thresholds:
            for macro_name, macro_value in thresholds.items():
                _upsert_object_macro_assignment(
                    server,
                    dev,
                    macro_name,
                    macro_value,
                    mtype=ZabbixMacroTypeChoices.TEXT,
                    description='nwn:fortios:configured-memory-threshold',
                )
            stats['memory_thresholds'] += len(thresholds)
        elif threshold_error:
            logger.warning(
                '  %s: memory thresholds not refreshed (%s); preserving device override/platform defaults',
                dev.name,
                threshold_error,
            )
        if unobservable:
            logger.warning(
                '  %s: excluding NetBox enabled+cabled names absent from FortiOS CMDB: %s',
                dev.name,
                ', '.join(unobservable),
            )
        logger.info(
            '  %s: IFNAME=%s (%s observable of %s enabled+cabled), SD-WAN expected=%s, memory=%s',
            dev.name,
            scoped['{$NET.IF.IFNAME.MATCHES}'],
            len(ifnames),
            len(netbox_ifnames),
            sdwan_expected,
            '/'.join(thresholds.values()) if thresholds else 'platform/default',
        )

    logger.info(
        '  FortiOS devices=%s token_assignment=%s fqdn_pruned=%s '
        'interface_macros=%s sdwan_expectations=%s memory_thresholds=%s',
        stats['devices'],
        stats['token_assignment'],
        stats['fqdn_pruned'],
        stats['interface_macros'],
        stats['sdwan_expectations'],
        stats['memory_thresholds'],
    )
    return stats


def _expected_host_macros(canonical_role: str) -> dict[str, str]:
    expected = dict(ROLE_MACROS[canonical_role])
    for spec in ROLE_REGEX_MACRO_ASSIGNMENTS.get(canonical_role, ()):
        expected[_linkdown_ifalias_regex_macro(spec['context'])] = spec['value']
    return expected


def _zabbix_hosts_by_name(api, names: list[str]) -> dict[str, dict]:
    """host technical name → host.get row with macros. Chunked for large estates."""
    out: dict[str, dict] = {}
    chunk = 100
    for i in range(0, len(names), chunk):
        part = names[i : i + chunk]
        rows = api.host.get(
            filter={'host': part},
            output=['host', 'hostid'],
            selectMacros=['macro', 'value'],
        ) or []
        for row in rows:
            out[row['host']] = row
    return out


def _host_macros_match(host_row: dict, expected: dict[str, str]) -> bool:
    current = {m.get('macro'): m.get('value') for m in host_row.get('macros') or []}
    return all(current.get(macro) == value for macro, value in expected.items())


def _upsert_host_macros(api, hostid: str, wanted: dict[str, str]) -> list[str]:
    """Create/update named host macros only. Never replaces the rest of the host."""
    current = {m['macro']: m for m in api.usermacro.get(hostids=hostid, output='extend') or [] if m.get('macro')}
    changed: list[str] = []
    for macro, value in wanted.items():
        row = current.get(macro)
        if row is None:
            api.usermacro.create(hostid=hostid, macro=macro, value=value)
            changed.append(macro)
            continue
        if str(row.get('value') or '') != value:
            api.usermacro.update(hostmacroid=row['hostmacroid'], value=value)
            changed.append(macro)
    return changed


def _queue_if_lld_checks(api, hostids: list[str], *, log_label: str) -> dict[str, int | str]:
    """Check-now net.if.discovery so Access IFALIAS changes drop unlabelled rows."""
    if not hostids:
        return {'status': 'none', 'hosts': 0, 'tasks': 0}
    rules = []
    ordered = sorted({str(h) for h in hostids})
    for start in range(0, len(ordered), 100):
        rules.extend(
            api.discoveryrule.get(
                hostids=ordered[start:start + 100],
                filter={'key_': _IF_DISCOVERY_KEY},
                output=['itemid', 'hostid'],
            )
            or []
        )
    tasks = [
        {'type': _CHECK_NOW_TASK_TYPE, 'request': {'itemid': rule['itemid']}}
        for rule in rules
    ]
    if not tasks:
        return {'status': 'no-discovery-rules', 'hosts': len(ordered), 'tasks': 0}
    task_ids: list[str] = []
    for start in range(0, len(tasks), 20):
        result = api.task.create(tasks[start:start + 20]) or {}
        task_ids.extend(str(task_id) for task_id in result.get('taskids', []))
    logger.info(
        '  %s IF LLD check-now queued: hosts=%s rules=%s tasks=%s',
        log_label,
        len(ordered),
        len(rules),
        len(task_ids),
    )
    return {'status': 'queued', 'hosts': len(ordered), 'tasks': len(task_ids)}


def queue_oob_if_lld_checks(api) -> dict[str, int | str]:
    """Check-now IF LLD on hosts still holding chassis OOB interface rows."""
    template_ids: set[str] = set()
    for name in (_EXOS_STOCK_TEMPLATE, _EXOS_OBSERVABILITY_TEMPLATE, _VOSS_TEMPLATE):
        found = api.template.get(filter={'name': [name]}, output=['templateid']) or []
        template_ids.update(str(t['templateid']) for t in found)
    if not template_ids:
        return {'status': 'missing-template', 'hosts': 0, 'tasks': 0}

    host_ids: set[str] = set()
    for template_id in sorted(template_ids):
        hosts = api.host.get(templateids=[template_id], output=['hostid']) or []
        host_ids.update(str(h['hostid']) for h in hosts)
    if not host_ids:
        return {'status': 'no-hosts', 'hosts': 0, 'tasks': 0}

    stale: set[str] = set()
    ordered = sorted(host_ids)
    for start in range(0, len(ordered), 100):
        chunk = ordered[start:start + 100]
        for needle in _IFNAME_OOB_ITEM_NEEDLES:
            items = api.item.get(
                hostids=chunk,
                search={'name': needle},
                output=['hostid'],
            ) or []
            stale.update(str(item['hostid']) for item in items)
    if not stale:
        return {'status': 'clean', 'hosts': 0, 'tasks': 0}
    return _queue_if_lld_checks(api, sorted(stale), log_label='chassis OOB')


def patch_access_port_scope_host_macros(api) -> dict[str, int | str]:
    """Write Access IFALIAS / LINKDOWN.IFALIAS on Zabbix hosts. Not HostSync.

    Template default IFALIAS.MATCHES is ``.*`` (Core-safe). Access hosts that
    never got HostSync inherit that and ticket every admin-up desk port. This
    writes only Switch Access host macros so the Average requires a grammar
    display-string. Core/Dist/Mgmt hosts are not touched.
    """
    logger.info('Network: Switch Access host macros (IFALIAS + LINKDOWN.IFALIAS grammar)')
    roles = resolve_roles_for_macros('Switch Access')
    if not roles:
        logger.info('  No Switch Access role — skip')
        return {'status': 'no-role', 'patched': 0, 'missing': 0, 'in_sync': 0}
    wanted = _access_zabbix_host_macros(ROLE_MACROS['Switch Access'])
    devices = list(
        Device.objects.filter(status='active', role_id__in=[r.pk for r in roles]).order_by('name')
    )
    if not devices:
        logger.info('  No active Switch Access devices — skip')
        return {'status': 'no-devices', 'patched': 0, 'missing': 0, 'in_sync': 0}
    by_host = _zabbix_hosts_by_name(api, [d.name for d in devices])
    patched: list[str] = []
    missing: list[str] = []
    in_sync = 0
    patched_hostids: list[str] = []
    for device in devices:
        row = by_host.get(device.name)
        if row is None:
            missing.append(device.name)
            continue
        changed = _upsert_host_macros(api, str(row['hostid']), wanted)
        if changed:
            patched.append(device.name)
            patched_hostids.append(str(row['hostid']))
            logger.info('  %s: wrote %s', device.name, ', '.join(changed))
        else:
            in_sync += 1
    queued = _queue_if_lld_checks(api, patched_hostids, log_label='Access') if patched_hostids else {
        'status': 'none',
        'hosts': 0,
        'tasks': 0,
    }
    logger.info(
        '  Access host macros: patched=%s in_sync=%s missing_in_zabbix=%s check-now=%s',
        len(patched),
        in_sync,
        len(missing),
        queued.get('status'),
    )
    if missing:
        logger.warning('  Access devices not in Zabbix (sample): %s', missing[:12])
    return {
        'status': 'ok',
        'patched': len(patched),
        'in_sync': in_sync,
        'missing': len(missing),
        'sample': patched[:12],
        'check_now': queued.get('status'),
        'check_now_tasks': queued.get('tasks', 0),
    }


def report_hosts_needing_macro_sync(server=None) -> dict:
    """Log Switch* hosts whose Zabbix host macros differ from NetBox role assignments.

    Access IFALIAS / LINKDOWN.IFALIAS are written by
    ``patch_access_port_scope_host_macros`` (not HostSync). Remaining drift is
    Core/Dist/Mgmt or Access hosts not yet in Zabbix.
    """
    role_macros_by_id: dict[int, dict[str, str]] = {}
    for canonical in ROLE_MACROS:
        expected = _expected_host_macros(canonical)
        for role in resolve_roles_for_macros(canonical):
            role_macros_by_id[role.pk] = expected
    if not role_macros_by_id:
        logger.info('Network: no Switch* roles found — skip HostSync reminder')
        return {'count': 0, 'sample': [], 'in_sync': 0, 'missing': 0}
    qs = Device.objects.filter(status='active', role_id__in=role_macros_by_id).select_related('role')
    devices = list(qs.order_by('name'))
    if not devices:
        logger.info('Network: no active Switch* devices — skip HostSync reminder')
        return {'count': 0, 'sample': [], 'in_sync': 0, 'missing': 0}

    drifted: list[str] = []
    missing: list[str] = []
    in_sync = 0
    compared = False
    if server is not None:
        try:
            with ZabbixConnection(server) as api:
                by_host = _zabbix_hosts_by_name(api, [d.name for d in devices])
            compared = True
            for device in devices:
                expected = role_macros_by_id.get(device.role_id) or {}
                row = by_host.get(device.name)
                if row is None:
                    missing.append(device.name)
                    continue
                if _host_macros_match(row, expected):
                    in_sync += 1
                else:
                    drifted.append(device.name)
        except Exception as exc:
            logger.info(
                'Could not compare Switch* host macros via Zabbix API (%s). '
                '%s active Switch* device(s) inherit role IFALIAS / Access PORTID; '
                'this is not a stale-host list. --apply does not mass-sync. Sample: %s',
                exc,
                len(devices),
                [d.name for d in devices[:12]],
            )
            return {
                'count': 0,
                'sample': [d.name for d in devices[:12]],
                'in_sync': 0,
                'missing': 0,
                'reminder_only': True,
            }

    if not compared:
        logger.info(
            'Reminder: role IFALIAS / Access PORTID become host macros only after HostSync. '
            '%s active Switch* device(s) inherit those assignments; this is not a stale-host list. '
            '--apply does not mass-sync. Sample: %s',
            len(devices),
            [d.name for d in devices[:12]],
        )
        return {
            'count': 0,
            'sample': [d.name for d in devices[:12]],
            'in_sync': 0,
            'missing': 0,
            'reminder_only': True,
        }

    needs_sync = drifted + missing
    if not needs_sync:
        logger.info(
            'Network: %s active Switch* Zabbix host(s) already have role IFALIAS / PORTID macros; none need HostSync',
            in_sync,
        )
        return {'count': 0, 'sample': [], 'in_sync': in_sync, 'missing': 0}

    logger.warning(
        'Role IFALIAS / Access PORTID live as host macros after HostSync. '
        '--apply updated NetBox assignments only. Does not mass-sync. '
        '%s host(s) differ from role assignments, %s not yet in Zabbix, %s already in sync. Sample: %s',
        len(drifted),
        len(missing),
        in_sync,
        needs_sync[:12],
    )
    return {
        'count': len(needs_sync),
        'sample': needs_sync[:12],
        'in_sync': in_sync,
        'missing': len(missing),
        'drifted': len(drifted),
    }


def step_template_rules(server, tpl: dict[str, M.ZabbixTemplate]) -> None:
    """Ensure Extreme platform TemplateRules (EXOS/VOSS/IQ Engine; same as zerotouch)."""
    logger.info('=' * 60)
    logger.info('Network: Extreme platform TemplateRules')
    logger.info('=' * 60)
    hg_os_network, _ = ensure(
        M.ZabbixHostgroup,
        zabbixserver=server,
        name=f'{PREFIX}OS/Network' if server.name == SIM_SERVER_NAME else 'OS/Network',
        defaults={'value': 'OS/Network'},
        update_fields=['value'],
    )

    rule_specs = (
        ('Extreme EXOS', 'EXOS|Switch Engine', 'Extreme EXOS Observability'),
        ('Extreme VOSS', 'VOSS|Fabric Engine', 'Extreme VOSS by SNMP'),
        ('Extreme IQ Engine', 'IQ ENGINE|IQEngine|IQ-ENGINE', 'Extreme IQ Engine by SNMP'),
    )
    for rule_name, pattern, tpl_name in rule_specs:
        if tpl_name not in tpl:
            continue
        ensure_template_rule(
            server,
            rule_name,
            {
                'pattern': pattern,
                'zabbixtemplate': tpl[tpl_name],
                'enabled': True,
                'priority': 100,
                'zabbixtag': None,
                'zabbixhostgroup': hg_os_network,
                'require_tags': '',
                'role_pattern': '',
                'manufacturer': None,
            },
        )
        logger.info('  Rule %s → %s', simulation_rule_name(server, rule_name), tpl[tpl_name].name)

    for rule_name, _pattern, tpl_name in rule_specs:
        if tpl_name not in tpl:
            continue
        names = ztc.template_rule_names(server, rule_name, **_rule_kwargs())
        for rule in template_rules_for_server(server).filter(name__in=names):
            if rule.zabbixtemplate_id and 'Network Generic' in (rule.zabbixtemplate.name or ''):
                rule.zabbixtemplate = tpl[tpl_name]
                rule.save(update_fields=['zabbixtemplate'])
                logger.info('  PRUNED: %s rule was Network Generic → retargeted', rule.name)


def step_speed_expect_assignment(server, tpl: dict[str, M.ZabbixTemplate], *, link: bool) -> None:
    """Optional NetBox role assignment. Default off — Speed Expect is nested on
    VOSS and EXOS Observability, so empty display-strings stay undiscovered and
    a later HostSync must not also link the same template directly.
    """
    t = tpl.get('Extreme Port Speed Expect by SNMP')
    role_names = ('Switch Core', 'Switch Dist', 'Switch Mgmt', 'Switch Access')
    if not link or t is None:
        if t is not None:
            pruned = 0
            for role_name in role_names:
                try:
                    role = get_role(role_name)
                except DeviceRole.DoesNotExist:
                    role = DeviceRole.objects.filter(name__icontains=role_name.replace('Switch ', '')).first()
                    if role is None:
                        continue
                deleted, _ = M.ZabbixTemplateAssignment.objects.filter(
                    zabbixtemplate=t,
                    assigned_object_type=ct(DeviceRole),
                    assigned_object_id=role.id,
                ).delete()
                pruned += deleted
            if pruned:
                logger.info('  PRUNED: %s leftover Speed Expect role assignment(s) (nested on VOSS/Observability)', pruned)
        logger.info(
            '  Speed Expect: nested on VOSS / EXOS Observability (unlabeled ifAlias '
            'is not discovered). Not assigning on Switch roles (pass --link-speed-expect '
            'only if a stock-only host has no companion/VOSS parent).'
        )
        return
    for role_name in role_names:
        try:
            role = get_role(role_name)
        except DeviceRole.DoesNotExist:
            role = DeviceRole.objects.filter(name__icontains=role_name.replace('Switch ', '')).first()
            if role is None:
                continue
        ensure(
            M.ZabbixTemplateAssignment,
            zabbixtemplate=t,
            assigned_object_type=ct(DeviceRole),
            assigned_object_id=role.id,
            defaults={},
        )
        logger.info('  Speed Expect → role %s', role.name)


def step_snmp_cg_on_switch_roles(snmp_group) -> None:
    for role_name in SWITCH_SNMP_ROLES:
        try:
            role = get_role(role_name)
        except DeviceRole.DoesNotExist:
            role, _ = DeviceRole.objects.get_or_create(
                slug=slugify(role_name),
                defaults={'name': f'{PREFIX}{role_name}', 'color': '4caf50', 'vm_role': False},
            )
        ensure(
            M.ZabbixConfigurationGroupAssignment,
            zabbixconfigurationgroup=snmp_group,
            assigned_object_type=ct(DeviceRole),
            assigned_object_id=role.id,
            defaults={},
        )


def cleanup_lab() -> None:
    Device.objects.filter(name__startswith=PREFIX).delete()
    M.ZabbixMacroAssignment.objects.filter(zabbixmacro__description__startswith='nwn:').delete()
    M.ZabbixMacro.objects.filter(description__startswith='nwn:').delete()
    M.ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup__name__startswith=PREFIX).delete()
    M.ZabbixConfigurationGroupAssignment.objects.filter(zabbixconfigurationgroup__name__startswith=PREFIX).delete()
    M.ZabbixTemplateAssignment.objects.filter(zabbixtemplate__name__startswith=PREFIX).delete()
    M.ZabbixTemplateAssignment.objects.filter(zabbixtemplate__name__startswith='Extreme').filter(
        assigned_object_type=ct(DeviceRole),
        assigned_object_id__in=DeviceRole.objects.filter(slug__startswith=PREFIX).values_list('pk', flat=True),
    ).delete()
    # Do not delete a shared lab ZabbixServer (may be ZeroTouch Configure Lab).
    # Never treat an arbitrary URL match as lab — that can be production.
    lab_ok_names = _lab_server_names()
    lab_servers = M.ZabbixServer.objects.filter(name__in=lab_ok_names)
    if LAB_JSON.exists():
        lab_url = json.loads(LAB_JSON.read_text()).get('url')
        if lab_url:
            foreign = M.ZabbixServer.objects.filter(url=lab_url).exclude(name__in=lab_ok_names)
            if foreign.exists():
                names = ', '.join(foreign.values_list('name', flat=True))
                raise SystemExit(
                    f'Refusing --simulate cleanup: ZabbixServer(s) {names} share lab URL {lab_url!r} '
                    f'but are not {sorted(lab_ok_names)}. Rename or remove them first.'
                )
    for server in lab_servers.distinct():
        template_rules_for_server(server).filter(name__startswith=PREFIX).delete()
        M.ZabbixTemplateRule.objects.filter(
            zabbixtemplate__zabbixserver=server,
            zabbixtemplate__name__startswith=PREFIX,
        ).delete()
        M.ZabbixHostBinding.objects.filter(zabbixserver=server, hostname__startswith=PREFIX).delete()
        M.ZabbixHostgroup.objects.filter(zabbixserver=server, name__startswith=PREFIX).delete()
        M.ZabbixTemplate.objects.filter(zabbixserver=server, name__startswith=PREFIX).delete()
    M.ZabbixServer.objects.filter(name=SIM_SERVER_NAME).delete()
    M.ZabbixConfigurationGroup.objects.filter(name__startswith=PREFIX).delete()
    Site.objects.filter(slug__startswith=PREFIX).delete()
    SiteGroup.objects.filter(slug__startswith=PREFIX).delete()
    DeviceRole.objects.filter(slug__startswith=PREFIX).delete()
    Platform.objects.filter(slug__startswith=PREFIX).delete()
    DeviceType.objects.filter(slug__startswith=PREFIX).delete()
    Manufacturer.objects.filter(slug__startswith=PREFIX).delete()
    Tag.objects.filter(slug__startswith=PREFIX).delete()


def run_simulate(*, link_speed_expect: bool = False, cutover_silence: bool = False) -> int:
    apply_macro_mode(cutover_silence=cutover_silence)
    global RESULTS
    RESULTS = []
    cleanup_lab()

    if not LAB_JSON.exists():
        raise SystemExit(f'Lab credentials missing: {LAB_JSON}')
    lab = json.loads(LAB_JSON.read_text())

    sg_ch, _ = SiteGroup.objects.get_or_create(slug=slugify('CH'), defaults={'name': f'{PREFIX}CH'})
    leaf, _ = SiteGroup.objects.get_or_create(slug=slugify('CH-STA'), defaults={'name': f'{PREFIX}CH-STA', 'parent': sg_ch})
    site, _ = Site.objects.get_or_create(slug=slugify('CH-STA-L44'), defaults={'name': f'{PREFIX}CH-STA-L44', 'group': leaf})

    roles = {}
    for name in SWITCH_SNMP_ROLES:
        roles[name], _ = DeviceRole.objects.get_or_create(
            slug=slugify(name),
            defaults={'name': f'{PREFIX}{name}', 'color': '4caf50', 'vm_role': False},
        )
    roles['Access Point'], _ = DeviceRole.objects.get_or_create(
        slug=slugify('Access Point'),
        defaults={'name': f'{PREFIX}Access Point', 'color': '2196f3', 'vm_role': False},
    )
    roles[_FIREWALL_ROLE], _ = DeviceRole.objects.get_or_create(
        slug=slugify(_FIREWALL_ROLE),
        defaults={'name': f'{PREFIX}{_FIREWALL_ROLE}', 'color': 'ff9800', 'vm_role': False},
    )

    # Monkey-patch get_role for prefixed lab (same trick as zerotouch)
    orig_get_role = globals()['get_role']

    def lab_get_role(name: str) -> DeviceRole:
        return DeviceRole.objects.get(slug=slugify(name))

    globals()['get_role'] = lab_get_role

    try:
        # One ZabbixServer per URL (unique constraint). Reuse zerotouch lab server if present.
        lab_ok_names = _lab_server_names()
        server = M.ZabbixServer.objects.filter(name=SIM_SERVER_NAME).first()
        if server is None:
            ztc_lab = 'ZeroTouch Configure Lab'
            server = M.ZabbixServer.objects.filter(name=ztc_lab, url=lab['url']).first()
        if server is None:
            conflict = M.ZabbixServer.objects.filter(url=lab['url']).exclude(name__in=lab_ok_names).first()
            if conflict is not None:
                raise SystemExit(
                    f'Lab URL {lab["url"]!r} already used by ZabbixServer {conflict.name!r} — '
                    'refusing to reuse a non-lab server for --simulate'
                )
            server = M.ZabbixServer.objects.create(
                name=SIM_SERVER_NAME,
                url=lab['url'],
                token=lab['token'],
                validate_certs=False,
                sync_enabled=True,
                skip_version_check=False,
            )
        else:
            logger.info('Reusing ZabbixServer %r for lab URL', server.name)
            server.token = lab['token']
            server.url = lab['url']
            server.validate_certs = False
            server.sync_enabled = True
            server.skip_version_check = False
            server.save()

        M.ZabbixServerAssignment.objects.get_or_create(
            zabbixserver=server,
            assigned_object_type=ct(SiteGroup),
            assigned_object_id=sg_ch.id,
            defaults={'sync_enabled': True},
        )

        snmp_group, _ = M.ZabbixConfigurationGroup.objects.get_or_create(
            name=f'{PREFIX}SNMP Monitoring',
            defaults={'description': 'network lab'},
        )
        # SNMP interface on CG (same shape as zerotouch step5)
        ensure(
            M.ZabbixHostInterface,
            zabbixserver=server,
            assigned_object_type=ct(M.ZabbixConfigurationGroup),
            assigned_object_id=snmp_group.pk,
            type=ZabbixHostInterfaceTypeChoices.SNMP,
            defaults={
                'interface_type': ZabbixInterfaceTypeChoices.DEFAULT,
                'useip': ZabbixInterfaceUseChoices.IP,
                'port': 161,
                'snmp_version': ZabbixHostInterfaceSNMPVersionChoices.SNMPV2,
                'snmp_community': '{$SNMP_COMMUNITY}',
                'dns': '',
            },
            update_fields=['interface_type', 'useip', 'port', 'snmp_version', 'snmp_community', 'dns'],
        )
        step_snmp_cg_on_switch_roles(snmp_group)
        ensure(
            M.ZabbixConfigurationGroupAssignment,
            zabbixconfigurationgroup=snmp_group,
            assigned_object_type=ct(DeviceRole),
            assigned_object_id=roles['Access Point'].id,
            defaults={},
        )

        with ZabbixConnection(server) as api:
            # Clean previous nwn- hosts
            for h in api.host.get(search={'host': PREFIX}, output=['hostid', 'host']) or []:
                if h['host'].startswith(PREFIX):
                    api.host.delete(h['hostid'])
            imported = import_extreme_templates(api)
            step_global_macros_zabbix(api)
            # Stub Extreme EXOS if stock missing (lab may not have it)
            if 'Extreme EXOS by SNMP' not in imported:
                tgroups = api.templategroup.get(filter={'name': f'{PREFIX}templates'})
                tgid = tgroups[0]['groupid'] if tgroups else api.templategroup.create(name=f'{PREFIX}templates')['groupids'][0]
                tid = api.template.create(host=f'{PREFIX}exos.snmp', name='Extreme EXOS by SNMP', groups=[{'groupid': tgid}])['templateids'][0]
                # Avoid icmpping collision later — add a dummy item-less template is fine for resolve tests
                imported['Extreme EXOS by SNMP'] = (int(tid), 'Extreme EXOS by SNMP')
                record('lab_stub_exos', True, 'stock EXOS absent — stub template created', group='import')
            patch_statuses = patch_etherlike_ifalias_filters(api)
            for tname, status in patch_statuses.items():
                # missing/no-duplex-lld OK for lab stub EXOS; fail only on unexpected API outcomes
                record(
                    f'etherlike_ifalias_{tname}',
                    status in ('ok', 'patched', 'no-duplex-lld', 'missing'),
                    status,
                    group='import',
                )
            for tname in ('Extreme EXOS by SNMP', 'Extreme VOSS by SNMP'):
                ok, detail = assert_etherlike_ifalias_filters(api, tname)
                record(f'etherlike_ifalias_assert_{tname}', ok, detail, group='import')

            if_lld_status = patch_exos_interface_lld_rollout(api)
            record(
                'exos_if_lld_rollout',
                if_lld_status in ('ok', 'patched', 'missing', 'no-if-lld'),
                if_lld_status,
                group='import',
            )
            ok, detail = assert_exos_interface_lld_rollout(api)
            # Lab stub EXOS has no real IF LLD — treat missing/n/a as pass
            record('exos_if_lld_rollout_assert', ok or 'n/a' in detail, detail, group='import')

            ifname_oob = patch_ifname_skip_chassis_oob(api)
            for tname, status in ifname_oob.items():
                record(
                    f'ifname_oob_{tname}',
                    status in ('ok', 'patched', 'missing'),
                    status,
                    group='import',
                )
                ok, detail = assert_ifname_skip_chassis_oob(api, tname)
                record(f'ifname_oob_assert_{tname}', ok or 'n/a' in detail, detail, group='import')

            psu_lld_status = patch_exos_psu_lld_present_only(api)
            record(
                'exos_psu_lld_present_only',
                psu_lld_status in ('ok', 'patched', 'missing', 'no-psu-lld'),
                psu_lld_status,
                group='import',
            )
            ok, detail = assert_exos_psu_lld_present_only(api)
            record('exos_psu_lld_present_only_assert', ok or 'n/a' in detail, detail, group='import')

            voss_psu = patch_voss_psu_lld_present_only(api)
            for key, status in voss_psu.items():
                record(
                    f'voss_psu_lld_{key}',
                    status in ('ok', 'patched', 'missing', 'no-psu-lld'),
                    status,
                    group='import',
                )
            ok, detail = assert_voss_psu_lld_present_only(api)
            record('voss_psu_lld_present_only_assert', ok or 'n/a' in detail, detail, group='import')

            psu_not_up = patch_psu_not_up(api)
            for tname, status in psu_not_up.items():
                record(
                    f'psu_not_up_{tname}',
                    status in ('ok', 'patched', 'missing', 'no-psu-lld'),
                    status,
                    group='import',
                )
                ok, detail = assert_psu_not_up(api, tname)
                record(f'psu_not_up_assert_{tname}', ok or 'n/a' in detail, detail, group='import')

            linkdown_status = patch_linkdown_one_average(api)
            for tname, status in linkdown_status.items():
                record(
                    f'linkdown_average_{tname}',
                    status in ('ok', 'patched', 'missing', 'no-if-lld'),
                    status,
                    group='import',
                )
                ok, detail = assert_linkdown_one_average(api, tname)
                record(f'linkdown_average_assert_{tname}', ok or 'n/a' in detail, detail, group='import')

            temp_statuses = patch_extreme_template_temp_macros(api)
            for tname, status in temp_statuses.items():
                record(
                    f'template_temp_{tname}',
                    status in ('ok', 'patched', 'missing'),
                    status,
                    group='import',
                )
            for tname in _TEMP_TEMPLATE_NAMES:
                ok, detail = assert_extreme_template_temp_macros(api, tname)
                record(f'template_temp_assert_{tname}', ok, detail, group='import')

            util_statuses = patch_extreme_template_util_macros(api)
            for tname, status in util_statuses.items():
                record(
                    f'template_util_{tname}',
                    status in ('ok', 'patched', 'missing'),
                    status,
                    group='import',
                )
            for tname in _IF_UTIL_TEMPLATE_NAMES:
                ok, detail = assert_extreme_template_util_macros(api, tname)
                record(f'template_util_assert_{tname}', ok or 'n/a' in detail, detail, group='import')

            health = step_health_patches(api)
            icmp_statuses = health.get('icmp_noise') or {}
            for tname, status in icmp_statuses.items():
                record(
                    f'icmp_noise_{tname}',
                    status in ('ok', 'patched', 'missing', 'no-triggers', 'no-names'),
                    status,
                    group='import',
                )
            ascii_titles = patch_ascii_trigger_titles(api)
            for tname, status in ascii_titles.items():
                record(
                    f'ascii_titles_{tname}',
                    str(status).startswith(('ok', 'patched', 'missing', 'lld-pending', 'queued')),
                    status,
                    group='import',
                )
            for tname in _ASCII_TITLE_TEMPLATES:
                ok, detail = assert_ascii_trigger_titles(api, tname)
                record(f'ascii_titles_assert_{tname}', ok or 'n/a' in detail, detail, group='import')
            record(
                'exos_health_dashboard',
                str(health.get('exos_health')) == 'companion-yaml',
                str(health.get('exos_health')),
                group='import',
            )
            record(
                'exos_stock_interface_grid',
                str(health.get('exos_stock_grid')) in ('ok', 'patched', 'missing-template'),
                str(health.get('exos_stock_grid')),
                group='import',
            )
            record(
                'iq_interface_honeycomb',
                str(health.get('iq_interface_map')) in ('ok', 'patched', 'missing-template'),
                str(health.get('iq_interface_map')),
                group='import',
            )
            for tname in ('Extreme VOSS by SNMP', 'Extreme IQ Engine by SNMP', 'Extreme EXOS by SNMP'):
                ok, detail = assert_wan_icmp_noise_disabled(api, tname)
                record(f'icmp_noise_assert_{tname}', ok, detail, group='import')
            ok, detail = assert_template_macros(api, 'Extreme VOSS by SNMP', VOSS_HEALTH_MACROS)
            record('voss_health_macros', ok, detail, group='import')
            ok, detail = assert_template_macros(api, 'Extreme Port Speed Expect by SNMP', SPEED_EXPECT_HEALTH_MACROS)
            record('speed_expect_usw_util_off', ok, detail, group='import')
            ok, detail = assert_template_macros(api, 'Extreme IQ Engine by SNMP', IQ_HEALTH_MACROS)
            record('iq_health_macros', ok, detail, group='import')
            ok, detail = assert_template_dashboard(api, 'Extreme VOSS by SNMP', 'Health', ('Overview', 'Hardware'))
            record('voss_health_dashboard', ok, detail, group='import')
            ok, detail = assert_template_dashboard(api, 'Extreme IQ Engine by SNMP', 'Health', ('Overview', 'RF'))
            record('iq_health_dashboard', ok, detail, group='import')
            ok, detail = assert_template_dashboard(api, 'Extreme EXOS Observability', 'Health', ('Overview', 'Hardware'))
            # The companion may be absent in a deliberately minimal lab stub.
            record(
                'exos_health_dashboard_assert',
                ok or 'n/a' in detail,
                detail,
                group='import',
            )
            for tname, pages in (
                ('Extreme VOSS by SNMP', ('Overview', 'Port')),
                ('Extreme IQ Engine by SNMP', ('Overview',)),
                ('Extreme EXOS by SNMP', ('Overview', 'Port')),
            ):
                ok, detail = assert_template_dashboard(api, tname, 'Network interfaces', pages)
                record(f'interface_dashboard_{tname}', ok, detail, group='import')
            ok, detail = assert_exos_stock_interface_grid(api)
            record('exos_stock_interface_grid_assert', ok, detail, group='import')

        tpl_models: dict[str, M.ZabbixTemplate] = {}
        for name, (tid, _) in imported.items():
            tpl_models[name] = ensure_nbx_template(server, tid, name)
            record(f'import_{name}', True, str(tid), group='import')

        step_server_macros(server)
        step_role_macros(server)
        report_hosts_needing_macro_sync(server)
        step_template_rules(server, tpl_models)
        step_speed_expect_assignment(server, tpl_models, link=link_speed_expect)

        # Hostgroups (Sites × Roles) — same Jinja idea as zerotouch
        hg_lab, _ = ensure(M.ZabbixHostgroup, zabbixserver=server, name=f'{PREFIX}lab', defaults={'value': f'{PREFIX}lab'}, update_fields=['value'])
        hg_sites, _ = ensure(
            M.ZabbixHostgroup,
            zabbixserver=server,
            name=f'{PREFIX}Sites',
            defaults={
                'value': ('Sites/{{ object.site.group.get_ancestors(include_self=True) ' '| map(attribute="name") | join("/") }}/{{ object.site.name }}'),
            },
            update_fields=['value'],
        )
        hg_roles, _ = ensure(
            M.ZabbixHostgroup,
            zabbixserver=server,
            name=f'{PREFIX}Roles',
            defaults={'value': 'Roles/{{ object.role.name }}'},
            update_fields=['value'],
        )
        for hg in (hg_lab, hg_sites, hg_roles):
            M.ZabbixHostgroupAssignment.objects.get_or_create(
                zabbixhostgroup=hg,
                assigned_object_type=ct(SiteGroup),
                assigned_object_id=sg_ch.id,
            )

        mfr, _ = Manufacturer.objects.get_or_create(slug=slugify('extreme'), defaults={'name': f'{PREFIX}Extreme'})
        dtype, _ = DeviceType.objects.get_or_create(slug=slugify('5520'), defaults={'manufacturer': mfr, 'model': f'{PREFIX}5520'})
        plat_voss, _ = Platform.objects.get_or_create(slug=slugify('voss'), defaults={'name': f'{PREFIX}Extreme VOSS 9.3'})
        plat_exos, _ = Platform.objects.get_or_create(slug=slugify('exos'), defaults={'name': f'{PREFIX}Extreme EXOS 32.1'})
        plat_iq, _ = Platform.objects.get_or_create(
            slug=slugify('iq-engine'),
            defaults={'name': f'{PREFIX}Extreme IQ ENGINE 10.6'},
        )
        plat_fortios, _ = Platform.objects.get_or_create(
            slug=slugify('fortios'),
            defaults={'name': f'{PREFIX}FortiOS 7.4'},
        )

        octet = [50]

        def next_ip():
            octet[0] += 1
            return f'10.92.1.{octet[0]}/32'

        def attach(device, address):
            iface = Interface.objects.create(device=device, name='Mgmt', type='1000base-t')
            ip = IPAddress.objects.create(address=address, status='active', assigned_object=iface)
            device.primary_ip4 = ip
            device.save()

        objects = {}
        for key, role_name, platform in [
            ('voss_core', 'Switch Core', plat_voss),
            ('voss_dist', 'Switch Dist', plat_voss),
            ('voss_access', 'Switch Access', plat_voss),
            ('exos_core', 'Switch Core', plat_exos),
            ('exos_dist', 'Switch Dist', plat_exos),
            ('ap_access', 'Access Point', plat_iq),
        ]:
            d = Device.objects.create(
                name=f'{PREFIX}{key}',
                device_type=dtype,
                role=roles[role_name],
                site=site,
                platform=platform,
                status='active',
            )
            attach(d, next_ip())
            objects[key] = d

        fortigate = Device.objects.create(
            name=f'{PREFIX}fortigate',
            device_type=dtype,
            role=roles[_FIREWALL_ROLE],
            site=site,
            platform=plat_fortios,
            status='active',
        )
        attach(fortigate, next_ip())
        _step_fortios_platform_macros(server)

        with ZabbixConnection(server) as api:
            access_macros = patch_access_port_scope_host_macros(api)
            record(
                'access_host_macros',
                access_macros.get('status') in ('ok', 'no-devices', 'no-role'),
                str(access_macros),
                group='import',
            )
            fabric_macros = patch_voss_fabric_pair_host_macros(api)
            record(
                'voss_fabric_pair_macros',
                fabric_macros.get('status') in ('ok', 'no-pairs'),
                str(fabric_macros),
                group='import',
            )

        # --- Resolve asserts (NetBox side, like zerotouch) ---
        def cg_name(obj):
            a = get_assigned_zabbixobjects(obj)
            cg = a.get('configurationgroup')
            return cg.zabbixconfigurationgroup.name if cg else None

        def tpl_names(obj):
            a = get_assigned_zabbixobjects(obj)
            return sorted(t.zabbixtemplate.name for t in (a.get('templates') or []) if getattr(t, 'zabbixtemplate', None))

        def macro_map(obj):
            a = get_assigned_zabbixobjects(obj)
            out = {}
            for ma in a.get('macros') or []:
                rendered, _ = ma.render(object=obj)
                out[str(ma)] = rendered
            return out

        record('voss_core_cg_snmp', cg_name(objects['voss_core']) == snmp_group.name, cg_name(objects['voss_core']), group='resolve')
        record(
            'voss_core_template',
            any('Extreme VOSS' in n for n in tpl_names(objects['voss_core'])) and not any('Network Generic' in n for n in tpl_names(objects['voss_core'])),
            str(tpl_names(objects['voss_core'])),
            group='resolve',
        )
        record(
            'exos_core_template',
            any('EXOS' in n for n in tpl_names(objects['exos_core'])) and not any('Network Generic' in n for n in tpl_names(objects['exos_core'])),
            str(tpl_names(objects['exos_core'])),
            group='resolve',
        )
        record(
            'dist_macros_equal_core',
            ROLE_MACROS['Switch Dist'] == CORE_LIKE_IF_MACROS and ROLE_MACROS['Switch Mgmt'] == CORE_LIKE_IF_MACROS,
            str(ROLE_MACROS['Switch Dist']),
            group='resolve',
        )
        m_core = macro_map(objects['voss_core'])
        record('core_ifalias_matches', m_core.get('{$NET.IF.IFALIAS.MATCHES}') == '.*', str(m_core), group='resolve')
        record('core_ifalias_not_matches_x_only', m_core.get('{$NET.IF.IFALIAS.NOT_MATCHES}') == '^X(-|$)', str(m_core), group='resolve')
        m_dist = macro_map(objects['voss_dist'])
        record(
            'dist_ifalias_like_core_all_ports',
            m_dist.get('{$NET.IF.IFALIAS.MATCHES}') == '.*' and m_dist.get('{$NET.IF.IFALIAS.NOT_MATCHES}') == '^X(-|$)',
            str(m_dist),
            group='resolve',
        )
        m_acc = macro_map(objects['voss_access'])
        record(
            'access_ifalias_grammar_classes',
            m_acc.get('{$NET.IF.IFALIAS.MATCHES}') == ACCESS_IFALIAS_MATCHES,
            str(m_acc),
            group='resolve',
        )
        record(
            'access_portid_speed_classes',
            m_acc.get('{$PORTID.LLD.IFALIAS.MATCHES}') == ACCESS_PORTID_MATCHES,
            str(m_acc),
            group='resolve',
        )
        record(
            'access_linkdown_ifalias_default_off',
            m_acc.get(_LINKDOWN_IFALIAS_MACRO) == _LINKDOWN_IFALIAS_ACCESS_DEFAULT,
            str(m_acc),
            group='resolve',
        )
        record(
            'access_linkdown_ifalias_grammar_regex',
            m_acc.get(_linkdown_ifalias_regex_macro()) == '1',
            str(m_acc),
            group='resolve',
        )
        record(
            'core_linkdown_ifalias_not_forced',
            _LINKDOWN_IFALIAS_MACRO not in m_core,
            str(m_core),
            group='resolve',
        )
        m_fw = macro_map(fortigate)
        record(
            'firewall_https_not_http_80',
            m_fw.get('{$FGATE.SCHEME}') == 'https' and m_fw.get('{$FGATE.API.PORT}') == _FGATE_API_PORT,
            str(m_fw),
            group='resolve',
        )
        record(
            'firewall_ifname_lld_open',
            m_fw.get('{$NET.IF.IFNAME.MATCHES}') == '.*'
            and m_fw.get('{$NET.IF.IFNAME.NOT_MATCHES}') == 'CHANGE_IF_NEEDED',
            str(m_fw),
            group='resolve',
        )
        record(
            'firewall_ha_expected_pair',
            m_fw.get('{$FGATE.HA.EXPECTED}') == '2',
            str(m_fw),
            group='resolve',
        )
        record(
            'firewall_no_policy_lld',
            m_fw.get('{$FWP.FWNAME.MATCHES}') == '^$',
            str(m_fw),
            group='resolve',
        )
        want_fqdn = _nb_ip_addr(fortigate.primary_ip4)
        record(
            'firewall_fqdn_from_platform_jinja',
            m_fw.get('{$FGATE.API.FQDN}') == want_fqdn,
            f'got={m_fw.get("{$FGATE.API.FQDN}")!r} want={want_fqdn!r}',
            group='resolve',
        )
        role_fqdn = M.ZabbixMacroAssignment.objects.filter(
            zabbixmacro__macro=_FGATE_FQDN_MACRO,
            assigned_object_type=ct(DeviceRole),
            assigned_object_id=roles[_FIREWALL_ROLE].id,
        ).exists()
        device_fqdn = M.ZabbixMacroAssignment.objects.filter(
            zabbixmacro__macro=_FGATE_FQDN_MACRO,
            assigned_object_type=ct(Device),
            assigned_object_id=fortigate.id,
        ).exists()
        plat_fqdn = M.ZabbixMacroAssignment.objects.filter(
            zabbixmacro__macro=_FGATE_FQDN_MACRO,
            assigned_object_type=ct(Platform),
            assigned_object_id=plat_fortios.id,
        ).first()
        record(
            'firewall_fqdn_not_on_role_or_device',
            (not role_fqdn and not device_fqdn and plat_fqdn is not None
             and plat_fqdn.value == _FGATE_FQDN_JINJA),
            f'role={role_fqdn} device={device_fqdn} plat={getattr(plat_fqdn, "value", None)!r}',
            group='resolve',
        )
        record(
            'switch_core_has_no_fgate_scheme',
            '{$FGATE.SCHEME}' not in m_core,
            str(m_core),
            group='resolve',
        )
        def rule_templates(canonical: str) -> list[str]:
            names = ztc.template_rule_names(server, canonical, **_rule_kwargs())
            return list(
                template_rules_for_server(server)
                .filter(name__in=names)
                .values_list('zabbixtemplate__name', flat=True)
            )

        voss_tpls = rule_templates('Extreme VOSS')
        record(
            'voss_rule_not_netgeneric',
            any(n and 'Network Generic' not in n for n in voss_tpls),
            str(voss_tpls),
            group='resolve',
        )
        iq_tpls = rule_templates('Extreme IQ Engine')
        record(
            'iq_rule_not_netgeneric',
            any(n and 'Network Generic' not in n for n in iq_tpls),
            str(iq_tpls),
            group='resolve',
        )
        record(
            'ap_template_iq_engine',
            any('IQ Engine' in n for n in tpl_names(objects['ap_access'])) and not any('Network Generic' in n for n in tpl_names(objects['ap_access'])),
            str(tpl_names(objects['ap_access'])),
            group='resolve',
        )
        exos_tpls = rule_templates('Extreme EXOS')
        record(
            'exos_rule_exists',
            any(n and 'Network Generic' not in n for n in exos_tpls),
            str(exos_tpls),
            group='resolve',
        )

        # --- Sync + Zabbix asserts ---
        with ZabbixConnection(server) as api:
            for key, obj in objects.items():
                try:
                    SyncHostJob(instance=obj).run()
                    record(f'sync_{key}', True, obj.name, group='sync')
                except Exception as exc:
                    record(f'sync_{key}', False, f'{exc}\n{traceback.format_exc()[-400:]}', group='sync')

            def host(name):
                found = api.host.get(
                    filter={'host': name},
                    selectInterfaces='extend',
                    selectParentTemplates=['name'],
                    selectGroups=['name'],
                    selectMacros='extend',
                )
                return found[0] if found else None

            h = host(objects['voss_core'].name)
            record('zbx_voss_core_exists', bool(h), objects['voss_core'].name, group='zabbix')
            if h:
                ok, detail = assert_effective_if_util(api, h['hostid'])
                record('zbx_voss_core_effective_util_off', ok, detail, group='zabbix')
            if h:
                tpls = [t.get('name') for t in h.get('parentTemplates', [])]
                record(
                    'zbx_voss_no_netgeneric',
                    any('VOSS' in (n or '') for n in tpls) and not any('Network Generic' in (n or '') for n in tpls),
                    str(tpls),
                    group='zabbix',
                )

                def host_macros(host_obj):
                    # Secret macros omit value in API responses — never use m['value'].
                    out = {}
                    for m in host_obj.get('macros') or []:
                        if isinstance(m, dict) and 'macro' in m:
                            out[m['macro']] = m.get('value', '')
                    return out

                macros = host_macros(h)
                record('zbx_core_macro_x_exclude', macros.get('{$NET.IF.IFALIAS.NOT_MATCHES}') == '^X(-|$)', str(macros), group='zabbix')
                record('zbx_core_macro_matches_all', macros.get('{$NET.IF.IFALIAS.MATCHES}') == '.*', str(macros), group='zabbix')
                ifs = [i for i in h.get('interfaces', []) if str(i.get('type')) == '2']
                record('zbx_snmp_if', bool(ifs), str(h.get('interfaces')), group='zabbix')
                ping = api.item.get(hostids=h['hostid'], filter={'key_': 'icmpping'}, output=['key_'])
                record('zbx_single_icmpping', len(ping) <= 1, f'count={len(ping)}', group='zabbix')

            for dist_key in ('voss_dist', 'exos_dist'):
                h_d = host(objects[dist_key].name)
                if h_d:
                    macros = {m['macro']: m.get('value', '') for m in (h_d.get('macros') or []) if isinstance(m, dict) and 'macro' in m}
                    record(
                        f'zbx_{dist_key}_ifalias_like_core',
                        macros.get('{$NET.IF.IFALIAS.MATCHES}') == '.*' and macros.get('{$NET.IF.IFALIAS.NOT_MATCHES}') == '^X(-|$)',
                        str(macros),
                        group='zabbix',
                    )

            h_a = host(objects['voss_access'].name)
            if h_a:
                ok, detail = assert_effective_if_util(api, h_a['hostid'])
                record('zbx_voss_access_effective_util_off', ok, detail, group='zabbix')
                macros = {m['macro']: m.get('value', '') for m in (h_a.get('macros') or []) if isinstance(m, dict) and 'macro' in m}
                record(
                    'zbx_access_ifalias_grammar_classes',
                    macros.get('{$NET.IF.IFALIAS.MATCHES}') == ACCESS_IFALIAS_MATCHES,
                    str(macros),
                    group='zabbix',
                )
                record(
                    'zbx_access_portid_speed_classes',
                    macros.get('{$PORTID.LLD.IFALIAS.MATCHES}') == ACCESS_PORTID_MATCHES,
                    str(macros),
                    group='zabbix',
                )
                record(
                    'zbx_access_linkdown_ifalias_off',
                    macros.get(_LINKDOWN_IFALIAS_MACRO) == _LINKDOWN_IFALIAS_ACCESS_DEFAULT,
                    str(macros),
                    group='zabbix',
                )
                record(
                    'zbx_access_linkdown_ifalias_grammar',
                    macros.get(_linkdown_ifalias_regex_macro()) == '1',
                    str(macros),
                    group='zabbix',
                )

            h_e = host(objects['exos_core'].name)
            if h_e:
                tpls = [t.get('name') for t in h_e.get('parentTemplates', [])]
                record('zbx_exos_template', any('EXOS' in (n or '') for n in tpls), str(tpls), group='zabbix')
                ok, detail = assert_effective_if_util(api, h_e['hostid'])
                record('zbx_exos_core_effective_util_off', ok, detail, group='zabbix')

            h_ap = host(objects['ap_access'].name)
            record('zbx_ap_exists', bool(h_ap), objects['ap_access'].name, group='zabbix')
            if h_ap:
                tpls = [t.get('name') for t in h_ap.get('parentTemplates', [])]
                record(
                    'zbx_ap_iq_template',
                    any('IQ Engine' in (n or '') for n in tpls) and not any('Network Generic' in (n or '') for n in tpls),
                    str(tpls),
                    group='zabbix',
                )

            gmacros = {m['macro']: m.get('value', '') for m in (api.usermacro.get(globalmacro=True, output='extend') or []) if isinstance(m, dict) and 'macro' in m}
            expect_mlt = GLOBAL_MACROS['{$MLT.CONTROL}']
            record('zbx_global_util_off', gmacros.get('{$IF.UTIL.MAX}') == '101', gmacros.get('{$IF.UTIL.MAX}'), group='zabbix')
            record('zbx_global_mlt_control', gmacros.get('{$MLT.CONTROL}') == expect_mlt, gmacros.get('{$MLT.CONTROL}'), group='zabbix')
            record(
                'zbx_global_no_portid',
                '{$PORTID.LLD.IFALIAS.MATCHES}' not in gmacros and '{$PORTID.LLD.IFTYPE.MATCHES}' not in gmacros,
                str({k: gmacros[k] for k in gmacros if k.startswith('{$PORTID.')}),
                group='zabbix',
            )
            # TEMP_* are template-only (EXOS/VOSS). Asserted earlier as template_temp_assert_*.

        passed = sum(1 for r in RESULTS if r['ok'])
        total = len(RESULTS)
        REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        REPORT_JSON.write_text(json.dumps({'summary': {'passed': passed, 'total': total}, 'results': RESULTS}, indent=2))
        lines = [
            '# Network nbxSync simulation report',
            '',
            f'**Score:** {passed}/{total}',
            '',
            'Aligned with `configure_nbxsync_zerotouch.py` (`ensure`, TemplateRules, SyncHostJob, PREFIX lab).',
            '',
            '| Group | Case | Result | Detail |',
            '|---|---|---|---|',
        ]
        for r in RESULTS:
            lines.append(f"| {r['group']} | `{r['name']}` | {'PASS' if r['ok'] else 'FAIL'} | {str(r['detail'])[:120].replace('|', '/')} |")
        REPORT_MD.write_text('\n'.join(lines) + '\n')
        print(f'\nSummary: {passed}/{total} — {REPORT_MD}')
        return 0 if passed == total else 1
    finally:
        globals()['get_role'] = orig_get_role


PROD_SERVER_NAME = 'Zabbix Production'


def _assert_server_url_ready(server, expected_url: str | None = None) -> None:
    url = (getattr(server, 'url', None) or '').strip()
    if not url:
        raise SystemExit(
            f'ZabbixServer {server.name!r} has an empty URL — set NBX_ZABBIX_URL before --apply'
        )
    if expected_url and url.rstrip('/') != expected_url.rstrip('/'):
        raise SystemExit(
            f'ZabbixServer {server.name!r} url={url!r} does not match '
            f'NBX_ZABBIX_URL={expected_url!r} — refusing API mutations'
        )


def resolve_apply_zabbix_server(*, token: str):
    """Select the --apply target. Never fall back to an arbitrary ZabbixServer.objects.first()."""
    env_url = (os.environ.get('NBX_ZABBIX_URL') or '').strip() or None
    named = M.ZabbixServer.objects.filter(name=PROD_SERVER_NAME).first()
    if named is None:
        if not env_url:
            raise SystemExit(
                f'No ZabbixServer named {PROD_SERVER_NAME!r}. Set NBX_ZABBIX_URL to create '
                'or select the target server by URL. Refusing arbitrary ZabbixServer.objects.first().'
            )
        matches = list(M.ZabbixServer.objects.filter(url=env_url))
        if len(matches) > 1:
            names = ', '.join(sorted(row.name for row in matches))
            raise SystemExit(
                f'Multiple ZabbixServer rows use NBX_ZABBIX_URL={env_url!r}: {names}. '
                f'Rename so exactly one is {PROD_SERVER_NAME!r} or unique by URL.'
            )
        if len(matches) == 1:
            server = matches[0]
            server.token = token
            server.save(update_fields=['token'])
            logger.warning(
                'No ZabbixServer named %r; using existing row %r with matching NBX_ZABBIX_URL',
                PROD_SERVER_NAME,
                server.name,
            )
        else:
            server = M.ZabbixServer.objects.create(
                name=PROD_SERVER_NAME,
                url=env_url,
                token=token,
                validate_certs=not env_url.startswith('http://'),
                sync_enabled=True,
            )
            logger.info('  CREATED ZabbixServer %s url=%s', server.name, server.url)
        _assert_server_url_ready(server, expected_url=env_url)
        return server

    named.token = token
    update_fields = ['token']
    if env_url:
        named.url = env_url
        update_fields.append('url')
    named.save(update_fields=update_fields)
    _assert_server_url_ready(named, expected_url=env_url)
    return named


def run_apply(*, link_speed_expect: bool = False, cutover_silence: bool = False) -> int:
    """Apply network deltas on the production / shared ZabbixServer row."""
    apply_macro_mode(cutover_silence=cutover_silence)
    if cutover_silence:
        logger.warning('CUTOVER-SILENCE IS ENABLED — EXOS/VOSS TEMP_* set to 999, MLT/optic floors muted.')
        logger.warning('This is a temporary LM migration overlay. Re-run without --cutover-silence to restore destination values.')
    token = os.environ.get('NBX_ZABBIX_TOKEN')
    if not token:
        raise SystemExit('Set NBX_ZABBIX_TOKEN (or use --simulate)')
    server = resolve_apply_zabbix_server(token=token)

    with ZabbixConnection(server) as api:
        imported = import_extreme_templates(api)
        step_global_macros_zabbix(api)
        patch_etherlike_ifalias_filters(api)
        patch_exos_interface_lld_rollout(api)
        patch_ifname_skip_chassis_oob(api)
        queue_oob_if_lld_checks(api)
        patch_exos_psu_lld_present_only(api)
        queue_exos_psu_lld_checks(api)
        patch_voss_psu_lld_present_only(api)
        queue_voss_psu_lld_checks(api)
        patch_psu_not_up(api)
        patch_linkdown_one_average(api)
        patch_extreme_template_temp_macros(api)
        patch_extreme_template_util_macros(api)
        step_health_patches(api)
        patch_ascii_trigger_titles(api)
    tpl_models = {name: ensure_nbx_template(server, tid, name) for name, (tid, name) in imported.items()}
    step_server_macros(server)
    step_role_macros(server)
    with ZabbixConnection(server) as api:
        patch_access_port_scope_host_macros(api)
        patch_voss_fabric_pair_host_macros(api)
    report_hosts_needing_macro_sync(server)
    step_template_rules(server, tpl_models)
    step_speed_expect_assignment(server, tpl_models, link=link_speed_expect)
    logger.info('Network configuration applied (macros=%s)', 'cutover-silence' if cutover_silence else 'destination')
    logger.info(
        'FortiOS platform FortiGate HTTP macros are NetBox assignments only '
        '(https/%s, WAN/HA/mgmt LLD, CPU/mem CRIT 101). Zabbix monitoring TOKEN '
        'stays on Platform FortiOS; %s is reserved for inventory automation. '
        'FQDN is platform Jinja on primary_ip4. This run does not HostSync Fortis '
        'and does not retarget FortiOS. Use --apply-fortigate-http for the HTTP '
        'cutover without zerotouch.',
        _FGATE_API_PORT,
        _FGATE_AUTOMATION_TOKEN_ENV,
    )
    return 0


def run_apply_firewall_macros() -> int:
    """NetBox-only: ZabbixMacroAssignment on Platform FortiOS.

    Does not import Extreme YAML, does not call the Zabbix API, does not
    HostSync Fortis, and does not retarget FortiOS.
    """
    token = os.environ.get('NBX_ZABBIX_TOKEN')
    if not token:
        raise SystemExit('Set NBX_ZABBIX_TOKEN (or use --simulate)')
    server = resolve_apply_zabbix_server(token=token)
    _step_fortios_platform_macros(server, required=True)
    logger.info(
        'FortiOS platform FortiGate HTTP macros written '
        '(https/%s, WAN/HA/mgmt LLD, CPU/mem CRIT 101). Existing NetBox '
        '%s monitoring assignment is preserved. %s is platform Jinja on primary_ip4. '
        'No Extreme import, no HostSync, no FortiOS retarget. '
        'Use --apply-fortigate-http for the companion cutover.',
        _FGATE_API_PORT,
        _FGATE_TOKEN_MACRO,
        _FGATE_FQDN_MACRO,
    )
    return 0


def _require_fortigate_http_preflight(*, server=None):
    """Run the complete read-only cutover gate and return resolved objects."""
    if server is None:
        token = os.environ.get('NBX_ZABBIX_TOKEN')
        if not token:
            raise SystemExit('Set NBX_ZABBIX_TOKEN')
        server = resolve_apply_zabbix_server(token=token)
    with ZabbixConnection(server) as api:
        http = import_fortigate_http_template(api)
        snmp = _lookup_zabbix_template(api, _FORTIGATE_SNMP_TEMPLATE)
        icmp = _lookup_zabbix_template(api, _ICMP_PING_TEMPLATE)
        zbx_errors, scripts = _preflight_fortigate_http_zabbix(api, http[0])
    errors = zbx_errors + _preflight_fortigate_http(server, icmp_ok=icmp is not None)
    _print_fortigate_http_plan(
        server,
        scripts=scripts,
        icmp_ok=icmp is not None,
        errors=errors,
    )
    if errors:
        for error in errors:
            logger.error('  preflight: %s', error)
        raise SystemExit('FortiGate HTTP preflight failed — no writes:\n  ' + '\n  '.join(errors))
    return server, http, snmp, icmp


def run_check_fortigate_http() -> int:
    """Check NetBox automation access, monitoring-token presence, and Zabbix state."""
    server = M.ZabbixServer.objects.filter(name=PROD_SERVER_NAME).first()
    if server is None:
        raise SystemExit(f'No ZabbixServer named {PROD_SERVER_NAME!r} configured in NetBox')
    _require_fortigate_http_preflight(server=server)
    logger.info('FortiGate HTTP preflight OK — check-only mode wrote nothing')
    return 0


def run_apply_fortigate_http() -> int:
    """FortiGate HTTP cutover without zerotouch or Extreme YAML. Fail closed.

    Looks up Cloud FortiGate by HTTP (**Zabbix, 7.0-2**), applies bounded
    ZBX-27082 and multi-VDOM collector compatibility fixes, imports FortiGate
    Observability, and retargets **FortiOS only**. Does not assign Forti
    templates or the REST token on role Firewall.
    """
    server = M.ZabbixServer.objects.filter(name=PROD_SERVER_NAME).first()
    if server is None:
        raise SystemExit(f'No ZabbixServer named {PROD_SERVER_NAME!r} configured in NetBox')
    server, http, snmp, icmp = _require_fortigate_http_preflight(server=server)
    logger.info('Preflight OK — patching Cloud HTTP, importing Observability, writing FortiOS levers')

    with ZabbixConnection(server) as api:
        apply_fortigate_http_patches(api, http[0])
        observability = import_fortigate_observability_template(api)
        ensure_overlay_census_items(api, observability[0])
        ensure_observability_trigger_dependencies(api, observability[0])
        ensure_observability_primary_trigger_gates(api, observability[0])

    _step_fortios_platform_macros(server, required=True)
    _step_fortigate_http_nbxsync(
        server,
        observability=observability,
        http=http,
        snmp=snmp,
        icmp=icmp,
    )
    _step_fortigate_http_transport(server)
    _step_fortios_device_macros(server)
    logger.info(
        'FortiGate HTTP cutover written in NetBox. No HostSync. '
        'Shared %s is on Platform FortiOS (not role Firewall). '
        '%s is platform Jinja on primary_ip4. '
        'FortiOS winning CG is %s (not %s). FMG/FAZ platforms keep %s. '
        'Leftover ICMP/HTTP/SNMP template rows on FortiOS objects are pruned; agent CGs are not. '
        'HostSync both members of the first cluster, then the rest. '
        'Do not re-run zerotouch — it still floors FortiOS on %s.',
        _FGATE_TOKEN_MACRO,
        _FGATE_FQDN_MACRO,
        _FORTIGATE_HTTP_CG,
        _AGENT_MONITORING_CG,
        _SNMP_MONITORING_CG,
        _FORTIGATE_SNMP_TEMPLATE,
    )
    return 0


def _cato_rpc(server):
    """JSON-RPC helper used by the Cato pack (not zabbix_utils object methods)."""
    from zabbix_api import ZabbixAPI

    return ZabbixAPI(server.url, token=server.token)


def _print_cato_plan(*, errors: list[str], apply: bool) -> None:
    from cato_http import (
        CATO_API_KEY_ENV,
        CATO_API_URL,
        collector_host,
        collector_visible_name,
        default_account_id,
    )

    logger.info('=' * 60)
    logger.info('Cato collector proposed writes (nothing written yet)' if apply else 'Cato collector check (read-only)')
    logger.info('=' * 60)
    logger.info('GraphQL preflight: %s account %s', CATO_API_URL, default_account_id())
    logger.info('Token source: %s (never printed)', CATO_API_KEY_ENV)
    logger.info('Zabbix host: %s (%s)', collector_host(), collector_visible_name())
    logger.info('Import template from %s', CATO_HTTP_YAML)
    logger.info('No HostSync, no Extreme import, no Socket role mutation, no zerotouch')
    if errors:
        logger.info('Preflight errors (%s) — abort, no writes:', len(errors))
        for err in errors:
            logger.info('  %s', err)


def _require_cato_preflight(*, server=None, apply: bool = True):
    """Fail-closed GraphQL gate. Does not import YAML or touch Socket hosts."""
    from cato_http import preflight_cato_graphql

    if server is None:
        server = M.ZabbixServer.objects.filter(name=PROD_SERVER_NAME).first()
        if server is None:
            raise SystemExit(f'No ZabbixServer named {PROD_SERVER_NAME!r} configured in NetBox')
    errors = preflight_cato_graphql()
    _print_cato_plan(errors=errors, apply=apply)
    if errors:
        for error in errors:
            logger.error('  preflight: %s', error)
        raise SystemExit('Cato GraphQL preflight failed — no writes:\n  ' + '\n  '.join(errors))
    return server


def run_check_cato() -> int:
    """Read-only Cato GraphQL preflight plus collector host/template shape."""
    from configure_cato_zabbix import _all_pass, verify_account_host
    from cato_http import collector_host
    from configure_cato_zabbix import _exact_template, _get_host, _template_pack_checks

    server = M.ZabbixServer.objects.filter(name=PROD_SERVER_NAME).first()
    if server is None:
        raise SystemExit(f'No ZabbixServer named {PROD_SERVER_NAME!r} configured in NetBox')
    _require_cato_preflight(server=server, apply=False)
    api = _cato_rpc(server)
    template = _exact_template(api)
    if template is None:
        logger.info('Cato template not imported yet — preflight OK, nothing else to check')
        return 0
    collector = _get_host(api, collector_host())
    if collector is None:
        records = _template_pack_checks(api, str(template['templateid']))
        logger.info('Cato template present; collector host not created yet')
        return 0 if _all_pass(records) else 1
    records = verify_account_host(api, str(collector['hostid']))
    logger.info('Cato collector check OK — wrote nothing')
    return 0 if _all_pass(records) else 1


def run_apply_cato() -> int:
    """Refresh the Cato account collector without zerotouch or HostSync."""
    from configure_cato_zabbix import _all_pass, apply_cato_pack
    from cato_http import CATO_API_KEY_ENV, CATO_PROXY_GROUP_ENV

    server = M.ZabbixServer.objects.filter(name=PROD_SERVER_NAME).first()
    if server is None:
        raise SystemExit(f'No ZabbixServer named {PROD_SERVER_NAME!r} configured in NetBox')
    api_token = (os.environ.get(CATO_API_KEY_ENV) or '').strip()
    if not api_token:
        raise SystemExit(f'Set {CATO_API_KEY_ENV} for --apply-cato')
    server = _require_cato_preflight(server=server)
    logger.info('Preflight OK — importing Cato template and converging the account host')
    api = _cato_rpc(server)
    records = apply_cato_pack(
        api,
        api_token,
        proxy_group=os.environ.get(CATO_PROXY_GROUP_ENV) or None,
    )
    if not _all_pass(records):
        raise SystemExit('Cato collector apply verification failed')
    logger.info(
        'Cato collector written. No HostSync. No Socket role change. '
        'Do not re-run zerotouch to refresh this pack.'
    )
    return 0


def run_zabbix_only(*, link_speed_expect: bool = False) -> int:
    """Fallback smoke without NetBox object graph — delegates to run_network_zabbix_sim."""
    from run_network_zabbix_sim import main as sim_main

    argv = ['run_network_zabbix_sim.py']
    if link_speed_expect:
        argv.append('--with-speed-expect')
    sys.argv = argv
    return sim_main()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--simulate', action='store_true', help='Lab: NetBox estate + SyncHostJob + Zabbix asserts')
    mode.add_argument('--zabbix-only', action='store_true', help='Zabbix API smoke only (no NetBox graph)')
    mode.add_argument('--apply', action='store_true', help='Apply network deltas (needs NBX_ZABBIX_TOKEN)')
    mode.add_argument(
        '--apply-firewall-macros',
        action='store_true',
        help='NetBox-only: FortiGate HTTP macros on Platform FortiOS (no Extreme import, no HostSync, no FortiOS retarget)',
    )
    mode.add_argument(
        '--apply-fortigate-http',
        action='store_true',
        help='FortiGate HTTP cutover: FortiOS Observability companion, fail-closed preflight, no Firewall-role Forti templates, no HostSync',
    )
    mode.add_argument(
        '--check-fortigate-http',
        action='store_true',
        help='Read-only FortiGate HTTP preflight: Zabbix parent + every FortiOS API endpoint/token',
    )
    mode.add_argument(
        '--apply-cato',
        action='store_true',
        help='Cato collector refresh: GraphQL preflight, import Cato Networks by HTTP, converge account host; no HostSync, no zerotouch',
    )
    mode.add_argument(
        '--check-cato',
        action='store_true',
        help='Read-only Cato GraphQL preflight and collector host/template shape; no writes',
    )
    parser.add_argument('--link-speed-expect', action='store_true', help='Also assign Port Speed Expect on Switch roles (avoid if already nested on VOSS/Observability)')
    parser.add_argument(
        '--cutover-silence',
        action='store_true',
        help='Temporary LM-migration overlay (TEMP/OPTIC=999, MLT=0). Default is destination end-state.',
    )
    args = parser.parse_args()
    if args.simulate:
        return run_simulate(link_speed_expect=args.link_speed_expect, cutover_silence=args.cutover_silence)
    if args.zabbix_only:
        return run_zabbix_only(link_speed_expect=args.link_speed_expect)
    if args.apply_firewall_macros:
        if args.link_speed_expect or args.cutover_silence:
            raise SystemExit('--apply-firewall-macros does not take --link-speed-expect or --cutover-silence')
        return run_apply_firewall_macros()
    if args.check_fortigate_http:
        if args.link_speed_expect or args.cutover_silence:
            raise SystemExit('--check-fortigate-http does not take --link-speed-expect or --cutover-silence')
        return run_check_fortigate_http()
    if args.apply_fortigate_http:
        if args.link_speed_expect or args.cutover_silence:
            raise SystemExit('--apply-fortigate-http does not take --link-speed-expect or --cutover-silence')
        return run_apply_fortigate_http()
    if args.check_cato:
        if args.link_speed_expect or args.cutover_silence:
            raise SystemExit('--check-cato does not take --link-speed-expect or --cutover-silence')
        return run_check_cato()
    if args.apply_cato:
        if args.link_speed_expect or args.cutover_silence:
            raise SystemExit('--apply-cato does not take --link-speed-expect or --cutover-silence')
        return run_apply_cato()
    return run_apply(link_speed_expect=args.link_speed_expect, cutover_silence=args.cutover_silence)


if __name__ == '__main__':
    raise SystemExit(main())
