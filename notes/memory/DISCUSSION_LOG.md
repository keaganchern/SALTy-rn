# Elementwise Compiler Discussion Log

Append-only. Dates use Asia/Seoul.

## 2026-08-29 — Branch reset around the reusable compiler goal

**Question:** Does the existing five-case backend meet the intended automation
goal, and what must be stable before building the new branch?

**Conclusion:** it does not meet the goal because frontend profiles, intrinsic
catalog subsets, model profiles, emitter branches, and proof targets remain
program-specific. Preserve their reusable parsers, typed descriptors, Lean
intrinsic semantics, schedule theorems, dashboard implementation, proof policy, and
tests, but replace the case-scoped authorities.

The branch is `feat/elementwise-compiler`, based on `1707e5e`. Its first prototype
commit `986acd4` validates the desired S8 VMax proof shape and generated/agent file
separation, but manually stages the new loop and specification. The active
acceptance test is to reproduce that result with zero framework source changes.

**Evidence:** current source inspection, the 40/36-pair structural audit, dashboard
snapshot, current global intrinsic index, and successful Lean build of
`SALT.Example.S8VMaxV2.Audit`.

**Unresolved:** implement capability/result schemas, generic typed assertion and
program extraction, fixed-no-tail emission, proof orchestration, and dashboard
dependency closure before migrating fixed-tail and multi-phase cases.

## 2026-08-29 — Memory and planning audit

**Question:** Is the memory/planning system ready to drive the whole new branch?

**Conclusion:** no. The latest discussion existed only in an outer untracked notes
tree; the new branch had no memory directory. The outer current-state file had
grown to 396 lines and the active plan mixed current work with a long historical
checklist. Create a concise branch-local system with strict file responsibilities,
an append-only decision ledger, milestone exit gates, and a stable architecture
document. Let generated manifests/dashboard own live coverage counts to avoid
drift between prose and code.

**Evidence:** filesystem and line-count audit on `feat/elementwise-compiler`.

**Unresolved:** enforce the update protocol during each substantive implementation
turn and keep `PROJECT_STATE.md` below its size target.

## 2026-08-29 — Independent architecture review, rounds 1 and 2

**Question:** Is the plan safe to implement, and what hidden gaps remain?

**Reviewer verdict:** `GO WITH REQUIRED REVISIONS`. The checked S8 proof shape and
generic schedule theorem justify implementation, but the first code commit should
wait for one design-correction pass.

Round 1 confirmed five blocking implementation gaps: old case-scoped authorities,
an unrealized generated-artifact stack, handwritten assertion comparison, missing
terminal failure/counterexample states, and a dashboard still driven by
`supported_cases`/hardcoded proof targets.

Round 2 identified additional gaps not explicit in the first plan:

- operator arity plus schedule is insufficient for planar complex `f32-vcmul`; a
  reusable logical element layout/view capability is separate;
- direct paired claims require complete separate Neon/RVV assumption sets plus
  family/intrinsic legality; source assert extraction is not general runtime-assert
  semantics;
- “agent can write only Proof” must be stated as before/after protected-closure
  integrity checking unless a real sandbox exists;
- manifest, models, spec, proof task, proof, and result need canonical parent-hash
  edges;
- build a thin fixed-no-tail end-to-end slice before broad dashboard migration;
- the held-out gate needs two positives, randomized names/paths for the second,
  semantic/structural negatives, clean temporary execution, deterministic rerun,
  and zero tracked framework changes.

**Resolution:** accepted these as EC-012 through EC-016 and revised architecture
and milestones before implementation. The new order is minimal schemas, thin
fixed-no-tail generation, proof/result integrity, honest held-out gate, then
dashboard migration.

**Convergence:** after reading the revised documents, the same reviewer returned
`GO`. It confirmed every must-fix-before-code item was incorporated and found no
remaining document defect severe enough to block M1a. Five nonblocking wording
amendments were applied before committing the review baseline.

**Unresolved:** begin M1a and enforce its schema/hash exit gates before implementing
the generic frontend.

## 2026-08-29 — Concrete assertion audit and contract correction

**Question:** Is taking all Neon and RVV assertions as a conjunction correct, and
what exactly should the held-out gate test?

**Conclusion:** no. Shared assertions are insufficient, but conjoining every
assertion also hides a target that is stricter than the source. Directed
translation must use the Neon entry contract as its domain and prove it implies
the RVV entry contract. Assertions nested under a branch or loop are local proof
obligations using the current symbolic state and reach condition. This supersedes
the domain formula in EC-013 through EC-017.

The first acceptance gate is a compiler/framework generalization test, not another
semantic axiom and not a per-program proof substitute. At least one unseen
same-family positive and one semantic/structural negative are necessary evidence
for the claimed zero-framework-edit automation. Name/path randomization is a cheap
regression check against the current case-scoped architecture, not part of the
trusted computing base.

**Evidence:** `examples/s8-vmax-to-lean` has a Neon-only `batch % 16 == 0` entry
assertion; dropping it admits inputs for which the fixed-no-tail Neon loop and RVV
loop differ. `kernels/source/f32-f16-vcvt.c` has bounds on the reduced `batch`
inside its tail branch; treating those as entry assumptions incorrectly excludes
larger valid inputs. A target-only stronger divisibility assertion demonstrates
why taking the union/intersection of both sides can hide a translation-domain gap.

**Unresolved:** implement the supported assertion-expression grammar, implication
checking, and local path-obligation generation in M1a/M1b.

## 2026-08-29 — Common-domain claim and corpus layout/assert counts

**Question:** Is the intended theorem equality only where both supplied programs
are valid, how common are grouped elements, and what do inline assertions mean?

**Conclusion:** the user confirmed the phase-one goal is paired-program equivalence
on the intersection of entry contracts. Adopt that as the default while reporting
contract implications separately; retain source-domain refinement as an optional
stronger replacement claim. Local assertions are proved at their program point and
never intersected into the entry domain.

Of twenty audited elementwise pairs, nineteen use ordinary same-index scalar
streams, one (`f32-vcmul`) uses planar complex grouping, and none uses an
overlapping adjacent-index window. Five elementwise Neon files have eleven
tail-local remainder assertions; all twenty pairs' entry assertions match, and the
corresponding RVV files have no local assertions.

**Evidence:** direct classification of all twenty source/target C pairs at commit
`3dc22b2`; the tail assertions in `f32-f16-vcvt`, `qs8-f32-vcvt`, `qs8-vcvt`,
`qs8-vlrelu`, and `qu8-f32-vcvt`; the planar pointer derivations in `f32-vcmul`.

**Unresolved:** expose common-domain, Neon-implies-RVV, and RVV-implies-Neon as
separate generated/result fields and dashboard states.

## 2026-08-29 — Equal-entry phase-one rule and full local-assert audit

**Question:** Can phase one require normal pairs with equal entry assertions and
simply ignore assertions inside the function?

