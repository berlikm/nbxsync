from django.test import TestCase

from nbxsync.utils.sync.template_parents import drop_nested_parent_templateids, fetch_template_parent_map


class DropNestedParentTemplateidsTestCase(TestCase):
    def test_observability_plus_icmp_keeps_only_observability(self):
        obs, http, icmp = 13901, 10002, 10001
        parent_map = {obs: [http, icmp], http: [icmp], icmp: []}
        self.assertEqual(
            drop_nested_parent_templateids([icmp, obs], parent_map),
            [obs],
        )

    def test_transitive_icmp_via_http_is_dropped(self):
        obs, http, icmp = 1, 2, 3
        parent_map = {obs: [http], http: [icmp], icmp: []}
        self.assertEqual(
            drop_nested_parent_templateids([obs, icmp], parent_map),
            [obs],
        )

    def test_siblings_are_kept(self):
        obs, snmp = 1, 4
        parent_map = {obs: [2, 3], snmp: []}
        self.assertEqual(
            drop_nested_parent_templateids([obs, snmp], parent_map),
            [obs, snmp],
        )

    def test_single_template_is_kept(self):
        self.assertEqual(drop_nested_parent_templateids([10001], {10001: []}), [10001])

    def test_dedupes_and_coerces_strings(self):
        self.assertEqual(
            drop_nested_parent_templateids(['10', 10, '20'], {10: [], 20: []}),
            [10, 20],
        )

    def test_empty_intended(self):
        self.assertEqual(drop_nested_parent_templateids([], {}), [])


class FetchTemplateParentMapTestCase(TestCase):
    def test_walks_unintended_parents(self):
        rows = {
            1: [2],
            2: [3],
            3: [],
        }
        calls = []

        def getter(ids):
            calls.append(tuple(ids))
            return [
                {
                    'templateid': tid,
                    'parentTemplates': [{'templateid': pid} for pid in rows[tid]],
                }
                for tid in ids
                if tid in rows
            ]

        parent_map = fetch_template_parent_map([1, 3], getter)
        self.assertEqual(parent_map[1], [2])
        self.assertEqual(parent_map[2], [3])
        self.assertEqual(drop_nested_parent_templateids([1, 3], parent_map), [1])
        fetched = {tid for batch in calls for tid in batch}
        self.assertEqual(fetched, {1, 2, 3})
