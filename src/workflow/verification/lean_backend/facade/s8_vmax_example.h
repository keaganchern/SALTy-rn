#ifndef SALT_LEAN_S8_VMAX_EXAMPLE_FACADE_H
#define SALT_LEAN_S8_VMAX_EXAMPLE_FACADE_H

/* Parse-only declarations; this file assigns no intrinsic semantics. */
#include "integer_types.h"

struct salt_s8_vmax_params {
  struct {
    int8_t threshold;
  } scalar;
};

int8x16_t vdupq_n_s8(int8_t);
int8x16_t vld1q_s8(const int8_t*);
int8x16_t vmaxq_s8(int8x16_t, int8x16_t);
int8x16_t vminq_s8(int8x16_t, int8x16_t);
void vst1q_s8(int8_t*, int8x16_t);

size_t __riscv_vsetvl_e8m8(size_t);
vint8m8_t __riscv_vle8_v_i8m8(const int8_t*, size_t);
vint8m8_t __riscv_vmax_vx_i8m8(vint8m8_t, int8_t, size_t);
void __riscv_vse8_v_i8m8(int8_t*, vint8m8_t, size_t);

#endif
