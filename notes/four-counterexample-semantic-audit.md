# Four-Counterexample Semantic Audit

Audit date: 2026-08-30 (Asia/Seoul)
Repository: `feat/elementwise-compiler@cc53aa51455d24ffd151404ba94bf3000e2a84c8`

## Bottom line

| Case | Checked claim | Classification | Does the checked witness reflect the C pair? |
|---|---|---|---|
| `f32-vmax` | `completeValueEquivalenceClaim` | real source/target value gap | yes |
| `f32-vmin` | `completeValueEquivalenceClaim` | real source/target value gap | yes |
| `f32-vrndne` | `completeValueEquivalenceClaim` | repaired Lean-model artifact under `FPCR.DN=0`; now proved | no |
| `s8-vclamp` | `neonPhaseFunctionsEqualClaim` | real source phase-order gap; it also refutes the complete claim at length 1 | yes, when `min > max` |

**Confirmed:** the four outcomes must not be described as one “NaN semantic gap.”
The two max/min cases are genuine NaN-related instruction differences; the rounding
case was a NaN-related modeling false positive and has now been repaired;
the clamp case is a non-floating, non-NaN program-order difference.

This audit remains at the value-semantics layer. It does not establish C object
memory, legal overread, compiler, full FP-status, RVV `vsetvl`, or binary
correspondence.

## Executable reproduction

On the audited AArch64 host:

```sh
clang -std=c11 -O2 -Wall -Wextra -Werror \
  notes/demos/neon-rvv-semantic-gap-aarch64.c \
  -o /tmp/neon-rvv-semantic-gap-aarch64
/tmp/neon-rvv-semantic-gap-aarch64
```

Observed with Apple Clang 17 at both `-O0` and `-O2`:

```text
f32-vmax Neon             0x7FC00000
f32-vmax RVV oracle       0x00000000
f32-vmin Neon             0x7FC00000
f32-vmin RVV oracle       0x00000000
f32-vrndne Neon           0x7FE00001
f32-vrndne RVV fixup      0x7FE00001
f32-vrndne Lean repaired  0x7FE00001
s8-vclamp Neon main       0
s8-vclamp Neon tail       5
s8-vclamp RVV oracle      0
```

The probe executes the real Neon intrinsics. Because this host is not RISC-V, its
RVV side is a portable per-lane oracle for the target instruction semantics, not an
executed RVV binary. The one-lane witnesses make scheduling irrelevant. The RVV
oracle follows the ratified vector specification: `vfmin`/`vfmax` use the scalar
`minimumNumber`/`maximumNumber` behavior, and the integer clamp uses the exact
`vmax`-then-`vmin` order present in the target C.

The AArch64 `-O0` assembly contains `fmax.4s`, `fmin.4s`, `fadd.4s`, and `fsub.4s`;
the runtime probe clears `FPCR.DN` before checking the payload-preserving rounding
case and restores the original FPCR afterward.

Official semantic references:

- Arm ACLE maps `vmaxq_f32`/`vminq_f32` to the non-number variants `FMAX`/`FMIN`,
  rather than `FMAXNM`/`FMINNM`: <https://arm-software.github.io/acle/neon_intrinsics/advsimd.html>.
- RISC-V vector `vfmin`/`vfmax` use `minimumNumber`/`maximumNumber`:
  <https://docs.riscv.org/reference/isa/unpriv/v-st-ext.html#_vector_floating_point_minmax_instructions>.
- With one NaN, the RISC-V scalar operation returns the numeric operand; with two
  NaNs it returns the canonical NaN:
  <https://docs.riscv.org/reference/isa/unpriv/f-st-ext.html#_single_precision_floating_point_computational_instructions>.

## `f32-vmax` and `f32-vmin`

### Source and target

**Confirmed:** the source calls `vmaxq_f32`/`vminq_f32`, while the target calls
`__riscv_vfmax_vv_f32m8`/`__riscv_vfmin_vv_f32m8`:

- `kernels/source/f32-vmax.c:20-32`
- `kernels/target/f32-vmax.c:14-27`
- `kernels/source/f32-vmin.c:20-32`
- `kernels/target/f32-vmin.c:14-27`

For the stored witness `left = +0`, `right = 0x7FC00000`:

