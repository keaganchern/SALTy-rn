# Elementwise Compiler Active Plan

Last updated: 2026-08-29 (Asia/Seoul)

## Active Milestone

The width/tail milestone is committed. The external-condition/counterexample
milestone is implemented and independently reviewed after closing three
fail-open paths. Models and Spec
preserve distinct 8/16/32-bit widths; external audits bind the pinned registration
and initializer and fail closed as `required-missing`; S8 clamp has a Lean-checked
cross-phase counterexample. No external condition is currently `resolved`. The
active milestone is retiring the legacy dashboard's parallel case
authorities before capability expansion becomes the only production status source.

## Canonical Artifact Chain

```text
IntrinsicCapability ─────┐
LayoutViewCapability ────┼─> ProgramManifest.json
ScheduleFamilyCapability ┘          │ manifest_sha256
                                    v
                                Models.lean
                                    │ models_sha256
                                    v
                                 Spec.lean
                                    │ spec_sha256
                                    v
                              ProofTask.json
                                    │ proof_task_sha256
                                    v
                                 Proof.lean
                                    │ proof_sha256
                                    v
                                Result.json
```

`ExternalCondition.json` is mandatory, separately evidenced, and
content-addressed. XNNPACK-domain runs bind registrations and initializers;
standalone runs explicitly select an unconditional claim over all modeled
parameters. It may create a contextual claim only by establishing the direct
claim's full Neon/RVV/family/intrinsic assumption domain.

`CrossPhaseAudit.json` is mandatory. It distinguishes non-multi-phase programs,
missing external domains, bounded searches with no witness, and Lean-checked
counterexamples. A bounded miss is diagnostic only; a checked counterexample
forbids proof-task creation.

## Milestone Roadmap

### M0 — Branch-Local Memory and Independent Review

**Status:** Completed.

Exit gates:

- concise branch-local state, decisions, plan, architecture, and discussion log;
- reviewer verdict and required revisions recorded;
- product scope, artifact ownership, assumption domains, and held-out gate fixed.

### M1a — Minimal Core Schemas

**Status:** Completed in implementation stage 1.

Deliver only the schemas and canonical hashing needed by the vertical slice:

- global exact `IntrinsicCapability` without `supported_cases` authority;
- scalar-lane `LayoutViewCapability`;
- fixed-no-tail and RVV-strip-mine `ScheduleFamilyCapability` identities;
- typed entry contracts, normalized cross-side equality, and derived local-tail
  assertion facts;
- canonical `ProgramManifest`, `ProofTask`, and terminal `Result` schemas;
- explicit parent hashes and stable failure-state enum.

Exit gates:

- canonical serialize/parse/round-trip and digest tests pass;
- changing any parent, assumption, capability, theorem identity, policy, or
  toolchain input changes the appropriate descendant identity;
- one exact intrinsic capability can satisfy multiple program manifests;
- no schema field names a supported program/case;
- existing five-case records can be read through a compatibility adapter, but that
  adapter cannot satisfy the held-out gate.

### M1b — Thin Generic Fixed-No-Tail Slice

**Status:** Completed in implementation stage 2, including fixed-tail reuse.

Deliver the narrowest real compiler path before broad dashboard work:

- generic explicit-entry frontend with no path-based/default-profile fallback;
- typed assertion extraction with entry-versus-local control context;
- exact global intrinsic binding;
- scalar-lane layout and fixed-no-tail/RVV schedule recognition;
- whole-function consumed-statement/effect accounting;
- generated independent block/chunk expressions, `fNeon`, and `fRvv`;
- generated complete logical Models and proof-free Spec.

Exit gates:

- removing S8-VMax-specific profile/catalog/model declarations does not prevent
  generation;
- call signature, pointer step, loop/count update, assertion, or `vl` mutations
  change the manifest or fail closed;
- unequal normalized entry contracts return `entry-contract-mismatch`;
- tail-local assertions are proved from the path condition and current remainder,
  not copied into the function-entry contract;
- derived tail facts include preserved element-size divisibility/alignment as well
  as lower and upper remainder bounds;
