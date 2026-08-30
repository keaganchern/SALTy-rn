# Intrinsic Semantic Audit — Final Independent Review

Review date: 2026-08-30 (Asia/Seoul)
Reviewer role: independent convergence reviewer
Reviewed tree: current shared worktree; no commit was created by the reviewer

## Verdict

Verdict: GO (180/180)

Verdict: GO (19/19)

These verdicts approve the 180 exact capabilities used by the current nineteen
scalar programs and the nineteen exact program outcomes at their recorded claim
scopes. They do **not** promote sampled value evidence to exhaustive intrinsic
semantics, and they do not establish C abstract-machine, compiler, binary, or
complete Arm/RISC-V ISA-state correspondence.

The exact approved `program_id` set, in `ProgramReviewPlan.json` order, is:

1. `f32-f16-vcvt`
2. `f32-vadd`
3. `f32-vdiv`
4. `f32-vlrelu`
5. `f32-vmax`
6. `f32-vmin`
7. `f32-vmul`
8. `f32-vmulc`
9. `f32-vrndne`
10. `f32-vsqrt`
11. `f32-vsub`
12. `qs8-f32-vcvt`
13. `qs8-vadd-minmax`
14. `qs8-vcvt`
15. `qs8-vlrelu`
16. `qs8-vmul-minmax-fp32`
17. `qu8-f32-vcvt`
18. `qu8-vadd-minmax`
19. `s8-vclamp`

## Confirmed Findings

### Inventory and closure

- The final registry, intrinsic audit, master CSV, and semantic ledger contain
  184 unique `capability_id` values: 103 Neon and 81 RVV. The live review plan
  uses 180; four are unused.
- The earlier count of 189 contained five duplicate semantic identities: one
  `vrshlq_s32` descriptor and four scalarized max/min descriptors. Their faithful
  vector-vector replacements collapse onto existing capabilities. No supported C
  call or modeled behavior was removed.
- `IntrinsicReviewChecks.json` contains 180 unique subjects and every status is
  `passed`. `ProgramReviewChecks.json` contains the nineteen program IDs above,
  every status is `passed`, and its intrinsic closure records 180 used, 180
  reviewed, and 180 Lean-checked capabilities.
- All ten parent files recorded by `SemanticAuditLedger.json` exist and their
  SHA-256 digests match. The differential audits select semantic families from
  the stable `IntrinsicReviewPlan.json`; the master semantic ledger consumes the
  differential artifacts. It does not serve as their semantic-family parent, so
  the former master/audit circular hash dependency is absent.

### Rounding-shift repair

- Arm `SRSHL`/`vrshlq_s32` uses the signed low byte of each shift lane. Negative
  counts perform a signed rounding right shift; right counts of at least 32 yield
  zero for a 32-bit lane. In the reviewed RNU range, the result is equivalent to
  `(x + 2^(d-1)) >> d` using an unbounded integer temporary. The old 64-bit
  `BitVec` temporary could wrap for oversized counts; the repaired Lean helper
  cannot.
- RVV `vssra.vx` uses only the low `log2(SEW)` shift bits. For SEW=32 the Lean
  model now uses `shift % 32`. RNU is modeled as arithmetic shift plus source bit
  `d-1`; the signed tie cases, including negative values, match the pinned ISA
  rule and the Spike executions.
- The two architectures are not globally equivalent for every raw count. For
  example, an RVV count of 32 has effective count zero, while an Arm right count
  of 32 yields zero. Accordingly, `rounding_shift_equiv` remains restricted to
  `shift <= 31`, and the RVV architectural bridge states the masked count
  explicitly. This restriction is necessary, not a proof escape.
- The faithful Neon descriptor maps the vector-vector intrinsic to
  `vrshlq_s32_vec`. The generated QS8 proof recovers the older scalar kernel
  helper only through an explicit broadcast-negation bridge and
  `p.shift.toNat <= 31`; the final theorem supplies that premise from the existing
  `WellFormedParams` contract.

### Max/min descriptor cleanup