- Arm `FMAX`/`FMIN` propagates the quiet NaN, producing `0x7FC00000`.
- RVV `maximumNumber`/`minimumNumber` chooses the sole numeric operand, producing
  `+0`, or `0x00000000`.

### Lean adequacy for this witness

**Confirmed:** the checked Lean witness matches the actual lane results:

- `SALT.Intrinsics.Neon.vmaxq_f32` and `vminq_f32` use
  `FP32.maxPropagatingNaN`/`minPropagatingNaN`.
- `SALT.Intrinsics.RVV.vfmax_vv_f32` and `vfmin_vv_f32` use
  `FP32.maxNumber`/`minNumber`.
- `Counterexample.lean` proves Neon `0x7FC00000` versus RVV `0x00000000` for both
  complete value claims.

The relevant definitions are in
`src/verification_bw/lean/SALT/Intrinsics/FP32.lean:79-120`,
`Neon.lean:99-103`, and `RVV.lean:105-109`.

**Confirmed qualification:** the Arm helpers are still not a complete full-ISA FP
model. They omit FP status and FPCR state, and their both-NaN selection is simplified.
Those limitations do not explain away this witness: one operand is an ordinary
number and the other is a quiet NaN, so the result distinction is unambiguous.

### Is the difference only about NaNs?

**Confirmed relative to the current pure value definitions:** yes. When neither
operand is NaN, both Arm and RVV helpers reduce to the same `orderedMax` or
`orderedMin`, including the `-0 < +0` rule. When either operand is NaN, results can
differ in NaN-versus-number selection or NaN payload/canonicalization.

Thus a reviewed finite/no-NaN precondition or an observation relation that
quotients all NaNs could remove these exact-bit witnesses. The compiler cannot infer
either choice: the pinned FP32 tensor path does not reject NaN input values.

## `f32-vrndne`

### Repair outcome

**Confirmed:** the shared intrinsic defect has been fixed. Neon arithmetic now
uses explicit Arm `DN=0/AH=0` NaN selection and quieting, while RVV arithmetic
uses explicit canonical-NaN rules. The old witness is gone: both modeled sides
produce `0x7FE00001`, and `Proof.lean` now establishes
`completeValueEquivalenceClaim` for every input without adding a no-NaN
assumption. The published result is `verified(value)`.

Re-running every floating program exposed nine real exact-bit C/ISA value gaps:
`f32-vadd`, `f32-vdiv`, `f32-vlrelu`, `f32-vmax`, `f32-vmin`, `f32-vmul`,
`f32-vmulc`, `f32-vsqrt`, and `f32-vsub`. These arise because Arm `DN=0`
arithmetic can preserve/quiet a NaN payload while RISC-V arithmetic returns the
canonical NaN; they are not repairs to be hidden with a generated assumption.

### Why the old Lean claim was false

**Confirmed:** the old counterexample used signaling NaN `0x7FA00001` and
computed:

```text
Lean Neon = 0x7FC00000
Lean RVV  = 0x7FE00001
```

The RVV C explicitly detects NaNs, ORs in the quiet bit, and merges the quieted
original payload back into the result (`kernels/target/f32-vrndne.c:31-37`). The
generated RVV model faithfully retains that dataflow.

The generated Neon dataflow is also structurally faithful to the source, but its
`vaddq_f32`/`vsubq_f32` wrappers call the shared Lean host operations
`FP32.add`/`FP32.sub`. On this toolchain those primitives canonicalize the signaling
NaN to `0x7FC00000`. That is why the model loses payload bits before the final
`vbslq_f32`.

### What the C source does

**Confirmed on AArch64 with `FPCR.DN=0`:** the actual Neon sequence quiets the
signaling NaN while preserving its payload, producing `0x7FE00001`. This is exactly
the value reconstructed by the RVV target fixup. Therefore the stored witness is
not a C-pair counterexample in the reviewed `DN=0` mode; it is a Lean-model false
positive.

**Qualification:** with Arm default-NaN mode (`FPCR.DN=1`), payload preservation is
not expected, so the current C pair can again differ on payload-carrying NaNs. The
current intrinsic audit explicitly describes the pure Neon arithmetic abstraction
under `FPCR.DN=0`; a future full C/ISA claim must either bind FPCR or state a weaker
NaN observation.

