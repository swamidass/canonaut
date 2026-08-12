#!/usr/bin/env python3
"""Render the paper's timing tables from repro/benchmark_data.csv.

Writes `repro/tables.tex`, containing the three table bodies (small-n,
large-n scaling, graph6 batch) with means, 95 % confidence-interval half-widths
and speedups, ready to paste into publication/main.tex.

Usage:
    python3 repro/collect_criterion.py && python3 repro/make_tables.py
"""

import collections
import csv
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "repro" / "benchmark_data.csv"
OUT = ROOT / "repro" / "tables.tex"

FAMILY_LABEL = {
    "complete": r"Complete $K_n$",
    "cycle": r"Cycle $C_n$",
    "path": r"Path $P_n$",
    "star": r"Star $S_n$",
    "random_p50": r"Random $G(n,0.5)$",
}
FAMILY_ORDER = ["complete", "cycle", "path", "star", "random_p50"]

HARD_LABEL = {
    "cfi": "CFI",
    "hadamard": "Hadamard",
    "paley": "Paley",
}
HARD_ORDER = ["cfi", "hadamard", "paley"]

BATCH_LABEL = {
    "cubic_10": r"Cubic, $n{=}10$",
    "all_9": r"All graphs, $n{=}9$",
    "bipartite_10": r"Bipartite, $n{=}10$",
}
BATCH_COUNT = {"cubic_10": 21, "all_9": 1000, "bipartite_10": 1000}

SMALL_SIZES = [8, 16, 32, 64, 128]
SCALING_SIZES = [256, 512, 1024, 2048]


def load():
    """-> {(group, family, n): {impl: (mean_ns, ci_half_width_ns)}}"""
    table = collections.defaultdict(dict)
    with open(DATA) as handle:
        for row in csv.DictReader(handle):
            mean = float(row["mean_ns"])
            half = (float(row["ci_hi_ns"]) - float(row["ci_lo_ns"])) / 2
            key = (row["group"], row["family"], int(row["n"]) if row["n"] else 0)
            table[key][row["impl"]] = (mean, half)
    return table


def format_time(nanoseconds: float, half_width: float) -> str:
    """`mean ± ci` in the largest unit that keeps 3 significant digits."""
    for scale, unit in ((1e6, r"\,ms"), (1e3, r"\,$\mu$s"), (1, r"\,ns")):
        if nanoseconds >= scale:
            value, error = nanoseconds / scale, half_width / scale
            digits = 2 if value < 10 else (1 if value < 100 else 0)
            return f"{value:.{digits}f}\\,$\\pm$\\,{error:.{digits}f}{unit}"
    return f"{nanoseconds:.0f}\\,$\\pm$\\,{half_width:.0f}\\,ns"


def speedup(entry) -> str:
    """t_nauty / t_canonaut, with an interval propagated from both CIs."""
    canonaut_mean, canonaut_half = entry["canonaut"]
    nauty_mean, nauty_half = entry["nauty"]
    ratio = nauty_mean / canonaut_mean
    relative = ((canonaut_half / canonaut_mean) ** 2 + (nauty_half / nauty_mean) ** 2) ** 0.5
    return f"{ratio:.2f}\\,$\\pm$\\,{ratio * relative:.2f}$\\times$"


def rows_for(table, group, sizes, order=None, labels=None):
    order = order or FAMILY_ORDER
    labels = labels or FAMILY_LABEL
    lines = []
    for position, family in enumerate(order):
        family_rows = []
        for n in sizes:
            entry = table.get((group, family, n))
            if not entry or "canonaut" not in entry or "nauty" not in entry:
                continue
            family_rows.append(
                (n, format_time(*entry["canonaut"]), format_time(*entry["nauty"]), speedup(entry))
            )
        if not family_rows:
            continue
        if position:
            lines.append(r"\midrule")
        label = labels[family]
        for index, (n, canonaut, nauty, ratio) in enumerate(family_rows):
            name = label if index == 0 else ""
            lines.append(f"{name:18s} & {n:4d} & {canonaut} & {nauty} & {ratio} \\\\")
    return lines


def main():
    table = load()
    out = []

    out.append("% --- Table 1: single-graph canonicalization, n = 8..128 -------------")
    out += rows_for(table, "small", SMALL_SIZES)

    out.append("")
    out.append("% --- Table 2: large-n scaling, n = 256..2048 ------------------------")
    out += rows_for(table, "scaling", SCALING_SIZES)

    out.append("")
    out.append("% --- Table 3: refinement-blind instances -----------------------------")
    hard_sizes = sorted({n for (group, _, n) in table if group == "hard"})
    out += rows_for(table, "hard", hard_sizes, HARD_ORDER, HARD_LABEL)

    out.append("")
    out.append("% --- Table 4: graph6 batch ------------------------------------------")
    for name in ("cubic_10", "all_9", "bipartite_10"):
        entry = table.get(("g6_batch", name, 0))
        if not entry:
            continue
        out.append(
            f"{BATCH_LABEL[name]} & {BATCH_COUNT[name]} & "
            f"{format_time(*entry['canonaut'])} & {format_time(*entry['nauty'])} & {speedup(entry)} \\\\"
        )

    OUT.write_text("\n".join(out) + "\n")
    print(f"wrote {OUT}")
    print("\n".join(out))


if __name__ == "__main__":
    main()
