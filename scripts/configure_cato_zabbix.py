#!/usr/bin/env python3
"""Install and verify the Cato account-scoped Zabbix monitoring pack.

The Cato API represents an account, not a NetBox device.  This script owns the
single collector host and its secret macro.  It deliberately does not create or
manage Socket hosts; nbxSync owns those NetBox-backed ICMP hosts.

Usage:
  NBX_CATO_API_KEY=... python scripts/configure_cato_zabbix.py --simulate
  NBX_ZABBIX_URL=https://zabbix.example NBX_ZABBIX_TOKEN=... \\
    NBX_CATO_API_KEY=... python scripts/configure_cato_zabbix.py --apply
  NBX_ZABBIX_URL=https://zabbix.example NBX_ZABBIX_TOKEN=... \\
    python scripts/configure_cato_zabbix.py --verify

``--simulate`` uses the local Zabbix lab and creates only ``cato-sim-account-964``.
It exercises a valid Cato collection, then an invalid-token collector failure;
it is intentionally slow because it waits through the template's 5m/15m
no-data windows.
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

TEMPLATE_NAME = "Cato Networks by HTTP"
HOST = "cato-account-964"
VISIBLE_NAME = "Cato Account 964"
HOST_GROUP = "Applications/Cato"
SIM_HOST = "cato-sim-account-964"
ICMP_TEMPLATE_NAME = "ICMP Ping"

TEMPLATE_PATH = ROOT / "zabbix/templates/cato_http/template_cato_networks_http.yaml"
CATO_API_URL = "https://api.catonetworks.com/api/v1/graphql2"
CATO_ACCOUNT_ID = "964"
SECRET_TEXT = 1
TEXT = 0
SERVER_MONITORED = 0
PROXY_GROUP_MONITORED = 2

MANAGED_TAGS = [
    {"tag": "managed_by", "value": "cato-pack"},
    {"tag": "component", "value": "cato"},
    {"tag": "monitoring_domain", "value": "cato_overlay"},
]
CATO_MACROS = {
    "{$CATO.API.URL}": (CATO_API_URL, TEXT),
    "{$CATO.ACCOUNT.ID}": (CATO_ACCOUNT_ID, TEXT),
}
MASTER_KEYS = ("cato.account.snapshot", "cato.account.metrics")
EXPECTED_TEMPLATE_ITEM_KEYS = {
    "cato.account.snapshot",
    "cato.account.metrics",
    "cato.api.snapshot.error_count",
    "cato.api.metrics.error_count",
    "cato.api.snapshot.schema_violation_count",
    "cato.api.metrics.schema_violation_count",
    "zabbix[host,,items_unsupported]",
}
EXPECTED_DISCOVERY_KEYS = {
    "cato.site.discovery",
    "cato.socket.discovery",
    "cato.wan.discovery",
    "cato.wan.metrics.discovery",
}
EXPECTED_GRAPH_PROTOTYPES = {
    "Cato WAN {#SITE.NAME} / {#LINK.NAME}: Bandwidth",
    "Cato WAN {#SITE.NAME} / {#LINK.NAME}: Packet loss",
    "Cato WAN {#SITE.NAME} / {#LINK.NAME}: Latency and jitter",
}
EXPECTED_COLLECTOR_TRIGGER_NAMES = {
    "Cato API: Snapshot GraphQL errors",
    "Cato API: Metrics GraphQL errors",
    "Cato API: Snapshot GraphQL schema violations",
    "Cato API: Metrics GraphQL schema violations",
    "Cato API: Unsupported items present",
    "Cato API: No snapshot data for 5m",
    "Cato API: No metrics data for 15m",
}
EXPECTED_STATE_TRIGGER_PROTOTYPE_NAMES = {
    "Cato site {#SITE.NAME}: Disconnected",
    "Cato Socket {#SERIAL}: Disconnected while site is up",
    "Cato WAN {#SITE.NAME} / {#LINK.NAME}: Disconnected while site is up",
}
EXPECTED_UNSUPPORTED_TRIGGER_DEPENDENCIES = {
    "Cato API: No snapshot data for 5m",
    "Cato API: No metrics data for 15m",
}

SLA_PREFIXES = {
    "cato.wan.rx.bps[": "RX bandwidth",
    "cato.wan.tx.bps[": "TX bandwidth",
    "cato.wan.loss.rx.pct[": "RX loss",
    "cato.wan.loss.tx.pct[": "TX loss",
    "cato.wan.jitter.rx.ms[": "RX jitter",
    "cato.wan.jitter.tx.ms[": "TX jitter",
    "cato.wan.rtt.ms[": "RTT",
}
COLLECTOR_COUNTER_KEYS = {
    "cato.api.snapshot.error_count",
    "cato.api.metrics.error_count",
    "cato.api.snapshot.schema_violation_count",
    "cato.api.metrics.schema_violation_count",
    "zabbix[host,,items_unsupported]",
}
SNAPSHOT_FRESH_SECONDS = 5 * 60
METRICS_FRESH_SECONDS = 15 * 60
SIM_EXPECTED_CENSUS = {"sites": 11, "sockets": 21, "wan_rows": 33, "sla_rows": 17}


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


def _set_cato_macros(api: ZabbixAPI, hostid: str, api_token: str) -> None:
    for macro, (value, macro_type) in CATO_MACROS.items():
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
        {"hostids": templateid, "output": ["triggerid", "description", "expression"]},
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
            "selectPages": ["name"],
        },
    )
    health = [dashboard for dashboard in dashboards if dashboard["name"] == "Health"]
    page_names = (
        {page["name"] for page in health[0].get("pages", [])}
        if len(health) == 1
        else set()
    )
    checks.append(
        _record(
            "Cato Health dashboard",
            len(health) == 1 and page_names == {"Overview", "WAN SLA"},
            f"count={len(health)} pages={sorted(page_names)}",
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
            _owned(collector) and collector["host"] in {HOST, SIM_HOST},
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
    proxy_group = os.environ.get("NBX_CATO_PROXY_GROUP") or None
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
            macros.get("{$CATO.ACCOUNT.ID}", {}).get("value") == CATO_ACCOUNT_ID,
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
    root = json.loads(snapshot_value)
    data = root.get("data") or {}
    snapshot = data.get("accountSnapshot") or {}
    serials: set[str] = set()
    for site in snapshot.get("sites", []) or []:
        info = site.get("info") or {}
        if not str(info.get("connType") or "").startswith("SOCKET_"):
            continue
        for device in site.get("devices", []) or []:
            serial = str((device.get("socketInfo") or {}).get("serial") or "").strip()
            if serial:
                serials.add(serial)
    return serials


def verify_socket_hosts(api: ZabbixAPI, account_hostid: str) -> list[dict[str, Any]]:
    """Compare Cato's last snapshot serials with NetBox-owned Socket ICMP hosts."""
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

    all_hosts = api.call(
        "host.get",
        {
            "output": ["hostid", "host", "name"],
            "selectTags": "extend",
            "selectInterfaces": ["interfaceid", "type", "main", "ip"],
            "selectParentTemplates": ["templateid", "name"],
            "selectInventory": ["serialno_a"],
        },
    )
    sockets = [
        host
        for host in all_hosts
        if str(host["hostid"]) != str(account_hostid)
        and {("component", "cato"), ("monitoring_domain", "cato_socket")}
        <= _tag_map(host)
    ]
    host_serials = {
        str((host.get("inventory") or {}).get("serialno_a") or "").strip()
        for host in sockets
    }
    host_serials.discard("")
    missing_serials = sorted(snapshot_serials - host_serials)
    unexpected_serials = sorted(host_serials - snapshot_serials)
    checks.append(
        _record(
            "Cato Socket ICMP host census",
            len(sockets) <= len(snapshot_serials),
            f"{len(sockets)}/{len(snapshot_serials)} hosts tagged component=cato, monitoring_domain=cato_socket",
        )
    )
    checks.append(
        _record(
            "Cato Socket inventory serial identity",
            len(host_serials) == len(sockets) and not unexpected_serials,
            f"missing={missing_serials} unexpected={unexpected_serials}",
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
    root = json.loads(snapshot_value)
    data = root.get("data") or {}
    snapshot = data.get("accountSnapshot") or {}
    sites = sockets = wan_rows = 0
    for site in snapshot.get("sites", []) or []:
        info = site.get("info") or {}
        if not str(info.get("connType") or "").startswith("SOCKET_"):
            continue
        sites += 1
        for device in site.get("devices", []) or []:
            socket = device.get("socketInfo") or {}
            if not str(socket.get("serial") or "").strip():
                continue
            sockets += 1
            wan_rows += sum(
                1
                for interface in device.get("interfaces", []) or []
                if (interface.get("info") or {}).get("id") is not None
            )
    return {"sites": sites, "sockets": sockets, "wan_rows": wan_rows}


def _metrics_sla_census(metrics_value: str) -> int:
    root = json.loads(metrics_value)
    data = root.get("data") or {}
    metrics = data.get("accountMetrics") or {}
    pairs: set[tuple[str, str]] = set()
    for site in metrics.get("sites", []) or []:
        info = site.get("info") or {}
        site_id = site.get("id")
        if site_id is None or not str(info.get("connType") or "").startswith("SOCKET_"):
            continue
        for interface in site.get("interfaces", []) or []:
            interface_info = interface.get("interfaceInfo") or {}
            link_id = interface_info.get("id")
            if link_id is not None:
                pairs.add((str(site_id), str(link_id)))
    return len(pairs)


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
        family = [item for item in items if item["key_"].startswith(prefix)]
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
            prefix: sum(item["key_"].startswith(prefix) for item in items)
            for prefix in expected
        }
        counts_ready = all(counts[prefix] >= expected[prefix][0] for prefix in expected)
        values_current = all(
            counts[prefix] == expected[prefix][0]
            and all(
                _is_fresh(item, int(time.time()), expected[prefix][1])
                for item in items
                if item["key_"].startswith(prefix)
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


def run_simulate() -> int:
    """Exercise import, owned host lifecycle, discovery, and isolation in the lab."""
    api_token = os.environ.get("NBX_CATO_API_KEY", "")
    if not api_token:
        raise RuntimeError("NBX_CATO_API_KEY is required for --simulate")
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
    api_token = os.environ.get("NBX_CATO_API_KEY", "")
    if not api_token:
        raise RuntimeError("NBX_CATO_API_KEY is required for --apply")
    api = _production_api()
    proxy_group = os.environ.get("NBX_CATO_PROXY_GROUP") or None
    if proxy_group:
        _get_proxy_group_id(api, proxy_group)
    templateid = import_template(api)
    hostid = ensure_account_host(api, templateid, api_token, proxy_group=proxy_group)
    records = verify_account_host(api, hostid)
    return 0 if _all_pass(records) else 1


def run_verify() -> int:
    """Read only: verify the imported pack, collector host, and Socket ICMP census."""
    api = _production_api()
    template = _exact_template(api)
    if template is None:
        records = [_record("Cato template", False, "missing")]
        return 0 if _all_pass(records) else 1
    collector = _get_host(api, HOST)
    if collector is None:
        records = [_record("Cato account host", False, "missing")]
        records.extend(_template_pack_checks(api, str(template["templateid"])))
        return 0 if _all_pass(records) else 1
    records = verify_account_host(api, str(collector["hostid"]))
    records.extend(_collector_data_checks(api, str(collector["hostid"])))
    records.extend(verify_socket_hosts(api, str(collector["hostid"])))
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
        help="import pack and converge production account host",
    )
    actions.add_argument(
        "--verify",
        action="store_true",
        help="read-only production account and Socket-host verification",
    )
    args = parser.parse_args()
    try:
        if args.simulate:
            return run_simulate()
        if args.apply:
            return run_apply()
        return run_verify()
    except Exception as exc:
        # Do not include environment values, request bodies, or macro contents in errors.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
