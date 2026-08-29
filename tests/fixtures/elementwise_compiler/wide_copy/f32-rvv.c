void test_rvv_f32(
    size_t batch,
    const float* input,
    float* output)
{
  assert(batch != 0);
  assert(batch % sizeof(float) == 0);
  assert(input != NULL);
  assert(output != NULL);

  size_t n = batch / sizeof(float);
  while (n > 0) {
    const size_t vl = salt_rvv_setvl_f32(n);
    const salt_vf32m1_t value = salt_rvv_load_f32(input, vl);
    salt_rvv_store_f32(output, value, vl);
    input += vl;
    output += vl;
    n -= vl;
  }
}
