#!/usr/bin/env bash
# canonaut dev environment bootstrap.
#
# Installs everything needed to build, test, and regenerate test_data/ on a
# fresh machine:
#   - Rust toolchain (via rustup, if `cargo` isn't already on PATH)
#   - nauty's `geng`/`genbg` + C library (via Homebrew on macOS, apt on Debian/
#     Ubuntu) — needed to regenerate test_data/*.g6 and for the `c-nauty-bench`
#     benchmark feature
#   - a Python venv with pynauty + networkx — needed to regenerate
#     test_data/*.ref (pynauty ground truth) and test_data/large_*.g6 (networkx)
#
# test_data/ is regenerated from scratch every run (see .gitignore — none of it
# is committed) so this script is the only source of truth for those files.
#
# Usage:
#   ./setup.sh                # full setup + regenerate test_data + run tests
#   ./setup.sh --skip-testdata  # skip nauty/python/test_data, just build Rust

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

SKIP_TESTDATA=0
for arg in "$@"; do
    case "$arg" in
        --skip-testdata) SKIP_TESTDATA=1 ;;
        *) echo "unknown argument: $arg" >&2; exit 1 ;;
    esac
done

log() { printf '\n== %s ==\n' "$1"; }

# ---------------------------------------------------------------------------
log "Rust toolchain"
if command -v cargo >/dev/null 2>&1; then
    echo "found: $(cargo --version)"
else
    echo "cargo not found, installing via rustup..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    # shellcheck disable=SC1091
    source "$HOME/.cargo/env"
fi

# ---------------------------------------------------------------------------
if [ "$SKIP_TESTDATA" = "1" ]; then
    log "Skipping test_data regeneration (--skip-testdata)"
else
    log "nauty (geng/genbg, C library)"
    if command -v geng >/dev/null 2>&1; then
        echo "found: $(command -v geng)"
    else
        os="$(uname -s)"
        if [ "$os" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
            echo "geng not found, installing via Homebrew..."
            brew install nauty
        elif [ "$os" = "Linux" ] && command -v apt-get >/dev/null 2>&1; then
            echo "geng not found, installing via apt..."
            sudo apt-get update && sudo apt-get install -y nauty
        else
            echo "geng not found and no supported package manager detected." >&2
            echo "Install nauty manually from https://pallini.di.uniroma1.it/" >&2
            echo "(./configure && make), or re-run with --skip-testdata." >&2
            exit 1
        fi
    fi

    log "Python env (pynauty + networkx)"
    PY=python3
    if ! command -v "$PY" >/dev/null 2>&1; then
        echo "python3 not found — install it, or re-run with --skip-testdata." >&2
        exit 1
    fi
    VENV="$ROOT/.venv-testdata"
    if [ ! -d "$VENV" ]; then
        "$PY" -m venv "$VENV"
    fi
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet pynauty networkx

    log "Regenerating test_data/*.g6 (geng — exact match verified against original corpora)"
    mkdir -p test_data
    geng 9 test_data/all_9.g6
    geng -b 10 test_data/bipartite_10.g6
    geng -c 10 test_data/connected_10.g6
    geng -d3D3 10 test_data/cubic_10.g6
    geng -t 11 test_data/triangle_free_11.g6
    geng -P 9 test_data/perfect_9.g6
    geng -T 9 test_data/chordal_9.g6
    geng -F 9 test_data/clawfree_9.g6
    geng -k 9 test_data/k4free_9.g6
    geng -C 9 test_data/biconnected_9.g6
    geng -d4D4 10 test_data/regular4_10.g6
    geng -S 10 test_data/split_10.g6

    log "Regenerating test_data/large_*.g6 (networkx: word-boundary sizes 63-513)"
    "$VENV/bin/python3" tools/gen_large_g6.py

    log "Regenerating test_data/random_mixed.g6 (networkx: unstructured G(n,p) graphs)"
    "$VENV/bin/python3" tools/gen_random_g6.py

    log "Regenerating test_data/*.ref (pynauty ground truth)"
    "$VENV/bin/python3" tools/gen_g6_vectors.py

    # The committed smoke corpus is a deterministic sample of the above; it is
    # what a plain `cargo test` cross-validates on a fresh clone.
    log "Regenerating test_data/smoke/ (committed cross-validation sample)"
    "$VENV/bin/python3" tools/gen_smoke_corpus.py
fi

# ---------------------------------------------------------------------------
log "Build + test"
cargo build --tests
if [ "$SKIP_TESTDATA" = "1" ]; then
    cargo test
else
    cargo test -- --include-ignored
fi

log "Done"
