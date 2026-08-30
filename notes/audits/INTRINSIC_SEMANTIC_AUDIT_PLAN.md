# Intrinsic Semantic Audit Plan

Audit start: 2026-08-30 (Asia/Seoul)
Scope: all 184 semantically distinct exact intrinsic variants in `IntrinsicRegistry.json`

## Objective

Determine whether each exact Lean intrinsic denotation faithfully represents the
Neon or RVV operation used by the real C kernels, at the explicitly stated value
and architecture conditions. This is a deeper audit than the existing hash-bound
review closure.

**Confirmed distinction:** the current 180/180 used-variant review proves that the
exact signature, descriptor, implementation hash, primary-source binding, Lean
build, and review artifacts are current. It does not by itself prove semantic
adequacy against complete Arm/RISC-V behavior. The four unused variants have no
current schema-v2 review.

The inventory was initially reported as 189. One duplicate `vrshlq_s32`
descriptor and four contextual scalarized Neon max/min descriptors were repaired
and then collapsed onto existing faithful exact capabilities. The final 184 count
therefore removes duplicate audit identities, not supported behavior.

## Unit of Audit

One row represents one exact `capability_id`, not one spelling. Two descriptors
with the same C spelling remain separate rows when their types or semantics differ.

Each row must bind three objects:

1. the real Neon or RVV C call sites and argument/`vl`/immediate order;
2. the pinned official intrinsic prototype and ISA operation/version;
3. the exact Lean semantic symbol and transitive implementation hash.

## Evidence Ladder

| Level | Name | Required evidence |
|---|---|---|
| L0 | inventory | exact ID, signature, role, usage, implementation hash |
| L1 | provenance-checked | official prototype and ISA selector match the C call |
| L2 | semantics-reviewed | independent manual comparison covers normal and edge behavior |
| L3 | differential-checked | adversarial executable/oracle tests compare C/ISA with Lean |
| L4 | adequacy-proved | a theorem connects the Lean definition to an independent formal ISA model |

Existing review approval is recorded separately from this ladder. A row is not
called semantically confirmed merely because it passed the old review.

## Deep Verdicts

- `confirmed`: evidence at the row's current ladder level found no semantic gap;
- `conditional`: correct only under explicit state or input conditions;
- `needs_deep_audit`: provenance exists but edge semantics remain unchecked;
- `suspected_bug`: a concrete mismatch is plausible and needs reproduction;
- `confirmed_bug`: an independently reproducible mismatch exists;
- `unused_unreviewed`: registry variant is outside the current 19-program closure.

## Risk Priority

1. **P0:** FP arithmetic, min/max, comparison, conversion, NaN/state-sensitive
   operations, and any helper that delegates to host `Float32`;
2. **P1:** fixed-point rounding, saturation, narrowing, shift masking, `vxrm`,
   `vxsat`, lane insertion/extraction, partial load/store;
3. **P2:** `vsetvl`, active-lane/mask/tail behavior, permutation, widening, merge;
4. **P3:** exact-width integer/bitwise arithmetic and representation-preserving
   reinterpretation.

## Per-Row Checklist

1. Match exact C prototype, return type, parameter order, signedness, lane shape,
   immediate range, and active `vl` use.
2. Identify the official ISA instruction and architectural state read or written.
3. Compare the Lean definition branch by branch, including overflow, underflow,
   NaN, signed zero, saturation, shift extremes, and empty/partial active lanes as
   applicable.
4. Record all assumptions rather than silently normalizing them.
5. Add adversarial tests. Exhaust 8-bit domains when practical; use boundary sets
   for 16/32-bit integers and binary32 bit-pattern classes.
6. Require an independent reviewer before promoting a row to L2 or above.
7. Treat L4 as a separate Arm/RISC-V formal-model bridge, not as a spreadsheet
   checkbox obtainable by inspection.

## Execution Order

1. Audit P0 floating-point variants and the two positive program proofs first.
2. Audit P1 rounding/saturation/shift variants used by blocked quantized programs.
3. Audit P2 schedule, mask, tail, lane, and permutation semantics.
4. Batch-check P3 exact integer operations with exhaustive or algebraic tests.
5. Re-run every dependent program whenever a semantic definition changes, then
   republish all content-addressed review and result artifacts.

## Acceptance Gate

The CSV is an audit tracker, not a new source of truth for proof acceptance. A
semantic status promotion requires evidence files or executable commands in the
repository and an independent reviewer. Any implementation change must flow
through the existing registry, audit plan, Lean checks, program regeneration, and
program-review closure.
