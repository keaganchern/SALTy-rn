#include "intrinsics_facade.h"

void s8_clamp16_rvv(
    const int8_t* input,
    int8_t* output,
    int8_t lo,
    int8_t hi)
{
  size_t remaining = 16;
  while (remaining != 0) {
    const size_t vl = __riscv_vsetvl_e8m1(remaining);
    vint8m1_t value = __riscv_vle8_v_i8m1(input, vl);
    value = __riscv_vmax_vx_i8m1(value, lo, vl);
    value = __riscv_vmin_vx_i8m1(value, hi, vl);
    __riscv_vse8_v_i8m1(output, value, vl);
    input += vl;
    output += vl;
    remaining -= vl;
  }
}
