void test_neon_real_f32(
    size_t batch,
    const float* input,
    float* output)
{
  assert(batch != 0);
  assert(batch % sizeof(float) == 0);
  assert(input != NULL);
  assert(output != NULL);

  for (; batch >= 4 * sizeof(float); batch -= 4 * sizeof(float)) {
    const float32x4_t value = vld1q_f32(input); input += 4;
    vst1q_f32(output, value); output += 4;
  }
  if (batch != 0) {
    const float32x4_t value = vld1q_f32(input);
    float32x2_t live = vget_low_f32(value);
    if (batch & (2 * sizeof(float))) {
      vst1_f32(output, live); output += 2;
      live = vget_high_f32(value);
    }
    if (batch & (1 * sizeof(float))) {
      vst1_lane_f32(output, live, 0);
    }
  }
}
