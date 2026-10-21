# SaltyRN Discussion Log

Entries are append-only. The canonical current conclusions live in
`PROJECT_STATE.md`.

## 2026-07-11: Repository and Intrinsic Audit

**Questions:** How are Lean intrinsics produced, do they match the original C/ISA,
what is each remote branch doing, and is current work aligned with the project goal?

**Conclusions:** No reproducible intrinsic-to-Lean generator was found. Existing
Lean models are hand-authored/kernel-specialized shallow embeddings. Their current
QS8 proofs are meaningful inside the Lean model but are not yet C/ISA correspondence
proofs. `lean-verification` is stale relative to main; `vlen128` is the latest active
branch and only adds translated targets. The formal-verification research objective
is aligned with the original project discussion, while the active engineering path is not yet integrated
with Lean automation.

**Detailed note:** `../neon-to-lean-mapping.md`.

## 2026-07-12: Durable Memory and Float32 Questions

**Questions:** Establish project memory; assess whether Float32 is a blocker, whether
to model it from lower-level binary32 definitions, whether current Lean is aligned
with C, whether generated proofs are correct, and what remains after complete
intrinsic coverage.

**Initial confirmed findings:** Lean 4.29's core `Float32` arithmetic is opaque and
extern-backed rather than kernel-reducible IEEE-754 semantics. Current `F32VELU`
Neon/RVV models share one definition, so their theorem does not independently
validate either C implementation. Complete intrinsic coverage alone would still
leave C frontend, memory/UB contracts, control flow, RVV configuration, FP
environment, theorem binding, and proof/CI obligations.

**Proof audit result:** all 50 Lean modules and 11 exported equivalence theorems
compile with no source-level `sorry`/`admit`/explicit axiom. Eight QS8 add/addc
theorems nevertheless depend transitively on 31 native `bv_decide` axioms, so they
extend the TCB to Lean's compiler/native checker. The F32 and clamp proofs use only
standard axioms. All are correct relative to their Lean statements, but none proves
C-to-Lean correspondence.

**Float32 result:** Float32 affects 28/40 current source kernels. Native Lean
`Float32` is executable but kernel-opaque. The historical F32VELU pair has a concrete
fused/non-fused mismatch: Neon `vmlaq_f32` is non-fused, RVV `vfmacc` is fused, while
Lean models both as separate multiply then add. The current `fmax` helper also omits
NaN and signed-zero distinctions, and its Neon loop chunking does not reproduce the
historical C loop. Therefore the existing F32 theorem must not be used as C
equivalence evidence. A host-level binary32 check produced an all-normal finite
counterexample (`3620B2AC * 2ED17056 + 1BADB75B`): fused result `2583786D`,
non-fused result `2583786E`.

**Decision proposal:** use an explicit bit-level binary32 value semantics, initially
fixed to RNE and gradual underflow, with distinct FMA and ISA-specific min/max
wrappers. Audit Gondolin/TorchLean's `IEEE32Exec` as a reuse candidate and validate
it differentially; native `Float32` remains a testing oracle only. Begin the first
vertical slice with an integer kernel, then add a simple current-main FP kernel and
explicit FMA/minmax stress cases.

## 2026-07-12: Float32 "Solved" and IR Scope Correction

**Question:** If binary32 can be defined from bits, why is Float32 still considered
a Lean pain point, and which of the previously listed gaps should the IR solve?

**Conclusion:** representation and a pure-Lean fixed-RNE executable value model are
now available, but proof of complete IEEE behavior, all FP state, runtime/C/ISA
bridges, and scalable automation are not generally solved. Gondolin materially
reduces implementation work but does not close those bridges.

The previous nine-item list was too broad. The intended production design is
`ArtifactEnvelope + KernelIR + Contract/Observe`, interpreted in Lean. That complete
pipeline should make preprocessing/provenance, supported memory/UB semantics,
contracts, RVV configuration, selected FP semantics, and artifact binding part of
the definition of a completed translation. What remains outside it is independent
semantic assurance/common-mode-error control, equivalence proof automation, caller
composition where needed, CI policy, and an optional machine-code bridge.

## 2026-07-12: Integer-First Decision Proposal

**Question:** Can Float32 be deferred, what IR questions remain, and what should be
implemented next?

