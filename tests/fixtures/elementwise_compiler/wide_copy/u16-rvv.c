void test_rvv_u16(
    size_t batch,
    const uint16_t* input,
    uint16_t* output)
{
  assert(batch != 0);
  assert(batch % sizeof(uint16_t) == 0);
  assert(input != NULL);
  assert(output != NULL);

  size_t n = batch / sizeof(uint16_t);
  while (n > 0) {
    const size_t vl = salt_rvv_setvl_u16(n);
    const salt_vu16m1_t value = salt_rvv_load_u16(input, vl);
    salt_rvv_store_u16(output, value, vl);
    input += vl;
    output += vl;
    n -= vl;
  }
}
