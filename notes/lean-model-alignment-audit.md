# Lean Model Alignment Audit

Audit date: 2026-07-16 (Asia/Seoul)

## Scope and Pinned Revisions

This audit answers a narrow question: what do the existing Lean theorems prove,
where do their definitions diverge from the referenced C/intrinsic semantics, and
which divergences are acceptable abstractions for the intended project claim?

The historical audit target is:

- `lean-verification@dd1c0ab12dedccc8d1e0296c82cbc3b72c32249f`
- historical symbolic F32 pair at
  `5c9c3f6a1d2373b1c9e55a48a273de8b0bb0f7de`
- current kernel comparison baseline
  `main@6acdf7a522e2b97b96831f8e95b578e6edf42a83`

The current generated-IR prototype is audited separately at:

- branch `research/lean-ir-e2e`
- commit `0eb0f75b7410c9ff59100af4541487716697235d`

No production source file was changed by this audit.

## Direct Answer

**Confirmed:** the structural summary of the proof *shape* is substantially correct:

```text
Neon loop = map/zipWith fNeon
RVV loop  = map/zipWith fRvv
pointwise fNeon = fRvv
--------------------------------
Neon loop = RVV loop
```

`SALT/Kernel/Class.lean` packages the last step for unary map, binary zip, and
broadcast kernels. Once both refinement lemmas and the pointwise lemma exist, the
final theorem is mostly a template application.

**Confirmed:** this does **not** make the whole proof routine. The semantic burden is
in three inputs to the template:

1. whether each hand-written loop really denotes its C implementation;
2. whether `fNeon` and `fRvv` really denote the named intrinsics;
3. whether the pointwise equality is true for the real C/ISA operations.

Several existing families make the pointwise lemma easy by copying the same scalar
body into both sides. That is a valid proof of the stated Lean proposition, but it
also permits the same semantic mistake to occur on both sides.

**Confirmed:** all existing final theorems are valid relative to their Lean
definitions, subject to the documented native `bv_decide` trust extension. They are
not C/ISA correctness theorems because no C-to-Lean or ISA-to-Lean correspondence
bridge is part of their statements or dependencies.

## Claim Levels Used in This Audit

Keep these claims separate:

1. Lean accepts a proof term for the stated proposition.
2. The two Lean implementation models are equal.
3. Each Lean model faithfully denotes a pinned C translation unit.
4. The two C functions are observationally equivalent under an explicit contract.
5. Compiled Arm and RISC-V machine code implement those C semantics.

The historical branch establishes level 1 and parts of level 2 for four semantic
families. It does not establish levels 3-5.

## Findings First

| Severity | Status | Finding | Consequence |
|---|---|---|---|
| Critical | **Confirmed** | Historical Neon VELU uses non-fused `vmlaq_f32`; RVV uses fused `vfmacc`, while both Lean sides use non-fused `mul` then `add`. | A finite normal input produces a 1-ULP output mismatch. The intended bit-equivalence claim is false for that historical pair. |
| Critical | **Confirmed** | `QS8VAddC.computeBias` uses total wrapping `BitVec 32` multiplication, but the pinned C pair uses signed `int32_t` multiplication. Existing Lean preconditions do not prevent overflow. | The Lean theorem includes inputs for which the C source and target have undefined behavior. It cannot be lifted to a C theorem without a no-overflow contract or defined wrapping C. |
| High | **Confirmed** | `QS8ClampEmit` has no ordered-bounds premise. The likely current C source executes max/min in one loop and min/max in its 8-byte/tail paths. | With `min > max`, Lean/RVV and the Neon tail return different bytes. The theorem can match C only under an explicit ordered, representable bounds contract. |
| High | **Confirmed** | Neon/RVV intrinsic files are kernel-specialized list functions, not complete intrinsic semantics. | Their names overstate their scope. They are usable as active-lane value helpers only after a scoped correspondence theorem. |
| High | **Confirmed** | No historical final theorem binds a C AST, source digest, compiler flags, memory model, or ISA model. | `Emit` and `Parsed` names are not evidence of translation provenance. |
| High | **Confirmed** | Eight QS8 final theorems depend on 31 native `bv_decide` axioms through `RoundingEquiv`. | The Lean compiler/native runtime is in the trusted computing base unless the proof is replaced or that policy is accepted explicitly. |
| Medium | **Confirmed** | Historical RVV loops select one `vl = min(remaining, vlmax)` schedule and omit LMUL, masks, tail policy, `vstart`, `vxrm`, `vxsat`, and other state. | The value theorem covers one abstraction, not every legal RVV execution. Map-like kernels can likely be generalized to legal partitions. |
| Medium | **Confirmed** | Default `lake build` imports only the three base families and omits the eight generated-looking families, adequacy, and tests. | A default green build does not check all checked-in Lean modules. |
| Medium | **Confirmed** | The current generated prototype proves a restricted synthetic case, while real `s8-vclamp` is still audit-only. | It is useful infrastructure, not yet the real vertical slice. |

