# Elementwise M7 program outcome review — 2026-08-29

Reviewer: agent `/root/elementwise_plan_review`

## Scope and method

**Confirmed.** I reviewed the current worktree read-only against `notes/policies/elementwise-program-review-v1.md`, `verification/elementwise-compiler/ProgramReviewPlan.json`, `verification/elementwise-compiler/ProgramReviewChecks.json`, the 19 scalar-layout program directories, the intrinsic-review closure visible through the graph, and `notes/reviews/evidence/elementwise-m7-focused-tests.txt:2` (`48 passed in 275.85s`).

**Confirmed.** I did not rerun the full corpus. I used quick JSON / source inspection plus two Lean spot checks:

- `f32-vadd`: `check_proof` on a temporary copy of the program directory returned `verified(value)` with checker `cfff29d22b01cf4d0949411ea955b789b508b3e960769ac5c34bdde05019cd84` and toolchain `1ce7d3879378e751ecae7bb5fd76c57bde9e4957e69b20b4693d759eb34a8c6d`, matching the planned proof path (`verification/elementwise-compiler/programs/f32-vadd/Proof.lean:115`, `verification/elementwise-compiler/ProgramReviewPlan.json:65-80`).
- `s8-vclamp`: staged `Models.lean` + `Spec.lean` + `Counterexample.lean` elaborated successfully, but the stored counterexample checker digest `617ebac5...` does not match the current cross-phase checker digest `0cdeedf3...`.

## High-level verdict

**Confirmed.** The 19-program scalar-layout outcome split is currently recorded as 8 `verified(value)`, 4 `counterexample`, and 7 `external-condition-missing` (`verification/elementwise-compiler/ProgramReviewPlan.json:6-10`; `verification/elementwise-compiler/ProgramReviewChecks.json:6-12`).

**Confirmed.** The graph is honest about claim scope: value status is surfaced, while C and ISA remain `not-established` (`src/workflow/verification/intrinsic_dashboard/elementwise_graph.py:653-717`; spot-check output from the current graph showed `f32-vadd`, `f32-vmax`, `qs8-vcvt`, and `s8-vclamp` all keep `claim.c = claim.isa = not-established`). The graph also honestly keeps grouped-layout `f32-vcmul` outside the 19 scalar-layout review subjects and reports it as `layout-unrecognized`.

**Inference.** Most of the machinery is in the right shape for publication of program outcomes, but one counterexample path is still stale relative to its checker and one phase-counterexample witness has not been upgraded to the same named-theorem discipline as the whole-program witnesses.

## What is solid

### 1. Plan / checks / outcome inventory are current

**Confirmed.** `build_program_review_plan` and `build_program_review_checks` are the live constructors (`src/workflow/verification/elementwise_compiler/program_reviews.py:170-323`). The checked-in plan and checks match the current repository state under read-only recomputation.

**Confirmed.** `ProgramReviewChecks.json` records a full 19-subject pass set and intrinsic closure `used=180`, `reviewed=180`, `lean_checked=180` (`verification/elementwise-compiler/ProgramReviewChecks.json:6-12`).

### 2. The 8 verified(value) proofs are properly shaped

**Confirmed.** Each verified program has a theorem exactly of the frozen claim form `theorem completeValueEquivalence : completeValueEquivalenceClaim := by`:

- `f32-f16-vcvt` — `verification/elementwise-compiler/programs/f32-f16-vcvt/Proof.lean:195`
- `f32-vadd` — `verification/elementwise-compiler/programs/f32-vadd/Proof.lean:115`
- `f32-vdiv` — `verification/elementwise-compiler/programs/f32-vdiv/Proof.lean:115`
- `f32-vlrelu` — `verification/elementwise-compiler/programs/f32-vlrelu/Proof.lean:126`
- `f32-vmul` — `verification/elementwise-compiler/programs/f32-vmul/Proof.lean:115`
- `f32-vmulc` — `verification/elementwise-compiler/programs/f32-vmulc/Proof.lean:84`
- `f32-vsqrt` — `verification/elementwise-compiler/programs/f32-vsqrt/Proof.lean:81`
- `f32-vsub` — `verification/elementwise-compiler/programs/f32-vsub/Proof.lean:115`

