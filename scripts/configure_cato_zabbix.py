#!/usr/bin/env python3
"""Install and verify the Cato account-scoped Zabbix monitoring pack.

The Cato API represents an account, not a NetBox device.  This script owns the
single collector host and its secret macro.  It deliberately does not create or
manage Socket hosts; nbxSync owns those NetBox-backed ICMP hosts.

Production collector refresh is ``configure_nbxsync_network.py --apply-cato``.
This module is the Zabbix-API implementation that flag calls. Do not re-run
zerotouch to update the collector.

Usage:
  NBX_CATO_API_KEY=... python scripts/configure_cato_zabbix.py --simulate
  NBX_ZABBIX_URL=https://zabbix.example NBX_ZABBIX_TOKEN=... \\
    NBX_CATO_API_KEY=... python scripts/configure_cato_zabbix.py --apply
  NBX_ZABBIX_URL=https://zabbix.example NBX_ZABBIX_TOKEN=... \\
    python scripts/configure_cato_zabbix.py --verify
  NBX_ZABBIX_URL=https://zabbix.example NBX_ZABBIX_TOKEN=... \\
    python scripts/configure_cato_zabbix.py --verify --require-sockets

``--simulate`` uses the local Zabbix lab and creates only ``cato-sim-account-964``.
It exercises a valid Cato collection, then an invalid-token collector failure;
it is intentionally slow because it waits through the template's 5m/15m
no-data windows. ``--apply`` fail-closes on GraphQL preflight before import.
``--verify`` is collector-only unless ``--require-sockets`` is passed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from zabbix_api import ZabbixAPI  # noqa: E402
from cato_http import (  # noqa: E402
    CATO_API_KEY_ENV,
    CATO_API_URL,
    CATO_PROXY_GROUP_ENV,
    COLLECTOR_COUNTER_KEYS,
    CENSUS_EXPECTED_MACROS,
    EXPECTED_COLLECTOR_TRIGGER_NAMES,
    EXPECTED_DASHBOARD_NAMES,
    EXPECTED_DASHBOARD_ITEM_REFERENCES,
    EXPECTED_DASHBOARD_NAVIGATOR_GROUPS,
    EXPECTED_NAVIGATOR_SHOW_LINES,
    EXPECTED_DISCOVERY_KEYS,
    EXPECTED_GRAPH_PROTOTYPES,
    EXPECTED_HEALTH_PAGES,
    EXPECTED_ITEM_PROTOTYPE_KEYS,
    EXPECTED_NETWORK_PAGES,
    EXPECTED_PATH_PAGES,
    EXPECTED_STATE_TRIGGER_PROTOTYPE_NAMES,
    EXPECTED_TEMPLATE_ITEM_KEYS,
    EXPECTED_UNSUPPORTED_TRIGGER_DEPENDENCIES,
    HOST_GROUP,
    ICMP_TEMPLATE_NAME,
    MANAGED_TAGS,
    MASTER_KEYS,
    METRICS_FRESH_SECONDS,
    PROXY_GROUP_MONITORED,
    SECRET_TEXT,
    SERVER_MONITORED,
    SIM_EXPECTED_CENSUS,
    SLA_PREFIXES,
    SNAPSHOT_FRESH_SECONDS,
    TEMPLATE_NAME,
    TEMPLATE_PATH,
    TEXT,
    collect_cato_preflight,
    collector_host,
    collector_visible_name,
    default_account_id,
    host_macros,
    metrics_sla_census,
    normalize_socket_serial,
    sim_host,
    snapshot_census,
    snapshot_socket_serials,
)

HOST = collector_host()
VISIBLE_NAME = collector_visible_name()
SIM_HOST = sim_host()
CATO_MACROS = host_macros()
LEGACY_LAN_DISCOVERY_KEY = "cato.lan.port.discovery"
LEGACY_LAN_ITEM_PREFIXES = (
    "cato.lan.port.rx.bps[",
    "cato.lan.port.tx.bps[",
)


def import_rules() -> dict[str, dict[str, bool]]:
    """Use the same safe import contract as the network configuration script."""
    return {
        "templates": {"createMissing": True, "updateExisting": True},
        "template_groups": {"createMissing": True, "updateExisting": True},
        "templateLinkage": {"createMissing": True, "deleteMissing": False},
        "valueMaps": {"createMissing": True, "updateExisting": True},
        "items": {
            "createMissing": True,
            "updateExisting": True,
            "deleteMissing": False,
        },
        "discoveryRules": {
            "createMissing": True,
            "updateExisting": True,
            "deleteMissing": False,
        },
        "triggers": {
            "createMissing": True,
            "updateExisting": True,
            "deleteMissing": False,
        },
        "graphs": {
            "createMissing": True,
            "updateExisting": True,
            "deleteMissing": False,
        },
        "httptests": {
            "createMissing": True,
            "updateExisting": True,
            "deleteMissing": False,
        },
        "templateDashboards": {
            "createMissing": True,
            "updateExisting": True,
            "deleteMissing": False,
        },
    }


def _record(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    result = {"name": name, "ok": bool(ok), "detail": detail}
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return result


def _all_pass(records: list[dict[str, Any]]) -> bool:
    return all(record["ok"] for record in records)


def _exact_template(api: ZabbixAPI) -> dict[str, Any] | None:
    found = api.call(
        "template.get",
        {"filter": {"name": TEMPLATE_NAME}, "output": ["templateid", "host", "name"]},
    )
    if len(found) > 1:
        raise RuntimeError(f"multiple templates named {TEMPLATE_NAME!r}")
    return found[0] if found else None


def import_template(api: ZabbixAPI) -> str:
    """Import the Cato template and return its stable template ID."""
    if not TEMPLATE_PATH.exists():
        raise RuntimeError(f"Cato template is missing: {TEMPLATE_PATH}")
    api.call(
        "configuration.import",
        {
            "format": "yaml",
            "rules": import_rules(),
            "source": TEMPLATE_PATH.read_text(),
        },
    )
    template = _exact_template(api)
    if template is None:
        raise RuntimeError(f"template missing after import: {TEMPLATE_NAME}")
    return str(template["templateid"])


def ensure_hostgroup(api: ZabbixAPI, name: str) -> str:
    """Create the dedicated account collector group when it does not exist."""
    found = api.call(
        "hostgroup.get", {"filter": {"name": name}, "output": ["groupid", "name"]}
    )
    if len(found) > 1:
        raise RuntimeError(f"multiple host groups named {name!r}")
    if found:
        return str(found[0]["groupid"])
    result = api.call("hostgroup.create", {"name": name})
    return str(result["groupids"][0])


def _get_proxy_group_id(api: ZabbixAPI, name: str) -> str:
    found = api.call(
        "proxygroup.get",
        {"filter": {"name": name}, "output": ["proxy_groupid", "name"]},
    )
    if len(found) != 1:
        raise RuntimeError(f"active proxy group not found: {name!r}")
    return str(found[0]["proxy_groupid"])


def _get_host(api: ZabbixAPI, host: str) -> dict[str, Any] | None:
    found = api.call(
        "host.get",
        {
            "filter": {"host": host},
            "output": [
                "hostid",
                "host",
                "name",
                "status",
                "monitored_by",
                "proxy_groupid",
            ],
            "selectTags": "extend",
            "selectInterfaces": "extend",
            "selectParentTemplates": ["templateid", "host", "name"],
            "selectGroups": ["groupid", "name"],
        },
    )
    if len(found) > 1:
        raise RuntimeError(f"multiple hosts named {host!r}")
    return found[0] if found else None

def _legacy_usb_port_itemids(api: ZabbixAPI, hostid: str) -> list[str]:
    """Return only obsolete, discovered Cato USB physical-port item IDs.

    The current port LLD excludes USB.  Zabbix otherwise retains previously
    discovered resources for its seven-day lost-resource lifetime, including
    their noise-producing trigger instances.  Restrict deletion to an
    LLD-generated ``cato.port.*`` item whose *port* label is USB; a site name
    containing USB or a manually created item cannot match.
    """
    items = api.call(
        "item.get",
        {
            "hostids": hostid,
            "output": ["itemid", "name", "key_", "flags"],
            "selectDiscoveryRule": ["key_"],
        },
    )
    itemids: list[str] = []
    for item in items:
        discovery_rule = item.get("discoveryRule") or {}
        port_label = str(item.get("name", "")).rsplit("/", 1)[-1].split(":", 1)[0]
        if (
            str(item.get("flags")) == "4"
            and isinstance(discovery_rule, dict)
            and discovery_rule.get("key_") == "cato.port.discovery"
            and str(item.get("key_", "")).startswith("cato.port.")
            and "USB" in port_label.upper()
        ):
            itemids.append(str(item["itemid"]))
    return sorted(itemids, key=int)


def retire_legacy_usb_port_items(api: ZabbixAPI, hostid: str) -> int:
    """Delete obsolete USB port items and their generated trigger instances."""
    itemids = _legacy_usb_port_itemids(api, hostid)
    if not itemids:
        return 0
    deleted = {str(itemid) for itemid in api.call("item.delete", itemids)["itemids"]}
    if deleted != set(itemids):
        raise RuntimeError(
            "Cato USB retirement did not delete exactly the selected items: "
            f"selected={itemids} deleted={sorted(deleted, key=int)}"
        )
    return len(itemids)


def _legacy_lan_items(api: ZabbixAPI, hostid: str) -> list[dict[str, Any]]:
    """Return only discovered LAN items emitted by the superseded LLD rule."""
    items = api.call(
        "item.get",
        {
            "hostids": hostid,
            "output": ["itemid", "key_", "flags"],
            "selectDiscoveryRule": ["key_"],
        },
    )
    return sorted(
        [
            item
            for item in items
            if str(item.get("flags")) == "4"
            and (item.get("discoveryRule") or {}).get("key_")
            == LEGACY_LAN_DISCOVERY_KEY
            and str(item.get("key_", "")).startswith(LEGACY_LAN_ITEM_PREFIXES)
        ],
        key=lambda item: int(item["itemid"]),
    )


def _legacy_lan_graphids(
    api: ZabbixAPI, hostid: str, legacy_itemids: set[str]
) -> list[str]:
    """Return generated LAN graphs whose every item belongs to the old LLD."""
    if not legacy_itemids:
        return []
    graphs = api.call(
        "graph.get",
        {
            "hostids": hostid,
            "output": ["graphid", "name"],
            "selectGraphItems": "extend",
            "search": {"name": "Cato LAN "},
        },
    )
    graphids: list[str] = []
    for graph in graphs:
        itemids = {
            str(item["itemid"]) for item in graph.get("gitems") or []
        }
        if (
            str(graph.get("name", "")).startswith("Cato LAN ")
            and itemids
            and itemids <= legacy_itemids
        ):
            graphids.append(str(graph["graphid"]))
    return sorted(graphids, key=int)


def _legacy_lan_ruleids(api: ZabbixAPI, templateid: str) -> list[str]:
    rules = api.call(
        "discoveryrule.get",
        {
            "hostids": templateid,
            "filter": {"key_": [LEGACY_LAN_DISCOVERY_KEY]},
            "output": ["itemid", "key_"],
        },
    )
    return sorted((str(rule["itemid"]) for rule in rules), key=int)


def retire_legacy_lan_port_discovery(
    api: ZabbixAPI, hostid: str, templateid: str
) -> tuple[int, int, int]:
    """Remove the superseded LAN LLD before its duplicate graphs can recur."""
    ruleids = _legacy_lan_ruleids(api, templateid)
    if len(ruleids) > 1:
        raise RuntimeError(
            "multiple legacy Cato LAN discovery rules found: "
            f"{ruleids}"
        )
    legacy_items = _legacy_lan_items(api, hostid)
    itemids = {str(item["itemid"]) for item in legacy_items}
    graphids = _legacy_lan_graphids(api, hostid, itemids)

    if graphids:
        api.call("graph.delete", graphids)
    if itemids:
        api.call("item.delete", sorted(itemids, key=int))
    if ruleids:
        api.call("discoveryrule.delete", ruleids)

    remaining_ruleids = _legacy_lan_ruleids(api, templateid)
    remaining_items = _legacy_lan_items(api, hostid)
    remaining_graphids = _legacy_lan_graphids(
        api, hostid, {str(item["itemid"]) for item in remaining_items}
    )
    if remaining_ruleids or remaining_items or remaining_graphids:
        raise RuntimeError(
            "legacy Cato LAN retirement incomplete: "
            f"rules={remaining_ruleids} "
            f"items={[item['itemid'] for item in remaining_items]} "
            f"graphs={remaining_graphids}"
        )
    return len(ruleids), len(graphids), len(itemids)


def _owned(host_data: dict[str, Any]) -> bool:
    return any(
        tag.get("tag") == "managed_by" and tag.get("value") == "cato-pack"
        for tag in host_data.get("tags", [])
    )


def _set_host_macro(
    api: ZabbixAPI, hostid: str, macro: str, value: str, macro_type: int
) -> None:
    """Set one managed macro without round-tripping unrelated secret values."""
    current = api.call(
        "usermacro.get",
        {"hostids": hostid, "filter": {"macro": [macro]}, "output": "extend"},
    )
    if len(current) > 1:
        raise RuntimeError(f"multiple {macro} macros on host {hostid}")
    if current:
        api.call(
            "usermacro.update",
            {
                "hostmacroid": current[0]["hostmacroid"],
                "value": value,
                "type": macro_type,
            },
        )
    else:
        api.call(
            "usermacro.create",
            {"hostid": hostid, "macro": macro, "value": value, "type": macro_type},
        )


def _set_census_macros(api: ZabbixAPI, hostid: str, census: dict[str, int]) -> None:
    """Host-level expected counts from live USB-filtered GraphQL census."""
    for macro, field in CENSUS_EXPECTED_MACROS:
        _set_host_macro(api, hostid, macro, str(int(census[field])), TEXT)


def _set_cato_macros(api: ZabbixAPI, hostid: str, api_token: str) -> None:
    for macro, (value, macro_type) in host_macros().items():
        _set_host_macro(api, hostid, macro, value, macro_type)
    _set_host_macro(api, hostid, "{$CATO.API.TOKEN}", api_token, SECRET_TEXT)


def _host_payload(
    templateid: str,
    groupid: str,
    *,
    visible_name: str,
    proxy_groupid: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": visible_name,
        "groups": [{"groupid": groupid}],
        "templates": [{"templateid": templateid}],
        "tags": MANAGED_TAGS,
        "status": 0,
        "monitored_by": (
            SERVER_MONITORED if proxy_groupid is None else PROXY_GROUP_MONITORED
        ),
    }
    if proxy_groupid is not None:
        payload["proxy_groupid"] = proxy_groupid
    return payload


def ensure_account_host(
    api: ZabbixAPI,
    templateid: str,
    api_token: str,
    *,
    host: str = HOST,
    visible_name: str = VISIBLE_NAME,
    host_group: str = HOST_GROUP,
    proxy_group: str | None = None,
) -> str:
    """Make one owned, interface-free account collector host exactly converge."""
    if not api_token:
        raise RuntimeError("NBX_CATO_API_KEY is required")

    groupid = ensure_hostgroup(api, host_group)
    proxy_groupid = _get_proxy_group_id(api, proxy_group) if proxy_group else None
    payload = _host_payload(
        templateid,
        groupid,
        visible_name=visible_name,
        proxy_groupid=proxy_groupid,
    )
    existing = _get_host(api, host)

    if existing is not None:
        if not _owned(existing):
            raise RuntimeError(
                f"refusing to adopt unowned host {host!r}; add managed_by=cato-pack only after review"
            )
        hostid = str(existing["hostid"])
        old_templateids = [
            str(template["templateid"])
            for template in existing.get("parentTemplates", [])
            if str(template.get("templateid")) != str(templateid)
        ]
        update = {"hostid": hostid, **payload}
        if old_templateids:
            update["templates_clear"] = [
                {"templateid": old_id} for old_id in old_templateids
            ]
        # Extra templates can own interface-bound items. Unlink them before
        # deleting interfaces, or Zabbix rejects the interface deletion.
        api.call("host.update", update)

        interfaceids = [
            str(interface["interfaceid"])
            for interface in existing.get("interfaces", [])
        ]
        if interfaceids:
            api.call("hostinterface.delete", interfaceids)
    else:
        created = api.call(
            "host.create",
            {"host": host, "interfaces": [], **payload},
        )
        hostid = str(created["hostids"][0])

    _set_cato_macros(api, hostid, api_token)
    return hostid


def _template_pack_checks(api: ZabbixAPI, templateid: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    item_keys = {
        item["key_"]
        for item in api.call(
            "item.get", {"hostids": templateid, "output": ["itemid", "key_"]}
        )
    }
    missing_items = sorted(EXPECTED_TEMPLATE_ITEM_KEYS - item_keys)
    checks.append(
        _record(
            "Cato template master and health items",
            not missing_items,
            f"missing={missing_items}",
        )
    )

    lld_keys = {
        rule["key_"]
        for rule in api.call(
            "discoveryrule.get", {"hostids": templateid, "output": ["itemid", "key_"]}
        )
    }
    missing_lld = sorted(EXPECTED_DISCOVERY_KEYS - lld_keys)
    checks.append(
        _record(
            "Cato template discovery rules", not missing_lld, f"missing={missing_lld}"
        )
    )
    legacy_lld = sorted(
        key for key in lld_keys if key == LEGACY_LAN_DISCOVERY_KEY
    )
    checks.append(
        _record(
            "Cato legacy LAN discovery rule",
            not legacy_lld,
            f"present={legacy_lld}",
        )
    )


    graphs = api.call(
        "graphprototype.get", {"hostids": templateid, "output": ["graphid", "name"]}
    )
    triggers = api.call(
        "trigger.get",
        {
            "hostids": templateid,
            "output": ["triggerid", "description"],
            "selectDependencies": "extend",
        },
    )
    trigger_names = {trigger["description"] for trigger in triggers}
    missing_triggers = sorted(EXPECTED_COLLECTOR_TRIGGER_NAMES - trigger_names)
    checks.append(
        _record(
            "Cato template collector triggers",
            not missing_triggers,
            f"missing={missing_triggers}",
        )
    )
    trigger_names_by_id = {
        trigger["triggerid"]: trigger["description"] for trigger in triggers
    }
    unsupported_trigger = next(
        (
            trigger
            for trigger in triggers
            if trigger["description"] == "Cato API: Unsupported items present"
        ),
        None,
    )
    unsupported_dependencies = {
        trigger_names_by_id.get(dependency["triggerid"], "")
        for dependency in (unsupported_trigger or {}).get("dependencies", [])
    }
    checks.append(
        _record(
            "Cato unsupported-item trigger dependencies",
            unsupported_dependencies == EXPECTED_UNSUPPORTED_TRIGGER_DEPENDENCIES,
            f"dependencies={sorted(unsupported_dependencies)}",
        )
    )
    trigger_prototypes = api.call(
        "triggerprototype.get",
        {
            "hostids": templateid,
            "output": ["triggerid", "description", "expression", "priority"],
        },
    )
    trigger_prototype_names = {
        trigger_prototype["description"] for trigger_prototype in trigger_prototypes
    }
    missing_state_triggers = sorted(
        EXPECTED_STATE_TRIGGER_PROTOTYPE_NAMES - trigger_prototype_names
    )
    checks.append(
        _record(
            "Cato template state trigger prototypes",
            not missing_state_triggers,
            f"missing={missing_state_triggers}",
        )
    )
    state_triggers_using_nodata = sorted(
        trigger_prototype["description"]
        for trigger_prototype in trigger_prototypes
        if trigger_prototype["description"] in EXPECTED_STATE_TRIGGER_PROTOTYPE_NAMES
        and "nodata(" in trigger_prototype.get("expression", "").lower()
    )
    checks.append(
        _record(
            "Cato state triggers have no nodata",
            not state_triggers_using_nodata,
            f"nodata={state_triggers_using_nodata}",
        )
    )
    graph_names = {graph["name"] for graph in graphs}
    missing_graphs = sorted(EXPECTED_GRAPH_PROTOTYPES - graph_names)
    checks.append(
        _record(
            "Cato template SLA graph prototypes",
            not missing_graphs,
            f"missing={missing_graphs}",
        )
    )
    dashboards = api.call(
        "templatedashboard.get",
        {
            "templateids": templateid,
            "output": ["dashboardid", "name"],
            "selectPages": "extend",
        },
    )
    dash_by_name = {dashboard["name"]: dashboard for dashboard in dashboards}
    missing_dash = sorted(EXPECTED_DASHBOARD_NAMES - set(dash_by_name))
    checks.append(
        _record(
            "Cato Health/Path/Network dashboards",
            not missing_dash,
            f"missing={missing_dash} present={sorted(dash_by_name)}",
        )
    )
    health = dash_by_name.get("Health") or {}
    health_pages = {page["name"] for page in health.get("pages", [])}
    checks.append(
        _record(
            "Cato Health dashboard pages",
            health_pages == EXPECTED_HEALTH_PAGES,
            f"pages={sorted(health_pages)}",
        )
    )
    path = dash_by_name.get("Path") or {}
    path_pages = {page["name"] for page in path.get("pages", [])}
    checks.append(
        _record(
            "Cato Path dashboard pages",
            path_pages == EXPECTED_PATH_PAGES,
            f"pages={sorted(path_pages)}",
        )
    )
    network = dash_by_name.get("Network") or {}
    network_pages = {page["name"] for page in network.get("pages", [])}
    checks.append(
        _record(
            "Cato Network dashboard pages",
            network_pages == EXPECTED_NETWORK_PAGES,
            f"pages={sorted(network_pages)}",
        )
    )
    navigator_groups: dict[tuple[str, str, str], list[str]] = {}
    for dashboard in dashboards:
        for page in dashboard.get("pages", []):
            for widget in page.get("widgets", []):
                if widget.get("type") != "itemnavigator":
                    continue
                fields = {
                    field["name"]: field["value"]
                    for field in widget.get("fields", [])
                }
                groups: list[str] = []
                index = 0
                while f"group_by.{index}.tag_name" in fields:
                    groups.append(fields[f"group_by.{index}.tag_name"])
                    index += 1
                navigator_groups[
                    (dashboard["name"], page["name"], str(widget.get("name")))
                ] = groups
    checks.append(
        _record(
            "Cato dashboard nested navigator filters",
            navigator_groups == EXPECTED_DASHBOARD_NAVIGATOR_GROUPS,
            f"actual={navigator_groups}",
        )
    )
    navigator_limits: list[tuple[str, str, str, str]] = []
    for dashboard in dashboards:
        for page in dashboard.get("pages", []):
            for widget in page.get("widgets", []):
                if widget.get("type") != "itemnavigator":
                    continue
                fields = {
                    field["name"]: field["value"]
                    for field in widget.get("fields", [])
                }
                limit = str(fields.get("show_lines") or "")
                if limit != EXPECTED_NAVIGATOR_SHOW_LINES:
                    navigator_limits.append(
                        (
                            dashboard["name"],
                            page["name"],
                            str(widget.get("name")),
                            limit,
                        )
                    )
    checks.append(
        _record(
            "Cato dashboard navigator item limit",
            not navigator_limits,
            f"expected={EXPECTED_NAVIGATOR_SHOW_LINES} bad={navigator_limits}",
        )
    )
    item_references: dict[tuple[str, str, str], str] = {}
    invalid_item_reference_fields: dict[tuple[str, str, str], list[str]] = {}
    for dashboard in dashboards:
        for page in dashboard.get("pages", []):
            for widget in page.get("widgets", []):
                if widget.get("type") != "item":
                    continue
                fields = {
                    field["name"]: field["value"]
                    for field in widget.get("fields", [])
                }
                widget_key = (
                    dashboard["name"],
                    page["name"],
                    str(widget.get("name")),
                )
                if "itemid._reference" in fields:
                    item_references[widget_key] = fields["itemid._reference"]
                invalid = sorted(
                    field
                    for field in fields
                    if field.startswith("itemid.")
                    and field.endswith("._reference")
                    and field != "itemid._reference"
                )
                if invalid:
                    invalid_item_reference_fields[widget_key] = invalid
    checks.append(
        _record(
            "Cato dashboard Item value references",
            item_references == EXPECTED_DASHBOARD_ITEM_REFERENCES
            and not invalid_item_reference_fields,
            f"actual={item_references} invalid={invalid_item_reference_fields}",
        )
    )
    prototypes = api.call(
        "itemprototype.get",
        {"hostids": templateid, "output": ["itemid", "key_"]},
    )
    prototype_keys = {item["key_"] for item in prototypes}
    missing_prototypes = sorted(EXPECTED_ITEM_PROTOTYPE_KEYS - prototype_keys)
    checks.append(
        _record(
            "Cato template item prototypes",
            not missing_prototypes,
            f"missing={missing_prototypes}",
        )
    )
    site_disconnected = next(
        (
            trigger_prototype
            for trigger_prototype in trigger_prototypes
            if trigger_prototype["description"] == "Cato site {#SITE.NAME}: Disconnected"
        ),
        None,
    )
    site_priority = str((site_disconnected or {}).get("priority", ""))
    checks.append(
        _record(
            "Cato site disconnected is High not Disaster",
            site_priority == "4",
            f"priority={site_priority}",
        )
    )
    return checks


def verify_account_host(api: ZabbixAPI, hostid: str) -> list[dict[str, Any]]:
    """Read only: prove the collector has the intended isolated ownership shape."""
    checks: list[dict[str, Any]] = []
    found = api.call(
        "host.get",
        {
            "hostids": hostid,
            "output": [
                "hostid",
                "host",
                "name",
                "status",
                "monitored_by",
                "proxy_groupid",
            ],
            "selectTags": "extend",
            "selectInterfaces": "extend",
            "selectParentTemplates": ["templateid", "name"],
            "selectGroups": ["groupid", "name"],
        },
    )
    if len(found) != 1:
        return [_record("Cato account host", False, f"hostid={hostid} not found")]
    collector = found[0]
    checks.append(
        _record(
            "Cato account host ownership",
            _owned(collector)
            and collector["host"] in {collector_host(), sim_host(), HOST, SIM_HOST},
            collector["host"],
        )
    )
    checks.append(
        _record(
            "Cato account host enabled",
            str(collector.get("status", "")) == "0",
            f"status={collector.get('status')}",
        )
    )
    proxy_group = os.environ.get(CATO_PROXY_GROUP_ENV) or None
    if proxy_group:
        expected_proxy_groupid = _get_proxy_group_id(api, proxy_group)
        transport_ok = (
            str(collector.get("monitored_by")) == str(PROXY_GROUP_MONITORED)
            and str(collector.get("proxy_groupid")) == expected_proxy_groupid
        )
        transport_detail = f"proxy_group={proxy_group!r}"
    else:
        transport_ok = str(collector.get("monitored_by")) == str(SERVER_MONITORED)
        transport_detail = "Zabbix server"
    checks.append(
        _record("Cato account collector transport", transport_ok, transport_detail)
    )
    checks.append(
        _record(
            "Cato account host interfaces",
            not collector.get("interfaces", []),
            f"count={len(collector.get('interfaces', []))}",
        )
    )
    template_names = {
        template["name"] for template in collector.get("parentTemplates", [])
    }
    checks.append(
        _record(
            "Cato account host template",
            template_names == {TEMPLATE_NAME},
            f"templates={sorted(template_names)}",
        )
    )
    group_names = {group["name"] for group in collector.get("groups", [])}
    checks.append(
        _record(
            "Cato account host group",
            group_names == {HOST_GROUP},
            f"groups={sorted(group_names)}",
        )
    )
    actual_tags = {
        (tag.get("tag"), tag.get("value")) for tag in collector.get("tags", [])
    }
    expected_tags = {(tag["tag"], tag["value"]) for tag in MANAGED_TAGS}
    checks.append(
        _record(
            "Cato account host tags",
            actual_tags == expected_tags,
            f"tags={sorted(actual_tags)}",
        )
    )
    macros = {
        macro["macro"]: macro
        for macro in api.call("usermacro.get", {"hostids": hostid, "output": "extend"})
    }
    checks.append(
        _record(
            "Cato account URL macro",
            macros.get("{$CATO.API.URL}", {}).get("value") == CATO_API_URL,
            "present" if "{$CATO.API.URL}" in macros else "missing",
        )
    )
    checks.append(
        _record(
            "Cato account ID macro",
            macros.get("{$CATO.ACCOUNT.ID}", {}).get("value") == default_account_id(),
            "present" if "{$CATO.ACCOUNT.ID}" in macros else "missing",
        )
    )
    token = macros.get("{$CATO.API.TOKEN}")
    checks.append(
        _record(
            "Cato account token macro",
            bool(token) and int(token.get("type", -1)) == SECRET_TEXT,
            "secret-text present" if token else "missing",
        )
    )
    template = _exact_template(api)
    checks.extend(
        _template_pack_checks(api, str(template["templateid"]))
        if template is not None
        else [_record("Cato template", False, "missing")]
    )
    legacy_usb_itemids = _legacy_usb_port_itemids(api, hostid)
    checks.append(
        _record(
            "Cato legacy USB port items",
            not legacy_usb_itemids,
            f"count={len(legacy_usb_itemids)}",
        )
    )
    legacy_lan_items = _legacy_lan_items(api, hostid)
    legacy_lan_graphids = _legacy_lan_graphids(
        api, hostid, {str(item["itemid"]) for item in legacy_lan_items}
    )
    checks.append(
        _record(
            "Cato legacy LAN graphs and items",
            not legacy_lan_items and not legacy_lan_graphids,
            f"items={len(legacy_lan_items)} graphs={len(legacy_lan_graphids)}",
        )
    )

    return checks


def _tag_map(host_data: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (tag.get("tag", ""), tag.get("value", "")) for tag in host_data.get("tags", [])
    }


def _latest_text_history(api: ZabbixAPI, itemid: str) -> str | None:
    history = api.call(
        "history.get",
        {
            "history": 4,
            "itemids": [itemid],
            "sortfield": "clock",
            "sortorder": "DESC",
            "limit": 1,
        },
    )
    return str(history[0]["value"]) if history else None


def _snapshot_socket_serials(snapshot_value: str) -> set[str]:
    return snapshot_socket_serials(snapshot_value)


def _is_discovered_key(key: str, prefix: str) -> bool:
    return key.startswith(prefix) and "__seed" not in key


def verify_socket_hosts(
    api: ZabbixAPI,
    account_hostid: str,
    *,
    require_sockets: bool = False,
) -> list[dict[str, Any]]:
    """Compare Cato's last snapshot serials with NetBox-owned Socket ICMP hosts.

    Default is collector-safe: 0/N Socket ICMP hosts (the current hold) does
    not fail. Pass require_sockets=True only after the approved Socket
    migration.
    """
    checks: list[dict[str, Any]] = []
    masters = _master_items(api, account_hostid)
    snapshot_value = _latest_text_history(
        api, masters["cato.account.snapshot"]["itemid"]
    )
    if snapshot_value is None:
        return [
            _record("Cato snapshot serial source", False, "no accountSnapshot history")
        ]
    try:
        snapshot_serials = _snapshot_socket_serials(snapshot_value)
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return [
            _record(
                "Cato snapshot serial source",
                False,
                f"unreadable accountSnapshot: {exc}",
            )
        ]
    checks.append(
        _record(
            "Cato snapshot Socket serial census",
            bool(snapshot_serials),
            f"serials={len(snapshot_serials)}",
        )
    )

    tagged = api.call(
        "host.get",
        {
            "output": ["hostid", "host", "name"],
            "selectTags": "extend",
            "selectInterfaces": ["interfaceid", "type", "main", "ip"],
            "selectParentTemplates": ["templateid", "name"],
            "selectInventory": ["serialno_a"],
            "tags": [
                {"tag": "component", "value": "cato", "operator": 0},
                {"tag": "monitoring_domain", "value": "cato_socket", "operator": 0},
            ],
            "evaltype": 0,
        },
    )
    sockets = [
        host
        for host in tagged
        if str(host["hostid"]) != str(account_hostid)
        and {("component", "cato"), ("monitoring_domain", "cato_socket")}
        <= _tag_map(host)
    ]
    host_serials = {
        normalize_socket_serial((host.get("inventory") or {}).get("serialno_a"))
        for host in sockets
    }
    missing_serials = sorted(snapshot_serials - host_serials)
    unexpected_serials = sorted(host_serials - snapshot_serials)
    identity_ok = len(host_serials) == len(sockets) and not unexpected_serials
    if require_sockets:
        identity_ok = identity_ok and not missing_serials and len(sockets) > 0
    checks.append(
        _record(
            "Cato Socket ICMP host census",
            (not require_sockets and len(sockets) <= len(snapshot_serials))
            or (require_sockets and len(sockets) == len(snapshot_serials)),
            f"{len(sockets)}/{len(snapshot_serials)} hosts tagged component=cato, monitoring_domain=cato_socket",
        )
    )
    checks.append(
        _record(
            "Cato Socket inventory serial identity",
            identity_ok,
            f"missing={missing_serials} unexpected={unexpected_serials} require_sockets={require_sockets}",
        )
    )
    account_ping = api.call(
        "item.get",
        {
            "hostids": account_hostid,
            "filter": {"key_": ["icmpping"]},
            "output": ["itemid", "key_"],
        },
    )
    checks.append(
        _record(
            "Cato account host has no ICMP item",
            not account_ping,
            f"count={len(account_ping)}",
        )
    )

    now = int(time.time())
    for socket in sorted(sockets, key=lambda item: item["host"]):
        agent_interfaces = [
            interface
            for interface in socket.get("interfaces", [])
            if str(interface.get("type")) == "1"
        ]
        agent_interface_ok = len(agent_interfaces) == 1 and bool(
            agent_interfaces[0].get("ip")
        )
        checks.append(
            _record(
                f"{socket['host']} primary-IP Agent interface",
                agent_interface_ok,
                f"count={len(agent_interfaces)}",
            )
        )
        ping_items = api.call(
            "item.get",
            {
                "hostids": socket["hostid"],
                "filter": {"key_": ["icmpping"]},
                "output": ["itemid", "key_", "lastclock"],
            },
        )
        ping_fresh = (
            len(ping_items) == 1
            and int(ping_items[0].get("lastclock", 0) or 0)
            >= now - SNAPSHOT_FRESH_SECONDS
        )
        checks.append(
            _record(
                f"{socket['host']} current single icmpping",
                ping_fresh,
                f"count={len(ping_items)}",
            )
        )
        template_names = {
            template["name"] for template in socket.get("parentTemplates", [])
        }
        checks.append(
            _record(
                f"{socket['host']} stock ICMP Ping template",
                ICMP_TEMPLATE_NAME in template_names,
                f"templates={sorted(template_names)}",
            )
        )
        checks.append(
            _record(
                f"{socket['host']} not account collector",
                TEMPLATE_NAME not in template_names,
                f"templates={sorted(template_names)}",
            )
        )
    return checks


def _find_host_or_raise(api: ZabbixAPI, host: str) -> str:
    found = _get_host(api, host)
    if found is None:
        raise RuntimeError(f"host not found: {host}")
    return str(found["hostid"])


def _delete_sim_host(api: ZabbixAPI) -> None:
    found = _get_host(api, SIM_HOST)
    if found is not None:
        api.call("host.delete", [found["hostid"]])


def _master_items(api: ZabbixAPI, hostid: str) -> dict[str, dict[str, Any]]:
    items = api.call(
        "item.get",
        {
            "hostids": hostid,
            "filter": {"key_": list(MASTER_KEYS)},
            "output": ["itemid", "key_", "lastclock", "lastvalue", "state", "error"],
        },
    )
    by_key = {item["key_"]: item for item in items}
    missing = sorted(set(MASTER_KEYS) - set(by_key))
    if missing:
        raise RuntimeError(f"collector master items missing: {missing}")
    return by_key


def _all_host_items(api: ZabbixAPI, hostid: str) -> list[dict[str, Any]]:
    return api.call(
        "item.get",
        {
            "hostids": hostid,
            "output": ["itemid", "key_", "lastclock", "lastvalue", "state"],
        },
    )


def _socket_snapshot_census(snapshot_value: str) -> dict[str, int]:
    return snapshot_census(snapshot_value)


def _metrics_sla_census(metrics_value: str) -> int:
    return metrics_sla_census(metrics_value)


def _is_fresh(item: dict[str, Any], now: int, window: int) -> bool:
    return (
        str(item.get("state", "")) == "0"
        and int(item.get("lastclock", 0) or 0) >= now - window
    )


def _zero_counter(item: dict[str, Any] | None, now: int) -> bool:
    if item is None or not _is_fresh(item, now, METRICS_FRESH_SECONDS + 60):
        return False
    try:
        return float(item.get("lastvalue", "")) == 0
    except (TypeError, ValueError):
        return False


def _expected_data_families(census: dict[str, int]) -> dict[str, tuple[int, int, str]]:
    families: dict[str, tuple[int, int, str]] = {
        "cato.site.connected[": (census["sites"], SNAPSHOT_FRESH_SECONDS, "site state"),
        "cato.socket.connected[": (
            census["sockets"],
            SNAPSHOT_FRESH_SECONDS,
            "Socket state",
        ),
        "cato.socket.site_connected[": (
            census["sockets"],
            SNAPSHOT_FRESH_SECONDS,
            "Socket site state",
        ),
        "cato.socket.version[": (
            census["sockets"],
            SNAPSHOT_FRESH_SECONDS,
            "Socket version",
        ),
        "cato.wan.connected[": (
            census["wan_rows"],
            SNAPSHOT_FRESH_SECONDS,
            "WAN state",
        ),
        "cato.wan.site_connected[": (
            census["wan_rows"],
            SNAPSHOT_FRESH_SECONDS,
            "WAN site state",
        ),
        "cato.wan.tunnel_uptime[": (
            census["wan_rows"],
            SNAPSHOT_FRESH_SECONDS,
            "WAN uptime",
        ),
        "cato.wan.pop[": (census["wan_rows"], SNAPSHOT_FRESH_SECONDS, "WAN POP"),
    }
    families.update(
        {
            prefix: (census["sla_rows"], METRICS_FRESH_SECONDS, label)
            for prefix, label in SLA_PREFIXES.items()
        }
    )
    families["cato.wan.jitter.max.ms["] = (
        census["sla_rows"],
        METRICS_FRESH_SECONDS,
        "overlay jitter",
    )
    return families


def _collector_data_checks(
    api: ZabbixAPI,
    hostid: str,
    *,
    expected_census: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    """Verify fresh master history, discoveries, values, and collector counters."""
    records: list[dict[str, Any]] = []
    now = int(time.time())
    masters = _master_items(api, hostid)
    master_windows = {
        "cato.account.snapshot": SNAPSHOT_FRESH_SECONDS,
        "cato.account.metrics": METRICS_FRESH_SECONDS,
    }
    for key, window in master_windows.items():
        records.append(
            _record(
                f"Cato {key} HTTP 200/fresh",
                _is_fresh(masters[key], now, window),
                (
                    "supported and current"
                    if _is_fresh(masters[key], now, window)
                    else "unsupported or stale"
                ),
            )
        )

    snapshot_value = _latest_text_history(
        api, masters["cato.account.snapshot"]["itemid"]
    )
    metrics_value = _latest_text_history(api, masters["cato.account.metrics"]["itemid"])
    if snapshot_value is None or metrics_value is None:
        return records + [
            _record(
                "Cato master history bodies",
                False,
                "accountSnapshot or accountMetrics history is absent",
            )
        ]
    try:
        snapshot_census = _socket_snapshot_census(snapshot_value)
        metrics_rows = _metrics_sla_census(metrics_value)
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return records + [
            _record("Cato master history bodies", False, f"unreadable response: {exc}")
        ]

    census = {**snapshot_census, "sla_rows": metrics_rows}
    records.append(
        _record(
            "Cato current API discovery census",
            all(value > 0 for value in census.values()),
            f"sites={census['sites']} sockets={census['sockets']} wan={census['wan_rows']} sla={census['sla_rows']}",
        )
    )
    if expected_census is not None:
        records.append(
            _record(
                "Cato expected lab discovery census",
                census == expected_census,
                f"actual={census} expected={expected_census}",
            )
        )

    items = _all_host_items(api, hostid)
    by_key = {item["key_"]: item for item in items}
    counter_failures = sorted(
        key for key in COLLECTOR_COUNTER_KEYS if not _zero_counter(by_key.get(key), now)
    )
    records.append(
        _record(
            "Cato zero GraphQL/schema/unsupported counters",
            not counter_failures,
            f"nonzero_or_stale={counter_failures}",
        )
    )

    expected_prefixes = _expected_data_families(census)
    for prefix, (expected, window, label) in expected_prefixes.items():
        family = [item for item in items if _is_discovered_key(item["key_"], prefix)]
        stale = sum(not _is_fresh(item, now, window) for item in family)
        records.append(
            _record(
                f"Cato current {label} values",
                expected > 0 and len(family) == expected and stale == 0,
                f"count={len(family)} expected={expected} stale_or_unsupported={stale}",
            )
        )
    return records


def _force_items(api: ZabbixAPI, items: dict[str, dict[str, Any]]) -> None:
    for item in items.values():
        api.call("task.create", {"type": 6, "request": {"itemid": item["itemid"]}})


def _wait_for_advance(
    api: ZabbixAPI,
    hostid: str,
    keys: set[str],
    baseline: dict[str, int],
    *,
    timeout: int,
) -> dict[str, dict[str, Any]]:
    deadline = time.monotonic() + timeout
    while True:
        items = api.call(
            "item.get",
            {
                "hostids": hostid,
                "output": [
                    "itemid",
                    "key_",
                    "lastclock",
                    "lastvalue",
                    "state",
                    "error",
                ],
            },
        )
        relevant = {item["key_"]: item for item in items if item["key_"] in keys}
        if all(
            int(relevant.get(key, {}).get("lastclock", 0) or 0) > baseline.get(key, 0)
            for key in keys
        ):
            return relevant
        if time.monotonic() >= deadline:
            not_advanced = {
                key: relevant.get(key, {}).get("lastclock", "missing")
                for key in sorted(keys)
                if int(relevant.get(key, {}).get("lastclock", 0) or 0)
                <= baseline.get(key, 0)
            }
            raise RuntimeError(f"timed out waiting for item timestamps: {not_advanced}")
        time.sleep(5)


def _force_item_key(
    api: ZabbixAPI, hostid: str, key: str, *, timeout: int = 180
) -> dict[str, Any]:
    found = api.call(
        "item.get",
        {
            "hostids": hostid,
            "filter": {"key_": [key]},
            "output": ["itemid", "key_", "lastclock"],
        },
    )
    if len(found) != 1:
        raise RuntimeError(f"cannot force exactly one item for key {key!r}")
    item = found[0]
    baseline = {key: int(item.get("lastclock", 0) or 0)}
    api.call("task.create", {"type": 6, "request": {"itemid": item["itemid"]}})
    return _wait_for_advance(api, hostid, {key}, baseline, timeout=timeout)[key]

def _cato_problems(api: ZabbixAPI, hostid: str) -> list[dict[str, Any]]:
    return api.call(
        "problem.get",
        {
            "hostids": hostid,
            "output": ["eventid", "name", "severity"],
            "selectTags": "extend",
            "recent": False,
            "suppressed": False,
        },
    )


def _scope(problem: dict[str, Any]) -> str:
    for tag in problem.get("tags", []):
        if tag.get("tag") == "scope":
            return str(tag.get("value", ""))
    return ""


def _dependent_clock_baseline(api: ZabbixAPI, hostid: str) -> dict[str, int]:
    items = _all_host_items(api, hostid)
    return {
        item["key_"]: int(item.get("lastclock", 0) or 0)
        for item in items
        if item["key_"] not in MASTER_KEYS and item["key_"].startswith("cato.")
    }


def _wait_for_data_families(
    api: ZabbixAPI,
    hostid: str,
    census: dict[str, int],
    *,
    timeout: int,
    require_current: bool = False,
) -> tuple[bool, dict[str, int]]:
    expected = _expected_data_families(census)
    deadline = time.monotonic() + timeout
    counts: dict[str, int] = {}
    while True:
        items = _all_host_items(api, hostid)
        counts = {
            prefix: sum(_is_discovered_key(item["key_"], prefix) for item in items)
            for prefix in expected
        }
        counts_ready = all(counts[prefix] >= expected[prefix][0] for prefix in expected)
        values_current = all(
            counts[prefix] == expected[prefix][0]
            and all(
                _is_fresh(item, int(time.time()), expected[prefix][1])
                for item in items
                if _is_discovered_key(item["key_"], prefix)
            )
            for prefix in expected
        )
        if counts_ready and (not require_current or values_current):
            return True, counts
        if time.monotonic() >= deadline:
            return False, counts
        time.sleep(5)


def _run_happy_collection(api: ZabbixAPI, hostid: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    discovery_baseline = _dependent_clock_baseline(api, hostid)
    masters = _master_items(api, hostid)
    baseline = {
        key: int(item.get("lastclock", 0) or 0) for key, item in masters.items()
    }
    _force_items(api, masters)
    advanced = _wait_for_advance(api, hostid, set(MASTER_KEYS), baseline, timeout=180)
    records.append(_record("Cato master collection", True, "both masters advanced"))
    now = int(time.time())
    records.append(
        _record(
            "Cato master support state",
            all(
                _is_fresh(
                    advanced[key],
                    now,
                    (
                        SNAPSHOT_FRESH_SECONDS
                        if key.endswith("snapshot")
                        else METRICS_FRESH_SECONDS
                    ),
                )
                for key in MASTER_KEYS
            ),
            "all masters supported",
        )
    )
    health = _force_item_key(api, hostid, "zabbix[host,,items_unsupported]")
    records.append(
        _record(
            "Cato unsupported-item health collection",
            _is_fresh(health, int(time.time()), METRICS_FRESH_SECONDS + 60),
            "internal health item advanced",
        )
    )
    ready, counts = _wait_for_data_families(
        api, hostid, SIM_EXPECTED_CENSUS, timeout=180
    )
    records.append(
        _record(
            "Cato all discovery families created",
            ready,
            f"counts={counts}",
        )
    )
    if ready:
        masters = _master_items(api, hostid)
        second_baseline = {
            key: int(item.get("lastclock", 0) or 0) for key, item in masters.items()
        }
        _force_items(api, masters)
        _wait_for_advance(api, hostid, set(MASTER_KEYS), second_baseline, timeout=180)
        values_ready, value_counts = _wait_for_data_families(
            api,
            hostid,
            SIM_EXPECTED_CENSUS,
            timeout=180,
            require_current=True,
        )
    else:
        values_ready, value_counts = False, counts
    records.append(
        _record(
            "Cato all discovery family values current",
            values_ready,
            f"counts={value_counts}",
        )
    )
    records.extend(
        _collector_data_checks(api, hostid, expected_census=SIM_EXPECTED_CENSUS)
    )

    dependent_now = _dependent_clock_baseline(api, hostid)
    advanced_dependents = sum(
        1
        for key, clock in dependent_now.items()
        if clock > discovery_baseline.get(key, 0)
    )
    records.append(
        _record(
            "Cato dependent history",
            advanced_dependents > 0,
            f"advanced_items={advanced_dependents}",
        )
    )
    return records


def _run_collector_isolation(
    api: ZabbixAPI, hostid: str, api_token: str
) -> list[dict[str, Any]]:
    """Prove an HTTP collector failure remains collector-scoped after both nodata windows."""
    records: list[dict[str, Any]] = []
    before = {
        problem["eventid"]
        for problem in _cato_problems(api, hostid)
        if _scope(problem) in {"site", "socket", "wan"}
    }
    dependent_before = _dependent_clock_baseline(api, hostid)
    _set_host_macro(
        api, hostid, "{$CATO.API.TOKEN}", "invalid-cato-simulation-token", SECRET_TEXT
    )
    try:
        _force_items(api, _master_items(api, hostid))
        deadline = time.monotonic() + 16 * 60 + 30
        collector_problems: list[dict[str, Any]] = []
        state_problems: list[dict[str, Any]] = []
        while True:
            problems = _cato_problems(api, hostid)
            collector_problems = [
                problem for problem in problems if _scope(problem) == "collector"
            ]
            state_problems = [
                problem
                for problem in problems
                if _scope(problem) in {"site", "socket", "wan"}
            ]
            new_state = {problem["eventid"] for problem in state_problems} - before
            has_expected_nodata = {
                "Cato API: No snapshot data for 5m",
                "Cato API: No metrics data for 15m",
            } <= {problem["name"] for problem in collector_problems}
            if has_expected_nodata and not new_state:
                break
            if time.monotonic() >= deadline:
                break
            time.sleep(15)

        collector_names = {problem["name"] for problem in collector_problems}
        records.append(
            _record(
                "Cato invalid-token collector problems",
                {
                    "Cato API: No snapshot data for 5m",
                    "Cato API: No metrics data for 15m",
                }
                <= collector_names,
                f"collector_problems={sorted(collector_names)}",
            )
        )
        new_state = {problem["eventid"] for problem in state_problems} - before
        records.append(
            _record(
                "Cato invalid-token no service outage",
                not new_state,
                f"new_state_problems={len(new_state)}",
            )
        )
    finally:
        _set_host_macro(api, hostid, "{$CATO.API.TOKEN}", api_token, SECRET_TEXT)

    masters = _master_items(api, hostid)
    master_baseline = {
        key: int(item.get("lastclock", 0) or 0) for key, item in masters.items()
    }
    _force_items(api, masters)
    _wait_for_advance(api, hostid, set(MASTER_KEYS), master_baseline, timeout=180)
    _force_item_key(api, hostid, "zabbix[host,,items_unsupported]")

    deadline = time.monotonic() + 360
    active_collector: list[dict[str, Any]] = []
    dependent_after: dict[str, int] = {}
    while True:
        active_collector = [
            problem
            for problem in _cato_problems(api, hostid)
            if _scope(problem) == "collector"
        ]
        dependent_after = _dependent_clock_baseline(api, hostid)
        any_dependent_advanced = any(
            clock > dependent_before.get(key, 0)
            for key, clock in dependent_after.items()
        )
        if not active_collector and any_dependent_advanced:
            break
        if time.monotonic() >= deadline:
            break
        time.sleep(10)
    records.append(
        _record(
            "Cato collector recovery",
            not active_collector,
            f"active_collector_problems={len(active_collector)}",
        )
    )
    records.append(
        _record(
            "Cato dependent timestamps recover",
            any(
                clock > dependent_before.get(key, 0)
                for key, clock in dependent_after.items()
            ),
            "dependent values advanced after token restoration",
        )
    )
    records.extend(
        _collector_data_checks(api, hostid, expected_census=SIM_EXPECTED_CENSUS)
    )
    return records


def apply_cato_pack(
    api: ZabbixAPI,
    api_token: str,
    *,
    host: str | None = None,
    visible_name: str | None = None,
    proxy_group: str | None = None,
    census: dict[str, int] | None = None,
    skip_preflight: bool = False,
) -> list[dict[str, Any]]:
    """Fail-closed GraphQL preflight, then import YAML and converge the collector."""
    if not api_token:
        raise RuntimeError(f"{CATO_API_KEY_ENV} is required")
    live = census
    if not skip_preflight or live is None:
        errors, collected = collect_cato_preflight(
            api_key=api_token, account_id=default_account_id()
        )
        if errors:
            raise RuntimeError("Cato GraphQL preflight failed:\n  " + "\n  ".join(errors))
        live = collected
    if proxy_group:
        _get_proxy_group_id(api, proxy_group)
    templateid = import_template(api)
    hostid = ensure_account_host(
        api,
        templateid,
        api_token,
        host=host or collector_host(),
        visible_name=visible_name or collector_visible_name(),
        proxy_group=proxy_group,
    )
    _set_census_macros(api, hostid, live)
    legacy_rules, legacy_graphs, legacy_items = retire_legacy_lan_port_discovery(
        api, hostid, templateid
    )
    retired_usb = retire_legacy_usb_port_items(api, hostid)
    records = [
        _record(
            "Cato legacy LAN discovery retired",
            True,
            f"rules={legacy_rules} graphs={legacy_graphs} items={legacy_items}",
        ),
        _record("Cato legacy USB port items retired", True, f"count={retired_usb}"),
    ]
    records.extend(verify_account_host(api, hostid))
    return records


def verify_cato_collector(
    api: ZabbixAPI,
    *,
    require_sockets: bool = False,
    check_live_data: bool = True,
) -> list[dict[str, Any]]:
    """Read-only collector verification. Socket ICMP census is optional."""
    template = _exact_template(api)
    if template is None:
        return [_record("Cato template", False, "missing")]
    collector = _get_host(api, collector_host())
    if collector is None:
        records = [_record("Cato account host", False, "missing")]
        records.extend(_template_pack_checks(api, str(template["templateid"])))
        return records
    hostid = str(collector["hostid"])
    records = verify_account_host(api, hostid)
    if check_live_data:
        records.extend(_collector_data_checks(api, hostid))
    if require_sockets:
        records.extend(verify_socket_hosts(api, hostid, require_sockets=True))
    else:
        records.extend(verify_socket_hosts(api, hostid, require_sockets=False))
    return records


def run_simulate() -> int:
    """Exercise import, owned host lifecycle, discovery, and isolation in the lab."""
    api_token = os.environ.get(CATO_API_KEY_ENV, "")
    if not api_token:
        raise RuntimeError(f"{CATO_API_KEY_ENV} is required for --simulate")
    errors, census = collect_cato_preflight(
        api_key=api_token, account_id=default_account_id()
    )
    if errors:
        raise RuntimeError("Cato GraphQL preflight failed:\n  " + "\n  ".join(errors))
    api = ZabbixAPI.from_lab()
    _delete_sim_host(api)
    first_templateid = import_template(api)
    second_templateid = import_template(api)
    records = [
        _record(
            "Cato template idempotent import",
            first_templateid == second_templateid,
            f"templateid={second_templateid}",
        )
    ]
    hostid = ensure_account_host(
        api,
        second_templateid,
        api_token,
        host=SIM_HOST,
        visible_name=f"{VISIBLE_NAME} (simulation)",
    )
    _set_census_macros(api, hostid, census)
    second_hostid = ensure_account_host(
        api,
        second_templateid,
        api_token,
        host=SIM_HOST,
        visible_name=f"{VISIBLE_NAME} (simulation)",
    )
    records.append(
        _record(
            "Cato account host idempotent convergence",
            hostid == second_hostid,
            f"hostid={second_hostid}",
        )
    )
    records.extend(verify_account_host(api, hostid))
    happy_records = _run_happy_collection(api, hostid)
    records.extend(happy_records)
    if _all_pass(happy_records):
        records.extend(_run_collector_isolation(api, hostid, api_token))
    else:
        records.append(
            _record(
                "Cato collector-isolation prerequisite",
                False,
                "valid collection did not establish a baseline; check Cato account access",
            )
        )
    return 0 if _all_pass(records) else 1


def _production_api() -> ZabbixAPI:
    url = os.environ.get("NBX_ZABBIX_URL", "")
    token = os.environ.get("NBX_ZABBIX_TOKEN", "")
    if not url or not token:
        raise RuntimeError("NBX_ZABBIX_URL and NBX_ZABBIX_TOKEN are required")
    return ZabbixAPI(url, token=token)


def run_apply() -> int:
    """Import the pack and converge the one production account host."""
    api_token = os.environ.get(CATO_API_KEY_ENV, "")
    if not api_token:
        raise RuntimeError(f"{CATO_API_KEY_ENV} is required for --apply")
    api = _production_api()
    records = apply_cato_pack(
        api,
        api_token,
        proxy_group=os.environ.get(CATO_PROXY_GROUP_ENV) or None,
    )
    return 0 if _all_pass(records) else 1


def run_verify(*, require_sockets: bool = False) -> int:
    """Read only: verify the imported pack and collector host.

    Socket ICMP serial matching is informational during the 0/21 hold.
    Pass ``--require-sockets`` only after the approved Socket migration.
    """
    api = _production_api()
    records = verify_cato_collector(api, require_sockets=require_sockets)
    return 0 if _all_pass(records) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument(
        "--simulate",
        action="store_true",
        help="run full collector proof against local Zabbix lab",
    )
    actions.add_argument(
        "--apply",
        action="store_true",
        help="GraphQL preflight, import pack, converge production account host",
    )
    actions.add_argument(
        "--verify",
        action="store_true",
        help="read-only production collector verification (Socket ICMP optional)",
    )
    parser.add_argument(
        "--require-sockets",
        action="store_true",
        help="with --verify, fail when snapshot serials are missing from Socket ICMP hosts",
    )
    args = parser.parse_args()
    if args.require_sockets and not args.verify:
        raise SystemExit("--require-sockets is only valid with --verify")
    try:
        if args.simulate:
            return run_simulate()
        if args.apply:
            return run_apply()
        return run_verify(require_sockets=args.require_sockets)
    except Exception as exc:
        # Do not include environment values, request bodies, or macro contents in errors.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
