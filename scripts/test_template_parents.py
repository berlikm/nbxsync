#!/usr/bin/env python3
"""Pure-function tests for HostSync nested-parent skipping (no Django)."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'nbxsync' / 'utils' / 'sync' / 'template_parents.py'


def _load():
    spec = importlib.util.spec_from_file_location('template_parents', MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class NestedParentSkipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_fortigate_observability_plus_icmp(self):
        drop = self.mod.drop_nested_parent_templateids
        obs, http, icmp = 13901, 10002, 10001
        parent_map = {obs: [http, icmp], http: [icmp], icmp: []}
        self.assertEqual(drop([icmp, http, obs], parent_map), [obs])

    def test_fetch_walks_http_when_only_obs_and_icmp_are_intended(self):
        fetch = self.mod.fetch_template_parent_map
        drop = self.mod.drop_nested_parent_templateids
        rows = {1: [2], 2: [3], 3: []}

        def getter(ids):
            return [
                {'templateid': tid, 'parentTemplates': [{'templateid': p} for p in rows[tid]]}
                for tid in ids
            ]

        parent_map = fetch([1, 3], getter)
        self.assertEqual(drop([1, 3], parent_map), [1])


if __name__ == '__main__':
    unittest.main()
