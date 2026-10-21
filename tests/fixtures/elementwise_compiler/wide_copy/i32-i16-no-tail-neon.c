void test_neon_i32_i16_no_tail(
    size_t batch,
    const int32_t* input,
    int16_t* output)
{
  assert(batch != 0);
  assert(batch % (4 * sizeof(int32_t)) == 0);
  assert(input != NULL);
  assert(output != NULL);

  for (; batch >= 4 * sizeof(int32_t); batch -= 4 * sizeof(int32_t)) {
    const salt_i32x4_t value = salt_neon_load4_i32(input); input += 4;
    const salt_i16x4_t narrowed = salt_neon_narrow_i16(value);
    salt_neon_store4_i16(output, narrowed); output += 4;
  }
}
