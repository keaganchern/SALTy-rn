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

**Confirmed limitation:** the current Python backend generated only the imported
local block/chunk model. The new loop assembly and `Spec.lean` were manually staged
to validate the desired output. This is not yet zero-source-change onboarding.

## Assertion and Contract Rule

Source `assert` expressions should be translated mechanically. They are not the
entire C contract. Memory extent/writability, alias/restrict, overread, frame,
intrinsic legality/state, and legal RVV progress come from reusable C, intrinsic,
or architecture layers. External caller restrictions absent from the kernel need
independent evidence.

The proof agent may not add axioms, weaken a frozen goal, or invent a precondition.
A false or unsupported direct claim returns failure or a counterexample. An
optional contextual claim is regenerated only from separately supplied evidence.

Direct paired claims retain the complete separate Neon and RVV assumption sets and
add family/intrinsic legality. They do not reduce the domain to assertion text
shared by both sides. Generated artifacts form a canonical content-addressed chain
from manifest through result; proof acceptance uses before/after protected-closure
digests and is an integrity gate, not process isolation.

## Current Gap

**Confirmed:** the architecture and proof shape are settled; the generic compiler
path is not implemented. The current backend still requires named profiles,
catalogs, model switches, and proof targets. The existing dashboard is present but
uses the old case-scoped data model and does not show execution-family nodes.

## Immediate Objective

Make fixed-no-tail generation pass the two-positive/one-negative held-out gate:

```text
registered intrinsics/layout/families + two positive C pairs + one mutation
  -> no Python/Lean source edits
  -> generated manifest, Models.lean, Spec.lean, ProofTask.json
  -> proof attempt and Lean result
  -> dashboard program state derived automatically
```

One positive may use the existing synthetic `s8-vmax`; the second must randomize
path, filename, function, and module identities. The negative changes one side from
max to min. Do not onboard a sixth named case by adding another profile while this
gate is open.

## Independent Plan Review

**Confirmed, 2026-08-29:** a separate reviewer agent first returned
`GO WITH REQUIRED REVISIONS`. After layout/view capability, exact assumption
domains, content-addressed parent hashes, honest proof-process wording, milestone
reordering, and a stronger anti-special-casing gate were incorporated, its
convergence review returned `GO`: no remaining design-document defect blocks M1a.
The review is preserved in `notes/reviews/elementwise-compiler-plan-review-2026-08-29.md`.
