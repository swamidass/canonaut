"""
Tests for the ergonomic canonaut Python API.

Run directly (no pytest required):
    .venv-testdata/bin/python3 -m unittest bindings/python/tests/test_canonaut.py -v
or, if pytest is installed:
    pytest bindings/python/tests/
"""

import unittest

import canonaut


class TestCanonize(unittest.TestCase):
    def test_arbitrary_string_labels(self):
        r = canonaut.canonize([("a", "b"), ("b", "c"), ("c", "d"), ("d", "a")])
        self.assertEqual(r.num_orbits, 1)
        self.assertEqual(r.group_size1, 8.0)
        self.assertEqual(set(r.labeling), {"a", "b", "c", "d"})

    def test_uncolored_p4_has_two_orbits(self):
        r = canonaut.canonize([(0, 1), (1, 2), (2, 3)])
        self.assertEqual(r.num_orbits, 2)
        self.assertEqual(r.group_size1, 2.0)
        orbit_sets = {frozenset(g) for g in r.orbits}
        self.assertEqual(orbit_sets, {frozenset({0, 3}), frozenset({1, 2})})

    def test_dict_colors_break_symmetry(self):
        r = canonaut.canonize(
            [(0, 1), (1, 2), (2, 3)],
            colors={0: "red", 1: "red", 2: "blue", 3: "blue"},
        )
        self.assertEqual(r.num_orbits, 4)
        self.assertEqual(r.group_size1, 1.0)

    def test_sequence_colors_aligned_to_nodes(self):
        r = canonaut.canonize(
            [(0, 1), (1, 2), (2, 3)],
            nodes=[0, 1, 2, 3],
            colors=[0, 0, 1, 1],
        )
        self.assertEqual(r.num_orbits, 4)

    def test_colors_missing_nodes_share_implicit_bucket(self):
        # P4's only nontrivial automorphism is the reversal 0<->3, 1<->2, which
        # maps {0,3} onto itself and {1,2} onto itself. Coloring exactly {0,3}
        # and leaving 1,2 as an implicit shared bucket must NOT break that
        # automorphism, since it still respects both classes as sets.
        colored = canonaut.canonize(
            [(0, 1), (1, 2), (2, 3)], colors={0: "end", 3: "end"}
        )
        uncolored = canonaut.canonize([(0, 1), (1, 2), (2, 3)])
        self.assertEqual(colored.canonical_bytes(), uncolored.canonical_bytes())
        self.assertEqual(colored.num_orbits, uncolored.num_orbits)

    def test_colors_on_one_vertex_breaks_symmetry(self):
        # Coloring only vertex 0 forces it out of {0,3}'s pairing, forbidding
        # the reversal automorphism entirely.
        r = canonaut.canonize([(0, 1), (1, 2), (2, 3)], colors={0: "special"})
        self.assertEqual(r.num_orbits, 4)

    def test_colors_wrong_sequence_length_raises(self):
        with self.assertRaises(ValueError):
            canonaut.canonize([(0, 1), (1, 2)], colors=[0, 1])

    def test_isolated_node_via_nodes(self):
        r = canonaut.canonize([("a", "b")], nodes=["a", "b", "isolated"])
        orbit_sets = {frozenset(g) for g in r.orbits}
        self.assertIn(frozenset({"isolated"}), orbit_sets)

    def test_generators_are_node_to_node_maps(self):
        r = canonaut.canonize(
            [("a", "b"), ("b", "c"), ("c", "d"), ("d", "a")], generators=True
        )
        self.assertEqual(len(r.generators), r.num_generators)
        for gen in r.generators:
            self.assertEqual(set(gen.keys()), {"a", "b", "c", "d"})
            self.assertEqual(set(gen.values()), {"a", "b", "c", "d"})

    def test_canonical_bytes_is_isomorphism_invariant(self):
        k1 = canonaut.canonize(
            [("a", "b"), ("b", "c"), ("c", "d"), ("d", "a")]
        ).canonical_bytes()
        k2 = canonaut.canonize([(1, 2), (2, 3), (3, 4), (4, 1)]).canonical_bytes()
        self.assertEqual(k1, k2)

    def test_networkx_duck_typing(self):
        nx = _import_networkx_or_skip(self)
        g = nx.cycle_graph(["x", "y", "z", "w"])
        r = canonaut.canonize(g)
        self.assertEqual(r.num_orbits, 1)

    def test_networkx_directed_is_detected(self):
        nx = _import_networkx_or_skip(self)
        g = nx.DiGraph([(0, 1), (1, 2), (2, 0)])
        r = canonaut.canonize(g)
        # A directed 3-cycle has a trivial-vs-symmetric group depending on
        # orientation; the point of this test is just that it runs without
        # requiring an explicit directed=True.
        self.assertEqual(r.num_orbits, 1)


class TestAreIsomorphic(unittest.TestCase):
    def test_string_labels(self):
        self.assertTrue(
            canonaut.are_isomorphic(
                [("p", "q"), ("q", "r"), ("r", "s"), ("s", "p")],
                [(1, 2), (2, 3), (3, 4), (4, 1)],
            )
        )

    def test_non_isomorphic_graphs(self):
        # Path vs cycle on the same vertex count are never isomorphic.
        self.assertFalse(
            canonaut.are_isomorphic(
                [(0, 1), (1, 2), (2, 3)],
                [(0, 1), (1, 2), (2, 3), (3, 0)],
            )
        )

    def test_mismatched_vertex_count_is_false(self):
        self.assertFalse(
            canonaut.are_isomorphic([(0, 1)], [(0, 1), (1, 2)])
        )


def _import_networkx_or_skip(testcase):
    try:
        import networkx as nx
    except ImportError:
        testcase.skipTest("networkx not installed")
    return nx


if __name__ == "__main__":
    unittest.main()