## Complete Lean Inventory

The historical Lean tree contains 52 source units: 50 under `SALT/`, plus
`SALT.lean` and `Main.lean`. It declares 153 public theorems and 11 final kernel
equivalence theorems. The following table accounts for every source unit.

| Files | Count | Audit result |
|---|---:|---|
| `SALT.lean`, `Main.lean` | 2 | Root import and differential-test executable. `SALT.lean` imports only base VAdd, VAddC, and F32VELU families. |
| `SALT/Basic.lean` | 1 | Generic list/BitVec helpers; no C/ISA claim. |
| `SALT/Core/{CoreOp,Lane,CrossISA,Tactic,Adequacy}.lean` | 5 | Scalar vocabulary, list lifting, rounding bridge, tactic, and internal definitional adequacy. `Adequacy` is wrapper-to-CoreOp `rfl`, not ISA adequacy. |
| `SALT/FP/Basic.lean` | 1 | Native `Float32` helpers and table. `fmax` and table commentary are not a complete architectural FP specification. |
| `SALT/Intrinsics/{Neon,RVV}.lean` | 2 | Kernel-specialized list wrappers; incomplete full-intrinsic and architectural state semantics. |
| `SALT/Kernel/Class.lean` | 1 | Generic `map`/`zipWith`/broadcast proof templates. |
| `SALT/Kernel/QS8/Params.lean` | 1 | Shared BitVec parameter record and partial well-formedness predicate. |
| `SALT/Proof/RoundingEquiv.lean` | 1 | Genuine Neon/RVV rounding equivalence for `shift <= 31`; uses native `bv_decide`. |
| `SALT/Test/{Rand,Ref,Differential}.lean` | 3 | Lean CoreOp versus local Lean/Int shadow tests; no C or hardware oracle. |
| `SALT/Kernel/F32VELU/{Params,Core,Neon,RVV,Equivalence}.lean` | 5 | Shared scalar body, two list schedules, and bit-output theorem. Both element functions are `rfl` to `coreElem`. |
| `SALT/Kernel/F32VELUEmit/{Neon,RVV,Equivalence}.lean` | 3 | Second, generation-looking snapshot; Neon/RVV scalar bodies are textually the same and lack generation provenance. |
| `SALT/Kernel/QS8ClampEmit/{Neon,RVV,Equivalence}.lean` | 3 | Identical scalar clamp body plus different chunking. No pinned historical C counterpart. |
| `SALT/Kernel/QS8VAdd/{Neon,RVV,Equivalence}.lean` | 3 | Base binary add model with one substantive rounding bridge. |
| `SALT/Kernel/QS8VAddEmit/{Neon,RVV,Equivalence}.lean` | 3 | Algorithmically duplicates base VAdd with formatting/local-name changes. |
| `SALT/Kernel/QS8VAddParsed/{Neon,RVV,Equivalence}.lean` | 3 | Namespace-level duplicate of Emit; no parser certificate. |
| `SALT/Kernel/QS8VAddC/{Neon,RVV,Equivalence}.lean` | 3 | Base broadcast add model; bias equality is reflexive BitVec computation. |
| `SALT/Kernel/QS8VAddCEmit/{Neon,RVV,Equivalence}.lean` | 3 | Algorithmically duplicates base VAddC. |
| `SALT/Kernel/QS8VAddCParsed/{Neon,RVV,Equivalence}.lean` | 3 | Duplicate of Emit apart from a local name. |
| `SALT/Kernel/QS8VAddCParsedFull/{Neon,RVV,Equivalence}.lean` | 3 | Same algorithm with C-like locals/inlining. |
| `SALT/Kernel/QS8VAddCParsedFully/{Neon,RVV,Equivalence}.lean` | 3 | Further local rewrites/reassociation; same proof contract. |
| **Total** | **52** | Every unit was compiled explicitly during this audit. |

