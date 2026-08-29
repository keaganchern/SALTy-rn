#ifndef SALT_ELEMENTWISE_SHARED_FACADE_H
#define SALT_ELEMENTWISE_SHARED_FACADE_H

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
#define INT32_C(value) value
#define UINT16_C(value) value
#define UINT32_C(value) value##U
#define __RISCV_VXRM_RDN 2
#if defined(__aarch64__)
#define XNN_ARCH_ARM64 1
#else
#define XNN_ARCH_ARM64 0
#endif
#define XNN_ARCH_ARM 0

struct xnn_f32_default_params { char opaque; };
struct xnn_f32_lrelu_params { struct { float slope; } scalar; };
struct xnn_qs8_f32_cvt_params { struct { int32_t zero_point; float scale; } scalar; };
struct xnn_qu8_f32_cvt_params { struct { int32_t zero_point; float scale; } scalar; };
union xnn_qs8_mul_minmax_params { struct { int8_t a_zero_point; int8_t b_zero_point; float scale; int16_t output_zero_point; int8_t output_min; int8_t output_max; } scalar; };

typedef struct { unsigned char opaque[1]; } float32x2_t;
typedef struct { unsigned char opaque[1]; } float32x4_t;
typedef struct { unsigned char opaque[1]; } int16x4_t;
typedef struct { unsigned char opaque[1]; } int16x8_t;
typedef struct { unsigned char opaque[1]; } int32x4_t;
typedef struct { unsigned char opaque[1]; } int8x16_t;
typedef struct { unsigned char opaque[1]; } int8x8_t;
typedef struct { unsigned char opaque[1]; } uint16x4_t;
typedef struct { unsigned char opaque[1]; } uint16x8_t;
typedef struct { unsigned char opaque[1]; } uint32x2_t;
typedef struct { unsigned char opaque[1]; } uint32x4_t;
typedef struct { unsigned char opaque[1]; } uint8x8_t;
typedef struct { unsigned char opaque[1]; } vbool4_t;
typedef struct { unsigned char opaque[1]; } vfloat32m8_t;
typedef struct { unsigned char opaque[1]; } vint16m4_t;
typedef struct { unsigned char opaque[1]; } vint32m8_t;
typedef struct { unsigned char opaque[1]; } vint8m2_t;
typedef struct { unsigned char opaque[1]; } vint8m8_t;
typedef struct { unsigned char opaque[1]; } vuint16m4_t;
typedef struct { unsigned char opaque[1]; } vuint32m8_t;
typedef struct { unsigned char opaque[1]; } vuint8m2_t;