- any non-derived local assertion fails phase-one family recognition;
- generated family instances bind the exact parsed control/effect inventory;
- no code branch depends on kernel id, input path, basename, function name, or
  generated namespace;
- the manually staged V2 Models/Spec are no longer used by the acceptance path.

### M1c — Proof Task, Result, and Integrity Gate

**Status:** Completed in implementation stage 3.

Deliver:

- content-addressed `ProofTask.json` and exact generated proposition identity;
- agent invocation with `Proof.lean` as the designated permitted mutable artifact;
- before/after protected-closure digests;
- Lean theorem-type, forbidden-token, transitive-axiom, freshness, and mutation
  checks;
- `Result.json` with terminal states:
  `parse-unsupported`, `intrinsic-missing`, `intrinsic-ambiguous`,
  `entry-contract-mismatch`, `layout-unrecognized`, `family-unrecognized`, `generation-failed`,
  `proof-search-failed`, `counterexample`, `lean-failed`, and `verified(value)`.

Exit gates:

- deleting and regenerating the proof changes no protected parent artifact;
- modifying Models/Spec/task/policy invalidates the result;
- max-to-min makes the original claim fail or yields a checked counterexample;
- documentation says integrity/reviewer gate, not filesystem sandbox.

### M2 — Honest Held-Out Gate

**Status:** Completed in implementation stage 3.

Run in a clean temporary checkout and output root:

- positive fixture A: S8 VMax semantics with normalized equal entry contracts
  through the generic CLI;
- positive fixture B: same family/intrinsics but randomized directories,
  basenames, function identifiers, and generated module namespace;
- negative fixture: one supported side changed from max to min;
- structural negatives: pointer step, loop update, assertion, and active-`vl`
  mutations.

Exit gates:

- both positive fixtures generate deterministic artifacts after output deletion;
- both positive fixtures have equal normalized Neon/RVV entry contracts;
- `git diff --exit-code` passes for all tracked framework files;
- `git status --porcelain` shows only allowed generated/proof artifacts under the
  temporary output root, preferably zero tracked changes anywhere;
- fixture B never uses the old example directory/name/namespace;
- the generic acceptance path imports none of `supported_cases`, `PROOF_CASES`,
  `POLICY_CASES`, case-id emitter branches, or path-based frontend defaults.

### M3 — Dashboard Reads the Real Artifact Graph

**Status:** Completed for the new `/api/elementwise` path; legacy-dashboard
migration and a checked-in held-out-to-dashboard regression remain active gaps.

Deliver:

- intrinsic, layout, schedule-family, program, artifact, proof, and claim-scope
  nodes derived from capabilities/manifests/results;
- explicit missing-piece and terminal-failure display;
- automatic transition to `proof-ready` and `verified(value)`;
- stale propagation through the parent-hash graph;
- value/C/ISA layers shown separately.

Exit gates:

- both held-out fixtures appear without dashboard code/config entries;
- adding one intrinsic/layout/family capability updates every dependent program;
- file presence alone cannot satisfy spec/proof/verification state;
- `supported_cases`, hardcoded proof targets, and policy cases are no longer
  authorities on the new path.

### M4 — Fixed Tail and Binary Reuse

**Status:** Completed. Core generation landed in implementation stage 2 and the
mutation/held-out gates pass through the shared compiler path.

Deliver:

- unary and synchronized-binary fixed-tail recognition;
- generated live-prefix observation and independent tail-read values;
- structural 4/2/1 or analogous store-plan extraction;
- reuse existing schedule theorems and integer fixtures.

Exit gates:

- two integer programs with different intrinsic pipelines use the same family
  implementation without program-specific source;
- tail-store, slide, load-base, or pointer mutations fail recognition/proof;
- logical value scope stays distinct from physical overread legality.

### M5 — Compositional Multi-Phase Family

**Status:** Completed for the audited 64/8 and nested 16/8 control encodings in
implementation stages 4, 6, and the final structural-adapter cleanup.

Deliver ordered phase lists, a generic phase-composition theorem, and structural
recognition for 16/8/4/2/1 and 64/8/4/2/1 streams.

Exit gates:

