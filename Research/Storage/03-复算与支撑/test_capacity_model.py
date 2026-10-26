"""Meaningful arithmetic and input-contract checks; Proof of Love2."""
import json
import unittest
from decimal import Decimal
from pathlib import Path
from capacity_model import calculate, run_scenarios


class CapacityTests(unittest.TestCase):
    def setUp(self):
        data = json.loads(Path(__file__).with_name('scenarios.json').read_text(encoding='utf-8'))
        self.params = {**data['common'], **data['scenarios']['E0']}

    def test_exact_toy_components(self):
        p = dict(self.params, events_per_day=10, retention_days=2, payload_bytes=100,
                 indexed_fraction=0.5, vectors_per_indexed_event=2, dimensions=4,
                 float_bytes=2, graph_degree=3, neighbor_bytes=8,
                 node_overhead_bytes=4, pq_code_bytes=4, metadata_bytes=10,
                 hot_days=1)
        expected = {'events': 20, 'vectors': 20, 'raw_logical_bytes': 2000,
                    'archive_physical_bytes': 1500, 'canonical_vectors_physical_bytes': 320,
                    'ann_physical_bytes': 1280, 'metadata_physical_bytes': 400,
                    'hot_cache_extra_bytes': 500, 'rebuild_temporary_bytes': 1600,
                    'peak_used_bytes': 5600}
        q = calculate(p)
        for name, value in expected.items():
            self.assertEqual(q[name], Decimal(value), name)
        self.assertEqual(q['provisioned_bytes'], Decimal(5600) / Decimal('0.75'))

    def test_reserve_is_fraction_of_provisioned_space(self):
        q = calculate(self.params)
        self.assertEqual(q['provisioned_bytes'] * Decimal('0.75'), q['peak_used_bytes'])
        self.assertNotEqual(q['provisioned_bytes'], q['peak_used_bytes'] * Decimal('1.25'))

    def test_index_fraction_multiplicity_and_dimensions(self):
        base = calculate(self.params)
        for key in ('indexed_fraction', 'vectors_per_indexed_event', 'dimensions'):
            with self.subTest(key=key):
                increased = calculate(dict(self.params, **{key: self.params[key] * 2}))
                self.assertGreater(increased['provisioned_bytes'], base['provisioned_bytes'])
                self.assertEqual(increased['canonical_vectors_physical_bytes'],
                                 base['canonical_vectors_physical_bytes'] * 2)
                self.assertEqual(increased['archive_physical_bytes'], base['archive_physical_bytes'])
                if key == 'dimensions':
                    self.assertEqual(increased['ann_physical_bytes'], base['ann_physical_bytes'])

    def test_invalid_values_for_every_numeric_field(self):
        for key in self.params:
            for value in (-1, float('nan'), float('inf'), -float('inf'), True, False, '1'):
                with self.subTest(key=key, value=value):
                    with self.assertRaises(ValueError):
                        calculate(dict(self.params, **{key: value}))

    def test_fraction_bounds_and_noninteger_counts(self):
        for key, value in [('indexed_fraction', 1.01), ('compression_ratio', 0),
                           ('free_reserve_fraction', 1),
                           ('archive_ec_factor', 0.9), ('hot_days', 366),
                           ('dimensions', 1.5), ('events_per_day', 0)]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                calculate(dict(self.params, **{key: value}))

    def test_encoded_payload_expansion(self):
        base = calculate(self.params)
        expanded = calculate(dict(self.params, compression_ratio=1.2))
        for key in ('archive_physical_bytes', 'hot_cache_extra_bytes'):
            self.assertEqual(expanded[key], base[key] * Decimal('2.4'))
        for key in ('canonical_vectors_physical_bytes', 'ann_physical_bytes',
                    'metadata_physical_bytes', 'rebuild_temporary_bytes'):
            self.assertEqual(expanded[key], base[key])
        self.assertGreater(expanded['provisioned_bytes'], base['provisioned_bytes'])

    def test_complete_closed_schema(self):
        missing = dict(self.params)
        missing.pop('dimensions')
        for invalid in (missing, dict(self.params, typo=1), [], None):
            with self.assertRaises(ValueError):
                calculate(invalid)
        with self.assertRaises(ValueError):
            run_scenarios({'common': self.params, 'scenarios': {'X': {'dimensions': 1}}})

    def test_zero_index_fraction_does_not_remove_archive_or_metadata(self):
        q = calculate(dict(self.params, indexed_fraction=0))
        for key in ('vectors', 'ann_physical_bytes', 'canonical_vectors_physical_bytes',
                    'rebuild_temporary_bytes'):
            self.assertEqual(q[key], 0)
        self.assertGreater(q['archive_physical_bytes'], 0)
        self.assertGreater(q['metadata_physical_bytes'], 0)


if __name__ == '__main__':
    unittest.main()
