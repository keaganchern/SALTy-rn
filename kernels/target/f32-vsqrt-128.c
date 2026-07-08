void test_rvv(
    size_t batch,
    const float* input,
    float* output,
    const struct xnn_f32_default_params* unused_params)
{
  assert(batch != 0);
  assert(batch % sizeof(float) == 0);
  assert(input != NULL);
  assert(output != NULL);

  size_t n = batch / sizeof(float);
  while (n > 0) {
    size_t vl = __riscv_vsetvl_e32m8(n);
    vfloat32m8_t vx = __riscv_vle32_v_f32m8(input, vl);
    vfloat32m8_t vy = __riscv_vfsqrt_v_f32m8(vx, vl);
    __riscv_vse32_v_f32m8(output, vy, vl);
    input += vl;
    output += vl;
    n -= vl;
  }
}