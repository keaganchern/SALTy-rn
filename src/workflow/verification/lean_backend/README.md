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
  -> independent executable Neon and RVV Lean value models
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

Generate the four additional model pairs and configured protected obligations:

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
s8-vclamp        signed unary clamp (generated 64/8/4/2/1 value schedule)
qs8-vcvt         signed widening, qrdmulh, rounding, and narrowing
qs8-vlrelu       signed compare, mask/select, scaling, and narrowing
qu8-vadd-minmax  unsigned binary arithmetic and a reviewed signed-shift branch
```

## Established Boundary

Most generated Lean definitions independently execute one selected Neon main
block and one RVV active chunk. The original `QS8VAddMinmax/Proof.lean` proves
its two block models equal for well-formed parameters and two 16-lane inputs.
For `s8-vclamp`, the frontend validates and consumes all 36 Neon intrinsic calls
and emits the 64-lane, 8-lane, and 4/2/1 live-prefix value paths.
`S8VClamp/AllLengths.lean` proves that the generated Neon value schedule is
equal to an RVV chunk model for every input length and every complete positive partition,
under ordered clamp bounds. Its stronger entry theorem takes arbitrary values for
seven would-be tail-overread bytes and proves that their contents do not affect
the live output. This is not a proof that the physical overread is legal.
`QS8VCvt/Proof.lean` proves
the generated conversion blocks equal under the parameter domain of the
pinned `XNNPACK@867d5a344790802ee067be62f572c2e2722bf6fb` revision. The
[zero-point checks](https://github.com/google/XNNPACK/blob/867d5a344790802ee067be62f572c2e2722bf6fb/src/tensor.c#L50-L70)
and [conversion multiplier construction](https://github.com/google/XNNPACK/blob/867d5a344790802ee067be62f572c2e2722bf6fb/src/microparams-init.c#L1103-L1118)
are the external evidence for that contract. `QS8VLReLU/Proof.lean` proves the
generated 8-lane LReLU blocks equal for every 32-bit parameter representation.
The deterministic `QS8VLReLU/Obligation.lean` fixes the arbitrary-length claim,
and the separately reviewed `QS8VLReLU/CandidateProof.lean` proves it for every
input length, every sufficient tail-overread value list, and every complete
positive RVV partition. Its contract argument records XNN's legal producer domain. The
[LReLU multiplier construction](https://github.com/google/XNNPACK/blob/867d5a344790802ee067be62f572c2e2722bf6fb/src/microparams-init.c#L619-L646)
provides the multiplier ranges. `QU8VAddMinmax/Proof.lean` proves its generated
8-lane blocks equal when the effective shift is at most 31. Its contract-bound
entry point records the pinned producer's shift, multiplier, output-zero-point,
and fixed clamp invariants. The
[QU8 add parameter construction](https://github.com/google/XNNPACK/blob/867d5a344790802ee067be62f572c2e2722bf6fb/src/microparams-init.c#L830-L882)
and XNN's validation of
[QU8 zero points](https://github.com/google/XNNPACK/blob/867d5a344790802ee067be62f572c2e2722bf6fb/src/tensor.c#L50-L78)
and [positive finite scales](https://github.com/google/XNNPACK/blob/867d5a344790802ee067be62f572c2e2722bf6fb/src/tensor.c#L318-L343)
are the external evidence for those invariants.

An unconstrained `qs8-vcvt` theorem is false at the qrdmulh
`(-32768, -32768)` corner because the current RVV doubling sequence wraps before
narrowing. The proof uses the full XNN contract: signed 8-bit input/output zero
points and a multiplier in `[1, 32768]`. The arithmetic step only needs the input
zero-point bound: after subtracting an input byte and shifting by seven, the
first qrdmulh operand lies in `[-32640, 32640]`, so the exceptional pair is
unreachable. The LReLU target instead narrows the exact 16-by-16 product with a
shift of 15, so its value equality includes the signed-minimum multiplication
corner without a parameter hypothesis. Both qrdmulh results omit architectural
saturation flags. The QU8 proof likewise establishes lane values only; it does
not relate Neon QC to RVV `vxsat` or model the persistent `vxrm` state.

`SALT/Kernel/Schedule.lean` proves generic fixed-chunk/tail and
positive-partition refinements to `List.map`/`List.zipWith` for arbitrary list
lengths. The `s8-vclamp`, `qs8-vcvt`, and `qs8-vlrelu` adapters use a little-endian
live-prefix value abstraction for their 4/2/1 lane stores. They prove content independence
for any seven supplied byte values after a short tail, but do not establish
their C-memory readability, alignment, aliasing, host endianness, or real
`vsetvl`/ISA executions. `qs8-vcvt` consumes all 23 reachable Neon calls and all
11 RVV calls; `qs8-vlrelu` consumes all 30 Neon and all 13 RVV calls when
generating their full value models. The VCVT case-specific
`Proof.lean` remains reviewed code; `generate_cases.py` generates the protected
LReLU obligation but not its candidate proof. The other two scale-up cases remain
selected-block results and do not yet connect their complete Neon tails to the
schedule theorems.

Therefore these are generated Lean value-model equivalence results; only the
`s8-vclamp`, `qs8-vcvt`, and `qs8-vlrelu` results currently quantify over
arbitrary input lengths. They are not yet C-source observational-equivalence,
intrinsic-to-ISA adequacy, or compiled-binary theorems.

A smaller Chinese teaching example is available at
`examples/s8-vmax-to-lean/README.zh-CN.md`. Its synthetic Neon/RVV C pair goes
through this actual frontend and emitter and produces a checked local-block Lean
model and proof; it is kept outside the five real-kernel generation set.

## Intrinsic Coverage Dashboard

`kernels/xnnpack-kernel-families.csv` is the fixed 107-family catalog shared by
Keagan. It deliberately contains no generated or review status: kernel families,
concrete C programs, intrinsic spellings, Lean mappings, and review attestations
are different records.

The local dashboard in `src/workflow/verification/intrinsic_dashboard/` inventories
only the 40 local SALTyRN programs, projects the current restricted Lean registry,
and reports hash-bound independent reviews. Registry presence or a checked Lean
theorem is never presented as intrinsic semantic approval or C/ISA equivalence.
