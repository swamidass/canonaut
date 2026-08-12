#!/usr/bin/env bash
# Memory sweep behind the paper's memory-usage figure and allocation numbers.
#
# Part 1 (cross-implementation): runs src/bin/memcheck (canonaut) and
# benches/c_memcheck.c (C nauty) across the same deterministic graph families
# and sizes, one process per data point, recording "maximum resident set size"
# from `/usr/bin/time -l` (macOS/BSD; on Linux use `/usr/bin/time -v` and read
# "Maximum resident set size").  Output: repro/memory_data.csv
#   family,n,impl,rss_bytes
#
# Part 2 (canonaut heap): re-runs the same points with the counting global
# allocator built into src/bin/memcheck, separating buffers allocated during
# set-up from anything allocated in the steady-state canonicalization loop.
# Output: repro/allocation_data.csv
#   family,n,iters,setup_allocations,setup_bytes,steady_state_allocations,steady_state_bytes,peak_live_bytes
#
# Requires nauty >= 2.8 headers/library under /usr/local (same prerequisite as
# `cargo bench --features c-nauty-bench`).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUSTFLAGS="-C target-cpu=native" cargo build --release --bin memcheck
clang -O3 -I/usr/local/include -L/usr/local/lib -lnauty benches/c_memcheck.c -o /tmp/c_memcheck

RSS_OUT="repro/memory_data.csv"
ALLOC_OUT="repro/allocation_data.csv"
echo "family,n,impl,rss_bytes" > "$RSS_OUT"
echo "family,n,iters,setup_allocations,setup_bytes,steady_state_allocations,steady_state_bytes,peak_live_bytes" > "$ALLOC_OUT"

FAMILIES_CHEAP="cycle path"
FAMILIES_EXPENSIVE="complete star"
SIZES_CHEAP="8 16 32 64 128 256 512"
SIZES_EXPENSIVE="8 16 32 64 128 256"

measure_rss() {
    local label="$1"; shift
    local rss
    rss=$(/usr/bin/time -l "$@" 2>&1 >/dev/null | awk '/maximum resident set size/ {print $1}')
    echo "$label,$rss"
}

measure_alloc() {
    local family="$1" n="$2" iters="$3"
    # memcheck prints `key=value` pairs; pull the ones this CSV records.
    ./target/release/memcheck "$family" "$n" "$iters" | awk -v f="$family" -v n="$n" -v it="$iters" '
        {
            for (i = 1; i <= NF; i++) {
                split($i, kv, "=")
                v[kv[1]] = kv[2]
            }
            printf "%s,%s,%s,%s,%s,%s,%s,%s\n", f, n, it,
                v["setup_allocations"], v["setup_bytes"],
                v["steady_state_allocations"], v["steady_state_bytes"], v["peak_live_bytes"]
        }'
}

sweep() {
    local family="$1" n="$2" iters="$3"
    measure_rss "$family,$n,canonaut" ./target/release/memcheck "$family" "$n" "$iters" | tee -a "$RSS_OUT"
    measure_rss "$family,$n,nauty" /tmp/c_memcheck "$family" "$n" "$iters" | tee -a "$RSS_OUT"
    measure_alloc "$family" "$n" "$iters" | tee -a "$ALLOC_OUT"
}

for family in $FAMILIES_CHEAP; do
    for n in $SIZES_CHEAP; do
        sweep "$family" "$n" 500
    done
done

for family in $FAMILIES_EXPENSIVE; do
    for n in $SIZES_EXPENSIVE; do
        sweep "$family" "$n" 30
    done
done

# Buffer reuse: identical steady-state behaviour at 2 000 and 100 000 iterations.
# Random graphs have no C counterpart here (benches/c_memcheck.c builds only the
# deterministic families, since bit-identical RNG parity with Rust is not worth
# arranging for a memory measurement), so only the canonaut side is recorded.
for iters in 2000 100000; do
    measure_rss "random,64,canonaut" ./target/release/memcheck random 64 "$iters" | tee -a "$RSS_OUT"
    measure_alloc "random" 64 "$iters" | tee -a "$ALLOC_OUT"
done

echo "Wrote $RSS_OUT and $ALLOC_OUT"
