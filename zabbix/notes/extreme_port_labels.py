"""
Extreme Port Labels — NetBox Custom Script
==========================================

Generate / verify the on-box port label ``CLASS[-SPEED]-ID`` (SNMP ``ifAlias``)
on Extreme switches, from NetBox cabling topology.

Three modes:

1. **preview** (default) — expected labels from NetBox cabling. No SSH.
2. **compliance** — same plan, plus the live label from the box. Nothing is
   pushed. Live labels without a complete cable stay on the box and are listed
   as ``kept``.
3. **remediate** — push only non-compliant *cabled* ports. Double-gated:
   ``mode=remediate`` **and** NetBox's *Commit changes* box.

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

import csv
import importlib.util
import io
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
# testable outside a NetBox worker (see test_extreme_port_labels.py).

#: EXOS ``display-string`` truncates silently past 20. VOSS ``name`` allows 64,
#: but the fleet uses the lowest common denominator so one label fits both.
MAX_LABEL_LEN = 20

#: Union of the two EXOS User Guide 32.7.1 character lists, plus ``?``, ``.``
#: (fleet policy: no dots — SPEED is ``2G5``, ports use ``_``), and the EXOS
#: port-list separators ``,`` ``;`` so a label cannot become a second command.
FORBIDDEN_CHARS = frozenset(': ."<>&?;,\t\n\r')

#: Pushed labels are an allowlist, not a denylist. EXOS ``display-string`` is
#: unquoted on the wire; anything outside this set is refused before SSH.
SAFE_LABEL_RE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{0,19}$")

#: Local ifName interpolated into ``configure ports …`` / ``interface GigabitEthernet …``.
#: One, two, or three numeric fields (EXOS ``1:24``, VOSS ``1/24`` / ``1/1/1``).
SAFE_PORT_RE = re.compile(r"^\d{1,4}([:/]\d{1,4}){0,2}$")

CLASSES = ("USW", "US", "UP", "MON", "UW", "TMON", "X", "N")

#: Classes that never carry a SPEED token.
NO_SPEED_CLASSES = frozenset({"X", "N", "UW", "TMON"})

#: Grammar token ``2G5`` (dots forbidden). Other PHYs are derived from Mbps
#: (``50G``, ``200G``, ``800G``) so a new IEEE rate does not need a table row.
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
_SPEED_TOKEN_RE = re.compile(r"^(?:\d+G\d*|\d+M)$")

CLASS_DEFAULT_MBPS = {"USW": 10000, "US": 10000, "UP": 1000, "MON": 1000}


def mbps_to_speed_token(mbps: int | None) -> str | None:
    """Map a link rate to a grammar SPEED token.

    Known spellings win (``2500`` → ``2G5``, not ``2.5G``). Anything else that
    is a whole number of Gbps or Mbps becomes ``NG`` / ``NM`` so 50G / 200G /
    800G work the day the first transceiver shows up in NetBox.
    """
    if not mbps or mbps <= 0:
        return None
    known = MBPS_SPEED_TOKEN.get(mbps)
    if known:
        return known
    if mbps % 1000 == 0:
        return f"{mbps // 1000}G"
    if mbps > 1000 and mbps % 500 == 0 and (mbps % 1000) == 500:
        return f"{mbps // 1000}G5"
    if mbps < 1000:
        return f"{mbps}M"
    return None


def speed_token_to_mbps(token: str | None) -> int | None:
    """Inverse of ``mbps_to_speed_token``. ``None`` if the token is not a PHY."""
    if not token:
        return None
    known = SPEED_TOKEN_MBPS.get(token)
    if known is not None:
        return known
    match = re.fullmatch(r"(\d+)G(\d*)", token)
    if match:
        whole = int(match.group(1))
        frac = match.group(2)
        if not frac:
            return whole * 1000
        if frac == "5":
            return whole * 1000 + 500
        return None
    match = re.fullmatch(r"(\d+)M", token)
    if match:
        return int(match.group(1))
    return None

#: Do not size the ID against a worst-case SPEED token. Reserving ``400G-`` (5)
#: on a 1G USW link forced Dist→Access ``USW-1G-GFL-AC01_23`` (18) to drop
#: the floor, so GFL-ACCE01 and L02-ACCE01 both became ``USW-1G-AC01_23``
#: on Core. Reserve ``len(token)+1`` of the token that will actually be emitted.


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
            return speed_token_to_mbps(self.speed_token)
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
    if (
        rest
        and cls not in NO_SPEED_CLASSES
        and _SPEED_TOKEN_RE.fullmatch(rest[0])
        and speed_token_to_mbps(rest[0]) is not None
    ):
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
    if not SAFE_LABEL_RE.fullmatch(raw.upper()):
        issues.append("unsafe_charset")
    if raw != raw.upper():
        issues.append("not_uppercase")
    parsed = parse_label(raw)
    if parsed is None:
        issues.append("unparseable")
        return issues
    if parsed.speed_token and parsed.cls in NO_SPEED_CLASSES:
        issues.append("speed_on_neutral_class")
    if (parsed.speed_token
            and speed_token_to_mbps(parsed.speed_token) == CLASS_DEFAULT_MBPS.get(parsed.cls)):
        # One fact, one encoding — a token equal to the class default is noise.
        issues.append("redundant_speed")
    return issues


def is_safe_cli_label(label: str) -> bool:
    """True when ``label`` is safe to interpolate into an unquoted EXOS CLI."""
    return bool(label) and len(label) <= MAX_LABEL_LEN and bool(SAFE_LABEL_RE.fullmatch(label))


def is_safe_cli_port(ifname: str) -> bool:
    """True when ``ifname`` is a single EXOS/VOSS port, not a list or injection."""
    return bool(ifname) and bool(SAFE_PORT_RE.fullmatch(ifname.strip()))


def redact_error(text: str) -> str:
    """Keep SSH errors useful without echoing a password if netmiko includes one."""
    raw = "" if text is None else str(text)
    return re.sub(r"(?i)(password|passwd|secret|community)\s*[:=]\s*\S+", r"\1=***", raw)


#: Statuses that must not look like a clean compliance run. ``kept`` is listed
#: but not blocking — those strings are often still useful (ISP, leftover NIC).
BLOCKING_STATUSES = frozenset({
    "diff", "missing", "too_long", "forbidden",
    "unreachable", "alias_hijacked",
})

#: Cap markdown tables in the NetBox job log. The archive is the CSV Output tab;
#: a 1500-row first-run dump is truncated by NetBox and unreadable anyway.
LOG_TABLE_LIMIT = 40

CSV_COLUMNS = (
    "site", "device", "port", "kind",
    "class", "speed", "link_mbps",
    "far_site", "far_device", "far_port", "far_role",
    "expected", "live", "description_string", "ifalias_source",
    "status", "blocking", "collision", "len", "detail",
)

_EXCEL_PORT_RE = re.compile(r"^\d{1,4}[:/.\-]\d{1,4}([:/.\-]\d{1,4})?$")


def _excel_text(value: str) -> str:
    """Stop Excel turning VOSS ``1/17`` into a date when the CSV is pasted."""
    raw = "" if value is None else str(value)
    if _EXCEL_PORT_RE.fullmatch(raw):
        return f'="{raw}"'
    return raw


def plan_class(plan) -> str:
    parsed = parse_label(getattr(plan, "expected", "") or "")
    return parsed.cls if parsed else ""


def plan_speed(plan) -> str:
    parsed = parse_label(getattr(plan, "expected", "") or "")
    return (parsed.speed_token or "") if parsed else ""


def plan_ifalias_source(plan) -> str:
    """What SNMP ifAlias actually is. Zabbix LLD reads this, not display-string."""
    stored = getattr(plan, "ifalias_source", "") or ""
    if stored:
        return stored
    if (getattr(plan, "kind", "") == "exos"
            and getattr(plan, "description_string", "")):
        return "description-string"
    if getattr(plan, "kind", "") == "voss" and getattr(plan, "live", ""):
        return "name"
    if getattr(plan, "live", ""):
        return "display-string"
    return ""


def plan_is_blocking(plan) -> bool:
    return (
        getattr(plan, "status", "") in BLOCKING_STATUSES
        or bool(getattr(plan, "collision", False))
    )


def flag_collisions(plans: list) -> int:
    """Mark ports that share an expected label on the same device.

    The ladder is local (one far-end). Two neighbours can compress to the same
    20-character string; preview must say so instead of looking clean.
    """
    groups: dict[tuple[str, str], list] = {}
    for plan in plans:
        plan.collision = False
        expected = (plan.expected or "").strip().upper()
        if not expected or plan.status in {"kept", "unreachable"}:
            continue
        groups.setdefault((plan.device or "", expected), []).append(plan)
    hit = 0
    for group in groups.values():
        if len(group) < 2:
            continue
        for plan in group:
            plan.collision = True
        hit += len(group)
    return hit


def status_counts(plans: list) -> dict[str, int]:
    counts: dict[str, int] = {}
    for plan in plans:
        key = plan.status or "?"
        counts[key] = counts.get(key, 0) + 1
    return counts


def class_counts(plans: list) -> dict[str, int]:
    counts: dict[str, int] = {}
    for plan in plans:
        key = plan_class(plan) or (plan.status or "?")
        counts[key] = counts.get(key, 0) + 1
    return counts


def device_scorecard(plans: list) -> list[dict[str, str | int]]:
    """One row per switch — the job-log shape NetBox can actually render."""
    by_device: dict[str, list] = {}
    for plan in plans:
        by_device.setdefault(plan.device or "", []).append(plan)
    rows: list[dict[str, str | int]] = []
    for name in sorted(by_device):
        group = by_device[name]
        counts = status_counts(group)
        rows.append({
            "device": name,
            "site": group[0].site or "",
            "kind": group[0].kind or "",
            "ports": len(group),
            "ok": counts.get("ok", 0),
            "diff": counts.get("diff", 0),
            "missing": counts.get("missing", 0),
            "hijacked": counts.get("alias_hijacked", 0),
            "kept": counts.get("kept", 0),
            "unreach": counts.get("unreachable", 0),
            "too_long": counts.get("too_long", 0),
            "collision": sum(1 for p in group if getattr(p, "collision", False)),
            "blocking": sum(1 for p in group if plan_is_blocking(p)),
        })
    return rows


def markdown_table(
    headers: list[str],
    rows: list[list[str]],
    *,
    limit: int | None = LOG_TABLE_LIMIT,
) -> str:
    """Markdown table for the NetBox job log. Truncates; CSV is the archive."""
    if not rows:
        return ""
    shown = rows if limit is None else rows[:limit]
    omitted = len(rows) - len(shown)
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("--------" for _ in headers) + "|",
    ]
    for row in shown:
        lines.append("| " + " | ".join(row) + " |")
    if omitted:
        lines.append("")
        lines.append(f"_… {omitted} more rows in the CSV Output tab._")
    return "\n".join(lines)


def plans_to_csv(plans: list) -> str:
    """Excel-friendly CSV for the NetBox script Output tab (copy → sheet)."""
    flag_collisions(plans)
    buf = io.StringIO()
    buf.write("\ufeff")
    buf.write("sep=,\n")
    writer = csv.DictWriter(
        buf, fieldnames=CSV_COLUMNS, extrasaction="ignore", lineterminator="\n",
    )
    writer.writeheader()
    for plan in sorted(plans, key=lambda p: (p.device or "", p.ifname or "")):
        parsed = parse_label(plan.expected) if plan.expected else None
        link_mbps = getattr(plan, "link_mbps", None)
        writer.writerow({
            "site": plan.site,
            "device": plan.device,
            "port": _excel_text(plan.ifname),
            "kind": plan.kind,
            "class": parsed.cls if parsed else "",
            "speed": (parsed.speed_token or "") if parsed else "",
            "link_mbps": "" if link_mbps is None else str(link_mbps),
            "far_site": getattr(plan, "far_site", "") or "",
            "far_device": getattr(plan, "far_device", "") or "",
            "far_port": getattr(plan, "far_port", "") or "",
            "far_role": getattr(plan, "far_role", "") or "",
            "expected": plan.expected,
            "live": plan.live,
            "description_string": getattr(plan, "description_string", "") or "",
            "ifalias_source": plan_ifalias_source(plan),
            "status": plan.status,
            "blocking": "yes" if plan_is_blocking(plan) else "no",
            "collision": "yes" if getattr(plan, "collision", False) else "no",
            "len": len(plan.expected) if plan.expected else 0,
            "detail": plan.detail,
        })
    return buf.getvalue()


def build_label(cls: str, link_mbps: int | None, ident: str) -> str:
    """Assemble ``CLASS[-SPEED]-ID``, omitting SPEED at the class default speed."""
    token = None
    if cls not in NO_SPEED_CLASSES and link_mbps:
        if link_mbps != CLASS_DEFAULT_MBPS.get(cls):
            token = mbps_to_speed_token(link_mbps)
    pieces = [cls]
    if token:
        pieces.append(token)
    if ident:
        pieces.append(ident)
    return "-".join(pieces)


# ---- ID abbreviator -------------------------------------------------------
#
# Two layers, on purpose:
#
#   OPEN (do not add per-device rows): hostname tokens, site-slug prefix
#   strip, port segmentation, longest-fit ladder, refuse vs truncate.
#   A new SAN / ESX / Cohesity / odd box follows its NetBox name.
#
#   CLOSED (edit only when the *taxonomy* changes): FABRIC_CODE_SHORT /
#   ROLE_TO_CODE (estate spelling of CORE/DIST/…), CLASS role words,
#   BMC fallback tokens, port-name filler. Unknown USW role-words still
#   collapse to two letters (SPINE→SP) so 40G physics keep working.
#
# Validated against real device names in this estate:
#   CH-STA-L50-B01-ACCE01   CH-STA-L50-L01-CORE01   CH-NKN-G08-L02-CORE01-1
#   CH-STA-L50-B01-ACPO03   CH-STA-L42-CORE01-2     CH-STA-P-BACK02
# Two-letter codes are **fabric only** (the estate already writes Co/Di on
# the box). Endpoints keep the hostname token (SAN, SNAS, ESX, BACK) — a
# made-up SN/NS/CY/DC does not tell an engineer what they are looking at.

FABRIC_CODE_SHORT = {
    "CORE": "CO",
    "DIST": "DI",
    "ACCE": "AC",
    "ACPO": "AP",
    "MGMT": "MG",
    "FWGW": "FW",
    "FWZONE": "FW",
    "CATO": "CT",
}
ROLE_CODE_SHORT = FABRIC_CODE_SHORT  # used by the fabric ladder only

#: Role overwrites the hostname **only** for fabric, where CORE/DIST hygiene
#: varies. Server / storage / cohesity names (ESX, SAN, SNAS, SAN10-N01) are
#: left alone — flattening them to ES/SN/CY is how labels stopped making sense.
ROLE_TO_CODE = {
    "switch core": "CO",
    "switch dist": "DI",
    "switch access": "AC",
    "switch mgmt": "MG",
    "access point": "AP",
    "firewall": "FW",
    "sd wan socket": "WA",
}


def role_code(far_role: str | None) -> str:
    """Two-letter fabric code, or '' so the hostname token is kept.

    Exact role names from this estate win. A new ``Switch Spine`` / ``Switch
    Leaf`` role still shortens (SPINE→SP, LEAF→LE) without a table row —
    same rule ``_code_bases`` uses for unknown USW hostname words.
    """
    key = (far_role or "").strip().lower()
    if not key:
        return ""
    known = ROLE_TO_CODE.get(key)
    if known:
        return known
    words = key.replace("-", " ").split()
    if len(words) >= 2 and words[0] == "switch":
        tail = words[-1].upper()
        if tail in FABRIC_CODE_SHORT:
            return FABRIC_CODE_SHORT[tail]
        if len(tail) >= 4 and tail.isalpha():
            return tail[:2]
    return ""

_TAIL_RE = re.compile(r"^(?P<code>[A-Z]+)(?P<num>\d*)$")
_PORT_PAREN_RE = re.compile(r"\(([^)]+)\)")
#: Port-name filler. Whole segments only (``ct0.eth4`` → ``CT0_4``). Never
#: invented per-vendor — if a segment is not in this set it stays.
_PORT_NOISE = frozenset({"ETH", "NIC", "NETWORK", "EMBEDDED", "PARTITION", "PORT"})


def _uniq(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


@dataclass(frozen=True)
class DeviceNameParts:
    scope: str      # location token taken from the *hostname* (or a site token that was actually stripped from it)
    code: str       # CORE / ESX / SAN / N / ...
    num: str        # 01 / 42 / ''
    stack: str      # stack member suffix ('1', '2') or ''
    extra: str = "" # leftover identity between scope and code (SAN10 on lr50-san10-n01)


def split_device_name(name: str, site_slug: str, local_site_slug: str) -> DeviceNameParts:
    """Break a NetBox device name into the pieces the abbreviator needs.

    Strip only leading hostname tokens that also lead the far-site slug.
    Scope is a token that exists on the hostname (or was stripped from it) —
    never a NetBox site tail like ``DC`` that does not appear in the name.
    Leftover middle tokens (``SAN10``) stay as ``extra`` so Cohesity
    ``lr50-san10-n01`` remains ``LR50-SAN10-N01``, not ``CY01``.
    """
    clean = (name or "").upper().split(".")[0]
    host = [tok for tok in clean.split("-") if tok]
    if not host:
        return DeviceNameParts("", "", "", "")
    site = [tok for tok in (site_slug or "").upper().split("-") if tok]
    local = (local_site_slug or "").upper()
    site_u = (site_slug or "").upper()

    shared = 0
    while shared < len(host) and shared < len(site) and host[shared] == site[shared]:
        shared += 1
    rest = list(host[shared:] or host[-1:])

    stack = ""
    if len(rest) > 1 and rest[-1].isdigit() and len(rest[-1]) <= 2:
        stack = rest.pop()

    tail = rest.pop() if rest else (host[-1] if host else "")
    match = _TAIL_RE.match(tail)
    code, num = (match.group("code"), match.group("num")) if match else (tail, "")
    leftover = rest
    site_tail = site[-1] if site else ""
    same_site = bool(site_u) and site_u == local
    local_toks = set(local.split("-")) if local else set()

    if same_site:
        scope = leftover[-1] if leftover else ""
        extra_toks = leftover[:-1] if leftover else []
    elif site_tail and site_tail in host:
        # Building/site token really is on the hostname (L50, ZH5). Floor leftover
        # is dropped — L50-CO01 from L26 is the useful identity, not L01-CO01.
        scope = site_tail
        extra_toks = []
    elif leftover:
        scope = leftover[0]
        extra_toks = leftover[1:]
    elif shared:
        scope = host[shared - 1]
        extra_toks = []
    else:
        scope = ""
        extra_toks = []

    # Do not repeat the building we are sitting in (ch-zrh-zh4 → ZH4).
    # That was inventing ``DC``'s cousin: a scope that costs the far-port.
    if scope and scope in local_toks:
        extra_toks = [tok for tok in extra_toks if tok != scope]
        scope = extra_toks[0] if extra_toks else ""
        extra_toks = extra_toks[1:] if extra_toks else []

    return DeviceNameParts(
        scope=scope, code=code, num=num, stack=stack,
        extra="-".join(extra_toks),
    )


def _clean_port_segments(text: str) -> list[str]:
    token = (text or "").upper().replace(":", "_").replace("/", "_").replace(".", "_")
    token = "".join(ch for ch in token if ch.isalnum() or ch == "_")
    segs: list[str] = []
    for seg in token.split("_"):
        if not seg:
            continue
        if seg.startswith("PORT") and len(seg) > 4 and seg[4:].isdigit():
            seg = seg[4:]
        for noise in _PORT_NOISE:
            if seg.startswith(noise) and seg[len(noise):].isdigit():
                seg = seg[len(noise):]
                break
            if (
                seg.endswith(noise)
                and len(seg) > len(noise)
                and seg[: -len(noise)].isalnum()
                and (
                    any(ch.isdigit() for ch in seg[: -len(noise)])
                    or len(seg[: -len(noise)]) > 3
                )
            ):
                # ``IDRAC10NIC`` → ``IDRAC10``. Not ``VMNIC`` → ``VM``.
                seg = seg[: -len(noise)]
                break
        segs.append(str(int(seg)) if seg.isdigit() else seg)
    kept = [seg for seg in segs if seg not in _PORT_NOISE]
    return kept or segs


def normalize_port_token(port_name: str) -> str:
    """``1:24`` / ``ct0.eth4`` / ``port15`` → ``1_24`` / ``CT0_4`` / ``15``.

    Dots are forbidden. Filler segments (ETH, NIC, PORT, EMBEDDED, …) drop
    so ``ct0.eth4`` is ``CT0_4`` and a 40G token still fits. Leading zeros
    stripped per numeric segment.
    """
    return "_".join(_port_identity_segments(port_name))


def _port_identity_segments(port_name: str) -> list[str]:
    """Prefer a rendering that still has letters (``CT0_4``, ``IDRAC_1``)."""
    raw = port_name or ""
    candidates = [raw]
    match = _PORT_PAREN_RE.search(raw)
    if match:
        candidates.append(match.group(1))
        candidates.append(f"{raw[:match.start()]} {match.group(1)}")

    scored: list[tuple[tuple[int, int], list[str]]] = []
    for cand in candidates:
        segs = _clean_port_segments(cand)
        if not segs:
            continue
        joined = "_".join(segs)
        has_letter = any(ch.isalpha() for ch in joined)
        scored.append(((0 if has_letter else 1, len(joined)), segs))
    if not scored:
        return []
    scored.sort(key=lambda item: item[0])
    return scored[0][1]


def _port_suffix_candidates(port_name: str) -> list[str]:
    """Renderings of the far-end port, most detailed first.

    Numeric switch ports use ``_23`` / ``_1_20`` — the extra ``P`` was a
    character 40G does not have. Vendor NIC names shed trailing segments so a
    tight budget costs detail rather than the whole port. Numeric slot+port is
    never shortened to the slot only (``2_14`` → ``2`` would name the slot).
    """
    token = normalize_port_token(port_name)
    if not token:
        return [""]
    if token[0].isdigit():
        return [f"_{token}"]

    segments = token.split("_")
    forms = [token, token.replace("_", "")]
    forms += ["".join(segments[:n]) for n in range(len(segments) - 1, 0, -1)]
    return [f"_{form}" for form in _uniq(forms)]


def _port_suffix(port_name: str) -> str:
    """``23`` and Fortinet ``port23`` both render as ``_23``."""
    return _port_suffix_candidates(port_name)[0]


def _compact_port_suffixes(port_name: str) -> list[str]:
    """One-character-tighter numeric ports: ``1_20`` -> ``_120``.

    Used only when the underscored form cannot fit. Dropping the floor collides
    two floors' MG01; dropping the port collides ``1:20`` with ``1:21``.
    """
    token = normalize_port_token(port_name)
    if token and token[0].isdigit() and "_" in token:
        compact = token.replace("_", "")
        if compact != token:
            return [f"_{compact}"]
    return []


def _code_bases(parts: DeviceNameParts, short_fabric: bool = False) -> list[str]:
    """Fabric → 2 letters. Everything else keeps the hostname word, then shortens.

    ``short_fabric`` is True for USW (switch/firewall). Unknown role-words
    (``SPINE``, ``LEAF``, ``BORDER``) take the first two letters so a 40G
    token still has room for floor + port — the same reason CORE is CO.
    Endpoints must NOT use this: SNAS→SN is how labels stopped making sense.
    """
    word = parts.code or ""
    if word in FABRIC_CODE_SHORT:
        return [FABRIC_CODE_SHORT[word]]
    if word in FABRIC_CODE_SHORT.values():
        return [word]
    if short_fabric and len(word) >= 4 and word.isalpha():
        return [word[:2]]
    if not word:
        return [""]
    bases = [word[:n] for n in range(len(word), 1, -1)]
    if len(word) == 1:
        bases = [word]
    return _uniq(bases)


def _code_forms(parts: DeviceNameParts, short_fabric: bool = False) -> list[str]:
    """Longest identity first: ``SAN10-N01``, then ``N01``; ``CO01-1``, then ``CO01``."""
    numbered = [f"{base}{parts.num}" for base in _code_bases(parts, short_fabric) if base or parts.num]
    extras = [parts.extra] if parts.extra else [""]
    if parts.extra:
        extras.append("")  # retry without the cluster token if over budget
    forms: list[str] = []
    for extra in extras:
        prefix = f"{extra}-" if extra else ""
        for num in numbered:
            if parts.stack:
                forms.append(f"{prefix}{num}-{parts.stack}")
            forms.append(f"{prefix}{num}")
    return _uniq(forms)


def id_candidates(
    parts: DeviceNameParts,
    port_name: str = "",
    short_fabric: bool = False,
) -> list[str]:
    """Longest-first ID forms. ``build_label_for_far_end`` takes the first that fits.

    Fabric codes are two letters so 40G still fits. Endpoint codes stay as
    they appear on the hostname until the budget forces a shorter prefix.

    Keep the floor (SCOPE) whenever physics allow. Stack is dropped before
    SCOPE or the far port: on this estate ``CORE01-1`` / ``CORE01-2`` already
    differ by the VOSS slot (``01:01`` vs ``02:01``), so
    ``USW-1G-L02-CO01_1_1`` (18) keeps both floor and port.
    """
    codes = _code_forms(parts, short_fabric)
    scope = f"{parts.scope}-" if parts.scope else ""
    suffixes = _port_suffix_candidates(port_name)
    compact = _compact_port_suffixes(port_name)

    ladder: list[str] = []
    for code in codes:
        for sfx in suffixes:
            ladder.append(f"{scope}{code}{sfx}")
    for code in codes:
        for sfx in compact:
            ladder.append(f"{scope}{code}{sfx}")
    if scope:
        for code in codes:
            ladder.append(f"{scope}{code}")
    for code in codes:
        for sfx in suffixes:
            ladder.append(f"{code}{sfx}")
    for code in codes:
        for sfx in compact:
            ladder.append(f"{code}{sfx}")
    ladder.extend(codes)
    return _uniq(ladder)


def build_label_for_far_end(
    cls: str,
    link_mbps: int | None,
    parts: DeviceNameParts,
    port_name: str = "",
) -> str:
    """Pick the longest ID form that fits.

    Reserve the SPEED slot only for the token that will actually be emitted
    (``1G-`` is 3, ``40G-`` is 4). Do not reserve a phantom ``400G-`` on a 1G
    link — that dropped floor tokens. Room for ``40G`` comes from **short
    codes** (``CO`` ``DI`` ``AC`` ``MG``), not from leaving the ID blank.
    """
    token_needed = (
        cls not in NO_SPEED_CLASSES
        and bool(link_mbps)
        and link_mbps != CLASS_DEFAULT_MBPS.get(cls)
        and mbps_to_speed_token(link_mbps) is not None
    )
    token = mbps_to_speed_token(link_mbps) if token_needed else None
    reserve = (len(token) + 1) if token else 0
    budget = MAX_LABEL_LEN - reserve
    tried = ""
    short_fabric = cls == "USW"
    for ident in id_candidates(parts, port_name, short_fabric=short_fabric):
        bare = build_label(cls, None, ident)
        label = build_label(cls, link_mbps, ident)
        tried = label
        if len(bare) <= budget and not (FORBIDDEN_CHARS & set(label)):
            return label
    raise LabelTooLong(
        build_label(cls, link_mbps, id_candidates(parts, port_name, short_fabric=short_fabric)[0]),
        tried,
    )


def plan_label(
    *,
    local_site: str,
    far_name: str,
    far_site: str,
    far_port: str,
    far_role: str,
    far_is_mgmt: bool,
    link_mbps: int | None,
) -> str:
    """Same derivation ``expected_label_for`` uses, without NetBox objects."""
    cls = classify(far_role, link_mbps, far_port or "", far_is_mgmt)
    parts = split_device_name(far_name, far_site, local_site)
    code = role_code(far_role)
    if code:
        parts = replace(parts, code=code)
    port_ref = "" if cls == "UP" else (far_port or "")
    return build_label_for_far_end(cls, link_mbps, parts, port_ref)


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
#
# This is the *closed* policy table. The ID abbreviator is open (it follows
# whatever hostname NetBox has). CLASS cannot be open: a new "Camera" at 10G
# must stay MON, not become US. Operational contract: reuse the NetBox roles
# below. Inventing "Hypervisor" / "HCI" / "Tape" without adding a token here
# labels those data NICs MON (safe default, not silent US).

#: Far-end roles that are network infrastructure rather than an endpoint. A
#: firewall link carries the same operational weight as a switch uplink, so it
#: gets USW (link/flap/errors + speed expectation) rather than US/MON.
INFRA_ROLE_TOKENS = frozenset({"switch", "firewall"})

#: Far-end roles whose data NICs are production data path -> US regardless of
#: negotiated speed. Their out-of-band management ports are still MON.
DATA_ENDPOINT_ROLE_TOKENS = frozenset({"server", "storage", "cohesity"})

#: Fallback only. The authoritative out-of-band signal is the far device's
#: NetBox ``oob_ip`` being assigned to that interface; these name tokens cover
#: hosts where nobody has set it yet.
BMC_PORT_TOKENS = ("idrac", "ilo", "bmc", "ipmi", "cimc", "imm", "mgmt", "oob")

_ROLE_WORD_RE = re.compile(r"[a-z0-9]+")


def _role_words(role: str) -> set[str]:
    """Word tokens from a NetBox role name (``Switch Dist`` → {switch, dist})."""
    return set(_ROLE_WORD_RE.findall((role or "").lower()))


def is_bmc_port(far_port: str | None) -> bool:
    """True for an out-of-band management interface on the far end."""
    name = (far_port or "").lower()
    return any(token in name for token in BMC_PORT_TOKENS)


def classify(far_role: str, link_mbps: int | None, far_port: str = "",
             far_is_mgmt: bool = False) -> str:
    """CLASS from the far-end **role**, not from link speed.

    Speed only decides the optional SPEED token after CLASS is known.
    Unknown roles are ``MON`` even at 10G — a 10G camera is not a server.
    Matching is by role *words* so ``IPswitch`` does not become USW.
    """
    words = _role_words(far_role)
    if words & INFRA_ROLE_TOKENS:
        return "USW"
    if "access" in words and "point" in words:
        return "UP"
    if "sdwan" in words or ("sd" in words and "wan" in words):
        return "UW"
    if words & DATA_ENDPOINT_ROLE_TOKENS:
        # Lights-out and controller management is MON; data NICs are production.
        return "MON" if (far_is_mgmt or is_bmc_port(far_port)) else "US"
    return "MON"


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
    far_device: str = ""
    far_port: str = ""
    far_role: str = ""
    far_site: str = ""
    link_mbps: int | None = None
    ifalias_source: str = ""
    collision: bool = False

    @property
    def blocking(self) -> bool:
        # ``kept`` is listed, not failed — leftover ISP / NIC labels stay.
        # Duplicate expected labels on one box are blocking even when each
        # row looks ``ok`` in isolation.
        return plan_is_blocking(self)


def compare_plan(
    plan: PortPlan,
    labels: dict[str, str],
    descriptions: dict[str, str],
    clear_description: bool = False,
) -> None:
    """Fill live / status / commands on one plan. Pure helper (no SSH)."""
    if plan.status in {"too_long", "unreachable", "kept"}:
        return
    plan.live = lookup_live_label(labels, plan.ifname)
    plan.description_string = lookup_live_label(descriptions, plan.ifname)

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

    if plan.kind == "exos" and plan.description_string:
        plan.ifalias_source = "description-string"
        extra = (
            "description-string wins ifAlias "
            f"({plan.description_string!r})"
        )
        if plan.status == "ok":
            plan.status = "alias_hijacked"
            extra += (
                "; tick 'Also clear EXOS description-string' "
                "before Zabbix LLD will see the grammar"
            )
        plan.detail = f"{plan.detail}; {extra}" if plan.detail else extra
    elif plan.kind == "voss":
        plan.ifalias_source = "name" if plan.live else ""
    else:
        plan.ifalias_source = "display-string" if plan.live else ""

    if plan.status in {"missing", "diff", "forbidden", "too_long"} and plan.expected:
        if plan.kind == "voss":
            plan.commands = voss_apply_commands(plan.ifname, plan.expected)
        else:
            plan.commands = exos_apply_commands(
                plan.ifname, plan.expected, clear_description
            )
    elif plan.status == "alias_hijacked" and clear_description:
        plan.commands = exos_apply_commands(plan.ifname, plan.expected, True)


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
    far_is_mgmt = _is_management_interface(far)
    local_site = getattr(getattr(iface.device, "site", None), "slug", "") or ""
    far_site = getattr(getattr(far_device, "site", None), "slug", "") or ""
    try:
        return plan_label(
            local_site=local_site,
            far_name=far_device.name or "",
            far_site=far_site,
            far_port=far.name or "",
            far_role=far_role,
            far_is_mgmt=far_is_mgmt,
            link_mbps=link_mbps,
        ), "ok"
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
                "Preview expected CLASS[-SPEED]-ID labels from NetBox cabling "
                "(no SSH), compare them to the live box, or push. Cabled ports "
                "are evaluated; live labels without a NetBox cable are kept on "
                "the box and listed (never pushed). Preview needs no Commit. "
                "Remediation needs mode=remediate AND Commit changes AND "
                "(an allowlist or the full-scope box)."
            )
            commit_default = False
            scheduling_enabled = True
            job_timeout = 3600

            fieldsets = (
                ("Mode", ("mode", "clear_description_string", "canary",
                           "force_full_remediate")),
                ("Scope", ("site_group", "site", "role", "tag", "devices",
                           "platform_filter", "structural_tag")),
                ("Reporting", ("include_admin_down", "include_neutral",
                               "fail_on_diff")),
                ("Execution", ("save_config", "max_workers")),
            )

        # ---- Mode ----

        mode = ChoiceVar(
            choices=(
                ("preview", "Preview — expected labels from NetBox, no SSH"),
                ("compliance", "Compliance — read the box, report diffs"),
                ("remediate", "Remediate — push non-compliant labels (needs Commit)"),
            ),
            default="preview",
            description=(
                "Preview never opens SSH. Compliance reads display-string / "
                "interface name. Remediation additionally requires Commit "
                "changes, and either a canary allowlist or 'Remediate entire "
                "scope'."
            ),
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
        force_full_remediate = BooleanVar(
            default=False,
            description=(
                "Allow a remediate push without a canary allowlist. Leave off "
                "until preview + compliance look right on paper."
            ),
            label="Remediate entire scope (no allowlist)",
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
                "Interface tags marking ports that must never alert "
                "(SPAN, lab, operator mute). Stack / ISC / MLAG peer-links "
                "are ordinary USW uplinks — do not tag them. Tagged ports "
                "are expected to be labelled `X` regardless of cabling."
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
            description=(
                "Mark the job failed when any blocking row remains: diff, "
                "missing, too_long, forbidden, unreachable, alias_hijacked, "
                "or a duplicate expected label on one switch. Tick this on "
                "scheduled compliance runs."
            ),
            label="Fail the job on blocking rows",
        )

        # ---- Execution ----

        save_config = BooleanVar(
            default=True,
            description="Persist after a successful per-device apply.",
            label="Save config after apply",
        )
        max_workers = IntegerVar(
            default=8, min_value=1, max_value=20,
            description="Concurrent SSH sessions (capped at 20 — do not stampede the OOB).",
            label="Concurrent workers",
        )

        # ================================================================

        def run(self, data, commit):
            started = time.time()
            mode = data.get("mode", "preview")
            remediating = mode == "remediate" and bool(commit)
            preview_only = mode == "preview"

            structural_tag_ids = {t.pk for t in (data.get("structural_tag") or [])}

            device_list = self._resolve_devices(data)
            if not device_list:
                self.log_failure("No Extreme devices match the selected scope.")
                return

            self.log_info(
                f"## Extreme Port Labels\n"
                f"- **Mode:** {mode}"
                f"{' + COMMIT (live push)' if remediating else ' (no push)'}\n"
                f"- **SSH:** {'no' if preview_only else 'yes'}\n"
                f"- **Devices:** {len(device_list)}\n"
                f"- **Max label length:** {MAX_LABEL_LEN}\n"
                f"- **Workers:** {data.get('max_workers', 8)}"
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
            if remediating and not allowlist and not data.get("force_full_remediate"):
                self.log_failure(
                    "Remediate refused: set a **canary allowlist** or tick "
                    "**Remediate entire scope**. Preview/compliance first."
                )
                return
            if remediating and not allowlist:
                self.log_warning(
                    "Remediation with **no canary allowlist** — every "
                    "non-compliant port in scope will be pushed."
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
                if preview_only:
                    continue
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

            # ---- 2. Read live labels (skipped in preview) ----
            live_by_device: dict[str, tuple[dict[str, str], dict[str, str]]] = {}
            if not preview_only:
                workers = min(int(data.get("max_workers", 8) or 8), max(1, len(targets)))
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
                                plan.detail = redact_error(error)
                            self.log_warning(
                                f"[{index}/{len(targets)}] **{name}** — "
                                f"{redact_error(error)}"
                            )
                            continue
                        live_by_device[name] = (labels, descriptions)
                        self._note_kept_live(plans_by_device[name], labels, descriptions)
                        self.log_info(
                            f"[{index}/{len(targets)}] **{name}** — "
                            f"{len(labels)} live label(s) read"
                        )

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

            flag_collisions(all_plans)
            self._report(all_plans, preview_only=preview_only)

            # ---- 4. Remediate ----
            if mode == "remediate":
                self._remediate(all_plans, targets, data, remediating, allowlist)

            # ---- 5. Outcome ----
            blocking = [p for p in all_plans if p.blocking]
            unreachable_n = sum(1 for p in all_plans if p.status == "unreachable")
            elapsed = int(time.time() - started)
            if preview_only:
                self.log_success(
                    f"Preview: {len(all_plans)} expected label(s) from NetBox "
                    f"cabling ({elapsed}s). CSV is in the Output tab — copy into Excel."
                )
            elif not blocking:
                self.log_success(
                    f"All {len(all_plans)} evaluated port(s) compliant ({elapsed}s). "
                    f"Zabbix ifAlias matches expected on every cabled port we could read."
                )
            elif data.get("fail_on_diff") and not remediating:
                extra = (
                    f" including {unreachable_n} unreachable"
                    if unreachable_n else ""
                )
                self.log_failure(
                    f"{len(blocking)} port(s) blocking out of "
                    f"{len(all_plans)}{extra} ({elapsed}s)."
                )
            else:
                extra = (
                    f" including {unreachable_n} unreachable"
                    if unreachable_n else ""
                )
                self.log_warning(
                    f"{len(blocking)} port(s) blocking out of "
                    f"{len(all_plans)}{extra} ({elapsed}s)."
                )
            return plans_to_csv(all_plans)

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

        @staticmethod
        def _far_bits(iface) -> tuple[str, str, str, str]:
            far = _far_endpoint(iface)
            if far is None:
                return "", "", "", ""
            if type(far).__name__ == "CircuitTermination":
                circuit = getattr(far, "circuit", None)
                cid = str(getattr(circuit, "cid", None) or "")
                provider = (
                    getattr(getattr(circuit, "provider", None), "name", None)
                    or getattr(getattr(circuit, "provider", None), "slug", None)
                    or ""
                )
                return str(provider), cid, "Circuit", ""
            far_device = getattr(far, "device", None)
            return (
                getattr(far_device, "name", None) or "",
                getattr(far, "name", None) or "",
                getattr(getattr(far_device, "role", None), "name", None) or "",
                getattr(getattr(far_device, "site", None), "slug", None) or "",
            )

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
                far_device, far_port, far_role, far_site = self._far_bits(iface)
                far = _far_endpoint(iface)
                link_mbps = None
                if far is not None and type(far).__name__ != "CircuitTermination":
                    speeds = [
                        s for s in (
                            iftype_to_mbps(getattr(iface, "type", None)),
                            iftype_to_mbps(getattr(far, "type", None)),
                        ) if s
                    ]
                    link_mbps = min(speeds) if speeds else None
                plan = PortPlan(
                    device=device.name,
                    site=getattr(device.site, "slug", "") or "",
                    kind=kind,
                    ifname=iface.name,
                    expected=expected,
                    far_device=far_device,
                    far_port=far_port,
                    far_role=far_role,
                    far_site=far_site,
                    link_mbps=link_mbps,
                )
                if status == "too_long":
                    plan.status = "too_long"
                    plan.detail = (
                        f"no ID form fits {MAX_LABEL_LEN} chars; "
                        f"shortest={expected}"
                    )
                else:
                    plan.status = "ok"
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
                return {}, {}, redact_error(str(exc))
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
        def _note_kept_live(plans: list[PortPlan], labels: dict[str, str],
                            descriptions: dict[str, str] | None = None) -> None:
            """Live labels with no cabled NetBox port — list them, never push.

            These strings often still tell an engineer what the port used to
            be (ISP, leftover server NIC). Keeping them beats blanking the
            box. Status is ``kept``, not a failure.
            """
            if not plans or not labels:
                return
            template = plans[0]
            planned: set[str] = set()
            for plan in plans:
                planned |= port_key_aliases(plan.ifname)
            descriptions = descriptions or {}
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
                    description_string=lookup_live_label(descriptions, live_port),
                    status="kept",
                    detail="live label kept; no complete cable in NetBox",
                    ifalias_source=(
                        "description-string"
                        if template.kind == "exos"
                        and lookup_live_label(descriptions, live_port)
                        else ("name" if template.kind == "voss" else "display-string")
                    ),
                ))

        @staticmethod
        def _compare(plan: PortPlan, labels, descriptions, clear_description: bool):
            compare_plan(plan, labels, descriptions, clear_description)

        def _report(self, plans: list[PortPlan], preview_only: bool = False):
            counts = status_counts(plans)
            classes = class_counts(plans)
            blocking_n = sum(1 for p in plans if p.blocking)
            hijacked = sum(1 for p in plans if plan_ifalias_source(p) == "description-string")
            collisions = sum(1 for p in plans if p.collision)
            summary = " · ".join(f"**{k}** {v}" for k, v in sorted(counts.items()))
            class_line = " · ".join(f"**{k}** {v}" for k, v in sorted(classes.items()))
            self.log_info(
                f"\n---\n## Summary\n{summary or '_nothing evaluated_'}\n\n"
                f"CLASS: {class_line or '—'}\n\n"
                f"**Blocking:** {blocking_n}"
                f" · **ifAlias hijacked by description-string:** {hijacked}"
                f" · **collisions:** {collisions}\n\n"
                "`ok` means Zabbix ifAlias matches expected. "
                "`alias_hijacked` means display-string matches but EXOS "
                "description-string still owns ifAlias.\n\n"
                "Full sheet is the **CSV in the Output tab** — copy into Excel "
                "and filter `blocking`, `status`, `class`, `ifalias_source`."
            )

            scorecard = device_scorecard(plans)
            score_rows = [
                [
                    _cell(str(r["device"])), _cell(str(r["site"])), _cell(str(r["kind"])),
                    str(r["ports"]), str(r["ok"]), str(r["blocking"]),
                    str(r["diff"]), str(r["missing"]), str(r["hijacked"]),
                    str(r["kept"]), str(r["unreach"]), str(r["collision"]),
                    str(r["too_long"]),
                ]
                for r in scorecard
            ]
            score_md = markdown_table(
                ["Device", "Site", "Kind", "Ports", "ok", "blocking",
                 "diff", "miss", "hijack", "kept", "unreach", "coll", "long"],
                score_rows,
                limit=None,
            )
            if score_md:
                for start in range(0, len(score_md.splitlines()), 200):
                    chunk = "\n".join(score_md.splitlines()[start:start + 200])
                    self.log_info(f"\n### Per-device scorecard\n\n{chunk}")

            if preview_only:
                too_long = [p for p in plans if p.status == "too_long"]
                collided = [p for p in plans if p.collision]
                if too_long:
                    self.log_warning(
                        f"{len(too_long)} port(s) cannot fit 20 characters — "
                        "see CSV status=too_long."
                    )
                if collided:
                    self.log_warning(
                        f"{len(collided)} port(s) share an expected label with "
                        "another port on the same switch — see CSV collision=yes."
                    )
                return

            def _emit(title: str, headers: list[str], body_rows: list[list[str]]) -> None:
                text = markdown_table(headers, body_rows)
                if text:
                    self.log_info(f"\n### {title}\n\n{text}")

            blocking_rows = [p for p in plans if p.blocking]
            _emit(
                "Blocking (Zabbix ifAlias is not the expected grammar)",
                ["Device", "ifName", "Expected", "Live", "ifAlias from", "Status"],
                [
                    [
                        _cell(p.device), _cell(p.ifname),
                        f"`{_cell(p.expected) or '—'}`",
                        f"`{_cell(p.live) or '—'}`",
                        _cell(plan_ifalias_source(p) or "—"),
                        p.status + (" collision" if p.collision else ""),
                    ]
                    for p in sorted(blocking_rows, key=lambda x: (x.device, x.ifname))
                ],
            )
            kept = [p for p in plans if p.status == "kept"]
            _emit(
                "Kept live labels (no NetBox cable — left on the box)",
                ["Device", "ifName", "Live"],
                [
                    [_cell(p.device), _cell(p.ifname), f"`{_cell(p.live) or '—'}`"]
                    for p in sorted(kept, key=lambda x: (x.device, x.ifname))
                ],
            )

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
            workers = min(int(data.get("max_workers", 8) or 8), max(1, len(by_device)))
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
                    if not is_safe_cli_label(plan.expected or ""):
                        return (False, "\n".join(transcript),
                                f"refused {plan.ifname}: label charset not [A-Z0-9_-]")
                    if not is_safe_cli_port(plan.ifname):
                        return (False, "\n".join(transcript),
                                f"refused {plan.ifname}: port name is not a single "
                                "EXOS/VOSS port (no lists, no extra punctuation)")
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
                return False, "\n".join(transcript), redact_error(str(exc))
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
