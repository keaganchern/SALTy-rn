/*
 * Parse-only declarations for the current-main s8-vclamp pair.
 *
 * This file deliberately supplies types and intrinsic spellings only. It does
 * not assign semantics to any Neon or RVV operation.
 */

typedef signed char int8_t;
typedef signed int int32_t;
typedef unsigned short uint16_t;
typedef unsigned int uint32_t;
typedef unsigned long size_t;

typedef struct { int8_t lanes[8]; } int8x8_t;
typedef struct { int8_t lanes[16]; } int8x16_t;
typedef struct { uint16_t lanes[4]; } uint16x4_t;
typedef struct { uint32_t lanes[2]; } uint32x2_t;
typedef struct { int8_t opaque[1]; } vint8m8_t;

struct xnn_s8_minmax_params {
  struct {
    int32_t min;
    int32_t max;
  } scalar;
};

#define XNN_OOB_READS
#define XNN_UNLIKELY(x) (x)
#define NULL ((void*) 0)
#define assert(x) ((void) (x))

int8x16_t vdupq_n_s8(int8_t x);
int8x16_t vld1q_s8(const int8_t* p);
int8x8_t vld1_s8(const int8_t* p);
int8x16_t vmaxq_s8(int8x16_t a, int8x16_t b);
int8x16_t vminq_s8(int8x16_t a, int8x16_t b);
int8x8_t vmax_s8(int8x8_t a, int8x8_t b);
int8x8_t vmin_s8(int8x8_t a, int8x8_t b);
int8x8_t vget_low_s8(int8x16_t x);
uint32x2_t vreinterpret_u32_s8(int8x8_t x);
uint16x4_t vreinterpret_u16_s8(int8x8_t x);
int8x8_t vext_s8(int8x8_t a, int8x8_t b, int n);
void vst1q_s8(int8_t* p, int8x16_t x);
void vst1_s8(int8_t* p, int8x8_t x);
void vst1_lane_u32(void* p, uint32x2_t x, int lane);
void vst1_lane_u16(void* p, uint16x4_t x, int lane);
void vst1_lane_s8(int8_t* p, int8x8_t x, int lane);

size_t __riscv_vsetvl_e8m8(size_t avl);
vint8m8_t __riscv_vle8_v_i8m8(const int8_t* p, size_t vl);
vint8m8_t __riscv_vmax_vx_i8m8(vint8m8_t x, int8_t y, size_t vl);
vint8m8_t __riscv_vmin_vx_i8m8(vint8m8_t x, int8_t y, size_t vl);
void __riscv_vse8_v_i8m8(int8_t* p, vint8m8_t x, size_t vl);
