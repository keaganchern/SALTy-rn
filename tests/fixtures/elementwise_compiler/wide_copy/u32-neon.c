void test_neon_u32(
    size_t batch,
    const uint32_t* input,
    uint32_t* output)
{
  assert(batch != 0);
  assert(batch % sizeof(uint32_t) == 0);
  assert(input != NULL);
  assert(output != NULL);

  for (; batch >= 4 * sizeof(uint32_t); batch -= 4 * sizeof(uint32_t)) {
    const salt_u32x4_t value = salt_neon_load4_u32(input); input += 4;
    salt_neon_store4_u32(output, value); output += 4;
  }
  if (batch != 0) {
    const salt_u32x4_t value = salt_neon_load4_u32(input);
    salt_u32x2_t live = salt_neon_low2_u32(value);
    if (batch & (2 * sizeof(uint32_t))) {
      salt_neon_store2_u32(output, live); output += 2;
      live = salt_neon_high2_u32(value);
    }
    if (batch & (1 * sizeof(uint32_t))) {
      salt_neon_store1_u32(output, live, 0);
    }
  }
}
