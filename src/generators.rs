//! Deterministic graph generators used by the test suite, the Criterion
//! benchmarks (`benches/bench.rs`), and the measurement binaries
//! (`src/bin/memcheck.rs`, `src/bin/profile.rs`).
//!
//! Every generator returns a flat MSB-0 bit-matrix (`n * m` `usize` words,
//! `m = ceil(n / 64)`) in the layout expected by
//! [`CanonautManager::canonize`](crate::structs::CanonautManager::canonize),
//! so the same buffer can be handed unchanged to the C reference
//! implementation in the comparison benchmarks.

use crate::structs::graph::add_one_edge;
use crate::utilities::words_needed;

pub fn generate_empty_graph(number_of_vertices: usize) -> Vec<usize> {
    vec![0; words_needed(number_of_vertices) * number_of_vertices]
}

pub fn generate_cycle_graph(number_of_vertices: usize) -> Vec<usize> {
    let mut graph = generate_empty_graph(number_of_vertices);
    if number_of_vertices == 1 {
        return graph;
    }
    for index in 0..number_of_vertices {
        add_one_edge(
            &mut graph,
            index,
            (index + 1) % number_of_vertices,
            words_needed(number_of_vertices) as u32,
        );
    }
    graph
}

pub fn generate_complete_graph(number_of_vertices: usize) -> Vec<usize> {
    let mut graph = generate_empty_graph(number_of_vertices);
    let words = words_needed(number_of_vertices) as u32;

    for row in 0..number_of_vertices {
        for column in (row + 1)..number_of_vertices {
            add_one_edge(&mut graph, row, column, words);
        }
    }
    graph
}

pub fn generate_path_graph(number_of_vertices: usize) -> Vec<usize> {
    let mut graph = generate_empty_graph(number_of_vertices);
    let words = words_needed(number_of_vertices) as u32;

    if number_of_vertices < 2 {
        return graph;
    }

    for index in 0..(number_of_vertices - 1) {
        add_one_edge(&mut graph, index, index + 1, words);
    }
    graph
}

pub fn generate_random_graph(number_of_vertices: usize, density: f64, seed: u64) -> Vec<usize> {
    use rand::{SeedableRng, rngs::SmallRng};
    let mut graph = generate_empty_graph(number_of_vertices);
    let words = words_needed(number_of_vertices) as u32;
    let mut random_generator = SmallRng::seed_from_u64(seed);
    for row in 0..number_of_vertices {
        for column in (row + 1)..number_of_vertices {
            use rand::Rng;
            if random_generator.random::<f64>() < density {
                add_one_edge(&mut graph, row, column, words);
            }
        }
    }
    graph
}

pub fn generate_star_graph(number_of_vertices: usize) -> Vec<usize> {
    let mut graph = generate_empty_graph(number_of_vertices);
    let words = words_needed(number_of_vertices) as u32;

    if number_of_vertices < 2 {
        return graph;
    }

    for index in 1..number_of_vertices {
        add_one_edge(&mut graph, 0, index, words);
    }
    graph
}

