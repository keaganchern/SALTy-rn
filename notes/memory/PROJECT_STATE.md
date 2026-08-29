# Elementwise Compiler Project State

Last updated: 2026-08-30 (Asia/Seoul)

## Snapshot

- Branch: `feat/elementwise-compiler`
- Audited implementation head before the final memory update: `4ae0cd5`
- Base: `1707e5e1b847fe0c4a0a17ff058928485db82cee`
- First branch commit: `986acd4` (`s8-vmax` target-architecture prototype)
- Upstream corpus baseline: `origin/main@6acdf7a522e2b97b96831f8e95b578e6edf42a83`
- Publication target: `fork/feat/elementwise-compiler`.

## Product Definition

**Confirmed:** build a restricted, reusable compiler for Neon/RVV elementwise C
pairs. Once its exact typed intrinsics, logical layout/view, and execution family
are supported, a new program must require zero new Python or Lean source code.

One command must:

1. parse both C functions and reject unconsumed or unsupported constructs;
2. bind every call to the global exact typed intrinsic library;
3. recognize the logical layout/view, execution family, and source assertions;
4. generate independent Neon/RVV implementation models;
5. generate and freeze the specification and proof task;
6. run an agent and accept the run only when the designated proof is the sole
   changed artifact inside the protected closure;
7. check the result with Lean and publish a machine-readable status;
8. update the dashboard through dependency closure, without a program-specific
   dashboard entry.

## Dashboard Motivation

**Confirmed:** the dashboard is part of the architecture. It represents a puzzle
graph:

```text
exact intrinsic variants + logical layout/view + execution-family capabilities
        -> automatically discovered program dependencies
        -> fresh Models/Spec
        -> proof ready
        -> agent proof
        -> Lean verified
```

Completing one reusable intrinsic or family capability must automatically unlock
every compatible program. A manually maintained `supported_cases` list is not an
acceptable production authority.

**Reviewer correction:** the reusable graph also needs a logical element
layout/view capability. Schedule says when coordinates are processed; layout says
how physical scalar streams form one logical element and observation. Scalar-lane
layouts cover phase one. Planar complex `f32-vcmul` is not covered until a reusable
grouped layout exists.

## Supported Claim Layers

Keep these claims visibly separate:

1. generated Lean models are equal for arbitrary logical input lengths;
2. intrinsic Lean definitions correspond to the intended Arm/RISC-V operations;
3. the complete C functions refine the logical value models under explicit memory
   and caller conditions;
4. legal ISA executions implement the modeled schedules and intrinsic semantics;
5. compiled binaries implement the C functions.

**Confirmed current scope:** existing results and the S8 prototype establish only
parts of layer 1 relative to current Lean definitions. No current program has a
complete C-function theorem.

## Execution Families

Tail shape is parsed program information and a reusable capability:

- `fixed-no-tail`: a fixed-width loop with source-derived divisibility;
- `fixed-tail`: a fixed-width loop followed by a nonempty short-tail path;
- `multi-phase`: ordered fixed-width phases followed by an optional final tail;
- `rvv-strip-mine`: positive-progress active-length chunks covering the input.

Unary programs normalize to `List.map`; binary programs to `List.zipWith`;
scalar-broadcast programs remain maps with scalar parameters. Each family theorem
is proved once and instantiated by generated program artifacts.

## Audited Corpus Facts

**Confirmed at `1707e5e`, 2026-08-29:** there are 40 source C files, 37 target
paths, and 36 nonempty pairs. Twenty nonempty pairs are elementwise. Seventeen use
the strict fixed-main-loop plus optional-tail shape; three require a compositional
multi-phase stream (`f32-f16-vcvt`, `qs8-vadd-minmax`, and `s8-vclamp`).

**Confirmed layout audit:** nineteen of the twenty elementwise pairs use ordinary
same-coordinate scalar streams. One, `f32-vcmul`, groups planar real/imaginary
streams into a logical complex element. None of the twenty uses an overlapping
`i, i+1` window; such kernels belong to a window/stencil family.