**Proposal:** defer FP denotation and proofs, while reserving typed FP/mask syntax,
pluggable semantic/effect state, byte memory, explicit observation, build provenance,
and fail-closed FP feature detection. This makes FP a later semantics module rather
than a rewrite of the integer executor.

Use current-main `s8-vclamp` as the first complete paired slice. Default theorem
choices are output-prefix plus frame observation, all legal RVV `vl` schedules, and
a pinned Clang typed-AST frontend with 100% body coverage plus a Lean-checkable
extraction manifest. These remain proposals until the production schema is accepted.

**Slice audit:** `s8-vclamp` needs parameter representability
`-128 <= min <= max <= 127`, input padding to `roundUp(batch,8)`, output extent
`batch`, and an alias decision; the proposed alias contract is disjoint buffers or
exact in-place. Its source has 64/8/tail paths while the RVV target strip-mines, so
it provides the smallest current-main pair that exercises the intended memory,
schedule, termination, and frame semantics.

## 2026-07-12: Memory Protocol and First Integer Prototype

**Question:** Create durable planning/decision memory and begin implementing the
accepted integer-first default.

**Conclusion:** Added `DECISIONS.md` and `PLAN.md`, expanded the root memory protocol,
and implemented the first S8 prototype under `prototype/neon2lean`. The production
schema now separates artifact provenance, typed `KernelIR`, contract/observation,
byte memory, and the integer feature gate. Translation acceptance is deliberately
layered: audit completeness and emitter translation claims are not concrete IR
binding; the structural relation checks typed references, ranges, consistency, and
bidirectional coverage against an actual IR, but does not prove semantic preservation.

**Evidence:** pinned-signature Clang extraction audits all 399 source and 121 target
nodes. Regression tests reject unknown intrinsic spellings, reachable float syntax,
signature changes, nested integer casts, malformed emitter numbers, and a
`vminq_s8` to `vmaxq_s8` semantic mutation. RVV descriptors now bind exact SEW/LMUL.
JSON and generated Lean regenerate byte-for-byte. `lake build` passes all 18 jobs.
The four exported S8 value theorems report only `propext` and `Quot.sound`; generated
source/target envelopes evaluate to internally bound `true` and translation-claim
`false`.

**Unresolved:** all coverage entries remain `AST_AUDIT_ONLY`; no semantic C-to-IR
lowering or artifact-bound kernel theorem exists. The abstract RVV progress proof
still needs a real `vsetvl`/ISA bridge, and memory safety, partial-store footprint,
frame, alias, and final observational-equivalence proofs remain. The reviewed
descriptor registry also needs a version/hash in artifact provenance.
Before interpreting emitted IR, the reference-shape checker must gain SSA use-order
and CFG-dominance checks, and coverage must bind function identity plus per-entry
kind/range lowering certificates; the current relation deliberately checks only
reference/range set consistency.

## 2026-07-12: IR Completeness and Minimal E2E Clarification

**Question:** Is the IR finished, how extensible is it, and what end-to-end case or
concrete output exists now?

**Conclusion:** The current production files are an IR schema and validation shell,
not an executable semantic IR. They define typed parameters/operations/blocks,
provenance, byte memory, contracts, observations, and registry checks, but have no
operation interpreter, explicit branch terminators, phi/block arguments, dominance,
or generated semantic IR. The S8 extractor is a kernel-specific AST shape audit; all
520 entries remain `AST_AUDIT_ONLY`. Therefore there is no C-to-Lean verification E2E.

**Concrete current demo:** for input `[-128,-100,-4,0,5,20,100,127]`, bounds
`[-10,20]`, and abstract RVV chunks `[3,3,2]`, both Lean value models evaluate to
`[-10,-10,-4,0,5,20,20,20]`, and their executable equality check returns `true`.
Separately, real-C auditing reports 399/399 source and 121/121 target AST nodes, with
internally-bound envelopes `true` and semantic-translation claims `false`.

**Proposal:** first build a synthetic paired `s8-clamp16` semantic E2E: one fixed
16-lane Neon block and an RVV `while + vsetvl` loop over the same 16 bytes, quantified
over every legal positive `vl` schedule. This closes C AST -> generated IR ->
interpreter -> memory/frame theorem without the real kernel's Neon tail complexity.
It is not arbitrary-batch verification. Then reuse the machinery for real
`s8-vclamp`, physical tail behavior, and all legal RVV schedules.

