# Elementwise Compiler Project State

Last updated: 2026-08-29 (Asia/Seoul)

## Snapshot

- Branch: `feat/elementwise-compiler`
- Base: `1707e5e1b847fe0c4a0a17ff058928485db82cee`
- First branch commit: `986acd4` (`s8-vmax` target-architecture prototype)
- Upstream corpus baseline: `origin/main@6acdf7a522e2b97b96831f8e95b578e6edf42a83`

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

**Historical intrinsic snapshot before M4:** the configured index had 96 exact typed variants:
54 Neon variants under 49 spellings and 42 RVV variants under 36 spellings. The
local corpus contains 190 Neon and 165 RVV lexical spellings. Semantic adequacy is
not established and there are zero configured independent reviewers.

These numbers are an audit snapshot, not live status. The dashboard/generated
manifest must own future counts.

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

## S8 VMax Prototype

**Confirmed:** commit `986acd4` adds a Lean-checked target structure using the
existing generated S8 vmax block/chunk models and existing max intrinsics. It
proves:

```text
Neon loop = map fNeon
RVV loop  = map fRvv
forall x, fNeon x = fRvv x
therefore Neon logical output = RVV logical output
```

`fNeon` and `fRvv` are defined independently through their respective intrinsic
expressions. `Spec.lean` contains proof-free frozen propositions; `Proof.lean` is
the designated agent-owned artifact; `Audit.lean` checks the exported claim and
axioms. The current repository-local process is not a write sandbox.

**Historical prototype limitation, superseded:** at commit `986acd4`, the Python
backend generated only the local block/chunk model, so loop assembly and Spec were
manually staged. The current explicit compiler and randomized held-out gate now
generate the complete stack without framework edits.

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

**Confirmed:** implementation stages 1 and 2 now provide strict content-addressed
schemas for intrinsic/layout/schedule capabilities, typed entry contracts,
program manifests, generated artifacts, proof tasks, and terminal results. It also
adds a profile-free Clang entry point: callers explicitly provide both C paths,
function names, architectures, target triples, and parse facades. Reachable call
types are discovered from the facade declarations; assertions are emitted with
their control context and translated by a fail-closed typed expression parser.

The generic path is exercised on all five existing integer pairs without reading
their named frontend profiles. Their normalized entry contracts match;
`qs8-vcvt`'s two local tail assertions remain local facts. Exact intrinsic
ambiguities are resolved by one program-independent, information-preserving rule;
true ties fail closed. The compiler recognizes 8-, 16-, and 32-bit scalar streams,
fixed-no-tail, complete power-of-two fixed tails, two-phase schedules, and RVV
strip-mining, and hash-binds the
complete parsed call/control/assert/effect inventory. It emits canonical
`ProgramManifest.json`, capability records, independent `fNeon`/`fRvv`
definitions, proof-free `Models.lean`/`Spec.lean`, and an artifact index.

Generated unary tail (`qs8-vcvt`), binary tail (`qu8-vadd-minmax`), nested binary
two-phase (`qs8-vadd-minmax`), separate-loop two-phase (`s8-vclamp`), and
synthetic fixed-no-tail (`s8-vmax`) outputs elaborate in Lean. Output deletion and
regeneration is byte deterministic. Scalar-lane layout records carry a C type per
stream, so same-coordinate conversions such as `float[i] -> uint16[i]` are not
misclassified merely because input and output element types differ. The old named
profiles remain regression adapters; the production compiler accepts no case id.

The two-phase emitters are structural on both supported C encodings. In
particular, the separate-loop path derives the second block, live-prefix tail,
data dependencies, pointer versions, and store widths from the extraction. The
former `s8-vclamp` call-number/template table has been removed. A supported
semantic operation change regenerates a different model; it is not rejected for
departing from a memorized program body.

The proof gate now elaborates the frozen generated claim, emits
`ProofTask.json`, permits an external agent to modify only `Proof.lean` inside the
accepted closure, rejects proof escape identifiers, checks the exact theorem type
and transitive axioms with Lean, and publishes content-addressed `Result.json`.
It compiles its small Lean dependency closure in a temporary root, so checking does
not modify the repository's tracked `.lake` products.

The older dashboard proof-policy audit likewise copies the complete Lean source
tree without `.lake`, performs a fresh build, and audits the elaborated theorem in
that temporary root. Checked-in cache state is neither trusted nor modified.

