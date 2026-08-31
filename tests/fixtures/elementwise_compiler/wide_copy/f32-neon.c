void test_neon_f32(
    size_t batch,
    const float* input,
    float* output)
{
  assert(batch != 0);
  assert(batch % sizeof(float) == 0);
  assert(input != NULL);
  assert(output != NULL);

  for (; batch >= 4 * sizeof(float); batch -= 4 * sizeof(float)) {
    const salt_f32x4_t value = salt_neon_load4_f32(input); input += 4;
    salt_neon_store4_f32(output, value); output += 4;
  }
  if (batch != 0) {
    const salt_f32x4_t value = salt_neon_load4_f32(input);
    salt_f32x2_t live = salt_neon_low2_f32(value);
    if (batch & (2 * sizeof(float))) {
      salt_neon_store2_f32(output, live); output += 2;
      live = salt_neon_high2_f32(value);
    }
    if (batch & (1 * sizeof(float))) {
      salt_neon_store1_f32(output, live, 0);
    }
  }
}
