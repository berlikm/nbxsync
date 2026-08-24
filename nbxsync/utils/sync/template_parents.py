"""Drop nested parent templateids before ``host.update``.

Zabbix rejects linking a template together with one of its ancestors:

    Cannot link template X ... because its parent template Y would be linked twice

NetBox inheritance can still assign both (Template Rule Observability plus ICMP
Ping from an Agent Monitoring configuration group, or Speed Expect plus a
companion that already nests it). HostSync must send only the leaves.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence


def drop_nested_parent_templateids(
    intended: Sequence[int | str],
    parent_map: Mapping[int, Sequence[int]],
) -> list[int]:
    """Return intended templateids with nested parents removed.

    A templateid is dropped when it is a (possibly transitive) parent of
    another intended template. Siblings such as FortiGate by SNMP and
    FortiGate Observability are both kept — SNMP is not a nested parent.
    """
    ordered: list[int] = []
    seen: set[int] = set()
    for raw in intended:
        tid = int(raw)
        if tid in seen:
            continue
        seen.add(tid)
        ordered.append(tid)
    intended_set = set(ordered)

    def ancestors(tid: int) -> set[int]:
        found: set[int] = set()
        stack = [int(pid) for pid in parent_map.get(int(tid), [])]
        while stack:
            pid = stack.pop()
            if pid in found:
                continue
            found.add(pid)
            stack.extend(int(p) for p in parent_map.get(pid, []))
        return found

    nested: set[int] = set()
    for tid in ordered:
        nested.update(pid for pid in ancestors(tid) if pid in intended_set and pid != tid)
    return [tid for tid in ordered if tid not in nested]


def _parent_ids(row: Mapping) -> list[int]:
    parents: list[int] = []
    for parent in row.get('parentTemplates') or []:
        if isinstance(parent, Mapping) and 'templateid' in parent:
            parents.append(int(parent['templateid']))
        else:
            parents.append(int(parent))
    return parents


def fetch_template_parent_map(
    templateids: Iterable[int | str],
    get_templates: Callable[[list[int]], Sequence[Mapping]],
) -> dict[int, list[int]]:
    """Build a direct-parent map, walking ancestors not in the intended set.

    ``get_templates(ids)`` must return Zabbix ``template.get`` rows with
    ``templateid`` and ``parentTemplates``. Observability may list ICMP Ping
    as a direct parent, or only nest it through FortiGate by HTTP — the walk
    fetches those extra parents so a leftover ICMP assignment is still dropped.
    """
    parent_map: dict[int, list[int]] = {}
    pending = {int(tid) for tid in templateids}
    seen: set[int] = set()
    while pending:
        batch = sorted(tid for tid in pending if tid not in seen)
        if not batch:
            break
        seen.update(batch)
        pending.clear()
        rows = get_templates(batch) or []
        for row in rows:
            tid = int(row['templateid'])
            parents = _parent_ids(row)
            parent_map[tid] = parents
            for pid in parents:
                if pid not in seen:
                    pending.add(pid)
    return parent_map
