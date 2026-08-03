"""
Generate pynauty reference files for graph6 test data.

For each .g6 file in test_data/, runs pynauty on up to MAX_GRAPHS graphs and
writes a binary reference file (<name>.ref) in the same directory.

Binary format (per graph, no framing):
  n : u32 LE       — number of vertices
  m : u32 LE       — words_per_vertex = ceil(n / 64)
  canonical : n*m * u64 LE   — canonical adjacency matrix, MSB-0 usize layout

Usage (run via ./setup.sh, or manually against its venv):
    .venv-testdata/bin/python3 tools/gen_g6_vectors.py
    .venv-testdata/bin/python3 tools/gen_g6_vectors.py --max 10000
"""

import struct
import sys
import pathlib
import argparse
import pynauty


WORD_BITS = 64
ROOT = pathlib.Path(__file__).parent.parent
TEST_DATA = ROOT / "test_data"


def words_needed(n: int) -> int:
    if n == 0:
        return 0
    return ((n - 1) >> 6) + 1


def decode_certificate(cert: bytes, n: int) -> list[int]:
    m = words_needed(n)
    result = []
    for i in range(n * m):
        chunk = cert[i * 8 : (i + 1) * 8]
        result.append(struct.unpack("<Q", chunk)[0])
    return result


def parse_g6_line(line: bytes):
    """Parse one graph6 line → (n, adjacency_dict). Returns None on error."""
    s = line.strip()
    if not s:
        return None
    if s.startswith(b">>graph6<<"):
        s = s[10:]
    if not s or s[0] in (ord(":"), ord("&")):
        return None

    pos = 0
    if s[pos] != 126:
        n = s[pos] - 63
        pos += 1
    elif pos + 1 < len(s) and s[pos + 1] != 126:
        if pos + 4 > len(s):
            return None
        n = ((s[pos + 1] - 63) << 12) | ((s[pos + 2] - 63) << 6) | (s[pos + 3] - 63)
        pos += 4
    else:
        if pos + 8 > len(s):
            return None
        n = (
            ((s[pos + 2] - 63) << 30)
            | ((s[pos + 3] - 63) << 24)
            | ((s[pos + 4] - 63) << 18)
            | ((s[pos + 5] - 63) << 12)
            | ((s[pos + 6] - 63) << 6)
            | (s[pos + 7] - 63)
        )
        pos += 8

    adj = {i: set() for i in range(n)}
    data = s[pos:]
    bit_idx = 0
    for j in range(1, n):
        for i in range(j):
            byte_pos = bit_idx // 6
            bit_in_byte = 5 - (bit_idx % 6)
            if byte_pos < len(data):
                raw = data[byte_pos]
                if ((raw - 63) >> bit_in_byte) & 1:
                    adj[i].add(j)
                    adj[j].add(i)
            bit_idx += 1

    return n, {i: sorted(adj[i]) for i in range(n)}


def process_file(g6_path: pathlib.Path, ref_path: pathlib.Path, max_graphs: int):
    count = 0
    errors = 0
    with open(g6_path, "rb") as src, open(ref_path, "wb") as dst:
        for line in src:
            if count >= max_graphs:
                break
            parsed = parse_g6_line(line)
            if parsed is None:
                errors += 1
                continue
            n, adj_dict = parsed
            m = words_needed(n)
            g = pynauty.Graph(n, adjacency_dict=adj_dict)
            cert = pynauty.certificate(g)
            canon = decode_certificate(cert, n)
            dst.write(struct.pack("<II", n, m))
            for w in canon:
                dst.write(struct.pack("<Q", w))
            count += 1
    return count, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max",
        type=int,
        default=5_000,
        help="Max graphs per file (default: 5000)",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Specific .g6 files to process (default: all in test_data/)",
    )
    args = parser.parse_args()

    if args.files:
        g6_files = [pathlib.Path(f) for f in args.files]
    else:
        g6_files = sorted(TEST_DATA.glob("*.g6"))

    for g6_path in g6_files:
        ref_path = g6_path.with_suffix(".ref")
        print(f"Processing {g6_path.name} → {ref_path.name} (max {args.max} graphs)...", end=" ", flush=True)
        count, errors = process_file(g6_path, ref_path, args.max)
        print(f"{count} graphs written, {errors} parse errors.")

    print("Done. Run `cargo test -- --ignored` to verify against pynauty.")


if __name__ == "__main__":
    main()