## 2026-07-13: Viability of C-to-IR-to-Lean and Generated Specs

**Question:** Is `C -> IR -> Lean`, followed by automatic spec generation, a viable
route?

**Conclusion:** Yes for a fail-closed, deliberately restricted C/intrinsic subset.
The approach matches established formal-compiler and translation-validation patterns:
give an IR precise semantics, interpret or symbolically execute it, and prove a fixed
refinement/equivalence obligation. The decisive difficulty is the checked C-to-IR and
intrinsic/ISA correspondence bridge, not Lean proof checking itself.

**Spec boundary:** automate IR emission, per-node lowering certificates, theorem
headers, and optionally an architecture-neutral normal form used as a proof witness.
Do not treat a functional spec generated from the same unchecked IR as independent
evidence. Contract/UB assumptions, observation, intrinsic denotations, and axiom policy
must be versioned reviewed inputs; direct source/target observational equivalence is
the primary theorem.

**Evidence:** CompCert uses formally specified source/intermediate languages and
semantic-preservation simulations; Vellvm provides formal LLVM semantics and a
refining executable interpreter; Alive2 converts LLVM to its IR and checks refinement;
Lean-MLIR provides typed SSA/dialect denotations and verified rewrites. These validate
the architecture pattern, while none removes SaltyRN's Neon/RVV and C-boundary work.

## 2026-07-14: First Generated Semantic-IR E2E and Fork Preparation

**Question:** Continue the chosen route, organize the past several days into about five
chronological commits on `Etha-Sun/SALTy-rn`, and make further concrete progress.

**Conclusion:** Implemented synthetic `s8-clamp16` as the first paired generated
semantic-IR E2E. The restricted frontend consumes real C translation units and emits
typed operation graphs plus 100% translated coverage. A reviewed registry now binds
each spelling to type/config, semantic opcode, and effect. Lean checks artifact/function
identity and local use order, directly executes both generated IRs, and proves success,
final-memory/output equality, frame, and exact 16-address write summaries for every
positive RVV progress partition under the fixed contract.

**Mutation result:** replacing RVV min with a second supported max succeeds in the
frontend, emits different IR, and still passes registry/shape checks; Lean proves a
concrete inequivalence. Unknown calls and unsupported AST still fail closed. This
supersedes the idea that every semantic mutation should be rejected by extraction.

**Evidence:** `lake build` passes 25 jobs; both Python regression suites pass;
checked JSON/Lean regeneration is byte deterministic; new exported theorems depend
only on `propext` and `Quot.sound`. A demo input produces identical signed outputs for
Neon and RVV chunks `[3,5,8]`.

**Boundary:** the microcase is synthetic and uses a parse facade, restricted Python
lowering, structured single-block control, and transactional final-state memory. It is
not the real XNN kernel or an Arm/RISC-V ISA theorem. Positive progress schedules are
an overapproximation until the `vsetvl` bridge is proved. The real `s8-vclamp` artifact
remains audit-only and is the next generalization target.

## 2026-07-14: Public Fork Integration and Reproducibility Gate

**Question:** How should the accumulated work be organized into reviewable Git history
on the public fork, while removing local/private provenance and preserving evidence?

**Conclusion:** Created local branch `research/lean-ir-e2e` from upstream
`main@6acdf7a` and reconstructed five staged commits dated July 10--14: U8 typed IR,
the production IR foundation, signed-clamp value proof, real-S8 fail-closed audit, and
the generated semantic E2E plus project memory. Private correspondence is excluded.
Repository artifacts now contain only repository-relative paths.

**Evidence:** direct-checkout regeneration preserves 399/399 source and 121/121 target
audit coverage; `check_e2e.py` passes both frontend suites, 25-job Lean build,
forbidden-token scan, and an exported-axiom whitelist of only `propext`/`Quot.sound`.

**Unresolved:** the branch is local and has not been pushed. The next semantic step is
still generalizing normalized lowering and structured control to real `s8-vclamp`.

## 2026-07-16: Teaching Audit of Existing Lean Examples

