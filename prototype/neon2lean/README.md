# NEON to typed Lean IR demo

This prototype extracts the 64-byte main loop from the real
`kernels/source/u8-vclamp.c` file. It uses Clang's semantic JSON AST,
not source-text matching, and emits a deeply embedded Lean term.

The generated term preserves:

- 16 lanes and 8-bit elements in the Lean type;
- the four input/output offsets;
- unsigned `max` then unsigned `min` intrinsic dataflow;
- the `uint32_t` parameter to `uint8_t` low-bit conversion performed by `vdupq_n_u8`;
- the loop guard/decrement and pointer advances;
- the source path, SHA-256 digest, and AST byte range.

Run from the workspace root:

```bash
python3 prototype/neon2lean/tools/extract_u8_vclamp.py \
  --repo-root . \
  kernels/source/u8-vclamp.c \
  --output prototype/neon2lean/Neon2LeanDemo/Generated.lean

cd prototype/neon2lean
lake build
```

Run all reproducibility, frontend, build, source-policy, and exported-axiom gates from
the repository root:

```sh
python3 prototype/neon2lean/tools/check_e2e.py --repo-root .
```

`Proof.lean` checks that every extracted 16-byte store implements unsigned clamp and
that one main-loop iteration writes exactly offsets `[0, 64)`. The parse facade only
keeps intrinsic spellings and C types visible to Clang; all operation semantics live in
Lean. It also proves the scalar lemma needed to reconcile the main-loop and tail clamp
orders under the post-truncation `min <= max` condition.

This is intentionally not a full `u8-vclamp` proof yet. The 8-byte loop and 4/2/1-byte
tail should become separate schedule nodes after the main-loop IR is accepted.

## Integer production skeleton

`Neon2LeanDemo/Production/` is the next schema revision. It adds build/source
provenance, fixed and scalable vector tags, an integer-only fail-closed feature gate,
allocation-aware byte memory, explicit contracts, and configurable observations.
Floating-point tags are preserved, but no FP operation has a denotation yet.

The first paired value-level slice is under `Neon2LeanDemo/S8VClamp/`. It proves that
the source's 64/8/tail value schedule and every positive chunk partition compute the
same signed clamp. This is deliberately an auxiliary theorem: the physical tail
read, RVV `vsetvl` legality, generated artifact binding, and final memory/frame
theorem remain separate acceptance gates.

Generate the fail-closed AST audit manifest with:

```bash
python3 prototype/neon2lean/tools/extract_s8_vclamp.py \
  --repo-root . \
  --source kernels/source/s8-vclamp.c \
  --target kernels/target/s8-vclamp.c \
  --output prototype/neon2lean/artifacts/s8-vclamp/manifest.json

python3 prototype/neon2lean/tools/emit_s8_manifest_lean.py \
  --manifest prototype/neon2lean/artifacts/s8-vclamp/manifest.json \
  --output prototype/neon2lean/Neon2LeanDemo/S8VClamp/GeneratedArtifact.lean
```

Every current AST entry is deliberately emitted as `AST_AUDIT_ONLY`, not as a
translated IR node. Consequently the generated envelopes are internally bound audit
claims but `claimsFullTranslation = false`. Even a true emitter claim is not enough:
`KernelIR.hasConsistentCoverageBinding` additionally checks typed IR references,
reference shape, ranges, and bidirectional coverage. It does not establish SSA
dominance or C-semantics preservation. Semantic KernelIR lowering is not implemented
for this slice yet.

Run the fail-closed regression checks from the workspace root:

```bash
python3 prototype/neon2lean/tools/test_s8_extractor.py --workspace .
```

The checks cover deterministic baseline extraction, unknown-intrinsic rejection,
reachable-FP rejection, and rejection of an allowlisted-intrinsic semantic mutation.

## Generated semantic `s8-clamp16` slice

`cases/s8-clamp16/` is the first paired slice whose final theorem directly executes
generated `Production.KernelIR` values. The Neon translation unit contains one
16-byte load/splat/max/min/store block. The RVV translation unit contains a
`while + vsetvl` strip-mined loop. The frontend lowers the supported statement and
intrinsic subset to operation data; it does not require the calls to match the
expected clamp theorem.

The checked artifacts bind 47/47 Neon and 71/71 RVV function-body AST nodes to
parameters, operations, or the structured-control block. Lean then rechecks exact
function identity/range, hashes, registry identity, operation signatures, SEW/LMUL,
single-block use order, and coverage before interpreting the generated operations.

Generate and test from the repository root:

```bash
python3 prototype/neon2lean/tools/extract_s8_clamp16.py \
  --repo-root . \
  --neon prototype/neon2lean/cases/s8-clamp16/neon.c \
  --rvv prototype/neon2lean/cases/s8-clamp16/rvv.c \
  --facade prototype/neon2lean/cases/s8-clamp16/intrinsics_facade.h \
  --output prototype/neon2lean/artifacts/s8-clamp16/manifest.json

python3 prototype/neon2lean/tools/emit_s8_clamp16_lean.py \
  --manifest prototype/neon2lean/artifacts/s8-clamp16/manifest.json \
  --output prototype/neon2lean/Neon2LeanDemo/S8Clamp16/Generated.lean

python3 prototype/neon2lean/tools/test_s8_clamp16.py --repo-root .
```

`generated_success_under_contract` proves successful execution, final-memory
equivalence, an output-range frame condition, and the exact 16-address write summary
for every positive progress partition of 16. `Mutation.lean` changes the generated
RVV min operation to a second supported max operation: registry and IR validation
still pass, while Lean execution produces a concrete inequivalence proof.

This is an honest semantic-IR E2E for a restricted synthetic C subset, not yet a
theorem about Arm/RISC-V ISA execution. The Clang-to-normalized-subset bridge, the
transactional final-state memory quotient, and intrinsic-to-ISA adequacy remain
reviewed proof obligations. The positive partitions are a conservative progress
model, not a claim that every partition is an ISA-realizable `vsetvl` trace.
