# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `test_data/smoke/`: a committed 1 965-graph cross-validation corpus with
  pynauty reference canonical forms, so a plain `cargo test` on a fresh clone
  verifies canonical forms against C nauty without running `./setup.sh`
  (`tools/gen_smoke_corpus.py`).
- `repro/`: scripts that regenerate every number and figure in the paper
  (`collect_criterion.py`, `make_tables.py`, `plot_figures.py`,
  `measure_memory.sh`) together with the collected measurement data.
- `src/bin/memcheck` reports heap traffic through a counting global allocator,
  separating set-up allocations from steady-state ones.
- Continuous integration (`.github/workflows/ci.yml`): tests on Linux/macOS/
  Windows, MSRV 1.85, clippy, Miri, the full pynauty cross-validation, and the
  Python bindings.
- `CITATION.cff`.
- Refinement-blind graph generators (`canonaut::generators`): Cai-Fürer-Immerman
  graphs over the 3-regular circulant (twisted and untwisted), Sylvester
  Hadamard bipartite graphs, and Paley graphs — plus a `hard` benchmark group
  and tests that use them as ground truth (twisted and untwisted CFI graphs
  must receive different canonical forms; |Aut| of the Paley graph on q
  vertices must be q(q-1)/2).
- `tests::test_word_boundary_paths`: fast canonicalizations covering
  m = 1, 2, 3, 4 words per vertex — the subset the Miri CI job runs.

### Changed

- Graph generators moved from `canonaut::tests` to `canonaut::generators`; the
  test suite and its fixtures are now `#[cfg(test)]` and no longer part of the
  published library.
- Corpus-driven tests skip with a message instead of failing when the
  (uncommitted) full corpora have not been regenerated.

### Fixed

- Short-prune condition in the automorphism-processing branches compared
  `gca_canonical_level` with itself, so `needs_short_prune` was never set. It
  now compares against `gca_first_level`, matching nauty's
  `if (gca_canon != gca_first) needshortprune = TRUE`.
- `fmperm_safe` allocated an `n`-byte visited array on every call for n > 64,
  i.e. once per automorphism found; it now uses a thread-local scratch buffer,
  making steady-state canonicalization allocation-free at every tested size.

### Removed

- Dead C-translation leftovers `itos`, `writeperm`, `fmperm` and `alloc_error`
  (all `pub unsafe fn` with no callers). No `unsafe fn` remains in the public
  API.
- Two no-op `std::mem::transmute` calls on `&[u32]` slices.

## [1.0.0]

- First release: dense canonical labeling, automorphism group generators,
  orbits via the Schreier–Sims chain, vertex-coloured canonicalization,
  digraphs, graph6 I/O, and the `canonaut` Python bindings.