**Confirmed.** The proof gate blocks forbidden identifiers and audits axioms via `#print axioms` (`src/workflow/verification/elementwise_compiler/proof.py:547,572-721`). The checked-in focused tests also passed (`notes/reviews/evidence/elementwise-m7-focused-tests.txt:2`).

### 3. The 3 whole-program counterexamples are honestly marked as executable witnesses

**Confirmed.** The policy now says concrete counterexamples may use Lean `native_decide`, but only as a toolchain-bound executable witness, not an axiom-free proof (`notes/policies/elementwise-program-review-v1.md:16,25-28`). That boundary is honest.

**Confirmed.** `program_counterexamples.py` now emits a named theorem `completeValueEquivalenceCounterexample : Not completeValueEquivalenceClaim`, then audits the exact theorem and restricts accepted native axioms to the theorem-local generated one (`src/workflow/verification/elementwise_compiler/program_counterexamples.py:271-274,449-509`).

**Confirmed.** The checked-in whole-program witnesses follow that shape:

- `f32-vmax` — `verification/elementwise-compiler/programs/f32-vmax/Counterexample.lean:18-21`
- `f32-vmin` — `verification/elementwise-compiler/programs/f32-vmin/Counterexample.lean:18-21`
- `f32-vrndne` — `verification/elementwise-compiler/programs/f32-vrndne/Counterexample.lean:16-19`

**Confirmed.** Their stored checker digest is `90b39905...`, which matches the current whole-program counterexample checker.

### 4. The 7 blocked programs are not smuggling assumptions

**Confirmed.** The seven `external-condition-missing` subjects are:

- `qs8-f32-vcvt`
- `qs8-vadd-minmax`
- `qs8-vcvt`
- `qs8-vlrelu`
- `qs8-vmul-minmax-fp32`
- `qu8-f32-vcvt`
- `qu8-vadd-minmax`

**Confirmed.** In the plan they carry `checker_sha256: null` and `outcome_status: external-condition-missing` (`verification/elementwise-compiler/ProgramReviewPlan.json:495-762`). A read-only directory check confirmed none of those seven directories contains `ProofTask.json`, `Proof.lean`, `Result.json`, or `Counterexample.json`.

## Blocking issues

### Blocker 1. `s8-vclamp` still uses the older anonymous phase-counterexample format

**Confirmed.** The current cross-phase generator still emits anonymous `example` terms, not a named theorem (`src/workflow/verification/elementwise_compiler/counterexamples.py:189-192`).

**Confirmed.** The checked-in `s8-vclamp` witness is still in that form:

- `verification/elementwise-compiler/programs/s8-vclamp/Counterexample.lean:8-11`

It proves a concrete disagreement between `fNeon` and `fNeonSecondary`, and it elaborates, but it is not a named theorem analogous to the new whole-program `completeValueEquivalenceCounterexample` discipline.

**Inference.** If the release standard for Phase 7 is now “all counterexample outcomes are bound through a named theorem plus checker audit,” then `s8-vclamp` has not caught up.

### Blocker 2. The current program-review closure is not fully fail-closed for the phase-counterexample checker path

**Confirmed.** `s8-vclamp` stores checker digest `617ebac5...` in both the witness and the cross-phase audit (`verification/elementwise-compiler/programs/s8-vclamp/Counterexample.json:3`, `verification/elementwise-compiler/programs/s8-vclamp/CrossPhaseAudit.json:3`).

**Confirmed.** The current cross-phase checker digest computed from `src/workflow/verification/elementwise_compiler/counterexamples.py` is `0cdeedf33b226d86d426e4e9c1a6a2170d024663befe731988cb853722e3d1b8`. The staged `s8-vclamp/Counterexample.lean` still elaborates, so this is not a Lean syntax failure; it is a stale provenance binding.

**Confirmed.** `ProgramReviewChecks` only hashes `program_reviews.py`, `proof.py`, `schema.py`, and `elementwise_graph.py` (`src/workflow/verification/elementwise_compiler/program_reviews.py:301-309`). It does not hash `counterexamples.py` or `program_counterexamples.py`.

