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
  * Patch stock EXOS ``psu.discovery`` to skip ``notPresent`` stack-MIB padding and queue check-now discovery for stale rows (no fork, no host sync)
  * Override stock Extreme EXOS/VOSS template ``{$TEMP_*}`` macros (stock 55/65 wins over globals)
  * Disable ICMP loss/RTT triggers on EXOS/VOSS/IQ (items stay for Health; CH proxy RTT is WAN)
  * Health dashboards ship in YAML (VOSS/IQ + EXOS Observability companion). ``--apply`` patches the stock EXOS **Network interfaces** Overview + Port layout and drops leftover Health Diagnostics pages.
  * Platform TemplateRules: EXOS → Observability companion (nests stock); VOSS / IQ Engine → Extreme * by SNMP
  * Switch role IFALIAS / IFTYPE macros via ZabbixMacroAssignment (inheritance resolves these)
  * Global **destination** macros on the Zabbix server object (production end-state)
  * Optional ``--cutover-silence`` overlay (999 / MLT=0) for temporary LM migration only
  * Optional Speed Expect template link (stage 4); Routing stays unlinked until OSPF canary

Stage matrix (what each flag enables):
  ``--apply``                     = stages 0–3: template imports + EXOS/VOSS/IQ rules + IFALIAS + destination globals + TEMP/ICMP/Health patches
  ``--apply --link-speed-expect`` = stage 4: + Speed Expect template assignments on Switch roles
  ``--apply --cutover-silence``   = cutover overlay: TEMP/OPTIC=999, MLT/VIST=0 (temporary, re-run without to restore)
  Routing / Stage 6 context macros = manual (Extreme switching page)

Re-apply safety (estate already has switches/APs in Zabbix):
  * Does **not** delete hosts, interfaces, history, or hostids
  * Does **not** mass-sync every device (template updates inherit in Zabbix)
  * YAML ``deleteMissing: false`` — retired items linger; LLD is not wiped
  * ``--apply`` without ``--link-speed-expect`` does **not** unlink Speed Expect if it was linked earlier
  * Empty SNMP secrets are zerotouch's job and must not blank existing CG passphrases

Import policy:
  YAML imports use deleteMissing=False (safe — retired items linger but templates don't lose content).
  Re-run ``--apply`` after Extreme template upgrades to re-assert TEMP/EtherLike/ICMP/Health patches.
  Speed Expect: re-running ``--apply`` without ``--link-speed-expect`` does NOT unlink existing assignments (future: add ``--unlink-speed-expect``).

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
    'Extreme VOSS by SNMP': ROOT / 'zabbix/templates/extreme_voss_snmp/template_net_extreme_voss_snmp.yaml',
    'Extreme EXOS Observability': ROOT / 'zabbix/templates/extreme_exos_observability_snmp/template_extreme_exos_observability_snmp.yaml',
    'Extreme Port Speed Expect by SNMP': ROOT / 'zabbix/templates/extreme_port_speed_expect_snmp/template_net_extreme_port_speed_expect_snmp.yaml',
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
    '{$PORTID.LLD.IFALIAS.MATCHES}': '^(USW|US|UP|MON)(-|$)',
    '{$PORTID.LLD.IFTYPE.MATCHES}': '^6$',
}

# Extreme EXOS/VOSS template-only macros (NOT global — scoped to switch templates).
# Stock EXOS ships {$TEMP_WARN}=55 / {$TEMP_CRIT}=65 — way too low for G2+.
EXTREME_TEMPLATE_TEMP_MACROS = {
    '{$TEMP_WARN}': '95',
    '{$TEMP_CRIT}': '100',
    '{$TEMP_CRIT_LOW}': '-273',
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
_IF_LLD_ROLLOUT_LIFETIME = '0'
_IF_LLD_ROLLOUT_TIMEOUT = '30s'


_PSU_DISCOVERY_KEY = 'psu.discovery'
_PSU_NUMBER_OID = '1.3.6.1.4.1.1916.1.1.1.27.1.1'
_PSU_STATUS_OID = '1.3.6.1.4.1.1916.1.1.1.27.1.2'
_PSU_DISCOVERY_OID = (
    f'discovery[{{#SNMPVALUE}},{_PSU_NUMBER_OID},{{#PSU.STATUS}},{_PSU_STATUS_OID}]'
)
_PSU_STATUS_MACRO = '{#PSU.STATUS}'
_PSU_NOTPRESENT = '^1$'
_PSU_LLD_LIFETIME = '0'


def _psu_lld_skips_notpresent(rule: dict) -> bool:
    snmp_oid = str(rule.get('snmp_oid') or '')
    if '{#PSU.STATUS}' not in snmp_oid or _PSU_STATUS_OID not in snmp_oid:
        return False
    lifetime = str(rule.get('lifetime') or '')
    if lifetime not in (_PSU_LLD_LIFETIME, '0s', '0d', '0h'):
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
    (``presentNotOK`` / ``presentPowerOff``). Lifetime 0 so leftover empty-slot
    items drop on the next discovery. Does not fork the stock YAML.
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
        output=['itemid', 'key_', 'snmp_oid', 'lifetime', 'enabled_lifetime'],
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
        lifetime=_PSU_LLD_LIFETIME,
        enabled_lifetime=_PSU_LLD_LIFETIME,
        filter={'evaltype': _LLD_EVAL_AND, 'conditions': conditions},
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
        output=['itemid', 'snmp_oid', 'lifetime'],
        selectFilter='extend',
    )
    if not rules:
        return True, 'no PSU LLD — n/a'
    ok = _psu_lld_skips_notpresent(rules[0])
    return ok, str({'snmp_oid': rules[0].get('snmp_oid'), 'filter': rules[0].get('filter')})


