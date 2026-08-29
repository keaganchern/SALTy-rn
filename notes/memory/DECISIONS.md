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

## EC-019: Phase One Requires Equal Entry Contracts

**Status:** Accepted, 2026-08-29. Narrows EC-018 for the initial nineteen-program
scope and removes contract-implication reporting from the first implementation.

Parse both entry contracts into normalized typed expressions and require equality.
The generated theorem uses that shared contract. A mismatch is unsupported rather
than intersected, implied, or treated as a replacement-coverage question. Positive
new-program acceptance fixtures must obey the same rule.

Do not silently erase arbitrary local assertions. The fixed-tail family may consume
and automatically discharge only assertions equal to facts derived from its loop
exit and tail reach condition. Any other local assertion fails recognition in phase
one. This covers all eleven local assertions in the five affected phase-one
elementwise pairs without a per-program profile.

## EC-020: The Production Frontend Has Only Explicit Inputs

**Status:** Accepted and implemented, 2026-08-29.

The production entry point receives the C path, exact function name, architecture,
target triple, and parse-facade path explicitly. It never selects a case, facade,
target, or function from a basename or `source`/`target` directory. Clang binds
every reachable direct call to one unique facade declaration; the compiler then
resolves that typed call against global intrinsic capabilities. The old
profile-based entry point remains a regression adapter and is forbidden from the
held-out acceptance path.

The frontend returns every assertion with its containing control id. A separate
restricted parser translates side-effect-free C conditions into typed normalized
trees. Entry assertions form the side contract; nested assertions remain local
obligations. No handwritten expected-assertion list participates in the production
path.

## EC-021: Ambiguous Intrinsics Use One Information-Preserving Global Rule

**Status:** Accepted and implemented, 2026-08-29.

When several configured exact typed descriptors share a source spelling, argument
types, result type, and architecture, select only by descriptor information: retain
more semantic operands, prefer identity operand transforms, and erase fewer source
constraints. Program name, path, function name, namespace, and former profile
provenance are forbidden inputs. A remaining tie is `intrinsic-ambiguous`.

Capability records bind both the selected descriptor and implementation digests.
This resolves the five existing integer fixtures without pretending the selected
definitions have independent architecture review.

## EC-022: Generated Models and Specifications Are Separate Frozen Parents

**Status:** Accepted and implemented, 2026-08-29.

`Models.lean` contains the independently projected Neon/RVV value models and loop
assembly. `Spec.lean` imports Models and declares proof-free named propositions:
each loop equals its map/zipWith form, the two element functions agree, and the
complete value observations agree. Neither artifact contains proof search output.
The later `ProofTask.json` binds their hashes and designates `Proof.lean` as the
only mutable proof artifact.

## EC-023: Proof Checking Builds an External Temporary Lean Closure

**Status:** Accepted and implemented, 2026-08-29.

Elaborate Models, Spec, the agent proof, and the audit in a temporary Lean module
root. Copy and compile the small checked dependency source closure there rather
than trusting or updating repository `.lake` products. Freeze the checked claim's
elaborated print, exact toolchain identity, checker policy, and parent hashes in
`ProofTask.json` before delegation.

The delegated command receives the task path and acceptance requires every output
file except `Proof.lean` to remain byte-identical. The checker then rejects escape
identifiers, verifies the theorem has exactly the frozen claim type, audits
transitive axioms, compares protected-closure digests, and emits `Result.json`.
This is still an integrity gate rather than OS process isolation.

## EC-024: Corpus and Dashboard Status Come From One Artifact Graph

**Status:** Accepted and implemented, 2026-08-29.

Discover elementwise pairs structurally from paired C sources. Publish one
content-addressed `CorpusReport.json` and one status record per discovered pair.
The dashboard has no program allowlist: it reads that report and verifies each
referenced capability, manifest, generated source, proof task, proof, and result.
A changed or unbound child propagates to `stale-artifact`; file presence cannot
produce `proof-ready` or `verified(value)`.

