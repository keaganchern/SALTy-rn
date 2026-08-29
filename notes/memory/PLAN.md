# Elementwise Compiler Active Plan

Last updated: 2026-08-29 (Asia/Seoul)

## Active Milestone

Turn the checked S8 vmax target structure into a zero-source-change vertical slice.
The compiler must accept the existing C pair using already registered intrinsics,
generate the complete protected artifact stack, launch/check a proof attempt, and
make the dashboard derive its state without adding `s8-vmax` to a Python case list.

## Canonical Artifacts

For one program pair, generation produces:

```text
ProgramManifest.json  parsed types, assertions, operations, dependencies, family
Models.lean           independent Neon/RVV implementations and lane functions
Spec.lean             frozen proof-free propositions
ProofTask.json        hashes, imports, theorem names, writable proof path
Proof.lean             only agent-owned source
Result.json           generation/proof/Lean status and precise failure reason
```

Names or paths may change only through an explicit decision. Ownership may not.

## Milestone Roadmap

### M0 — Branch-Local Memory and Architecture

**Status:** Completed.

Exit gates:

- branch contains concise current state, decisions, active plan, architecture, and
  append-only discussion log;
- documents state the zero-source-change acceptance test and dashboard motivation;
- stale five-case continuation is not presented as the active plan.

### M1 — Capability and Result Schema

**Status:** In progress.

Deliver:

- typed global intrinsic capability records without `supported_cases` authority;
- execution-family capability records for fixed-no-tail, fixed-tail,
  multi-phase, and RVV strip-mine;
- `ProgramManifest` and `Result` schemas with stable failure states;
- dashboard projection derived only from these records.

Exit gates:

- one intrinsic capability can satisfy multiple compatible program dependencies;
- program rows need no manually named proof target;
- old five-case rows can be projected through a compatibility adapter during
  migration, but the adapter cannot satisfy the held-out S8 gate.

### M2 — Generic Typed Frontend

**Status:** Pending.

Deliver:

- discover function identity, signature, parameters, and assertions from Clang;
- parse supported assertion Boolean expressions into a typed predicate tree;
- infer buffer roles and scalar/parameter fields from use/dataflow;
- bind calls through the global exact typed intrinsic registry;
- record all control, load/store, pointer, and count effects in the manifest;
- reject every unconsumed or ambiguous construct.

Exit gates:

- removing all S8-vmax-specific profile/catalog declarations does not prevent its
  manifest from being generated;
- changing a call signature, pointer step, loop update, assertion, or `vl` operand
  changes the manifest or fails closed;
- the manifest is deterministic and source/facade/compiler provenance-bound.

### M3 — Fixed-No-Tail Generation

**Status:** Pending.

Deliver:

- recognize fixed width plus source-derived divisibility;
- generate independent block/chunk expressions, `fNeon`, and `fRvv`;
- generate complete Neon/RVV logical loop models;
- generate proof-free `Spec.lean` using the reusable family theorem;
- remove manually staged V2 Models/Spec from the acceptance path.

Exit gates:

- one command regenerates the current S8 VMax V2 proposition byte-for-byte or a
  reviewed equivalent proposition;
- the command contains no branch on `s8-vmax`, function name, namespace, or source
  path;
- a second synthetic same-family input requires no source changes to generate.

### M4 — Proof Task and Lean Result

**Status:** Pending.

Deliver:

- freeze generated artifacts and emit `ProofTask.json`;
- restrict the agent-writable path to `Proof.lean` in the review policy;
- verify exact theorem type, forbidden tokens, transitive axioms, and freshness;
- report proof failure separately from a checked semantic counterexample.

Exit gates:

- the S8 proof can be deleted and regenerated without changing protected files;
- an agent modification to Models/Spec/policy invalidates the result;
- `vmax` to `vmin` produces a failed original claim or checked counterexample.

### M5 — Dashboard Puzzle Migration

**Status:** Pending.

Deliver:

- intrinsic, family, program, generation, proof, and claim-scope nodes;
- explicit missing-piece list per program;
- automatic transition to `proof-ready` when dependency closure completes;
- value/C/ISA layers displayed separately;
- remove `supported_cases` and hardcoded `PROOF_CASES` as authorities.

Exit gates:

- adding one intrinsic capability updates every dependent program automatically;
- S8 VMax appears without a dashboard code/config entry;
- no UI success is inferred only from file presence.

### M6 — Fixed Tail and Binary Reuse

**Status:** Pending.

Deliver:

- unary and synchronized-binary fixed-tail recognition;
- generated live-prefix observation and independent tail-read values;
- structural 4/2/1 or analogous store-plan extraction;
- reuse existing schedule theorems and integer fixtures.

Exit gates:

- at least two existing integer programs with different intrinsic pipelines use
  the same family implementation without program-specific source;
- a tail-store, slide, load-base, or pointer mutation fails recognition or proof;
- logical value scope remains distinct from physical overread legality.

### M7 — Compositional Multi-Phase Family

**Status:** Pending.

Deliver:

- ordered phase list with fixed widths and optional nested/final tail;
- generic phase-composition theorem;
- structural recognition for the 16/8/4/2/1 and 64/8/4/2/1 shapes.

Exit gates:

- `qs8-vadd-minmax` and `s8-vclamp` select the same parameterized multi-phase
  mechanism without named emitter branches;
- later `f32-f16-vcvt` needs FP/intrinsic work, not a new control-flow compiler.

### M8 — Coverage Expansion

**Status:** Pending.

Fill missing exact integer intrinsic variants, then establish the reviewed FP
semantic layer before onboarding FP elementwise pairs. Dashboard progress must be
monotone through shared dependencies rather than manually advanced program rows.

## Immediate Work Queue

Only the first incomplete item is active at a time:

1. define branch-local `ProgramManifest`/`Result` and capability schemas;
2. change dashboard state computation to accept global intrinsic/family nodes;
3. emit an S8 VMax manifest through the generic frontend;
4. generate fixed-no-tail Models/Spec from that manifest;
5. generate/check the proof task and publish Result;
6. run the zero-source-change held-out mutation matrix;
7. migrate fixed-tail unary and binary fixtures;
8. add multi-phase composition;
9. expand integer intrinsic coverage;
10. start the explicit FP semantics milestone.

## Global Acceptance Gates

1. **Zero source edits:** onboarding a held-out same-family program changes no
   Python/Lean framework source.
2. **Independent models:** Neon and RVV dataflows and lane functions are generated
   separately.
3. **Whole-program consumption:** unsupported calls/control/effects fail closed.
4. **Generated frozen goal:** proof search cannot change Models/Spec/observation.
5. **Proof safety:** no `sorry`, `admit`, custom axiom, unsafe proof escape, or
   unapproved native decision dependency.
6. **Mutation sensitivity:** supported semantic changes alter the model and fail
   the old claim or yield a checked counterexample.
7. **Dashboard derivation:** program readiness is computed from capability closure.
8. **Scope honesty:** value results are not labeled C/ISA results.
9. **Reproducibility:** manifests and generated artifacts bind source, facade,
   registry, compiler producer, and exact toolchain inputs.

## Deferred but Visible

- full byte-memory, alias/restrict, frame, and legal overread refinement;
- real-header/compiler dependency closure;
- ISA-legal RVV `vsetvl`, masks, tail policy, `vxrm`, and `vxsat` correspondence;
- complete Arm machine state and compiled-binary correctness;
- reduction, permutation, window/gather, convolution, and GEMM families.
