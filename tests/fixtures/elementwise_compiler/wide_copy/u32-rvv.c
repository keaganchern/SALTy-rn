void test_rvv_u32(
    size_t batch,
    const uint32_t* input,
    uint32_t* output)
{
  assert(batch != 0);
  assert(batch % sizeof(uint32_t) == 0);
  assert(input != NULL);
  assert(output != NULL);

  size_t n = batch / sizeof(uint32_t);
  while (n > 0) {
    const size_t vl = salt_rvv_setvl_u32(n);
    const salt_vu32m1_t value = salt_rvv_load_u32(input, vl);
    salt_rvv_store_u32(output, value, vl);
    input += vl;
    output += vl;
    n -= vl;
  }
}
