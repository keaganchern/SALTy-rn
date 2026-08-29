# Elementwise M2 Independent Review

Review date: 2026-08-29 (Asia/Seoul)

Scope: uncommitted external-condition, cross-phase audit, counterexample,
proof-gate, corpus, and dashboard changes following commit `339db51`.

Reviewer: independent read-only Codex reviewer `elementwise_plan_review`.

## First Verdict: NO-GO

The first review found three fail-open paths:

1. omitting `CompilerRequest.external_condition` also omitted the audit, so an
   unaudited S8 clamp stack could reach `prepare_proof_task`;
2. a bound, Lean-checked counterexample was validated but did not forbid creation
   of a proof task;
3. multi-phase counterexample checking was selected by the corpus driver rather
   than required by the generic compiler path.

No M2 commit was made after this verdict.

## Revisions

- every compilation now emits a scoped, content-addressed
  `ExternalCondition.json` and binds it through the manifest and index;
- standalone compilation selects `local-unconditional-claim`, which assumes no
  hidden caller restriction and retains all modeled parameter values;
- every compilation emits `CrossPhaseAudit.json` from `compile_pair`;
- a Lean-checked counterexample is terminal and blocks `ProofTask.json`;
- the dashboard verifies external, phase-audit, counterexample, and terminal
  result hashes, including counterexample results that correctly have no proof
  task.

## Convergence Verdict: GO

The reviewer reproduced all three repaired paths:

- standalone `s8-vclamp`: explicit local-unconditional audit, checked
  counterexample, proof-task rejection;
- registered `s8-vclamp`: registered-domain audit, checked counterexample,
  proof-task rejection;
- standalone `s8-vmax`: explicit audit, cross-phase `not-applicable`, proof task
  accepted.

Reviewer checks passed:

- 18 schema/external/corpus tests;
- 3 mandatory-binding/dashboard tests;
- direct inspection of the checked-in corpus graph, where `s8-vclamp` is a
  non-stale `counterexample` result with no proof task.

The reviewer found no remaining fail-open blocker. It noted that the status word
`not-required` must always be read together with the explicit
`local-unconditional-claim` scope; the separate scope and mandatory audits make
this a naming caution rather than a correctness blocker.
