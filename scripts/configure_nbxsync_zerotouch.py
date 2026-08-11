#!/usr/bin/env python3
"""
nbxSync Zero-Touch Configuration Script

Applies ``docs/netbox-zabbix/configuration.md`` for a first-build speed-run.
Day-to-day ops use the NetBox GUI/API; see ``docs/netbox-zabbix/README.md``.

Hostgroup-first ops model: Zabbix navigation hangs off
``Sites/*`` × ``Roles/*`` × ``OS/*`` (+ lean ``Priority/Critical`` via tag).
Transport stays on Configuration Groups (SiteGroup Agent default + role SNMP /
Server Agent+OOB / SPACE exceptions). Multi-credential SNMPv3 profiles per CG
(network / Linux / Dell iDRAC / SAP). Tags CAN select transport via CG→Tag
assignment (``snmp``); Host Interfaces must NOT sit on tags. SAP uses role-based CG assignment (not tags).

Deltas vs the old checklist script:

  Δ5b  Agent CG → each top-level country SiteGroup (not 31 role→Agent rows)
  Δ5b  Pure Storage stays on SiteGroup Agent + HTTP template (ANY) — not SNMP CG
  Δ5b  Storage removed from SNMP CG (Cohesity → OOB SNMP Only)
  Δ5b  Server BMC = "Server Agent+OOB" with MONITORING-DELL SHA/AES on OOB SNMP
  Δ5b  ESXi = CG "ESXi OOB iDRAC" (MONITORING-DELL @ oob_ip) on ESXi platforms;
       VMware FQDN only on role vCenter (disable legacy platform rule "VMware ESXi")
  Δ5   Multi SNMPv3 profiles via SNMP_PROFILES + env NBX_SNMP_*_{MON,LINUX,DELL,SAP}
  Δ5   "SNMP Monitoring (Linux)" CG on NetBox tag snmp (was SNMP by tag / VM by SNMP)
  Δ5   "Agent Monitoring (SPACE)" port 10060 on Space Server role
  Δ5   "SNMP Monitoring (SAP)" CG on SAP HANA / SAP ME roles (provisional; confirm auth with Robert)
  Δ6   Platform TemplateRules attach OS/* hostgroups only — no os_family Zabbix tags
  Δ6b  snmp NetBox tag + compound TemplateRules → Linux by SNMP / Windows by SNMP
       (OS templates; transport from SNMP Monitoring (Linux) CG on the same tag)
  Δ8   Hostgroups: Sites + Roles Jinja @ SiteGroup + Priority/Critical; drop
       Managed/nbxSync and Teams/* (prefer Roles/* unless Zabbix RBAC needs Teams)
  Δ7   Role templates: Network Device → Network Generic fallback only; Firewall → FortiGate.
       Do NOT floor Switch*/AP with Network Generic — platform TemplateRules (EXOS, …)
       already attach specialized templates; both define icmpping and Zabbix rejects duplicates.
  Δ10  Single inventory Jinja payload applied to every country SiteGroup
  Δ0   NetBox inventory mutations OFF by default (--mutate-netbox to restore)
  ΔP0  Templates/proxies by Zabbix name; ensure() updates; prune shadow macros;
       --verify census (unprofiled / no-template / SNMP-role-on-Agent / …)
  ΔICMP Do NOT assign ICMP Ping at SiteGroup — collides with icmpping* in SNMP templates

Template vs hostgroup visibility (plugin model, not a script bug):
  * ZabbixTemplateAssignment hangs off NetBox objects (Role / SiteGroup / Device / …)
    → visible on the Role (or Template) page, NOT on the ZabbixHostgroup page.
  * ZabbixHostgroupAssignment / TemplateRule.zabbixhostgroup control group membership
    → Hostgroup page shows assignments + (with PR #25) TemplateRules for OS/*.
  Roles/* Jinja only names the Zabbix group; it does not carry templates.

Usage::

  # Production apply (resolves template/proxy IDs from live Zabbix by name)
  export NBX_ZABBIX_TOKEN=...
  export NBX_SNMP_AUTHPASS_MON=... NBX_SNMP_PRIVPASS_MON=...
  export NBX_SNMP_AUTHPASS_LINUX=... NBX_SNMP_PRIVPASS_LINUX=...
  export NBX_SNMP_AUTHPASS_DELL=... NBX_SNMP_PRIVPASS_DELL=...
  # optional SAP (after Robert confirms auth/priv):
  # export NBX_SNMP_AUTHPASS_SAP=... NBX_SNMP_PRIVPASS_SAP=...
  # Huawei (LogicMonitor user, non-fleet):
  # export NBX_SNMP_AUTHPASS_HUAWEI=... NBX_SNMP_PRIVPASS_HUAWEI=...
  # Per-device Pure Storage API tokens (one per array):
  # Per-vCenter SSO credentials (one per vCenter VM):
  # export NBX_VMWARE_USER_CH_STA_P_VCSA02=...
  # export NBX_VMWARE_PASS_CH_STA_P_VCSA02=...
  # MSSQL service account (shared):
  # export NBX_MSSQL_USER=... NBX_MSSQL_PASS=...
  python scripts/configure_nbxsync_zerotouch.py

  # IMPORTANT: Run scripts/configure_nbxsync_network.py after zerotouch for
  # Extreme EXOS/VOSS/IQ Engine template imports, TemplateRules, and macros.
  # Zerotouch creates the template objects but not the EXOS TemplateRule.

  # --mutate-netbox: first build only — creates ESXi Hypervisor role, migrates
  # ESXi devices from Server role, tags do_not_monitor on Cato/Messpc.

Roadmap / known debt:
  - Agent TLS: currently "No encryption" (tls_connect=1). Proxies use cert
    accept; agents do not. Plan a CG evolution (PSK/cert) when encrypted agent
    traffic is required — don't leave it as silent debt.
  - Cohesity VM selector: step5b queries VMs by role='Cohesity' + primary_ip4.
    Future: use a tag or cluster type instead of inventory scrape so new VMs
    don't require a re-run.
  - Stage 6 capacity macros: zerotouch stops at destination globals ($IF.UTIL.MAX=101,
    raised TEMP_*, optic floors). Context macros like {$IF.UTIL.MAX:"USW"} are
    post-cutover (Extreme doc §7 stage 6).

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
ZABBIX_URL = os.environ.get('NBX_ZABBIX_URL', 'https://sensirion.zabbix.cloud')


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
    # Optional — resolved by name if the template exists in Zabbix (imported by
    # configure_nbxsync_network.py or manually). When unresolved, the platform
    # TemplateRule falls back to Network Generic (see step6_template_rules).
    'extreme_voss_snmp': 'Extreme VOSS by SNMP',
    'extreme_iq_engine_snmp': 'Extreme IQ Engine by SNMP',
    'network_generic_snmp': 'Network Generic Device by SNMP',
    'fortigate_snmp': 'FortiGate by SNMP',
    'vmware_fqdn': 'VMware FQDN',
    'dell_idrac_snmp': 'Dell iDRAC by SNMP',
    'mssql_odbc': 'MSSQL by ODBC',
    'mssql_agent2': 'MSSQL by Zabbix agent 2',
    'pure_storage_http': 'Pure Storage FlashArray v2 by HTTP',
    'gitlab_http': 'GitLab by HTTP',
    # Created in Zabbix: clone of Network Generic without snmptrap.fallback
    # and zabbix[host,snmp,available] to avoid collision with Dell iDRAC
    # on Dell storage/Cohesity devices.
    'storage_generic_snmp': 'Storage Generic Device by SNMP',
    # Production storage templates (manufacturer-scoped TemplateRules in §6.3).
    # Names must match Zabbix Cloud exactly (see hosts STOD*/snas*/san*).
    # Dell Storage arrays use the HPE MSA HTTP template (same API shape in this estate).
    'hpe_msa_http': 'HPE MSA 2060 Storage by HTTP',
    'huawei_storage_snmp': 'Huawei OceanStor Dorado by SNMP',
    'synology_storage_snmp': 'Synology DiskStation SNMPv3',
    # Placeholder application templates — LM parity, items built post-cutover.
    'as_java_agent': 'AS Java by Zabbix agent (stub)',
    'tableau_bridge_agent': 'Tableau Bridge by Zabbix agent (stub)',
    'cellmap_agent': 'CellMap by Zabbix agent (stub)',
    'oracle_agent2': 'Oracle by Zabbix agent 2 (stub)',
    'sap_agent': 'SAP by Zabbix agent (stub)',
    'acronis_agent': 'Acronis by Zabbix agent (stub)',
    'sccm_agent': 'SCCM by Zabbix agent (stub)',
    'print_spool_agent': 'Print Spool by Zabbix agent (stub)',
    'icmp_ping': 'ICMP Ping',
    # Stock Zabbix template: proxy health (last access, version, config sync latency).
    'proxy_health': 'Remote Zabbix proxy health',
}

# Populated by resolve_templates() / lab ensure_t(): key → (templateid, name)
TPL: dict[str, tuple[int, str]] = {}

PROXY_NAMES = {
    # Production Zabbix Cloud names (must match exactly). Lab overrides: NBX_PROXY_CH, …
    'ch': os.environ.get('NBX_PROXY_CH', 'ch-sta-p-zabp01'),
    'ch2': os.environ.get('NBX_PROXY_CH2', 'ch-sta-p-zabp02'),
    'hu': os.environ.get('NBX_PROXY_HU', 'hu-deb-p-zabp01'),
    'kr': os.environ.get('NBX_PROXY_KR', 'kr-sel-p-zabp01'),
    'cn': os.environ.get('NBX_PROXY_CN', 'cn-sha-p-zabp01'),
}
# Extra proxies that join the CH proxy group (high availability).
CH_PROXY_GROUP_EXTRA = ['ch2']

# Network SNMP only — Storage is HTTP/TBD (not MONITORING MD5/DES).
SNMP_ROLES = [
    'Switch Core',
    'Switch Dist',
    'Switch Access',
    'Switch Mgmt',
    'Switch Hybrid',
    'Access Point',
    'Firewall',
    'Network Device',
    'Virtual Appliance',
    # 'Storage' not in SNMP CG: prevents Pure arrays from getting SNMP interface.
]

# SNMPv3 credential profiles (LogicMonitor account map). Passphrases from env.
# Linux "SHA" in LM is treated as SHA1 until confirmed otherwise.
SNMP_PROFILES = {
    'network': {
        'user': 'MONITORING',
        'auth': ZabbixInterfaceSNMPV3AuthProtoChoices.MD5,
        'priv': ZabbixInterfaceSNMPV3PrivProtoChoices.DES,
        'auth_env': ('NBX_SNMP_AUTHPASS_MON', 'NBX_SNMP_AUTHPASS'),
        'priv_env': ('NBX_SNMP_PRIVPASS_MON', 'NBX_SNMP_PRIVPASS'),
    },
    'linux': {
        'user': 'MONITORING-LINUX',
        'auth': ZabbixInterfaceSNMPV3AuthProtoChoices.SHA1,
        'priv': ZabbixInterfaceSNMPV3PrivProtoChoices.AES128,
        'auth_env': ('NBX_SNMP_AUTHPASS_LINUX',),
        'priv_env': ('NBX_SNMP_PRIVPASS_LINUX',),
    },
    'dell': {
        'user': 'MONITORING-DELL',
        'auth': ZabbixInterfaceSNMPV3AuthProtoChoices.SHA1,
        'priv': ZabbixInterfaceSNMPV3PrivProtoChoices.AES128,
        'auth_env': ('NBX_SNMP_AUTHPASS_DELL',),
        'priv_env': ('NBX_SNMP_PRIVPASS_DELL',),
    },
    # Provisional — confirm auth/priv with Robert before relying on SAP SNMP.
    'sap': {
        'user': 'SAPUSER',
        'auth': ZabbixInterfaceSNMPV3AuthProtoChoices.SHA1,
        'priv': ZabbixInterfaceSNMPV3PrivProtoChoices.AES128,
        'auth_env': ('NBX_SNMP_AUTHPASS_SAP',),
        'priv_env': ('NBX_SNMP_PRIVPASS_SAP',),
    },
}

# Self-referencing host macros that shadow Zabbix globals — prune on every run.
# Secret macros managed by zerotouch (role-level ZabbixMacro with ZabbixMacroAssignment).
# These are NO LONGER shadow-macros — they get real values from env vars and are
# pushed to hosts via the inheritance chain during sync.
# Old self-referencing macros (if any remain from previous versions) are still pruned.
SHADOW_MACROS = ()  # Empty — secrets are now managed in step11_macros

# Previous script listed these under Agent; SiteGroup Agent default covers them now.
# Server is carved out into Server Agent+OOB; Space Server → Agent Monitoring (SPACE).
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
]

SERVER_BMC_ROLES = ['Server', 'Cohesity']  # Cohesity: Dell nodes with only oob_ip

# Platforms that are ESXi hypervisors (not vCenter appliances). VMware API monitoring
# is vCenter-only; these hosts get Dell iDRAC on oob_ip and OS/VMware hostgroup.
ESXI_PLATFORM_RE = re.compile(r'ESXi|VMware ESX', re.I)

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


# Templates that may be missing in lab / early cutover — resolve soft.
OPTIONAL_TPL_KEYS = frozenset({
    'icmp_ping',
    'proxy_health',
    'extreme_voss_snmp',
    'extreme_iq_engine_snmp',
    # Placeholder app templates — soft-resolve (may not exist in Zabbix yet).
    'as_java_agent',
    'tableau_bridge_agent',
    'cellmap_agent',
    'oracle_agent2',
    'sap_agent',
    'acronis_agent',
    'sccm_agent',
    'print_spool_agent',
})

# Alternate Zabbix names tried in order when the primary TPL_NAMES entry is absent.
TPL_NAME_ALIASES: dict[str, tuple[str, ...]] = {
    'pure_storage_http': (
        'Pure Storage FlashArray v2 by HTTP',
        'Pure Storage FlashArray v1 by HTTP',
    ),
    'huawei_storage_snmp': (
        'Huawei OceanStor Dorado by SNMP',
        'Huawei Storage by SNMP',
    ),
    'synology_storage_snmp': (
        'Synology DiskStation SNMPv3',
        'Synology NAS by SNMP',
    ),
}


def resolve_templates(server, *, names: dict[str, str] | None = None, required: bool = True) -> dict[str, tuple[int, str]]:
    """Resolve template keys to (templateid, name) via Zabbix API name lookup.

    ``names`` values are preferred display names. ``TPL_NAME_ALIASES`` supplies
    fallbacks (e.g. Pure v2 → v1) when the preferred name is not imported yet.
    """
    names = names or TPL_NAMES
    resolved: dict[str, tuple[int, str]] = {}
    missing: list[str] = []
    with ZabbixConnection(server) as api:
        for key, name in names.items():
            candidates = (name,) + tuple(a for a in TPL_NAME_ALIASES.get(key, ()) if a != name)
            found_row = None
            for candidate in candidates:
                found = api.template.get(filter={'name': candidate}, output=['templateid', 'name']) or []
                if found:
                    found_row = found[0]
                    if candidate != name:
                        logger.info('  Template %s: using alias %r (preferred %r missing)', key, candidate, name)
                    break
            if not found_row:
                missing.append(name)
                continue
            resolved[key] = (int(found_row['templateid']), found_row['name'])
    if missing and required:
        raise SystemExit('Zabbix template(s) not found by name (fix names or import templates): ' + ', '.join(missing))
    if missing:
        logger.warning('  Optional templates missing: %s', ', '.join(missing))
    logger.info('  Resolved %s/%s templates by name', len(resolved), len(names))
    return resolved


def resolve_proxies(server, names: dict[str, str] | None = None) -> dict[str, M.ZabbixProxy]:
    """Ensure NetBox ZabbixProxy rows exist with proxyid taken from Zabbix by name.

    Active proxies use mutual TLS on the proxy host + Zabbix Cloud portal (PEM files
    are *not* managed here). NetBox only records tls_accept=Certificate so a later
    NetBox→Zabbix proxy sync does not reset encryption to “no encryption”.
    """
    names = names or PROXY_NAMES
    proxies: dict[str, M.ZabbixProxy] = {}
    with ZabbixConnection(server) as api:
        for key, name in names.items():
            found = api.proxy.get(filter={'name': name}, output=['proxyid', 'name']) or []
            if not found:
                raise SystemExit(f'Zabbix proxy not found by name: {name!r} (key={key})')
            proxyid = int(found[0]['proxyid'])
            proxy, _ = ensure(
                M.ZabbixProxy,
                name=name,
                defaults={
                    'zabbixserver': server,
                    'operating_mode': ZabbixProxyTypeChoices.ACTIVE,
                    'proxyid': proxyid,
                    'tls_accept': [ZabbixTLSChoices.CERT],
                    'description': f'Proxy {name}',
                },
                update_fields=['zabbixserver', 'operating_mode', 'proxyid', 'tls_accept', 'description'],
            )
            proxies[key] = proxy
    return proxies


def _env_first(names: tuple[str, ...] | list[str]) -> str:
    for name in names:
        val = os.environ.get(name, '')
        if val:
            return val
    return ''


def _snmp_v3_fields(profile: str = 'network') -> dict:
    """SNMPv3 fields for a named credential profile (see SNMP_PROFILES).

    Passphrases are real secrets on the interface; with snmp_pushcommunity=True,
    hostsync writes them as secret host macros and hostinterfacesync points the
    Zabbix interface details at those macros. Empty env leaves existing
    passphrase fields untouched on re-run (not overwritten with blanks).
    """
    try:
        cfg = SNMP_PROFILES[profile]
    except KeyError as exc:
        raise SystemExit(f'Unknown SNMP profile {profile!r}; known: {sorted(SNMP_PROFILES)}') from exc
    authpass = _env_first(cfg['auth_env'])
    privpass = _env_first(cfg['priv_env'])
    if not authpass or not privpass:
        logger.warning(
            'SNMP profile %r: auth/priv env unset or empty (%s / %s) — authPriv will fail until set',
            profile,
            cfg['auth_env'][0],
            cfg['priv_env'][0],
        )
    fields = {
        'snmp_version': ZabbixHostInterfaceSNMPVersionChoices.SNMPV3,
        'snmp_usebulk': True,
        'snmp_max_repetitions': 10,
        'snmp_community': '',
        'snmp_pushcommunity': True,
        'snmpv3_security_name': cfg['user'],
        'snmpv3_security_level': ZabbixInterfaceSNMPV3SecurityLevelChoices.AUTHPRIV,
        'snmpv3_authentication_protocol': cfg['auth'],
        'snmpv3_privacy_protocol': cfg['priv'],
    }
    if authpass:
        fields['snmpv3_authentication_passphrase'] = authpass
    if privpass:
        fields['snmpv3_privacy_passphrase'] = privpass
    return fields


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

    # Overlays / opt-ins: critical → Priority HG; snmp → Linux SNMP CG+templates; snmp-sap → SAP SNMP CG.
    for name, desc in [
        ('critical', 'Priority/Critical hostgroup membership (24/7 escalation)'),
        ('snmp', 'Zero-touch Linux SNMP: selects SNMP Monitoring (Linux) CG + Linux/Windows by SNMP TemplateRules'),
        # ('snmp-sap', '...'),  # Removed — SAP now uses role-based CG assignment
    ]:
    # Reuse existing tag by slug OR name (NetBox auto-slugifies '_' -> '-')
        t = Tag.objects.filter(slug=name).first() or Tag.objects.filter(name=name).first()
        if t is None:
            t = Tag.objects.create(slug=name, name=name, description=desc)
            logger.info("  Tag '%s': CREATED (id=%s)", name, t.id)
        else:
            if desc and t.description != desc:
                t.description = desc
                t.save(update_fields=['description'])
            logger.info("  Tag '%s': EXISTS as slug=%s (id=%s)", name, t.slug, t.id)

    role, created = DeviceRole.objects.get_or_create(
        slug='virtual-appliance',
        defaults={'name': 'Virtual Appliance', 'color': '9e9e9e', 'vm_role': True},
    )
    logger.info("  Role 'Virtual Appliance': %s (id=%s)", 'CREATED' if created else 'EXISTS', role.id)

    # ESXi Hypervisor role — separates ESXi hosts from regular Servers so they
    # get ESXi OOB iDRAC CG (SNMP only on oob_ip) instead of Server Agent+OOB
    # (which adds an unwanted Agent interface on primary_ip — ESXi has no agent).
    esxi_role, esxi_created = DeviceRole.objects.get_or_create(
        slug='esxi-hypervisor',
        defaults={'name': 'ESXi Hypervisor', 'color': '00b0f0', 'vm_role': False},
    )
    logger.info("  Role 'ESXi Hypervisor': %s (id=%s)", 'CREATED' if esxi_created else 'EXISTS', esxi_role.id)

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

    # Migrate ESXi platform devices from Server role to ESXi Hypervisor
    migrated = 0
    for dev in Device.objects.filter(platform__name__iregex=ESXI_PLATFORM_RE.pattern):
        if dev.role_id == esxi_role.id:
            continue
        dev.role = esxi_role
        dev.save(update_fields=['role'])
        migrated += 1
    if migrated:
        logger.info('  Migrated %s ESXi device(s) → ESXi Hypervisor role', migrated)

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
            'description': 'CH Stäfa proxy pair (NL, US route through CH)',
        },
        update_fields=['zabbixserver', 'description'],
    )
    for key in ('ch', *CH_PROXY_GROUP_EXTRA):
        proxy = proxies.get(key)
        if proxy is None:
            continue
        # local_address is required by nbxSync when a proxy is in a group.
        if proxy.proxygroup_id != ch_proxy_group.pk or not proxy.local_address:
            proxy.proxygroup = ch_proxy_group
            if not proxy.local_address:
                logger.warning(
                    '  %s joined CH Proxy Group but local_address is empty — set it in NetBox/Zabbix',
                    proxy.name,
                )
                proxy.local_address = proxy.local_address or '127.0.0.1'
            proxy.local_port = proxy.local_port or 10051
            proxy.save()
            logger.info('  Linked %s → CH Proxy Group (tls_accept=%s)', proxy.name, proxy.tls_accept)
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


def _rename_cg(from_names: list[str], to_name: str, description: str) -> M.ZabbixConfigurationGroup:
    """Rename the first matching legacy CG to to_name, or ensure to_name exists."""
    target = M.ZabbixConfigurationGroup.objects.filter(name=to_name).first()
    for old_name in from_names:
        legacy = M.ZabbixConfigurationGroup.objects.filter(name=old_name).first()
        if legacy is None or (target is not None and legacy.pk == target.pk):
            continue
        if target is None:
            legacy.name = to_name
            legacy.description = description
            legacy.save(update_fields=['name', 'description'])
            logger.info('  Renamed configuration group %s → %s', old_name, to_name)
            return legacy
        logger.warning('  Both %r and %r exist — using %r; retire %r manually', old_name, to_name, to_name, old_name)
        return target
    group, _ = ensure(
        M.ZabbixConfigurationGroup,
        name=to_name,
        defaults={'description': description},
        update_fields=['description'],
    )
    return group


def step4_configgroups():
    logger.info('=' * 60)
    logger.info('Step 4: Configuration Groups (multi-credential SNMP)')
    logger.info('=' * 60)
    snmp_group, _ = get_or_create(
        M.ZabbixConfigurationGroup,
        name='SNMP Monitoring',
        defaults={'description': 'SNMPv3 MONITORING MD5/DES — Extreme/Forti/AP/network roles'},
    )
    agent_group, _ = get_or_create(
        M.ZabbixConfigurationGroup,
        name='Agent Monitoring',
        defaults={'description': 'Default agent transport (assigned at top SiteGroups)'},
    )
    server_oob_group, _ = get_or_create(
        M.ZabbixConfigurationGroup,
        name='Server Agent+OOB',
        defaults={'description': 'Server: Agent @ primary + SNMP MONITORING-DELL @ oob_ip'},
    )
    # Legacy VM by SNMP / SNMP by tag → Linux credential profile CG.
    linux_snmp_group = _rename_cg(
        ['VM by SNMP', 'SNMP by tag'],
        'SNMP Monitoring (Linux)',
        'SNMPv3 MONITORING-LINUX SHA/AES — zero-touch via NetBox tag snmp',
    )
    oob_snmp_group, _ = get_or_create(
        M.ZabbixConfigurationGroup,
        name='OOB SNMP Only',
        defaults={'description': 'SNMP MONITORING MD5/DES @ oob_ip — Cohesity physical (no primary IP)'},
    )
    esxi_oob_group, _ = get_or_create(
        M.ZabbixConfigurationGroup,
        name='ESXi OOB iDRAC',
        defaults={
            'description': (
                'ESXi hypervisor: SNMP MONITORING-DELL @ oob_ip only — no agent, no VMware SDK. '
                'Hypervisor/VM metrics come from vCenter (VMware FQDN).'
            ),
        },
    )
    sap_snmp_group, _ = get_or_create(
        M.ZabbixConfigurationGroup,
        name='SAP Agent+SNMP',
        defaults={'description': 'SAP: Agent :10050 + SNMPv3 SAPUSER — dual-plane transport (one CG, both interfaces)'},
    )
    space_agent_group, _ = get_or_create(
        M.ZabbixConfigurationGroup,
        name='Agent Monitoring (SPACE)',
        defaults={'description': 'Agent port 10060 — Space Server role (camLine uses 10050)'},
    )
    huawei_snmp_group, _ = get_or_create(
        M.ZabbixConfigurationGroup,
        name='SNMP Monitoring (Huawei)',
        defaults={'description': 'SNMPv3 LogicMonitor SHA1/AES128 — Huawei OceanStor (per-device creds, non-fleet)'},
    )
    return {
        'snmp': snmp_group,
        'agent': agent_group,
        'server_oob': server_oob_group,
        'linux_snmp': linux_snmp_group,
        'oob_snmp': oob_snmp_group,
        'esxi_oob': esxi_oob_group,
        'sap_snmp': sap_snmp_group,
        'space_agent': space_agent_group,
        'huawei_snmp': huawei_snmp_group,
    }


def step5_host_interfaces(server, groups: dict):
    logger.info('=' * 60)
    logger.info('Step 5: ZabbixHostInterface (per-credential CG profiles)')
    logger.info('=' * 60)
    ct_cfg = ct(M.ZabbixConfigurationGroup)

    def ensure_if(**lookup_and_defaults):
        defaults = lookup_and_defaults.pop('defaults')
        ensure(M.ZabbixHostInterface, defaults=defaults, **lookup_and_defaults)

    def snmp_if(group, *, profile: str, use_oob_ip: bool = False):
        ensure_if(
            zabbixserver=server,
            assigned_object_type=ct_cfg,
            assigned_object_id=group.id,
            type=ZabbixHostInterfaceTypeChoices.SNMP,
            use_oob_ip=use_oob_ip,
            defaults={
                'zabbixconfigurationgroup': group,
                'interface_type': ZabbixInterfaceTypeChoices.DEFAULT,
                'port': 161,
                'useip': ZabbixInterfaceUseChoices.IP,
                'dns': '',
                **_snmp_v3_fields(profile),
            },
        )

    def snmp_v2_if(group, *, community='public', use_oob_ip: bool = False):
        ensure_if(
            zabbixserver=server,
            assigned_object_type=ct_cfg,
            assigned_object_id=group.id,
            type=ZabbixHostInterfaceTypeChoices.SNMP,
            use_oob_ip=use_oob_ip,
            defaults={
                'zabbixconfigurationgroup': group,
                'interface_type': ZabbixInterfaceTypeChoices.DEFAULT,
                'port': 161,
                'useip': ZabbixInterfaceUseChoices.IP,
                'dns': '',
                'snmp_version': ZabbixHostInterfaceSNMPVersionChoices.SNMPV2,
                'snmp_usebulk': True,
                'snmp_max_repetitions': 10,
                'snmp_community': community,
                'snmp_pushcommunity': True,
            },
        )

    def agent_if(group, *, port: int = 10050):
        ensure_if(
            zabbixserver=server,
            assigned_object_type=ct_cfg,
            assigned_object_id=group.id,
            type=ZabbixHostInterfaceTypeChoices.AGENT,
            defaults={
                'zabbixconfigurationgroup': group,
                'interface_type': ZabbixInterfaceTypeChoices.DEFAULT,
                'port': port,
                'useip': ZabbixInterfaceUseChoices.IP,
                'tls_connect': ZabbixTLSChoices.NO_ENCRYPTION,
                'dns': '',
            },
        )

    # 5.1 Network SNMP — MONITORING MD5/DES
    snmp_if(groups['snmp'], profile='network')
    # 5.2 Default agent — 10050
    agent_if(groups['agent'], port=10050)
    # 5.3 Server Agent+OOB — agent + Dell iDRAC SNMP
    agent_if(groups['server_oob'], port=10050)
    snmp_if(groups['server_oob'], profile='dell', use_oob_ip=True)
    # 5.4 Linux SNMP opt-in — MONITORING-LINUX SHA/AES
    snmp_if(groups['linux_snmp'], profile='linux')
    # 5.5 Cohesity OOB — network MONITORING
    snmp_if(groups['oob_snmp'], profile='network', use_oob_ip=True)
    # 5.5b ESXi OOB — iDRAC SNMPv2c only (no agent; VMware via vCenter)
    # iDRACs use SNMPv2c community 'public' (no SNMPv3 configured on iDRACs).
    snmp_v2_if(groups['esxi_oob'], community='public', use_oob_ip=True)
    # 5.6 SAP Agent+SNMP — dual-plane: Agent :10050 + SNMP SAPUSER (one CG, both interfaces)
    agent_if(groups['sap_snmp'], port=10050)
    snmp_if(groups['sap_snmp'], profile='sap')
    # 5.6b Huawei SNMP — LogicMonitor SHA1/AES128 (non-fleet credential)
    huawei = groups['huawei_snmp']
    ensure_if(
        zabbixserver=server,
        assigned_object_type=ct(M.ZabbixConfigurationGroup),
        assigned_object_id=huawei.id,
        type=ZabbixHostInterfaceTypeChoices.SNMP,
        use_oob_ip=False,
        defaults={
            'zabbixconfigurationgroup': huawei,
            'interface_type': ZabbixInterfaceTypeChoices.DEFAULT,
            'port': 161,
            'useip': ZabbixInterfaceUseChoices.IP,
            'dns': '',
            'snmp_version': ZabbixHostInterfaceSNMPVersionChoices.SNMPV3,
            'snmpv3_security_level': ZabbixInterfaceSNMPV3SecurityLevelChoices.AUTHPRIV,
            'snmpv3_security_name': 'LogicMonitor',
            'snmpv3_authentication_protocol': ZabbixInterfaceSNMPV3AuthProtoChoices.SHA1,
            'snmpv3_privacy_protocol': ZabbixInterfaceSNMPV3PrivProtoChoices.AES128,
            'snmpv3_authentication_passphrase': _env_first(('NBX_SNMP_AUTHPASS_HUAWEI',)),
            'snmpv3_privacy_passphrase': _env_first(('NBX_SNMP_PRIVPASS_HUAWEI',)),
            'snmp_pushcommunity': True,
        },
    )
    # 5.7 SPACE agent — 10060
    agent_if(groups['space_agent'], port=10060)

    # HostInterface must not hang on tags (interface shape lives on the CG).
    # CG→Tag assignment is the zero-touch transport selector (step 5b).
    pruned_ifs, _ = M.ZabbixHostInterface.objects.filter(
        zabbixserver=server,
        assigned_object_type=ct(Tag),
    ).delete()
    if pruned_ifs:
        logger.info('  PRUNED: %s tag-targeted HostInterface(s)', pruned_ifs)


def step5b_configgroup_assignments(groups: dict, country_slugs=None):
    """SiteGroup Agent default; network SNMP roles; tag/role zero-touch overrides."""
    logger.info('=' * 60)
    logger.info('Step 5b: ConfigurationGroupAssignment (zero-touch)')
    logger.info('=' * 60)
    country_slugs = country_slugs or COUNTRY_SLUGS
    snmp_group = groups['snmp']
    agent_group = groups['agent']
    server_oob_group = groups['server_oob']
    linux_snmp_group = groups['linux_snmp']
    oob_snmp_group = groups['oob_snmp']
    esxi_oob_group = groups['esxi_oob']
    sap_snmp_group = groups['sap_snmp']
    space_agent_group = groups['space_agent']

    for slug in country_slugs:
        sg = get_sitegroup(slug)
        get_or_create(
            M.ZabbixConfigurationGroupAssignment,
            zabbixconfigurationgroup=agent_group,
            assigned_object_type=ct(SiteGroup),
            assigned_object_id=sg.id,
            defaults={},
        )
    logger.info('  Agent Monitoring → %s top SiteGroups', len(country_slugs))

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

    def assign_tag(group, slug: str, name: str | None = None):
        tag = Tag.objects.filter(slug=slug).first() or Tag.objects.filter(name=name or slug).first()
        if tag is None:
            tag = Tag.objects.create(slug=slug, name=name or slug)
        get_or_create(
            M.ZabbixConfigurationGroupAssignment,
            zabbixconfigurationgroup=group,
            assigned_object_type=ct(Tag),
            assigned_object_id=tag.id,
            defaults={},
        )
        logger.info('  %s → NetBox tag %s (zero-touch opt-in)', group.name, slug)

    def assign_manufacturer(group, *names: str):
        """Assign CG to the first matching Manufacturer (inheritance beats Site Group Agent)."""
        mfr = None
        for name in names:
            mfr = (
                Manufacturer.objects.filter(name__iexact=name).first()
                or Manufacturer.objects.filter(slug__iexact=name.lower().replace(' ', '-')).first()
            )
            if mfr is not None:
                break
        if mfr is None:
            logger.warning('  Manufacturer not found (%s) — skip CG %s', '/'.join(names), group.name)
            return
        get_or_create(
            M.ZabbixConfigurationGroupAssignment,
            zabbixconfigurationgroup=group,
            assigned_object_type=ct(Manufacturer),
            assigned_object_id=mfr.id,
            defaults={},
        )
        logger.info('  %s → Manufacturer %s (SNMP storage; beats Site Group Agent)', group.name, mfr.name)

    for role_name in SNMP_ROLES:
        assign_role(snmp_group, role_name)
    for role_name in SERVER_BMC_ROLES:
        # Cohesity goes to OOB SNMP Only (no primary_ip4 — only oob_ip)
        if role_name == 'Cohesity':
            assign_role(oob_snmp_group, role_name)
            continue
        assign_role(server_oob_group, role_name)

    assign_role(space_agent_group, 'Space Server')

    # ESXi Hypervisor role → ESXi OOB iDRAC CG (SNMP only on oob_ip, no Agent)
    assign_role(esxi_oob_group, 'ESXi Hypervisor')

    # SAP HANA and SAP ME: single dual-plane CG (Agent + SNMP in one CG).
    # No separate Agent Monitoring assignment — the SAP Agent+SNMP CG has both interfaces.
    assign_role(sap_snmp_group, 'SAP HANA')
    assign_role(sap_snmp_group, 'SAP ME')

    # Prune stale Agent Monitoring CG assignments from SAP roles (now in SAP Agent+SNMP CG).
    for role_name in ('SAP HANA', 'SAP ME'):
        role = get_role(role_name)
        if role:
            stale_agent = M.ZabbixConfigurationGroupAssignment.objects.filter(
                zabbixconfigurationgroup=agent_group,
                assigned_object_type=ct(DeviceRole),
                assigned_object_id=role.id,
            ).delete()
            if stale_agent[0]:
                logger.info('  PRUNED: Agent Monitoring from %s (now in SAP Agent+SNMP CG)', role_name)
    # Rename old CG if it exists
    old_sap_cg = M.ZabbixConfigurationGroup.objects.filter(name='SNMP Monitoring (SAP)').first()
    if old_sap_cg:
        old_sap_cg.name = 'SAP Agent+SNMP'
        old_sap_cg.description = 'SAP: Agent :10050 + SNMPv3 SAPUSER — dual-plane transport (one CG, both interfaces)'
        old_sap_cg.save(update_fields=['name', 'description'])
        logger.info('  RENAMED: SNMP Monitoring (SAP) → SAP Agent+SNMP')

    # Tag inheritance is collected before role/site — snmp beats Agent default.
    assign_tag(linux_snmp_group, 'snmp', 'snmp')
    logger.info('  NOTE: Dell iDRAC template = TemplateRule Dell∧Server / ESXi (§6); OOB creds = MONITORING-DELL')

    # ESXi OOB iDRAC CG is now assigned on the ESXi Hypervisor role (line 960),
    # not on the platform. Prune stale platform-level assignments.
    esxi_platforms = [p for p in Platform.objects.all() if ESXI_PLATFORM_RE.search(p.name or '')]
    for plat in esxi_platforms:
        stale, _ = M.ZabbixConfigurationGroupAssignment.objects.filter(
            zabbixconfigurationgroup=esxi_oob_group,
            assigned_object_type=ct(Platform),
            assigned_object_id=plat.id,
        ).delete()
        if stale:
            logger.info('  PRUNED: ESXi OOB iDRAC platform assignment on %s (now role-based)', plat.name)

    # SNMP storage manufacturers — Site Group Agent would leave them without SNMP.
    # Manufacturer CG wins first in inheritance → SNMP Monitoring (network MONITORING).
    # Pure / HPE stay on Agent default (HTTP templates).
    # Huawei gets its own CG (SNMP Monitoring (Huawei)) with LogicMonitor SHA/AES
    # credentials — different from the fleet SNMP Monitoring (MONITORING MD5/DES).
    assign_manufacturer(snmp_group, 'Synology')

    # HU-DEB-SAN01 (Huawei storage): assign the Huawei-specific SNMP CG directly
    # on the device. This overrides the SiteGroup Agent Monitoring default (same
    # way switches get SNMP Monitoring via their role). The Huawei CG has its own
    # HostInterface with LogicMonitor SHA1/AES128 credentials.
    huawei_san01 = Device.objects.filter(name__iexact='HU-DEB-SAN01').first()
    if huawei_san01:
        get_or_create(
            M.ZabbixConfigurationGroupAssignment,
            zabbixconfigurationgroup=groups['huawei_snmp'],
            assigned_object_type=ct(Device),
            assigned_object_id=huawei_san01.id,
            defaults={},
        )
        logger.info('  HU-DEB-SAN01 → SNMP Monitoring (Huawei) with LogicMonitor SHA/AES')

    # §5.5b Cohesity VMs with primary_ip4 → SNMP Monitoring (not OOB SNMP Only,
    # which is for physical nodes with only oob_ip — VMs have no oob_ip).
    cohesity_vms = list(
        VirtualMachine.objects.filter(
            role__name__iexact='Cohesity',
            status='active',
            primary_ip4__isnull=False,
        )
    )
    for vm in cohesity_vms:
        get_or_create(
            M.ZabbixConfigurationGroupAssignment,
            zabbixconfigurationgroup=snmp_group,
            assigned_object_type=ct(VirtualMachine),
            assigned_object_id=vm.id,
            defaults={},
        )

    # Prune SNMP Monitoring CG from roles no longer in SNMP_ROLES (e.g. Storage
    # removed because Pure arrays use HTTP, not SNMP).
    snmp_role_ids = set()
    for name in SNMP_ROLES:
        role = DeviceRole.objects.filter(name__iexact=name).first()
        if role:
            snmp_role_ids.add(role.id)
    leftover_snmp = M.ZabbixConfigurationGroupAssignment.objects.filter(
        zabbixconfigurationgroup=snmp_group,
        assigned_object_type=ct(DeviceRole),
    ).exclude(assigned_object_id__in=snmp_role_ids)
    if leftover_snmp.exists():
        deleted, _ = leftover_snmp.delete()
        logger.info('  PRUNED: %s SNMP Monitoring CG assignment(s) from roles no longer in SNMP_ROLES', deleted)

    # Prune stale Huawei manufacturer CG assignment (replaced by Huawei-specific CG).
    huawei = Manufacturer.objects.filter(name__iexact='Huawei').first()
    if huawei:
        stale_huawei_cg = M.ZabbixConfigurationGroupAssignment.objects.filter(
            zabbixconfigurationgroup=snmp_group,
            assigned_object_type=ct(Manufacturer),
            assigned_object_id=huawei.id,
        )
        deleted, _ = stale_huawei_cg.delete()
        if deleted:
            logger.info('  PRUNED: Huawei manufacturer SNMP CG (replaced by SNMP Monitoring (Huawei) CG)')

    # Prune stale fleet SNMP Monitoring CG on HU-DEB-SAN01 (replaced by Huawei CG).
    if huawei_san01:
        stale_dev_snmp = M.ZabbixConfigurationGroupAssignment.objects.filter(
            zabbixconfigurationgroup=snmp_group,
            assigned_object_type=ct(Device),
            assigned_object_id=huawei_san01.id,
        )
        deleted, _ = stale_dev_snmp.delete()
        if deleted:
            logger.info('  PRUNED: fleet SNMP Monitoring CG from HU-DEB-SAN01 (replaced by Huawei CG)')

    # Prune stale per-device HostInterface on HU-DEB-SAN01 (credentials now on the CG).
    if huawei_san01:
        stale_hi = M.ZabbixHostInterface.objects.filter(
            zabbixserver=server,
            assigned_object_type=ct(Device),
            assigned_object_id=huawei_san01.id,
        )
        deleted, _ = stale_hi.delete()
        if deleted:
            logger.info('  PRUNED: per-device HostInterface on HU-DEB-SAN01 (now on Huawei CG)')
    if cohesity_vms:
        logger.info('  %s Cohesity VM(s) → SNMP Monitoring (direct override, have primary_ip4)', len(cohesity_vms))


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
                'description': description,
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

    # Keep description empty — membership comes from TemplateRules; long essays clutter the GUI.
    hg_os_windows = hg('OS/Windows', 'OS/Windows')
    hg_os_linux = hg('OS/Linux', 'OS/Linux')
    hg_os_network = hg('OS/Network', 'OS/Network')
    hg_os_vmware = hg('OS/VMware', 'OS/VMware')

    tpl_windows = make_template(*TPL['windows_agent'], req=[HostInterfaceRequirementChoices.AGENT])
    tpl_linux = make_template(*TPL['linux_agent'], req=[HostInterfaceRequirementChoices.AGENT])
    tpl_linux_snmp = make_template(*TPL['linux_snmp'], req=[HostInterfaceRequirementChoices.SNMP])
    tpl_windows_snmp = make_template(*TPL['windows_snmp'], req=[HostInterfaceRequirementChoices.SNMP])
    tpl_exos = make_template(*TPL['extreme_exos_snmp'], req=[HostInterfaceRequirementChoices.SNMP])
    tpl_netgeneric = make_template(*TPL['network_generic_snmp'], req=[HostInterfaceRequirementChoices.SNMP])
    tpl_fortigate = make_template(*TPL['fortigate_snmp'], req=[HostInterfaceRequirementChoices.SNMP])
    # VMware FQDN is vCenter-role only (step 7) — not linked via ESXi platform rules.
    # Extreme VOSS / IQ Engine: optional templates, fall back to Network Generic when missing.
    _voss_tpl = TPL.get('extreme_voss_snmp') or TPL['network_generic_snmp']
    _iq_tpl = TPL.get('extreme_iq_engine_snmp') or TPL['network_generic_snmp']
    tpl_voss = make_template(*_voss_tpl, req=[HostInterfaceRequirementChoices.SNMP])
    tpl_iq = make_template(*_iq_tpl, req=[HostInterfaceRequirementChoices.SNMP])
    rules = [
        ('Windows Server', r'Windows Server', tpl_windows, hg_os_windows, 50),
        ('Windows catch-all', r'Windows', tpl_windows, hg_os_windows, 200),
        ('Linux', r'Ubuntu|Debian|Linux|Red Hat|CentOS|Alma|SUSE|Arch|Photon|Other.*Linux', tpl_linux, hg_os_linux, 100),
        ('Extreme VOSS', r'VOSS', tpl_voss, hg_os_network, 100),
        ('Extreme IQ Engine', r'IQ ENGINE', tpl_iq, hg_os_network, 100),

        ('FortiOS', r'FORTIOS|FortiOS', tpl_fortigate, hg_os_network, 100),
        ('FortiAnalyzer/Manager', r'FortiAnalyzer|FortiManager', tpl_netgeneric, hg_os_network, 50),
        # Photon guests / appliances — Linux agent (not ESXi hypervisors).
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
            'role_pattern': '',
            'manufacturer': None,
        }
        ensure(M.ZabbixTemplateRule, name=name, defaults=defaults, update_fields=list(defaults.keys()))

    # Legacy: VMware FQDN on ESXi platform — hypervisors are discovered from vCenter only.
    legacy_esxi_vmware = M.ZabbixTemplateRule.objects.filter(name='VMware ESXi').first()
    if legacy_esxi_vmware is not None and legacy_esxi_vmware.enabled:
        legacy_esxi_vmware.enabled = False
        legacy_esxi_vmware.save(update_fields=['enabled'])
        logger.info('  DISABLED legacy TemplateRule %r (VMware FQDN is vCenter-only)', 'VMware ESXi')

    # Δ6b: NetBox tag snmp → OS-correct SNMP templates.
    # Pair with "SNMP Monitoring (Linux)" CG (assigned on the same tag) for the interface.
    # HostSync drops agent templates when only SNMP IF is present (and vice versa).
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
            'role_pattern': '',
            'manufacturer': None,
            'enabled': True,
            'priority': 40,
        }
        ensure(M.ZabbixTemplateRule, name=name, defaults=defaults, update_fields=list(defaults.keys()))

    # Oracle: tag-gated TemplateRule — tag any VM/Device with 'oracle' tag to get
    # Oracle by Zabbix agent 2. Merges with OS template from platform rule (Linux/Windows).
    tpl_oracle = make_template(*TPL['oracle_agent2'], req=[HostInterfaceRequirementChoices.AGENT])
    ensure(
        M.ZabbixTemplateRule,
        name='Oracle (tag)',
        defaults={
            'pattern': '.*',
            'zabbixtemplate': tpl_oracle,
            'zabbixhostgroup': None,
            'zabbixtag': None,
            'require_tags': 'oracle',
            'role_pattern': '',
            'manufacturer': None,
            'enabled': True,
            'priority': 40,
        },
        update_fields=['pattern', 'zabbixtemplate', 'zabbixhostgroup', 'zabbixtag', 'require_tags', 'role_pattern', 'manufacturer', 'enabled', 'priority'],
    )
    logger.info('  Rule Oracle (tag) → %s', tpl_oracle.name)

    # Dell iDRAC: Manufacturer ∧ Server role (no NetBox tag). Additive merge means
    # Manufacturer-wide assignment is too wide — keep OEM templates on Device type.
    dell = Manufacturer.objects.filter(name='Dell').first() or Manufacturer.objects.filter(slug='dell').first()
    tpl_idrac = make_template(*TPL['dell_idrac_snmp'], req=[HostInterfaceRequirementChoices.SNMP])
    if dell is not None:
        defaults = {
            'pattern': '.*',
            'role_pattern': '^Server$',
            'require_tags': '',
            'manufacturer': dell,
            'zabbixtemplate': tpl_idrac,
            'zabbixhostgroup': None,
            'zabbixtag': None,
            'enabled': True,
            'priority': 80,
        }
        ensure(M.ZabbixTemplateRule, name='Dell iDRAC (Server)', defaults=defaults, update_fields=list(defaults.keys()))
        # ESXi hypervisors: iDRAC + OS/VMware hostgroup (no VMware FQDN template).
        defaults_esxi = {
            'pattern': r'ESXi|VMware ESX',
            'role_pattern': '',
            'require_tags': '',
            'manufacturer': dell,
            'zabbixtemplate': tpl_idrac,
            'zabbixhostgroup': hg_os_vmware,
            'zabbixtag': None,
            'enabled': True,
            'priority': 80,
        }
        ensure(M.ZabbixTemplateRule, name='Dell iDRAC (ESXi)', defaults=defaults_esxi, update_fields=list(defaults_esxi.keys()))
        logger.info('  Rule Dell iDRAC (ESXi) → %s + OS/VMware', tpl_idrac.name)
        # Prune legacy Manufacturer-wide iDRAC assignment if present.
        deleted, _ = M.ZabbixTemplateAssignment.objects.filter(
            zabbixtemplate=tpl_idrac,
            assigned_object_type=ct(Manufacturer),
            assigned_object_id=dell.id,
        ).delete()
        if deleted:
            logger.info('  PRUNED: %s Manufacturer-wide Dell iDRAC assignment(s)', deleted)
    else:
        logger.warning("  Manufacturer 'Dell' not found, skipping Dell iDRAC TemplateRule")

    # Pure Storage: Manufacturer → FlashArray by HTTP (v2 preferred; v1 alias).
    # Arrays use role=Storage; stay on Site Group Agent (HTTP / ANY). Not SNMP CG.
    pure = Manufacturer.objects.filter(name='Pure Storage').first() or Manufacturer.objects.filter(slug__iexact='pure-storage').first()
    tpl_pure = make_template(*TPL['pure_storage_http'], req=[HostInterfaceRequirementChoices.ANY])
    if pure is not None:
        defaults = {
            'pattern': '.*',
            'role_pattern': '',
            'require_tags': '',
            'manufacturer': pure,
            'zabbixtemplate': tpl_pure,
            'zabbixhostgroup': None,
            'zabbixtag': None,
            'enabled': True,
            'priority': 80,
        }
        ensure(M.ZabbixTemplateRule, name='Pure Storage (HTTP)', defaults=defaults, update_fields=list(defaults.keys()))
        logger.info('  Rule Pure Storage (HTTP) → %s', tpl_pure.name)
    else:
        logger.warning("  Manufacturer 'Pure Storage' not found, skipping Pure Storage TemplateRule")

    # Dell Storage: Manufacturer Dell ∧ role Storage → HPE MSA 2060 Storage by HTTP.
    # Estate uses that template on Dell arrays (no separate Dell Storage by HTTP import).
    # No HPE manufacturer rule — HPE MSA mapping removed.
    legacy_hpe_msa = M.ZabbixTemplateRule.objects.filter(name='HPE MSA (HTTP)').first()
    if legacy_hpe_msa is not None and legacy_hpe_msa.enabled:
        legacy_hpe_msa.enabled = False
        legacy_hpe_msa.save(update_fields=['enabled'])
        logger.info('  DISABLED legacy TemplateRule %r (HPE MSA template is for Dell Storage)', 'HPE MSA (HTTP)')

    dell_mfr = Manufacturer.objects.filter(name='Dell').first() or Manufacturer.objects.filter(slug__iexact='dell').first()
    if 'hpe_msa_http' in TPL:
        tpl_msa_http = make_template(*TPL['hpe_msa_http'], req=[HostInterfaceRequirementChoices.ANY])
        if dell_mfr is not None:
            defaults = {
                'pattern': '.*', 'role_pattern': '^Storage$', 'require_tags': '',
                'manufacturer': dell_mfr, 'zabbixtemplate': tpl_msa_http,
                'zabbixhostgroup': None, 'zabbixtag': None, 'enabled': True, 'priority': 80,
            }
            ensure(M.ZabbixTemplateRule, name='Dell Storage (HTTP)', defaults=defaults, update_fields=list(defaults.keys()))
            logger.info('  Rule Dell Storage (HTTP) → %s', tpl_msa_http.name)
        else:
            logger.warning("  Manufacturer 'Dell' not found, skipping Dell Storage TemplateRule")
    else:
        logger.warning('  Template HPE MSA 2060 Storage by HTTP not resolved — skip Dell Storage TemplateRule')

    # Huawei OceanStor Dorado by SNMP (hu-deb-san01). Transport: SNMP CG on Manufacturer.
    huawei = Manufacturer.objects.filter(name='Huawei').first() or Manufacturer.objects.filter(slug__iexact='huawei').first()
    if 'huawei_storage_snmp' in TPL:
        tpl_huawei = make_template(*TPL['huawei_storage_snmp'], req=[HostInterfaceRequirementChoices.SNMP])
        if huawei is not None:
            defaults = {
                'pattern': '.*', 'role_pattern': '^Storage$', 'require_tags': '',
                'manufacturer': huawei, 'zabbixtemplate': tpl_huawei,
                'zabbixhostgroup': None, 'zabbixtag': None, 'enabled': True, 'priority': 80,
            }
            ensure(M.ZabbixTemplateRule, name='Huawei OceanStor (SNMP)', defaults=defaults, update_fields=list(defaults.keys()))
            logger.info('  Rule Huawei OceanStor (SNMP) → %s', tpl_huawei.name)
        else:
            logger.warning("  Manufacturer 'Huawei' not found, skipping Huawei TemplateRule")
    else:
        logger.warning('  Template Huawei OceanStor Dorado by SNMP not resolved — skip TemplateRule')

    # Synology DiskStation SNMPv3 (hu-deb-p-snas01). Transport: SNMP CG on Manufacturer.
    synology = Manufacturer.objects.filter(name='Synology').first() or Manufacturer.objects.filter(slug__iexact='synology').first()
    if 'synology_storage_snmp' in TPL:
        tpl_synology = make_template(*TPL['synology_storage_snmp'], req=[HostInterfaceRequirementChoices.SNMP])
        if synology is not None:
            defaults = {
                'pattern': '.*', 'role_pattern': '^Storage$', 'require_tags': '',
                'manufacturer': synology, 'zabbixtemplate': tpl_synology,
                'zabbixhostgroup': None, 'zabbixtag': None, 'enabled': True, 'priority': 80,
            }
            ensure(M.ZabbixTemplateRule, name='Synology DiskStation (SNMP)', defaults=defaults, update_fields=list(defaults.keys()))
            logger.info('  Rule Synology DiskStation (SNMP) → %s', tpl_synology.name)
            if 'icmp_ping' in TPL:
                tpl_icmp = make_template(*TPL['icmp_ping'], req=[HostInterfaceRequirementChoices.ANY])
                defaults_icmp = {
                    'pattern': '.*', 'role_pattern': '^Storage$', 'require_tags': '',
                    'manufacturer': synology, 'zabbixtemplate': tpl_icmp,
                    'zabbixhostgroup': None, 'zabbixtag': None, 'enabled': True, 'priority': 85,
                }
                ensure(M.ZabbixTemplateRule, name='Synology Storage ICMP', defaults=defaults_icmp, update_fields=list(defaults_icmp.keys()))
        else:
            logger.warning("  Manufacturer 'Synology' not found, skipping Synology TemplateRule")
    else:
        logger.warning('  Template Synology DiskStation SNMPv3 not resolved — skip TemplateRule')

    # Prune legacy Huawei Storage ICMP rule — Huawei OceanStor Dorado template
    # already defines icmpping items; adding ICMP Ping causes duplicate key collision.
    legacy_huawei_icmp = M.ZabbixTemplateRule.objects.filter(name='Huawei Storage ICMP').first()
    if legacy_huawei_icmp is not None:
        legacy_huawei_icmp.delete()
        logger.info('  DELETED legacy TemplateRule %r (Huawei template already has icmpping)', 'Huawei Storage ICMP')

    # Zabbix Proxy role: proxy VMs (role=Zabbix Proxy via netbox-sync -ZABP\d+ pattern).
    # Platform rule already gives them Linux by Zabbix agent (Ubuntu). These two
    # add-on templates provide ICMP reachability + Zabbix's stock proxy-health metrics
    # (last access, version mismatch, config sync latency, performance counters).
    if 'icmp_ping' in TPL:
        tpl_icmp_proxy = make_template(*TPL['icmp_ping'], req=[HostInterfaceRequirementChoices.ANY])
        ensure(
            M.ZabbixTemplateRule,
            name='Zabbix Proxy ICMP',
            defaults={
                'pattern': '.*',
                'role_pattern': '^Zabbix Proxy$',
                'require_tags': '',
                'manufacturer': None,
                'zabbixtemplate': tpl_icmp_proxy,
                'zabbixhostgroup': None,
                'zabbixtag': None,
                'enabled': True,
                'priority': 90,
            },
            update_fields=['pattern', 'role_pattern', 'require_tags', 'manufacturer', 'zabbixtemplate', 'zabbixhostgroup', 'zabbixtag', 'enabled', 'priority'],
        )
        logger.info('  Rule Zabbix Proxy ICMP → %s', tpl_icmp_proxy.name)
    if 'proxy_health' in TPL:
        tpl_health = make_template(*TPL['proxy_health'], req=[HostInterfaceRequirementChoices.ANY])
        ensure(
            M.ZabbixTemplateRule,
            name='Zabbix Proxy Health',
            defaults={
                'pattern': '.*',
                'role_pattern': '^Zabbix Proxy$',
                'require_tags': '',
                'manufacturer': None,
                'zabbixtemplate': tpl_health,
                'zabbixhostgroup': None,
                'zabbixtag': None,
                'enabled': True,
                'priority': 90,
            },
            update_fields=['pattern', 'role_pattern', 'require_tags', 'manufacturer', 'zabbixtemplate', 'zabbixhostgroup', 'zabbixtag', 'enabled', 'priority'],
        )
        logger.info('  Rule Zabbix Proxy Health → %s', tpl_health.name)

    # ICMP Ping for agent-monitored hosts — distinguishes "host down" from "agent down".
    # SNMP templates usually embed icmpping, but Linux/Windows agent templates do not.
    if 'icmp_ping' in TPL:
        tpl_icmp_agent = make_template(*TPL['icmp_ping'], req=[HostInterfaceRequirementChoices.ANY])
        ensure(
            M.ZabbixTemplateRule,
            name='Agent Host ICMP',
            defaults={
                'pattern': '.*',
                'role_pattern': '^(Server|Domain Controller|Fileserver|MSSQL|MSSQL Query Server|Tableau|GitLab|GitHub Runner|TeamCity|HLK|SCCM|PKI|NAC|Acronis Management|VDI|Session Host|Connection Broker|Azure Data Factory|FiveTran|CellMap|Production Backup|Solidworks PDM|Subversion|vCenter|SAP HANA|SAP ME|Space Server)$',
                'require_tags': '',
                'manufacturer': None,
                'zabbixtemplate': tpl_icmp_agent,
                'zabbixhostgroup': None,
                'zabbixtag': None,
                'enabled': True,
                'priority': 95,
            },
            update_fields=['pattern', 'role_pattern', 'require_tags', 'manufacturer', 'zabbixtemplate', 'zabbixhostgroup', 'zabbixtag', 'enabled', 'priority'],
        )
        logger.info('  Rule Agent Host ICMP → %s', tpl_icmp_agent.name)

    # Rename leftovers from placeholder template names.
    for old_name in ('Huawei Storage (SNMP)', 'Synology NAS (SNMP)'):
        stale = M.ZabbixTemplateRule.objects.filter(name=old_name).first()
        if stale is not None:
            stale.enabled = False
            stale.save(update_fields=['enabled'])
            logger.info('  DISABLED legacy TemplateRule %r (replaced by production names)', old_name)

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
        (make_template(*TPL['mssql_agent2'], req=[HostInterfaceRequirementChoices.AGENT]), 'MSSQL'),
        (make_template(*TPL['mssql_agent2'], req=[HostInterfaceRequirementChoices.AGENT]), 'MSSQL Query Server'),
        (make_template(*TPL['vmware_fqdn'], req=[HostInterfaceRequirementChoices.ANY]), 'vCenter'),
        # VMware FQDN is ONLY on vCenter. ESXi: ESXi OOB iDRAC CG + Dell iDRAC TemplateRule.
        # Pure Storage: no role assignment — HTTP template is manufacturer TemplateRule (step 6).
        (make_template(*TPL['gitlab_http'], req=[HostInterfaceRequirementChoices.ANY]), 'GitLab'),
        (make_template(*TPL['linux_snmp'], req=[HostInterfaceRequirementChoices.SNMP]), 'Virtual Appliance'),
        # Network Generic only on Network Device (no platform / no regex match).
        # Switch*/AP must NOT get this floor — EXOS (etc.) TemplateRules already attach
        # specialized templates; pairing both yields duplicate icmpping item keys.
        (make_template(*TPL['network_generic_snmp'], req=[HostInterfaceRequirementChoices.SNMP]), 'Network Device'),
        # Storage Generic only on Cohesity — Storage role gets manufacturer-specific templates via §6.3
        (make_template(*TPL['storage_generic_snmp'], req=[HostInterfaceRequirementChoices.SNMP]), 'Cohesity'),
        (make_template(*TPL['fortigate_snmp'], req=[HostInterfaceRequirementChoices.SNMP]), 'Firewall'),
        # Placeholder application templates — LM parity. Items built post-cutover,
        # but the template is linked so hosts are discoverable in Zabbix.
        # AS Java: only on 2 hosts (ch-sta-*-as01/02, role=Server). Not assignable by role.
        (make_template(*TPL['tableau_bridge_agent'], req=[HostInterfaceRequirementChoices.AGENT]), 'Tableau'),
        (make_template(*TPL['cellmap_agent'], req=[HostInterfaceRequirementChoices.AGENT]), 'CellMap'),
        (make_template(*TPL['oracle_agent2'], req=[HostInterfaceRequirementChoices.AGENT]), 'Database'),  # Oracle if role exists
        (make_template(*TPL['sap_agent'], req=[HostInterfaceRequirementChoices.AGENT]), 'SAP ME'),
        (make_template(*TPL['sap_agent'], req=[HostInterfaceRequirementChoices.AGENT]), 'SAP HANA'),
        (make_template(*TPL['acronis_agent'], req=[HostInterfaceRequirementChoices.AGENT]), 'Acronis Management'),
        (make_template(*TPL['sccm_agent'], req=[HostInterfaceRequirementChoices.AGENT]), 'SCCM'),
        # Oracle: tag-gated, not role-based. Tag VMs with 'oracle' tag.
        # (make_template(*TPL['oracle_agent2'], req=[HostInterfaceRequirementChoices.AGENT]), 'Database'),  # Removed — role doesn't exist
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

    # Prune legacy MSSQL by ODBC assignments (replaced by MSSQL by Zabbix agent 2).
    old_mssql_tpl = M.ZabbixTemplate.objects.filter(name='MSSQL by ODBC').first()
    if old_mssql_tpl:
        deleted, _ = M.ZabbixTemplateAssignment.objects.filter(
            zabbixtemplate=old_mssql_tpl,
            assigned_object_type=ct(DeviceRole),
        ).delete()
        if deleted:
            logger.info('  PRUNED: %s MSSQL by ODBC assignment(s) (replaced by Agent 2)', deleted)

    # Prune legacy Pure Storage role assignment (replaced by manufacturer-scoped TemplateRule).
    old_pure_tpl = M.ZabbixTemplate.objects.filter(name=TPL['pure_storage_http'][1] if isinstance(TPL['pure_storage_http'], tuple) else 'Pure Storage FlashArray v1 by HTTP').first()
    if old_pure_tpl:
        deleted, _ = M.ZabbixTemplateAssignment.objects.filter(
            zabbixtemplate=old_pure_tpl,
            assigned_object_type=ct(DeviceRole),
        ).delete()
        if deleted:
            logger.info('  PRUNED: %s Pure Storage role assignment(s) (replaced by manufacturer TemplateRule)', deleted)

    # Prune legacy Storage Generic assignment from Storage role — manufacturer-specific
    # templates (Dell HTTP, Huawei SNMP, Pure HTTP, Synology SNMP) now cover it via §6.3.
    old_storage_tpl = M.ZabbixTemplate.objects.filter(name='Storage Generic Device by SNMP').first()
    if old_storage_tpl:
        storage_role = DeviceRole.objects.filter(name__iexact='Storage').first()
        if storage_role:
            deleted, _ = M.ZabbixTemplateAssignment.objects.filter(
                zabbixtemplate=old_storage_tpl,
                assigned_object_type=ct(DeviceRole),
                assigned_object_id=storage_role.id,
            ).delete()
            if deleted:
                logger.info('  PRUNED: %s Storage Generic assignment(s) from Storage role (manufacturer rules cover it)', deleted)

    # Prune legacy Switch*/AP → Network Generic floors (icmpping collision with EXOS/etc.).
    tpl_netgeneric = make_template(*TPL['network_generic_snmp'], req=[HostInterfaceRequirementChoices.SNMP])
    for role_name in ('Switch Core', 'Switch Dist', 'Switch Access', 'Switch Mgmt', 'Access Point'):
        try:
            role = get_role(role_name)
        except DeviceRole.DoesNotExist:
            continue
        deleted, _ = M.ZabbixTemplateAssignment.objects.filter(
            zabbixtemplate=tpl_netgeneric,
            assigned_object_type=ct(DeviceRole),
            assigned_object_id=role.id,
        ).delete()
        if deleted:
            logger.info('  PRUNED: %s Network Generic assignment(s) from role %s', deleted, role_name)

    # Dell iDRAC is scoped via TemplateRule (step 6: Dell ∧ Server), not Manufacturer.

    # Transport-only CGs — prune leftover CG→template links
    # (Linux/Windows by SNMP come from tag compound TemplateRules in step 6).
    for cg_name_suffix in ('VM by SNMP', 'SNMP by tag', 'SNMP Monitoring (Linux)', 'SNMP Monitoring (SAP)'):
        for cg in M.ZabbixConfigurationGroup.objects.filter(name__endswith=cg_name_suffix):
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
        defaults={
            'value': ('Sites/{{ object.site.group.get_ancestors(include_self=True) | map(attribute="name") | join("/") }}/{{ object.site.name }}'),
        },
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
        '{% set n = object.name | lower -%}\n{%- if "-p-" in n or n.endswith("-p") or "-p0" in n or "-p1" in n -%}Production\n{%- elif "-d-" in n -%}Development\n{%- elif "-q-" in n -%}QA\n{%- elif "-s-" in n -%}Sandbox\n{%- elif "-t-" in n -%}Test\n{%- elif "vdi" in n -%}VDI\n{%- else -%}Unknown\n{%- endif -%}'
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
    'url_a': '{% if object.device_type %}https://netbox.sensirion.lokal/dcim/devices/{{ object.id }}/{% else %}https://netbox.sensirion.lokal/virtualization/virtual-machines/{{ object.id }}/{% endif %}',
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


def _ensure_macro_assignment(server, macro_name, value, obj, mtype=ZabbixMacroTypeChoices.SECRET, description=''):
    """Create server-level ZabbixMacro + ZabbixMacroAssignment on obj.

    ZabbixMacro.assigned_object must be ZabbixServer (per MACRO_ASSIGNMENT_MODELS).
    ZabbixMacroAssignment.assigned_object is the Device/DeviceRole/VM that inherits it.
    """
    # 1. Server-level macro definition
    macro, _ = ensure(
        M.ZabbixMacro,
        macro=macro_name,
        assigned_object_type=ct(M.ZabbixServer),
        assigned_object_id=server.id,
        defaults={'value': '', 'type': mtype,
                  'description': description or f'ztc:{macro_name}'},
        update_fields=['type', 'description'],
    )
    # 2. Assignment on the target object (carries the actual value)
    ensure(
        M.ZabbixMacroAssignment,
        zabbixmacro=macro,
        assigned_object_type=ContentType.objects.get_for_model(type(obj)),
        assigned_object_id=obj.id,
        defaults={'value': value, 'is_regex': False, 'context': ''},
        update_fields=['value', 'is_regex', 'context'],
    )
    return macro


def step11_macros(server):
    logger.info('=' * 60)
    logger.info('Step 11: ZabbixMacros')
    logger.info('=' * 60)
    prune_shadow_macros()

    # ---- Text macros (role-level) ----
    text_specs = [
        ('{$CPU.UTIL.CRIT}', '90', 'MSSQL'),
        ('{$CPU.UTIL.CRIT}', '80', 'Server'),
        ('{$MEM.UTIL.CRIT}', '85', 'VDI'),
        ('{$MSSQL.DSN}', 'nbxsync', 'MSSQL'),
        ('{$VMWARE.URL}', 'https://{{ object.name }}/sdk', 'vCenter'),
    ]
    for macro_name, macro_value, role_name in text_specs:
        try:
            role = get_role(role_name)
        except DeviceRole.DoesNotExist:
            logger.warning('  Role not found: %s, skipping macro %s', role_name, macro_name)
            continue
        _ensure_macro_assignment(
            server, macro_name, macro_value, role,
            mtype=ZabbixMacroTypeChoices.TEXT, description=f'ztc:{role_name}')

    # ---- Secret macros: Pure Storage (per-device) ----
    # Each array has its own API token. Assignment is on the Device.
    # Env vars: NBX_PURE_TOKEN_<HOSTNAME> (uppercased, dashes→underscores).
    pure_arrays = Device.objects.filter(
        device_type__manufacturer__name__iexact='Pure Storage'
    )
    for dev in pure_arrays:
        env_key = f'NBX_PURE_TOKEN_{dev.name.upper().replace("-", "_")}'
        token = os.environ.get(env_key, '')
        if token:
            _ensure_macro_assignment(
                server, '{$PURE.FLASHARRAY.API.TOKEN}', token, dev,
                description=f'ztc:secret:pure:{dev.name}')
            # The template script appends 'api/{version}/login' to this URL.
            # Base URL only — no /api path. Script adds trailing '/' if missing.
            api_url = f'https://{dev.primary_ip4.address.ip}/' if dev.primary_ip4 else f'https://{dev.name}/'
            _ensure_macro_assignment(
                server, '{$PURE.FLASHARRAY.API.URL}', api_url, dev,
                mtype=ZabbixMacroTypeChoices.TEXT,
                description=f'ztc:pure-url:{dev.name}')
            logger.info('  Macros {$PURE.FLASHARRAY.API.TOKEN}/{$PURE.FLASHARRAY.API.URL} on %s', dev.name)
        else:
            logger.warning('  Env var %s not set — Pure array %s will have no API token', env_key, dev.name)

    # ---- Secret macros: VMware vCenter (per-VM, per-SSO-domain) ----
    # Env vars: NBX_VMWARE_USER_<HOSTNAME>, NBX_VMWARE_PASS_<HOSTNAME>.
    vcenter_vms = VirtualMachine.objects.filter(role__name__iexact='vCenter')
    for vm in vcenter_vms:
        env_key_user = f'NBX_VMWARE_USER_{vm.name.upper().replace("-", "_")}'
        env_key_pass = f'NBX_VMWARE_PASS_{vm.name.upper().replace("-", "_")}'
        vmware_user = os.environ.get(env_key_user, '')
        vmware_pass = os.environ.get(env_key_pass, '')
        for macro_name, val in [
            ('{$VMWARE.USERNAME}', vmware_user),
            ('{$VMWARE.PASSWORD}', vmware_pass),
        ]:
            if val:
                _ensure_macro_assignment(
                    server, macro_name, val, vm,
                    description=f'ztc:secret:vcenter:{vm.name}')
        if vmware_user and vmware_pass:
            logger.info('  Macros {$VMWARE.USERNAME}/{$VMWARE.PASSWORD} on %s', vm.name)
        else:
            logger.warning('  Env vars %s/%s not set — vCenter %s will have no SSO credentials',
                           env_key_user, env_key_pass, vm.name)

    # ---- Secret macros: MSSQL (role-level, shared) ----
    mssql_user = os.environ.get('NBX_MSSQL_USER', '')
    mssql_pass = os.environ.get('NBX_MSSQL_PASS', '')
    for macro_name, macro_value in [
        ('{$MSSQL.USER}', mssql_user),
        ('{$MSSQL.PASSWORD}', mssql_pass),
    ]:
        if macro_value:
            try:
                role = get_role('MSSQL')
                _ensure_macro_assignment(
                    server, macro_name, macro_value, role,
                    description='ztc:secret:MSSQL')
            except DeviceRole.DoesNotExist:
                logger.warning('  Role MSSQL not found, skipping %s', macro_name)
        else:
            logger.warning('  Env var not set for %s — skipping', macro_name)

    # ---- Prune stale ZabbixMacro objects with wrong assigned_object_type ----
    # Previous script versions created ZabbixMacro directly on DeviceRole/Device/VM
    # instead of ZabbixServer. These are invisible to inheritance — prune them.
    for model_cls in (DeviceRole, Device, VirtualMachine, Manufacturer):
        stale = M.ZabbixMacro.objects.filter(assigned_object_type=ct(model_cls))
        deleted, _ = stale.delete()
        if deleted:
            logger.info('  PRUNED: %s stale %s-level ZabbixMacro(s)', deleted, model_cls.__name__)

    # Also prune old wrong-name macros from previous script versions
    for old_macro in ('{$PURESTORAGE.TOKEN}', '{$VMWARE.USER}'):
        old = M.ZabbixMacro.objects.filter(macro=old_macro)
        deleted, _ = old.delete()
        if deleted:
            logger.info('  PRUNED: %s stale %s macro(s) (renamed to match template)', deleted, old_macro)

    # ---- Prune stale {$IF.UTIL.MAX} role macros ----
    ifutil = M.ZabbixMacro.objects.filter(macro='{$IF.UTIL.MAX}')
    deleted, _ = ifutil.delete()
    if deleted:
        logger.info('  PRUNED: %s {$IF.UTIL.MAX} macro(s) (global 101 must not be shadowed)', deleted)

def ensure_storage_generic_template(server) -> None:
    """Create 'Storage Generic Device by SNMP' in Zabbix if missing.

    This is a clone of 'Network Generic Device by SNMP' without the
    ``snmptrap.fallback`` and ``zabbix[host,snmp,available]`` items,
    which collide with Dell iDRAC on Dell storage/Cohesity hardware.
    """
    name = TPL_NAMES['storage_generic_snmp']
    with ZabbixConnection(server) as api:
        found = api.template.get(filter={'name': [name]}, output=['templateid', 'name'])
        if found:
            return
        src = api.template.get(filter={'name': ['Network Generic Device by SNMP']}, selectItems='extend')
        if not src:
            logger.warning('  Cannot create Storage Generic: source template %r not found', 'Network Generic Device by SNMP')
            return
        src = src[0]
        groups = api.templategroup.get()
        gid = groups[0]['groupid'] if groups else None
        if not gid:
            logger.warning('  Cannot create Storage Generic: no template group found')
            return
        result = api.template.create(host=name, name=name, groups=[{'groupid': gid}])
        tpl_id = result['templateids'][0]
        skip = {'snmptrap.fallback', 'zabbix[host,snmp,available]'}
        copied = 0
        for item in src.get('items', []):
            if item['key_'] in skip:
                continue
            try:
                api.item.create(
                    {
                        'hostid': tpl_id,
                        'name': item['name'],
                        'key_': item['key_'],
                        'type': int(item['type']),
                        'value_type': int(item.get('value_type', 3)),
                        'delay': item.get('delay', '1h'),
                    }
                )
                copied += 1
            except Exception:
                pass
        logger.info('  CREATED: %r in Zabbix (%d items, id=%s)', name, copied, tpl_id)


def run_production(*, mutate_netbox: bool = False, url: str | None = None, token: str | None = None, lab_http: bool = False):
    global TPL
    logger.info('=' * 60)
    logger.info('nbxSync Zero-Touch Configuration')
    logger.info('Successor to previous checklist configure_nbxsync.py')
    logger.info('=' * 60)
    # Warn if required SNMP secrets are missing (fail-closed for first apply).
    missing_snmp = [name for name in (
        'NBX_SNMP_AUTHPASS_MON', 'NBX_SNMP_PRIVPASS_MON',
        'NBX_SNMP_AUTHPASS_LINUX', 'NBX_SNMP_PRIVPASS_LINUX',
    ) if not os.environ.get(name)]
    if missing_snmp:
        logger.warning('MISSING SNMP env vars: %s — SNMP interfaces will have empty passphrases', ', '.join(missing_snmp))
        logger.warning('Set these before first apply: export %s=... etc.', ' '.join(missing_snmp))
    # Optional SNMP profiles (Dell iDRAC, SAP) — warn but don't block.
    missing_optional_snmp = [name for name in (
        'NBX_SNMP_AUTHPASS_DELL', 'NBX_SNMP_PRIVPASS_DELL',
    ) if not os.environ.get(name)]
    if missing_optional_snmp:
        logger.warning('Optional SNMP env unset (iDRAC/SAP): %s', ', '.join(missing_optional_snmp))

    # Network script reminder.
    logger.info('NOTE: Run scripts/configure_nbxsync_network.py after this for EXOS/VOSS/IQ Engine template imports and Extreme macros.')
    step0_cleanup(mutate_netbox=mutate_netbox)
    server = step1_zabbix_server(url=url, token=token, lab_http=lab_http)
    ensure_storage_generic_template(server)
    required_names = {k: v for k, v in TPL_NAMES.items() if k not in OPTIONAL_TPL_KEYS}
    TPL = resolve_templates(server, names=required_names, required=True)
    # Extreme VOSS / IQ Engine / ICMP — soft-resolve when present.
    TPL.update(resolve_templates(server, names={k: TPL_NAMES[k] for k in OPTIONAL_TPL_KEYS}, required=False))
    proxies, ch_proxy_group = step2_proxies(server)
    step3_server_assignments(server, proxies, ch_proxy_group)
    groups = step4_configgroups()
    step5_host_interfaces(server, groups)
    step5b_configgroup_assignments(groups)
    step6_template_rules(server)
    step7_template_assignments(server)
    step8_hostgroups(server)
    step9_tags()
    step10_host_inventory()
    step11_macros(server)

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
    logger.info(
        'Zero-touch deltas: SiteGroup Agent, multi-credential SNMP CGs '
        '(Linux via tag snmp, SAP via roles), SPACE :10060, Server Agent+OOB, '
        'hostgroup-first (Sites×Roles×OS); HI never on tags'
    )
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
    esxi_on_server_role = 0
    snmp_role_on_agent_cg = 0
    os_family_tags_remaining = M.ZabbixTag.objects.filter(tag='os_family').count()
    snmp_tag_ifs = M.ZabbixHostInterface.objects.filter(assigned_object_type=ct(Tag)).count()
    agent_cg_name = 'Agent Monitoring'
    snmp_ish_cgs = {
        'SNMP Monitoring',
        'SNMP Monitoring (Linux)',
        'SNMP Monitoring (SAP)',
        'OOB SNMP Only',
        'Server Agent+OOB',
        'SNMP by tag',
        'VM by SNMP',
    }

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

        # ESXi platform must not have role Server — should be ESXi Hypervisor
        plat_name = getattr(getattr(obj, 'platform', None), 'name', '') or ''
        if ESXI_PLATFORM_RE.search(plat_name) and role_name == 'Server':
            esxi_on_server_role += 1

    shadow = M.ZabbixMacro.objects.filter(macro__in=SHADOW_MACROS).count()
    print(
        json.dumps(
            {
                'objects_scanned': len(objects),
                'unprofiled': unprofiled,
                'no_template': no_template,
                'agent_cg_without_agent_platform_fact': agent_without_platform_fact,
                'snmp_role_resolved_to_agent_cg': snmp_role_on_agent_cg,
                'active_without_primary_or_oob_ip': active_no_primary,
                'esxi_on_server_role': esxi_on_server_role,
                'os_family_tags_remaining': os_family_tags_remaining,
                'tag_targeted_host_interfaces_remaining': snmp_tag_ifs,
            },
            indent=2,
        )
    )
    return 0


# =============================================================================
# Lab simulation (proof against local Zabbix — prefixed synthetic estate)
# =============================================================================


def record(name: str, ok: bool, detail: str = '', *, group: str = 'general') -> None:
    RESULTS.append({'name': name, 'ok': bool(ok), 'detail': detail, 'group': group})
    print(f'[{"PASS" if ok else "FAIL"}] {group}/{name}: {detail}')


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
                raise SystemExit(f'Refusing --simulate cleanup: ZabbixServer(s) {names} share lab URL {lab_url!r} but are not {SIM_SERVER_NAME!r}. Rename or remove them first.')
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
    site_l44, _ = SiteGroup.objects.get_or_create(
        slug=slugify('CH-STA-L44'),
        defaults={'name': f'{PREFIX}CH-STA-L44', 'group': leaf},
    )
    role_names = sorted(set(SNMP_ROLES + SERVER_BMC_ROLES + AGENT_DEFAULT_ROLES_DOC + ['Messpc', 'Sd Wan Socket', 'Virtual Appliance', 'Pure Storage', 'Storage', 'Tableau', 'CellMap', 'SAP ME', 'SAP HANA', 'Acronis Management', 'SCCM', 'Print Server', 'Database', 'Space Server']))
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
        for key, name in [('ch', 'nwn-ch-zabp01'), ('ch2', 'nwn-ch-zabp02'), ('hu', 'nwn-hu-zabp01'), ('kr', 'nwn-kr-zabp01'), ('cn', 'nwn-cn-zabp01')]:
            proxy, _ = M.ZabbixProxy.objects.get_or_create(
                name=f'{PREFIX}{name}',
                defaults={
                    'zabbixserver': server,
                    'operating_mode': ZabbixProxyTypeChoices.ACTIVE,
                    'tls_accept': [ZabbixTLSChoices.CERT],
                    'proxygroup': pg if key in ('ch', 'ch2') else None,
                    'local_address': '127.0.0.1' if key in ('ch', 'ch2') else '',
                    'local_port': 10051,
                    'description': 'lab',
                },
            )
            proxies[key] = proxy

        # Use prefixed country slugs in steps
        step3_server_assignments(server, proxies, pg, country_slugs=country_slugs)

        # Prefix CG names for lab isolation
        cg_groups = {
            'snmp': M.ZabbixConfigurationGroup.objects.get_or_create(name=f'{PREFIX}SNMP Monitoring', defaults={'description': 'lab'})[0],
            'agent': M.ZabbixConfigurationGroup.objects.get_or_create(name=f'{PREFIX}Agent Monitoring', defaults={'description': 'lab'})[0],
            'server_oob': M.ZabbixConfigurationGroup.objects.get_or_create(name=f'{PREFIX}Server Agent+OOB', defaults={'description': 'lab'})[0],
            'linux_snmp': M.ZabbixConfigurationGroup.objects.get_or_create(name=f'{PREFIX}SNMP Monitoring (Linux)', defaults={'description': 'lab'})[0],
            'oob_snmp': M.ZabbixConfigurationGroup.objects.get_or_create(name=f'{PREFIX}OOB SNMP Only', defaults={'description': 'lab'})[0],
            'esxi_oob': M.ZabbixConfigurationGroup.objects.get_or_create(name=f'{PREFIX}ESXi OOB iDRAC', defaults={'description': 'lab'})[0],
            'sap_snmp': M.ZabbixConfigurationGroup.objects.get_or_create(name=f'{PREFIX}SNMP Monitoring (SAP)', defaults={'description': 'lab'})[0],
            'space_agent': M.ZabbixConfigurationGroup.objects.get_or_create(name=f'{PREFIX}Agent Monitoring (SPACE)', defaults={'description': 'lab'})[0],
        }
        snmp_group = cg_groups['snmp']
        agent_group = cg_groups['agent']
        server_oob_group = cg_groups['server_oob']
        linux_snmp_group = cg_groups['linux_snmp']
        esxi_oob_group = cg_groups['esxi_oob']
        space_agent_group = cg_groups['space_agent']
        vm_snmp_group = linux_snmp_group  # legacy alias for hygiene asserts

        # ESXi platform so step5b can assign ESXi OOB iDRAC (production looks up by name).
        Platform.objects.get_or_create(name=f'{PREFIX}VMware ESXi', defaults={'slug': slugify(f'{PREFIX}vmware-esxi')})
        Manufacturer.objects.get_or_create(name='Dell', defaults={'slug': 'dell'})

        # Lab SNMP secrets (satisfy authPriv profile create; not production values)
        for key, val in (
            ('NBX_SNMP_AUTHPASS_MON', 'lab-mon-authpass'),
            ('NBX_SNMP_PRIVPASS_MON', 'lab-mon-privpass'),
            ('NBX_SNMP_AUTHPASS_LINUX', 'lab-linux-authpass'),
            ('NBX_SNMP_PRIVPASS_LINUX', 'lab-linux-privpass'),
            ('NBX_SNMP_AUTHPASS_DELL', 'lab-dell-authpass'),
            ('NBX_SNMP_PRIVPASS_DELL', 'lab-dell-privpass'),
            ('NBX_SNMP_AUTHPASS_SAP', 'lab-sap-authpass'),
            ('NBX_SNMP_PRIVPASS_SAP', 'lab-sap-privpass'),
        ):
            os.environ.setdefault(key, val)
        # Lab app credentials (per-device env vars)
        for dev in Device.objects.filter(device_type__manufacturer__name__iexact=f'{PREFIX}Pure Storage'):
            os.environ.setdefault(
                f'NBX_PURE_TOKEN_{dev.name.upper().replace("-", "_")}', 'lab-pure-token')
        for vm in VirtualMachine.objects.filter(role__name__iexact='vCenter'):
            os.environ.setdefault(
                f'NBX_VMWARE_USER_{vm.name.upper().replace("-", "_")}', 'lab-vmware-user')
            os.environ.setdefault(
                f'NBX_VMWARE_PASS_{vm.name.upper().replace("-", "_")}', 'lab-vmware-pass')
        os.environ.setdefault('NBX_MSSQL_USER', 'lab-mssql-user')
        os.environ.setdefault('NBX_MSSQL_PASS', 'lab-mssql-pass')

        step5_host_interfaces(server, cg_groups)
        step5b_configgroup_assignments(cg_groups, country_slugs=country_slugs)

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
            TPL['extreme_voss_snmp'] = (int(ensure_t(f'{PREFIX}voss.snmp', f'{PREFIX}Extreme VOSS by SNMP')), f'{PREFIX}Extreme VOSS by SNMP')
            TPL['extreme_iq_engine_snmp'] = (int(ensure_t(f'{PREFIX}iq.snmp', f'{PREFIX}Extreme IQ Engine by SNMP')), f'{PREFIX}Extreme IQ Engine by SNMP')
            TPL['network_generic_snmp'] = (int(ensure_t(f'{PREFIX}net.snmp', f'{PREFIX}Network Generic Device by SNMP')), f'{PREFIX}Network Generic Device by SNMP')
            TPL['fortigate_snmp'] = (int(ensure_t(f'{PREFIX}forti.snmp', f'{PREFIX}FortiGate by SNMP')), f'{PREFIX}FortiGate by SNMP')
            TPL['vmware_fqdn'] = (int(ensure_t(f'{PREFIX}vmware', f'{PREFIX}VMware FQDN')), f'{PREFIX}VMware FQDN')
            TPL['dell_idrac_snmp'] = (int(ensure_t(f'{PREFIX}idrac', f'{PREFIX}Dell iDRAC by SNMP')), f'{PREFIX}Dell iDRAC by SNMP')
            TPL['mssql_odbc'] = (int(ensure_t(f'{PREFIX}mssql', f'{PREFIX}MSSQL by ODBC')), f'{PREFIX}MSSQL by ODBC')
            TPL['mssql_agent2'] = (int(ensure_t(f'{PREFIX}mssql.agent2', f'{PREFIX}MSSQL by Zabbix agent 2')), f'{PREFIX}MSSQL by Zabbix agent 2')
            TPL['pure_storage_http'] = (int(ensure_t(f'{PREFIX}pure', f'{PREFIX}Pure Storage FlashArray v2 by HTTP')), f'{PREFIX}Pure Storage FlashArray v2 by HTTP')
            TPL['gitlab_http'] = (int(ensure_t(f'{PREFIX}gitlab', f'{PREFIX}GitLab by HTTP')), f'{PREFIX}GitLab by HTTP')
            TPL['linux_snmp'] = (int(ensure_t(f'{PREFIX}linux.snmp', f'{PREFIX}Linux by SNMP')), f'{PREFIX}Linux by SNMP')
            TPL['windows_snmp'] = (int(ensure_t(f'{PREFIX}windows.snmp', f'{PREFIX}Windows by SNMP')), f'{PREFIX}Windows by SNMP')
            TPL['storage_generic_snmp'] = (int(ensure_t(f'{PREFIX}storage.snmp', f'{PREFIX}Storage Generic Device by SNMP')), f'{PREFIX}Storage Generic Device by SNMP')
            TPL['hpe_msa_http'] = (int(ensure_t(f'{PREFIX}hpe.msa', f'{PREFIX}HPE MSA 2060 Storage by HTTP')), f'{PREFIX}HPE MSA 2060 Storage by HTTP')
            TPL['huawei_storage_snmp'] = (int(ensure_t(f'{PREFIX}huawei.storage', f'{PREFIX}Huawei OceanStor Dorado by SNMP')), f'{PREFIX}Huawei OceanStor Dorado by SNMP')
            TPL['synology_storage_snmp'] = (int(ensure_t(f'{PREFIX}synology.nas', f'{PREFIX}Synology DiskStation SNMPv3')), f'{PREFIX}Synology DiskStation SNMPv3')
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
            defaults={
                'value': ('Sites/{{ object.site.group.get_ancestors(include_self=True) | map(attribute="name") | join("/") }}/{{ object.site.name }}'),
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
        step11_macros(server)
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

        # No platform — Firewall keeps FortiGate role floor (same template as FortiOS rule).
        # Access Point has no Network Generic role floor (platform rules only; see step 7).
        fw = Device.objects.create(name=f'{PREFIX}fw-zone-01', device_type=dtype, role=roles['Firewall'], site=site, status='active')
        attach_dev(fw, next_ip())
        objects['firewall'] = fw
        ap = Device.objects.create(name=f'{PREFIX}ap-acce-01', device_type=dtype, role=roles['Access Point'], site=site, status='active')
        attach_dev(ap, next_ip())
        objects['access_point'] = ap

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

        # Tag snmp alone selects SNMP Monitoring (Linux) CG (zero-touch — no per-VM CG row).
        vm_ov = VirtualMachine.objects.create(name=f'{PREFIX}ensa-snmp-vm', cluster=cluster, role=roles['Server'], site=site, platform=plat_linux, status='active')
        attach_vm(vm_ov, next_ip())
        vm_ov.tags.add(snmp_tag)
        objects['vm_snmp'] = vm_ov

        win_snmp = VirtualMachine.objects.create(name=f'{PREFIX}win-snmp-vm', cluster=cluster, role=roles['Server'], site=site, platform=plat_win, status='active')
        attach_vm(win_snmp, next_ip())
        win_snmp.tags.add(snmp_tag)
        objects['win_snmp'] = win_snmp

        def cg_name(obj):
            a = get_assigned_zabbixobjects(obj)
            cg = a.get('configurationgroup')
            return cg.zabbixconfigurationgroup.name if cg else None

        def tpl_names(obj):
            a = get_assigned_zabbixobjects(obj)
            return sorted(t.zabbixtemplate.name for t in (a.get('templates') or []) if getattr(t, 'zabbixtemplate', None) is not None)

        record('server_cg_oob', cg_name(objects['server_oob']) == server_oob_group.name, cg_name(objects['server_oob']), group='resolve')
        record('switch_cg_snmp', cg_name(objects['switch']) == snmp_group.name, cg_name(objects['switch']), group='resolve')
        # Storage left SiteGroup Agent (no longer on network SNMP CG).
        record('storage_cg_agent', cg_name(objects['storage']) == agent_group.name, cg_name(objects['storage']), group='resolve')
        record('new_role_sitegroup_agent', cg_name(objects['new_role']) == agent_group.name, cg_name(objects['new_role']), group='resolve')
        record('dc_sitegroup_agent', cg_name(objects['dc']) == agent_group.name, cg_name(objects['dc']), group='resolve')
        record('vm_snmp_via_tag', cg_name(objects['vm_snmp']) == linux_snmp_group.name, cg_name(objects['vm_snmp']), group='resolve')
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
        record(
            'firewall_role_floor_fortigate',
            any('FortiGate' in n for n in tpl_names(objects['firewall'])),
            str(tpl_names(objects['firewall'])),
            group='resolve',
        )
        switch_tpls = tpl_names(objects['switch'])
        record(
            'switch_exos_no_netgeneric',
            any('EXOS' in n for n in switch_tpls) and not any('Network Generic' in n for n in switch_tpls),
            str(switch_tpls),
            group='resolve',
        )
        netgeneric_tpl = M.ZabbixTemplate.objects.filter(zabbixserver=server, name__icontains='Network Generic Device by SNMP').first()
        switch_floor_left = 0
        if netgeneric_tpl is not None:
            for role_name in ('Switch Core', 'Switch Dist', 'Switch Access', 'Switch Mgmt', 'Access Point'):
                try:
                    role = get_role(role_name)
                except DeviceRole.DoesNotExist:
                    continue
                switch_floor_left += M.ZabbixTemplateAssignment.objects.filter(
                    zabbixtemplate=netgeneric_tpl,
                    assigned_object_type=ct(DeviceRole),
                    assigned_object_id=role.id,
                ).count()
        record('no_switch_ap_netgeneric_floor', switch_floor_left == 0, f'leftover={switch_floor_left}', group='resolve')
        agent_role_rows = M.ZabbixConfigurationGroupAssignment.objects.filter(zabbixconfigurationgroup=agent_group, assigned_object_type=ct(DeviceRole)).count()
        record('zero_agent_role_sprawl', agent_role_rows == 0, f'rows={agent_role_rows}', group='resolve')
        mfr_cg = M.ZabbixConfigurationGroupAssignment.objects.filter(assigned_object_type=ct(Manufacturer), assigned_object_id=dell.pk).count()
        record('no_manufacturer_transport_cg', mfr_cg == 0, f'count={mfr_cg}', group='resolve')

        with ZabbixConnection(server) as api:
            for key in ('server_oob', 'switch', 'storage', 'firewall', 'access_point', 'win_vm', 'new_role', 'dc', 'vm_snmp', 'win_snmp'):
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
            sw_tpls = [t.get('name') for t in (h_sw.get('parentTemplates', []) if h_sw else [])]
            record(
                'zbx_switch_exos_only',
                any('EXOS' in (n or '') for n in sw_tpls) and not any('Network Generic' in (n or '') for n in sw_tpls),
                str(sw_tpls),
                group='zabbix',
            )
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
            h_fw = host(objects['firewall'].name)
            fw_tpls = [t.get('name') for t in (h_fw.get('parentTemplates', []) if h_fw else [])]
            record('zbx_firewall_fortigate', any('FortiGate' in (n or '') for n in fw_tpls), str(fw_tpls), group='zabbix')

            # Hostgroup-first hygiene
            record('no_os_family_tags', M.ZabbixTag.objects.filter(tag='os_family').count() == 0, str(M.ZabbixTag.objects.filter(tag='os_family').count()), group='hygiene')
            record(
                'snmp_os_template_rules',
                M.ZabbixTemplateRule.objects.filter(name__in=['SNMP Linux (tag)', 'SNMP Windows (tag)'], enabled=True).count() == 2,
                str(list(M.ZabbixTemplateRule.objects.filter(name__startswith='SNMP ').values_list('name', flat=True))),
                group='hygiene',
            )
            idrac_rule = M.ZabbixTemplateRule.objects.filter(name='Dell iDRAC (Server)', enabled=True).select_related('manufacturer').first()
            record(
                'dell_idrac_server_rule',
                bool(idrac_rule and idrac_rule.manufacturer_id and idrac_rule.role_pattern == '^Server$'),
                str(idrac_rule and (idrac_rule.manufacturer, idrac_rule.role_pattern, idrac_rule.pattern)),
                group='hygiene',
            )
            idrac_esxi = M.ZabbixTemplateRule.objects.filter(name='Dell iDRAC (ESXi)', enabled=True).select_related('manufacturer', 'zabbixhostgroup').first()
            record(
                'dell_idrac_esxi_rule',
                bool(
                    idrac_esxi
                    and idrac_esxi.manufacturer_id
                    and idrac_esxi.zabbixhostgroup
                    and 'VMware' in (idrac_esxi.zabbixhostgroup.name or '')
                    and 'ESXi' in (idrac_esxi.pattern or '')
                ),
                str(idrac_esxi and (idrac_esxi.pattern, getattr(idrac_esxi.zabbixhostgroup, 'name', None))),
                group='hygiene',
            )
            legacy_vmware_esxi = M.ZabbixTemplateRule.objects.filter(name='VMware ESXi').first()
            record(
                'vmware_esxi_platform_rule_disabled',
                legacy_vmware_esxi is None or not legacy_vmware_esxi.enabled,
                str(legacy_vmware_esxi and legacy_vmware_esxi.enabled),
                group='hygiene',
            )
            record('vm_snmp_cg_transport_only', M.ZabbixTemplateAssignment.objects.filter(assigned_object_type=ct(M.ZabbixConfigurationGroup), assigned_object_id=vm_snmp_group.id).count() == 0, 'ok', group='hygiene')

            def _snmp_if(group):
                return M.ZabbixHostInterface.objects.filter(
                    assigned_object_type=ct(M.ZabbixConfigurationGroup),
                    assigned_object_id=group.id,
                    type=ZabbixHostInterfaceTypeChoices.SNMP,
                ).first()

            esxi_if = _snmp_if(esxi_oob_group)
            esxi_agent_ifs = M.ZabbixHostInterface.objects.filter(
                assigned_object_type=ct(M.ZabbixConfigurationGroup),
                assigned_object_id=esxi_oob_group.id,
                type=ZabbixHostInterfaceTypeChoices.AGENT,
            ).count()
            record(
                'esxi_oob_dell_snmp_only',
                bool(
                    esxi_if
                    and esxi_if.use_oob_ip
                    and esxi_if.snmpv3_security_name == 'MONITORING-DELL'
                    and esxi_agent_ifs == 0
                ),
                str((esxi_if.snmpv3_security_name, esxi_if.use_oob_ip, esxi_agent_ifs) if esxi_if else None),
                group='hygiene',
            )
            vmware_tpl = M.ZabbixTemplate.objects.filter(zabbixserver=server, name__icontains='VMware FQDN').first()
            vmware_role_ok = False
            vmware_detail = 'no template'
            if vmware_tpl is not None:
                role_names = []
                for a in M.ZabbixTemplateAssignment.objects.filter(zabbixtemplate=vmware_tpl):
                    if a.assigned_object_type_id == ct(DeviceRole).id:
                        role = DeviceRole.objects.filter(pk=a.assigned_object_id).first()
                        if role:
                            role_names.append(role.name.replace(PREFIX, ''))
                vmware_role_ok = role_names == ['vCenter']
                vmware_detail = str(role_names)
            record('vmware_fqdn_vcenter_only', vmware_role_ok, vmware_detail, group='hygiene')

            net_if = _snmp_if(snmp_group)
            record(
                'snmp_network_md5_des',
                bool(
                    net_if
                    and net_if.snmp_pushcommunity
                    and net_if.snmpv3_security_name == 'MONITORING'
                    and net_if.snmpv3_authentication_protocol == ZabbixInterfaceSNMPV3AuthProtoChoices.MD5
                    and net_if.snmpv3_privacy_protocol == ZabbixInterfaceSNMPV3PrivProtoChoices.DES
                ),
                str((net_if.snmpv3_security_name, net_if.snmpv3_authentication_protocol, net_if.snmpv3_privacy_protocol) if net_if else None),
                group='hygiene',
            )
            linux_if = _snmp_if(linux_snmp_group)
            record(
                'snmp_linux_sha_aes',
                bool(
                    linux_if
                    and linux_if.snmpv3_security_name == 'MONITORING-LINUX'
                    and linux_if.snmpv3_authentication_protocol == ZabbixInterfaceSNMPV3AuthProtoChoices.SHA1
                    and linux_if.snmpv3_privacy_protocol == ZabbixInterfaceSNMPV3PrivProtoChoices.AES128
                ),
                str((linux_if.snmpv3_security_name, linux_if.snmpv3_authentication_protocol, linux_if.snmpv3_privacy_protocol) if linux_if else None),
                group='hygiene',
            )
            dell_if = _snmp_if(server_oob_group)
            record(
                'snmp_dell_idrac_profile',
                bool(
                    dell_if
                    and dell_if.use_oob_ip
                    and dell_if.snmpv3_security_name == 'MONITORING-DELL'
                    and dell_if.snmpv3_authentication_protocol == ZabbixInterfaceSNMPV3AuthProtoChoices.SHA1
                ),
                str((dell_if.snmpv3_security_name, dell_if.use_oob_ip, dell_if.snmpv3_authentication_protocol) if dell_if else None),
                group='hygiene',
            )
            space_if = M.ZabbixHostInterface.objects.filter(
                assigned_object_type=ct(M.ZabbixConfigurationGroup),
                assigned_object_id=space_agent_group.id,
                type=ZabbixHostInterfaceTypeChoices.AGENT,
            ).first()
            record('space_agent_port_10060', bool(space_if and int(space_if.port) == 10060), str(space_if.port if space_if else None), group='hygiene')
            record(
                'linux_snmp_cg_on_tag',
                M.ZabbixConfigurationGroupAssignment.objects.filter(
                    zabbixconfigurationgroup=linux_snmp_group,
                    assigned_object_type=ct(Tag),
                    assigned_object_id=snmp_tag.id,
                ).exists(),
                'ok',
                group='hygiene',
            )
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
            lines.append(f'| {r["group"]} | `{r["name"]}` | {"PASS" if r["ok"] else "FAIL"} | {r["detail"][:120].replace("|", "/")} |')
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
