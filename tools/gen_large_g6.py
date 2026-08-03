"""
Generate graph6 files for large graphs (n around and above 64/128 word
boundaries) to stress-test the words_per_vertex == 2 and > 2 code paths
(is_automorphism_two_words / is_automorphism_multiword) against pynauty.

Writes one .g6 file per size bucket into test_data/, each containing a mix
of random and highly-symmetric graphs (which exercise automorphism-group
discovery much harder than trivial random graphs do).

Usage (run via ./setup.sh, or manually against its venv):
    .venv-testdata/bin/python3 tools/gen_large_g6.py
"""

import pathlib
import networkx as nx

ROOT = pathlib.Path(__file__).parent.parent
TEST_DATA = ROOT / "test_data"

SIZES = [63, 64, 65, 100, 127, 128, 129, 192, 255, 256, 257, 383, 511, 512, 513]


def graphs_for_n(n: int):
    out = []

    out.append(("cycle", nx.cycle_graph(n)))
    out.append(("complete_bipartite", nx.complete_bipartite_graph(n // 2, n - n // 2)))
    out.append(("circulant_3", nx.circulant_graph(n, [1, 2, 3])))
    out.append(("path", nx.path_graph(n)))

    # Hypercube Q_k when n is a power of two.
    k = n.bit_length() - 1
    if (1 << k) == n:
        out.append(("hypercube", nx.hypercube_graph(k)))

    # Random graphs at a few densities, fixed seed for reproducibility.
    for p, tag in [(0.02, "sparse"), (0.1, "medium"), (0.5, "dense")]:
        g = nx.gnp_random_graph(n, p, seed=hash((n, tag)) & 0xFFFFFFFF)
        out.append((f"random_{tag}", g))

    # Relabel node sets to plain ints 0..n-1 (hypercube nodes are tuples).
    result = []
    for name, g in out:
        g = nx.convert_node_labels_to_integers(g)
        assert g.number_of_nodes() == n
        result.append((name, g))
    return result


def write_g6(path: pathlib.Path, graphs):
    with open(path, "wb") as f:
        for _name, g in graphs:
            f.write(nx.to_graph6_bytes(g, header=False))


def main():
    for n in SIZES:
        graphs = graphs_for_n(n)
        path = TEST_DATA / f"large_{n}.g6"
        write_g6(path, graphs)
        print(f"{path.name}: {len(graphs)} graphs written")


if __name__ == "__main__":
    main()
