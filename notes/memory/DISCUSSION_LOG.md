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
