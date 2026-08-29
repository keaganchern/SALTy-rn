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
