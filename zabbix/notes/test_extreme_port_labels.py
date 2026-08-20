#!/usr/bin/env python3
"""Pure-helper tests for extreme_port_labels.py (no NetBox, no SSH)."""

from __future__ import annotations

import os
import re
import sys
import tempfile
import textwrap
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
        self.assertEqual(e.classify("ESXi Hypervisor", 10000, "vmnic3"), "US")
        self.assertEqual(e.classify("ESXi Hypervisor", 1000, "iDRAC"), "MON")

    def test_idrac_is_mon(self):
        self.assertEqual(e.classify("Server", 1000, "iDRAC", True), "MON")
        self.assertEqual(e.classify("Server", 1000, "idrac"), "MON")

    def test_cohesity_embedded_nic_is_ilo_mon(self):
        """HPE inventory name NIC.Embedded is iLO on Cohesity, not a data NIC."""
        embedded = "Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)"
        self.assertEqual(
            e.classify("Cohesity", 1000, embedded, False), "MON",
        )
        self.assertEqual(
            e.classify("Cohesity", 1000, "eth0", False, extra="COH-N01-ILO"),
            "MON",
        )
        self.assertEqual(e.classify("Cohesity", 1000, "eth0", False), "US")
        self.assertEqual(e.classify("Server", 1000, embedded, False), "US")

    def test_ap_and_sdwan(self):
        self.assertEqual(e.classify("Access Point", 2500, "eth0"), "UP")
        self.assertEqual(e.classify("Sd Wan Socket", 1000, "wan1"), "UW")

    def test_unknown_role_is_mon_even_at_10g(self):
        """Speed does not pick CLASS. Server/storage are US; everything else is MON."""
        self.assertEqual(e.classify("Printer", 10000, "eth0"), "MON")
        self.assertEqual(e.classify("Camera", 1000, "eth0"), "MON")
        self.assertEqual(e.classify("Network Device", 40000, "1"), "MON")
        self.assertEqual(e.classify("Messpc", 10000, "eth0"), "MON")

    def test_unknown_10g_emits_mon_with_speed_token(self):
        self.assertEqual(e.build_label("MON", 10000, "PRN01"), "MON-10G-PRN01")
        self.assertEqual(e.build_label("US", 1000, "ES40_NIC0"), "US-1G-ES40_NIC0")

    def test_new_switch_role_is_usw_without_a_table_row(self):
        self.assertEqual(e.classify("Switch Spine", 40000, "1"), "USW")
        self.assertEqual(e.classify("Switch Leaf", 10000, "1"), "USW")
        self.assertEqual(e.role_code("Switch Spine"), "SP")
        self.assertEqual(e.role_code("Switch Leaf"), "LE")
        self.assertEqual(e.role_code("Switch Core"), "C")
        self.assertEqual(e.role_code("Switch Dist"), "D")
        self.assertEqual(e.role_code("Switch Access"), "A")
        self.assertEqual(e.role_code("Switch Mgmt"), "M")


class PlatformKindTests(unittest.TestCase):
    def test_exos_and_switch_engine(self):
        self.assertEqual(e.platform_kind("Extreme EXOS"), "exos")
        self.assertEqual(e.platform_kind("Switch Engine"), "exos")
        self.assertEqual(e.platform_kind(None, "switch-engine"), "exos")

    def test_voss_is_not_matched_as_exos_via_xos(self):
        """``XOS`` is a substring of ``VOSS`` — must not classify VOSS as EXOS."""
        self.assertEqual(e.platform_kind("VOSS"), "voss")
        self.assertEqual(e.platform_kind("Extreme VOSS"), "voss")

    def test_fabric_engine_and_vsp(self):
        self.assertEqual(e.platform_kind("Fabric Engine"), "voss")
        self.assertEqual(e.platform_kind(None, "fabric-engine"), "voss")
        self.assertEqual(e.platform_kind("VSP 8600"), "voss")
        self.assertEqual(e.platform_kind(None, "vsp-7400"), "voss")

    def test_normalize_choicevar_and_labels(self):
        self.assertEqual(e.normalize_platform_filter("voss"), "voss")
        self.assertEqual(e.normalize_platform_filter("VOSS only"), "voss")
        self.assertEqual(e.normalize_platform_filter(("voss", "VOSS only")), "voss")
        self.assertEqual(e.normalize_platform_filter(""), "both")
        self.assertEqual(e.normalize_platform_filter(None), "both")
        self.assertEqual(e.normalize_platform_filter("EXOS + VOSS"), "both")
        self.assertEqual(e.normalize_platform_filter("exos"), "exos")


