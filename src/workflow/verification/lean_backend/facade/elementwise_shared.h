#ifndef SALT_ELEMENTWISE_SHARED_FACADE_H
#define SALT_ELEMENTWISE_SHARED_FACADE_H

typedef __SIZE_TYPE__ size_t;

#define NULL ((void*) 0)
#define assert(condition) ((void) 0)

typedef struct { unsigned char opaque[1]; } float32x2_t;
typedef struct { unsigned char opaque[1]; } float32x4_t;
typedef struct { unsigned char opaque[1]; } vfloat32m8_t;

float32x2_t vget_high_f32(float32x4_t vector);
float32x2_t vget_low_f32(float32x4_t vector);
float32x4_t vld1q_f32(const float * base);
void vst1_f32(float * base, float32x2_t value);
void vst1_lane_f32(float * base, float32x2_t value, int lane);
void vst1q_f32(float * base, float32x4_t value);
vfloat32m8_t __riscv_vle32_v_f32m8(const float * base, size_t vl);
void __riscv_vse32_v_f32m8(float * base, vfloat32m8_t value, size_t vl);
size_t __riscv_vsetvl_e32m8(size_t avl);

#endif
