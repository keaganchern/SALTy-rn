# Elementwise Compiler M8 Final Audit

Audit date: 2026-08-30 (Asia/Seoul)

Branch: `feat/elementwise-compiler`

Implementation parent: `92aad8c` (`feat: close nineteen program outcome reviews`)

## Delivered scope

**Confirmed.** Structural discovery reports twenty elementwise C pairs. Nineteen
use the supported scalar-lane layout and pass one profile-free compiler path; the
grouped planar-complex `f32-vcmul` is explicitly deferred.

**Confirmed.** The nineteen scalar outcomes are:

- 8 `verified(value)`: `f32-f16-vcvt`, `f32-vadd`, `f32-vdiv`, `f32-vlrelu`,
  `f32-vmul`, `f32-vmulc`, `f32-vsqrt`, and `f32-vsub`;
- 4 `counterexample`: whole-program witnesses for `f32-vrndne`, `f32-vmax`, and
  `f32-vmin`, plus the `s8-vclamp` cross-phase witness;
- 7 `external-condition-missing`: the remaining QS8/QU8 programs.

Only `verified(value)` is an equivalence theorem. Counterexample and missing-input
reviews approve the integrity and honesty of those recorded outcomes.

**Confirmed.** All 180 exact intrinsic variants used by these programs are
independently reviewed and Lean-checked. The full configured registry has 189
exact variants; the other nine are unused by this scalar closure.

## Integrity gates

**Confirmed.** `ProgramReviewPlan.json` binds each C source pair, Manifest,
Models, proof-free Spec, external condition, cross-phase audit, witness or proof
branch, Result, checker, and toolchain. `ProgramReviewChecks.json` recomputes the
live plan, enforces the 180/180 intrinsic closure, and validates each outcome's
exclusive artifact shape.

**Confirmed.** Publisher and loader both reject stale live parents, even when the
stored Plan/Checks are internally self-consistent. Program review loading occurs
only after the reusable IntrinsicAudit and IntrinsicReviewPlan parents validate.
The dashboard strictly loads nineteen current review records and reports 8/4/7.

**Confirmed.** Generated Manifest identity now hashes the reachable local
generation-code closure. Proof, whole-program diagnostic search, program review,
corpus orchestration, and dashboard changes no longer invalidate all Manifests;
their own checker hashes continue to invalidate their descendants.

## Verification evidence

**Confirmed.** The complete elementwise compiler and dashboard test directories
pass `247` tests. The final review/audit/dashboard convergence selection passes
`29` tests.

**Confirmed.** The first complete-repository run produced `442 passed / 2 failed`.
Both failures showed that copied-corpus intrinsic mutations were masked by a later
missing program-review policy. After moving reusable intrinsic-parent validation
before program-review loading and republishing reviews under the new graph checker,
the same complete suite passed:

```text
444 passed in 437.23s (0:07:17)
```

The final output is stored in
`notes/reviews/evidence/elementwise-m8-full-tests.txt`. Legacy tests rewrote tracked
Lean `.lake` caches; those cache changes and untracked build products were removed
before the final commit.

**Confirmed.** The independent convergence report records
`Verdict: GO (19/19)` and reproduces real CLI publication, strict loading, current
checker bindings, named theorem/axiom audits, and website review counts. See
`notes/reviews/elementwise-m7-program-outcome-convergence-2026-08-29.md`.

## Claim boundary and remaining work

**Confirmed.** These results establish only equality or disagreement of the
generated Lean value models relative to the reviewed Lean intrinsic definitions.
The dashboard continues to mark C and ISA correspondence `not-established`.

**Proposal.** Subsequent work should be separate milestones: establish the seven
external caller conditions where upstream evidence supports them; resolve the
intended FP NaN semantics behind the three whole-program witnesses; add a reusable
grouped planar-complex layout for `f32-vcmul`; and later prove C memory/alias/
overread, ISA, and compiled-binary correspondence layers.
