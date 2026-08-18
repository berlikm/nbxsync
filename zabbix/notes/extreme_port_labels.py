"""
Extreme Port Labels — NetBox Custom Script
==========================================

Generate / verify the on-box port label ``CLASS[-SPEED]-ID`` (SNMP ``ifAlias``)
on Extreme switches, from NetBox cabling topology.

Two modes:

1. **compliance** (default) — compute the expected label from NetBox, read the
   live label off the switch, report the diff. Nothing is pushed.
2. **remediate** — same computation, but push only the non-compliant ports.
   Double-gated: ``mode=remediate`` **and** NetBox's *Commit changes* box.

Why it matters: Zabbix LLD filters on ``{$NET.IF.IFALIAS.MATCHES}``. A wrong or
truncated label silently drops a port out of (or into) monitoring.

Grammar / length rules: ``zabbix/reference/port-identity-foundation.md``.
Vendor CLI citations + the ID convention: ``README-extreme-port-labels.md``.

Transport is borrowed from ``extreme_cli_runner.py`` (same directory) — this
script does not open its own SSH stack.

Environment variables (identical to the CLI runner):
  EXTREME_VENV_PATH                                   — venv holding netmiko
  NBX_NAPALM_EXOS_USERNAME / NBX_NAPALM_EXOS_PASSWORD — EXOS credentials
  NBX_NAPALM_VOSS_USERNAME / NBX_NAPALM_VOSS_PASSWORD — VOSS credentials
"""

from __future__ import annotations

import importlib.util
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, replace

# ---------------------------------------------------------------------------
# Inject the netmiko venv into sys.path (same convention as the CLI runner)
# ---------------------------------------------------------------------------
_VENV_PATH = os.getenv("EXTREME_VENV_PATH", "")
if _VENV_PATH:
    import glob as _glob
    _sp = _glob.glob(os.path.join(_VENV_PATH, "lib", "python*", "site-packages"))
    if _sp and _sp[0] not in sys.path:
        sys.path.insert(0, _sp[0])

logger = logging.getLogger("extreme_port_labels")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)-7s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(_h)


# ===========================================================================
# SECTION 1 — Pure grammar helpers
# ===========================================================================
#
# Nothing below this banner imports NetBox, so the whole section is unit
# testable outside a NetBox worker (see ../tests/test_extreme_port_labels.py).

#: EXOS ``display-string`` truncates silently past 20. VOSS ``name`` allows 64,
#: but the fleet uses the lowest common denominator so one label fits both.
MAX_LABEL_LEN = 20

#: Union of the two EXOS User Guide 32.7.1 character lists, plus ``?``.
FORBIDDEN_CHARS = frozenset(': "<>&?')

CLASSES = ("USW", "US", "UP", "MON", "UW", "TMON", "X", "N")

#: Classes that never carry a SPEED token.
NO_SPEED_CLASSES = frozenset({"X", "N", "UW", "TMON"})

SPEED_TOKEN_MBPS = {
    "100M": 100,
    "1G": 1000,
    "2G5": 2500,
    "5G": 5000,
    "10G": 10000,
    "25G": 25000,
    "40G": 40000,
    "100G": 100000,
    "400G": 400000,
}
MBPS_SPEED_TOKEN = {v: k for k, v in SPEED_TOKEN_MBPS.items()}

CLASS_DEFAULT_MBPS = {"USW": 10000, "US": 10000, "UP": 1000, "MON": 1000}

#: Widest SPEED token plus its separator. Every label is sized as if a token
#: were present, even when the link runs at the class default today — so a port
#: that is later re-optic'd (1G -> 40G) never overflows and never needs a
#: fleet-wide re-label.
SPEED_SLOT_LEN = max(len(token) for token in SPEED_TOKEN_MBPS) + 1


class LabelTooLong(ValueError):
    """Raised instead of emitting a label EXOS would silently truncate."""

    def __init__(self, label: str, suggestion: str):
        super().__init__(
            f"label {label!r} is {len(label)} chars (max {MAX_LABEL_LEN}); "
            f"shortest form tried was {suggestion!r}"
        )
        self.label = label
        self.suggestion = suggestion


@dataclass(frozen=True)
class ParsedLabel:
    cls: str
    speed_token: str | None
    ident: str

    @property
    def expected_mbps(self) -> int | None:
        if self.speed_token:
            return SPEED_TOKEN_MBPS[self.speed_token]
        return CLASS_DEFAULT_MBPS.get(self.cls)


def parse_label(raw: str) -> ParsedLabel | None:
    """Parse ``CLASS[-SPEED]-ID``. Returns ``None`` for unparseable legacy text."""
    if not raw:
        return None
    parts = raw.strip().upper().split("-")
    cls = parts[0]
    if cls not in CLASSES:
        return None
    rest = parts[1:]
    speed = None
    if rest and cls not in NO_SPEED_CLASSES and rest[0] in SPEED_TOKEN_MBPS:
        speed = rest[0]
        rest = rest[1:]
    return ParsedLabel(cls=cls, speed_token=speed, ident="-".join(rest))


def validate_label(raw: str) -> list[str]:
    """Return a list of machine-readable problems with ``raw`` (empty = clean)."""
    issues: list[str] = []
    if not raw:
        return ["empty"]
    if len(raw) > MAX_LABEL_LEN:
        issues.append("too_long")
    bad = sorted(FORBIDDEN_CHARS & set(raw))
    if bad:
        issues.append("forbidden_chars:" + "".join(bad))
    if not raw[0].isalnum():
        issues.append("first_char_not_alnum")
    if raw != raw.upper():
        issues.append("not_uppercase")
    parsed = parse_label(raw)
    if parsed is None:
        issues.append("unparseable")
        return issues
    if parsed.speed_token and parsed.cls in NO_SPEED_CLASSES:
        issues.append("speed_on_neutral_class")
    if (parsed.speed_token
            and SPEED_TOKEN_MBPS[parsed.speed_token] == CLASS_DEFAULT_MBPS.get(parsed.cls)):
        # One fact, one encoding — a token equal to the class default is noise.
        issues.append("redundant_speed")
    return issues