**Confirmed assertion audit:** all twenty pairs have textually equal entry
assertions. Five Neon files contain eleven tail-local remainder assertions while
their RVV partners contain no local assertion. These are program-point invariants,
not extra function-entry restrictions. Across the whole paired corpus, fourteen
program names have local assertions: twelve have only derived invariants, while
`f32-dwconv-minmax` and `f32-igemm-minmax` contain real pointer-table non-null
constraints. See `../elementwise-compiler/ASSERT_AUDIT.md`.

## Reusable Assets

Retain and generalize:

- the Clang JSON AST walker and fail-closed extraction approach;
- typed intrinsic schema, exact descriptors, and global intrinsic index;
- `SALT.Intrinsics.Neon` and `SALT.Intrinsics.RVV` value definitions;
- `SALT.Kernel.Schedule` map/zipWith and partition theorems;
- proof-policy hashing, forbidden-token, axiom, freshness, and mutation checks;
- dashboard HTTP/UI/scanner infrastructure;
- the five integer cases as regression fixtures.

Retire as production authorities:

- per-program `FrontendProfile` assertion/signature inventories;
- per-program `ModelProfile` selections;
- duplicated `ScaleupCatalog` subsets;
- `case_id` branches in emitters;
- hardcoded dashboard `PROOF_CASES` and `supported_cases` dependency filtering.

## Assertion and Contract Rule

Source `assert` expressions should be translated mechanically. They are not the
entire C contract. Memory extent/writability, alias/restrict, overread, frame,
intrinsic legality/state, and legal RVV progress come from reusable C, intrinsic,
or architecture layers. External caller restrictions absent from the kernel need
independent evidence.

The proof agent may not add axioms, weaken a frozen goal, or invent a precondition.
A false or unsupported direct claim returns failure or a counterexample. An
optional contextual claim is regenerated only from separately supplied evidence.

Phase one requires the normalized Neon and RVV entry contracts to match and proves
equivalence under that shared contract. It does not attempt implication or complete
replacement coverage. The fixed-tail recognizer automatically discharges only
local remainder assertions derived from its loop/tail structure; any other local
assertion fails recognition. Generated artifacts form a canonical
content-addressed chain from manifest through result; proof acceptance uses
before/after protected-closure digests and is an integrity gate, not process
isolation.

## Current Implementation

**Confirmed:** strict content-addressed schemas cover intrinsic/layout/schedule
capabilities, typed entry contracts, Manifests, generated Models/Spec, proof tasks,
counterexamples, results, and independent reviews. The profile-free Clang entry
accepts explicit C pairs and parse facades, translates assertions with control
context, and fail-closes on unconsumed calls, control, assertions, or effects.

The compiler recognizes 8/16/32-bit scalar streams, fixed-no-tail, complete
power-of-two tails, both audited two-phase encodings, and RVV strip-mining. It
emits independent `fNeon`/`fRvv` definitions and proof-free Models/Spec without a
case id. Scalar layouts retain each stream's C type, and two-phase secondary
functions/data dependencies are derived from extraction rather than a template.

The proof gate freezes the exact claim and parents, permits only `Proof.lean`,
rejects proof escapes, audits transitive axioms, and publishes a hash-bound Result.
Lean checks build their dependency closure in temporary roots; checked-in caches
are not trusted. The compiler fingerprint follows reachable generation code, while
proof, diagnostic, review, and dashboard consumers carry separate checker hashes.

**Confirmed held-out gate:** two S8 VMax C pairs pass generation and proof after
full output deletion. The second pair uses randomized directories, basenames,
function identifiers, and Lean namespace. A Neon max-to-min change invalidates the
agent proof, and pointer-step, loop-update, entry-assertion, and active-`vl`
mutations all fail closed. The complete run leaves every tracked repository file
byte-identical.

**Confirmed current batch state:** structural discovery finds twenty elementwise
pairs: nineteen scalar-layout and one deferred grouped complex layout. All nineteen
scalar programs pass the same profile-free parse/recognize/resolve/emit path and
have content-addressed Manifest/Models/proof-free Spec artifacts. Their terminal
outcomes are eight `verified(value)`, four Lean-checked `counterexample`, and seven
`external-condition-missing`. The checked counterexamples are the `s8-vclamp`
cross-phase ordering bug plus whole-program FP disagreements in `f32-vrndne`,
`f32-vmax`, and `f32-vmin`. `f32-vcmul` remains `layout-unrecognized` outside the
nineteen. There are no parser, contract, intrinsic, family, or generation failures
in the scalar scope. The external-condition dimension remains twelve
`not-required` and eight `required-missing` across all twenty discovered pairs.