**Conclusion:** require normalized entry-contract equality and drop contract
implication/replacement reporting from phase one. The held-out positive fixtures
must satisfy the same rule. Do not ignore arbitrary local assertions. The fixed-tail
recognizer can automatically discharge the eleven remainder assertions in the five
affected phase-one programs because they follow immediately from the loop exit and
nonzero tail condition; every other local assertion fails recognition.

Across the full paired corpus, fourteen program names contain local assertions.
Twelve contain only assignment/control-derived invariants. Two non-elementwise
programs, `f32-dwconv-minmax` and `f32-igemm-minmax`, check caller-supplied pointer
table entries and therefore contain real data-dependent constraints.

**Evidence:** one-by-one audit recorded in
`notes/elementwise-compiler/ASSERT_AUDIT.md`.

**Unresolved:** the existing synthetic S8 VMax fixture has mismatched entry
assertions and must be normalized or replaced before it can serve as a positive
phase-one acceptance fixture.

## 2026-08-29 — Reviewer convergence on the nineteen-program scope

**Question:** After excluding `f32-vcmul` and narrowing assertion handling, can
implementation start without another design pass?

**Reviewer verdict:** `GO`. No hidden layout or claim gap blocks M1a. All eleven
local assertions in the five affected elementwise files belong to one reusable
fixed-tail fact family. The one implementation caution is to derive preserved
element-size divisibility/alignment as well as range bounds.

**Remaining coverage gates:** three multi-phase programs (`f32-f16-vcvt`,
`qs8-vadd-minmax`, `s8-vclamp`) and reviewed FP/broader intrinsic semantics. These
block claiming all nineteen complete, but do not block starting the framework.

**Evidence:** fourth review pass over commit `345a3bd`, the nineteen C pairs, and
`notes/elementwise-compiler/ASSERT_AUDIT.md`.

## 2026-08-29 — Implementation stage 1: schemas, explicit parsing, and contracts

**Question:** Can the first compiler layer be implemented without adding another
program profile, while retaining exact typed calls and distinguishing entry from
local assertions?

**Conclusion:** yes. The new elementwise package now owns strict canonical schemas
for capabilities, contracts, manifests, generated artifacts, proof tasks, and
results. A new explicit Clang entry point derives the function signature and every
reachable direct-call parse contract from the supplied C/facade pair. It returns
assertions instead of comparing them with a handwritten table. A restricted typed
parser accepts the audited pure assertion grammar and rejects calls, assignment,
subscripts, and increment/decrement.

All five existing integer pairs parse through this explicit path without their
named frontend profiles and produce equal normalized entry contracts. The
`qs8-vcvt` tail bounds are retained as two local facts under the same tail-control
node. The old profile entry point still passes its regression tests.

**Evidence:** 48 focused tests under
`tests/verification/elementwise_compiler` and
`tests/verification/lean_backend/test_frontend.py`.

**Unresolved:** global intrinsic resolution currently exposes several exact typed
spellings with multiple configured lowering descriptors. Stage 2 must either bind
one reviewed program-independent capability or return `intrinsic-ambiguous`; it
must not choose by former case provenance.

## 2026-08-29 — Implementation stage 2: generic manifest and Models/Spec generation

**Question:** Can real unary, binary, tail, and no-tail pairs be generated without
selecting a named program profile, and can the specification remain separate from
the proof?

**Conclusion:** yes for the current 8-bit scalar-layout slice. The explicit
compiler now resolves exact intrinsics with one global information-preserving rule,
recognizes scalar stream layout plus fixed/RVV schedules, verifies all parsed
calls/control/assert/effects are consumed, and emits a canonical manifest,
capabilities, independent Models, proof-free Spec, and artifact index. The same
path generated `qs8-vcvt`, `qu8-vadd-minmax`, and a normalized synthetic `s8-vmax`.
Their generated Lean Models and Specs elaborate. Deleting and regenerating output
is byte deterministic.

The remaining legacy S8 multiphase emitter selection was changed from a program-id
test to structural `multiphase_widths`; the production compiler itself accepts no
case id. This is groundwork, not yet proof that all nineteen programs compile.

**Evidence:** 129 focused Python regressions; Lean builds of
`SALT.Kernel.ElementwiseLayout`, the generated unary/binary/no-tail smoke modules,
and `SALT.Example.S8VMax.Audit`.

**Unresolved:** build and validate ProofTask/Result; run held-out and mutation
gates; batch-classify all nineteen; add general multi-phase recognition and missing
integer/FP semantics; drive the dashboard from the artifact graph.

## 2026-08-29 — Implementation stage 3: frozen proof task and held-out gate

**Question:** Does the generic stack remain fixed while an agent writes only the
proof, and does it reject program identity tricks and semantic/structural changes?

**Conclusion:** yes for the fixed-no-tail S8 VMax vertical slice. The checker
elaborates the generated Models and proof-free Spec before writing a hash-bound
ProofTask. An external command may create `Proof.lean`; every other output artifact
is protected by before/after hashes. Lean then checks the exact named theorem,
forbidden-token policy, and transitive axioms before `verified(value)` is emitted.

The held-out runner generated two positive C pairs without framework edits. The
second used new randomized paths, basenames, function names, and namespace, and
remained byte-deterministic after deleting its output. Replacing Neon max by min
made the same proof fail. Mutating the pointer step, loop decrement, entry
assertion, or RVV active `vl` was rejected before a valid stack was produced.

**Evidence:** four proof/held-out tests, including an actual delegated proof command
and Lean checking; the gate snapshots every tracked file before and after.

**Unresolved:** batch visibility for all nineteen programs, structural two-phase
recognition, artifact-graph dashboard integration, and missing reviewed semantics.

## 2026-08-29 — Elementwise infrastructure completion

**Question:** Can the branch implement the full reusable elementwise workflow,
including the nineteen-program batch, both audited tail encodings, proof integrity,
held-out onboarding, and the puzzle dashboard, without adding per-program compiler
or UI entries?

**Conclusion:** yes for the compiler infrastructure and current value-semantics
capabilities. Structural discovery reports twenty elementwise pairs, nineteen with
scalar-lane layout. Five integer pairs pass the typed compiler and generate
Manifest, Models, and proof-free Spec. Fourteen scalar pairs stop explicitly at
`intrinsic-missing`; grouped `f32-vcmul` stops at `layout-unrecognized`. No scalar
pair stops at parser, contract, schedule-family, or generator failure.

The schedule library now has unary and binary two-phase theorems. The recognizer
and generator cover separate 64/8/4/2/1 loops and nested 16/8/4/2/1 do-while code.
The `qs8-vadd-minmax` generated Models/Spec were elaborated by Lean and a frozen
ProofTask was produced. Scalar layout records now preserve per-stream types.

The dashboard reads the content-addressed corpus graph and separates value, C, and
ISA states. It derives `spec-generated`, `proof-ready`, terminal proof failure,
and `verified(value)` only from validated parents; mutation tests confirm stale
propagation. The randomized held-out S8 VMax path still demonstrates zero
framework edits and an actual agent-written, Lean-checked proof.