### Final Theorem Families

| Final theorem | Semantic family | Distinct semantic content |
|---|---|---|
| `f32_velu_equiv` | F32VELU | Shared native-Float32 scalar body; base list schedules. |
| `f32veluemit_equiv` | F32VELU | Same scalar algorithm; Emit formatting. |
| `qs8clampemit_equiv` | S8 clamp | Identical element body; fixed-8 versus selected RVV chunking. |
| `qs8_vadd_equiv` | QS8 VAdd | Integer pipeline plus rounding equivalence. |
| `qs8vaddemit_equiv` | QS8 VAdd | Duplicate presentation. |
| `qs8vaddparsed_equiv` | QS8 VAdd | Duplicate presentation. |
| `qs8_vaddc_equiv` | QS8 VAddC | Broadcast bias plus rounding equivalence. |
| `qs8vaddcemit_equiv` | QS8 VAddC | Duplicate presentation. |
| `qs8vaddcparsed_equiv` | QS8 VAddC | Duplicate presentation. |
| `qs8vaddcparsedfull_equiv` | QS8 VAddC | Duplicate presentation. |
| `qs8vaddcparsedfully_equiv` | QS8 VAddC | Duplicate presentation. |

There are 11 final theorems but only four semantic families. The variants do not
provide independent semantic validation because there are no cross-stage theorems,
generator inputs, source hashes, or regeneration commands in the historical branch.

## Proof Anatomy

`SALT/Kernel/Class.lean:19-28` proves unary equivalence from two map refinements and
one pointwise equality. Lines 36-48 do the same for `zipWith`; lines 56-67 add a
broadcast-bias equality.

**Confirmed:** the final applications are templates.

**Confirmed:** these preceding lemmas are not automatically trustworthy:

- the loop-to-map lemma establishes only equality between two Lean definitions;
- the element lemma establishes equality between two Lean scalar definitions;
- neither statement mentions the C function that the definition is said to mirror.

For QS8, the cross-ISA rounding lemma is real mathematical content. For F32VELU and
Clamp, the element lemma is essentially reflexive because both sides use the same
formula. This is the main reason a clean Lean proof can coexist with a C/ISA
misalignment.

## Shared Semantic Layers

### `CoreOp` and `Adequacy`

**Confirmed:** `CoreOp.lean` defines total BitVec arithmetic and a small FP operator
set. It has no FMA constructor, no FP environment, no exception flags, and no
architecture-specific FP max/min constructors.

**Confirmed:** every intrinsic theorem in `Core/Adequacy.lean` closes by `rfl`. For
example, `vsubl_s8_core` unfolds a wrapper into the exact CoreOp expression used to
define it. This checks internal layering, not correspondence with Arm ACLE or the
RISC-V ISA.

### Neon wrappers

**Confirmed:** `Intrinsics/Neon.lean` models arbitrary `List`s instead of fixed-size
Neon registers and specializes several signatures to the kernel's broadcast use:

- `vmulq_s32` accepts a scalar second argument although the real intrinsic is
  vector-vector;
- `vmlaq_s32`, `vqaddq_s16`, `vmax_s8`, and `vmin_s8` similarly bake in broadcasts;
- `vrshlq_s32` accepts one `Nat` and only performs right-shift rounding, whereas the
  real intrinsic accepts a vector of signed per-lane shift controls and supports
  both left and right shifts.

