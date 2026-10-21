/* Execute the repository's original Neon f32-vmax C function on AArch64. */

#if !defined(__aarch64__)
#error "this half of the reproducer requires AArch64"
#endif

#include <arm_neon.h>
#include <assert.h>
#include <inttypes.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define XNN_OOB_READS
#define XNN_UNLIKELY(condition) (condition)

struct xnn_f32_default_params {
  char unused;
};

/* Compile the real source function, without rewriting its intrinsic sequence. */
#include "../../../kernels/source/f32-vmax.c"

static float f32_from_bits(uint32_t bits) {
  float value;
  memcpy(&value, &bits, sizeof(value));
  return value;
}

static uint32_t f32_to_bits(float value) {
  uint32_t bits;
  memcpy(&bits, &value, sizeof(bits));
  return bits;
}

int main(void) {
  const float input_a[4] = {
      f32_from_bits(UINT32_C(0x00000000)),
      f32_from_bits(UINT32_C(0x00000000)),
      f32_from_bits(UINT32_C(0x00000000)),
      f32_from_bits(UINT32_C(0x00000000)),
  };
  const float input_b[4] = {
      f32_from_bits(UINT32_C(0x7FC00000)),
      f32_from_bits(UINT32_C(0x7FC00000)),
      f32_from_bits(UINT32_C(0x7FC00000)),
      f32_from_bits(UINT32_C(0x7FC00000)),
  };
  float output[4] = {0};
  const struct xnn_f32_default_params params = {0};

  uint64_t saved_fpcr;
  __asm__ volatile("mrs %0, fpcr" : "=r"(saved_fpcr));
  const uint64_t reviewed_fpcr = saved_fpcr &
      ~((UINT64_C(1) << 1) |
        (UINT64_C(3) << 22) |
        (UINT64_C(1) << 24) |
        (UINT64_C(1) << 25) |
        (UINT64_C(0x1F) << 8) |
        (UINT64_C(1) << 15));
  __asm__ volatile("msr fpcr, %0\nisb" : : "r"(reviewed_fpcr) : "memory");

  test_neon(sizeof(input_a), input_a, input_b, output, &params);
  const uint32_t result = f32_to_bits(output[0]);

  __asm__ volatile("msr fpcr, %0\nisb" : : "r"(saved_fpcr) : "memory");
  printf("Neon original C output: 0x%08" PRIX32 "\n", result);
  return result == UINT32_C(0x7FC00000) ? 0 : 1;
}