class FutureProofTests(unittest.TestCase):
    """Rates / roles / ports that do not exist in the current estate."""

    def test_speed_token_from_mbps_not_a_closed_table(self):
        self.assertEqual(e.mbps_to_speed_token(2500), "2G5")
        self.assertEqual(e.mbps_to_speed_token(50000), "50G")
        self.assertEqual(e.mbps_to_speed_token(200000), "200G")
        self.assertEqual(e.mbps_to_speed_token(800000), "800G")
        self.assertEqual(e.mbps_to_speed_token(100), "100M")
        self.assertEqual(e.speed_token_to_mbps("50G"), 50000)
        self.assertEqual(e.speed_token_to_mbps("2G5"), 2500)

    def test_iftype_parses_future_ieee_slugs(self):
        self.assertEqual(e.iftype_to_mbps("50gbase-x"), 50000)
        self.assertEqual(e.iftype_to_mbps("200gbase-kr4"), 200000)
        self.assertEqual(e.iftype_to_mbps("800gbase-r"), 800000)
        self.assertEqual(e.iftype_to_mbps("2.5gbase-t"), 2500)

    def test_build_label_emits_50g_without_a_table_row(self):
        self.assertEqual(e.build_label("US", 50000, "SAN01_4"), "US-50G-SAN01_4")
        parsed = e.parse_label("US-50G-SAN01_4")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.speed_token, "50G")
        self.assertEqual(parsed.expected_mbps, 50000)

    def test_new_spine_hostname_shortens_like_core(self):
        """USW role-words not in FABRIC_CODE_SHORT still get 2 letters.

        ``USW-40G-L01-SP01_1_20`` is 21, so the ladder concatenates slot+port
        the same way it does for a tight M01 — ``_120`` — instead of dropping
        the floor.
        """
        lab = e.plan_label(
            local_site="ch-sta-l50",
            far_name="CH-STA-L50-L01-SPINE01",
            far_site="ch-sta-l50",
            far_port="1:20",
            far_role="Switch Spine",
            far_is_mgmt=False,
            link_mbps=40000,
        )
        self.assertEqual(lab, "USW-40G-L01-SP01_120")
        self.assertLessEqual(len(lab), 20)

    def test_endpoint_is_not_flattened_to_two_letters(self):
        lab = e.plan_label(
            local_site="ch-zrh-zh4",
            far_name="ch-zrh-zh4-snas01",
            far_site="ch-zrh-zh4",
            far_port="lan5",
            far_role="Storage",
            far_is_mgmt=False,
            link_mbps=10000,
        )
        self.assertIn("SNAS", lab)
        self.assertNotIn("SN01", lab)

    def test_voss_subport_is_a_safe_cli_port(self):
        self.assertTrue(e.is_safe_cli_port("1/1/1"))
        self.assertFalse(e.is_safe_cli_port("1:1-1:3"))
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
        self.assertEqual(lab, "USW-1G-GFL-A01_23")
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
        self.assertEqual(gfl, "USW-1G-GFL-A01_23")
        self.assertEqual(l02, "USW-1G-L02-A01_23")
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
        self.assertEqual(lab, "USW-1G-GFL-D01_1")

    def test_nkn_dist_to_core_keeps_stack_floor_and_port(self):
        """Slotted ``1:1`` *is* member 1. Hostname ``-1`` is not repeated."""
        lab = self._label(
            "USW", 1000, "CH-NKN-G08-L02-CORE01-1",
            "ch-nkn-g08", "ch-nkn-g08", "01:01", "Switch Core",
        )
        self.assertEqual(lab, "USW-1G-L02-C01_1_1")
        self.assertEqual(
            self._label(
                "USW", 40000, "CH-NKN-G08-L02-CORE01-1",
                "ch-nkn-g08", "ch-nkn-g08", "01:01", "Switch Core",
            ),
            "USW-40G-L02-C01_1_1",
        )
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
        self.assertEqual(a, "USW-1G-L02-C01_1_5")

    def test_szx_1g_access_to_stacked_core_keeps_floor_and_concat_port(self):
        """Dropping P frees the underscored slot+port; 40G still fits ``_1_48``."""
        a = self._label(
            "USW", 1000, "CN-SZX-ECP-L17-CORE01-1",
            "cn-szx-ecp", "cn-szx-ecp", "01:48", "Switch Core",
        )
        b = self._label(
            "USW", 1000, "CN-SZX-ECP-L17-CORE01-2",
            "cn-szx-ecp", "cn-szx-ecp", "02:48", "Switch Core",
        )
        self.assertEqual(a, "USW-1G-L17-C01_1_48")
        self.assertEqual(b, "USW-1G-L17-C01_2_48")
        self.assertEqual(
            self._label(
                "USW", 40000, "CN-SZX-ECP-L17-CORE01-1",
                "cn-szx-ecp", "cn-szx-ecp", "01:48", "Switch Core",
            ),
            "USW-40G-L17-C01_1_48",
        )
        self.assertLessEqual(len(a), 20)

    def test_l50_1g_mgmt_slotted_ports_keep_floor(self):
        """Without P, ``_1_20`` fits at 1G; 40G still keeps the underscore."""
        a = self._label(
            "USW", 1000, "CH-STA-L50-L01-MGMT01",
            "ch-sta-l50", "ch-sta-l50", "1:20", "Switch Mgmt",
        )
        b = self._label(
            "USW", 1000, "CH-STA-L50-L01-MGMT01",
            "ch-sta-l50", "ch-sta-l50", "1:21", "Switch Mgmt",
        )
        self.assertEqual(a, "USW-1G-L01-M01_1_20")
        self.assertEqual(b, "USW-1G-L01-M01_1_21")
        self.assertEqual(
            self._label(
                "USW", 40000, "CH-STA-L50-L01-MGMT01",
                "ch-sta-l50", "ch-sta-l50", "1:20", "Switch Mgmt",
            ),
            "USW-40G-L01-M01_1_20",
        )
        self.assertNotEqual(a, b)

    def test_jp_core_without_numeric_keeps_floor_by_dropping_stack(self):
        """CORE-1 has no index. Slot ``1:48`` already names member 1."""
        lab = self._label(
            "USW", 1000, "JP-YOK-CHO-L06-CORE-1",
            "jp-yok-cho", "jp-yok-cho", "01:48", "Switch Core",
        )
        self.assertEqual(lab, "USW-1G-L06-C_1_48")
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
        self.assertEqual(gfl, "USW-1G-GFL-A02_24")
        self.assertEqual(b01, "USW-1G-B01-A02_24")

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
            "USW-B01-D01_29",
            "USW-GFL-D01_29",
            "USW-L01-D01_29",
            "USW-L02-D01_54",
        ])
        self.assertEqual(len(set(labels)), 4)

    def test_stacking_ports_keep_far_port(self):
        """Member lives in ``_2_16``. Do not drop the far port (1:15 vs 1:16)."""
        a = self._label(
            "USW", None, "CH-NKN-G08-L02-CORE01-2",
            "ch-nkn-g08", "ch-nkn-g08", "02:16", "Switch Core",
        )
        b = self._label(
            "USW", None, "CH-NKN-G08-L02-CORE01-2",
            "ch-nkn-g08", "ch-nkn-g08", "02:15", "Switch Core",
        )
        self.assertEqual(a, "USW-L02-C01_2_16")
        self.assertEqual(b, "USW-L02-C01_2_15")

    def test_unslotted_port_keeps_hostname_stack(self):
        """``48`` does not encode member 2, so hostname ``-2`` stays."""
        lab = self._label(
            "USW", 10000, "CH-NKN-G08-L02-CORE01-2",
            "ch-nkn-g08", "ch-nkn-g08", "48", "Switch Core",
        )
        self.assertEqual(lab, "USW-L02-C01-2_48")

    def test_hostname_stack_kept_when_port_slot_differs(self):
        """Peer ``1:1`` on hostname ``-2`` is not member 2 — keep ``-2``."""
        lab = self._label(
            "USW", None, "CH-NKN-G08-L02-CORE01-2",
            "ch-nkn-g08", "ch-nkn-g08", "1:1", "Switch Core",
        )
        self.assertEqual(lab, "USW-L02-C01-2_1_1")

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
        self.assertEqual(a, "US-SAN02_CT0_10")
        self.assertEqual(b, "US-SAN02_CT0_2")
        self.assertEqual(
            self._label(
                "US", 40000, "ch-zrh-zh4-san02",
                "ch-zrh-zh4", "ch-zrh-zh4", "ct0.eth10", "Storage",
            ),
            "US-40G-SAN02_CT0_10",
        )
        self.assertLessEqual(len(a), 20)
        self.assertLessEqual(len(b), 20)

    def test_hu_40g_fits_without_spelling_core(self):
        lab = self._label(
            "USW", 40000, "HU-DEB-NAG-CORE04",
            "hu-deb-nag-b", "hu-deb-nag-b", "25", "Switch Core",
        )
        self.assertEqual(lab, "USW-40G-C04_25")
        self.assertNotIn("CORE", lab)
        self.assertLessEqual(len(lab), 20)

    def test_cross_site_zh4_to_zh5_keeps_site_tail(self):
        lab = self._label(
            "USW", 10000, "CH-ZRH-ZH5-CORE01",
            "ch-zrh-zh5", "ch-zrh-zh4", "46", "Switch Core",
        )
        self.assertEqual(lab, "USW-ZH5-C01_46")

    def test_jiux_l3_firewall_keeps_l3_scope(self):
        lab = self._label(
            "USW", 1000, "CN-SHA-JIUX-L3-FWGW01",
            "cn-sha-jiu", "cn-sha-jiu", "port15", "Firewall",
        )
        self.assertEqual(lab, "USW-1G-L3-FW01_15")

    def test_idrac_fits_and_stays_mon(self):
        lab = self._label(
            "MON", 1000, "ch-zrh-zh4-esx40.sensirion.lokal",
            "ch-zrh-zh4", "ch-zrh-zh4", "iDRAC 10 (NIC.1)", "Server",
        )
        self.assertEqual(lab, "MON-ESX40_ILO10_1")
        self.assertTrue(lab.startswith("MON-ESX40"), lab)
        self.assertIn("ILO", lab)
        self.assertNotIn("IDRAC", lab)
        self.assertLessEqual(len(lab), 20)

    def test_idrac_token_renders_as_ilo(self):
        self.assertEqual(e.normalize_port_token("iDRAC 10 (NIC.1)"), "ILO10_1")
        self.assertEqual(e.normalize_port_token("iDRAC 9 (NIC.1)"), "ILO9_1")
        self.assertEqual(e.normalize_port_token("iDRAC"), "ILO")
        self.assertEqual(e.normalize_port_token("vmnic1"), "NIC1")
        self.assertEqual(e.normalize_port_token("vmnic0"), "NIC0")
        self.assertEqual(e.normalize_port_token("mgmt"), "MG")
        self.assertEqual(e.normalize_port_token("CTE0.B.MGMT"), "CTE0_B_MG")
        lab = self._label(
            "MON", 1000, "cn-sha-p-esx13.sensirion.lokal",
            "cn-sha-jiu", "cn-sha-jiu", "iDRAC 9 (NIC.1)", "Server",
        )
        self.assertEqual(lab, "MON-P-ESX13_ILO9_1")
        self.assertNotIn("IDRAC", lab)

    def test_vmnic_renders_nic_so_1g_and_40g_fit(self):
        lab = self._label(
            "US", 1000, "hu-deb-p-esx13.sensirion.lokal",
            "hu-deb-nag-a", "hu-deb-nag-a", "vmnic0", "Server",
        )
        self.assertEqual(lab, "US-1G-P-ESX13_NIC0")
        self.assertLessEqual(len(lab), 20)
        self.assertEqual(
            self._label(
                "US", 40000, "hu-deb-p-esx13.sensirion.lokal",
                "hu-deb-nag-a", "hu-deb-nag-a", "vmnic0", "Server",
            ),
            "US-40G-P-ESX13_NIC0",
        )

    def test_san_cte_mgmt_shortens_to_mg_so_10g_fits(self):
        """``CTE0.B.MGMT`` used to concatenate to ``CTE0BMGMT`` (19)."""
        a = e.plan_label(
            local_site="hu-deb-nag-a",
            far_name="HU-DEB-SAN01",
            far_site="hu-deb-nag-a",
            far_port="CTE0.A.MGMT",
            far_role="Storage",
            far_is_mgmt=False,
            link_mbps=1000,
        )
        b = e.plan_label(
            local_site="hu-deb-nag-a",
            far_name="HU-DEB-SAN01",
            far_site="hu-deb-nag-a",
            far_port="CTE0.B.MGMT",
            far_role="Storage",
            far_is_mgmt=False,
            link_mbps=1000,
        )
        self.assertEqual(a, "MON-SAN01_CTE0_A_MG")
        self.assertEqual(b, "MON-SAN01_CTE0_B_MG")
        ten = e.plan_label(
            local_site="hu-deb-nag-a",
            far_name="HU-DEB-SAN01",
            far_site="hu-deb-nag-a",
            far_port="CTE0.B.MGMT",
            far_role="Storage",
            far_is_mgmt=False,
            link_mbps=10000,
        )
        self.assertEqual(ten, "MON-10G-SAN01_B_MG")
        self.assertLessEqual(len(ten), 20)
        self.assertNotEqual(a, b)
        ten_a = e.plan_label(
            local_site="hu-deb-nag-a",
            far_name="HU-DEB-SAN01",
            far_site="hu-deb-nag-a",
            far_port="CTE0.A.MGMT",
            far_role="Storage",
            far_is_mgmt=False,
            link_mbps=10000,
        )
        self.assertEqual(ten_a, "MON-10G-SAN01_A_MG")
        self.assertNotEqual(ten, ten_a)

    def test_firewall_mgmt_port_renders_mg(self):
        lab = self._label(
            "USW", 1000, "KR-SEL-HAN-L14-FWGW01",
            "kr-sel-han", "kr-sel-han", "mgmt", "Firewall",
        )
        self.assertEqual(lab, "USW-1G-L14-FW01_MG")
        self.assertEqual(
            self._label(
                "USW", 10000, "KR-SEL-HAN-L14-FWGW01",
                "kr-sel-han", "kr-sel-han", "mgmt", "Firewall",
            ),
            "USW-L14-FW01_MG",
        )

    def test_cohesity_room_prefix_dropped_same_site_and_cross_site(self):
        """``LR50`` is a lab room, not a floor. Drop it so 10G still fits."""
        for local in ("ch-sta-l26", "ch-sta-l50"):
            parts = e.split_device_name(
                "lr50-san10-n01.sensirion.lokal", "ch-sta-l50", local,
            )
            self.assertNotEqual(parts.scope, "LR50", parts)
            self.assertNotIn("LR50", parts.extra)
            self.assertEqual(parts.code, "N")
            self.assertEqual(parts.num, "01")
            self.assertTrue(
                parts.scope == "SAN10" or parts.extra == "SAN10", parts,
            )

    def test_cohesity_ilo_uses_far_device_not_description(self):
        """Description says N07; the cable lands on n08."""
        lab = self._label(
            "MON", 1000, "lr50-san10-n08.sensirion.lokal",
            "ch-sta-l50", "ch-sta-l26",
            "Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)",
            "Cohesity",
        )
        self.assertEqual(lab, "MON-SAN10-N08")
        self.assertIn("SAN10", lab)
        self.assertIn("N08", lab)
        self.assertNotIn("LR50", lab)
        self.assertNotIn("CY", lab)

    def test_site_slug_not_on_hostname_is_not_invented(self):
        """esx47 lives in NetBox site ch-zrh-dc; the name is zh4-esx47. No DC."""
        lab = self._label(
            "US", 1000, "ch-zrh-zh4-esx47.sensirion.lokal",
            "ch-zrh-dc", "ch-zrh-zh4", "vmnic4", "Server",
        )
        self.assertEqual(lab, "US-1G-ESX47_NIC4")
        self.assertNotIn("DC", lab)

    def test_endpoint_codes_keep_hostname_words(self):
        san = self._label(
            "US", 10000, "kr-sel-san11",
            "kr-sel-han", "kr-sel-han", "ct0.eth4", "Storage",
        )
        nas = self._label(
            "US", 10000, "HU-DEB-P-SNAS01",
            "hu-deb-nag-b", "hu-deb-nag-b", "LAN5", "Storage",
        )
        self.assertEqual(san, "US-SAN11_CT0_4")
        self.assertEqual(nas, "US-P-SNAS01_LAN5")
        self.assertNotIn("SN11", san)
        self.assertNotIn("NS01", nas)
        self.assertEqual(
            self._label(
                "US", 40000, "kr-sel-san11",
                "kr-sel-han", "kr-sel-han", "ct0.eth4", "Storage",
            ),
            "US-40G-SAN11_CT0_4",
        )

    def test_esxi_hypervisor_data_nic_is_us_and_keeps_nic_index(self):
        """Role ESXi Hypervisor is US. ``vmnic`` renders ``NIC`` so 10G fits."""
        a = e.plan_label(
            local_site="kr-sel-han",
            far_name="kr-sel-p-esx13.sensirion.lokal",
            far_site="kr-sel-han",
            far_port="vmnic3",
            far_role="ESXi Hypervisor",
            far_is_mgmt=False,
            link_mbps=10000,
        )
        b = e.plan_label(
            local_site="kr-sel-han",
            far_name="kr-sel-p-esx13.sensirion.lokal",
            far_site="kr-sel-han",
            far_port="vmnic5",
            far_role="ESXi Hypervisor",
            far_is_mgmt=False,
            link_mbps=10000,
        )
        self.assertEqual(a, "US-P-ESX13_NIC3")
        self.assertEqual(b, "US-P-ESX13_NIC5")
        self.assertNotEqual(a, b)
        self.assertNotIn("VMNIC", a)
        self.assertLessEqual(len(a), 20)

    def test_cohesity_1g_does_not_invent_10g(self):
        """NetBox 1000 Mbps stays 1G. Room prefix LR50 is not in the ID."""
        lab = self._label(
            "US", 1000, "lr50-san10-n01.sensirion.lokal",
            "ch-sta-l50", "ch-sta-l26",
            "",
            "Cohesity",
        )
        self.assertEqual(lab, "US-1G-SAN10-N01")
        self.assertNotIn("LR50", lab)
        self.assertNotIn("10G", lab)

    def test_cohesity_10g_fits_without_room_prefix(self):
        lab = self._label(
            "MON", 10000, "lr50-san10-n13.sensirion.lokal",
            "ch-sta-l50", "ch-sta-l26",
            "Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)",
            "Cohesity",
        )
        self.assertEqual(lab, "MON-10G-SAN10-N13")
        self.assertLessEqual(len(lab), 20)
        self.assertNotIn("LR50", lab)

    def test_cohesity_embedded_nic_plan_is_mon_from_cable(self):
        """Live Preview has no far_is_mgmt. NIC.Embedded + Cohesity → MON.

        ID still comes from the far hostname (n01), not ``COH-N07-ILO``.
        """
        lab = e.plan_label(
            local_site="ch-sta-l26",
            far_name="lr50-san10-n01.sensirion.lokal",
            far_site="ch-sta-l50",
            far_port="Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)",
            far_role="Cohesity",
            far_is_mgmt=False,
            link_mbps=1000,
            extra="COH-N07-ILO",
        )
        self.assertEqual(lab, "MON-SAN10-N01")
        self.assertNotIn("N07", lab)
        self.assertNotIn("LR50", lab)
        self.assertNotIn("1G", lab)

    def test_generated_labels_never_contain_dots(self):
        samples = [
            ("USW", 1000, "CH-NKN-G08-L02-CORE01-1", "ch-nkn-g08", "ch-nkn-g08", "01:01", "Switch Core"),
            ("USW", 1000, "CH-STA-L50-L01-MGMT01", "ch-sta-l50", "ch-sta-l50", "1:20", "Switch Mgmt"),
            ("US", 10000, "ch-zrh-zh4-san02", "ch-zrh-zh4", "ch-zrh-zh4", "ct0.eth10", "Storage"),
            ("USW", None, "CH-NKN-G08-L02-CORE01-2", "ch-nkn-g08", "ch-nkn-g08", "02:16", "Switch Core"),
        ]
        for args in samples:
            lab = self._label(*args)
            self.assertNotIn(".", lab, lab)
            self.assertFalse(e.FORBIDDEN_CHARS & set(lab), lab)
            self.assertTrue(e.is_safe_cli_label(lab), lab)
            # Role words in the ID, not a far-port token like `_MGMT`.
            for banned in ("CORE", "DIST", "ACCE", "MGMT"):
                self.assertIsNone(
                    re.search(rf"(?:^|-){banned}\d", lab), lab
                )


    def test_dot_is_a_forbidden_character(self):
        self.assertIn(".", e.FORBIDDEN_CHARS)

    def test_port_token_uses_underscore_not_dot(self):
        self.assertEqual(e.normalize_port_token("01:01"), "1_1")
        self.assertEqual(e.normalize_port_token("1/24"), "1_24")
        self.assertEqual(e.normalize_port_token("ct0.eth10"), "CT0_10")
        self.assertEqual(e.normalize_port_token("ct0.eth4"), "CT0_4")

    def test_port_encodes_stack_on_slotted_ifname(self):
        self.assertTrue(e._port_encodes_stack("02:10", "2"))
        self.assertTrue(e._port_encodes_stack("2:10", "02"))
        self.assertFalse(e._port_encodes_stack("48", "2"))
        self.assertFalse(e._port_encodes_stack("1:1", "2"))

    def test_isc_and_stack_peer_are_usw_not_x(self):
        """Switch↔switch ISC / stack members alert as USW. X is SPAN / mute."""
        isc = self._label(
            "USW", 10000, "CH-ZRH-ZH4-CORE02",
            "ch-zrh-zh4", "ch-zrh-zh4", "1", "Switch Core",
        )
        stack = self._label(
            "USW", None, "CH-NKN-G08-L02-CORE01-2",
            "ch-nkn-g08", "ch-nkn-g08", "02:16", "Switch Core",
        )
        self.assertTrue(isc.startswith("USW-"), isc)
        self.assertTrue(stack.startswith("USW-"), stack)
        self.assertFalse(isc.startswith("X"), isc)
        self.assertFalse(stack.startswith("X"), stack)


