# Growing bounded verification coverage within ten minutes

Audit: 2026-09-10, `Saltyrn-final`, branch `main`, HEAD `6acdf7a` plus the existing working-tree changes. Solver measurements use the locally installed cvc5 1.3.1 and Bitwuzla 0.8.2-dev on this Mac, VLEN=256. These are exploratory single-run measurements, not a ten-minute benchmark or a statistical speedup claim. Compilation is excluded from the reported verification-process times.

## Main finding

Six of the seven "specific dims" kernels stop at a fixed grid. They do not keep growing until the time budget expires. The highest-priority improvement is an expanding, validity-aware shape scheduler with accurate per-shape results. It can use the existing bounded SMT queries without invariants, abstractions, new input restrictions, or changed comparison tolerances.

Current fixture definitions are in `src/workflow/verification/engine/emit.py`:

| Kernel | Current shape schedule |
|---|---|
| f32-dwconv2d-chw | 18 fixed shapes: height 1–6; width 16,20,32 **bytes** |
| f32-dwconv-minmax | Already grows channels; output_width stays in {1,2} |
| f32-conv-hwc2chw | 180 fixed shapes: 5 heights × 6 widths × 6 output-channel counts |
| x32-packw-gemm-goi | 80 fixed shapes: 2 groups × 5 column counts × 4 reduction sizes × 2 padding sizes |
| qd8-f32-qc4w-gemm-minmax | 35 fixed shapes: mr=1; 7 column counts × 5 reduction sizes |
| f32-igemm-minmax | 8 fixed shapes: mr=1; 4 column counts × 2 reduction sizes |
| f32-gemm-minmax | 32 fixed shapes: 4 row counts × 4 column counts × 2 reduction sizes |

`nest()` traverses nested loops in dimension order, rather than sorting shapes globally by cost. Each call receives all remaining time. A difficult early shape can consume the remaining budget; grow-mode loops stop after their first timeout.

## Confirmed expansion opportunity

The unmodified packw orchestrator, with a 15-second budget, proved all **80 existing shapes in about 0.7 seconds** and stopped. Its grid fixes `kc` to 1,2,3,4.

An isolated generated-harness experiment changed only that dimension list to **5,6,7,8**, retaining the same g, nc, extra_bytes values, constraints, kernel sources, VLEN, and comparison. It proved **80 additional shapes in 0.99 seconds**. No new input assumptions or invariants were introduced. This validates expansion for those particular shapes; it does not prove arbitrary kc.

Artifacts:

- `build/verification_cvc5/optimization_study/packw_grid.log`
- `build/verification_cvc5/optimization_study/packw_extended_results.json`
- `build/verification_cvc5/optimization_study/packw_extended/harnesses/verify_x32-packw-gemm-goi.cpp`

## Query-level experiments

I generated identical single-shape workloads with the existing fixtures and **no added input-range restriction**. The split variant flattens the final output conjunction, then uses incremental cvc5 `checkSatAssuming(not(output_equality))` for every leaf while keeping all original assertions. Every leaf must be UNSAT for the shape to pass; SAT or unknown does not pass. This is the same logical obligation, not a sample of output lanes.

| Kernel / shape | Existing cvc5 query | Split output queries | Same formula through external Bitwuzla |
|---|---:|---:|---:|
| GEMM mr=4,nc=12,kc=8 bytes | 3.26 s, pass | 4.35 s, pass (48 outputs) | 8.41 s, pass |
| HWC→CHW conv H=1,W=2,OC=4 | 5.67 s, pass | 5.83 s, pass (4 outputs) | 10.67 s, timeout |
| Depthwise CHW H=1,width=16 bytes | 1.78 s, pass | 1.88 s, pass (4 outputs) | 1.72 s, pass |

These samples do **not** justify enabling output splitting or routing all floating-point formulas to Bitwuzla. Splitting kept the unrelated assertions in the solver; dependency-aware slicing is a different, untested optimization and would require additional soundness checks.