- `qs8-vadd-minmax` and `s8-vclamp` select the same parameterized mechanism without
  named emitter branches;
- the separate-loop adapter contains no program id or fixed call-number table;
- `f32-f16-vcvt` is blocked only by FP/intrinsic support, not control flow.

### M6 — Coverage Expansion

**Status:** Active capability work. The reusable width/tail blocker is closed;
external conditions, counterexamples, dashboard authority, and intrinsic review
remain.

Fill missing integer intrinsic variants. Then establish reviewed FP semantics and
new layout/view capabilities, including planar complex grouping, before claiming
coverage of all 20 audited elementwise pairs.

Before treating the remaining scalar blockers as intrinsic-only, complete the
external-condition, cross-phase, and dashboard-authority gates below.

## Immediate Work Queue

1. **Completed and independently reviewed:** mandatory content-addressed external input
   audits, explicit missing states, generic cross-phase audits, and checked
   counterexample rejection;
2. **Completed and independently reviewed:** `/api/elementwise` uses only the
   verified artifact closure; a checked-in held-out VMax reaches `proof-ready`
   without dashboard configuration, and the UI exposes conditions, phase audit,
   witnesses, and M/E/D/S/A/C/T/R;
3. **Active:** add independently reviewed integer/FP intrinsic capabilities, starting from
   the dependencies shared by the largest number of the fourteen blocked scalar
   programs;
4. add parse facades as mechanical typed declarations where missing;
5. rerun `workflow.verification.elementwise_compiler.corpus` and require the
   checked-in report/dashboard to change only through the artifact graph;
6. generate proof tasks for newly unblocked programs and delegate only
   `Proof.lean`;
7. keep grouped `f32-vcmul` deferred until a reviewed complex layout/view exists;
8. use the new `counterexample` terminal state to explain false
   cross-phase/equivalence obligations;
9. for `s8-vclamp`, preserve the false direct claim and candidate signed
   `min <= max`, but keep it unresolved until an actual caller/initializer
   guarantee is established; the pinned unary clamp path does not call the
   previously cited output-range validator.
10. keep all eight audited quantized-parameter programs in
    `required-missing` until their reusable initializer/caller postconditions are
    checked; generated Models/Spec alone are not proof ready.

## Nineteen-Program Delivery and Review Plan

The delivery target is the nineteen scalar-layout pairs. `f32-vcmul` remains a
separate grouped-layout milestone.

### Stage A — Close Reusable Framework Gaps

1. **Completed:** generalize element widths, phase widths, loads, and tail stores
   together with the family theorem and generated Spec shape;
2. **Completed for the current generated multi-phase set:** require every phase to
   implement one scalar action under bound conditions, otherwise emit a concrete
   counterexample or an explicit missing-condition state;
3. **Completed as a fail-closed audit path:** bind the pinned XNNPACK registration
   and initializer in a content-addressed artifact. Establishing reusable
   postconditions that promote the eight current `required-missing` states to
   `resolved` remains capability work;
4. **Completed:** make the artifact graph the only production elementwise dashboard
   authority. Keep the legacy table only as an explicitly non-authoritative
   historical/non-elementwise view.

## Eight-Commit Execution Ledger

1. **Width/tail generalization — completed and independently reviewed:**
   8/16/32 input/output widths, float facade types, generic fixed tails, strict RVV
   byte-to-element normalization, phase-specific scalar functions, held-out
   generation, and Lean elaboration. Reviewer verdict: `GO`.
2. **External audits and counterexamples — completed and independently reviewed:**
   mandatory scoped audits, pinned/hash-bound registration and initializer
   evidence, explicit missing state, mandatory generic cross-phase audit,
   proof-gate rejection, and a real Lean-checked counterexample producer. All
   eight quantized conditions remain unresolved rather than being fabricated.
   The first review found three fail-open paths; after mandatory audit bindings,
   generic compiler integration, and terminal counterexample rejection were
   added, the convergence review returned `GO`.
