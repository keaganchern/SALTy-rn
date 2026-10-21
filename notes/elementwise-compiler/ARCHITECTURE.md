# Elementwise Compiler Architecture

Last updated: 2026-08-29 (Asia/Seoul)

## North Star

For a program whose exact typed intrinsics and execution family are already
supported:

```text
C pair -> one command -> generated implementation/specification stack
       -> proof agent -> Lean-checked result
```

No program-specific Python or Lean source is added.

## Capability Graph

```text
IntrinsicCapability ─────┐
LayoutViewCapability ────┼─> ProgramManifest ─> Models ─> Spec ─> ProofTask
ScheduleFamilyCapability ┘                                      │
                                                               v
                                                         Agent Proof
                                                               │
                                                               v
                                                         Lean Result
```

`CapabilityRegistry.json` and each `ProgramManifest.json` record this graph.

## Artifact Ownership

| Artifact | Producer | Mutable during proof? | Meaning |
|---|---|---:|---|
| input Neon/RVV C | user/corpus | no | source pair |
| intrinsic capability | framework/reviewer | no | exact typed semantic mapping |
| layout/view capability | framework/reviewer | no | scalar memory streams to logical elements |
| schedule-family capability | framework/reviewer | no | reusable execution recognizer and theorem |
| optional external contract | caller/API evidence | no | contextual assumptions absent from C bodies |
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

It is the parser's structural inventory of the program, not a handwritten
intermediate language.

## Logical Element Layout/View

Operator arity and schedule do not determine the logical element representation.
Most initial integer programs use one scalar lane per logical element. A case such
as planar `f32-vcmul` is elementwise only after real and imaginary scalar streams
are grouped into one logical complex element and its two output planes are observed
together.

A reusable layout/view capability defines:

1. how typed memory/value streams form one logical input element;
2. how a logical output element projects back to output streams;
3. the index/length relation between physical streams and logical coordinates;
4. the observation used by the value theorem.

Phase one supports scalar-lane layouts only. Grouped, planar, interleaved, or
multi-output elementwise programs remain `layout-unrecognized` until a reusable
view exists. They do not require a new schedule family merely because their layout
differs.

Multiple flat input streams at the same coordinate remain ordinary elementwise
`zipWith`: for example `output[i] = add(inputA[i], inputB[i])`. Non-overlapping
groups such as `(input[2*i], input[2*i+1])` may later use a grouped-element view.
Overlapping neighborhoods such as `(input[i], input[i+1])` are window/stencil
semantics, not this elementwise family.

## Family Interface

A family capability supplies:

1. a fail-closed structural recognizer;
2. generated model construction rules;
3. legality predicates derived from source/program structure;
4. an observation appropriate to the claim layer;
5. reusable Lean refinement theorems;
6. capability identity and version/hash.

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

## Assertion and Assumption Domains

Do not combine every assertion from both files into one theorem precondition.
Classify each assertion by where it executes:

- an assertion in the entry prefix, before control flow or modeled effects, is an
  entry contract declaration for that side;
- an assertion under a loop or branch is a local proof obligation at that exact
  program point, using the current symbolic values and reach condition;
- an unsupported or effectful assertion expression fails closed.

Let `C_neon` be the supported Neon entry contract and let `C_rvv` be the RVV entry
contract. Phase one requires their normalized typed expression trees to be equal.
The paired-program theorem then proves output equality under this one shared entry
contract. A mismatch returns `entry-contract-mismatch`; phase one does not attempt
contract implication or replacement-coverage claims.

The compiler checks:

1. every reachable local assertion on each side from that side's entry contract
   and path condition;
2. every dynamic layout, schedule, and intrinsic safety condition in the stated
   theorem domain, unless supplied by separately hash-bound caller/API evidence;
3. output equality under the selected domain and explicitly named
   memory/environment assumptions of the selected claim layer.

Static intrinsic restrictions, such as an immediate operand range, are checked by
the compiler rather than added to the theorem precondition. A missing or incorrect
intrinsic semantic definition never becomes a precondition.

The fixed-tail recognizer may automatically discharge a local remainder assertion
only when it exactly follows from the recognized loop exit and tail reach condition.
Every other local assertion fails closed. See `ASSERT_AUDIT.md` for the corpus
classification.

In phase one, entry `assert(...)` is an audited contract declaration under the
pinned preprocessing policy. This is not a theorem about debug abort behavior,
`NDEBUG`, or every preprocessing configuration. Pointer validity, buffer extent,
aliasing, and overread rights belong to the later memory/correspondence layer; the
value theorem records them but cannot prove them from list-valued inputs.

## Content-Addressed Artifact Chain

Canonical serialization and parent hashes prevent artifacts from different runs
or programs from being mixed:

1. `ProgramManifest.json` uses canonical JSON and binds the two source files,
   facades/preprocessed inputs, compiler producer, exact capability ids/digests,
   selected layout/schedule instances, extracted assumptions, and full consumed
   statement/effect inventory.
2. `Models.lean` embeds `manifest_sha256`; its own exact file digest is recorded.
3. `Spec.lean` embeds `manifest_sha256` and `models_sha256`; its exact file digest
   is recorded.
4. `ProofTask.json` uses canonical JSON and binds all three digests, the exact
   writable proof path, module/theorem identity, elaborated expected-type digest,
   checker-policy digest, and expected Lean/toolchain identity.
5. `Result.json` uses canonical JSON and binds `proof_task_sha256`, `proof_sha256`,
   checker/toolchain identity, start/end protected-closure digests, and one terminal
   result state.

Every consumer verifies the complete parent chain before using an artifact. A
filename, module name, or file-presence check is never a provenance edge.

## Result State Machine

```text
discovered
  -> parse-unsupported | parsed
  -> intrinsic-missing/ambiguous | intrinsics-ready
  -> layout-unrecognized | layout-ready
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
The proof agent is outside the logical trust boundary only because acceptance
checks that the protected artifact closure is hash-identical before and after proof
search and treats the designated `Proof.lean` path as the only permitted mutable
artifact in that closure. This is an integrity and reviewer gate, not an OS or
filesystem sandbox; the process may technically have broader write access.

Intrinsic-to-ISA adequacy, C byte-memory refinement, legal architecture traces,
and compiled-binary correctness are additional bridges, not consequences of the
value proof.

## First Acceptance Test

Delete all S8-VMax-specific generator configuration, retain the global max
intrinsic and scalar-layout/fixed-no-tail capabilities, then run the compiler in a
clean temporary checkout/output root.

The anti-special-casing gate uses two positive same-family fixtures and one
negative semantic mutation. One positive fixture may be S8 VMax; the other must use
randomized directories, basenames, function identifiers, and a fresh generated
module namespace. It cannot live under the old example path. The negative fixture
changes one supported side from max to min.

After deleting outputs, deterministic reruns must reproduce them. Framework
tracked files remain byte-identical (`git diff --exit-code`); status may contain
only explicitly allowed generated artifacts and the designated proof under the
temporary output root. The generic compiler path may not use path-based frontend
fallbacks, kernel names, case ids, or manually listed proof targets.
