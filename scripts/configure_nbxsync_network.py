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
  * Patch stock EXOS ``psu.discovery`` to skip ``notPresent`` stack-MIB padding and queue check-now discovery for stale rows (no fork, no host sync)
  * Discovered link-down stays **Average** (drop leftover USW High if a prior apply created it)
  * Override stock Extreme EXOS/VOSS template ``{$TEMP_*}`` macros (stock 55/65 wins over globals)
  * Disable ICMP loss/RTT triggers on EXOS/VOSS/IQ (items stay for Health; CH proxy RTT is WAN)
  * Health dashboards ship in YAML (VOSS/IQ + EXOS Observability companion). ``--apply`` patches the stock EXOS **Network interfaces** Overview + Port layout and drops leftover Health Diagnostics pages.
  * Platform TemplateRules: EXOS → Observability companion (nests stock); VOSS / IQ Engine → Extreme * by SNMP
  * Switch role IFALIAS / IFTYPE macros via ZabbixMacroAssignment (inheritance resolves these)
  * Global **destination** macros on the Zabbix server object (production end-state).
    ``{$PORTID.LLD.*}`` defaults live on Extreme Port Speed Expect — not globals.
  * Optional ``--cutover-silence`` overlay (999 / MLT=0) for temporary LM migration only
  * Optional Speed Expect **role** assignment (``--link-speed-expect``). Prefer nesting
    on VOSS / EXOS Observability so unlabeled ports stay silent and labels start
    working on the next LLD without HostSync. Do not also role-assign if nested
    (Zabbix rejects a template linked both directly and through a parent).

Stage matrix (what each flag enables):
  ``--apply``                     = stages 0–3: template imports + EXOS/VOSS/IQ rules + IFALIAS + destination globals + TEMP/ICMP/Health patches.
                                    Speed Expect is nested on VOSS and EXOS Observability (empty ifAlias = not discovered).
  ``--apply --link-speed-expect`` = extra NetBox role assignment. Skip while nested — duplicate link on HostSync.
  ``--apply --cutover-silence``   = cutover overlay: TEMP/OPTIC=999, MLT/VIST=0 (temporary, re-run without to restore)
  Routing / Stage 6 context macros = manual (Extreme switching page)

Re-apply safety (estate already has switches/APs in Zabbix):
  * Does **not** delete hosts, interfaces, history, or hostids
  * Does **not** mass-sync every device (template updates inherit in Zabbix)
  * After role macros, logs Switch* hosts whose Zabbix host macros differ from
    NetBox role assignments (not every active Switch*). Does not mass-sync.
  * YAML ``deleteMissing: false`` — retired items linger; LLD is not wiped
  * ``--apply`` without ``--link-speed-expect`` does **not** unlink a leftover role assignment
    (Speed Expect is nested on the platform templates; skip the flag).
  * Empty SNMP secrets are zerotouch's job and must not blank existing CG passphrases

Import policy:
  YAML imports use deleteMissing=False (safe — retired items linger but templates don't lose content).
  Re-run ``--apply`` after Extreme template upgrades to re-assert TEMP/EtherLike/ICMP/Health patches.
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
)
from nbxsync.jobs.synchost import SyncHostJob
from nbxsync.utils import get_assigned_zabbixobjects
from nbxsync.utils.zabbixconnection import ZabbixConnection

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

# Role → port-scoping macros (zabbix/01-extreme-switching.md).
# Core / Dist / Mgmt = every admin-up ethernet/LAG except X*.
# Access = USW (to Dist) and UP (to AP) only — no desk/laptop/US/MON/UW/TMON.
# There is no Switch Hybrid role.
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
        '{$NET.IF.IFALIAS.MATCHES}': '^(USW|UP)(-|$)',
        '{$NET.IF.IFALIAS.NOT_MATCHES}': 'CHANGE_IF_NEEDED',
        '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
        # Speed Expect uses PORTID.* not NET.IF.* — override or US/MON leak in.
        '{$PORTID.LLD.IFALIAS.MATCHES}': '^(USW|UP)(-|$)',
    },
}

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
    '{$MLT.CONTROL}': '1',  # .diff() keeps unused/disabled MLTs quiet
    '{$VIST.CONTROL}': '0',  # set host macro =1 on VOSS fabric pairs
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


