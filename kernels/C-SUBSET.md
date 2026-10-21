# C subset required by the NEON and RVV kernels

**Takeaway:** The kernels in [`source/`](source/) and [`target/`](target/) fit a
**restricted C99 subset plus a finite NEON/RVV intrinsic environment**.

- **Include:** scalar and vector types, qualified pointers, fixed-size arrays,
  parameter structs/unions, declarations, ordinary expressions and direct calls,
  `if/else`, `for`, `while`, and `do/while`; also handle the small set of XNNPACK
  macros and architecture conditionals.
- **Omit:** `switch`, `goto`, explicit jump statements, recursion, function
  pointers, variadics, variable-length arrays, dynamic allocation, atomics, and
  inline assembly. Full system-header parsing is unnecessary when their types
  and operations are supplied through a fixed environment.
- **Adding RVV:** retain the same C99 baseline; add comma expressions, omitted
  `for` steps, `ptrdiff_t`, guarded macro definitions, and RVV types/intrinsics.
  RVV requires richer vector semantics, but little additional C syntax.

## 1. Scope

| Inspected directory | C files | Kernel bodies | Physical lines |
| --- | ---: | ---: | ---: |
| [`source/`](source/) | 40 | 40 `test_neon` definitions | 5,114 |
| [`target/`](target/) | 37 | 36 `test_rvv` definitions | 2,253 |
| **Combined** | **77** | **76** | **7,367** |

`target/u8-vclamp.c` is empty. Three sources have no corresponding target:
`qd8-f32-qc8w-gemm-minmax.c`, `qd8-f32-qc8w-igemm-minmax.c`, and
`qs8-qc8w-gemm-minmax-fp32.c`. The inspected set therefore does not contain 40
complete source/target pairs.

The audit includes both sides of architecture conditionals and parameter
declarations embedded in leading comments. It excludes harnesses, expanded
system headers, and intrinsic implementations. All findings describe this
repository snapshot, not every upstream XNNPACK kernel.

## 2. Required C syntax

### Types and declarations

| Feature | Required forms |
| --- | --- |
| Functions | One `void` kernel definition per nonempty file, typed parameters, direct calls, and fall-through completion |
| Local declarations | Declarations mixed with statements, declarations in `for` initializers, and locals with or without initializers |
| Qualifiers and storage | `const`, pointer-level `restrict`, and `static` local tables |
| Pointers | Object pointers through depth two (`T **`), including `void *`; dereferencing, address-of, indexing, arithmetic, and casts |
| Arrays | Fixed-size local arrays with brace initializers: `int32_t[7]`, `int8_t[32]`, and `uint8_t[32]` |
| Records | Parameter structs/unions, nested untagged structs with named members, and `.` / `->` access |
| Vector values | NEON/RVV vectors, tuples, and RVV masks |

The combined set uses these scalar type spellings:

```text
void, char, int, float
int8_t, uint8_t, int16_t, uint16_t, int32_t, uint32_t
size_t, intptr_t, uintptr_t, ptrdiff_t
```

`char` occurs in dummy parameter fields; `ptrdiff_t` is added by the RVV target
[f32-conv-hwc2chw.c](target/f32-conv-hwc2chw.c). The three array declarations are
static local tables in [f32-dwconv2d-chw.c](source/f32-dwconv2d-chw.c),
[qs8-rsum.c](source/qs8-rsum.c), and [qu8-rsum.c](source/qu8-rsum.c); the last two
use `XNN_ALIGN(16)`. Nested records have named members such as `scalar`, so C11
anonymous-member lookup is unnecessary. No multiple-declarator declaration is
needed by the inspected kernels.

Although no kernel explicitly declares a `double`, the source `floor` calls
introduce that type through their library interface, as explained in Section 4.

### Control flow and expressions

The statement forms are blocks, declarations, expression statements, `if/else`,
`for`, `while`, and `do ... while`. Declarations and loops need normal lexical
scope. `for` initializers may be empty or declare a variable, and the step may
be omitted. All observed `for` loops have a condition.

| Expression class | Required forms |
| --- | --- |
| Arithmetic | Binary `+ - * / %`, unary `-` |
| Bitwise | `&`, `>>` |
| Comparison | `< <= > >= == !=` |
| Logical | `! && \|\|` |
| Update and sequencing | `= += -=`, prefix `--`, postfix `++`, comma operator |
| Selection | `?:`, including pointer and vector results |
| Memory and types | Unary dereference `*`, address-of `&`, casts, `sizeof(type)`, indexing, `.` and `->` |
| Calls and grouping | Direct calls and parentheses |

Literals are decimal/hexadecimal integers and decimal/hexadecimal `float`
constants with an `f` suffix. Hexadecimal floating exponents such as
`0x1.715476p+0f` must be tokenized correctly.

The less obvious requirements have concrete examples:

