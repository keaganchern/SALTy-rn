# Draft PR: Add an audited, arbitrary-length elementwise Neon-to-RVV verification pipeline

## Summary

This PR adds a reusable, fail-closed pipeline for generating and checking
value-level Lean equivalence claims for elementwise Neon/RVV kernel pairs over
arbitrary logical input lengths.

The central goal is puzzle-style reuse: once the exact typed intrinsics, scalar
layout, and execution schedule used by a kernel are registered, the kernel can be
parsed, modeled, specified, checked, reviewed, and displayed without adding a
program-specific Python branch, Lean model, proof target, or dashboard entry.

For the current scalar-layout elementwise corpus, the pipeline discovers and
generates artifacts for all 19 in-scope kernel pairs. Independent, hash-bound
program reviews reproduce the following outcomes:

| Outcome | Count | Programs / meaning |
|---|---:|---|
| `verified(value)` | 2 | `f32-f16-vcvt` and `f32-vrndne` have Lean proofs of the generated complete value-equivalence claim |
| `counterexample` | 10 | Nine floating-point exact-bit disagreements and one `s8-vclamp` phase-order disagreement have checked witnesses |
| `external-condition-missing` | 7 | The models and Specs are generated, but proof delegation stops because required caller/initializer conditions are not yet established |

Thus, all 19 scalar programs complete the generation and outcome-audit workflow;
12 reach a definite semantic verdict, but only 2 are proved equivalent. This PR
does not claim that all 19 translations are correct.

## Motivation and design evolution

The previous CVC5/Bitwuzla path executes generated C++ harnesses at concrete
`batch` and VLEN choices. It reuses C execution effectively, but each run produces
one finite symbolic term graph and does not establish a theorem for arbitrary
lengths.

The Lean path therefore needs a static representation of the loop itself. Rather
than implementing a general C compiler, this PR introduces a restricted frontend
that recognizes reviewed kernel structures and fails closed on every unconsumed
call, effect, assertion, or control-flow construct.

The initial hypothesis was that intrinsic semantics alone were the reusable
pieces. Corpus analysis showed that a kernel actually needs four kinds of pieces:

1. exact typed Neon and RVV intrinsic semantics;
2. a logical layout/view describing how physical streams form output elements;
3. an execution family describing fixed blocks, tails, multi-phase execution, or
   RVV strip mining;
4. explicit entry and externally established conditions, together with the final
   observable output.

For the current 19 scalar-layout kernels, the Neon control flow reduces to fixed
blocks with power-of-two tails plus three compositional multi-phase schedules
(`8 -> 4`, `16 -> 8`, and `64 -> 8`). All corresponding RVV loops are modeled as
positive-progress strip-mined partitions. These reusable schedule theorems let the
generated models quantify over arbitrary logical lengths rather than enumerating
concrete loop executions.

Assertions are handled according to provenance:

- matching function-entry assertions become typed input contracts;
- tail-local assertions such as `1 <= batch <= 7` are discharged from the
  recognized loop exit and branch condition;
- conditions produced outside the kernel are never invented by the proof agent.

The final public obligation is `completeValueEquivalenceClaim`. Element-, block-,
tail-, loop-, and phase-level claims remain useful proof decompositions, but they
are proof guidance rather than the semantic result we ultimately report. A future
cleanup can make this distinction more explicit in the generated Spec interface.

## Pipeline

```text
Neon C + RVV C
    |
    v
fail-closed Clang AST extraction
    |
    +--> exact intrinsic capabilities
    +--> scalar layout/view capability
    +--> fixed/tail/multi-phase/strip-mine schedule capability
    +--> entry and external-condition evidence
    |
    v
ProgramManifest.json
    |
    v
Models.lean + ExternalCondition.json + CrossPhaseAudit.json
    |
    v
Spec.lean --> ProofTask.json --> agent-owned Proof.lean
    |                              |
    +--> checked counterexample    +--> Lean proof checker
                    \              /
                     v            v
                       Result.json
                            |
                            v
              independent program review + dashboard
```

The Neon and RVV models are generated independently from their respective C
dataflows and exact intrinsic descriptors. The proof task freezes the theorem and
all protected parents. The agent may write only `Proof.lean`; the checker rejects
`sorry`, custom axioms, unsafe escapes, modified parents, stale hashes, and proofs
that do not establish the designated theorem.

## What this PR adds

### Reusable compiler and artifact graph

- strict schemas for capabilities, contracts, manifests, generated artifacts,
  proof tasks, results, counterexamples, and reviews;
- explicit Clang-based parsing of supplied C/facade pairs without per-program
  frontend profiles;
- global, exact typed intrinsic resolution with content-addressed identities;
- reusable scalar layouts and fixed, tail, multi-phase, and RVV strip-mine
  execution families;
- independent generation of `Models.lean` and proof-free `Spec.lean`;
- frozen proof tasks, mutation checks, freshness checks, and axiom/escape audits;
- explicit terminal states for verified claims, checked counterexamples, missing
  external conditions, and unsupported layouts;
- an artifact-derived elementwise dashboard with no program allowlist.