def build_label(cls: str, link_mbps: int | None, ident: str) -> str:
    """Assemble ``CLASS[-SPEED]-ID``, omitting SPEED at the class default speed."""
    token = None
    if cls not in NO_SPEED_CLASSES and link_mbps:
        if link_mbps != CLASS_DEFAULT_MBPS.get(cls):
            token = MBPS_SPEED_TOKEN.get(link_mbps)
    pieces = [cls]
    if token:
        pieces.append(token)
    if ident:
        pieces.append(ident)
    return "-".join(pieces)


# ---- ID abbreviator -------------------------------------------------------
#
# Validated against real device names in this estate:
#   CH-STA-L50-B01-ACCE01   CH-STA-L50-L01-CORE01   CH-NKN-G08-L02-CORE01-1
#   CH-STA-L50-B01-ACPO03   CH-STA-L42-CORE01-2     CH-STA-P-BACK02
# The 2-letter compression mirrors the convention already on the boxes
# (``L26-GFL-Di02:29``, ``NNI:L26-Co02:1/24``).

ROLE_CODE_SHORT = {
    "CORE": "CO",
    "DIST": "DI",
    "ACCE": "AC",
    "ACPO": "AP",
    "MGMT": "MG",
    "FWGW": "FW",
    "FWZONE": "FW",
    "CATO": "CT",
    "BACK": "BK",
    "ESX": "ES",
    "VM": "VM",
    "SAN": "SN",
    "SNAS": "NS",
    "STOD": "SD",
}

#: The NetBox *role* is the authority for the code wherever it is at least as
#: specific as the hostname — hostname hygiene varies, roles do not. Server and
#: Storage are deliberately absent: their names (ESX/BACK, SAN/SNAS/STOD) carry
#: a distinction the role flattens away.
ROLE_TO_CODE = {
    "switch core": "CO",
    "switch dist": "DI",
    "switch access": "AC",
    "switch mgmt": "MG",
    "access point": "AP",
    "firewall": "FW",
    "cohesity": "CY",
    "sd wan socket": "WA",
    "network device": "ND",
    "messpc": "PC",
}


def role_code(far_role: str | None) -> str:
    """Two-letter code for a NetBox device role, '' when the name knows better."""
    return ROLE_TO_CODE.get((far_role or "").strip().lower(), "")

_TAIL_RE = re.compile(r"^(?P<code>[A-Z]+)(?P<num>\d*)$")


@dataclass(frozen=True)
class DeviceNameParts:
    scope: str      # location token (same site) or far-site tail (cross site)
    code: str       # ACCE / CORE / ESX / ...
    num: str        # 01 / 42 / ''
    stack: str      # stack member suffix ('1', '2') or ''


def split_device_name(name: str, site_slug: str, local_site_slug: str) -> DeviceNameParts:
    """Break a NetBox device name into the pieces the abbreviator needs.

    ``<SITESLUG>-[<LOC>-]<CODE><NN>[-<STACK>]`` is the house convention; names
    that do not follow it degrade gracefully to their trailing segment.
    """
    clean = (name or "").upper().split(".")[0]      # drop any DNS suffix
    site = (site_slug or "").upper()
    local = (local_site_slug or "").upper()

    rest = clean[len(site) + 1:] if site and clean.startswith(site + "-") else clean
    segments = [s for s in rest.split("-") if s]
    if not segments:
        return DeviceNameParts("", clean, "", "")

    stack = ""
    if len(segments) > 1 and segments[-1].isdigit() and len(segments[-1]) <= 2:
        stack = segments.pop()

    tail = segments.pop()
    match = _TAIL_RE.match(tail)
    code, num = (match.group("code"), match.group("num")) if match else (tail, "")

    if site and site == local:
        scope = segments[-1] if segments else ""
    else:
        # Cross-site: the far site identifies the box better than its floor.
        scope = (site.split("-")[-1] if site else (segments[-1] if segments else ""))
    return DeviceNameParts(scope=scope, code=code, num=num, stack=stack)


def normalize_port_token(port_name: str) -> str:
    """``1:24`` / ``1/24`` -> ``1.24``; strip anything the grammar forbids."""
    token = (port_name or "").upper().replace(":", ".").replace("/", ".")
    return "".join(ch for ch in token if ch.isalnum() or ch in "._")


def _port_suffix_candidates(port_name: str) -> list[str]:
    """Renderings of the far-end port, most detailed first.

    Vendor NIC names (``ct1.eth0``, ``CTE0.A.P2``) shed trailing segments so a
    tight budget costs detail rather than the whole port. Numeric switch ports
    are never compacted — ``2.14`` shortened to ``2`` would name the slot only.
    """
    token = normalize_port_token(port_name)
    if not token:
        return [""]
    if token.startswith("PORT") and token[4:5].isdigit():
        token = token[4:]
    if token[0].isdigit():
        return [f"_P{token}"]

    segments = token.split(".")
    forms = [token, token.replace(".", "")]
    forms += ["".join(segments[:n]) for n in range(len(segments) - 1, 0, -1)]

    out: list[str] = []
    seen: set[str] = set()
    for form in forms:
        if form and form not in seen:
            seen.add(form)
            out.append(f"_{form}")
    return out


def _port_suffix(port_name: str) -> str:
    """``_P`` is the one and only port marker: ``23`` and Fortinet ``port23``
    both render as ``_P23``. Non-numeric ports keep their own token."""
    return _port_suffix_candidates(port_name)[0]

def id_candidates(parts: DeviceNameParts, port_name: str = "") -> list[str]:
    """Deterministic shortest-first-that-fits ladder for the ID field.

    The role code is *always* the two-letter form -- spelling out ``ACCE`` buys
    no clarity over ``AC`` but costs two characters that the port number needs.
    Order is deliberate: drop the scope before the port, because two parallel
    links to the same neighbour are only told apart by the port.
    """
    short_code = ROLE_CODE_SHORT.get(parts.code, parts.code[:2])
    short = f"{short_code}{parts.num}" + (f"-{parts.stack}" if parts.stack else "")
    scope = f"{parts.scope}-" if parts.scope else ""

    ladder = []
    for sfx in _port_suffix_candidates(port_name):
        ladder.append(f"{scope}{short}{sfx}")
        ladder.append(f"{short}{sfx}")
    ladder += [f"{scope}{short}", short]
    seen: set[str] = set()
    return [c for c in ladder if not (c in seen or seen.add(c))]


