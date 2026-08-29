# Elementwise Compiler Discussion Log

Append-only. Dates use Asia/Seoul.

## 2026-08-29 — Branch reset around the reusable compiler goal

**Question:** Does the existing five-case backend meet the intended automation
goal, and what must be stable before building the new branch?

**Conclusion:** it does not meet the goal because frontend profiles, intrinsic
catalog subsets, model profiles, emitter branches, and proof targets remain
program-specific. Preserve their reusable parsers, typed descriptors, Lean
intrinsic semantics, schedule theorems, dashboard implementation, proof policy, and
tests, but replace the case-scoped authorities.

The branch is `feat/elementwise-compiler`, based on `1707e5e`. Its first prototype
commit `986acd4` validates the desired S8 VMax proof shape and generated/agent file
separation, but manually stages the new loop and specification. The active
acceptance test is to reproduce that result with zero framework source changes.

**Evidence:** current source inspection, the 40/36-pair structural audit, dashboard
snapshot, current global intrinsic index, and successful Lean build of
`SALT.Example.S8VMaxV2.Audit`.

**Unresolved:** implement capability/result schemas, generic typed assertion and
program extraction, fixed-no-tail emission, proof orchestration, and dashboard
dependency closure before migrating fixed-tail and multi-phase cases.

## 2026-08-29 — Memory and planning audit

**Question:** Is the memory/planning system ready to drive the whole new branch?

**Conclusion:** no. The latest discussion existed only in an outer untracked notes
tree; the new branch had no memory directory. The outer current-state file had
grown to 396 lines and the active plan mixed current work with a long historical
checklist. Create a concise branch-local system with strict file responsibilities,
an append-only decision ledger, milestone exit gates, and a stable architecture
document. Let generated manifests/dashboard own live coverage counts to avoid
drift between prose and code.

**Evidence:** filesystem and line-count audit on `feat/elementwise-compiler`.

**Unresolved:** enforce the update protocol during each substantive implementation
turn and keep `PROJECT_STATE.md` below its size target.

## 2026-08-29 — Independent architecture review, rounds 1 and 2

**Question:** Is the plan safe to implement, and what hidden gaps remain?

**Reviewer verdict:** `GO WITH REQUIRED REVISIONS`. The checked S8 proof shape and
generic schedule theorem justify implementation, but the first code commit should
wait for one design-correction pass.

Round 1 confirmed five blocking implementation gaps: old case-scoped authorities,
an unrealized generated-artifact stack, handwritten assertion comparison, missing
terminal failure/counterexample states, and a dashboard still driven by
`supported_cases`/hardcoded proof targets.

Round 2 identified additional gaps not explicit in the first plan:

- operator arity plus schedule is insufficient for planar complex `f32-vcmul`; a
  reusable logical element layout/view capability is separate;
- direct paired claims require complete separate Neon/RVV assumption sets plus
  family/intrinsic legality; source assert extraction is not general runtime-assert
  semantics;
- “agent can write only Proof” must be stated as before/after protected-closure
  integrity checking unless a real sandbox exists;
- manifest, models, spec, proof task, proof, and result need canonical parent-hash
  edges;
- build a thin fixed-no-tail end-to-end slice before broad dashboard migration;
- the held-out gate needs two positives, randomized names/paths for the second,
  semantic/structural negatives, clean temporary execution, deterministic rerun,
  and zero tracked framework changes.

**Resolution:** accepted these as EC-012 through EC-016 and revised architecture
and milestones before implementation. The new order is minimal schemas, thin
fixed-no-tail generation, proof/result integrity, honest held-out gate, then
dashboard migration.

**Convergence:** after reading the revised documents, the same reviewer returned
`GO`. It confirmed every must-fix-before-code item was incorporated and found no
remaining document defect severe enough to block M1a. Five nonblocking wording
amendments were applied before committing the review baseline.

**Unresolved:** begin M1a and enforce its schema/hash exit gates before implementing
the generic frontend.