def import_extreme_templates(api) -> dict[str, tuple[int, str]]:
    """Import YAML templates; return name → (templateid, name)."""
    out: dict[str, tuple[int, str]] = {}
    for name, path in TEMPLATE_FILES.items():
        if not path.exists():
            logger.error('Missing template file: %s', path)
            continue
        import_error = None
        try:
            api.configuration.import_(
                format='yaml',
                rules=import_rules(),
                source=path.read_text(),
            )
        except Exception as exc:
            import_error = exc
            logger.warning('  Import failed for %s; checking for an existing exact template: %s', name, exc)
        found = api.template.get(filter={'name': [name]}, output=['templateid', 'host', 'name'])
        if not found:
            # stock EXOS may already exist under another host key
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
    # Stock EXOS if present
    exos = api.template.get(filter={'name': ['Extreme EXOS by SNMP']}, output=['templateid', 'name'])
    if exos:
        out['Extreme EXOS by SNMP'] = (int(exos[0]['templateid']), 'Extreme EXOS by SNMP')
    return out


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
# Disable immediately so X-ports / empty PSU slots leave the honeycomb; delete
# after 7d (default) so rediscovery re-enables with history intact.
_LLD_DELETE_AFTER = 0
_LLD_DELETE_IMMEDIATELY = 2
_LLD_DISABLE_IMMEDIATELY = 2
_LLD_DELETE_LIFETIME = '7d'
_LLD_DISABLE_LIFETIME = '0'


def _lld_lost_resources_fields() -> dict:
    return {
        'lifetime': _LLD_DELETE_LIFETIME,
        'lifetime_type': _LLD_DELETE_AFTER,
        'enabled_lifetime': _LLD_DISABLE_LIFETIME,
        'enabled_lifetime_type': _LLD_DISABLE_IMMEDIATELY,
    }


def _lld_lost_resources_ok(rule: dict) -> bool:
    """Disable lost immediately; delete after 7d — never delete-immediately."""
    lifetime = str(rule.get('lifetime') or '')
    lifetime_type = str(rule.get('lifetime_type') if rule.get('lifetime_type') is not None else '')
    enabled = str(rule.get('enabled_lifetime') if rule.get('enabled_lifetime') is not None else '0')
    enabled_type = str(rule.get('enabled_lifetime_type') if rule.get('enabled_lifetime_type') is not None else '')
    if lifetime_type in (str(_LLD_DELETE_IMMEDIATELY), 'DELETE_IMMEDIATELY'):
        return False
    if lifetime in ('0', '0s', '0d', '0h') and lifetime_type not in ('1', 'DELETE_NEVER'):
        return False
    delete_after = lifetime in (_LLD_DELETE_LIFETIME, '7d0h', '604800') and lifetime_type in (
        '',
        str(_LLD_DELETE_AFTER),
        'DELETE_AFTER',
    )
    disable_now = enabled in ('0', '0s', '0d', '0h', '') and enabled_type in (
        '',
        str(_LLD_DISABLE_IMMEDIATELY),
        'DISABLE_IMMEDIATELY',
    )
    return delete_after and disable_now


_PSU_DISCOVERY_KEY = 'psu.discovery'
_PSU_NUMBER_OID = '1.3.6.1.4.1.1916.1.1.1.27.1.1'
_PSU_STATUS_OID = '1.3.6.1.4.1.1916.1.1.1.27.1.2'
_PSU_DISCOVERY_OID = (
    f'discovery[{{#SNMPVALUE}},{_PSU_NUMBER_OID},{{#PSU.STATUS}},{_PSU_STATUS_OID}]'
)
_PSU_STATUS_MACRO = '{#PSU.STATUS}'
_PSU_NOTPRESENT = '^1$'


def _psu_lld_skips_notpresent(rule: dict) -> bool:
    snmp_oid = str(rule.get('snmp_oid') or '')
    if '{#PSU.STATUS}' not in snmp_oid or _PSU_STATUS_OID not in snmp_oid:
        return False
    if not _lld_lost_resources_ok(rule):
        return False
    for c in (rule.get('filter') or {}).get('conditions') or []:
        if (
            c.get('macro') == _PSU_STATUS_MACRO
            and int(c.get('operator', 0)) == _LLD_NOT_MATCHES_REGEX
            and c.get('value') == _PSU_NOTPRESENT
        ):
            return True
    return False


