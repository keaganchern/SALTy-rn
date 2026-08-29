# Elementwise Compiler Decision Ledger

Last updated: 2026-08-29 (Asia/Seoul)

This file is append-only. A later choice must mark the earlier decision
superseded rather than silently editing its meaning.

## EC-001: Reusable Compiler, Not Per-Program Matching

**Status:** Accepted, 2026-08-29.

Once an exact typed intrinsic and an execution family exist, a new same-family
program requires zero new Python or Lean source code. New handwritten work is
allowed only for a genuinely new intrinsic variant or reusable program family.

## EC-002: Dashboard Is the Capability Dependency Graph

**Status:** Accepted, 2026-08-29.

Build the dashboard from the same manifests and capability registry used by the
compiler. Program readiness is derived from intrinsic, family, generation, proof,
Lean-check, and claim-scope dependencies. Do not maintain a second program-status
catalog for the UI.

## EC-003: Generated Specification and Agent Proof Are Separate

**Status:** Accepted, 2026-08-29.

The trusted generation step owns `ProgramManifest.json`, `Models.lean`,
`Spec.lean`, and `ProofTask.json`. The proof agent may create or change only
`Proof.lean`. The checker freezes the generated artifacts and verifies the exact
exported proposition and its transitive axioms.

## EC-004: No Agent-Invented Axioms or Contracts

**Status:** Accepted, 2026-08-29.

The proof agent cannot add an axiom, `sorry`, precondition, observation, or weaker
goal. Proof failure remains failure. A contextual theorem may be generated only
from separately supplied, hash-bound caller/API evidence.

## EC-005: Tail Shape Is a Reusable Family Capability

**Status:** Accepted, 2026-08-29.

Distinguish fixed-no-tail, fixed-plus-tail, compositional multi-phase, and RVV
strip-mine schedules in parser output and dashboard state. Prove each family once,
parameterized by widths, arity, block/tail semantics, and observation. Do not add a
named theorem or emitter branch for each program.

## EC-006: Independent Lane Functions

**Status:** Accepted, 2026-08-29.

Generate `fNeon` and `fRvv` independently from the two intrinsic/dataflow
expressions. Prove their pointwise equality. Never define both complete loops from
one shared lane function before correspondence has been established.

## EC-007: Claim Layers Remain Separate

**Status:** Accepted, 2026-08-29.

Display logical value equality, intrinsic semantic review, complete C-memory
refinement, ISA schedule/state correspondence, and binary/compiler correspondence
as separate cumulative layers. A Lean theorem relative to current definitions does
not silently promote a program to a C or ISA claim.

## EC-008: Integer Value Layer Is the First Production Gate

**Status:** Accepted, 2026-08-29.

First deliver arbitrary-length logical value equality for supported integer
elementwise programs, using source-derived assertions and explicit tail-read
values. Keep physical overread legality, byte-memory/frame proofs, real `vsetvl`
traces, and FP semantics as visible later capabilities.

## EC-009: Fail Closed and Consume the Whole Function

**Status:** Accepted, 2026-08-29.

The parser/recognizer must account for every value-relevant statement, call,
control edge, load/store, and pointer/count update inside the supported grammar.
Unknown or ambiguous constructs stop generation with a precise unsupported reason.

## EC-010: Preserve Reusable Work on a Clean Branch

**Status:** Accepted, 2026-08-29.

Develop on `feat/elementwise-compiler`, based on `1707e5e`. Reuse later intrinsic,
schedule, dashboard, proof-policy, and mutation-test work while replacing the
case-specific authorities. Repository history need not be minimal; the new branch's
working architecture and ownership boundaries must be clean.

## EC-011: Program Failure States Are First-Class

**Status:** Accepted, 2026-08-29.

The result schema distinguishes at least: parse unsupported, intrinsic missing or
ambiguous, family unrecognized, generation stale/failed, proof search failed,
semantic counterexample found, Lean check failed, and verified at a named claim
scope. “Proof file exists” is never a success state.

## EC-012: Logical Element Layout Is Independent of Schedule

**Status:** Accepted, 2026-08-29.

Add a reusable layout/view capability between scalar memory streams and logical
elements. Phase one supports scalar-lane layouts. Planar/grouped/multi-output cases
such as `f32-vcmul` are not covered merely by classifying their operator as binary
and their loop as fixed-tail; they remain layout-unrecognized until a reusable
logical complex view and observation are implemented.

## EC-013: Direct Claims Use Complete Per-Side Assumption Domains

**Status:** Accepted, 2026-08-29.

Generate separate Neon and RVV assumption sets plus family and intrinsic legality.
The direct paired theorem requires their conjunction, not only assertions common to
both files. Treat source `assert` text as an audited source assumption under the
pinned preprocessing policy, not as a model of every runtime assert/NDEBUG mode.
External contextual contracts are separate hash-bound evidence and must establish
the direct domain rather than silently replace it.

## EC-014: Generated Artifacts Form a Content-Addressed Parent Chain

**Status:** Accepted, 2026-08-29.

Use canonical serialization and explicit parent digests from manifest through
models, spec, proof task, proof, and result. Every consumer verifies the full chain.
Paths, module names, timestamps, and file presence are not sufficient bindings.

## EC-015: Proof-Agent Isolation Claim Is Integrity-Scoped

**Status:** Accepted, 2026-08-29.

For phase one, say that acceptance permits only the designated proof artifact to
differ inside a before/after hash-checked protected closure. Do not claim that the
repository-local proof process is technically unable to write other files. Actual
filesystem/process isolation is a later hardening milestone.

## EC-016: Held-Out Tests Must Defeat Name and Path Special Cases

**Status:** Accepted, 2026-08-29.

The first gate uses two positive fixed-no-tail fixtures and one semantic negative,
runs in a clean temporary checkout/output root, randomizes the second fixture's
paths and function/module identities, deletes and regenerates outputs, and leaves
tracked framework files unchanged. The generic path forbids path-based defaults,
case ids, and manually listed proof targets.

## EC-017: Translation Uses Source-Domain Contract Refinement

**Status:** Accepted, 2026-08-29. Supersedes the domain rule in EC-013 while
preserving EC-013 as review history.

Do not prove the primary translation theorem under the conjunction of every Neon
and RVV assertion. For directed Neon-to-RVV correctness, use the Neon entry
contract as the caller domain and prove that it implies the RVV entry contract.
Otherwise a stronger target assertion can silently remove source-valid inputs from
the theorem. Assertions nested under control flow are local proof obligations at
their program point, not function-entry assumptions. Unsupported assertion syntax
fails closed; the proof agent cannot turn it into a new assumption.

## EC-018: Phase One Proves Common-Domain Pair Equivalence

**Status:** Accepted, 2026-08-29. Supersedes EC-017 only as the phase-one default
claim; retains EC-017 as the stronger replacement claim.

For the supplied Neon/RVV program pair, phase one proves equal observations under
the conjunction of their entry contracts. It separately reports the two contract
implications, so a common-domain proof cannot be presented as full RVV replacement
coverage. Assertions nested under control flow remain local proof obligations and
are never added to the entry-contract conjunction.