class CliSafetyTests(unittest.TestCase):
    def test_safe_label_accepts_grammar(self):
        self.assertTrue(e.is_safe_cli_label("USW-1G-L02-C01-1_1_1"))
        self.assertTrue(e.is_safe_cli_label("US-SAN02_CT0_10"))

    def test_safe_label_rejects_injection(self):
        self.assertFalse(e.is_safe_cli_label("USW-FOO;SAVE"))
        self.assertFalse(e.is_safe_cli_label("USW-FOO BAR"))
        self.assertFalse(e.is_safe_cli_label("USW-P1.1"))
        self.assertFalse(e.is_safe_cli_label(""))

    def test_safe_port_accepts_exos_and_voss(self):
        self.assertTrue(e.is_safe_cli_port("1"))
        self.assertTrue(e.is_safe_cli_port("1:51"))
        self.assertTrue(e.is_safe_cli_port("1/24"))
        self.assertTrue(e.is_safe_cli_port("1/1/1"))

    def test_safe_port_rejects_lists_and_junk(self):
        self.assertFalse(e.is_safe_cli_port("1:1-1:3"))
        self.assertFalse(e.is_safe_cli_port("1:1,1:3"))
        self.assertFalse(e.is_safe_cli_port("1:1; reboot"))

    def test_csv_has_header_and_row(self):
        plan = e.PortPlan(
            device="SW1", site="lab", kind="exos", ifname="1:1",
            expected="USW-D01_23", status="ok", far_device="DIST01",
            netbox_description="Stack-CORE02_p16",
            speed_source="local:iftype:10gbase-x-sfpp",
        )
        text = e.plans_to_csv([plan])
        body = text.lstrip("\ufeff")
        lines = body.splitlines()
        self.assertEqual(lines[0], "sep=,")
        header = lines[1]
        self.assertTrue(header.startswith("site,device,ssh_via,port,"), header)
        for col in (
            "class", "speed", "link_mbps", "speed_source", "far_site",
            "netbox_description", "ifalias_source", "ssh_via",
            "blocking", "collision", "description_string",
            "rewrite",
        ):
            self.assertIn(col, header.split(","), header)
        self.assertIn("SW1", text)
        self.assertIn("USW-D01_23", text)
        self.assertIn("USW", text)
        self.assertIn("Stack-CORE02_p16", text)
        self.assertIn("iftype:10gbase-x-sfpp", text)

    def test_csv_protects_voss_port_from_excel_dates(self):
        plan = e.PortPlan(
            device="SW1", site="lab", kind="voss", ifname="1/17",
            expected="USW-DI01_23", status="ok",
        )
        text = e.plans_to_csv([plan])
        # csv.writer quotes the formula as "=""1/17""" — Excel reads ="1/17".
        self.assertIn("1/17", text)
        self.assertIn('=""', text)

    def test_kept_live_label_is_not_blocking(self):
        plan = e.PortPlan(
            device="SW1", site="lab", kind="exos", ifname="48",
            live="ISP_Netrics", status="kept",
            detail="live label kept; no complete cable in NetBox",
        )
        self.assertFalse(plan.blocking)
        self.assertFalse(e.PortPlan(
            device="SW1", site="lab", kind="exos", ifname="1",
            expected="USW-CO02_P1", status="ok",
        ).blocking)
        self.assertTrue(e.PortPlan(
            device="SW1", site="lab", kind="exos", ifname="1",
            expected="USW-CO02_P1", live="ISC", status="diff",
        ).blocking)

    def test_unreachable_and_hijacked_are_blocking(self):
        self.assertTrue(e.PortPlan(
            device="SW1", site="lab", kind="exos", ifname="1",
            status="unreachable",
        ).blocking)
        self.assertTrue(e.PortPlan(
            device="SW1", site="lab", kind="exos", ifname="1",
            expected="USW-CO02_1", live="USW-CO02_1",
            description_string="old text", status="alias_hijacked",
            ifalias_source="description-string",
        ).blocking)

    def test_duplicate_expected_on_one_device_is_blocking(self):
        a = e.PortPlan(
            device="CORE01", site="lab", kind="exos", ifname="1",
            expected="USW-AC01_23", status="ok",
        )
        b = e.PortPlan(
            device="CORE01", site="lab", kind="exos", ifname="2",
            expected="USW-AC01_23", status="ok",
        )
        c = e.PortPlan(
            device="CORE01", site="lab", kind="exos", ifname="3",
            expected="USW-DI01_29", status="ok",
        )
        e.flag_collisions([a, b, c])
        self.assertTrue(a.collision)
        self.assertTrue(b.collision)
        self.assertFalse(c.collision)
        self.assertTrue(a.blocking)
        self.assertFalse(c.blocking)

    def test_structural_x_ports_are_not_collisions(self):
        a = e.PortPlan(device="CORE01", site="lab", kind="exos", ifname="47",
                       expected="X", status="ok")
        b = e.PortPlan(device="CORE01", site="lab", kind="exos", ifname="48",
                       expected="X", status="ok")
        e.flag_collisions([a, b])
        self.assertFalse(a.collision)
        self.assertFalse(b.collision)
        self.assertFalse(a.blocking)

    def test_allowlist_accepts_colon_or_slash(self):
        allow = {"CORE01::1/17"}
        self.assertTrue(e.allowlist_hit("CORE01", "1:17", allow))
        self.assertTrue(e.allowlist_hit("CORE01", "1/17", allow))
        self.assertFalse(e.allowlist_hit("CORE01", "1/18", allow))
        self.assertFalse(e.allowlist_hit("CORE02", "1/17", allow))
        self.assertTrue(
            e.allowlist_hit("CORE01-2", "2:10", {"CORE01-1::2:10"}, "CORE01-1")
        )

    def test_iface_speed_falls_back_to_kbps_field(self):
        class _I:
            def __init__(self, **kw):
                self.__dict__.update(kw)

        iface = _I(type=None, speed=10_000_000)
        self.assertEqual(e.iface_speed_mbps(iface), 10000)
        typed = _I(type="10gbase-x-sfpp", speed=None)
        self.assertEqual(e.iface_speed_mbps(typed), 10000)
        self.assertEqual(e.iface_speed_source(typed), "iftype:10gbase-x-sfpp")
        forced = _I(type="10gbase-x-sfpp", speed=1_000_000)
        self.assertEqual(e.iface_speed_mbps(forced), 1000)
        self.assertEqual(e.iface_speed_source(forced), "speed:1000000kbps")
        stack = _I(type="extreme-summitstack", speed=None)
        self.assertIsNone(e.iface_speed_mbps(stack))
        self.assertEqual(e.iface_speed_source(stack), "")
        kbps = _I(type=None, speed=1_000_000)
        self.assertEqual(e.iface_speed_source(kbps), "speed:1000000kbps")
        far = _I(type="1000base-t", speed=None)
        mbps, src = e.link_mbps_and_source(typed, far)
        self.assertEqual(mbps, 1000)
        self.assertEqual(src, "far:iftype:1000base-t")

    def test_empty_far_name_raises_label_too_long_not_index_error(self):
        parts = e.split_device_name("", "", "")
        with self.assertRaises(e.LabelTooLong):
            e.build_label_for_far_end("USW", 10000, parts, "1:20")

    def test_too_long_plan_still_records_live_ifalias(self):
        plan = e.PortPlan(
            device="SW1", site="lab", kind="exos", ifname="1",
            expected="USW-THIS-WILL-NOT-FIT-AT-ALL", status="too_long",
        )
        e.compare_plan(plan, labels={"1": "ISC"}, descriptions={})
        self.assertEqual(plan.status, "too_long")
        self.assertEqual(plan.live, "ISC")
        self.assertEqual(plan.commands, [])

    def test_matching_display_with_description_string_is_hijacked(self):
        plan = e.PortPlan(
            device="SW1", site="lab", kind="exos", ifname="1",
            expected="USW-CO02_1", status="ok",
        )
        e.compare_plan(
            plan,
            labels={"1": "USW-CO02_1"},
            descriptions={"1": "ISC leftover"},
            clear_description=False,
        )
        self.assertEqual(plan.status, "alias_hijacked")
        self.assertEqual(plan.ifalias_source, "description-string")
        self.assertTrue(plan.blocking)
        self.assertEqual(plan.commands, [])

    def test_hijacked_gets_clear_command_when_ticked(self):
        plan = e.PortPlan(
            device="SW1", site="lab", kind="exos", ifname="1",
            expected="USW-CO02_1", status="ok",
        )
        e.compare_plan(
            plan,
            labels={"1": "USW-CO02_1"},
            descriptions={"1": "ISC leftover"},
            clear_description=True,
        )
        self.assertEqual(plan.status, "alias_hijacked")
        self.assertIn("unconfigure port 1 description-string", plan.commands)

    def test_scorecard_rolls_up_per_device(self):
        plans = [
            e.PortPlan(device="A", site="s", kind="exos", ifname="1",
                       expected="USW-CO02_1", status="ok"),
            e.PortPlan(device="A", site="s", kind="exos", ifname="2",
                       expected="USW-DI01_23", status="diff"),
            e.PortPlan(device="B", site="s", kind="voss", ifname="1/17",
                       expected="USW-AC01_5", status="unreachable"),
        ]
        rows = {r["device"]: r for r in e.device_scorecard(plans)}
        self.assertEqual(rows["A"]["ok"], 1)
        self.assertEqual(rows["A"]["diff"], 1)
        self.assertEqual(rows["A"]["blocking"], 1)
        self.assertEqual(rows["B"]["unreach"], 1)
        self.assertEqual(rows["B"]["blocking"], 1)

    def test_preview_planned_is_not_a_match_and_not_a_rewrite(self):
        plan = e.PortPlan(
            device="SW1", site="lab", kind="exos", ifname="1",
            expected="USW-CO02_1", status="planned",
        )
        self.assertFalse(plan.blocking)
        self.assertEqual(e.plan_rewrite(plan), "")
        rows = e.device_scorecard([plan])
        self.assertEqual(rows[0]["planned"], 1)
        self.assertEqual(rows[0]["ok"], 0)
        self.assertEqual(rows[0]["rewrite"], 0)
        csv = e.plans_to_csv([plan])
        self.assertIn("planned", csv)
        self.assertRegex(csv, r",planned,,no,")

    def test_compliance_diff_is_rewrite_yes(self):
        plan = e.PortPlan(
            device="SW1", site="lab", kind="exos", ifname="1",
            expected="USW-CO02_1", status="planned",
        )
        e.compare_plan(plan, labels={"1": "ISC"}, descriptions={})
        self.assertEqual(plan.status, "diff")
        self.assertEqual(e.plan_rewrite(plan), "yes")
        self.assertTrue(plan.commands)
        match = e.PortPlan(
            device="SW1", site="lab", kind="exos", ifname="2",
            expected="USW-DI01_23", status="planned",
        )
        e.compare_plan(match, labels={"2": "USW-DI01_23"}, descriptions={})
        self.assertEqual(match.status, "ok")
        self.assertEqual(e.plan_rewrite(match), "no")
        self.assertFalse(match.commands)

    def test_markdown_table_truncates(self):
        rows = [[str(i), "x"] for i in range(50)]
        text = e.markdown_table(["N", "V"], rows, limit=5)
        self.assertIn("… 45 more rows", text)
        data_lines = [ln for ln in text.splitlines() if ln.startswith("| ") and "N" not in ln]
        self.assertEqual(len(data_lines), 5)

    def test_scorecard_log_chunks_title_parts_when_split(self):
        header = ["| Device |", "|--------|"]
        body = [f"| sw{i} |" for i in range(1, 6)]
        one = e.scorecard_log_chunks(header, body, chunk=10)
        self.assertEqual(len(one), 1)
        self.assertEqual(one[0][0], "Per-device scorecard")
        parts = e.scorecard_log_chunks(header, body, chunk=2)
        self.assertEqual([p[0] for p in parts], [
            "Per-device scorecard (1/3, devices 1–2)",
            "Per-device scorecard (2/3, devices 3–4)",
            "Per-device scorecard (3/3, devices 5–5)",
        ])
        self.assertEqual(len(parts[0][1]), 4)  # header + 2 rows


    def test_semicolon_is_forbidden(self):
        self.assertIn(";", e.FORBIDDEN_CHARS)
        self.assertIn(".", e.FORBIDDEN_CHARS)


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

    def test_cohesity_embedded_nic_is_mgmt(self):
        class _Role:
            name = "Cohesity"

        class _Iface:
            mgmt_only = False
            name = "Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)"
            device = type("D", (), {"oob_ip": None, "role": _Role()})()

        self.assertTrue(e._is_management_interface(_Iface()))

    def test_server_embedded_nic_is_not_mgmt(self):
        class _Role:
            name = "Server"

        class _Iface:
            mgmt_only = False
            name = "Embedded NIC 1 Port 1 Partition 1 (NIC.Embedded.1-1)"
            device = type("D", (), {"oob_ip": None, "role": _Role()})()

        self.assertFalse(e._is_management_interface(_Iface()))

    def test_ilo_in_local_description_is_mgmt_hint(self):
        class _Role:
            name = "Cohesity"

        class _Iface:
            mgmt_only = False
            name = "eth0"
            device = type("D", (), {"oob_ip": None, "role": _Role()})()

        self.assertTrue(e._is_management_interface(_Iface(), extra="COH-N01-ILO"))
        self.assertFalse(e._is_management_interface(_Iface()))