**Evidence:** commits `891f559`, `156e1b6`, and `bddaadf`; checked-in
`verification/elementwise-compiler/CorpusReport.json`; 99 elementwise/dashboard
tests; 55 legacy case-emitter/model-profile regressions; successful Lean
elaboration of the generated nested two-phase ProofTask.

**Unresolved:** independent semantic review is still zero. Fourteen scalar
programs need exact typed integer/FP intrinsic capability work, and `f32-vcmul`
needs a grouped complex layout. Value results do not establish C, ISA, or binary
correctness.

## 2026-08-29 — Final structural cleanup and cache-independent proof audit

**Question:** Does the completed infrastructure still hide a per-program adapter,
and can its proof checks be reproduced without trusting the repository's Lean
cache?

**Conclusion:** the separate 64/8 loop path was rewritten to derive calls, value
dependencies, pointer versions, block widths, and 4/2/1 stores from the extracted
control/dataflow graph. The fixed `s8-vclamp` call ids, exact body table, and named
emitter were removed. Registered semantic changes now regenerate the model, while
invalid slides, lane immediates, pointer/count updates, and control changes still
fail closed. Both supported two-phase C encodings instantiate the same
parameterized Lean schedule.

The legacy proof-policy checker now copies the Lean source tree without `.lake`,
builds it in a temporary directory, and audits there. The generated separate-loop
Models/Spec also produced a frozen ProofTask in a temporary Lean root.

**Evidence:** 171 focused compiler/dashboard/legacy-emitter tests and 379 passing
tests in the complete repository suite; a clean corpus
refresh with five `spec-generated`, fourteen `intrinsic-missing`, one
`layout-unrecognized`, and zero stale artifact nodes; fresh-build proof-policy
audit; generated `SALT.Generated.GenericSeparateTwoPhase` ProofTask.

**Unresolved:** capability expansion and independent semantic review remain the
next milestone; this entry closes the compiler-infrastructure milestone only.

## 2026-08-29 — Independent final implementation audit

**Question:** Does HEAD `a77933b` fully match the original elementwise-compiler
plan, and can the current status be called a finished framework or nineteen
completed proofs?

**Conclusion:** the independent reviewer returned `GO WITH GAPS` for the framework
and `NO-GO` for nineteen completed proofs. It reran 57 focused tests, reproduced
the 20 discovered / 19 scalar / 1 grouped and 5 Spec / 14 intrinsic-missing / 1
layout counts, and confirmed that the new compiler and `/api/elementwise` graph do
not use a program allowlist. It also manually fed a randomized held-out artifact
report to the graph and observed `verified(value)` without dashboard configuration.

The audit found three previously understated gaps. First, the current block
emitter supports only 8-bit input/output streams and the prefix-tail emitter is
fixed to an 8-lane load with 4/2/1 stores, so adding intrinsics alone is not yet
shown sufficient for all nineteen scalar programs. Second, legacy `/api/state`
still depends on `PROOF_CASES`, `GENERATED_CASES`, and older profile/catalog data.
Third, `counterexample` is defined as a terminal status but has no producer. The
held-out dashboard capability also needs a checked-in regression.

**Evidence:** reviewer inspection of `emit.py`, `model_profiles.py`,
`intrinsic_dashboard/state.py`, `targets.py`, `freshness.py`, and
`elementwise_graph.py`; 57 focused tests passed in 78.37 seconds; temporary corpus
and held-out graph runs.

**Unresolved:** generalize width/tail emission, migrate or retire the legacy graph,
add the held-out dashboard regression and counterexample path, then expand and
independently review intrinsic capabilities before generating proofs for all
nineteen scalar programs.

## 2026-08-29 — `s8-vclamp` exposes a real contract/counterexample gap

**Question:** Is the generated two-phase `s8-vclamp` Spec actually true under the
entry assertions extracted from C?

**Conclusion:** no. The 64-byte Neon block executes max-with-min then min-with-max;
the 8-byte and tail blocks execute the reverse. With signed `x = 0`, `min = 10`,
and `max = 5`, they return 5 and 10. The entry assertions contain no
`min <= max`, so the generated secondary-block and whole-loop single-`fNeon`
obligations are false. The independent reviewer confirmed the source and generated
model paths preserve this difference.

This has not produced an unsound proof: `Spec.lean` is proof-free and the program
status is only `spec-generated`. It does show that the absent counterexample
producer and external-contract path are required for an intelligible end-to-end
result. An agent proof may not add `min <= max`; that condition needs independent
evidence and hash binding, otherwise the direct claim must fail with the concrete
counterexample.

**Evidence:** `kernels/source/s8-vclamp.c:16-20,24-38,45-57`;
`verification/elementwise-compiler/programs/s8-vclamp/Models.lean:30-79,109-111`;
`Spec.lean:15-19,27-31`.

**Follow-up evidence:** full XNNPACK does supply the intended caller/API condition.
`xnn_subgraph_check_output_min_max` rejects `output_min > output_max`; the
S8-vclamp registration selects `xnn_init_qs8_clamp_scalar_params`, which quantizes
those clamp bounds into the microkernel's scalar min/max fields. The older direct
`xnn_init_s8_minmax_scalar_params` additionally asserts strict
`output_min < output_max`. In this repository, the harness only instantiates one
valid pair (`-100`, `100`) and is not a universal contract.

**Unresolved:** implement the counterexample result producer and the
content-addressed external-contract bridge from upstream validation/initialization
evidence to the generated signed parameter relation.

## 2026-08-29 — Frequency of missing external parameter conditions

**Question:** Is the missing caller/initializer condition seen in `s8-vclamp` rare
enough to defer entirely?

**Conclusion:** no. An audit of all twenty elementwise pairs found eight quantized
parameter programs whose intended XNNPACK parameter ranges or relations are
constructed or checked outside the isolated kernel entry assertions. Eleven
programs have no semantic parameter fields, and `f32-vlrelu` has one copied slope
without a comparable hidden relation found. The detailed classification is in
`notes/elementwise-compiler/EXTERNAL_INPUT_AUDIT.md`.

The practical decision is not to implement whole-XNNPACK interprocedural analysis
immediately, but also not to ignore the issue. The dashboard/compiler must first
surface an unchecked-external-input state for these eight programs. A later
reusable evidence extractor should follow XNNPACK validation and registered
microparameter initializer paths without per-program compiler branches.

**Evidence:** current corpus C and report; XNNPACK `tensor.c`,
`subgraph/validation.c`, `microparams-init.c`, and kernel `.inc` registrations;
legacy `param_configs.py` as non-trusted corroboration.

**Unresolved:** implement the status and generic external-contract artifact;
independently prove the initializer-to-generated-parameter relations used by each
program family.

## 2026-08-29 — Proposal for nineteen reviewed deliveries

