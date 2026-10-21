# SaltyRN Decision Ledger

Last updated: 2026-07-14 (Asia/Seoul)

Statuses are `Accepted`, `Proposed`, or `Superseded`. Accepted decisions are the
working defaults until a later dated entry explicitly supersedes them.

## D-001: Proof Claim Ladder

**Status:** Accepted, 2026-07-12.

Keep Lean typechecking, Lean-model equivalence, C-to-Lean correspondence, C-source
observational equivalence, and machine-code correctness as separate claims. The
current project targets C-source observational equivalence; machine code is a later
optional bridge.

## D-002: Integer-First Development

**Status:** Accepted, 2026-07-12.

Defer Float32 denotation and FP kernel proofs. Preserve integer/FP/mask type tags,
exact intrinsic identity, extensible architecture/effect state, byte memory,
observation parameters, and full build provenance. While the integer feature set is
active, every reachable FP type, cast, operation, or contraction fails closed.

## D-003: Three-Part Generated Artifact

**Status:** Accepted, 2026-07-12.

Every supported kernel must produce:

```text
ArtifactEnvelope  build command, hashes, ranges, target/ABI, coverage
KernelIR          typed program, memory effects, intrinsic nodes, schedule
Contract/Observe  valid states, UB boundary, outputs and state projection
```

The emitter generates data, not arbitrary theorem bodies. Lean owns the reviewed
denotation and theorem combinators.

## D-004: Initial Verification Defaults

**Status:** Accepted as working defaults, 2026-07-12.

- Quantify over every legal RVV VLEN/`vl` schedule, rather than only VLEN=128.
- Observe the written output prefix and require a frame property; quotient away
  unobserved architectural status in the first slice.
- Permit disjoint input/output buffers or exact in-place execution, not arbitrary
  partial overlap.
- Initially trust a pinned Clang typed AST, but require fail-closed extraction,
  complete body coverage, deterministic regeneration, and a checked manifest.
- Bind the real translation unit, headers, defines, flags, target triple, ABI, and
  source/dependency hashes. A synthetic facade is not final authority.
- Fix little-endian execution initially and avoid implementation-defined signed
  narrowing through representability preconditions.

## D-005: First Paired Vertical Slice

**Status:** Accepted, 2026-07-12.

Use current-main `s8-vclamp`: both Neon source and RVV target exist. The initial
contract is `batch > 0`, `-128 <= min <= max <= 127`, input readable through
`roundUp(batch, 8)`, output writable through `batch`, and disjoint or exact in-place
buffers. Prove memory safety, termination, exact footprint/frame, refinement of both
sides to signed clamp, and final observational equivalence.

## D-006: Proof-Agent Boundary

**Status:** Accepted, 2026-07-12.

An agent may synthesize theorem bodies and supporting lemmas. It may not weaken or
edit semantic definitions, contracts, observation relations, theorem headers, source
binding, or the allowed-axiom policy merely to make a proof pass.

## D-007: Layered Translation Acceptance

**Status:** Accepted, 2026-07-12.

Keep three checks distinct: an envelope may report complete AST auditing; an emitter
may claim that coverage entries were translated; only a concrete relation against a
reference-shape-checked `KernelIR` may establish structural coverage binding. Translation
references are typed as parameter, operation, or block references and are checked in
both directions. A reviewed operation-descriptor registry, not extractor-supplied
family tags, fixes each supported spelling's architecture, type signature, and RVV
SEW/LMUL shape.
This still does not prove semantic preservation. Registry version/provenance and a
validated lowering bridge are required before the result becomes authoritative.

## D-008: Generated-Spec Trust Boundary

**Status:** Accepted, 2026-07-14.

Automatically generate source/target IR data, checked lowering certificates, and a
fixed observational-equivalence theorem obligation. A generated architecture-neutral
normal form may be used as a proof witness, but not presented as an independent API
specification. Contracts, observations, intrinsic denotations, and allowed axioms
remain reviewed/versioned inputs. Direct source-IR/target-IR equivalence is primary.

## D-009: Supported Mutations Lower to Different IR

**Status:** Accepted, 2026-07-14.

The frontend rejects unknown syntax, types, casts, and calls, but it must not reject a
supported intrinsic mutation merely because it no longer implements the expected
theorem. Such a mutation produces different typed IR; Lean execution/proof must then
fail or expose a counterexample. Answer-shaped extractor validation remains useful only
as an audit oracle, not as the production translator.

## D-010: Positive Progress Is Not ISA Legality

**Status:** Accepted, 2026-07-14.

Call the current RVV quantification a `PositivePartition` or positive progress model.
Do not call every such partition an ISA-legal `vsetvl` trace. A later bridge must fix
VLEN/VLMAX/SEW/LMUL and prove that concrete `vsetvl` execution yields a member of the
verified progress set.

## D-011: Publish the Coq Reduction Slice on `proof/sum`

**Status:** Accepted, 2026-10-02.

Use an isolated `proof/sum` branch from fork main and a normal Coq project at
`coq/neon-rvv-reduction`. Include the complete NEON partial-correctness route,
RVV loads VL=0/1 and the other completed RVV instruction proofs selected by the
owner. Keep every generated program instruction definition and its original
trace, with lossless compression permitted, plus required semantic bridges.
Include the entire proof dependency closure; Coq proof helpers named `Cache` are
sources, not disposable build artifacts. Ignore compiled Coq outputs.

Keep unfinished experiments and the conditional whole-RVV route in the original
research branch. Explicitly state the missing VL=2..8 load contracts and the
external extraction/adequacy boundary. Compile project sources afresh, check
objects recursively and inspect exported assumptions before claiming validation.
Publish the branch and prepare a local PR draft; opening a PR remains a later step.

**Confirmed implementation:** the checked project was published as
`origin/proof/sum@2bbe27e` on 2026-10-02; the PR draft remains local.
