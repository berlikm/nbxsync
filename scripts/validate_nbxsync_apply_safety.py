#!/usr/bin/env python3
"""Static checks for zerotouch/network apply isolation (no Django, no Zabbix).

Catches the review regressions:

  * TemplateRule lookup by ``name=`` alone (shared-DB mutation)
  * ``ZabbixServer.objects.first()`` as an apply fallback
  * ``--verify`` Extreme counters sitting behind ``if cg is None: continue``
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ZEROTOUCH = SCRIPTS / 'configure_nbxsync_zerotouch.py'
NETWORK = SCRIPTS / 'configure_nbxsync_network.py'

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = '') -> None:
    RESULTS.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def _parse(path: Path) -> tuple[str, ast.AST]:
    src = path.read_text(encoding='utf-8')
    return src, ast.parse(src, filename=str(path))


def _function_source(src: str, tree: ast.AST, name: str) -> str | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node)
    return None


def _attr_chain(node: ast.AST) -> list[str]:
    names: list[str] = []
    cur: ast.AST | None = node
    while isinstance(cur, ast.Attribute):
        names.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        names.append(cur.id)
    return list(reversed(names))


def _zabbixserver_objects_first_calls(src: str, tree: ast.AST) -> list[str]:
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        chain = _attr_chain(node.func)
        if len(chain) >= 3 and chain[-3:] == ['ZabbixServer', 'objects', 'first']:
            hits.append(ast.get_source_segment(src, node) or '.'.join(chain))
    return hits


UNSCOPED_RULE_FILTER = re.compile(
    r'M\.ZabbixTemplateRule\.objects\.filter\(\s*name(?:__in|__startswith)?\s*=',
)
ENSURE_RULE_BY_NAME = re.compile(r'ensure\(\s*M\.ZabbixTemplateRule\b')


def main() -> int:
    ztc_src, ztc_tree = _parse(ZEROTOUCH)
    net_src, net_tree = _parse(NETWORK)

    for label, src in (('zerotouch', ztc_src), ('network', net_src)):
        matches = [m.group(0) for m in UNSCOPED_RULE_FILTER.finditer(src)]
        record(
            f'{label}_no_unscoped_templaterule_name_filter',
            not matches,
            'ok' if not matches else repr(matches),
        )
        ensure_hits = ENSURE_RULE_BY_NAME.findall(src)
        record(
            f'{label}_no_ensure_templaterule_by_name',
            not ensure_hits,
            'ok' if not ensure_hits else repr(ensure_hits),
        )

    first_calls = _zabbixserver_objects_first_calls(net_src, net_tree)
    record(
        'network_no_arbitrary_zabbixserver_first_call',
        not first_calls,
        'ok' if not first_calls else first_calls,
    )
    record(
        'network_resolve_apply_server_exists',
        _function_source(net_src, net_tree, 'resolve_apply_zabbix_server') is not None,
        'resolve_apply_zabbix_server',
    )

    verify = _function_source(ztc_src, ztc_tree, 'run_verify') or ''
    extreme_idx = verify.find('switch_without_extreme_template += 1')
    unprofiled_idx = verify.find('unprofiled += 1')
    record(
        'verify_extreme_before_unprofiled_continue',
        extreme_idx != -1 and unprofiled_idx != -1 and extreme_idx < unprofiled_idx,
        f'extreme@{extreme_idx} unprofiled@{unprofiled_idx}',
    )
    hive_idx = verify.find('hiveos_without_iq_rule += 1')
    ap_idx = verify.find('ap_without_iq_template += 1')
    record(
        'verify_hiveos_and_ap_before_unprofiled',
        hive_idx != -1 and ap_idx != -1 and hive_idx < unprofiled_idx and ap_idx < unprofiled_idx,
        f'hive@{hive_idx} ap@{ap_idx} unprofiled@{unprofiled_idx}',
    )

    helpers = (
        'template_rules_for_server',
        'ensure_template_rule',
        'delete_template_rule',
        'get_template_rule',
        'simulation_rule_name',
    )
    ztc_funcs = {n.name for n in ast.walk(ztc_tree) if isinstance(n, ast.FunctionDef)}
    missing = [name for name in helpers if name not in ztc_funcs]
    record('zerotouch_templaterule_helpers', not missing, 'ok' if not missing else str(missing))

    net_funcs = {n.name for n in ast.walk(net_tree) if isinstance(n, ast.FunctionDef)}
    record(
        'network_uses_scoped_templaterule_helpers',
        'ensure_template_rule' in net_funcs and 'template_rules_for_server' in net_funcs,
        'ensure_template_rule + template_rules_for_server',
    )
    record(
        'network_report_hosts_takes_server',
        'def report_hosts_needing_macro_sync(server' in net_src,
        'report_hosts_needing_macro_sync(server=None)',
    )

    fg = _function_source(net_src, net_tree, 'run_apply_fortigate_http') or ''
    record(
        'network_fortigate_http_apply_exists',
        bool(fg),
        'run_apply_fortigate_http',
    )
    record(
        'network_fortigate_http_apply_skips_extreme_and_hostsync',
        bool(fg) and 'import_extreme_templates' not in fg and 'SyncHostJob' not in fg,
        'no Extreme import / HostSync in --apply-fortigate-http',
    )
    fg_import = _function_source(net_src, net_tree, 'import_fortigate_http_template') or ''
    record(
        'network_fortigate_http_reuses_existing_template',
        'not re-importing' in fg_import,
        'Cloud 7.0-2 is not overwritten',
    )
    record(
        'network_fortigate_http_never_imports_yaml',
        'import_yaml_templates' not in fg_import
        and 'configuration.import_' not in fg_import
        and 'FORTIGATE_HTTP_YAML' in fg_import,
        'lookup Cloud 7.0-2 only; bundled 7.0-3 is never imported',
    )
    record(
        'network_fortigate_http_aborts_unknown_vendor',
        'if not _is_cloud_fortigate_http_vendor(vendor)' in fg_import
        and 'if vendor and not _is_cloud_fortigate_http_vendor' not in fg_import,
        'empty vendor is not treated as compatible',
    )
    record(
        'zerotouch_no_fortigate_http_auto_cutover',
        'fortigate_http' not in ztc_src,
        'Forti HTTP cutover is network --apply-fortigate-http, not zerotouch',
    )
    forti_preflight = _function_source(net_src, net_tree, '_require_fortigate_http_preflight') or ''
    record(
        'network_fortigate_http_fail_closed_preflight',
        '_require_fortigate_http_preflight' in fg
        and '_preflight_fortigate_http' in forti_preflight
        and '_print_fortigate_http_plan' in forti_preflight
        and '_preflight_fortigate_http_zabbix' in forti_preflight
        and 'raise SystemExit' in forti_preflight,
        'preflight prints the plan and aborts before NetBox/Zabbix writes',
    )
    record(
        'network_fortigate_http_patches_zbx27082',
        'apply_fortigate_http_patches' in fg,
        'surgical ZBX-27082 / WAN / policy patches on Cloud HTTP',
    )
    nbx = _function_source(net_src, net_tree, '_step_fortigate_http_nbxsync') or ''
    record(
        'network_fortigate_http_fortios_only_no_firewall_floor',
        'FortiGate Observability' in nbx
        and 'ZabbixTemplateAssignment' not in nbx
        and '_SNMP_MONITORING_CG' not in nbx,
        'FortiOS companion rule; no Firewall role template/CG floor',
    )
    preflight = _function_source(net_src, net_tree, '_preflight_fortigate_http') or ''
    record(
        'network_fortigate_http_preflight_blocks_snmp_dual_link',
        '_DEVICE_DUAL_LINK_TEMPLATES' in preflight
        and 'icmpping' in preflight
        and 'SNMP is not a nested parent' in preflight
        and '_prune_fortios_colliding_templates' in nbx,
        'device-level FortiGate by SNMP is an abort; ICMP/HTTP are pruned as nested parents',
    )
    record(
        'network_reads_yaml_as_utf8',
        "read_text(encoding='utf-8')" in net_src,
        'YAML import does not depend on Windows CP1252',
    )
    record(
        'validator_reads_sources_as_utf8',
        "encoding='utf-8'" in Path(__file__).read_text(encoding='utf-8'),
        'apply-safety validator is encoding-explicit',
    )
    forti_import = _function_source(net_src, net_tree, 'import_fortigate_observability_template') or ''
    record(
        'network_fortigate_observability_imported',
        'import_fortigate_observability_template' in fg and 'strict=True' in forti_import,
        'estate companion YAML import is mandatory and fail-closed; stock 7.0-3 is not imported',
    )
    forti_http = (SCRIPTS / 'fortigate_http.py').read_text(encoding='utf-8')
    zbx_src = (SCRIPTS / 'fortigate_http_zabbix.py').read_text(encoding='utf-8')
    companion = (
        SCRIPTS.parent
        / 'zabbix/templates/fortinet_fortigate_observability/template_fortigate_observability.yaml'
    ).read_text(encoding='utf-8')
    record(
        'network_fortigate_http_overlay_census',
        'patch_vdom_star_items(api, templateid)' in zbx_src
        and 'patch_vdom_lld_metadata(api, templateid)' in zbx_src
        and "paths.append({'lld_macro': '{#VDOM}', 'path': '$.vdom'})" in zbx_src
        and '_with_vdom_tag' in zbx_src
        and "{'tag': 'vdom', 'value': '{#VDOM}'}" in zbx_src
        and 'patch_dashboard_time_periods(api, templateid)' in zbx_src
        and "'name': 'time_period.to'" in zbx_src
        and "'/api/v2/monitor/system/ha-checksums'" in companion
        and 'ha-nonsync-checksums' not in companion
        and 'ensure_overlay_census_items' in zbx_src
        and 'ensure_overlay_census_items' in net_src
        and 'OVERLAY_INVENTORY_KEY' in forti_http
        and 'overlayRaw' in zbx_src
        and 'code === 424' in forti_http,
        'multi-VDOM collectors, names, filter tags, and independent SD-WAN/IPsec census',
    )
    record(
        'network_fortigate_observability_dependencies',
        'ensure_observability_trigger_dependencies(api, observability[0])' in fg
        and 'OBSERVABILITY_TRIGGER_DEPENDENCIES' in zbx_src
        and 'api.trigger.update' in zbx_src,
        'companion imports before its ten dependencies are added idempotently',
    )
    apply_src = _function_source(zbx_src, ast.parse(zbx_src), 'apply_fortigate_http_patches') or ''
    record(
        'network_fortigate_reboot_is_warning',
        'patch_reboot_warning(api, templateid)' in apply_src
        and "REBOOT_TRIGGER = 'FortiGate: Device has been restarted'" in zbx_src
        and '_PRIORITY_WARNING = 2' in zbx_src,
        'stock reboot Info becomes Warning on the Cloud HTTP parent',
    )
    record(
        'network_fortigate_observability_traffic_navigation',
        "'Interface *: Bits received'" in companion
        and "'Interface *: Bits sent'" in companion
        and "'SD-WAN *: Bytes received per second'" in companion
        and "'SD-WAN *: Bytes sent per second'" in companion
        and 'type: graphprototype' not in companion,
        'companion navigators select nested HTTP traffic items without invalid graph prototype references',
    )
    record(
        'network_fortigate_http_raw_master_history',
        'patch_raw_master_history' in zbx_src
        and 'RAW_MASTER_HISTORY' in forti_http
        and "RAW_MASTER_HISTORY = '1h'" in forti_http,
        'netif/sdwan/system masters keep 1h history so lastclock is visible',
    )
    device_macros = _function_source(net_src, net_tree, '_step_fortios_device_macros') or ''
    object_macro = _function_source(net_src, net_tree, '_upsert_object_macro_assignment') or ''
    record(
        'network_fortigate_mgmt_link_alert_is_context_disabled',
        "context: str = ''" in object_macro
        and 'context=context' in object_macro
        and "'{$NET.IF.CONTROL}'" in device_macros
        and "context='mgmt'" in device_macros,
        'mgmt remains discovered; only its unreliable physical-link trigger is disabled per Device',
    )
    record(
        'network_fortigate_device_scope_matches_observable_inventory',
        '/api/v2/cmdb/system/interface?vdom=*' in device_macros
        and '_flatten_forti_cmdb_list' in device_macros
        and 'observable_names=observable' in device_macros
        and '/api/v2/cmdb/system/sdwan?vdom=*' in device_macros
        and "'{$FGATE.SDWAN.EXPECTED}'" in device_macros,
        'interface baseline is NetBox∩FortiOS; SD-WAN expectation is exact per Device',
    )
    record(
        'network_fortigate_ha_sync_is_primary_only',
        'ensure_observability_primary_trigger_gates(api, observability[0])' in fg
        and 'HA_VDOM_PRIMARY_GATE' in zbx_src
        and 'fgate.observability.ha.role)=1' in zbx_src,
        'HA VDOM mismatch remains collected on both members but tickets on the primary',
    )
    record(
        'network_fortigate_fqdn_is_platform_jinja',
        "FGATE_FQDN_JINJA = '{{ object.primary_ip4.address.ip }}'" in forti_http
        and 'FGATE_FQDN_MACRO: FGATE_FQDN_JINJA' in forti_http
        and 'FIREWALL_DEVICE_MACROS = ()' in forti_http,
        'FQDN is Platform FortiOS Jinja, not a device literal',
    )
    record(
        'network_fortigate_api_port_is_20443',
        "FGATE_API_PORT = '20443'" in forti_http
        and "'{$FGATE.API.PORT}': FGATE_API_PORT" in forti_http,
        'ha-mgmt GUI is 20443, not stock 80 or HTTPS 443',
    )
    plat_macros = _function_source(net_src, net_tree, '_step_fortios_platform_macros') or ''
    record(
        'network_fortigate_prunes_device_fqdn',
        '_prune_fortios_device_fqdn' in plat_macros,
        'leftover device-level FQDN is deleted so platform Jinja inherits',
    )
    record(
        'network_fortigate_unused_forticloud_license_is_silent',
        "'{$SERVICE.LICENSE.CONTROL}'" in plat_macros
        and "context='forticloud'" in plat_macros,
        'FortiCloud status stays visible but its unused Unknown license cannot page',
    )
    transport = _function_source(net_src, net_tree, '_step_fortigate_http_transport') or ''
    record(
        'network_fortigate_http_drops_snmp_cg_from_fortios',
        bool(transport)
        and '_prune_role_cg_names' in transport
        and '_fmg_faz_platforms' in transport
        and '_step_fortigate_http_transport(server)' in fg,
        'SNMP Monitoring moves to FMG/FAZ platforms; FortiOS is HTTP',
    )
    record(
        'network_fortigate_http_cg_on_fortios_platform',
        bool(transport)
        and '_FORTIGATE_HTTP_CG' in transport
        and '_ensure_fortigate_http_group' in transport
        and '_fortios_platforms' in transport
        and '_prune_icmp_from_fortigate_http_group' in transport
        and '_AGENT_MONITORING_CG' in transport,
        'FortiOS winning CG is FortiGate HTTP; Agent Monitoring is pruned from FortiOS objects',
    )
    prune = _function_source(net_src, net_tree, '_prune_fortios_colliding_templates') or ''
    record(
        'network_fortigate_does_not_prune_icmp_from_agent_cgs',
        bool(prune)
        and 'agent-plane CGs' in prune
        and 'ZabbixConfigurationGroup' not in prune
        and 'DeviceType' in prune,
        'FortiOS leftover ICMP/HTTP/SNMP is pruned; shared agent CGs are not',
    )
    record(
        'network_fortigate_nested_parents_are_http_and_icmp',
        'FORTIOS_NESTED_PARENT_TEMPLATES' in forti_http
        and 'DEVICE_DUAL_LINK_TEMPLATES = (FORTIGATE_SNMP_TEMPLATE,)' in forti_http
        and "FORTIGATE_HTTP_CG = 'FortiGate HTTP'" in forti_http,
        'ICMP/HTTP are nested parents; FortiOS uses FortiGate HTTP CG; only SNMP dual-link aborts apply',
    )
    ztc_icmp = _function_source(ztc_src, ztc_tree, 'step4_configgroups') or ''
    record(
        'zerotouch_fortigate_http_cg_has_no_icmp',
        'FORTIGATE_HTTP_CG' in ztc_src
        and 'forti_http' in ztc_icmp
        and 'Observability nests it' in ztc_src
        and 'fortigate_http' not in ztc_src,
        'zerotouch creates FortiGate HTTP CG without importing the Forti HTTP cutover module',
    )

    cato = _function_source(net_src, net_tree, 'run_apply_cato') or ''
    record(
        'network_cato_apply_exists',
        bool(cato),
        'run_apply_cato',
    )
    record(
        'network_cato_apply_skips_extreme_and_hostsync',
        bool(cato)
        and 'import_extreme_templates' not in cato
        and 'SyncHostJob' not in cato
        and 'enable_cato' not in cato
        and 'mutate_netbox' not in cato,
        'no Extreme import / HostSync / Socket migration in --apply-cato',
    )
    cato_preflight = _function_source(net_src, net_tree, '_require_cato_preflight') or ''
    record(
        'network_cato_fail_closed_preflight',
        '_require_cato_preflight' in cato
        and (
            'preflight_cato_graphql' in cato_preflight
            or 'collect_cato_preflight' in cato_preflight
        )
        and '_print_cato_plan' in cato_preflight
        and 'raise SystemExit' in cato_preflight,
        'Cato GraphQL preflight aborts before YAML/host writes',
    )
    record(
        'network_cato_uses_pack_module',
        'apply_cato_pack' in cato and 'CATO_HTTP_YAML' in net_src,
        'network --apply-cato reuses configure_cato_zabbix.apply_cato_pack',
    )
    record(
        'zerotouch_no_cato_collector_apply',
        'apply-cato' not in ztc_src and 'apply_cato_pack' not in ztc_src,
        'Cato collector refresh is network --apply-cato, not zerotouch',
    )

    fmg = _function_source(net_src, net_tree, 'run_apply_fmg_faz') or ''
    record(
        'network_fmg_faz_apply_exists',
        bool(fmg),
        'run_apply_fmg_faz',
    )
    record(
        'network_fmg_faz_apply_skips_extreme_and_hostsync',
        bool(fmg)
        and 'import_extreme_templates' not in fmg
        and 'SyncHostJob' not in fmg
        and 'configure_nbxsync_zerotouch' not in fmg,
        'no Extreme import / HostSync / zerotouch in --apply-fmg-faz',
    )
    fmg_preflight = _function_source(net_src, net_tree, '_require_fmg_faz_preflight') or ''
    record(
        'network_fmg_faz_fail_closed_preflight',
        '_require_fmg_faz_preflight' in fmg
        and '_preflight_fmg_faz' in fmg_preflight
        and '_print_fmg_faz_plan' in fmg_preflight
        and 'raise SystemExit' in fmg_preflight,
        'FMG/FAZ preflight prints the plan and aborts before YAML/NetBox writes',
    )
    nbx_fmg = _function_source(net_src, net_tree, '_step_fmg_faz_nbxsync') or ''
    record(
        'network_fmg_faz_splits_rules_and_disables_legacy',
        '_fmg_faz_rule_specs' in nbx_fmg
        and '_disable_legacy_fmg_faz_rule' in nbx_fmg
        and '_prune_fmg_faz_colliding_templates' in nbx_fmg
        and '_step_fmg_faz_snmp_cg' in nbx_fmg
        and 'ZabbixTemplateAssignment' not in nbx_fmg,
        'split FortiManager/FortiAnalyzer rules; no Firewall-role template floor',
    )
    snmp_cg = _function_source(net_src, net_tree, '_step_fmg_faz_snmp_cg') or ''
    record(
        'network_fmg_faz_keeps_snmp_monitoring_on_platforms',
        bool(snmp_cg) and '_SNMP_MONITORING_CG' in snmp_cg and '_fmg_faz_platforms' in snmp_cg,
        'SNMP Monitoring stays on FMG/FAZ platforms',
    )
    record(
        'zerotouch_no_fmg_faz_cutover',
        'apply-fmg-faz' not in ztc_src
        and 'fmg_faz_snmp' not in ztc_src
        and 'Fortinet FMG-FAZ by SNMP' not in ztc_src,
        'FMG/FAZ SNMP pack is network --apply-fmg-faz, not zerotouch',
    )

    mssql = _function_source(net_src, net_tree, 'run_apply_mssql') or ''
    record(
        'network_mssql_apply_exists',
        bool(mssql),
        'run_apply_mssql',
    )
    record(
        'network_mssql_apply_skips_extreme_and_hostsync',
        bool(mssql)
        and 'import_extreme_templates' not in mssql
        and 'SyncHostJob' not in mssql
        and 'configure_nbxsync_zerotouch' not in mssql,
        'no Extreme import / HostSync / zerotouch in --apply-mssql',
    )
    mssql_preflight = _function_source(net_src, net_tree, '_require_mssql_preflight') or ''
    record(
        'network_mssql_fail_closed_preflight',
        '_require_mssql_preflight' in mssql
        and '_preflight_mssql' in mssql_preflight
        and '_print_mssql_plan' in mssql_preflight
        and 'raise SystemExit' in mssql_preflight,
        'MSSQL preflight prints the plan and aborts before YAML/NetBox writes',
    )
    nbx_mssql = _function_source(net_src, net_tree, '_step_mssql_nbxsync') or ''
    record(
        'network_mssql_assigns_roles_keeps_stock',
        'ZabbixTemplateAssignment' in nbx_mssql
        and '_MSSQL_STOCK_TEMPLATE' in nbx_mssql
        and 'delete' not in nbx_mssql
        and 'HostInterfaceRequirementChoices.AGENT' in nbx_mssql,
        'role assignment alongside stock Agent 2; never unlink stock',
    )
    record(
        'zerotouch_mssql_observability_optional_soft_assign',
        'apply-mssql' not in ztc_src
        and 'template_mssql_observability.yaml' not in ztc_src
        and "'mssql_observability': 'MSSQL Observability'" in ztc_src
        and 'mssql_observability' in ztc_src,
        'zerotouch soft-assigns MSSQL Observability after import; YAML import is --apply-mssql',
    )

    failed = sum(1 for _, ok, _ in RESULTS if not ok)
    print(f'\n{len(RESULTS) - failed}/{len(RESULTS)} apply-safety checks passed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
