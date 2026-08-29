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