## 2026-08-29 — Concrete assertion audit and contract correction

**Question:** Is taking all Neon and RVV assertions as a conjunction correct, and
what exactly should the held-out gate test?

**Conclusion:** no. Shared assertions are insufficient, but conjoining every
assertion also hides a target that is stricter than the source. Directed
translation must use the Neon entry contract as its domain and prove it implies
the RVV entry contract. Assertions nested under a branch or loop are local proof
obligations using the current symbolic state and reach condition. This supersedes
the domain formula in EC-013 through EC-017.

The first acceptance gate is a compiler/framework generalization test, not another
semantic axiom and not a per-program proof substitute. At least one unseen
same-family positive and one semantic/structural negative are necessary evidence
for the claimed zero-framework-edit automation. Name/path randomization is a cheap
regression check against the current case-scoped architecture, not part of the
trusted computing base.

**Evidence:** `examples/s8-vmax-to-lean` has a Neon-only `batch % 16 == 0` entry
assertion; dropping it admits inputs for which the fixed-no-tail Neon loop and RVV
loop differ. `kernels/source/f32-f16-vcvt.c` has bounds on the reduced `batch`
inside its tail branch; treating those as entry assumptions incorrectly excludes
larger valid inputs. A target-only stronger divisibility assertion demonstrates
why taking the union/intersection of both sides can hide a translation-domain gap.

**Unresolved:** implement the supported assertion-expression grammar, implication
checking, and local path-obligation generation in M1a/M1b.

## 2026-08-29 — Common-domain claim and corpus layout/assert counts

**Question:** Is the intended theorem equality only where both supplied programs
are valid, how common are grouped elements, and what do inline assertions mean?

**Conclusion:** the user confirmed the phase-one goal is paired-program equivalence
on the intersection of entry contracts. Adopt that as the default while reporting
contract implications separately; retain source-domain refinement as an optional
stronger replacement claim. Local assertions are proved at their program point and
never intersected into the entry domain.

Of twenty audited elementwise pairs, nineteen use ordinary same-index scalar
streams, one (`f32-vcmul`) uses planar complex grouping, and none uses an
overlapping adjacent-index window. Five elementwise Neon files have eleven
tail-local remainder assertions; all twenty pairs' entry assertions match, and the
corresponding RVV files have no local assertions.

**Evidence:** direct classification of all twenty source/target C pairs at commit
`3dc22b2`; the tail assertions in `f32-f16-vcvt`, `qs8-f32-vcvt`, `qs8-vcvt`,
`qs8-vlrelu`, and `qu8-f32-vcvt`; the planar pointer derivations in `f32-vcmul`.

**Unresolved:** expose common-domain, Neon-implies-RVV, and RVV-implies-Neon as
separate generated/result fields and dashboard states.

## 2026-08-29 — Equal-entry phase-one rule and full local-assert audit

**Question:** Can phase one require normal pairs with equal entry assertions and
simply ignore assertions inside the function?

**Conclusion:** require normalized entry-contract equality and drop contract
implication/replacement reporting from phase one. The held-out positive fixtures
must satisfy the same rule. Do not ignore arbitrary local assertions. The fixed-tail
recognizer can automatically discharge the eleven remainder assertions in the five
affected phase-one programs because they follow immediately from the loop exit and
nonzero tail condition; every other local assertion fails recognition.

Across the full paired corpus, fourteen program names contain local assertions.
Twelve contain only assignment/control-derived invariants. Two non-elementwise
programs, `f32-dwconv-minmax` and `f32-igemm-minmax`, check caller-supplied pointer
table entries and therefore contain real data-dependent constraints.

**Evidence:** one-by-one audit recorded in
`notes/elementwise-compiler/ASSERT_AUDIT.md`.

**Unresolved:** the existing synthetic S8 VMax fixture has mismatched entry
assertions and must be normalized or replaced before it can serve as a positive
phase-one acceptance fixture.