- The four repaired Neon max/min descriptors now preserve both vector operands
  with identity lowering. The scalar kernel form is recovered only by the explicit
  `List.replicate` bridge lemmas used at the real broadcast call sites.
- The bridge lemmas require the operand length needed to identify the broadcast
  and prove lane-wise equality. They do not claim that arbitrary vector-vector
  max/min equals a scalar operation.

### Proof integrity

- The reviewed shift and generated QS8 proof files contain no `sorry`, `admit`,
  new axiom, `unsafe`, or `native_decide` escape.
- The QS8 bridge proof was made explicit with rewrite/simplification steps. No
  heartbeat increase was used to hide an unresolved elaboration problem.
- The strengthened intermediate theorem premise is discharged from the public
  theorem's pre-existing well-formedness assumption. The public equivalence
  statement was not weakened.

## Executable Evidence Rechecked

The reviewer independently reran the following gates on the final 184-capability
tree:

| Gate | Result |
|---|---:|
| FP0-FP4 architecture/Lean differential audit | 191/191 passed |
| I2/I3 plus repaired RVV regression audit | 232/232 passed |
| current I0/I1 architecture/Lean differential audit | 378/378 passed; 3 subjects remain explicitly conditional |
| structural/schedule audit | 68/68 passed; all 68 remain explicitly outside ISA-correctness claims |
| targeted differential-audit tests | 29 passed |
| Lean backend tests | 194 passed |
| `generate_cases --check` | passed |
| `SALT.Proof.RoundingEquiv`, `SALT.Test.IntegerIntrinsics`, and generated QS8 proof build | passed |

For the two repaired rounding roots specifically:

- the Lean SRSHL regression crosses five boundary values with all 256 signed-byte
  counts (1280 cases); the native AArch64 probe executes real `srshl.4s` and passes
  75 representative boundary cases;
- both the current-used RVV capability and the retained explicit repaired
  regression execute 43 cases through the real C intrinsic compiled by LLVM and
  run by Spike. The matrix covers values `{0, 1, -1, INT_MIN, INT_MAX}`, shifts
  `{0, 1, 31, 32, 33, 63, 64, RV64_SIZE_MAX}`, and positive/negative shift-one
  rounding cases. Both are 43/43.

This evidence is sufficient to mark the two discovered modeling bugs **fixed**
and their architecture comparison **L3-sampled**. It is not sufficient to label
either whole intrinsic exhaustive, L4, or a full state correspondence theorem.

## Program Outcomes

The final content-addressed plan records and the checks reproduce:

- 2 `verified(value)`: `f32-f16-vcvt`, `f32-vrndne`;
- 10 `counterexample`: the nine floating exact-bit/NaN-related program witnesses
  and the non-NaN `s8-vclamp` phase witness;
- 7 `external-condition-missing`: the seven quantized programs listed in the
  approved program set above.

The program verdict approves these exact outcomes, including honest blocked or
counterexample outcomes. It does not assert that all nineteen programs are
equivalent.

## Remaining Non-Blocking Limits

- Forty-three master-ledger rows remain conditional on their recorded
  architecture, state, broadcast, or input assumptions.
- Ten load/store/`vsetvl` rows remain `needs_deep_audit`; their traceability or
  generator evidence is not described as ISA semantic correctness.
- `vxsat`, exception flags/traps, inactive and tail lanes, memory/register state,
  compiler correspondence, and L4 adequacy remain outside the relevant pure-value
  claims where the artifacts say so.
- A now-unused private width lemma in `RoundingEquiv.lean` can be removed as
  cleanup, but it is not referenced by the proof and is not a correctness issue.

## Final Assessment

**Confirmed:** no semantic, proof-integrity, inventory, hash-closure, or current
publication blocker remains for the scoped 180/180 intrinsic review and 19/19
program-outcome review. The current documentation is appropriately conservative:
sampled evidence remains sampled, conditional rows remain conditional, and the
ten structural memory/`vsetvl` gaps remain visible rather than being promoted.
