/*
 * Reproduce the signed-overflow input admitted by the historical QS8VAddC
 * Lean theorem but undefined by the corresponding C expression.
 *
 * Build and run:
 *   clang -std=c11 -O1 -fsanitize=undefined \
 *     notes/demos/qs8-vaddc-overflow.c -o /tmp/qs8-vaddc-overflow
 *   /tmp/qs8-vaddc-overflow
 *
 * UBSan is expected to report signed integer overflow.
 */

#include <stdint.h>
#include <stdio.h>

int main(void) {
  volatile int32_t input_b = 127;
  volatile int32_t b_zero_point = -128;
  volatile int32_t b_multiplier = INT32_MAX;
  const int32_t bias = (input_b - b_zero_point) * b_multiplier;
  printf("bias=%d\n", bias);
  return 0;
}