**Question:** What do the already verified `QS8ClampEmit`, `QS8VAddC`, and `F32VELU`
examples actually prove, and how should their files be read?

**Conclusion:** all three use the same proof architecture: reduce each ISA-specific
list loop to a `map`/`zipWith` normal form, prove pointwise equality, then apply a
generic kernel-class theorem. `QS8ClampEmit` is the clearest warm-up because both
element functions are identical. `QS8VAddC` adds one genuine cross-model lemma for
Neon versus RVV-RNU rounding shifts under `shift <= 31`. `F32VELU` is the key warning:
both sides reduce by `rfl` to one shared opaque `Float32` computation, so its clean
Lean theorem is not independent IEEE/C/ISA validation.

**Evidence:** audit pinned to `lean-verification@dd1c0ab`. Concrete Lean runs
gave clamp outputs `[-10,-10,-4,0,20,20,20]` for both an 8-lane Neon schedule and
RVV `vlmax=3`, and VAddC outputs `[-1,2,7]` for both sides. `#print axioms` reports
only `propext`/`Quot.sound` for clamp, while VAddC transitively carries 31 native
`bv_decide` axioms from the rounding lemma. The executable walkthrough is saved as
`notes/demos/existing-lean-examples.lean`.

**Boundary:** the runtime harness, bounded SMT harness, and unbounded Lean list theorem
are distinct artifacts. None of the existing final Lean theorems binds a C AST, source
hash, pointer/memory semantics, or an official intrinsic/ISA model. `Emit`/`Parsed`
names alone are not provenance certificates.

## 2026-07-16: Historical Lean-to-C/ISA Alignment Audit

**Question:** Is the existing pattern merely `Neon = map f`, `RVV = map f`, followed
by a template proof; which translations are inaccurate; which inaccuracies are
acceptable; and do any accepted Lean theorems remain misaligned with real C/ISA
implementations?

**Conclusion:** the structural summary is correct, but the two loop-refinement lemmas
and pointwise element equality carry the semantic burden. All 11 final theorems are
valid relative to their Lean definitions, with a native-`bv_decide` trust qualification
for the eight QS8 add/addc variants. They cover only four semantic families and do not
establish C or ISA correspondence. List/chunk abstractions and omitted inactive state
can be acceptable under explicit output-only contracts; copied FMA semantics, signed-C
overflow modeled as wrapping, and clamp equality without ordered bounds cannot.

**Evidence:** all 52 Lean source units compiled explicitly; no `sorry`, `admit`,
explicit `axiom`, or `unsafe` was found. A full finite-normal F32 VELU input
`0xBB44B983` produces Neon/non-fused `0xBB446E00` and RVV/fused `0xBB446DFF`.
UBSan reports signed overflow for the allowed VAddC bias case
`255 * INT32_MAX`. For `x=0, min=100, max=-100`, the current Neon clamp tail returns
`100`, while RVV and the Lean model return `-100`. Reproducers and the complete
module/provenance/TCB matrix are in `notes/lean-model-alignment-audit.md`.

**Current IR comparison:** synthetic `s8-clamp16@0eb0f75` is a defensible restricted
generated semantic-IR E2E, but it uses external strip-mine control and transactional
memory. Real `s8-vclamp` remains 399/399 plus 121/121 `AST_AUDIT_ONLY`; its handwritten
value theorem and synthetic generated-IR theorem are not connected. Lean checks
recorded digest consistency, not file hashes; Python regeneration supplies freshness.

**Unresolved:** the required publication claim, authoritative C/flags/contracts, and
whether all legal RVV `vsetvl` traces are required remain project-owner decisions.
The next implementation target remains full semantic lowering of real `s8-vclamp`,
with ordered/representable bounds, physical tail memory, partial stores, bundled
artifact binding, and real-artifact freshness CI.

## 2026-07-16: Translation Validation, Verified Lifting, and IR Taxonomy

**Question:** Are there only two directions: verify an LM rewrite, as in verified
lifting/LLMLift, or use PL techniques to translate `Neon -> IR -> Lean`?

