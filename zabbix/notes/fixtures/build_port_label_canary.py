#!/usr/bin/env python3
"""Compile ``port_label_canary.tsv`` from the fleet row modules.

The ``expected_label`` / ``len`` / ``headroom`` columns are the *old* generator
(5-char SPEED slot). Tests recompute; those columns are the regression baseline.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "port_label_canary.tsv"

HEADER = [
    "canary_key",
    "iftype",
    "netbox_description",
    "far_device",
    "far_port",
    "far_role",
    "far_site",
    "far_is_mgmt",
    "link_mbps",
    "class",
    "expected_label",
    "len",
    "headroom",
    "status",
]


def _bool(value: bool) -> str:
    return "TRUE" if value else "FALSE"


def _mbps(value) -> str:
    if value is None or value == "":
        return ""
    return str(int(value))


def emit_row(row: tuple) -> list[str]:
    key, ift, desc, far, port, role, site, mgmt, mbps, cls, old = row
    old = old or ""
    length = str(len(old)) if old else ""
    headroom = str(20 - len(old)) if old else ""
    return [
        key,
        ift,
        desc or "",
        far,
        port or "",
        role,
        site,
        _bool(bool(mgmt)),
        _mbps(mbps),
        cls,
        old,
        length,
        headroom,
        "ok",
    ]


def nkn_from_existing() -> list[tuple]:
    """NKN G08 in the current TSV is the complete site; keep it as-is."""
    rows = []
    with OUT.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle, delimiter="\t"):
            if not raw["canary_key"].startswith("CH-NKN-"):
                continue
            mgmt = raw["far_is_mgmt"].strip().upper() in {"TRUE", "1", "YES"}
            mbps = raw["link_mbps"].strip()
            rows.append(
                (
                    raw["canary_key"].strip(),
                    raw["iftype"].strip(),
                    raw.get("netbox_description") or "",
                    raw["far_device"].strip(),
                    raw.get("far_port") or "",
                    raw["far_role"].strip(),
                    raw["far_site"].strip(),
                    mgmt,
                    int(float(mbps)) if mbps else None,
                    raw["class"].strip(),
                    raw.get("expected_label") or "",
                )
            )
    return rows


def main() -> int:
    # Imported here so ``python3 build_port_label_canary.py`` works from any cwd.
    sys.path.insert(0, str(HERE))
    from canary_fleet import extra_rows

    combined: dict[str, tuple] = {}
    for row in nkn_from_existing() + extra_rows():
        combined[row[0]] = row
    ordered = list(combined.values())
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(HEADER)
        for row in ordered:
            writer.writerow(emit_row(row))
    print(f"wrote {len(ordered)} rows -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