_DATACLASS_RUNNER = textwrap.dedent(
    """
    from dataclasses import dataclass

    @dataclass
    class Session:
        name: str

    _EXOS_USERNAME = "exos-user"
    _EXOS_PASSWORD = "x"
    _VOSS_USERNAME = "voss-user"
    _VOSS_PASSWORD = "y"
    PROBE = Session("ok")
    """
).lstrip()


class CliRunnerLoadTests(unittest.TestCase):
    def setUp(self):
        e._reset_cli_runner()

    def tearDown(self):
        e._reset_cli_runner()

    def test_search_finds_runner_under_scripts_when_labels_sit_at_base_dir(self):
        """Prod miss: labels at BASE_DIR, runner in BASE_DIR/scripts."""
        with tempfile.TemporaryDirectory() as tmp:
            scripts = os.path.join(tmp, "scripts")
            os.makedirs(scripts)
            runner = os.path.join(scripts, "extreme_cli_runner.py")
            with open(runner, "w", encoding="utf-8") as handle:
                handle.write("VALUE = 1\n")
            labels = os.path.join(tmp, "extreme_port_labels.py")
            found = e._runner_candidate_paths(labels)
            self.assertEqual(
                [os.path.realpath(p) for p in found],
                [os.path.realpath(runner)],
            )

    def test_search_prefers_sibling_over_parent_scripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            scripts = os.path.join(tmp, "scripts")
            os.makedirs(scripts)
            sibling = os.path.join(scripts, "extreme_cli_runner.py")
            parent = os.path.join(tmp, "extreme_cli_runner.py")
            with open(sibling, "w", encoding="utf-8") as handle:
                handle.write("WHERE = 'scripts'\n")
            with open(parent, "w", encoding="utf-8") as handle:
                handle.write("WHERE = 'base'\n")
            labels = os.path.join(scripts, "extreme_port_labels.py")
            found = e._runner_candidate_paths(labels)
            self.assertEqual(os.path.realpath(found[0]), os.path.realpath(sibling))

    def test_exec_registers_module_before_dataclasses_run(self):
        """Python 3.12 dataclasses fail if the module is not in sys.modules."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "extreme_cli_runner.py")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(_DATACLASS_RUNNER)
            module = e._exec_cli_runner(path)
            self.assertIs(sys.modules[e._RUNNER_MODULE_NAME], module)
            self.assertEqual(module.PROBE.name, "ok")
            self.assertEqual(module._EXOS_USERNAME, "exos-user")

    def test_load_from_scripts_subdir_and_status_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            scripts = os.path.join(tmp, "scripts")
            os.makedirs(scripts)
            path = os.path.join(scripts, "extreme_cli_runner.py")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(_DATACLASS_RUNNER)
            labels = os.path.join(tmp, "extreme_port_labels.py")
            loaded = e._load_cli_runner(labels)
            self.assertIsNotNone(loaded)
            self.assertEqual(os.path.realpath(e._RUNNER_PATH), os.path.realpath(path))
            lines = e.runner_status_lines()
            self.assertEqual(lines[0], "runner_loaded True")
            self.assertEqual(lines[1], "runner_error None")
            self.assertIn(os.path.realpath(path), lines[2])
            self.assertEqual(lines[3], "credentials extreme_exos extreme_vsp")

    def test_status_when_runner_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            labels = os.path.join(tmp, "extreme_port_labels.py")
            self.assertIsNone(e._load_cli_runner(labels))
            lines = e.runner_status_lines()
            self.assertEqual(lines[0], "runner_loaded False")
            self.assertTrue(lines[1].startswith("runner_error "))
            self.assertNotEqual(lines[1], "runner_error None")
            self.assertEqual(lines[2], "runner_path None")
            self.assertEqual(lines[3], "credentials unavailable")


_NETMIKO_AUTH_TIMEOUT = """\
SSH failed after 3 attempts: Authentication to device failed.

