#ifndef SALT_LEAN_QS8_VLRELU_FACADE_H
#define SALT_LEAN_QS8_VLRELU_FACADE_H

/* Parse-only declarations; this file assigns no intrinsic semantics. */
#include "integer_types.h"

struct xnn_qs8_lrelu_params {
  struct {
    int32_t input_zero_point;
    int32_t positive_multiplier;
    int32_t negative_multiplier;
    int32_t output_zero_point;
  } scalar;
};

int16x8_t vdupq_n_s16(int16_t);
int16x8_t vmovq_n_s16(int16_t);
int8x8_t vld1_s8(const int8_t*);
int16x8_t vsubw_s8(int16x8_t, int8x8_t);
uint16x8_t vcltq_s16(int16x8_t, int16x8_t);
int16x8_t vshlq_n_s16(int16x8_t, int);
int16x8_t vbslq_s16(uint16x8_t, int16x8_t, int16x8_t);
int16x8_t vqrdmulhq_s16(int16x8_t, int16x8_t);
int16x8_t vqaddq_s16(int16x8_t, int16x8_t);
int8x8_t vqmovn_s16(int16x8_t);
void vst1_s8(int8_t*, int8x8_t);
uint32x2_t vreinterpret_u32_s8(int8x8_t);
void vst1_lane_u32(uint32_t*, uint32x2_t, int);
int8x8_t vext_s8(int8x8_t, int8x8_t, int);
uint16x4_t vreinterpret_u16_s8(int8x8_t);
void vst1_lane_u16(uint16_t*, uint16x4_t, int);
void vst1_lane_s8(int8_t*, int8x8_t, int);

size_t __riscv_vsetvl_e8m2(size_t);
vint8m2_t __riscv_vle8_v_i8m2(const int8_t*, size_t);
vint16m4_t __riscv_vsext_vf2_i16m4(vint8m2_t, size_t);
vint16m4_t __riscv_vrsub_vx_i16m4(vint16m4_t, int16_t, size_t);
vbool4_t __riscv_vmslt_vx_i16m4_b4(vint16m4_t, int16_t, size_t);
vint16m4_t __riscv_vsll_vx_i16m4(vint16m4_t, size_t, size_t);
vint16m4_t __riscv_vmv_v_x_i16m4(int16_t, size_t);
vint16m4_t __riscv_vmerge_vxm_i16m4(vint16m4_t, int16_t, vbool4_t, size_t);
vint32m8_t __riscv_vwmul_vv_i32m8(vint16m4_t, vint16m4_t, size_t);
vint16m4_t __riscv_vnclip_wx_i16m4(vint32m8_t, size_t, unsigned int, size_t);
vint16m4_t __riscv_vsadd_vx_i16m4(vint16m4_t, int16_t, size_t);
vint8m2_t __riscv_vnclip_wx_i8m2(vint16m4_t, size_t, unsigned int, size_t);
void __riscv_vse8_v_i8m2(int8_t*, vint8m2_t, size_t);

#endif