**Confirmed.** `load_program_reviews` revalidates against recomputed plan/checks and full subject coverage (`src/workflow/verification/elementwise_compiler/program_reviews.py:499-548`), which is good, but because the current checks closure excludes the phase-counterexample checker module, this path can stay stale without the loader noticing.

**Inference.** This is a real fail-open on the phase-counterexample branch. It is enough to block a clean 19/19 approval.

## 19 scalar-layout program outcomes reviewed

**Confirmed.** I reviewed the current recorded outcome for each scalar-layout subject in `ProgramReviewPlan.json`.

| Program ID | Recorded outcome | Review note |
|---|---|---|
| `f32-f16-vcvt` | `verified(value)` | Proof theorem shape is correct. |
| `f32-vadd` | `verified(value)` | Spot-checked through `check_proof`; bindings match. |
| `f32-vdiv` | `verified(value)` | Proof theorem shape is correct. |
| `f32-vlrelu` | `verified(value)` | Proof theorem shape is correct. |
| `f32-vmul` | `verified(value)` | Proof theorem shape is correct. |
| `f32-vmulc` | `verified(value)` | Proof theorem shape is correct. |
| `f32-vsqrt` | `verified(value)` | Proof theorem shape is correct. |
| `f32-vsub` | `verified(value)` | Proof theorem shape is correct. |
| `f32-vmax` | `counterexample` | Named whole-program counterexample theorem present. |
| `f32-vmin` | `counterexample` | Named whole-program counterexample theorem present. |
| `f32-vrndne` | `counterexample` | Named whole-program counterexample theorem present. |
| `s8-vclamp` | `counterexample` | Phase disagreement witness elaborates, but checker binding is stale and witness is not yet a named theorem. |
| `qs8-f32-vcvt` | `external-condition-missing` | No proof or result artifacts; blocked honestly. |
| `qs8-vadd-minmax` | `external-condition-missing` | No proof or result artifacts; blocked honestly. |
| `qs8-vcvt` | `external-condition-missing` | No proof or result artifacts; blocked honestly. |
| `qs8-vlrelu` | `external-condition-missing` | No proof or result artifacts; blocked honestly. |
| `qs8-vmul-minmax-fp32` | `external-condition-missing` | No proof or result artifacts; blocked honestly. |
| `qu8-f32-vcvt` | `external-condition-missing` | No proof or result artifacts; blocked honestly. |
| `qu8-vadd-minmax` | `external-condition-missing` | No proof or result artifacts; blocked honestly. |

## Approval boundary

**Confirmed.** Even if the blockers above are fixed, a program review here approves only the exact recorded Lean value-model outcome for each subject. It does **not** approve C abstract-machine equivalence, intrinsic implementation adequacy beyond the already separate 180/180 intrinsic review closure, or ISA / machine-code correctness (`notes/policies/elementwise-program-review-v1.md:3-5`; current graph claim layer keeps C and ISA as `not-established`).

## Judgment on the current loader / publisher design

**Confirmed.** The publisher is strict about requiring the report, requiring all 19 program IDs in the report, and emitting one review record per subject (`src/workflow/verification/elementwise_compiler/program_reviews.py:433-496`). The loader is also strict about full parent equality and full coverage (`src/workflow/verification/elementwise_compiler/program_reviews.py:499-548`).

**Inference.** That design is close, but today it is not fully fail-closed because the checker closure used for program-review freshness omits the phase-counterexample module that already changed under `s8-vclamp`.

## Required fix before publishing 19 approvals

**Proposal.** Before publishing `program-reviews/*.json`, do both of these:

1. Regenerate `s8-vclamp` so its phase-counterexample witness and `CrossPhaseAudit.json` bind the current checker digest.
2. Extend the program-review freshness closure so checker changes in `counterexamples.py` and `program_counterexamples.py` also stale out program reviews, or otherwise revalidate stored counterexample checker digests against the live checker code during load.

Verdict: NO-GO