**Question:** Is the branch ready to finish the nineteen scalar-layout programs by
completing intrinsic puzzle pieces, with independent intrinsic and program review,
and can its commit history stay below eight commits?

**Conclusion:** an independent reviewer returned `GO WITH GAPS`. The delivery plan
is practical, but the branch is not yet in an all-program intrinsic-only phase.
Reusable width/tail generation, external input evidence, cross-phase scalar-action
checking/counterexamples, and dashboard authority must be closed first. After
that, exact intrinsic definitions can be added and reviewed once per semantic
piece, followed by Lean-checked proofs and separate program review records.

The reviewer agreed that nineteen scalar-layout programs are a reasonable target
but that their successful proofs cannot be guaranteed before those gates expose
any further semantic mismatch. Memory-only commits will be folded into the code
milestones they document. The next delivery series, rather than the entire branch
history, should stay within roughly eight large commits.

**Unresolved:** user approval to begin the staged implementation and history
cleanup; actual intrinsic semantic review remains zero.

## 2026-08-29 — Width and tail generalization milestone

**Question:** Can the compiler remove its 8-bit and exact 8-lane/4-2-1 limits
without adding any program-specific adapter?

**Conclusion:** yes for the scalar value layer. The profile and generator now
carry distinct 8/16/32 input and output widths; prefix tails derive their complete
power-of-two store schedule; and both audited tail-storage encodings are checked
structurally. Float32 facade types are explicit typed descriptors rather than
being misclassified as integers. RVV byte-to-element conversion is accepted only
when its parsed divisor matches the stream C type.

**Evidence:** held-out U16 and U32 fixed-tail copy pairs, an F32 fixed-tail copy,
and a U16 fixed-no-tail pair all generate Manifest/Models/Spec/ProofTask and
elaborate in Lean. A mutated U16 RVV divisor using `sizeof(uint32_t)` fails closed.
The full repository suite passes 393 tests.

**Unresolved:** this milestone does not add the corpus's missing intrinsic
semantics, external caller-condition evidence, cross-phase counterexample
producer, or independent review records. Those are the next gates.

**Independent review:** the first review found two blockers: wide RVV code could
use byte-count `batch` directly, and multi-phase Spec silently reused the primary
scalar function for its secondary block. Both were fixed with permanent negative
and generation tests. A second read-only review returned `GO` after 38 passing
focused tests and temporary generation of both multi-phase corpus shapes. The
phase-equality proposition remains deliberately unproved for the next milestone.

## 2026-08-29 — External-condition audit and checked counterexample milestone

**Question:** Can the framework automatically distinguish kernel-entry asserts
from facts established outside the isolated C pair, and can it explain a false
multi-phase claim without letting the proof agent add an assumption?

**Conclusion:** yes for detection, provenance, refusal, and concrete
counterexamples; no current external condition is promoted to resolved. A generic
same-stem registration discovery finds one XNNPACK `.inc` candidate without a
program allowlist. The compiler verifies the pinned XNNPACK gitlink, requires one
common Neon/RVV parameter initializer, records every consulted file and hash in
`ExternalCondition.json`, and reproduces that extraction in the proof gate. The
twenty-program audit yields twelve `not-required` and eight
`required-missing`. The proof gate refuses to create a ProofTask for the latter.

The earlier claim that XNNPACK's output-range validator established S8 clamp
ordering was corrected. The function exists, but the pinned unary clamp path does
not call it. The generated signed `min <= max` predicate is therefore labeled a
candidate only. The unconditional claim remains visible.

The multi-phase diagnostic found `s8-vclamp` parameters `min = 5`, `max = 0` and
input `0`. Generated `fNeon` returns `0`; `fNeonSecondary` returns `5`.
`Counterexample.lean` checks both evaluations and their inequality with Lean;
`Counterexample.json` binds the Manifest, Models, Spec, checker, witness, and
toolchain hashes. The checked-in corpus now reports one `counterexample`, four
`external-condition-missing`, fourteen `intrinsic-missing`, and one deferred
grouped layout. A missing condition with no candidate blocks cross-phase search
instead of turning a bounded-search timeout into generation failure.

**Evidence:** pinned XNNPACK commit
`867d5a344790802ee067be62f572c2e2722bf6fb`; generated
`verification/elementwise-compiler/programs/s8-vclamp/ExternalCondition.json`,
`Counterexample.lean`, and `Counterexample.json`; focused schema/compiler/proof/
external-condition tests; deterministic corpus regeneration.

**Unresolved:** the eight quantized parameter families still need reusable,
checked initializer/caller postconditions before contextual proof tasks can be
created. The next framework milestone is the single dashboard/artifact authority.

## 2026-08-29 — M2 fail-open closure and convergence review

**Question:** Do external-condition and multi-phase checks remain mandatory when
the generic compiler is called outside the corpus runner, and does a checked
counterexample actually stop proof delegation?

**Conclusion:** yes after three required revisions. The first independent review
returned `NO-GO`: the external audit request was optional, a checked witness did
not block `prepare_proof_task`, and cross-phase search was chosen only by the
corpus driver. The compiler now always emits a scoped `ExternalCondition.json`,
always invokes a content-addressed `CrossPhaseAudit.json`, and treats a bound
Lean-checked counterexample as terminal. The dashboard validates the same closure
and accepts counterexample results only when they bind the witness/checker/
toolchain and correctly have no ProofTask.

**Evidence:** standalone and registered S8 clamp both emit the checked
`min = 5, max = 0, x = 0` witness and reject proof-task creation; standalone S8
VMax emits `local-unconditional-claim` plus cross-phase `not-applicable` and may
proceed to proof. The independent convergence review returned `GO`; 73 focused
compiler/proof/corpus/dashboard tests and the complete 402-test repository suite
passed. See
`notes/reviews/elementwise-m2-review-2026-08-29.md`.

**Unresolved:** the eight registered XNNPACK parameter domains remain
`required-missing`; a bounded cross-phase search with no witness remains a
diagnostic, not a proof.

## 2026-08-29 — Single elementwise dashboard authority milestone

**Question:** Does the website now implement the puzzle model without a second
program list, and can an unseen same-family program become proof-ready without a
dashboard edit?

**Conclusion:** yes after one review correction. `/api/elementwise` derives every
row from `CorpusReport.json` plus the verified M/E/D/S/A/C/T/R artifact closure;
the production graph imports none of the legacy program/profile authorities. A
checked-in held-out VMax compiles and reaches `proof-ready` after being published
to a temporary report, with no dashboard configuration.

The first independent review returned `NO-GO` because the page showed only the
condition and phase statuses, not their full audit evidence. The UI now also shows
condition scope, bounded-search trial count, and the complete counterexample
witness. The convergence review returned `GO`. The old case table remains only as
an explicitly labeled historical/non-elementwise view and cannot drive the new
projection.

**Evidence:** schema-v2 elementwise graph and UI; held-out graph regression; 141
dashboard tests and 50 focused graph/web/server tests; reviewer record
`notes/reviews/elementwise-m3-dashboard-review-2026-08-29.md`.

