#include "intrinsics_facade.h"

void s8_clamp16_neon(
    const int8_t* input,
    int8_t* output,
    int8_t lo,
    int8_t hi)
{
  const int8x16_t lower = vdupq_n_s8(lo);
  const int8x16_t upper = vdupq_n_s8(hi);
  int8x16_t value = vld1q_s8(input);
  value = vmaxq_s8(value, lower);
  value = vminq_s8(value, upper);
  vst1q_s8(output, value);
}
