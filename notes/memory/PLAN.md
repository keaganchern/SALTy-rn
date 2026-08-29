# Elementwise Compiler Active Plan

Last updated: 2026-08-30 (Asia/Seoul)

## Active Milestone

**Status: completed.** The shared compiler generates Manifest/Models/proof-free
Spec for all nineteen scalar-layout programs. Widths, tails, multi-phase
schedules, external audits, checked counterexamples, 180/180 used exact intrinsic
reviews, eight frozen Lean proofs, and nineteen independent outcome reviews are
published. The final outcomes are 8 `verified(value)`, 4 `counterexample`, and 7
`external-condition-missing`. The grouped `f32-vcmul` and higher C/ISA claim
layers remain explicit future work rather than hidden acceptance gaps.

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

A false generated claim follows `Models/Spec -> Counterexample.lean/json ->
Result.json` instead of creating a ProofTask. A missing external condition stops
before either branch. `ProgramReviewPlan/Checks` then bind each exact terminal
stack and an independent report publishes one `program-reviews/<id>.json` record.

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

**Status:** All nineteen scalar-layout programs generate typed artifacts through
the shared compiler. Seven quantized programs remain blocked by external caller
conditions and one has a checked counterexample. Exact intrinsic review, program
proof/result generation, and program review remain active. The grouped complex
layout for `f32-vcmul` stays deferred outside the nineteen-program target.

## Immediate Work Queue

1. **Completed and independently reviewed:** mandatory content-addressed external input
   audits, explicit missing states, generic cross-phase audits, and checked
   counterexample rejection;
2. **Completed and independently reviewed:** `/api/elementwise` uses only the
   verified artifact closure; a checked-in held-out VMax reaches `proof-ready`
   without dashboard configuration, and the UI exposes conditions, phase audit,
   witnesses, and M/E/D/S/A/C/T/R;
3. **Completed and independently reviewed:** all nineteen scalar-layout programs
   generate Manifest/Models/Spec through the shared compiler; exact review identity
   and schema-v3 dashboard accounting distinguish 178/186 spellings, 189 registry
   variants, and 180 variants used by the current nineteen-program closure;
4. **Completed and independently reviewed:** 180 used exact variants are partitioned
   into twelve semantic families, bound to official exact prototypes and explicit
   architecture conditions, machine-checked, and published as separate schema-v2
   records. Reviewer verdict: `GO (180/180)`;
5. **Active:** generate proof tasks for the eleven condition-free programs,
   delegate only `Proof.lean`, and publish an honest verified/failure/
   counterexample outcome for every scalar program;
6. independently review all nineteen program outcomes, including the seven
   external-condition blockers and the existing S8 clamp counterexample;
7. rerun the corpus and require the checked-in report/dashboard to change only
   through the artifact graph;
8. keep grouped `f32-vcmul` deferred until a reviewed complex layout/view exists;
9. use the new `counterexample` terminal state to explain false
   cross-phase/equivalence obligations;
10. for `s8-vclamp`, preserve the false direct claim and candidate signed
   `min <= max`, but keep it unresolved until an actual caller/initializer
   guarantee is established; the pinned unary clamp path does not call the
   previously cited output-range validator.
11. keep all eight audited quantized-parameter programs in
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
4. **Intrinsic batch 1 — completed and independently reviewed:** nine shared F32
   structural/schedule variants, mechanically rendered facade, exact descriptor
   and implementation bindings, pinned primary evidence, Lean/negative checks,
   and generated dashboard registry. Reviewer verdict: `GO` after the lane-store
   immediate bug was fixed without narrowing the legal lane set.
5. **Shared scalar compiler and exact audit identity — completed and independently
   reviewed:** all nineteen scalar programs generate typed artifacts; FP32 value
   definitions, scalar broadcast, facade-width preservation, safe source
   conditionals, and remaining descriptors are present. Exact IDs and dashboard
   rows distinguish all 189 registry variants and the 180 used by the current
   nineteen-program closure. Reviewer verdict changed from `NO-GO` to `GO` after
   the identity/dashboard correction.
6. **Exact intrinsic audit and publication — completed and independently reviewed:**
   official exact Arm/RVV prototypes, transitive implementation hashes, explicit
   FP state scope, twelve review families, 180 machine-check packs, schema-v2
   records, and fail-closed dashboard parents. Reviewer verdict: `GO (180/180)`.
7. **Program proof and outcome review — completed and independently reviewed:**
   all nineteen scalar-layout outcomes are generated without program-specific
   framework edits; eight prove, four have named checked witnesses, and seven
   remain blocked without fabricated assumptions. Reviewer verdict: `GO (19/19)`.
8. **Final audit — completed:** randomized held-out programs, deterministic
   regeneration, stale-parent/checker mutations, full 444-test regression,
   dashboard snapshot with 19 reviews, cache cleanup, and memory reconciliation.

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

**Status:** Completed for the nineteen scalar-layout programs.

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

**Status:** Completed on 2026-08-30 (Asia/Seoul).

Run held-out width/tail/condition variants, full repository tests, deterministic
regeneration, stale-artifact mutations, and a final independent corpus review.
Report any program that cannot be proved rather than adding an assumption in its
agent proof.

Final evidence: 247 elementwise compiler/dashboard tests, 29 convergence tests,
and 444 complete repository tests pass. The independent program convergence report
binds the final 19-review publication. See
`notes/reviews/elementwise-m8-final-audit-2026-08-30.md`.

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

- make repeated `proof check` byte-idempotent, or separate the mutable result edge
  from the protected pre-proof closure so a recheck does not stale published reviews;
- add a generic checked producer-contract bridge: first close the two direct-copy
  dequantization initializers from tensor validation, then translate initializer
  `assert`s separately from caller-established guarantees for the remaining five
  quantized programs;
- replace shared host-Float32 arithmetic with architecture-conditioned Neon/RVV NaN
  semantics before treating the eight FP `verified(value)` results as exact-bit ISA
  evidence; rerun `f32-vrndne`, `f32-vmin`, and `f32-vmax` afterward;
- grouped/planar logical layouts such as `f32-vcmul`;
- full byte-memory, alias/restrict, frame, and legal overread refinement;
- real-header/compiler dependency closure;
- actual filesystem/process isolation for proof search;
- ISA-legal RVV `vsetvl`, masks, tail policy, `vxrm`, and `vxsat` correspondence;
- complete Arm machine state and compiled-binary correctness;
- reduction, permutation, window/gather, convolution, and GEMM families.
