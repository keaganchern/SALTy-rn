# Elementwise External Input-Condition Audit

Audit date: 2026-08-29 (Asia/Seoul)

Repository scope: `feat/elementwise-compiler@c36d91e`, twenty programs in
`verification/elementwise-compiler/CorpusReport.json`.

Upstream evidence scope: Google XNNPACK `master`, inspected on 2026-08-29. This
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
| `s8-vclamp` | signed `min <= max`; validated output range and clamp initializer |
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

- Local twenty-program list:
  `verification/elementwise-compiler/CorpusReport.json`.
- Local kernel entry assertions and parameter reads: `kernels/source/*.c` and
  `kernels/target/*.c`.
- Legacy corroboration: `src/workflow/verification/param_configs.py`.
- XNNPACK validates quantized tensor zero-point ranges and requires a finite,
  normalized, positive scale:
  <https://github.com/google/XNNPACK/blob/master/src/tensor.c>.
- XNNPACK output-range validation rejects `output_min > output_max`:
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
The minimum honest next step is to mark these eight programs as having unchecked
external input conditions and prevent that state from being confused with a proof
ready program. A later generic extractor should follow the registered parameter
initializer and upstream validation evidence; it must not add per-program Python
branches or let the proof agent invent conditions.