## EC-025: Scalar-Lane Layout Allows Per-Stream C Types

**Status:** Accepted and implemented, 2026-08-29.

Element-wise means that logical coordinate `i` is independent, not that every
physical stream has the same C element type. Record the C type of each input and
output stream in the layout instance. Conversions such as `float[i] -> uint16[i]`
remain scalar-lane programs. Physical grouping such as planar complex values is a
different layout capability.

## EC-026: Multi-Phase Is One Parameterized Schedule With Structural Encodings

**Status:** Accepted and implemented, 2026-08-29.

Represent large width, small width, and final prefix stores as schedule parameters.
Both separate fixed loops (64/8/4/2/1) and a nested do-while small phase
(16/8/4/2/1) instantiate the same unary/binary `runTwoPhaseTail` family. The
frontend may have separate structural grammar alternatives for the two C control
encodings, but selection cannot use a program id, path, function name, or Lean
namespace.

## EC-027: Supported Semantic Changes Regenerate Models

**Status:** Accepted and implemented, 2026-08-29.

Reject control, pointer, lane-store, immediate, or dependency changes that violate
the recognized family. When a changed intrinsic is still registered and remains
well typed in the same dataflow, generate the changed model instead of comparing
the body with a remembered program template. The resulting equivalence proof must
then succeed, fail, or produce a checked counterexample against the regenerated
claim. This rule enabled removal of the fixed `s8-vclamp` call-number table.

## EC-028: Separate Skeleton Completion From Corpus Proof Completion

**Status:** Accepted after independent final audit, 2026-08-29.

Report the current result as a reusable 8-bit elementwise compiler skeleton, not
as a completed nineteen-program proof pipeline. The five generated programs have
Manifest/Models/proof-free Spec only; fourteen scalar programs remain blocked and
independent intrinsic review is zero.

Do not describe all fourteen scalar blockers as intrinsic-only until the reusable
emitter is generalized beyond 8-bit input/output streams and the exact 8-lane
load plus 4/2/1 prefix-tail shape. Treat the new artifact-driven
`/api/elementwise` graph and the legacy case-driven `/api/state` graph as distinct
until the latter is migrated or retired.

## EC-029: False Generated Obligations Need an Explanatory Terminal Result

**Status:** Accepted after concrete `s8-vclamp` review, 2026-08-29.

A proof-free generated Spec is a candidate obligation, not an accepted theorem.
It may therefore be false without making the checker unsound. However, when two
parsed phases do not implement the same scalar function under the bound entry
contract, the pipeline must not present the program as merely waiting for proof.
It must emit a checked counterexample or an explicit family/contract failure.

For `s8-vclamp`, `min <= max` may be added only through the separately evidenced,
hash-bound external-contract path. The confirmed evidence is XNNPACK's output
range validation followed by its registered S8 clamp parameter initializer; the
local harness is only a test instance, not general evidence. The proof agent may
not invent the condition. The direct claim under the isolated source assertions
remains false and must stay visible.

## EC-030: External Parameter Conditions Are a Reusable Capability Gap

**Status:** Accepted after twenty-program audit, 2026-08-29.

Eight of the twenty elementwise programs consume quantized parameter structs whose
legal ranges or relations are established outside the isolated kernel body. This
is too frequent to classify as one `s8-vclamp` exception. Until a generic,
content-addressed validation/initializer evidence path exists, show an explicit
unchecked-external-input state and do not call these programs proof ready.

Do not build per-program condition tables into the new compiler. The later generic
mechanism should follow the selected XNNPACK parameter initializer and its upstream
validation evidence. The old handwritten `PARAM_CONSTRAINTS` may be used for
diagnostic comparison only, not as trusted proof input.

## EC-031: Nineteen Reviewed Programs and Milestone Commit Discipline

**Status:** Accepted as the next delivery proposal, 2026-08-29.

