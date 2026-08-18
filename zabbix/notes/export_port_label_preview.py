#!/usr/bin/env python3
"""Replay the fleet canary and write the current generator's labels.

Produces:
  fixtures/port_label_preview.tsv  — every cabled Extreme port, Excel-friendly
  port-label-preview.md            — counts and the rows a human should eyeball
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

import extreme_port_labels as e
import port_label_canary as canary

HERE = Path(__file__).resolve().parent
TSV = HERE / "fixtures" / "port_label_preview.tsv"
MD = HERE / "port-label-preview.md"

HEADER = [
    "site",
    "device",
    "port",
    "iftype",
    "netbox_description",
    "far_device",
    "far_port",
    "far_role",
    "class",
    "mbps",
    "expected",
    "len",
    "note",
]


def _site_of(device: str, local_site: str) -> str:
    return (local_site or "").upper() or device.split("-")[0]


def _note(row: canary.CanaryRow, label: str, error: str) -> str:
    bits = []
    if error:
        bits.append(error)
    desc = (row.netbox_description or "").upper()
    iftype = (row.iftype or "").lower()
    if "ISC" in desc:
        bits.append("ISC")
    if "summitstack" in iftype:
        bits.append("stack")
    if "MLAG" in desc:
        bits.append("MLAG")
    if label and "_" in label.split("-")[-1] and any(
        ch.isdigit() for ch in label.split("_P")[-1]
    ) and "." not in label:
        token = e.normalize_port_token(row.far_port)
        if token and token[0].isdigit() and "_" in token:
            compact = token.replace("_", "")
            if label.endswith(f"_P{compact}") and f"_P{token}" not in label:
                bits.append("concat-port")
    if label and len(label) == e.MAX_LABEL_LEN:
        bits.append("at-20")
    if "." in (label or ""):
        bits.append("HAS-DOT")
    return ",".join(bits)


def replay_all() -> tuple[list[dict[str, str]], list[str]]:
    rows = canary.load_canary()
    sites = canary.device_site_map(rows)
    out: list[dict[str, str]] = []
    errors: list[str] = []
    for row in rows:
        local_site = canary.local_site_for(row, sites)
        label = ""
        err = ""
        try:
            label = canary.replay(row, local_site)
        except e.LabelTooLong as exc:
            err = "too_long"
            errors.append(f"{row.canary_key}: {exc}")
        rec = {
            "site": _site_of(row.local_device, local_site),
            "device": row.local_device,
            "port": row.local_port,
            "iftype": row.iftype,
            "netbox_description": row.netbox_description,
            "far_device": row.far_device,
            "far_port": row.far_port,
            "far_role": row.far_role,
            "class": (e.parse_label(label).cls if label else row.canary_class),
            "mbps": "" if row.link_mbps is None else str(row.link_mbps),
            "expected": label,
            "len": str(len(label)) if label else "",
            "note": _note(row, label, err),
        }
        out.append(rec)
    return out, errors


def write_tsv(records: list[dict[str, str]]) -> None:
    TSV.parent.mkdir(parents=True, exist_ok=True)
    with TSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def write_markdown(records: list[dict[str, str]], errors: list[str]) -> None:
    by_class = Counter(r["class"] for r in records)
    by_site = Counter(r["site"] for r in records)
    notes = Counter(
        bit for r in records for bit in (r["note"].split(",") if r["note"] else [])
        if bit
    )
    at_20 = [r for r in records if r["len"] == "20"]
    concat = [r for r in records if "concat-port" in r["note"]]
    isc = [r for r in records if "ISC" in r["note"]]
    stack = [r for r in records if "stack" in r["note"]]
    dots = [r for r in records if "HAS-DOT" in r["note"]]
    collisions: dict[tuple[str, str], list[str]] = defaultdict(list)
    for rec in records:
        if rec["expected"]:
            collisions[(rec["device"], rec["expected"])].append(rec["port"])
    collided = {k: v for k, v in collisions.items() if len(v) > 1}

    def _sample(rows: list[dict[str, str]], limit: int = 40) -> str:
        body = [
            [r["device"], r["port"], r["far_device"], r["far_port"], f"`{r['expected']}`", r["len"], r["note"]]
            for r in rows[:limit]
        ]
        table = _md_table(
            ["Device", "Port", "Far device", "Far port", "Expected", "Len", "Note"],
            body,
        )
        extra = ""
        if len(rows) > limit:
            extra = f"\n\n_{len(rows) - limit} more in `{TSV.name}`._"
        return table + extra

    zh4_core = [r for r in records if r["device"] == "CH-ZRH-ZH4-CORE01"]
    nkn_core = [r for r in records if r["device"] == "CH-NKN-G08-L02-CORE01-1"]

    lines = [
        "# Port-label preview (current generator)",
        "",
        "What `extreme_port_labels.py` will write on the box, replayed from the",
        f"fleet canary (**{len(records)}** cabled Extreme ports). Full sheet:",
        f"[`fixtures/{TSV.name}`](fixtures/{TSV.name}) — open in Excel, filter by site / CLASS / note.",
        "",
        "This is **plan-only** (NetBox cabling → expected `ifAlias`). It is not a",
        "live vs expected compliance diff.",
        "",
        "## Counts",
        "",
        f"- Ports: **{len(records)}**",
        f"- Devices: **{len({r['device'] for r in records})}**",
        f"- Sites: **{len(by_site)}**",
        f"- Too long: **{len(errors)}**",
        f"- Labels with `.`: **{len(dots)}** (must be 0)",
        f"- Duplicate label on the same device: **{len(collided)}** (must be 0)",
        f"- Exactly 20 characters: **{len(at_20)}**",
        f"- Concatenated slot+port (`_P120` style): **{len(concat)}**",
        f"- ISC (from NetBox description): **{len(isc)}** — all must be `USW`",
        f"- Stack (`extreme-summitstack`): **{len(stack)}** — all must be `USW`",
        "",
        "### CLASS",
        "",
        _md_table(["CLASS", "Count"], [[cls, str(by_class[cls])] for cls in sorted(by_class)]),
        "",
        "### Site",
        "",
        _md_table(
            ["Site", "Ports"],
            [[site, str(by_site[site])] for site, _ in by_site.most_common()],
        ),
        "",
        "## Eyeball these first",
        "",
        "### ISC (keep `USW`, do not mute)",
        "",
        _sample(isc, 30),
        "",
        "### Stacking ports (keep `USW`)",
        "",
        _sample(stack, 30),
        "",
        "### Concatenated far port (1:20 → `_P120`)",
        "",
        _sample(concat, 25),
        "",
        "### Full 20-character labels (budget, not truncated)",
        "",
        _sample(at_20, 40),
        "",
        "## Sample devices",
        "",
        "### `CH-ZRH-ZH4-CORE01` (ISC + servers + SAN + firewall)",
        "",
        _sample(zh4_core, 50),
        "",
        "### `CH-NKN-G08-L02-CORE01-1` (floor kept on 1G, stack USW)",
        "",
        _sample(nkn_core, 40),
        "",
    ]
    if errors:
        lines += ["## Too long", "", "```", *errors, "```", ""]
    if collided:
        lines += ["## Collisions (must be empty)", ""]
        for (device, label), ports in sorted(collided.items())[:40]:
            lines.append(f"- `{device}` `{label}` ← {ports}")
        lines.append("")
    if notes:
        lines += [
            "## Note tags in the TSV",
            "",
            _md_table(["Note", "Count"], [[k, str(v)] for k, v in notes.most_common()]),
            "",
        ]
    MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    records, errors = replay_all()
    write_tsv(records)
    write_markdown(records, errors)
    print(f"wrote {TSV} ({len(records)} rows)")
    print(f"wrote {MD}")
    if errors:
        print(f"{len(errors)} too-long")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