**Inference:** no non-NaN discrepancy is currently known for this pair. The present
audit establishes that the checked NaN witness is spurious; it is not by itself an
unbounded proof of C equivalence for every non-NaN bit pattern.

### Implemented modeling repair

**Confirmed:** the repair was made in the shared intrinsic value layer, not in the
generated `f32-vrndne` program. It covers add/sub/mul/div/sqrt, comparisons, and
max/min NaN selection, with focused Lean tests and axiom-free bridge lemmas. It
does not claim to model exception flags or arbitrary FPCR modes.

**Proposal (broader intrinsic-semantics cleanup):** replace shared host
`Float32.add/sub` as the authority for exceptional values with reviewed
architecture-specific bit semantics. This broader layer should eventually model:

1. Arm `DN=0` signaling-NaN quieting and payload/sign propagation;
2. Arm `DN=1` default-NaN behavior as a separate stateful mode;
3. RISC-V canonical-NaN arithmetic and `fflags` separately from pure values.

The narrow change directly touches five generated programs through the shared
add/sub wrappers (`f32-vrndne`, `f32-vadd`, `f32-vsub`, `f32-f16-vcvt`, and
`qs8-vmul-minmax-fp32`). All current FP outcomes should still be rerun because the
same host-arithmetic design is also used by multiply, divide, square root, and
conversion wrappers. That broader validation scope must not be confused with the
implementation cost of fixing the one `vrndne` witness.

## `s8-vclamp`

### What the checked theorem says

**Confirmed:** the checked-in theorem refutes
`neonPhaseFunctionsEqualClaim`, not `completeValueEquivalenceClaim`:

```text
x = 0, min = 5, max = 0
Neon 64-lane phase: max(x, min), then min(..., max) = 0
Neon 8/tail phase:  min(x, max), then max(..., min) = 5
```

This exactly follows `kernels/source/s8-vclamp.c:24-49,53-57`. The RVV target always
uses the first order, max-then-min (`kernels/target/s8-vclamp.c:15-27`). The Lean
models preserve all three orders in `Models.lean:30-58,101-120`.

### Does it also refute the final Neon/RVV claim?

**Confirmed:** yes. A separately staged Lean check instantiated the complete claim
with a one-byte input `[0]`, seven overread bytes, the same parameters, and a
singleton RVV partition. It checked:

```text
complete Neon output = [5]
complete RVV output  = [0]
Not completeValueEquivalenceClaim
```

The current pipeline publishes only the earlier phase witness because
`find_program_counterexample` stops when cross-phase analysis already found a
counterexample (`program_counterexamples.py:354-357`). This is a reporting/pipeline
limitation, not evidence that the complete claim might still be true.

### Contract boundary

**Confirmed:** if signed `min <= max`, the two operation orders implement the same
clamp and this witness is excluded. The direct kernel bodies assert neither that
condition nor any parameter invariant.

The pinned XNNPACK initializer applies the same quantizer separately to clamp min
and max (`benchmark/XNNPACK/src/microparams-init.c:751-761`), but it does not assert
their order. The generic unary-definition path records clamp parameters without an
order check (`src/subgraph/unary.c:372-459`). A different legacy initializer
`xnn_init_s8_minmax_scalar_params` does assert `output_min < output_max`, but it is
not the registered initializer for this unary clamp path.

**Inference:** reversed quantized bounds are reachable through the inspected path
unless a higher API contract not represented in this call chain forbids them. Until
that bridge is established, the unconditional final claim is genuinely false and
`min <= max` must remain an explicit candidate condition rather than an invented
fact.

## Final outcome changes

1. Keep `f32-vmax` and `f32-vmin` as real exact-bit value counterexamples; decide
   explicitly whether to fix the translation, impose a NaN policy, or weaken the
   observation.
2. `f32-vrndne` is now `verified(value)` under the stated Arm mode. Preserve the
   nine newly exposed FP arithmetic differences as checked counterexamples.
3. Publish a named complete-claim witness for `s8-vclamp`, in addition to the useful
   phase-local diagnostic. Prove a conditional theorem under `min <= max` only when
   that condition is explicit in the selected contract/evidence.
4. Keep value, full intrinsic/FP-state, C, and ISA claims separate. The executable
   AArch64 probe is strong reproduction evidence, but the RVV half remains a
   specification oracle until the same test is executed as an RVV binary on a
   conforming implementation or simulator.