def build_label_for_far_end(
    cls: str,
    link_mbps: int | None,
    parts: DeviceNameParts,
    port_name: str = "",
) -> str:
    """Pick the longest ID form that fits.

    Reserve the SPEED slot only when a token will actually be emitted.
    Reserving 5 characters on every default-speed USW/US/UP/MON port was
    dropping building/site scope, so two DIST01 uplinks on port 29 became
    the same label.
    """
    token_needed = (
        cls not in NO_SPEED_CLASSES
        and bool(link_mbps)
        and link_mbps != CLASS_DEFAULT_MBPS.get(cls)
        and link_mbps in MBPS_SPEED_TOKEN
    )
    reserve = SPEED_SLOT_LEN if token_needed else 0
    budget = MAX_LABEL_LEN - reserve
    tried = ""
    for ident in id_candidates(parts, port_name):
        bare = build_label(cls, None, ident)
        label = build_label(cls, link_mbps, ident)
        tried = label
        if len(bare) <= budget and not (FORBIDDEN_CHARS & set(label)):
            return label
    raise LabelTooLong(build_label(cls, link_mbps, id_candidates(parts, port_name)[0]), tried)


# ---- Interface type -> speed ---------------------------------------------

_IFTYPE_SPEED_RE = re.compile(r"^(\d+(?:\.\d+)?)(g?)base", re.IGNORECASE)


def iftype_to_mbps(iface_type: str | None) -> int | None:
    """NetBox interface type slug -> Mbps (``10gbase-x-sfpp`` -> 10000)."""
    if not iface_type:
        return None
    match = _IFTYPE_SPEED_RE.match(iface_type)
    if not match:
        return None
    value = float(match.group(1))
    return int(value * (1000 if match.group(2).lower() == "g" else 1))


# ---- Far-end role -> CLASS -----------------------------------------------

#: Far-end roles that are network infrastructure rather than an endpoint. A
#: firewall link carries the same operational weight as a switch uplink, so it
#: gets USW (link/flap/errors + speed expectation) rather than US/MON.
INFRA_ROLE_TOKENS = ("switch", "firewall")

#: Far-end roles whose data NICs are production data path -> US regardless of
#: negotiated speed. Their out-of-band management ports are still MON.
DATA_ENDPOINT_ROLE_TOKENS = ("server", "storage", "cohesity")

#: Fallback only. The authoritative out-of-band signal is the far device's
#: NetBox ``oob_ip`` being assigned to that interface; these name tokens cover
#: hosts where nobody has set it yet.
BMC_PORT_TOKENS = ("idrac", "ilo", "bmc", "ipmi", "cimc", "imm", "mgmt", "oob")


def is_bmc_port(far_port: str | None) -> bool:
    """True for an out-of-band management interface on the far end."""
    name = (far_port or "").lower()
    return any(token in name for token in BMC_PORT_TOKENS)


def classify(far_role: str, link_mbps: int | None, far_port: str = "",
             far_is_mgmt: bool = False) -> str:
    """CLASS from the far-end role, its interface purpose, and the link speed."""
    role = (far_role or "").strip().lower()
    if any(token in role for token in INFRA_ROLE_TOKENS):
        return "USW"
    if "access point" in role:
        return "UP"
    if "sd wan" in role or "sd-wan" in role:
        return "UW"
    if any(token in role for token in DATA_ENDPOINT_ROLE_TOKENS):
        # Lights-out and controller management is MON; data NICs are production.
        return "MON" if (far_is_mgmt or is_bmc_port(far_port)) else "US"
    return "US" if (link_mbps or 0) >= 10000 else "MON"


# ===========================================================================
# SECTION 2 — Live-device label readers / writers (transport from the runner)
# ===========================================================================

#: EXOS emits the configured label as a config line; ``show ports configuration``
#: truncates it to 8 chars + ``>`` and is useless for compliance.
_RE_EXOS_DISPLAY = re.compile(
    r"^configure\s+ports?\s+(?P<port>\S+)\s+display-string\s+(?P<value>.+?)\s*$",
    re.MULTILINE,
)
_RE_EXOS_DESCRIPTION = re.compile(
    r"^configure\s+ports?\s+(?P<port>\S+)\s+description-string\s+(?P<value>.+?)\s*$",
    re.MULTILINE,
)
_RE_VOSS_IFACE = re.compile(r"^interface\s+GigabitEthernet\s+(?P<port>\S+)\s*$", re.IGNORECASE)
_RE_VOSS_NAME = re.compile(r'^\s*name\s+"?(?P<value>[^"\r\n]*)"?\s*$', re.IGNORECASE)


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def expand_exos_port_list(spec: str) -> list[str]:
    """Expand ``1:1-1:4`` / ``1:1,1:3`` / ``1-4`` to individual port names."""
    spec = (spec or "").strip()
    if not spec:
        return []
    out: list[str] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" not in part:
            out.append(part)
            continue
        start, end = part.split("-", 1)
        expanded = _expand_exos_range(start.strip(), end.strip())
        out.extend(expanded if expanded else [part])
    return out


def _expand_exos_range(start: str, end: str) -> list[str] | None:
    sep = ":" if ":" in start else ("/" if "/" in start else None)
    if sep:
        s_slot, s_port = start.split(sep, 1)
        if sep not in end:
            # ``1:1-4`` — same slot
            e_slot, e_port = s_slot, end
        else:
            e_slot, e_port = end.split(sep, 1)
        if s_slot != e_slot:
            return None
        try:
            a, b = int(s_port), int(e_port)
        except ValueError:
            return None
        if a > b or b - a > 128:
            return None
        return [f"{s_slot}{sep}{n}" for n in range(a, b + 1)]
    try:
        a, b = int(start), int(end)
    except ValueError:
        return None
    if a > b or b - a > 128:
        return None
    return [str(n) for n in range(a, b + 1)]


def port_key_aliases(ifname: str) -> set[str]:
    """NetBox ``1:24`` vs EXOS ``1:24`` vs VOSS ``1/24`` vs ``1.24``."""
    raw = (ifname or "").strip()
    if not raw:
        return set()
    upper = raw.upper()
    if upper.startswith("PORT") and len(raw) > 4 and raw[4].isdigit():
        raw = raw[4:]
    keys = {raw, raw.replace(":", "/"), raw.replace(":", "."),
            raw.replace("/", ":"), raw.replace("/", "."),
            raw.replace(".", ":"), raw.replace(".", "/")}
    return {k for k in keys if k}


