"""
Generate a graph6 corpus of purely random G(n, p) graphs at small-to-medium n
(below the word-boundary sizes tools/gen_large_g6.py covers), for pynauty
ground-truth comparison. Structural corpora (test_data/*.g6 via geng) all have
some regularity by construction; this exercises canonicalization on graphs
with no special structure at all.

Usage (run via ./setup.sh, or manually against its venv):
    .venv-testdata/bin/python3 tools/gen_random_g6.py
"""

import pathlib
import networkx as nx

ROOT = pathlib.Path(__file__).parent.parent
TEST_DATA = ROOT / "test_data"

SIZES = [6, 8, 10, 12, 15, 20, 30, 40, 50]
DENSITIES = [0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95]


def main():
    graphs = []
    for n in SIZES:
        for p in DENSITIES:
            seed = hash((n, p)) & 0xFFFFFFFF
            graphs.append(nx.gnp_random_graph(n, p, seed=seed))

    path = TEST_DATA / "random_mixed.g6"
    with open(path, "wb") as f:
        for g in graphs:
            f.write(nx.to_graph6_bytes(g, header=False))
    print(f"{path.name}: {len(graphs)} graphs written")


if __name__ == "__main__":
    main()