def patch_exos_psu_lld_present_only(api, template_name: str = 'Extreme EXOS by SNMP') -> str:
    """Drop stack-MIB padding from stock EXOS PSU discovery.

    ``extremePowerSupplyTable`` has a row for every possible stack member slot.
    Stock LLD walks only the number column, so an 8-slot stack paints 32 grey
    hexes. Walk status too and skip ``notPresent(1)``. Failed/off units stay
    (``presentNotOK`` / ``presentPowerOff``). Disable lost immediately so empty
    slots leave the honeycomb on the next discovery; delete after 7d so a
    truncated walk does not wipe history. Does not fork the stock YAML.
    """
    logger.info('Network: EXOS psu.discovery present-only')
    tpls = api.template.get(filter={'name': [template_name]}, output=['templateid', 'name'])
    if not tpls:
        logger.warning('  %s: template not found — skip PSU LLD patch', template_name)
        return 'missing'
    tid = tpls[0]['templateid']
    rules = api.discoveryrule.get(
        hostids=tid,
        filter={'key_': _PSU_DISCOVERY_KEY},
        output=['itemid', 'key_', 'snmp_oid', 'lifetime', 'lifetime_type', 'enabled_lifetime', 'enabled_lifetime_type'],
        selectFilter='extend',
    )
    if not rules:
        logger.warning('  %s: no %s — skip', template_name, _PSU_DISCOVERY_KEY)
        return 'no-psu-lld'
    rule = rules[0]
    if _psu_lld_skips_notpresent(rule):
        logger.info('  %s: PSU LLD already skips notPresent', template_name)
        return 'ok'
    conditions = []
    for c in (rule.get('filter') or {}).get('conditions') or []:
        if c.get('macro') == _PSU_STATUS_MACRO:
            continue
        conditions.append(
            {
                'macro': c['macro'],
                'value': c.get('value', ''),
                'operator': int(c.get('operator', _LLD_MATCHES_REGEX)),
            }
        )
    conditions.append(
        {
            'macro': _PSU_STATUS_MACRO,
            'value': _PSU_NOTPRESENT,
            'operator': _LLD_NOT_MATCHES_REGEX,
        }
    )
    api.discoveryrule.update(
        itemid=rule['itemid'],
        snmp_oid=_PSU_DISCOVERY_OID,
        filter={'evaltype': _LLD_EVAL_AND, 'conditions': conditions},
        **_lld_lost_resources_fields(),
    )
    logger.info('  %s: patched PSU LLD to skip notPresent (itemid=%s)', template_name, rule['itemid'])
    return 'patched'


_EXOS_STOCK_TEMPLATE = 'Extreme EXOS by SNMP'
_EXOS_OBSERVABILITY_TEMPLATE = 'Extreme EXOS Observability'
_PSU_ITEM_NAME = 'Power supply status'
_CHECK_NOW_TASK_TYPE = 6


def queue_exos_psu_lld_checks(api, template_names: tuple[str, ...] | None = None) -> dict[str, int | str]:
    """Queue immediate PSU LLD checks for hosts retaining notPresent rows.

    LLD filters affect newly returned discovery data; they do not proactively
    remove already-discovered item rows. Queueing check-now tasks makes an
    apply converge immediately without host-syncing or changing NetBox.
    Hosts are selected through either the stock EXOS template or its
    Observability companion, and only hosts with a current PSU status value of
    ``1`` are queued. ``-2`` stack hosts have neither template and are skipped.
    """
    names = template_names or (_EXOS_STOCK_TEMPLATE, _EXOS_OBSERVABILITY_TEMPLATE)
    template_ids: set[str] = set()
    for name in names:
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

    stale_hosts: set[str] = set()
    ordered_hosts = sorted(host_ids)
    for start in range(0, len(ordered_hosts), 100):
        items = api.item.get(
            hostids=ordered_hosts[start:start + 100],
            search={'name': _PSU_ITEM_NAME},
            searchByAny=True,
            output=['hostid', 'lastvalue'],
        ) or []
        stale_hosts.update(
            str(item['hostid'])
            for item in items
            if str(item.get('lastvalue')) in ('1', '1.0')
        )
    if not stale_hosts:
        return {'status': 'clean', 'hosts': 0, 'tasks': 0}

    rules = []
    ordered_stale = sorted(stale_hosts)
    for start in range(0, len(ordered_stale), 100):
        rules.extend(
            api.discoveryrule.get(
                hostids=ordered_stale[start:start + 100],
                filter={'key_': [_PSU_DISCOVERY_KEY]},
                output=['itemid', 'hostid'],
            )
            or []
        )
    tasks = [
        {'type': _CHECK_NOW_TASK_TYPE, 'request': {'itemid': rule['itemid']}}
        for rule in rules
    ]
    if not tasks:
        return {'status': 'no-discovery-rules', 'hosts': len(stale_hosts), 'tasks': 0}

    task_ids: list[str] = []
    for start in range(0, len(tasks), 20):
        result = api.task.create(tasks[start:start + 20]) or {}
        task_ids.extend(str(task_id) for task_id in result.get('taskids', []))
    logger.info(
        '  EXOS PSU LLD check-now queued: hosts=%s rules=%s tasks=%s',
        len(stale_hosts),
        len(rules),
        len(task_ids),
    )
    return {'status': 'queued', 'hosts': len(stale_hosts), 'tasks': len(task_ids)}


