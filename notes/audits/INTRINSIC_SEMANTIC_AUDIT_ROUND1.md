# Intrinsic Semantic Audit — Multi-Stage Closure

Audit date: 2026-08-30 (Asia/Seoul)
Scope: all 184 semantically distinct exact variants in `IntrinsicRegistry.json`

## Outcome

**Confirmed:** the deterministic master ledger contains one row per final exact
`capability_id`. It joins real C call sites, the pinned official Arm/RISC-V
prototype and selector, the exact Lean definition, executable or traceable
evidence, explicit conditions, dependent programs, and content hashes.

| Current verdict | Exact variants |
|---|---:|
| confirmed at the recorded scope | 131 |
| conditional on recorded state/input/scope assumptions | 43 |
| needs deeper memory/`vsetvl` audit | 10 |
| suspected modeling bug | 0 |
| confirmed modeling bug | 0 |
| total | 184 |

The 180 variants used by the current nineteen scalar programs are review subjects;
the remaining four registry variants are unused. Review freshness and semantic
depth remain separate axes. None of the evidence below establishes full C
abstract-machine, compiler, machine-code, or complete ISA-state equivalence.

## Why 189 Became 184

**Confirmed:** the earlier 189 count included five duplicate semantic audit
identities:

1. a second `vrshlq_s32` descriptor with the same intended operation;
2. four unused Neon `vmax_s8`/`vmaxq_s8`/`vmin_s8`/`vminq_s8` descriptors that
   scalarized a vector operand even though faithful vector-vector capabilities
   already existed.

The shift descriptor was repaired and collapsed. The max/min descriptors were
changed to faithful vector-vector identity lowering and then collapsed onto the
existing exact capabilities. The final count therefore removes duplicate rows; it
does not remove supported behavior or a C call site.

## Repaired Modeling Bugs

### Neon `vrshlq_s32`

The old helper wrapped the rounding temporary before an oversized arithmetic
right shift and used an unsigned interpretation of the low shift byte. Native
AArch64 probes reproduced the mismatch. The Lean implementation now uses an
integer temporary, returns zero for right counts at least 32, and interprets the
low byte as signed. The faithful vector-vector descriptor preserves
`vdupq_n_s32(-shift)`; bridge lemmas recover the scalar kernel form only after the
reviewed broadcast and `shift ≤ 31` condition are supplied. Five values across all
256 signed-byte counts pass the Lean regression, and the native evidence contains
75 architecture cases.

### RVV `vssra.vx`

A real RVV C intrinsic compiled by LLVM and executed by Spike returns `1` for
`input=1`, `shift=32`, RNU because the instruction masks the shift to the low five
bits. The old Lean helper used raw `Nat` and returned zero. It now uses
`shift % 32`; the architectural rounding theorem and dependent proofs were updated.
The active audit plus the retained repaired-regression subject pass 232/232 P1
integer architecture/Lean vectors.

### Exact immediate evidence

The intrinsic-audit matcher now distinguishes an exact immediate, a dynamic
compatible example, and an actual conflict. An RDN descriptor can no longer inherit
an RNU API example merely because the call arity matches.

## Differential and Trace Evidence

| Audit group | Exact subjects | Executed/checked evidence | Result | Honest scope |
|---|---:|---:|---|---|
| FP0–FP4 | 28 | 191 architecture/Lean vectors | 191 pass, 0 mismatch | L3 sampled pure value |
| I2/I3 plus repaired RVV regression | 20 | 232 architecture/Lean vectors | 232 pass, 0 mismatch | L3 sampled active-lane value |
| current I0/I1 | 65 | 378 architecture/Lean vectors | 378 pass, 0 mismatch | L3 sampled; 3 broadcast-conditional |
| S0/S1/S2 | 68 | 418 C calls, 246 bindings | 68 pass trace checks | L2 trace or L3 generator mutation, not ISA correctness |

The FP matrix covers NaN classes, signaling/quiet behavior, payloads, signed zero,
subnormals, conversions, comparisons, selection, sign injection, operand order,
division, and square root. The integer matrices cover signed/unsigned boundaries,
saturation, narrowing, shift extremes, rounding modes represented by each exact
descriptor, and repaired shift-mask regressions. These are deliberately recorded
as sampled evidence rather than exhaustive proofs.

## Remaining Conditions and Deep Gaps

1. Three I1 descriptors (`vmulq_s32`, `vmlaq_s32`, `vqaddq_s16`) use a scalar Lean
   helper only because the current C operand is proven to come from a uniform
   broadcast. A non-uniform mutation is rejected fail-closed. Full vector-vector
   semantics remain a useful cleanup, but current program calls are covered.
2. FP state assumptions, including the audited Arm RN/FZ=0/DN=0/AH=0 scope and
   relevant RVV rounding state, remain explicit. Exception flags and traps are not
   part of the pure-value claim.
3. Saturation/rounding architectural state such as `vxsat`/`vxrm` is conditional
   where the current Lean claim observes only active-lane values.
4. Seven RVV loads/stores and three `vsetvl` subjects still need an independent
   register/memory/state correspondence audit. Their present evidence proves
   traceable lowering or generator behavior, not ISA correctness.
5. L4 adequacy remains unestablished for every row because there is no theorem to
   an independent formal Arm/RISC-V ISA model.

## Program Rerun

After the semantic fixes and final 184-row regeneration, the nineteen scalar
program outcomes remain:

- 2 `verified(value)`: `f32-f16-vcvt`, `f32-vrndne`;
- 10 `counterexample`: nine floating exact-bit NaN differences plus the
  non-NaN, missing-bound `s8-vclamp` phase witness;
- 7 `external-condition-missing`: quantized programs whose required caller or
  initializer conditions have not been established.

The source-of-truth artifacts are
`verification/elementwise-compiler/SemanticAuditLedger.json`,
`verification/elementwise-compiler/*DifferentialAudit.json`, and
`notes/audits/intrinsic-semantic-audit.csv`. The spreadsheet is a rendered view of
the ledger, not an authority that can promote a theorem claim.
