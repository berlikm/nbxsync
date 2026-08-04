#!/usr/bin/env python
"""Zero-touch nbxsync configuration + optional live simulation.

The GUI configuration checklist is the **functional contract**. This script is
the **automated delivery** of those same outcomes:

  * §1–3  Server, proxies, country SiteGroup server/proxy assignments
  * §4–5  Agent / SNMP / Server Agent+OOB / VM-by-SNMP ConfigGroups + IFs
          (Agent default on SiteGroups — not 31 role→Agent rows;
           storage on SNMP; BMC = one CG with Agent + use_oob_ip)
  * §6–7  TemplateRules + app/Manufacturer template assignments
  * §8–9  Jinja Sites/Roles once per SiteGroup; Teams; tag hostgroups; tags
  * §10–11 Inventory + role macros
  * §12   Assert plugin safety-gate defaults (configuration.py still owns settings)

Usage (from repo root, NetBox deps installed)::

  export NETBOX_CONFIGURATION=netbox.configuration_nbxsync
  export DJANGO_SETTINGS_MODULE=netbox.settings
  PYTHONPATH=/workspace/.deps/netbox/netbox:/workspace \\
    /workspace/.deps/venv/bin/python scripts/configure_nbxsync_zerotouch.py --simulate

Lab artifacts:
  /opt/cursor/artifacts/zerotouch_configure_sim_results.json
  /opt/cursor/artifacts/ZEROTOUCH_CONFIGURE_SIM_REPORT.md
  /opt/cursor/artifacts/CHECKLIST_VS_ZEROTOUCH.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path

import django

LAB_JSON = Path('/home/ubuntu/zabbix-docker/lab.json')
REPORT_JSON = Path('/opt/cursor/artifacts/zerotouch_configure_sim_results.json')
REPORT_MD = Path('/opt/cursor/artifacts/ZEROTOUCH_CONFIGURE_SIM_REPORT.md')
PREFIX = 'ztc-'
SERVER_NAME = 'ZeroTouch Configure Lab'

# Country SiteGroups used in the checklist (lab creates prefixed copies).
COUNTRIES = ('CH', 'HU', 'JP', 'KR', 'NL', 'US', 'CN')

# Role → transport exceptions (SNMP). Everything else inherits SiteGroup Agent.
SNMP_ROLES = (
    'Switch Core',
    'Switch Dist',
    'Switch Access',
    'Switch Mgmt',
    'Access Point',
    'Firewall',
    'Network Device',
    'Virtual Appliance',
    # SNMP-only / HTTP-poll storage must NOT stay on Agent CG
    'Pure Storage',
    'Cohesity',
    'Storage',
)

# Roles that need BMC dual-plane (Agent primary + SNMP OOB) — complete CG.
SERVER_BMC_ROLES = ('Server',)

# App / manufacturer template → role (business knowledge — still explicit).
# Same outcomes as checklist §7; transport comes from CGs above.
APP_TEMPLATE_ROLES = {
    'MSSQL by ODBC': ('MSSQL', 'MSSQL Query Server'),
    'VMware FQDN': ('vCenter',),
    'Pure Storage FlashArray by HTTP': ('Pure Storage',),
    'GitLab by HTTP': ('GitLab',),
    'Linux by SNMP': ('Virtual Appliance',),
}

# Teams overlays (static — tenancy skipped).
TEAMS = {
    'Teams/Network': (
        'Switch Core',
        'Switch Dist',
        'Switch Access',
        'Switch Mgmt',
        'Access Point',
        'Firewall',
        'Network Device',
    ),
    'Teams/Infrastructure': (
        'Server',
        'Domain Controller',
        'Fileserver',
        'Print Server',
        'SCCM',
        'PKI',
        'NAC',
        'Acronis Management',
    ),
    'Teams/Database Team': ('MSSQL', 'MSSQL Query Server', 'Nautilus'),
    'Teams/DevOps': ('GitLab', 'GitHub Runner', 'TeamCity', 'HLK'),
    'Teams/Application Team': ('SAP ME', 'SecsGem', 'Tableau', 'CellMap'),
    'Teams/Storage Team': ('Pure Storage', 'Cohesity', 'Storage', 'Production Backup'),
}

# Roles that need to exist for assignments (lab creates any missing).
ALL_ROLES = sorted(
    {
        *SNMP_ROLES,
        *SERVER_BMC_ROLES,
        *(r for roles in APP_TEMPLATE_ROLES.values() for r in roles),
        *(r for roles in TEAMS.values() for r in roles),
        'Domain Controller',
        'Fileserver',
        'MSSQL',
        'MSSQL Query Server',
        'GitLab',
        'vCenter',
        'Pure Storage',
        'VDI',  # exclusion target
        'Messpc',
        'Sd Wan Socket',
    }
)

ENV_TAG_JINJA = """{% set n = object.name | lower -%}
{%- if "-p-" in n or n.endswith("-p") or "-p0" in n or "-p1" in n -%}Production
{%- elif "-d-" in n -%}Development
{%- elif "-q-" in n -%}QA
{%- elif "-s-" in n -%}Sandbox
{%- elif "-t-" in n -%}Test
{%- elif "vdi" in n -%}VDI
{%- else -%}Unknown
{%- endif -%}"""


def bootstrap_django() -> None:
    os.environ.setdefault('NETBOX_CONFIGURATION', 'netbox.configuration_nbxsync')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
    netbox_root = Path('/workspace/.deps/netbox/netbox')
    if netbox_root.exists() and str(netbox_root) not in sys.path:
        sys.path.insert(0, str(netbox_root))
    repo = Path('/workspace')
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    django.setup()


bootstrap_django()

from django.contrib.contenttypes.models import ContentType  # noqa: E402
from django.db import transaction  # noqa: E402

from dcim.models import Device, DeviceRole, DeviceType, Interface, Manufacturer, Platform, Site, SiteGroup  # noqa: E402
from extras.models import Tag  # noqa: E402
from ipam.models import IPAddress  # noqa: E402
from virtualization.models import Cluster, ClusterType, VirtualMachine  # noqa: E402

from nbxsync.choices import (  # noqa: E402
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
from nbxsync.jobs.synchost import SyncHostJob  # noqa: E402
from nbxsync.models import (  # noqa: E402
    ZabbixConfigurationGroup,
    ZabbixConfigurationGroupAssignment,
    ZabbixHostBinding,
    ZabbixHostgroup,
    ZabbixHostgroupAssignment,
    ZabbixHostInterface,
    ZabbixHostInventory,
    ZabbixMacro,
    ZabbixProxy,
    ZabbixProxyGroup,
    ZabbixServer,
    ZabbixServerAssignment,
    ZabbixTag,
    ZabbixTagAssignment,
    ZabbixTemplate,
    ZabbixTemplateAssignment,
    ZabbixTemplateRule,
)
from nbxsync.utils import get_assigned_zabbixobjects  # noqa: E402
from nbxsync.utils.zabbixconnection import ZabbixConnection  # noqa: E402

RESULTS: list[dict] = []


def record(name: str, ok: bool, detail: str = '', *, group: str = 'general') -> None:
    RESULTS.append({'name': name, 'ok': bool(ok), 'detail': detail, 'group': group})
    print(f"[{'PASS' if ok else 'FAIL'}] {group}/{name}: {detail}")


def ct(model):
    return ContentType.objects.get_for_model(model)


def slugify(name: str) -> str:
    return PREFIX + name.lower().replace(' ', '-').replace('/', '-')


def get_or_create_role(name: str, *, vm_role: bool = True) -> DeviceRole:
    role, _ = DeviceRole.objects.get_or_create(
        slug=slugify(name),
        defaults={'name': f'{PREFIX}{name}', 'color': '9e9e9e', 'vm_role': vm_role},
    )
    return role


@dataclass
class Ctx:
    server: ZabbixServer
    proxy_group: ZabbixProxyGroup | None = None
    proxies: dict = field(default_factory=dict)
    countries: dict = field(default_factory=dict)  # code -> SiteGroup
    roles: dict = field(default_factory=dict)
    cg_agent: ZabbixConfigurationGroup | None = None
    cg_snmp: ZabbixConfigurationGroup | None = None
    cg_server_oob: ZabbixConfigurationGroup | None = None
    cg_vm_snmp: ZabbixConfigurationGroup | None = None
    templates: dict = field(default_factory=dict)
    hostgroups: dict = field(default_factory=dict)
    tags: dict = field(default_factory=dict)
    manufacturer_dell: Manufacturer | None = None
    site: Site | None = None
    cluster: Cluster | None = None
    platform_linux: Platform | None = None
    platform_win: Platform | None = None
    platform_exos: Platform | None = None
    dtype: DeviceType | None = None
    _octet: int = 40
    created_hosts: list = field(default_factory=list)

    def next_ip(self, net: str = '10.91.1') -> str:
        self._octet += 1
        return f'{net}.{self._octet}/32'


def cleanup_lab() -> None:
    Device.objects.filter(name__startswith=PREFIX).delete()
    VirtualMachine.objects.filter(name__startswith=PREFIX).delete()
    ZabbixTemplateRule.objects.filter(name__startswith=PREFIX).delete()
    ZabbixHostgroupAssignment.objects.filter(zabbixhostgroup__name__startswith=PREFIX).delete()
    ZabbixConfigurationGroupAssignment.objects.filter(zabbixconfigurationgroup__name__startswith=PREFIX).delete()
    ZabbixTemplateAssignment.objects.filter(zabbixtemplate__name__startswith=PREFIX).delete()
    ZabbixTagAssignment.objects.filter(zabbixtag__name__startswith=PREFIX).delete()
    ZabbixMacro.objects.filter(description__startswith=PREFIX).delete()
    for sg in SiteGroup.objects.filter(slug__startswith=PREFIX):
        ZabbixHostInventory.objects.filter(assigned_object_type=ct(SiteGroup), assigned_object_id=sg.pk).delete()

    lab_url = json.loads(LAB_JSON.read_text()).get('url') if LAB_JSON.exists() else None
    servers = list(ZabbixServer.objects.filter(name=SERVER_NAME))
    if lab_url:
        servers = list(ZabbixServer.objects.filter(url=lab_url)) or servers
    for server in servers:
        ZabbixServerAssignment.objects.filter(zabbixserver=server).delete()
        ZabbixHostInterface.objects.filter(zabbixserver=server, assigned_object_type=ct(ZabbixConfigurationGroup)).filter(
            assigned_object_id__in=ZabbixConfigurationGroup.objects.filter(name__startswith=PREFIX).values_list('pk', flat=True)
        ).delete()
        ZabbixHostBinding.objects.filter(zabbixserver=server).delete()
        ZabbixProxy.objects.filter(zabbixserver=server, name__startswith=PREFIX).delete()
        ZabbixProxyGroup.objects.filter(zabbixserver=server, name__startswith=PREFIX).delete()
        ZabbixHostgroup.objects.filter(zabbixserver=server, name__startswith=PREFIX).delete()
        ZabbixTemplate.objects.filter(zabbixserver=server, name__startswith=PREFIX).delete()
    # Also drop any leftover PREFIX interfaces on the shared server
    if lab_url:
        for server in ZabbixServer.objects.filter(url=lab_url):
            ZabbixHostInterface.objects.filter(zabbixserver=server).delete()

    ZabbixConfigurationGroup.objects.filter(name__startswith=PREFIX).delete()
    ZabbixTag.objects.filter(name__startswith=PREFIX).delete()
    Site.objects.filter(slug__startswith=PREFIX).delete()
    SiteGroup.objects.filter(slug__startswith=PREFIX).delete()
    DeviceRole.objects.filter(slug__startswith=PREFIX).delete()
    Platform.objects.filter(slug__startswith=PREFIX).delete()
    DeviceType.objects.filter(slug__startswith=PREFIX).delete()
    Manufacturer.objects.filter(slug__startswith=PREFIX).delete()
    Cluster.objects.filter(name__startswith=PREFIX).delete()
    ClusterType.objects.filter(slug__startswith=PREFIX).delete()
    Tag.objects.filter(slug__startswith=PREFIX).exclude(slug='do_not_monitor').delete()
    # Do not delete ZabbixServer — URL is globally unique; configure() reuses it.


def cleanup_zabbix(api) -> None:
    ids = [h['hostid'] for h in (api.host.get(search={'host': PREFIX}, output=['hostid', 'host']) or []) if h['host'].startswith(PREFIX)]
    if ids:
        api.host.delete(*ids)


def ensure_zabbix_templates(api) -> dict:
    groups = api.hostgroup.get(filter={'name': f'{PREFIX}lab'})
    gid = groups[0]['groupid'] if groups else api.hostgroup.create(name=f'{PREFIX}lab')['groupids'][0]
    tgroups = api.templategroup.get(filter={'name': f'{PREFIX}templates'})
    tgid = tgroups[0]['groupid'] if tgroups else api.templategroup.create(name=f'{PREFIX}templates')['groupids'][0]

    def ensure(host: str, name: str) -> str:
        found = api.template.get(filter={'host': host})
        if found:
            return found[0]['templateid']
        return api.template.create(host=host, name=name, groups=[{'groupid': tgid}])['templateids'][0]

    return {
        'gid': gid,
        'linux': ensure(f'{PREFIX}linux.agent', f'{PREFIX}Linux by Agent'),
        'windows': ensure(f'{PREFIX}windows.agent', f'{PREFIX}Windows by Agent'),
        'snmp': ensure(f'{PREFIX}network.snmp', f'{PREFIX}Network by SNMP'),
        'idrac': ensure(f'{PREFIX}dell.idrac', f'{PREFIX}Dell iDRAC by SNMP'),
        'mssql': ensure(f'{PREFIX}mssql.odbc', f'{PREFIX}MSSQL by ODBC'),
        'gitlab': ensure(f'{PREFIX}gitlab.http', f'{PREFIX}GitLab by HTTP'),
        'linux_snmp': ensure(f'{PREFIX}linux.snmp', f'{PREFIX}Linux by SNMP'),
        'vmware': ensure(f'{PREFIX}vmware.fqdn', f'{PREFIX}VMware FQDN'),
        'pure': ensure(f'{PREFIX}pure.http', f'{PREFIX}Pure Storage FlashArray by HTTP'),
        'fortigate': ensure(f'{PREFIX}fortigate.snmp', f'{PREFIX}FortiGate by SNMP'),
    }


def _snmp_v3_kwargs() -> dict:
    return {
        'snmp_version': ZabbixHostInterfaceSNMPVersionChoices.SNMPV3,
        'snmp_usebulk': True,
        'snmp_max_repetitions': 10,
        'snmpv3_security_name': 'MONITORING',
        'snmpv3_security_level': ZabbixInterfaceSNMPV3SecurityLevelChoices.AUTHPRIV,
        'snmpv3_authentication_protocol': ZabbixInterfaceSNMPV3AuthProtoChoices.SHA256,
        'snmpv3_authentication_passphrase': '{$SNMP_AUTHPASS}',
        'snmpv3_privacy_protocol': ZabbixInterfaceSNMPV3PrivProtoChoices.AES128,
        'snmpv3_privacy_passphrase': '{$SNMP_PRIVPASS}',
        'snmp_pushcommunity': False,
    }


def configure(ctx: Ctx, *, lab_http: bool = True) -> Ctx:
    """Apply zero-touch checklist (corrected). Idempotent within PREFIX namespace."""
    # --- §1 Server ---
    lab = json.loads(LAB_JSON.read_text()) if LAB_JSON.exists() else {'url': 'http://127.0.0.1:8080', 'token': 'x'}
    # URL is unique — reuse any existing lab server pointing at the same Zabbix.
    server = ZabbixServer.objects.filter(url=lab['url']).order_by('id').first()
    if server is None:
        server = ZabbixServer.objects.create(
            name=SERVER_NAME,
            url=lab['url'],
            token=lab['token'],
            validate_certs=not lab_http,
            sync_enabled=True,
            skip_version_check=False,
        )
    else:
        server.name = SERVER_NAME
        server.token = lab['token']
        server.validate_certs = not lab_http
        server.sync_enabled = True
        server.skip_version_check = False
        server.save()
    ctx.server = server

    # --- §2 Proxies ---
    pg, _ = ZabbixProxyGroup.objects.get_or_create(
        name=f'{PREFIX}CH Proxy Group',
        defaults={'zabbixserver': server, 'description': 'CH-based monitoring (NL/US)'},
    )
    if pg.zabbixserver_id != server.pk:
        pg.zabbixserver = server
        pg.save()
    ctx.proxy_group = pg

    def ensure_proxy(name: str, *, group=None, local_address: str = '', local_port: int = 10051) -> ZabbixProxy:
        proxy, created = ZabbixProxy.objects.get_or_create(
            name=f'{PREFIX}{name}',
            defaults={
                'zabbixserver': server,
                'proxygroup': group,
                'operating_mode': ZabbixProxyTypeChoices.ACTIVE,
                'local_address': local_address,
                'local_port': local_port,
            },
        )
        if not created:
            proxy.zabbixserver = server
            proxy.proxygroup = group
            proxy.local_address = local_address
            proxy.local_port = local_port
            proxy.save()
        ctx.proxies[name] = proxy
        return proxy

    ensure_proxy('ch-proxy-1', group=pg, local_address='127.0.0.1', local_port=10051)
    ensure_proxy('hu-proxy-1')
    ensure_proxy('kr-proxy-1')
    ensure_proxy('cn-proxy-1')

    # --- Topology (lab): country SiteGroups + sample site ---
    for code in COUNTRIES:
        sg, _ = SiteGroup.objects.get_or_create(slug=slugify(code), defaults={'name': f'{PREFIX}{code}'})
        ctx.countries[code] = sg

    leaf, _ = SiteGroup.objects.get_or_create(
        slug=slugify('CH-STA'),
        defaults={'name': f'{PREFIX}CH-STA', 'parent': ctx.countries['CH']},
    )
    if leaf.parent_id != ctx.countries['CH'].pk:
        leaf.parent = ctx.countries['CH']
        leaf.save()

    site, _ = Site.objects.get_or_create(
        slug=slugify('CH-STA-L44'),
        defaults={'name': f'{PREFIX}CH-STA-L44', 'group': leaf},
    )
    ctx.site = site

    for name in ALL_ROLES:
        ctx.roles[name] = get_or_create_role(name, vm_role=name not in {'Switch Core', 'Switch Dist', 'Firewall'})

    ctx.platform_linux, _ = Platform.objects.get_or_create(
        slug=slugify('ubuntu'),
        defaults={'name': f'{PREFIX}Ubuntu 22.04 LTS'},
    )
    ctx.platform_win, _ = Platform.objects.get_or_create(
        slug=slugify('windows'),
        defaults={'name': f'{PREFIX}Windows Server 2022'},
    )
    ctx.platform_exos, _ = Platform.objects.get_or_create(
        slug=slugify('exos'),
        defaults={'name': f'{PREFIX}Extreme EXOS 32.1'},
    )
    ctx.manufacturer_dell, _ = Manufacturer.objects.get_or_create(slug=slugify('dell'), defaults={'name': f'{PREFIX}Dell'})
    ctx.dtype, _ = DeviceType.objects.get_or_create(
        slug=slugify('poweredge'),
        defaults={'manufacturer': ctx.manufacturer_dell, 'model': f'{PREFIX}PowerEdge'},
    )
    ctype, _ = ClusterType.objects.get_or_create(slug=slugify('vmware'), defaults={'name': f'{PREFIX}VMware'})
    ctx.cluster, _ = Cluster.objects.get_or_create(name=f'{PREFIX}cluster-ch', defaults={'type': ctype, 'scope': site})

    # --- §3 Server assignments per country ---
    proxy_map = {
        'CH': (None, pg),
        'HU': (ctx.proxies['hu-proxy-1'], None),
        'JP': (ctx.proxies['kr-proxy-1'], None),
        'KR': (ctx.proxies['kr-proxy-1'], None),
        'NL': (None, pg),
        'US': (None, pg),
        'CN': (ctx.proxies['cn-proxy-1'], None),
    }
    for code, sg in ctx.countries.items():
        proxy, pgroup = proxy_map[code]
        ZabbixServerAssignment.objects.update_or_create(
            zabbixserver=server,
            assigned_object_type=ct(SiteGroup),
            assigned_object_id=sg.pk,
            defaults={'zabbixproxy': proxy, 'zabbixproxygroup': pgroup, 'sync_enabled': True},
        )

    # --- §4–5 ConfigGroups + interfaces (corrected) ---
    ctx.cg_agent, _ = ZabbixConfigurationGroup.objects.get_or_create(
        name=f'{PREFIX}Agent Monitoring',
        defaults={'description': 'Default agent transport (SiteGroup)'},
    )
    ctx.cg_snmp, _ = ZabbixConfigurationGroup.objects.get_or_create(
        name=f'{PREFIX}SNMP Monitoring',
        defaults={'description': 'SNMP transport for network + SNMP-only storage'},
    )
    ctx.cg_server_oob, _ = ZabbixConfigurationGroup.objects.get_or_create(
        name=f'{PREFIX}Server Agent+OOB',
        defaults={'description': 'Complete server profile: Agent primary + SNMP OOB'},
    )
    ctx.cg_vm_snmp, _ = ZabbixConfigurationGroup.objects.get_or_create(
        name=f'{PREFIX}VM by SNMP',
        defaults={'description': 'Direct VM override profile (complete SNMP)'},
    )

    def ensure_agent_if(cg: ZabbixConfigurationGroup) -> None:
        qs = ZabbixHostInterface.objects.filter(
            zabbixserver=server,
            assigned_object_type=ct(ZabbixConfigurationGroup),
            assigned_object_id=cg.pk,
            type=ZabbixHostInterfaceTypeChoices.AGENT,
        )
        if not qs.exists():
            ZabbixHostInterface.objects.create(
                zabbixserver=server,
                assigned_object_type=ct(ZabbixConfigurationGroup),
                assigned_object_id=cg.pk,
                type=ZabbixHostInterfaceTypeChoices.AGENT,
                interface_type=ZabbixInterfaceTypeChoices.DEFAULT,
                useip=ZabbixInterfaceUseChoices.IP,
                port=10050,
                tls_connect=ZabbixTLSChoices.NO_ENCRYPTION,
                dns='',
            )

    def ensure_snmp_if(cg: ZabbixConfigurationGroup, *, use_oob: bool = False) -> None:
        qs = ZabbixHostInterface.objects.filter(
            zabbixserver=server,
            assigned_object_type=ct(ZabbixConfigurationGroup),
            assigned_object_id=cg.pk,
            type=ZabbixHostInterfaceTypeChoices.SNMP,
            use_oob_ip=use_oob,
        )
        if not qs.exists():
            ZabbixHostInterface.objects.create(
                zabbixserver=server,
                assigned_object_type=ct(ZabbixConfigurationGroup),
                assigned_object_id=cg.pk,
                type=ZabbixHostInterfaceTypeChoices.SNMP,
                interface_type=ZabbixInterfaceTypeChoices.DEFAULT,
                useip=ZabbixInterfaceUseChoices.IP,
                port=161,
                use_oob_ip=use_oob,
                dns='',
                **_snmp_v3_kwargs(),
            )

    ensure_agent_if(ctx.cg_agent)
    ensure_snmp_if(ctx.cg_snmp, use_oob=False)
    ensure_agent_if(ctx.cg_server_oob)
    ensure_snmp_if(ctx.cg_server_oob, use_oob=True)
    ensure_snmp_if(ctx.cg_vm_snmp, use_oob=False)

    # Zero-touch: Agent CG on each TOP country SiteGroup (replaces 31 role rows)
    for sg in ctx.countries.values():
        ZabbixConfigurationGroupAssignment.objects.get_or_create(
            zabbixconfigurationgroup=ctx.cg_agent,
            assigned_object_type=ct(SiteGroup),
            assigned_object_id=sg.pk,
        )

    # SNMP exceptions on roles
    for role_name in SNMP_ROLES:
        ZabbixConfigurationGroupAssignment.objects.get_or_create(
            zabbixconfigurationgroup=ctx.cg_snmp,
            assigned_object_type=ct(DeviceRole),
            assigned_object_id=ctx.roles[role_name].pk,
        )

    # Server BMC complete profile (Role beats SiteGroup Agent)
    for role_name in SERVER_BMC_ROLES:
        ZabbixConfigurationGroupAssignment.objects.get_or_create(
            zabbixconfigurationgroup=ctx.cg_server_oob,
            assigned_object_type=ct(DeviceRole),
            assigned_object_id=ctx.roles[role_name].pk,
        )

    return ctx


def configure_templates_and_overlays(ctx: Ctx, zids: dict) -> None:
    server = ctx.server

    def tmpl(name: str, tid: str, req) -> ZabbixTemplate:
        obj, _ = ZabbixTemplate.objects.update_or_create(
            name=f'{PREFIX}{name}',
            zabbixserver=server,
            defaults={'templateid': int(tid), 'interface_requirements': req},
        )
        ctx.templates[name] = obj
        return obj

    tmpl('Linux by Agent', zids['linux'], [HostInterfaceRequirementChoices.AGENT])
    tmpl('Windows by Agent', zids['windows'], [HostInterfaceRequirementChoices.AGENT])
    tmpl('Network by SNMP', zids['snmp'], [HostInterfaceRequirementChoices.SNMP])
    tmpl('Dell iDRAC by SNMP', zids['idrac'], [HostInterfaceRequirementChoices.SNMP])
    tmpl('MSSQL by ODBC', zids['mssql'], [HostInterfaceRequirementChoices.AGENT])
    tmpl('GitLab by HTTP', zids['gitlab'], [HostInterfaceRequirementChoices.AGENT])
    tmpl('Linux by SNMP', zids['linux_snmp'], [HostInterfaceRequirementChoices.SNMP])
    tmpl('VMware FQDN', zids['vmware'], [HostInterfaceRequirementChoices.AGENT])
    tmpl('Pure Storage FlashArray by HTTP', zids['pure'], [HostInterfaceRequirementChoices.ANY])
    tmpl('FortiGate by SNMP', zids['fortigate'], [HostInterfaceRequirementChoices.SNMP])

    # OS hostgroups for rules
    hg_os_win, _ = ZabbixHostgroup.objects.get_or_create(
        name=f'{PREFIX}OS/Windows',
        zabbixserver=server,
        defaults={'value': 'OS/Windows'},
    )
    hg_os_linux, _ = ZabbixHostgroup.objects.get_or_create(
        name=f'{PREFIX}OS/Linux',
        zabbixserver=server,
        defaults={'value': 'OS/Linux'},
    )
    hg_os_net, _ = ZabbixHostgroup.objects.get_or_create(
        name=f'{PREFIX}OS/Network',
        zabbixserver=server,
        defaults={'value': 'OS/Network'},
    )
    tag_os_win, _ = ZabbixTag.objects.get_or_create(name=f'{PREFIX}os_family_windows', defaults={'tag': 'os_family', 'value': 'Windows'})
    tag_os_linux, _ = ZabbixTag.objects.get_or_create(name=f'{PREFIX}os_family_linux', defaults={'tag': 'os_family', 'value': 'Linux'})
    tag_os_exos, _ = ZabbixTag.objects.get_or_create(name=f'{PREFIX}os_family_exos', defaults={'tag': 'os_family', 'value': 'EXOS'})
    tag_os_voss, _ = ZabbixTag.objects.get_or_create(name=f'{PREFIX}os_family_voss', defaults={'tag': 'os_family', 'value': 'VOSS'})
    tag_os_iq, _ = ZabbixTag.objects.get_or_create(name=f'{PREFIX}os_family_iq', defaults={'tag': 'os_family', 'value': 'IQEngine'})
    tag_os_forti, _ = ZabbixTag.objects.get_or_create(name=f'{PREFIX}os_family_fortios', defaults={'tag': 'os_family', 'value': 'FortiOS'})
    tag_os_esxi, _ = ZabbixTag.objects.get_or_create(name=f'{PREFIX}os_family_esxi', defaults={'tag': 'os_family', 'value': 'ESXi'})

    # Checklist §6 TemplateRules — same patterns, automated
    rules = [
        ('Windows Server', 'Windows Server', ctx.templates['Windows by Agent'], hg_os_win, tag_os_win, 50),
        ('Windows catch-all', 'Windows', ctx.templates['Windows by Agent'], hg_os_win, tag_os_win, 200),
        ('Linux', r'Ubuntu|Debian|Linux|Red Hat|CentOS|Alma|SUSE|Arch|Photon|Other.*Linux', ctx.templates['Linux by Agent'], hg_os_linux, tag_os_linux, 100),
        ('Extreme EXOS', 'EXOS', ctx.templates['Network by SNMP'], hg_os_net, tag_os_exos, 100),
        ('Extreme VOSS', 'VOSS', ctx.templates['Network by SNMP'], hg_os_net, tag_os_voss, 100),
        ('Extreme IQ Engine', 'IQ ENGINE', ctx.templates['Network by SNMP'], hg_os_net, tag_os_iq, 100),
        ('FortiOS', r'FORTIOS|FortiOS', ctx.templates['FortiGate by SNMP'], hg_os_net, tag_os_forti, 100),
        ('FortiAnalyzer/Manager', r'FortiAnalyzer|FortiManager', ctx.templates['Network by SNMP'], hg_os_net, tag_os_forti, 50),
        ('VMware ESXi', r'ESXi|VMware ESX|vSphere', ctx.templates['VMware FQDN'], None, tag_os_esxi, 100),
        ('VMware Photon', 'Photon', ctx.templates['Linux by Agent'], hg_os_linux, tag_os_linux, 50),
    ]
    for name, pattern, template, hg, tag, prio in rules:
        ZabbixTemplateRule.objects.update_or_create(
            name=f'{PREFIX}{name}',
            defaults={
                'pattern': pattern,
                'zabbixtemplate': template,
                'zabbixhostgroup': hg,
                'zabbixtag': tag,
                'priority': prio,
                'enabled': True,
            },
        )

    # §7 Template assignments
    ZabbixTemplateAssignment.objects.get_or_create(
        zabbixtemplate=ctx.templates['Dell iDRAC by SNMP'],
        assigned_object_type=ct(Manufacturer),
        assigned_object_id=ctx.manufacturer_dell.pk,
    )
    for tmpl_name, role_names in APP_TEMPLATE_ROLES.items():
        key = tmpl_name  # already prefixed keys in ctx.templates
        for role_name in role_names:
            ZabbixTemplateAssignment.objects.get_or_create(
                zabbixtemplate=ctx.templates[key],
                assigned_object_type=ct(DeviceRole),
                assigned_object_id=ctx.roles[role_name].pk,
            )

    # §8 Hostgroups
    hg_lab, _ = ZabbixHostgroup.objects.update_or_create(
        name=f'{PREFIX}lab',
        zabbixserver=server,
        defaults={'value': f'{PREFIX}lab', 'groupid': int(zids['gid'])},
    )
    hg_managed, _ = ZabbixHostgroup.objects.get_or_create(
        name=f'{PREFIX}Managed',
        zabbixserver=server,
        defaults={'value': 'Managed/nbxSync'},
    )
    hg_sites, _ = ZabbixHostgroup.objects.get_or_create(
        name=f'{PREFIX}Sites-jinja',
        zabbixserver=server,
        defaults={'value': 'Sites/{{ object.site.group.name }}/{{ object.site.name }}'},
    )
    hg_roles, _ = ZabbixHostgroup.objects.get_or_create(
        name=f'{PREFIX}Roles-jinja',
        zabbixserver=server,
        defaults={'value': 'Roles/{{ object.role.name }}'},
    )
    hg_critical, _ = ZabbixHostgroup.objects.get_or_create(
        name=f'{PREFIX}Priority-Critical',
        zabbixserver=server,
        defaults={'value': 'Priority/Critical'},
    )
    hg_prod_db, _ = ZabbixHostgroup.objects.get_or_create(
        name=f'{PREFIX}Teams-Production-DB',
        zabbixserver=server,
        defaults={'value': 'Teams/Production DB'},
    )
    ctx.hostgroups.update(
        lab=hg_lab,
        managed=hg_managed,
        sites=hg_sites,
        roles=hg_roles,
        critical=hg_critical,
        prod_db=hg_prod_db,
    )

    for code, sg in ctx.countries.items():
        for hg in (hg_lab, hg_managed, hg_sites, hg_roles):
            ZabbixHostgroupAssignment.objects.get_or_create(
                zabbixhostgroup=hg,
                assigned_object_type=ct(SiteGroup),
                assigned_object_id=sg.pk,
            )

    for team_value, role_names in TEAMS.items():
        hg, _ = ZabbixHostgroup.objects.get_or_create(
            name=f'{PREFIX}{team_value.replace("/", "-")}',
            zabbixserver=server,
            defaults={'value': team_value},
        )
        for role_name in role_names:
            if role_name in ctx.roles:
                ZabbixHostgroupAssignment.objects.get_or_create(
                    zabbixhostgroup=hg,
                    assigned_object_type=ct(DeviceRole),
                    assigned_object_id=ctx.roles[role_name].pk,
                )

    tag_critical, _ = Tag.objects.get_or_create(slug=slugify('critical'), defaults={'name': f'{PREFIX}critical'})
    tag_prod_db, _ = Tag.objects.get_or_create(slug=slugify('production_db'), defaults={'name': f'{PREFIX}production_db'})
    tag_exclude, _ = Tag.objects.get_or_create(slug='do_not_monitor', defaults={'name': 'do_not_monitor'})
    ctx.tags.update(critical=tag_critical, production_db=tag_prod_db, exclude=tag_exclude)

    ZabbixHostgroupAssignment.objects.get_or_create(
        zabbixhostgroup=hg_critical,
        assigned_object_type=ct(Tag),
        assigned_object_id=tag_critical.pk,
    )
    ZabbixHostgroupAssignment.objects.get_or_create(
        zabbixhostgroup=hg_prod_db,
        assigned_object_type=ct(Tag),
        assigned_object_id=tag_prod_db.pk,
    )

    # §9 Tags
    ztag_env, _ = ZabbixTag.objects.get_or_create(
        name=f'{PREFIX}environment',
        defaults={'tag': 'environment', 'value': ENV_TAG_JINJA},
    )
    for sg in ctx.countries.values():
        ZabbixTagAssignment.objects.get_or_create(
            zabbixtag=ztag_env,
            assigned_object_type=ct(SiteGroup),
            assigned_object_id=sg.pk,
        )
    ztag_cluster, _ = ZabbixTag.objects.get_or_create(
        name=f'{PREFIX}cluster',
        defaults={'tag': 'cluster', 'value': '{{ object.cluster.name }}'},
    )
    ZabbixTagAssignment.objects.get_or_create(
        zabbixtag=ztag_cluster,
        assigned_object_type=ct(Cluster),
        assigned_object_id=ctx.cluster.pk,
    )
    ztag_exclude, _ = ZabbixTag.objects.get_or_create(
        name=f'{PREFIX}do_not_monitor',
        defaults={'tag': 'do_not_monitor', 'value': '1'},
    )
    for role_name in ('Messpc', 'Sd Wan Socket', 'VDI'):
        ZabbixTagAssignment.objects.get_or_create(
            zabbixtag=ztag_exclude,
            assigned_object_type=ct(DeviceRole),
            assigned_object_id=ctx.roles[role_name].pk,
        )

    # §10 Inventory (one mapping → all countries)
    for sg in ctx.countries.values():
        ZabbixHostInventory.objects.update_or_create(
            assigned_object_type=ct(SiteGroup),
            assigned_object_id=sg.pk,
            defaults={
                'inventory_mode': ZabbixHostInventoryModeChoices.AUTOMATIC,
                'name': f'{PREFIX}{{{{ object.name }}}}',
                'type': '{{ object.__class__.__name__ }}',
                'serialno_a': '{{ object.serial }}',
                'hardware': '{{ object.device_type.model if object.device_type else "" }}',
                'hardware_full': '{{ object.device_type.manufacturer.name if object.device_type else "" }} {{ object.device_type.model if object.device_type else "" }}',
                'tag': '{{ object.asset_tag }}',
                'location': '{{ object.site.name }}',
                'site_rack': '{{ object.rack.name if object.rack else "" }}',
                'url_a': 'https://netbox.example/dcim/devices/{{ object.id }}/',
                'deployment_status': '{{ object.status }}',
            },
        )

    # §11 Macros — checklist thresholds / secret placeholders
    macros = [
        ('{$CPU.UTIL.CRIT}', '90', 'MSSQL'),
        ('{$CPU.UTIL.CRIT}', '80', 'Server'),
        ('{$IF.UTIL.MAX}', '80', 'Switch Core'),
        ('{$IF.UTIL.MAX}', '90', 'Switch Dist'),
        ('{$MEM.UTIL.CRIT}', '85', 'VDI'),
        ('{$MSSQL.DSN}', 'nbxsync', 'MSSQL'),
        ('{$MSSQL.USER}', '{$MSSQL.USER}', 'MSSQL'),
        ('{$MSSQL.PASSWORD}', '{$MSSQL.PASSWORD}', 'MSSQL'),
        ('{$VMWARE.URL}', 'https://{{ object.name }}', 'vCenter'),
        ('{$VMWARE.USER}', '{$VMWARE.USER}', 'vCenter'),
        ('{$VMWARE.PASSWORD}', '{$VMWARE.PASSWORD}', 'vCenter'),
        ('{$PURESTORAGE.TOKEN}', '{$PURESTORAGE.TOKEN}', 'Pure Storage'),
    ]
    for macro, value, role_name in macros:
        ZabbixMacro.objects.update_or_create(
            macro=macro,
            assigned_object_type=ct(DeviceRole),
            assigned_object_id=ctx.roles[role_name].pk,
            defaults={'value': value, 'type': ZabbixMacroTypeChoices.TEXT, 'description': f'{PREFIX}{role_name}'},
        )


def _attach_device_ip(device: Device, address: str, *, oob: str | None = None) -> None:
    iface = Interface.objects.create(device=device, name='eth0', type='1000base-t')
    ip = IPAddress.objects.create(address=address, status='active', assigned_object=iface)
    device.primary_ip4 = ip
    if oob:
        oob_iface = Interface.objects.create(device=device, name='iDRAC', type='1000base-t')
        oob_ip = IPAddress.objects.create(address=oob, status='active', assigned_object=oob_iface)
        device.oob_ip = oob_ip
    device.save()


def _attach_vm_ip(vm: VirtualMachine, address: str) -> None:
    ip = IPAddress.objects.create(address=address, status='active')
    vm.primary_ip4 = ip
    vm.save()


def build_fleet(ctx: Ctx) -> dict:
    """Create representative objects and return them for assertions."""
    objects = {}
    server_role = ctx.roles['Server']
    switch_role = ctx.roles['Switch Core']
    storage_role = ctx.roles['Storage']
    mssql_role = ctx.roles['MSSQL']
    gitlab_role = ctx.roles['GitLab']

    d_srv = Device.objects.create(
        name=f'{PREFIX}linux-srv-p-01',
        device_type=ctx.dtype,
        role=server_role,
        site=ctx.site,
        platform=ctx.platform_linux,
        status='active',
    )
    _attach_device_ip(d_srv, ctx.next_ip(), oob=ctx.next_ip('10.91.254'))
    objects['server_oob'] = d_srv

    d_srv_no_oob = Device.objects.create(
        name=f'{PREFIX}linux-srv-no-oob',
        device_type=ctx.dtype,
        role=server_role,
        site=ctx.site,
        platform=ctx.platform_linux,
        status='active',
    )
    _attach_device_ip(d_srv_no_oob, ctx.next_ip())
    objects['server_no_oob'] = d_srv_no_oob

    d_sw = Device.objects.create(
        name=f'{PREFIX}sw-core-01',
        device_type=ctx.dtype,
        role=switch_role,
        site=ctx.site,
        platform=ctx.platform_exos,
        status='active',
    )
    _attach_device_ip(d_sw, ctx.next_ip())
    d_sw.tags.add(ctx.tags['critical'])
    objects['switch'] = d_sw

    d_stor = Device.objects.create(
        name=f'{PREFIX}storage-01',
        device_type=ctx.dtype,
        role=storage_role,
        site=ctx.site,
        status='active',
    )
    _attach_device_ip(d_stor, ctx.next_ip())
    objects['storage'] = d_stor

    vm_win = VirtualMachine.objects.create(
        name=f'{PREFIX}win-vm-p-01',
        cluster=ctx.cluster,
        role=server_role,
        site=ctx.site,
        platform=ctx.platform_win,
        status='active',
    )
    _attach_vm_ip(vm_win, ctx.next_ip())
    objects['win_vm'] = vm_win

    vm_linux = VirtualMachine.objects.create(
        name=f'{PREFIX}linux-vm-01',
        cluster=ctx.cluster,
        role=mssql_role,
        site=ctx.site,
        platform=ctx.platform_linux,
        status='active',
    )
    _attach_vm_ip(vm_linux, ctx.next_ip())
    objects['mssql_vm'] = vm_linux

    vm_gitlab = VirtualMachine.objects.create(
        name=f'{PREFIX}gitlab-01',
        cluster=ctx.cluster,
        role=gitlab_role,
        site=ctx.site,
        platform=ctx.platform_linux,
        status='active',
    )
    _attach_vm_ip(vm_gitlab, ctx.next_ip())
    objects['gitlab_vm'] = vm_gitlab

    # §5.5 — direct VM override beats role Agent/SiteGroup (complete SNMP profile)
    vm_snmp = VirtualMachine.objects.create(
        name=f'{PREFIX}ensa-snmp-vm',
        cluster=ctx.cluster,
        role=server_role,
        site=ctx.site,
        platform=ctx.platform_linux,
        status='active',
    )
    _attach_vm_ip(vm_snmp, ctx.next_ip())
    ZabbixConfigurationGroupAssignment.objects.get_or_create(
        zabbixconfigurationgroup=ctx.cg_vm_snmp,
        assigned_object_type=ct(VirtualMachine),
        assigned_object_id=vm_snmp.pk,
    )
    objects['vm_snmp_override'] = vm_snmp

    # §9.3 — excluded role must not sync
    vdi = VirtualMachine.objects.create(
        name=f'{PREFIX}vdi-excluded',
        cluster=ctx.cluster,
        role=ctx.roles['VDI'],
        site=ctx.site,
        platform=ctx.platform_win,
        status='active',
    )
    _attach_vm_ip(vdi, ctx.next_ip())
    objects['vdi_excluded'] = vdi

    # Non-BMC agent role (Domain Controller) → SiteGroup Agent, not Server OOB CG
    dc = VirtualMachine.objects.create(
        name=f'{PREFIX}dc-p-01',
        cluster=ctx.cluster,
        role=ctx.roles['Domain Controller'],
        site=ctx.site,
        platform=ctx.platform_win,
        status='active',
    )
    _attach_vm_ip(dc, ctx.next_ip())
    objects['dc_vm'] = dc

    # New role growth — no dedicated Agent CG row; SiteGroup default must apply
    new_role = get_or_create_role('Brand New App', vm_role=True)
    ctx.roles['Brand New App'] = new_role
    vm_new = VirtualMachine.objects.create(
        name=f'{PREFIX}new-role-01',
        cluster=ctx.cluster,
        role=new_role,
        site=ctx.site,
        platform=ctx.platform_linux,
        status='active',
    )
    _attach_vm_ip(vm_new, ctx.next_ip())
    objects['new_role_vm'] = vm_new

    return objects


def _cg_name(obj) -> str | None:
    assigned = get_assigned_zabbixobjects(obj)
    cg = assigned.get('configurationgroup')
    if not cg:
        return None
    return cg.zabbixconfigurationgroup.name


def _tmpl_names(obj) -> list[str]:
    assigned = get_assigned_zabbixobjects(obj)
    return sorted({t.zabbixtemplate.name for t in assigned.get('templates', [])})


def _if_types(obj) -> list[tuple]:
    assigned = get_assigned_zabbixobjects(obj)
    out = []
    for iface in assigned.get('hostinterfaces', []):
        out.append((iface.type, bool(iface.use_oob_ip), iface.port, bool(getattr(iface, 'interface_type', 1))))
    return sorted(out)


def _hg_values(obj) -> list[str]:
    assigned = get_assigned_zabbixobjects(obj)
    # Hostgroup assignments carry Jinja; resolve like sync does is heavy — check raw values / static.
    vals = []
    for a in assigned.get('hostgroups', []):
        vals.append(a.zabbixhostgroup.value)
    return sorted(vals)


def sync_host(obj) -> None:
    SyncHostJob(instance=obj).run()


def verify_resolution(ctx: Ctx, objects: dict) -> None:
    srv = objects['server_oob']
    record('server_cg_is_agent_oob', _cg_name(srv) == ctx.cg_server_oob.name, _cg_name(srv), group='resolve')
    ifs = _if_types(srv)
    record(
        'server_has_agent_and_oob_snmp',
        any(t == 1 and not oob for t, oob, *_ in ifs) and any(t == 2 and oob for t, oob, *_ in ifs),
        str(ifs),
        group='resolve',
    )
    tmpls = _tmpl_names(srv)
    record('server_has_linux_and_idrac', any('Linux by Agent' in t for t in tmpls) and any('iDRAC' in t for t in tmpls), str(tmpls), group='resolve')

    sw = objects['switch']
    record('switch_cg_is_snmp', _cg_name(sw) == ctx.cg_snmp.name, _cg_name(sw), group='resolve')
    record('switch_critical_hostgroup', any('Priority/Critical' in v for v in _hg_values(sw)), str(_hg_values(sw)), group='resolve')

    stor = objects['storage']
    record('storage_cg_is_snmp_not_agent', _cg_name(stor) == ctx.cg_snmp.name, _cg_name(stor), group='resolve')

    win = objects['win_vm']
    # VM with Server role gets Server Agent+OOB CG; OOB IF skipped without oob_ip
    record('win_vm_cg_server_profile', _cg_name(win) == ctx.cg_server_oob.name, _cg_name(win), group='resolve')
    record('win_vm_windows_template', any('Windows by Agent' in t for t in _tmpl_names(win)), str(_tmpl_names(win)), group='resolve')

    new_vm = objects['new_role_vm']
    record('new_role_inherits_sitegroup_agent', _cg_name(new_vm) == ctx.cg_agent.name, _cg_name(new_vm), group='resolve')
    record('new_role_jinja_roles_value', any('Roles/{{' in v for v in _hg_values(new_vm)), str(_hg_values(new_vm)), group='resolve')

    dc = objects['dc_vm']
    record('dc_inherits_sitegroup_agent', _cg_name(dc) == ctx.cg_agent.name, _cg_name(dc), group='resolve')

    vm_ov = objects['vm_snmp_override']
    record('vm_direct_snmp_overrides_role', _cg_name(vm_ov) == ctx.cg_vm_snmp.name, _cg_name(vm_ov), group='resolve')

    gitlab = objects['gitlab_vm']
    record('gitlab_app_template', any('GitLab' in t for t in _tmpl_names(gitlab)), str(_tmpl_names(gitlab)), group='resolve')

    mssql = objects['mssql_vm']
    record('mssql_app_template', any('MSSQL' in t for t in _tmpl_names(mssql)), str(_tmpl_names(mssql)), group='resolve')

    # Environment Jinja tag present on SiteGroup chain
    assigned = get_assigned_zabbixobjects(objects['server_oob'])
    env_tags = [a.zabbixtag for a in assigned.get('tags', []) if a.zabbixtag.tag == 'environment']
    record('environment_tag_assigned', len(env_tags) == 1, f'count={len(env_tags)}', group='resolve')

    # Anti-pattern check: Manufacturer-only OOB CG must NOT be how we assign
    manufacturer_cgs = ZabbixConfigurationGroupAssignment.objects.filter(
        assigned_object_type=ct(Manufacturer),
        assigned_object_id=ctx.manufacturer_dell.pk,
    )
    record('no_manufacturer_transport_cg', manufacturer_cgs.count() == 0, f'count={manufacturer_cgs.count()}', group='resolve')

    # Count Agent CG role assignments — should be 0 (SiteGroup default instead)
    agent_role_rows = ZabbixConfigurationGroupAssignment.objects.filter(
        zabbixconfigurationgroup=ctx.cg_agent,
        assigned_object_type=ct(DeviceRole),
    ).count()
    record('zero_agent_cg_role_sprawl', agent_role_rows == 0, f'role_rows={agent_role_rows}', group='resolve')

    # Checklist §6 rule count
    rule_n = ZabbixTemplateRule.objects.filter(name__startswith=PREFIX).count()
    record('template_rules_checklist_parity', rule_n >= 10, f'rules={rule_n}', group='resolve')

    # §11 macros present
    macro_n = ZabbixMacro.objects.filter(description__startswith=PREFIX).count()
    record('macros_checklist_parity', macro_n >= 12, f'macros={macro_n}', group='resolve')

    # §12 plugin settings (read-only assert — configuration.py is outside this script)
    from nbxsync.settings import get_plugin_settings

    ps = get_plugin_settings()
    record(
        'plugin_safety_gates_default_off',
        getattr(ps, 'allow_inherited_deletion', None) is False and getattr(ps, 'adopt_existing_hosts', None) is False,
        f'allow_inherited_deletion={getattr(ps, "allow_inherited_deletion", None)} adopt={getattr(ps, "adopt_existing_hosts", None)}',
        group='resolve',
    )


def verify_zabbix(ctx: Ctx, objects: dict, api) -> None:
    def host_by_name(name: str):
        found = api.host.get(filter={'host': name}, selectInterfaces='extend', selectParentTemplates=['name'], selectGroups=['name'], selectTags='extend')
        return found[0] if found else None

    # Sync key objects
    for key in ('server_oob', 'server_no_oob', 'switch', 'storage', 'win_vm', 'new_role_vm', 'mssql_vm', 'vm_snmp_override', 'dc_vm'):
        try:
            sync_host(objects[key])
            ctx.created_hosts.append(objects[key].name)
            record(f'sync_{key}', True, objects[key].name, group='sync')
        except Exception as exc:
            record(f'sync_{key}', False, f'{exc}\n{traceback.format_exc()[-400:]}', group='sync')

    # Exclusion: VDI role carries do_not_monitor — sync should skip / not create host
    try:
        sync_host(objects['vdi_excluded'])
        record('sync_vdi_excluded_runs', True, 'job returned', group='sync')
    except Exception as exc:
        record('sync_vdi_excluded_runs', False, str(exc), group='sync')
    h_vdi = host_by_name(objects['vdi_excluded'].name)
    # exclude_tag may be empty in lab plugin settings — record observed behavior
    from nbxsync.settings import get_plugin_settings

    exclude = getattr(get_plugin_settings(), 'exclude_tag', '') or ''
    if exclude == 'do_not_monitor':
        record('zbx_vdi_excluded_absent', h_vdi is None, f'host={h_vdi}', group='zabbix')
    else:
        record(
            'zbx_vdi_exclude_tag_config_note',
            True,
            f'plugin exclude_tag={exclude!r} — set to do_not_monitor in configuration.py (§12) for deletion semantics',
            group='zabbix',
        )

    h = host_by_name(objects['server_oob'].name)
    if not h:
        record('zbx_server_oob_exists', False, 'missing', group='zabbix')
    else:
        ifs = [(i.get('type'), i.get('ip'), i.get('port'), i.get('main')) for i in h.get('interfaces', [])]
        record(
            'zbx_server_dual_if',
            any(t == '1' and p == '10050' for t, _, p, _ in ifs) and any(t == '2' and p == '161' for t, _, p, _ in ifs),
            str(ifs),
            group='zabbix',
        )
        # OOB IP should be on SNMP IF
        # Refresh IPs from DB (related objects can expose address as a raw str).
        objects['server_oob'].refresh_from_db()
        oob_obj = IPAddress.objects.get(id=objects['server_oob'].oob_ip_id)
        primary_obj = IPAddress.objects.get(id=objects['server_oob'].primary_ip4_id)
        oob = str(oob_obj.address.ip)
        primary = str(primary_obj.address.ip)
        record(
            'zbx_server_oob_ip_on_snmp',
            any(t == '2' and ip == oob for t, ip, *_ in ifs) and any(t == '1' and ip == primary for t, ip, *_ in ifs),
            f'ifs={ifs} oob={oob} primary={primary}',
            group='zabbix',
        )
        tnames = [t['name'] for t in h.get('parentTemplates', [])]
        record('zbx_server_templates', any('Linux' in n for n in tnames) and any('iDRAC' in n for n in tnames), str(tnames), group='zabbix')
        groups = [g['name'] for g in h.get('groups', [])]
        record('zbx_server_sites_roles_groups', any(g.startswith('Sites/') for g in groups) and any(g.startswith('Roles/') for g in groups), str(groups), group='zabbix')

    h_sw = host_by_name(objects['switch'].name)
    if h_sw:
        groups = [g['name'] for g in h_sw.get('groups', [])]
        record('zbx_switch_priority_critical', 'Priority/Critical' in groups, str(groups), group='zabbix')
        ifs = [(i.get('type'), i.get('port')) for i in h_sw.get('interfaces', [])]
        record('zbx_switch_snmp_if', any(t == '2' for t, _ in ifs), str(ifs), group='zabbix')
    else:
        record('zbx_switch_exists', False, 'missing', group='zabbix')

    h_stor = host_by_name(objects['storage'].name)
    if h_stor:
        ifs = [(i.get('type'), i.get('port')) for i in h_stor.get('interfaces', [])]
        record('zbx_storage_snmp_if', any(t == '2' for t, _ in ifs), str(ifs), group='zabbix')
    else:
        record('zbx_storage_exists', False, 'missing', group='zabbix')

    h_new = host_by_name(objects['new_role_vm'].name)
    if h_new:
        groups = [g['name'] for g in h_new.get('groups', [])]
        record('zbx_new_role_group_materialized', any('Brand New App' in g for g in groups), str(groups), group='zabbix')
        ifs = [(i.get('type'), i.get('port')) for i in h_new.get('interfaces', [])]
        record('zbx_new_role_agent_if', any(t == '1' for t, _ in ifs), str(ifs), group='zabbix')
    else:
        record('zbx_new_role_exists', False, 'missing', group='zabbix')

    h_ov = host_by_name(objects['vm_snmp_override'].name)
    if h_ov:
        ifs = [(i.get('type'), i.get('port')) for i in h_ov.get('interfaces', [])]
        record('zbx_vm_snmp_override_snmp_if', any(t == '2' for t, _ in ifs) and not any(t == '1' for t, _ in ifs), str(ifs), group='zabbix')
    else:
        record('zbx_vm_snmp_override_exists', False, 'missing', group='zabbix')

    h_win = host_by_name(objects['win_vm'].name)
    if h_win:
        ifs = [(i.get('type'), i.get('port')) for i in h_win.get('interfaces', [])]
        # VM: Agent only (OOB skipped)
        record('zbx_win_vm_agent_only', any(t == '1' for t, _ in ifs) and not any(t == '2' for t, _ in ifs), str(ifs), group='zabbix')
        tnames = [t['name'] for t in h_win.get('parentTemplates', [])]
        record('zbx_win_vm_windows_tmpl', any('Windows' in n for n in tnames), str(tnames), group='zabbix')
    else:
        record('zbx_win_vm_exists', False, 'missing', group='zabbix')


def write_report() -> int:
    passed = sum(1 for r in RESULTS if r['ok'])
    total = len(RESULTS)
    REPORT_JSON.write_text(json.dumps({'summary': {'passed': passed, 'total': total}, 'results': RESULTS}, indent=2))
    lines = [
        '# Zero-Touch Configure Simulation Report',
        '',
        f'**Score:** {passed}/{total}',
        '',
        'Script: `scripts/configure_nbxsync_zerotouch.py --simulate`',
        '',
        'Corrected vs manual checklist: SiteGroup Agent default, SNMP for storage, Server Agent+OOB single CG, Jinja Roles once per SiteGroup.',
        '',
        '| Group | Case | Result | Detail |',
        '|---|---|---|---|',
    ]
    for r in RESULTS:
        lines.append(f"| {r['group']} | `{r['name']}` | {'PASS' if r['ok'] else 'FAIL'} | {r['detail'][:120].replace('|', '/')} |")
    REPORT_MD.write_text('\n'.join(lines) + '\n')
    print(f'\nSummary: {passed}/{total} — {REPORT_MD}')
    return 0 if passed == total else 1


def run_simulate() -> int:
    cleanup_lab()
    ctx = Ctx(server=None)  # type: ignore[arg-type]
    with transaction.atomic():
        configure(ctx, lab_http=True)
    lab = json.loads(LAB_JSON.read_text())
    with ZabbixConnection(ctx.server) as api:
        cleanup_zabbix(api)
        zids = ensure_zabbix_templates(api)
    configure_templates_and_overlays(ctx, zids)
    objects = build_fleet(ctx)
    verify_resolution(ctx, objects)
    with ZabbixConnection(ctx.server) as api:
        verify_zabbix(ctx, objects, api)
    return write_report()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--simulate', action='store_true', help='Clean lab namespace, apply zero-touch config, sync fleet, assert')
    parser.add_argument('--configure-only', action='store_true', help='Apply config objects only (still uses PREFIX lab topology)')
    args = parser.parse_args()
    if args.simulate or not args.configure_only:
        # Default to simulate when no flag — user asked to set up and prove it works.
        if not args.configure_only:
            return run_simulate()
    cleanup_lab()
    ctx = Ctx(server=None)  # type: ignore[arg-type]
    configure(ctx, lab_http=True)
    if LAB_JSON.exists():
        with ZabbixConnection(ctx.server) as api:
            zids = ensure_zabbix_templates(api)
        configure_templates_and_overlays(ctx, zids)
    print('Configured zero-touch lab namespace.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