def assert_exos_psu_lld_present_only(api, template_name: str = 'Extreme EXOS by SNMP') -> tuple[bool, str]:
    tpls = api.template.get(filter={'name': [template_name]}, output=['templateid'])
    if not tpls:
        return True, 'template absent — n/a'
    rules = api.discoveryrule.get(
        hostids=tpls[0]['templateid'],
        filter={'key_': _PSU_DISCOVERY_KEY},
        output=['itemid', 'snmp_oid', 'lifetime', 'lifetime_type', 'enabled_lifetime', 'enabled_lifetime_type'],
        selectFilter='extend',
    )
    if not rules:
        return True, 'no PSU LLD — n/a'
    ok = _psu_lld_skips_notpresent(rules[0])
    return ok, str({'snmp_oid': rules[0].get('snmp_oid'), 'filter': rules[0].get('filter')})


_LINKDOWN_HIGH_GATE = '{$LINKDOWN.HIGH:"{#IFALIAS}"}'
_LINKDOWN_HIGH_MACRO_PREFIX = '{$LINKDOWN.HIGH'
_LINKDOWN_TEMPLATES = ('Extreme EXOS by SNMP', 'Extreme VOSS by SNMP')


def _triggerproto_name(proto: dict) -> str:
    return str(proto.get('description') or proto.get('name') or '')