def lookup_live_label(labels: dict[str, str], ifname: str) -> str:
    """Find a live label despite ``:`` vs ``/`` vs ``.`` in the port name."""
    if not labels:
        return ""
    if ifname in labels:
        return labels[ifname]
    wanted = port_key_aliases(ifname)
    for key, value in labels.items():
        if key in wanted or (port_key_aliases(key) & wanted):
            return value
    return ""


def parse_exos_labels(config_text: str) -> tuple[dict[str, str], dict[str, str]]:
    """Extract ``{port: display-string}`` and ``{port: description-string}``.

    EXOS may emit a port *list* (``1:1-1:4`` or ``1:1,1:3``). Expand those so
    lookup by a single NetBox ifName still hits.
    """
    display: dict[str, str] = {}
    for m in _RE_EXOS_DISPLAY.finditer(config_text or ""):
        value = _unquote(m.group("value"))
        for port in expand_exos_port_list(m.group("port")):
            display[port] = value
    description: dict[str, str] = {}
    for m in _RE_EXOS_DESCRIPTION.finditer(config_text or ""):
        value = _unquote(m.group("value"))
        for port in expand_exos_port_list(m.group("port")):
            description[port] = value
    return display, description


def parse_voss_labels(config_text: str) -> dict[str, str]:
    """Extract ``{port: name}`` from the PORT CONFIGURATION blocks."""
    labels: dict[str, str] = {}
    current: str | None = None
    for line in (config_text or "").splitlines():
        iface = _RE_VOSS_IFACE.match(line.strip())
        if iface:
            current = iface.group("port")
            continue
        if line.strip().lower() == "exit":
            current = None
            continue
        if current:
            name = _RE_VOSS_NAME.match(line)
            if name:
                labels[current] = name.group("value").strip()
    return labels


def exos_apply_commands(port: str, label: str, clear_description: bool) -> list[str]:
    """EXOS: set ``display-string``; optionally clear the hijacking description.

    ``configure ports <port_list> display-string <string>`` — form confirmed on
    live switches (``show configuration`` emits exactly this line).
    ``unconfigure port <port_list> description-string`` — EXOS UG 32.7.1,
    "Configuring Extended Port Description".
    """
    cmds = [f"configure ports {port} display-string {label}"]
    if clear_description:
        cmds.append(f"unconfigure port {port} description-string")
    return cmds


def voss_apply_commands(port: str, label: str) -> list[str]:
    """VOSS/Fabric Engine: ``name`` under the GigabitEthernet interface."""
    return [f"interface GigabitEthernet {port}", f'name "{label}"', "exit"]


# ---- Thin integration with extreme_cli_runner.py --------------------------

_RUNNER = None
_RUNNER_ERROR: str | None = None


