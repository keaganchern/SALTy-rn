#include <fenv.h>
#include <float.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#pragma STDC FENV_ACCESS ON

/*
 * Reproduce the value-semantics difference behind a historical F32 VELU
 * modeling gap. The historical symbolic Neon shim modeled vmlaq_f32 as
 * separately rounded multiply/add, while RVV vfmacc is fused. The historical
 * Lean model used the non-fused expression for both sides.
 *
 * This does not claim that every compiled AArch64 vmlaq_f32 remains
 * non-fused: compiler contraction may emit FMLA.
 *
 * Build and run:
 *   clang -std=c11 -O2 -fno-fast-math -frounding-math \
 *     -ffp-contract=off \
 *     notes/demos/f32-velu-fma-counterexample.c -lm \
 *     -o /tmp/f32-velu-fma-counterexample
 *   /tmp/f32-velu-fma-counterexample
 *
 * Exit status 0 means the exact expected pair was reproduced. Status 2 means
 * that the host floating-point environment is unsupported.
 */

#if FLT_RADIX != 2 || FLT_MANT_DIG != 24 || FLT_MAX_EXP != 128
#error "This reproducer requires IEEE-754 binary32 float."
#endif

_Static_assert(sizeof(float) == sizeof(uint32_t), "float must be 32 bits");

static const uint32_t table[16] = {
  0x3F800000u, 0x3F7DAAC3u, 0x3F7B95C2u, 0x3F79C3D3u,
  0x3F7837F0u, 0x3F76F532u, 0x3F75FED7u, 0x3F75583Fu,
  0x3F7504F3u, 0x3F7508A4u, 0x3F75672Au, 0x3F76248Cu,
  0x3F7744FDu, 0x3F78CCDFu, 0x3F7AC0C7u, 0x3F7D257Du,
};

static float from_bits(uint32_t bits) {
  float value;
  memcpy(&value, &bits, sizeof(value));
  return value;
}

static uint32_t to_bits(float value) {
  uint32_t bits;
  memcpy(&bits, &value, sizeof(bits));
  return bits;
}

static float mul_add_separate(float addend, float left, float right) {
  volatile float product = left * right;
  volatile float result = addend + product;
  return result;
}

static float elu(float x, int fused) {
  const float sat_cutoff = -0x1.154246p+4f;
  const float magic_bias = 0x1.800000p19f;
  const float log2e = 0x1.715476p+0f;
  const float c3 = 0x1.55561Cp-3f;
  const float c2 = 0x1.0001ECp-1f;
  const float minus_ln2_hi = -0x1.62E400p-1f;
  const float minus_ln2_lo = -0x1.7F7D1Cp-20f;

  float z = fmaxf(x, sat_cutoff);
  float n = fused ? fmaf(z, log2e, magic_bias)
                  : mul_add_separate(magic_bias, z, log2e);
  const uint32_t n_bits = to_bits(n);
  const uint32_t idx = n_bits & 0xFu;
  const uint32_t en = n_bits << 19;
  const uint32_t l = table[idx];
  n = n - magic_bias;
  float t = fused ? fmaf(n, minus_ln2_hi, z)
                  : mul_add_separate(z, n, minus_ln2_hi);
  t = fused ? fmaf(n, minus_ln2_lo, t)
            : mul_add_separate(t, n, minus_ln2_lo);
  float s = from_bits(l + en);
  float p = fused ? fmaf(t, c3, c2)
                  : mul_add_separate(c2, t, c3);
  p = p * t;
  t = t * s;
  s = s - 1.0f;
  p = fused ? fmaf(p, t, t) : mul_add_separate(t, p, t);
  const float ve = p + s;
  return x < 0.0f ? ve : x;
}

int main(void) {
  if (fegetround() != FE_TONEAREST) {
    fprintf(stderr, "requires FE_TONEAREST\n");
    return 2;
  }
  if (to_bits(1.0f) != 0x3F800000u) {
    fprintf(stderr, "requires IEEE-754 binary32 object representation\n");
    return 2;
  }

  /* Confirm that halfway additions use the ties-to-even rule. */
  volatile float one = 1.0f;
  volatile float half_ulp = 0x1p-24f;
  volatile float halfway_result = one + half_ulp;
  if (to_bits(halfway_result) != 0x3F800000u) {
    fprintf(stderr, "requires round-to-nearest, ties-to-even\n");
    return 2;
  }

  const uint32_t input_bits = 0xBB44B983u;
  const float input = from_bits(input_bits);
  const float separate = elu(input, 0);
  const float fused = elu(input, 1);
  const uint32_t separate_bits = to_bits(separate);
  const uint32_t fused_bits = to_bits(fused);

  printf("x=0x%08X (%a)\n", input_bits, input);
  printf("separate=0x%08X (%a)\n", separate_bits, separate);
  printf("fused=0x%08X (%a)\n", fused_bits, fused);

  return separate_bits == 0xBB446E00u &&
      fused_bits == 0xBB446DFFu ? 0 : 1;
}
