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

## S8 VMax Regression

**Confirmed:** the original `986acd4` prototype established the three-part
loop-to-map/map-to-map proof shape. Its manual generation limitation is superseded:
the randomized held-out VMax gate now generates and proves the complete stack with
zero framework edits.

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

**Confirmed current batch state:** structural discovery finds twenty elementwise
pairs: nineteen scalar-layout and one deferred grouped complex layout. All nineteen
scalar programs pass the same profile-free parse/recognize/resolve/emit path and
have content-addressed Manifest/Models/proof-free Spec artifacts. Eleven are
`spec-generated`, seven are `external-condition-missing`, and `s8-vclamp` has a
Lean-checked counterexample. `f32-vcmul` remains `layout-unrecognized` outside the
nineteen. There are no parser, contract, intrinsic, family, or generation failures
in the scalar scope. The external-condition dimension remains twelve
`not-required` and eight `required-missing`.

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

**Confirmed current review state:** current implementation changes invalidate the
older nine F32 review bindings as intended. Their records remain as historical
evidence, but the generated registry honestly reports 0/189 reviewed and 0/180
reviewed among variants used by the nineteen programs. A first independent M5
audit returned `NO-GO` after finding the old spelling-level identity collision;
after exact identities and schema-v3 counts were added, the same reviewer reran
the corpus/graph/web checks and returned `GO`.

**Confirmed current validation:** fresh temporary-root Lean compilation audited
all five retained legacy theorem types and found only `Classical.choice`,
`Quot.sound`, and `propext`. The complete repository suite passes 418 tests. The
default checked-in artifact root was cleanly regenerated: schema v3 reports 19
scalar manifests, 189 unique exact variants, 180 used variants, and zero stale
program nodes.

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

**Confirmed external-condition/counterexample implementation:** every compilation
binds `ExternalCondition.json` and `CrossPhaseAudit.json`. Registered XNNPACK runs
pin and hash the discovered registration/initializer path; standalone runs make an
explicit unconditional claim. Twelve programs need no external semantic parameter
condition, while all eight quantized programs remain `required-missing`; no caller
condition is fabricated. The pinned S8 clamp path does not call the separately
found output-range validator, so signed `min <= max` remains only a candidate.

The cross-phase checker distinguishes not-applicable, missing-condition,
bounded-no-witness, and Lean-checked counterexample states. Its checked S8 clamp
witness is `min = 5`, `max = 0`, `x = 0`, producing 0 and 5 in the two Neon phases.
A bounded miss is diagnostic only; a bound counterexample is terminal and blocks
proof delegation. See `../elementwise-compiler/EXTERNAL_INPUT_AUDIT.md`.

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

## Independent Reviews

**Confirmed:** the design, width/tail, external-condition, dashboard-authority,
first intrinsic batch, and current shared-scalar/exact-identity milestones all
received convergence `GO` after their initial findings were fixed. Detailed
records are under `notes/reviews/` and `DISCUSSION_LOG.md`; the latest reviewer
specifically reproduced 189 unique exact rows and 180 used variants.
