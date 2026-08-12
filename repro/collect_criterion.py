#!/usr/bin/env python3
"""Collect Criterion estimates into a single CSV (with 95% confidence intervals).

Reads `target/criterion/**/new/estimates.json` — produced by

    cargo bench --features c-nauty-bench

— and writes `repro/benchmark_data.csv` with one row per
(group, family, implementation, n) measurement:

    group,family,impl,n,mean_ns,ci_lo_ns,ci_hi_ns,stddev_ns

`group` is one of `small` (Table 1), `scaling` (Table 2), `g6_batch` (Table 3).
Speedups quoted in the paper are t_nauty / t_canonaut of the `mean_ns` column;
`repro/make_tables.py` regenerates the LaTeX table bodies from this file.
"""

import csv
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CRITERION = ROOT / "target" / "criterion"
OUT = ROOT / "repro" / "benchmark_data.csv"

# Benchmark-group directory -> family label used in the paper.
SMALL_GROUPS = {
    "complete": "complete",
    "cycle": "cycle",
    "path": "path",
    "star": "star",
    "random_p50": "random_p50",
}


def read_estimate(path):
    """Return (mean_ns, ci_lo_ns, ci_hi_ns, stddev_ns) from an estimates.json."""
    with open(path) as handle:
        data = json.load(handle)
    mean = data["mean"]
    stddev = data.get("std_dev", {}).get("point_estimate", float("nan"))
    return (
        mean["point_estimate"],
        mean["confidence_interval"]["lower_bound"],
        mean["confidence_interval"]["upper_bound"],
        stddev,
    )


def collect():
    if not CRITERION.is_dir():
        sys.exit(f"no Criterion output at {CRITERION} — run `cargo bench --features c-nauty-bench` first")

    rows = []
    for estimates in sorted(CRITERION.glob("**/new/estimates.json")):
        parts = estimates.relative_to(CRITERION).parts[:-2]  # drop new/estimates.json
        if not parts:
            continue
        group = parts[0]

        if group in SMALL_GROUPS and len(parts) == 3:
            # e.g. cycle/canonaut/128
            _, implementation, n = parts
            family, bench_group = SMALL_GROUPS[group], "small"
        elif group in ("scaling", "hard") and len(parts) == 3:
            # e.g. scaling/canonaut_random_p50/2048, hard/canonaut_cfi/600
            _, tag, n = parts
            implementation, _, family = tag.partition("_")
            bench_group = group
        elif group == "g6_batch" and len(parts) == 2:
            # e.g. g6_batch/canonaut_all_9  (no n dimension)
            _, tag = parts
            implementation, _, family = tag.partition("_")
            bench_group, n = "g6_batch", ""
        else:
            continue

        # Older runs used the pre-rename ids; keep only the current pair.
        if implementation not in ("canonaut", "nauty"):
            continue

        mean, ci_lo, ci_hi, stddev = read_estimate(estimates)
        rows.append(
            {
                "group": bench_group,
                "family": family,
                "impl": implementation,
                "n": n,
                "mean_ns": f"{mean:.1f}",
                "ci_lo_ns": f"{ci_lo:.1f}",
                "ci_hi_ns": f"{ci_hi:.1f}",
                "stddev_ns": f"{stddev:.1f}",
            }
        )

    rows.sort(key=lambda r: (r["group"], r["family"], int(r["n"] or 0), r["impl"]))
    with open(OUT, "w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["group", "family", "impl", "n", "mean_ns", "ci_lo_ns", "ci_hi_ns", "stddev_ns"],
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    collect()