**Confirmed width/tail closure:** the production generator now carries distinct
8/16/32-bit input and output widths through Models and Spec. Prefix tails accept a
complete descending power-of-two decomposition instead of one memorized 4/2/1
shape, and accept the two audited storage encodings: lane-store/slide and
full-vector-store/high-half. RVV byte counts such as `n = batch / sizeof(float)`
are normalized to logical element counts only after exact type and dependency
checks. Held-out U16/U32/F32 fixed-tail and U16 fixed-no-tail pairs reach a freshly
elaborated ProofTask; a mixed I32-to-I16 pair confirms distinct widths through the
same full chain. Multi-phase Models now project the secondary block to a separate
`fNeonSecondary` and expose phase equality as an explicit claim instead of hiding
it in `fNeon`. This closes the reusable width blocker; it does not prove phase
equality or supply missing corpus intrinsics and external conditions.

**Confirmed dashboard-authority closure:** `/api/elementwise` derives discovery and
status only from `CorpusReport.json` plus the content-addressed M/E/D/S/A/C/T/R
artifact closure. A checked-in held-out VMax pair reaches `proof-ready` without a
dashboard case entry. The page displays input-condition scope/status, cross-phase
status/trial count, concrete counterexample witnesses, and separate value/C/ISA
claims. The retained legacy table is labeled historical and cannot affect the
elementwise projection. The schema-v3 page distinguishes three counts that must
not be conflated: 186 architecture/spelling dependencies, of which 178 are
configured; 189 exact registry variants; and 180 exact variants actually used by
the nineteen-program artifact closure. Exact capability and review identities bind
the descriptor hash, so different typed descriptors with one spelling cannot
share approval. Each of the 189 variants has a distinct dashboard row.

**Confirmed current review state:** all 180 exact variants used by the nineteen
scalar programs now carry distinct schema-v2 independent review records. The
records bind official exact C prototypes, descriptor and transitive implementation
hashes, pure-value claim scope, 23 explicit architecture-conditioned subjects,
machine checks, policy, and reviewer report. The complete 189-variant registry
therefore reports 180 reviewed and nine unused/unreviewed variants. The older nine
schema-v1 F32 records moved to a historical directory and cannot satisfy the live
loader.

The first M6 review returned `NO-GO` because RVV evidence proved only call arity
and the graph could display scoped reviews without its audit parents. RVV now
matches every exact official prototype in pinned `intrinsic_funcs.adoc`, and the
default graph requires both the audit and review plan whenever schema-v2 records
exist. The convergence review returned `GO (180/180)`.

**Confirmed current validation:** the M6 review pack partitions 180 used exact
subjects into twelve semantic families and machine-checks every subject. The
default checked-in artifact root was regenerated with 19 scalar manifests, 189
unique exact variants, 180 used/reviewed/Lean-checked variants, 23 conditioned
variants, and zero stale program nodes. A fresh owner-facing rerun on local HEAD
passed 248 elementwise compiler/dashboard tests. After the final program-review loading-order
correction, the complete repository suite passes 444 tests in 437.23 seconds.
Tracked Lean build caches produced by legacy tests were restored and are not part
of the delivery.

**Confirmed rerun gap:** invoking `proof check` again on an already published
verified program changes the closure/result hash because `ArtifactIndex.json`
contains the prior result binding. The Lean theorem still verifies, but the command
is not byte-idempotent and stales the existing program review until republished.

**Confirmed program review closure:** each of the nineteen scalar programs has a
strict, content-addressed independent outcome review. The review subject binds the
C sources, Manifest, Models, proof-free Spec, external condition, cross-phase
audit, counterexample or ProofTask/Proof/Result, checker, and toolchain. The first
review found stale/anonymous counterexample and checker-closure gaps. After named
witnesses, live checker recomputation, full regeneration, and fail-closed publisher
and loader checks, the convergence reviewer returned `GO (19/19)`. The dashboard
loads all nineteen reviews and reports the exact 8/4/7 split. C and ISA
correspondence remain explicitly `not-established`.

