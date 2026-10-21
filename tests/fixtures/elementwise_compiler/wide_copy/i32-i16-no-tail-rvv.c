void test_rvv_i32_i16_no_tail(
    size_t batch,
    const int32_t* input,
    int16_t* output)
{
  assert(batch != 0);
  assert(batch % (4 * sizeof(int32_t)) == 0);
  assert(input != NULL);
  assert(output != NULL);

  size_t n = batch / sizeof(int32_t);
  while (n > 0) {
    const size_t vl = salt_rvv_setvl_i32_i16(n);
    const salt_vi32m1_t value = salt_rvv_load_i32(input, vl);
    const salt_vi16m1_t narrowed = salt_rvv_narrow_i16(value, 0, 2, vl);
    salt_rvv_store_i16(output, narrowed, vl);
    input += vl;
    output += vl;
    n -= vl;
  }
}
