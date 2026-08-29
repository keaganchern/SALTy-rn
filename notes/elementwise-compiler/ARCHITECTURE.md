# Elementwise Compiler Architecture

Last updated: 2026-08-29 (Asia/Seoul)

## North Star

For a program whose exact typed intrinsics and execution family are already
supported:

```text
C pair -> one command -> generated implementation/specification stack
       -> proof agent -> Lean-checked result -> dashboard update
```

No program-specific Python or Lean source is added.

## Capability Graph

```text
IntrinsicCapability ─┐
                     ├─> ProgramManifest ─> Models ─> Spec ─> ProofTask
FamilyCapability ────┘                                      │
                                                            v
                                                      Agent Proof
                                                            │
                                                            v
                                                      Lean Result
```

The dashboard renders this graph. It does not own a parallel support database.

## Artifact Ownership

| Artifact | Producer | Mutable during proof? | Meaning |
|---|---|---:|---|
| input Neon/RVV C | user/corpus | no | source pair |
| intrinsic capability | framework/reviewer | no | exact typed semantic mapping |
| family capability | framework/reviewer | no | reusable execution recognizer and theorem |
| `ProgramManifest.json` | compiler | no | parsed program and resolved dependencies |
| `Models.lean` | compiler | no | independent implementations and lane functions |
| `Spec.lean` | compiler | no | frozen propositions without proof |
| `ProofTask.json` | compiler | no | hashes, target theorem, writable path |
| `Proof.lean` | proof agent | yes | proof terms and helper lemmas only |
| `Result.json` | checker | no | precise final or failure state |

## Generated Program Manifest

The manifest contains facts derived from the two C bodies:

- source/facade/compiler provenance;
- function identities and typed parameters;
- parsed source assertions;
- buffer/scalar/parameter roles;
- ordered calls and exact intrinsic capability ids;
- value dependencies and independently extracted lane expressions;
- loop guards, count updates, load/store effects, and pointer advances;
- recognized source and target execution families;
- every consumed statement/effect and any rejection reason.

It is the parser's “程序结构清单”, not a handwritten intermediate language.

## Family Interface

A family capability supplies:

1. a fail-closed structural recognizer;
2. generated model construction rules;
3. legality predicates derived from source/program structure;
4. an observation appropriate to the claim layer;
5. reusable Lean refinement theorems;
6. dashboard capability identity and version/hash.

Initial value families:

- fixed width with divisibility and no tail;
- fixed width plus unary short tail;
- fixed width plus synchronized binary short tail;
- ordered multi-phase stream plus final tail;
- RVV positive-partition strip mining.

## Specification Shape

Unary:

```text
NeonLoop = map fNeon
RvvLoop  = map fRvv
forall x, fNeon x = fRvv x
therefore NeonLoop = RvvLoop
```

Binary replaces `map` with `zipWith`. The compiler never creates one shared lane
function before proving the independently generated functions equal.

## Preconditions

The direct specification includes source assertions translated mechanically and
family legality derived from program structure. Missing intrinsic semantics do not
become preconditions. External caller/API restrictions absent from the body are
optional separately evidenced inputs and produce a visibly contextual theorem.

## Result State Machine

```text
discovered
  -> parse-unsupported | parsed
  -> intrinsic-missing/ambiguous | intrinsics-ready
  -> family-unrecognized | generation-ready
  -> generation-failed/stale | proof-ready
  -> proof-search-failed | counterexample | proof-produced
  -> lean-failed | verified(value|c|isa)
```

Every failure records the exact missing dependency or rejected construct. Proof
file presence alone never advances the state.

## Trusted Boundary

At the value layer, acceptance trusts the parser/generator, pinned parse/build
context, exact intrinsic descriptors and Lean definitions, family models and
theorems, proof-policy checker, Lean toolchain/kernel, and standard allowed axioms.
The proof agent is outside the logical trust boundary only because its output is
restricted and checked; repository-local execution is not an OS sandbox.

Intrinsic-to-ISA adequacy, C byte-memory refinement, legal architecture traces,
and compiled-binary correctness are additional bridges, not consequences of the
value proof.

## First Acceptance Test

Delete all S8-VMax-specific generator configuration, retain the C pair and global
max intrinsic capabilities, then run the compiler. It must generate the manifest,
models, spec, proof task, proof result, and dashboard row without framework source
edits. A second same-family synthetic input must pass the same gate to rule out a
hidden name/path special case.
