# Differential output comparison

`tests/differential.py` compiles the original kernel as AArch64 NEON, transpiles
it with the current Lean executable, compiles the result as RVV, and executes
both with identical binary inputs. It covers all **40 repository kernels** and
compares exact output bytes, including multiple outputs and strided buffer gaps.
The original C body is preserved; it does not pass through the Lean parser or
printer, so a shared parsing bug cannot change both sides of the comparison.

These are real instruction executions under QEMU, without test-only intrinsic
substitutes. This suite is separate from `tests/regressions.py`, whose host
vector structs test a few specific C lowering behaviors.

## Run

Build the transpiler first. Supply QEMU user emulators supporting RVV 1.0 and
cross compilers able to produce statically linked AArch64/RV64 Linux executables.
[QEMU 7.0 introduced RVV 1.0 support](https://www.qemu.org/2022/04/19/qemu-7-0-0/).
The tested setup is **Zig 0.14.1 and QEMU 8.2.2**. Zig supplies Clang, target
headers, and musl for both architectures, avoiding a separate Linux sysroot;
[the Zig 0.14 release uses LLVM 19](https://ziglang.org/download/0.14.0/release-notes.html).

```sh
cd lean-transpiler
lake build

# qemu-aarch64 and qemu-riscv64 must be on PATH, or pass runner paths below.
python3 tests/differential.py --zig /path/to/zig

# Select kernels and increase the seeded random sample.
python3 tests/differential.py --zig /path/to/zig \
  --kernels f32-vadd qs8-vadd-minmax qs8-rsum --seed 123 --random-cases 200

# Static QEMU binaries can be passed explicitly.
python3 tests/differential.py --zig /path/to/zig \
  --source-runner /path/to/qemu-aarch64-static \
  --target-runner '/path/to/qemu-riscv64-static -cpu rv64,v=true,vlen={vlen},elen=64,vext_spec=v1.0'

# Alternatively supply normal cross compiler commands and their sysroot options.
python3 tests/differential.py \
  --source-cc 'aarch64-linux-gnu-gcc' \
  --target-cc 'clang-19 --target=riscv64-linux-gnu --sysroot=/path/to/riscv/sysroot'
```

Command arguments are shell-split into argv lists; commands are never executed
through a shell. An empty runner prefix supports native execution. The target
executable reads the actual `vlenb` CSR and rejects a VLEN different from the
requested one, including on native hardware. Missing tools are errors, not
skipped tests. Neither this script nor the build installs any tools.

## Coverage and comparison contract

| Adapters | Outputs and shape coverage |
| --- | --- |
| `f32-vadd`, `f32-vsub`, `f32-vmul`, `f32-vdiv`, `f32-vmin`, `f32-vmax`, `f32-vsqrt`, `f32-vrndne` | Exact float bits, vector lengths and tails |
| `s8-vclamp`, `u8-vclamp`, `qs8-vadd-minmax`, `qu8-vadd-minmax` | Quantized bytes, varied clamps/zero points/multipliers/shifts |
| `qs8-rsum`, `qu8-rsum` | Complete 32-bit reduction result |
| `f32-vcmul`, `f32-vmulc`, `f32-vlrelu`, `f32-f16-vcvt` | Both complex planes, broadcast multiply, slopes, half-precision result bits |
| `qs8-f32-vcvt`, `qu8-f32-vcvt`, `qs8-vcvt`, `qs8-vlrelu`, `qs8-vmul-minmax-fp32` | Conversion, rounding, saturation and quantization parameters |
| `qs8-rdsum`, `qu8-rdsum` | Every channel accumulator; row strides and boundaries around 7/252/504 rows |
| `f32-gemm-minmax`, `f32-igemm-minmax`, `f32-spmm-minmax` | Row/channel/K tails, packed weights, indirect offsets/zero entries, sparse maps including empty channels |
| `qd8-f32-qc4w-gemm-minmax`, `qd8-f32-qc8w-gemm-minmax`, `qd8-f32-qc8w-igemm-minmax`, `qs8-qc8w-gemm-minmax-fp32` | Packed int4/int8 weights, zero-point corrections, per-channel scales, bias and output strides |
| `f32-dwconv-minmax`, `f32-dwconv2d-chw`, `f32-conv-hwc2chw` | Width/height/channel tails, zero padding, offsets, partial output-row ranges and strides |
| `f32-maxpool`, `f32-argmaxpool` | Pooling passes around 9/18/27 elements, channel tails and ties; argmax values **and indices** |
| `f32-raddstoreexpminusmax` | Every exponential **and the sum** |
| `x32-packw-gemm-goi`, `x32-transposec` | Packed/transposed words and padding; groups, absent bias, extra bytes, odd dimensions and strides |

The default is 82 cases per kernel: 50 deterministic zero/edge cases plus 32
seeded random cases. Flat-vector lengths exercise boundaries around 4, 8, 16,
32, 64, 128, 256 and 2048 elements; random lengths range from 1 to 4096.
Shape-aware adapters use rotating boundary grids and randomly selected dimensions,
strides and parameters, rather than the full Cartesian product. `--list` prints
the complete inventory. A host test checks it against `kernels/source/*.c`, so
adding an untested repository kernel fails that inventory check.

Every case runs at `-O0` and `-O2` and RVV VLEN 128, 256 and 512:
**40 × 82 × 2 × 3 = 19,680 source/target case comparisons**. The source result is
reused across VLENs. Both sides use the original NEON packing sizes (4/8/16
channels as appropriate), independent of VLEN. Pointer tables are rebuilt from
serialized offsets, including zero-buffer sentinels; host pointer addresses are
never serialized.

The original flat-vector driver checks input immutability and output guards.
The additional buffer driver checks every read-only buffer and every buffer's
64-byte outer guards, then emits all writable buffers in order, including
initialized stride gaps and packed padding. Inputs include initialized space for
permitted vector overreads. These checks do not detect every invalid read or
write, and equality of padding bytes does not by itself prove they were untouched.

Compilation disables fast math and FP contraction. The assumed FP environment
is default round-to-nearest, with ARM flush-to-zero/default-NaN modes disabled.
FP exception/status flags are not compared. The source configuration is AArch64.
There is no numeric tolerance, NaN canonicalization or signed-zero normalization.

### Input domains and recorded results

`--float-domain finite` uses signed zeros, subnormals, extreme values and random
finite bit patterns in the flat float adapters, including the new complex,
broadcast, leaky-ReLU and half-conversion cases. Division avoids zero denominators;
square root avoids negative nonzero inputs. Overflow may still produce infinities.
GEMM, convolution, pooling and sparse cases use bounded finite floats. The
exp-minus-max adapter uses finite inputs with differences in `[-80, 0]`.
Quantized adapters use bounded, finite scales. These restrictions also apply
under `--float-domain ieee`; that option adds infinities and quiet/signaling NaN
payloads to the float bit-pattern adapters, not every floating buffer.

```sh
python3 tests/differential.py --zig /path/to/zig --float-domain ieee
```

The expanded seed-1 finite run passes **19,680 comparisons**. Expansion exposed
an unaligned quantized tail-store bug: the original NEON store allowed a byte
address, but its lowered scalar dereference imposed 16/32-bit alignment. The
lowering now copies the extracted bytes, and the exact saved failing case passes
at both optimization levels and all three VLENs.

The expanded IEEE run reveals a separate **source-compiler discrepancy** in
`f32-vcmul`: Clang 19 at `-O2` reverses the final addition's operands in the
imaginary result. With competing NaNs it returns `0xffc23456` where documented
intrinsic order returns `0x7fc12345`. `-O0` agrees. This remains a reported failure
at all three VLENs; it is neither normalized nor excluded from the suite. The
transpiler retains documented ARM operand order. The kernel reference remains
ordinary compiler-generated NEON code.

QEMU 8.2.2 can force agnostic tail/mask lanes to all ones: append
`,rvv_ta_all_1s=true,rvv_ma_all_1s=true` to the target CPU string. The seed-2 IEEE
run with these settings agrees for the other 39 kernels and for `f32-vcmul` at
`-O0`; it reports the same `-O2` payload-order discrepancy. Sampled comparisons
across all 40 kernels still do not prove equivalence for all inputs.

## Focused floating-point rules

```sh
python3 tests/differential.py --zig /path/to/zig --suite fp --float-domain ieee
python3 tests/differential.py --suite fp --list
```

This suite generates 23 small programs covering the 19 supported FP arithmetic,
min/max, square-root, multiply-add, and reduction intrinsics, including every
lane of both lane-FMA variants. Binary and ternary operands range over grids of
12 representative bit patterns: finite values, signed zeros, infinities, and
positive/negative quiet/signaling NaNs with different payloads. Reductions use
mixed lanes to check the pairwise tree. Each program also receives 32 seeded
random lane patterns. The harness checks the original NaN bits, signaling-NaN
priority, and invalid operations such as `0 * infinity` with a quiet-NaN addend.

The default **instruction reference** pins `vfma_f32` and `vfmaq_f32` to the
[ACLE operand mapping](https://arm-software.github.io/acle/neon_intrinsics/advsimd.html)
using two small AArch64 inline-assembly wrappers. All other reference operations
use the ordinary NEON intrinsics. This avoids Clang 19's observed swapping of
the two multiplicands in non-lane FMA, including at `-O0` and with strict FP:
the swap preserves numerical multiplication but changes which competing NaN
payload is selected. The lowered rules follow documented ARM instruction order,
not this compiler-specific reordering. The propagation order and fused invalid
case are also described in QEMU's
[ARM NaN selection implementation](https://github.com/qemu/qemu/blob/v8.2.2/fpu/softfloat-specialize.c.inc).

With this instruction reference, seed 1 passed **147,048 bitwise comparisons**
at `-O0`/`-O2`, VLEN 128/256/512, and with agnostic lanes forced to ones. The
unmodified C compiler reference remains available explicitly:

```sh
python3 tests/differential.py --zig /path/to/zig --suite fp --float-domain ieee \
  --fp-reference compiler
```

On Clang 19 this still reports the two non-lane FMA payload-order differences;
they are neither normalized nor marked passing. `report.json`, failure metadata,
and new replay cases record the reference mode. Replay preserves the recorded
mode unless explicitly overridden. This option never changes the reference
for the 40 repository kernels: their source bodies always remain unmodified.

## Failures and replay

Each run creates a new directory under `.lake/differential/`, or the new path
specified by `--work-dir`. It retains:

- Original/transpiled kernel C, the shared driver and compatibility header,
  generated adapter headers, and compiled executables.
- Exact serialized input cases and source/target output bytes.
- `commands.jsonl` with compiler/runner argv, exit status, and diagnostics.
- `report.json` with toolchain versions, configuration, counts, and failures.
- A `failure-O*-vlen*/case.json` and standalone `input.bin` for each first
  failing case, with a `failure.json` describing the difference and commands.

Output corruption, truncation, extra output, input/guard changes, nonzero exits,
and timeouts fail the run. The driver flushes each case's output so a crash or
timeout can be located from the completed prefix. A timeout caused by an
overall batch time budget may not recur for the isolated case; the full batch
input and command log are also retained. Compile/setup errors are reported
separately in `report.json` and are never called equivalence failures or passes.

Replay the exact saved input against the current source and transpiler:

```sh
python3 tests/differential.py --zig /path/to/zig \
  --replay /path/to/failure-O2-vlen128/case.json --opt 2 --vlen 128
```

Supply the same custom runner options if they were used originally. Replay
recompiles both sides; it does not reuse an old expected-output file. A nonzero
exit is intentional when the mismatch persists. The harness was also checked
by injecting a one-byte corruption into an otherwise successful RVV run and
confirming that it failed and saved a replay case.

The comparator, truncated-output handling, crash-prefix attribution, seeded
input generation, replay serialization, exit handling, and timeout handling
have focused host unit tests:

```sh
python3 -m unittest discover -s tests -p test_differential.py -v
```

## Add a kernel

For a flat-vector or single-reduction kernel, add an `Adapter` in
`tests/differential.py` and extend its parameter/input generators as needed.
For other signatures, add a `BufferAdapter` and a case-generation branch in
[`tests/kernel_cases.py`](../kernel_cases.py). Its `header()` emits the C call
adapter; `CaseBuilder` serializes 32 configuration words and up to eight named
buffers for [`buffer_driver.c`](buffer_driver.c). Mark every output or accumulator
writable and initialize all input/padding bytes. Use `pointers()` to reconstruct
indirect inputs from offsets. Keep parameter records local to each invocation.

Both protocols support the same compiler/runner options, exact comparison,
artifact capture and replay command. Generators must satisfy the original
kernel's valid-input and padding requirements. Add boundary shapes for each loop
and tail, keep packed layouts independent of RVV VLEN, and update the inventory
check when intentionally adding a new source kernel.
