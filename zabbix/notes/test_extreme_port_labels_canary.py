#!/usr/bin/env python3
"""Replay the fleet canary TSV through the real label builder.

The ``expected_label`` column is the *old* generator (5-char SPEED slot, floor
dropped). These tests recompute every row and assert the invariants that
must hold before remediation: length, grammar, CLASS, floor kept, no
per-device collisions.
"""

from __future__ import annotations

import unittest
from collections import defaultdict

import extreme_port_labels as e
import port_label_canary as canary


class ExcelPortRecoveryTests(unittest.TestCase):
    def test_us_month_day(self):
        self.assertEqual(canary.recover_excel_port("Jan 19"), "1:19")
        self.assertEqual(canary.recover_excel_port("Jan 7"), "1:7")

    def test_de_day_month(self):
        self.assertEqual(canary.recover_excel_port("01. Jul"), "1:7")
        self.assertEqual(canary.recover_excel_port("02. Jan"), "2:1")
        self.assertEqual(canary.recover_excel_port("02. Mär"), "2:3")
        self.assertEqual(canary.recover_excel_port("02. Feb"), "2:2")
        self.assertEqual(canary.recover_excel_port("02. Apr"), "2:4")

    def test_real_ports_untouched(self):
        self.assertEqual(canary.recover_excel_port("01:01"), "01:01")
        self.assertEqual(canary.recover_excel_port("1/24"), "1/24")
        self.assertEqual(canary.recover_excel_port("mgmt0"), "mgmt0")
        self.assertEqual(canary.recover_excel_port("ct0.eth10"), "ct0.eth10")


class FleetCanaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not canary.CANARY_TSV.exists():
            raise unittest.SkipTest(f"missing {canary.CANARY_TSV}")
        cls.rows = canary.load_canary()
        cls.sites = canary.device_site_map(cls.rows)
        cls.planned: list[tuple[canary.CanaryRow, str, str]] = []
        cls.too_long: list[tuple[canary.CanaryRow, str, str]] = []
        for row in cls.rows:
            local_site = canary.local_site_for(row, cls.sites)
            try:
                label = canary.replay(row, local_site)
            except e.LabelTooLong as exc:
                cls.too_long.append((row, local_site, str(exc)))
                continue
            cls.planned.append((row, local_site, label))

    def test_canary_is_populated(self):
        self.assertGreaterEqual(len(self.rows), 400, "canary TSV looks truncated")

    def test_every_label_fits_and_parses(self):
        failures = [
            f"{row.canary_key}: LabelTooLong {msg}"
            for row, _site, msg in self.too_long
        ]
        for row, _site, label in self.planned:
            if len(label) > e.MAX_LABEL_LEN:
                failures.append(f"{row.canary_key}: {label!r} len={len(label)}")
            if e.FORBIDDEN_CHARS & set(label) or "." in label:
                failures.append(f"{row.canary_key}: forbidden in {label!r}")
            if not e.is_safe_cli_label(label):
                failures.append(f"{row.canary_key}: unsafe CLI charset {label!r}")
            parsed = e.parse_label(label)
            if parsed is None:
                failures.append(f"{row.canary_key}: unparseable {label!r}")
        self.assertEqual(failures, [], "\n".join(failures[:40]))

    def test_class_matches_classify(self):
        failures = []
        for row, _site, label in self.planned:
            cls = e.classify(row.far_role, row.link_mbps, row.far_port, row.far_is_mgmt)
            if cls != row.canary_class:
                failures.append(
                    f"{row.canary_key}: classify={cls} canary={row.canary_class}"
                )
            parsed = e.parse_label(label)
            if parsed and parsed.cls != cls:
                failures.append(f"{row.canary_key}: label {label} cls {parsed.cls} != {cls}")
        self.assertEqual(failures, [], "\n".join(failures[:40]))

    def test_floor_kept_whenever_scope_exists(self):
        failures = []
        for row, local_site, label in self.planned:
            parts = canary.far_parts(row, local_site)
            if not parts.scope:
                continue
            parsed = e.parse_label(label)
            ident = parsed.ident if parsed else label
            token = parts.scope.upper()
            if not (ident.upper().startswith(token + "-") or ident.upper() == token):
                failures.append(
                    f"{row.canary_key}: scope {parts.scope} missing from {label} "
                    f"(far={row.far_device} port={row.far_port})"
                )
        self.assertEqual(failures, [], "\n".join(failures[:60]))

    def test_no_duplicate_labels_on_one_device(self):
        by_device: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        for row, _site, label in self.planned:
            by_device[row.local_device][label].append(row.canary_key)
        collisions = []
        for device, labels in sorted(by_device.items()):
            for label, keys in sorted(labels.items()):
                if len(keys) > 1:
                    collisions.append(f"{device}: {label} <- {keys}")
        self.assertEqual(collisions, [], "\n".join(collisions[:40]))

    def test_nkn_gfl_and_l02_access_differ_on_core(self):
        wanted = {
            "CH-NKN-G08-L02-CORE01-1::1:5": "USW-1G-L02-AC01_P23",
            "CH-NKN-G08-GFL-DIST01::1": "USW-1G-GFL-AC01_P23",
            "CH-NKN-G08-GFL-DIST01::23": "USW-1G-L02-CO01_P1_1",
        }
        got = {row.canary_key: label for row, _s, label in self.planned}
        missing = {key: wanted[key] for key in wanted if key not in got}
        self.assertFalse(missing, f"canary missing keys {missing}")
        failures = [f"{key}: got {got[key]} want {val}" for key, val in wanted.items() if got.get(key) != val]
        self.assertEqual(failures, [])
        core = got.get("CH-NKN-G08-L02-CORE01-1::1:5")
        # L02 access on Core must not be the floor-less USW-1G-AC01_P23.
        if core:
            self.assertIn("L02", core)

    def test_l26_core_dist_floors_do_not_collide(self):
        got = {
            row.canary_key: label
            for row, _s, label in self.planned
            if row.local_device == "CH-STA-L26-L02-CORE01"
            and "DIST" in row.far_device
        }
        if not got:
            self.skipTest("L26 core dist rows not in canary")
        labels = list(got.values())
        self.assertEqual(len(labels), len(set(labels)), got)
        for label in labels:
            self.assertRegex(label, r"USW-(GFL|L01|L02)-DI")

    def test_isc_and_stack_ports_are_usw_not_x(self):
        """Stack / ISC / MLAG peer-links are fabric. They must alert as USW."""
        failures = []
        seen = 0
        for row, _site, label in self.planned:
            desc = (row.netbox_description or "").upper()
            iftype = (row.iftype or "").lower()
            is_isc = "ISC" in desc
            is_stack = "summitstack" in iftype
            if not (is_isc or is_stack):
                continue
            seen += 1
            parsed = e.parse_label(label)
            if not parsed or parsed.cls != "USW" or label.startswith("X"):
                failures.append(
                    f"{row.canary_key}: {label!r} desc={row.netbox_description!r} "
                    f"iftype={row.iftype!r}"
                )
        self.assertGreater(seen, 20, "canary has no ISC/stack rows to check")
        self.assertEqual(failures, [], "\n".join(failures[:40]))


if __name__ == "__main__":
    unittest.main()
