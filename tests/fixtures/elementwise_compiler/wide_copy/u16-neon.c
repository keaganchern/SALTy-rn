void test_neon_u16(
    size_t batch,
    const uint16_t* input,
    uint16_t* output)
{
  assert(batch != 0);
  assert(batch % sizeof(uint16_t) == 0);
  assert(input != NULL);
  assert(output != NULL);

  for (; batch >= 4 * sizeof(uint16_t); batch -= 4 * sizeof(uint16_t)) {
    const salt_u16x4_t value = salt_neon_load4_u16(input); input += 4;
    salt_neon_store4_u16(output, value); output += 4;
  }
  if (batch != 0) {
    const salt_u16x4_t value = salt_neon_load4_u16(input);
    salt_u16x2_t live = salt_neon_low2_u16(value);
    if (batch & (2 * sizeof(uint16_t))) {
      salt_neon_store2_u16(output, live); output += 2;
      live = salt_neon_high2_u16(value);
    }
    if (batch & (1 * sizeof(uint16_t))) {
      salt_neon_store1_u16(output, live, 0);
    }
  }
}