def patch_exos_interface_lld_rollout(api, template_name: str = 'Extreme EXOS by SNMP') -> str:
    """Align stock EXOS net.if.discovery with VOSS rollout settings.

    Stock Extreme EXOS ships delay=1h, a long lost-resources period, and the
    default SNMP timeout. Dist/Access EXOS boxes with many VLAN ifaces then
    show EtherLike duplex (small table) and **zero** ``net.if.*`` traffic
    items (full IF-MIB walk). Idempotent API patch; does not fork the stock YAML.
    """
    logger.info('Network: EXOS net.if.discovery rollout (delay/lifetime/timeout)')
    tpls = api.template.get(filter={'name': [template_name]}, output=['templateid', 'name'])
    if not tpls:
        logger.warning('  %s: template not found — skip IF LLD rollout patch', template_name)
        return 'missing'
    tid = tpls[0]['templateid']
    rules = api.discoveryrule.get(
        hostids=tid,
        filter={'key_': _IF_DISCOVERY_KEY},
        output=['itemid', 'key_', 'delay', 'lifetime', 'enabled_lifetime', 'timeout'],
    )
    if not rules:
        logger.warning('  %s: no %s — skip', template_name, _IF_DISCOVERY_KEY)
        return 'no-if-lld'
    rule = rules[0]
    delay = str(rule.get('delay') or '')
    lifetime = str(rule.get('lifetime') or '')
    enabled = str(rule.get('enabled_lifetime') or '')
    timeout = str(rule.get('timeout') or '')
    delay_ok = delay == _IF_LLD_ROLLOUT_DELAY and lifetime in (_IF_LLD_ROLLOUT_LIFETIME, '0s', '0d') and enabled in (
        _IF_LLD_ROLLOUT_LIFETIME,
        '0s',
        '0d',
        '',
    )
    if delay_ok and timeout == _IF_LLD_ROLLOUT_TIMEOUT:
        logger.info(
            '  %s: IF LLD rollout already set (delay=%s lifetime=%s timeout=%s)',
            template_name,
            delay,
            lifetime,
            timeout,
        )
        return 'ok'
    payload = {
        'itemid': rule['itemid'],
        'delay': _IF_LLD_ROLLOUT_DELAY,
        'lifetime': _IF_LLD_ROLLOUT_LIFETIME,
        'enabled_lifetime': _IF_LLD_ROLLOUT_LIFETIME,
        'timeout': _IF_LLD_ROLLOUT_TIMEOUT,
    }
    try:
        api.discoveryrule.update(**payload)
    except Exception as exc:
        logger.warning(
            '  %s: IF LLD timeout=%s rejected (%s) — patching delay/lifetime only',
            template_name,
            _IF_LLD_ROLLOUT_TIMEOUT,
            exc,
        )
        api.discoveryrule.update(
            itemid=rule['itemid'],
            delay=_IF_LLD_ROLLOUT_DELAY,
            lifetime=_IF_LLD_ROLLOUT_LIFETIME,
            enabled_lifetime=_IF_LLD_ROLLOUT_LIFETIME,
        )
        return 'patched-no-timeout'
    logger.info(
        '  %s: patched IF LLD delay=%s lifetime=%s timeout=%s (was delay=%s lifetime=%s timeout=%s)',
        template_name,
        _IF_LLD_ROLLOUT_DELAY,
        _IF_LLD_ROLLOUT_LIFETIME,
        _IF_LLD_ROLLOUT_TIMEOUT,
        delay,
        lifetime,
        timeout,
    )
    return 'patched'