**Unresolved:** intrinsic review remains zero. The next work is a hash-bound,
independently reviewed intrinsic capability batch ordered by corpus fan-out.

## 2026-08-29 — First reviewed intrinsic puzzle batch

**Question:** Can reusable intrinsic progress be generated and audited once per
exact typed piece, then appear automatically for every dependent program?

**Conclusion:** yes for the first nine F32 structural/schedule variants. A shared
typed library and generated parse facade feed the production canonical index. A
content-addressed `IntrinsicRegistry.json` contains all 105 exact variants and
embeds matching independent reviews; the dependency graph currently shows 94
configured spellings and 9 Lean-checked/reviewed spellings. No program id or
dashboard case entry selects them.

The first independent audit returned `NO-GO` for `vst1_lane_f32`: the official
descriptor correctly allowed lanes 0 and 1, but the context-specific emitter
always took lane 0. The implementation now reads the constant lane and generates
`drop (lane * width)` followed by `take width`; lane 1 is modeled distinctly and
lane 2 fails closed. The implementation hash was widened to include the
context-specific emitter so this class of change invalidates old reviews. The
convergence review returned `GO` for all 9 items.

**Evidence:** pinned Arm ACLE r2026Q1 commit
`c218a6b499897e70d88ceab7c6148d692541929f`; ratified RISC-V Vector C Intrinsics
v1.0 commit `b611045daf6c1f2449a5dad6f1a1a6b244b52798`; review policy and check-output
hashes under `notes/`; nine records under
`verification/elementwise-compiler/intrinsic-reviews/`; 35 focused descriptor/
held-out tests, 8 corpus/graph integrity tests, a deterministic corpus rebuild,
and the complete 412-test repository suite.

**Unresolved:** fourteen scalar programs still have missing semantic intrinsics;
eight quantized programs retain their independently visible external-condition
dimension. Batch 2 must add and review semantic families without weakening either
condition or cross-phase gates.

## 2026-08-29 — All scalar programs generated and exact review identity closed

**Question:** Does the generic compiler now generate the complete scalar-layout
corpus, and does the website count the same reusable puzzle pieces that reviewers
actually approve?

**Conclusion:** all nineteen scalar-layout pairs now pass one profile-free compiler
path and emit content-addressed Manifest/Models/proof-free Spec artifacts. Eleven
are ready for proof-task work, seven remain blocked by missing external caller
conditions, and `s8-vclamp` retains its checked counterexample. The grouped
`f32-vcmul` remains intentionally deferred.

The first independent review returned `NO-GO` because 189 registry variants were
collapsed into 178 spelling-level identities; nine groups could share an identity
despite distinct descriptors. Capability and review IDs now include the descriptor
digest. The schema-v3 graph produces 189 unique exact rows, derives 180 used exact
variants from program artifact closures, and separately reports 178 configured of
186 spelling dependencies. The convergence review reran corpus, graph, and web
tests and returned `GO`.

**Evidence:** generic `compile_pair`/`compile_corpus` path; refreshed checked-in
schema-v3 graph with zero stale nodes; exact-identity, scalar-broadcast, and
parameter-width tests; fresh temporary Lean build and theorem audit; 418 passing
repository tests; independent reviewer verdict in the active thread.

**Unresolved:** current implementation changes intentionally stale the nine prior
F32 approvals, so exact review progress is 0/189 globally and 0/180 for the current
nineteen-program closure. Seven external domains and program proof/review batches
remain.

## 2026-08-29 — Complete exact intrinsic audit and publication

**Question:** Can the website now be filled as a reusable puzzle graph, with every
intrinsic used by the nineteen scalar programs independently and exactly reviewed?

**Conclusion:** yes for the pure value-model layer. The audit covers 189 exact
configured variants and the twelve-family review plan covers all 180 variants used
by the nineteen-program closure exactly once. Separate schema-v2 records bind
official exact prototypes, descriptor and transitive implementation hashes,
explicit architecture conditions, machine checks, policy, and reviewer identity.
The graph now reports 180/180 reviewed and Lean-checked used variants without any
program-specific entry.

The first independent review returned `NO-GO`: RVV evidence checked only official
call arity, and scoped review display could survive missing audit parents. The RVV
audit now parses the full pinned official prototype, while the default graph
requires both audit and review-plan parents. The convergence reviewer reran the
focused suite, dry-ran 180 strict publications, and returned `GO (180/180)`.

**Evidence:** `IntrinsicAudit.json`, `IntrinsicReviewPlan.json`,
`IntrinsicReviewChecks.json`, 180 live records under `intrinsic-reviews/`, review
report `notes/reviews/elementwise-m6-intrinsic-review-2026-08-29.md`, 170 focused
Python tests, and fresh 46-job plus seven-target Lean builds.

**Unresolved:** review proves only the declared Lean value-model subjects under
their listed state conditions. Seven program claims still lack external caller
conditions, S8 clamp has a checked counterexample, eleven direct claims still need
proof attempts, and none of these reviews establishes full C or ISA refinement.

## 2026-08-30 — Nineteen scalar program outcomes and final integration

**Question:** After the reusable intrinsic puzzle is complete, can the framework
advance every scalar-layout program without per-program Python/Lean framework
edits, publish honest terminal outcomes, and independently review the whole chain?

**Conclusion:** yes for the current Lean value-model scope. The same generated
Manifest/Models/Spec path covers all nineteen scalar programs. Eight direct claims
have frozen agent-written `Proof.lean` files accepted by the exact theorem,
protected-parent, forbidden-token, axiom, checker, and toolchain gates. Generic
bounded search found and Lean-checked three whole-program FP witnesses
(`f32-vrndne`, `f32-vmax`, `f32-vmin`); the mandatory compiler audit retained the
`s8-vclamp` cross-phase witness. Seven quantized programs stop at independently
visible missing external conditions without proof artifacts.

The first program reviewer returned `NO-GO` because the S8 witness theorem was
anonymous/stale and the review checker closure omitted the two counterexample
producers. Those were fixed, every generated stack was rebuilt under a corrected
reachable-code compiler identity, and all eight proofs were re-frozen and checked.
The publisher and loader now recompute live parents. A final full-suite failure
then exposed diagnostic ordering in copied-corpus audit tests; intrinsic parents
now validate before program reviews. The convergence reviewer repeatedly dry-ran
strict publication and returned `GO (19/19)` on the final snapshot.

**Evidence:** commit `92aad8c` contains the nineteen outcome stacks and first
published reviews; `ProgramReviewPlan.json`, `ProgramReviewChecks.json`, and 19
records under `program-reviews/` bind the final state; reviewer report
`notes/reviews/elementwise-m7-program-outcome-convergence-2026-08-29.md`; 247
elementwise compiler/dashboard tests, 29 final convergence tests, and 444 complete
repository tests pass. The final audit is
`notes/reviews/elementwise-m8-final-audit-2026-08-30.md`.

