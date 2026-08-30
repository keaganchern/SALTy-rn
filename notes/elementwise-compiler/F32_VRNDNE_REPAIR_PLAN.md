# `f32-vrndne` Arm-NaN Modeling Repair Plan

Audit target: `feat/elementwise-compiler@cc53aa51455d24ffd151404ba94bf3000e2a84c8`
on 2026-08-30 (Asia/Seoul).

## Goal

Remove the spurious `f32-vrndne` Lean counterexample under Arm value-mode
conditions `FPCR.DN=0`, `FPCR.FZ=0`, `FPCR.RMode=RN`, and `FPCR.AH=0` (or no
`FEAT_AFP`), with all six floating-point exception traps disabled. Do this
without adding a no-NaN assumption, weakening exact-bit observation, changing a
generated theorem statement, or special-casing one program in generated
`Models.lean`.

## Confirmed cause and impact

- The generated Neon and RVV dataflows match the reviewed C instruction sequences.
- Neon `vaddq_f32` and `vsubq_f32` currently delegate to the same host
  `FP32.add/sub` value functions used by the RVV wrappers.
- Host `Float32.add/sub` canonicalizes the stored signaling-NaN witness to
  `0x7FC00000`. Actual AArch64 Neon under `DN=0` quietens and preserves that
  payload as `0x7FE00001`; the RVV C explicitly reconstructs the same value.
- Review expanded the necessary shared repair from add/sub alone to add, subtract,
  multiply, divide, square root, max/min NaN selection, and ordered comparison.
  Leaving any of these on the host primitive would keep an architecture-dependent
  NaN result inside the supposedly explicit value model.
- Correcting the shared wrappers exposed nine real floating-point disagreements:
  `f32-vadd`, `f32-vdiv`, `f32-vlrelu`, `f32-vmax`, `f32-vmin`, `f32-vmul`,
  `f32-vmulc`, `f32-vsqrt`, and `f32-vsub`. The `f32-vrndne` mismatch disappeared
  and now has an all-input proof. Existing positive outcomes were recomputed rather
  than preserved by assumption.
- The current capability `implementation_sha256` covers the complete backend and
  transitive Lean import closure. A small `FP32.lean` edit intentionally changes
  the hashes of all 112 semantic subjects that import it. The 65 structural and
  three schedule subjects retain their implementation hashes, but the current
  publisher still requires one new `GO (180/180)` report and republishes the full
  batch. That is an artifact/review cost, not evidence that the semantic change
  itself is large.

## Implemented semantic change

1. In `SALT/Intrinsics/FP32.lean`, make the bit classifiers available before
   arithmetic and add explicit predicates for NaN class, infinity, zero, sign,
   and invalid add/sub/mul/div/sqrt combinations.
2. Follow the reviewed Arm operand priority: signaling NaNs before quiet NaNs,
   then operand order within each class. Quiet the selected signaling NaN while
   preserving its sign and payload. Do not guess this rule: bind the implementation
   and tests to authoritative Arm instruction/pseudocode evidence. This rule is
   stated only for `AH=0` (or absent `FEAT_AFP`).
3. Define Arm-`DN=0/AH=0` add/sub/mul/div/sqrt value wrappers. After input-NaN
   processing, explicitly return the default NaN for invalid non-NaN operations.
   Use the host binary32/RNE operation only for the remaining cases.
4. Make the RVV-oriented add/sub/mul/div/sqrt paths explicit: any NaN input,
   invalid non-NaN operation, or NaN host result is canonicalized to `0x7FC00000`.
   This removes host NaN bit patterns from the architecture contract.
5. Replace `FP32.ne` and `FP32.lt` with reducible bit-level binary32 value
   comparisons. `lt` is ordered, returns false for NaNs and both zero encodings,
   and handles sign/reversed negative ordering directly from bits. `ne` treats
   every NaN as unequal while treating `+0` and `-0` as equal. In particular,
   `FP32.ne x x = FP32.isNaN x` supplies the bridge needed by `f32-vrndne`.
6. Correct Arm max/min signaling-NaN priority and use the Arm arithmetic wrappers
   only from Neon; RVV continues to use the canonical paths.
7. Add ordinary, axiom-free bit lemmas for NaN quieting, absolute value, and the
   exponent-mask comparison. These support the two accepted all-input proofs
   without `native_decide` or a program-specific semantic shortcut.
8. Update intrinsic review metadata and the executable probe to state `AH=0` (or
   absent `FEAT_AFP`) and all six exception traps disabled. `FPSR` being outside
   the observed value claim does not itself disable traps.