Common causes of this problem are:
1. Invalid username and password
2. Incorrect SSH-key file
3. Connecting to the wrong device

Device settings: extreme_exos 10.8.30.11:22


Authentication timeout.
"""

_NETMIKO_VOSS_PROMPT = """\
SSH failed after 3 attempts: 

Pattern not detected: '(?:\\#|>)' in output.

Things you might try to fix this:
1. Adjust the regex pattern to better identify the terminating string. Note, in
many situations the pattern is automatically based on the network device's prompt.
2. Increase the read_timeout to a larger value.

You can also look at the Netmiko session_log or debug log for more information.
"""


class SshSessionErrorTests(unittest.TestCase):
    """One failed login is copied onto every port — keep the CSV one line."""

    def test_summarize_drops_netmiko_lecture_keeps_timeout(self):
        summary = e.summarize_ssh_error(_NETMIKO_AUTH_TIMEOUT)
        self.assertIn("Authentication timeout", summary)
        self.assertIn("3 attempts", summary)
        self.assertNotIn("Common causes", summary)
        self.assertNotIn("Invalid username", summary)
        self.assertNotIn("Device settings", summary)
        self.assertNotIn("10.8.30.11", summary)
        self.assertLessEqual(len(summary), e.SSH_DETAIL_MAX)

    def test_summarize_voss_pattern_not_detected(self):
        summary = e.summarize_ssh_error(_NETMIKO_VOSS_PROMPT)
        self.assertIn("Pattern not detected", summary)
        self.assertIn("3 attempts", summary)
        self.assertNotIn("Things you might try", summary)
        self.assertNotIn("session_log", summary)
        self.assertNotIn("read_timeout", summary)
        self.assertLessEqual(len(summary), e.SSH_DETAIL_MAX)

    def test_stamp_marks_every_port_with_one_login_note(self):
        plans = [
            e.PortPlan(device="SW1", site="s", kind="exos", ifname=str(n),
                       expected="UP-GFL-AP01", commands=["should-clear"])
            for n in (17, 19, 21, 22, 23, 24)
        ]
        detail = e.stamp_device_ssh_failure(plans, _NETMIKO_AUTH_TIMEOUT)
        self.assertIn("1 login", detail)
        self.assertIn("6 port(s)", detail)
        self.assertIn("Authentication timeout", detail)
        self.assertNotIn("Common causes", detail)
        for plan in plans:
            self.assertEqual(plan.status, "unreachable")
            self.assertEqual(plan.detail, detail)
            self.assertEqual(plan.commands, [])


class VossSshTransportTests(unittest.TestCase):
    """VOSS must match Extreme Firmware Upgrade, not the EXOS runner helper."""

    def setUp(self):
        e._reset_cli_runner()

    def tearDown(self):
        e._reset_cli_runner()

    def test_connect_kwargs_give_auth_60s(self):
        kw = e.voss_connect_kwargs()
        self.assertEqual(kw["timeout"], 60)
        self.assertEqual(kw["auth_timeout"], 60)
        self.assertEqual(kw["banner_timeout"], 30)
        self.assertIs(kw["fast_cli"], False)

    def test_prompt_is_firmware_expect_string(self):
        self.assertEqual(e.VOSS_PROMPT_RE, r"#|>")

    def test_send_voss_uses_firmware_expect_string(self):
        class Fake:
            def __init__(self):
                self.calls = []

            def send_command(self, cmd, read_timeout=60, expect_string=None):
                self.calls.append((cmd, read_timeout, expect_string))
                return "hostname:1# "

        nc = Fake()
        out = e._send(nc, "show running-config", read_timeout=180, kind="voss")
        self.assertEqual(out, "hostname:1# ")
        self.assertEqual(nc.calls, [("show running-config", 180, r"#|>")])

    def test_send_voss_falls_back_to_timing_on_prompt_miss(self):
        class Fake:
            def send_command(self, cmd, read_timeout=60, expect_string=None):
                raise OSError("Pattern not detected: '(?:\\#|>)' in output.")

            def send_command_timing(self, cmd, read_timeout=60, last_read=2.0):
                return f"timing:{cmd}"

        out = e._send_voss(Fake(), "save config", read_timeout=60)
        self.assertEqual(out, "timing:save config")

    def test_exos_send_does_not_use_voss_expect_string(self):
        class Fake:
            def send_command_timing(self, cmd, read_timeout=60):
                return f"exos:{cmd}:{read_timeout}"

        # No runner loaded in this isolated import — EXOS falls back to timing,
        # never to VOSS expect_string.
        out = e._send(Fake(), "show configuration vlan", read_timeout=120)
        self.assertEqual(out, "exos:show configuration vlan:120")


class ExosStackSessionTests(unittest.TestCase):
    def test_parse_stack_hostname(self):
        self.assertEqual(
            e.parse_exos_stack_hostname("CN-SHA-JIU-L03-CORE01-1"),
            ("CN-SHA-JIU-L03-CORE01", "1"),
        )
        self.assertEqual(
            e.parse_exos_stack_hostname("JP-YOK-CHO-L06-CORE-2"),
            ("JP-YOK-CHO-L06-CORE", "2"),
        )
        self.assertIsNone(e.parse_exos_stack_hostname("CH-STA-L50-B01-ACCE01"))
        self.assertIsNone(e.parse_exos_stack_hostname("CN-SHA-JIU-L03-CORE01"))

    def test_ifname_slot_and_canonical(self):
        self.assertEqual(e.ifname_stack_slot("2:10"), "2")
        self.assertEqual(e.ifname_stack_slot("02:10"), "2")
        self.assertEqual(e.ifname_stack_slot("2/10"), "2")
        self.assertIsNone(e.ifname_stack_slot("10"))
        self.assertEqual(e.canonical_port_key("02:10"), "2:10")
        self.assertEqual(e.canonical_port_key("2/10"), "2:10")

    def test_session_key_groups_exos_stack_not_voss(self):
        a = e.exos_stack_session_key(
            name="CN-SHA-JIU-L03-CORE01-1", site="cn-sha-jiu", kind="exos",
        )
        b = e.exos_stack_session_key(
            name="CN-SHA-JIU-L03-CORE01-2", site="cn-sha-jiu", kind="exos",
        )
        self.assertEqual(a, b)
        self.assertNotEqual(
            a,
            e.exos_stack_session_key(
                name="CN-SHA-JIU-L03-CORE03-1", site="cn-sha-jiu", kind="exos",
            ),
        )
        self.assertNotEqual(
            e.exos_stack_session_key(name="VSP-1", site="s", kind="voss"),
            e.exos_stack_session_key(name="VSP-2", site="s", kind="voss"),
        )
        self.assertEqual(
            e.exos_stack_session_key(
                name="A-2", site="s", vc_id=9, kind="exos",
            ),
            e.exos_stack_session_key(
                name="B-1", site="s", vc_id=9, kind="exos",
            ),
        )

    def test_pick_ssh_member_prefers_master_then_slot1(self):
        members = [
            {"name": "CORE01-2", "ip": None, "master": False, "position": 2},
            {"name": "CORE01-1", "ip": "10.0.0.1", "master": True, "position": 1},
        ]
        picked = e.pick_exos_stack_ssh_member(members)
        self.assertEqual(picked["name"], "CORE01-1")
        no_master = [
            {"name": "CORE01-2", "ip": None, "master": False, "position": 2},
            {"name": "CORE01-1", "ip": "10.0.0.1", "master": False, "position": 1},
        ]
        self.assertEqual(e.pick_exos_stack_ssh_member(no_master)["name"], "CORE01-1")
        self.assertIsNone(e.pick_exos_stack_ssh_member([
            {"name": "CORE01-2", "ip": None, "master": False, "position": 2},
        ]))

    def test_prefer_slot2_owner_for_duplicate_ifname(self):
        master = e.PortPlan(
            device="CORE01-1", site="s", kind="exos", ifname="2:10",
            expected="USW-WRONG",
        )
        member = e.PortPlan(
            device="CORE01-2", site="s", kind="exos", ifname="2:10",
            expected="US-P-ESX13_NIC2",
        )
        kept = e.prefer_stack_ifname_owner([master, member])
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0].device, "CORE01-2")
        self.assertEqual(kept[0].expected, "US-P-ESX13_NIC2")

    def test_live_slot2_is_not_kept_when_member_has_cable(self):
        plans = [
            e.PortPlan(
                device="CORE01-1", site="s", kind="exos", ifname="1:8",
                expected="MON-P-ESX11_ILO9_1", ssh_device="CORE01-1",
            ),
            e.PortPlan(
                device="CORE01-2", site="s", kind="exos", ifname="2:10",
                expected="US-P-ESX13_NIC2", ssh_device="CORE01-1",
            ),
        ]
        e.note_kept_live(
            plans,
            {"1:8": "MON-P-ESX11_ILO9_1", "2:10": "ESX13_eth2", "2:99": "ISP"},
            {},
            ssh_device="CORE01-1",
        )
        kept = [p for p in plans if p.status == "kept"]
        self.assertEqual([p.ifname for p in kept], ["2:99"])
        self.assertEqual(kept[0].device, "CORE01-1")

    def test_collision_is_per_live_box_not_netbox_member(self):
        a = e.PortPlan(
            device="CORE01-1", site="s", kind="exos", ifname="1:1",
            expected="USW-D01_23", ssh_device="CORE01-1",
        )
        b = e.PortPlan(
            device="CORE01-2", site="s", kind="exos", ifname="2:1",
            expected="USW-D01_23", ssh_device="CORE01-1",
        )
        e.flag_collisions([a, b])
        self.assertTrue(a.collision)
        self.assertTrue(b.collision)

    def test_csv_ssh_via_only_when_member_differs(self):
        member = e.PortPlan(
            device="CORE01-2", site="s", kind="exos", ifname="2:2",
            expected="USW-L02-D02_27", ssh_device="CORE01-1",
        )
        text = e.plans_to_csv([member])
        self.assertIn("CORE01-2", text)
        self.assertIn("CORE01-1", text)
        local = e.PortPlan(
            device="CORE01-1", site="s", kind="exos", ifname="1:8",
            expected="MON-X", ssh_device="CORE01-1",
        )
        local_csv = e.plans_to_csv([local])
        header = local_csv.splitlines()[1]
        self.assertIn("ssh_via", header)


if __name__ == "__main__":
    unittest.main()