**Unresolved:** four direct value claims are false under current models, seven need
caller-condition evidence, `f32-vcmul` needs a reusable grouped layout, and full C
memory/overread/alias plus ISA and binary correspondence remain unproved layers.

## 2026-08-30 — Owner-facing Git, eight-item, and end-to-end audit

**Question:** Which branch contains the current edits, how many commits landed in
the last two days, were they pushed, did the eight-item delivery finish, and does
the result support zero-framework-edit onboarding with an agent-reviewed end-to-end
example?

**Confirmed:** the active worktree began clean at
`feat/elementwise-compiler@4ae0cd5`. It contains 23 commits after base `1707e5e`,
all within the preceding 48 hours. Live `ls-remote` found no same-named branch on
either `fork` or `origin`; the fork's older `feat/neon-rvv-to-lean` still ends at
`f6ff9c4`, so the current head is not remotely published.

**Confirmed:** all eight items in the execution ledger have implementation and
review evidence. The supported claim is zero new Python/Lean framework source for
a held-out same-family C pair after its exact intrinsics, scalar layout, and
schedule family exist. It is automated code generation, not “zero code generation,”
and it consumes a Neon/RVV pair plus explicit frontend metadata rather than one
arbitrary C file. Nineteen scalar programs currently produce the honest 8 verified
/ 4 counterexample / 7 external-condition-missing split; grouped `f32-vcmul` and
non-elementwise families remain out of scope.

**Evidence:** a live dashboard rebuild reproduced 20 discovered pairs, 19 scalar,
180/180 reviewed used variants, 19 independent program reviews, and explicit
`not-established` C/ISA layers. A fresh isolated Python 3.13 run passed 248 focused
compiler/dashboard tests. `f32-vadd` was traced through C, Manifest, independently
generated Models, proof-free Spec, frozen ProofTask, agent-owned Proof, Lean Result,
and independent program review; Lean reaccepted the frozen value theorem.

**New issue:** re-running `proof check` on that already published stack rewrote
`Result.json` and `ArtifactIndex.json` with a new closure hash even though protected
parents and proof were unchanged. The cause is that the protected closure hashes
`ArtifactIndex.json`, which already contains the previous result edge. The checked-in
files were restored after diagnosis. Also, the default uv-selected Python 3.12.7
environment segfaults in pytest's readline capture initialization on this host;
the same tests pass under isolated Homebrew Python 3.13.

**Unresolved:** make proof rechecks idempotent; establish seven external caller
conditions; decide FP NaN policy for three refuted pairs; add the complex layout;
and separately build C-memory, legal-overread, alias/frame, real `vsetvl`, ISA, and
binary correspondence layers.

## 2026-08-30 — Classify failed outcomes, producer conditions, and NaN reachability

**Question:** Are the eleven non-verified scalar outcomes caused by incomplete Lean
translation, real source/target differences, or external XNNPACK constraints; can
the seven external conditions be translated; and are NaNs actually legal inputs?

**Confirmed conclusions:** the failures are mixed. `f32-vmax` and `f32-vmin` use
Neon FMAX/FMIN versus RVV maximumNumber/minimumNumber, so one-NaN inputs produce a
real instruction-level value difference. `f32-vrndne` is different: the RVV C
explicitly detects NaN and restores the quieted input payload, but the current Lean
model uses one host `Float32.add/sub` operation for both architectures and makes its
Neon path canonicalize. Under the reviewed Arm `FPCR.DN=0` condition, that witness
is a Lean-model artifact. `s8-vclamp` is a real phase-order difference only when
`min > max`; the pinned unary call path still supplies no established ordered-bound
guarantee.

For the seven external blockers, QINT8/QUINT8 zero-point ranges and positive normal
scales are runtime-validated in `tensor.c`. The two dequantizers merely copy those
validated values and should be the first automatically resolvable producer cases.
The remaining five initializers compute scale ratios and then assert bounds on
ratios, multipliers, shifts, or LReLU negative scale. The unary/binary operator
creation paths validate individual scales but do not enforce those derived bounds;
LReLU does not validate the slope bounds either. A generic initializer frontend can
translate assignments, `fabsf`, `lrintf`, bit reinterpretation, and `assert` into a
conditional `WellFormedParams` theorem, but the asserted predicates must remain
distinct from facts proved by callers. Otherwise a debug assertion would be
silently promoted into an XNNPACK API guarantee.

FP32 dense-tensor creation checks datatype/shape but does not scan element values.
The XNNPACK binary microkernel tester explicitly skips checking NaN reference
outputs with the comment that not all kernels handle them. Therefore NaN is not
excluded by the actual input path, although a cross-platform exact NaN result is
also not clearly promised. Exact-bit verification must model architecture-specific
NaN behavior. Excluding NaN or quotienting NaN payloads is a possible explicit
upper-layer contract/observation choice, not a fact the compiler may infer.

**Evidence:** `benchmark/XNNPACK/src/tensor.c:50-98,130-160,163-217,318-343`;
`src/operators/unary-elementwise-nc.c:89-147,243-277`;
`src/operators/binary-elementwise-nd.c:134-210`;
`src/microparams-init.c:674-703,830-934,1052-1071,1207-1234,1267-1275`;
`test/vbinary-microkernel-tester.cc:80-119`; corpus source/target files and checked
counterexamples; official Arm Neon intrinsic mapping and Arm FMAX semantics; official
RISC-V F/V NaN and minimumNumber/maximumNumber specifications.

**Unresolved:** decide the intended XNNPACK-level NaN observation; determine whether
the five assert-only producer domains should become explicit API preconditions or
upstream runtime checks; implement and review the generic producer bridge; and
re-run all FP outcomes after architecture-specific arithmetic NaN semantics land.

## 2026-08-30 — Reproduce and separate the four generated counterexamples

**Question:** Do the `f32-vmax`, `f32-vmin`, `f32-vrndne`, and `s8-vclamp`
counterexamples expose differences in the original C pair or mistakes in the Lean
model, and are all four caused by NaNs?

**Confirmed:** the answer is mixed. On AArch64 with `FPCR.DN=0`, the executable
probe runs the source-side Neon operations and obtains `0x7FC00000` for both
`vmaxq_f32(+0, qNaN)` and `vminq_f32(+0, qNaN)`. The ratified RVV
maximumNumber/minimumNumber value oracle returns `+0`, exactly matching the checked
Lean witnesses. These two are real source/target exact-bit gaps and their
non-NaN branches reduce to the same ordered operation.

**Confirmed model defect:** for signaling NaN `0x7FA00001`, actual Neon `vrndne`
quietens and preserves the payload as `0x7FE00001`; the target C's explicit RVV
fixup reconstructs that same result. Current Lean produces `0x7FC00000` on the
Neon side because shared host `Float32.add/sub` canonicalizes the NaN. The checked
`f32-vrndne` witness is therefore not a C-pair counterexample in the reviewed
`DN=0` mode. `DN=1` remains a separate stateful case where the C pair can differ.

