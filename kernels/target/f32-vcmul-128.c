void test_rvv(
    size_t batch,
    const float* input_a,
    const float* input_b,
    float* output,
    const struct xnn_f32_default_params* restrict params) XNN_OOB_READS
{
  assert(batch != 0);
  assert(batch % sizeof(float) == 0);
  assert(input_a != NULL);
  assert(input_b != NULL);
  assert(output != NULL);

  const float* ar = input_a;
  const float* ai = (const float*) ((uintptr_t) input_a + batch);
  const float* br = input_b;
  const float* bi = (const float*) ((uintptr_t) input_b + batch);
  float* or = output;
  float* oi = (float*) ((uintptr_t) output + batch);

  size_t n = batch / sizeof(float);
  while (n > 0) {
    size_t vl = __riscv_vsetvl_e32m4(n);

    vfloat32m4_t var = __riscv_vle32_v_f32m4(ar, vl);
    vfloat32m4_t vai = __riscv_vle32_v_f32m4(ai, vl);
    vfloat32m4_t vbr = __riscv_vle32_v_f32m4(br, vl);
    vfloat32m4_t vbi = __riscv_vle32_v_f32m4(bi, vl);

    vfloat32m4_t vaccr = __riscv_vfmul_vv_f32m4(var, vbr, vl);
    vfloat32m4_t vacci = __riscv_vfmul_vv_f32m4(var, vbi, vl);

    // vmlsq_f32 is not fused; compute multiply then subtract
    vfloat32m4_t temp_r = __riscv_vfmul_vv_f32m4(vai, vbi, vl);
    vaccr = __riscv_vfsub_vv_f32m4(vaccr, temp_r, vl);

    // vmlaq_f32 is not fused; compute multiply then add
    vfloat32m4_t temp_i = __riscv_vfmul_vv_f32m4(vai, vbr, vl);
    vacci = __riscv_vfadd_vv_f32m4(vacci, temp_i, vl);

    __riscv_vse32_v_f32m4(or, vaccr, vl);
    __riscv_vse32_v_f32m4(oi, vacci, vl);

    ar += vl;
    ai += vl;
    br += vl;
    bi += vl;
    or += vl;
    oi += vl;
    n -= vl;
  }
}