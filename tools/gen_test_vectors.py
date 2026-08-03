"""
Generate ground-truth test vectors for the Rust nauty implementation.

Uses pynauty (which wraps the original C nauty library) to compute canonical
forms, then encodes the adjacency matrix in the same MSB-0 bit-matrix format
that the Rust implementation uses (Vec<usize>, 64-bit words, MSB = vertex 0).

pynauty stores each 64-bit word in little-endian byte order, which on a 64-bit
LE machine matches the in-memory layout of Rust's usize directly.

Output: a Rust source file with hardcoded test cases.

Usage:
    .venv-testdata/bin/python3 tools/gen_test_vectors.py > src/test_vectors.rs
"""

import pynauty
import struct

WORD_BITS = 64


def words_needed(n: int) -> int:
    """Matches Rust's words_needed(n): ceil(n / 64)."""
    if n == 0:
        return 0
    return ((n - 1) >> 6) + 1


def decode_certificate(cert: bytes, n: int) -> list[int]:
    """
    Convert pynauty's certificate bytes to the Rust MSB-0 usize layout.

    pynauty stores each 64-bit word in little-endian byte order (native nauty
    format). On a 64-bit LE machine this is also the in-memory layout of usize.
    Vertex j lives in word j//64, at bit (63 - j%64) counted from the LSB
    (equivalently, bit j%64 counted from the MSB — i.e. MSB-0).
    """
    m = words_needed(n)
    result = []
    for i in range(n * m):
        chunk = cert[i * 8:(i + 1) * 8]
        val = struct.unpack('<Q', chunk)[0]  # little-endian u64
        result.append(val)
    return result


def extract_neighbors(canon: list[int], n: int, row: int) -> list[int]:
    """Read back the neighbor set from an MSB-0 canonical bit-matrix row."""
    m = words_needed(n)
    neighbors = []
    for wi in range(m):
        w = canon[row * m + wi]
        for bit in range(WORD_BITS):
            j = wi * WORD_BITS + bit
            if j < n and (w >> (WORD_BITS - 1 - bit)) & 1:
                neighbors.append(j)
    return neighbors


def verify_symmetric(canon: list[int], n: int) -> None:
    for i in range(n):
        for j in extract_neighbors(canon, n, i):
            assert i in extract_neighbors(canon, n, j), \
                f"Non-symmetric canonical graph: edge {i}-{j} is one-directional"


# ── Graph factories ──────────────────────────────────────────────────────────

def empty_adj(n): return [set() for _ in range(n)]
def sa(adj, u, v): adj[u].add(v); adj[v].add(u)

def directed_empty_adj(n): return [[] for _ in range(n)]
def da(adj, u, v): adj[u].append(v)  # directed arc u -> v only

def make_K(n):
    adj = empty_adj(n)
    for i in range(n):
        for j in range(i + 1, n): sa(adj, i, j)
    return adj, n

def make_cycle(n):
    adj = empty_adj(n)
    for i in range(n): sa(adj, i, (i + 1) % n)
    return adj, n

def make_path(n):
    adj = empty_adj(n)
    for i in range(n - 1): sa(adj, i, i + 1)
    return adj, n

def make_star(n):
    adj = empty_adj(n)
    for i in range(1, n): sa(adj, 0, i)
    return adj, n

def make_Kbip(p, q):
    n = p + q
    adj = empty_adj(n)
    for i in range(p):
        for j in range(p, n): sa(adj, i, j)
    return adj, n

def make_petersen():
    n = 10
    adj = empty_adj(n)
    for i in range(5): sa(adj, i, (i + 1) % 5)       # outer pentagon
    for i in range(5): sa(adj, i + 5, (i + 2) % 5 + 5)  # inner pentagram
    for i in range(5): sa(adj, i, i + 5)               # spokes
    return adj, n

def make_heawood():
    """Heawood graph (14 vertices, 21 edges) — the (3,6)-cage."""
    n = 14
    adj = empty_adj(n)
    for u, v in [(0,1),(0,5),(0,13),(1,2),(1,10),(2,3),(2,7),(3,4),(3,12),
                  (4,5),(4,9),(5,6),(6,7),(6,11),(7,8),(8,9),(8,13),
                  (9,10),(10,11),(11,12),(12,13)]:
        sa(adj, u, v)
    return adj, n

