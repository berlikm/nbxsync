"""Replay a NetBox port-label canary TSV through ``plan_label``.

The canary is an export of every cabled Extreme port. Excel corrupts some
VOSS ``1/19`` far-port values into dates (``Jan 19``, ``01. Jul``, ``02. Mär``);
those are recovered here so the tests match NetBox, not the spreadsheet.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, replace
from pathlib import Path

import extreme_port_labels as e

CANARY_TSV = Path(__file__).resolve().parent / "fixtures" / "port_label_canary.tsv"

_MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "MÄR": 3,
    "APR": 4,
    "MAY": 5,
    "MAI": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "OKT": 10,
    "NOV": 11,
    "DEC": 12,
    "DEZ": 12,
}

_US_DATE = re.compile(r"^([A-Za-zÄäÖöÜü]{3,})\s+(\d{1,2})$")
_DE_DATE = re.compile(r"^(\d{1,2})\.\s*([A-Za-zÄäÖöÜü]{3,})\.?$")


def _month(token: str) -> int | None:
    upper = token.upper()
    if upper.startswith("MÄR") or upper.startswith("MAR"):
        return 3
    return _MONTHS.get(upper[:3])


def recover_excel_port(far_port: str) -> str:
    """Undo Excel date coercion of ``1/19`` / ``1:7`` / ``2/3``."""
    raw = (far_port or "").strip()
    if not raw:
        return raw
    match = _US_DATE.fullmatch(raw)
    if match:
        month = _month(match.group(1))
        if month:
            return f"{month}:{int(match.group(2))}"
    match = _DE_DATE.fullmatch(raw)
    if match:
        month = _month(match.group(2))
        if month:
            return f"{int(match.group(1))}:{month}"
    return raw


@dataclass(frozen=True)
class CanaryRow:
    canary_key: str
    iftype: str
    netbox_description: str
    far_device: str
    far_port: str
    far_role: str
    far_site: str
    far_is_mgmt: bool
    link_mbps: int | None
    canary_class: str
    old_expected: str

    @property
    def local_device(self) -> str:
        return self.canary_key.split("::", 1)[0]

    @property
    def local_port(self) -> str:
        return self.canary_key.split("::", 1)[1] if "::" in self.canary_key else ""


def _parse_bool(value: str) -> bool:
    return value.strip().upper() in {"TRUE", "1", "YES"}


def _parse_mbps(value: str) -> int | None:
    value = (value or "").strip()
    if not value:
        return None
    return int(float(value))


def load_canary(path: Path | None = None) -> list[CanaryRow]:
    target = path or CANARY_TSV
    with target.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = []
        for raw in reader:
            rows.append(
                CanaryRow(
                    canary_key=raw["canary_key"].strip(),
                    iftype=(raw.get("iftype") or "").strip(),
                    netbox_description=(raw.get("netbox_description") or "").strip(),
                    far_device=raw["far_device"].strip(),
                    far_port=recover_excel_port(raw.get("far_port") or ""),
                    far_role=raw["far_role"].strip(),
                    far_site=raw["far_site"].strip(),
                    far_is_mgmt=_parse_bool(raw.get("far_is_mgmt") or ""),
                    link_mbps=_parse_mbps(raw.get("link_mbps") or ""),
                    canary_class=raw["class"].strip(),
                    old_expected=(raw.get("expected_label") or "").strip(),
                )
            )
    return rows


def device_site_map(rows: list[CanaryRow]) -> dict[str, str]:
    """``far_device`` → ``far_site``; locals are looked up from the reverse cable."""
    mapping: dict[str, str] = {}
    for row in rows:
        key = row.far_device.upper().split(".")[0]
        mapping[key] = row.far_site
    return mapping


def local_site_for(row: CanaryRow, sites: dict[str, str]) -> str:
    key = row.local_device.upper().split(".")[0]
    if key in sites:
        return sites[key]
    name = row.local_device.upper()
    prefixes = [site for site in set(sites.values()) if name.startswith(site.upper() + "-")]
    if prefixes:
        return max(prefixes, key=len)
    return row.far_site


def far_parts(row: CanaryRow, local_site: str) -> e.DeviceNameParts:
    parts = e.split_device_name(row.far_device, row.far_site, local_site)
    code = e.role_code(row.far_role)
    if code:
        parts = replace(parts, code=code)
    return parts


def replay(row: CanaryRow, local_site: str) -> str:
    return e.plan_label(
        local_site=local_site,
        far_name=row.far_device,
        far_site=row.far_site,
        far_port=row.far_port,
        far_role=row.far_role,
        far_is_mgmt=row.far_is_mgmt,
        link_mbps=row.link_mbps,
        extra=row.netbox_description,
    )
