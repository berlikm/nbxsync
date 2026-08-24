#!/usr/bin/env python3
"""Unicode operators must not land in Zabbix problem titles."""

from __future__ import annotations

import unittest

from extreme_ascii_titles import (
    ascii_zabbix_title,
    title_needs_ascii,
    title_payload,
    yaml_title_fields_needing_ascii,
)


_OLD = (
    'Port identity: Interface 1:24(USW-1G-L02-D01_4): '
    'Speed {ITEM.LASTVALUE1} ≠ expected {#IF.SPEED.EXPECTED} Mbps (class {#IF.CLASS})'
)
_WANT = (
    'Port identity: Interface 1:24(USW-1G-L02-D01_4): '
    'Speed {ITEM.LASTVALUE1} != expected {#IF.SPEED.EXPECTED} Mbps (class {#IF.CLASS})'
)


class AsciiTitleTests(unittest.TestCase):
    def test_neq_becomes_ascii(self):
        self.assertEqual(ascii_zabbix_title(_OLD), _WANT)
        self.assertTrue(title_needs_ascii(_OLD))
        self.assertFalse(title_needs_ascii(_WANT))

    def test_cp437_mojibake(self):
        mojibake = _OLD.replace('\u2260', 'Γëá')
        self.assertEqual(ascii_zabbix_title(mojibake), _WANT)

    def test_payload_rewrites_event_name_only(self):
        row = {
            'triggerid': '9',
            'description': 'Port identity: Interface {#IFNAME}({#IFALIAS}): Speed not equal to expected {#IF.SPEED.EXPECTED} Mbps',
            'event_name': _OLD,
        }
        self.assertEqual(title_payload(row), {'event_name': _WANT})

    def test_payload_empty_when_already_ascii(self):
        self.assertEqual(
            title_payload({'triggerid': '1', 'description': 'Speed not equal', 'event_name': _WANT}),
            {},
        )

    def test_yaml_walk_flags_event_name(self):
        got = yaml_title_fields_needing_ascii({'name': 'Speed not equal', 'event_name': _OLD})
        self.assertEqual(got, [f'event_name={_OLD}'])

    def test_yaml_walk_accepts_ascii_ne(self):
        self.assertEqual(
            yaml_title_fields_needing_ascii({'name': 'Speed not equal', 'event_name': _WANT}),
            [],
        )


if __name__ == '__main__':
    unittest.main()
