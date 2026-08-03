# canonaut

A safe, native Rust implementation of [nauty](https://pallini.di.uniroma1.it/) — McKay's algorithm for computing graph automorphism groups and canonical labelings.

Given a graph, `canonaut` finds:
- **Canonical form** — a unique representative of the isomorphism class; two graphs are isomorphic iff their canonical forms are identical
- **Automorphism group** — generators of the symmetry group, plus orbit information and group size

## `DenseGraph` — building a graph

`DenseGraph` stores adjacency as a flat bit-matrix and tracks its own directedness and (optional) vertex coloring.

```rust
use canonaut::structs::DenseGraph;

let mut graph = DenseGraph::new(4);
// 4-cycle: 0-1-2-3-0
graph.add_edge(0, 1);
graph.add_edge(1, 2);
graph.add_edge(2, 3);
graph.add_edge(3, 0);
```

A graph's directedness is fixed at construction: `DenseGraph::new` / `add_edge` for
undirected graphs, `DenseGraph::new_directed` / `add_arc` for digraphs. Calling the
wrong one of `add_edge`/`add_arc` panics rather than silently producing a malformed
adjacency matrix.

## `CanonautManager` — high-level API

`CanonautManager` owns all working buffers and reuses them across calls. Allocate once, run many times — zero allocation on the hot path as long as the graph order doesn't grow.

### Canonicalization

```rust
use canonaut::structs::{CanonautManager, DenseGraph};

fn main() {
    let n = 4;
    let mut g = DenseGraph::new(n);
    g.add_edge(0, 1);
    g.add_edge(1, 2);
    g.add_edge(2, 3);
    g.add_edge(3, 0);

    let mut manager = CanonautManager::new(n).with_canonization();
    manager.canonize_graph(&g);

    println!("Orbits: {}", manager.statistics().number_of_orbits);
    println!("Canon:  {:?}", manager.canonical_graph);
}
```

`canonize_graph` reads `graph.is_directed()` and configures digraph mode automatically —
no separate builder call needed for digraphs.

### Automorphism group info

After `canonize_graph`, `statistics()` reports the group:

```rust
let stats = manager.statistics();
// Group size = stats.group_size1 * 10^stats.group_size2
println!("group size: {}e{}", stats.group_size1, stats.group_size2);
println!("orbits:     {}", stats.number_of_orbits);
println!("generators: {}", stats.number_of_generators);
```

### Batch canonicalization (reuse manager)

Buffers are only resized when the graph order increases:

```rust
let mut manager = CanonautManager::new(max_n).with_canonization();
for g in graph_database.iter() {
    manager.canonize_graph(g); // g: &DenseGraph
    // use manager.canonical_graph, .labeling(), .orbits() ...
}
```

### Isomorphism testing

Two graphs are isomorphic iff their canonical forms coincide:

```rust
let canon_g = {
    let mut mgr = CanonautManager::new(n).with_canonization();
    mgr.canonize_graph(&g);
    mgr.canonical_graph.clone()
};
let canon_h = {
    let mut mgr = CanonautManager::new(n).with_canonization();
    mgr.canonize_graph(&h);
    mgr.canonical_graph.clone()
};
assert_eq!(canon_g, canon_h); // isomorphic iff equal
```

### Vertex-colored (partitioned) canonicalization

Coloring constrains the search: vertices of different colors are never identified by
an automorphism, and the canonical form respects the coloring. Attach a coloring to
the graph itself with `set_colors` (picked up automatically by `canonize_graph`), or
pass colors explicitly per call with `canonize_with_colors` / `canonize_graph_with_colors`
to canonicalize the same graph under several different colorings.

```rust
let mut path_p4 = DenseGraph::new(4); // 0-1-2-3
path_p4.add_edge(0, 1);
path_p4.add_edge(1, 2);
path_p4.add_edge(2, 3);

let mut manager = CanonautManager::new(4).with_canonization();
manager.canonize_graph(&path_p4);
// uncolored: 2 orbits, |Aut| = 2

path_p4.set_colors(vec![0, 0, 1, 1]);
manager.canonize_graph(&path_p4);
// colored: 4 orbits, |Aut| = 1 (picked up automatically)
```

### Directed graphs

```rust
let mut g = DenseGraph::new_directed(4);
g.add_arc(0, 1);
g.add_arc(1, 2);
g.add_arc(2, 3);
g.add_arc(3, 0);

let mut manager = CanonautManager::new(4).with_canonization();
manager.canonize_graph(&g); // digraph mode set automatically
println!("|Aut| = {}", manager.statistics().group_size1); // 4.0
```

### Automorphism generators

Register a callback with the same signature as nauty's `userautomproc` to receive
every generator permutation found:

```rust
fn on_automorphism(n: u32, perm: &mut [u32], orbits: &mut [u32], num_orbits: u32, stabvert: u32, index: u32) {
    println!("{:?}", perm);
}

let mut manager = CanonautManager::new(4)
    .with_canonization()
    .with_automorphism_callback(on_automorphism);
```

## Low-level API

Use `canonaut::structs::add_one_edge`/`add_one_arc` and `CanonautManager::canonize`
directly when working with raw adjacency slices instead of `DenseGraph` — e.g. when
integrating with `graph6` I/O (`canonaut::graph6`) or other external representations.

```rust
use canonaut::structs::{CanonautManager, add_one_edge};
use canonaut::utilities::words_needed;

let n = 6;
let m = words_needed(n) as u32;

// Build a cycle C6
let mut g = vec![0usize; n * m as usize];
for i in 0..n {
    add_one_edge(&mut g, i, (i + 1) % n, m);
}

let mut manager = CanonautManager::new(n).with_canonization();
manager.canonize(&g);
let canon = manager.take_canonical_graph();
println!("{:?}", canon);
```

## Key types

| Type | Location | Purpose |
|------|----------|---------|
| `CanonautManager` | `canonaut::structs` | High-level manager; owns all buffers |
| `DenseGraph` | `canonaut::structs` | Dense graph container (adjacency + directedness + coloring) |
| `CanonautOptions` | `canonaut::structs` | Algorithm configuration |
| `Statistics` | `canonaut::structs` | Output: group size, orbit count, search tree stats |
| `add_one_edge` | `canonaut::structs` | Add undirected edge to a raw flat adjacency bitmatrix |
| `add_one_arc` | `canonaut::structs` | Add directed edge (arc) to a raw flat adjacency bitmatrix |
| `words_needed` | `canonaut::utilities` | Compute `m = ⌈n/word_bits⌉` |

## Running tests

```sh
cargo test
```

Comparison tests against pynauty reference output need `test_data/` populated
first. `test_data/` isn't committed — every file in it is regenerated
deterministically (the `.g6` corpora are exact `geng`/`networkx` output, the
`.ref` files are pynauty ground truth):

```sh
./setup.sh                    # installs nauty + a Python venv, regenerates
                               # test_data/, then runs the full test suite

./setup.sh --skip-testdata    # skip all of the above, just build + `cargo test`
```

See `setup.sh` for exactly what each step installs and regenerates.

## Benchmarks

The Criterion benchmarks compare against the C reference implementation. They
are gated behind the `c-nauty-bench` feature, which compiles a small C helper
and links the system libnauty (headers and library expected under
`/usr/local`):

```sh
cargo bench --features c-nauty-bench
```

A plain `cargo build` / `cargo test` has no C dependencies.

## Python bindings

`bindings/python` (package `graphcanon` on PyPI) exposes `canonize()` and
`are_isomorphic()` via [pyo3](https://pyo3.rs)/[maturin](https://www.maturin.rs),
with arbitrary hashable node labels and `networkx` interoperability on top of
the same `CanonautManager` core. It's a separate workspace member — not built
by a plain `cargo build`/`cargo test` at the repo root:

```sh
cd bindings/python
maturin develop --release   # or: maturin build --release
```

See `bindings/python/README.md` for the Python-side API.

## License

Licensed under the [Apache License, Version 2.0](LICENSE).

This crate is a Rust port of [nauty and Traces](https://pallini.di.uniroma1.it/) (version 2.6+), which is also licensed under the Apache License, Version 2.0.

Original copyright holders:
- Brendan McKay, Australian National University (1984–)
- Adolfo Piperno, University of Rome "Sapienza" (2008–)
- Gunnar Brinkmann, University of Ghent (2009–)
- Magma project, University of Sydney
- Sampo Niskanen and Patric Östergård
