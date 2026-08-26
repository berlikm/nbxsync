#!/usr/bin/env python3
"""Cato HTTP collector contract (no Django, no Zabbix).

Collector refresh is ``configure_nbxsync_network.py --apply-cato``.
That path imports the YAML, fail-closes on GraphQL preflight, and converges
the one owned account host. It does **not** run zerotouch, HostSync Socket
devices, or mutate NetBox Socket roles.

``configure_cato_zabbix.py`` remains the Zabbix-API implementation used by
the network script and by lab ``--simulate``.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / 'zabbix/templates/cato_http'
TEMPLATE_PATH = TEMPLATE_DIR / 'template_cato_networks_http.yaml'
LLD_JS = {
    'cato.site.discovery': TEMPLATE_DIR / 'lld_sites.js',
    'cato.socket.discovery': TEMPLATE_DIR / 'lld_sockets.js',
    'cato.wan.discovery': TEMPLATE_DIR / 'lld_wan.js',
    'cato.wan.metrics.discovery': TEMPLATE_DIR / 'lld_wan_metrics.js',
    'cato.port.discovery': TEMPLATE_DIR / 'lld_ports.js',
}

TEMPLATE_NAME = 'Cato Networks by HTTP'
HOST_GROUP = 'Applications/Cato'
ICMP_TEMPLATE_NAME = 'ICMP Ping'
CATO_API_URL = 'https://api.catonetworks.com/api/v1/graphql2'
CATO_API_KEY_ENV = 'NBX_CATO_API_KEY'
CATO_ACCOUNT_ID_ENV = 'NBX_CATO_ACCOUNT_ID'
CATO_HOST_ENV = 'NBX_CATO_HOST'
CATO_PROXY_GROUP_ENV = 'NBX_CATO_PROXY_GROUP'
DEFAULT_ACCOUNT_ID = '964'
DEFAULT_CONN_TYPE = '^SOCKET_'

SECRET_TEXT = 1
TEXT = 0
SERVER_MONITORED = 0
PROXY_GROUP_MONITORED = 2

MANAGED_TAGS = [
    {'tag': 'managed_by', 'value': 'cato-pack'},
    {'tag': 'component', 'value': 'cato'},
    {'tag': 'monitoring_domain', 'value': 'cato_overlay'},
]

SNAPSHOT_QUERY = (
    'query AccountSnapshot($accountID: ID!) { accountSnapshot(accountID: $accountID) { '
    'sites { id connectivityStatus operationalStatus lastConnected connectedSince '
    'popName hostCount '
    'degradedStatus { isDegraded degradedDetails { reason } } '
    'info { name type connType isHA sockets { id serial isPrimary platform version } } '
    'haStatus { readiness wanConnectivity keepalive socketVersion } '
    'devices { id name connected connectedSince haRole version deviceUptime '
    'socketInfo { id serial isPrimary platform version } '
    'interfacesLinkState { id mediaIn up hasAddress hasInternet hasTunnel duplex linkSpeed } '
    'interfaces { id name connected popName tunnelUptime type physicalPort '
    'tunnelRemoteIP tunnelConnectionReason tunnelRemoteIPInfo { provider } '
    'info { id name upstreamBandwidth downstreamBandwidth destType } } } } } }'
)

METRICS_QUERY = (
    'query AccountMetrics($accountID: ID!) { accountMetrics(accountID: $accountID, '
    'timeFrame: "last.PT5M", groupDevices: true, groupInterfaces: false) { '
    'sites { id name info { connType } interfaces { name '
    'interfaceInfo { id name upstreamBandwidth downstreamBandwidth destType } '
    'metrics(toRate: true) { bytesDownstream bytesUpstream '
    'lostDownstreamPcnt lostUpstreamPcnt jitterDownstream jitterUpstream rtt '
    'packetsDiscardedDownstream packetsDiscardedUpstream } '
    'timeseries(labels: [lastMilePacketLoss, lastMileLatency], buckets: 1) { label data } '
    '} } } }'
)

MASTER_KEYS = ('cato.account.snapshot', 'cato.account.metrics')
EXPECTED_TEMPLATE_ITEM_KEYS = {
    'cato.account.snapshot',
    'cato.account.metrics',
    'cato.api.snapshot.error_count',
    'cato.api.metrics.error_count',
    'cato.api.snapshot.schema_violation_count',
    'cato.api.metrics.schema_violation_count',
    'cato.api.snapshot.available',
    'cato.api.metrics.available',
    'cato.site.connected[__seed]',
    'cato.site.degraded[__seed]',
    'cato.socket.connected[__seed]',
    'cato.wan.connected[__seed]',
    'cato.site.ha.readiness.code[__seed]',
    'cato.wan.rx.bps[__seed]',
    'cato.site.discovery.count',
    'cato.socket.discovery.count',
    'cato.wan.discovery.count',
    'cato.wan.metrics.discovery.count',
    'cato.site.up.count',
    'cato.socket.up.count',
    'cato.wan.up.count',
    'cato.site.degraded.count',
    'cato.site.ha.not_ready.count',
    'cato.wan.loss.worst.pct',
    'cato.wan.rtt.worst.ms',
    'cato.wan.jitter.worst.ms',
    'cato.wan.lastmile.loss.worst.pct',
    'cato.wan.lastmile.latency.worst.ms',
    'cato.wan.rx.util.worst.pct',
    'cato.wan.tx.util.worst.pct',
    'zabbix[host,,items_unsupported]',
}
EXPECTED_DISCOVERY_KEYS = set(LLD_JS)
EXPECTED_DASHBOARD_NAMES = {'Health', 'Path', 'Network'}
EXPECTED_HEALTH_PAGES = {'Overview', 'Census', 'Degraded', 'API'}
EXPECTED_PATH_PAGES = {'Overview', 'Last mile', 'Probe'}
EXPECTED_NETWORK_PAGES = {'Overview', 'Tunnels', 'HA', 'Ports'}
EXPECTED_DASHBOARD_NAVIGATOR_GROUPS = {
    ('Health', 'Degraded', 'Degraded'): ['site', 'connection_type'],
    ('Path', 'Probe', 'Counters'): ['site', 'connection_type', 'dest_type'],
    ('Network', 'Tunnels', 'Tunnels'): [
        'site',
        'connection_type',
        'ha_role',
        'dest_type',
    ],
    ('Network', 'HA', 'HA'): ['site', 'connection_type'],
    ('Network', 'Ports', 'Ports'): [
        'site',
        'port_kind',
        'ha_role',
        'connection_type',
    ],
}
EXPECTED_GRAPH_PROTOTYPES = {
    'Cato WAN {#SITE.NAME} / {#LINK.NAME}: Bandwidth',
    'Cato WAN {#SITE.NAME} / {#LINK.NAME}: Packet loss',
    'Cato WAN {#SITE.NAME} / {#LINK.NAME}: RTT',
    'Cato WAN {#SITE.NAME} / {#LINK.NAME}: Jitter',
}
EXPECTED_COLLECTOR_TRIGGER_NAMES = {
    'Cato API: Snapshot GraphQL errors',
    'Cato API: Metrics GraphQL errors',
    'Cato API: Snapshot GraphQL schema violations',
    'Cato API: Metrics GraphQL schema violations',
    'Cato API: Unsupported items present',
    'Cato API: No snapshot data for 5m',
    'Cato API: No metrics data for 15m',
    'Cato census: fewer Socket sites than expected',
    'Cato census: fewer Sockets than expected',
    'Cato census: fewer WAN links than expected',
    'Cato census: fewer WAN SLA rows than expected',
}
EXPECTED_STATE_TRIGGER_PROTOTYPE_NAMES = {
    'Cato site {#SITE.NAME}: Disconnected',
    'Cato site {#SITE.NAME}: Degraded',
    'Cato Socket {#SITE.NAME} / {#SERIAL}: Disconnected while site is up',
    'Cato WAN {#SITE.NAME} / {#SERIAL} / {#LINK.NAME}: Disconnected while site is up',
    'Cato site {#SITE.NAME}: HA not ready',
    'Cato site {#SITE.NAME}: HA socket version not ok',
    'Cato WAN {#SITE.NAME} / {#LINK.NAME}: High overlay packet loss',
    'Cato WAN {#SITE.NAME} / {#LINK.NAME}: High last-mile packet loss',
    'Cato WAN {#SITE.NAME} / {#LINK.NAME}: High overlay RTT',
    'Cato wan port {#SITE.NAME} / {#SERIAL} / {#PORT.ID}: Media down',
    'Cato lan port {#SITE.NAME} / {#SERIAL} / {#PORT.ID}: Media down',
    'Cato wan port {#SITE.NAME} / {#SERIAL} / {#PORT.ID}: No tunnel while media is up',
}
EXPECTED_UNSUPPORTED_TRIGGER_DEPENDENCIES = {
    'Cato API: No snapshot data for 5m',
    'Cato API: No metrics data for 15m',
}
EXPECTED_ITEM_PROTOTYPE_KEYS = {
    'cato.site.connected[{#SITE.ID}]',
    'cato.site.operational_status[{#SITE.ID}]',
    'cato.site.degraded[{#SITE.ID}]',
    'cato.site.degraded.reasons[{#SITE.ID}]',
    'cato.site.pop[{#SITE.ID}]',
    'cato.site.host_count[{#SITE.ID}]',
    'cato.site.ha[{#SITE.ID}]',
    'cato.site.ha.readiness[{#SITE.ID}]',
    'cato.site.ha.readiness.code[{#SITE.ID}]',
    'cato.site.ha.socket_version[{#SITE.ID}]',
    'cato.socket.connected[{#SITE.ID},{#SOCKET.ID}]',
    'cato.socket.uptime[{#SITE.ID},{#SOCKET.ID}]',
    'cato.wan.connected[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]',
    'cato.wan.dest_type[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]',
    'cato.wan.physical_port[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]',
    'cato.wan.provider[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]',
    'cato.wan.remote_ip[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]',
    'cato.wan.connection_reason[{#SITE.ID},{#SOCKET.ID},{#LINK.ID}]',
    'cato.port.media_in[{#SITE.ID},{#SOCKET.ID},{#PORT.ID}]',
    'cato.port.up[{#SITE.ID},{#SOCKET.ID},{#PORT.ID}]',
    'cato.port.has_tunnel[{#SITE.ID},{#SOCKET.ID},{#PORT.ID}]',
    'cato.port.has_internet[{#SITE.ID},{#SOCKET.ID},{#PORT.ID}]',
    'cato.port.kind.code[{#SITE.ID},{#SOCKET.ID},{#PORT.ID}]',
    'cato.wan.rx.bps[{#SITE.ID},{#LINK.ID}]',
    'cato.wan.tx.bps[{#SITE.ID},{#LINK.ID}]',
    'cato.wan.loss.rx.pct[{#SITE.ID},{#LINK.ID}]',
    'cato.wan.loss.tx.pct[{#SITE.ID},{#LINK.ID}]',
    'cato.wan.loss.max.pct[{#SITE.ID},{#LINK.ID}]',
    'cato.wan.jitter.rx.ms[{#SITE.ID},{#LINK.ID}]',
    'cato.wan.jitter.tx.ms[{#SITE.ID},{#LINK.ID}]',
    'cato.wan.jitter.max.ms[{#SITE.ID},{#LINK.ID}]',
    'cato.wan.rtt.ms[{#SITE.ID},{#LINK.ID}]',
    'cato.wan.lastmile.loss.pct[{#SITE.ID},{#LINK.ID}]',
    'cato.wan.lastmile.latency.ms[{#SITE.ID},{#LINK.ID}]',
    'cato.wan.discard.rx.pps[{#SITE.ID},{#LINK.ID}]',
    'cato.wan.discard.tx.pps[{#SITE.ID},{#LINK.ID}]',
    'cato.wan.rx.util.pct[{#SITE.ID},{#LINK.ID}]',
    'cato.wan.tx.util.pct[{#SITE.ID},{#LINK.ID}]',
}
SLA_PREFIXES = {
    'cato.wan.rx.bps[': 'RX bandwidth',
    'cato.wan.tx.bps[': 'TX bandwidth',
    'cato.wan.loss.rx.pct[': 'RX loss',
    'cato.wan.loss.tx.pct[': 'TX loss',
    'cato.wan.loss.max.pct[': 'overlay loss',
    'cato.wan.jitter.rx.ms[': 'RX jitter',
    'cato.wan.jitter.tx.ms[': 'TX jitter',
    'cato.wan.rtt.ms[': 'RTT',
}
COLLECTOR_COUNTER_KEYS = {
    'cato.api.snapshot.error_count',
    'cato.api.metrics.error_count',
    'cato.api.snapshot.schema_violation_count',
    'cato.api.metrics.schema_violation_count',
    'zabbix[host,,items_unsupported]',
}
SNAPSHOT_FRESH_SECONDS = 5 * 60
METRICS_FRESH_SECONDS = 15 * 60
SIM_EXPECTED_CENSUS = {'sites': 11, 'sockets': 21, 'wan_rows': 33, 'sla_rows': 17}

TEMPLATE_MACROS = {
    '{$CATO.SITE.CONN_TYPE.MATCHES}': DEFAULT_CONN_TYPE,
    '{$CATO.SITES.EXPECTED}': '11',
    '{$CATO.SOCKETS.EXPECTED}': '21',
    '{$CATO.WAN.EXPECTED}': '33',
    '{$CATO.SLA.EXPECTED}': '17',
    '{$CATO.LOSS.WARN}': '2',
    '{$CATO.LASTMILE.LOSS.WARN}': '2',
    '{$CATO.RTT.WARN}': '101',
    '{$CATO.HA.READINESS.OK}': 'ready',
    '{$CATO.HA.VERSION.OK}': 'ok',
}


def default_account_id() -> str:
    return (os.environ.get(CATO_ACCOUNT_ID_ENV) or DEFAULT_ACCOUNT_ID).strip() or DEFAULT_ACCOUNT_ID


def collector_host(account_id: str | None = None) -> str:
    override = (os.environ.get(CATO_HOST_ENV) or '').strip()
    if override:
        return override
    return f'cato-account-{account_id or default_account_id()}'


def collector_visible_name(account_id: str | None = None) -> str:
    return f'Cato Account {account_id or default_account_id()}'


def sim_host(account_id: str | None = None) -> str:
    return f'cato-sim-account-{account_id or default_account_id()}'


def host_macros(account_id: str | None = None) -> dict[str, tuple[str, int]]:
    return {
        '{$CATO.API.URL}': (CATO_API_URL, TEXT),
        '{$CATO.ACCOUNT.ID}': (account_id or default_account_id(), TEXT),
    }


def graphql_posts(query: str, account_id_macro: str = '{$CATO.ACCOUNT.ID}') -> str:
    return json.dumps(
        {'query': query, 'variables': {'accountID': account_id_macro}},
        separators=(',', ':'),
    )


def load_lld_js(key: str) -> str:
    path = LLD_JS[key]
    return path.read_text(encoding='utf-8').rstrip('\n') + '\n'


def substitute_conn_type(js: str, pattern: str = DEFAULT_CONN_TYPE) -> str:
    return js.replace('{$CATO.SITE.CONN_TYPE.MATCHES}', pattern)


def run_lld_js(js: str, payload: str, *, conn_type: str = DEFAULT_CONN_TYPE) -> Any:
    """Execute a Cato LLD script with Node. ``payload`` is the HTTP body string."""
    import shutil
    import subprocess
    import tempfile

    node = shutil.which('node') or '/exec-daemon/node'
    source = substitute_conn_type(js, conn_type)
    wrapper = (
        'const fs = require("fs");\n'
        'const value = fs.readFileSync(0, "utf8");\n'
        'function __cato_lld(value) {\n'
        f'{source}'
        '}\n'
        'process.stdout.write(String(__cato_lld(value)));\n'
    )
    with tempfile.NamedTemporaryFile('w', suffix='.js', encoding='utf-8', delete=False) as handle:
        handle.write(wrapper)
        script_path = handle.name
    try:
        proc = subprocess.run(
            [node, script_path],
            input=payload,
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        Path(script_path).unlink(missing_ok=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or 'node failed').strip()
        raise RuntimeError(err)
    return json.loads(proc.stdout)


def _schema_violation_count(body: dict[str, Any]) -> int:
    count = 0
    for error in body.get('errors') or []:
        extensions = (error or {}).get('extensions') or {}
        violations = extensions.get('schemaViolations')
        if isinstance(violations, list):
            count += len(violations)
    return count


def graphql_request(
    url: str,
    api_key: str,
    query: str,
    account_id: str,
    *,
    timeout: int = 30,
) -> tuple[dict[str, Any] | None, str | None]:
    """POST one Cato GraphQL query. Never includes the API key in the error text."""
    payload = json.dumps(
        {'query': query, 'variables': {'accountID': account_id}},
        separators=(',', ':'),
    ).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'x-api-key': api_key,
        },
        method='POST',
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            status = getattr(resp, 'status', None) or resp.getcode()
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        return None, f'HTTP {exc.code} from Cato GraphQL'
    except urllib.error.URLError as exc:
        reason = getattr(exc, 'reason', exc)
        return None, f'Cato GraphQL transport failed: {type(reason).__name__}'
    except TimeoutError:
        return None, 'Cato GraphQL timed out'
    if int(status) != 200:
        return None, f'HTTP {status} from Cato GraphQL'
    try:
        body = json.loads(raw.decode())
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, 'Cato GraphQL returned non-JSON'
    if not isinstance(body, dict):
        return None, 'Cato GraphQL JSON root is not an object'
    return body, None


def preflight_cato_graphql(
    *,
    api_key: str | None = None,
    account_id: str | None = None,
    url: str = CATO_API_URL,
) -> list[str]:
    """Fail-closed GraphQL gate used by --apply-cato / configure_cato_zabbix --apply."""
    errors: list[str] = []
    key = (api_key if api_key is not None else os.environ.get(CATO_API_KEY_ENV) or '').strip()
    if not key:
        errors.append(f'{CATO_API_KEY_ENV} is missing; Cato GraphQL preflight cannot authenticate')
        return errors
    acct = (account_id or default_account_id()).strip()
    if not acct:
        errors.append(f'{CATO_ACCOUNT_ID_ENV} is empty')
        return errors

    snapshot, snap_err = graphql_request(url, key, SNAPSHOT_QUERY, acct)
    if snap_err:
        errors.append(f'accountSnapshot: {snap_err}')
    else:
        assert snapshot is not None
        gql_errors = snapshot.get('errors') or []
        if gql_errors:
            messages = [
                str((err or {}).get('message') or 'GraphQL error')
                for err in gql_errors
            ]
            errors.append('accountSnapshot GraphQL errors: ' + '; '.join(messages[:5]))
        violations = _schema_violation_count(snapshot)
        if violations:
            errors.append(f'accountSnapshot schemaViolations={violations}')
        data = (snapshot.get('data') or {}).get('accountSnapshot')
        if not data:
            errors.append('accountSnapshot returned no data.accountSnapshot')
        else:
            census = snapshot_census(snapshot)
            if census['sites'] <= 0:
                errors.append('accountSnapshot has no SOCKET_ sites')

    metrics, met_err = graphql_request(url, key, METRICS_QUERY, acct)
    if met_err:
        errors.append(f'accountMetrics: {met_err}')
    else:
        assert metrics is not None
        gql_errors = metrics.get('errors') or []
        if gql_errors:
            messages = [
                str((err or {}).get('message') or 'GraphQL error')
                for err in gql_errors
            ]
            errors.append('accountMetrics GraphQL errors: ' + '; '.join(messages[:5]))
        violations = _schema_violation_count(metrics)
        if violations:
            errors.append(f'accountMetrics schemaViolations={violations}')
        data = (metrics.get('data') or {}).get('accountMetrics')
        if not data:
            errors.append('accountMetrics returned no data.accountMetrics')
        else:
            sla_rows = metrics_sla_census(metrics)
            if sla_rows <= 0:
                errors.append('accountMetrics has no SOCKET_ SLA rows')
    return errors


def _socket_conn_type(info: dict[str, Any] | None) -> bool:
    return str((info or {}).get('connType') or '').startswith('SOCKET_')


def snapshot_census(root: dict[str, Any] | str) -> dict[str, int]:
    if isinstance(root, str):
        root = json.loads(root)
    snapshot = ((root.get('data') or {}).get('accountSnapshot') or {})
    sites = sockets = wan_rows = 0
    for site in snapshot.get('sites') or []:
        info = site.get('info') or {}
        if not _socket_conn_type(info):
            continue
        sites += 1
        for device in site.get('devices') or []:
            socket = device.get('socketInfo') or {}
            if not str(socket.get('serial') or '').strip():
                continue
            sockets += 1
            wan_rows += sum(
                1
                for interface in device.get('interfaces') or []
                if (interface.get('info') or {}).get('id') is not None
            )
    return {'sites': sites, 'sockets': sockets, 'wan_rows': wan_rows}


def metrics_sla_census(root: dict[str, Any] | str) -> int:
    if isinstance(root, str):
        root = json.loads(root)
    metrics = ((root.get('data') or {}).get('accountMetrics') or {})
    pairs: set[tuple[str, str]] = set()
    for site in metrics.get('sites') or []:
        info = site.get('info') or {}
        site_id = site.get('id')
        if site_id is None or not _socket_conn_type(info):
            continue
        for interface in site.get('interfaces') or []:
            link_id = (interface.get('interfaceInfo') or {}).get('id')
            if link_id is not None:
                pairs.add((str(site_id), str(link_id)))
    return len(pairs)


def normalize_socket_serial(value: object) -> str:
    """Use a canonical case because Cato serial casing is not stable."""
    return str(value or '').strip().upper()


def snapshot_socket_serials(root: dict[str, Any] | str) -> set[str]:
    if isinstance(root, str):
        root = json.loads(root)
    snapshot = ((root.get('data') or {}).get('accountSnapshot') or {})
    serials: set[str] = set()
    for site in snapshot.get('sites') or []:
        info = site.get('info') or {}
        if not _socket_conn_type(info):
            continue
        for device in site.get('devices') or []:
            serial = normalize_socket_serial(
                (device.get('socketInfo') or {}).get('serial')
            )
            if serial:
                serials.add(serial)
    return serials
