#ifndef SALT_LEAN_QS8_VADD_MINMAX_FACADE_H
#define SALT_LEAN_QS8_VADD_MINMAX_FACADE_H

/*
 * Parse-only declarations for the current qs8-vadd-minmax kernel pair.
 *
 * The frontend records this file's hash in its result.  These declarations
 * provide types and exact call signatures to Clang; they do not define the
 * semantics of any intrinsic.
 */

typedef __SIZE_TYPE__ size_t;
typedef __INT8_TYPE__ int8_t;
typedef __INT16_TYPE__ int16_t;
typedef __INT32_TYPE__ int32_t;
typedef __UINT8_TYPE__ uint8_t;
typedef __UINT16_TYPE__ uint16_t;
typedef __UINT32_TYPE__ uint32_t;

#define NULL ((void*) 0)
#define assert(condition) ((void) 0)
#define XNN_OOB_READS
#define XNN_LIKELY(condition) (condition)
#define XNN_UNLIKELY(condition) (condition)

#define __RISCV_VXRM_RNU 0
#define __RISCV_VXRM_RDN 2

struct xnn_qs8_add_minmax_params {
  struct {
    int8_t a_zero_point;
    int8_t b_zero_point;
    int32_t bias;
    int32_t a_multiplier;
    int32_t b_multiplier;
    int32_t shift;
    int16_t output_zero_point;
    int8_t output_min;
    int8_t output_max;
  } scalar;
};

typedef struct { int8_t lanes[8]; } int8x8_t;
typedef struct { int8_t lanes[16]; } int8x16_t;
typedef struct { int16_t lanes[4]; } int16x4_t;
typedef struct { int16_t lanes[8]; } int16x8_t;
typedef struct { int32_t lanes[4]; } int32x4_t;
typedef struct { uint16_t lanes[4]; } uint16x4_t;
typedef struct { uint32_t lanes[2]; } uint32x2_t;

int8x8_t vdup_n_s8(int8_t);
int8x16_t vdupq_n_s8(int8_t);
int16x8_t vdupq_n_s16(int16_t);
int32x4_t vdupq_n_s32(int32_t);
int8x8_t vld1_s8(const int8_t*);
int16x8_t vsubl_s8(int8x8_t, int8x8_t);
int16x4_t vget_low_s16(int16x8_t);
int16x4_t vget_high_s16(int16x8_t);
int8x8_t vget_low_s8(int8x16_t);
int32x4_t vmovl_s16(int16x4_t);
int32x4_t vmulq_s32(int32x4_t, int32x4_t);
int32x4_t vmlaq_s32(int32x4_t, int32x4_t, int32x4_t);
int32x4_t vrshlq_s32(int32x4_t, int32x4_t);
int8x8_t vqmovn_s16(int16x8_t);
int16x4_t vqmovn_s32(int32x4_t);
int16x8_t vcombine_s16(int16x4_t, int16x4_t);
int8x16_t vcombine_s8(int8x8_t, int8x8_t);
int16x8_t vqaddq_s16(int16x8_t, int16x8_t);
int8x8_t vmax_s8(int8x8_t, int8x8_t);
int8x16_t vmaxq_s8(int8x16_t, int8x16_t);
int8x8_t vmin_s8(int8x8_t, int8x8_t);
int8x16_t vminq_s8(int8x16_t, int8x16_t);
void vst1_s8(int8_t*, int8x8_t);
void vst1q_s8(int8_t*, int8x16_t);
uint32x2_t vreinterpret_u32_s8(int8x8_t);
uint16x4_t vreinterpret_u16_s8(int8x8_t);
void vst1_lane_u32(uint32_t*, uint32x2_t, int);
void vst1_lane_u16(uint16_t*, uint16x4_t, int);
void vst1_lane_s8(int8_t*, int8x8_t, int);
int8x8_t vext_s8(int8x8_t, int8x8_t, int);

typedef struct { int8_t opaque; } vint8m2_t;
typedef struct { int16_t opaque; } vint16m4_t;
typedef struct { int32_t opaque; } vint32m8_t;

size_t __riscv_vsetvl_e8m2(size_t);
vint8m2_t __riscv_vle8_v_i8m2(const int8_t*, size_t);
vint16m4_t __riscv_vwsub_vx_i16m4(vint8m2_t, int8_t, size_t);
vint32m8_t __riscv_vsext_vf2_i32m8(vint16m4_t, size_t);
vint32m8_t __riscv_vmul_vx_i32m8(vint32m8_t, int32_t, size_t);
vint32m8_t __riscv_vmacc_vx_i32m8(vint32m8_t, int32_t, vint32m8_t, size_t);
vint32m8_t __riscv_vssra_vx_i32m8(vint32m8_t, size_t, unsigned int, size_t);
vint16m4_t __riscv_vnclip_wx_i16m4(vint32m8_t, size_t, unsigned int, size_t);
vint16m4_t __riscv_vsadd_vx_i16m4(vint16m4_t, int16_t, size_t);
vint8m2_t __riscv_vnclip_wx_i8m2(vint16m4_t, size_t, unsigned int, size_t);
vint8m2_t __riscv_vmax_vx_i8m2(vint8m2_t, int8_t, size_t);
vint8m2_t __riscv_vmin_vx_i8m2(vint8m2_t, int8_t, size_t);
void __riscv_vse8_v_i8m2(int8_t*, vint8m2_t, size_t);

#endif
