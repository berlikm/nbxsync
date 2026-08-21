"""
Extreme Port Mute — NetBox Custom Script
========================================

Admin-disable a port, or prefix its live on-box label with ``X-``, from an
**allowlist**. Not a fourth mode on Extreme Port Labels: cabling remediate
must never be able to shut an uplink.

Two actions (auto-detect EXOS vs VOSS from the NetBox platform):

1. **shutdown** (default) — EXOS ``disable port <slot:port>``;
   VOSS ``interface GigabitEthernet <slot/port>`` then ``shutdown``.
2. **x_prefix** — keep the live display-string / ``name``, prefix ``X-``,
   truncate from the **end** to 20 characters. EXOS writes ``display-string``
   and always clears ``description-string`` (that field wins SNMP ifAlias).

Allowlist only. There is no “entire scope” box. Stack / SummitStack ports
are refused. Complete NetBox cables are skipped unless you tick the override.
EXOS stacks SSH via the member with ``oob_ip`` / ``primary_ip`` (the VC
master) — same rule as port labels. This script does **not** write
``Interface.enabled`` in NetBox.

Deploy next to ``extreme_port_labels.py`` under ``SCRIPTS_ROOT``.
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
from dataclasses import dataclass, field

logger = logging.getLogger("extreme_port_mute")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)-7s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(_h)


# ---------------------------------------------------------------------------
# Load extreme_port_labels.py by path (NetBox isolates script modules)
# ---------------------------------------------------------------------------

_LABELS = None
_LABELS_ERROR: str | None = None
_LABELS_MODULE_NAME = "_epl_mute_lib"
MAX_LABEL_LEN = 20
_CANARY_RE = re.compile(r"^(\S+)::(\S+)$")
_STACKING_RE = re.compile(r"(?i)\bstacking([_\s-]*port)?\b")
LOG_TABLE_LIMIT = 40
CSV_COLUMNS = (
    "canary", "device", "netbox_member", "ssh_via", "site", "kind",
    "port", "action", "live", "description_string", "new_label",
    "cabled", "far_device", "far_port", "iftype", "port_in_netbox",
    "status", "detail", "commands",
)


def _labels_candidate_paths(script_path: str | None = None) -> list[str]:
    here = os.path.dirname(os.path.abspath(script_path or __file__))
    names = ["extreme_port_labels.py"]
    out: list[str] = []
    seen: set[str] = set()
    for folder in (
        here,
        os.path.join(here, "scripts"),
        os.path.join(os.path.dirname(here), "scripts"),
        "/opt/netbox/netbox/scripts",
    ):
        for name in names:
            path = os.path.join(folder, name)
            real = os.path.realpath(path)
            if real in seen or not os.path.isfile(path):
                continue
            seen.add(real)
            out.append(path)
    return out


def _load_labels(script_path: str | None = None):
    """Return the port-labels module. Reuse a copy already in sys.modules."""
    global _LABELS, _LABELS_ERROR
    if _LABELS is not None or _LABELS_ERROR is not None:
        return _LABELS
    for mod in list(sys.modules.values()):
        if (
            getattr(mod, "platform_kind", None)
            and getattr(mod, "exos_apply_commands", None)
            and os.path.basename(getattr(mod, "__file__", "") or "")
            == "extreme_port_labels.py"
        ):
            _LABELS = mod
            return _LABELS
    errors: list[str] = []
    for path in _labels_candidate_paths(script_path):
        try:
            spec = importlib.util.spec_from_file_location(_LABELS_MODULE_NAME, path)
            if spec is None or spec.loader is None:
                errors.append(f"{path}: no loader")
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[_LABELS_MODULE_NAME] = module
            spec.loader.exec_module(module)
            _LABELS = module
            return _LABELS
        except Exception as exc:  # noqa: BLE001
            sys.modules.pop(_LABELS_MODULE_NAME, None)
            errors.append(f"{path}: {exc}")
    _LABELS_ERROR = "; ".join(errors) if errors else (
        "extreme_port_labels.py not found next to extreme_port_mute.py"
    )
    logger.warning("could not load extreme_port_labels.py (%s)", _LABELS_ERROR)
    return None


def epl():
    mod = _load_labels()
    if mod is None:
        raise RuntimeError(
            f"extreme_port_labels.py could not be loaded ({_LABELS_ERROR})"
        )
    return mod


# ===========================================================================
# Pure helpers (unit-tested; no NetBox, no SSH)
# ===========================================================================


def parse_allowlist_text(text: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Parse ``DEVICE::port`` lines. ``#`` comments allowed. No ranges."""
    entries: list[tuple[str, str]] = []
    errors: list[str] = []
    for index, raw in enumerate((text or "").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        match = _CANARY_RE.match(line)
        if not match:
            errors.append(
                f"line {index}: expected DEVICE::port, got {raw.strip()!r}"
            )
            continue
        host, port = match.group(1).strip(), match.group(2).strip()
        entries.append((host, port))
    return entries, errors


def already_x_muted(live: str) -> bool:
    """True when the string is already CLASS ``X`` / ``X-…``."""
    text = (live or "").strip().strip('"').strip("'").upper()
    return text == "X" or text.startswith("X-")


def x_prefix_source(display: str, description: str = "") -> str:
    """Text to prefix: EXOS display-string, else description-string, else empty."""
    display = (display or "").strip().strip('"').strip("'")
    if display:
        return display
    return (description or "").strip().strip('"').strip("'")


def x_prefix_label(live: str, max_len: int = MAX_LABEL_LEN) -> str:
    """``X-`` + live label, truncated from the end to ``max_len``.

    Empty live → ``X``. Already ``X`` / ``X-…`` is not double-prefixed.
    Uppercased so the result can pass the labels ``SAFE_LABEL_RE``.
    """
    text = x_prefix_source(live, "")
    if not text:
        return "X"
    upper = text.upper()
    if upper == "X" or upper.startswith("X-"):
        return upper[:max_len]
    return ("X-" + upper)[:max_len]


def is_stack_port(*, iftype: str = "", description: str = "") -> bool:
    """Refuse SummitStack / stacking ports so a mute job cannot split a VC."""
    blob = f"{iftype or ''} {description or ''}".lower()
    if "summitstack" in blob:
        return True
    return bool(_STACKING_RE.search(blob))


def native_cli_port(kind: str, ifname: str) -> str:
    """EXOS uses ``slot:port``; VOSS uses ``slot/port`` (and sub-port)."""
    raw = (ifname or "").strip()
    if kind == "voss":
        return raw.replace(":", "/").replace(".", "/")
    return raw.replace("/", ":").replace(".", ":")


def cli_shutdown_cmds(kind: str, ifname: str) -> list[str]:
    """Per-port disable/shutdown. Never a range — the transcript must be 1:1."""
    port = native_cli_port(kind, ifname)
    if kind == "voss":
        return [
            f"interface GigabitEthernet {port}",
            "shutdown",
            "exit",
        ]
    return [f"disable port {port}"]


def cli_x_prefix_cmds(kind: str, ifname: str, label: str) -> list[str]:
    """Write the X- label. EXOS always clears description-string (ifAlias)."""
    port = native_cli_port(kind, ifname)
    labels = epl()
    if kind == "voss":
        return labels.voss_apply_commands(port, label)
    return labels.exos_apply_commands(port, label, True)


def mute_dedupe_key(ssh_device: str, device: str, ifname: str) -> str:
    labels = epl()
    host = ssh_device or device
    return f"{host}::{labels.canonical_port_key(ifname)}"


@dataclass
class MutePlan:
    canary: str
    device: str
    ifname: str
    kind: str = ""
    site: str = ""
    ssh_device: str = ""
    netbox_member: str = ""
    action: str = "shutdown"
    live: str = ""
    description_string: str = ""
    new_label: str = ""
    cabled: bool = False
    far_device: str = ""
    far_port: str = ""
    iftype: str = ""
    netbox_description: str = ""
    port_in_netbox: bool = False
    status: str = "planned"
    detail: str = ""
    commands: list[str] = field(default_factory=list)

    @property
    def blocking(self) -> bool:
        return self.status in {"error", "unreachable"}


def decide_mute(
    plan: MutePlan,
    *,
    allow_cabled: bool,
    live_known: bool,
) -> MutePlan:
    """Fill ``status`` / ``commands``. Safe to call twice (preview then after SSH)."""
    labels = epl()
    plan.commands = []
    if plan.status in {"unreachable", "error"} and plan.detail and not plan.kind:
        return plan
    if plan.kind not in {"exos", "voss"}:
        plan.status = "error"
        plan.detail = "unknown platform; set EXOS or VOSS on the NetBox device"
        return plan
    if not labels.is_safe_cli_port(plan.ifname):
        plan.status = "error"
        plan.detail = (
            "port name is not a single EXOS/VOSS port "
            "(no ranges, no lists, no extra punctuation)"
        )
        return plan
    if is_stack_port(
        iftype=plan.iftype, description=plan.netbox_description,
    ):
        plan.status = "skip"
        plan.detail = "refused: SummitStack / stacking port"
        return plan
    if plan.cabled and not allow_cabled:
        far = f"{plan.far_device} {plan.far_port}".strip()
        plan.status = "skip"
        plan.detail = (
            "cabled in NetBox"
            + (f" ({far})" if far else "")
            + "; tick Allow cabled ports to override"
        )
        return plan

    if plan.action == "x_prefix":
        if not live_known:
            plan.new_label = ""
            plan.status = "planned"
            plan.detail = (
                "apply will read live display-string, prefix X-, "
                f"truncate to {MAX_LABEL_LEN} from the end"
            )
            return plan
        source = x_prefix_source(plan.live, plan.description_string)
        plan.new_label = x_prefix_label(source)
        display_ok = (plan.live or "").strip().strip('"').strip("'") == plan.new_label
        desc_clear = not (plan.kind == "exos" and (plan.description_string or "").strip())
        if display_ok and desc_clear:
            plan.status = "already"
            plan.detail = "already X / X- on display-string; nothing to write"
            return plan
        if not labels.is_safe_cli_label(plan.new_label):
            plan.status = "error"
            plan.detail = (
                f"X- label {plan.new_label!r} is not safe CLI "
                f"([A-Z0-9_-], max {MAX_LABEL_LEN})"
            )
            return plan
        plan.commands = cli_x_prefix_cmds(plan.kind, plan.ifname, plan.new_label)
        plan.status = "planned"
        if not desc_clear:
            plan.detail = (
                "prefix live label with X- and clear EXOS description-string "
                "(it currently wins ifAlias)"
            )
        else:
            plan.detail = "prefix live display-string with X- (truncate from the end)"
        return plan

    plan.commands = cli_shutdown_cmds(plan.kind, plan.ifname)
    plan.status = "planned"
    plan.detail = "admin-disable port"
    if not plan.port_in_netbox:
        plan.detail += " (port not in NetBox)"
    return plan


def apply_mute_on_session(
    nc,
    kind: str,
    plans: list[MutePlan],
    save_config: bool,
) -> tuple[bool, str, str | None]:
    """Push mute commands on an open session. Same prompt hunt as port labels."""
    labels = epl()
    transcript: list[str] = []
    todo = [p for p in plans if p.commands]
    if not todo:
        return True, "", None
    voss_config = False

    def _send(cmd: str, read_timeout: int = 60) -> str:
        return labels._send(nc, cmd, read_timeout=read_timeout, kind=kind)

    for plan in todo:
        if not labels.is_safe_cli_port(plan.ifname):
            return False, "\n".join(transcript), (
                f"refused {plan.ifname}: port name is not a single EXOS/VOSS port"
            )
        if plan.action == "x_prefix" and not labels.is_safe_cli_label(plan.new_label):
            return False, "\n".join(transcript), (
                f"refused {plan.ifname}: label charset not [A-Z0-9_-]"
            )
        if kind == "voss" and not voss_config:
            output = _send("configure terminal", read_timeout=30)
            transcript.append("> configure terminal")
            if (output or "").strip():
                transcript.append(output.strip())
            if labels._looks_rejected(output):
                return False, "\n".join(transcript), (
                    "command rejected: 'configure terminal'"
                )
            voss_config = True
        for cmd in plan.commands:
            if any(ch in cmd for ch in "\n\r;"):
                return False, "\n".join(transcript), (
                    f"refused {plan.ifname}: command contains newline or ';'"
                )
            output = _send(cmd, read_timeout=60)
            transcript.append(f"> {cmd}")
            if (output or "").strip():
                transcript.append(output.strip())
            if labels._looks_rejected(output):
                plan.status = "error"
                plan.detail = f"command rejected: {cmd!r}"
                return False, "\n".join(transcript), plan.detail
        plan.status = "applied"
        plan.detail = "applied"
    if voss_config:
        output = _send("end", read_timeout=30)
        transcript.append("> end")
        if (output or "").strip():
            transcript.append(output.strip())
    if save_config:
        if kind == "voss":
            output = labels._send_voss_timing(nc, "save config", read_timeout=180)
            transcript.append("> save config")
        else:
            output = labels._send(nc, "save configuration", read_timeout=180)
            transcript.append("> save configuration")
        if (output or "").strip():
            transcript.append(output.strip())
    return True, "\n".join(transcript), None


def plans_to_csv(plans: list[MutePlan]) -> str:
    labels = epl()
    buf = io.StringIO()
    buf.write("\ufeff")
    buf.write("sep=,\n")
    writer = csv.DictWriter(
        buf, fieldnames=CSV_COLUMNS, extrasaction="ignore", lineterminator="\n",
    )
    writer.writeheader()
    for plan in sorted(plans, key=lambda p: (p.device or "", p.ifname or "")):
        ssh_via = plan.ssh_device or ""
        if ssh_via == (plan.device or ""):
            ssh_via = ""
        writer.writerow({
            "canary": plan.canary,
            "device": plan.device,
            "netbox_member": plan.netbox_member,
            "ssh_via": ssh_via,
            "site": plan.site,
            "kind": plan.kind,
            "port": labels._excel_text(plan.ifname),
            "action": plan.action,
            "live": plan.live,
            "description_string": plan.description_string,
            "new_label": plan.new_label,
            "cabled": "yes" if plan.cabled else "no",
            "far_device": plan.far_device,
            "far_port": labels._excel_text(plan.far_port) if plan.far_port else "",
            "iftype": plan.iftype,
            "port_in_netbox": "yes" if plan.port_in_netbox else "no",
            "status": plan.status,
            "detail": plan.detail,
            "commands": " | ".join(plan.commands),
        })
    return buf.getvalue()


def _cell(value) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def markdown_table(headers: list[str], rows: list[list[str]], *, limit: int = LOG_TABLE_LIMIT) -> str:
    if not rows:
        return ""
    shown = rows[:limit]
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


# ===========================================================================
# NetBox Script
# ===========================================================================

try:
    from dcim.choices import DeviceStatusChoices
    from dcim.models import Device, Interface
    from extras.scripts import (
        BooleanVar,
        ChoiceVar,
        IntegerVar,
        Script,
        TextVar,
    )
    _NETBOX = True
except Exception:  # noqa: BLE001 — helpers stay importable outside NetBox
    _NETBOX = False
    Script = object  # type: ignore[assignment,misc]


if _NETBOX:

    class ExtremePortMute(Script):
        """Allowlist shutdown / X- mute on Extreme EXOS and VOSS."""

        class Meta(Script.Meta):
            name = "Extreme Port Mute (shutdown / X-)"
            description = (
                "Paste DEVICE::port lines. Shutdown (admin-disable) or prefix "
                "the live on-box label with X- (truncate to 20 from the end). "
                "Platform is detected from NetBox (EXOS vs VOSS). EXOS stacks "
                "SSH via the master. SummitStack ports are refused. Cabled "
                "ports need an override tick. Never writes NetBox "
                "Interface.enabled. Allowlist required — no entire-scope push. "
                "Apply needs Commit changes."
            )
            commit_default = False
            scheduling_enabled = False
            job_timeout = 3600
            fieldsets = (
                ("Mode", ("mode", "action")),
                ("Ports (required allowlist)", ("allowlist",)),
                ("Safety", ("allow_cabled", "save_config", "max_workers")),
            )

        mode = ChoiceVar(
            choices=(
                ("preview", "Preview — resolve allowlist in NetBox, no SSH"),
                ("apply", "Apply — SSH; needs Commit to push"),
            ),
            default="preview",
            description=(
                "Preview never opens SSH. Apply without Commit reads live "
                "labels and prints the commands. Apply + Commit pushes."
            ),
            label="Mode",
        )
        action = ChoiceVar(
            choices=(
                ("shutdown", "Shutdown / disable port (default on Core unused)"),
                ("x_prefix", "Prefix live display-string with X- (keep link up)"),
            ),
            default="shutdown",
            description=(
                "Shutdown: EXOS `disable port`, VOSS GigabitEthernet `shutdown`. "
                "X-: keep the live string, prefix X-, cut from the end to 20 "
                "chars. Zabbix IFALIAS mute without bringing the link down."
            ),
            label="Action",
        )
        allowlist = TextVar(
            required=True,
            description=(
                "One `device-name::ifname` per line. Full NetBox hostname. "
                "`2:10` and `2/10` match. Example:\n"
                "NL-ENS-NEP-GFL-CORE01-1::2:10\n"
                "NL-ENS-NEP-GFL-CORE01-1::2:11"
            ),
            label="Allowlist (DEVICE::port)",
        )
        allow_cabled = BooleanVar(
            default=False,
            description=(
                "Allow mute/shutdown on a port that has a complete NetBox cable. "
                "Off by default — leftover unused ports (no cable) are the "
                "usual target. Stack ports are still refused."
            ),
            label="Allow cabled ports",
        )
        save_config = BooleanVar(
            default=True,
            description="Persist after a successful per-box apply.",
            label="Save config after apply",
        )
        max_workers = IntegerVar(
            default=8, min_value=1, max_value=20,
            description=(
                "Concurrent SSH logins — one session per EXOS stack (master) "
                "or per VOSS box, not per port."
            ),
            label="Concurrent workers",
        )

        def run(self, data, commit):
            started = time.time()
            labels = _load_labels()
            if labels is None:
                self.log_failure(
                    "extreme_port_labels.py could not be loaded "
                    f"({_LABELS_ERROR}). Copy it next to this file under "
                    "SCRIPTS_ROOT (`/opt/netbox/netbox/scripts/`)."
                )
                return

            mode = data.get("mode") or "preview"
            action = data.get("action") or "shutdown"
            if action not in {"shutdown", "x_prefix"}:
                action = "shutdown"
            applying = mode == "apply" and bool(commit)
            preview_only = mode != "apply"
            allow_cabled = bool(data.get("allow_cabled"))

            entries, parse_errors = parse_allowlist_text(data.get("allowlist") or "")
            if parse_errors:
                for err in parse_errors:
                    self.log_failure(err)
            if not entries:
                self.log_failure(
                    "Allowlist is empty. Paste DEVICE::port lines. "
                    "There is no entire-scope mute."
                )
                return
            if parse_errors:
                return

            self.log_info(
                f"## Extreme Port Mute\n"
                f"- **Mode:** {mode}"
                f"{' + COMMIT (live push)' if applying else ' (no push)'}\n"
                f"- **Action:** {action}\n"
                f"- **Allowlist:** {len(entries)} port(s)\n"
                f"- **Allow cabled:** {'yes' if allow_cabled else 'no'}\n"
                f"- **Save config:** {bool(data.get('save_config', True))}\n"
            )
            self.log_info("```\n" + "\n".join(labels.runner_status_lines()) + "\n```")
            if mode == "apply" and not commit:
                self.log_warning(
                    "Mode is *apply* but **Commit changes** is unticked — "
                    "this run only previews the commands after SSH."
                )

            device_names = {host for host, _port in entries}
            found = self._devices_named(device_names)
            missing = sorted(device_names - set(found))
            device_list = list(found.values())
            extra_stack: list[str] = []
            if device_list:
                device_list, extra_stack = self._expand_exos_stack_members(device_list)
            if extra_stack:
                shown = ", ".join(extra_stack[:12])
                more = f" (+{len(extra_stack) - 12})" if len(extra_stack) > 12 else ""
                self.log_info(
                    "EXOS stack: included "
                    f"**{len(extra_stack)}** member(s) so slot-N cables and "
                    f"SSH via the master work: {shown}{more}."
                )
            sessions = self._group_ssh_sessions(device_list)
            ssh_by_device: dict[str, tuple] = {}
            for ssh_device, ip, kind, members in sessions:
                ssh_name = (
                    ssh_device.name if ssh_device is not None else members[0]["name"]
                )
                for member in members:
                    ssh_by_device[member["name"]] = (ssh_device, ip, kind, ssh_name, members)

            iface_index = self._iface_index(device_list)

            plans: list[MutePlan] = []
            seen_keys: set[str] = set()
            for host, port in entries:
                canary = f"{host}::{port}"
                plan = MutePlan(
                    canary=canary, device=host, ifname=port, action=action,
                )
                device = found.get(host)
                if device is None:
                    plan.status = "error"
                    plan.detail = (
                        f"device {host!r} not found (active) in NetBox — "
                        "use the full hostname"
                    )
                    plans.append(plan)
                    continue
                kind = labels.platform_kind(
                    getattr(getattr(device, "platform", None), "name", None),
                    getattr(getattr(device, "platform", None), "slug", None),
                )
                session = ssh_by_device.get(device.name)
                ssh_name = session[3] if session else device.name
                ssh_kind = session[2] if session else kind
                plan.kind = ssh_kind or kind or ""
                plan.site = getattr(getattr(device, "site", None), "slug", "") or ""
                plan.ssh_device = ssh_name
                owner, iface = self._pick_iface(iface_index, session[4] if session else [], port)
                if iface is not None:
                    plan.port_in_netbox = True
                    plan.netbox_member = getattr(getattr(iface, "device", None), "name", "") or ""
                    plan.iftype = getattr(iface, "type", None) or ""
                    plan.netbox_description = (getattr(iface, "description", None) or "").strip()
                    far = labels._far_endpoint(iface)
                    if far is not None:
                        plan.cabled = True
                        if type(far).__name__ == "CircuitTermination":
                            plan.far_device = "circuit"
                            plan.far_port = str(
                                getattr(getattr(far, "circuit", None), "cid", "") or ""
                            )
                        else:
                            far_dev = getattr(far, "device", None)
                            plan.far_device = getattr(far_dev, "name", None) or ""
                            plan.far_port = getattr(far, "name", None) or ""
                    if getattr(iface, "type", None) in labels._NON_PHYSICAL_TYPES:
                        plan.status = "skip"
                        plan.detail = f"not a physical Ethernet port ({iface.type})"
                        plans.append(plan)
                        continue
                key = mute_dedupe_key(plan.ssh_device, plan.device, plan.ifname)
                if key in seen_keys:
                    plan.status = "skip"
                    plan.detail = "duplicate of an earlier allowlist row on this stack/port"
                    plans.append(plan)
                    continue
                seen_keys.add(key)
                if plan.status != "skip":
                    decide_mute(plan, allow_cabled=allow_cabled, live_known=False)
                plans.append(plan)

            if missing:
                self.log_warning(
                    "Not in NetBox (active): " + ", ".join(missing)
                )

            session_plans: dict[str, list[MutePlan]] = {}
            for plan in plans:
                if plan.status in {"error", "skip"} and not plan.kind:
                    continue
                session_plans.setdefault(plan.ssh_device or plan.device, []).append(plan)

            if preview_only:
                self._report(plans, preview_only=True)
                elapsed = int(time.time() - started)
                self.log_success(
                    f"Preview: {len(plans)} allowlist row(s) ({elapsed}s). "
                    "No SSH. Run Apply without Commit to read live labels; "
                    "Apply + Commit to push. CSV is in the Output tab."
                )
                return plans_to_csv(plans)

            if labels._RUNNER is None and any(
                p.kind == "exos" and p.status == "planned" for p in plans
            ):
                self.log_failure(
                    "SSH transport unavailable — extreme_cli_runner.py could "
                    f"not be loaded ({labels._RUNNER_ERROR}). Deploy the runner "
                    "next to this script under SCRIPTS_ROOT. VOSS-only jobs "
                    "do not need the runner."
                )
                return plans_to_csv(plans)

            targets: list[tuple] = []
            for ssh_device, ip, kind, members in sessions:
                ssh_name = (
                    ssh_device.name if ssh_device is not None else members[0]["name"]
                )
                group = [
                    p for p in session_plans.get(ssh_name, [])
                    if p.status == "planned"
                ]
                if not group:
                    # still SSH if any row on this session needs live labels
                    group = [
                        p for p in session_plans.get(ssh_name, [])
                        if p.status not in {"error", "skip", "already"}
                    ]
                if not group:
                    continue
                if not ip:
                    names = ", ".join(m["name"] for m in members)
                    detail = (
                        "EXOS stack: no oob_ip/primary_ip on any member "
                        f"({names})"
                        if len(members) > 1
                        else "no oob_ip/primary_ip in NetBox"
                    )
                    for plan in session_plans.get(ssh_name, []):
                        if plan.status == "planned":
                            plan.status = "unreachable"
                            plan.commands = []
                            plan.detail = detail
                    self.log_warning(f"**{ssh_name}** — {detail}", obj=ssh_device)
                    continue
                targets.append((ssh_device, ip, kind, ssh_name))

            workers = min(int(data.get("max_workers", 8) or 8), max(1, len(targets) or 1))
            if targets:
                self.log_info(
                    f"SSH: **{len(targets)}** login(s) (one per EXOS stack or "
                    f"VOSS box, {workers} concurrent)."
                )
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures = {
                        pool.submit(
                            self._session_device,
                            ssh_name, ip, kind,
                            session_plans.get(ssh_name, []),
                            applying,
                            bool(data.get("save_config", True)),
                            allow_cabled,
                        ): ssh_name
                        for _dev, ip, kind, ssh_name in targets
                    }
                    for index, future in enumerate(as_completed(futures), 1):
                        name = futures[future]
                        connect_error, apply_error, transcript = future.result()
                        if connect_error:
                            self.log_warning(
                                f"[{index}/{len(targets)}] **{name}** — SSH failed: "
                                f"{labels.summarize_ssh_error(connect_error)}"
                            )
                            self.log_info(
                                f"```\n{labels.redact_error(connect_error)}\n```"
                            )
                            continue
                        applied_n = sum(
                            1 for p in session_plans.get(name, [])
                            if p.status == "applied"
                        )
                        self.log_info(
                            f"[{index}/{len(targets)}] **{name}** — "
                            f"{len(session_plans.get(name, []))} row(s)"
                            + (f", {applied_n} applied" if applied_n else "")
                        )
                        if transcript:
                            self.log_info(
                                f"\n---\n### {name}\n```\n{transcript}\n```"
                            )
                        if apply_error:
                            self.log_failure(
                                f"**{name}** — apply failed: "
                                f"{labels.summarize_ssh_error(apply_error)}"
                            )

            if mode == "apply" and not applying:
                would = [p for p in plans if p.commands]
                for name in sorted({p.ssh_device or p.device for p in would}):
                    cmds = [
                        c for p in would
                        if (p.ssh_device or p.device) == name
                        for c in p.commands
                    ]
                    self.log_info(
                        f"\n---\n### Would apply on {name}\n```\n"
                        + "\n".join(cmds)
                        + "\n```"
                    )
                self.log_success(
                    f"Preview only — {len(would)} port(s) would be pushed. "
                    "Tick **Commit changes** to apply."
                )

            self._report(plans, preview_only=False)
            elapsed = int(time.time() - started)
            blocking = [p for p in plans if p.blocking]
            applied_n = sum(1 for p in plans if p.status == "applied")
            if applying and not blocking:
                self.log_success(
                    f"Applied {applied_n} port(s) ({elapsed}s). "
                    "NetBox Interface.enabled was not changed."
                )
            elif blocking:
                self.log_warning(
                    f"{len(blocking)} row(s) error/unreachable out of "
                    f"{len(plans)} ({elapsed}s)."
                )
            else:
                self.log_success(f"Done: {len(plans)} row(s) ({elapsed}s).")
            return plans_to_csv(plans)

        def _devices_named(self, names: set[str]) -> dict:
            if not names:
                return {}
            qs = Device.objects.filter(
                name__in=list(names),
                status=DeviceStatusChoices.STATUS_ACTIVE,
            ).select_related(
                "platform", "site", "role",
                "device_type", "device_type__manufacturer",
                "primary_ip4", "primary_ip6", "oob_ip",
                "virtual_chassis", "virtual_chassis__master",
            )
            return {d.name: d for d in qs}

        def _expand_exos_stack_members(self, devices: list) -> tuple[list, list[str]]:
            labels = epl()
            by_pk = {d.pk: d for d in devices if getattr(d, "pk", None) is not None}
            extra_names: list[str] = []
            seen_vc: set = set()
            seen_stem: set = set()
            related = (
                "platform", "site", "role",
                "device_type", "device_type__manufacturer",
                "primary_ip4", "primary_ip6", "oob_ip",
                "virtual_chassis", "virtual_chassis__master",
            )

            def _add(peer) -> None:
                pk = getattr(peer, "pk", None)
                if pk is None or pk in by_pk:
                    return
                kind = labels.platform_kind(
                    getattr(getattr(peer, "platform", None), "name", None),
                    getattr(getattr(peer, "platform", None), "slug", None),
                )
                if kind != "exos":
                    return
                by_pk[pk] = peer
                extra_names.append(peer.name)

            for device in list(devices):
                kind = labels.platform_kind(
                    getattr(getattr(device, "platform", None), "name", None),
                    getattr(getattr(device, "platform", None), "slug", None),
                )
                if kind != "exos":
                    continue
                vc = getattr(device, "virtual_chassis", None)
                vc_id = getattr(vc, "pk", None) if vc is not None else None
                if vc_id is not None:
                    if vc_id in seen_vc:
                        continue
                    seen_vc.add(vc_id)
                    for peer in Device.objects.filter(
                        virtual_chassis_id=vc_id,
                        status=DeviceStatusChoices.STATUS_ACTIVE,
                    ).select_related(*related):
                        _add(peer)
                    continue
                parsed = labels.parse_exos_stack_hostname(device.name or "")
                if not parsed:
                    continue
                stem, _slot = parsed
                site_id = getattr(getattr(device, "site", None), "pk", None)
                key = (site_id, stem)
                if key in seen_stem:
                    continue
                seen_stem.add(key)
                names = [f"{stem}-{i}" for i in range(1, 9)]
                qs = Device.objects.filter(
                    name__in=names,
                    status=DeviceStatusChoices.STATUS_ACTIVE,
                ).select_related(*related)
                if site_id is not None:
                    qs = qs.filter(site_id=site_id)
                for peer in qs:
                    _add(peer)
            extra_names.sort()
            return sorted(by_pk.values(), key=lambda d: d.name or ""), extra_names

        def _stack_member_info(self, device) -> dict:
            labels = epl()
            vc = getattr(device, "virtual_chassis", None)
            master = getattr(vc, "master", None) if vc is not None else None
            master_pk = getattr(master, "pk", None)
            return {
                "device": device,
                "name": device.name,
                "ip": labels._device_ssh_ip(device),
                "master": (
                    master_pk is not None
                    and getattr(device, "pk", None) == master_pk
                ),
                "position": getattr(device, "vc_position", None),
                "kind": labels.platform_kind(
                    getattr(getattr(device, "platform", None), "name", None),
                    getattr(getattr(device, "platform", None), "slug", None),
                ),
                "site": getattr(getattr(device, "site", None), "slug", "") or "",
                "vc_id": getattr(vc, "pk", None) if vc is not None else None,
            }

        def _group_ssh_sessions(self, device_list: list) -> list[tuple]:
            labels = epl()
            groups: dict[str, list[dict]] = {}
            for device in device_list:
                info = self._stack_member_info(device)
                if info["kind"] is None:
                    continue
                key = labels.exos_stack_session_key(
                    name=info["name"],
                    site=info["site"],
                    vc_id=info["vc_id"],
                    kind=info["kind"],
                )
                groups.setdefault(key, []).append(info)
            sessions = []
            for members in groups.values():
                picked = labels.pick_exos_stack_ssh_member(members)
                ssh_device = picked["device"] if picked else None
                ip = picked["ip"] if picked else None
                kind = members[0]["kind"]
                sessions.append((ssh_device, ip, kind, members))
            return sessions

        def _iface_index(self, devices: list) -> dict[str, list]:
            labels = epl()
            index: dict[str, list] = {}
            if not devices:
                return index
            pks = [d.pk for d in devices if getattr(d, "pk", None) is not None]
            qs = Interface.objects.filter(device_id__in=pks).select_related("device")
            if any(f.name == "_path" for f in Interface._meta.get_fields()):
                qs = qs.select_related("_path")
            for iface in qs:
                key = labels.canonical_port_key(iface.name or "")
                index.setdefault(key, []).append(iface)
                for alias in labels.port_key_aliases(iface.name or ""):
                    index.setdefault(alias, []).append(iface)
            return index

        def _pick_iface(self, index: dict, members: list, port: str):
            labels = epl()
            wanted = labels.port_key_aliases(port) | {labels.canonical_port_key(port)}
            hits = []
            seen: set[int] = set()
            for key in wanted:
                for iface in index.get(key, []):
                    pk = getattr(iface, "pk", None)
                    if pk in seen:
                        continue
                    if pk is not None:
                        seen.add(pk)
                    hits.append(iface)
            if not hits:
                return None, None
            member_names = {m["name"] for m in members} if members else set()
            if member_names:
                scoped = [
                    iface for iface in hits
                    if getattr(getattr(iface, "device", None), "name", "") in member_names
                ]
                if scoped:
                    hits = scoped
            slot = labels.ifname_stack_slot(port)
            if slot:
                for iface in hits:
                    parsed = labels.parse_exos_stack_hostname(
                        getattr(getattr(iface, "device", None), "name", "") or ""
                    )
                    if parsed and parsed[1] == slot:
                        return getattr(iface, "device", None), iface
            iface = hits[0]
            return getattr(iface, "device", None), iface

        def _session_device(
            self, name, ip, kind, plans, apply, save_config, allow_cabled,
        ):
            labels = epl()
            try:
                from django.db import close_old_connections
                close_old_connections()
            except Exception:  # noqa: BLE001
                pass
            nc = None
            transcript = ""
            try:
                nc = labels._connect(name, ip, kind)
                live_map, descriptions = labels._fetch_live_labels(nc, kind)
                for plan in plans:
                    if plan.status in {"skip", "error"}:
                        continue
                    plan.live = labels.lookup_live_label(live_map, plan.ifname)
                    plan.description_string = labels.lookup_live_label(
                        descriptions, plan.ifname,
                    )
                    decide_mute(plan, allow_cabled=allow_cabled, live_known=True)
                if apply:
                    ok, transcript, err = apply_mute_on_session(
                        nc, kind, plans, save_config,
                    )
                    if err:
                        return None, err, transcript
                else:
                    lines = []
                    for plan in plans:
                        for cmd in plan.commands:
                            lines.append(f"> {cmd}")
                    transcript = "\n".join(lines)
                return None, None, transcript
            except Exception as exc:  # noqa: BLE001
                logger.error("[%s] SSH session failed: %s", name, exc)
                err = labels.redact_error(str(exc))
                for plan in plans:
                    if plan.status == "planned":
                        plan.status = "unreachable"
                        plan.commands = []
                        plan.detail = labels.summarize_ssh_error(err)
                return err, None, transcript
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

        def _report(self, plans: list[MutePlan], preview_only: bool):
            counts: dict[str, int] = {}
            for plan in plans:
                counts[plan.status] = counts.get(plan.status, 0) + 1
            summary = " · ".join(f"**{k}** {v}" for k, v in sorted(counts.items()))
            self.log_info(
                f"\n---\n## Summary\n{summary or '_nothing evaluated_'}\n\n"
                "Full sheet is the **CSV in the Output tab**. "
                "This script does **not** write NetBox `Interface.enabled` — "
                "admin-down there separately if you want NetBox to match the box.\n"
            )
            rows = [
                [
                    _cell(p.device), _cell(p.ifname), _cell(p.kind),
                    _cell(p.action), _cell(p.status),
                    f"`{_cell(p.live) or '—'}`",
                    f"`{_cell(p.new_label) or '—'}`",
                    _cell(p.detail),
                ]
                for p in sorted(plans, key=lambda x: (x.device, x.ifname))
            ]
            table = markdown_table(
                ["Device", "Port", "Kind", "Action", "Status", "Live", "New", "Detail"],
                rows,
            )
            if table:
                self.log_info("\n### Allowlist rows\n\n" + table)
            cmds = [p for p in plans if p.commands]
            if cmds and preview_only:
                lines = [c for p in cmds for c in p.commands]
                self.log_info(
                    "\n### Commands (preview, no SSH)\n```\n"
                    + "\n".join(lines)
                    + "\n```"
                )
