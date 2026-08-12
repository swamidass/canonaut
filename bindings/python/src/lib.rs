use std::cell::RefCell;

use canonaut::{
    structs::{BitSetOpsMSB0, CanonautManager},
    utilities::words_needed,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

// ---------------------------------------------------------------------------
// Thread-local generator accumulator
// ---------------------------------------------------------------------------

thread_local! {
    static GENERATORS: RefCell<Vec<Vec<u32>>> = RefCell::new(Vec::new());
}

fn capture_generator(
    _gen_num: u32,
    perm: &mut [u32],
    _orbits: &mut [u32],
    _num_orbits: u32,
    _orbit_rep: u32,
    n: u32,
) {
    GENERATORS.with(|g| g.borrow_mut().push(perm[..n as usize].to_vec()));
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

fn build_adjacency(n: usize, edges: &[(usize, usize)], directed: bool) -> Vec<usize> {
    let m = words_needed(n);
    let mut adj = vec![0usize; n * m];
    for &(u, v) in edges {
        adj[u * m..(u + 1) * m].set_bit(v);
        if !directed {
            adj[v * m..(v + 1) * m].set_bit(u);
        }
    }
    adj
}

fn edges_from_bitmatrix(adj: &[usize], n: usize, m: usize) -> Vec<(usize, usize)> {
    let mut edges = Vec::new();
    for v in 0..n {
        let row = &adj[v * m..(v + 1) * m];
        let mut w = 0;
        while let Some(next) = row.next_set_bit(w) {
            edges.push((v, next));
            w = next + 1;
        }
    }
    edges
}

// ---------------------------------------------------------------------------
// Python-facing result type
// ---------------------------------------------------------------------------

#[pyclass]
struct CanonResult {
    #[pyo3(get)]
    /// Canonical labeling: labeling[i] = canonical index of original vertex i.
    labeling: Vec<u32>,
    #[pyo3(get)]
    /// Orbit representative for each vertex: orbits[i] = orbit id of vertex i.
    orbits: Vec<u32>,
    #[pyo3(get)]
    /// Edges of the canonical graph as sorted (u, v) pairs.
    canonical_edges: Vec<(usize, usize)>,
    #[pyo3(get)]
    /// |Aut(G)| ≈ group_size1 × 10^group_size2.
    group_size1: f64,
    #[pyo3(get)]
    group_size2: u32,
    #[pyo3(get)]
    num_generators: u32,
    #[pyo3(get)]
    num_orbits: u32,
    #[pyo3(get)]
    /// Automorphism generator permutations (non-empty only when generators=True).
    generators: Vec<Vec<u32>>,
    // Private: raw canonical bitmatrix words for canonical_bytes().
    canonical_words: Vec<usize>,
    n: usize,
    m: usize,
}

#[pymethods]
impl CanonResult {
    fn __repr__(&self) -> String {
        format!(
            "CanonResult(n={}, num_orbits={}, |Aut|≈{:.4}e{}, generators={})",
            self.n,
            self.num_orbits,
            self.group_size1,
            self.group_size2,
            self.generators.len(),
        )
    }

    /// Return the canonical bitmatrix as a `bytes` object (big-endian words).
    ///
    /// Suitable as a hashable canonical key:
    /// ``canon_a.canonical_bytes() == canon_b.canonical_bytes()``
    /// iff the two graphs are isomorphic.
    fn canonical_bytes<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        let mut buf: Vec<u8> = Vec::with_capacity(self.n * self.m * 8);
        for &w in &self.canonical_words[..self.n * self.m] {
            buf.extend_from_slice(&(w as u64).to_be_bytes());
        }
        PyBytes::new(py, &buf)
    }
}

// ---------------------------------------------------------------------------
// Exported functions
// ---------------------------------------------------------------------------

/// Compute the canonical form of a graph.
///
/// Parameters
/// ----------
/// n : int
///     Number of vertices (vertices are 0-indexed).
/// edges : list[tuple[int, int]]
///     Edge list.  For undirected graphs each edge should appear once.
/// directed : bool, optional
///     Treat the graph as directed.  Default ``False``.
/// generators : bool, optional
///     Collect automorphism generator permutations.  Slightly slower.
///     Default ``False``.
/// colors : list[int], optional
///     One color per vertex (length must equal ``n``). Vertices with different
///     colors are never mapped onto each other by any automorphism, and the
///     canonical form respects the coloring. Colors need not be contiguous or
///     sorted — only which vertices share a color matters. Default: uncolored.
///
/// Returns
/// -------
/// CanonResult
///
/// Examples
/// --------
/// >>> import canonaut
/// >>> r = canonaut.canonize(6, [(0,1),(1,2),(2,3),(3,4),(4,5),(5,0)])
/// >>> r.num_orbits
/// 1
#[pyfunction]
#[pyo3(signature = (n, edges, *, directed=false, generators=false, colors=None))]
fn canonize(
    n: usize,
    edges: Vec<(usize, usize)>,
    directed: bool,
    generators: bool,
    colors: Option<Vec<u32>>,
) -> PyResult<CanonResult> {
    let adj = build_adjacency(n, &edges, directed);

    let mut mgr = CanonautManager::new(n).with_canonization();
    if generators {
        GENERATORS.with(|g| g.borrow_mut().clear());
        mgr = mgr.with_automorphism_callback(capture_generator);
    }
    match colors {
        Some(colors) => {
            if colors.len() != n {
                return Err(PyValueError::new_err(format!(
                    "colors has length {} but n={}",
                    colors.len(),
                    n
                )));
            }
            mgr.canonize_with_colors(&adj, &colors);
        }
        None => mgr.canonize(&adj),
    }

    let m = words_needed(n);
    let stats = mgr.statistics();
    let labeling = mgr.labeling()[..n].to_vec();
    let orbits_vec = mgr.orbits()[..n].to_vec();
    let canonical_words = mgr.canonical_graph[..n * m].to_vec();
    let canonical_edges = edges_from_bitmatrix(&canonical_words, n, m);
    let gens = if generators {
        GENERATORS.with(|g| g.borrow().clone())
    } else {
        Vec::new()
    };

    Ok(CanonResult {
        labeling,
        orbits: orbits_vec,
        canonical_edges,
        group_size1: stats.group_size1,
        group_size2: stats.group_size2,
        num_generators: stats.number_of_generators,
        num_orbits: stats.number_of_orbits,
        generators: gens,
        canonical_words,
        n,
        m,
    })
}

/// Test whether two graphs are isomorphic.
///
/// Parameters
/// ----------
/// n1, n2 : int
///     Vertex counts of the two graphs.
/// edges1, edges2 : list[tuple[int, int]]
///     Edge lists.
/// directed : bool, optional
///     Treat both graphs as directed.
///
/// Returns
/// -------
/// bool
#[pyfunction]
#[pyo3(signature = (n1, edges1, n2, edges2, *, directed=false))]
fn are_isomorphic(
    n1: usize,
    edges1: Vec<(usize, usize)>,
    n2: usize,
    edges2: Vec<(usize, usize)>,
    directed: bool,
) -> bool {
    if n1 != n2 || edges1.len() != edges2.len() {
        return false;
    }
    let n = n1;
    let m = words_needed(n);
    let adj1 = build_adjacency(n, &edges1, directed);
    let adj2 = build_adjacency(n, &edges2, directed);
    let mut mgr = CanonautManager::new(n).with_canonization();
    mgr.canonize(&adj1);
    let canon1 = mgr.canonical_graph[..n * m].to_vec();
    mgr.canonize(&adj2);
    canon1 == mgr.canonical_graph[..n * m]
}

// ---------------------------------------------------------------------------
// Module
// ---------------------------------------------------------------------------

#[pymodule]
fn _canonaut(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CanonResult>()?;
    m.add_function(wrap_pyfunction!(canonize, m)?)?;
    m.add_function(wrap_pyfunction!(are_isomorphic, m)?)?;
    Ok(())
}
