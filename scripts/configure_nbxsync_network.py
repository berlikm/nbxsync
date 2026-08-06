#!/usr/bin/env python3
"""
nbxSync Network Configuration Script (Extreme switching)

Sibling of ``configure_nbxsync_zerotouch.py``. Same runtime shape:

  * Django + NetBox lab bootstrap
  * ``ensure()`` / ``get_or_create`` idempotent rows
  * ``--simulate`` → prefixed synthetic estate + SyncHostJob + live Zabbix asserts
  * Production apply uses ``NBX_ZABBIX_TOKEN`` (lab: ``--simulate`` reads lab.json)

Owns the Extreme switching half of Track B (see ``zabbix/01-extreme-switching.md``):

  * Import Extreme VOSS / Port Speed Expect / Routing templates into Zabbix
  * Patch stock Extreme EXOS EtherLike duplex LLD with the same IFALIAS filters as net.if.discovery
  * Override stock Extreme EXOS/VOSS template ``{$TEMP_*}`` macros (stock 55/65 wins over globals)
  * Platform TemplateRules: EXOS / VOSS / IQ Engine → Extreme * by SNMP (not Network Generic)
  * Switch role IFALIAS / IFTYPE macros via ZabbixMacroAssignment (inheritance resolves these)
  * Global **destination** macros on the Zabbix server object (production end-state)
  * Optional ``--cutover-silence`` overlay (999 / MLT=0) for temporary LM migration only
  * Optional Speed Expect template link (stage 4); Routing stays unlinked until OSPF canary

Does **not** re-implement SiteGroup Agent / hostgroup-first / Server OOB — call
``configure_nbxsync_zerotouch.py`` for that. This script assumes SNMP CG on Switch*
roles (zerotouch step 5b) and only layers Extreme-specific templates + macros.

Usage::

  # Lab proof (NetBox + live Zabbix) — destination macros
  PYTHONPATH=/workspace/.deps/netbox/netbox:/workspace \\
    /workspace/.deps/venv/bin/python scripts/configure_nbxsync_network.py --simulate

  # Apply destination network deltas (production token)
  export NBX_ZABBIX_TOKEN=...
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
os.environ.setdefault('NETBOX_CONFIGURATION', os.environ.get('NETBOX_CONFIGURATION', 'netbox.configuration_nbxsync'))

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
    'Extreme VOSS by SNMP': ROOT / 'zabbix/templates/extreme_voss_snmp/template_net_extreme_voss_snmp.yaml',
    'Extreme Port Speed Expect by SNMP': ROOT
    / 'zabbix/templates/extreme_port_speed_expect_snmp/template_net_extreme_port_speed_expect_snmp.yaml',
    'Extreme Routing by SNMP': ROOT / 'zabbix/templates/extreme_routing_snmp/template_net_extreme_routing_snmp.yaml',
    'Extreme IQ Engine by SNMP': ROOT
    / 'zabbix/templates/extreme_iq_engine_snmp/template_net_extreme_iq_engine_snmp.yaml',
}

# Role → port-scoping macros (01 §A.5 / §A.8). Hybrid starts access/opt-in.
ROLE_MACROS = {
    'Switch Core': {
        '{$NET.IF.IFALIAS.MATCHES}': '.*',
        '{$NET.IF.IFALIAS.NOT_MATCHES}': '^X(-|$)',
        '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
    },
    'Switch Dist': {
        '{$NET.IF.IFALIAS.MATCHES}': '.*',
        '{$NET.IF.IFALIAS.NOT_MATCHES}': '^X(-|$)',
        '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
    },
    'Switch Mgmt': {
        '{$NET.IF.IFALIAS.MATCHES}': '.*',
        '{$NET.IF.IFALIAS.NOT_MATCHES}': '^X(-|$)',
        '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
    },
    'Switch Access': {
        '{$NET.IF.IFALIAS.MATCHES}': '^(USW|US|UP|MON|UW|TMON)(-|$)',
        '{$NET.IF.IFALIAS.NOT_MATCHES}': 'CHANGE_IF_NEEDED',
        '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
    },
    'Switch Hybrid': {
        '{$NET.IF.IFALIAS.MATCHES}': '^(USW|US|UP|MON|UW|TMON)(-|$)',
        '{$NET.IF.IFALIAS.NOT_MATCHES}': 'CHANGE_IF_NEEDED',
        '{$NET.IF.IFTYPE.MATCHES}': '^(6|161)$',
    },
}

# Production end-state (default). Stock EXOS 55/65 is wrong for G2+ internal sensors
# (GTAC 000088439: Normal often 10–100, Max 110). Prefer vendor overTemp *status*
# as the hard alarm; value macros warn 90 / crit 100.
DESTINATION_GLOBAL_MACROS = {
    '{$IF.UTIL.MAX}': '101',  # stock util% off until stage-6 context macros
    '{$TEMP_WARN}': '90',
    '{$TEMP_CRIT}': '100',
    '{$TEMP_CRIT_LOW}': '-273',
    '{$OPTIC.TEMP.CRIT}': '70',
    '{$OPTIC.TEMP.MAX}': '150',
    '{$OPTIC.RX.DBM.MIN}': '-25',  # secondary; prefer DOM *Status alarms
    '{$OPTIC.RX.DBM.FLOOR}': '-39',
    '{$OPTIC.DOM.ALARM_HIGH}': '3',
    '{$OPTIC.DOM.ALARM_LOW}': '5',
    '{$MLT.CONTROL}': '1',  # .diff() keeps unused/disabled MLTs quiet
    '{$VIST.CONTROL}': '0',  # set host macro =1 on VOSS fabric pairs
    '{$IST.CONTROL}': '0',  # classic IST unused on FE fabric
    '{$SNMP.TIMEOUT}': '5m',
    '{$PORTID.LLD.IFALIAS.MATCHES}': '^(USW|US|UP|MON)(-|$)',
    '{$PORTID.LLD.IFTYPE.MATCHES}': '^6$',
}

# Temporary LM-migration overlay only — never the long-term target.
CUTOVER_SILENCE_OVERLAY = {
    '{$TEMP_WARN}': '999',
    '{$TEMP_CRIT}': '999',
    '{$OPTIC.TEMP.CRIT}': '999',
    '{$OPTIC.RX.DBM.MIN}': '-100',
    '{$MLT.CONTROL}': '0',
}

GLOBAL_MACROS = dict(DESTINATION_GLOBAL_MACROS)


def apply_macro_mode(*, cutover_silence: bool = False) -> None:
    """Set module GLOBAL_MACROS to destination, optionally overlay cutover silence."""
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
        api.configuration.import_(
            format='yaml',
            rules=import_rules(),
            source=path.read_text(),
        )
        found = api.template.get(filter={'name': [name]}, output=['templateid', 'host', 'name'])
        if not found:
            # stock EXOS may already exist under another host key
            found = api.template.get(search={'name': name}, output=['templateid', 'host', 'name'])
            found = [t for t in (found or []) if t.get('name') == name]
        if found:
            out[name] = (int(found[0]['templateid']), name)
            logger.info('  Imported/found %s (id=%s)', name, found[0]['templateid'])
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


# Stock Extreme EXOS ships {$TEMP_WARN}=55 / {$TEMP_CRIT}=65. Template macros beat globals,
# so setting globals alone never stops the G2+ "Normal @ 70°C" false critical.
_TEMP_TEMPLATE_MACRO_KEYS = ('{$TEMP_WARN}', '{$TEMP_CRIT}', '{$TEMP_CRIT_LOW}')
_TEMP_TEMPLATE_NAMES = ('Extreme EXOS by SNMP', 'Extreme VOSS by SNMP')


def _template_macro_map(macros: list) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in macros or []:
        if isinstance(m, dict) and m.get('macro'):
            out[m['macro']] = m.get('value', '')
    return out


def _wanted_temp_template_macros() -> dict[str, str]:
    """TEMP_* values from GLOBAL_MACROS (destination or cutover-silence overlay)."""
    return {k: GLOBAL_MACROS[k] for k in _TEMP_TEMPLATE_MACRO_KEYS if k in GLOBAL_MACROS}


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


def step_role_macros() -> None:
    """ZabbixMacroAssignment on Switch* roles — what inheritance actually syncs."""
    logger.info('=' * 60)
    logger.info('Network: role IFALIAS / IFTYPE macros')
    logger.info('=' * 60)
    # Macros need a ZabbixMacro parent (server-scoped). Find/create per name.
    server = M.ZabbixServer.objects.filter(name=SIM_SERVER_NAME).first() or M.ZabbixServer.objects.first()
    if server is None:
        raise SystemExit('No ZabbixServer — run with --simulate or create a server first')

    for role_name, macros in ROLE_MACROS.items():
        try:
            role = get_role(role_name)
        except DeviceRole.DoesNotExist:
            # Production may use unprefixed names
            role = DeviceRole.objects.filter(name=role_name).first() or DeviceRole.objects.filter(name__iendswith=role_name).first()
            if role is None:
                logger.warning('  Role not found: %s — skipping', role_name)
                continue
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
        ('Extreme EXOS', 'EXOS', 'Extreme EXOS by SNMP'),
        ('Extreme VOSS', 'VOSS', 'Extreme VOSS by SNMP'),
        ('Extreme IQ Engine', 'IQ ENGINE', 'Extreme IQ Engine by SNMP'),
    )
    for rule_name, pattern, tpl_name in rule_specs:
        if tpl_name not in tpl:
            continue
        ensure(
            M.ZabbixTemplateRule,
            name=rule_name,
            defaults={
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
            update_fields=[
                'pattern',
                'zabbixtemplate',
                'enabled',
                'priority',
                'zabbixhostgroup',
                'require_tags',
                'role_pattern',
                'manufacturer',
            ],
        )
        logger.info('  Rule %s → %s', rule_name, tpl[tpl_name].name)

    for rule_name, _pattern, tpl_name in rule_specs:
        if tpl_name not in tpl:
            continue
        for rule in M.ZabbixTemplateRule.objects.filter(name=rule_name):
            if rule.zabbixtemplate_id and 'Network Generic' in (rule.zabbixtemplate.name or ''):
                rule.zabbixtemplate = tpl[tpl_name]
                rule.save(update_fields=['zabbixtemplate'])
                logger.info('  PRUNED: %s rule was Network Generic → retargeted', rule_name)


def step_speed_expect_assignment(server, tpl: dict[str, M.ZabbixTemplate], *, link: bool) -> None:
    """Stage 4 — optional. Assign Speed Expect on Switch Core/Dist platforms via role? No — both platforms."""
    if not link or 'Extreme Port Speed Expect by SNMP' not in tpl:
        logger.info('  Speed Expect: not linked (pass --link-speed-expect for stage 4)')
        return
    t = tpl['Extreme Port Speed Expect by SNMP']
    for role_name in ('Switch Core', 'Switch Dist', 'Switch Mgmt', 'Switch Access', 'Switch Hybrid'):
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
    M.ZabbixTemplateRule.objects.filter(name__in=['Extreme EXOS', 'Extreme VOSS', 'Extreme IQ Engine']).delete()
    M.ZabbixTemplateRule.objects.filter(zabbixtemplate__name__startswith=PREFIX).delete()
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
    lab_servers = M.ZabbixServer.objects.filter(name=SIM_SERVER_NAME)
    if LAB_JSON.exists():
        lab_url = json.loads(LAB_JSON.read_text()).get('url')
        if lab_url:
            lab_servers = M.ZabbixServer.objects.filter(url=lab_url) | lab_servers
    for server in lab_servers.distinct():
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

    # Monkey-patch get_role for prefixed lab (same trick as zerotouch)
    orig_get_role = globals()['get_role']

    def lab_get_role(name: str) -> DeviceRole:
        return DeviceRole.objects.get(slug=slugify(name))

    globals()['get_role'] = lab_get_role

    try:
        # One ZabbixServer per URL (unique constraint). Reuse zerotouch lab server if present.
        server = M.ZabbixServer.objects.filter(name=SIM_SERVER_NAME).first()
        if server is None:
            server = M.ZabbixServer.objects.filter(url=lab['url']).first()
        if server is None:
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

        tpl_models: dict[str, M.ZabbixTemplate] = {}
        for name, (tid, _) in imported.items():
            tpl_models[name] = ensure_nbx_template(server, tid, name)
            record(f'import_{name}', True, str(tid), group='import')

        step_server_macros(server)
        step_role_macros()
        step_template_rules(server, tpl_models)
        step_speed_expect_assignment(server, tpl_models, link=link_speed_expect)

        # Hostgroups (Sites × Roles) — same Jinja idea as zerotouch
        hg_lab, _ = ensure(M.ZabbixHostgroup, zabbixserver=server, name=f'{PREFIX}lab', defaults={'value': f'{PREFIX}lab'}, update_fields=['value'])
        hg_sites, _ = ensure(
            M.ZabbixHostgroup,
            zabbixserver=server,
            name=f'{PREFIX}Sites',
            defaults={
                'value': (
                    'Sites/{{ object.site.group.get_ancestors(include_self=True) '
                    '| map(attribute="name") | join("/") }}/{{ object.site.name }}'
                ),
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
            ('voss_access', 'Switch Access', plat_voss),
            ('exos_core', 'Switch Core', plat_exos),
            ('voss_hybrid', 'Switch Hybrid', plat_voss),
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
        m_core = macro_map(objects['voss_core'])
        record('core_ifalias_matches', m_core.get('{$NET.IF.IFALIAS.MATCHES}') == '.*', str(m_core), group='resolve')
        record('core_ifalias_not_matches_x_only', m_core.get('{$NET.IF.IFALIAS.NOT_MATCHES}') == '^X(-|$)', str(m_core), group='resolve')
        m_acc = macro_map(objects['voss_access'])
        record('access_ifalias_opt_in', 'USW' in (m_acc.get('{$NET.IF.IFALIAS.MATCHES}') or ''), str(m_acc), group='resolve')
        record('hybrid_opt_in_like_access', 'USW' in (macro_map(objects['voss_hybrid']).get('{$NET.IF.IFALIAS.MATCHES}') or ''), str(macro_map(objects['voss_hybrid'])), group='resolve')
        record(
            'voss_rule_not_netgeneric',
            M.ZabbixTemplateRule.objects.filter(name='Extreme VOSS').exclude(zabbixtemplate__name__icontains='Network Generic').exists(),
            str(list(M.ZabbixTemplateRule.objects.filter(name='Extreme VOSS').values_list('zabbixtemplate__name', flat=True))),
            group='resolve',
        )
        record(
            'iq_rule_not_netgeneric',
            M.ZabbixTemplateRule.objects.filter(name='Extreme IQ Engine').exclude(zabbixtemplate__name__icontains='Network Generic').exists(),
            str(list(M.ZabbixTemplateRule.objects.filter(name='Extreme IQ Engine').values_list('zabbixtemplate__name', flat=True))),
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

            h_a = host(objects['voss_access'].name)
            if h_a:
                macros = {m['macro']: m.get('value', '') for m in (h_a.get('macros') or []) if isinstance(m, dict) and 'macro' in m}
                record('zbx_access_opt_in', 'USW' in (macros.get('{$NET.IF.IFALIAS.MATCHES}') or ''), str(macros), group='zabbix')

            h_e = host(objects['exos_core'].name)
            if h_e:
                tpls = [t.get('name') for t in h_e.get('parentTemplates', [])]
                record('zbx_exos_template', any('EXOS' in (n or '') for n in tpls), str(tpls), group='zabbix')

            gmacros = {m['macro']: m.get('value', '') for m in (api.usermacro.get(globalmacro=True, output='extend') or []) if isinstance(m, dict) and 'macro' in m}
            expect_temp = GLOBAL_MACROS['{$TEMP_WARN}']
            expect_mlt = GLOBAL_MACROS['{$MLT.CONTROL}']
            record('zbx_global_util_off', gmacros.get('{$IF.UTIL.MAX}') == '101', gmacros.get('{$IF.UTIL.MAX}'), group='zabbix')
            record('zbx_global_temp_warn', gmacros.get('{$TEMP_WARN}') == expect_temp, gmacros.get('{$TEMP_WARN}'), group='zabbix')
            record('zbx_global_mlt_control', gmacros.get('{$MLT.CONTROL}') == expect_mlt, gmacros.get('{$MLT.CONTROL}'), group='zabbix')
            record(
                'zbx_global_destination_temp_crit',
                gmacros.get('{$TEMP_CRIT}') == GLOBAL_MACROS['{$TEMP_CRIT}'],
                gmacros.get('{$TEMP_CRIT}'),
                group='zabbix',
            )

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


def run_apply(*, link_speed_expect: bool = False, cutover_silence: bool = False) -> int:
    """Apply network deltas on the production / shared ZabbixServer row."""
    apply_macro_mode(cutover_silence=cutover_silence)
    token = os.environ.get('NBX_ZABBIX_TOKEN')
    if not token:
        raise SystemExit('Set NBX_ZABBIX_TOKEN (or use --simulate)')
    url = os.environ.get('NBX_ZABBIX_URL', 'http://10.0.105.144:8080')
    server = M.ZabbixServer.objects.first()
    if server is None:
        server = M.ZabbixServer.objects.create(name='Zabbix', url=url, token=token, validate_certs=False, sync_enabled=True)
    else:
        server.token = token
        if url:
            server.url = url
        server.save()

    with ZabbixConnection(server) as api:
        imported = import_extreme_templates(api)
        step_global_macros_zabbix(api)
        patch_etherlike_ifalias_filters(api)
        patch_extreme_template_temp_macros(api)
    tpl_models = {name: ensure_nbx_template(server, tid, name) for name, (tid, name) in imported.items()}
    step_server_macros(server)
    step_role_macros()
    step_template_rules(server, tpl_models)
    step_speed_expect_assignment(server, tpl_models, link=link_speed_expect)
    logger.info('Network configuration applied (macros=%s)', 'cutover-silence' if cutover_silence else 'destination')
    return 0


def run_zabbix_only() -> int:
    """Fallback smoke without NetBox object graph — delegates to run_network_zabbix_sim."""
    from run_network_zabbix_sim import main as sim_main

    sys.argv = ['run_network_zabbix_sim.py', '--with-speed-expect']
    return sim_main()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--simulate', action='store_true', help='Lab: NetBox estate + SyncHostJob + Zabbix asserts')
    mode.add_argument('--zabbix-only', action='store_true', help='Zabbix API smoke only (no NetBox graph)')
    mode.add_argument('--apply', action='store_true', help='Apply network deltas (needs NBX_ZABBIX_TOKEN)')
    parser.add_argument('--link-speed-expect', action='store_true', help='Stage 4: assign Port Speed Expect on Switch roles')
    parser.add_argument(
        '--cutover-silence',
        action='store_true',
        help='Temporary LM-migration overlay (TEMP/OPTIC=999, MLT=0). Default is destination end-state.',
    )
    args = parser.parse_args()
    if args.simulate:
        return run_simulate(link_speed_expect=args.link_speed_expect, cutover_silence=args.cutover_silence)
    if args.zabbix_only:
        return run_zabbix_only()
    return run_apply(link_speed_expect=args.link_speed_expect, cutover_silence=args.cutover_silence)


if __name__ == '__main__':
    raise SystemExit(main())
