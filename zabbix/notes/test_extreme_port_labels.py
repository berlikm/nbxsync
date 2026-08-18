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

    def test_nkn_gfl_1g_dist_to_access_keeps_floor(self):
        """Canary Dist::23 → GFL-ACCE01. Floor must stay (GFL vs L02)."""
        lab = self._label(
            "USW", 1000, "CH-NKN-G08-GFL-ACCE01",
            "ch-nkn-g08", "ch-nkn-g08", "23", "Switch Access",
        )
        self.assertEqual(lab, "USW-1G-GFL-AC01_P23")
        self.assertLessEqual(len(lab), 20)

    def test_nkn_gfl_vs_l02_access_do_not_collide_on_core(self):
        """Core sees both GFL-ACCE01 and L02-ACCE01 on port 23."""
        gfl = self._label(
            "USW", 1000, "CH-NKN-G08-GFL-ACCE01",
            "ch-nkn-g08", "ch-nkn-g08", "23", "Switch Access",
        )
        l02 = self._label(
            "USW", 1000, "CH-NKN-G08-L02-ACCE01",
            "ch-nkn-g08", "ch-nkn-g08", "23", "Switch Access",
        )
        self.assertEqual(gfl, "USW-1G-GFL-AC01_P23")
        self.assertEqual(l02, "USW-1G-L02-AC01_P23")
        self.assertNotEqual(gfl, l02)

    def test_nkn_gfl_ap_keeps_floor_without_far_port(self):
        lab = self._label(
            "UP", 1000, "CH-NKN-G08-GFL-ACPO01",
            "ch-nkn-g08", "ch-nkn-g08", "", "Access Point",
        )
        self.assertEqual(lab, "UP-GFL-AP01")

    def test_nkn_gfl_1g_access_to_dist_keeps_floor(self):
        lab = self._label(
            "USW", 1000, "CH-NKN-G08-GFL-DIST01",
            "ch-nkn-g08", "ch-nkn-g08", "1", "Switch Dist",
        )
        self.assertEqual(lab, "USW-1G-GFL-DI01_P1")

    def test_nkn_dist_to_core_keeps_floor_and_port_by_dropping_stack(self):
        """USW-1G-L02-CO01-1_P1.1 is 22. Drop stack; VOSS slot 01: vs 02: remains."""
        lab = self._label(
            "USW", 1000, "CH-NKN-G08-L02-CORE01-1",
            "ch-nkn-g08", "ch-nkn-g08", "01:01", "Switch Core",
        )
        self.assertEqual(lab, "USW-1G-L02-CO01_P1.1")
        self.assertLessEqual(len(lab), 20)

    def test_leading_zeros_on_voss_port_match_unpadded(self):
        a = self._label(
            "USW", 1000, "CH-NKN-G08-L02-CORE01-1",
            "ch-nkn-g08", "ch-nkn-g08", "01:05", "Switch Core",
        )
        b = self._label(
            "USW", 1000, "CH-NKN-G08-L02-CORE01-1",
            "ch-nkn-g08", "ch-nkn-g08", "1:5", "Switch Core",
        )
        self.assertEqual(a, b)
        self.assertEqual(a, "USW-1G-L02-CO01_P1.5")

    def test_szx_1g_access_to_stacked_core_keeps_floor_and_concat_port(self):
        """USW-1G-L17-CO01-1_P1.48 is 22; drop-stack dotted is 21. Concat port."""
        a = self._label(
            "USW", 1000, "CN-SZX-ECP-L17-CORE01-1",
            "cn-szx-ecp", "cn-szx-ecp", "01:48", "Switch Core",
        )
        b = self._label(
            "USW", 1000, "CN-SZX-ECP-L17-CORE01-2",
            "cn-szx-ecp", "cn-szx-ecp", "02:48", "Switch Core",
        )
        self.assertEqual(a, "USW-1G-L17-CO01_P148")
        self.assertEqual(b, "USW-1G-L17-CO01_P248")
        self.assertLessEqual(len(a), 20)

    def test_l50_1g_mgmt_slotted_ports_keep_floor(self):
        """USW-1G-L01-MG01_P1.20 is 21. Concatenate so 1:20 and 1:21 differ."""
        a = self._label(
            "USW", 1000, "CH-STA-L50-L01-MGMT01",
            "ch-sta-l50", "ch-sta-l50", "1:20", "Switch Mgmt",
        )
        b = self._label(
            "USW", 1000, "CH-STA-L50-L01-MGMT01",
            "ch-sta-l50", "ch-sta-l50", "1:21", "Switch Mgmt",
        )
        self.assertEqual(a, "USW-1G-L01-MG01_P120")
        self.assertEqual(b, "USW-1G-L01-MG01_P121")
        self.assertNotEqual(a, b)

    def test_jp_core_without_numeric_keeps_floor_by_dropping_stack(self):
        """CORE-1 has no index; USW-1G-L06-CO-1_P1.48 is 21."""
        lab = self._label(
            "USW", 1000, "JP-YOK-CHO-L06-CORE-1",
            "jp-yok-cho", "jp-yok-cho", "01:48", "Switch Core",
        )
        self.assertEqual(lab, "USW-1G-L06-CO_P1.48")
        self.assertLessEqual(len(lab), 20)

    def test_l44_gfl_and_b01_access_do_not_collide_on_dist(self):
        gfl = self._label(
            "USW", 1000, "CH-STA-L44-GFL-ACCE02",
            "ch-sta-l44", "ch-sta-l44", "24", "Switch Access",
        )
        b01 = self._label(
            "USW", 1000, "CH-STA-L44-B01-ACCE02",
            "ch-sta-l44", "ch-sta-l44", "24", "Switch Access",
        )
        self.assertEqual(gfl, "USW-1G-GFL-AC02_P24")
        self.assertEqual(b01, "USW-1G-B01-AC02_P24")

    def test_l50_core_dist_floors_stay_distinct(self):
        labels = [
            self._label("USW", 10000, name, "ch-sta-l50", "ch-sta-l50", port, "Switch Dist")
            for name, port in (
                ("CH-STA-L50-B01-DIST01", "29"),
                ("CH-STA-L50-GFL-DIST01", "29"),
                ("CH-STA-L50-L01-DIST01", "29"),
                ("CH-STA-L50-L02-DIST01", "54"),
            )
        ]
        self.assertEqual(labels, [
            "USW-B01-DI01_P29",
            "USW-GFL-DI01_P29",
            "USW-L01-DI01_P29",
            "USW-L02-DI01_P54",
        ])
        self.assertEqual(len(set(labels)), 4)

    def test_stacking_ports_keep_far_port(self):
        a = self._label(
            "USW", None, "CH-NKN-G08-L02-CORE01-2",
            "ch-nkn-g08", "ch-nkn-g08", "02:16", "Switch Core",
        )
        b = self._label(
            "USW", None, "CH-NKN-G08-L02-CORE01-2",
            "ch-nkn-g08", "ch-nkn-g08", "02:15", "Switch Core",
        )
        self.assertEqual(a, "USW-L02-CO01-2_P2.16")
        self.assertEqual(b, "USW-L02-CO01-2_P2.15")

    def test_san_eth10_and_eth2_stay_distinct(self):
        a = self._label(
            "US", 10000, "ch-zrh-zh4-san02",
            "ch-zrh-zh4", "ch-zrh-zh4", "ct0.eth10", "Storage",
        )
        b = self._label(
            "US", 10000, "ch-zrh-zh4-san02",
            "ch-zrh-zh4", "ch-zrh-zh4", "ct0.eth2", "Storage",
        )
        self.assertNotEqual(a, b)
        self.assertIn("ETH10", a)
        self.assertIn("ETH2", b)
        self.assertLessEqual(len(a), 20)
        self.assertLessEqual(len(b), 20)

    def test_hu_40g_isc_keeps_nag_scope(self):
        lab = self._label(
            "USW", 40000, "HU-DEB-NAG-CORE04",
            "hu-deb-nag-b", "hu-deb-nag-b", "25", "Switch Core",
        )
        self.assertEqual(lab, "USW-40G-NAG-CO04_P25")
        self.assertLessEqual(len(lab), 20)

    def test_cross_site_zh4_to_zh5_keeps_site_tail(self):
        lab = self._label(
            "USW", 10000, "CH-ZRH-ZH5-CORE01",
            "ch-zrh-zh5", "ch-zrh-zh4", "46", "Switch Core",
        )
        self.assertEqual(lab, "USW-ZH5-CO01_P46")

    def test_jiux_l3_firewall_keeps_l3_scope(self):
        lab = self._label(
            "USW", 1000, "CN-SHA-JIUX-L3-FWGW01",
            "cn-sha-jiu", "cn-sha-jiu", "port15", "Firewall",
        )
        self.assertEqual(lab, "USW-1G-L3-FW01_P15")

    def test_idrac_fits_and_stays_mon(self):
        lab = self._label(
            "MON", 1000, "ch-zrh-zh4-esx40.sensirion.lokal",
            "ch-zrh-zh4", "ch-zrh-zh4", "iDRAC 10 (NIC.1)", "Server",
        )
        self.assertTrue(lab.startswith("MON-ES40"), lab)
        self.assertLessEqual(len(lab), 20)

    def test_cohesity_ilo_uses_far_device_not_description(self):
        """Description says N07; the cable lands on n08."""
        lab = self._label(
            "MON", 1000, "lr50-san10-n08.sensirion.lokal",
            "ch-sta-l50", "ch-sta-l26",
            "Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)",
            "Cohesity",
        )
        self.assertEqual(lab, "MON-L50-CY08")


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
