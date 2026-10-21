# SALTy Lean NEON → RVV transpiler

A small, standalone Lean 4.27 transpiler for the restricted C used by the
[40 SALTy source kernels](../kernels/source/). It preserves loops, unrolling,
scalar expressions, pointer arithmetic, and tail handling. NEON operations become
calls to generated helpers using RVV intrinsics with fixed NEON lane counts.
There is no optimization pass.

Parsing, architecture selection, AST transformation, and C emission run in Lean.
The generated C contains only the helpers it needs and does not depend on
`neon2rvv.h`. **Python is not required to build or run the transpiler**; it is used
for tests and development-time rule generation.

This is an executable syntactic transpiler, not a verified compiler. See
[tests and validation](#tests-and-validation) for the distinction between syntax
checks, sampled behavior comparisons, and their coverage limits.

- [Quick start](#quick-start)
- [Commands](#commands)
- [Supported inputs and target behavior](#supported-inputs-and-target-behavior)
- [Tests and validation](#tests-and-validation)
- [Implementation and development](#implementation-and-development)
- [Provenance](#provenance)

## Quick start

Use the stock Lean toolchain pinned in [lean-toolchain](lean-toolchain).
From the repository root:

```sh
cd lean-transpiler
lake build

lake exe neon2rvv transpile ../kernels/source/qs8-vadd-minmax.c \
  --kernel -o /tmp/qs8-vadd-rvv.c
```

`--kernel` prepares this repository's source snippets: their leading parameter
record comment becomes a C declaration, and the transpiled output includes
[salty_compat.h](include/salty_compat.h) for the XNNPACK compatibility context.
For ordinary C input, omit `--kernel` and supply the required declarations and
headers yourself.

To compile the generated C, use an RVV 1.0 intrinsic compiler such as Clang 19+
with a suitable RISC-V sysroot:

```sh
clang-19 --target=riscv64 --sysroot=/path/to/riscv/sysroot \
  -march=rv64gcv -mabi=lp64d -ffp-contract=off -Iinclude -O2 \
  -c /tmp/qs8-vadd-rvv.c -o /tmp/qs8-vadd-rvv.o
```

The target is **RV64 with VLEN ≥ 128**. Do not use `-ffast-math`.
The generated file also disables FP contraction.

## Commands

All examples below assume the working directory is `lean-transpiler/`.

```text
lake exe neon2rvv COMMAND INPUT [-o OUTPUT] [--kernel] [--arch arm64|arm]
```

| Command | Result |
| --- | --- |
| `transpile` | Select source architecture branches and lower NEON C to RVV C |
| `roundtrip` | Parse C and print canonical C, without lowering or architecture selection |
| `ast` | Serialize the parsed C AST as JSON |
| `emit` | Read a JSON AST and print C |
| `lean` | Emit a Lean definition `program : Transpiler.Program` |
| `check` | Check that canonical C printing and reparsing are stable |

Output goes to stdout unless `-o` is supplied. Only `transpile` selects
architecture branches: the default is `--arch arm64`; `--arch arm` selects the
32-bit ARM branches. **Both produce RV64 C**, without emulating a complete
32-bit ABI. The entry point `test_neon` becomes `test_rvv`; other function names
are preserved. The prefix `salty_rvv_` is reserved for generated identifiers.

For example, persist an AST and print it back to C:

```sh
lake exe neon2rvv ast ../kernels/source/f32-vadd.c --kernel -o /tmp/kernel.json
lake exe neon2rvv emit /tmp/kernel.json -o /tmp/kernel.c
```

To inspect the AST as Lean data:

```sh
lake exe neon2rvv lean ../kernels/source/f32-vadd.c --kernel -o /tmp/Kernel.lean
lake env lean /tmp/Kernel.lean
```

## Supported inputs and target behavior

### C subset

The parser supports declarations, scalar/vector/pointer types, arrays and
initializers, casts, both forms of `sizeof`, ordinary expressions and calls,
indexing and member access, blocks, `if`/`else`, `for`, `while`, `do`/`while`,
`return`, `break`, and `continue`. It also supports struct/union declarations,
anonymous nested records, `XNN_ALIGN`, and `XNN_OOB_READS`. Literal spelling,
including hexadecimal floats, is retained; comments and formatting are not.

The frontend does not support function-pointer declarators, K&R functions,
variadic declarations, enums, `switch`/`goto`, inline assembly,
designated/compound literals, or arbitrary compiler attributes. Basic typedefs
parse, but complete typedef scoping and C type resolution are not implemented.
Unknown NEON intrinsics and incorrect intrinsic argument counts are rejected.

| Vector construct | Handling |
| --- | --- |
| Tuple reads, such as `v.val[0]` | RVV `vget`; requires a directly named tuple variable and a decimal constant index |
| Tuple writes | Generated setters evaluate the RHS once, update the tuple, and return the assigned vector; nested assignments are supported |
| Uninitialized tuple locals | Zero-initialized so a partial write can safely pass the tuple to `vset` |
| Vector `sizeof` | Retains the source NEON byte count as a `size_t` constant, without evaluating the operand |
| Vector arrays and record fields | Rejected because native RVV vector types are sizeless |

Vector `sizeof` expression support includes variables, pointer dereferences,
tuple elements, casts, catalogued NEON calls, calls to declared functions, and
assignment/comma/conditional expressions. This limited source-type recovery
is not a full C type checker.

### Preprocessing

`parseC` preserves directives as syntax. Before parsing, the `transpile` CLI
selects nested `#if`, `#ifdef`, `#ifndef`, `#elif`, `#else`, and `#endif` branches
using the supported architecture names (`XNN_ARCH_ARM64`, `XNN_ARCH_ARM`,
`__aarch64__`, `__arm__`), integer conditions, `defined`, `!`, `&&`, `||`, `==`,
and `!=`. Unknown conditions are errors.

Generic macro expansion is not implemented. Preprocess other macros externally
while retaining intrinsic calls. The known XNN expression macros are preserved
for the target C compiler.

### Execution assumptions

The output retains the source's padding, aliasing, and valid-input requirements.
The intended floating-point environment uses default rounding with ARM
flush-to-zero and default-NaN modes disabled. Exception/status flags are not
emulated.

Supported floating-point rules preserve NaN signs and payloads, prioritize
signaling NaNs, and follow **ARM's documented intrinsic operand order**. Non-fused
multiply-add/subtract stays unfused, and reductions retain the NEON pairwise
tree. A source compiler can reorder operands and choose a different NaN payload;
the [FMA reference discussion](tests/differential/README.md#focused-floating-point-rules)
explains the observed Clang 19 case and how it is tested.

## Tests and validation

Run the checks that need Lean, Python, and a host C compiler:

```sh
lake exe transpiler-tests
python3 tests/regressions.py
python3 tests/corpus.py
python3 -m unittest discover -s tests -p test_differential.py
```

For real NEON/RVV execution, supply cross compilers and QEMU user emulators.
Zig can supply both cross compilers and their C libraries:

```sh
# Requires qemu-aarch64 and qemu-riscv64 on PATH, or explicit runner options.
python3 tests/differential.py --zig /path/to/zig
python3 tests/differential.py --zig /path/to/zig --float-domain ieee
python3 tests/differential.py --zig /path/to/zig --suite fp --float-domain ieee
```

The [differential testing guide](tests/differential/README.md) covers setup,
input generation, reference selection, failure replay, and adding adapters.

| Suite | What it checks | Recorded coverage |
| --- | --- | --- |
| [Lean unit tests](Tests.lean) | Syntax, ASTs, architecture selection, lowering, and rejection cases | Passed; no generated C execution |
| [Corpus](tests/corpus.py) | Roundtrips, absence of NEON nodes, Lean elaboration, and optional RVV compilation | 40 sources, 80 targets, 240 syntax/type checks passed |
| [Host regressions](tests/regressions.py) | Control flow, `sizeof`, and tuple behavior using test-only vector structs | Five programs passed at `-O0`/`-O2` |
| [Kernel comparisons](tests/differential.py) | Exact output bytes from real NEON/RVV instructions under QEMU | 40 kernels; 19,680 finite-input comparisons passed; IEEE mode exposes a Clang NaN-order discrepancy in complex multiply |
| [Focused FP comparisons](tests/fp_cases.py) | NaN priority, invalid operations, and reduction order under QEMU | 19 intrinsics in 23 programs; 147,048 bitwise comparisons passed |

The differential runs used Zig 0.14.1 and QEMU 8.2.2, at `-O0`/`-O2` and VLEN
128/256/512. Repository-kernel reference bodies bypass the Lean parser/printer
and remain unmodified. In the focused FP suite, the two non-lane FMA reference
operations are pinned to ARM's documented operand order. Selecting
`--fp-reference compiler` exposes Clang 19's different NaN selection.

These results establish agreement for the tested cases. Runtime kernel coverage
is **40 of 40 kernels**; syntax checks and sampled executions do not prove
semantic equivalence for all kernels, inputs, or source compilers.

<details>
<summary>Optional compiler checks and the development-container command</summary>

With an RVV-enabled Clang and suitable headers:

```sh
python3 tests/corpus.py --clang clang-19 --include /path/to/riscv/sysroot/include
```

Add `--objects` to request machine-code generation. The Lean-distributed Clang 19
in the development container supports RVV builtin syntax/type checks but lacks
its full resource headers and RISC-V code-generation backend. Its corpus checks
can be reproduced with:

```sh
python3 tests/corpus.py \
  --clang /root/.elan/toolchains/leanprover--lean4---v4.27.0/bin/clang \
  --builtin-header \
  --include /root/.elan/toolchains/leanprover--lean4---v4.27.0/include/clang \
  --include /opt/riscv/riscv32-unknown-elf/include
```

`--builtin-header` supplies typedefs for Clang's real `__rvv_*` types and its
intrinsic-enabling pragma; it does not replace intrinsic signatures or execution.
`tests/regressions.py` accepts the same compiler/header options for its outputs.

</details>

## Implementation and development

### Lean API

```lean
import Transpiler
open Transpiler

def translateSource (source : String) : Except String Program := do
  let selected ← selectArchitecture source .arm64
  let input ← parseC selected
  transpile (← loadRules) input

-- parseC : String → Except String Program
-- transpile : RuleTable → Program → Except String Program
-- printC : Program → String
```

The AST records C syntax, type spellings, and qualifiers, with distinct NEON and
RVV vector/intrinsic variants. Scalar expressions are left for the target C
compiler to analyze. There is no C operational semantics or verified RVV
instruction vocabulary. Parser/lowering traversals use executable `partial def`s;
a future correctness proof would also require a semantic model and suitable
traversal/equational infrastructure.

### Lowering rules and the Python generator

[Rules.lean](Transpiler/Rules.lean) contains vector aliases and 191 wrapper
templates covering the corpus's 190 intrinsic names. Lean's `loadRules` parses
these templates into the same AST used for input programs. Generated helpers
are ordinary AST nodes, not opaque C statement strings.

The build consumes `Rules.lean` directly. To regenerate it during development:

```sh
python3 scripts/import_rules.py
lake build
```

[import_rules.py](scripts/import_rules.py) reads the sibling
[neon2rvv header](../neon2rvv/neon2rvv.h) and the source-kernel inventory, applies
local corrections, and writes `Transpiler/Rules.lean`. When changing a generated
rule, update the generator and regenerate the Lean file together. **Neither
Python nor the reference clones are required by the normal build or CLI.**

### Source map

| File | Responsibility |
| --- | --- |
| [AST.lean](Transpiler/AST.lean) | Shared C syntax and separate NEON/RVV variants |
| [Lexer.lean](Transpiler/Lexer.lean) | Tokens, comments, directives, and literal spelling |
| [Parser.lean](Transpiler/Parser.lean) | Restricted C declarations, statements, and expressions |
| [Printer.lean](Transpiler/Printer.lean) | Canonical C emission with explicit parentheses |
| [Frontend.lean](Transpiler/Frontend.lean) | Architecture selection and kernel-context preparation |
| [Rules.lean](Transpiler/Rules.lean) | Generated vector aliases and helper templates |
| [Lowering.lean](Transpiler/Lowering.lean) | AST transformation, tuple/`sizeof` handling, and helper dependencies |
| [Main.lean](Main.lean) | CLI, file I/O, and JSON/Lean AST serialization |
| [salty_compat.h](include/salty_compat.h) | Standalone XNNPACK compatibility context |

## Provenance

[C-parsing-for-Lean4](../C-parsing-for-Lean4/) informed the separation of grammar,
AST constructors, and parsing. This project uses its own restricted parser on
stock Lean; it does not depend on that project's custom toolchain.

The helper templates originate from [neon2rvv](../neon2rvv/). Local corrections
include the floating-point behavior described above, `vzip1q_f32`/`vzip2q_f32`,
overflow-safe `vqrdmulhq_s16`, unaligned quantized tail stores, and
signed-low-byte/out-of-range shift handling in
`vrshlq_s32`. See [NOTICE](NOTICE), the retained
[header license](LICENSE.neon2rvv), and the
[reference repository license](LICENSE.neon2rvv-repository) for provenance and
licensing. Generated C includes the helper source's MIT notice.
