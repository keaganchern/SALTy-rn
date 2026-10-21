#ifndef SALTYRN_S8_CLAMP16_INTRINSICS_FACADE_H
#define SALTYRN_S8_CLAMP16_INTRINSICS_FACADE_H

typedef __SIZE_TYPE__ size_t;
typedef signed char int8_t;

typedef int8_t int8x16_t __attribute__((ext_vector_type(16)));
typedef int8_t vint8m1_t __attribute__((ext_vector_type(16)));

int8x16_t vld1q_s8(const int8_t* input);
int8x16_t vdupq_n_s8(int8_t value);
int8x16_t vmaxq_s8(int8x16_t left, int8x16_t right);
int8x16_t vminq_s8(int8x16_t left, int8x16_t right);
void vst1q_s8(int8_t* output, int8x16_t value);

size_t __riscv_vsetvl_e8m1(size_t remaining);
vint8m1_t __riscv_vle8_v_i8m1(const int8_t* input, size_t vl);
vint8m1_t __riscv_vmax_vx_i8m1(vint8m1_t value, int8_t bound, size_t vl);
vint8m1_t __riscv_vmin_vx_i8m1(vint8m1_t value, int8_t bound, size_t vl);
void __riscv_vse8_v_i8m1(int8_t* output, vint8m1_t value, size_t vl);

#endif