**Confirmed external-condition/counterexample implementation:** every compilation
binds `ExternalCondition.json` and `CrossPhaseAudit.json`. Registered XNNPACK runs
pin and hash the discovered registration/initializer path; standalone runs make an
explicit unconditional claim. Twelve programs need no external semantic parameter
condition, while all eight quantized programs remain `required-missing`; no caller
condition is fabricated. The pinned S8 clamp path does not call the separately
found output-range validator, so signed `min <= max` remains only a candidate.

**Confirmed external-evidence split:** the pinned tensor path does establish each
QINT8/QUINT8 zero-point range and requires every quantization scale to be positive,
finite, and normal. This is enough in principle to resolve the producer bridge for
`qs8-f32-vcvt` and `qu8-f32-vcvt`, whose initializers only copy those values. The
derived ratio, multiplier, shift, and LReLU-slope bounds needed by the other five
blocked programs appear as initializer `assert`s, but no matching runtime caller
validation was found. They may be translated as explicit initializer preconditions;
they cannot yet be labeled caller-established XNNPACK guarantees.

**Confirmed/Inference on NaNs:** FP32 tensor creation does not inspect or reject
element values, and XNNPACK's own binary microkernel tests explicitly skip NaN
reference outputs because kernels are inconsistent. Thus the current call path
does not justify a no-NaN theorem assumption. The `f32-vmax`/`f32-vmin` witnesses
match the real FMAX versus RVV maximumNumber/minimumNumber distinction for a numeric
operand paired with NaN. The `f32-vrndne` witness is instead a current Lean-model
artifact under Arm `FPCR.DN=0`: its RVV C has an explicit payload-restoration fixup,
while shared host `FP32.add/sub` incorrectly canonicalizes the modeled Neon path.
Ordinary FP arithmetic still shares that host operation across Neon and RVV, so the
eight current FP value proofs are not yet exact-NaN ISA claims.

The cross-phase checker distinguishes not-applicable, missing-condition,
bounded-no-witness, and Lean-checked counterexample states. Its checked S8 clamp
witness is `min = 5`, `max = 0`, `x = 0`, producing 0 and 5 in the two Neon phases.
A bounded miss is diagnostic only; a bound counterexample is terminal and blocks
proof delegation. See `../elementwise-compiler/EXTERNAL_INPUT_AUDIT.md`.

## Completed Delivery and Next Boundary

The requested scalar elementwise delivery now implements this chain:

```text
registered intrinsics/layout/families + discovered C pair
  -> no Python/Lean source edits
  -> generated manifest, Models.lean, Spec.lean, ProofTask.json
  -> proof attempt, checked counterexample, or explicit external blocker
  -> independent outcome review
  -> dashboard program state derived automatically
```

The two randomized S8 VMax positives and semantic/structural negatives already
satisfy the zero-framework-edit gate for the supported 8-bit family. New program
support must arrive by adding or generalizing reusable intrinsic, layout, element
width, or tail capabilities, never by adding a program id to the compiler or
dashboard.

**Delivered target:** all nineteen scalar-layout programs have separate hash-bound
outcome reviews, and all 180 exact intrinsic variants they use have separate
hash-bound intrinsic reviews. This does not mean nineteen equivalence theorems:
only eight direct value claims are proved, four are refuted by checked witnesses,
and seven are honestly blocked by missing external caller evidence.

**Next proposal, not part of this completed milestone:** establish the seven
external caller conditions where true, decide the intended FP NaN semantics for
the three false direct claims, and add one reusable grouped planar-complex layout
for `f32-vcmul`. Full C-memory and ISA correspondence remain separate later layers.

## Independent Reviews

**Confirmed:** the design, width/tail, external-condition, dashboard-authority,
intrinsic batches, shared-scalar/exact-identity, and nineteen-program outcome
milestones all received convergence `GO` after their initial findings were fixed.
Detailed records are under `notes/reviews/` and `DISCUSSION_LOG.md`; the latest
reviewer reproduced the 180/180 intrinsic closure, the 8/4/7 program split, and 19
strictly loadable program reviews.
