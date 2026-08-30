# Clean PR Reproducibility Audit

Audit date: 2026-08-31 (Asia/Seoul)

Audited committed tree: `feat/elementwise-compiler@78ee4ac`

Purpose: define a reviewable PR that retains all current scalar-elementwise
results without committing redundant working output.

This is a working cleanup audit, not a runtime dependency and not automatically a
document that must ship in the final PR.

## Verdict

**Independent reviewer verdict:** `NO-GO as written; CONDITIONAL GO with required
changes`.

**Confirmed:** the current 487 per-program capability files cannot simply be
ignored. `ArtifactIndex.json`, the proof protected closure, the dashboard graph,
and the program-review verifier all resolve and hash those local paths. Removing
them would invalidate every current proof/result/review chain.

**Proposal:** first replace program-local capability copies with references to one
global, fail-closed capability authority; then regenerate and independently
republish all nineteen scalar outcome chains.

## Current Diff Composition

The direct `origin/main..feat/elementwise-compiler` diff contains 1,137 files:

| Category | Files | Disposition |
|---|---:|---|
| `verification/elementwise-compiler/programs/` | 657 | Retain curated chains; remove duplicate capability occurrences after registry refactor |
| Intrinsic review records | 180 | Retain or normalize into one canonical audited collection |
| Program review records | 19 | Retain and republish after hash changes |
| Corpus/audit indexes, schemas, history | 30 | Keep live compact authorities; move history/raw traces out |
| Workflow implementation | 76 | Dependency-prune, then retain compiler/checker core |
| Lean tree | 44 | Retain trusted/replay closure; remove legacy generated/examples where unused |
| Tests | 64 | Retain focused generation, replay, mutation, and freshness tests |
| Notes | 53 | Retain only operational, policy, and final evidence documents |
| Other configuration/examples/output | 14 | Select by clean-clone reproduction need |

The 657 program files split into:

- 487 program-local capability occurrences;
- 169 files in the nineteen scalar program chains;
- one `f32-vcmul/ProgramStatus.json` explaining the deferred grouped layout.

The 487 occurrences contain 185 unique capability blobs:

- 180 exact intrinsic capabilities used by the nineteen scalar programs;
- five layout/schedule capabilities;
- 302 duplicate occurrences across program directories.

## Target Repository Shape

```text
src/workflow/verification/
  elementwise_compiler/       compiler, recognition, emission, proof/result gates
  lean_backend/               only the parser/index/emitter dependency closure
  intrinsic_dashboard/        optional UI after core verification is decoupled

src/verification_bw/lean/SALT/
  Basic.lean
  Intrinsics/{FP32,Neon,RVV}.lean
  Kernel/{Schedule,ElementwiseTwoPhase,ElementwiseFamily,ElementwiseLayout}.lean
  Proof/                      only reusable helpers actually imported by checked proofs

tests/
  fixtures/elementwise_compiler/
  verification/elementwise_compiler/
  verification/lean_backend/  only dependency and mutation regressions

verification/elementwise-compiler/
  CapabilityRegistry.json     intrinsic + layout + schedule authority
  IntrinsicReviews.*          canonical reviewed intrinsic collection
  CorpusReport.json
  ProgramReviewPlan.json
  ProgramReviewChecks.json
  program-reviews/            19 current outcome approvals
  results/                    19 curated scalar chains + f32-vcmul deferred status

build/verification/elementwise-compiler/
  ...complete regenerated working tree, ignored by Git...
```

## Curated Result Projection

Keep all nineteen scalar outcomes, not only one or two examples.

Every scalar program keeps:

- `ProgramManifest.json`;
- `Models.lean`;
- `Spec.lean`;
- `ExternalCondition.json`;
- `CrossPhaseAudit.json`;
- `ArtifactIndex.json`;
- `ProgramStatus.json`.

Terminal additions are:

- two verified programs: `ProofTask.json`, `Proof.lean`, `Result.json`;
- ten refuted programs: `Counterexample.lean`, `Counterexample.json`,
  `Result.json`;
- seven externally blocked programs: no ProofTask, Proof, Counterexample, or
  Result, by design.

This is 169 files for the nineteen scalar programs, or 170 when retaining the
single deferred `f32-vcmul` status.

## Memory and Documentation Selection

### Exclude from the PR

**Confirmed:** none of the five `notes/memory/*` files is referenced by source,
tests, or verification artifacts. They are local project-management state and can
be excluded from the clean PR.

Also exclude or move to CI/release storage:

- historical intrinsic reviews;
- intermediate design-review rounds;
- old repair plans after their final conclusions are documented;
- raw differential JSON/stdout/probe traces;
- spreadsheet and inspect output;
- old `SALT/Generated/*` and unused Lean examples;
- `.lake`, `.DS_Store`, and all local build output.

### Machine-required documents

The current review records hash-bind these files, so they cannot be removed
without republishing the reviews:

- `notes/policies/elementwise-intrinsic-review-v2.md`;
- `notes/policies/elementwise-program-review-v1.md`;
- `notes/reviews/intrinsic-semantic-audit-final-2026-08-30.md`;
- `notes/reviews/evidence/elementwise-m6-lean-build.txt`;
- `notes/reviews/evidence/elementwise-m6-python-tests.txt`.

### Recommended user-facing documents

Retain a small explanatory set:

- `src/workflow/verification/elementwise_compiler/README.md`;
- `notes/elementwise-compiler/ARCHITECTURE.md`;
- `notes/elementwise-compiler/ASSERT_AUDIT.md`;
- `notes/elementwise-compiler/EXTERNAL_INPUT_AUDIT.md`;
- one final semantic/outcome audit report;
- optionally the original-C `f32-vmax` reproducer as a concrete counterexample.

The current 53 note files can therefore plausibly fall to roughly 12--16 retained
documentation/evidence files, subject to regenerated review bindings.

## Required Implementation Changes

1. Create a global capability authority covering the 180 used intrinsics and five
   layout/schedule capabilities.
2. Make each program bind `capability_id`, kind, version, and SHA rather than a
   local path.
3. Update compiler publication, proof protected-closure verification, dashboard
   loading, and program-review verification together.
4. Resolve only the program's referenced registry entries. Do not bind every
   program to the hash of all unused registry entries.
5. Fail closed on missing, duplicate, wrong-kind, dangling, or digest-mismatched
   capability references.
6. Add a deterministic `publish-curated` command that projects exactly the
   allowed 169/170 files from the ignored build tree and removes stale files.
7. Parameterize the corpus root; current review/dashboard code partly assumes
   `verification/elementwise-compiler`.
8. If raw audit traces move to CI, update the ledger/review schema to bind a
   durable artifact identifier and SHA. Deleting local hash parents is not safe.
9. Move core stack verification out of the dashboard package before treating the
   dashboard as optional.
10. Lock Python/libclang/Clang and define a stable Lean release identity or a
    reproducible runner/container.

## Realistic File Counts

| Delivery shape | Estimated files | Assessment |
|---|---:|---|
| Code only, without all nineteen result chains | 80--150 | Too small for the requested evidence-preserving PR |
| Current records, after only removing 487 local copies | about 650 | Broken unless the capability/hash representation changes |
| Global capability registry, but 180 review files remain separate | 470--580 | Safest low-refactor target |
| Global capability registry plus normalized review collection | 290--380 | Best reviewable target, but needs more schema/loader work |

**Recommendation:** target 290--380 files only if review-record normalization is
implemented and independently audited. Otherwise accept a still-reviewable
470--580-file PR rather than weakening the evidence chain.

## Reproducibility Acceptance Gates

The cleanup is complete only when:

1. two independent clean clones/worktrees start from the intended PR base;
2. the XNNPACK submodule and toolchain are pinned and initialized;
3. one documented command regenerates the complete build tree;
4. both runs produce identical file manifests and SHA-256 values;
5. `publish-curated` matches the checked-in 169/170-file projection byte for byte;
6. corpus outcomes are exactly two verified, ten counterexamples, seven external
   blockers, plus one grouped-layout deferred status;
7. all nineteen Models/Specs elaborate;
8. both saved proofs replay against their frozen tasks with no proof escape;
9. all ten counterexample Lean witnesses replay and bind matching JSON/Results;
10. the seven blocked cases produce no ProofTask, Proof, or Result;
11. all 180 used intrinsic and five layout/schedule capabilities resolve uniquely
    and hash-match;
12. missing/dangling/mutated capability and parent tests fail closed;
13. `ProgramReviewChecks` reports 19/19 passed and the intrinsic closure reports
    180 used/reviewed/Lean-checked;
14. focused Python tests, Lean build, generation freshness, and diff checks pass;
15. the final tree contains no `.lake`, `.DS_Store`, build directory, spreadsheet,
    inspect output, or raw trace; and
16. the final worktree is clean.

Until these gates pass on the reorganized tree, the existing committed audit is
evidence for the current layout only; it is not evidence that the proposed clean
PR remains reproducible.
