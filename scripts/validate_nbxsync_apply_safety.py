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
    src = path.read_text()
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
    record(
        'zerotouch_no_fortigate_http_auto_cutover',
        'fortigate_http' not in ztc_src,
        'Forti HTTP cutover is network --apply-fortigate-http, not zerotouch',
    )

    failed = sum(1 for _, ok, _ in RESULTS if not ok)
    print(f'\n{len(RESULTS) - failed}/{len(RESULTS)} apply-safety checks passed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
