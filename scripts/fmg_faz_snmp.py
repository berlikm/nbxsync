#!/usr/bin/env python3
"""FortiManager / FortiAnalyzer SNMP contract (no Django, no Zabbix).

Cutover is ``configure_nbxsync_network.py --apply-fmg-faz``.

Shared MIB: FORTINET-FORTIMANAGER-FORTIANALYZER-MIB (enterprises.12356.103).
There is no official Zabbix template (ZBXNEXT-10433). Do **not** assign
FortiGate HTTP/SNMP or Network Generic onto these platforms (icmpping
collision; wrong objects). Do **not** re-run zerotouch — it still floors
FMG/FAZ on Network Generic.

Parent **Fortinet FMG-FAZ by SNMP** owns chassis/HA/RAID/sensor/IF-MIB,
device/ADOM inventory, and Health + Network interfaces dashboards.
**FortiManager Observability** and **FortiAnalyzer Observability** nest
that parent (EXOS companion pattern) and add the product board plus
FAZ log-disk triggers. Role Firewall is not the lever (FortiGates share it).
"""

from __future__ import annotations

from pathlib import Path

FMG_FAZ_SNMP_TEMPLATE = 'Fortinet FMG-FAZ by SNMP'
FORTIMANAGER_OBSERVABILITY_TEMPLATE = 'FortiManager Observability'
FORTIANALYZER_OBSERVABILITY_TEMPLATE = 'FortiAnalyzer Observability'

FMG_TEMPLATE_RULE = 'FortiManager'
FAZ_TEMPLATE_RULE = 'FortiAnalyzer'
LEGACY_FMG_FAZ_TEMPLATE_RULE = 'FortiAnalyzer/Manager'

FMG_PLATFORM_PATTERN = r'FortiManager'
FAZ_PLATFORM_PATTERN = r'FortiAnalyzer'
# Combined leftover from zerotouch — apply disables it so both rules cannot
# assign Network Generic *and* Observability (icmpping collision).
LEGACY_FMG_FAZ_PLATFORM_PATTERN = r'FortiAnalyzer|FortiManager'

NETWORK_GENERIC_TEMPLATE = 'Network Generic Device by SNMP'
ICMP_PING_TEMPLATE = 'ICMP Ping'
SNMP_MONITORING_CG = 'SNMP Monitoring'

# Dual-link on an FMG/FAZ host collides icmpping or polls the wrong product.
# Parent is nested by the Observability companions — do not also assign it.
FMG_FAZ_COLLIDING_TEMPLATES = (
    NETWORK_GENERIC_TEMPLATE,
    ICMP_PING_TEMPLATE,
    'FortiGate by HTTP',
    'FortiGate Observability',
    'FortiGate by SNMP',
    FMG_FAZ_SNMP_TEMPLATE,
)

ROOT = Path(__file__).resolve().parents[1]
FMG_FAZ_SNMP_YAML = (
    ROOT / 'zabbix/templates/fortinet_fmg_faz_snmp/template_net_fortinet_fmg_faz_snmp.yaml'
)
FORTIMANAGER_OBSERVABILITY_YAML = (
    ROOT
    / 'zabbix/templates/fortinet_fortimanager_observability/template_fortimanager_observability.yaml'
)
FORTIANALYZER_OBSERVABILITY_YAML = (
    ROOT
    / 'zabbix/templates/fortinet_fortianalyzer_observability/template_fortianalyzer_observability.yaml'
)

TEMPLATE_FILES = {
    FMG_FAZ_SNMP_TEMPLATE: FMG_FAZ_SNMP_YAML,
    FORTIMANAGER_OBSERVABILITY_TEMPLATE: FORTIMANAGER_OBSERVABILITY_YAML,
    FORTIANALYZER_OBSERVABILITY_TEMPLATE: FORTIANALYZER_OBSERVABILITY_YAML,
}

# enterprises.12356.103 — fnFortiManagerMib
FM_MIB = '1.3.6.1.4.1.12356.103'
FN_SYS_SERIAL = '1.3.6.1.4.1.12356.100.1.1.1.0'

PARENT_ICMP_NAME = f'{FMG_FAZ_SNMP_TEMPLATE}: Unavailable by ICMP ping'
PARENT_ICMP_EXPR = f'max(/{FMG_FAZ_SNMP_TEMPLATE}/icmpping,#3)=0'
PARENT_SNMP_NAME = f'{FMG_FAZ_SNMP_TEMPLATE}: No SNMP data collection'
PARENT_SNMP_EXPR = (
    f'max(/{FMG_FAZ_SNMP_TEMPLATE}/zabbix[host,snmp,available],{{$SNMP.TIMEOUT}})=0'
)

