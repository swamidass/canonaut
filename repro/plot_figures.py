"""
Generates the paper's figures from the collected measurement data:

  - performance_speedup.pdf: speedup (t_C / t_canonaut) vs n, in two panels —
    the structured and random families, and the refinement-blind ones (CFI,
    Hadamard, Paley) — with error bars propagated from Criterion's 95 %
    confidence intervals (repro/benchmark_data.csv, see collect_criterion.py).
  - memory_usage.pdf: peak RSS vs n, canonaut vs C nauty
    (repro/memory_data.csv, see repro/measure_memory.sh).

Figures are written next to the data in repro/, and also into publication/ when
that directory exists (that is where main.tex includes them from).

Usage:
    python3 repro/plot_figures.py
"""

import collections
import csv
import pathlib

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPRO = ROOT / "repro"
PAPER = ROOT / "publication"

# Validated categorical palette (light mode), fixed order.
BLUE = "#2a78d6"
AQUA = "#1baf7a"
YELLOW = "#eda100"
GREEN = "#008300"
VIOLET = "#4a3aa7"
RED = "#e34948"

INK = "#0b0b0b"
MUTED = "#898781"
GRID = "#e1e0d9"

plt.rcParams.update(
    {
        "font.size": 10,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
        "svg.fonttype": "none",
    }
)

FAMILIES = [
    ("Complete $K_n$", BLUE, "complete"),
    ("Random $G(n,0.5)$", AQUA, "random_p50"),
    ("Cycle $C_n$", YELLOW, "cycle"),
    ("Path $P_n$", GREEN, "path"),
    ("Star $S_n$", VIOLET, "star"),
]

HARD_FAMILIES = [
    ("CFI", BLUE, "cfi"),
    ("Hadamard", VIOLET, "hadamard"),
    ("Paley", AQUA, "paley"),
]


def save(figure, name):
    for directory in (REPRO, PAPER):
        if directory.is_dir():
            figure.savefig(directory / f"{name}.pdf")
            figure.savefig(directory / f"{name}.png", dpi=200)
    print(f"wrote {name}.pdf/.png")


# ---------------------------------------------------------------------------
# Figure 1: performance speedup vs n
# ---------------------------------------------------------------------------


def load_timings(groups=("small", "scaling")):
    """-> {(family, n): {impl: (mean, ci_half_width)}}, both in nanoseconds."""
    timings = collections.defaultdict(dict)
    with open(REPRO / "benchmark_data.csv") as handle:
        for row in csv.DictReader(handle):
            if row["group"] not in groups:
                continue
            mean = float(row["mean_ns"])
            half = (float(row["ci_hi_ns"]) - float(row["ci_lo_ns"])) / 2
            # The small-n and scaling groups cover disjoint sizes except where
            # they overlap; prefer the scaling run there (flat sampling).
            key = (row["family"], int(row["n"]))
            if row["group"] == "scaling" or row["impl"] not in timings[key]:
                timings[key][row["impl"]] = (mean, half)
    return timings


def speedup_points(timings, family):
    """-> ([n], [speedup], [error]) sorted by n."""
    points = []
    for (row_family, n), entry in timings.items():
        if row_family != family or "canonaut" not in entry or "nauty" not in entry:
            continue
        canonaut_mean, canonaut_half = entry["canonaut"]
        nauty_mean, nauty_half = entry["nauty"]
        ratio = nauty_mean / canonaut_mean
        relative = ((canonaut_half / canonaut_mean) ** 2 + (nauty_half / nauty_mean) ** 2) ** 0.5
        points.append((n, ratio, ratio * relative))
    points.sort()
    return zip(*points)


def plot_performance():
    figure, (axes, hard_axes) = plt.subplots(
        1, 2, figsize=(7.2, 3.4), gridspec_kw={"width_ratios": [1.55, 1]}
    )

    timings = load_timings()
    for label, color, family in FAMILIES:
        sizes, ratios, errors = speedup_points(timings, family)
        axes.errorbar(
            sizes, ratios, yerr=errors, color=color, marker="o", markersize=4,
            linewidth=1.6, elinewidth=1.0, capsize=2.5, label=label,
        )

    hard_timings = load_timings(("hard",))
    for label, color, family in HARD_FAMILIES:
        sizes, ratios, errors = speedup_points(hard_timings, family)
        hard_axes.errorbar(
            sizes, ratios, yerr=errors, color=color, marker="s", markersize=4,
            linewidth=1.6, elinewidth=1.0, capsize=2.5, label=label,
        )

    for axis, title in ((axes, "Structured and random"), (hard_axes, "Refinement-blind")):
        axis.axhline(1.0, color=MUTED, linewidth=0.8, linestyle="--", zorder=0)
        axis.set_xscale("log", base=2)
        axis.set_xlabel("Graph order $n$")
        axis.set_title(title, fontsize=10)
        axis.xaxis.set_major_formatter(mticker.ScalarFormatter())
        axis.legend(frameon=False, fontsize=8, loc="best")
        for spine in ("top", "right"):
            axis.spines[spine].set_visible(False)

    axes.set_ylabel(r"Speedup ($t_C / t_{\mathrm{canonaut}}$)")
    axes.set_xticks([8, 32, 128, 512, 2048])
    hard_axes.set_xticks([128, 256, 512, 1000])

    figure.tight_layout()
    save(figure, "performance_speedup")


# ---------------------------------------------------------------------------
# Figure 2: peak memory vs n
# ---------------------------------------------------------------------------


def plot_memory():
    path = REPRO / "memory_data.csv"
    if not path.exists():
        print("no repro/memory_data.csv — skipping memory figure (run repro/measure_memory.sh)")
        return

    rows = [row for row in csv.DictReader(open(path)) if row["family"] != "random"]
    families = sorted({row["family"] for row in rows})

    figure, axes = plt.subplots(1, len(families), figsize=(9.5, 2.8), sharey=True)
    if len(families) == 1:
        axes = [axes]

    for axis, family in zip(axes, families):
        for impl, color, label in [("canonaut", BLUE, "canonaut"), ("nauty", RED, "nauty 2.8.9 (C)")]:
            points = sorted(
                (int(row["n"]), int(row["rss_bytes"]) / 1e6)
                for row in rows
                if row["family"] == family and row["impl"] == impl
            )
            sizes, megabytes = zip(*points)
            axis.plot(sizes, megabytes, color=color, marker="o", markersize=3.5, linewidth=1.4, label=label)
        axis.set_xscale("log", base=2)
        axis.set_title(family.capitalize(), fontsize=10)
        axis.set_xlabel("$n$")
        for spine in ("top", "right"):
            axis.spines[spine].set_visible(False)

    axes[0].set_ylabel("Peak RSS (MB)")
    axes[-1].legend(frameon=False, fontsize=8.5, loc="lower right")

    figure.tight_layout()
    save(figure, "memory_usage")


if __name__ == "__main__":
    plot_performance()
    plot_memory()
