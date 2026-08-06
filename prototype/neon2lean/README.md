# Typed Neon/RVV-to-Lean prototype

This RFC prototype explores a fail-closed path from restricted C/intrinsic
programs to Lean:

```text
pinned C translation units
  -> Clang JSON AST frontend
  -> typed source and target KernelIR data
  -> reviewed Lean interpreter
  -> fixed observational-equivalence theorem
```

It is not a proof about production SaltyRN kernels, compiled binaries, or the
Arm/RISC-V ISAs. The current executable case is deliberately synthetic and
integer-only.

## Artifact structure

`Neon2LeanDemo/Production/` defines:

- `ArtifactEnvelope` for source hashes, ranges, frontend provenance, and
  translation coverage;
- typed scalar, fixed-vector, scalable-vector, and mask values;
- byte-addressed partial memory and explicit effects;
- `KernelIR`, an integer-only feature gate, and an interpreter;
- explicit contracts and observation relations;
- `PositivePartition`, a generic progress model that does not claim exact
  `vsetvl` legality.

The frontend emits data, not theorem bodies. Lean owns the operation registry,
interpreter, contracts, observations, and final theorem statements.

## Generated `s8-clamp16` slice

`cases/s8-clamp16/` contains a restricted pair:

- the Neon-style side loads, clamps, and stores one fixed 16-byte vector;
- the RVV-style side strip-mines the same 16 bytes using a positive chunk
  schedule.

The checked manifest binds all 47 Neon and 71 RVV function-body AST nodes to
parameters, operations, or structured control. Lean rechecks source ranges,
hashes, operation descriptors, types, registry identity, single-block use
order, and bidirectional coverage before interpreting the generated programs.

`generated_success_under_contract` proves, for every positive partition of 16:

- both generated programs execute successfully under the explicit contract;
- their outputs and final memories are equal;
- memory outside the output range is preserved;
- both write summaries contain exactly the 16 output addresses.

`Mutation.lean` replaces the supported RVV min operation with a second max.
Structural validation still succeeds, while Lean execution proves a concrete
inequivalence.

## Reproduction

From the repository root:

```sh
python3 prototype/neon2lean/tools/check_e2e.py --repo-root .
```

The gate checks semantic regeneration, supported and unsupported mutations,
malformed manifests, the Lean build, forbidden proof tokens, and exported
theorem axioms. Pass a different Clang executable with `--clang PATH`.

Extraction uses the canonical parse target `x86_64-unknown-linux-gnu` and does
not read platform headers. The manifest retains the exact producer Clang
version. Cross-version freshness comparison ignores only that version string;
source/header/extractor hashes, preprocessed hashes, AST coverage, typed IR, and
control metadata must remain identical. Lean generated on the current host is
compiled separately.

To regenerate the checked artifacts explicitly:

```sh
python3 prototype/neon2lean/tools/extract_s8_clamp16.py \
  --repo-root . \
  --neon prototype/neon2lean/cases/s8-clamp16/neon.c \
  --rvv prototype/neon2lean/cases/s8-clamp16/rvv.c \
  --facade prototype/neon2lean/cases/s8-clamp16/intrinsics_facade.h \
  --output prototype/neon2lean/artifacts/s8-clamp16/manifest.json

python3 prototype/neon2lean/tools/emit_s8_clamp16_lean.py \
  --manifest prototype/neon2lean/artifacts/s8-clamp16/manifest.json \
  --output prototype/neon2lean/Neon2LeanDemo/S8Clamp16/Generated.lean
```

## Verification boundary

The following remain external or incomplete:

- semantic preservation from Clang AST to normalized operations;
- adequacy of the reviewed operation registry to Arm and RISC-V semantics;
- a C abstract-machine model, including undefined behavior and general aliasing;
- exact characterization of legal RVV `vsetvl` traces;
- production-kernel control flow, tails, and physical memory behavior;
- all floating-point operations and FP environment state.

Proof automation may propose proof terms, but it must not change the generated
programs, contracts, observations, theorem statements, or allowed-axiom policy.