float32x4_t vabsq_f32(float32x4_t value);
uint16x4_t vadd_u16(uint16x4_t left, uint16x4_t right);
float32x4_t vaddq_f32(float32x4_t left, float32x4_t right);
uint16x8_t vaddq_u16(uint16x8_t left, uint16x8_t right);
uint32x4_t vaddq_u32(uint32x4_t left, uint32x4_t right);
int16x8_t vaddw_s8(int16x8_t wide, int8x8_t narrow);
uint16x8_t vaddw_u8(uint16x8_t wide, uint8x8_t narrow);
uint16x4_t vand_u16(uint16x4_t left, uint16x4_t right);
uint16x8_t vandq_u16(uint16x8_t left, uint16x8_t right);
uint32x4_t vandq_u32(uint32x4_t left, uint32x4_t right);
uint16x4_t vbsl_u16(uint16x4_t mask, uint16x4_t if_true, uint16x4_t if_false);
float32x4_t vbslq_f32(uint32x4_t mask, float32x4_t if_true, float32x4_t if_false);
int16x8_t vbslq_s16(uint16x8_t mask, int16x8_t if_true, int16x8_t if_false);
uint16x8_t vbslq_u16(uint16x8_t mask, uint16x8_t if_true, uint16x8_t if_false);
uint32x4_t vcaltq_f32(float32x4_t left, float32x4_t right);
uint32x4_t vcgtq_u32(uint32x4_t left, uint32x4_t right);
uint16x8_t vcltq_s16(int16x8_t left, int16x8_t right);
uint32x4_t vcltq_s32(int32x4_t left, int32x4_t right);
int16x8_t vcombine_s16(int16x4_t low, int16x4_t high);
int8x16_t vcombine_s8(int8x8_t low, int8x8_t high);
uint16x8_t vcombine_u16(uint16x4_t low, uint16x4_t high);
float32x4_t vcvtq_f32_s32(int32x4_t value);
float32x4_t vdivq_f32(float32x4_t left, float32x4_t right);
int8x8_t vdup_n_s8(int8_t value);
uint8x8_t vdup_n_u8(uint8_t value);
float32x4_t vdupq_n_f32(float value);
int16x8_t vdupq_n_s16(int16_t value);
int32x4_t vdupq_n_s32(int32_t value);
int8x16_t vdupq_n_s8(int8_t value);
uint16x8_t vdupq_n_u16(uint16_t value);
uint32x4_t vdupq_n_u32(uint32_t value);
int8x8_t vext_s8(int8x8_t left, int8x8_t right, int offset);
uint16x4_t vext_u16(uint16x4_t left, uint16x4_t right, int offset);
uint8x8_t vext_u8(uint8x8_t left, uint8x8_t right, int offset);
float32x2_t vget_high_f32(float32x4_t vector);
int16x4_t vget_high_s16(int16x8_t vector);
float32x2_t vget_low_f32(float32x4_t vector);
int16x4_t vget_low_s16(int16x8_t vector);
int8x8_t vget_low_s8(int8x16_t vector);
uint16x4_t vget_low_u16(uint16x8_t value);
int8x8_t vld1_s8(const int8_t * base);
uint8x8_t vld1_u8(const uint8_t * base);
float32x4_t vld1q_dup_f32(const float * base);
float32x4_t vld1q_f32(const float * base);
int8x16_t vld1q_s8(const int8_t * base);
int8x8_t vmax_s8(int8x8_t left, int8x8_t right);
uint8x8_t vmax_u8(uint8x8_t left, uint8x8_t right);
float32x4_t vmaxq_f32(float32x4_t left, float32x4_t right);
int8x16_t vmaxq_s8(int8x16_t left, int8x16_t right);
uint32x4_t vmaxq_u32(uint32x4_t left, uint32x4_t right);
int8x8_t vmin_s8(int8x8_t left, int8x8_t right);
uint8x8_t vmin_u8(uint8x8_t left, uint8x8_t right);
float32x4_t vminq_f32(float32x4_t left, float32x4_t right);
int8x16_t vminq_s8(int8x16_t left, int8x16_t right);
int32x4_t vmlaq_s32(int32x4_t acc, int32x4_t left, int32x4_t right);
int32x4_t vmovl_s16(int16x4_t vector);
uint16x4_t vmovn_u32(uint32x4_t value);
int16x8_t vmovq_n_s16(int16_t value);
int32x4_t vmovq_n_s32(int32_t value);
uint32x4_t vmovq_n_u32(uint32_t value);
int32x4_t vmull_s16(int16x4_t left, int16x4_t right);
float32x4_t vmulq_f32(float32x4_t left, float32x4_t right);
int32x4_t vmulq_s32(int32x4_t left, int32x4_t right);
uint16x4_t vorr_u16(uint16x4_t left, uint16x4_t right);
uint16x8_t vorrq_u16(uint16x8_t left, uint16x8_t right);
uint32x4_t vorrq_u32(uint32x4_t left, uint32x4_t right);
int16x8_t vqaddq_s16(int16x8_t left, int16x8_t right);
int16x8_t vqmovn_high_s32(int16x4_t low, int32x4_t high);
int8x8_t vqmovn_s16(int16x8_t vector);
int16x4_t vqmovn_s32(int32x4_t vector);
uint8x8_t vqmovun_s16(int16x8_t vector);
int16x8_t vqrdmulhq_s16(int16x8_t left, int16x8_t right);
int32x4_t vqsubq_s32(int32x4_t left, int32x4_t right);
uint16x4_t vreinterpret_u16_s8(int8x8_t value);
uint16x4_t vreinterpret_u16_u8(uint8x8_t value);
uint32x2_t vreinterpret_u32_s8(int8x8_t value);
uint32x2_t vreinterpret_u32_u16(uint16x4_t value);
uint32x2_t vreinterpret_u32_u8(uint8x8_t value);
float32x4_t vreinterpretq_f32_u32(uint32x4_t value);
int16x8_t vreinterpretq_s16_u16(uint16x8_t value);
int32x4_t vreinterpretq_s32_f32(float32x4_t value);
uint16x8_t vreinterpretq_u16_s16(int16x8_t value);
uint32x4_t vreinterpretq_u32_f32(float32x4_t value);
int32x4_t vrshlq_s32(int32x4_t vector, int32x4_t shift);
int16x8_t vshlq_n_s16(int16x8_t vector, int shift);
uint16x4_t vshrn_n_u32(uint32x4_t value, int shift);
float32x4_t vsqrtq_f32(float32x4_t value);
void vst1_f32(float * base, float32x2_t value);
void vst1_lane_f32(float * base, float32x2_t value, int lane);
void vst1_lane_s8(int8_t * base, int8x8_t value, int lane);
void vst1_lane_u16(uint16_t * base, uint16x4_t value, int lane);
void vst1_lane_u32(uint32_t * base, uint32x2_t value, int lane);
void vst1_lane_u8(uint8_t * base, uint8x8_t value, int lane);
void vst1_s8(int8_t * base, int8x8_t value);
void vst1_u16(uint16_t * base, uint16x4_t value);
void vst1_u8(uint8_t * base, uint8x8_t value);
void vst1q_f32(float * base, float32x4_t value);
void vst1q_s8(int8_t * base, int8x16_t value);
void vst1q_u16(uint16_t * base, uint16x8_t value);
int16x8_t vsubl_s8(int8x8_t left, int8x8_t right);
uint16x8_t vsubl_u8(uint8x8_t left, uint8x8_t right);
float32x4_t vsubq_f32(float32x4_t left, float32x4_t right);
int16x8_t vsubw_s8(int16x8_t wide, int8x8_t narrow);
vuint16m4_t __riscv_vadd_vv_u16m4(vuint16m4_t left, vuint16m4_t right, size_t vl);
vint32m8_t __riscv_vadd_vx_i32m8(vint32m8_t value, int32_t scalar, size_t vl);
vuint16m4_t __riscv_vadd_vx_u16m4(vuint16m4_t value, uint16_t scalar, size_t vl);
vuint32m8_t __riscv_vadd_vx_u32m8(vuint32m8_t value, uint32_t scalar, size_t vl);
vuint16m4_t __riscv_vand_vx_u16m4(vuint16m4_t value, uint16_t scalar, size_t vl);
vuint32m8_t __riscv_vand_vx_u32m8(vuint32m8_t value, uint32_t scalar, size_t vl);
vfloat32m8_t __riscv_vfabs_v_f32m8(vfloat32m8_t value, size_t vl);
vfloat32m8_t __riscv_vfadd_vf_f32m8(vfloat32m8_t vector, float scalar, size_t vl);
vfloat32m8_t __riscv_vfadd_vv_f32m8(vfloat32m8_t left, vfloat32m8_t right, size_t vl);
vfloat32m8_t __riscv_vfcvt_f_x_v_f32m8(vint32m8_t value, size_t vl);
vint32m8_t __riscv_vfcvt_x_f_v_i32m8(vfloat32m8_t value, size_t vl);
vfloat32m8_t __riscv_vfdiv_vv_f32m8(vfloat32m8_t left, vfloat32m8_t right, size_t vl);
vfloat32m8_t __riscv_vfmax_vv_f32m8(vfloat32m8_t left, vfloat32m8_t right, size_t vl);
vfloat32m8_t __riscv_vfmin_vv_f32m8(vfloat32m8_t left, vfloat32m8_t right, size_t vl);
vfloat32m8_t __riscv_vfmul_vf_f32m8(vfloat32m8_t vector, float scalar, size_t vl);
vfloat32m8_t __riscv_vfmul_vv_f32m8(vfloat32m8_t left, vfloat32m8_t right, size_t vl);
vfloat32m8_t __riscv_vfsgnj_vv_f32m8(vfloat32m8_t magnitude, vfloat32m8_t sign, size_t vl);
vfloat32m8_t __riscv_vfsqrt_v_f32m8(vfloat32m8_t value, size_t vl);
vfloat32m8_t __riscv_vfsub_vf_f32m8(vfloat32m8_t vector, float scalar, size_t vl);
vfloat32m8_t __riscv_vfsub_vv_f32m8(vfloat32m8_t left, vfloat32m8_t right, size_t vl);
vfloat32m8_t __riscv_vle32_v_f32m8(const float * base, size_t vl);
vint8m2_t __riscv_vle8_v_i8m2(const int8_t * base, size_t vl);
vint8m8_t __riscv_vle8_v_i8m8(const int8_t * base, size_t vl);
vuint8m2_t __riscv_vle8_v_u8m2(const uint8_t * base, size_t vl);
vint32m8_t __riscv_vmacc_vx_i32m8(vint32m8_t destination, int32_t scalar, vint32m8_t source, size_t vl);
vint16m4_t __riscv_vmax_vx_i16m4(vint16m4_t vector, int16_t scalar, size_t vl);
vint8m2_t __riscv_vmax_vx_i8m2(vint8m2_t vector, int8_t scalar, size_t vl);
vint8m8_t __riscv_vmax_vx_i8m8(vint8m8_t vector, int8_t scalar, size_t vl);
vuint32m8_t __riscv_vmaxu_vx_u32m8(vuint32m8_t value, uint32_t scalar, size_t vl);
vuint8m2_t __riscv_vmaxu_vx_u8m2(vuint8m2_t vector, uint8_t scalar, size_t vl);
vfloat32m8_t __riscv_vmerge_vvm_f32m8(vfloat32m8_t if_false, vfloat32m8_t if_true, vbool4_t mask, size_t vl);
vint16m4_t __riscv_vmerge_vxm_i16m4(vint16m4_t if_false, int16_t if_true, vbool4_t mask, size_t vl);
vuint16m4_t __riscv_vmerge_vxm_u16m4(vuint16m4_t base, uint16_t replacement, vbool4_t mask, size_t vl);
vbool4_t __riscv_vmfgt_vf_f32m8_b4(vfloat32m8_t vector, float scalar, size_t vl);
vbool4_t __riscv_vmfne_vv_f32m8_b4(vfloat32m8_t left, vfloat32m8_t right, size_t vl);
vint8m2_t __riscv_vmin_vx_i8m2(vint8m2_t vector, int8_t scalar, size_t vl);
vint8m8_t __riscv_vmin_vx_i8m8(vint8m8_t vector, int8_t scalar, size_t vl);
vuint8m2_t __riscv_vminu_vx_u8m2(vuint8m2_t vector, uint8_t scalar, size_t vl);
vbool4_t __riscv_vmsgtu_vx_u32m8_b4(vuint32m8_t value, uint32_t scalar, size_t vl);
vbool4_t __riscv_vmslt_vx_i16m4_b4(vint16m4_t vector, int16_t scalar, size_t vl);
vbool4_t __riscv_vmslt_vx_i32m8_b4(vint32m8_t vector, int32_t scalar, size_t vl);
vint32m8_t __riscv_vmul_vx_i32m8(vint32m8_t vector, int32_t scalar, size_t vl);
vint16m4_t __riscv_vmv_v_x_i16m4(int16_t value, size_t vl);
vint16m4_t __riscv_vnclip_wx_i16m4(vint32m8_t vector, size_t shift, unsigned int vxrm, size_t vl);
vint8m2_t __riscv_vnclip_wx_i8m2(vint16m4_t vector, size_t shift, unsigned int vxrm, size_t vl);
vuint8m2_t __riscv_vnclipu_wx_u8m2(vuint16m4_t vector, size_t shift, unsigned int vxrm, size_t vl);
vuint16m4_t __riscv_vnsrl_wx_u16m4(vuint32m8_t value, size_t shift, size_t vl);
vuint16m4_t __riscv_vor_vv_u16m4(vuint16m4_t left, vuint16m4_t right, size_t vl);
vuint32m8_t __riscv_vor_vx_u32m8(vuint32m8_t vector, uint32_t scalar, size_t vl);
vint32m8_t __riscv_vreinterpret_v_f32m8_i32m8(vfloat32m8_t value);
vuint32m8_t __riscv_vreinterpret_v_f32m8_u32m8(vfloat32m8_t value);
vuint16m4_t __riscv_vreinterpret_v_i16m4_u16m4(vint16m4_t value);
vint16m4_t __riscv_vreinterpret_v_u16m4_i16m4(vuint16m4_t value);
vfloat32m8_t __riscv_vreinterpret_v_u32m8_f32m8(vuint32m8_t value);
vint16m4_t __riscv_vrsub_vx_i16m4(vint16m4_t vector, int16_t scalar, size_t vl);
vint16m4_t __riscv_vsadd_vx_i16m4(vint16m4_t vector, int16_t scalar, size_t vl);
void __riscv_vse16_v_u16m4(uint16_t * base, vuint16m4_t value, size_t vl);
void __riscv_vse32_v_f32m8(float * base, vfloat32m8_t value, size_t vl);
void __riscv_vse8_v_i8m2(int8_t * base, vint8m2_t value, size_t vl);
void __riscv_vse8_v_i8m8(int8_t * base, vint8m8_t value, size_t vl);
void __riscv_vse8_v_u8m2(uint8_t * base, vuint8m2_t value, size_t vl);
size_t __riscv_vsetvl_e32m8(size_t avl);
size_t __riscv_vsetvl_e8m2(size_t avl);
size_t __riscv_vsetvl_e8m8(size_t avl);
vint16m4_t __riscv_vsext_vf2_i16m4(vint8m2_t vector, size_t vl);
vint32m8_t __riscv_vsext_vf2_i32m8(vint16m4_t vector, size_t vl);
vint16m4_t __riscv_vsll_vx_i16m4(vint16m4_t vector, size_t shift, size_t vl);
vint32m8_t __riscv_vsll_vx_i32m8(vint32m8_t vector, size_t shift, size_t vl);
vint32m8_t __riscv_vssra_vx_i32m8(vint32m8_t vector, size_t shift, unsigned int vxrm, size_t vl);
vint16m4_t __riscv_vsub_vx_i16m4(vint16m4_t value, int16_t scalar, size_t vl);
vint32m8_t __riscv_vwmul_vv_i32m8(vint16m4_t left, vint16m4_t right, size_t vl);
vint32m8_t __riscv_vwmul_vx_i32m8(vint16m4_t vector, int16_t scalar, size_t vl);
vint16m4_t __riscv_vwsub_vx_i16m4(vint8m2_t vector, int8_t scalar, size_t vl);
vuint16m4_t __riscv_vwsubu_vx_u16m4(vuint8m2_t vector, uint8_t scalar, size_t vl);
vuint16m4_t __riscv_vzext_vf2_u16m4(vuint8m2_t value, size_t vl);

#endif
