#include <arm_neon.h>

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

static uint32_t reference_srshl_s32(int32_t value, int count) {
  if (count < 0) {
    const int right = -count;
    if (right >= 32) {
      return 0;
    }
    const int64_t rounded = (int64_t) value + (INT64_C(1) << (right - 1));
    return (uint32_t) (rounded >> right);
  }
  if (count >= 32) {
    return 0;
  }
  return (uint32_t) value << count;
}

int main(void) {
  static const int32_t values[] = {
    0, 1, -1, INT32_MIN, INT32_MAX,
  };
  static const int8_t counts[] = {
    -128, -65, -64, -63, -33, -32, -31, -1, 0, 1, 31, 32, 63, 64, 127,
  };
  size_t checked = 0;
  for (size_t i = 0; i < sizeof(values) / sizeof(values[0]); i++) {
    for (size_t j = 0; j < sizeof(counts) / sizeof(counts[0]); j++) {
      const int32x4_t result = vrshlq_s32(
        vdupq_n_s32(values[i]), vdupq_n_s32(counts[j]));
      const uint32_t actual = vgetq_lane_u32(vreinterpretq_u32_s32(result), 0);
      const uint32_t expected = reference_srshl_s32(values[i], counts[j]);
      if (actual != expected) {
        fprintf(stderr,
          "FAIL value=%" PRId32 " count=%d actual=%08" PRIX32
          " expected=%08" PRIX32 "\n",
          values[i], counts[j], actual, expected);
        return 1;
      }
      if ((values[i] == 1 && counts[j] == -64) ||
          (values[i] == -1 && counts[j] == -65)) {
        printf("edge value=%" PRId32 " count=%d result=%08" PRIX32 "\n",
          values[i], counts[j], actual);
      }
      checked++;
    }
  }
  printf("PASS %zu AArch64 SRSHL cases\n", checked);
  return 0;
}
