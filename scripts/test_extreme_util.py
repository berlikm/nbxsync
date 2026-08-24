#!/usr/bin/env python3
"""EXOS template {$IF.UTIL.MAX}=101 must win over stock 90."""

from __future__ import annotations

import unittest

from extreme_util import (
    IF_UTIL_MAX_MACRO,
    IF_UTIL_MAX_OFF,
    effective_macro_from_layers,
    if_util_is_off,
)


class IfUtilPrecedenceTests(unittest.TestCase):
    def test_off_value(self):
        self.assertTrue(if_util_is_off('101'))
        self.assertFalse(if_util_is_off('90'))

    def test_stock_template_90_beats_global_until_patched(self):
        value, source = effective_macro_from_layers(
            host={},
            inherited={},
            template={IF_UTIL_MAX_MACRO: '90'},
            global_macros={IF_UTIL_MAX_MACRO: IF_UTIL_MAX_OFF},
            name=IF_UTIL_MAX_MACRO,
        )
        self.assertEqual(value, '90')
        self.assertEqual(source, 'template')
        self.assertFalse(if_util_is_off(value))

    def test_patched_template_101(self):
        value, source = effective_macro_from_layers(
            host={},
            inherited={IF_UTIL_MAX_MACRO: IF_UTIL_MAX_OFF},
            template={IF_UTIL_MAX_MACRO: IF_UTIL_MAX_OFF},
            global_macros={IF_UTIL_MAX_MACRO: IF_UTIL_MAX_OFF},
            name=IF_UTIL_MAX_MACRO,
        )
        self.assertEqual((value, source), (IF_UTIL_MAX_OFF, 'inherited'))
        self.assertTrue(if_util_is_off(value))

    def test_host_override_wins(self):
        value, source = effective_macro_from_layers(
            host={IF_UTIL_MAX_MACRO: '80'},
            inherited={IF_UTIL_MAX_MACRO: IF_UTIL_MAX_OFF},
            template={IF_UTIL_MAX_MACRO: IF_UTIL_MAX_OFF},
            global_macros={IF_UTIL_MAX_MACRO: IF_UTIL_MAX_OFF},
            name=IF_UTIL_MAX_MACRO,
        )
        self.assertEqual((value, source), ('80', 'host'))


if __name__ == '__main__':
    unittest.main()