**Confirmed (literature):** classical verified lifting is not merely post-hoc
checking of an LM-produced source-to-target rewrite. It uses synthesis, such as
CEGIS, to find a high-level program or summary and verifies functional equivalence
to the low-level source. LLMLift changes the proposal mechanism: an LLM receives
target-language semantics expressed through Python context, proposes a target
program and equivalence proof, and an external formal verifier remains the checker.
Tenspiler shows the related compiler architecture `source -> synthesized TensIR ->
multiple target backends`, with the IR supporting lifting, verification, and code
generation.

**Confirmed (taxonomy):** two useful axes were being conflated. Candidate generation
can be (1) an untrusted LM/tool followed by per-instance translation validation or
(2) a certifying synthesis/compiler. Proof organization can independently be direct
source/target equivalence or two refinements through a shared IR/spec. Therefore
`Neon/RVV C -> IR -> Lean` is semantic extraction shared by several strategies; it
does not itself generate an RVV rewrite and is not the alternative to LLMLift.

**Proposal:** for the current SaltyRN objective, use a hybrid. Preserve the existing
LM as the untrusted RVV candidate generator; deterministically and fail-closed lower
both Neon and RVV C bodies to a typed semantic IR; make Lean prove the fixed
observational-equivalence theorem. Let an LLM/CEGIS system optionally propose a
shared normal form, invariant, or proof script, but treat all of those as untrusted
witnesses. A genuinely different long-term project would lower Neon to a shared IR
and then generate RVV through a semantics-preserving verified backend.

**Evidence:**

- Verified Lifting of Stencil Computations (PLDI 2016):
  <https://people.eecs.berkeley.edu/~akcheung/papers/pldi16.html>
- LLMLift technical report (2024):
  <https://www2.eecs.berkeley.edu/Pubs/TechRpts/2024/EECS-2024-11.html>
- Tenspiler (ECOOP 2024):
  <https://doi.org/10.4230/LIPIcs.ECOOP.2024.32>

**Unresolved:** the paper framing still needs an explicit choice between a
translation-validator contribution, a verified-lifting contribution centered on a
SIMD normal form, and the much larger verified-compiler contribution. The first is
the closest match to the stated project objective and current SaltyRN artifact.

## 2026-07-16: How LLMLift Establishes Equivalence

**Question:** What does LLMLift's generated equivalence proof actually contain, and
how is it checked?

**Confirmed:** for the side-effect-free source/target functions in the paper, the
correctness condition is `forall state sigma, S(sigma) = T(sigma)`. The LLM first
proposes a program summary (`PS`) composed only from the supplied target-DSL
operators. If the source has loops, it then proposes loop invariants (`Inv`) that
relate the partially computed source state to a prefix application of `PS`. These
are Python-shaped IR expressions, not Lean/Coq proof terms or unstructured natural
language arguments.

**Confirmed:** a rule-based parser rejects unsupported constructs and rewrites `PS`
and `Inv` into the verification oracle's language. Floyd-Hoare verification-condition
generation reduces the loop proof to initialization, preservation, and termination
obligations. cvc5 or Z3 checks those obligations for validity; a failed Boolean result
causes LLMLift to request another candidate. Thus the LLM supplies the candidate and
inductive certificate, while deterministic VC generation plus SMT performs the
actual universal check.

**Confirmed boundary:** the paper's claim is limited to side-effect-free code and its
framework does not support pointers or objects. The proved equality is between the
source semantics accepted by its frontend and the verified IR program summary under
the encoded DSL operator semantics. A syntax-directed rule system subsequently emits
concrete DSL code, so fidelity of the source frontend, DSL axioms/semantics, VC
generator, SMT solver, and IR-to-concrete code generator all remain relevant to the
end-to-end claim. The current Metalift tutorial separately offers Rosette as a bounded
testing mode and SMT plus user-supplied DSL axioms as its full-verification mode.

**Inference for SaltyRN:** LLMLift's useful transferable idea is to let an LLM propose
the shared SIMD summary and loop invariants. It is not a drop-in Neon/RVV verifier:
pointer memory, aliasing, undefined behavior, intrinsic effects, and dynamic RVV `vl`
first need explicit semantics. Lean can replace the SMT oracle while keeping the same
division of labor: the agent proposes summaries/invariants/proof scripts, and the
fixed theorem plus Lean kernel checks them.

**Evidence:**

- LLMLift paper, Sections 3 and Appendix E:
  <https://people.eecs.berkeley.edu/~sseshia/pubdir/llmlift-neurips24.pdf>