### Intrinsic semantic audit

The canonical registry contains 184 semantically distinct exact variants. The 19
current scalar programs use 180 of them, and all 180 have separate schema-v2 review
records binding their prototypes, descriptors, transitive implementation hashes,
claim scopes, architecture conditions, and machine checks.

The audit also repaired architecture-specific exceptional-value semantics instead
of using one host `Float32` behavior for both architectures. In the reviewed value
mode, Arm preserves/quietens NaN payloads where specified, while RISC-V arithmetic
returns canonical NaNs. This removed the former false `f32-vrndne`
counterexample, proved that kernel's complete value claim, and exposed nine real
exact-bit floating-point disagreements that had previously been hidden.

The final independent verdicts are `GO (180/180)` for used exact intrinsic
variants and `GO (19/19)` for the exact recorded program outcomes.

### Honest counterexamples and blockers

The pipeline treats a checked counterexample as a valid audit result, not as a
proof-generation failure. In particular:

- the nine floating-point witnesses arise from actual Arm/RISC-V exact-bit NaN
  behavior under the recorded value semantics;
- `s8-vclamp` has different min/max composition orders across Neon phases when
  `min > max`;
- an executable reproducer directly runs the repository's original `f32-vmax`
  Neon C on AArch64 and the original RVV C through LLVM/Spike.

The seven external-condition blockers are also intentional fail-closed outcomes.
Two dequantization kernels appear resolvable from existing tensor validation of
scale and zero point. The remaining kernels need a checked producer bridge for
derived ratios, multipliers, shifts, or LReLU bounds. Initializer `assert`s are not
silently promoted to caller guarantees.

## Validation

The final recorded audit includes:

- full Lean build passing;
- 194 Lean-backend tests passing;
- 29 differential-audit tests passing;
- 180/180 used intrinsic review records loading and passing;
- 19/19 program outcome review records loading and passing;
- FP differential samples: 191/191 passing;
- P1 integer differential samples: 232/232 passing;
- plain-integer differential samples: 378/378 passing;
- structural/schedule checks: 68/68 passing at their explicitly non-ISA scope;
- full repository regression: 460 tests passed and 23 skipped, followed by a
  successful proof-policy hash rebind and all 14 proof-policy tests passing.

Randomized held-out S8 VMax pairs also regenerate from an empty output directory,
reach a Lean-checked result with no framework edits, and reject semantic and
structural mutations.

## Claim boundary

The positive results in this PR are value-equivalence theorems relative to the
generated Lean definitions and their recorded architecture conditions. They are
not yet complete theorems about:

- the C abstract machine, aliasing, frame conditions, or legal overreads;
- full Arm/RISC-V register, memory, exception, mask, tail, or `vsetvl` state;
- compiler lowering or binary equivalence.

The dashboard and review artifacts keep these claim layers separate.

## Scope and future work

This PR intentionally stops at the scalar-layout elementwise layer.

The two main next steps are:

1. **External-condition bridge.** Translate and prove reusable producer/caller
   contracts for the seven blocked quantized kernels, while keeping entry
   assertions, derived local invariants, initializer assertions, and actual API
   guarantees distinct.
2. **Broader layouts and kernel families.** Add a grouped planar-complex layout for
   `f32-vcmul`, then extend a restricted typed Kernel IR with reusable 2-D/strided
   layouts, reductions, gather/window access, and multi-output observations.

The repository contains 36 nonempty Neon/RVV pairs, but the additional 16
non-elementwise pairs are a future scale-up target, not current coverage. They
require more than additional intrinsics or a different output type: most introduce
new address maps, accumulator state, reduction order, or observation structure.

Additional technical debt includes making repeated proof checks byte-idempotent
and eventually establishing independent C/ISA correspondence bridges.

## Suggested review order

1. `src/workflow/verification/elementwise_compiler/` for parsing, recognition,
   generation, proof/result policy, and audits;
2. `src/verification_bw/lean/SALT/Kernel/` for reusable arbitrary-length schedule
   and layout theorems;
3. `src/verification_bw/lean/SALT/Intrinsics/` for exact Neon/RVV value semantics;
4. `verification/elementwise-compiler/` for generated manifests, Specs, results,
   witnesses, and content-addressed reviews;
5. `src/workflow/verification/intrinsic_dashboard/` for the artifact-derived UI;
6. `notes/reviews/` and `notes/audits/` for independent verdicts and semantic
   evidence.

## Draft checklist

- [x] Reusable scalar elementwise frontend and generator
- [x] Arbitrary-length fixed/tail/multi-phase/RVV schedule models
- [x] Frozen proof tasks and proof-integrity checks
- [x] 180/180 used exact intrinsic reviews
- [x] 19/19 exact program-outcome reviews
- [x] Checked counterexamples and explicit external-condition blockers
- [x] Artifact-derived dashboard
- [ ] Remove or restore local Lean build-cache changes before marking ready for review
- [ ] Confirm and publish the intended PR base branch
- [ ] Keep grouped layouts, non-elementwise families, and C/ISA bridges as follow-up work