3. **Single artifact/dashboard authority — completed and independently reviewed:**
   `/api/elementwise` reads only CorpusReport and the verified M/E/D/S/A/C/T/R
   closure; held-out VMax needs no dashboard config; concrete condition/phase/
   witness evidence is visible. The first review returned `NO-GO` for missing UI
   evidence; the convergence review returned `GO` after all three fields landed.
4. **Intrinsic batch 1 — active:** shared high-fanout structural, integer,
   bitwise, conversion, and simple FP pieces with
   exact typed definitions and independent review records.
5. **Intrinsic batch 2:** remaining FP and typed variants with the same review
   gates.
6. **Program batch 1:** generate, prove or explicitly fail, and independently
   review the first scalar-layout program batch.
7. **Program batch 2:** apply the same pipeline to the remaining scalar-layout
   programs without framework edits.
8. **Final audit:** randomized held-out cases, deterministic regeneration, stale
   mutation tests, full regression, corpus review, dashboard snapshot, and memory.

### Stage B — Intrinsic Puzzle Completion and Review

Add exact typed intrinsic definitions by reusable semantic family. Each intrinsic
review record must bind the definition hash, authoritative evidence hash, review
policy, reviewer identity, and any executable/Lean checks. The reviewer agent is
read-only over the reviewed definition and may only emit its review record. A
review record is advisory/hash-gated evidence; Lean and parent-hash checks remain
the mechanical acceptance gates.

The dashboard must distinguish `defined`, `Lean-checked`, and
`independently-reviewed`. Completing one intrinsic review unlocks every dependent
program without a program-specific entry.

### Stage C — Program Proof and Review

For each of the nineteen programs, regenerate the full artifact chain, delegate
only `Proof.lean`, run the frozen-goal/axiom/parent-hash checker, and then obtain an
independent program review record. That record binds the source, manifest, Models,
Spec, ProofTask, Proof, Result, toolchain, and review policy hashes. The program
reviewer checks source consumption, claim scope, conditions, and result status; it
cannot modify implementation, Spec, or proof.

The dashboard must show generated, proof-attempted, Lean-verified, and
independently-reviewed as separate states. A real counterexample remains a valid
audited outcome, but it does not satisfy the target that all nineteen translations
pass.

### Stage D — Final Corpus Audit

Run held-out width/tail/condition variants, full repository tests, deterministic
regeneration, stale-artifact mutations, and a final independent corpus review.
Report any program that cannot be proved rather than adding an assumption in its
agent proof.

## Commit Policy

Do not treat memory/documentation updates as standalone delivery commits. During
history cleanup, fold the existing planning/review commits into the implementation
milestone they explain; there is no requirement to compress all current work into
four commits.

For the next nineteen-program delivery series, target no more than roughly eight
large semantic commits covering framework-gap closure, reviewed intrinsic
families, program proof/review batches, and final integration. Fold future memory
updates into the relevant implementation commit.

## Global Acceptance Gates

1. **Zero framework edits:** held-out same-family onboarding changes no framework
   source.
2. **Independent models:** Neon and RVV dataflows/lane functions are generated
   separately from their exact descriptors.
3. **Whole-function consumption:** unsupported calls/control/effects fail closed.
4. **Control binding:** selected family instances hash-bind the parsed control and
   effect inventory they abstract.
5. **Generated frozen goal:** proof search cannot alter accepted parents.
6. **Proof safety:** no forbidden placeholder/custom axiom/unsafe proof escape.
7. **Mutation sensitivity:** semantic changes alter the model and invalidate the
   original equivalence or yield a checked counterexample.
8. **Artifact closure:** every result verifies its canonical parent-hash chain.
9. **Dashboard derivation:** readiness comes from capability/artifact closure.
10. **Scope honesty:** value results are not labeled C/ISA results.

## Deferred but Visible

- grouped/planar logical layouts such as `f32-vcmul`;
- full byte-memory, alias/restrict, frame, and legal overread refinement;
- real-header/compiler dependency closure;
- actual filesystem/process isolation for proof search;
- ISA-legal RVV `vsetvl`, masks, tail policy, `vxrm`, and `vxsat` correspondence;
- complete Arm machine state and compiled-binary correctness;
- reduction, permutation, window/gather, convolution, and GEMM families.
