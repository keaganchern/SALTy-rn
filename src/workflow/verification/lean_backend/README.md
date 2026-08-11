# Restricted C-Intrinsic to Lean Backend

This directory contains a restricted automatic Lean backend for five current
integer Neon/RVV pairs. It does not consume CVC5 terms.

## Current Pipeline

```text
pinned C source and target
  -> Clang JSON AST for fixed target triples
  -> typed calls, dataflow, source ranges, and control facts
  -> exact intrinsic registry and fail-closed binding checks
  -> deterministic registry-bound manifest
  -> independent executable Neon and RVV Lean block models
  -> reviewed Lean bridge proof
```

`schema.py`, `registry.py`, and `scaleup_catalog.py` define the supported types,
exact C signatures, semantic immediates, and corresponding `SALT.Intrinsics`
definitions. `profiles.py` fixes each pair's Clang parse contract. `frontend.py`
extracts the selected C bodies. `binding.py` checks artifact freshness, call
inventory, types, immediate values, operand provenance, and reviewed control
facts. `emit_lean.py` handles the first golden case; `case_emit.py` handles the
four scale-up block profiles. Unknown or unmodeled calls, casts, operators,
effects, directives, and control shapes are rejected.

Generate a manifest and the checked-in Lean models from the repository root:

```sh
PYTHONPATH=src python3 -m workflow.verification.lean_backend.generate \
  --repository-root . \
  --output /tmp/qs8-vadd-minmax-manifest.json \
  --lean-out src/verification_bw/lean/SALT/Generated/QS8VAddMinmax/Models.lean
```

Run the frontend and mutation tests:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python3 -m pytest -q -p no:cacheprovider tests/verification/lean_backend
```

Build the generated proof from `src/verification_bw/lean`:

```sh
lake build SALT.Generated.QS8VAddMinmax.Proof
```

Generate the four additional block-model pairs:

```sh
PYTHONPATH=src python3 -m workflow.verification.lean_backend.generate_cases \
  --repository-root .

# Deterministic freshness check without writing files.
PYTHONPATH=src python3 -m workflow.verification.lean_backend.generate_cases \
  --repository-root . --check
```

The generated set is:

```text
qs8-vadd-minmax   signed binary fixed-point add and clamp
s8-vclamp        signed unary clamp (64-lane Neon main block)
qs8-vcvt         signed widening, qrdmulh, rounding, and narrowing
qs8-vlrelu       signed compare, mask/select, scaling, and narrowing
qu8-vadd-minmax  unsigned binary arithmetic and a reviewed signed-shift branch
```

## Established Boundary

The generated Lean definitions independently execute one selected Neon main
block and one RVV active chunk. The original `QS8VAddMinmax/Proof.lean` proves
its two block models equal for well-formed parameters and two 16-lane inputs.
`S8VClamp/Proof.lean` additionally proves equality of the generated 64-lane
Neon block and RVV chunk for inputs of length 64. `QS8VCvt/Proof.lean` proves
the generated 8-lane conversion blocks equal under the parameter domain of the
pinned `XNNPACK@867d5a344790802ee067be62f572c2e2722bf6fb` revision. The
[zero-point checks](https://github.com/google/XNNPACK/blob/867d5a344790802ee067be62f572c2e2722bf6fb/src/tensor.c#L50-L70)
and [conversion multiplier construction](https://github.com/google/XNNPACK/blob/867d5a344790802ee067be62f572c2e2722bf6fb/src/microparams-init.c#L1207-L1223)
are the external evidence for that contract. The remaining generated modules
are executable translation artifacts; a module is not called proved merely
because both definitions typecheck.

An unconstrained `qs8-vcvt` theorem is false at the qrdmulh
`(-32768, -32768)` corner because the current RVV doubling sequence wraps before
narrowing. The proof uses the full XNN contract: signed 8-bit input/output zero
points and a multiplier in `[1, 32768]`. The arithmetic step only needs the input
zero-point bound: after subtracting an input byte and shifting by seven, the
first qrdmulh operand lies in `[-32640, 32640]`, so the exceptional pair is
unreachable. The dynamic QU8 shift still needs its reviewed effective-range
contract.

`SALT/Kernel/Schedule.lean` separately proves generic fixed-chunk/tail and
positive-partition refinements to `List.map`/`List.zipWith` for arbitrary list
lengths. The current generated proof does not yet connect the complete Neon tail,
C memory effects, or real `vsetvl` executions to those schedule theorems.

Therefore the result is generated Lean block-model equivalence. It is not yet a
C-source observational-equivalence theorem, an intrinsic-to-ISA adequacy theorem,
or a compiled-binary theorem.
