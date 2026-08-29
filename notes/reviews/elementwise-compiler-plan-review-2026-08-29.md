# Elementwise Compiler Plan Review

Review date: 2026-08-29 (Asia/Seoul)

Reviewer task: `/root/elementwise_plan_review`, separate Codex reviewer agent using
`gpt-5.4` with `xhigh` reasoning.

## Scope

The reviewer inspected the branch-local state, decision ledger, plan,
architecture, S8 VMax Lean prototype, current Python frontend/emitter, and current
dashboard/proof-policy implementation. It was asked to look for circularity,
tautological specifications, hidden case-specific authorities, incomplete family
classification, assumption/contract mistakes, provenance gaps, and an
unexecutable milestone order.

## Round 1

Initial verdict: **GO WITH REQUIRED REVISIONS**.

The core proof shape was judged implementable because the checked prototype keeps
`fNeon`/`fRvv` separate, freezes proof-free propositions, and composes reusable
loop-to-map theorems. Five implementation blockers remained:

1. the active backend/dashboard path still used named profiles, catalogs, emitter
   branches, `supported_cases`, and hardcoded proof targets;
2. the planned manifest/models/spec/proof-task/result boundary did not exist;
3. assertions were compared against handwritten expected strings rather than
   translated into typed assumptions;
4. proof/check status lacked precise terminal failure and counterexample states;
5. the dashboard was not yet a capability dependency graph.

The reviewer allowed implementation to begin only with the new capability/schema
path, never by adding a sixth named case.

## Round 2: Adversarial Follow-Up

The second round challenged gaps not explicit in the first response. The reviewer
identified five required architecture corrections:

1. **Logical element layout/view is first-class.** `f32-vcmul` is elementwise only
   after planar real/imag streams form one logical complex value. Intrinsic arity
   and schedule taxonomy alone do not cover all 20 pairs.
2. **Assumption domains stay separate.** Direct paired claims require complete
   `A_neon`, `A_rvv`, layout legality, schedule legality, and intrinsic legality.
   Source assert extraction is an audited assumption policy, not general C runtime
   assert/NDEBUG semantics. External contracts are separate evidence.
3. **Proof-agent isolation wording must be honest.** Phase one can accept a
   before/after hash-identical protected closure with one designated proof artifact,
   but cannot claim repository-local filesystem isolation.
4. **Artifacts need canonical parent hashes.** Manifest, Models, Spec, ProofTask,
   Proof, and Result must form a verified content-addressed chain.
5. **Use a thin vertical slice before broad dashboard migration.** The held-out
   gate needs two positives, randomized identities for the second, semantic and
   structural negatives, clean temporary execution, deterministic regeneration,
   and zero framework modifications.

## Changes Made

The branch incorporated the review as decisions EC-012 through EC-016 and revised:

- `notes/elementwise-compiler/ARCHITECTURE.md`;
- `notes/memory/PROJECT_STATE.md`;
- `notes/memory/DECISIONS.md`;
- `notes/memory/PLAN.md`;
- `notes/memory/DISCUSSION_LOG.md`.

The active order is now:

```text
M1a minimal schemas and hash closure
M1b thin generic fixed-no-tail generation
M1c proof task/result integrity
M2  honest held-out gate
M3  dashboard reads real artifacts
M4+ tail, multi-phase, intrinsic/FP/layout expansion
```

## Round 3: Convergence

Final verdict: **GO**.

The reviewer confirmed that all must-fix-before-first-code items were incorporated
and that no remaining documentation defect blocks M1a. It suggested five minor
consistency edits: include layout/view in the opening product definition and CLI
step, align the immediate objective with the three-fixture gate, split layout and
schedule legality notation, and describe the persisted reviewer evidence
precisely. All five were applied.

## Claim Matrix

| Evidence reached | Allowed claim | Claims still disallowed |
|---|---|---|
| Generated models/spec + Lean proof | equality of the generated logical value models | intrinsic, C, ISA, binary correctness |
| Above + reviewed intrinsic adequacy | modeled calls match reviewed intrinsic value semantics | complete C/ISA/binary correctness |
| Above + byte-memory/layout/C bridge | paired C functions have the stated observation under explicit conditions | machine-code correctness |
| Above + legal ISA schedule/state bridge | modeled legal Neon/RVV executions agree | compiler/binary correctness |
| Above + compiler bridge | compiled artifacts implement the proved C semantics | claims outside the recorded build/toolchain |

## Blocking Work Before the Held-Out Gate

1. implement canonical capability/assumption/manifest/result schema and hash
   closure;
2. remove path/name/profile fallback from the generic acceptance path;
3. bind every selected family instance to the complete parsed control/effect
   inventory;
4. generate independent Models and frozen Spec from manifests;
5. implement proof task/result terminal states and integrity checks;
6. run the two-positive/one-negative clean anti-special-casing test;
7. make the dashboard consume the resulting graph instead of file presence or
   case tables.

## Deferrable Work

- grouped/planar views such as complex `f32-vcmul`;
- Float32/Float16 semantics;
- full C byte-memory, alias, frame, and physical overread legality;
- legal RVV `vsetvl` and other architecture-state correspondence;
- actual proof-process filesystem isolation;
- compiler and machine-code correctness.

These deferrals must remain visible dashboard layers and cannot be inferred from a
value proof.

## Post-Review Correction: Assertion Direction

A subsequent concrete audit found that the round-two recommendation to conjoin
the complete per-side assumption sets was too weak for directed translation and
wrong for control-local assertions. The accepted correction is EC-017: use the
Neon entry contract as the source-call domain, prove it implies the RVV entry
contract, and prove nested assertions at their actual program points. This keeps
the useful review finding--shared-text intersection is unsound--without hiding a
stronger target precondition inside the theorem domain.

The user subsequently clarified that phase one compares two supplied programs only
where both entry contracts hold, rather than claiming RVV accepts every Neon-valid
call. EC-018 therefore makes common-domain equality the default and retains EC-017
as a separately labeled stronger replacement theorem. Local-assert handling is
unchanged: nested assertions remain program-point obligations.

A final scope clarification narrowed this further: the initial nineteen-program
slice accepts only pairs whose normalized entry contracts are equal (EC-019). It
does not implement implication or replacement reporting. The complete local-assert
audit is recorded separately in `notes/elementwise-compiler/ASSERT_AUDIT.md`.
