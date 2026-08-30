/*
 * AArch64 executable probe for the four generated Lean counterexamples.
 *
 * The Neon functions below execute the same lane operations used by the source
 * kernels.  The RVV functions are portable value oracles for the corresponding
 * target instruction sequence, so this file does not claim to execute an RVV
 * binary on the AArch64 host.  The chosen one-lane inputs make loop scheduling
 * irrelevant.
 *
 * Build and run on AArch64:
 *   clang -std=c11 -O2 -Wall -Wextra -Werror \
 *     notes/demos/neon-rvv-semantic-gap-aarch64.c \
 *     -o /tmp/neon-rvv-semantic-gap-aarch64
 *   /tmp/neon-rvv-semantic-gap-aarch64
 */

#if !defined(__aarch64__)
#error "this probe executes Arm Neon instructions and requires AArch64"
#endif

#include <arm_neon.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#if defined(__clang__) || defined(__GNUC__)
#define NOINLINE __attribute__((noinline))
#else
#define NOINLINE
#endif

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

static int f32_is_nan_bits(uint32_t bits) {
  return (bits & UINT32_C(0x7F800000)) == UINT32_C(0x7F800000) &&
      (bits & UINT32_C(0x007FFFFF)) != 0;
}

static NOINLINE uint32_t neon_vmax_lane(uint32_t left, uint32_t right) {
  const float32x4_t a = vdupq_n_f32(f32_from_bits(left));
  const float32x4_t b = vdupq_n_f32(f32_from_bits(right));
  return f32_to_bits(vgetq_lane_f32(vmaxq_f32(a, b), 0));
}

static NOINLINE uint32_t neon_vmin_lane(uint32_t left, uint32_t right) {
  const float32x4_t a = vdupq_n_f32(f32_from_bits(left));
  const float32x4_t b = vdupq_n_f32(f32_from_bits(right));
  return f32_to_bits(vgetq_lane_f32(vminq_f32(a, b), 0));
}

/* RVV VFMAX/VFMIN use maximumNumber/minimumNumber on active elements. */
static NOINLINE uint32_t rvv_maximum_number(uint32_t left, uint32_t right) {
  if (f32_is_nan_bits(left)) {
    return f32_is_nan_bits(right) ? UINT32_C(0x7FC00000) : right;
  }
  if (f32_is_nan_bits(right)) {
    return left;
  }
  const float a = f32_from_bits(left);
  const float b = f32_from_bits(right);
  if (a < b) return right;
  if (b < a) return left;
  if ((left & UINT32_C(0x7FFFFFFF)) == 0 &&
      (right & UINT32_C(0x7FFFFFFF)) == 0) {
    return left & right;
  }
  return left;
}

static NOINLINE uint32_t rvv_minimum_number(uint32_t left, uint32_t right) {
  if (f32_is_nan_bits(left)) {
    return f32_is_nan_bits(right) ? UINT32_C(0x7FC00000) : right;
  }
  if (f32_is_nan_bits(right)) {
    return left;
  }
  const float a = f32_from_bits(left);
  const float b = f32_from_bits(right);
  if (a < b) return left;
  if (b < a) return right;
  if ((left & UINT32_C(0x7FFFFFFF)) == 0 &&
      (right & UINT32_C(0x7FFFFFFF)) == 0) {
    return left | right;
  }
  return left;
}

/* Exact Neon main/tail operation orders from kernels/source/s8-vclamp.c. */
static NOINLINE int8_t neon_s8_main_lane(int8_t x, int8_t min, int8_t max) {
  int8x8_t value = vdup_n_s8(x);
  value = vmax_s8(value, vdup_n_s8(min));
  value = vmin_s8(value, vdup_n_s8(max));
  return vget_lane_s8(value, 0);
}

static NOINLINE int8_t neon_s8_tail_lane(int8_t x, int8_t min, int8_t max) {
  int8x8_t value = vdup_n_s8(x);
  value = vmin_s8(value, vdup_n_s8(max));
  value = vmax_s8(value, vdup_n_s8(min));
  return vget_lane_s8(value, 0);
}

/* Exact per-lane order from kernels/target/s8-vclamp.c. */
static NOINLINE int8_t rvv_s8_lane(int8_t x, int8_t min, int8_t max) {
  x = x > min ? x : min;
  return x < max ? x : max;
}

