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

**Confirmed intrinsic snapshot:** the configured index has 96 exact typed variants:
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
true ties fail closed. The compiler recognizes scalar streams, fixed-no-tail,
fixed-tail with 4/2/1 prefix stores, two-phase 64/8 and nested 16/8 schedules, and
RVV strip-mining, and hash-binds the
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

**Confirmed batch/dashboard state:** structural discovery finds twenty elementwise
pairs: nineteen scalar-lane and one deferred grouped complex layout. The checked-in
corpus report currently has five `spec-generated`, fourteen `intrinsic-missing`,
and one `layout-unrecognized`. There are no parser, contract, family, or generation
failures in the nineteen-program scalar scope. The dashboard reads the report and
verifies every Manifest/Models/Spec/ProofTask/Proof/Result parent hash before
displaying progress; a modified child becomes `stale-artifact`. It shows value,
C, and ISA claim layers separately.

**Remaining capability work:** the fourteen blocked scalar programs need exact
typed parse facades and reviewed integer/FP intrinsic definitions. `f32-vcmul`
needs a grouped complex layout/view. These are visible puzzle pieces, not hidden
program profiles or control-flow generator work. No current corpus program is
claimed `verified(value)` merely because its Spec was generated.

**Confirmed final validation:** the complete repository suite passes with 379
tests. The refreshed twenty-program graph has zero stale nodes, and the checked-in
legacy generated models pass deterministic regeneration checks.

## Immediate Objective

Expand reviewed intrinsic capabilities through the now-complete artifact chain:

```text
registered intrinsics/layout/families + discovered C pair
  -> no Python/Lean source edits
  -> generated manifest, Models.lean, Spec.lean, ProofTask.json
  -> proof attempt and Lean result
  -> dashboard program state derived automatically
```

The two randomized S8 VMax positives and semantic/structural negatives already
satisfy the zero-framework-edit gate. New program support must now arrive by
adding reusable intrinsic or layout capability records, never by adding a program
id to the compiler or dashboard.

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
