# Elementwise External Input-Condition Audit

Audit date: 2026-08-29 (Asia/Seoul)

Repository scope: `feat/elementwise-verification`, twenty programs in
`verification/elementwise-results/CorpusReport.json`.

Upstream evidence scope: pinned Google XNNPACK commit
`867d5a344790802ee067be62f572c2e2722bf6fb`, audited on 2026-08-29. This
audit asks whether parameter facts used by the intended XNNPACK call domain are
absent from the isolated Neon/RVV kernel entry assertions. It does not audit C
memory extent, FP environment, or ISA state.

## Result

**Confirmed:** this is not unique to `s8-vclamp`. Eight of the twenty programs
consume quantized parameter structs whose legal values are constructed or checked
outside the isolated kernel body. None of their kernel entry assertion sets records
those parameter facts.

**Confirmed:** eleven programs have no semantic parameter fields in the isolated
kernel (`void*` or unused/default params). One additional program, `f32-vlrelu`,
copies a slope parameter, but no comparable hidden relation between parameter
fields was found. This does not rule out separate FP/ISA environment obligations.

| Program group | Count | External parameter facts found |
|---|---:|---|
| quantized parameter programs | 8 | yes; ranges/relations come from tensor validation or microparameter initialization |
| no semantic parameter fields | 11 | none of this parameter-contract kind |
| `f32-vlrelu` | 1 | slope is copied; no hidden cross-field/range condition found |

## Eight Confirmed Programs

| Program | Upstream-derived facts relevant to the isolated params |
|---|---|
| `s8-vclamp` | initializer applies one quantizer to clamp `min`/`max`; signed `min <= max` repairs the phase mismatch, but its caller guarantee is unresolved |
| `qs8-vadd-minmax` | bounded shift and multipliers; zero-point ranges; ordered/fixed output bounds |
| `qu8-vadd-minmax` | bounded shift and multipliers; zero-point ranges; ordered/fixed output bounds |
| `qs8-vcvt` | multiplier in `[1, 32768]`; signed zero-point ranges |
| `qs8-vlrelu` | positive multiplier in `[1, 32768]`; negative multiplier in `[-32767, 32768] \ {0}`; zero-point ranges |
| `qs8-vmul-minmax-fp32` | positive bounded product/output scale; zero-point ranges; ordered/fixed output bounds |
| `qs8-f32-vcvt` | signed zero point in `[-128, 127]`; finite normalized positive scale |
| `qu8-f32-vcvt` | unsigned zero point in `[0, 255]`; finite normalized positive scale |

The existing legacy diagnostic data already names six of these parameter-struct
families in `src/workflow/verification/param_configs.py`, including min/max,
shift, and multiplier restrictions. It is useful corroboration but is handwritten
data and cannot serve as the new compiler's trusted evidence source.

## Twelve Other Programs

The following eleven have no semantic parameter field in the extracted kernel:

`f32-f16-vcvt`, `f32-vadd`, `f32-vcmul`, `f32-vdiv`, `f32-vmax`, `f32-vmin`,
`f32-vmul`, `f32-vmulc`, `f32-vrndne`, `f32-vsqrt`, and `f32-vsub`.

`f32-vlrelu` reads one `slope`. XNNPACK's scalar initializer copies the supplied
negative slope directly; this audit found no analogous missing `min <= max` or
multi-field parameter invariant for it.

## Evidence

**Correction to the first audit pass:** `xnn_subgraph_check_output_min_max`
exists in the pinned tree, but the audited unary clamp path
`xnn_define_clamp -> xnn_define_unary -> xnn_create_unary_elementwise_nc` does
not call it. File co-occurrence is not a call-chain proof. Therefore the current
compiler records signed `params.min <= params.max` only as a candidate and keeps
`s8-vclamp` in `required-missing`.

- Local twenty-program list:
  `verification/elementwise-results/CorpusReport.json`.
- Local kernel entry assertions and parameter reads: `kernels/source/*.c` and
  `kernels/target/*.c`.
- Legacy corroboration: `src/workflow/verification/param_configs.py`.
- XNNPACK validates quantized tensor zero-point ranges and requires a finite,
  normalized, positive scale:
  <https://github.com/google/XNNPACK/blob/master/src/tensor.c>.
- XNNPACK output-range validation rejects `output_min > output_max`, but is not
  currently connected to the pinned unary clamp path:
  <https://github.com/google/XNNPACK/blob/master/src/subgraph/validation.c>.
- XNNPACK constructs S8/QU8 add, QS8 conversion, QS8 LReLU, QS8 multiply, and
  clamp microparameters in:
  <https://github.com/google/XNNPACK/blob/master/src/microparams-init.c>.
- Kernel-to-initializer bindings are in the corresponding `src/*/*.inc` files,
  e.g.:
  <https://github.com/google/XNNPACK/blob/master/src/s8-vclamp/s8-vclamp.inc>.

## Decision Implication

Eight of twenty is too common to treat as an isolated exception. It does not
justify building a whole-program interprocedural XNNPACK frontend immediately.
The implemented minimum honest step now marks these eight programs
`required-missing` and prevents that state from being confused with proof ready.
The extractor follows the unique same-stem registration to the shared Neon/RVV
parameter initializer and hashes the pinned commit plus every consulted file.
Resolving a condition still requires a checked caller/initializer postcondition;
it must not come from a per-program table or from the proof agent.

Every compiler invocation now emits this audit class. XNNPACK corpus runs use the
registered-domain scope above. A standalone/held-out invocation without an
upstream registration emits `local-unconditional-claim`: it assumes no hidden
caller restriction and leaves every modeled parameter value in the generated
claim. That explicit scope is not caller evidence and cannot repair a false
claim; the mandatory cross-phase audit or the proof must still establish the
claim. There is no `not-audited` state that can enter proof preparation.
