#!/usr/bin/env python3
"""Pure-helper tests for extreme_port_mute.py (no NetBox, no SSH)."""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import extreme_port_mute as m  # noqa: E402
import extreme_port_labels as e  # noqa: E402


GFL_LIST = """
# leftover unused slot-2 ports on NEP-GFL CORE01
NEP-GFL-CORE01-1::2:10
NL-ENS-NEP-GFL-CORE01-1::2:11
NL-ENS-NEP-GFL-CORE01-1::2:12
NL-ENS-NEP-GFL-CORE01-1::2:13
NL-ENS-NEP-GFL-CORE01-1::2:14
NL-ENS-NEP-GFL-CORE01-1::2:15
NL-ENS-NEP-GFL-CORE01-1::2:16
NL-ENS-NEP-GFL-CORE01-1::2:17
"""


class ParseAllowlistTests(unittest.TestCase):
    def test_user_paste_parses_eight_rows(self):
        entries, errors = m.parse_allowlist_text(GFL_LIST)
        self.assertEqual(errors, [])
        self.assertEqual(len(entries), 8)
        self.assertEqual(entries[0], ("NEP-GFL-CORE01-1", "2:10"))
        self.assertEqual(entries[1], ("NL-ENS-NEP-GFL-CORE01-1", "2:11"))
        self.assertEqual(entries[-1], ("NL-ENS-NEP-GFL-CORE01-1", "2:17"))

    def test_rejects_range_and_garbage(self):
        entries, errors = m.parse_allowlist_text(
            "CORE01::2:10-2:17\nnot-a-canary\nCORE01::2:11\n"
        )
        self.assertEqual(entries, [("CORE01", "2:10-2:17"), ("CORE01", "2:11")])
        self.assertEqual(len(errors), 1)
        self.assertIn("expected DEVICE::port", errors[0])

    def test_comments_and_blanks(self):
        entries, errors = m.parse_allowlist_text(
            "\n# header\nCORE01::2:10  # leftover\n\n"
        )
        self.assertEqual(errors, [])
        self.assertEqual(entries, [("CORE01", "2:10")])


class XPrefixTests(unittest.TestCase):
    def test_empty_becomes_x(self):
        self.assertEqual(m.x_prefix_label(""), "X")
        self.assertEqual(m.x_prefix_label("   "), "X")

    def test_prefixes_and_truncates_from_end(self):
        live = "USW-10G-GFL-ACCE01A"  # 19 chars; X- (2) + 19 = 21 → cut the tail
        out = m.x_prefix_label(live)
        self.assertEqual(len(out), 20)
        self.assertTrue(out.startswith("X-"))
        self.assertEqual(out, ("X-" + live)[:20])
        self.assertEqual(out, "X-USW-10G-GFL-ACCE01")
        self.assertFalse(out.endswith("A"))

    def test_does_not_double_prefix(self):
        self.assertEqual(m.x_prefix_label("X"), "X")
        self.assertEqual(m.x_prefix_label("X-USW-FOO"), "X-USW-FOO")
        self.assertEqual(m.x_prefix_label("x-already"), "X-ALREADY")

    def test_source_prefers_display_over_description(self):
        self.assertEqual(m.x_prefix_source("DISP", "DESC"), "DISP")
        self.assertEqual(m.x_prefix_source("", "DESC"), "DESC")
        self.assertTrue(m.already_x_muted("X-FOO"))
        self.assertFalse(m.already_x_muted("USW-FOO"))


class StackPortTests(unittest.TestCase):
    def test_summitstack_type_is_refused(self):
        self.assertTrue(m.is_stack_port(iftype="extreme-summitstack"))
        self.assertTrue(m.is_stack_port(description="STACKING_PORT"))
        self.assertFalse(m.is_stack_port(iftype="10gbase-x-sfpp", description=""))
        self.assertFalse(
            m.is_stack_port(iftype="10gbase-x-sfpp", description="unused slot 2")
        )