def assert_exos_interface_lld_rollout(api, template_name: str = 'Extreme EXOS by SNMP') -> tuple[bool, str]:
    tpls = api.template.get(filter={'name': [template_name]}, output=['templateid'])
    if not tpls:
        return True, 'template absent — n/a'
    rules = api.discoveryrule.get(
        hostids=tpls[0]['templateid'],
        filter={'key_': _IF_DISCOVERY_KEY},
        output=['delay', 'lifetime', 'enabled_lifetime', 'timeout'],
    )
    if not rules:
        return True, 'no IF LLD — n/a'
    r = rules[0]
    detail = f"delay={r.get('delay')} lifetime={r.get('lifetime')} enabled_lifetime={r.get('enabled_lifetime')} timeout={r.get('timeout')}"
    ok = str(r.get('delay')) == _IF_LLD_ROLLOUT_DELAY and str(r.get('lifetime')) in (
        _IF_LLD_ROLLOUT_LIFETIME,
        '0s',
        '0d',
    )
    return ok, detail


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
    """TEMP_* values for Extreme templates. Uses EXTREME_TEMPLATE_TEMP_MACROS
    unless cutover-silence overlay is active (then GLOBAL_MACROS has 999s)."""
    if any(k in GLOBAL_MACROS for k in _TEMP_TEMPLATE_MACRO_KEYS):
        return {k: GLOBAL_MACROS[k] for k in _TEMP_TEMPLATE_MACRO_KEYS if k in GLOBAL_MACROS}
    return dict(EXTREME_TEMPLATE_TEMP_MACROS)


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
    """ICMP noise off + EXOS Health dashboard. Never raises."""
    logger.info('Network: Health / ICMP-noise patches')
    try:
        return apply_extreme_health_patches(api)
    except Exception as exc:  # noqa: BLE001
        logger.warning('  Health patches failed (non-fatal): %s', exc)
        return {'icmp_noise': {'error': str(exc)}, 'exos_health': f'error:{exc}'}


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
        ('Extreme EXOS', 'EXOS', 'Extreme EXOS Observability'),
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
    """Stage 4 — optional. Assign Speed Expect on Switch roles.

    ``link=False`` is a no-op: existing assignments stay. Never unlink here.
    """
    if not link or 'Extreme Port Speed Expect by SNMP' not in tpl:
        logger.info('  Speed Expect: not linking (pass --link-speed-expect for stage 4). ' 'Existing assignments are left in place.')
        return
    t = tpl['Extreme Port Speed Expect by SNMP']
    for role_name in ('Switch Core', 'Switch Dist', 'Switch Mgmt', 'Switch Access'):
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
                if_lld_status in ('ok', 'patched', 'patched-no-timeout', 'missing', 'no-if-lld'),
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
        record(
            'ap_template_iq_engine',
            any('IQ Engine' in n for n in tpl_names(objects['ap_access'])) and not any('Network Generic' in n for n in tpl_names(objects['ap_access'])),
            str(tpl_names(objects['ap_access'])),
            group='resolve',
        )
        record(
            'exos_rule_exists',
            M.ZabbixTemplateRule.objects.filter(name='Extreme EXOS').exclude(zabbixtemplate__name__icontains='Network Generic').exists(),
            str(list(M.ZabbixTemplateRule.objects.filter(name='Extreme EXOS').values_list('zabbixtemplate__name', flat=True))),
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


def run_apply(*, link_speed_expect: bool = False, cutover_silence: bool = False) -> int:
    """Apply network deltas on the production / shared ZabbixServer row."""
    apply_macro_mode(cutover_silence=cutover_silence)
    if cutover_silence:
        logger.warning('CUTOVER-SILENCE IS ENABLED — TEMP_* set to 999, MLT/VIST disabled.')
        logger.warning('This is a temporary LM migration overlay. Re-run without --cutover-silence to restore destination values.')
    else:
        # Warn if cutover-silence macros are still in place from a previous run
        from nbxsync.models import ZabbixMacro

        stuck = ZabbixMacro.objects.filter(macro='{$TEMP_WARN}', value='999').count()
        if stuck:
            logger.warning('CUTOVER-SILENCE STILL ACTIVE: %s macro(s) with TEMP_WARN=999 found. Re-run with --cutover-silence then without to clear, or manually verify.', stuck)
    token = os.environ.get('NBX_ZABBIX_TOKEN')
    if not token:
        raise SystemExit('Set NBX_ZABBIX_TOKEN (or use --simulate)')
    url = os.environ.get('NBX_ZABBIX_URL', 'http://10.0.105.144:8080')
    server = M.ZabbixServer.objects.filter(name='Zabbix Production').first() or M.ZabbixServer.objects.first()
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
        patch_exos_interface_lld_rollout(api)
        patch_exos_psu_lld_present_only(api)
        queue_exos_psu_lld_checks(api)
        patch_extreme_template_temp_macros(api)
        step_health_patches(api)
    tpl_models = {name: ensure_nbx_template(server, tid, name) for name, (tid, name) in imported.items()}
    step_server_macros(server)
    step_role_macros()
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
        return run_zabbix_only(link_speed_expect=args.link_speed_expect)
    return run_apply(link_speed_expect=args.link_speed_expect, cutover_silence=args.cutover_silence)


if __name__ == '__main__':
    raise SystemExit(main())