The official [Arm Neon intrinsic reference](https://arm-software.github.io/acle/neon_intrinsics/advsimd.html)
shows the real signatures and instruction mappings.

**Acceptance judgment:** this is acceptable as a named active-lane specialization
only if a bridge proves that the actual call site constructs precisely those
broadcast controls and remains in the modeled shift range. It is not acceptable as
the global definition of the intrinsic under its unqualified ACLE name.

### RVV wrappers

**Confirmed:** `Intrinsics/RVV.lean` explicitly omits LMUL and also omits `vl`, mask,
tail/mask policy, `vstart`, `vtype`, `vxrm`, `vxsat`, and FP/CSR state from operation
results. `vnclip` is hard-coded to shift zero and loses the saturation flag.

**Confirmed concrete mismatch:** the Lean non-rounding shifts use the full `Nat`
amount. The ISA uses only the low `lg2(SEW)` bits. Therefore:

```text
Lean: vsll_vx_i8 [1] 8 = [0]
RVV:  shift control 8 is masked to 0, so result = [1]
```

The official [RISC-V V specification](https://docs.riscv.org/reference/isa/unpriv/v-st-ext)
also specifies the full vector state and legal `vl` range. For the existing QS8
kernel path, `shift <= 31` at SEW=32 makes shift masking unobservable; the global
wrapper remains inaccurate outside that restricted use.

**Confirmed:** each historical loop takes a fixed positive `vlmax` and chooses
`min(remaining, vlmax)`. For `VLMAX < AVL < 2*VLMAX`, an implementation may instead
choose any `vl` in `ceil(AVL/2)..VLMAX`. The current theorem therefore covers one
deterministic value schedule, not all legal executions.

**Acceptance judgment:** for pure lane-map kernels, omitting inactive architectural
state and proving over legal positive partitions is a defensible output-only
abstraction. The current fixed schedule is incomplete rather than necessarily wrong.

## Kernel Family Audits

### QS8VAdd

**Confirmed:** this is the strongest historical example. The pinned C source and
target files exist, and the Lean lane formula follows their intended sequence:
widen/subtract zero points, multiply/accumulate in 32 bits, rounding shift,
saturating narrowing, output zero point, and clamp.

**Confirmed:** `elem_equiv` is not purely reflexive. It uses the theorem that Neon
rounding shift and RVV RNU rounding shift agree for the kernel's `shift <= 31`
domain. This is substantive cross-model reasoning.

**Confirmed limitations:** the Lean theorem permits arbitrary/empty lists, abstracts
the source's fixed chunks and tail overreads, and says nothing about pointers,
aliasing, partial stores, C undefined behavior, or RVV state. Its `WellFormedParams`
also contains conditions unused by the final internal equality.

**Inference:** the active-lane output formula is plausible for the pinned integer
pair. A C-level claim still needs extraction, memory, contract, and ISA bridges.

### QS8VAddC

**Confirmed:** this family adds a pre-loop scalar bias. Both Lean sides define it as
wrapping `BitVec 32` multiplication, so `computeBias_eq` is immediate.

**Confirmed blocker:** the pinned C source computes:

```c
const int32_t vbias_val = vxb * vb;
```

Signed overflow is undefined in C. `QS8AddMinmaxParams.WellFormedParams` requires a
positive multiplier but supplies no no-overflow bound. The persisted UBSan demo
`notes/demos/qs8-vaddc-overflow.c` uses:

```text
input_b = 127, b_zero_point = -128, b_multiplier = INT32_MAX
255 * 2147483647
```

UBSan reports signed integer overflow, while Lean deterministically wraps modulo
`2^32`.

**Acceptance judgment:** not acceptable for a C theorem as currently quantified.
Add and prove a no-overflow contract, or change and bind the C semantics to an
explicitly wrapping operation.

### QS8ClampEmit versus current `s8-vclamp`

**Confirmed:** no clamp C pair exists in the pinned historical branch. The likely
intended current counterpart is `kernels/{source,target}/s8-vclamp.c`,
but that relationship is an inference because the Lean artifact contains no source
binding.

**Confirmed:** the current Neon source uses max then min in the 64-byte loop, but min
then max in the 8-byte and tail paths. RVV and both Lean element functions use max
then min. The Lean theorem has no `output_min <= output_max` premise and reuses a
BitVec8 QS8-add parameter record, while the C fields are `int32_t` narrowed to
`int8_t`.

Concrete value counterexample:

```text
x = 0, min = 100, max = -100
Lean / RVV / Neon 64-byte path: min(max(0, 100), -100) = -100
Neon 8-byte and tail path:      max(min(0, -100), 100) = 100
```

The existing runtime harness fixes `batch = 64` and ordered bounds, so it does not
exercise this case.

**Acceptance judgment:** the abstraction is acceptable only under explicit bounds
`-128 <= min <= max <= 127` (or a separately specified conversion policy). Under
ordered bounds, the two clamp orders coincide. Without the contract, the intended
full-function theorem is false.

### F32VELU and F32VELUEmit

**Confirmed:** `F32VELU.Neon.neonElemFn` and `F32VELU.RVV.rvvElemFn` each reduce by
`rfl` to the same `Core.coreElem`. In Emit, the two scalar functions are directly
identical. The final theorem therefore validates a common model, not two independent
translations.

**Confirmed:** Lean core `Float32.add`, `mul`, `ofBits`, and `toBits` are opaque and
extern-backed. Lean documents them as IEEE binary32 runtime operations, but they do
not reduce in the kernel. The proof can use congruence of identical opaque calls; it
cannot prove their rounding, NaN, signed-zero, subnormal, or exception behavior.
See the official [Lean Float32 API](https://lean-lang.org/doc/api/Init/Data/Float32.html).

**Confirmed FMA mismatch:** Arm ACLE defines `vmlaq_f32` as
`vadd(a, vmul(b, c))`, with two operations. RISC-V `vfmacc` is fused. The repository's
symbolic shims correctly distinguish these operations, but the Lean RVV body uses
the Neon non-fused expression.

The full scalar ELU pipeline, with `prescale = alpha = beta = 1`, has a finite-normal
counterexample preserved in `notes/demos/f32-velu-fma-counterexample.c`:

```text
x                  = 0xBB44B983 (-0x1.897306p-9)
Neon separate      = 0xBB446E00 (-0x1.88dcp-9)
RVV fused          = 0xBB446DFF (-0x1.88dbfep-9)
```

This is a one-ULP final output difference, not merely an intermediate mismatch.

**Confirmed max mismatch:** Arm `vmaxq_f32` maps to `FMAX`; RVV `vfmax` implements
`maximumNumber`. The historical Neon SMT shim acknowledges the divergence at
`src/verification/neon/intrinsics.hpp:1035-1119` and deliberately dispatches ordinary
Neon `vmax` to the maxNum helper to match RVV. That shim is an engineering oracle,
not faithful Arm semantics for unrestricted NaNs.

Lean's helper is:

```lean
def fmax (a b : Float32) := if b <= a then a else b
```

It is asymmetric on NaNs and signed zero and is not a complete model of either
architectural operation. Although `WellFormedParams` and `InDomain` require finite
values, `f32_velu_equiv` does not take either hypothesis.

**Confirmed provenance gap:** the comments cite
`kernels/source/f32-velu.c`, which does not exist on the pinned branch or current
main. A historical symbolic Neon/RVV pair exists at commit `5c9c3f6`; its Neon main
loop is 16-wide and its RVV side uses fused operations. The Lean 12/4 schedule likely
resembles an external XNNPACK x12 VELU kernel, but no hash or generator binds it.
These are different possible sources and must not be conflated.

**Acceptance judgment:** loop chunking, table-address abstraction, and ignored tail
lanes can be acceptable for an output-only value theorem under a memory/FP contract.
Replacing fused RVV operations with non-fused operations, replacing Arm FMAX with a
different NaN policy, and omitting the domain from the final theorem are not
acceptable for bit-exact C/ISA equivalence.

#### Historical symbolic verifier does not close the gap

**Confirmed:** the deleted `tests/verifier/f32-velu_verifier.cpp` is not a certificate
that the fused and non-fused implementations passed verification:

- it fixes `prescale = alpha = beta = 1` rather than quantifying over parameters;
- it runs four elements, so the Neon 16-element main loop is not reached;
- its LUT differs from the later `xnn_minimal.h`/Lean table starting at index 3;
- if result lengths differ, it compares only their common prefix;
- it treats every pair of NaNs as equal and every pair of subnormal-or-zero results
  as equal, which is weaker than bit equality;
- no checked-in successful run or proof certificate was found.

The finite-normal counterexample in this audit is outside the verifier's NaN/tiny
quotients. A sound run over the intended pair and table should therefore find a
counterexample rather than prove universal bit equality. Current
`src/verification/core/comparison.hpp` still deliberately equates arbitrary NaN bit
patterns, so its observational relation must also be stated separately from bitwise
equality.

## Proof Correctness and Trusted Computing Base

**Confirmed build results:** every one of the 52 source units compiled. The default
`lake build` ran a 25-job import closure, but omitted all Emit/Parsed/Clamp modules;
they were therefore also compiled explicitly. No source contains `sorry`, `admit`,
an explicit `axiom`, or `unsafe`.

**Confirmed differential result:**

```text
lake exe diff-test 0xCAFEF00DBEEF 4096
9/9 checks passed; 36,906 samples
```

These checks compare CoreOp with a local Lean/Int shadow reference. They do not run
the checked-in C or hardware and do not validate kernel provenance.

**Confirmed exported-axiom result:**

- F32VELU and F32VELUEmit depend on `propext`, `Classical.choice`, and `Quot.sound`.
- QS8ClampEmit depends on `propext` and `Quot.sound`.
- All eight VAdd/VAddC finals also depend on 31
  `rounding_shift_equiv._native.bv_decide.ax_*` axioms.

Lean's native decision procedure validates a generated result through compiled code,
so the compiler/native runtime is trusted for those theorems. This is not the same as
a `sorry`, but it must be an explicit project trust decision and a CI policy.

## Generation and Provenance Audit

**Confirmed:** the historical branch contains no Lean generator, source manifest,
hash, Clang command, AST mapping, or regeneration test for any `Emit`/`Parsed*`
family. Searches across the available upstream branches found generators for C++
verification harnesses, not these Lean files.

**Confirmed:** all generated-looking families first appear together in `dd1c0ab`,
whose commit subject describes only `.lake` cleanup even though it adds or rewrites
thousands of non-build-artifact lines. There is no intermediate generation history.

**Inference:** the repeated files look like snapshots from translation experiments.
That is not enough evidence to state that they were generated from the cited C, nor
that `Parsed`, `Full`, and `Fully` are certified stages.

## Current `C -> IR -> Lean` Prototype Boundary

This section concerns `research/lean-ir-e2e@0eb0f75`, not the historical upstream
Lean branch.

### Synthetic `s8-clamp16`

**Confirmed:** this is a real restricted semantic-IR E2E:

- a fail-closed Python/Clang frontend consumes two synthetic C translation units;
- all 47 Neon and 71 RVV body nodes are classified as translated references;
- generated typed operations are executed by a Lean interpreter;
- the theorem covers any positive partition totaling 16;
- under a fixed memory/parameter contract, it proves success, equal final memory and
  output, an outside frame, and a 16-address write summary;
- current exported theorems use only `propext` and `Quot.sound`.

**Confirmed boundary:** this is fixed-length synthetic C, not the real kernel. The
RVV loop is recognized by Python and represented as an external
`positiveStripMine` control mode rather than a general CFG. `vsetvl` returns the
caller-provided chunk length. The memory executor reads all 16 bytes first, computes
list values, then performs one transactional final write; its write summary is
constructed from output length rather than accumulated store effects.

**Acceptance judgment:** these quotients are defensible for the stated fixed-16,
disjoint-or-exact-in-place, final-output theorem. They do not establish full C memory
execution or ISA trace equivalence.

### Artifact binding

**Confirmed:** Lean checks equality among recorded digest strings, ranges, function
identity, reference existence, typed operation shapes, registry identity, and local
use order. `Sha256Claim` is only a string; Lean does not read and hash the C/header/
extractor files. Python regeneration performs the real hash/freshness check.

**Confirmed:** the source/target coverage-binding facts are separate theorems in
`S8Clamp16/Binding.lean`. `generated_success_under_contract` does not take them as
premises, and `executeChunk` does not inspect an artifact envelope. The checked-in
suite establishes both facts side by side, but the exported execution theorem alone
is not a bundled certificate for a particular C artifact.

**Confirmed:** `hasConsistentCoverageBinding` checks reference-set consistency, not
that an AST construct was semantically preserved by a particular lowering rule. The
intentional `vmin -> vmax` mutation still has a structurally bound IR and then fails
semantically in Lean. This is a useful negative test, and also demonstrates that a
common-mode lowering error remains possible.

**Proposal:** bundle binding/registry theorems into the final certified-program
premise instead of leaving them as adjacent independent facts.

### Real `s8-vclamp`

**Confirmed:** the real current-main artifact has 399/399 Neon and 121/121 RVV AST
nodes under strict shape auditing, but every entry is `AST_AUDIT_ONLY` and
`claimsFullTranslation = false`. Its value-schedule theorem is handwritten and does
not execute that artifact.

**Confirmed:** the synthetic IR proof and real-kernel value theorem are two separate
lines of work. They share a partition definition but are not connected by a theorem.

**Confirmed freshness nuance:** the synthetic gate regenerates and byte-compares
both checked-in manifest and Lean output. The real-kernel test only compares two
temporary regenerations; the checked-in real manifest/output were fresh during this
audit, but current CI would not detect future drift.

## Acceptability Matrix

| Modeling choice | Classification | Required condition |
|---|---|---|
| Lists instead of physical Neon registers | Acceptable abstraction | State that the theorem is active-lane value semantics and prove call-site chunk correspondence. |
| Broadcast-specialized intrinsic helper | Acceptable specialization | Rename/scope it and prove the actual operand is a broadcast. |
| Omit inactive lanes and architectural status | Acceptable observation quotient | C API does not expose them; no omitted state changes later visible behavior. |
| Fixed RVV `min(remaining,VLMAX)` schedule | Incomplete scope | Generalize to all legal schedules or explicitly claim one implementation policy. |
| Transactional memory for fixed clamp16 | Acceptable microcase quotient | Disjoint or exact in-place buffers and only final memory/output observed. |
| Ignore Neon tail overread/partial stores | Not acceptable for real kernel | Add readable padding, exact write footprint, and physical tail semantics. |
| Wrapping Lean bias versus signed-overflow C | Blocker | Add no-overflow contract or defined wrapping C semantics. |
| Clamp equality without ordered bounds | Blocker | Add representable `min <= max` contract. |
| RVV FMA modeled as non-fused mul/add | Blocker | Preserve FMA as a distinct IR/semantic operation; expected bit equality may be false. |
| Arm FMAX silently changed to maxNum | Blocker outside finite domain | Preserve intrinsic identity and make finite/NaN policy explicit. |
| Generate spec and both impls from one unchecked IR | Common-mode risk | Primary theorem should compare source IR and target IR directly; use an independently reviewed spec only as additional evidence. |
| Agent-generated proof after fixed semantics | Acceptable | Freeze theorem, definitions, contract, observation, and axiom policy; Lean and CI check the proof. |

## Recommended Repair Order

1. **Proposal:** label historical results accurately as Lean-model equivalence, not C
   or ISA equivalence.
2. **Proposal:** keep the accepted integer-first policy. Reject FP syntax fail-closed
   until the IR has distinct `fma`, `mul`, `add`, Arm FMAX, RVV maximumNumber, and an
   explicit FP profile.
3. **Proposal:** complete real `s8-vclamp` semantic lowering: 64/8/tail control,
   overread contract, 4/2/1 stores, actual memory effects, and arbitrary batch.
4. **Proposal:** add the ordered/representable clamp contract and VAddC no-overflow
   contract before claiming C correspondence.
5. **Proposal:** quantify the RVV theorem over every legal `vsetvl` trace, then prove
   the ISA trace relation to the positive-partition model.
6. **Proposal:** add per-entry lowering certificates and bind artifact/registry checks
   into the exported theorem object. Add real-artifact byte freshness to CI.
7. **Proposal:** add independent semantic assurance: official model review,
   differential tests against C/hardware/SoftFloat where appropriate, and negative
   regressions for the three counterexamples in this report.
8. **Proposal:** make CI compile all 52 historical modules and run `#print axioms` on
   every exported theorem; decide explicitly whether native axioms are allowed.

## Reproduction Commands

From the repository root:

```sh
clang -std=c11 -O2 -ffp-contract=off \
  notes/demos/f32-velu-fma-counterexample.c -lm \
  -o /tmp/f32-velu-fma-counterexample
/tmp/f32-velu-fma-counterexample

clang -std=c11 -O1 -fsanitize=undefined \
  notes/demos/qs8-vaddc-overflow.c \
  -o /tmp/qs8-vaddc-overflow
/tmp/qs8-vaddc-overflow

python3 prototype/neon2lean/tools/check_e2e.py --repo-root .
```

The FMA demo returns nonzero precisely when the two outputs unexpectedly agree. The
UBSan demo is expected to report signed integer overflow.

## Bottom Line

**Confirmed:** the existing Lean proofs are internally correct theorems over their
definitions. The proof architecture is reusable, and QS8VAdd contains a meaningful
cross-ISA rounding argument.

**Confirmed:** there are already proven-looking families with real semantic
misalignment. The most serious is not a weakness in Lean's proof engine; it is that
the definitions made Neon and RVV equal before the proof began.

**Proposal:** continue `C -> typed semantic IR -> Lean`, but treat frontend
correspondence, intrinsic identity, contracts, memory/control effects, artifact
binding, and independent semantic validation as part of the verified pipeline. Once
those are fixed, the final proof can safely be template-generated and delegated to
an agent.
