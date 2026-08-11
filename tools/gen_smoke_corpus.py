"""
Build the small, committed cross-validation corpus in `test_data/smoke/`.

Unlike the full corpora (which `./setup.sh` regenerates and `.gitignore`
excludes, ~125 MB), this corpus is committed so that a plain `cargo test` on a
fresh clone runs the pynauty cross-validation without any external tooling.

For each source corpus it takes an evenly spaced sample of graphs and writes

    test_data/smoke/<name>.g6    the sampled graph6 lines
    test_data/smoke/<name>.ref   pynauty canonical forms (same binary layout
                                 as tools/gen_g6_vectors.py)

Usage (needs the venv built by ./setup.sh):
    .venv-testdata/bin/python3 tools/gen_smoke_corpus.py
"""

import pathlib
import struct
import sys

import pynauty

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_g6_vectors import decode_certificate, parse_g6_line, words_needed  # noqa: E402

ROOT = pathlib.Path(__file__).parent.parent
TEST_DATA = ROOT / "test_data"
SMOKE = TEST_DATA / "smoke"

# (source corpus, number of graphs to sample)
# Small corpora: enough graphs to cover many distinct symmetry types.
# Large corpora: a handful each, chosen at the m = 1 / 2 / >2 word boundaries
# so the word-count-specialised code paths are exercised on a fresh clone.
SAMPLES = [
    ("all_9", 300),
    ("bipartite_10", 200),
    ("connected_10", 200),
    ("cubic_10", 21),
    ("triangle_free_11", 200),
    ("perfect_9", 150),
    ("chordal_9", 150),
    ("clawfree_9", 150),
    ("k4free_9", 150),
    ("biconnected_9", 150),
    ("regular4_10", 60),
    ("split_10", 150),
    ("random_mixed", 100),
    ("large_63", 4),
    ("large_64", 4),
    ("large_65", 4),
    ("large_127", 3),
    ("large_128", 3),
    ("large_129", 3),
]


def sample_lines(path: pathlib.Path, count: int) -> list[bytes]:
    """Evenly spaced sample of `count` graph6 lines (deterministic)."""
    lines = [line.strip() for line in path.read_bytes().splitlines() if line.strip()]
    if len(lines) <= count:
        return lines
    stride = len(lines) / count
    return [lines[int(index * stride)] for index in range(count)]


def main():
    if not TEST_DATA.is_dir():
        sys.exit("test_data/ missing — run ./setup.sh first")
    SMOKE.mkdir(exist_ok=True)

    total_graphs = 0
    for name, count in SAMPLES:
        source = TEST_DATA / f"{name}.g6"
        if not source.exists():
            print(f"skipping {name}: {source} not found")
            continue

        # Keep only lines that parse, so the .g6 and .ref files stay aligned
        # graph-for-graph (the Rust test walks both sequentially).
        sampled = [(line, parse_g6_line(line)) for line in sample_lines(source, count)]
        sampled = [(line, parsed) for line, parsed in sampled if parsed is not None]
        (SMOKE / f"{name}.g6").write_bytes(b"\n".join(line for line, _ in sampled) + b"\n")

        with open(SMOKE / f"{name}.ref", "wb") as out:
            written = 0
            for _, parsed in sampled:
                n, adjacency = parsed
                canon = decode_certificate(
                    pynauty.certificate(pynauty.Graph(n, adjacency_dict=adjacency)), n
                )
                out.write(struct.pack("<II", n, words_needed(n)))
                for word in canon:
                    out.write(struct.pack("<Q", word))
                written += 1

        total_graphs += written
        print(f"{name}: {written} graphs")

    size = sum(f.stat().st_size for f in SMOKE.iterdir())
    print(f"\n{total_graphs} graphs in {SMOKE} ({size / 1024:.0f} KiB)")


if __name__ == "__main__":
    main()