class CliTests(unittest.TestCase):
    def test_native_port_exos_colon_voss_slash(self):
        self.assertEqual(m.native_cli_port("exos", "2/10"), "2:10")
        self.assertEqual(m.native_cli_port("voss", "2:10"), "2/10")
        self.assertEqual(m.native_cli_port("voss", "1/1/1"), "1/1/1")

    def test_exos_shutdown_is_disable_port(self):
        self.assertEqual(m.cli_shutdown_cmds("exos", "2:10"), ["disable port 2:10"])
        self.assertEqual(m.cli_shutdown_cmds("exos", "2/10"), ["disable port 2:10"])

    def test_voss_shutdown_is_gigabitethernet_interface(self):
        self.assertEqual(
            m.cli_shutdown_cmds("voss", "2:10"),
            ["interface GigabitEthernet 2/10", "shutdown", "exit"],
        )

    def test_exos_x_prefix_clears_description_string(self):
        cmds = m.cli_x_prefix_cmds("exos", "2:10", "X-USW-FOO")
        self.assertEqual(cmds[0], "configure ports 2:10 display-string X-USW-FOO")
        self.assertIn("unconfigure port 2:10 description-string", cmds)
        self.assertFalse(any("description-string " in c and not c.startswith("unconfigure") for c in cmds))

    def test_voss_x_prefix_sets_name(self):
        cmds = m.cli_x_prefix_cmds("voss", "2:10", "X-USW-FOO")
        self.assertEqual(cmds[0], "interface GigabitEthernet 2/10")
        self.assertEqual(cmds[1], 'name "X-USW-FOO"')
        self.assertEqual(cmds[2], "exit")

    def test_commands_are_single_ports_not_ranges(self):
        for kind in ("exos", "voss"):
            blob = " ".join(m.cli_shutdown_cmds(kind, "2:17"))
            self.assertNotIn("-", blob.split("port")[-1] if "port" in blob else blob)


class DecideMuteTests(unittest.TestCase):
    def _plan(self, **kw) -> m.MutePlan:
        base = dict(
            canary="NL-ENS-NEP-GFL-CORE01-1::2:10",
            device="NL-ENS-NEP-GFL-CORE01-1",
            ifname="2:10",
            kind="exos",
            action="shutdown",
        )
        base.update(kw)
        return m.MutePlan(**base)

    def test_shutdown_preview_emits_disable(self):
        plan = m.decide_mute(self._plan(), allow_cabled=False, live_known=False)
        self.assertEqual(plan.status, "planned")
        self.assertEqual(plan.commands, ["disable port 2:10"])

    def test_voss_shutdown_preview(self):
        plan = m.decide_mute(
            self._plan(kind="voss", ifname="1/17"),
            allow_cabled=False, live_known=False,
        )
        self.assertEqual(plan.commands[0], "interface GigabitEthernet 1/17")
        self.assertIn("shutdown", plan.commands)

    def test_stack_port_refused_even_if_cabled_allowed(self):
        plan = m.decide_mute(
            self._plan(ifname="2:27", iftype="extreme-summitstack", cabled=True),
            allow_cabled=True, live_known=False,
        )
        self.assertEqual(plan.status, "skip")
        self.assertIn("SummitStack", plan.detail)
        self.assertEqual(plan.commands, [])

    def test_cabled_skipped_without_override(self):
        plan = m.decide_mute(
            self._plan(cabled=True, far_device="LEAF01", far_port="1:1"),
            allow_cabled=False, live_known=False,
        )
        self.assertEqual(plan.status, "skip")
        self.assertIn("cabled", plan.detail)
        self.assertEqual(plan.commands, [])

    def test_cabled_allowed_emits_disable(self):
        plan = m.decide_mute(
            self._plan(cabled=True),
            allow_cabled=True, live_known=False,
        )
        self.assertEqual(plan.status, "planned")
        self.assertEqual(plan.commands, ["disable port 2:10"])

    def test_range_port_is_error(self):
        plan = m.decide_mute(
            self._plan(ifname="2:10-2:17"),
            allow_cabled=False, live_known=False,
        )
        self.assertEqual(plan.status, "error")
        self.assertEqual(plan.commands, [])

    def test_x_prefix_preview_does_not_guess_live(self):
        plan = m.decide_mute(
            self._plan(action="x_prefix"),
            allow_cabled=False, live_known=False,
        )
        self.assertEqual(plan.status, "planned")
        self.assertEqual(plan.commands, [])
        self.assertEqual(plan.new_label, "")

    def test_x_prefix_after_live_read(self):
        plan = m.decide_mute(
            self._plan(action="x_prefix", live="USW-FOO"),
            allow_cabled=False, live_known=True,
        )
        self.assertEqual(plan.new_label, "X-USW-FOO")
        self.assertIn("display-string X-USW-FOO", plan.commands[0])
        self.assertTrue(e.is_safe_cli_label(plan.new_label))

    def test_x_prefix_already_muted(self):
        plan = m.decide_mute(
            self._plan(action="x_prefix", live="X-USW-FOO"),
            allow_cabled=False, live_known=True,
        )
        self.assertEqual(plan.status, "already")
        self.assertEqual(plan.commands, [])

    def test_x_prefix_still_clears_hijacking_description(self):
        plan = m.decide_mute(
            self._plan(
                action="x_prefix", live="X-USW-FOO",
                description_string="old human text",
            ),
            allow_cabled=False, live_known=True,
        )
        self.assertEqual(plan.status, "planned")
        self.assertIn("unconfigure port 2:10 description-string", plan.commands)

    def test_x_prefix_unsafe_live_is_error(self):
        plan = m.decide_mute(
            self._plan(action="x_prefix", live="FOO BAR"),
            allow_cabled=False, live_known=True,
        )
        self.assertEqual(plan.status, "error")
        self.assertIn("not safe CLI", plan.detail)

    def test_unknown_platform_errors(self):
        plan = m.decide_mute(
            self._plan(kind="ios"),
            allow_cabled=False, live_known=False,
        )
        self.assertEqual(plan.status, "error")
        self.assertIn("unknown platform", plan.detail)

    def test_gfl_2_10_is_not_a_stack_port(self):
        """GFL stack is 1:27/1:28 and 2:27/2:28, not 2:10–2:17."""
        plan = m.decide_mute(
            self._plan(iftype="10gbase-x-sfpp"),
            allow_cabled=False, live_known=False,
        )
        self.assertEqual(plan.status, "planned")
        self.assertEqual(plan.commands, ["disable port 2:10"])