# Template-level defaults. FAZ Observability overrides disk High + log lag.
FMG_FAZ_PARENT_MACROS = {
    '{$ICMP_LOSS_WARN}': '10',
    '{$ICMP_RESPONSE_TIME_WARN}': '0.15',
    '{$SNMP.TIMEOUT}': '5m',
    '{$CPU.UTIL.WARN}': '85',
    '{$CPU.UTIL.CRIT}': '101',
    '{$MEMORY.UTIL.MAX}': '90',
    '{$DISK.UTIL.WARN}': '80',
    '{$DISK.UTIL.CRIT}': '90',
    '{$IF.UTIL.MAX}': '101',
    '{$IF.ERRORS.WARN}': '2',
    '{$IFCONTROL}': '1',
    '{$NET.IF.IFNAME.MATCHES}': '.*',
    '{$NET.IF.IFNAME.NOT_MATCHES}': '^(vlan|ssl|hamgmt|npu|disk)',
    '{$NET.IF.IFTYPE.MATCHES}': '^6$',
    '{$NET.IF.IFADMINSTATUS.MATCHES}': '^1$',
    '{$NET.IF.DISCOVERY.MIN}': '1',
    '{$UNSUPPORTED.MAX}': '5',
    '{$FM.DEVICE.CONTROL}': '1',
    '{$FM.DEVICE.EXPECTED}': '0',
    '{$FM.DEVICE.NAME.MATCHES}': '.*',
    '{$FM.DEVICE.NAME.NOT_MATCHES}': 'CHANGE_IF_NEEDED',
    '{$FM.DEVICE.MODE.MATCHES}': '^[1-3]$',
    '{$FM.CONFIG.CONTROL}': '0',
    '{$FM.HA.CONTROL}': '0',
    '{$FM.HA.EXPECTED}': '0',
    '{$FM.ADOM.NAME.MATCHES}': '.*',
    '{$FM.ADOM.NAME.NOT_MATCHES}': 'CHANGE_IF_NEEDED',
    '{$FM.ADOM.ARCHIVE.WARN}': '80',
    '{$FM.ADOM.ARCHIVE.CRIT}': '90',
}

FORTIMANAGER_PLATFORM_MACROS = {
    '{$FM.DEVICE.CONTROL}': '1',
    '{$FM.CONFIG.CONTROL}': '0',
    '{$FM.HA.CONTROL}': '0',
    '{$FM.HA.EXPECTED}': '0',
    '{$FM.DEVICE.EXPECTED}': '0',
}

# FAZ ships a default ADOM per product type (FortiMail, FortiWeb, …) even when
# unused. Shared parent keeps CHANGE_IF_NEEDED so FMG is untouched. Override
# only on the FAZ companion / platform. Keep root, others, Syslog,
# Unmanaged_Devices.
FAZ_ADOM_FACTORY_NOT_MATCHES = (
    '^Forti(Analyzer|Authenticator|Cache|Carrier|Client|DDoS|Deceptor|'
    'Firewall(Carrier)?|Mail|Manager|NAC|Proxy|Sandbox|Web)$'
)

FORTIANALYZER_PLATFORM_MACROS = {
    '{$FM.DEVICE.CONTROL}': '1',
    '{$FM.CONFIG.CONTROL}': '0',
    '{$FM.HA.CONTROL}': '0',
    '{$FM.HA.EXPECTED}': '0',
    '{$FM.DEVICE.EXPECTED}': '0',
    '{$FAZ.LOG.LAG.WARN}': '60',
    '{$FAZ.LOG.LAG.CRIT}': '300',
    '{$FAZ.LIC.GBDAY.MAX}': '0',
    '{$DISK.UTIL.HIGH}': '95',
    '{$FM.ADOM.NAME.NOT_MATCHES}': FAZ_ADOM_FACTORY_NOT_MATCHES,
}

FORTIANALYZER_TEMPLATE_MACROS = {
    '{$FAZ.LOG.LAG.WARN}': '60',
    '{$FAZ.LOG.LAG.CRIT}': '300',
    '{$FAZ.LIC.GBDAY.MAX}': '0',
    '{$DISK.UTIL.HIGH}': '95',
    '{$FM.ADOM.NAME.NOT_MATCHES}': FAZ_ADOM_FACTORY_NOT_MATCHES,
}


def platform_is_fortimanager(name: str | None) -> bool:
    import re

    return bool(name) and re.search(FMG_PLATFORM_PATTERN, name, re.I) is not None


def platform_is_fortianalyzer(name: str | None) -> bool:
    import re

    return bool(name) and re.search(FAZ_PLATFORM_PATTERN, name, re.I) is not None


def fmg_faz_rule_specs() -> tuple[tuple[str, str, str], ...]:
    """(rule name, platform regex, observability template)."""
    return (
        (FMG_TEMPLATE_RULE, FMG_PLATFORM_PATTERN, FORTIMANAGER_OBSERVABILITY_TEMPLATE),
        (FAZ_TEMPLATE_RULE, FAZ_PLATFORM_PATTERN, FORTIANALYZER_OBSERVABILITY_TEMPLATE),
    )
