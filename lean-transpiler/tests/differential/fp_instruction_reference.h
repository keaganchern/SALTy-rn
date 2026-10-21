#ifndef SALTY_FP_INSTRUCTION_REFERENCE_H
#define SALTY_FP_INSTRUCTION_REFERENCE_H

/* ACLE maps vfma[q]_f32(a,b,c) to FMLA Vd,Vn,Vm with a,b,c respectively.
 * Clang 19's generic FMA lowering swaps Vn/Vm, even at O0 and with strict FP.
 * Multiplication remains numerically commutative, but NaN payload priority
 * does not. Pin just these two instructions for the instruction reference.
 * --fp-reference compiler omits this header and tests unmodified C intrinsics.
 * https://arm-software.github.io/acle/neon_intrinsics/advsimd.html
 */
#include <arm_neon.h>

static inline float32x2_t salty_test_fma2(float32x2_t a, float32x2_t b, float32x2_t c) {
  __asm__ volatile ("fmla %0.2s, %1.2s, %2.2s" : "+w"(a) : "w"(b), "w"(c));
  return a;
}

static inline float32x4_t salty_test_fma4(float32x4_t a, float32x4_t b, float32x4_t c) {
  __asm__ volatile ("fmla %0.4s, %1.4s, %2.4s" : "+w"(a) : "w"(b), "w"(c));
  return a;
}

#define vfma_f32(a,b,c) salty_test_fma2((a),(b),(c))
#define vfmaq_f32(a,b,c) salty_test_fma4((a),(b),(c))

#endif