**Confirmed held-out gate:** two S8 VMax C pairs pass generation and proof after
full output deletion. The second pair uses randomized directories, basenames,
function identifiers, and Lean namespace. A Neon max-to-min change invalidates the
agent proof, and pointer-step, loop-update, entry-assertion, and active-`vl`
mutations all fail closed. The complete run leaves every tracked repository file
byte-identical.

**Confirmed batch state:** structural discovery finds twenty elementwise pairs:
nineteen scalar-lane and one deferred grouped complex layout. The checked-in
corpus report now has one Lean-checked `counterexample`, four
`external-condition-missing`, fourteen `intrinsic-missing`, and one
`layout-unrecognized`. Its independent external-condition dimension reports
twelve `not-required` and eight `required-missing`. There are no parser,
contract, family, or generation failures in the nineteen-program scalar scope.
The dashboard reads the report and
verifies every Manifest/Models/Spec/ProofTask/Proof/Result parent hash before
displaying progress; a modified child becomes `stale-artifact`. It shows value,
C, and ISA claim layers separately.

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

**Confirmed width-milestone validation:** the complete repository suite passed with 393
tests. The refreshed twenty-program graph has zero stale nodes, and the checked-in
legacy generated models pass deterministic regeneration checks. A later
independent audit at HEAD `a77933b` reran 57 focused compiler/dashboard tests and
reproduced the 20/19/1 and 5/14/1 counts.

**Confirmed current M2 validation:** the complete repository suite passes with
402 tests. The refreshed graph has zero stale nodes and reports 14
`intrinsic-missing`, 4 `external-condition-missing`, 1 Lean-checked
`counterexample`, and 1 `layout-unrecognized`. An independent convergence review
reproduced standalone/registered clamp rejection and standalone VMax proof-task
preparation, then returned `GO`.

**Confirmed dashboard-authority closure:** `/api/elementwise` derives discovery and
status only from `CorpusReport.json` plus the content-addressed M/E/D/S/A/C/T/R
artifact closure. A checked-in held-out VMax pair reaches `proof-ready` without a
dashboard case entry. The page displays input-condition scope/status, cross-phase
status/trial count, concrete counterexample witnesses, and separate value/C/ISA
claims. The retained legacy table is labeled historical and cannot affect the
elementwise projection. An independent review first found three missing evidence
fields in the UI; after they were added, convergence review returned `GO`.
The generated intrinsic registry now has 105 exact typed variants. Across the
twenty-program dependency graph, 94 architecture/spelling pieces are configured;
the first nine F32 structural/schedule pieces are Lean-checked and independently
reviewed. The active milestone is the remaining semantic intrinsic families.

**Confirmed first intrinsic-review batch:** one program-independent typed library
adds exact F32 load/store, low/high extraction, lane store, RVV load/store, and
active-length descriptors. Its parse facade is mechanically rendered from that
library. Nine content-addressed review records bind exact source type, descriptor,
the real generic/context-specific lowering files, pinned Arm ACLE or RISC-V Vector
C Intrinsics evidence, check outputs, policy, and reviewer. A first audit found
that `vst1_lane_f32` accepted lane 1 but always modeled lane 0; the lowering now
uses `drop (lane * width)` and rejects lane 2. Convergence review returned `GO`.
These approvals establish repository value-model evidence only, not complete C or
ISA correctness.

**Confirmed intrinsic-batch validation:** the complete repository suite passes
412 tests. Rebuilding the checked-in corpus twice produces the same complete tree
digest; the graph has zero stale program nodes and reports 9/94 reviewed dependency
pieces. The independent convergence audit returned `GO` for all nine exact
variants after reproducing the lane-1 positive and lane-2 rejection tests.

**Confirmed concrete false obligation:** `s8-vclamp`'s 64-byte Neon phase applies
signed max-with-min and then min-with-max, while its 8-byte and tail phases apply
them in the opposite order. Under the currently extracted entry contract,
`x = 0`, `min = 10`, `max = 5` makes those phases return 5 and 10 respectively.
Therefore its generated single-`fNeon` secondary-block and whole-loop claims are
false unless separately evidenced input conditions include `min <= max`.
Models/Spec generation has not accepted a false theorem—the Spec is proof-free—but
the pipeline must report this as a checked counterexample/family-contract failure
or bind an evidenced external contract, rather than leave it as an unexplained
`spec-generated` program.

**Confirmed correction to the upstream-condition claim:** the extracted kernel
body does not assert `min <= max`; its local harness merely chooses one valid
instance. The pinned registration does select
`xnn_init_qs8_clamp_scalar_params`, but the first audit incorrectly treated the
existence of `xnn_subgraph_check_output_min_max` elsewhere in XNNPACK as a call
edge. The pinned unary clamp path does not call that validator. The positive-scale
and clamp-order caller guarantees are therefore unresolved. Signed
`params.min <= params.max` is a useful candidate condition, not established input
evidence.