def _ungate_linkdown_expr(expr: str) -> str:
    out = expr
    for suffix in ('=0', '=1'):
        token = f' and {_LINKDOWN_HIGH_GATE}{suffix}'
        out = out.replace(token, '')
    return out


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
    """
    logger.info('Network: discovered link-down stays Average')
    results: dict[str, str] = {}
    for template_name in _LINKDOWN_TEMPLATES:
        tpls = api.template.get(filter={'name': [template_name]}, output=['templateid'])
        if not tpls:
            results[template_name] = 'missing'
            continue
        tid = tpls[0]['templateid']
        changed = _drop_template_macros(api, template_name, (_LINKDOWN_HIGH_MACRO_PREFIX,)) == 'patched'
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
            output=['triggerid', 'description', 'expression'],
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
            if 'Link down' not in _triggerproto_name(proto):
                continue
            expr = str(proto.get('expression') or '')
            ungated = _ungate_linkdown_expr(expr)
            if ungated != expr:
                api.triggerprototype.update(triggerid=proto['triggerid'], expression=ungated)
                changed = True
                logger.info('  %s: ungated Average link-down', template_name)
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
        output=['triggerid', 'description', 'expression'],
    ) or []
    names = [_triggerproto_name(p) for p in protos if 'Link down' in _triggerproto_name(p)]
    exprs = [str(p.get('expression') or '') for p in protos]
    ok = (
        not any('(USW)' in n for n in names)
        and not any(_LINKDOWN_HIGH_GATE in e for e in exprs)
    )
    return ok, f'linkdown={names}'


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


def step_health_patches(api) -> dict:
    """ICMP noise off + EXOS Health dashboard. Fail closed — a silent skip hid broken Health."""
    logger.info('Network: Health / ICMP-noise patches')
    return apply_extreme_health_patches(api)


def ensure_nbx_template(server, templateid: int, name: str) -> M.ZabbixTemplate:
    obj, _ = ensure(
        M.ZabbixTemplate,
        name=name,
        zabbixserver=server,
        defaults={
            'templateid': templateid,
            'interface_requirements': [HostInterfaceRequirementChoices.SNMP],
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


def step_role_macros(server) -> None:
    """ZabbixMacroAssignment on Switch* roles — what inheritance actually syncs."""
    logger.info('=' * 60)
    logger.info('Network: role IFALIAS / IFTYPE macros')
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
                zmacro, _ = ensure(
                    M.ZabbixMacro,
                    macro=macro_name,
                    assigned_object_type=ct(M.ZabbixServer),
                    assigned_object_id=server.id,
                    defaults={
                        'value': value,  # default; assignment overrides per role
                        'type': ZabbixMacroTypeChoices.TEXT,
                        'description': f'nwn:{macro_name}',
                    },
                    update_fields=['type', 'description'],
                )
                # UniqueConstraint includes value — update-in-place by macro+role+context.
                ma = M.ZabbixMacroAssignment.objects.filter(
                    zabbixmacro=zmacro,
                    assigned_object_type=ct(DeviceRole),
                    assigned_object_id=role.id,
                    context='',
                    is_regex=False,
                ).first()
                if ma is None:
                    M.ZabbixMacroAssignment.objects.create(
                        zabbixmacro=zmacro,
                        assigned_object_type=ct(DeviceRole),
                        assigned_object_id=role.id,
                        value=value,
                        context='',
                        is_regex=False,
                    )
                elif ma.value != value:
                    ma.value = value
                    ma.save(update_fields=['value'])
                logger.info('  %s %s = %s', role.name, macro_name, value)


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


def report_hosts_needing_macro_sync(server=None) -> dict:
    """Log Switch* hosts whose Zabbix host macros differ from NetBox role assignments.

    `--apply` does not HostSync. Without a live API this is a reminder, not a stale list.
    """
    role_macros_by_id: dict[int, dict[str, str]] = {}
    for canonical, macros in ROLE_MACROS.items():
        for role in resolve_roles_for_macros(canonical):
            role_macros_by_id[role.pk] = macros
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

            psu_lld_status = patch_exos_psu_lld_present_only(api)
            record(
                'exos_psu_lld_present_only',
                psu_lld_status in ('ok', 'patched', 'missing', 'no-psu-lld'),
                psu_lld_status,
                group='import',
            )
            ok, detail = assert_exos_psu_lld_present_only(api)
            record('exos_psu_lld_present_only_assert', ok or 'n/a' in detail, detail, group='import')

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

            health = step_health_patches(api)
            icmp_statuses = health.get('icmp_noise') or {}
            for tname, status in icmp_statuses.items():
                record(
                    f'icmp_noise_{tname}',
                    status in ('ok', 'patched', 'missing', 'no-triggers', 'no-names'),
                    status,
                    group='import',
                )
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
            'access_ifalias_usw_and_up_only',
            m_acc.get('{$NET.IF.IFALIAS.MATCHES}') == '^(USW|UP)(-|$)',
            str(m_acc),
            group='resolve',
        )
        record(
            'access_portid_usw_and_up_only',
            m_acc.get('{$PORTID.LLD.IFALIAS.MATCHES}') == '^(USW|UP)(-|$)',
            str(m_acc),
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
                macros = {m['macro']: m.get('value', '') for m in (h_a.get('macros') or []) if isinstance(m, dict) and 'macro' in m}
                record(
                    'zbx_access_ifalias_usw_and_up',
                    macros.get('{$NET.IF.IFALIAS.MATCHES}') == '^(USW|UP)(-|$)',
                    str(macros),
                    group='zabbix',
                )
                record(
                    'zbx_access_portid_usw_and_up',
                    macros.get('{$PORTID.LLD.IFALIAS.MATCHES}') == '^(USW|UP)(-|$)',
                    str(macros),
                    group='zabbix',
                )

            h_e = host(objects['exos_core'].name)
            if h_e:
                tpls = [t.get('name') for t in h_e.get('parentTemplates', [])]
                record('zbx_exos_template', any('EXOS' in (n or '') for n in tpls), str(tpls), group='zabbix')

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
        patch_exos_psu_lld_present_only(api)
        queue_exos_psu_lld_checks(api)
        patch_linkdown_one_average(api)
        patch_extreme_template_temp_macros(api)
        step_health_patches(api)
    tpl_models = {name: ensure_nbx_template(server, tid, name) for name, (tid, name) in imported.items()}
    step_server_macros(server)
    step_role_macros(server)
    report_hosts_needing_macro_sync(server)
    step_template_rules(server, tpl_models)
    step_speed_expect_assignment(server, tpl_models, link=link_speed_expect)
    logger.info('Network configuration applied (macros=%s)', 'cutover-silence' if cutover_silence else 'destination')
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
    return run_apply(link_speed_expect=args.link_speed_expect, cutover_silence=args.cutover_silence)


if __name__ == '__main__':
    raise SystemExit(main())
