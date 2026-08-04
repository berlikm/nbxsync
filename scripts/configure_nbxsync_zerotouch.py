#!/usr/bin/env python3
"""
nbxSync Zero-Touch Configuration Script

Successor to the previous checklist script (configure_nbxsync.py that implemented
docs/nbxsync/nbxsync-configuration-checklist.md step-for-step).

Hostgroup-first ops model (chosen scenario): Zabbix navigation and alerting hang
off ``Sites/*`` × ``Roles/*`` × ``OS/*`` (+ lean ``Priority/Critical`` via tag).
Transport stays on Configuration Groups (SiteGroup Agent default + role SNMP /
Server Agent+OOB exceptions). Tags are for overlays only — never transport.

Deltas vs the old checklist script:

  Δ5b  Agent CG → each top-level country SiteGroup (not 31 role→Agent rows)
  Δ5b  Pure Storage stays on SiteGroup Agent + HTTP template (ANY) — not SNMP CG
  Δ5b  Storage → SNMP CG; Cohesity → OOB SNMP Only
  Δ5b  Server BMC = one "Server Agent+OOB" CG (Agent + SNMP use_oob_ip) on Server
       role — NOT Manufacturer Dell → separate OOB CG
  Δ5   Drop snmp-tag HostInterface (I7: tags never carry transport).
       "VM by SNMP" CG = SNMP interface only (per-VM override)
  Δ6   Platform TemplateRules attach OS/* hostgroups only — no os_family Zabbix tags
  Δ6b  snmp NetBox tag + compound TemplateRules → Linux by SNMP / Windows by SNMP
       (OS-correct templates; pairs with VM-by-SNMP CG for transport)
  Δ8   Hostgroups: Sites + Roles Jinja @ SiteGroup + Priority/Critical; drop
       Managed/nbxSync and Teams/* (prefer Roles/* unless Zabbix RBAC needs Teams)
  Δ10  Single inventory Jinja payload applied to every country SiteGroup
  Δ0   NetBox inventory mutations OFF by default (--mutate-netbox to restore)
  ΔP0  Templates/proxies by Zabbix name; ensure() updates; prune shadow macros;
       --verify census (unprofiled / no-template / SNMP-role-on-Agent / …)

Usage::

  # Production apply (resolves template/proxy IDs from live Zabbix by name)
  export NBX_ZABBIX_TOKEN=...
  python scripts/configure_nbxsync_zerotouch.py

  # Read-only census (coverage gaps)
  python scripts/configure_nbxsync_zerotouch.py --verify

  # Lab proof against local Zabbix (prefixed synthetic estate)
  PYTHONPATH=/workspace/.deps/netbox/netbox:/workspace \\
    python scripts/configure_nbxsync_zerotouch.py --simulate
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import traceback
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
os.environ.setdefault('NETBOX_CONFIGURATION', os.environ.get('NETBOX_CONFIGURATION', 'netbox.configuration_nbxsync'))

# Prefer installed NetBox when present (lab / cloud agent layout).
_NETBOX = Path('/workspace/.deps/netbox/netbox')
if _NETBOX.exists() and str(_NETBOX) not in sys.path:
    sys.path.insert(0, str(_NETBOX))
if '/workspace' not in sys.path:
    sys.path.insert(0, '/workspace')

import django

django.setup()

from django.contrib.contenttypes.models import ContentType
from dcim.models import Device, DeviceRole, DeviceType, Interface, Manufacturer, Platform, Site, SiteGroup
from extras.models import Tag
from ipam.models import IPAddress
from virtualization.models import Cluster, ClusterType, VirtualMachine

from nbxsync import models as M
from nbxsync.choices import (
    HostInterfaceRequirementChoices,
    ZabbixHostInterfaceSNMPVersionChoices,
    ZabbixHostInterfaceTypeChoices,
    ZabbixHostInventoryModeChoices,
    ZabbixInterfaceSNMPV3AuthProtoChoices,
    ZabbixInterfaceSNMPV3PrivProtoChoices,
    ZabbixInterfaceSNMPV3SecurityLevelChoices,
    ZabbixInterfaceTypeChoices,
    ZabbixInterfaceUseChoices,
    ZabbixMacroTypeChoices,
    ZabbixProxyTypeChoices,
    ZabbixTLSChoices,
)
from nbxsync.jobs.synchost import SyncHostJob
from nbxsync.utils import get_assigned_zabbixobjects
from nbxsync.utils.zabbixconnection import ZabbixConnection

logger = logging.getLogger('configure_nbxsync_zerotouch')
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# ---- Production constants (same targets as previous checklist script) ----
ZABBIX_URL = os.environ.get('NBX_ZABBIX_URL', 'http://10.0.105.144:8080')


def _read_token() -> str:
    """Production token: env only. Lab token is read explicitly in --simulate."""
    env = os.environ.get('NBX_ZABBIX_TOKEN')
    if env:
        return env.strip()
    raise SystemExit('Set NBX_ZABBIX_TOKEN (lab: use --simulate, which reads lab.json)')


COUNTRY_SLUGS = ['ch', 'hu', 'jp', 'kr', 'nl', 'us', 'cn']

# Canonical Zabbix template *names*. IDs are resolved at apply time via the API
# (see resolve_templates). The optional ints below are documentation only for a
# typical 7.0 install — never used as the source of truth.
TPL_NAMES = {
    'windows_agent': 'Windows by Zabbix agent',
    'linux_agent': 'Linux by Zabbix agent',
    'linux_snmp': 'Linux by SNMP',
    'windows_snmp': 'Windows by SNMP',
    'extreme_exos_snmp': 'Extreme EXOS by SNMP',
    'network_generic_snmp': 'Network Generic Device by SNMP',
    'fortigate_snmp': 'FortiGate by SNMP',
    'vmware_fqdn': 'VMware FQDN',
    'dell_idrac_snmp': 'Dell iDRAC by SNMP',
    'mssql_odbc': 'MSSQL by ODBC',
    'pure_storage_http': 'Pure Storage FlashArray v1 by HTTP',
    'gitlab_http': 'GitLab by HTTP',
    # Created in Zabbix: clone of Network Generic without snmptrap.fallback
    # and zabbix[host,snmp,available] to avoid collision with Dell iDRAC
    # on Dell storage/Cohesity devices.
    'storage_generic_snmp': 'Storage Generic Device by SNMP',
    'icmp_ping': 'ICMP Ping',
}

# Populated by resolve_templates() / lab ensure_t(): key → (templateid, name)
TPL: dict[str, tuple[int, str]] = {}

PROXY_NAMES = {
    'ch': 'ch-proxy-1',
    'hu': 'hu-proxy-1',
    'kr': 'kr-proxy-1',
    'cn': 'cn-proxy-1',
}

SNMP_ROLES = [
    'Switch Core',
    'Switch Dist',
    'Switch Access',
    'Switch Mgmt',
    'Access Point',
    'Firewall',
    'Network Device',
    'Virtual Appliance',
    # SNMP-only storage (Pure is HTTP — not here)
    'Storage',
]

# Self-referencing host macros that shadow Zabbix globals — prune on every run.
SHADOW_MACROS = (
    '{$MSSQL.USER}',
    '{$MSSQL.PASSWORD}',
    '{$VMWARE.USER}',
    '{$VMWARE.PASSWORD}',
    '{$PURESTORAGE.TOKEN}',
)

# Previous script listed these under Agent; SiteGroup Agent default covers them now.
# Server is carved out into Server Agent+OOB instead.
AGENT_DEFAULT_ROLES_DOC = [
    'Domain Controller',
    'Fileserver',
    'Print Server',
    'MSSQL',
    'MSSQL Query Server',
    'SAP ME',
    'SecsGem',
    'Tableau',
    'Nautilus',
    'GitLab',
    'GitHub Runner',
    'TeamCity',
    'HLK',
    'vCenter',
    'SCCM',
    'PKI',
    'NAC',
    'Acronis Management',
    'VDI',
    'Session Host',
    'Connection Broker',
    'Azure Data Factory',
    'FiveTran',
    'CellMap',
    'Production Backup',
    'Solidworks PDM',
    'Subversion',
    'Space Server',
]

SERVER_BMC_ROLES = ['Server', 'Cohesity']  # Cohesity: Dell nodes with only oob_ip

LAB_JSON = Path('/home/ubuntu/zabbix-docker/lab.json')
REPORT_JSON = Path('/opt/cursor/artifacts/zerotouch_configure_sim_results.json')
REPORT_MD = Path('/opt/cursor/artifacts/ZEROTOUCH_CONFIGURE_SIM_REPORT.md')
PREFIX = 'ztc-'
SIM_SERVER_NAME = 'ZeroTouch Configure Lab'
RESULTS: list[dict] = []


def _ensure_report_dir() -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)


def ct(model):
    return ContentType.objects.get_for_model(model)


def get_role(name: str) -> DeviceRole:
    try:
        return DeviceRole.objects.get(name=name)
    except DeviceRole.DoesNotExist:
        return DeviceRole.objects.get(name__iexact=name)


def get_sitegroup(slug: str) -> SiteGroup:
    return SiteGroup.objects.get(slug=slug)


def get_or_create(model, defaults=None, **kwargs):
    """Deprecated alias — prefer ``ensure`` so re-runs update script-owned fields."""
    return ensure(model, defaults=defaults, **kwargs)


def _values_equal(old, new) -> bool:
    if isinstance(new, (list, tuple)) and isinstance(old, (list, tuple)):
        return list(old) == list(new)
    return old == new


def ensure(model, defaults=None, update_fields=None, **lookup):
    """Create or update a row. Unlike get_or_create, ``defaults`` refresh on EXISTS.

    ``update_fields`` limits which defaults keys are written on update (default: all).
    """
    defaults = dict(defaults or {})
    obj, created = model.objects.get_or_create(defaults=defaults, **lookup)
    if created:
        logger.info('  CREATED: %s = %s', model.__name__, obj)
        return obj, True

    fields = list(update_fields) if update_fields is not None else list(defaults.keys())
    changed: list[str] = []
    for field in fields:
        if field not in defaults:
            continue
        new = defaults[field]
        old = getattr(obj, field)
        if _values_equal(old, new):
            continue
        setattr(obj, field, new)
        changed.append(field)
    if changed:
        obj.save()
        logger.info('  UPDATED: %s = %s (%s)', model.__name__, obj, ', '.join(changed))
    else:
        logger.info('  EXISTS: %s = %s', model.__name__, obj)
    return obj, False


def prune_shadow_macros() -> int:
    """Delete host macros whose value is a self-reference that shadows Zabbix globals."""
    deleted, _ = M.ZabbixMacro.objects.filter(macro__in=SHADOW_MACROS).delete()
    if deleted:
        logger.info('  PRUNED: %s self-referencing secret macro(s)', deleted)
    return deleted


def resolve_templates(server, *, names: dict[str, str] | None = None, required: bool = True) -> dict[str, tuple[int, str]]:
    """Resolve template keys to (templateid, name) via Zabbix API name lookup."""
    names = names or TPL_NAMES
    resolved: dict[str, tuple[int, str]] = {}
    missing: list[str] = []
    with ZabbixConnection(server) as api:
        for key, name in names.items():
            found = api.template.get(filter={'name': name}, output=['templateid', 'name']) or []
            if not found:
                missing.append(name)
                continue
            resolved[key] = (int(found[0]['templateid']), found[0]['name'])
    if missing and required:
        raise SystemExit('Zabbix template(s) not found by name (fix names or import templates): ' + ', '.join(missing))
    if missing:
        logger.warning('  Optional templates missing: %s', ', '.join(missing))
    logger.info('  Resolved %s/%s templates by name', len(resolved), len(names))
    return resolved


def resolve_proxies(server, names: dict[str, str] | None = None) -> dict[str, M.ZabbixProxy]:
    """Ensure NetBox ZabbixProxy rows exist with proxyid taken from Zabbix by name."""
    names = names or PROXY_NAMES
    proxies: dict[str, M.ZabbixProxy] = {}
    with ZabbixConnection(server) as api:
        for country, name in names.items():
            found = api.proxy.get(filter={'name': name}, output=['proxyid', 'name']) or []
            if not found:
                raise SystemExit(f'Zabbix proxy not found by name: {name!r} (country={country})')
            proxyid = int(found[0]['proxyid'])
            proxy, _ = ensure(
                M.ZabbixProxy,
                name=name,
                defaults={
                    'zabbixserver': server,
                    'operating_mode': ZabbixProxyTypeChoices.ACTIVE,
                    'proxyid': proxyid,
                    'description': f'Proxy for {country.upper()}',
                },
                update_fields=['zabbixserver', 'operating_mode', 'proxyid', 'description'],
            )
            proxies[country] = proxy
    return proxies


def _snmp_v3_fields() -> dict:
    return {
        'snmp_version': ZabbixHostInterfaceSNMPVersionChoices.SNMPV3,
        'snmp_usebulk': True,
        'snmp_max_repetitions': 10,
        'snmp_community': '',
        'snmp_pushcommunity': False,
        'snmpv3_security_name': 'MONITORING',
        'snmpv3_security_level': ZabbixInterfaceSNMPV3SecurityLevelChoices.AUTHPRIV,
        'snmpv3_authentication_passphrase': '{$SNMP_AUTHPASS}',
        'snmpv3_authentication_protocol': ZabbixInterfaceSNMPV3AuthProtoChoices.SHA256,
        'snmpv3_privacy_passphrase': '{$SNMP_PRIVPASS}',
        'snmpv3_privacy_protocol': ZabbixInterfaceSNMPV3PrivProtoChoices.AES128,
    }


# =============================================================================
# Production steps (zero-touch successor of previous configure_nbxsync.py)
# =============================================================================


def step0_cleanup(*, mutate_netbox: bool):
    logger.info('=' * 60)
    logger.info('Step 0: Plugin-side tags / roles%s', ' + NetBox mutations' if mutate_netbox else '')
    logger.info('=' * 60)

    tag, created = Tag.objects.get_or_create(
        slug='do_not_monitor',
        defaults={'name': 'do_not_monitor', 'description': 'Excluded from Zabbix monitoring by nbxsync'},
    )
    logger.info("  Tag 'do_not_monitor': %s (id=%s)", 'CREATED' if created else 'EXISTS', tag.id)

    # Overlays: critical → Priority HG; snmp → Linux/Windows by SNMP TemplateRules (not transport).
    for name, desc in [
        ('critical', 'Priority/Critical hostgroup membership (24/7 escalation)'),
        ('snmp', 'SNMP OS template flavor: Linux by SNMP / Windows by SNMP (pair with VM by SNMP CG for interface)'),
    ]:
        # Reuse existing tag by slug OR name (NetBox auto-slugifies '_' -> '-')
        t = Tag.objects.filter(slug=name).first() or Tag.objects.filter(name=name).first()
        if t is None:
            t = Tag.objects.create(slug=name, name=name, description=desc)
            logger.info("  Tag '%s': CREATED (id=%s)", name, t.id)
        else:
            if not t.description and desc:
                t.description = desc
                t.save(update_fields=['description'])
            logger.info("  Tag '%s': EXISTS as slug=%s (id=%s)", name, t.slug, t.id)

    role, created = DeviceRole.objects.get_or_create(
        slug='virtual-appliance',
        defaults={'name': 'Virtual Appliance', 'color': '9e9e9e', 'vm_role': True},
    )
    logger.info("  Role 'Virtual Appliance': %s (id=%s)", 'CREATED' if created else 'EXISTS', role.id)

    if not mutate_netbox:
        logger.info('  Skipping NetBox inventory mutations (pass --mutate-netbox to enable previous step0.3–0.5)')
        return

    # Previous script behaviour (optional — locked design prefers no inventory edits)
    updated = 0
    for vm in VirtualMachine.objects.filter(platform__name__icontains='fortianalyzer'):
        if vm.role and vm.role.slug == 'virtual-appliance':
            continue
        vm.role = role
        vm.save()
        updated += 1
    for vm in VirtualMachine.objects.filter(platform__name__icontains='fortimanager'):
        if vm.role and vm.role.slug == 'virtual-appliance':
            continue
        vm.role = role
        vm.save()
        updated += 1
    logger.info('  Reassigned %s Forti* VM(s) → Virtual Appliance', updated)

    for slug, label in [('sd-wan-socket', 'Cato socket'), ('messpc', 'Messpc')]:
        qs = Device.objects.filter(role__slug=slug)
        tagged = 0
        for d in qs:
            if 'do_not_monitor' not in d.tags.names():
                d.tags.add('do_not_monitor')
                tagged += 1
        logger.info('  Tagged %s %s(s) with do_not_monitor (%s total)', tagged, label, qs.count())


def step1_zabbix_server(*, url: str | None = None, token: str | None = None, lab_http: bool = False):
    logger.info('=' * 60)
    logger.info('Step 1: ZabbixServer')
    logger.info('=' * 60)
    url = url or ZABBIX_URL
    token = token or _read_token()
    server, _ = ensure(
        M.ZabbixServer,
        name='Zabbix Production',
        defaults={
            'url': url,
            'token': token,
            'validate_certs': not lab_http,
            'sync_enabled': True,
            'skip_version_check': False,
            'description': 'Zabbix (configured by zero-touch script)',
        },
        update_fields=['url', 'token', 'validate_certs', 'sync_enabled', 'skip_version_check', 'description'],
    )
    return server


def step2_proxies(server):
    logger.info('=' * 60)
    logger.info('Step 2: ZabbixProxy + ZabbixProxyGroup (proxyid from Zabbix by name)')
    logger.info('=' * 60)
    proxies = resolve_proxies(server)

    ch_proxy_group, _ = ensure(
        M.ZabbixProxyGroup,
        name='CH Proxy Group',
        defaults={
            'zabbixserver': server,
            'description': 'Proxy group for CH-based monitoring (NL, US route through CH)',
        },
        update_fields=['zabbixserver', 'description'],
    )
    ch_proxy = proxies['ch']
    if ch_proxy.proxygroup_id != ch_proxy_group.pk or not ch_proxy.local_address:
        ch_proxy.proxygroup = ch_proxy_group
        ch_proxy.local_address = ch_proxy.local_address or '127.0.0.1'
        ch_proxy.local_port = ch_proxy.local_port or 10051
        ch_proxy.save()
        logger.info('  Linked %s → CH Proxy Group', ch_proxy.name)
    return proxies, ch_proxy_group


def step3_server_assignments(server, proxies, ch_proxy_group, country_slugs=None):
    logger.info('=' * 60)
    logger.info('Step 3: ZabbixServerAssignment (per country SiteGroup)')
    logger.info('=' * 60)
    country_slugs = country_slugs or COUNTRY_SLUGS
    # Keys are logical country codes; country_slugs may be prefixed in lab mode.
    logical = {
        'ch': {'proxygroup': ch_proxy_group},
        'hu': {'proxy': proxies['hu']},
        'jp': {'proxy': proxies['kr']},
        'kr': {'proxy': proxies['kr']},
        'nl': {'proxygroup': ch_proxy_group},
        'us': {'proxygroup': ch_proxy_group},
        'cn': {'proxy': proxies['cn']},
    }
    for slug in country_slugs:
        code = slug.lower().removeprefix(PREFIX.lower()) if PREFIX else slug.lower()
        if code not in logical:
            code = slug.lower()
        sg = get_sitegroup(slug)
        spec = logical[code]
        defaults = {
            'zabbixserver': server,
            'assigned_object_type': ct(SiteGroup),
            'assigned_object_id': sg.id,
            'sync_enabled': True,
            'zabbixproxy': spec.get('proxy'),
            'zabbixproxygroup': spec.get('proxygroup'),
        }
        get_or_create(
            M.ZabbixServerAssignment,
            zabbixserver=server,
            assigned_object_type=ct(SiteGroup),
            assigned_object_id=sg.id,
            defaults=defaults,
        )


def step4_configgroups():
    logger.info('=' * 60)
    logger.info('Step 4: Configuration Groups')
    logger.info('=' * 60)
    snmp_group, _ = get_or_create(
        M.ZabbixConfigurationGroup,
        name='SNMP Monitoring',
        defaults={'description': 'SNMP v3 interface template for network + SNMP-only storage'},
    )
    agent_group, _ = get_or_create(
        M.ZabbixConfigurationGroup,
        name='Agent Monitoring',
        defaults={'description': 'Default agent transport (assigned at top SiteGroups)'},
    )
    # Δ: complete BMC profile (replaces separate OOB-only CG used as Manufacturer assignment)
    server_oob_group, _ = get_or_create(
        M.ZabbixConfigurationGroup,
        name='Server Agent+OOB',
        defaults={'description': 'Server profile: Agent @ primary + SNMP @ oob_ip (use_oob_ip)'},
    )
    vm_snmp_group, _ = ensure(
        M.ZabbixConfigurationGroup,
        name='VM by SNMP',
        defaults={
            'description': 'Per-VM SNMP transport only — pair with NetBox tag snmp → Linux/Windows by SNMP templates',
        },
        update_fields=['description'],
    )
    # OOB-only SNMP: for hardware with only oob_ip (no primary_ip4) — e.g. Cohesity Dell nodes
    oob_snmp_group, _ = get_or_create(
        M.ZabbixConfigurationGroup,
        name='OOB SNMP Only',
        defaults={'description': 'SNMP @ oob_ip only — for hardware without primary_ip4'},
    )
    return snmp_group, agent_group, server_oob_group, vm_snmp_group, oob_snmp_group


def step5_host_interfaces(server, snmp_group, agent_group, server_oob_group, vm_snmp_group, oob_snmp_group):
    logger.info('=' * 60)
    logger.info('Step 5: ZabbixHostInterface (Configuration Group profiles only)')
    logger.info('=' * 60)
    ct_cfg = ct(M.ZabbixConfigurationGroup)

    def ensure_if(**lookup_and_defaults):
        defaults = lookup_and_defaults.pop('defaults')
        ensure(M.ZabbixHostInterface, defaults=defaults, **lookup_and_defaults)

    # 5.1 SNMP CG
    ensure_if(
        zabbixserver=server,
        assigned_object_type=ct_cfg,
        assigned_object_id=snmp_group.id,
        type=ZabbixHostInterfaceTypeChoices.SNMP,
        use_oob_ip=False,
        defaults={
            'zabbixconfigurationgroup': snmp_group,
            'interface_type': ZabbixInterfaceTypeChoices.DEFAULT,
            'port': 161,
            'useip': ZabbixInterfaceUseChoices.IP,
            'dns': '',
            **_snmp_v3_fields(),
        },
    )
    # 5.2 Agent CG
    ensure_if(
        zabbixserver=server,
        assigned_object_type=ct_cfg,
        assigned_object_id=agent_group.id,
        type=ZabbixHostInterfaceTypeChoices.AGENT,
        defaults={
            'zabbixconfigurationgroup': agent_group,
            'interface_type': ZabbixInterfaceTypeChoices.DEFAULT,
            'port': 10050,
            'useip': ZabbixInterfaceUseChoices.IP,
            'tls_connect': ZabbixTLSChoices.NO_ENCRYPTION,
            'dns': '',
        },
    )
    # 5.3 Server Agent+OOB — both interfaces on ONE CG
    ensure_if(
        zabbixserver=server,
        assigned_object_type=ct_cfg,
        assigned_object_id=server_oob_group.id,
        type=ZabbixHostInterfaceTypeChoices.AGENT,
        defaults={
            'zabbixconfigurationgroup': server_oob_group,
            'interface_type': ZabbixInterfaceTypeChoices.DEFAULT,
            'port': 10050,
            'useip': ZabbixInterfaceUseChoices.IP,
            'tls_connect': ZabbixTLSChoices.NO_ENCRYPTION,
            'dns': '',
        },
    )
    ensure_if(
        zabbixserver=server,
        assigned_object_type=ct_cfg,
        assigned_object_id=server_oob_group.id,
        type=ZabbixHostInterfaceTypeChoices.SNMP,
        use_oob_ip=True,
        defaults={
            'zabbixconfigurationgroup': server_oob_group,
            'interface_type': ZabbixInterfaceTypeChoices.DEFAULT,
            'port': 161,
            'useip': ZabbixInterfaceUseChoices.IP,
            'dns': '',
            **_snmp_v3_fields(),
        },
    )
    # 5.4 VM by SNMP — transport only (SNMP IF). OS templates come from Δ6b rules.
    ensure_if(
        zabbixserver=server,
        assigned_object_type=ct_cfg,
        assigned_object_id=vm_snmp_group.id,
        type=ZabbixHostInterfaceTypeChoices.SNMP,
        use_oob_ip=False,
        defaults={
            'zabbixconfigurationgroup': vm_snmp_group,
            'interface_type': ZabbixInterfaceTypeChoices.DEFAULT,
            'port': 161,
            'useip': ZabbixInterfaceUseChoices.IP,
            'dns': '',
            **_snmp_v3_fields(),
        },
    )
    # 5.4b OOB SNMP Only (hardware without primary_ip4 — e.g. Cohesity Dell nodes)
    ensure_if(
        zabbixserver=server,
        assigned_object_type=ct_cfg,
        assigned_object_id=oob_snmp_group.id,
        type=ZabbixHostInterfaceTypeChoices.SNMP,
        use_oob_ip=True,
        defaults={
            'zabbixconfigurationgroup': oob_snmp_group,
            'interface_type': ZabbixInterfaceTypeChoices.DEFAULT,
            'port': 161,
            'useip': ZabbixInterfaceUseChoices.IP,
            'dns': '',
            **_snmp_v3_fields(),
        },
    )
    # Δ: snmp-tag HostInterface removed — never put transport on tags (I7).
    # Per-VM: assign "VM by SNMP" CG (IF) + NetBox tag snmp (Linux/Windows by SNMP rules).
    pruned_ifs, _ = M.ZabbixHostInterface.objects.filter(
        zabbixserver=server,
        assigned_object_type=ct(Tag),
    ).delete()
    if pruned_ifs:
        logger.info('  PRUNED: %s tag-targeted HostInterface(s)', pruned_ifs)


def step5b_configgroup_assignments(snmp_group, agent_group, server_oob_group, oob_snmp_group=None, vm_snmp_group=None, country_slugs=None):
    """Δ vs previous: SiteGroup Agent default; SNMP+storage exceptions; Server BMC CG."""
    logger.info('=' * 60)
    logger.info('Step 5b: ConfigurationGroupAssignment (zero-touch)')
    logger.info('=' * 60)
    country_slugs = country_slugs or COUNTRY_SLUGS

    for slug in country_slugs:
        sg = get_sitegroup(slug)
        get_or_create(
            M.ZabbixConfigurationGroupAssignment,
            zabbixconfigurationgroup=agent_group,
            assigned_object_type=ct(SiteGroup),
            assigned_object_id=sg.id,
            defaults={},
        )
    logger.info('  Agent Monitoring → %s top SiteGroups (replaces %s role→Agent rows)', len(country_slugs), len(AGENT_DEFAULT_ROLES_DOC) + 1)

    def assign_role(group, role_name):
        try:
            role = get_role(role_name)
        except DeviceRole.DoesNotExist:
            logger.warning('  Role not found: %s, skipping', role_name)
            return
        get_or_create(
            M.ZabbixConfigurationGroupAssignment,
            zabbixconfigurationgroup=group,
            assigned_object_type=ct(DeviceRole),
            assigned_object_id=role.id,
            defaults={},
        )

    for role_name in SNMP_ROLES:
        assign_role(snmp_group, role_name)
    for role_name in SERVER_BMC_ROLES:
        # Cohesity goes to OOB SNMP Only (no primary_ip4 — only oob_ip)
        if role_name == 'Cohesity' and oob_snmp_group is not None:
            assign_role(oob_snmp_group, role_name)
            continue
        assign_role(server_oob_group, role_name)

    # Explicitly do NOT assign OOB CG to Manufacturer Dell (previous script pattern — broken).
    logger.info('  NOTE: Dell iDRAC remains a Manufacturer TEMPLATE (§7), not a transport CG')


def step6_template_rules(server, country_slugs=None):
    logger.info('=' * 60)
    logger.info('Step 6: ZabbixTemplateRules (template + OS/* hostgroup, no os_family tags)')
    logger.info('=' * 60)
    country_slugs = country_slugs or COUNTRY_SLUGS

    def hg(name, value, description=''):
        obj, _ = ensure(
            M.ZabbixHostgroup,
            zabbixserver=server,
            name=name,
            defaults={
                'value': value,
                'description': description or 'Attached by TemplateRules when platform matches (no HostgroupAssignment needed)',
            },
            update_fields=['value', 'description'],
        )
        return obj

    def make_template(zbx_id, zbx_name, req=None):
        defaults = {'templateid': zbx_id, 'zabbixserver': server}
        if req is not None:
            defaults['interface_requirements'] = req
        obj, _ = ensure(
            M.ZabbixTemplate,
            name=zbx_name,
            zabbixserver=server,
            defaults=defaults,
            update_fields=list(defaults.keys()),
        )
        return obj

    hg_os_windows = hg('OS/Windows', 'OS/Windows', 'OS class via TemplateRules (Windows platforms)')
    hg_os_linux = hg('OS/Linux', 'OS/Linux', 'OS class via TemplateRules (Linux platforms)')
    hg_os_network = hg('OS/Network', 'OS/Network', 'OS class via TemplateRules (network OS platforms)')
    hg_os_vmware = hg('OS/VMware', 'OS/VMware', 'OS class via TemplateRules (ESXi / vSphere)')

    tpl_windows = make_template(*TPL['windows_agent'], req=[HostInterfaceRequirementChoices.AGENT])
    tpl_linux = make_template(*TPL['linux_agent'], req=[HostInterfaceRequirementChoices.AGENT])
    tpl_linux_snmp = make_template(*TPL['linux_snmp'], req=[HostInterfaceRequirementChoices.SNMP])
    tpl_windows_snmp = make_template(*TPL['windows_snmp'], req=[HostInterfaceRequirementChoices.SNMP])
    tpl_exos = make_template(*TPL['extreme_exos_snmp'], req=[HostInterfaceRequirementChoices.SNMP])
    tpl_netgeneric = make_template(*TPL['network_generic_snmp'], req=[HostInterfaceRequirementChoices.SNMP])
    tpl_fortigate = make_template(*TPL['fortigate_snmp'], req=[HostInterfaceRequirementChoices.SNMP])
    # HTTP/simple-check templates — ANY, not AGENT (ESXi often has no Zabbix agent)
    tpl_vmware = make_template(*TPL['vmware_fqdn'], req=[HostInterfaceRequirementChoices.ANY])
    if 'icmp_ping' in TPL:
        tpl_icmp = make_template(*TPL['icmp_ping'], req=[HostInterfaceRequirementChoices.ANY])
        for slug in country_slugs or COUNTRY_SLUGS:
            try:
                sg = get_sitegroup(slug)
            except SiteGroup.DoesNotExist:
                logger.warning('  SiteGroup %s missing — skip ICMP assignment', slug)
                continue
            ensure(
                M.ZabbixTemplateAssignment,
                zabbixtemplate=tpl_icmp,
                assigned_object_type=ct(SiteGroup),
                assigned_object_id=sg.id,
                defaults={},
            )

    # Hostgroup-first: OS classification lives in OS/* groups, not os_family tags.
    rules = [
        ('Windows Server', r'Windows Server', tpl_windows, hg_os_windows, 50),
        ('Windows catch-all', r'Windows', tpl_windows, hg_os_windows, 200),
        ('Linux', r'Ubuntu|Debian|Linux|Red Hat|CentOS|Alma|SUSE|Arch|Photon|Other.*Linux', tpl_linux, hg_os_linux, 100),
        ('Extreme EXOS', r'EXOS', tpl_exos, hg_os_network, 100),
        ('Extreme VOSS', r'VOSS', tpl_netgeneric, hg_os_network, 100),
        ('Extreme IQ Engine', r'IQ ENGINE', tpl_netgeneric, hg_os_network, 100),
        ('FortiOS', r'FORTIOS|FortiOS', tpl_fortigate, hg_os_network, 100),
        ('FortiAnalyzer/Manager', r'FortiAnalyzer|FortiManager', tpl_netgeneric, hg_os_network, 50),
        ('VMware ESXi', r'ESXi|VMware ESX|vSphere', tpl_vmware, hg_os_vmware, 100),
        ('VMware Photon', r'Photon', tpl_linux, hg_os_linux, 50),
    ]
    for name, pattern, template, hostgroup, priority in rules:
        defaults = {
            'pattern': pattern,
            'zabbixtemplate': template,
            'enabled': True,
            'priority': priority,
            'zabbixtag': None,
            'zabbixhostgroup': hostgroup,
            'require_tags': '',
        }
        ensure(M.ZabbixTemplateRule, name=name, defaults=defaults, update_fields=list(defaults.keys()))

    # Δ6b: NetBox tag snmp → OS-correct SNMP templates (not a single "VM by SNMP" template).
    # Pair with "VM by SNMP" CG for the SNMP interface. HostSync drops agent templates
    # when only SNMP IF is present (and vice versa).
    for name, pattern, template, hostgroup in [
        ('SNMP Linux (tag)', r'Ubuntu|Debian|Linux|Red Hat|CentOS|Alma|SUSE|Arch|Photon|Other.*Linux', tpl_linux_snmp, hg_os_linux),
        ('SNMP Windows (tag)', r'Windows', tpl_windows_snmp, hg_os_windows),
    ]:
        defaults = {
            'pattern': pattern,
            'zabbixtemplate': template,
            'zabbixhostgroup': hostgroup,
            'zabbixtag': None,
            'require_tags': 'snmp',
            'enabled': True,
            'priority': 40,
        }
        ensure(M.ZabbixTemplateRule, name=name, defaults=defaults, update_fields=list(defaults.keys()))

    # Drop leftover os_family Zabbix tags from previous checklist / script runs.
    orphan_tags = M.ZabbixTag.objects.filter(tag='os_family')
    if orphan_tags.exists():
        # Detach any remaining rule FKs first (rules above already set zabbixtag=None).
        M.ZabbixTemplateRule.objects.filter(zabbixtag__in=orphan_tags).update(zabbixtag=None)
        M.ZabbixTagAssignment.objects.filter(zabbixtag__in=orphan_tags).delete()
        n, _ = orphan_tags.delete()
        logger.info('  PRUNED: %s os_family ZabbixTag row(s)', n)


def step7_template_assignments(server):
    logger.info('=' * 60)
    logger.info('Step 7: ZabbixTemplateAssignment')
    logger.info('=' * 60)

    def make_template(zbx_id, zbx_name, req=None):
        defaults = {'templateid': zbx_id, 'zabbixserver': server}
        if req is not None:
            defaults['interface_requirements'] = req
        obj, _ = ensure(
            M.ZabbixTemplate,
            name=zbx_name,
            zabbixserver=server,
            defaults=defaults,
            update_fields=list(defaults.keys()),
        )
        return obj

    assignments = [
        (make_template(*TPL['mssql_odbc'], req=[HostInterfaceRequirementChoices.AGENT]), 'MSSQL'),
        (make_template(*TPL['mssql_odbc'], req=[HostInterfaceRequirementChoices.AGENT]), 'MSSQL Query Server'),
        (make_template(*TPL['vmware_fqdn'], req=[HostInterfaceRequirementChoices.ANY]), 'vCenter'),
        (make_template(*TPL['pure_storage_http'], req=[HostInterfaceRequirementChoices.ANY]), 'Pure Storage'),
        (make_template(*TPL['gitlab_http'], req=[HostInterfaceRequirementChoices.ANY]), 'GitLab'),
        (make_template(*TPL['linux_snmp'], req=[HostInterfaceRequirementChoices.SNMP]), 'Virtual Appliance'),
        (make_template(*TPL['network_generic_snmp'], req=[HostInterfaceRequirementChoices.SNMP]), 'Network Device'),
        (make_template(*TPL['storage_generic_snmp'], req=[HostInterfaceRequirementChoices.SNMP]), 'Storage'),
        (make_template(*TPL['storage_generic_snmp'], req=[HostInterfaceRequirementChoices.SNMP]), 'Cohesity'),
    ]
    for template, role_name in assignments:
        try:
            role = get_role(role_name)
        except DeviceRole.DoesNotExist:
            logger.warning('  Role not found: %s, skipping', role_name)
            continue
        ensure(
            M.ZabbixTemplateAssignment,
            zabbixtemplate=template,
            assigned_object_type=ct(DeviceRole),
            assigned_object_id=role.id,
            defaults={},
        )

    dell = Manufacturer.objects.filter(name='Dell').first() or Manufacturer.objects.filter(slug='dell').first()
    if dell is not None:
        tpl_idrac = make_template(*TPL['dell_idrac_snmp'], req=[HostInterfaceRequirementChoices.SNMP])
        ensure(
            M.ZabbixTemplateAssignment,
            zabbixtemplate=tpl_idrac,
            assigned_object_type=ct(Manufacturer),
            assigned_object_id=dell.id,
            defaults={},
        )
    else:
        logger.warning("  Manufacturer 'Dell' not found, skipping iDRAC template assignment")

    # VM by SNMP CG is transport-only — prune any leftover CG→template links
    # (Linux/Windows by SNMP come from tag compound TemplateRules in step 6).
    for cg in M.ZabbixConfigurationGroup.objects.filter(name__endswith='VM by SNMP'):
        deleted, _ = M.ZabbixTemplateAssignment.objects.filter(
            assigned_object_type=ct(M.ZabbixConfigurationGroup),
            assigned_object_id=cg.id,
        ).delete()
        if deleted:
            logger.info('  PRUNED: %s template assignment(s) from %s (transport-only)', deleted, cg.name)


def step8_hostgroups(server, country_slugs=None):
    logger.info('=' * 60)
    logger.info('Step 8: ZabbixHostgroups (Sites × Roles × Priority — hostgroup-first)')
    logger.info('=' * 60)
    country_slugs = country_slugs or COUNTRY_SLUGS

    # Δ: drop Managed/nbxSync (noise) and Teams/* (prefer Roles/*; re-add only for Zabbix RBAC).
    hg_sites, _ = ensure(
        M.ZabbixHostgroup,
        zabbixserver=server,
        name='Sites',
        defaults={'value': 'Sites/{{ object.site.group.name }}/{{ object.site.name }}'},
        update_fields=['value'],
    )
    # One Roles Jinja assignment per country SiteGroup (not per DeviceRole)
    hg_roles, _ = ensure(
        M.ZabbixHostgroup,
        zabbixserver=server,
        name='Roles',
        defaults={'value': 'Roles/{{ object.role.name }}'},
        update_fields=['value'],
    )
    for slug in country_slugs:
        sg = get_sitegroup(slug)
        for hg in (hg_sites, hg_roles):
            get_or_create(
                M.ZabbixHostgroupAssignment,
                zabbixhostgroup=hg,
                assigned_object_type=ct(SiteGroup),
                assigned_object_id=sg.id,
                defaults={},
            )

    # OS/* hostgroups are attached by TemplateRules (step 6), not SiteGroup assignments.
    hg_crit, _ = ensure(
        M.ZabbixHostgroup,
        zabbixserver=server,
        name='Priority/Critical',
        defaults={'value': 'Priority/Critical'},
        update_fields=['value'],
    )
    crit_tag = Tag.objects.filter(slug='critical').first() or Tag.objects.filter(name='critical').first()
    if crit_tag is None:
        logger.warning("  NetBox tag 'critical' missing — skipping Priority/Critical")
    else:
        get_or_create(
            M.ZabbixHostgroupAssignment,
            zabbixhostgroup=hg_crit,
            assigned_object_type=ct(Tag),
            assigned_object_id=crit_tag.id,
            defaults={},
        )


def step9_tags(country_slugs=None):
    logger.info('=' * 60)
    logger.info('Step 9: ZabbixTags')
    logger.info('=' * 60)
    country_slugs = country_slugs or COUNTRY_SLUGS

    def assign_tag(zabbix_tag, content_type, obj_id):
        get_or_create(
            M.ZabbixTagAssignment,
            zabbixtag=zabbix_tag,
            assigned_object_type=content_type,
            assigned_object_id=obj_id,
            defaults={},
        )

    cluster_tag, _ = get_or_create(
        M.ZabbixTag,
        tag='cluster',
        value='{{ object.cluster.name }}',
        defaults={'name': 'cluster (Jinja2)'},
    )
    for c in Cluster.objects.all():
        assign_tag(cluster_tag, ct(Cluster), c.id)

    env_template = (
        '{% set n = object.name | lower -%}\n'
        '{%- if "-p-" in n or n.endswith("-p") or "-p0" in n or "-p1" in n -%}Production\n'
        '{%- elif "-d-" in n -%}Development\n'
        '{%- elif "-q-" in n -%}QA\n'
        '{%- elif "-s-" in n -%}Sandbox\n'
        '{%- elif "-t-" in n -%}Test\n'
        '{%- elif "vdi" in n -%}VDI\n'
        '{%- else -%}Unknown\n'
        '{%- endif -%}'
    )
    env_tag, _ = get_or_create(
        M.ZabbixTag,
        tag='environment',
        value=env_template,
        defaults={'name': 'environment (Jinja2)'},
    )
    for slug in country_slugs:
        assign_tag(env_tag, ct(SiteGroup), get_sitegroup(slug).id)

    exclusion_tag, _ = get_or_create(
        M.ZabbixTag,
        tag='do_not_monitor',
        value='',
        defaults={'name': 'do_not_monitor'},
    )
    for role_name in ['Messpc', 'Sd Wan Socket', 'VDI']:
        try:
            role = get_role(role_name)
        except DeviceRole.DoesNotExist:
            logger.warning('  Role not found: %s (exclusion)', role_name)
            continue
        assign_tag(exclusion_tag, ct(DeviceRole), role.id)


# Single inventory Jinja payload — applied identically to every country SiteGroup.
INVENTORY_PAYLOAD = {
    'inventory_mode': ZabbixHostInventoryModeChoices.AUTOMATIC,
    'type': '{{ object.__class__.__name__ }}',
    'serialno_a': '{{ object.serial }}',
    'hardware': '{{ object.device_type.model if object.device_type else "" }}',
    'hardware_full': '{{ object.device_type.manufacturer.name if object.device_type else "" }} {{ object.device_type.model if object.device_type else "" }}',
    'tag': '{{ object.asset_tag }}',
    'location': '{{ object.site.name }}',
    'site_rack': '{{ object.rack.name if object.rack else "" }}',
    'name': '{{ object.name }}',
    'url_a': 'https://netbox.sensirion.lokal/dcim/devices/{{ object.id }}/',
    'deployment_status': '{{ object.status }}',
}


def step10_host_inventory(country_slugs=None):
    logger.info('=' * 60)
    logger.info('Step 10: ZabbixHostInventory (one payload × country SiteGroups)')
    logger.info('=' * 60)
    country_slugs = country_slugs or COUNTRY_SLUGS
    for slug in country_slugs:
        sg = get_sitegroup(slug)
        ensure(
            M.ZabbixHostInventory,
            assigned_object_type=ct(SiteGroup),
            assigned_object_id=sg.id,
            defaults=dict(INVENTORY_PAYLOAD),
            update_fields=list(INVENTORY_PAYLOAD.keys()),
        )


def step11_macros():
    logger.info('=' * 60)
    logger.info('Step 11: ZabbixMacros')
    logger.info('=' * 60)
    prune_shadow_macros()
    macro_specs = [
        ('{$CPU.UTIL.CRIT}', '90', 'MSSQL'),
        ('{$CPU.UTIL.CRIT}', '80', 'Server'),
        ('{$IF.UTIL.MAX}', '80', 'Switch Core'),
        ('{$IF.UTIL.MAX}', '90', 'Switch Dist'),
        ('{$MEM.UTIL.CRIT}', '85', 'VDI'),
        ('{$MSSQL.DSN}', 'nbxsync', 'MSSQL'),
        # Secrets stay as Zabbix *global* macros — do not create self-referencing host macros.
        ('{$VMWARE.URL}', 'https://{{ object.name }}/sdk', 'vCenter'),
    ]
    for macro_name, macro_value, role_name in macro_specs:
        try:
            role = get_role(role_name)
        except DeviceRole.DoesNotExist:
            logger.warning('  Role not found: %s, skipping macro %s', role_name, macro_name)
            continue
        ensure(
            M.ZabbixMacro,
            macro=macro_name,
            assigned_object_type=ct(DeviceRole),
            assigned_object_id=role.id,
            defaults={'value': macro_value, 'type': ZabbixMacroTypeChoices.TEXT, 'description': f'ztc:{role_name}'},
            update_fields=['value', 'type', 'description'],
        )


def run_production(*, mutate_netbox: bool = False, url: str | None = None, token: str | None = None, lab_http: bool = False):
    global TPL
    logger.info('=' * 60)
    logger.info('nbxSync Zero-Touch Configuration')
    logger.info('Successor to previous checklist configure_nbxsync.py')
    logger.info('=' * 60)
    step0_cleanup(mutate_netbox=mutate_netbox)
    server = step1_zabbix_server(url=url, token=token, lab_http=lab_http)
    required_names = {k: v for k, v in TPL_NAMES.items() if k != 'icmp_ping'}
    TPL = resolve_templates(server, names=required_names, required=True)
    TPL.update(resolve_templates(server, names={'icmp_ping': TPL_NAMES['icmp_ping']}, required=False))
    proxies, ch_proxy_group = step2_proxies(server)
    step3_server_assignments(server, proxies, ch_proxy_group)
    snmp_group, agent_group, server_oob_group, vm_snmp_group, oob_snmp_group = step4_configgroups()
    step5_host_interfaces(server, snmp_group, agent_group, server_oob_group, vm_snmp_group, oob_snmp_group)
    step5b_configgroup_assignments(snmp_group, agent_group, server_oob_group, oob_snmp_group, vm_snmp_group)
    step6_template_rules(server)
    step7_template_assignments(server)
    step8_hostgroups(server)
    step9_tags()
    step10_host_inventory()
    step11_macros()

    logger.info('=' * 60)
    logger.info('CONFIGURATION COMPLETE — Summary')
    logger.info('=' * 60)
    for model in [
        M.ZabbixServer,
        M.ZabbixProxy,
        M.ZabbixServerAssignment,
        M.ZabbixConfigurationGroup,
        M.ZabbixConfigurationGroupAssignment,
        M.ZabbixHostInterface,
        M.ZabbixHostgroup,
        M.ZabbixHostgroupAssignment,
        M.ZabbixTag,
        M.ZabbixTagAssignment,
        M.ZabbixTemplate,
        M.ZabbixTemplateRule,
        M.ZabbixTemplateAssignment,
        M.ZabbixHostInventory,
        M.ZabbixMacro,
    ]:
        logger.info('  %s: %s', model.__name__, model.objects.count())
    logger.info('Zero-touch deltas: SiteGroup Agent, Server Agent+OOB, hostgroup-first (Sites×Roles×OS), no Teams/os_family/snmp-tag')
    return server


AGENT_PLATFORM_HINT = re.compile(r'Windows|Ubuntu|Debian|Linux|Red Hat|CentOS|Alma|SUSE|Arch|Photon', re.I)
SNMP_ROLE_NAMES = set(SNMP_ROLES)


def run_verify(*, limit: int | None = None) -> int:
    """Production post-apply / pre-go-live census. Does not mutate."""
    logger.info('=' * 60)
    logger.info('Verify: resolution census (read-only, hostgroup-first)')
    logger.info('=' * 60)
    devices = list(Device.objects.filter(status='active').select_related('role', 'platform', 'site'))
    vms = list(VirtualMachine.objects.filter(status='active').select_related('role', 'platform', 'site'))
    objects = devices + vms
    if limit is not None:
        objects = objects[:limit]

    unprofiled = 0
    agent_without_platform_fact = 0
    active_no_primary = 0
    no_template = 0
    snmp_role_on_agent_cg = 0
    os_family_tags_remaining = M.ZabbixTag.objects.filter(tag='os_family').count()
    snmp_tag_ifs = M.ZabbixHostInterface.objects.filter(assigned_object_type=ct(Tag)).count()
    agent_cg_name = 'Agent Monitoring'
    snmp_ish_cgs = {'SNMP Monitoring', 'OOB SNMP Only', 'Server Agent+OOB', 'VM by SNMP'}

    for obj in objects:
        if getattr(obj, 'primary_ip4_id', None) is None and getattr(obj, 'primary_ip6_id', None) is None:
            # OOB-only hardware (Cohesity) may still be valid — count for awareness.
            if getattr(obj, 'oob_ip_id', None) is None:
                active_no_primary += 1
        assigned = get_assigned_zabbixobjects(obj)
        cg = assigned.get('configurationgroup')
        templates = assigned.get('templates') or []
        if cg is None:
            unprofiled += 1
            continue
        if not templates:
            no_template += 1
        cg_name = cg.zabbixconfigurationgroup.name
        role_name = getattr(getattr(obj, 'role', None), 'name', '') or ''
        if role_name in SNMP_ROLE_NAMES and cg_name == agent_cg_name:
            snmp_role_on_agent_cg += 1
        if cg_name == agent_cg_name or cg_name.endswith('Agent Monitoring'):
            plat = getattr(getattr(obj, 'platform', None), 'name', '') or ''
            if not AGENT_PLATFORM_HINT.search(plat):
                agent_without_platform_fact += 1
        # Soft check: SNMP-ish roles should not sit on plain Agent without a template.
        if role_name in SNMP_ROLE_NAMES and cg_name not in snmp_ish_cgs and not any(
            n in cg_name for n in ('SNMP', 'OOB', 'VM by SNMP')
        ):
            # already counted snmp_role_on_agent_cg when exact Agent name matches
            pass

    shadow = M.ZabbixMacro.objects.filter(macro__in=SHADOW_MACROS).count()
    print(json.dumps({
        'objects_scanned': len(objects),
        'unprofiled': unprofiled,
        'no_template': no_template,
        'agent_cg_without_agent_platform_fact': agent_without_platform_fact,
        'snmp_role_resolved_to_agent_cg': snmp_role_on_agent_cg,
        'active_without_primary_or_oob_ip': active_no_primary,
        'shadow_secret_macros_remaining': shadow,
        'os_family_tags_remaining': os_family_tags_remaining,
        'tag_targeted_host_interfaces_remaining': snmp_tag_ifs,
    }, indent=2))
    return 0


# =============================================================================
# Lab simulation (proof against local Zabbix — prefixed synthetic estate)
# =============================================================================


def record(name: str, ok: bool, detail: str = '', *, group: str = 'general') -> None:
    RESULTS.append({'name': name, 'ok': bool(ok), 'detail': detail, 'group': group})
    print(f"[{'PASS' if ok else 'FAIL'}] {group}/{name}: {detail}")


def slugify(name: str) -> str:
    return PREFIX + name.lower().replace(' ', '-').replace('/', '-')


def cleanup_lab() -> None:
    """Tear down only the prefixed lab estate. Never touch a non-lab ZabbixServer."""
    Device.objects.filter(name__startswith=PREFIX).delete()
    VirtualMachine.objects.filter(name__startswith=PREFIX).delete()
    M.ZabbixTemplateRule.objects.filter(name__startswith=PREFIX).delete()
    M.ZabbixTemplateRule.objects.filter(zabbixtemplate__name__startswith=PREFIX).delete()
    M.ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup__name__startswith=PREFIX).delete()
    M.ZabbixConfigurationGroupAssignment.objects.filter(zabbixconfigurationgroup__name__startswith=PREFIX).delete()
    M.ZabbixTemplateAssignment.objects.filter(zabbixtemplate__name__startswith=PREFIX).delete()
    M.ZabbixTagAssignment.objects.filter(zabbixtag__name__startswith=PREFIX).delete()
    M.ZabbixMacro.objects.filter(description__startswith='ztc:').delete()
    M.ZabbixMacro.objects.filter(description__startswith=PREFIX).delete()
    for sg in SiteGroup.objects.filter(slug__startswith=PREFIX):
        M.ZabbixHostInventory.objects.filter(assigned_object_type=ct(SiteGroup), assigned_object_id=sg.pk).delete()

    servers = list(M.ZabbixServer.objects.filter(name=SIM_SERVER_NAME))
    if LAB_JSON.exists():
        lab_url = json.loads(LAB_JSON.read_text()).get('url')
        if lab_url:
            foreign = M.ZabbixServer.objects.filter(url=lab_url).exclude(name=SIM_SERVER_NAME)
            if foreign.exists():
                names = ', '.join(foreign.values_list('name', flat=True))
                raise SystemExit(
                    f'Refusing --simulate cleanup: ZabbixServer(s) {names} share lab URL {lab_url!r} '
                    f'but are not {SIM_SERVER_NAME!r}. Rename or remove them first.'
                )
    for server in servers:
        # Scope deletes to PREFIX / lab SiteGroups and config groups — never wipe a shared prod server.
        lab_sg_ids = list(SiteGroup.objects.filter(slug__startswith=PREFIX).values_list('pk', flat=True))
        lab_cg_ids = list(M.ZabbixConfigurationGroup.objects.filter(name__startswith=PREFIX).values_list('pk', flat=True))
        M.ZabbixServerAssignment.objects.filter(zabbixserver=server, assigned_object_type=ct(SiteGroup), assigned_object_id__in=lab_sg_ids).delete()
        M.ZabbixHostInterface.objects.filter(zabbixserver=server, assigned_object_type=ct(M.ZabbixConfigurationGroup), assigned_object_id__in=lab_cg_ids).delete()
        M.ZabbixHostBinding.objects.filter(zabbixserver=server, hostname__startswith=PREFIX).delete()
        M.ZabbixProxy.objects.filter(zabbixserver=server, name__startswith=PREFIX).delete()
        M.ZabbixProxyGroup.objects.filter(zabbixserver=server, name__startswith=PREFIX).delete()
        # Rules may reference PREFIX templates with non-prefixed rule names — clear first.
        M.ZabbixTemplateRule.objects.filter(zabbixtemplate__zabbixserver=server, zabbixtemplate__name__startswith=PREFIX).delete()
        M.ZabbixTemplateAssignment.objects.filter(zabbixtemplate__zabbixserver=server, zabbixtemplate__name__startswith=PREFIX).delete()
        M.ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup__zabbixserver=server, zabbixhostgroup__name__startswith=PREFIX).delete()
        M.ZabbixTemplateRule.objects.filter(zabbixhostgroup__zabbixserver=server, zabbixhostgroup__name__startswith=PREFIX).update(zabbixhostgroup=None)
        M.ZabbixHostgroup.objects.filter(zabbixserver=server, name__startswith=PREFIX).delete()
        M.ZabbixTemplate.objects.filter(zabbixserver=server, name__startswith=PREFIX).delete()
    M.ZabbixConfigurationGroup.objects.filter(name__startswith=PREFIX).delete()
    M.ZabbixTag.objects.filter(name__startswith=PREFIX).delete()
    Site.objects.filter(slug__startswith=PREFIX).delete()
    SiteGroup.objects.filter(slug__startswith=PREFIX).delete()
    DeviceRole.objects.filter(slug__startswith=PREFIX).delete()
    Platform.objects.filter(slug__startswith=PREFIX).delete()
    DeviceType.objects.filter(slug__startswith=PREFIX).delete()
    Manufacturer.objects.filter(slug__startswith=PREFIX).delete()
    Cluster.objects.filter(name__startswith=PREFIX).delete()
    ClusterType.objects.filter(slug__startswith=PREFIX).delete()
    Tag.objects.filter(slug__startswith=PREFIX).exclude(slug='do_not_monitor').delete()


def run_simulate() -> int:
    """Build prefixed lab estate, apply zero-touch steps, sync + assert vs live Zabbix."""
    global TPL, RESULTS
    RESULTS = []
    cleanup_lab()

    if not LAB_JSON.exists():
        raise SystemExit(f'Lab credentials missing: {LAB_JSON}')
    lab = json.loads(LAB_JSON.read_text())
    # Prefixed countries + roles matching checklist names
    for code in ('CH', 'HU', 'JP', 'KR', 'NL', 'US', 'CN'):
        SiteGroup.objects.get_or_create(slug=slugify(code), defaults={'name': f'{PREFIX}{code}'})
    leaf, _ = SiteGroup.objects.get_or_create(
        slug=slugify('CH-STA'),
        defaults={'name': f'{PREFIX}CH-STA', 'parent': SiteGroup.objects.get(slug=slugify('CH'))},
    )
    site, _ = Site.objects.get_or_create(
        slug=slugify('CH-STA-L44'),
        defaults={'name': f'{PREFIX}CH-STA-L44', 'group': leaf},
    )
    role_names = sorted(set(SNMP_ROLES + SERVER_BMC_ROLES + AGENT_DEFAULT_ROLES_DOC + ['Messpc', 'Sd Wan Socket', 'Virtual Appliance', 'Pure Storage', 'Storage']))
    roles = {}
    for name in role_names:
        roles[name], _ = DeviceRole.objects.get_or_create(
            slug=slugify(name),
            defaults={'name': f'{PREFIX}{name}', 'color': '9e9e9e', 'vm_role': True},
        )
    # Monkey-patch lookups used by production steps
    country_slugs = [slugify(c) for c in ('CH', 'HU', 'JP', 'KR', 'NL', 'US', 'CN')]

    orig_get_sitegroup = globals()['get_sitegroup']
    orig_get_role = globals()['get_role']

    def lab_get_sitegroup(slug: str) -> SiteGroup:
        if not slug.startswith(PREFIX):
            slug = slugify(slug.upper() if len(slug) <= 3 else slug)
        # map ch -> ztc-ch
        if slug in country_slugs:
            return SiteGroup.objects.get(slug=slug)
        # production steps pass raw COUNTRY_SLUGS
        mapped = slugify(slug.upper()) if len(slug) <= 3 else slugify(slug)
        return SiteGroup.objects.get(slug=mapped)

    def lab_get_role(name: str) -> DeviceRole:
        return DeviceRole.objects.get(slug=slugify(name))

    globals()['get_sitegroup'] = lab_get_sitegroup
    globals()['get_role'] = lab_get_role

    try:
        Tag.objects.get_or_create(slug='do_not_monitor', defaults={'name': 'do_not_monitor'})
        Tag.objects.get_or_create(slug='critical', defaults={'name': f'{PREFIX}critical'})
        snmp_tag, _ = Tag.objects.get_or_create(slug='snmp', defaults={'name': 'snmp'})
        # Hostgroup-first lab: no production_db / Teams overlays

        # Create / refresh lab server only (never rename a foreign server onto lab URL)
        server = M.ZabbixServer.objects.filter(name=SIM_SERVER_NAME).first()
        if server is None:
            conflict = M.ZabbixServer.objects.filter(url=lab['url']).exclude(name=SIM_SERVER_NAME).first()
            if conflict is not None:
                raise SystemExit(f'Lab URL {lab["url"]!r} already used by ZabbixServer {conflict.name!r}')
            server = M.ZabbixServer.objects.create(
                name=SIM_SERVER_NAME,
                url=lab['url'],
                token=lab['token'],
                validate_certs=False,
                sync_enabled=True,
                skip_version_check=False,
            )
        else:
            server.token = lab['token']
            server.url = lab['url']
            server.validate_certs = False
            server.skip_version_check = False
            server.save()

        # Prefixed proxies (avoid clashing with production proxy names)
        pg, _ = M.ZabbixProxyGroup.objects.get_or_create(
            name=f'{PREFIX}CH Proxy Group',
            defaults={'zabbixserver': server, 'description': 'lab'},
        )
        proxies = {}
        for key, name in [('ch', 'ch-proxy-1'), ('hu', 'hu-proxy-1'), ('kr', 'kr-proxy-1'), ('cn', 'cn-proxy-1')]:
            proxy, _ = M.ZabbixProxy.objects.get_or_create(
                name=f'{PREFIX}{name}',
                defaults={
                    'zabbixserver': server,
                    'operating_mode': ZabbixProxyTypeChoices.ACTIVE,
                    'proxygroup': pg if key == 'ch' else None,
                    'local_address': '127.0.0.1' if key == 'ch' else '',
                    'local_port': 10051,
                },
            )
            proxies[key] = proxy

        # Use prefixed country slugs in steps
        step3_server_assignments(server, proxies, pg, country_slugs=country_slugs)

        # Prefix CG names for lab isolation
        snmp_group, _ = M.ZabbixConfigurationGroup.objects.get_or_create(name=f'{PREFIX}SNMP Monitoring', defaults={'description': 'lab'})
        agent_group, _ = M.ZabbixConfigurationGroup.objects.get_or_create(name=f'{PREFIX}Agent Monitoring', defaults={'description': 'lab'})
        server_oob_group, _ = M.ZabbixConfigurationGroup.objects.get_or_create(name=f'{PREFIX}Server Agent+OOB', defaults={'description': 'lab'})
        vm_snmp_group, _ = M.ZabbixConfigurationGroup.objects.get_or_create(name=f'{PREFIX}VM by SNMP', defaults={'description': 'lab'})
        oob_snmp_group, _ = M.ZabbixConfigurationGroup.objects.get_or_create(name=f'{PREFIX}OOB SNMP Only', defaults={'description': 'lab'})

        step5_host_interfaces(server, snmp_group, agent_group, server_oob_group, vm_snmp_group, oob_snmp_group)
        step5b_configgroup_assignments(snmp_group, agent_group, server_oob_group, oob_snmp_group, vm_snmp_group, country_slugs=country_slugs)

        # Lab templates in Zabbix
        with ZabbixConnection(server) as api:
            for h in api.host.get(search={'host': PREFIX}, output=['hostid', 'host']) or []:
                if h['host'].startswith(PREFIX):
                    api.host.delete(h['hostid'])
            groups = api.hostgroup.get(filter={'name': f'{PREFIX}lab'})
            gid = groups[0]['groupid'] if groups else api.hostgroup.create(name=f'{PREFIX}lab')['groupids'][0]
            tgroups = api.templategroup.get(filter={'name': f'{PREFIX}templates'})
            tgid = tgroups[0]['groupid'] if tgroups else api.templategroup.create(name=f'{PREFIX}templates')['groupids'][0]

            def ensure_t(host, name):
                found = api.template.get(filter={'host': [host]})
                if found:
                    return found[0]['templateid']
                found = api.template.get(filter={'name': [name]})
                if found:
                    return found[0]['templateid']
                # Fallback: scan (Zabbix filter quirks across versions)
                for t in api.template.get(output=['templateid', 'host', 'name']) or []:
                    if t.get('host') == host or t.get('name') == name:
                        return t['templateid']
                return api.template.create(host=host, name=name, groups=[{'groupid': tgid}])['templateids'][0]

            TPL.clear()
            TPL['linux_agent'] = (int(ensure_t(f'{PREFIX}linux.agent', f'{PREFIX}Linux by Agent')), f'{PREFIX}Linux by Agent')
            TPL['windows_agent'] = (int(ensure_t(f'{PREFIX}windows.agent', f'{PREFIX}Windows by Agent')), f'{PREFIX}Windows by Agent')
            TPL['extreme_exos_snmp'] = (int(ensure_t(f'{PREFIX}exos.snmp', f'{PREFIX}Extreme EXOS by SNMP')), f'{PREFIX}Extreme EXOS by SNMP')
            TPL['network_generic_snmp'] = (int(ensure_t(f'{PREFIX}net.snmp', f'{PREFIX}Network Generic Device by SNMP')), f'{PREFIX}Network Generic Device by SNMP')
            TPL['fortigate_snmp'] = (int(ensure_t(f'{PREFIX}forti.snmp', f'{PREFIX}FortiGate by SNMP')), f'{PREFIX}FortiGate by SNMP')
            TPL['vmware_fqdn'] = (int(ensure_t(f'{PREFIX}vmware', f'{PREFIX}VMware FQDN')), f'{PREFIX}VMware FQDN')
            TPL['dell_idrac_snmp'] = (int(ensure_t(f'{PREFIX}idrac', f'{PREFIX}Dell iDRAC by SNMP')), f'{PREFIX}Dell iDRAC by SNMP')
            TPL['mssql_odbc'] = (int(ensure_t(f'{PREFIX}mssql', f'{PREFIX}MSSQL by ODBC')), f'{PREFIX}MSSQL by ODBC')
            TPL['pure_storage_http'] = (int(ensure_t(f'{PREFIX}pure', f'{PREFIX}Pure Storage FlashArray v1 by HTTP')), f'{PREFIX}Pure Storage FlashArray v1 by HTTP')
            TPL['gitlab_http'] = (int(ensure_t(f'{PREFIX}gitlab', f'{PREFIX}GitLab by HTTP')), f'{PREFIX}GitLab by HTTP')
            TPL['linux_snmp'] = (int(ensure_t(f'{PREFIX}linux.snmp', f'{PREFIX}Linux by SNMP')), f'{PREFIX}Linux by SNMP')
            TPL['windows_snmp'] = (int(ensure_t(f'{PREFIX}windows.snmp', f'{PREFIX}Windows by SNMP')), f'{PREFIX}Windows by SNMP')
            TPL['storage_generic_snmp'] = (int(ensure_t(f'{PREFIX}storage.snmp', f'{PREFIX}Storage Generic Device by SNMP')), f'{PREFIX}Storage Generic Device by SNMP')
            TPL['icmp_ping'] = (int(ensure_t(f'{PREFIX}icmp', f'{PREFIX}ICMP Ping')), f'{PREFIX}ICMP Ping')

        step6_template_rules(server, country_slugs=country_slugs)
        # Prefixed Dell — never create a second Manufacturer named 'Dell'
        dell, _ = Manufacturer.objects.get_or_create(slug=slugify('dell'), defaults={'name': f'{PREFIX}Dell'})
        dtype, _ = DeviceType.objects.get_or_create(slug=slugify('poweredge'), defaults={'manufacturer': dell, 'model': f'{PREFIX}PowerEdge'})
        step7_template_assignments(server)

        # Prove ensure() refreshes interface_requirements on re-run (P0.3)
        stale = M.ZabbixTemplate.objects.get(name=TPL['vmware_fqdn'][1], zabbixserver=server)
        stale.interface_requirements = [HostInterfaceRequirementChoices.AGENT]
        stale.save()
        step6_template_rules(server, country_slugs=country_slugs)
        step7_template_assignments(server)
        refreshed = M.ZabbixTemplate.objects.get(pk=stale.pk)
        record(
            'ensure_updates_interface_requirements',
            list(refreshed.interface_requirements) == [HostInterfaceRequirementChoices.ANY],
            str(list(refreshed.interface_requirements)),
            group='idempotent',
        )

        # Hostgroups with PREFIX names to avoid colliding with production HGs on shared server
        # Re-implement minimal HG assignments for lab using prefixed HG names
        hg_lab, _ = M.ZabbixHostgroup.objects.update_or_create(
            zabbixserver=server,
            name=f'{PREFIX}lab',
            defaults={'value': f'{PREFIX}lab', 'groupid': int(gid)},
        )
        hg_sites, _ = ensure(
            M.ZabbixHostgroup,
            zabbixserver=server,
            name=f'{PREFIX}Sites',
            defaults={'value': 'Sites/{{ object.site.group.name }}/{{ object.site.name }}'},
            update_fields=['value'],
        )
        hg_roles, _ = ensure(
            M.ZabbixHostgroup,
            zabbixserver=server,
            name=f'{PREFIX}Roles',
            defaults={'value': 'Roles/{{ object.role.name }}'},
            update_fields=['value'],
        )
        hg_crit, _ = ensure(
            M.ZabbixHostgroup,
            zabbixserver=server,
            name=f'{PREFIX}Priority/Critical',
            defaults={'value': 'Priority/Critical'},
            update_fields=['value'],
        )
        for slug in country_slugs:
            sg = SiteGroup.objects.get(slug=slug)
            for hg in (hg_lab, hg_sites, hg_roles):
                M.ZabbixHostgroupAssignment.objects.get_or_create(
                    zabbixhostgroup=hg,
                    assigned_object_type=ct(SiteGroup),
                    assigned_object_id=sg.id,
                )
        crit_tag = Tag.objects.get(slug='critical')
        M.ZabbixHostgroupAssignment.objects.get_or_create(
            zabbixhostgroup=hg_crit,
            assigned_object_type=ct(Tag),
            assigned_object_id=crit_tag.id,
        )

        step9_tags(country_slugs=country_slugs)
        step10_host_inventory(country_slugs=country_slugs)
        step11_macros()
        record('shadow_macros_pruned', M.ZabbixMacro.objects.filter(macro__in=SHADOW_MACROS).count() == 0, str(SHADOW_MACROS), group='idempotent')

        plat_linux, _ = Platform.objects.get_or_create(slug=slugify('ubuntu'), defaults={'name': f'{PREFIX}Ubuntu 22.04 LTS'})
        plat_win, _ = Platform.objects.get_or_create(slug=slugify('windows'), defaults={'name': f'{PREFIX}Windows Server 2022'})
        plat_exos, _ = Platform.objects.get_or_create(slug=slugify('exos'), defaults={'name': f'{PREFIX}Extreme EXOS 32.1'})
        ctype, _ = ClusterType.objects.get_or_create(slug=slugify('vmware'), defaults={'name': f'{PREFIX}VMware'})
        cluster, _ = Cluster.objects.get_or_create(name=f'{PREFIX}cluster-ch', defaults={'type': ctype, 'scope': site})

        octet = [40]

        def next_ip(net='10.91.1'):
            octet[0] += 1
            return f'{net}.{octet[0]}/32'

        def attach_dev(device, address, oob=None):
            iface = Interface.objects.create(device=device, name='eth0', type='1000base-t')
            ip = IPAddress.objects.create(address=address, status='active', assigned_object=iface)
            device.primary_ip4 = ip
            if oob:
                oi = Interface.objects.create(device=device, name='iDRAC', type='1000base-t')
                oip = IPAddress.objects.create(address=oob, status='active', assigned_object=oi)
                device.oob_ip = oip
            device.save()

        def attach_vm(vm, address):
            ip = IPAddress.objects.create(address=address, status='active')
            vm.primary_ip4 = ip
            vm.save()

        objects = {}
        d = Device.objects.create(name=f'{PREFIX}linux-srv-p-01', device_type=dtype, role=roles['Server'], site=site, platform=plat_linux, status='active')
        attach_dev(d, next_ip(), oob=next_ip('10.91.254'))
        objects['server_oob'] = d

        sw = Device.objects.create(name=f'{PREFIX}sw-core-01', device_type=dtype, role=roles['Switch Core'], site=site, platform=plat_exos, status='active')
        attach_dev(sw, next_ip())
        sw.tags.add(crit_tag)
        objects['switch'] = sw

        stor = Device.objects.create(name=f'{PREFIX}storage-01', device_type=dtype, role=roles['Storage'], site=site, status='active')
        attach_dev(stor, next_ip())
        objects['storage'] = stor

        win = VirtualMachine.objects.create(name=f'{PREFIX}win-vm-p-01', cluster=cluster, role=roles['Server'], site=site, platform=plat_win, status='active')
        attach_vm(win, next_ip())
        objects['win_vm'] = win

        new_role, _ = DeviceRole.objects.get_or_create(slug=slugify('Brand New App'), defaults={'name': f'{PREFIX}Brand New App', 'color': '9e9e9e', 'vm_role': True})
        new_vm = VirtualMachine.objects.create(name=f'{PREFIX}new-role-01', cluster=cluster, role=new_role, site=site, platform=plat_linux, status='active')
        attach_vm(new_vm, next_ip())
        objects['new_role'] = new_vm

        dc = VirtualMachine.objects.create(name=f'{PREFIX}dc-p-01', cluster=cluster, role=roles['Domain Controller'], site=site, platform=plat_win, status='active')
        attach_vm(dc, next_ip())
        objects['dc'] = dc

        vm_ov = VirtualMachine.objects.create(name=f'{PREFIX}ensa-snmp-vm', cluster=cluster, role=roles['Server'], site=site, platform=plat_linux, status='active')
        attach_vm(vm_ov, next_ip())
        vm_ov.tags.add(snmp_tag)
        M.ZabbixConfigurationGroupAssignment.objects.get_or_create(
            zabbixconfigurationgroup=vm_snmp_group,
            assigned_object_type=ct(VirtualMachine),
            assigned_object_id=vm_ov.pk,
        )
        objects['vm_snmp'] = vm_ov

        win_snmp = VirtualMachine.objects.create(name=f'{PREFIX}win-snmp-vm', cluster=cluster, role=roles['Server'], site=site, platform=plat_win, status='active')
        attach_vm(win_snmp, next_ip())
        win_snmp.tags.add(snmp_tag)
        M.ZabbixConfigurationGroupAssignment.objects.get_or_create(
            zabbixconfigurationgroup=vm_snmp_group,
            assigned_object_type=ct(VirtualMachine),
            assigned_object_id=win_snmp.pk,
        )
        objects['win_snmp'] = win_snmp

        def cg_name(obj):
            a = get_assigned_zabbixobjects(obj)
            cg = a.get('configurationgroup')
            return cg.zabbixconfigurationgroup.name if cg else None

        def tpl_names(obj):
            a = get_assigned_zabbixobjects(obj)
            return sorted(
                t.zabbixtemplate.name
                for t in (a.get('templates') or [])
                if getattr(t, 'zabbixtemplate', None) is not None
            )

        record('server_cg_oob', cg_name(objects['server_oob']) == server_oob_group.name, cg_name(objects['server_oob']), group='resolve')
        record('switch_cg_snmp', cg_name(objects['switch']) == snmp_group.name, cg_name(objects['switch']), group='resolve')
        record('storage_cg_snmp', cg_name(objects['storage']) == snmp_group.name, cg_name(objects['storage']), group='resolve')
        record('new_role_sitegroup_agent', cg_name(objects['new_role']) == agent_group.name, cg_name(objects['new_role']), group='resolve')
        record('dc_sitegroup_agent', cg_name(objects['dc']) == agent_group.name, cg_name(objects['dc']), group='resolve')
        record('vm_snmp_override', cg_name(objects['vm_snmp']) == vm_snmp_group.name, cg_name(objects['vm_snmp']), group='resolve')
        record(
            'linux_snmp_template_rule',
            any('Linux by SNMP' in n for n in tpl_names(objects['vm_snmp'])),
            str(tpl_names(objects['vm_snmp'])),
            group='resolve',
        )
        record(
            'windows_snmp_template_rule',
            any('Windows by SNMP' in n for n in tpl_names(objects['win_snmp'])),
            str(tpl_names(objects['win_snmp'])),
            group='resolve',
        )
        agent_role_rows = M.ZabbixConfigurationGroupAssignment.objects.filter(
            zabbixconfigurationgroup=agent_group, assigned_object_type=ct(DeviceRole)
        ).count()
        record('zero_agent_role_sprawl', agent_role_rows == 0, f'rows={agent_role_rows}', group='resolve')
        mfr_cg = M.ZabbixConfigurationGroupAssignment.objects.filter(assigned_object_type=ct(Manufacturer), assigned_object_id=dell.pk).count()
        record('no_manufacturer_transport_cg', mfr_cg == 0, f'count={mfr_cg}', group='resolve')

        with ZabbixConnection(server) as api:
            for key in ('server_oob', 'switch', 'storage', 'win_vm', 'new_role', 'dc', 'vm_snmp', 'win_snmp'):
                try:
                    SyncHostJob(instance=objects[key]).run()
                    record(f'sync_{key}', True, objects[key].name, group='sync')
                except Exception as exc:
                    record(f'sync_{key}', False, f'{exc}\n{traceback.format_exc()[-300:]}', group='sync')

            def host(name):
                found = api.host.get(filter={'host': name}, selectInterfaces='extend', selectParentTemplates=['name'], selectGroups=['name'])
                return found[0] if found else None

            h = host(objects['server_oob'].name)
            if h:
                ifs = [(i.get('type'), i.get('ip'), i.get('port')) for i in h.get('interfaces', [])]
                objects['server_oob'].refresh_from_db()
                oob = str(IPAddress.objects.get(id=objects['server_oob'].oob_ip_id).address.ip)
                primary = str(IPAddress.objects.get(id=objects['server_oob'].primary_ip4_id).address.ip)
                record('zbx_dual_if', any(t == '1' for t, _, _ in ifs) and any(t == '2' for t, _, _ in ifs), str(ifs), group='zabbix')
                record('zbx_oob_ip', any(t == '2' and ip == oob for t, ip, _ in ifs) and any(t == '1' and ip == primary for t, ip, _ in ifs), f'{ifs} oob={oob}', group='zabbix')
                groups = [g['name'] for g in h.get('groups', [])]
                record('zbx_sites_roles', any(g.startswith('Sites/') for g in groups) and any(g.startswith('Roles/') for g in groups), str(groups), group='zabbix')
                record('zbx_os_linux', any(g == 'OS/Linux' or g.endswith('/OS/Linux') for g in groups) or 'OS/Linux' in groups, str(groups), group='zabbix')
            else:
                record('zbx_server_exists', False, 'missing', group='zabbix')

            h_sw = host(objects['switch'].name)
            record('zbx_switch_critical', bool(h_sw) and 'Priority/Critical' in [g['name'] for g in h_sw.get('groups', [])], str(h_sw.get('groups') if h_sw else None), group='zabbix')
            h_new = host(objects['new_role'].name)
            record('zbx_new_role_group', bool(h_new) and any('Brand New App' in g['name'] for g in h_new.get('groups', [])), str(h_new.get('groups') if h_new else None), group='zabbix')
            h_ov = host(objects['vm_snmp'].name)
            ifs = [(i.get('type'), i.get('port')) for i in (h_ov.get('interfaces', []) if h_ov else [])]
            tpls = [t.get('name') for t in (h_ov.get('parentTemplates', []) if h_ov else [])]
            record('zbx_vm_snmp_only', any(t == '2' for t, _ in ifs) and not any(t == '1' for t, _ in ifs), str(ifs), group='zabbix')
            record('zbx_linux_by_snmp', any('Linux by SNMP' in (n or '') for n in tpls), str(tpls), group='zabbix')
            h_ws = host(objects['win_snmp'].name)
            w_ifs = [(i.get('type'), i.get('port')) for i in (h_ws.get('interfaces', []) if h_ws else [])]
            w_tpls = [t.get('name') for t in (h_ws.get('parentTemplates', []) if h_ws else [])]
            record('zbx_win_snmp_only', any(t == '2' for t, _ in w_ifs) and not any(t == '1' for t, _ in w_ifs), str(w_ifs), group='zabbix')
            record('zbx_windows_by_snmp', any('Windows by SNMP' in (n or '') for n in w_tpls), str(w_tpls), group='zabbix')

            # Hostgroup-first hygiene
            record('no_os_family_tags', M.ZabbixTag.objects.filter(tag='os_family').count() == 0, str(M.ZabbixTag.objects.filter(tag='os_family').count()), group='hygiene')
            record(
                'snmp_os_template_rules',
                M.ZabbixTemplateRule.objects.filter(name__in=['SNMP Linux (tag)', 'SNMP Windows (tag)'], enabled=True).count() == 2,
                str(list(M.ZabbixTemplateRule.objects.filter(name__startswith='SNMP ').values_list('name', flat=True))),
                group='hygiene',
            )
            record('vm_snmp_cg_transport_only', M.ZabbixTemplateAssignment.objects.filter(assigned_object_type=ct(M.ZabbixConfigurationGroup), assigned_object_id=vm_snmp_group.id).count() == 0, 'ok', group='hygiene')
            record('no_teams_hostgroups', M.ZabbixHostgroup.objects.filter(zabbixserver=server, name__startswith='Teams').count() == 0, str(list(M.ZabbixHostgroup.objects.filter(zabbixserver=server, name__startswith='Teams').values_list('name', flat=True))), group='hygiene')
            record('no_managed_hostgroup', not M.ZabbixHostgroup.objects.filter(zabbixserver=server, name='Managed').exists(), 'ok', group='hygiene')

        passed = sum(1 for r in RESULTS if r['ok'])
        total = len(RESULTS)
        _ensure_report_dir()
        REPORT_JSON.write_text(json.dumps({'summary': {'passed': passed, 'total': total}, 'results': RESULTS}, indent=2))
        lines = [
            '# Zero-Touch Configure Simulation Report',
            '',
            f'**Score:** {passed}/{total}',
            '',
            'Successor of previous checklist `configure_nbxsync.py` with zero-touch deltas.',
            '',
            '| Group | Case | Result | Detail |',
            '|---|---|---|---|',
        ]
        for r in RESULTS:
            lines.append(f"| {r['group']} | `{r['name']}` | {'PASS' if r['ok'] else 'FAIL'} | {r['detail'][:120].replace('|', '/')} |")
        REPORT_MD.write_text('\n'.join(lines) + '\n')
        print(f'\nSummary: {passed}/{total} — {REPORT_MD}')
        return 0 if passed == total else 1
    finally:
        globals()['get_sitegroup'] = orig_get_sitegroup
        globals()['get_role'] = orig_get_role


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--simulate', action='store_true', help='Lab: synthetic estate + live Zabbix asserts')
    parser.add_argument('--verify', action='store_true', help='Read-only census: unprofiled / agent-without-platform / no primary IP')
    parser.add_argument('--verify-limit', type=int, default=None, help='Optional cap on objects scanned by --verify')
    parser.add_argument('--mutate-netbox', action='store_true', help='Enable previous step0 inventory mutations')
    parser.add_argument('--zabbix-url', default=None, help='Override Zabbix URL')
    parser.add_argument('--lab-http', action='store_true', help='Allow validate_certs=False (HTTP lab)')
    args = parser.parse_args()
    if args.simulate:
        return run_simulate()
    if args.verify:
        return run_verify(limit=args.verify_limit)
    run_production(mutate_netbox=args.mutate_netbox, url=args.zabbix_url, lab_http=args.lab_http)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