Two additional option probes (`fp-lazy-wb=true`, `bv-solver=bitblast`) also passed these shapes. `bitblast` is already the installed solver's default. Runs were not randomized/repeated, so the lower later timings cannot establish a speedup. No solver defaults were changed.

Reproduction scripts and raw results are under `build/verification_cvc5/optimization_study/`: `compare.py`, `results.json`, `portfolio.py`, `portfolio_results.json`, `options.py`, and `options_results.json`.

API reference used for the incremental experiment: [cvc5 C++ API](https://cvc5.github.io/docs/cvc5-1.3.1/api/cpp/cpp.html).

## Recommended implementation

1. **Generate expanding legal shapes and compile the harness once.** Keep the current grids as initial coverage, then add new shapes around their frontiers. Grow dimensions using their correct units and preserve kernel limits: GEMM mr<=4, IGEMM mr=1, f32 kc in multiples of four bytes. A largest size is not evidence for smaller untested sizes.
2. **Use bounded slices per shape, then retry deferred shapes.** For example, try 5 seconds, then 20, then 80, each capped by the remaining total 600-second deadline. These slice sizes are starting heuristics, not measured optima. Include formula construction in the deadline, and terminate a silent worker at its deadline. This can avoid spending the entire budget on one shape, at the cost of repeated work on deferred shapes.
3. **Record both throughput and complete coverage.** Preserve named dimension tuples, verdicts, query time, VLEN, input/parameter restrictions, and source/model hashes. Report the exact verified set and the largest completely verified region in the declared shape domain. A skipped/timed-out shape remains a hole; never promote a maximum observed dimension into a proof of the entire region.
4. **Parallelize independent shapes only under a declared resource budget.** Separate solver processes can prove unchanged queries concurrently. Report worker count, CPU time, and memory alongside wall time, so comparisons against the old ten-minute run remain fair. This has not been benchmarked here.

Do not simply extend every current dimension list blindly. In particular, IGEMM currently has `cn_stride=0` and nc<=8. Extending nc beyond one output tile requires a valid output-stride fixture and a fresh layout audit. The quantized fixture also contains explicit packing constraints and a VLEN/layout comment that must be checked against the actual selected kernel pair.

## Reporting and deadline issues to fix with the scheduler

- `run_verification()` displays `dims` but discards them when recording successful `BatchResult`s. Multidimensional passes become `batch=0`; JSON exposes a count but not the verified shapes. The final `grow_dim`/`grow_cross` and `reached` fields are not preserved either.
- The harness sets the query timeout **after** constructing formulas, using the time remaining **before** construction. Expensive construction can therefore overshoot the intended budget.
- The Python watchdog checks elapsed time inside `for line in proc.stdout`; a silent solver can keep that loop blocked, so this is not an independent hard deadline.
- Fixed-grid harnesses print `ALL_VERIFIED` even after timeout events. The current orchestrator notices the timeout and downgrades the verdict; raw-log consumers must also inspect every verdict rather than trust the final line.

## Formal scope

Scheduling changes need no additional invariants: each accepted shape still requires UNSAT for the original mismatch query under the original fixture assumptions. Unknown, timeout, crash, or a missing result never counts as a pass. Cache/replay is valid only for matching sources, semantic model, dimensions/strides/packing, VLEN, parameter assumptions, input domain, and comparison policy. Fresh ten-minute throughput measurements must not silently include results cached from previous runs.

The current claims remain bounded output equivalence under the implemented intrinsic/memory model and fixture restrictions. In particular, the current FP comparison equates signed zeros and accepts NaN-vs-NaN; fixture comments describing a small grid as covering production behavior are not proofs for untested sizes. These experiments preserved the current comparison and model.

This review created isolated experimental harnesses and this report. The production fixture grids, solver defaults, and verification semantics have not been changed.
