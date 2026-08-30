# Independent review: FP exceptional-value repair

Audit date: 2026-08-30 (Asia/Seoul)

Blocking findings for the implementation and formal-publication candidate: none.

- **Confirmed**: Against baseline `cc53aa51455d24ffd151404ba94bf3000e2a84c8`, the used intrinsic subject set remains exactly 180; exactly 112 semantic implementation hashes changed (53 Neon, 59 RVV), with 68 unchanged and no used subject added or removed.
- **Confirmed**: `FP32.lean` now separates the conditioned Arm DN=0/AH=0/FZ=0/RNE nontrapping value path from the RISC-V RNE canonical-NaN path. Arm input-NaN selection is signaling-before-quiet and operand-order within each class; invalid non-NaN operations return the default/canonical NaN; RISC-V canonicalizes every NaN result. Bit-level `lt`, `ne`, signed-zero handling, Arm propagating max/min, and RISC-V maximumNumber/minimumNumber are internally consistent. Neon/RVV wrappers select the intended architecture-specific helpers. No C-, flag-, trap-, or unconditional ISA-level theorem is claimed.
- **Confirmed**: The audit records all six Arm FP trap enables disabled for the relevant Neon floating arithmetic/conversion/max/min/comparison subjects, retaining the required RN/FZ/DN/AH conditions; the AArch64 probe clears the same state and excludes FPSR from the value claim.
- **Confirmed**: `f32-vrndne` and `f32-f16-vcvt` each prove the frozen `completeValueEquivalenceClaim`, have `verified(value)` results with protected closure unchanged, and contain no `sorry`, `admit`, `unsafe`, custom `axiom`, or forbidden-axiom escape. The stale vrndne counterexample artifacts are deleted.
- **Confirmed**: The nine floating complete-claim counterexamples and the `s8-vclamp` phase-claim counterexample are concrete, claim-correct, hash-bound witnesses. Program planning is exactly 2 verified(value), 10 counterexample, and 7 external-condition-missing; current machine checks report 19/19 passed.
- **Confirmed**: The current intrinsic audit/plan/check artifacts report 189 registry variants, 180 used variants, 12 families, and 180/180 machine-checked subjects. The current evidence files contain `172 passed`, `Build completed successfully (46 jobs).`, and `Build completed successfully (7 jobs).`; the publisher rejects mixed pass/fail summaries.
- **Inference**: The present 180 review files still bind the immediately preceding evidence hashes. This is the expected pre-publication state forced by the publisher's GO-before-write rule, not a semantic pass. This report authorizes exactly one formal publication with normal evidence validation so those records are overwritten to bind the current evidence. Final closure remains conditional on a post-publication read-only check that all 180 review SHA bindings, registry/audit/plan/check artifacts, ten counterexamples, two proofs, and 19 program outcomes are non-stale and that the full focused suite has zero failures.

Verdict: GO (180/180)

Program outcomes: GO (19/19)

Verdict: GO (19/19)