| Requirement | Evidence |
| --- | --- |
| Conditional side effects | `1 < k ? *id++ : i0` in [source/f32-argmaxpool.c](source/f32-argmaxpool.c) increments `id` only in the selected arm |
| Comma sequencing, added by RVV | `for (; batch > 0; batch -= vl, input += vl, output += vl)` in [target/qu8-f32-vcvt.c](target/qu8-f32-vcvt.c) |
| Omitted loop step, added by RVV | `for (; batch > 0; )` in [target/qs8-rsum.c](target/qs8-rsum.c) and [target/qu8-rsum.c](target/qu8-rsum.c) |
| Vector-valued ternary, added by RVV | `ky == 0 ? v_in0 : ky == 1 ? v_in1 : v_in2` in [target/f32-conv-hwc2chw.c](target/f32-conv-hwc2chw.c) |
| Byte-address arithmetic | `(float *) ((uintptr_t) p + stride)`, as used in [source/f32-spmm-minmax.c](source/f32-spmm-minmax.c) |

Mixed declarations and statements, declaration-based `for` initializers,
`restrict`, and hexadecimal floats establish the C99 baseline. See
[WG14 N1256](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1256.pdf),
§§6.4.4.2, 6.7.3, 6.8.2, and 6.8.5.

## 3. Intrinsic environment

Treat intrinsic calls as a finite typed vocabulary supplied to the frontend.
Their header implementations do not need to become part of the kernel language.

| Dialect | Distinct intrinsic names | Explicit vector/tuple/mask types | Types including intermediate results |
| --- | ---: | ---: | ---: |
| NEON | 190 | 16 | 18 |
| RVV | 165 | 19 | 19 |
| **Combined** | **355** | **35** | **37** |

The vocabulary includes loads/stores, arithmetic and fused operations,
comparisons, selection, bitwise operations, shifts, saturation, rounding,
narrowing/widening, conversion, reinterpretation, permutations, and reductions.

### NEON types

```text
float32x2_t, float32x4_t
int8x8_t, int8x16_t, int16x4_t, int16x8_t, int32x2_t, int32x4_t
uint8x8_t, uint8x16_t, uint16x4_t, uint16x8_t
uint32x2_t, uint32x4_t, uint64x1_t
float32x2x2_t, float32x4x2_t, uint32x2x2_t
```

The two types absent from explicit declarations are `int16x4_t`, returned by
operations such as `vget_low_s16`, and `uint64x1_t`, used by nested calls in the
ARM branch of [f32-raddstoreexpminusmax.c](source/f32-raddstoreexpminusmax.c).
Restricting types to declaration spellings would miss them. The f32-to-f16
conversion kernel uses integer bit representations and needs no native C
half-precision type.

Tuple member reads/writes such as `v.val[0]` occur in
[x32-packw-gemm-goi.c](source/x32-packw-gemm-goi.c),
[x32-transposec.c](source/x32-transposec.c), and
[f32-spmm-minmax.c](source/f32-spmm-minmax.c).

### RVV types

```text
vfloat32m1_t, vfloat32m2_t, vfloat32m4_t, vfloat32m8_t
vint8m2_t, vint8m8_t, vint16m4_t, vint32m1_t, vint32m4_t, vint32m8_t
vuint8m2_t, vuint16m4_t, vuint32m1_t, vuint32m4_t, vuint32m8_t
vbool4_t, vbool8_t, vbool32_t
vuint32m4x2_t
```