Target all nineteen scalar-layout programs with separate hash-bound intrinsic and
program review records. An intrinsic review is performed once per exact semantic
definition and automatically benefits every dependent program. A program review
binds the entire generated/proved artifact closure. Reviewer agents may emit
review records but may not modify the artifacts they review.

Do not promise all nineteen will verify before the reusable width, external-input,
and cross-phase checks have run; counterexamples must remain visible. Fold existing
and future memory-only commits into their corresponding implementation milestones.
The next delivery series should use no more than roughly eight large semantic
commits; this limit does not require compressing all work already completed into
four commits.

## EC-032: Widths, Tail Schedules, and RVV Counts Are Typed Program Facts

**Status:** Accepted and implemented, 2026-08-29.

Carry input width, output width, C element type, RVV count variable, fixed block
width, and tail-store widths from parsed program facts into generated Models and
Spec. The generic value layer supports 8-, 16-, and 32-bit streams, including
distinct input/output widths. A prefix tail is accepted only when its descending
power-of-two stores cover every non-full live length.

When RVV uses a separate element count, bind it to the logical list length only
after verifying the exact top-level definition `count = batch / sizeof(T)` and
that `T` matches the parsed Neon byte-count element type. A wrong divisor must
fail closed. Floating-point streams are represented as same-width bit vectors at
this layer; their arithmetic meaning still comes from independently reviewed
intrinsic definitions.

For a multi-phase Neon schedule, project each parsed phase to its own scalar
function. Generate phase-to-map claims separately and expose equality between the
phase functions as an explicit proof obligation. Never define the secondary phase
through the primary scalar function before that equality has been established.

## EC-033: File Co-Occurrence Is Not External-Condition Evidence

**Status:** Accepted and implemented, 2026-08-29. Supersedes the evidence claim
in EC-029 that XNNPACK output-range validation is confirmed on the S8 unary clamp
call path; EC-029's requirement to keep the direct false claim visible remains in
force.

An external condition is `resolved` only when the exact caller/initializer path
that establishes it is hash-bound and checked. Finding a suitable validator and a
parameter initializer in the same upstream repository is insufficient. At pinned
XNNPACK commit `867d5a344790802ee067be62f572c2e2722bf6fb`, the audited unary clamp
path does not call `xnn_subgraph_check_output_min_max`. Signed
`params.min <= params.max` therefore remains a candidate, and `s8-vclamp` remains
`required-missing` even though that candidate repairs the generated theorem.

`ExternalCondition.json` binds the local source pair, explicit registration,
shared Neon/RVV initializer, upstream commit, extractor, and consulted file
hashes. The proof gate may select a contextual claim only for `resolved` evidence;
it rejects `required-missing` before proof delegation.

## EC-034: Counterexample Search Is Checked but Bounded

**Status:** Accepted and implemented, 2026-08-29.

For a multi-phase generated model, a found scalar-function disagreement must be
reified in `Counterexample.lean`, checked by Lean, and bound to Manifest, Models,
Spec, checker, and toolchain hashes in `Counterexample.json`. A bounded search
that finds no witness is not a proof of equality. When the relevant external
condition is already missing and has no expressible candidate, report that
missing-condition blocker instead of treating a large unconstrained search
timeout as generation failure.

## EC-035: Audit Absence Is Never an Accepted Audit Result

**Status:** Accepted and implemented, 2026-08-29.

Every generated stack must bind both `ExternalCondition.json` and
`CrossPhaseAudit.json`. Omitting XNNPACK caller information selects an explicit
standalone scope whose generated proposition quantifies over all modeled
parameters; it does not silently map absence to `not-required`. XNNPACK corpus
runs must continue to use the registered-domain audit and may not fall back to the
standalone scope when registration discovery fails.

The cross-phase audit runs from the generic compiler path. It records
non-applicability, a missing external domain, a bounded search with no witness, or
a Lean-checked counterexample. A bounded miss remains only a diagnostic. A bound
counterexample is terminal and `prepare_proof_task` must reject it even if some
other condition is also missing.

