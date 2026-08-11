# Restricted C-Intrinsic to Lean Backend

This directory contains the first automatic Lean backend for the current
`qs8-vadd-minmax` Neon/RVV pair. It does not consume CVC5 terms.

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

`schema.py` and `registry.py` define the supported types, exact C signatures,
immediates, and corresponding `SALT.Intrinsics` definitions. `frontend.py`
extracts the selected C bodies. `binding.py` checks artifact freshness, call
inventory, types, immediate values, operand provenance, and the reviewed control
shape. `emit_lean.py` emits the two executable block models. Unknown or unmodeled
calls, casts, operators, effects, directives, and control shapes are rejected.

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

## Established Boundary

The generated Lean definitions independently execute the selected Neon 16-lane
main block and one RVV active chunk. `Proof.lean` proves that these two block
models are equal for well-formed parameters and two 16-lane inputs.

`SALT/Kernel/Schedule.lean` separately proves generic fixed-chunk/tail and
positive-partition refinements to `List.map`/`List.zipWith` for arbitrary list
lengths. The current generated proof does not yet connect the complete Neon tail,
C memory effects, or real `vsetvl` executions to those schedule theorems.

Therefore the result is generated Lean block-model equivalence. It is not yet a
C-source observational-equivalence theorem, an intrinsic-to-ISA adequacy theorem,
or a compiled-binary theorem.