The repair still does not model `DN=1`, `AH=1`, alternate rounding modes, FZ
behavior, exception flags, or trapping executions.

The original narrower comparison requirement was:

> Replace `FP32.ne` with a reducible bit-level binary32 value comparison:
   comparisons involving NaN are unequal, `+0` and `-0` are equal, equal remaining
   bit patterns are equal, and different remaining bit patterns are unequal. This
   supplies the theorem bridge between RVV `vmfne(x,x)` and `FP32.isNaN x` needed
   for the all-input `f32-vrndne` proof. This comparison is currently consumed by
   only `f32-vrndne`.

## Tests before corpus regeneration

Add focused Lean checks for:

- positive and negative signaling NaNs with payload preservation;
- one-NaN left and right operands;
- signaling-NaN priority over a quiet NaN in the other operand;
- operand priority when both NaNs have the same class;
- invalid non-NaN add/sub/mul/div/sqrt combinations returning `0x7FC00000`;
- unchanged representative finite arithmetic results;
- RVV canonical NaN results and Arm payload-preserving results across all repaired
  arithmetic operations;
- bit-level `ne` and ordered `lt` on NaNs, signed zeros, finite values, signs, and
  infinities, including `FP32.ne x x = FP32.isNaN x` as a proved lemma;
- the concrete `f32-vrndne` witness producing `0x7FE00001` on both modeled sides.

Retain and rerun the AArch64 executable probe in
`notes/demos/neon-rvv-semantic-gap-aarch64.c` as differential evidence. Lean tests
establish behavior of the definitions; the executable probe checks the reviewed
Arm machine behavior for representative cases. Neither alone establishes a full
ISA correspondence theorem.

## Regeneration and outcome gates

1. Build `SALT.Test.FP32` and the affected generated Lean modules.
2. Re-run counterexample search for every floating-point program. The old
   `f32-vrndne` witness must disappear. Any newly exposed disagreement is recorded
   as a checked counterexample rather than hidden by a contract.
3. Replace the obsolete fixture in
   `tests/verification/elementwise_compiler/test_program_counterexamples.py` that
   requires `f32-vadd` to miss. It must instead validate the newly correct checked
   NaN counterexample. Update the frozen outcome counts in
   `test_program_reviews.py` only after regeneration establishes the new split;
   do not assume that only `f32-vadd` and `f32-vsub` change.
4. Refresh the full corpus because the intrinsic implementation closure is global.
5. Regenerate the intrinsic audit, review plan, machine checks, and exact review
   records. An independent reviewer must approve the new 180/180 publication batch.
   Exactly 112 semantic implementation hashes are expected to change from the
   `FP32.lean` import closure; unchanged hashes must remain unchanged, while stale
   review records must not be copied forward.
6. Refresh program review artifacts and documentation. The stabilized split is
   `2 verified / 10 counterexample / 7 external-condition-missing`.
7. Run the focused Python intrinsic/compiler tests, complete repository regression,
   deterministic regeneration, forbidden-token scan, and exported-axiom policy.
8. Require `git diff --check`, no new `sorry`/`admit`/`unsafe`/custom axiom, and no
   theorem-header changes made merely to recover a proof.

## Reviewer gate before implementation

The preparation review returns `GO` only if it confirms:

- the fault belongs in shared intrinsic value semantics, not generated `vrndne`;
- the planned Arm NaN selection/quieting rule is accurate for the stated `DN=0`
  / `AH=0` nontrapping scope and has adequate authoritative evidence;
- invalid non-NaN infinity operations and the reducible RVV `vmfne` comparison
  bridge are included, so the task can end in an all-input proof rather than only
  a bounded counterexample miss;
- the five direct consumers and global review-hash blast radius are accounted for;
- possible new `f32-vadd`/`f32-vsub` counterexamples are accepted as honest
  outcomes rather than treated as regressions to suppress;
- the tests distinguish Lean-definition correctness from C/ISA evidence; and
- the patch remains confined to shared FP value semantics, review conditions,
  generated outcome refresh, and proof repair; there is no hash-granularity
  redesign and no full FP-state model.

A `NO-GO` verdict must name a concrete semantic, evidence, artifact, or test gap.
Implementation starts only after all blocking findings are resolved.

## Estimate

- Semantic definitions and focused Lean tests: roughly half a day.
- Affected proof/counterexample work: roughly half to one day, depending on the
  newly correct outcomes.
- Full fail-closed artifact refresh and independent re-review: the variable part;
  the current coarse implementation closure can make the complete integration
  exceed the one-day semantic fix.

The task is therefore quick at the semantic-code level, but completion means a
consistent reviewed corpus, not merely making one stored counterexample disappear.
