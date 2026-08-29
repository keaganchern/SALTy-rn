void test_rvv_real_f32(
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
    const size_t vl = __riscv_vsetvl_e32m8(n);
    const vfloat32m8_t value = __riscv_vle32_v_f32m8(input, vl);
    __riscv_vse32_v_f32m8(output, value, vl);
    input += vl;
    output += vl;
    n -= vl;
  }
}