def make_cube():
    """Q_3 hypercube (8 vertices, 12 edges, 3-regular)."""
    n = 8
    adj = empty_adj(n)
    for i in range(n):
        for j in range(i + 1, n):
            if bin(i ^ j).count('1') == 1: sa(adj, i, j)
    return adj, n

def make_prism(k):
    n = 2 * k
    adj = empty_adj(n)
    for i in range(k):
        sa(adj, i, (i + 1) % k)
        sa(adj, i + k, (i + 1) % k + k)
        sa(adj, i, i + k)
    return adj, n

def make_empty(n): return empty_adj(n), n

def make_bull():
    """Bull graph: K3 with two pendant edges (5 vertices)."""
    n = 5; adj = empty_adj(n)
    sa(adj, 0, 1); sa(adj, 1, 2); sa(adj, 0, 2)  # triangle
    sa(adj, 0, 3); sa(adj, 1, 4)                   # pendants
    return adj, n

def make_house():
    """House graph: C4 plus a triangle on top (5 vertices)."""
    n = 5; adj = empty_adj(n)
    sa(adj, 0, 1); sa(adj, 1, 2); sa(adj, 2, 3); sa(adj, 3, 0)  # square
    sa(adj, 0, 4); sa(adj, 1, 4)                                  # roof
    return adj, n

def make_diamond():
    """Diamond graph: K4 minus one edge (4 vertices)."""
    n = 4; adj = empty_adj(n)
    sa(adj, 0, 1); sa(adj, 0, 2); sa(adj, 0, 3); sa(adj, 1, 2); sa(adj, 2, 3)
    return adj, n

def make_paw():
    """Paw graph: K3 plus one pendant edge (4 vertices)."""
    n = 4; adj = empty_adj(n)
    sa(adj, 0, 1); sa(adj, 1, 2); sa(adj, 0, 2); sa(adj, 2, 3)
    return adj, n

# ── Directed graph factories ─────────────────────────────────────────────────

def make_dir_cycle(n):
    """Directed n-cycle: arcs i -> (i+1) mod n. |Aut| = n (rotations only, no
    reflections — distinguishes digraph mode from the underlying undirected cycle,
    whose group is the dihedral group of order 2n)."""
    adj = directed_empty_adj(n)
    for i in range(n): da(adj, i, (i + 1) % n)
    return adj, n

def make_dir_path(n):
    """Directed path: arcs i -> i+1. Trivial automorphism group (no reversal
    symmetry, unlike the undirected path)."""
    adj = directed_empty_adj(n)
    for i in range(n - 1): da(adj, i, i + 1)
    return adj, n

def make_transitive_tournament(n):
    """Transitive tournament: arc i -> j for every i < j. Every vertex has a
    distinct out-degree, so |Aut| = 1."""
    adj = directed_empty_adj(n)
    for i in range(n):
        for j in range(i + 1, n):
            da(adj, i, j)
    return adj, n

def make_out_star(n):
    """Out-star: arcs 0 -> i for i in 1..n. Center has out-degree n-1 and
    in-degree 0; leaves are mutually interchangeable (|Aut| = (n-1)!)."""
    adj = directed_empty_adj(n)
    for i in range(1, n): da(adj, 0, i)
    return adj, n

def make_in_star(n):
    """In-star: arcs i -> 0 for i in 1..n. Mirror of make_out_star; a distinct
    test because in- and out-degree are not interchangeable for a digraph."""
    adj = directed_empty_adj(n)
    for i in range(1, n): da(adj, i, 0)
    return adj, n

# ── Graphs to test ──────────────────────────────────────────────────────────