/* Exact Neon arithmetic/select sequence from kernels/source/f32-vrndne.c. */
static NOINLINE uint32_t neon_vrndne_lane(uint32_t input) {
  const float32x4_t x = vdupq_n_f32(f32_from_bits(input));
  const float32x4_t magic =
      vreinterpretq_f32_u32(vdupq_n_u32(UINT32_C(0x4B000000)));
  const float32x4_t abs_x = vabsq_f32(x);
  uint32x4_t mask = vcaltq_f32(magic, x);
  float32x4_t rounded_abs = vaddq_f32(abs_x, magic);
  mask = vorrq_u32(mask, vdupq_n_u32(UINT32_C(0x80000000)));
  rounded_abs = vsubq_f32(rounded_abs, magic);
  return f32_to_bits(vgetq_lane_f32(vbslq_f32(mask, x, rounded_abs), 0));
}

/* The final explicit NaN fixup in kernels/target/f32-vrndne.c. */
static NOINLINE uint32_t rvv_vrndne_nan_fixup(uint32_t input) {
  return input | UINT32_C(0x00400000);
}

static int check_u32(const char* name, uint32_t actual, uint32_t expected) {
  printf("%-27s 0x%08" PRIX32 "\n", name, actual);
  if (actual != expected) {
    fprintf(stderr, "%s: expected 0x%08" PRIX32 "\n", name, expected);
    return 1;
  }
  return 0;
}

static int check_i8(const char* name, int8_t actual, int8_t expected) {
  printf("%-27s %d\n", name, (int) actual);
  if (actual != expected) {
    fprintf(stderr, "%s: expected %d\n", name, (int) expected);
    return 1;
  }
  return 0;
}

int main(void) {
  volatile uint32_t zero = UINT32_C(0x00000000);
  volatile uint32_t qnan = UINT32_C(0x7FC00000);
  volatile uint32_t snan_payload = UINT32_C(0x7FA00001);

  uint64_t saved_fpcr;
  __asm__ volatile("mrs %0, fpcr" : "=r"(saved_fpcr));
  /*
   * Match the reviewed pure-value environment: AH=0, RMode=RN, FZ=0,
   * DN=0, and all six FP trap-enable bits clear.  FPSR flags are deliberately
   * outside this probe's value-result claim.
   */
  const uint64_t reviewed_fpcr = saved_fpcr &
      ~((UINT64_C(1) << 1) |
        (UINT64_C(3) << 22) |
        (UINT64_C(1) << 24) |
        (UINT64_C(1) << 25) |
        (UINT64_C(0x1F) << 8) |
        (UINT64_C(1) << 15));
  __asm__ volatile("msr fpcr, %0\nisb" : : "r"(reviewed_fpcr) : "memory");

  int failed = 0;
  failed |= check_u32("f32-vmax Neon", neon_vmax_lane(zero, qnan), qnan);
  failed |= check_u32("f32-vmax RVV oracle",
      rvv_maximum_number(zero, qnan), zero);
  failed |= check_u32("f32-vmin Neon", neon_vmin_lane(zero, qnan), qnan);
  failed |= check_u32("f32-vmin RVV oracle",
      rvv_minimum_number(zero, qnan), zero);

  failed |= check_u32("f32-vrndne Neon",
      neon_vrndne_lane(snan_payload), UINT32_C(0x7FE00001));
  failed |= check_u32("f32-vrndne RVV fixup",
      rvv_vrndne_nan_fixup(snan_payload), UINT32_C(0x7FE00001));
  failed |= check_u32("f32-vrndne Lean repaired", UINT32_C(0x7FE00001),
      UINT32_C(0x7FE00001));

  failed |= check_i8("s8-vclamp Neon main",
      neon_s8_main_lane(0, 5, 0), 0);
  failed |= check_i8("s8-vclamp Neon tail",
      neon_s8_tail_lane(0, 5, 0), 5);
  failed |= check_i8("s8-vclamp RVV oracle", rvv_s8_lane(0, 5, 0), 0);

  __asm__ volatile("msr fpcr, %0\nisb" : : "r"(saved_fpcr) : "memory");

  if (failed == 0) {
    puts("PASS: three real gaps and repaired vrndne alignment reproduced");
  }
  return failed != 0;
}