**Confirmed non-NaN gap:** `s8-vclamp` uses max-then-min in its 64-lane phase and
min-then-max in its 8/tail phase, while RVV always uses max-then-min. For `x=0`,
`min=5`, `max=0`, the executable results are Neon main `0`, Neon tail `5`, RVV
`0`. A staged Lean theorem with a one-byte input proves `Not
completeValueEquivalenceClaim`; the published checker records only
`neonPhaseFunctionsEqualClaim` because whole-program search returns early after a
phase witness. The selected unary initializer and definition path do not enforce
ordered bounds; the separately found legacy minmax initializer is not this path.

**Conclusion:** the four cases are not all NaN-related. The two max/min gaps are
real and NaN-specific; the rounding witness is NaN-related but model-induced under
the stated mode; the clamp gap is a real integer order/contract issue. Detailed
evidence and reproduction commands are in
`notes/four-counterexample-semantic-audit.md` and
`notes/demos/neon-rvv-semantic-gap-aarch64.c`.

**Unresolved:** replace host floating arithmetic with architecture-conditioned NaN
semantics and rerun every FP result; decide the intended upper-layer NaN
observation; publish the complete S8 witness; and either establish `min <= max` in
the selected caller contract or treat reversed-bound behavior as a translation
defect.

## 2026-08-30 — Narrow versus system-wide `f32-vrndne` repair scope

**Question:** Does fixing the spurious `f32-vrndne` counterexample really require
three to five days, or can the affected intrinsics simply be repaired?

**Confirmed:** the immediate defect is small and is located in the intrinsic value
layer. Neon `vaddq_f32` and `vsubq_f32` currently delegate to the same host
`Float32.add/sub` functions used by RVV wrappers, so the modeled Arm path loses a
signaling-NaN payload under `FPCR.DN=0`. A narrow correct repair can give those two
Neon wrappers reviewed Arm `DN=0` NaN behavior while retaining the existing finite
arithmetic path. It does not require a complete IEEE-754 implementation.

**Confirmed scope:** these shared add/sub wrappers occur in five generated programs:
`f32-vrndne`, `f32-vadd`, `f32-vsub`, `f32-f16-vcvt`, and
`qs8-vmul-minmax-fp32`. They must be rechecked after the change. The larger design
issue is that ordinary add/sub/mul/div/sqrt operations still share host primitives
between architectures and do not represent Arm FPCR, RISC-V rounding/flag state,
or complete architecture-specific exceptional-value behavior.

**Estimate/Proposal:** budget about one day, conservatively one to two days, for the
narrow `DN=0` value-semantics repair, focused NaN tests, and affected-program
regression. The previous three-to-five-day estimate applies only to a reusable,
reviewed cleanup of the wider shared FP layer plus full FP corpus regeneration and
review; it is not necessary to remove this one false counterexample.

## 2026-08-30 — Project synthesis, minimal public Spec, and 36-pair boundary

**Question:** How did the project evolve through the eight-stage delivery, how
should the positive, counterexample, and external-condition outcomes be understood,
and does a minimal final `completeValueEquivalenceClaim` let the current method
scale from twenty elementwise programs to all thirty-six nonempty pairs?

**Confirmed:** the eight-stage parse/capability/model/spec/proof/check/dashboard
chain is complete for the nineteen scalar-layout elementwise pairs. Its reviewed
terminal outcome split is 8 verified value claims, 4 checked counterexamples, and
7 missing external-condition bridges; grouped planar-complex `f32-vcmul` remains
outside that scalar set. Assertions must remain partitioned into entry conditions,
derived program-point invariants, and separately evidenced producer/caller
conditions.

**Confirmed design insight:** only the complete observable-value equality is
logically required as the public generated Spec. Element, block, loop, and phase
claims may remain internal proof decompositions supplied to the proof agent. This
removes an unnecessary Spec-generation admission gate, but does not make model
generation automatic for new memory and control-flow families.

**Confirmed causal correction:** the CVC5 path compiles a generated C++ harness and
executes embedded kernel bodies over symbolic values at each concrete batch/VLEN;
the concrete control execution builds one finite term graph. It therefore reuses C
execution more directly but does not quantify over arbitrary length. The Lean path
instead statically recognizes a restricted schedule language. In the current
nineteen programs, Neon schedules reduce to ten `4 + 2/1`, six `8 + 4/2/1`, and
three multi-phase `8→4`, `16→8`, or `64→8` shapes; all RVV sides use positive
strip-mined partitions.

**Confirmed local-assert behavior:** a tail assertion is not silently deleted.
For example, the `qs8-f32-vcvt` post-loop checks `1 <= batch <= 7`; the recognizer
derives this from the eight-byte loop exit and nonzero tail branch and records a
`fixed-tail-remainder` fact. Any unmatched local assertion fails closed. Separately,
the elementwise scalar projection may replicate one scalar across a Neon block,
but a proof must still establish that every arbitrary block equals a map/zipWith of
that projection; replication alone is not a lane-independence proof.

**Confirmed boundary:** the repository has 40 source files, 37 target paths, and
36 nonempty pairs. The current flat-list elementwise compiler directly covers none
of the sixteen additional non-elementwise pairs. At least thirteen require 2-D,
gather, packed, strided, or pointer-table memory/layout; the remainder still need
reduction or multi-output observation. Those pairs also add roughly 170 intrinsic
spellings absent from the current canonical Lean registry. Thirty-six is therefore
the scale-up target space, not the already supported count.

**Proposal:** evolve the model generator toward a restricted typed kernel IR and
add reusable layout, loop, reduction, and observation components in small vertical
slices. Start with grouped `f32-vcmul`, then lower-complexity reduction/transpose
cases, while retaining fail-closed parsing, independent models, frozen goals,
checked counterexamples, and evidenced external conditions. A concise project
narrative and verified Mermaid architecture diagram are recorded in
`notes/PROJECT_PROGRESS_OVERVIEW.md` and `figures/saltyrn-project-pipeline.mmd`.

## 2026-08-30 — Implement and close the `f32-vrndne` intrinsic repair

**Question:** Can the modeling bug be repaired quickly, with a plan reviewed
before implementation and the resulting corpus independently checked?

**Confirmed:** the reviewer approved the plan after the scope was expanded from a
two-wrapper patch to a coherent shared value-layer repair. Arm `DN=0/AH=0` and
RISC-V NaN behavior are now separated for arithmetic, comparison, and max/min.
The old `f32-vrndne` witness disappears and an axiom-free Lean proof establishes
its complete value claim for every input.

**Confirmed outcome change:** re-running all nineteen scalar programs yields
2 `verified(value)`, 10 checked counterexamples, and 7 missing external
conditions. Nine FP programs expose real Arm payload-preserving versus RISC-V
canonical-NaN exact-bit gaps; `s8-vclamp` remains the non-NaN order gap. All 180
used intrinsic reviews and all 19 program reviews were republished against current
content hashes with reviewer verdicts `GO (180/180)` and `GO (19/19)`.

