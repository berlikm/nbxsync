#!/usr/bin/env python3
"""Pure-helper tests for extreme_port_labels.py (no NetBox, no SSH)."""

from __future__ import annotations

import unittest
from dataclasses import replace

import extreme_port_labels as e


class ClassifyTests(unittest.TestCase):
    def test_switch_and_firewall_are_usw(self):
        self.assertEqual(e.classify("Switch Dist", 10000, "29"), "USW")
        self.assertEqual(e.classify("Firewall", 10000, "x1"), "USW")
        self.assertEqual(e.classify("Firewall", 1000, "ha"), "USW")

    def test_server_storage_are_us_even_at_1g(self):
        self.assertEqual(e.classify("Server", 1000, "eth0"), "US")
        self.assertEqual(e.classify("Storage", 25000, "ct0.eth10"), "US")
        self.assertEqual(e.classify("Cohesity", 10000, "eth0"), "US")

    def test_idrac_is_mon(self):
        self.assertEqual(e.classify("Server", 1000, "iDRAC", True), "MON")
        self.assertEqual(e.classify("Server", 1000, "idrac"), "MON")

    def test_ap_and_sdwan(self):
        self.assertEqual(e.classify("Access Point", 2500, "eth0"), "UP")
        self.assertEqual(e.classify("Sd Wan Socket", 1000, "wan1"), "UW")


class LabelUniquenessTests(unittest.TestCase):
    def _label(self, cls, mbps, name, fsite, lsite, port, role):
        parts = e.split_device_name(name, fsite, lsite)
        code = e.role_code(role)
        if code:
            parts = replace(parts, code=code)
        return e.build_label_for_far_end(cls, mbps, parts, port)

    def test_two_dist01_same_far_port_keep_building_scope(self):
        a = self._label("USW", 10000, "CH-STA-L50-B01-DIST01", "ch-sta-l50", "ch-sta-l50", "29", "Switch Dist")
        b = self._label("USW", 10000, "CH-STA-L50-L01-DIST01", "ch-sta-l50", "ch-sta-l50", "29", "Switch Dist")
        self.assertNotEqual(a, b, f"{a} vs {b}")
        self.assertIn("B01", a)
        self.assertIn("L01", b)
        self.assertLessEqual(len(a), 20)
        self.assertLessEqual(len(b), 20)

    def test_cross_site_keeps_site_tail(self):
        lab = self._label("USW", 10000, "CH-ZRH-ZH5-CORE01", "ch-zrh-zh5", "ch-zrh-zh4", "46", "Switch Core")
        self.assertIn("ZH5", lab)
        self.assertLessEqual(len(lab), 20)

    def test_firewall_is_usw_not_us(self):
        lab = self._label("USW", 10000, "CH-ZRH-ZH4-FWGW01", "ch-zrh-zh4", "ch-zrh-zh4", "x1", "Firewall")
        self.assertTrue(lab.startswith("USW-"), lab)

    def test_pure_25g_keeps_us_and_speed_token(self):
        lab = self._label("US", 25000, "ch-zrh-zh4-san02", "ch-zrh-zh4", "ch-zrh-zh4", "ct0.eth10", "Storage")
        self.assertTrue(lab.startswith("US-25G-"), lab)
        self.assertLessEqual(len(lab), 20)

    def test_uw_never_gets_a_speed_token(self):
        parts = e.DeviceNameParts("", "ISP", "", "")
        lab = e.build_label_for_far_end("UW", 1000, parts, "NETRICS")
        self.assertTrue(lab.startswith("UW-"), lab)
        self.assertNotIn("1G", lab)


class ParserTests(unittest.TestCase):
    def test_exos_range_expands(self):
        text = "configure ports 1:1-1:3 display-string FOO\n"
        display, _ = e.parse_exos_labels(text)
        self.assertEqual(display["1:1"], "FOO")
        self.assertEqual(display["1:3"], "FOO")

    def test_lookup_colon_vs_slash(self):
        labels = {"1/24": "USW-DI01_P29"}
        self.assertEqual(e.lookup_live_label(labels, "1:24"), "USW-DI01_P29")
        self.assertEqual(e.lookup_live_label(labels, "1.24"), "USW-DI01_P29")


class MgmtHeuristicTests(unittest.TestCase):
    def test_missing_primary_ip_is_not_mgmt(self):
        class _Iface:
            mgmt_only = False
            name = "ct0.eth10"
            device = type("D", (), {"oob_ip": None, "primary_ip": None})()

        self.assertFalse(e._is_management_interface(_Iface()))

    def test_idrac_name_is_mgmt(self):
        class _Iface:
            mgmt_only = False
            name = "iDRAC"
            device = type("D", (), {"oob_ip": None})()

        self.assertTrue(e._is_management_interface(_Iface()))


if __name__ == "__main__":
    unittest.main()