class ApplySessionTests(unittest.TestCase):
    def setUp(self):
        e._reset_cli_runner()

    def tearDown(self):
        e._reset_cli_runner()

    def test_exos_apply_disable_then_save(self):
        class Fake:
            def __init__(self):
                self.cmds = []

            def send_command_timing(self, cmd, read_timeout=60):
                self.cmds.append(cmd)
                return ""

        plan = m.MutePlan(
            canary="CORE01-1::2:10", device="CORE01-1", ifname="2:10",
            kind="exos", action="shutdown",
            commands=["disable port 2:10"],
        )
        ok, transcript, err = m.apply_mute_on_session(Fake(), "exos", [plan], True)
        self.assertTrue(ok)
        self.assertIsNone(err)
        self.assertEqual(plan.status, "applied")
        self.assertIn("> disable port 2:10", transcript)
        self.assertIn("> save configuration", transcript)
        self.assertNotIn("configure terminal", transcript)

    def test_voss_apply_enters_config_then_shutdown_then_save(self):
        class Fake:
            def __init__(self):
                self.cmds = []

            def send_command(self, cmd, read_timeout=60, expect_string=None):
                self.cmds.append((cmd, expect_string))
                return "hostname:1# "

            def send_command_timing(self, cmd, read_timeout=60, last_read=2.0):
                self.cmds.append((cmd, "timing"))
                return "saved"

        plan = m.MutePlan(
            canary="VSP01::1/17", device="VSP01", ifname="1/17",
            kind="voss", action="shutdown",
            commands=m.cli_shutdown_cmds("voss", "1/17"),
        )
        ok, transcript, err = m.apply_mute_on_session(Fake(), "voss", [plan], True)
        self.assertTrue(ok)
        self.assertIsNone(err)
        self.assertIn("> configure terminal", transcript)
        self.assertIn("> interface GigabitEthernet 1/17", transcript)
        self.assertIn("> shutdown", transcript)
        self.assertIn("> end", transcript)
        self.assertIn("> save config", transcript)

    def test_rejected_cli_stops_session(self):
        class Fake:
            def send_command_timing(self, cmd, read_timeout=60):
                return "% Error: Invalid input detected"

        plan = m.MutePlan(
            canary="CORE01::1:1", device="CORE01", ifname="1:1",
            kind="exos", action="shutdown",
            commands=["disable port 1:1"],
        )
        ok, transcript, err = m.apply_mute_on_session(Fake(), "exos", [plan], False)
        self.assertFalse(ok)
        self.assertIn("rejected", err or "")
        self.assertEqual(plan.status, "error")


class LabelsStaySeparateTests(unittest.TestCase):
    def test_labels_script_has_no_shutdown_or_mute_mode(self):
        path = os.path.join(_HERE, "extreme_port_labels.py")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn('("preview"', text)
        self.assertIn('("compliance"', text)
        self.assertIn('("remediate"', text)
        self.assertNotIn('("shutdown"', text)
        self.assertNotIn('("mute"', text)
        self.assertNotIn("disable port", text)

    def test_x_prefix_fits_safe_label_and_max_len(self):
        out = m.x_prefix_label("USW-10G-GFL-ACCE01_23")
        self.assertLessEqual(len(out), e.MAX_LABEL_LEN)
        self.assertTrue(out.startswith("X-"))


class DedupeAndCsvTests(unittest.TestCase):
    def test_stack_master_and_member_same_port_share_key(self):
        a = m.mute_dedupe_key("CORE01-1", "CORE01-1", "2:10")
        b = m.mute_dedupe_key("CORE01-1", "CORE01-2", "2/10")
        self.assertEqual(a, b)

    def test_csv_includes_action_and_status(self):
        plan = m.MutePlan(
            canary="CORE01::2:10", device="CORE01", ifname="2:10",
            kind="exos", action="shutdown", status="planned",
            commands=["disable port 2:10"],
        )
        csv_text = m.plans_to_csv([plan])
        self.assertIn("disable port 2:10", csv_text)
        self.assertIn("shutdown", csv_text)
        self.assertIn("planned", csv_text)


if __name__ == "__main__":
    unittest.main()