**Evidence:** `notes/elementwise-compiler/F32_VRNDNE_REPAIR_PLAN.md`;
`notes/reviews/elementwise-vrndne-final-review-2026-08-30.md`;
`notes/reviews/elementwise-vrndne-program-outcomes-review-2026-08-30.md`;
`src/verification_bw/lean/SALT/Intrinsics/FP32.lean`; and the generated
`f32-vrndne/Proof.lean` and `Result.json` artifacts.

**Unresolved:** decide the upper-layer NaN observation or translation policy for
the nine real FP gaps; continue treating full FP state, C, compiler, and ISA
correspondence as separate work.

## 2026-08-30 — Residual risk of additional micro-modeling defects

**Question:** After repairing the shared FP NaN semantics, could similar small
modeling mistakes still be hidden in the current corpus?

**Confirmed:** several boundaries are explicit rather than silently proved:
non-default FP modes, FP/RVV exception state, C memory behavior, compiler lowering,
and binary ISA correspondence are outside the current value theorem. The repaired
FP layer still uses Lean `Float32` for normal arithmetic after handling NaNs and
invalid exceptional cases explicitly.

**Inference:** more micro-defects are plausible, concentrated in finite FP
rounding/subnormal/signed-zero corners, conversions, and integer
rounding/saturation/shift instructions. Plain fixed-width BitVec arithmetic is
lower risk. This does not reclassify any current result: two claims remain proved
relative to the Lean model, ten have checked witnesses, seven are blocked on
external conditions, and one layout is unsupported.

**Proposal:** prioritize independent differential oracles for the two positive
claims and every shared arithmetic helper; exhaust 8/16-bit integer edge spaces,
use adversarial binary32 bit patterns, and compare real Arm plus a conforming
RISC-V implementation/simulator before upgrading a value theorem to C/ISA
correctness.

## 2026-08-30 — Begin an all-intrinsic semantic audit

**Question:** Should every configured intrinsic receive a new CSV audit row, and
should parallel reviewers compare real Neon/RVV calls, official operation
semantics, and the exact Lean implementation?

**Confirmed:** yes. The new audit uses exact capability IDs and keeps the existing
180/180 used-variant review gate separate from semantic confidence. Three
independent passes cover all 189 registry variants with no duplicate or missing
ID. Round 1 yields 113 confirmed at the inspected pure-value scope, 43
conditional, 30 needing deeper audit, two confirmed bug descriptors, and one
suspected bug descriptor.

**Confirmed evidence:** native arm64 execution and Lean evaluation disagree for
the shared Neon `vrshlq_s32` helper at large negative counts; both its used and
legacy descriptors are marked `confirmed_bug`. The current programs require an
external `shift in 0..31` contract and are not among the two proved value claims.
The unused RVV `vssra` helper lacks SEW shift masking and remains `suspected_bug`
pending an independent RVV execution oracle. Review also found conditional
`vxsat`, `vsetvl`, load/store, tail/state, and exact-immediate evidence gaps.

**Artifacts:** `notes/audits/intrinsic-semantic-audit.csv`,
`notes/audits/INTRINSIC_SEMANTIC_AUDIT_PLAN.md`,
`notes/audits/INTRINSIC_SEMANTIC_AUDIT_ROUND1.md`, and
`outputs/intrinsic-semantic-audit/intrinsic-semantic-audit.xlsx`.

**Unresolved:** execute the L3 differential queue, repair the confirmed Neon
helper, validate the unused RVV helper on Sail/hardware, and make official API-test
matching verify exact immediate values rather than only argument count.

## 2026-08-30 — Close the multi-stage exact-intrinsic audit

**Question:** Can the system compare every exact Neon/RVV intrinsic with official
and executable architecture behavior, repair modeling errors, remain traceable,
and then rerun all nineteen scalar programs?

**Confirmed:** yes at the explicitly recorded evidence levels. The canonical
inventory is 184 rather than 189 because five repaired descriptors collapse onto
existing faithful capabilities. The deterministic ledger classifies 131
confirmed, 43 conditional, and 10 needing deeper memory/`vsetvl` audit; no current
row remains a suspected or confirmed modeling bug.

**Confirmed evidence:** native AArch64/Lean tests cover all signed-byte
`vrshlq_s32` counts; LLVM RVV intrinsic plus Spike proves SEW masking for
`vssra.vx`. The four differential audits pass 191/191 FP, 232/232 P1 integer, and
378/378 plain-integer samples. Sixty-eight structural subjects pass trace and
generator checks, explicitly without an ISA-correctness claim. Full Lean build and
194 Lean-backend tests pass after faithful vector-vector max/min regeneration.

**Confirmed program rerun:** `f32-f16-vcvt` and `f32-vrndne` verify; nine floating
programs and `s8-vclamp` retain checked counterexamples; seven quantized programs
remain blocked by missing external conditions.

**Artifacts:** `verification/elementwise-compiler/SemanticAuditLedger.json`, four
`*DifferentialAudit.json` files, `notes/audits/intrinsic-semantic-audit.csv`, and
`notes/audits/INTRINSIC_SEMANTIC_AUDIT_ROUND1.md`.

**Unresolved:** L4 correspondence to an independent formal ISA model, full
register/memory/tail/exception-state semantics, the three broadcast-conditional
I1 helpers, and the seven external program conditions remain separate future work.

**Final independent review and regression:** the convergence reviewer issued
`GO (180/180)` and `GO (19/19)` in
`notes/reviews/intrinsic-semantic-audit-final-2026-08-30.md`. A full repository run
reported 460 passed and 23 skipped plus one stale protected-Lean-project hash;
after the required proof-policy rebind, the failed gate and all 14 proof-policy
tests pass. Final loaders report 180 intrinsic and 19 program reviews.

## 2026-08-31 — Reproduce a source/target difference from the original C files

**Question:** Can one counterexample be executed at the original C-intrinsic level,
rather than only in Lean or through a hand-written semantic oracle?

**Confirmed:** yes. `notes/demos/f32-vmax-c-counterexample/` directly includes the
repository's original `test_neon` and `test_rvv` definitions. On four lanes with
bit patterns `0x00000000` (`+0.0`) and `0x7FC00000` (quiet NaN), native AArch64
executes the source function and returns `0x7FC00000`. LLVM lowers the target function's RVV
intrinsic to `vfmax.vv`; Spike executes that binary and returns `0x00000000`.

**Conclusion:** this witness is a real original-C intrinsic-program gap caused by
Arm `FMAX` versus RVV `maximumNumber` behavior. It is not caused by the Lean model,
loop scheduling, missing XMLPack parameter constraints, or a portable RVV oracle.

**Evidence:** `notes/demos/f32-vmax-c-counterexample/run.sh` rebuilds both sides,
checks the RVV disassembly, inspects the Spike result, and prints the two bit-exact
outputs. The run passed on 2026-08-31.
