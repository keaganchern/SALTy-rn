void test_neon_u16_no_tail(
    size_t batch,
    const uint16_t* input,
    uint16_t* output)
{
  assert(batch != 0);
  assert(batch % (4 * sizeof(uint16_t)) == 0);
  assert(input != NULL);
  assert(output != NULL);

  for (; batch >= 4 * sizeof(uint16_t); batch -= 4 * sizeof(uint16_t)) {
    const salt_u16x4_t value = salt_neon_load4_u16(input); input += 4;
    salt_neon_store4_u16(output, value); output += 4;
  }
}