GRAPHS = {
    # Trivial
    "K1":         make_K(1),
    "K2":         make_K(2),
    "Empty3":     make_empty(3),
    # Complete
    "K3":         make_K(3),
    "K4":         make_K(4),
    "K5":         make_K(5),
    "K6":         make_K(6),
    # Cycles
    "C4":         make_cycle(4),
    "C5":         make_cycle(5),
    "C6":         make_cycle(6),
    "C7":         make_cycle(7),
    # Paths
    "P2":         make_path(2),
    "P3":         make_path(3),
    "P5":         make_path(5),
    "P10":        make_path(10),
    # Stars (K_{1,k})
    "Star4":      make_star(4),
    "Star6":      make_star(6),
    # Bipartite
    "K23":        make_Kbip(2, 3),
    "K33":        make_Kbip(3, 3),
    "K44":        make_Kbip(4, 4),
    # Named graphs
    "Petersen":   make_petersen(),
    "Heawood":    make_heawood(),
    "Cube":       make_cube(),
    "Prism3":     make_prism(3),
    "Prism5":     make_prism(5),
    # Small interesting graphs
    "Bull":       make_bull(),
    "House":      make_house(),
    "Diamond":    make_diamond(),
    "Paw":        make_paw(),
}

DIGRAPHS = {
    "DirCycle3":  make_dir_cycle(3),
    "DirCycle4":  make_dir_cycle(4),
    "DirCycle5":  make_dir_cycle(5),
    "DirPath4":   make_dir_path(4),
    "DirPath6":   make_dir_path(6),
    "TT3":        make_transitive_tournament(3),
    "TT4":        make_transitive_tournament(4),
    "TT5":        make_transitive_tournament(5),
    "OutStar4":   make_out_star(4),
    "InStar4":    make_in_star(4),
}


def run_pynauty(adj, n: int, directed: bool = False) -> dict:
    g = pynauty.Graph(n, directed=directed, adjacency_dict={i: sorted(adj[i]) for i in range(n)})
    cert = pynauty.certificate(g)
    gens, grpsize1, grpsize2, orbits, numorbits = pynauty.autgrp(g)
    canon = decode_certificate(cert, n)
    if not directed:
        verify_symmetric(canon, n)
    return {
        "n": n,
        "m": words_needed(n),
        "canon": canon,
        "grpsize1": grpsize1,
        "grpsize2": grpsize2,
        "numorbits": numorbits,
        "orbits": orbits,
        "directed": directed,
    }


results = {}
for name, (adj, n) in GRAPHS.items():
    results[name] = run_pynauty(adj, n, directed=False)
for name, (adj, n) in DIGRAPHS.items():
    results[name] = run_pynauty(adj, n, directed=True)

# ── Emit Rust ────────────────────────────────────────────────────────────────

print("""\
//! Known canonical graph forms for testing the canonaut implementation.
//!
//! AUTO-GENERATED by tools/gen_test_vectors.py — DO NOT EDIT BY HAND.
//! To regenerate:
//!   .venv-testdata/bin/python3 tools/gen_test_vectors.py > src/test_vectors.rs
//!
//! The canonical adjacency matrix is stored in the same MSB-0 usize bit-matrix
//! format as the Rust implementation:
//!   - n*m words total (n rows, m=ceil(n/64) words per row)
//!   - Vertex j in row i: word j/64, bit mask = 1 << (63 - j%64)
//!   - Equivalent: bit j from the MSB of the word
//!
//! Each TestVector also records automorphism group statistics from pynauty,
//! which the Rust implementation computes via Statistics. The group order is:
//!   grpsize1 * 2^grpsize2

pub struct TestVector {
    pub name: &'static str,
    pub number_of_vertices: usize,
    pub words_per_vertex: usize,
    pub canon: &'static [usize],
    /// Group size mantissa (group_size1 * 2^group_size2 = automorphism group order)
    pub group_size1: f64,
    pub group_size2: i32,
    pub number_of_orbits: usize,
    /// Whether `canon` was computed with pynauty's `directed=True` (digraph mode).
    pub directed: bool,
}

pub static TEST_VECTORS: &[TestVector] = &[\
""")

for name, r in results.items():
    canon_items = ", ".join(f"0x{x:016x}_usize" for x in r["canon"])
    directed_literal = "true" if r["directed"] else "false"
    print(f"""    TestVector {{
        name: "{name}",
        number_of_vertices: {r['n']},
        words_per_vertex: {r['m']},
        canon: &[{canon_items}],
        group_size1: {r['grpsize1']}_f64,
        group_size2: {r['grpsize2']}_i32,
        number_of_orbits: {r['numorbits']},
        directed: {directed_literal},
    }},""")

print("];")
