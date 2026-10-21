#ifndef SALT_LEAN_S8_VCLAMP_FACADE_H
#define SALT_LEAN_S8_VCLAMP_FACADE_H

/* Parse-only declarations; this file assigns no intrinsic semantics. */
#include "integer_types.h"

struct xnn_s8_minmax_params {
  struct {
    int32_t min;
    int32_t max;
  } scalar;
};

int8x16_t vdupq_n_s8(int8_t);
int8x16_t vld1q_s8(const int8_t*);
int8x16_t vmaxq_s8(int8x16_t, int8x16_t);
int8x16_t vminq_s8(int8x16_t, int8x16_t);
void vst1q_s8(int8_t*, int8x16_t);
int8x8_t vld1_s8(const int8_t*);
int8x8_t vget_low_s8(int8x16_t);
int8x8_t vmin_s8(int8x8_t, int8x8_t);
int8x8_t vmax_s8(int8x8_t, int8x8_t);
void vst1_s8(int8_t*, int8x8_t);
uint32x2_t vreinterpret_u32_s8(int8x8_t);
void vst1_lane_u32(uint32_t*, uint32x2_t, int);
int8x8_t vext_s8(int8x8_t, int8x8_t, int);
uint16x4_t vreinterpret_u16_s8(int8x8_t);
void vst1_lane_u16(uint16_t*, uint16x4_t, int);
void vst1_lane_s8(int8_t*, int8x8_t, int);

size_t __riscv_vsetvl_e8m8(size_t);
vint8m8_t __riscv_vle8_v_i8m8(const int8_t*, size_t);
vint8m8_t __riscv_vmax_vx_i8m8(vint8m8_t, int8_t, size_t);
vint8m8_t __riscv_vmin_vx_i8m8(vint8m8_t, int8_t, size_t);
void __riscv_vse8_v_i8m8(int8_t*, vint8m8_t, size_t);

#endif
