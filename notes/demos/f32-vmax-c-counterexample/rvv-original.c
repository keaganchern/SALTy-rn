/* Execute the repository's original RVV f32-vmax C function under Spike. */

#include <riscv_vector.h>
#include <stddef.h>
#include <stdint.h>

#define assert(condition) ((void) 0)
#define XNN_OOB_READS
#define XNN_UNLIKELY(condition) (condition)

struct xnn_f32_default_params {
  char unused;
};

/* Compile the real target function, without rewriting its intrinsic sequence. */
#include "../../../kernels/target/f32-vmax.c"

union f32_bits {
  uint32_t bits;
  float value;
};

uint32_t run_rvv_original(void) {
  union f32_bits input_a[4] = {
      {.bits = UINT32_C(0x00000000)},
      {.bits = UINT32_C(0x00000000)},
      {.bits = UINT32_C(0x00000000)},
      {.bits = UINT32_C(0x00000000)},
  };
  union f32_bits input_b[4] = {
      {.bits = UINT32_C(0x7FC00000)},
      {.bits = UINT32_C(0x7FC00000)},
      {.bits = UINT32_C(0x7FC00000)},
      {.bits = UINT32_C(0x7FC00000)},
  };
  union f32_bits output[4] = {
      {.bits = UINT32_C(0xFFFFFFFF)},
      {.bits = UINT32_C(0xFFFFFFFF)},
      {.bits = UINT32_C(0xFFFFFFFF)},
      {.bits = UINT32_C(0xFFFFFFFF)},
  };
  const struct xnn_f32_default_params params = {0};

  test_rvv(sizeof(input_a), &input_a[0].value, &input_b[0].value,
      &output[0].value, &params);
  return output[0].bits;
}