**Confirmed external-input audit:** the same category affects eight of the twenty
elementwise programs, not only `s8-vclamp`. They are the eight quantized-parameter
programs: S8 clamp, QS8/QU8 add, QS8 conversion, QS8 LReLU, QS8 multiply, and the
QS8/QU8-to-F32 conversions. Their legal parameter ranges or relations are
constructed/validated outside the isolated kernel entry assertions. Eleven
programs have no semantic parameter fields; `f32-vlrelu` copies one slope without
an analogous hidden relation found. See
`../elementwise-compiler/EXTERNAL_INPUT_AUDIT.md`.

**Confirmed external-condition/counterexample implementation:** every compilation
now emits a content-addressed input-condition audit. XNNPACK-domain compilation
binds a local pair to an explicit, uniquely discovered registration, verifies
the pinned submodule commit, follows the shared Neon/RVV parameter initializer, and
hash every consulted source in `ExternalCondition.json`. The extractor is
conservative: it classifies twelve programs `not-required` and all eight audited
quantized-parameter programs `required-missing`; it currently emits no `resolved`
condition. Standalone compilation records a distinct
`local-unconditional-claim` scope, meaning that no caller condition is assumed
and all modeled parameter values remain in the theorem domain; it is not treated
as an unaudited success. `Spec.lean` keeps the unconditional claim and, for S8 clamp, exposes
signed `min <= max` only as a diagnostic candidate. The proof gate rejects a
missing external condition before creating a ProofTask.

Every generated stack also binds `CrossPhaseAudit.json`; this check is invoked by
the generic compiler rather than only by the corpus runner. It records
not-applicable, blocked-external-condition, bounded-no-witness, or counterexample
without equating a bounded miss with proof. For multi-phase functions it searches
deterministic parameter and input candidates and can emit a concrete Lean-checked witness. The checked-in
`s8-vclamp` witness uses `min = 5`, `max = 0`, `x = 0`; the primary phase returns
0 and the secondary phase returns 5. `Counterexample.json` binds the exact
Manifest, Models, Spec, checker, Lean file, and toolchain hashes. Programs with a
missing condition but no expressible candidate are reported as blocked rather
than spending an unbounded search over unconstrained parameters. A bound checked
counterexample is terminal: `prepare_proof_task` rejects it before delegation.

## Immediate Objective

Close the external-condition, cross-phase, and dashboard-authority gaps, then
expand reviewed intrinsic capabilities through the artifact chain:

```text
registered intrinsics/layout/families + discovered C pair
  -> no Python/Lean source edits
  -> generated manifest, Models.lean, Spec.lean, ProofTask.json
  -> proof attempt and Lean result
  -> dashboard program state derived automatically
```

The two randomized S8 VMax positives and semantic/structural negatives already
satisfy the zero-framework-edit gate for the supported 8-bit family. New program
support must arrive by adding or generalizing reusable intrinsic, layout, element
width, or tail capabilities, never by adding a program id to the compiler or
dashboard.

**Delivery target:** all nineteen scalar-layout programs, with every exact
intrinsic and every final program carrying separate hash-bound independent review
records. This is executable only after the external-input,
cross-phase/counterexample, and dashboard-authority gaps are closed; success for
all nineteen cannot be promised before those checks expose remaining mismatches.

## Independent Plan Review

**Confirmed, 2026-08-29:** a separate reviewer agent first returned
`GO WITH REQUIRED REVISIONS`. After layout/view capability, exact assumption
domains, content-addressed parent hashes, honest proof-process wording, milestone
reordering, and a stronger anti-special-casing gate were incorporated, its
convergence review returned `GO`: no remaining design-document defect blocks M1a.
The review is preserved in `notes/reviews/elementwise-compiler-plan-review-2026-08-29.md`.
After the scope narrowed to nineteen scalar-layout pairs and equal entry contracts,
a fourth quick pass again returned `GO`; it required the fixed-tail checker to
preserve element-size divisibility in addition to proving remainder bounds.

**Confirmed M1 review:** the width/tail implementation received `GO` after the
reviewer reproduced the wide direct-byte-count rejection, mixed I32-to-I16 full
chain, phase-specific `fNeonSecondary` Spec, and integer descriptor digest guard.
See `notes/reviews/elementwise-width-tail-review-2026-08-29.md`.
