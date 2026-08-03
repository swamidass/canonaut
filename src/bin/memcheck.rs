// Peak-memory measurement harness for the paper's memory-usage figure.
// Runs `iters` canonize() calls on a fixed-size graph so external tools
// (e.g. `/usr/bin/time -l`, which reports "maximum resident set size") can
// read off peak RSS for one (family, n) data point per process invocation.
//
// Usage: memcheck <family> <n> [iters=2000]
//   family: complete | cycle | path | star | random

use canonaut::structs::CanonautManager;
use canonaut::tests::{
    generate_complete_graph, generate_cycle_graph, generate_path_graph, generate_random_graph,
    generate_star_graph,
};
use std::hint::black_box;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let family = args.get(1).expect("usage: memcheck <family> <n> [iters]");
    let vertex_count: usize = args.get(2).expect("usage: memcheck <family> <n> [iters]").parse().unwrap();
    let iterations: usize = args.get(3).map(|arg| arg.parse().unwrap()).unwrap_or(2000);

    let graph = match family.as_str() {
        "complete" => generate_complete_graph(vertex_count),
        "cycle" => generate_cycle_graph(vertex_count),
        "path" => generate_path_graph(vertex_count),
        "star" => generate_star_graph(vertex_count),
        "random" => generate_random_graph(vertex_count, 0.5, 42),
        other => panic!("unknown family '{other}' (expected complete|cycle|path|star|random)"),
    };

    let mut manager = CanonautManager::new(vertex_count).with_canonization();
    let mut orbit_sum: u64 = 0;
    for _ in 0..iterations {
        manager.canonize(black_box(&graph));
        orbit_sum += manager.statistics().number_of_orbits as u64;
    }
    // Print so the loop can't be optimized away; not otherwise meaningful.
    println!("{orbit_sum}");
}