## EC-036: Elementwise Status Has One Artifact Authority

**Status:** Accepted and implemented, 2026-08-29.

`/api/elementwise` derives program discovery, readiness, failure, and verification
only from the structural corpus report and verified content-addressed artifact
closure. It must not import legacy supported/proof/generated case lists. A new
program becomes visible after generic compilation and report publication without
adding dashboard configuration.

The page must expose the complete M/E/D/S/A/C/T/R chain, input-condition scope and
status, cross-phase status and trial count, concrete counterexample witness, and
separate value/C/ISA claim layers. The old `/api/state` table may remain for
non-elementwise and historical records only when it is visibly labeled
non-authoritative for the elementwise compiler.

## EC-037: Intrinsic Review Is Exact, Content-Addressed, and Fail-Closed

**Status:** Accepted and implemented for batch 1, 2026-08-29.

An intrinsic is displayed as independently reviewed only when one strict record
binds its architecture, spelling, Clang function type, arity, descriptor hash,
actual lowering implementation hash, pinned primary-source evidence, executable
check output, policy, and reviewer. The generated global registry publishes every
typed variant and embeds matching records; the dashboard rejects any changed or
misbound child instead of inferring review from a filename.

Structural implementation hashes include both the generic Lean emitter and the
context-specific case emitter. This is deliberately conservative: a lowering
change invalidates approval rather than allowing a stale green puzzle piece.
Legal immediate sets come from primary evidence and may not be narrowed merely to
make a review pass. The `vst1_lane_f32` lane-1 counterexample is now a permanent
positive/negative regression.

## EC-038: Spelling Counts Are Not Exact Review Units

**Status:** Accepted and implemented after M5 independent review, 2026-08-29.

Architecture plus spelling is useful for showing missing C intrinsic names, but it
is not an approval identity. The same spelling and Clang function type may have
multiple exact typed descriptors. `IntrinsicCapability.capability_id` and
`IntrinsicReview.review_id` therefore bind the descriptor digest in addition to
architecture, spelling, type, and arity. Implementation changes retain the exact
descriptor identity but invalidate the capability content hash and review binding.

The elementwise dashboard reports spelling dependencies and exact variants as
separate quantities. For the current corpus these are 178 configured spellings of
186 dependencies, 189 exact configured variants, and 180 exact variants used by
the nineteen scalar programs. Review and Lean-check progress is counted per exact
variant; a spelling-level aggregate cannot satisfy an exact review gate.

## EC-039: Exact Review Subjects Bind Official Prototypes and Explicit Scope

**Status:** Accepted and implemented, 2026-08-29.

An exact intrinsic review subject is stable across corpus usage and review
publication, but changes when its descriptor, transitive implementation closure,
official prototype, immediate constraints, value-claim scope, or architecture
conditions change. Usage/program lists are reporting metadata and do not enter the
stable audit-subject digest; this avoids a circular review/capability identity.

Neon exact signatures bind the pinned Arm ACLE database. RVV exact signatures
bind the pinned generated `intrinsic_funcs.adoc` prototype by complete return and
parameter types; official API-test calls and ISA selectors remain additional
evidence. Call arity alone is insufficient for an `exact_source_signature` pass.

## EC-040: Scoped Reviews Require Their Audit Parents

**Status:** Accepted and implemented, 2026-08-29.

Schema-v2 intrinsic reviews bind `audit_variant_sha256`, claim scope, and sorted
architecture conditions. The production graph must reject these reviews when
`IntrinsicAudit.json` or `IntrinsicReviewPlan.json` is missing, changed, or does
not cover every used exact subject. The internal audit-bootstrap projection may
omit these parents only while hiding all review state.

Review execution output is content-addressed. Refresh it through a staged file:
run checks while the previous evidence remains valid, atomically install the new
passing output, then immediately republish reviews. Tests must never pass by
temporarily ignoring stale review bindings.
