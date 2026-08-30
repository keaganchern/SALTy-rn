# Original-C `f32-vmax` counterexample

This reproducer compiles the repository's two original functions directly:

- `kernels/source/f32-vmax.c::test_neon`
- `kernels/target/f32-vmax.c::test_rvv`

All four lanes receive `(+0.0, qNaN)` with bit patterns `0x00000000` and
`0x7FC00000`. The Arm function executes `vmaxq_f32` (`FMAX`) and returns the NaN;
the RVV function executes `__riscv_vfmax_vv_f32m8` (`vfmax.vv`) and returns the
numeric operand `+0.0`.

On an AArch64 host with LLVM's RISC-V headers/toolchain and Spike installed, run:

```sh
notes/demos/f32-vmax-c-counterexample/run.sh
```

Expected output:

```text
Neon original C output: 0x7FC00000
RVV original C output:  0x00000000
PASS: original C kernels disagree for (+0.0, qNaN)
```

The RVV startup wrapper adds one to `a0` only after `test_rvv` returns. This makes
an all-zero C result visible in Spike's commit log; the reported C result removes
that observation-only offset.
