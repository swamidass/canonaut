//! Graph canonicalization and automorphism group computation.
//!
//! `canonaut` is a safe Rust port of the [nauty](https://pallini.di.uniroma1.it/)
//! algorithm (McKay 1981; McKay & Piperno 2014) for computing canonical labelings
//! and automorphism groups of graphs.
//!
//! # Quick start
//!
//! ```rust
//! use canonaut::structs::{CanonautManager, DenseGraph};
//!
//! let vertex_count = 4;
//! let mut graph = DenseGraph::new(vertex_count);
//! graph.add_edge(0, 1);
//! graph.add_edge(1, 2);
//! graph.add_edge(2, 3);
//! graph.add_edge(3, 0);
//!
//! let mut manager = CanonautManager::new(vertex_count).with_canonization();
//! manager.canonize_graph(&graph);
//! assert_eq!(manager.statistics().number_of_orbits, 1); // 4-cycle is vertex-transitive
//! ```
//!
//! # Module overview
//!
//! | Module | Purpose |
//! |--------|---------|
//! [`structs`] | Public types: [`structs::CanonautManager`], [`structs::DenseGraph`], [`structs::SparseGraph`], [`structs::Statistics`] |
//! [`graph6`] | graph6 / sparse6 file format parser |
//! [`utilities`] | Low-level helpers: [`utilities::words_needed`], [`utilities::safe_orbjoin`] |
//! [`structs::bitset`] | [`structs::BitSetOpsMSB0`] trait — MSB-0 bitset operations on `[usize]` |

pub mod bit_ops;
pub mod graph6;
pub mod simd_ops;
pub mod consts;
pub mod io;
pub mod refine;
pub mod rng;
pub mod support;
pub mod search;
pub mod structs;
pub mod test_vectors;
pub mod tests;
pub mod utilities;