RVV adds vector-length operations, mask values, tail policies, explicit
fixed-point rounding arguments, strided access, and a segment-store tuple.
Examples include `__riscv_vsetvl_e32m8(n)`, `_tu` accumulation in reductions,
and `__RISCV_VXRM_RNU` / `__RISCV_VXRM_RDN` in quantized arithmetic. The rounding
names can be predefined constants; kernel syntax needs no enum declarations.
See the [RVV intrinsic specification](https://github.com/riscv-non-isa/riscv-rvv-intrinsic-doc/blob/main/doc/rvv-intrinsic-spec.adoc).

## 4. Preprocessing and external context

These files are snippets whose type and macro environment must be supplied.
The frontend needs three preparation steps:

1. **Recover parameter declarations.** Source files often store record
   definitions in a leading comment. Promote that designated comment, as
   `--kernel` does, or supply the definitions externally. The targets also need
   external parameter definitions. Supply `struct xnn_qd8_quantization_params`,
   which is not repeated in the source comments.
2. **Resolve conditionals and macro definitions.** Sources use `#if`, `#else`,
   and `#endif` with `XNN_ARCH_ARM`, `XNN_ARCH_ARM64`, and their `||` combination.
   Targets add `#ifndef` / `#define` fallback hint macros in
   [qu8-rdsum.c](target/qu8-rdsum.c) and
   [x32-packw-gemm-goi.c](target/x32-packw-gemm-goi.c). Select branches before
   type checking: some branches declare the same name with different types.
3. **Handle the fixed macro vocabulary.** Forms such as
   `if XNN_UNLIKELY(n != 0)` rely on macro expansion for parentheses. Expand
   known macros or recognize those forms explicitly; also handle `XNN_ALIGN`
   and the function annotation `XNN_OOB_READS`.

The combined non-intrinsic call vocabulary has 14 names, including macros:

```text
assert
XNN_LIKELY, XNN_UNLIKELY, XNN_UNPREDICTABLE
INT8_C, INT32_C, UINT16_C, UINT32_C
min, doz, round_down_po2, round_up_po2, xnn_prefetch_to_l1, floor
```

Also supply `NULL` and standard typedefs. The existing
[`salty_compat.h`](../lean-transpiler/include/salty_compat.h) provides the small
compatibility context. The architecture selector in
[`Frontend.lean`](../lean-transpiler/Transpiler/Frontend.lean) does not implement
general macro preprocessing; the target fallback guards need the known macro
environment or an external preprocessor. Preserving directives in an AST does
not expand them.

**The `floor` exception:** [source/qs8-rdsum.c](source/qs8-rdsum.c) and
[source/qu8-rdsum.c](source/qu8-rdsum.c) call `floor((rows + 251) / 252)`.
The argument uses integer arithmetic, then the `double (double)` library
interface introduces conversions through `double` before assignment to `int`.
[C99 §7.12.9.2](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1256.pdf)
specifies that interface. Eliminating the call is a separate rewrite requiring
range/conversion reasoning.

## 5. Features not required

The following can be omitted at the boundary of the inspected kernel language:

| Area | Unneeded features |
| --- | --- |
| Control flow | `switch`, labels, `goto`, `break`, `continue`, explicit `return` |
| Functions | Recursion, indirect calls/function pointers, variadics |
| Declarations and aggregates | User typedef declarations, enum declarations, bitfields, flexible arrays, VLAs, multidimensional array declarations |
| Initialization | Designated initializers, compound literals |
| Storage and execution | Dynamic allocation, mutable global definitions, volatile/atomic accesses, inline assembly |
| Expressions and literals | `sizeof expression`, string/character literals, C bitwise OR/XOR/NOT or left-shift operators, compound assignments other than `+=` and `-=` |
| Language versions | C11/C23-only syntax |

These exclusions apply to the kernels, not the internals of external headers
and helpers. For example, intrinsic calls still perform bitwise operations
whose corresponding C operators are absent from the kernels.

## 6. Representation and semantic boundary

A sufficient core AST needs types, declarations, lvalues, the expressions above,
and structured statements. Records, intrinsics, and external calls can be
supplied in a fixed environment. Loops and side-effecting expressions can be
normalized into a smaller intermediate language while preserving scope,
sequencing, and conditional evaluation.

If this subset later receives semantics, the main obligations are:

- **Memory and ABI:** byte strides through pointer–integer casts, typed
  loads/stores, aliasing/alignment, record/union layout, and integer/pointer
  widths. `(float *)((uintptr_t)p + stride)` counts bytes; `p + stride` counts
  float elements. Selecting an ARM preprocessing branch alone does not choose
  a 32-bit ABI.
- **Input contracts:** tail vector loads may access padding beyond the logical
  remaining elements; syntax coverage does not establish valid memory access.
- **Scalar computation:** integer promotions/conversions, floating operations,
  and the `floor` interface described above.
- **Vector computation:** precise NEON/RVV operation behavior, including RVV
  dynamic `vl`/VLMAX, element widths, LMUL, masks, tail policies, and rounding.

## 7. Evidence and reproduction

[`audit_c_subset.py`](audit_c_subset.py) traverses JSON ASTs from the existing
Lean parser and records per-file features and SHA-256 hashes. It consults the
local [NEON](../op-semantics/neon-intrinsics.md) and
[RVV](../op-semantics/rvv-intrinsics.md) catalogues for intermediate vector types.
All 190 NEON and 165 RVV names were found. For the three RVV `_tu` variants,
base signatures were used solely to inventory vector types, not to validate
argument lists.

The current [`AST.lean`](../lean-transpiler/Transpiler/AST.lean) and
[`Parser.lean`](../lean-transpiler/Transpiler/Parser.lean) cover a superset of the
observed syntax. The investigation produced these results:

| Check | Result |
| --- | --- |
| Lean project build | Passed |
| Source C/JSON roundtrips | All 40 kernels passed |
| Generated RVV outputs from both source architecture selections | All 80 reparsed with no NEON AST nodes |
| Generated Lean AST definition | Elaborated successfully |
| Checked-in `target/` C parser/printer roundtrips | All 36 nonempty targets passed; the empty file produced an empty AST |

The 80 generated RVV outputs are separate from the 36 checked-in target bodies.
These results establish syntax/representation coverage. This investigation did
not perform C compiler checks, execution testing, or semantic verification.

From the repository root:

```sh
cd lean-transpiler
lake build
python3 tests/corpus.py
cd ..

python3 kernels/audit_c_subset.py > /tmp/salty-source-audit.json
python3 kernels/audit_c_subset.py --sources kernels/target > /tmp/salty-target-audit.json

for kernel in kernels/target/*.c; do
  if [ -s "$kernel" ]; then
    lean-transpiler/.lake/build/bin/neon2rvv check "$kernel" --kernel || exit 1
  fi
done
```
