#!/usr/bin/env python3
"""EtherLike FCS rate Warning must ignore counter resets."""

from __future__ import annotations

import unittest

from extreme_fcs import (
    FCS_KEY,
    fcs_expr_is_rate_with_hysteresis,
    fcs_rate_expr,
    fcs_recovery_expr,
)


class FcsExprTests(unittest.TestCase):
    def test_voss_shape(self):
        expr = fcs_rate_expr('Extreme VOSS by SNMP')
        self.assertTrue(fcs_expr_is_rate_with_hysteresis(expr))
        self.assertIn(FCS_KEY, expr)
        self.assertIn('ifCounterDiscontinuityTime', expr)
        rec = fcs_recovery_expr('Extreme VOSS by SNMP')
        self.assertIn('*0.8', rec)


if __name__ == '__main__':
    unittest.main()
