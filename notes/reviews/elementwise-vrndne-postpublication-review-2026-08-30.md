# Elementwise VRNDNE Post-Publication Review

Date: 2026-08-30 (Asia/Seoul)

Reviewer: `agent:vrndne-plan-reviewer`

Baseline: `cc53aa51455d24ffd151404ba94bf3000e2a84c8`

Reviewed state: the current working tree on `feat/elementwise-compiler`, after the
formal intrinsic-review and program-outcome publications. This is a read-only
post-publication audit; it does not replace or modify either publisher-bound
review report.

## Blocking findings

None.

## Confirmed

- `SALT/Intrinsics/FP32.lean` now gives separate, explicitly conditioned value
  semantics for Arm and RISC-V floating-point operations. Under Arm
  `DN=0`, `AH=0`, `FZ=0`, RNE, and disabled FP traps, input NaNs are selected
  signaling-before-quiet and by operand order within each class, then quieted
  while preserving sign and payload. Non-NaN invalid operations produce the
  default/canonical NaN. The RISC-V RNE path canonicalizes every NaN result.
- The bit-level `lt` and `ne` definitions implement ordered binary32 comparison,
  NaN behavior, and `+0 = -0` correctly. Arm max/min propagates the selected NaN;
  RISC-V max/min implements maximumNumber/minimumNumber, including the signed-zero
  choice. Neon and RVV wrappers call the intended architecture-specific helpers.
- The relevant Neon floating arithmetic, conversion, max/min, and comparison audit
  subjects carry the required RN/FZ/DN/AH conditions and require all six Arm FP
  trap-enable bits to be zero. The AArch64 probe clears the same FPCR state and
  keeps FPSR outside its value-result claim.
- Relative to the baseline, the used-subject set remains exactly 180. Exactly 112
  semantic implementation hashes changed: 53 Neon and 59 RVV. The other 68 are
  unchanged; no used subject was added or removed.
- `f32-vrndne` and `f32-f16-vcvt` both prove their unchanged
  `completeValueEquivalenceClaim` and publish `verified(value)`. Their protected
  closure hashes are unchanged across proof checking. Their proof sources contain
  no `sorry`, `admit`, `unsafe`, custom `axiom`, or forbidden-axiom escape.
  `f32-vrndne` no longer has a counterexample artifact.
- The nine floating counterexamples are bound to the corresponding complete value
  claims. The `s8-vclamp` counterexample is correctly bound to
  `neonPhaseFunctionsEqualClaim`. Each counterexample JSON digest, Lean-file hash,
  result binding, concrete inputs, and unequal outputs agree.
- `ProgramReviewPlan.json` reports exactly 2 `verified(value)`, 10
  `counterexample`, and 7 `external-condition-missing` outcomes.
  `ProgramReviewChecks.json` reports 19/19 passed. All 19 published program reviews
  bind the current plan, checks, subject, policy, and reviewer-report hashes.
- `IntrinsicAudit.json`, `IntrinsicReviewPlan.json`, and
  `IntrinsicReviewChecks.json` report 189 registry variants, 180 used variants,
  12 families, and 180/180 passed subjects. All 180 final intrinsic reviews are
  unique and bind the current audit subject, policy, final reviewer report, family
  checks, Python evidence, and Lean evidence. No stale execution-evidence binding
  remains.
- The post-publication focused Python command was independently rerun and passed
  all 172 tests. The focused Lean build was independently rerun and completed all
  7 jobs, with all 30 FP32 evaluations printing `true`. The recorded full Lean
  build completed 46 jobs successfully.
- The final full Python run reported 422 passed, 23 skipped, and one failure in the
  framework-unchanged snapshot because a notes file was synchronized while the
  test was running. After notes editing stopped, that exact test passed in an
  isolated rerun. This was a concurrent workspace-snapshot disturbance, not a
  semantic, proof, publisher, or artifact failure.

## Inference and claim boundary

The evidence supports the published Lean pure-value-model results under their
explicit architecture-state conditions. It does not by itself establish a full C
abstract-machine theorem, FP exception-state equivalence, or unconditional
machine-code/ISA refinement theorem.

Verdict: GO (180/180)

Program outcomes: GO (19/19)

Verdict: GO (19/19)
