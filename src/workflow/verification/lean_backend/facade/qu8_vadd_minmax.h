#ifndef SALT_LEAN_QU8_VADD_MINMAX_FACADE_H
#define SALT_LEAN_QU8_VADD_MINMAX_FACADE_H

/* Parse-only declarations; this file assigns no intrinsic semantics. */
#include "integer_types.h"

struct xnn_qu8_add_minmax_params {
  struct {
    uint8_t a_zero_point;
    uint8_t b_zero_point;
    int32_t bias;
    int32_t a_multiplier;
    int32_t b_multiplier;
    int32_t shift;
    int16_t output_zero_point;
    uint8_t output_min;
    uint8_t output_max;
  } scalar;
};

uint8x8_t vdup_n_u8(uint8_t);
int32x4_t vdupq_n_s32(int32_t);
int16x8_t vdupq_n_s16(int16_t);
uint8x8_t vld1_u8(const uint8_t*);
uint16x8_t vsubl_u8(uint8x8_t, uint8x8_t);
int16x8_t vreinterpretq_s16_u16(uint16x8_t);
int16x4_t vget_low_s16(int16x8_t);
int16x4_t vget_high_s16(int16x8_t);
int32x4_t vmovl_s16(int16x4_t);
int32x4_t vmulq_s32(int32x4_t, int32x4_t);
int32x4_t vmlaq_s32(int32x4_t, int32x4_t, int32x4_t);
int32x4_t vrshlq_s32(int32x4_t, int32x4_t);
int16x4_t vqmovn_s32(int32x4_t);
int16x8_t vcombine_s16(int16x4_t, int16x4_t);
int16x8_t vqaddq_s16(int16x8_t, int16x8_t);
uint8x8_t vqmovun_s16(int16x8_t);
uint8x8_t vmax_u8(uint8x8_t, uint8x8_t);
uint8x8_t vmin_u8(uint8x8_t, uint8x8_t);
void vst1_u8(uint8_t*, uint8x8_t);
uint32x2_t vreinterpret_u32_u8(uint8x8_t);
void vst1_lane_u32(uint32_t*, uint32x2_t, int);
uint8x8_t vext_u8(uint8x8_t, uint8x8_t, int);
uint16x4_t vreinterpret_u16_u8(uint8x8_t);
void vst1_lane_u16(uint16_t*, uint16x4_t, int);
void vst1_lane_u8(uint8_t*, uint8x8_t, int);

size_t __riscv_vsetvl_e8m2(size_t);
vuint8m2_t __riscv_vle8_v_u8m2(const uint8_t*, size_t);
vuint16m4_t __riscv_vwsubu_vx_u16m4(vuint8m2_t, uint8_t, size_t);
vint16m4_t __riscv_vreinterpret_v_u16m4_i16m4(vuint16m4_t);
vint32m8_t __riscv_vsext_vf2_i32m8(vint16m4_t, size_t);
vint32m8_t __riscv_vmul_vx_i32m8(vint32m8_t, int32_t, size_t);
vint32m8_t __riscv_vmacc_vx_i32m8(vint32m8_t, int32_t, vint32m8_t, size_t);
vint32m8_t __riscv_vssra_vx_i32m8(vint32m8_t, size_t, unsigned int, size_t);
vint32m8_t __riscv_vsll_vx_i32m8(vint32m8_t, size_t, size_t);
vint16m4_t __riscv_vnclip_wx_i16m4(vint32m8_t, size_t, unsigned int, size_t);
vint16m4_t __riscv_vsadd_vx_i16m4(vint16m4_t, int16_t, size_t);
vint16m4_t __riscv_vmax_vx_i16m4(vint16m4_t, int16_t, size_t);
vuint16m4_t __riscv_vreinterpret_v_i16m4_u16m4(vint16m4_t);
vuint8m2_t __riscv_vnclipu_wx_u8m2(vuint16m4_t, size_t, unsigned int, size_t);
vuint8m2_t __riscv_vmaxu_vx_u8m2(vuint8m2_t, uint8_t, size_t);
vuint8m2_t __riscv_vminu_vx_u8m2(vuint8m2_t, uint8_t, size_t);
void __riscv_vse8_v_u8m2(uint8_t*, vuint8m2_t, size_t);

#endif
