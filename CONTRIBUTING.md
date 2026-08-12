# Contributing to canonaut

Bug reports, reproducers, and patches are welcome. `canonaut` is a port of
nauty, so the bar for changes in the search core is deliberately high: the
canonical form a given graph receives is an API contract (it must stay
byte-identical to C nauty's), and the algorithm mirrors nauty's control flow so
the two can be diffed against each other.

## Getting set up

```sh
./setup.sh                    # Rust toolchain, nauty, a Python venv with
                              # pynauty/networkx, regenerated test_data/, tests
./setup.sh --skip-testdata    # just build and run the tests
```

## Before opening a pull request

```sh
cargo test                    # 105 tests, incl. the committed smoke corpus
cargo test -- --include-ignored   # + the full pynauty cross-validation
cargo clippy --all-targets -- -D warnings
```

Changes to the search, refinement, or bitset routines should also be checked
under Miri, which is what the CI job runs:

```sh
MIRIFLAGS=-Zmiri-disable-isolation cargo +nightly miri test --lib -- \
  --skip g6 --skip large --skip smoke --skip fuzz \
  --skip hard_instances --skip test_graphs --skip test_random --skip test_known
```

If a change can affect performance, report before/after numbers from
`cargo bench --features c-nauty-bench` (see `repro/README.md`).

## Ground rules for the core

- **Canonical forms may not change.** `test_data/smoke/` and the full corpora
  compare canonaut's output byte-for-byte against pynauty; any change that
  moves those outputs is a breaking change, not a bug fix.
- **`unsafe` stays internal and justified.** Every `unsafe` block carries a
  `// SAFETY:` comment stating the invariant that makes it sound. The public
  API contains no `unsafe fn`; keep it that way.
- **No allocation in the steady state.** `CanonautManager` owns its buffers and
  reuses them; `src/bin/memcheck` reports steady-state allocation counts and
  they should stay at zero.
- **Naming.** Identifiers are spelled out (`words_per_vertex`, not `m`) even
  where nauty abbreviates; a comment naming the nauty counterpart is welcome.

## Reporting a bug

A report is most useful with the graph that triggers it in graph6 form, the
`CanonautManager` configuration used, and what C nauty (or pynauty) returns for
the same input.