def _load_cli_runner():
    """Load the sibling ``extreme_cli_runner.py`` by path.

    NetBox loads every script file as an isolated module, so a plain
    ``import extreme_cli_runner`` is not reliable; loading by file location is.
    We reuse its SSH session helpers and credential resolution rather than
    standing up a second transport stack.
    """
    global _RUNNER, _RUNNER_ERROR
    if _RUNNER is not None or _RUNNER_ERROR is not None:
        return _RUNNER
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "extreme_cli_runner.py")
    try:
        spec = importlib.util.spec_from_file_location("_extreme_cli_runner_shared", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"no loader for {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _RUNNER = module
    except Exception as exc:  # noqa: BLE001 — never break script discovery
        _RUNNER_ERROR = str(exc)
        logger.warning("could not load extreme_cli_runner.py (%s)", exc)
    return _RUNNER


def _credentials(kind: str) -> tuple[str, str, str]:
    """(netmiko device_type, username, password) for ``exos`` / ``voss``."""
    runner = _load_cli_runner()
    if runner is not None:
        if kind == "voss":
            return "extreme_vsp", runner._VOSS_USERNAME, runner._VOSS_PASSWORD
        return "extreme_exos", runner._EXOS_USERNAME, runner._EXOS_PASSWORD
    # Runner unavailable — same env vars, so behaviour is identical.
    exos_user = os.getenv("NBX_NAPALM_EXOS_USERNAME", os.getenv("EXTREME_USERNAME", "admin"))
    exos_pass = os.getenv("NBX_NAPALM_EXOS_PASSWORD", os.getenv("EXTREME_PASSWORD", ""))
    if kind == "voss":
        return ("extreme_vsp",
                os.getenv("NBX_NAPALM_VOSS_USERNAME", exos_user),
                os.getenv("NBX_NAPALM_VOSS_PASSWORD", exos_pass))
    return "extreme_exos", exos_user, exos_pass


def _connect(device_name: str, device_ip: str, kind: str):
    netmiko_type, username, password = _credentials(kind)
    runner = _load_cli_runner()
    if runner is None:
        raise RuntimeError(
            f"extreme_cli_runner.py could not be loaded ({_RUNNER_ERROR}) — "
            f"it provides the SSH transport for this script."
        )
    return runner._connect_netmiko(device_name, device_ip, netmiko_type,
                                   username, password)


def _send(nc, cmd: str, read_timeout: int = 60) -> str:
    """Send one command, auto-confirming a y/N prompt (runner behaviour)."""
    runner = _load_cli_runner()
    if runner is not None:
        return runner._send_exos(nc, cmd, read_timeout=read_timeout)
    return nc.send_command_timing(cmd, read_timeout=read_timeout)


def _fetch_live_labels(nc, kind: str) -> tuple[dict[str, str], dict[str, str]]:
    """Read the live labels off an open session. Returns (labels, descriptions)."""
    if kind == "voss":
        text = _send(nc, "show running-config", read_timeout=180)
        return parse_voss_labels(text), {}
    text = _send(nc, "show configuration vlan", read_timeout=120)
    display, description = parse_exos_labels(text)
    if not display and not description:
        # Older/other EXOS builds may file the port stanza elsewhere.
        text = _send(nc, "show configuration", read_timeout=240)
        display, description = parse_exos_labels(text)
    return display, description


# ===========================================================================
# SECTION 3 — NetBox model layer
# ===========================================================================

try:
    from dcim.choices import DeviceStatusChoices
    from dcim.models import Device, DeviceRole, Interface, Site, SiteGroup
    from extras.models import Tag
    from extras.scripts import (
        BooleanVar,
        ChoiceVar,
        IntegerVar,
        MultiObjectVar,
        ObjectVar,
        Script,
        TextVar,
    )
    _NETBOX = True
except Exception:  # noqa: BLE001 — allows the helpers above to be imported bare
    _NETBOX = False
    Script = object  # type: ignore[assignment,misc]


#: Interface types that are never a physical, labellable port.
_NON_PHYSICAL_TYPES = frozenset({"virtual", "lag", "bridge", "other"})
_NON_PHYSICAL_NAME_RE = re.compile(r"^(mgmt|clip|vlan|mlt\.|v\d{3,})", re.IGNORECASE)


@dataclass
class PortPlan:
    device: str
    site: str
    kind: str                # 'exos' | 'voss'
    ifname: str
    expected: str = ""
    live: str = ""
    description_string: str = ""
    status: str = "pending"
    detail: str = ""
    commands: list[str] = field(default_factory=list)

    @property
    def blocking(self) -> bool:
        return self.status in {"diff", "missing", "too_long", "forbidden",
                               "description_string_set"}


def _platform_kind(platform_name: str | None) -> str | None:
    name = (platform_name or "").upper()
    if "EXOS" in name or "SWITCH ENGINE" in name:
        return "exos"
    if "VOSS" in name or "FABRIC ENGINE" in name:
        return "voss"
    return None


def _ip_from(addr) -> str | None:
    if addr is None:
        return None
    raw = str(getattr(addr, "address", addr) or "")
    host = raw.split("/")[0].strip()
    return host or None


def _device_ssh_ip(device) -> str | None:
    """Prefer out-of-band IP; fall back to primary. Never invent an address."""
    return _ip_from(getattr(device, "oob_ip", None)) or _ip_from(getattr(device, "primary_ip", None))


def _is_physical(iface) -> bool:
    if iface.type in _NON_PHYSICAL_TYPES:
        return False
    if _NON_PHYSICAL_NAME_RE.match(iface.name or ""):
        return False
    return True


def _far_endpoint(iface):
    """Far-end Interface or CircuitTermination on a *complete* cable path.

    ``connected_endpoints`` already walks patch-panel Front/Rear ports. A cable
    that dies on a rear port is incomplete — we return None (no derivable ID).
    A circuit handoff is a CircuitTermination, not an Interface.
    """
    try:
        endpoints = iface.connected_endpoints or []
    except Exception:  # noqa: BLE001 — unterminated/split cable paths raise
        return None
    for endpoint in endpoints:
        if isinstance(endpoint, Interface):
            return endpoint
        if type(endpoint).__name__ == "CircuitTermination":
            return endpoint
    return None


def _is_management_interface(iface) -> bool:
    """True when the far end is a lights-out / controller management port.

    Do **not** treat "device has no primary_ip" as management — Pure/SAN/Cohesity
    often only have oob_ip in NetBox while the cable is a production data NIC.
    Those must stay ``US``, not ``MON``.
    """
    if getattr(iface, "mgmt_only", False):
        return True
    oob = getattr(getattr(iface, "device", None), "oob_ip", None)
    if oob is not None and getattr(oob, "assigned_object", None) == iface:
        return True
    return is_bmc_port(getattr(iface, "name", None))


def expected_label_for(iface, structural_tag_ids: set[int]) -> tuple[str, str]:
    """Compute the expected label for one interface.

    Returns ``(label, status)`` where status is ``ok`` (label derived),
    ``structural`` (tagged never-alert), ``no_cable`` (out of scope), or
    ``too_long``.
    """
    if structural_tag_ids and {t.pk for t in iface.tags.all()} & structural_tag_ids:
        return "X", "structural"

    far = _far_endpoint(iface)
    if far is None:
        return "", "no_cable"

    if type(far).__name__ == "CircuitTermination":
        circuit = getattr(far, "circuit", None)
        cid = str(getattr(circuit, "cid", None) or "CIRCUIT")
        provider = (
            getattr(getattr(circuit, "provider", None), "slug", None)
            or getattr(getattr(circuit, "provider", None), "name", None)
            or "ISP"
        )
        parts = split_device_name(str(provider), "", "")
        if not parts.code:
            parts = DeviceNameParts("", str(provider).upper()[:6], "", "")
        try:
            return build_label_for_far_end("UW", None, parts, cid), "ok"
        except LabelTooLong as exc:
            return exc.suggestion, "too_long"

    local_mbps = iftype_to_mbps(iface.type)
    far_mbps = iftype_to_mbps(getattr(far, "type", None))
    speeds = [s for s in (local_mbps, far_mbps) if s]
    link_mbps = min(speeds) if speeds else None

    far_device = far.device
    far_role = getattr(getattr(far_device, "role", None), "name", "") or ""
    cls = classify(far_role, link_mbps, far.name or "", _is_management_interface(far))

    parts = split_device_name(
        far_device.name or "",
        getattr(getattr(far_device, "site", None), "slug", "") or "",
        getattr(getattr(iface.device, "site", None), "slug", "") or "",
    )
    code = role_code(far_role)
    if code:
        parts = replace(parts, code=code)
    # An AP has a single uplink, so its far-end port number is pure noise.
    port_ref = "" if cls == "UP" else (far.name or "")

    try:
        return build_label_for_far_end(cls, link_mbps, parts, port_ref), "ok"
    except LabelTooLong as exc:
        return exc.suggestion, "too_long"


# ===========================================================================
# SECTION 4 — NetBox Script
# ===========================================================================

if _NETBOX:

    class ExtremePortLabels(Script):
        """Compliance-check (and optionally remediate) Extreme port labels."""

        class Meta(Script.Meta):
            name = "Extreme Port Labels (ifAlias compliance)"
            description = (
                "Compute the expected CLASS[-SPEED]-ID port label from NetBox "
                "cabling, read the live label off each switch (EXOS "
                "display-string / VOSS interface name), and report the diff. "
                "Cabled ports are evaluated; live labels without a NetBox cable "
                "are reported as orphan and never pushed. Compliance-only by "
                "default; remediation needs mode=remediate AND Commit changes."
            )
            commit_default = False
            scheduling_enabled = True
            job_timeout = 3600

            fieldsets = (
                ("Mode", ("mode", "clear_description_string", "canary")),
                ("Scope", ("site_group", "site", "role", "tag", "devices",
                           "platform_filter", "structural_tag")),
                ("Reporting", ("include_admin_down", "include_neutral",
                               "fail_on_diff")),
                ("Execution", ("save_config", "max_workers")),
            )

        # ---- Mode ----

        mode = ChoiceVar(
            choices=(
                ("compliance", "Compliance — read only, report diffs"),
                ("remediate", "Remediate — push non-compliant labels (needs Commit)"),
            ),
            default="compliance",
            description="Remediation additionally requires the Commit changes box.",
            label="Mode",
        )

        clear_description_string = BooleanVar(
            default=False,
            description=(
                "EXOS only. When a port has a description-string it hijacks "
                "ifAlias and the display-string is ignored. Tick to also run "
                "`unconfigure port <p> description-string`. Off by default — "
                "that field may hold human text."
            ),
            label="Also clear EXOS description-string",
        )

        canary = TextVar(
            required=False,
            description=(
                "Allowlist for remediation: `device-name::ifname` per line "
                "(e.g. `CH-STA-L50-L01-CORE01::1/17`). When set, only these "
                "ports are pushed. Strongly recommended for the first live run."
            ),
            label="Canary allowlist (device::ifname)",
        )

        # ---- Scope ----

        site_group = MultiObjectVar(model=SiteGroup, required=False,
                                    description="Filter by site group")
        site = MultiObjectVar(model=Site, required=False,
                              description="Filter by site")
        role = MultiObjectVar(model=DeviceRole, required=False,
                              description="Filter by device role")
        tag = MultiObjectVar(model=Tag, required=False,
                             description="Filter by device tag")
        devices = MultiObjectVar(
            model=Device,
            required=False,
            description="Specific devices. Empty = all active devices matching above.",
            query_params={
                "status": "active",
                "manufacturer": "extreme-networks",
                "site_id": "$site",
                "role_id": "$role",
                "tag_id": "$tag",
            },
        )
        platform_filter = ChoiceVar(
            choices=(("both", "EXOS + VOSS"), ("exos", "EXOS only"), ("voss", "VOSS only")),
            default="both",
            description="Which Extreme platform to include.",
            label="Platform",
        )
        structural_tag = MultiObjectVar(
            model=Tag,
            required=False,
            description=(
                "Interface tags marking structural links that must never alert "
                "(stack, ISC, MLAG peer-link, SPAN). Ports carrying one of these "
                "tags are expected to be labelled `X` regardless of cabling."
            ),
            label="Structural (never-alert) interface tags",
        )

        # ---- Reporting ----

        include_admin_down = BooleanVar(
            default=False,
            description="Include interfaces disabled in NetBox.",
            label="Include admin-down ports",
        )
        include_neutral = BooleanVar(
            default=True,
            description="Report ports whose live label is class X or N.",
            label="Include X / N ports",
        )
        fail_on_diff = BooleanVar(
            default=False,
            description="Mark the job failed when blocking diffs remain.",
            label="Fail the job on blocking diffs",
        )

        # ---- Execution ----

        save_config = BooleanVar(
            default=True,
            description="Persist after a successful per-device apply.",
            label="Save config after apply",
        )
        max_workers = IntegerVar(
            default=10, min_value=1, max_value=50,
            description="Concurrent SSH sessions.",
            label="Concurrent workers",
        )

        # ================================================================

        def run(self, data, commit):
            started = time.time()
            mode = data.get("mode", "compliance")
            remediating = mode == "remediate" and bool(commit)

            structural_tag_ids = {t.pk for t in (data.get("structural_tag") or [])}

            device_list = self._resolve_devices(data)
            if not device_list:
                self.log_failure("No Extreme devices match the selected scope.")
                return

            self.log_info(
                f"## Extreme Port Labels\n"
                f"- **Mode:** {mode}"
                f"{' + COMMIT (live push)' if remediating else ' (read-only)'}\n"
                f"- **Devices:** {len(device_list)}\n"
                f"- **Max label length:** {MAX_LABEL_LEN}\n"
                f"- **Workers:** {data.get('max_workers', 10)}"
            )
            if mode == "remediate" and not commit:
                self.log_warning(
                    "Mode is *remediate* but **Commit changes** is unticked — "
                    "this run only previews the commands."
                )

            allowlist = {
                line.strip() for line in (data.get("canary") or "").splitlines()
                if line.strip()
            }
            if remediating and not allowlist:
                self.log_warning(
                    "Remediation with **no canary allowlist** — every non-compliant "
                    "port in scope will be pushed. First live run should set the allowlist."
                )
            elif remediating and allowlist:
                self.log_info(f"Canary allowlist active: {len(allowlist)} port(s).")

            # ---- 1. Build the expected plan from NetBox ----
            plans_by_device: dict[str, list[PortPlan]] = {}
            targets: list[tuple[Device, str, str]] = []   # (device, ip, kind)
            for device in device_list:
                kind = _platform_kind(getattr(device.platform, "name", None))
                if kind is None:
                    continue
                plans = self._plan_device(device, kind, data, structural_tag_ids)
                if not plans:
                    continue
                plans_by_device[device.name] = plans
                ip = _device_ssh_ip(device)
                if ip:
                    targets.append((device, ip, kind))
                else:
                    for plan in plans:
                        plan.status = "unreachable"
                        plan.detail = "no oob_ip/primary_ip in NetBox"

            if not plans_by_device:
                self.log_failure("No labellable ports found in the selected scope.")
                return

            # ---- 2. Read live labels ----
            workers = min(int(data.get("max_workers", 10) or 10), max(1, len(targets)))
            live_by_device: dict[str, tuple[dict[str, str], dict[str, str]]] = {}
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(self._read_device, device.name, ip, kind): device.name
                    for device, ip, kind in targets
                }
                for index, future in enumerate(as_completed(futures), 1):
                    name = futures[future]
                    labels, descriptions, error = future.result()
                    if error:
                        for plan in plans_by_device.get(name, []):
                            plan.status = "unreachable"
                            plan.detail = error
                        self.log_warning(f"[{index}/{len(targets)}] ❌ **{name}** — {error}")
                        continue
                    live_by_device[name] = (labels, descriptions)
                    self._note_orphans(plans_by_device[name], labels)
                    self.log_info(
                        f"[{index}/{len(targets)}] ✅ **{name}** — "
                        f"{len(labels)} live label(s) read"
                    )

            # ---- 3. Compare ----
            for name, plans in plans_by_device.items():
                if name not in live_by_device:
                    continue
                labels, descriptions = live_by_device[name]
                for plan in plans:
                    self._compare(plan, labels, descriptions,
                                  bool(data.get("clear_description_string")))

            all_plans = [p for plans in plans_by_device.values() for p in plans]
            if not data.get("include_neutral", True):
                all_plans = [
                    p for p in all_plans
                    if not (p.expected in {"X", "N"} or (p.expected or "").startswith(("X-", "N-")))
                ]

            self._report(all_plans)

            # ---- 4. Remediate ----
            if mode == "remediate":
                self._remediate(all_plans, targets, data, remediating, allowlist)

            # ---- 5. Outcome ----
            blocking = [p for p in all_plans if p.blocking]
            elapsed = int(time.time() - started)
            if not blocking:
                self.log_success(
                    f"All {len(all_plans)} evaluated port(s) compliant ({elapsed}s)."
                )
            elif data.get("fail_on_diff") and not remediating:
                self.log_failure(
                    f"{len(blocking)} port(s) non-compliant out of "
                    f"{len(all_plans)} ({elapsed}s)."
                )
            else:
                self.log_warning(
                    f"{len(blocking)} port(s) non-compliant out of "
                    f"{len(all_plans)} ({elapsed}s)."
                )

        # ---- helpers -------------------------------------------------------

        def _resolve_devices(self, data) -> list:
            selected = data.get("devices")
            if selected:
                queryset = Device.objects.filter(pk__in=[d.pk for d in selected])
            else:
                queryset = Device.objects.filter(status=DeviceStatusChoices.STATUS_ACTIVE)
                if data.get("site_group"):
                    group_ids: set[int] = set()
                    for group in data["site_group"]:
                        group_ids.add(group.pk)
                        descendants = getattr(group, "get_descendants", None)
                        if callable(descendants):
                            group_ids.update(
                                descendants(include_self=True).values_list("pk", flat=True)
                            )
                    queryset = queryset.filter(site__group_id__in=group_ids)
                if data.get("site"):
                    queryset = queryset.filter(site__in=data["site"])
                if data.get("role"):
                    queryset = queryset.filter(role__in=data["role"])
                if data.get("tag"):
                    queryset = queryset.filter(tags__in=data["tag"]).distinct()

            wanted = data.get("platform_filter", "both")
            result = []
            for device in queryset.select_related(
                "platform", "site", "primary_ip4", "primary_ip6", "oob_ip"
            ):
                kind = _platform_kind(getattr(device.platform, "name", None))
                if kind is None:
                    continue
                if wanted != "both" and kind != wanted:
                    continue
                result.append(device)
            return sorted(result, key=lambda d: d.name or "")

        def _plan_device(self, device, kind, data, structural_tag_ids) -> list[PortPlan]:
            plans: list[PortPlan] = []
            qs = (
                Interface.objects.filter(device=device)
                .select_related("device", "device__role", "device__site")
                .prefetch_related("tags")
            )
            if any(f.name == "_path" for f in Interface._meta.get_fields()):
                qs = qs.select_related("_path")
            interfaces = qs
            for iface in interfaces:
                if not _is_physical(iface):
                    continue
                if not iface.enabled and not data.get("include_admin_down"):
                    continue
                expected, status = expected_label_for(iface, structural_tag_ids)
                if status == "no_cable":
                    continue
                plan = PortPlan(
                    device=device.name,
                    site=getattr(device.site, "slug", "") or "",
                    kind=kind,
                    ifname=iface.name,
                    expected=expected,
                )
                if status == "too_long":
                    plan.status = "too_long"
                    plan.detail = f"no ID form fits {MAX_LABEL_LEN} chars; shortest={expected}"
                    plan.expected = ""
                plans.append(plan)
            return plans

        def _read_device(self, name, ip, kind):
            try:
                from django.db import close_old_connections
                close_old_connections()
            except Exception:  # noqa: BLE001
                pass
            nc = None
            try:
                nc = _connect(name, ip, kind)
                labels, descriptions = _fetch_live_labels(nc, kind)
                return labels, descriptions, None
            except Exception as exc:  # noqa: BLE001
                logger.error("[%s] label read failed: %s", name, exc)
                return {}, {}, str(exc)
            finally:
                if nc is not None:
                    try:
                        nc.disconnect()
                    except Exception:  # noqa: BLE001
                        pass
                try:
                    from django.db import close_old_connections
                    close_old_connections()
                except Exception:  # noqa: BLE001
                    pass

        @staticmethod
        def _note_orphans(plans: list[PortPlan], labels: dict[str, str]) -> None:
            """Live labels with no cabled NetBox port — report, never remediate."""
            if not plans or not labels:
                return
            template = plans[0]
            planned: set[str] = set()
            for plan in plans:
                planned |= port_key_aliases(plan.ifname)
            for live_port, live_label in labels.items():
                if not live_label:
                    continue
                if port_key_aliases(live_port) & planned:
                    continue
                plans.append(PortPlan(
                    device=template.device,
                    site=template.site,
                    kind=template.kind,
                    ifname=live_port,
                    live=live_label,
                    status="orphan",
                    detail="labelled on box, no cable in NetBox",
                ))

        @staticmethod
        def _compare(plan: PortPlan, labels, descriptions, clear_description: bool):
            if plan.status in {"too_long", "unreachable", "orphan"}:
                return
            plan.live = lookup_live_label(labels, plan.ifname)
            plan.description_string = lookup_live_label(descriptions, plan.ifname)

            if plan.description_string:
                # description-string wins ifAlias on EXOS, so the grammar label
                # in display-string is invisible to Zabbix while it is set.
                plan.status = "description_string_set"
                plan.detail = f"description-string={plan.description_string!r}"
                # Never wipe human text unless the operator ticked the box.
                if plan.expected and clear_description:
                    plan.commands = exos_apply_commands(plan.ifname, plan.expected, True)
                return

            issues = validate_label(plan.live) if plan.live else []
            if plan.live and "forbidden_chars" in " ".join(issues):
                plan.status = "forbidden"
                plan.detail = ",".join(issues)
            elif plan.live and "too_long" in issues:
                plan.status = "too_long"
                plan.detail = f"live label is {len(plan.live)} chars"
            elif not plan.live:
                plan.status = "missing"
            elif plan.live.upper() == plan.expected.upper():
                plan.status = "ok"
            else:
                plan.status = "diff"

            if plan.status in {"missing", "diff", "forbidden", "too_long"} and plan.expected:
                if plan.kind == "voss":
                    plan.commands = voss_apply_commands(plan.ifname, plan.expected)
                else:
                    plan.commands = exos_apply_commands(
                        plan.ifname, plan.expected, clear_description
                    )

        def _report(self, plans: list[PortPlan]):
            counts: dict[str, int] = {}
            for plan in plans:
                counts[plan.status] = counts.get(plan.status, 0) + 1
            summary = " · ".join(f"**{k}** {v}" for k, v in sorted(counts.items()))
            self.log_info(f"\n---\n## Summary\n{summary or '_nothing evaluated_'}")

            interesting = [p for p in plans if p.status != "ok"]
            if not interesting:
                return
            rows = [
                "| Device | ifName | Expected | Live | Len | Status | Detail |",
                "|--------|--------|----------|------|-----|--------|--------|",
            ]
            for plan in sorted(interesting, key=lambda p: (p.device, p.ifname)):
                rows.append(
                    f"| {_cell(plan.device)} | {_cell(plan.ifname)} "
                    f"| `{_cell(plan.expected) or '—'}` | `{_cell(plan.live) or '—'}` "
                    f"| {len(plan.expected)} | {plan.status} | {_cell(plan.detail)} |"
                )
            # NetBox truncates very long log entries; chunk the table.
            for start in range(0, len(rows) - 2, 200):
                chunk = rows[:2] + rows[2 + start:2 + start + 200]
                self.log_info("\n### Non-compliant ports\n\n" + "\n".join(chunk))

        def _remediate(self, all_plans, targets, data, remediating, allowlist):
            actionable = [p for p in all_plans if p.commands]
            if allowlist:
                actionable = [
                    p for p in actionable if f"{p.device}::{p.ifname}" in allowlist
                ]
            if not actionable:
                self.log_info("Nothing to remediate.")
                return

            by_device: dict[str, list[PortPlan]] = {}
            for plan in actionable:
                by_device.setdefault(plan.device, []).append(plan)

            if not remediating:
                for name, plans in sorted(by_device.items()):
                    lines = [c for p in plans for c in p.commands]
                    self.log_info(
                        f"\n---\n### Would apply on {name} ({len(plans)} port(s))\n"
                        "```\n" + "\n".join(lines) + "\n```"
                    )
                self.log_success(
                    f"Preview only — {len(actionable)} port(s) across "
                    f"{len(by_device)} device(s). Tick **Commit changes** to push."
                )
                return

            ip_kind = {device.name: (ip, kind) for device, ip, kind in targets}
            workers = min(int(data.get("max_workers", 10) or 10), max(1, len(by_device)))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {}
                for name, plans in by_device.items():
                    if name not in ip_kind:
                        self.log_warning(f"⏭️ {name} — no reachable IP, skipped.")
                        continue
                    ip, kind = ip_kind[name]
                    futures[pool.submit(
                        self._apply_device, name, ip, kind, plans,
                        bool(data.get("save_config", True)),
                    )] = name
                for index, future in enumerate(as_completed(futures), 1):
                    name = futures[future]
                    ok, transcript, error = future.result()
                    icon = "✅" if ok else "❌"
                    self.log_info(
                        f"[{index}/{len(futures)}] {icon} **{name}** — "
                        f"{len(by_device[name])} port(s)"
                    )
                    self.log_info(f"\n---\n### {icon} {name}\n```\n{transcript}\n```")
                    if error:
                        self.log_failure(f"**{name}** — {error}")

        def _apply_device(self, name, ip, kind, plans, save_config):
            nc = None
            transcript: list[str] = []
            try:
                nc = _connect(name, ip, kind)
                for plan in plans:
                    if plan.expected and len(plan.expected) > MAX_LABEL_LEN:
                        # Belt and braces — never push something EXOS would cut.
                        return (False, "\n".join(transcript),
                                f"refused {plan.ifname}: label exceeds {MAX_LABEL_LEN}")
                    if plan.expected and (FORBIDDEN_CHARS & set(plan.expected)):
                        return (False, "\n".join(transcript),
                                f"refused {plan.ifname}: forbidden characters")
                    if kind == "voss":
                        output = nc.send_config_set(plan.commands, read_timeout=90)
                        transcript.append("> " + " ; ".join(plan.commands))
                        transcript.append((output or "").strip())
                        if _looks_rejected(output):
                            return (False, "\n".join(transcript),
                                    f"command rejected: {plan.commands!r}")
                    else:
                        for cmd in plan.commands:
                            output = _send(nc, cmd, read_timeout=60)
                            transcript.append(f"> {cmd}")
                            if output.strip():
                                transcript.append(output.strip())
                            if _looks_rejected(output):
                                return (False, "\n".join(transcript),
                                        f"command rejected: {cmd!r}")
                    plan.status = "applied"
                if save_config:
                    cmd = "save config" if kind == "voss" else "save configuration"
                    output = _send(nc, cmd, read_timeout=180)
                    transcript.append(f"> {cmd}")
                    transcript.append((output or "").strip())
                return True, "\n".join(transcript), None
            except Exception as exc:  # noqa: BLE001
                logger.error("[%s] remediation failed: %s", name, exc)
                return False, "\n".join(transcript), str(exc)
            finally:
                if nc is not None:
                    try:
                        nc.disconnect()
                    except Exception:  # noqa: BLE001
                        pass


_RE_REJECTED = re.compile(
    r"(?im)^\s*%?\s*error\b|invalid input|ambiguous\s+|incomplete command|truncating to"
)


def _looks_rejected(output: str) -> bool:
    """EXOS returns CLI errors as text; also catch the truncation warning."""
    return bool(output) and bool(_RE_REJECTED.search(output))


def _cell(value) -> str:
    """Escape a value for a Markdown table cell."""
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\r", "").replace("\n", "<br>")
