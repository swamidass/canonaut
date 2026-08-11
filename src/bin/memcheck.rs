// Memory measurement harness for the paper's memory-usage figure.
//
// Runs `iters` canonize() calls on a fixed-size graph so external tools
// (e.g. `/usr/bin/time -l`, which reports "maximum resident set size") can
// read off peak RSS for one (family, n) data point per process invocation.
//
// Usage: memcheck <family> <n> [iters=2000]
//   family: complete | cycle | path | star | random | cfi | cfi_twisted
//         | hadamard | paley
//   For the hard families `n` is the construction parameter: the base vertex
//   count for cfi (graph order 10n), the Hadamard order (graph order 2n), and
//   the prime order for paley (graph order n).

use canonaut::generators::{
    generate_cfi_graph, generate_complete_graph, generate_cycle_graph, generate_hadamard_graph,
    generate_paley_graph, generate_path_graph, generate_random_graph, generate_star_graph,
};
use canonaut::structs::CanonautManager;
use std::hint::black_box;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let family = args.get(1).expect("usage: memcheck <family> <n> [iters]");
    let parameter: usize = args.get(2).expect("usage: memcheck <family> <n> [iters]").parse().unwrap();
    let iterations: usize = args.get(3).map(|arg| arg.parse().unwrap()).unwrap_or(2000);

    // Each arm yields the graph and its vertex count; for the hard families the
    // command-line argument is the construction parameter, not the order.
    let (graph, vertex_count) = match family.as_str() {
        "cfi" => (generate_cfi_graph(parameter, false), 10 * parameter),
        "cfi_twisted" => (generate_cfi_graph(parameter, true), 10 * parameter),
        "hadamard" => (generate_hadamard_graph(parameter), 2 * parameter),
        "paley" => (generate_paley_graph(parameter), parameter),
        "complete" => (generate_complete_graph(parameter), parameter),
        "cycle" => (generate_cycle_graph(parameter), parameter),
        "path" => (generate_path_graph(parameter), parameter),
        "star" => (generate_star_graph(parameter), parameter),
        "random" => (generate_random_graph(parameter, 0.5, 42), parameter),
        other => panic!(
            "unknown family '{other}' (expected complete|cycle|path|star|random|cfi|cfi_twisted|hadamard|paley)"
        ),
    };

    let mut manager = CanonautManager::new(vertex_count).with_canonization();

    let mut orbit_sum: u64 = 0;
    for _ in 0..iterations {
        manager.canonize(black_box(&graph));
        orbit_sum += manager.statistics().number_of_orbits as u64;
    }

    // `orbit_sum` is printed so the loop cannot be optimized away.
    println!("family={family} n={vertex_count} iters={iterations} orbit_sum={orbit_sum}");
}
