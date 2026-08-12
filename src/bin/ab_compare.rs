// Order-balanced A/B timing of canonaut against C nauty on one instance.
//
// The Criterion suite measures each implementation in its own benchmark, and
// always measures canonaut first.  For instances whose absolute runtime is a
// microsecond or less, that ordering can bias the comparison: whichever
// implementation runs first pays for whatever frequency ramping or cache
// warming the round needs.  This harness removes that asymmetry by
// interleaving the two implementations within a round and alternating which
// one goes first from round to round, then reporting the distribution of
// per-round ratios rather than a single point estimate.
//
//   cargo run --release --features c-nauty-bench --bin ab_compare -- <family> <n> [rounds]

use canonaut::generators::{
    generate_complete_graph, generate_cycle_graph, generate_path_graph, generate_random_graph,
    generate_star_graph,
};
use canonaut::structs::CanonautManager;
use canonaut::utilities::words_needed;
use std::hint::black_box;
use std::time::Instant;

unsafe extern "C" {
    fn c_nauty_dense_canonize(
        graph: *mut u64,
        labeling: *mut i32,
        partition: *mut i32,
        orbits: *mut i32,
        canonical_graph: *mut u64,
        words_per_vertex: i32,
        vertex_count: i32,
    );
}

struct CNauty {
    labeling: Vec<i32>,
    partition: Vec<i32>,
    orbits: Vec<i32>,
    canonical_graph: Vec<u64>,
    words_per_vertex: i32,
    vertex_count: i32,
}

impl CNauty {
    fn new(vertex_count: usize, words_per_vertex: usize) -> Self {
        CNauty {
            labeling: vec![0; vertex_count],
            partition: vec![0; vertex_count],
            orbits: vec![0; vertex_count],
            canonical_graph: vec![0; vertex_count * words_per_vertex],
            words_per_vertex: words_per_vertex as i32,
            vertex_count: vertex_count as i32,
        }
    }

    fn run(&mut self, graph: &[usize]) {
        // SAFETY: all buffers are sized n and n*m as densenauty requires.
        unsafe {
            c_nauty_dense_canonize(
                graph.as_ptr() as *mut u64,
                self.labeling.as_mut_ptr(),
                self.partition.as_mut_ptr(),
                self.orbits.as_mut_ptr(),
                self.canonical_graph.as_mut_ptr(),
                self.words_per_vertex,
                self.vertex_count,
            )
        }
    }
}

fn percentile(sorted: &[f64], q: f64) -> f64 {
    let position = q * (sorted.len() - 1) as f64;
    let lower = position.floor() as usize;
    let upper = position.ceil() as usize;
    if lower == upper {
        sorted[lower]
    } else {
        sorted[lower] + (position - lower as f64) * (sorted[upper] - sorted[lower])
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let family = args.get(1).expect("usage: ab_compare <family> <n> [rounds]");
    let vertex_count: usize = args.get(2).expect("usage: ab_compare <family> <n> [rounds]").parse().unwrap();
    let rounds: usize = args.get(3).map(|a| a.parse().unwrap()).unwrap_or(40);

    let graph = match family.as_str() {
        "complete" => generate_complete_graph(vertex_count),
        "cycle" => generate_cycle_graph(vertex_count),
        "path" => generate_path_graph(vertex_count),
        "star" => generate_star_graph(vertex_count),
        "random" => generate_random_graph(vertex_count, 0.5, 42),
        other => panic!("unknown family '{other}'"),
    };
    let words_per_vertex = words_needed(vertex_count);

    let mut manager = CanonautManager::new(vertex_count).with_canonization();
    let mut reference = CNauty::new(vertex_count, words_per_vertex);

    // Size a round so that each timed block lasts a few milliseconds, which
    // keeps the clock's resolution irrelevant.
    let mut iterations = 64usize;
    loop {
        let start = Instant::now();
        for _ in 0..iterations {
            manager.canonize(black_box(&graph));
        }
        if start.elapsed().as_secs_f64() > 0.005 || iterations > 1 << 22 {
            break;
        }
        iterations *= 2;
    }

    // Warm both sides before measuring anything.
    for _ in 0..iterations {
        manager.canonize(black_box(&graph));
        reference.run(black_box(&graph));
    }

    let time = |run: &mut dyn FnMut()| {
        let start = Instant::now();
        for _ in 0..iterations {
            run();
        }
        start.elapsed().as_secs_f64() / iterations as f64
    };

    let mut ratios = Vec::with_capacity(rounds);
    let (mut canonaut_total, mut nauty_total) = (0.0, 0.0);
    for round in 0..rounds {
        let (canonaut, nauty) = if round % 2 == 0 {
            let a = time(&mut || manager.canonize(black_box(&graph)));
            let b = time(&mut || reference.run(black_box(&graph)));
            (a, b)
        } else {
            // odd rounds measure C nauty first, so neither side is
            // systematically the one that pays for warming up
            let b = time(&mut || reference.run(black_box(&graph)));
            let a = time(&mut || manager.canonize(black_box(&graph)));
            (a, b)
        };
        canonaut_total += canonaut;
        nauty_total += nauty;
        ratios.push(nauty / canonaut);
    }

    ratios.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let median = percentile(&ratios, 0.5);
    let (low, high) = (percentile(&ratios, 0.025), percentile(&ratios, 0.975));
    let verdict = if low > 1.0 {
        "canonaut faster"
    } else if high < 1.0 {
        "nauty faster"
    } else {
        "indistinguishable"
    };

    println!(
        "{family}({vertex_count}): {iterations} iters/round, {rounds} rounds, order alternated\n  \
         canonaut {:>9.3} us   nauty {:>9.3} us\n  \
         ratio median {median:.4}  95% of rounds in [{low:.4}, {high:.4}]  ->  {verdict}",
        canonaut_total / rounds as f64 * 1e6,
        nauty_total / rounds as f64 * 1e6,
    );
}