- Metalift LLMLift tutorial:
  <https://metalift.pages.dev/docs/tutorial/llmlift-tutorial/>

## 2026-07-16: Publishable Audit Artifact Organization

**Question:** Which accumulated files are still outside Git, and how should the F32
counterexample and remaining audit material be committed?

**Confirmed:** the actual repository is the `upstream-main/` worktree on
`research/lean-ir-e2e`; the surrounding research directory is intentionally not a
Git repository for this project. Before this organization pass, the fork remote had
only `main@6acdf7a`, so the five existing IR commits were local-only. The root-level
prototype is a stale working duplicate and is not a source for new commits.

**Conclusion:** committed the standalone finite-normal F32 VELU fused-versus-
non-fused reproducer as `505b7f3`, then committed the complete historical Lean
alignment audit, QS8VAddC UBSan reproducer, and executable historical Lean walkthrough
as `83cb0cc`. Public artifacts use repository-relative paths and pinned revisions.
Early meeting notes, private correspondence, local absolute paths, `.DS_Store`, and
the stale root prototype remain excluded.

**Evidence:** the F32 demo reproduces outputs `0xBB446E00` and `0xBB446DFF`; the QS8
demo triggers UBSan on `255 * INT32_MAX`; the Lean walkthrough compiles against
`lean-verification@dd1c0ab` and prints the expected outputs and transitive axioms.

**Unresolved:** remote publication is a separate final step after the memory update
and full branch verification.


## 2026-07-16: Publish Research Batch to Fork Main

**Question:** Should the organized research history be published on a separate branch
or directly on the fork's `main`?

**Conclusion:** the project owner selected `main`. The fork's `main` was
fast-forwarded without force from `6acdf7a` through the eight-commit research batch
ending at `bf89dde`. The upstream `keaganchern/SALTy-rn` remote was not modified.

**Evidence:** the push reported `6acdf7a..bf89dde research/lean-ir-e2e -> main`.
The local worktree remained clean and the pre-push E2E gate passed frontend tests,
deterministic regeneration, the 25-job Lean build, proof-token policy, and exported-
axiom audit.

**Boundary:** local `main` continues to track upstream `origin/main`; development
remains on `research/lean-ir-e2e` so upstream comparison stays explicit.

## 2026-10-02: Package NEON and Completed RVV Coq Proofs

**Question:** How should the reduction proofs become a small conventional Coq
project, and which existing RVV instruction proofs should accompany load VL=1?

**Confirmed conclusion:** the owner selected branch `proof/sum` and requested the
other completed RVV instruction proofs. An isolated worktree from `94e88f4`
contains `coq/neon-rvv-reduction`: 131 sources, 20 NEON + 19 RVV generated program
instructions, four bridges and all corresponding compressed original traces.
The original `feat/assembly-reduction-lean@bc8b3b8` research checkout is preserved.

**Evidence:** an independent migration audit confirmed identical proof sources
after reversing namespace changes, except for the exact split of the two program
instruction tables. Both assemblies reproduce all instruction bytes in their
inventories and executable ELF segments. Selected NEON/RVV/bridge extractions
reproduce both trace and generated-Coq hashes. Absolute historical tool paths
are replaced only in recorded runtime configuration copies.

**Confirmed:** all 131 project sources compiled afresh in the existing pinned
Coq/Islaris environment, including both RVV load contracts.

**Confirmed:** recursive `coqchk` passed all 131 modules and dependencies with
`-bytecode-compiler yes`; all 35 exported theorem assumption reports were closed
under the global context. An earlier VM-disabled check was interrupted because
large bitvector conversion was expensive. `verification.json` records the
successful checker environment and the tested manifest hash.

**Unresolved:** a clean external dependency
installation has not been performed. RVV loads VL=2..8 remain unfinished;
conditional whole-program proofs are intentionally outside this slice. The
local PR draft will state those limits and the external extraction trust boundary.

**Confirmed publication:** Git reported `94e88f4..2bbe27e proof/sum -> proof/sum`
on the fork's origin. The project and verification summary are committed; the
PR description remains local at `coq/neon-rvv-reduction/_build/PR_DRAFT.md`.
No GitHub PR was opened.
