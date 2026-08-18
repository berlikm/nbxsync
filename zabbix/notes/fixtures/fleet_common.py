"""Shared canary row helpers."""

from __future__ import annotations

import csv
import io


def parse_pipe(blob: str) -> list[tuple]:
    """``key|iftype|desc|far|port|role|site|Y/N|mbps|class|old_expected``."""
    rows: list[tuple] = []
    for line in blob.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) != 11:
            raise ValueError(f"{len(parts)} fields (want 11): {line[:120]}")
        mgmt = parts[7].strip().upper() in {"Y", "TRUE", "1", "YES"}
        mbps = parts[8].strip()
        rows.append(
            (
                parts[0].strip(),
                parts[1].strip(),
                parts[2],
                parts[3].strip(),
                parts[4],
                parts[5].strip(),
                parts[6].strip(),
                mgmt,
                int(float(mbps)) if mbps else None,
                parts[9].strip(),
                parts[10].strip(),
            )
        )
    return rows


def parse_user_tsv(blob: str) -> list[tuple]:
    """Parse the pasted canary export (tab-separated, 14 columns)."""
    rows: list[tuple] = []
    reader = csv.reader(io.StringIO(blob.strip() + "\n"), delimiter="\t")
    for parts in reader:
        if not parts or parts[0].startswith("canary_key"):
            continue
        if len(parts) < 11:
            raise ValueError(f"{len(parts)} columns: {parts[:6]!r}")
        while len(parts) < 14:
            parts.append("")
        mbps = (parts[8] or "").strip()
        mgmt = (parts[7] or "").strip().upper() in {"TRUE", "1", "YES"}
        rows.append(
            (
                parts[0].strip(),
                (parts[1] or "").strip(),
                parts[2] or "",
                parts[3].strip(),
                parts[4] or "",
                parts[5].strip(),
                parts[6].strip(),
                mgmt,
                int(float(mbps)) if mbps else None,
                parts[9].strip(),
                (parts[10] or "").strip(),
            )
        )
    return rows
